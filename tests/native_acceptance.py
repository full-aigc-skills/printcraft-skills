"""显式原生验收；只使用固定已安装 CLI 与原创 CC0 夹具，不属于 mock 测试。"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixture',ROOT/'tests/fixtures/make_pdf.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

def sequence(text):
    decoder=json.JSONDecoder();values=[]
    while text.strip():
        value,end=decoder.raw_decode(text.lstrip());values.append(value);text=text.lstrip()[end:]
    return values

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime-home',type=Path,required=True);parser.add_argument('--workdir',type=Path,required=True);a=parser.parse_args();a.workdir.mkdir(mode=0o700,parents=True)
    scripts=ROOT/'skills/printcraft-use/scripts';source=a.workdir/'source.pdf';fixture.make_pdf(source);before=hashlib.sha256(source.read_bytes()).hexdigest()
    prefix=[sys.executable,'-I','-B',str(scripts/'cli.py'),'--runtime-home',str(a.runtime_home),'--']
    def call(*args):
        r=subprocess.run(prefix+list(args),capture_output=True,text=True,timeout=180)
        if r.returncode:raise ValueError(r.stderr or r.stdout)
        return r.stdout
    def steps(name,operations,path=source,allow_failure=False):
        plan={'domain':'printcraft','steps':[{'command':'doc_open','params':{'path':str(path)}},*operations]}
        planfile=a.workdir/(name+'.json');planfile.write_text(json.dumps(plan));planfile.chmod(0o600)
        declared=[]
        for operation in operations:
            params=operation['params'];output_path=params.get('out') or (params.get('path') if operation['command'] in {'doc_save','sign_id_create'} else None)
            if output_path:declared.append({'path':output_path,'role':'delivery','mediaType':'application/pdf' if output_path.endswith('.pdf') else 'application/x-pkcs12'})
        expected=a.workdir/(name+'-outputs.json');expected.write_text(json.dumps({'outputs':declared}))
        r=subprocess.run([sys.executable,'-I',str(scripts/'commands.py'),'run',str(planfile),'--runtime-home',str(a.runtime_home),'--output',str(a.workdir/(name+'-run')),'--input',str(source),'--expect',str(expected)],capture_output=True,text=True,timeout=240)
        planfile.unlink()
        if r.returncode and not allow_failure:raise ValueError(r.stdout+r.stderr)
        return json.loads(r.stdout)
    def tool(tool_name,**params):return {'command':tool_name,'params':dict(doc=1,**params)}
    results={}
    def record(name,fn):
        try:details=fn();results[name]={'status':'PASS','details':details}
        except Exception as error:results[name]={'status':'FAILED','error':str(error)}
    def page_case(name,operations,labels,pages,geometry=None):
        output=a.workdir/(name+'.pdf');receipt=steps(name,[*operations,tool('doc_save',path=str(output))]);info=json.loads(call('info',str(output)))
        observed=[call('text',str(output),'--page',str(i+1)).strip() for i in range(info['pages'])]
        assert info['pages']==pages,(info,pages)
        assert all(label in text for label,text in zip(labels,observed)) and len(labels)==len(observed),observed
        if geometry:assert info['first_page_pt']==geometry,info
        return {'executionRunId':receipt['runId'],'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'text':observed,'info':info}
    record('reorder',lambda:page_case('reorder',[tool('page_move',pages=[3],to=1)],['PAGE-GAMMA','PAGE-ALPHA','PAGE-BETA'],3))
    def extract():
        out=a.workdir/'extract.pdf';receipt=steps('extract',[tool('page_extract',pages=[3,1],out=str(out))]);text=call('text',str(out));assert text.index('PAGE-GAMMA')<text.index('PAGE-ALPHA');assert json.loads(call('info',str(out)))['pages']==2
        return {'runId':receipt['runId'],'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    record('extract',extract)
    def combine():
        out=a.workdir/'combine.pdf';receipt=steps('combine',[{'command':'doc_combine','params':{'paths':[str(source),str(a.workdir/'extract.pdf')],'out':str(out)}}]);text=call('text',str(out));assert json.loads(call('info',str(out)))['pages']==5;assert text.count('PAGE-GAMMA')==2
        return {'runId':receipt['runId'],'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    record('combine',combine)
    record('rotate',lambda:page_case('rotate',[tool('page_rotate',pages=[1],degrees=90)],['PAGE-ALPHA','PAGE-BETA','PAGE-GAMMA'],3,[792.0,612.0]))
    record('crop',lambda:page_case('crop',[tool('page_set_box',pages=[1],margins=[10,10,10,10])],['PAGE-ALPHA','PAGE-BETA','PAGE-GAMMA'],3,[592.0,772.0]))
    def partial():
        out=a.workdir/'partial.pdf';receipt=steps('partial',[tool('doc_save',path=str(out)),tool('page_rotate',pages=[999],degrees=90)],allow_failure=True)
        assert receipt['status']=='FAILED_OR_PARTIAL' and receipt['artifacts'][0]['status']=='PRESENT',receipt
        assert out.is_file() and receipt['automaticReplay'] is False
        return {'runId':receipt['runId'],'status':receipt['status'],'artifacts':receipt['artifacts']}
    record('partial_write_failure',partial)
    def form():
        out=a.workdir/'form.pdf';steps('form',[tool('form_add_field',page=1,type='text',name='sample',rect=[72,120,200,150]),tool('form_fill',values={'sample':'verified form'}),tool('doc_save',path=str(out))]);r=steps('form-reopen',[tool('form_fields')],out);items=sequence(r['stdout']);assert 'verified form' in json.dumps(items)
        return {'fields':items[-1],'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    record('form_save_reopen',form)
    def pdfa():
        r=steps('pdfa',[tool('pdfa_verify',level='2b')]);items=sequence(r['stdout']);assert 'violations' in json.dumps(items[-1]) or 'issues' in json.dumps(items[-1]);return items[-1]
    record('pdfa_subset_report',pdfa)
    def sign():
        r=steps('sign',[tool('sign_list')]);items=sequence(r['stdout']);assert items[-1]==[] or not items[-1].get('signatures',[]);return {'unsignedDocument':items[-1],'actualSigning':'NOT_RUN_NO_TEST_IDENTITY'}
    record('unsigned_signature_inspection',sign)
    def redact():
        out=a.workdir/'redacted.pdf';steps('redact',[tool('redact_mark',find='PAGE-ALPHA'),tool('redact_apply'),tool('doc_save',path=str(out),full=True)])
        text=call('text',str(out));assert 'PAGE-ALPHA' not in text and 'PAGE-BETA' in text and 'PAGE-GAMMA' in text
        assert b'PAGE-ALPHA' not in out.read_bytes()
        call('render',str(out),'--page','1','--out',str(a.workdir/'redacted.pam'))
        return {'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'removedTextAbsent':True,'objectBytesAbsent':True,'render':'redacted.pam','visualReview':'NOT_RUN'}
    record('redaction_text_objects_render',redact)
    def signed():
        identity=a.workdir/'fixture-only.p12';out=a.workdir/'signed.pdf'
        steps('create-test-id',[{'command':'sign_id_create','params':{'name':'PrintCraft Test Only','password':'fixture-only-not-production','path':str(identity)}}]);identity.chmod(0o600)
        try:
            steps('sign-document',[tool('sign_document',id=str(identity),password='fixture-only-not-production',out=str(out))])
            receipt=steps('sign-reopen',[tool('sign_list')],out);observed=sequence(receipt['stdout'])[-1]
            assert observed['count']==1 and observed['signed']==1 and observed['all_valid'] is False
            assert observed['signatures'][0]['status']=='unknown' and observed['signatures'][0]['modification']=='none'
            return {'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'signatures':observed,'trust':'SELF_SIGNED_FIXTURE_ONLY'}
        finally:
            if identity.exists():identity.unlink()
    record('signature_save_reopen',signed)
    r=steps('ocr-status',[{'command':'ocr_status','params':{}}]);results['ocr_status']={'status':'OBSERVED','details':sequence(r['stdout'])[-1],'chineseRecognition':'NOT_RUN','otherPlatforms':'NOT_RUN'}
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before,'original input changed'
    report={'runtimeVersion':call('--version').strip(),'originalSha256':before,'results':results,'sourceUnchanged':True,'visualReview':'NOT_RUN'}
    (a.workdir/'native-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(any(item.get('status')=='FAILED' for item in results.values()))
if __name__=='__main__':raise SystemExit(main())
