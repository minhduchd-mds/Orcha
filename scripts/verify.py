"""Portable isolated verification for desktop CI and local development."""
import argparse
import ast
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def _verify_ui_contract():
    index=(ROOT/'studio/index.html').read_text(encoding='utf-8')
    ui=(ROOT/'studio/ui-foundation.js').read_text(encoding='utf-8')
    css=(ROOT/'studio/ui-foundation.css').read_text(encoding='utf-8')
    skill=(ROOT/'skills/orcha-frontend-design/SKILL.md').read_text(encoding='utf-8')
    contract=(ROOT/'docs/ORCHA-UI-CONTRACT.md').read_text(encoding='utf-8')
    required=('Anh muốn Orcha làm gì?','Orcha cần quyền thực hiện','Orcha · Autonomous Work Platform')
    if not all(x in index for x in required):raise AssertionError('Orcha product copy contract is incomplete')
    if "iconRule:'outline-only'" not in ui or 'fill="none"' not in ui or 'stroke="currentColor"' not in ui:
        raise AssertionError('Outline icon registry contract missing')
    if '--ui-bg:var(--bg)' not in css or '--ui-accent:var(--accent)' not in css:
        raise AssertionError('UI Foundation must inherit canonical Orcha tokens')
    if 'Orcha Visual Baseline' not in skill or 'Claude frontend-design' not in skill or 'Outline only' not in skill:
        raise AssertionError('Mandatory frontend skill hierarchy/rules missing')
    if 'If a Claude-inspired idea would make Orcha look like a different product, reject that idea.' not in contract:
        raise AssertionError('UI contract must keep Claude quality rules subordinate to Orcha baseline')
    print('PASS: Orcha UI contract + outline icon + product copy',flush=True)

def main():
    subprocess.run([sys.executable,str(ROOT/'scripts/check_brand.py')],check=True,cwd=ROOT)
    parser=argparse.ArgumentParser();parser.add_argument('--fast',action='store_true');args=parser.parse_args()
    files=[*ROOT.glob('app/*.py'),*ROOT.glob('mcp_servers/*.py'),*ROOT.glob('scripts/*.py'),*ROOT.glob('tests/*.py')]
    for path in files:ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    print(f'PASS: Python syntax ({len(files)} files)',flush=True)
    node=shutil.which('node')
    if not node:raise RuntimeError('Node.js is required for JavaScript syntax verification')
    scripts=list(ROOT.glob('studio/*.js'))
    for path in scripts:subprocess.run([node,'--check',str(path)],check=True)
    print(f'PASS: JavaScript syntax ({len(scripts)} files)',flush=True)
    _verify_ui_contract()
    logic=(ROOT/'Modelfile.logic-0.8b').read_text(encoding='utf-8');assert 'FROM qwen3.5:0.8b' in logic and 'Orcha Logic 0.8B' in logic
    registry=json.loads((ROOT/'config/models.json').read_text(encoding='utf-8'));assert any(x.get('id')=='logic-08b' for x in registry.get('models',[]))
    if args.fast:return
    with tempfile.TemporaryDirectory(prefix='orcha-verify-') as directory:
        os.environ['ORCHA_DATA_DIR']=directory
        sys.path.insert(0,str(ROOT/'app'))
        count=0
        for path in sorted(ROOT.glob('app/*.py')):
            module=importlib.import_module(path.stem)
            if callable(getattr(module,'self_test',None)):module.self_test();count+=1
        print(f'PASS: {count} module self-tests',flush=True)
        import mcp_transport
        server={'command':'@python','args':['{root}/mcp_servers/computer_server.py']}
        try:
            for _ in range(2):
                result=mcp_transport.call(server,'computer.capabilities',{},5)
                if result.get('isError'):raise RuntimeError(result)
            if len(mcp_transport._CLIENTS)!=1:raise AssertionError('MCP client was not reused')
            print('PASS: persistent MCP capability calls (read-only)',flush=True)
        finally:mcp_transport.close_all()
        subprocess.run([sys.executable,str(ROOT/'tests/test_regressions.py')],check=True,cwd=ROOT)
    print('PASS: complete isolated verification',flush=True)

if __name__=='__main__':main()
