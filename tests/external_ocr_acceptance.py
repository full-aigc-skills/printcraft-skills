"""真实简繁中文扫描验收；不属于基础单元测试，不下载或安装外部后端。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'chi_sim': {'lines': ['中文扫描识别测试', '合同金额一千元', '打印交付验收', '中文扫描交付', '打印任务完成', '中文识别验收'],
                'nativeTargets': ['打印交付验收', '打印任务完成']},
    'chi_tra': {'lines': ['繁體中文掃描測試', '文件交付驗收', '合同金額一千元', '繁體掃描交付', '列印文件完成', '中文辨識驗收'],
                'nativeTargets': ['文件交付驗收', '列印文件完成']},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-home', type=Path, required=True)
    parser.add_argument('--tesseract', type=Path, required=True)
    parser.add_argument('--tessdata-dir', type=Path, required=True)
    parser.add_argument('--workdir', type=Path, required=True)
    parser.add_argument('--scripts', type=Path, default=ROOT / 'skills/printcraft-use/scripts')
    args = parser.parse_args(); work = args.workdir.resolve(); work.mkdir(mode=0o700)
    scripts = args.scripts.resolve()
    report = dict(protocol='printcraft.external-ocr-acceptance/1', cases={}, scope='macOS arm64 explicit external backend, original CC0 two-page scans only',
                  nativeChineseSupport=False, arbitraryOcrAccuracy='NOT_CLAIMED', mobile='NOT_RUN', visualReview='NOT_RUN',
                  sourceSha256={str(p.relative_to(scripts)): digest(p) for p in scripts.iterdir() if p.is_file() and p.suffix in ('.py', '.json')},
                  acceptanceScriptSha256=digest(Path(__file__)))
    cli = [sys.executable, '-I', '-B', str(scripts / 'cli.py'), '--runtime-home', str(args.runtime_home), '--']
    for language, expected in EXPECTED.items():
        source = ROOT / 'tests/fixtures/chinese' / (language + '.pdf'); before = digest(source)
        try:
            for page in (1, 2):
                result = subprocess.run(cli + ['text', str(source), '--page', str(page)], capture_output=True, text=True, check=True, timeout=60)
                assert not result.stdout.strip(), 'input already has text'
            lock_cmd = [sys.executable, '-I', '-B', str(scripts / 'ocr.py'), 'diagnose', '--backend', 'tesseract', '--language', language,
                        '--tesseract', str(args.tesseract), '--tessdata-dir', str(args.tessdata_dir)]
            diagnosis = subprocess.run(lock_cmd, capture_output=True, text=True, check=True, timeout=30)
            lock = work / (language + '-backend.json'); lock.write_text(diagnosis.stdout); lock.chmod(0o600)
            command = [sys.executable, '-I', '-B', str(scripts / 'ocr.py'), 'run', '--backend', 'tesseract', '--language', language,
                       '--backend-lock', str(lock), '--input', str(source), '--output-dir', str(work / language),
                       '--runtime-home', str(args.runtime_home), '--rasterize']
            run = subprocess.run(command, capture_output=True, text=True, timeout=300)
            (work / (language + '-stdout.json')).write_text(run.stdout)
            summary = json.loads(run.stdout)
            receipt = json.loads(Path(summary['receiptPath']).read_text())
            assert run.returncode == 0, receipt.get('error', receipt.get('status'))
            assert receipt['status'] == 'DETERMINISTIC_PASS_REVIEW_REQUIRED'
            assert receipt['pages'] == 2 and receipt['pixelEquality'] and receipt['preserved'] and receipt['newProcessReopen']
            extracted = [''.join(text.split()) for text in receipt['pageText']]
            for target, text in zip(expected['nativeTargets'], extracted):
                assert target in text, (target, text)
            recognized = (work / language / 'searchable.txt').read_text()
            for line in expected['lines']:
                assert line in ''.join(recognized.split()), (line, recognized)
            assert digest(source) == before
            report['cases'][language] = dict(status='PASS', argv=command, diagnosisArgv=lock_cmd,
                inputSha256=before, inputTextEmpty=True, expected=expected, extracted=extracted,
                recognizedText=recognized, outputSha256=digest(work / language / 'searchable.pdf'),
                receiptSha256=digest(work / language / 'receipt.json'), backend=json.loads(diagnosis.stdout),
                readingOrderLimitation='Native text contains spacing/order differences; scoped targets and backend text checked separately')
        except Exception as error:
            report['cases'][language] = dict(status='FAILED', error=str(error), inputSha256=before, inputUnchanged=digest(source) == before)
    report['status'] = 'PASS' if all(case['status'] == 'PASS' for case in report['cases'].values()) else 'FAILED'
    (work / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
