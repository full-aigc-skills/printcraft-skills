"""显式 PDF 清单的确定性验收与审阅绑定，不自动循环修订。"""
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
PROTOCOL='printcraft.verification/1'
RULE_VERSION=1

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def artifact(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('output_missing_or_symlink')
    data=path.read_bytes()
    if not data or not data.startswith(b'%PDF-') or b'%%EOF' not in data[-4096:]:raise ValueError('output_empty_or_invalid_pdf')
    return {'path':str(path.absolute()),'role':'delivery','mediaType':'application/pdf','size':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def compare(info,pages,expected):
    errors=[]
    if info.get('pages')!=expected.get('pages'):errors.append('page_count_mismatch')
    if expected.get('textPolicy','required')=='required' and any(not p.strip() for p in pages):errors.append('unexpected_empty_text')
    for i,text in enumerate(expected.get('pageText',[])):
        if i>=len(pages) or text not in pages[i]:errors.append(f'page_{i+1}_text_mismatch')
    if expected.get('firstPagePt') and info.get('first_page_pt')!=expected['firstPagePt']:errors.append('first_page_geometry_mismatch')
    return errors

def verify_request(path,script_dir,runtime_home=None):
    request=json.loads(Path(path).read_text())
    if request.get('protocol')!=PROTOCOL or request.get('ruleVersion')!=RULE_VERSION:raise ValueError('verification_protocol_or_rules_unsupported')
    if set(request)-{'protocol','ruleVersion','outputs','visualReviewRequired','runId','inputSha256'}:raise ValueError('verification_unknown_request_field')
    if not isinstance(request.get('outputs'),list) or not request['outputs']:raise ValueError('explicit_outputs_required')
    for input_path,digest in request.get('inputSha256',{}).items():
        if Path(input_path).is_symlink() or sha(input_path)!=digest:raise ValueError('verification_input_changed')
    prefix=[sys.executable,'-I','-B',str(script_dir/'cli.py')]
    if runtime_home:prefix+=['--runtime-home',str(runtime_home)]
    artifacts=[];errors=[]
    for expected in request['outputs']:
        if set(expected)-{'path','sha256','pages','pageText','textPolicy','firstPagePt','pageGeometry','sourcePages','role','mediaType'}:raise ValueError('verification_unknown_output_rule')
        if not isinstance(expected.get('pages'),int) or isinstance(expected['pages'],bool) or expected['pages']<1:raise ValueError('positive_page_count_required')
        if expected.get('textPolicy','required') not in {'required','scan','optional'}:raise ValueError('invalid_text_policy')
        candidate=artifact(expected['path']);before=candidate['sha256']
        if before!=expected.get('sha256'):raise ValueError('candidate_changed')
        def native(*arguments):
            result=subprocess.run(prefix+['--',*arguments],capture_output=True,text=True,timeout=180)
            if result.returncode:raise ValueError('native_reopen_failed: '+result.stderr[:1000])
            return result.stdout
        info=json.loads(native('info',candidate['path']))
        pages=[native('text',candidate['path'],'--page',str(i+1)).strip() for i in range(info['pages'])]
        found=compare(info,pages,expected)
        if expected.get('pageGeometry') is not None:
            with tempfile.NamedTemporaryFile(mode='w',suffix='.json',delete=False) as stream:
                temporary=Path(stream.name);json.dump([{'tool':'doc_open','args':{'path':candidate['path']}},{'tool':'doc_info','args':{'doc':1}}],stream)
            try:
                raw=native('run','--script',str(temporary));decoder=json.JSONDecoder();values=[]
                while raw.strip():
                    value,end=decoder.raw_decode(raw.lstrip());values.append(value);raw=raw.lstrip()[end:]
                geometry=values[-1]['pages'];candidate['pageGeometry']=geometry
                if geometry!=expected['pageGeometry']:found.append('page_geometry_mismatch')
            finally:temporary.unlink()
        if expected.get('sourcePages') is not None:
            mappings=expected['sourcePages']
            if len(mappings)!=len(pages):found.append('source_page_count_mismatch')
            for index,mapping in enumerate(mappings):
                if sha(mapping['path'])!=mapping['sha256']:raise ValueError('source_mapping_input_changed')
                text=native('text',mapping['path'],'--page',str(mapping['page'])).strip()
                if index>=len(pages) or pages[index]!=text:found.append(f'page_{index+1}_source_mismatch')
            candidate['sourcePages']=mappings
        candidate['role']=expected.get('role','delivery')
        candidate['mediaType']=expected.get('mediaType','application/pdf')
        if sha(candidate['path'])!=before:found.append('candidate_changed_during_verification')
        candidate.update(info=info,pageText=pages,textClassification='EMPTY_NEEDS_OCR_OR_INTENT_REVIEW' if not any(pages) else 'TEXT_PRESENT',errors=found)
        artifacts.append(candidate);errors.extend(found)
    return {'protocol':PROTOCOL,'ruleVersion':RULE_VERSION,'runId':request.get('runId'),'inputSha256':request.get('inputSha256',{}),'requestSha256':sha(path),'artifacts':artifacts,'errors':errors,'status':'FAILED' if errors else 'DETERMINISTIC_PASS_REVIEW_REQUIRED','completeAcceptance':False,'visualReview':'NOT_RUN','automaticRevision':False}

def accept_review(receipt,review):
    if receipt.get('protocol')!=PROTOCOL or receipt.get('status')!='DETERMINISTIC_PASS_REVIEW_REQUIRED':raise ValueError('deterministic_gate_not_passed')
    if review.get('ruleVersion')!=receipt['ruleVersion'] or review.get('requestSha256')!=receipt['requestSha256']:raise ValueError('stale_review')
    for item in receipt['artifacts']:
        if sha(item['path'])!=item['sha256']:raise ValueError('candidate_changed')
    if review.get('decision') not in {'approve','revise'} or not review.get('reviewer') or not review.get('notes'):raise ValueError('explicit_review_required')
    return dict(receipt,status='VERIFIED' if review['decision']=='approve' else 'REVISION_PROPOSED',visualReview=review,completeAcceptance=review['decision']=='approve',automaticRevision=False)

def validate_handoff(data,allowed_producers=('artcraft',),producer_versions=None):
    if not isinstance(data,dict) or set(data)!={'protocol','producer','producerVersion','files'}:raise ValueError('handoff_fields_invalid')
    if data.get('protocol')!='artcraft.printcraft-handoff/1' or data.get('producer') not in allowed_producers:raise ValueError('incompatible_producer_or_handoff')
    if not isinstance(data.get('producerVersion'),str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?',data['producerVersion']) or not isinstance(data.get('files'),list) or not data['files']:raise ValueError('producer_version_and_files_required')
    supported=producer_versions if producer_versions is not None else {'artcraft':{'1.0.0'}}
    if data['producerVersion'] not in supported.get(data['producer'],set()):raise ValueError('incompatible_producer_version')
    seen=set()
    for item in data['files']:
        if not isinstance(item,dict) or set(item)!={'path','sha256'} or not isinstance(item['path'],str) or not Path(item['path']).is_absolute() or not isinstance(item['sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',item['sha256']):raise ValueError('handoff_file_invalid')
        if item['path'] in seen:raise ValueError('handoff_duplicate_file')
        seen.add(item['path'])
        if artifact(item['path'])['sha256']!=item.get('sha256'):raise ValueError('handoff_hash_mismatch')
    return {'status':'HANDOFF_INTEGRITY_PASS','producerExecution':'NOT_RUN'}
