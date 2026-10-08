"""同步器必须保留用户漂移和已发布快照；只修改临时测试副本。"""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
DOMAIN=ROOT.name.removesuffix('-skills')
def fixture(target):
    target.mkdir();shutil.copytree(ROOT/'skills',target/'skills',ignore=shutil.ignore_patterns('__pycache__','.DS_Store'))
    module_path=ROOT/'scripts/sync_local_snapshot.py'
    spec=importlib.util.spec_from_file_location('fixture_sync',module_path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    (target/'plugin.json').write_text(json.dumps({'name':DOMAIN}))
    (target/'candidate-source.json').write_text(json.dumps({'sourceProject':ROOT.name,'sourceStatus':'local-unpublished-candidate','sourceVersion':'0.1.0-dev.1','releaseTag':None,'skillFileSha256':m.inventory(target/'skills')}))

class SnapshotSyncContract(unittest.TestCase):
    def module(self):
        path=ROOT/'scripts/sync_local_snapshot.py'
        spec=importlib.util.spec_from_file_location('snapshot_sync',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_user_snapshot_edits_are_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            target=Path(t)/'plugin';fixture(target)
            skill=target/'skills'/f'{DOMAIN}-use'/'SKILL.md'
            skill.write_text(skill.read_text()+'\nUser edit must survive\n')
            before=skill.read_bytes();lock=(target/'candidate-source.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'preserve_modified_plugin_snapshot'):
                self.module().sync(target)
            self.assertEqual(skill.read_bytes(),before)
            self.assertEqual((target/'candidate-source.json').read_bytes(),lock)

    def test_published_source_identity_is_never_replaced_by_local_candidate(self):
        with tempfile.TemporaryDirectory() as t:
            target=Path(t)/'plugin';fixture(target)
            path=target/'candidate-source.json';data=json.loads(path.read_text());data['releaseTag']='v0.1.0';path.write_text(json.dumps(data))
            before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'not_current_local_candidate'):
                self.module().sync(target)
            self.assertEqual(path.read_bytes(),before)

if __name__=='__main__':unittest.main()

class IndependentSync(unittest.TestCase):
    def test_normal_sync_keeps_local_harness_and_updates_source_version(self):
        with tempfile.TemporaryDirectory() as t:
            target=Path(t)/'plugin';fixture(target)
            local=target/'skills/printcraft-harness';local.mkdir();(local/'SKILL.md').write_text('local owned')
            module=SnapshotSyncContract().module();result=module.sync(target)
            self.assertEqual(result['snapshot'],'PASS');self.assertEqual((local/'SKILL.md').read_text(),'local owned')
            self.assertEqual(json.loads((target/'candidate-source.json').read_text())['sourceVersion'],json.loads((ROOT/'skill-suite.json').read_text())['version'])
    def test_source_removal_and_foreign_skill_preserve_all_files(self):
        for mode in ('removal','foreign'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                target=Path(t)/'plugin';fixture(target);m=SnapshotSyncContract().module()
                path=target/'skills/printcraft-use/scripts/deleted.txt' if mode=='removal' else target/'skills/foreign/SKILL.md';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('keep')
                lockpath=target/'candidate-source.json';lock=json.loads(lockpath.read_text());lock['skillFileSha256']=m.inventory(target/'skills');lockpath.write_text(json.dumps(lock));before=lockpath.read_bytes()
                with self.assertRaises(ValueError):m.sync(target)
                self.assertEqual(path.read_text(),'keep');self.assertEqual(lockpath.read_bytes(),before)
