"""PDF 产物合同，不把零退出当验收通过。"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PDFVerification(unittest.TestCase):
    def module(self):
        spec=importlib.util.spec_from_file_location('verification',ROOT/'skills/printcraft-use/scripts/verification.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_missing_empty_corrupt_and_symlink_are_rejected(self):
        v=self.module()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.pdf'
            for content in (None,b'',b'not pdf'):
                if content is not None:p.write_bytes(content)
                with self.assertRaises(ValueError):v.artifact(p)
            p.unlink();p.symlink_to(Path(t)/'other')
            with self.assertRaises(ValueError):v.artifact(p)
    def test_same_page_count_wrong_order_is_rejected(self):
        v=self.module()
        self.assertEqual(v.compare({'pages':2},['A','B'],{'pages':2,'pageText':['B','A']}),['page_1_text_mismatch','page_2_text_mismatch'])
    def test_scan_is_not_reported_as_missing_text(self):
        v=self.module()
        self.assertEqual(v.compare({'pages':1},[''],{'pages':1,'textPolicy':'scan'}),[])
        self.assertIn('unexpected_empty_text',v.compare({'pages':1},[''],{'pages':1,'textPolicy':'required'}))
    def test_changed_candidate_and_rule_invalidate_review(self):
        v=self.module()
        receipt={'protocol':'printcraft.verification/1','ruleVersion':1,'requestSha256':'x','artifacts':[],'status':'DETERMINISTIC_PASS_REVIEW_REQUIRED'}
        with self.assertRaises(ValueError):v.accept_review(receipt,{'ruleVersion':2,'requestSha256':'x','decision':'approve'})
        with self.assertRaises(ValueError):v.accept_review(receipt,{'ruleVersion':1,'requestSha256':'y','decision':'approve'})
if __name__=='__main__':unittest.main()

class HandoffAndReview(unittest.TestCase):
    def module(self):return PDFVerification().module()
    def test_handoff_wrong_producer_version_and_hash(self):
        v=self.module()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.pdf';p.write_bytes(b'%PDF-1.4\n%%EOF')
            data={'protocol':'artcraft.printcraft-handoff/1','producer':'artcraft','producerVersion':'1.0.0','files':[{'path':str(p),'sha256':v.sha(p)}]}
            self.assertEqual(v.validate_handoff(data)['status'],'HANDOFF_INTEGRITY_PASS')
            for field,value in [('protocol','future/99'),('producer','unrelated'),('producerVersion',None),('producerVersion','99.0.0')]:
                with self.assertRaises(ValueError):v.validate_handoff(dict(data,**{field:value}))
            data['files'][0]['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'hash_mismatch'):v.validate_handoff(data)
    def test_visual_review_rechecks_content_and_proposes_only_one_revision(self):
        v=self.module()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.pdf';p.write_bytes(b'%PDF-1.4\n%%EOF')
            receipt={'protocol':v.PROTOCOL,'status':'DETERMINISTIC_PASS_REVIEW_REQUIRED','ruleVersion':1,'requestSha256':'bound','artifacts':[{'path':str(p),'sha256':v.sha(p)}]}
            review={'ruleVersion':1,'requestSha256':'bound','reviewer':'fixture reviewer','notes':'page 1 crop','decision':'revise'}
            r=v.accept_review(receipt,review);self.assertEqual(r['status'],'REVISION_PROPOSED');self.assertFalse(r['automaticRevision'])
            p.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'candidate_changed'):v.accept_review(receipt,review)
