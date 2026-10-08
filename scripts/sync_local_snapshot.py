"""同步未发布的本地插件快照；预检旧摘要，不覆盖漂移或已发布来源。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import os

ROOT=Path(__file__).resolve().parents[1]


def inventory(root):
    """拒绝链接后计算技能文件摘要。"""
    entries=sorted(root.rglob('*'))
    if root.is_symlink() or any(p.is_symlink() for p in entries):raise ValueError('snapshot_symlink')
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in entries if p.is_file() and p.name!='.DS_Store' and '__pycache__' not in p.parts}


def sync(plugin):
    """仅对当前领域的未发布且未漂移快照做正常增量复制。"""
    if plugin.is_symlink() or any((plugin/p).is_symlink() for p in ('plugin.json','candidate-source.json','upstream','upstream/skill-suite.json')):raise ValueError('snapshot_metadata_symlink')
    domain=ROOT.name.removesuffix('-skills')
    metadata=plugin/'candidate-source.json'
    lock=json.loads(metadata.read_text())
    manifest=json.loads((plugin/'plugin.json').read_text())
    if (manifest['name']!=domain or lock.get('sourceProject')!=ROOT.name or lock.get('sourceStatus')!='local-unpublished-candidate' or lock.get('releaseTag') is not None):raise ValueError('not_current_local_candidate')
    all_current=inventory(plugin/'skills')
    local={'printcraft-harness'}
    suite=json.loads((ROOT/'skill-suite.json').read_text())
    if {p.split('/')[0] for p in all_current}-set(suite['skills'])-local:raise ValueError('foreign_plugin_skill')
    current={p:d for p,d in all_current.items() if p.split('/')[0] not in local}
    if current!=lock['skillFileSha256']:raise ValueError('preserve_modified_plugin_snapshot')
    previous_suite=plugin/'upstream/skill-suite.json'
    if previous_suite.exists() and (hashlib.sha256(previous_suite.read_bytes()).hexdigest()!=lock.get('sourceSuiteSha256') or json.loads(previous_suite.read_text()).get('version')!=lock.get('sourceVersion')):raise ValueError('preserve_modified_source_suite')
    incoming=inventory(ROOT/'skills')
    if set(current)-set(incoming):raise ValueError('source_removal_requires_review')
    # 完整暂存和二次预检后才发布单文件；拒绝阶段不改原快照。
    with tempfile.TemporaryDirectory(prefix='.snapshot-stage-',dir=plugin) as temporary:
        stage=Path(temporary)
        for relative,digest in incoming.items():
            target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/'skills'/relative,target)
            if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('source_changed_while_staging')
        if {p:d for p,d in inventory(plugin/'skills').items() if p.split('/')[0] not in local}!=current:raise ValueError('concurrent_snapshot_change')
        for relative,digest in incoming.items():
            if current.get(relative)==digest:continue
            target=plugin/'skills'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            os.replace(stage/relative,target)
    if {p:d for p,d in inventory(plugin/'skills').items() if p.split('/')[0] not in local}!=incoming:raise ValueError('snapshot_copy_mismatch')
    upstream=plugin/'upstream';upstream.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'skill-suite.json',upstream/'skill-suite.json')
    lock['sourceVersion']=suite['version']
    lock['sourceSuiteSha256']=hashlib.sha256((upstream/'skill-suite.json').read_bytes()).hexdigest()
    lock['skillFileSha256']=incoming
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=plugin,delete=False) as stream:
        stream.write(json.dumps(lock,ensure_ascii=False,indent=2)+'\n');stream.flush();os.fsync(stream.fileno());name=stream.name
    os.replace(name,metadata)
    return {'domain':domain,'skills':len(list((ROOT/'skills').glob('*/SKILL.md'))),'sourceRelease':'UNPUBLISHED','snapshot':'PASS'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plugin-root',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(sync(args.plugin_root),ensure_ascii=False))
