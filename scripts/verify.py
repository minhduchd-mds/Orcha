"""Portable isolated verification for desktop CI and local development."""
import argparse
import ast
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fast',action='store_true');args=parser.parse_args()
    files=[*ROOT.glob('app/*.py'),*ROOT.glob('mcp_servers/*.py'),*ROOT.glob('scripts/*.py'),*ROOT.glob('tests/*.py')]
    for path in files:ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    print(f'PASS: Python syntax ({len(files)} files)',flush=True)
    node=shutil.which('node')
    if not node:raise RuntimeError('Node.js is required for JavaScript syntax verification')
    scripts=list(ROOT.glob('studio/*.js'))
    for path in scripts:subprocess.run([node,'--check',str(path)],check=True)
    print(f'PASS: JavaScript syntax ({len(scripts)} files)',flush=True)
    if args.fast:return
    with tempfile.TemporaryDirectory(prefix='orcha-verify-') as directory:
        os.environ['ORCHA_DATA_DIR']=directory;os.environ['KIMIK3_DATA_DIR']=directory
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
