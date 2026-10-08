"""执行合同回归；子进程使用本地夹具，不访问真实服务。"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'skills/printcraft-use/scripts'

def load(name):
    spec=importlib.util.spec_from_file_location(name,SCRIPTS/(name+'.py'))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

class ExecutionHardening(unittest.TestCase):
    def test_versioned_inner_timeout_crosses_real_wrapper(self):
        e=load('execution')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);result=root/'result.json'
            child=root/'child.py';child.write_text('import time\nprint("partial",flush=True)\ntime.sleep(10)\n')
            wrapper=root/'wrapper.py'
            wrapper.write_text('import importlib.util,sys\nfrom pathlib import Path\ns=importlib.util.spec_from_file_location("execution",'+repr(str(SCRIPTS/'execution.py'))+')\nm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nr=m.execute([sys.executable,'+repr(str(child))+'],0.05,Path('+repr(str(result))+'))\nraise SystemExit(r["wrapperExitCode"])\n')
            outer=subprocess.run([sys.executable,'-I',str(wrapper)],capture_output=True,text=True,timeout=5)
            observed=e.read_result(result)
            self.assertNotEqual(outer.returncode,0)
            self.assertEqual(observed['status'],'UNKNOWN')
            self.assertIn('partial',observed['stdout'])
            self.assertFalse(observed['automaticReplay'])
    def test_service_eof_does_not_use_edit_deadline(self):
        e=load('execution')
        self.assertIsNone(e.timeout_for('mcp'))
        self.assertGreater(e.timeout_for('render'),e.timeout_for('tools'))
        with tempfile.TemporaryDirectory() as t:
            result=e.execute([sys.executable,'-c','import sys; print(sys.stdin.read())'],None,Path(t)/'r.json',stdin=subprocess.DEVNULL)
            self.assertEqual(result['exitCode'],0)
    def test_private_atomic_state_and_lock(self):
        e=load('execution')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'state.json';e.atomic_json(p,{'protocol':'printcraft.execution/1','runId':'r','attempted':True})
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
            with e.run_lock(Path(t)):
                with self.assertRaisesRegex(ValueError,'controller_busy'):
                    with e.run_lock(Path(t)):pass
            self.assertEqual(e.reconcile(p)['status'],'UNKNOWN')
            p.write_text('{}')
            with self.assertRaises(ValueError):e.reconcile(p)
    def test_sensitive_values_are_removed(self):
        e=load('execution');plan={'password':'hunter2','nested':{'api_key':'private'}}
        self.assertEqual(e.redact('hunter2 private',e.secrets(plan)),'[REDACTED] [REDACTED]')
    def test_unknown_protocol_fails_closed(self):
        e=load('execution')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'r';p.write_text('{"protocol":"printcraft.execution/99"}')
            with self.assertRaises(ValueError):e.read_result(p)

if __name__=='__main__':unittest.main()

class StopAndFailure(unittest.TestCase):
    def test_start_failure_is_not_retried(self):
        e=load('execution');r=e.execute(['/definitely/missing/native'],1)
        self.assertEqual(r['phase'],'start-failed');self.assertFalse(r['automaticReplay'])
    def test_explicit_service_stop_persists_unknown(self):
        import os,time,signal
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);result=root/'result.json';wrapper=root/'wrapper.py'
            wrapper.write_text('import importlib.util,sys\nfrom pathlib import Path\ns=importlib.util.spec_from_file_location("e",'+repr(str(SCRIPTS/'execution.py'))+')\nm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nm.execute([sys.executable,"-c","import time;time.sleep(20)"],None,Path('+repr(str(result))+'))\n')
            p=subprocess.Popen([sys.executable,str(wrapper)])
            try:
                for _ in range(100):
                    if result.exists():break
                    time.sleep(.01)
                self.assertTrue(result.exists());p.send_signal(signal.SIGTERM);p.wait(timeout=3)
                r=json.loads(result.read_text());self.assertEqual(r['status'],'UNKNOWN');self.assertEqual(r['phase'],'interrupted');self.assertFalse(r['descendantsConfirmedStopped'])
            finally:
                if p.poll() is None:p.kill();p.wait()

class FingerprintPrivacy(unittest.TestCase):
    def test_secret_redaction_does_not_corrupt_resource_hashes(self):
        e=load('execution');receipt={'planSha256':'a'*64,'stdout':'secret=a','inputSha256':{'/input.pdf':'a'*64}}
        observed=e.public_receipt(receipt,['a']);self.assertEqual(observed['planSha256'],'a'*64);self.assertEqual(observed['inputSha256'],receipt['inputSha256']);self.assertNotIn('secret=a',observed['stdout'])

class RealNestedGateway(unittest.TestCase):
    def test_actual_gateway_cli_and_native_timeout_keep_unknown(self):
        import shutil
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);scripts=root/'scripts';shutil.copytree(SCRIPTS,scripts);inner=scripts/'inner';shutil.copytree(SCRIPTS,inner)
            binary=root/'native-fixture';binary.write_text('#!'+sys.executable+'\nimport sys,time,json\nif sys.argv[1]=="tools":print(json.dumps([{\"name\":\"doc_info\",\"input_schema\":{\"type\":\"object\",\"properties\":{}}}]))\nelse:\n print("partial-native",flush=True)\n time.sleep(10)\n');binary.chmod(0o755)
            (inner/'bootstrap.py').write_text('def install(*args):return {"executable":'+repr(str(binary))+'}\n')
            (scripts/'cli.py').write_text('import sys,runpy\nif "run" in sys.argv:\n sys.argv.insert(1,"--timeout");sys.argv.insert(2,"0.5")\nrunpy.run_path('+repr(str(inner/'cli.py'))+',run_name="__main__")\n')
            import os
            if os.environ.get('PRINTCRAFT_LEGACY_EXIT_ONLY')=='1':
                # 重建已知旧退出码分支用于红灯证据；不是原 Git 快照，也不改生产源。
                gateway=scripts/'command_gateway.py';legacy=gateway.read_text().replace('if channel.exists():','if False and channel.exists():').replace("else 'UNKNOWN',phase='legacy-exit'","else 'FAILED_OR_PARTIAL',phase='legacy-exit'");gateway.write_text(legacy)
            plan=root/'plan.json';plan.write_text('{"domain":"printcraft","steps":[{"command":"doc_info","params":{}}]}')
            result=subprocess.run([sys.executable,'-I',str(scripts/'commands.py'),'run',str(plan),'--output',str(root/'task')],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            self.assertTrue((root/'task/receipt.json').exists(),result.stdout+result.stderr)
            receipt=json.loads((root/'task/receipt.json').read_text());self.assertEqual(receipt['status'],'UNKNOWN');self.assertEqual(receipt['phase'],'native-timeout');self.assertIn('partial-native',receipt['stdout'])

class AuthorizationScope(unittest.TestCase):
    def test_existing_authorization_reused_new_overwrite_and_print_reported(self):
        e=load('execution')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'original.pdf';p.write_bytes(b'original')
            plan={'steps':[{'command':'doc_open','params':{'path':str(p)}},{'command':'doc_save','params':{'doc':1}},{'command':'doc_print','params':{'doc':1}}]}
            scope=['overwrite:'+str(p),'print'];self.assertEqual(e.missing_scope(plan,scope),[]);self.assertEqual(e.missing_scope(plan,[]),scope)
            plan['steps'][1]['params']['path']=str(Path(t)/'new.pdf');self.assertEqual(e.missing_scope(plan,[]),['print'])
