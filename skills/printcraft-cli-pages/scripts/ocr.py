#!/usr/bin/env python3
"""显式 Tesseract 中文 OCR；生成栅格化新副本，不安装、不回退、不自动重放。"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import struct
import sys
import time
import uuid
import zlib

PROTOCOL = 'printcraft.ocr/1'
BACKEND_PROTOCOL = 'printcraft.ocr-backend/1'
LANGUAGES = ('chi_sim', 'chi_tra')
IDENTITY_FIELDS = {'protocol', 'backend', 'executable', 'tessdataDir', 'version', 'platform', 'language', 'binarySha256', 'modelSha256', 'pdfFontSha256'}


def load(name):
    spec = importlib.util.spec_from_file_location('craft_ocr_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(executable, tessdata, language, timeout=20):
    """仅只读查版本及文件摘要，不创建目录或下载；明确解析已有安装链接。"""
    if language not in LANGUAGES:
        raise ValueError('unsupported_external_language')
    executable = Path(executable).expanduser().resolve(strict=True)
    tessdata = Path(tessdata).expanduser().resolve(strict=True)
    files = [executable, tessdata / (language + '.traineddata'), tessdata / 'pdf.ttf']
    if any(not path.is_file() for path in files):
        raise ValueError('backend_asset_missing')
    digests = [sha(path) for path in files]
    result = subprocess.run([str(executable), '--version'], capture_output=True, text=True, timeout=timeout, check=True)
    version = result.stdout.splitlines()[0].strip() if result.stdout else ''
    if not re.fullmatch(r'tesseract 5\.[0-9]+\.[0-9]+', version):
        raise ValueError('unsupported_tesseract_version')
    if digests != [sha(path) for path in files]:
        raise ValueError('backend_identity_changed_during_diagnosis')
    return dict(protocol=BACKEND_PROTOCOL, backend='tesseract', executable=str(executable), tessdataDir=str(tessdata), version=version,
                platform=platform.system().lower() + '-' + platform.machine().lower(), language=language,
                binarySha256=digests[0], modelSha256=digests[1], pdfFontSha256=digests[2])


def validate_lock(lock, observed):
    if (not isinstance(lock, dict) or set(lock) != IDENTITY_FIELDS or lock.get('protocol') != BACKEND_PROTOCOL
            or lock.get('backend') != 'tesseract' or lock.get('language') not in LANGUAGES
            or any(not isinstance(value, str) or not value for value in lock.values())
            or any(not re.fullmatch('[a-f0-9]{64}', lock[key]) for key in ('binarySha256', 'modelSha256', 'pdfFontSha256'))
            or lock != observed):
        raise ValueError('backend_identity_mismatch_or_invalid_lock')


def pam_to_ppm(data):
    """只转换 8-bit 不透明 RGB/RGBA PAM；不静默丢弃透明信息。"""
    header, separator, pixels = data.partition(b'ENDHDR\n')
    if not separator or not header.startswith(b'P7\n') or len(header) > 4096:
        raise ValueError('invalid_pam_header')
    fields = {}
    for line in header.splitlines()[1:]:
        if not line or line.startswith(b'#'):
            continue
        key, _, value = line.partition(b' ')
        if key in fields:
            raise ValueError('duplicate_pam_field')
        fields[key] = value.strip()
    try:
        width, height, depth, maxval = [int(fields[key]) for key in (b'WIDTH', b'HEIGHT', b'DEPTH', b'MAXVAL')]
    except (KeyError, ValueError) as error:
        raise ValueError('invalid_pam_dimensions') from error
    if (width <= 0 or height <= 0 or width * height > 40_000_000 or depth not in (3, 4) or maxval != 255
            or fields.get(b'TUPLTYPE') != (b'RGB' if depth == 3 else b'RGB_ALPHA') or len(pixels) != width * height * depth):
        raise ValueError('unsupported_pam_geometry_or_payload')
    if depth == 4:
        if any(alpha != 255 for alpha in pixels[3::4]):
            raise ValueError('transparent_pam_rejected')
        rgb = bytearray(width * height * 3)
        for channel in range(3):
            rgb[channel::3] = pixels[channel::4]
        pixels = bytes(rgb)
    return f'P6\n{width} {height}\n255\n'.encode() + pixels


class ChildFailure(Exception):
    """保留已观察的子进程状态，不把未知结果改写为安全失败。"""


def ppm_to_png(ppm):
    # Tesseract 对 PPM 默认使用有损 JPEG；PNG 保留完整 RGB 像素。
    magic, dimensions, maximum, pixels = ppm.split(b'\n', 3)
    width, height = map(int, dimensions.split())
    if magic != b'P6' or maximum != b'255' or width <= 0 or height <= 0 or len(pixels) != width * height * 3:
        raise ValueError('invalid_rgb_ppm')
    def chunk(name, value):
        return struct.pack('>I', len(value)) + name + value + struct.pack('>I', zlib.crc32(name + value) & 0xffffffff)
    rows = b''.join(b'\x00' + pixels[start:start + width * 3] for start in range(0, len(pixels), width * 3))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def call_child(execution, argv, remaining, directory, receipt, phase):
    receipt['phase'] = phase
    if remaining <= 0:
        receipt['status'] = 'UNKNOWN'
        receipt['error'] = 'task_deadline'
        raise ChildFailure('task_deadline')
    result = execution.execute(argv, remaining, directory / 'last-process.json')
    receipt['stages'].append(dict(result, stage=phase, argv=argv))
    if result['status'] != 'NATIVE_EXIT_ZERO_REVIEW_REQUIRED':
        receipt['status'] = result['status']
        raise ChildFailure(phase)
    return result.get('stdout', '')


def new_output(path):
    output = Path(path).expanduser().absolute()
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise ValueError('new_output_directory_with_existing_parent_required')
    # Leptonica 在 macOS 下无法读取 /tmp 别名，使用真实父目录但不接受已有输出链接。
    output = output.parent.resolve() / output.name
    if '\n' in str(output) or '\r' in str(output):
        raise ValueError('output_path_newline')
    return output


def run_ocr(lock, source, output, runtime_home, language, dpi, timeout, rasterize):
    if not rasterize:
        raise ValueError('explicit_rasterize_required')
    output = new_output(output)
    if language not in LANGUAGES or type(dpi) is not int or not 150 <= dpi <= 300 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('invalid_ocr_policy')
    deadline = time.monotonic() + timeout
    source = Path(source).expanduser().absolute()
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('invalid_input_pdf')
    with source.open('rb') as stream:
        if not stream.read(8).startswith(b'%PDF-'):
            raise ValueError('invalid_input_pdf')
    # 严格锁结构校验先于执行用户指定路径；诊断后必须与该锁完全相同。
    validate_lock(lock, lock)
    if lock['language'] != language:
        raise ValueError('backend_identity_language_mismatch')
    validate_lock(lock, identity(lock['executable'], lock['tessdataDir'], language, min(20, max(.001, deadline - time.monotonic()))))
    bootstrap, execution, gateway = load('bootstrap'), load('execution'), load('command_gateway')
    scripts = Path(__file__).parent
    runtime_lock = json.loads((scripts / 'runtime.lock.json').read_text())
    runtime = bootstrap.diagnose(runtime_lock, runtime_home)
    if not runtime.get('installed'):
        raise ValueError('verified_native_installation_required; use printcraft-cli-setup')
    input_sha, resources = sha(source), gateway.capture_resources(scripts)
    # mkdir 的排他性就是本入口的任务身份消费；重入只读回执，不允许覆盖继续。
    output.mkdir(mode=0o700)
    receipt = dict(protocol=PROTOCOL, runId=str(uuid.uuid4()), attempted=True, status='UNKNOWN', phase='prepared',
                   automaticReplay=False, completeAcceptance=False, documentIdsReusable=False,
                   backendIdentity=lock, nativeIdentity=runtime, inputPath=str(source), inputSha256=input_sha,
                   skillResourceSha256=resources, rasterize=True, dpi=dpi, language=language, stages=[],
                   receiptPath=str(output / 'receipt.json'), pageSegmentationMode=3,
                   losses=['forms', 'bookmarks', 'attachments', 'signatures', 'vector-and-original-text-semantics'], visualReview='NOT_RUN')
    target = output / 'receipt.json'
    execution.atomic_json(target, receipt)
    prefix = [runtime['executable']]

    def call(args, phase):
        return call_child(execution, args, deadline - time.monotonic(), output, receipt, phase)

    try:
        original = output / 'input.pdf'
        shutil.copyfile(source, original); original.chmod(0o600)
        if sha(original) != input_sha or sha(source) != input_sha:
            raise ValueError('input_changed_before_native_render')
        backend_data = output / 'backend-data'; backend_data.mkdir(mode=0o700)
        for name, digest in ((language + '.traineddata', lock['modelSha256']), ('pdf.ttf', lock['pdfFontSha256'])):
            copy = backend_data / name
            shutil.copyfile(Path(lock['tessdataDir']) / name, copy); copy.chmod(0o600)
            if sha(copy) != digest:
                raise ValueError('backend_identity_changed_before_execution')
        version = call(prefix + ['--version'], 'native-version').splitlines()[0].strip()
        if version != runtime_lock['artifact'] + ' ' + runtime_lock['resolvedVersion']:
            raise ValueError('native_version_mismatch')
        catalog_text = call(prefix + ['tools'], 'native-catalog')
        catalog = gateway.strict_json(catalog_text)
        gateway.normalize('printcraft', catalog)
        receipt['nativeCatalogSha256'] = hashlib.sha256(catalog_text.encode()).hexdigest()
        receipt['nativeOcrLanguages'] = next(row['input_schema']['properties']['language']['enum'] for row in catalog if row['name'] == 'ocr_recognize')
        info = json.loads(call(prefix + ['info', str(original)], 'input-info'))
        pages = info['pages']
        if type(pages) is not int or not 1 <= pages <= 100:
            raise ValueError('unsupported_page_count')
        images, pixel_sha = [], []
        for page in range(1, pages + 1):
            pam = output / f'input-{page}.pam'
            call(prefix + ['render', str(original), '--page', str(page), '--dpi', str(dpi), '--out', str(pam)], f'render-{page}')
            ppm = pam_to_ppm(pam.read_bytes()); pam.unlink()
            image = output / f'page-{page}.png'; image.write_bytes(ppm_to_png(ppm)); image.chmod(0o600)
            images.append(str(image)); pixel_sha.append(hashlib.sha256(ppm).hexdigest())
        listing = output / 'images.txt'
        if any('\n' in item or '\r' in item for item in images):
            raise ValueError('image_list_path_newline')
        listing.write_text('\n'.join(images) + '\n'); listing.chmod(0o600)
        call([lock['executable'], str(listing), str(output / 'searchable'), '--tessdata-dir', str(backend_data), '-l', language,
              '--oem', '1', '--psm', '3', '--dpi', str(dpi), '-c', 'tessedit_create_pdf=1', '-c', 'tessedit_create_txt=1'], 'recognize')
        pdf = output / 'searchable.pdf'; text_file = output / 'searchable.txt'
        if not pdf.is_file() or not text_file.is_file() or pdf.stat().st_size == 0:
            raise ValueError('ocr_output_missing')
        pdf.chmod(0o600); text_file.chmod(0o600)
        reopened = json.loads(call(prefix + ['info', str(pdf)], 'reopen-info'))
        if reopened['pages'] != pages:
            raise ValueError('output_page_count_mismatch')
        observed_text = []
        for page in range(1, pages + 1):
            text = call(prefix + ['text', str(pdf), '--page', str(page)], f'reopen-text-{page}').strip()
            if not re.search('[\u3400-\u9fff]', text):
                raise ValueError('chinese_text_missing_on_page_' + str(page))
            observed_text.append(text)
            pam = output / f'output-{page}.pam'
            call(prefix + ['render', str(pdf), '--page', str(page), '--dpi', str(dpi), '--out', str(pam)], f'reopen-render-{page}')
            rendered = pam_to_ppm(pam.read_bytes()); pam.unlink()
            if hashlib.sha256(rendered).hexdigest() != pixel_sha[page - 1]:
                raise ValueError('output_image_geometry_or_pixels_changed_on_page_' + str(page))
        receipt.update(status='DETERMINISTIC_PASS_REVIEW_REQUIRED', phase='verified', pages=pages,
                       pageText=observed_text, pagePixelSha256=pixel_sha, newProcessReopen=True, pixelEquality=True)
    except ChildFailure:
        pass
    except KeyboardInterrupt:
        receipt.update(status='UNKNOWN', error='interrupted')
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        receipt.update(status='FAILED_OR_PARTIAL', error=str(error))
    finally:
        try:
            receipt['inputAfterSha256'] = sha(source)
            receipt['skillResourceAfterSha256'] = gateway.capture_resources(scripts)
            receipt['backendAfterIdentity'] = identity(lock['executable'], lock['tessdataDir'], language, min(20, max(.001, deadline - time.monotonic())))
            receipt['nativeAfterSha256'] = sha(runtime['executable'])
            receipt['preserved'] = (receipt['inputAfterSha256'] == input_sha and receipt['skillResourceAfterSha256'] == resources
                                    and receipt['backendAfterIdentity'] == lock and receipt['nativeAfterSha256'] == runtime['binarySha256'])
            if not receipt['preserved'] and receipt['status'] == 'DETERMINISTIC_PASS_REVIEW_REQUIRED':
                receipt['status'] = 'INPUT_OR_BACKEND_OR_SKILL_CHANGED_REVIEW_REQUIRED'
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            receipt['preservationCheckError'] = str(error)
            if receipt['status'] == 'DETERMINISTIC_PASS_REVIEW_REQUIRED':
                receipt['status'] = 'PRESERVATION_UNKNOWN_REVIEW_REQUIRED'
        receipt['artifacts'] = execution.output_inventory([dict(path=str(output / name), role=role, mediaType=media)
            for name, role, media in [('searchable.pdf', 'delivery', 'application/pdf'), ('searchable.txt', 'recognized-text', 'text/plain')]])
        execution.atomic_json(target, receipt)
        # 中间图像与模型均属本入口创建的材料；保留 input/output/回执以便对账。
        for path in output.glob('page-*.png'):
            path.unlink()
        if (output / 'backend-data').is_dir():
            shutil.rmtree(output / 'backend-data')
        if (output / 'images.txt').exists():
            (output / 'images.txt').unlink()
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('diagnose', 'run'))
    parser.add_argument('--backend', choices=('tesseract',), required=True)
    parser.add_argument('--language', choices=LANGUAGES, required=True)
    parser.add_argument('--tesseract', type=Path)
    parser.add_argument('--tessdata-dir', type=Path)
    parser.add_argument('--backend-lock', type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--runtime-home', type=Path, default=Path.home() / '.local/share/craft-runtimes')
    parser.add_argument('--dpi', type=int, default=150)
    parser.add_argument('--timeout', type=float, default=1800)
    parser.add_argument('--rasterize', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'diagnose':
            if not args.tesseract or not args.tessdata_dir:
                parser.error('diagnose requires --tesseract and --tessdata-dir')
            result = identity(args.tesseract, args.tessdata_dir, args.language)
        else:
            if not args.backend_lock or not args.input or not args.output_dir:
                parser.error('run requires --backend-lock, --input and --output-dir')
            lock = load('command_gateway').strict_json(args.backend_lock.read_text())
            result = run_ocr(lock, args.input, args.output_dir, args.runtime_home, args.language, args.dpi, args.timeout, args.rasterize)
        # 完整目录/进程诊断保留在私有回执；stdout 仅给调用者需要的摘要。
        public = result if args.action == 'diagnose' else {key: result[key] for key in (
            'protocol', 'runId', 'status', 'phase', 'receiptPath', 'backendIdentity', 'inputSha256',
            'artifacts', 'pages', 'pageText', 'preserved', 'visualReview', 'automaticReplay', 'error') if key in result}
        print(json.dumps(public, ensure_ascii=False, indent=2))
        return 0 if args.action == 'diagnose' or result['status'] == 'DETERMINISTIC_PASS_REVIEW_REQUIRED' else 1
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps(dict(error=str(error), automaticReplay=False, protocol=PROTOCOL), ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
