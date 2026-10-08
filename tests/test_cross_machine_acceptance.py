"""传输成员的边界回归；不作为实际跨机器运行证明。"""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('cross_machine', Path(__file__).with_name('cross_machine_acceptance.py'))
cross_machine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cross_machine)


class CrossMachineTests(unittest.TestCase):
    def test_safe_member_paths_preserve_unicode_and_spaces(self):
        self.assertEqual(str(cross_machine.member_path('移动 文件/project.json')), '移动 文件/project.json')

    def test_nonportable_or_escaping_member_is_refused(self):
        for name in ['../escape', '/absolute', 'a/../escape', 'a//b', 'a/./b', 'C:/escape', 'a\\b', '', 'a\x00b']:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'member_path_invalid'):
                cross_machine.member_path(name)

    def archive(self, root, payload=b'fixture', digest=None, extra=None):
        path = root / 'transport.zip'
        manifest = {'protocol': 'printcraft.cross-machine-transfer/1', 'files': {'input.pdf': {'bytes': len(payload), 'sha256': digest or hashlib.sha256(payload).hexdigest()}}}
        with zipfile.ZipFile(path, 'w') as zipped:
            zipped.writestr('transfer.json', json.dumps(manifest))
            zipped.writestr('input.pdf', payload)
            if extra:
                zipped.writestr(extra, b'unlisted')
        return path

    def test_transport_digest_checked_before_any_destination_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = self.archive(root)
            with self.assertRaisesRegex(ValueError, 'transport_digest_mismatch'):
                cross_machine.unpack(archive, root / 'received', '0' * 64)
            self.assertFalse((root / 'received').exists())

    def test_corrupt_member_rejected_before_any_destination_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = self.archive(root, digest='0' * 64)
            with self.assertRaisesRegex(ValueError, 'transport_member_digest_mismatch'):
                cross_machine.unpack(archive, root / 'received', cross_machine.sha(archive))
            self.assertFalse((root / 'received').exists())

    def test_unlisted_transport_file_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = self.archive(root, extra='extra.txt')
            with self.assertRaisesRegex(ValueError, 'transport_manifest_invalid'):
                cross_machine.unpack(archive, root / 'received', cross_machine.sha(archive))
            self.assertFalse((root / 'received').exists())

    def test_exact_transfer_preserves_bytes_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = self.archive(root)
            cross_machine.unpack(archive, root / 'received', cross_machine.sha(archive))
            self.assertEqual((root / 'received/input.pdf').read_bytes(), b'fixture')
            (root / 'received/input.pdf').write_bytes(b'user')
            with self.assertRaises(FileExistsError):
                cross_machine.unpack(archive, root / 'received', cross_machine.sha(archive))
            self.assertEqual((root / 'received/input.pdf').read_bytes(), b'user')


if __name__ == '__main__':
    unittest.main()
