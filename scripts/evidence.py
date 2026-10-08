"""分层证据指纹与过期判断；不以静态通过替代原生或模型验收。"""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def fingerprint(root):
    result={}
    for directory in ('skills','scripts','tests','upstream'):
        for path in sorted((root/directory).rglob('*')):
            if path.is_symlink():raise ValueError('source_symlink')
            if path.is_file() and '__pycache__' not in path.parts and path.name!='.DS_Store':result[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('skill-suite.json','plugin.json','candidate-source.json','.codex-plugin/plugin.json','docs/tool-coverage.json'):
        path=root/name
        if path.exists():result[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result

def current(index,root):
    if index.get('sourceSha256')!=fingerprint(root):return False
    return all((root/path).is_file() and hashlib.sha256((root/path).read_bytes()).hexdigest()==digest for path,digest in index.get('evidenceSha256',{}).items())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',type=Path);a=p.parse_args()
    if a.check:
        ok=current(json.loads(a.check.read_text()),ROOT);print(json.dumps({'sourceCurrent':ok}));raise SystemExit(not ok)
    print(json.dumps({'sourceSha256':fingerprint(ROOT)},ensure_ascii=False,indent=2))
