"""作者专用真实跨机器交付验收；直接固定原生执行，不替代手机/平板验收。"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'docs/verification/cross-plugin-public-artifacts'


def member_path(name):
    """只接受可移植普通文件的相对路径，拒绝平台分隔符和逃逸。"""
    if not isinstance(name, str) or not name or any(char in name for char in ['\\', ':', '\x00']) or name.startswith('/') or any(part in {'', '.', '..'} for part in name.split('/')):
        raise ValueError('member_path_invalid')
    return PurePosixPath(name)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity():
    return {'system': platform.system(), 'machine': platform.machine(), 'release': platform.release(),
            'python': platform.python_version(), 'runnerName': os.environ.get('RUNNER_NAME'),
            'workflowRunId': os.environ.get('GITHUB_RUN_ID'), 'workflowJob': os.environ.get('GITHUB_JOB'),
            'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}


def unpack(archive, destination, expected):
    """先校验 ZIP 身份和全部成员，再创建目的目录，避免部分不可信展开。"""
    if sha(archive) != expected:
        raise ValueError('transport_digest_mismatch')
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or len(names) > 1000 or sum(entry.file_size for entry in entries) > 32 * 1024 * 1024:
            raise ValueError('transport_inventory_invalid')
        for entry in entries:
            member_path(entry.filename)
            if entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('transport_member_not_regular')
        manifest = json.loads(zipped.read('transfer.json'))
        if manifest.get('protocol') != 'printcraft.cross-machine-transfer/1' or set(names) != set(manifest['files']) | {'transfer.json'}:
            raise ValueError('transport_manifest_invalid')
        for name, entry in manifest['files'].items():
            data = zipped.read(name)
            if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('transport_member_digest_mismatch')
        destination.mkdir(mode=0o700, parents=True)
        for name in names:
            target = destination.joinpath(*member_path(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output:
                output.write(zipped.read(name))
    return manifest


def pack(work):
    lock = json.loads((ROOT / 'tests/cross-machine-fixture.json').read_text())
    selected = {}
    for package in ['package-v1', 'package-v2']:
        assert sha(FIXTURES / package / 'project.json') == lock['projectSha256'][package]
        for path in sorted((FIXTURES / package).rglob('*')):
            if path.is_symlink():
                raise ValueError('fixture_symlink')
            if path.is_file():
                selected[str(path.relative_to(FIXTURES))] = path
    for name in ['revised.pdf', 'second.pdf', 'revised-1.pam', 'revised-2.pam', 'cross-plugin-report.json', 'producer-report.json']:
        selected[name] = FIXTURES / name
    assert sha(selected['revised.pdf']) == lock['deliverySha256']
    assert sha(selected['producer-report.json']) == lock['producerReportSha256']
    files = {name: {'sha256': sha(path), 'bytes': path.stat().st_size} for name, path in selected.items()}
    sender = identity()
    manifest = {'protocol': 'printcraft.cross-machine-transfer/1', 'sender': sender,
                'producer': 'artcraft', 'producerVersion': lock['producerVersion'], 'files': files,
                'sourceFiles': {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / 'tests/cross-machine-fixture.json']}}
    archive = work / 'transport.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr('transfer.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        for name, path in selected.items():
            member_path(name)
            zipped.write(path, name)
    assert all(sha(selected[name]) == entry['sha256'] for name, entry in files.items())
    digest = sha(archive)
    (work / 'transport.sha256').write_text(digest + '\n')
    report = {'status': 'PACKED_NOT_RECEIVED', 'sender': sender, 'transportSha256': digest,
              'files': files, 'inputUnchanged': True, 'mobileDevice': 'NOT_RUN'}
    (work / 'sender-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


def receive(args, work):
    lock_path = ROOT / 'tests/cross-machine-fixture.json'
    lock = json.loads(lock_path.read_text())
    report = {'status': 'FAILED', 'scope': 'CROSS_MACHINE_PACKAGE_AND_NATIVE_PDF_ONLY', 'receiver': identity(),
              'mobileDevice': 'NOT_RUN', 'visualReview': 'NOT_RUN', 'producerReexecution': 'NOT_RUN',
              'skillInstaller': 'NOT_RUN_DIRECT_NATIVE_ONLY',
              'sourceFiles': {relative: sha(ROOT / relative) for relative in ['tests/cross_machine_acceptance.py', 'tests/cross-machine-fixture.json', 'tests/platform_acceptance.py', 'tests/platform-artifacts.json', 'skills/printcraft-use/scripts/verification.py', 'skills/printcraft-use/scripts/commands.py']}}
    counter = 0

    def command(argv, cwd=None):
        nonlocal counter
        counter += 1
        result = subprocess.run(list(map(str, argv)), cwd=cwd, capture_output=True, timeout=240)
        (work / f'{counter:03}-stdout.log').write_bytes(result.stdout)
        (work / f'{counter:03}-stderr.log').write_bytes(result.stderr)
        (work / f'{counter:03}-call.json').write_text(json.dumps({'argv': argv, 'returncode': result.returncode}, default=str))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        return result.stdout.decode('utf-8')

    try:
        expected = (args.bundle / 'transport.sha256').read_text().strip()
        manifest = unpack(args.bundle / 'transport.zip', work / '接收 项目', expected)
        received = work / '接收 项目'
        report.update(sender=manifest['sender'], transportSha256=expected)
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            assert manifest['sender']['workflowJob'] == 'sender' and report['receiver']['workflowJob'] == 'receiver'
            assert manifest['sender']['workflowRunId'] == report['receiver']['workflowRunId']
            assert (manifest['sender']['system'], manifest['sender']['machine']) != (report['receiver']['system'], report['receiver']['machine']), 'same_os_cpu_pair_not_this_cross_machine_matrix'
        else:
            report['scope'] = 'LOCAL_PRECHECK_NOT_CROSS_MACHINE'
        assert manifest['producerVersion'] == lock['producerVersion']
        art_head = command(['git', 'rev-parse', 'HEAD'], args.artcraft_root).strip()
        assert art_head == lock['consumer']['commit'], art_head
        command(['git', 'diff', '--quiet', 'HEAD', '--', 'src', 'schemas', 'package.json'], args.artcraft_root)
        report['consumer'] = {'repository': lock['consumer']['repository'], 'commit': art_head,
                              'version': json.loads((args.artcraft_root / 'package.json').read_text())['version'],
                              'node': command([args.node, '--version']).strip(),
                              'verifyModuleSha256': sha(args.artcraft_root / 'src/artifacts/project_package.ts')}
        report['packageVerification'] = {}
        children = None
        for package, digest in lock['projectSha256'].items():
            observed = json.loads(command([args.node, args.artcraft_root / 'src/cli.ts', 'verify-package', '--package', received / package, '--sha', digest]))
            assert observed['sha256'] == digest
            report['packageVerification'][package] = {'sha256': digest, 'files': len(observed['files']), 'children': len(observed['children']), 'status': 'OFFICIAL_VERIFY_PACKAGE_PASS'}
            if package == 'package-v2':
                children = sorted(observed['children'], key=lambda child: child['nodeId'])
        assert children is not None
        paths = [Path(child['root']) / child['outputs'][0]['location'] for child in children]
        handoff = {'protocol': 'artcraft.printcraft-handoff/1', 'producer': 'artcraft', 'producerVersion': lock['producerVersion'],
                   'files': [{'path': str(path), 'sha256': sha(path)} for path in paths]}
        handoff_file = work / 'handoff.json'
        handoff_file.write_text(json.dumps(handoff))
        handoff_result = json.loads(command([sys.executable, '-I', '-B', ROOT / 'skills/printcraft-use/scripts/commands.py', 'handoff', handoff_file, '--producer-version', lock['producerVersion']]))
        assert handoff_result['status'] == 'HANDOFF_INTEGRITY_PASS'
        report['handoff'] = handoff_result
        platforms = json.loads((ROOT / 'tests/platform-artifacts.json').read_text())
        entry = platforms['platforms'][args.platform]
        aliases = {'amd64': 'x86_64', 'aarch64': 'arm64'}
        machine = aliases.get(platform.machine().lower(), platform.machine().lower())
        assert platform.system().lower() == entry['system'] and machine == entry['machine']
        archive = args.archive
        if archive is None:
            archive = work / entry['asset']
            urllib.request.urlretrieve(entry['url'], archive)
        binary = work / 'printcraft-cli'
        helper = load('platform_helper', ROOT / 'tests/platform_acceptance.py')
        helper.extract_binary(archive, binary, entry)
        report['runtime'] = dict(entry, versionOutput=command([binary, '--version']))
        assert report['runtime']['versionOutput'].splitlines()[0] == 'printcraft-cli 0.2.1'
        catalog = command([binary, 'tools'])
        (work / 'tools.json').write_text(catalog)
        report['catalogSha256'] = sha(work / 'tools.json')
        assert len(json.loads(catalog)) == 123
        delivery = received / 'revised.pdf'
        assert sha(delivery) == lock['deliverySha256']
        report['deliveredPdfInfo'] = json.loads(command([binary, 'info', delivery]))
        assert report['deliveredPdfInfo']['pages'] == 2 and report['deliveredPdfInfo']['first_page_pt'] == [120.0, 88.0]
        report['deliveredRenderSha256'] = []
        for page, expected_pixels in enumerate(lock['deliveryRenderSha256'], 1):
            image = work / f'delivered-{page}.pam'
            command([binary, 'render', delivery, '--page', page, '--out', image])
            assert sha(image) == expected_pixels, f'delivered_page_{page}_pixels_changed'
            report['deliveredRenderSha256'].append(sha(image))
        source = received / 'second.pdf'
        output = work / 'receiver-revised.pdf'
        plan = [{'tool': 'doc_open', 'args': {'path': str(source)}}, {'tool': 'page_set_box', 'args': {'doc': 1, 'pages': [1], 'margins': [4, 4, 4, 4]}}, {'tool': 'doc_save', 'args': {'doc': 1, 'path': str(output)}}]
        plan_file = work / 'receiver-plan.json'
        plan_file.write_text(json.dumps(plan))
        command([binary, 'run', '--script', plan_file])
        reopened = json.loads(command([binary, 'info', output]))
        assert reopened['pages'] == 2 and reopened['first_page_pt'] == [120.0, 88.0]
        for page, expected_pixels in enumerate(lock['deliveryRenderSha256'], 1):
            image = work / f'receiver-revised-{page}.pam'
            command([binary, 'render', output, '--page', page, '--out', image])
            assert sha(image) == expected_pixels, f'reworked_page_{page}_pixels_changed'
        report['selectiveRework'] = {'changedPages': [1], 'preservedPages': [2], 'outputSha256': sha(output), 'info': reopened, 'status': 'PASS_NATIVE_SAVE_REOPEN_RENDER'}
        report['allTransferredInputsUnchanged'] = all(sha(received / name) == entry['sha256'] for name, entry in manifest['files'].items())
        assert report['allTransferredInputsUnchanged']
        report['status'] = 'PASS_SCOPED_CROSS_MACHINE' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'PASS_LOCAL_PRECHECK'
    except Exception as error:
        report['error'] = str(error)
    report['artifacts'] = {str(p.relative_to(work)): sha(p) for p in sorted(work.glob('*')) if p.is_file() and p.name != 'printcraft-cli' and p.suffix in {'.json', '.log', '.pdf', '.pam'}}
    (work / 'receiver-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='mode', required=True)
    sender = sub.add_parser('pack')
    sender.add_argument('--workdir', required=True, type=Path)
    receiver = sub.add_parser('receive')
    receiver.add_argument('--workdir', required=True, type=Path)
    receiver.add_argument('--bundle', required=True, type=Path)
    receiver.add_argument('--artcraft-root', required=True, type=Path)
    receiver.add_argument('--platform', required=True)
    receiver.add_argument('--node', default='node')
    receiver.add_argument('--archive', type=Path)
    args = parser.parse_args()
    work = args.workdir.resolve()
    work.mkdir(parents=True, mode=0o700)
    if args.mode == 'pack':
        report = pack(work)
    else:
        args.artcraft_root = args.artcraft_root.resolve()
        report = receive(args, work)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report['status'] == 'FAILED')


if __name__ == '__main__':
    raise SystemExit(main())
