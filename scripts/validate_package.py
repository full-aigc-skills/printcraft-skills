"""校验本地技能结构与不可变安装锁；不安装运行时。"""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]

def validate():
    suite=json.loads((ROOT/'skill-suite.json').read_text())
    domain=suite['domain']
    expected=set(suite['skills'])
    actual={p.name for p in (ROOT/'skills').iterdir() if p.is_dir()}
    if actual!=expected:raise ValueError('skill_set_mismatch')
    canonical=ROOT/'skills'/f'{domain}-use'/'scripts'
    resources=('bootstrap.py','cli.py','runtime.lock.json','commands.py','command_gateway.py','execution.py','verification.py','ocr.py')
    for name in sorted(expected):
        p=ROOT/'skills'/name
        if p.is_symlink():raise ValueError('skill_symlink')
        text=(p/'SKILL.md').read_text()
        if not text.startswith('---\n') or f'name: {name}\n' not in text or 'description:' not in text:raise ValueError('skill_frontmatter_invalid')
        if len(text.splitlines())>=500:raise ValueError('skill_too_long')
        if '/mnt/skills/user' in text:raise ValueError('hardcoded_skill_path')
        actual_resources={f.name for f in (p/'scripts').iterdir() if f.is_file() and f.suffix in {'.py','.json'}}
        if actual_resources!=set(resources):raise ValueError('unexpected_execution_resource')
        for resource in resources:
            file=p/'scripts'/resource
            if file.is_symlink() or file.read_bytes()!=(canonical/resource).read_bytes():raise ValueError('independent_resource_drift')
        lock=json.loads((p/'scripts/runtime.lock.json').read_text())
        if lock['artifact'] not in {'printcraft-cli','pdfcraft-cli'}:raise ValueError('foreign_domain_runtime')
        for item in lock['artifacts'].values():
            for key in ('archiveSha256','binarySha256'):
                if not re.fullmatch('[0-9a-f]{64}',item[key]):raise ValueError('invalid_checksum')
    return {'domain':domain,'skills':len(expected),'structure':'PASS','nativeInstallation':'NOT_RUN','modelDispatch':'NOT_RUN'}

if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False))
