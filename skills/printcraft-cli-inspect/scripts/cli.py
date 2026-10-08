#!/usr/bin/env python3
"""独立技能固定运行时入口；执行结果通过私有文件传递，stdout 保留原生协议。"""
import argparse
import importlib.util
import json
import math
import subprocess
import zipfile
import os
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ALLOWED={'extract','render','split','tools','info','check','--version','run','combine','mcp','edit','ui','text'}
def load(name):
    spec=importlib.util.spec_from_file_location('craft_'+name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def setup_failure(runtime_home):
    return {'skill':'printcraft-cli-setup','bootstrapScript':str(Path(__file__).with_name('bootstrap.py').resolve()),'runtimeHome':str(Path(runtime_home).expanduser().absolute()),'automaticRetry':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-home',default=os.environ.get('CRAFT_RUNTIME_HOME',str(Path.home()/'.local/share/craft-runtimes')))
    parser.add_argument('--archive',type=Path);parser.add_argument('--result-file',type=Path)
    parser.add_argument('--timeout',type=float,help='非服务任务秒数；服务只由 EOF/停止结束')
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args();argv=args.arguments
    if argv[:1]==['--']:argv=argv[1:]
    if not argv or argv[0] not in ALLOWED:parser.error('unsupported_cli_subcommand: put the native subcommand first after --')
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout<=0 or argv[0] in {'mcp','ui'}):parser.error('invalid_timeout_or_service_deadline')
    execution=load('execution')
    try:
        installed=load('bootstrap').install(json.loads(Path(__file__).with_name('runtime.lock.json').read_text()),args.runtime_home,args.archive)
    except (ValueError,OSError,subprocess.SubprocessError,zipfile.BadZipFile) as error:
        result={'protocol':execution.PROTOCOL,'status':'FAILED_OR_PARTIAL','phase':'installation','exitCode':None,'wrapperExitCode':1,'automaticReplay':False,'error':str(error),'dependencySetup':setup_failure(args.runtime_home)}
        if args.result_file:execution.atomic_json(args.result_file,result)
        print(json.dumps(result),file=sys.stderr);return 1
    capture=argv[0] not in {'mcp','ui'}
    result=execution.execute([installed['executable'],*argv],args.timeout or execution.timeout_for(argv[0]),args.result_file,capture=capture)
    if capture:
        sys.stdout.write(result.get('stdout',''));sys.stderr.write(result.get('stderr',''))
    if result.get('error'):print(json.dumps({'error':result['error'],'status':result['status']}),file=sys.stderr)
    if args.result_file:
        result['runtimeIdentity']={k:v for k,v in installed.items() if k!='reused'}
        execution.atomic_json(args.result_file,result)
    return result['wrapperExitCode']
if __name__=='__main__':raise SystemExit(main())
