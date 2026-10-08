"""作者平台验收的制品信任与内容断言回归；不作为原生平台证明。"""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('platform_acceptance', Path(__file__).with_name('platform_acceptance.py'))
platform_acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(platform_acceptance)


class PlatformAcceptanceTests(unittest.TestCase):
    def test_archive_and_member_digests_are_both_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / 'fixture.zip'
            with zipfile.ZipFile(archive, 'w') as zipped:
                zipped.writestr('bundle/printcraft-cli', b'fixture')
            entry = {'archiveSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                     'member': 'bundle/printcraft-cli', 'binarySha256': '0' * 64}
            with self.assertRaisesRegex(ValueError, 'binary_digest'):
                platform_acceptance.extract_binary(archive, root / 'binary', entry)
            self.assertFalse((root / 'binary').exists())
            entry['binarySha256'] = hashlib.sha256(b'fixture').hexdigest()
            entry['archiveSha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'archive_digest'):
                platform_acceptance.extract_binary(archive, root / 'binary', entry)

    def test_only_exact_regular_member_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / 'fixture.tar.gz'
            with tarfile.open(archive, 'w:gz') as packed:
                bad = tarfile.TarInfo('../../escape')
                bad.size = 3
                packed.addfile(bad, io.BytesIO(b'bad'))
                good = tarfile.TarInfo('bundle/printcraft-cli')
                good.size = 7
                packed.addfile(good, io.BytesIO(b'fixture'))
            entry = {'archiveSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                     'member': good.name, 'binarySha256': hashlib.sha256(b'fixture').hexdigest()}
            platform_acceptance.extract_binary(archive, root / 'binary', entry)
            self.assertEqual((root / 'binary').read_bytes(), b'fixture')
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['binary', 'fixture.tar.gz'])

    def test_tar_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / 'fixture.tar.gz'
            with tarfile.open(archive, 'w:gz') as packed:
                link = tarfile.TarInfo('cli')
                link.type = tarfile.SYMTYPE
                link.linkname = '/bin/sh'
                packed.addfile(link)
            entry = {'archiveSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                     'member': 'cli', 'binarySha256': '0' * 64}
            with self.assertRaisesRegex(ValueError, 'member_not_regular'):
                platform_acceptance.extract_binary(archive, root / 'binary', entry)

    def test_matching_page_count_cannot_hide_wrong_order_or_empty_text(self):
        for text in [['PAGE-ALPHA', 'PAGE-BETA', 'PAGE-GAMMA'], ['PAGE-GAMMA', '', 'PAGE-BETA']]:
            with self.assertRaises(AssertionError):
                platform_acceptance.assert_pages({'pages': 3}, text, ['PAGE-GAMMA', 'PAGE-ALPHA', 'PAGE-BETA'])
        platform_acceptance.assert_pages({'pages': 3}, ['PAGE-GAMMA', 'PAGE-ALPHA', 'PAGE-BETA'], ['PAGE-GAMMA', 'PAGE-ALPHA', 'PAGE-BETA'])


if __name__ == '__main__':
    unittest.main()
