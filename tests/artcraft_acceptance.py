"""显式依赖的跨插件原生验收；不安装、不修改生产者仓库，不混入基础 unittest。"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('artcraft-root','vector-skill','vector-executable','vector-runtime-home','runtime-home','workdir'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--node',default='node')
    args=parser.parse_args()
    args.workdir=args.workdir.absolute()
    if args.workdir.exists():raise ValueError('new_workdir_required')
    args.workdir.mkdir(mode=0o700)
    scripts=ROOT/'skills/printcraft-use/scripts'
    def invoke(command,timeout=180):
        result=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
        if result.returncode:raise ValueError(result.stdout+result.stderr)
        return result.stdout
    producer=args.workdir/'producer'
    producer_command=[args.node,str(ROOT/'tests/artcraft_producer.ts'),str(args.artcraft_root.absolute()),str(args.vector_skill.absolute()),str(args.vector_executable.absolute()),str(args.vector_runtime_home.absolute()),sys.executable,str(producer)]
    invoke(producer_command,600)
    report=json.loads((producer/'producer-report.json').read_text())
    module_spec=importlib.util.spec_from_file_location('printcraft_verification',scripts/'verification.py')
    verification=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(verification)
    prefix=[sys.executable,'-I','-B',str(scripts/'cli.py'),'--runtime-home',str(args.runtime_home),'--']
    def native(*argv):return invoke(prefix+list(argv))
    original_inputs={}
    outputs={}
    handoffs={}
    for phase in ('first','second'):
        children=sorted(report[phase]['children'],key=lambda child:child['nodeId'])
        paths=[str(Path(child['root'])/child['outputs'][0]['location']) for child in children]
        handoff={'protocol':'artcraft.printcraft-handoff/1','producer':'artcraft','producerVersion':report['producerVersion'],'files':[{'path':path,'sha256':sha(path)} for path in paths]}
        handoff_file=args.workdir/(phase+'-handoff.json');handoff_file.write_text(json.dumps(handoff))
        handoffs[phase]=json.loads(invoke([sys.executable,'-I','-B',str(scripts/'commands.py'),'handoff',str(handoff_file),'--producer-version',report['producerVersion']]))
        original_inputs.update({path:sha(path) for path in paths})
        output=args.workdir/(phase+'.pdf')
        plan={'domain':'printcraft','steps':[{'command':'doc_combine','params':{'paths':paths,'out':str(output)}}]}
        plan_file=args.workdir/(phase+'-plan.json');plan_file.write_text(json.dumps(plan))
        expect=args.workdir/(phase+'-outputs.json');expect.write_text(json.dumps({'outputs':[{'path':str(output),'role':'delivery','mediaType':'application/pdf'}]}))
        command=[sys.executable,'-I','-B',str(scripts/'commands.py'),'run',str(plan_file),'--runtime-home',str(args.runtime_home),'--output',str(args.workdir/(phase+'-run')),'--expect',str(expect)]
        for path in paths:command+=['--input',path]
        execution=json.loads(invoke(command));assert execution['status']=='NATIVE_EXIT_ZERO_REVIEW_REQUIRED',execution
        assert json.loads(native('info',str(output)))['pages']==2
        outputs[phase]={'path':str(output),'sha256':sha(output),'runId':execution['runId']}
    # 仅裁剪返工页，不能改变独立页；真实渲染像素用于保留断言。
    revised=args.workdir/'revised.pdf'
    plan={'domain':'printcraft','steps':[{'command':'doc_open','params':{'path':outputs['second']['path']}},{'command':'page_set_box','params':{'doc':1,'pages':[1],'margins':[4,4,4,4]}},{'command':'doc_save','params':{'doc':1,'path':str(revised)}}]}
    plan_file=args.workdir/'crop-plan.json';plan_file.write_text(json.dumps(plan))
    expect=args.workdir/'crop-outputs.json';expect.write_text(json.dumps({'outputs':[{'path':str(revised),'role':'delivery','mediaType':'application/pdf'}]}))
    execution=json.loads(invoke([sys.executable,'-I','-B',str(scripts/'commands.py'),'run',str(plan_file),'--runtime-home',str(args.runtime_home),'--output',str(args.workdir/'crop-run'),'--input',outputs['second']['path'],'--expect',str(expect)]))
    assert execution['status']=='NATIVE_EXIT_ZERO_REVIEW_REQUIRED',execution
    rendered={}
    for name,pdf in [('first',outputs['first']['path']),('second',outputs['second']['path']),('revised',str(revised))]:
        rendered[name]=[]
        for page in (1,2):
            image=args.workdir/f'{name}-{page}.pam';native('render',pdf,'--page',str(page),'--out',str(image))
            rendered[name].append(sha(image))
    assert rendered['first'][0]!=rendered['second'][0]
    assert rendered['first'][1]==rendered['second'][1]==rendered['revised'][1]
    assert rendered['second'][0]!=rendered['revised'][0]
    # 移动的是实际 PDF 及已登记输入，和手机/平板验收分别记录。
    moved=args.workdir/'移动 PDF';moved.mkdir();shutil.copy2(revised,moved/'delivery.pdf')
    copied=moved/'delivery.pdf';assert sha(copied)==sha(revised)
    info=json.loads(native('info',str(copied)));assert info['pages']==2
    request={'protocol':verification.PROTOCOL,'ruleVersion':1,'inputSha256':original_inputs,'outputs':[{'path':str(copied),'sha256':sha(copied),'pages':2,'textPolicy':'optional'}]}
    request_file=args.workdir/'verification-request.json';request_file.write_text(json.dumps(request))
    receipt=verification.verify_request(request_file,scripts,args.runtime_home)
    assert receipt['status']=='DETERMINISTIC_PASS_REVIEW_REQUIRED',receipt
    (args.workdir/'verification-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    assert all(sha(path)==digest for path,digest in original_inputs.items())
    result={'status':'PASS','scope':'REAL_LOCAL_CROSS_PLUGIN_ONLY','producerReportSha256':sha(producer/'producer-report.json'),'producerVersion':report['producerVersion'],'producerSourceSha256':report['sourceSha256'],'producerCommand':producer_command,'handoffs':handoffs,'producerExecution':'REAL_NATIVE_PASS','producerSelectiveRework':report['selectiveRework'],'producerPortablePackage':report['portablePackage'],'outputs':outputs,'pdfSelectiveRework':{'status':'PASS','runId':execution['runId'],'changedPages':[1],'preservedPages':[2],'renderSha256':rendered},'pdfPortableDelivery':{'status':'PASS_SAME_MACHINE_DIRECTORY_MOVE','sha256':sha(copied),'info':info},'mobileDevice':'NOT_RUN','otherMachine':'NOT_RUN','visualReview':'NOT_RUN','sourceInputUnchanged':True,'publishedProducerIdentity':'NOT_VERIFIED','verificationRequestSha256':sha(request_file),'verificationReceiptSha256':sha(args.workdir/'verification-receipt.json')}
    (args.workdir/'cross-plugin-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'status':'PASS','report':str(args.workdir/'cross-plugin-report.json')}))

if __name__=='__main__':main()
