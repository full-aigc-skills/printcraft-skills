"""旧 PrintCraft 与新版 PdfCraft 的固定制品身份；原生版本进程全部模拟。"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class RuntimeNames(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'skills/printcraft-use/scripts/bootstrap.py'
        spec = importlib.util.spec_from_file_location('print_bootstrap', path)
        self.bootstrap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bootstrap)

    def fixture(self, root, artifact, version='0.3.0'):
        archive = root / (artifact + '.zip')
        content = b'synthetic test executable; never executed'
        with zipfile.ZipFile(archive, 'w') as package:
            package.writestr(artifact, content)
            package.writestr('LICENSE-MIT', 'Synthetic fixture license')
        expected = {
            'url': f'https://github.com/storytold/pdfcraft/releases/download/v{version}/{artifact}-{version}-macos-universal.zip',
            'archiveSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'binarySha256': hashlib.sha256(content).hexdigest(),
            'versionOutput': f'{artifact} {version}',
        }
        return {'artifact': artifact, 'resolvedVersion': version, 'artifacts': {'darwin-arm64': expected}}, archive

    def test_both_binary_names_install_and_reuse_without_crossing_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for artifact in ('printcraft-cli', 'pdfcraft-cli'):
                with self.subTest(artifact=artifact):
                    lock, archive = self.fixture(root, artifact)
                    version = subprocess.CompletedProcess([], 0, f'{artifact} 0.3.0\nextra metadata\n', '')
                    with patch.object(self.bootstrap.subprocess, 'run', return_value=version) as probe:
                        installed = self.bootstrap.install(lock, root/'runtime', archive, 'darwin-arm64')
                        reused = self.bootstrap.install(lock, root/'runtime', archive, 'darwin-arm64')
                    self.assertEqual(probe.call_count, 1)
                    self.assertTrue(reused['reused'])
                    self.assertEqual(Path(installed['executable']).parts[-3:], (artifact.removesuffix('-cli'), '0.3.0', artifact))
                    receipt = json.loads(Path(installed['executable']).with_name('installation.json').read_text())
                    self.assertEqual(receipt['rawVersionOutput'], f'{artifact} 0.3.0\nextra metadata')

    def test_release_tag_must_match_locked_version_before_runtime_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock, archive = self.fixture(root, 'printcraft-cli')
            lock['artifacts']['darwin-arm64']['url'] = lock['artifacts']['darwin-arm64']['url'].replace('/v0.3.0/', '/v0.2.1/')
            with patch.object(self.bootstrap.subprocess, 'run', side_effect=AssertionError('native probe must not start')):
                with self.assertRaisesRegex(ValueError, 'runtime_release_identity_mismatch'):
                    self.bootstrap.install(lock, root/'runtime', archive, 'darwin-arm64')
            self.assertFalse((root/'runtime').exists())

    def test_asset_name_must_match_binary_identity_before_runtime_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock, archive = self.fixture(root, 'printcraft-cli')
            lock['artifacts']['darwin-arm64']['url'] = lock['artifacts']['darwin-arm64']['url'].replace('/printcraft-cli-', '/photocraft-cli-')
            with patch.object(self.bootstrap.subprocess, 'run', side_effect=AssertionError('native probe must not start')):
                with self.assertRaisesRegex(ValueError, 'runtime_release_identity_mismatch'):
                    self.bootstrap.install(lock, root/'runtime', archive, 'darwin-arm64')
            self.assertFalse((root/'runtime').exists())

    def test_new_binary_refuses_legacy_version_output_and_preserves_old_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root/'runtime/printcraft/0.2.1/user-note'
            old.parent.mkdir(parents=True)
            old.write_text('preserve')
            lock, archive = self.fixture(root, 'pdfcraft-cli')
            version = subprocess.CompletedProcess([], 0, 'printcraft-cli 0.3.0\n', '')
            with patch.object(self.bootstrap.subprocess, 'run', return_value=version):
                with self.assertRaisesRegex(ValueError, 'runtime_version_mismatch'):
                    self.bootstrap.install(lock, root/'runtime', archive, 'darwin-arm64')
            self.assertEqual(old.read_text(), 'preserve')
            self.assertFalse((root/'runtime/pdfcraft/0.3.0').exists())


if __name__ == '__main__':
    unittest.main()

class InstallationBoundaries(unittest.TestCase):
    setUp=RuntimeNames.setUp
    fixture=RuntimeNames.fixture
    def test_corrupt_install_is_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);lock,archive=self.fixture(root,'printcraft-cli')
            with patch.object(self.bootstrap.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'printcraft-cli 0.3.0','')):
                installed=self.bootstrap.install(lock,root/'runtime',archive,'darwin-arm64')
            binary=Path(installed['executable']);binary.write_bytes(b'corrupted user change')
            with self.assertRaisesRegex(ValueError,'checksum_mismatch'):self.bootstrap.install(lock,root/'runtime',archive,'darwin-arm64')
            self.assertEqual(binary.read_bytes(),b'corrupted user change')
    def test_unsupported_platform_does_not_create_runtime(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);lock,archive=self.fixture(root,'printcraft-cli')
            with self.assertRaisesRegex(ValueError,'unsupported_platform'):self.bootstrap.install(lock,root/'runtime',archive,'linux-x86_64')
            self.assertFalse((root/'runtime').exists())
    def test_concurrent_install_uses_one_verified_directory(self):
        import sys,shutil
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);script=root/'bootstrap.py';shutil.copyfile(ROOT/'skills/printcraft-use/scripts/bootstrap.py',script)
            artifact='printcraft-cli';content=b'#!/bin/sh\nprintf "printcraft-cli 0.3.0\\n"\n';archive=root/'runtime.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr(artifact,content);z.writestr('LICENSE-MIT','Synthetic test fixture')
            lock={'artifact':artifact,'resolvedVersion':'0.3.0','artifacts':{'darwin-arm64':{'url':'https://github.com/storytold/pdfcraft/releases/download/v0.3.0/printcraft-cli-0.3.0-macos-universal.zip','archiveSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'binarySha256':hashlib.sha256(content).hexdigest(),'versionOutput':'printcraft-cli 0.3.0'}}}
            (root/'runtime.lock.json').write_text(json.dumps(lock));argv=[sys.executable,str(script),'--runtime-home',str(root/'runtime'),'--archive',str(archive)]
            processes=[subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
            results=[]
            for process in processes:
                out,err=process.communicate(timeout=10);self.assertEqual(process.returncode,0,err+out);results.append(json.loads(out))
            self.assertEqual(sorted(r['reused'] for r in results),[False,True])
