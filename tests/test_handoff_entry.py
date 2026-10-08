"""真实公开交接入口回归，不安装或启动原生程序。"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PublicHandoff(unittest.TestCase):
    def test_compatible_explicit_version_without_native_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);pdf=root/'provided.pdf';pdf.write_bytes(b'%PDF-1.4\n%%EOF')
            request=root/'handoff.json';request.write_text(json.dumps({'protocol':'artcraft.printcraft-handoff/1','producer':'artcraft','producerVersion':'0.1.0-dev.113-runtime.1','files':[{'path':str(pdf),'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()}]}))
            command=[sys.executable,'-I','-B',str(ROOT/'skills/printcraft-use/scripts/commands.py'),'handoff',str(request),'--producer-version','0.1.0-dev.113-runtime.1','--runtime-home',str(root/'not-installed')]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            observed=json.loads(result.stdout)
            self.assertEqual(observed['status'],'HANDOFF_INTEGRITY_PASS')
            self.assertFalse(observed['automaticExecution']);self.assertFalse((root/'not-installed').exists())
            missing=subprocess.run(command[:6]+command[8:],capture_output=True,text=True)
            self.assertNotEqual(missing.returncode,0)
            self.assertIn('explicit_producer_version_required',missing.stdout)
            wrong=subprocess.run([*command[:7],'99.0.0',*command[8:]],capture_output=True,text=True)
            self.assertNotEqual(wrong.returncode,0)
            self.assertIn('incompatible_producer_version',wrong.stdout)
            self.assertEqual(hashlib.sha256(pdf.read_bytes()).hexdigest(),json.loads(request.read_text())['files'][0]['sha256'])

if __name__=='__main__':unittest.main()
