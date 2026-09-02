#!/usr/bin/env python3
from __future__ import annotations
import json, os, time, uuid
from pathlib import Path
from typing import Any
import kimik3_lite as core

DATA=Path(os.environ.get('KIMIK3_DATA_DIR',str(core.DATA))).expanduser()
ROOT=DATA/'projects-v7'
SAFE_STATUS={'todo','running','waiting_approval','blocked','done','cancelled'}

def _safe_id(v:str)->str:
    s=''.join(c for c in str(v).strip().lower().replace(' ','-') if c.isalnum() or c in '-_')[:64]
    if not s or s.startswith('.') or '..' in s: raise ValueError('project/task id không hợp lệ')
    return s

def _p(pid:str)->Path:return ROOT/_safe_id(pid)
def _meta(pid:str)->Path:return _p(pid)/'project.json'
def _read(path:Path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def _write(path:Path,obj:Any):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def create(name:str,goal:str='',project_id:str|None=None)->dict:
    pid=_safe_id(project_id or name or ('project-'+uuid.uuid4().hex[:8]));path=_meta(pid)
    if path.exists():raise ValueError('Project đã tồn tại')
    now=time.time();obj={'id':pid,'name':name.strip() or pid,'goal':goal.strip(),'status':'active','created_at':now,'updated_at':now,'task_count':0,'done_count':0}
    _write(path,obj);_write(_p(pid)/'tasks.json',[]);_write(_p(pid)/'approvals.json',[]);_write(_p(pid)/'checkpoints.json',[]);return obj

def get(pid:str)->dict:
    obj=_read(_meta(pid),None)
    if not obj:raise FileNotFoundError(pid)
    tasks=_read(_p(pid)/'tasks.json',[]);approvals=_read(_p(pid)/'approvals.json',[]);cps=_read(_p(pid)/'checkpoints.json',[])
    return {**obj,'tasks':tasks,'approvals':approvals,'checkpoints':cps[-20:]}

def list_projects()->list[dict]:
    ROOT.mkdir(parents=True,exist_ok=True);out=[]
    for d in ROOT.iterdir():
        if d.is_dir():
            x=_read(d/'project.json',None)
            if x:out.append(x)
    return sorted(out,key=lambda x:x.get('updated_at',0),reverse=True)

def _sync(pid:str,tasks:list[dict]):
    p=_read(_meta(pid),{});p['task_count']=len(tasks);p['done_count']=sum(t.get('status')=='done' for t in tasks);p['updated_at']=time.time();_write(_meta(pid),p)

def add_task(pid:str,title:str,description:str='',depends_on:list[str]|None=None,write_intent:bool=False)->dict:
    get(pid);tasks=_read(_p(pid)/'tasks.json',[]);tid='task-'+uuid.uuid4().hex[:10];deps=list(dict.fromkeys(depends_on or []));known={t['id'] for t in tasks}
    if any(d not in known for d in deps):raise ValueError('Dependency không tồn tại')
    t={'id':tid,'title':title.strip() or 'Untitled task','description':description.strip(),'status':'todo','depends_on':deps,'write_intent':bool(write_intent),'created_at':time.time(),'updated_at':time.time(),'attempts':0,'last_result':''};tasks.append(t);_write(_p(pid)/'tasks.json',tasks);_sync(pid,tasks);return t

def update_task(pid:str,tid:str,patch:dict)->dict:
    tasks=_read(_p(pid)/'tasks.json',[]);found=None
    for t in tasks:
        if t['id']==tid:
            if 'status' in patch:
                st=str(patch['status']);
                if st not in SAFE_STATUS:raise ValueError('status không hợp lệ')
                t['status']=st
            for k in ('title','description','last_result'):
                if k in patch:t[k]=str(patch[k])[:12000]
            t['updated_at']=time.time();found=t;break
    if not found:raise FileNotFoundError(tid)
    _write(_p(pid)/'tasks.json',tasks);_sync(pid,tasks);return found

def ready_tasks(pid:str)->list[dict]:
    tasks=_read(_p(pid)/'tasks.json',[]);by={t['id']:t for t in tasks};out=[]
    for t in tasks:
        if t['status']!='todo':continue
        if all(by.get(d,{}).get('status')=='done' for d in t.get('depends_on',[])):out.append(t)
    return out

def request_approval(pid:str,tid:str,summary:str,actions:list[dict]|None=None)->dict:
    task=next((t for t in _read(_p(pid)/'tasks.json',[]) if t['id']==tid),None)
    if not task:raise FileNotFoundError(tid)
    arr=_read(_p(pid)/'approvals.json',[]);a={'id':'approval-'+uuid.uuid4().hex[:10],'task_id':tid,'summary':summary[:4000],'actions':actions or [],'status':'pending','created_at':time.time(),'resolved_at':None};arr.append(a);_write(_p(pid)/'approvals.json',arr);update_task(pid,tid,{'status':'waiting_approval'});return a

def resolve_approval(pid:str,aid:str,approved:bool)->dict:
    arr=_read(_p(pid)/'approvals.json',[]);found=None
    for a in arr:
        if a['id']==aid and a['status']=='pending':a['status']='approved' if approved else 'rejected';a['resolved_at']=time.time();found=a;break
    if not found:raise FileNotFoundError(aid)
    _write(_p(pid)/'approvals.json',arr);update_task(pid,found['task_id'],{'status':'todo' if approved else 'blocked'});return found

def checkpoint(pid:str,note:str='')->dict:
    g=get(pid);arr=_read(_p(pid)/'checkpoints.json',[]);cp={'id':'cp-'+uuid.uuid4().hex[:10],'created_at':time.time(),'note':note[:2000],'task_status':{t['id']:t['status'] for t in g['tasks']},'pending_approvals':[a['id'] for a in g['approvals'] if a['status']=='pending']};arr.append(cp);_write(_p(pid)/'checkpoints.json',arr[-100:]);return cp

def resume(pid:str)->dict:
    g=get(pid);return {'project':{k:g[k] for k in ('id','name','goal','status','task_count','done_count')},'ready':ready_tasks(pid),'waiting_approval':[a for a in g['approvals'] if a['status']=='pending'],'last_checkpoint':g['checkpoints'][-1] if g['checkpoints'] else None}

def self_test():
    import tempfile
    global ROOT
    old=ROOT
    with tempfile.TemporaryDirectory() as d:
        ROOT=Path(d);p=create('Demo','Goal');a=add_task(p['id'],'Read');b=add_task(p['id'],'Write',depends_on=[a['id']],write_intent=True);assert len(ready_tasks(p['id']))==1;update_task(p['id'],a['id'],{'status':'done'});assert ready_tasks(p['id'])[0]['id']==b['id'];ap=request_approval(p['id'],b['id'],'Need write');assert resume(p['id'])['waiting_approval'][0]['id']==ap['id'];resolve_approval(p['id'],ap['id'],True);checkpoint(p['id'],'ok');assert get(p['id'])['checkpoints']
    ROOT=old;print('PASS: project workspace')
if __name__=='__main__':self_test()
