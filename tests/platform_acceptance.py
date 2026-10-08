"""作者专用固定制品平台验收；直接原生执行，不宣称技能包装器支持该平台。"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_binary(archive, output, entry):
    """校验归档与精确普通文件成员；不展开其他路径、链接或附带程序。"""
    if sha256(archive) != entry['archiveSha256']:
        raise ValueError('archive_digest_mismatch')
    if str(archive).endswith('.zip'):
        with zipfile.ZipFile(archive) as packed:
            matches = [item for item in packed.infolist() if item.filename == entry['member']]
            if len(matches) != 1 or matches[0].is_dir() or stat.S_ISLNK(matches[0].external_attr >> 16):
                raise ValueError('member_not_regular_or_unique')
            data = packed.read(matches[0])
    else:
        with tarfile.open(archive, 'r:gz') as packed:
            matches = [item for item in packed.getmembers() if item.name == entry['member']]
            if len(matches) != 1 or not matches[0].isfile():
                raise ValueError('member_not_regular_or_unique')
            data = packed.extractfile(matches[0]).read()
    if hashlib.sha256(data).hexdigest() != entry['binarySha256']:
        raise ValueError('binary_digest_mismatch')
    with Path(output).open('xb') as target:
        target.write(data)
    Path(output).chmod(0o700)


def assert_pages(info, observed, expected):
    assert info['pages'] == len(expected), (info, expected)
    assert len(observed) == len(expected), observed
    assert all(label in text for label, text in zip(expected, observed)), observed


def sequence(text):
    decoder = json.JSONDecoder()
    values = []
    while text.strip():
        value, end = decoder.raw_decode(text.lstrip())
        values.append(value)
        text = text.lstrip()[end:]
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', required=True)
    parser.add_argument('--workdir', required=True, type=Path)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    lock_path = ROOT / 'tests/platform-artifacts.json'
    lock = json.loads(lock_path.read_text())
    entry = lock['platforms'][args.platform]
    work = args.workdir.resolve()
    work.mkdir(parents=True, mode=0o700)
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    report = {'contract': 'printcraft.native-platform-evidence/1', 'platform': args.platform,
              'sourceCommit': source_commit, 'startedAt': datetime.now(timezone.utc).isoformat(),
              'sourceFiles': {str(p.relative_to(ROOT)): sha256(p) for p in [Path(__file__), lock_path, ROOT / 'tests/fixtures/make_pdf.py']},
              'host': {'system': platform.system(), 'machine': platform.machine(), 'release': platform.release(), 'python': platform.python_version()},
              'workflow': {'runId': os.environ.get('GITHUB_RUN_ID'), 'runAttempt': os.environ.get('GITHUB_RUN_ATTEMPT')},
              'runtime': entry, 'results': {}, 'scope': 'DIRECT_NATIVE_ONLY_SKILL_INSTALLER_NOT_TESTED',
              'chineseRecognition': 'NOT_SUPPORTED_BY_PINNED_NATIVE', 'visualReview': 'NOT_RUN', 'status': 'FAILED'}
    counter = 0
    try:
        aliases = {'amd64': 'x86_64', 'aarch64': 'arm64'}
        machine = aliases.get(platform.machine().lower(), platform.machine().lower())
        assert platform.system().lower() == entry['system'] and machine == entry['machine'], report['host']
        archive = args.archive
        if archive is None:
            archive = work / entry['asset']
            urllib.request.urlretrieve(entry['url'], archive)
        binary = work / ('printcraft-cli.exe' if entry['system'] == 'windows' else 'printcraft-cli')
        extract_binary(archive, binary, entry)
        report['runtimeArchiveSha256'] = sha256(archive)
        report['runtimeBinarySha256'] = sha256(binary)

        def call(*native_args, expected_code=0):
            nonlocal counter
            counter += 1
            result = subprocess.run([str(binary), *map(str, native_args)], capture_output=True, timeout=180)
            (work / f'{counter:03}-stdout.log').write_bytes(result.stdout)
            (work / f'{counter:03}-stderr.log').write_bytes(result.stderr)
            (work / f'{counter:03}-call.json').write_text(json.dumps({'argv': native_args, 'returncode': result.returncode}, default=str))
            assert result.returncode == expected_code, {'argv': native_args, 'returncode': result.returncode,
                                                       'stderr': result.stderr.decode('utf-8', 'replace')}
            return result.stdout.decode('utf-8')

        version = call('--version')
        assert version.splitlines()[0] == 'printcraft-cli 0.2.1', version
        report['versionOutput'] = version
        catalog_text = call('tools')
        catalog = json.loads(catalog_text)
        (work / 'tools.json').write_text(catalog_text, encoding='utf-8')
        report['catalogSha256'] = sha256(work / 'tools.json')
        report['catalogToolCount'] = len(catalog)
        assert len(catalog) == 123, len(catalog)
        spec = importlib.util.spec_from_file_location('fixture', ROOT / 'tests/fixtures/make_pdf.py')
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        source = work / 'source.pdf'
        fixture.make_pdf(source)
        before = sha256(source)
        report['inputSha256'] = before

        def run(name, operations, input_pdf=source):
            plan = work / (name + '.json')
            plan.write_text(json.dumps([{'tool': 'doc_open', 'args': {'path': str(input_pdf)}}, *operations]), encoding='utf-8')
            return sequence(call('run', '--script', plan))

        def tool(tool_name, **params):
            return {'tool': tool_name, 'args': {'doc': 1, **params}}

        def record(name, fn):
            try:
                report['results'][name] = {'status': 'PASS', 'details': fn()}
            except Exception as error:
                report['results'][name] = {'status': 'FAILED', 'error': str(error)}

        def page_case(name, operations, labels, geometry=None):
            output = work / (name + '.pdf')
            run(name, [*operations, tool('doc_save', path=str(output))])
            info = json.loads(call('info', output))
            texts = [call('text', output, '--page', i + 1).strip() for i in range(info['pages'])]
            assert_pages(info, texts, labels)
            if geometry is not None:
                assert info['first_page_pt'] == geometry, info
            call('render', output, '--page', 1, '--out', work / (name + '.pam'))
            return {'outputSha256': sha256(output), 'info': info, 'texts': texts}

        record('reorder_save_reopen_render', lambda: page_case('reorder', [tool('page_move', pages=[3], to=1)], ['PAGE-GAMMA', 'PAGE-ALPHA', 'PAGE-BETA']))
        record('rotate_save_reopen_render', lambda: page_case('rotate', [tool('page_rotate', pages=[1], degrees=90)], ['PAGE-ALPHA', 'PAGE-BETA', 'PAGE-GAMMA'], [792.0, 612.0]))
        record('crop_save_reopen_render', lambda: page_case('crop', [tool('page_set_box', pages=[1], margins=[10, 10, 10, 10])], ['PAGE-ALPHA', 'PAGE-BETA', 'PAGE-GAMMA'], [592.0, 772.0]))

        def form():
            output = work / 'form.pdf'
            run('form', [tool('form_add_field', page=1, type='text', name='sample', rect=[72, 120, 200, 150]), tool('form_fill', values={'sample': 'verified form'}), tool('doc_save', path=str(output))])
            fields = run('form-reopen', [tool('form_fields')], output)[-1]
            assert 'verified form' in json.dumps(fields), fields
            return {'fields': fields, 'outputSha256': sha256(output)}
        record('form_save_reopen', form)

        def redact():
            output = work / 'redacted.pdf'
            run('redact', [tool('redact_mark', find='PAGE-ALPHA'), tool('redact_apply'), tool('doc_save', path=str(output), full=True)])
            text = call('text', output)
            assert 'PAGE-ALPHA' not in text and 'PAGE-BETA' in text and 'PAGE-GAMMA' in text, text
            assert b'PAGE-ALPHA' not in output.read_bytes()
            call('render', output, '--page', 1, '--out', work / 'redacted.pam')
            return {'outputSha256': sha256(output), 'textAndObjectBytesAbsent': True, 'visualReview': 'NOT_RUN'}
        record('redact_text_objects_render', redact)
        report['ocrStatus'] = run('ocr-status', [{'tool': 'ocr_status', 'args': {}}])[-1]
        report['sourceUnchanged'] = sha256(source) == before
        assert report['sourceUnchanged'], 'original_input_changed'
        assert all(result['status'] == 'PASS' for result in report['results'].values())
        report['status'] = 'PASS_SCOPED_NATIVE'
    except Exception as error:
        report['error'] = str(error)
    finally:
        report['artifacts'] = {str(p.relative_to(work)): sha256(p) for p in sorted(work.rglob('*')) if p.is_file() and p.name not in {'native-platform-report.json', 'printcraft-cli', 'printcraft-cli.exe'} and p.suffix not in {'.zip', '.gz'}}
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        (work / 'native-platform-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report['status'] != 'PASS_SCOPED_NATIVE')


if __name__ == '__main__':
    raise SystemExit(main())
