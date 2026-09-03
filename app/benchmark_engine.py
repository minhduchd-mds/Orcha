#!/usr/bin/env python3
from __future__ import annotations
import os, time
from pathlib import Path

import kimik3_lite as core
import mcp_gateway as mcp
import skill_runtime as skills
import storage

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('KIMIK3_DATA_DIR',str(ROOT/'data'))).expanduser()
LAST=DATA/'benchmark.json'


def _score_ratio(a,b): return 100 if b<=0 else max(0,min(100,round(a/b*100)))

def run(profile:str='balanced', session_id:str='default')->dict:
    started=time.time(); idx=core.load_index(); mem=core.load_memory(); sk=skills.list_skills(); tools=mcp.list_tools(session_id); servers=mcp.list_servers(False)
    ctx=core.context_status(profile,session_id)
    retrieval=100 if idx else 45
    skill_score=min(100,40+len(sk)*12)
    tool_score=min(100,35+sum(1 for x in tools if x.get('available'))*5)
    safety=100 if all(x.get('decision')=='deny' for x in tools if x.get('permission') in {'shell.execute','system.admin'}) else 60
    memory=60 if mem else 45
    context=min(100,45+round((ctx.get('virtual',{}).get('limit_tokens',0)/1_000_000)*35)+round((ctx.get('native',{}).get('limit_tokens',0)/40960)*20))
    score=round(retrieval*.2+skill_score*.18+tool_score*.18+safety*.18+memory*.1+context*.16)
    result={'score':score,'label':'KII benchmark local','profile':profile,'ts':time.time(),'elapsed_ms':round((time.time()-started)*1000),'metrics':{'retrieval_ready':retrieval,'skills':skill_score,'tooling':tool_score,'safety':safety,'memory':memory,'context':context},'inventory':{'index_chunks':len(idx),'memory_items':len(mem),'skills':len(sk),'tools':len(tools),'servers':len(servers)},'note':'Benchmark năng lực runtime cục bộ; không phải IQ và không thay thế benchmark học thuật của model.'}
    DATA.mkdir(parents=True,exist_ok=True); storage.atomic_json(LAST,result); return result

def last()->dict|None:
    # benchmark.json is a rebuildable projection: quarantine corruption and boot cleanly.
    return storage.read_json_derived(LAST,None)

def self_test():
    r=run(); assert 0<=r['score']<=100 and 'safety' in r['metrics']; print('PASS: benchmark engine')

if __name__=='__main__': self_test()
