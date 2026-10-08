"""显式外部 OCR 的身份、材料保护与失败边界；不作为真实识别证据。"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import struct
import zlib
import io
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/printcraft-use/scripts'


def load():
    spec = importlib.util.spec_from_file_location('external_ocr', SCRIPTS / 'ocr.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExternalOcr(unittest.TestCase):
    def test_cli_summary_omits_large_catalog_but_points_to_private_receipt(self):
        ocr = load()
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / 'lock.json'; lock.write_text('{}')
            receipt = dict(protocol='printcraft.ocr/1', status='DETERMINISTIC_PASS_REVIEW_REQUIRED', receiptPath='/task/receipt.json',
                           stages=[{'stdout': 'large native catalog'}], visualReview='NOT_RUN')
            argv = ['ocr.py', 'run', '--backend', 'tesseract', '--language', 'chi_sim', '--backend-lock', str(lock),
                    '--input', '/input.pdf', '--output-dir', '/task', '--rasterize']
            stream = io.StringIO()
            with patch.object(sys, 'argv', argv), patch.object(ocr, 'run_ocr', return_value=receipt), redirect_stdout(stream):
                self.assertEqual(ocr.main(), 0)
            result = json.loads(stream.getvalue())
            self.assertEqual(result['receiptPath'], '/task/receipt.json')
            self.assertNotIn('stages', result)

    def test_png_transport_is_lossless_rgb(self):
        pixels = bytes([1, 2, 3, 4, 5, 6])
        data = load().ppm_to_png(b'P6\n2 1\n255\n' + pixels)
        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
        offset = 8; chunks = {}
        while offset < len(data):
            size = struct.unpack('>I', data[offset:offset + 4])[0]
            name = data[offset + 4:offset + 8]; value = data[offset + 8:offset + 8 + size]
            self.assertEqual(struct.unpack('>I', data[offset + 8 + size:offset + 12 + size])[0], zlib.crc32(name + value) & 0xffffffff)
            chunks[name] = value; offset += 12 + size
        self.assertEqual(struct.unpack('>IIBBBBB', chunks[b'IHDR']), (2, 1, 8, 2, 0, 0, 0))
        self.assertEqual(zlib.decompress(chunks[b'IDAT']), b'\x00' + pixels)

    def test_output_parent_alias_is_canonical_for_leptonica(self):
        ocr = load()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); real = root / '真实 目录'; real.mkdir()
            alias = root / 'alias'; alias.symlink_to(real, target_is_directory=True)
            self.assertEqual(ocr.new_output(alias / '新任务'), real / '新任务')
            self.assertFalse((real / '新任务').exists())
            with self.assertRaisesRegex(ValueError, 'newline'):
                ocr.new_output(real / 'bad\nname')

    def test_backend_is_explicit_before_any_write(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'ocr.py'), 'run'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--backend', result.stderr)

    def test_pam_preserves_pixels_and_rejects_transparency(self):
        ocr = load()
        header = b'P7\nWIDTH 2\nHEIGHT 1\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n'
        self.assertEqual(ocr.pam_to_ppm(header + bytes([1, 2, 3, 255, 4, 5, 6, 255])), b'P6\n2 1\n255\n' + bytes([1, 2, 3, 4, 5, 6]))
        with self.assertRaisesRegex(ValueError, 'transparent'):
            ocr.pam_to_ppm(header + bytes([1, 2, 3, 0, 4, 5, 6, 255]))
        for bad in (header + b'bad', header.replace(b'WIDTH 2', b'WIDTH 0'), header.replace(b'DEPTH 4', b'DEPTH 9')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ocr.pam_to_ppm(bad)

    def test_identity_diagnosis_is_readonly_and_hash_bound(self):
        ocr = load()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); exe = root / 'engine'; exe.write_bytes(b'engine')
            (root / 'chi_sim.traineddata').write_bytes(b'model'); (root / 'pdf.ttf').write_bytes(b'font')
            before = sorted(root.rglob('*'))
            with patch.object(ocr.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'tesseract 5.5.3\n', '')):
                identity = ocr.identity(exe, root, 'chi_sim')
            self.assertEqual(before, sorted(root.rglob('*')))
            self.assertEqual(identity['protocol'], 'printcraft.ocr-backend/1')
            self.assertEqual(identity['modelSha256'], ocr.sha(root / 'chi_sim.traineddata'))
            self.assertEqual(identity['binarySha256'], ocr.sha(exe))
            self.assertEqual(identity['pdfFontSha256'], ocr.sha(root / 'pdf.ttf'))
            self.assertEqual(identity['language'], 'chi_sim')

    def test_identity_mismatch_and_unknown_fields_rejected(self):
        ocr = load()
        identity = {'protocol': 'printcraft.ocr-backend/1', 'backend': 'tesseract', 'executable': '/engine', 'tessdataDir': '/models', 'version': 'tesseract 5.5.3', 'platform': 'darwin-arm64', 'language': 'chi_sim', 'binarySha256': '1' * 64, 'modelSha256': '2' * 64, 'pdfFontSha256': '3' * 64}
        ocr.validate_lock(identity, identity)
        for key in ('binarySha256', 'modelSha256', 'pdfFontSha256', 'version', 'platform', 'language'):
            changed = dict(identity); changed[key] = 'changed'
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'identity'):
                ocr.validate_lock(identity, changed)
        with self.assertRaises(ValueError):
            ocr.validate_lock(dict(identity, unknown=True), identity)

    def test_requires_rasterize_and_existing_directory_is_preserved(self):
        ocr = load()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / '原件.pdf'; source.write_bytes(b'%PDF-1.4\noriginal')
            output = root / '任务'; output.mkdir(); (output / 'keep').write_text('user')
            with self.assertRaisesRegex(ValueError, 'rasterize'):
                ocr.run_ocr({}, source, root / 'new', root / 'runtime', 'chi_sim', 150, 60, False)
            with self.assertRaisesRegex(ValueError, 'output'):
                ocr.run_ocr({}, source, output, root / 'runtime', 'chi_sim', 150, 60, True)
            self.assertEqual((output / 'keep').read_text(), 'user')
            self.assertFalse((root / 'new').exists())
            self.assertFalse((root / 'runtime').exists())
            self.assertEqual(source.read_bytes(), b'%PDF-1.4\noriginal')

    def test_deadline_and_failed_child_do_not_replay(self):
        ocr = load()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            calls = []
            execution = type('Execution', (), {'execute': staticmethod(lambda *args, **kwargs: calls.append(args) or {'status': 'UNKNOWN', 'wrapperExitCode': 1, 'phase': 'native-timeout', 'automaticReplay': False})})
            receipt = {'status': 'UNKNOWN', 'stages': []}
            with self.assertRaises(ocr.ChildFailure):
                ocr.call_child(execution, ['engine'], 1, path, receipt, 'recognize')
            self.assertEqual(len(calls), 1)
            self.assertEqual(receipt['status'], 'UNKNOWN')
            self.assertEqual(receipt['stages'][0]['phase'], 'native-timeout')
            with self.assertRaises(ocr.ChildFailure):
                ocr.call_child(execution, ['engine'], -1, path, receipt, 'reopen')
            self.assertEqual(len(calls), 1)

    def test_missing_backend_identity_rejects_without_task_creation(self):
        ocr = load()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source.pdf'; source.write_bytes(b'%PDF-1.4\n')
            with self.assertRaises((ValueError, KeyError, OSError)):
                ocr.run_ocr({}, source, root / 'task', root / 'runtime', 'chi_sim', 150, 60, True)
            self.assertFalse((root / 'task').exists())


if __name__ == '__main__':
    unittest.main()
