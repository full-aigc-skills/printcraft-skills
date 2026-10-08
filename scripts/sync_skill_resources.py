"""从 use 规范副本生成六个独立技能的共享资源；不改文档和用户数据。"""
import argparse
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
RESOURCES=('bootstrap.py','cli.py','commands.py','command_gateway.py','execution.py','verification.py','ocr.py','runtime.lock.json')
def sync(check=False):
    suite=json.loads((ROOT/'skill-suite.json').read_text());source=ROOT/'skills/printcraft-use/scripts';drift=[]
    for name in suite['skills']:
        target=ROOT/'skills'/name/'scripts'
        for filename in RESOURCES:
            original=source/filename;destination=target/filename
            if original.is_symlink() or destination.is_symlink():raise ValueError('resource_symlink')
            if not destination.exists() or destination.read_bytes()!=original.read_bytes():
                drift.append(str(destination.relative_to(ROOT)))
                if not check:shutil.copyfile(original,destination)
    if check and drift:raise ValueError('resource_drift: '+str(drift))
    return {'mode':'check' if check else 'sync','drift':drift}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');print(json.dumps(sync(p.parse_args().check)))
