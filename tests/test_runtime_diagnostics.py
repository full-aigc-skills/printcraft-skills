import importlib.util
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class Diagnostics(unittest.TestCase):
    def test_diagnose_missing_does_not_write_or_download(self):
        spec=importlib.util.spec_from_file_location('bootstrap',ROOT/'skills/printcraft-use/scripts/bootstrap.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as t,patch.object(m,'download',side_effect=AssertionError('no download')):
            path=Path(t)/'missing';lock=json.loads((ROOT/'skills/printcraft-use/scripts/runtime.lock.json').read_text());r=m.diagnose(lock,path,'darwin-arm64')
            self.assertEqual(r['status'],'MISSING');self.assertFalse(path.exists())
    def test_coverage_detects_new_removed_tool(self):
        spec=importlib.util.spec_from_file_location('coverage',ROOT/'scripts/check_tool_coverage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        r=m.check([{'name':'new'}],{'tools':[{'tool':'old'}]});self.assertEqual(r['added'],['new']);self.assertEqual(r['removed'],['old'])
if __name__=='__main__':unittest.main()

class EvidenceStaleness(unittest.TestCase):
    def test_source_or_evidence_drift_invalidates_index(self):
        spec=importlib.util.spec_from_file_location('evidence',ROOT/'scripts/evidence.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        import hashlib
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'skills').mkdir();(root/'skills/a').write_text('source');artifact=root/'report.json';artifact.write_text('observed')
            index={'sourceSha256':m.fingerprint(root),'evidenceSha256':{'report.json':hashlib.sha256(artifact.read_bytes()).hexdigest()}}
            self.assertTrue(m.current(index,root));artifact.write_text('changed');self.assertFalse(m.current(index,root));artifact.write_text('observed');(root/'skills/a').write_text('changed');self.assertFalse(m.current(index,root))
