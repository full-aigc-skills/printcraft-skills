"""版本化执行结果、私有原子状态和只读对账；不重放写入。"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import threading

PROTOCOL='printcraft.execution/1'
STATES={'UNKNOWN','FAILED_OR_PARTIAL','NATIVE_EXIT_ZERO_REVIEW_REQUIRED','INPUT_CHANGED_REVIEW_REQUIRED','SKILL_CHANGED_REVIEW_REQUIRED','INPUT_OR_SKILL_CHANGED_REVIEW_REQUIRED','STARTED','OUTPUT_INVALID_REVIEW_REQUIRED'}

def atomic_json(path,data):
    path=Path(path)
    if path.is_symlink():raise ValueError('state_symlink')
    fd,name=tempfile.mkstemp(prefix='.private-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            os.fchmod(stream.fileno(),0o600);json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

@contextmanager
def run_lock(directory):
    fd=os.open(Path(directory)/'.controller.lock',os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('controller_busy') from None
        yield
    finally:os.close(fd)

def timeout_for(command):
    return None if command in {'mcp','ui'} else 1800 if command in {'render','run'} else 600 if command=='edit' else 120

def text(value):
    return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value or ''

def secrets(value):
    result=[]
    if isinstance(value,dict):
        for key,item in value.items():
            if any(word in key.lower().replace('-','_') for word in ('password','passwd','secret','token','api_key','credential')) and isinstance(item,(str,int)) and not isinstance(item,bool):
                if str(item):result.append(str(item))
            result.extend(secrets(item))
    elif isinstance(value,list):
        for item in value:result.extend(secrets(item))
    return sorted(set(result),key=len,reverse=True)

def redact(value,values):
    if isinstance(value,str):
        for secret in values:value=value.replace(secret,'[REDACTED]')
        return value
    if isinstance(value,dict):return {k:redact(v,values) for k,v in value.items()}
    if isinstance(value,list):return [redact(v,values) for v in value]
    return value

def public_receipt(data,values):
    """只脱敏诊断文字，不破坏绑定身份的 SHA-256；路径不应携带秘密。"""
    result=dict(data)
    for key in ('stdout','stderr','error','preservationCheckError'):
        if key in result:result[key]=redact(result[key],values)
    return result

def required_scope(plan):
    """识别计划中显式保存覆盖和真实打印；不是对所有原生能力的沙箱。"""
    required=set();opened={};next_id=1
    for step in plan['steps']:
        command=step['command'];params=step['params']
        if command=='doc_open' and isinstance(params.get('path'),str):opened[next_id]=str(Path(params['path']).absolute());next_id+=1
        if command=='doc_print':required.add('print')
        target=params.get('path') if command=='doc_save' else params.get('out')
        if command=='doc_save' and not target:
            target=opened.get(params.get('doc'))
            if target is None:required.add('in-place:unresolved')
        if target and Path(target).exists():required.add('overwrite:'+str(Path(target).absolute()))
    return required

def missing_scope(plan,authorized):return sorted(required_scope(plan)-set(authorized))

def read_result(path):
    data=json.loads(Path(path).read_text())
    if data.get('protocol')!=PROTOCOL:raise ValueError('execution_protocol_unsupported_or_legacy')
    if data.get('status') not in STATES:raise ValueError('execution_state_invalid')
    return data

def output_inventory(outputs):
    observed=[]
    for item in outputs:
        path=Path(item['path']);entry=dict(item,path=str(path.absolute()),status='MISSING')
        if path.is_symlink():entry['status']='SYMLINK_REJECTED'
        elif path.is_file():
            data=path.read_bytes();entry.update(size=len(data),sha256=hashlib.sha256(data).hexdigest(),status='PRESENT' if data else 'EMPTY')
        observed.append(entry)
    return observed

def reconcile(path):
    data=json.loads(Path(path).read_text())
    if data.get('protocol')!=PROTOCOL or not isinstance(data.get('runId'),str) or not data['runId']:raise ValueError('legacy_or_invalid_state_readonly')
    result=dict(data)
    if data.get('runRegistry'):
        marker=Path(data['runRegistry'])/(data['runId']+'.json')
        identity=json.loads(marker.read_text())
        if identity.get('runId')!=data['runId'] or identity.get('receipt')!=str(Path(path).absolute()):raise ValueError('run_identity_mismatch')
        if identity.get('receiptSha256') and identity['receiptSha256']!=hashlib.sha256(Path(path).read_bytes()).hexdigest():raise ValueError('receipt_fingerprint_mismatch')
    result['artifacts']=output_inventory(data.get('expectedOutputs',[]))
    old={item['path']:item.get('sha256') for item in data.get('artifacts',[])}
    result['outputDrift']=[item['path'] for item in result['artifacts'] if old.get(item['path'])!=item.get('sha256')]
    if data.get('pid'):
        try:os.kill(data['pid'],0);result['processObservation']='ALIVE_IDENTITY_NOT_CONFIRMED'
        except ProcessLookupError:result['processObservation']='NOT_FOUND'
        except PermissionError:result['processObservation']='INACCESSIBLE_IDENTITY_NOT_CONFIRMED'
    if result.get('attempted') and result.get('status') in {None,'STARTED'}:result['status']='UNKNOWN'
    result.update(reconcileOnly=True,automaticReplay=False,documentIdsReusable=False)
    return result

def execute(argv,timeout,result_file=None,capture=True,stdin=None):
    started=time.time();process=None
    result={'protocol':PROTOCOL,'status':'UNKNOWN','phase':'starting','exitCode':None,'wrapperExitCode':1,'automaticReplay':False,'stdout':'','stderr':'','startedAt':started,'descendantsConfirmedStopped':False}
    previous=None
    if threading.current_thread() is threading.main_thread():
        previous=signal.getsignal(signal.SIGTERM)
        def stop(signum,frame):raise KeyboardInterrupt('explicit_stop')
        signal.signal(signal.SIGTERM,stop)
    try:
        process=subprocess.Popen(argv,stdin=stdin,stdout=subprocess.PIPE if capture else None,stderr=subprocess.PIPE if capture else None,start_new_session=True)
        result.update(phase='native-running',pid=process.pid)
        if result_file:atomic_json(result_file,result)
        stdout,stderr=process.communicate(timeout=timeout)
        result.update(status='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' if process.returncode==0 else 'FAILED_OR_PARTIAL',phase='native-exited',exitCode=process.returncode,wrapperExitCode=process.returncode,stdout=text(stdout),stderr=text(stderr))
    except (subprocess.TimeoutExpired,KeyboardInterrupt) as error:
        result.update(status='UNKNOWN',phase='native-timeout' if isinstance(error,subprocess.TimeoutExpired) else 'interrupted',error=type(error).__name__,stdout=text(getattr(error,'output',None)),stderr=text(getattr(error,'stderr',None)))
        if process:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            try:
                stdout,stderr=process.communicate(timeout=5)
                result.update(stdout=text(stdout) or result['stdout'],stderr=text(stderr) or result['stderr'])
            except (OSError,subprocess.SubprocessError):pass
    except OSError as error:
        result.update(status='FAILED_OR_PARTIAL',phase='start-failed',error=str(error))
    finally:
        if previous is not None:signal.signal(signal.SIGTERM,previous)
    result['finishedAt']=time.time()
    if result_file:atomic_json(result_file,result)
    return result
