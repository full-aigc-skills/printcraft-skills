"""固定原生目录与契约所有者覆盖；新增/移除工具不默认为已覆盖。"""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check(catalog,coverage):
    observed={tool['name'] for tool in catalog};known={item['tool'] for item in coverage['tools']}
    if len(known)!=len(coverage['tools']):raise ValueError('duplicate_coverage_tool')
    return {'status':'PASS' if observed==known else 'GAP','added':sorted(observed-known),'removed':sorted(known-observed),'nativeAcceptance':'PER_TOOL_SEPARATE'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);a=p.parse_args();result=check(json.loads(a.catalog.read_text()),json.loads((ROOT/'docs/tool-coverage.json').read_text()));print(json.dumps(result));raise SystemExit(result['status']!='PASS')
