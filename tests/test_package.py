"""独立技能源本地合同；不运行原生程序。"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
DOMAIN=ROOT.name.removesuffix('-skills')

class PackageContract(unittest.TestCase):
    def test_structure_and_resources(self):
        p=ROOT/'scripts/validate_package.py'
        spec=importlib.util.spec_from_file_location('validator',p)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.validate()['skills'],6)

    def test_each_skill_gateway_runs_alone_in_python_isolated_mode(self):
        raw=[{'name':'doc_info','input_schema':{'type':'object','properties':{}}}] if DOMAIN=='printcraft' else [{'id':'file.new','label':'New','params':'','menu':['File']}]
        for entry in sorted((ROOT/'skills').glob('*/SKILL.md')):
            source=entry.parent
            with self.subTest(skill=source.name),tempfile.TemporaryDirectory(prefix='独立 技能 ') as t:
                root=Path(t);skill=root/source.name;shutil.copytree(source,skill)
                catalog=root/'catalog.json';catalog.write_text(json.dumps(raw))
                out=subprocess.run([sys.executable,'-I','-B',str(skill/'scripts/commands.py'),'list','--catalog',str(catalog)],capture_output=True,text=True)
                self.assertEqual(out.returncode,0,out.stdout+out.stderr)
                self.assertEqual(json.loads(out.stdout)['count'],1)

    def test_invalid_native_subcommand_rejects_before_installation(self):
        with tempfile.TemporaryDirectory() as t:
            runtime=Path(t)/'runtime'
            out=subprocess.run([sys.executable,'-I','-B',str(ROOT/'skills'/f'{DOMAIN}-use'/'scripts/cli.py'),'--runtime-home',str(runtime),'--','sh'],capture_output=True,text=True)
            self.assertNotEqual(out.returncode,0)
            self.assertIn('unsupported_cli_subcommand',out.stderr)
            self.assertFalse(runtime.exists())

if __name__=='__main__':unittest.main()
