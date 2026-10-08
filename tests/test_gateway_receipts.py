"""任务回执与输入身份合同；全部子进程为模拟，不安装或运行原生工具。"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
DOMAIN=ROOT.name.removesuffix('-skills')

class ReceiptContract(unittest.TestCase):
    def setUp(self):
        self.scripts=ROOT/'skills'/f'{DOMAIN}-use'/'scripts'
        spec=importlib.util.spec_from_file_location('gateway',self.scripts/'command_gateway.py')
        self.g=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.g)

    def catalog(self):
        return [{'name':'doc_info','input_schema':{'type':'object','properties':{}}}] if DOMAIN=='printcraft' else [{'id':'file.new','params':'','menu':[]}]

    def plan(self,root):
        p=root/'plan.json'
        p.write_text(json.dumps({'domain':DOMAIN,'steps':[{'command':'doc_info' if DOMAIN=='printcraft' else 'file.new','params':{}}]}))
        return p

    def invoke(self,argv,side_effect):
        with patch.object(sys,'argv',['commands.py',*argv]),patch.object(self.g.subprocess,'run',side_effect=side_effect) as run,contextlib.redirect_stdout(io.StringIO()):
            result=self.g.main(DOMAIN,self.scripts)
            return result,run.call_count

    def test_receipt_binds_explicit_input_and_actual_runtime_lock(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'input.bin';source.write_bytes(b'original input');output=root/'output'
            discovery=subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
            success=subprocess.CompletedProcess([],0,'native output','')
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output),'--input',str(source)],[discovery,success])
            self.assertEqual((result,count),(0,2))
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertEqual(receipt['inputSha256'][str(source)],hashlib.sha256(b'original input').hexdigest())
            self.assertEqual(receipt['runtimeLockSha256'],hashlib.sha256((self.scripts/'runtime.lock.json').read_bytes()).hexdigest())
            self.assertFalse(receipt['completeAcceptance'])
            self.assertEqual(receipt['status'],'NATIVE_EXIT_ZERO_REVIEW_REQUIRED')

    def test_inner_unknown_result_overrides_exit_one(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);output=root/'output'
            def native(argv,**kwargs):
                if '--result-file' not in argv:
                    return subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
                channel=Path(argv[argv.index('--result-file')+1])
                channel.write_text(json.dumps({'protocol':'printcraft.execution/1','status':'UNKNOWN','phase':'native-timeout','exitCode':None,'wrapperExitCode':1,'stdout':'partial','stderr':'','automaticReplay':False}))
                return subprocess.CompletedProcess([],1,'','')
            code,count=self.invoke(['run',str(self.plan(root)),'--output',str(output)],native)
            self.assertEqual(json.loads((output/'receipt.json').read_text())['status'],'UNKNOWN')
            self.assertEqual((code,count),(1,2))

    def test_same_run_id_different_output_never_replays(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);plan=self.plan(root)
            discovery=subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'');success=subprocess.CompletedProcess([],0,'','')
            code,count=self.invoke(['run',str(plan),'--output',str(root/'first'),'--run-id','same'],[discovery,success])
            self.assertEqual(code,0)
            (root/'first/receipt.json').unlink()
            code,count=self.invoke(['run',str(plan),'--output',str(root/'second'),'--run-id','same'],[discovery])
            self.assertEqual((code,count),(1,1));self.assertFalse((root/'second').exists())

    def test_secret_echo_is_redacted_and_private_material_removed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);output=root/'out';plan=root/'secret.json';plan.write_text(json.dumps({'domain':DOMAIN,'steps':[{'command':'doc_open','params':{'password':'secret-value'}}]}))
            catalog=[{'name':'doc_open','input_schema':{'type':'object','properties':{'password':{'type':'string'}}}}]
            result,count=self.invoke(['run',str(plan),'--output',str(output)],[subprocess.CompletedProcess([],0,json.dumps(catalog),''),subprocess.CompletedProcess([],1,'echo secret-value','error secret-value')])
            text=(output/'receipt.json').read_text();self.assertNotIn('secret-value',text);self.assertIn('[REDACTED]',text)
            self.assertFalse((output/'native-plan.json').exists());self.assertFalse((output/'native-result.json').exists())
            self.assertEqual((output/'receipt.json').stat().st_mode & 0o777,0o600)

    def test_changed_input_during_discovery_blocks_native_edit(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'input.bin';source.write_bytes(b'original');output=root/'output'
            def changed(argv,**kwargs):
                source.write_bytes(b'changed while installing')
                return subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output),'--input',str(source)],changed)
            self.assertEqual((result,count),(1,1))
            self.assertFalse(output.exists())

    def test_input_missing_is_rejected_before_discovery(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(root/'out'),'--input',str(root/'missing')],AssertionError('must not start'))
            self.assertEqual((result,count),(1,0))

    def test_timeout_keeps_partial_logs_and_unknown_without_replay(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);output=root/'output'
            discovery=subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
            timeout=subprocess.TimeoutExpired(['native'],900,output=b'partial output',stderr=b'partial error')
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output)],[discovery,timeout])
            self.assertEqual((result,count),(1,2))
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertEqual(receipt['status'],'UNKNOWN')
            self.assertEqual(receipt['stdout'],'partial output')
            self.assertEqual(receipt['stderr'],'partial error')
            self.assertFalse(receipt['automaticReplay'])

    def test_changed_input_on_zero_exit_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'input.bin';source.write_bytes(b'original');output=root/'output';calls=[]
            def native(argv,**kwargs):
                calls.append(argv)
                if len(calls)==1:return subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
                source.write_bytes(b'changed by native operation')
                return subprocess.CompletedProcess([],0,'','')
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output),'--input',str(source)],native)
            self.assertEqual((result,count),(1,2))
            self.assertEqual(json.loads((output/'receipt.json').read_text())['status'],'INPUT_CHANGED_REVIEW_REQUIRED')

if __name__=='__main__':unittest.main()

class OutputDeclaration(unittest.TestCase):
    setUp=ReceiptContract.setUp
    catalog=ReceiptContract.catalog
    plan=ReceiptContract.plan
    invoke=ReceiptContract.invoke
    def test_zero_exit_missing_declared_output_fails_delivery(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);expected=root/'outputs.json';expected.write_text(json.dumps({'outputs':[{'path':str(root/'missing.pdf'),'role':'delivery','mediaType':'application/pdf'}]}))
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(root/'run'),'--expect',str(expected)],[subprocess.CompletedProcess([],0,json.dumps(self.catalog()),''),subprocess.CompletedProcess([],0,'','')])
            self.assertEqual(result,1);receipt=json.loads((root/'run/receipt.json').read_text());self.assertEqual(receipt['status'],'OUTPUT_INVALID_REVIEW_REQUIRED');self.assertEqual(receipt['artifacts'][0]['status'],'MISSING')
    def test_corrupt_receipt_is_detected_by_registry_on_reconcile(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);self.invoke(['run',str(self.plan(root)),'--output',str(root/'run')],[subprocess.CompletedProcess([],0,json.dumps(self.catalog()),''),subprocess.CompletedProcess([],0,'','')])
            p=root/'run/receipt.json';data=json.loads(p.read_text());data['status']='UNKNOWN';p.write_text(json.dumps(data))
            result,count=self.invoke(['reconcile',str(p)],AssertionError('read-only'))
            self.assertEqual((result,count),(1,0));self.assertEqual(json.loads(p.read_text())['status'],'UNKNOWN')
