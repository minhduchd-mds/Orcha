#!/usr/bin/env python3
from __future__ import annotations
import storage
import json, os, time, uuid
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
DATA=storage.DATA
LOG=DATA/'action_timeline.jsonl'


def _ensure(): DATA.mkdir(parents=True,exist_ok=True)

@storage.serialized
def record(kind:str, session_id:str='default', **fields:Any)->dict:
    _ensure(); item={'id':'act-'+uuid.uuid4().hex[:12],'ts':time.time(),'kind':kind,'session_id':session_id,**fields}
    with LOG.open('a',encoding='utf-8') as f: f.write(json.dumps(item,ensure_ascii=False)+'\n')
    return item

def list_events(session_id:str|None=None, limit:int=100)->list[dict]:
    if not LOG.exists(): return []
    out=[]
    for line in LOG.read_text(encoding='utf-8',errors='ignore').splitlines():
        try:
            x=json.loads(line)
            if session_id and x.get('session_id')!=session_id: continue
            out.append(x)
        except Exception: pass
    return out[-max(1,min(limit,500)):]

def find(action_id:str)->dict|None:
    return next((x for x in reversed(list_events(None,500)) if x.get('id')==action_id),None)

def mark_rollback(action_id:str, result:dict, session_id:str='default')->dict:
    return record('rollback',session_id,target_action_id=action_id,result=result,status='done' if result.get('ok') else 'error')

def self_test():
    _ensure(); x=record('test','ci',tool='noop',status='done'); assert find(x['id']); print('PASS: action log')

if __name__=='__main__': self_test()


def rollback(action_id,session_id,approved=False):
    import mcp_gateway as mcp
    import permission_engine as permissions
    with storage.transaction():
        item=find(action_id)
        if not item or item.get('session_id')!=session_id:raise ValueError('Unknown action for session')
        rb=item.get('rollback')
        if not isinstance(rb,dict):raise ValueError('No automatic rollback for this action')
        if not approved:raise ValueError('Explicit rollback confirmation required')
        marker=DATA/'rollback-claims'/f'{action_id}.json'
        if marker.exists():raise ValueError('Rollback already attempted; review the recorded result before another manual operation')
        tool=next(x for x in mcp.list_tools(session_id) if x['name']==rb['tool'])
        key='rollback:'+action_id
        permissions.grant(tool['permission'],'once',60,session_id,key)
        storage.atomic_json(marker,{'status':'running','created_at':time.time()})
    result=mcp.call_tool(rb['tool'],rb.get('arguments',{}),session_id,action_key=key)
    with storage.transaction():
        storage.atomic_json(marker,{'status':'done' if result.get('ok') else 'error','result':result})
        mark_rollback(action_id,result,session_id)
    return result
