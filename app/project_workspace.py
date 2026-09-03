#!/usr/bin/env python3
from __future__ import annotations
import storage
import json, os, time, uuid
from pathlib import Path
from typing import Any
import orcha_core as core

DATA=storage.DATA
ROOT=DATA/'projects-v7'
SAFE_STATUS={'todo','running','waiting_approval','blocked','done','cancelled'}

def _safe_id(v:str)->str:
    s=''.join(c for c in str(v).strip().lower().replace(' ','-') if c.isalnum() or c in '-_')[:64]
    if not s or s.startswith('.') or '..' in s: raise ValueError('project/task id không hợp lệ')
    return s

def _p(pid:str)->Path:return ROOT/_safe_id(pid)
def _meta(pid:str)->Path:return _p(pid)/'project.json'
def _read(path:Path,default):return storage.read_json(path,default)
def _write(path:Path,obj:Any):storage.atomic_json(path,obj)


@storage.serialized
def create(name:str,goal:str='',project_id:str|None=None)->dict:
    pid=_safe_id(project_id or name or ('project-'+uuid.uuid4().hex[:8]));path=_meta(pid)
    if path.exists():raise ValueError('Project đã tồn tại')
    now=time.time();obj={'id':pid,'name':name.strip() or pid,'goal':goal.strip(),'status':'active','created_at':now,'updated_at':now,'task_count':0,'done_count':0}
    _write(path,obj);_write(_p(pid)/'tasks.json',[]);_write(_p(pid)/'approvals.json',[]);_write(_p(pid)/'checkpoints.json',[]);return obj

@storage.serialized
def get(pid:str)->dict:
    obj=_read(_meta(pid),None)
    if not obj:raise FileNotFoundError(pid)
    tasks=_read(_p(pid)/'tasks.json',[]);approvals=_read(_p(pid)/'approvals.json',[]);cps=_read(_p(pid)/'checkpoints.json',[])
    return {**obj,'task_count':len(tasks),'done_count':sum(t.get('status')=='done' for t in tasks),'tasks':tasks,'approvals':approvals,'checkpoints':cps[-20:]}

@storage.serialized
def list_projects()->list[dict]:
    ROOT.mkdir(parents=True,exist_ok=True);out=[]
    for d in ROOT.iterdir():
        if d.is_dir():
            x=_read(d/'project.json',None)
            if x:out.append(x)
    return sorted(out,key=lambda x:x.get('updated_at',0),reverse=True)

def _sync(pid:str,tasks:list[dict]):
    p=_read(_meta(pid),{});p['task_count']=len(tasks);p['done_count']=sum(t.get('status')=='done' for t in tasks);p['updated_at']=time.time();_write(_meta(pid),p)

@storage.serialized
def add_task(pid:str,title:str,description:str='',depends_on:list[str]|None=None,write_intent:bool=False, planner:dict|None=None)->dict:
    get(pid);tasks=_read(_p(pid)/'tasks.json',[]);tid='task-'+uuid.uuid4().hex[:10];deps=list(dict.fromkeys(depends_on or []));known={t['id'] for t in tasks}
    if any(d not in known for d in deps):raise ValueError('Dependency không tồn tại')
    t={'id':tid,'title':title.strip() or 'Untitled task','description':description.strip(),'status':'todo','depends_on':deps,'write_intent':bool(write_intent),'created_at':time.time(),'updated_at':time.time(),'attempts':0,'last_result':'','planner':planner or {},'agent_run_id':None,'verification':None};tasks.append(t);_write(_p(pid)/'tasks.json',tasks);_sync(pid,tasks);return t

@storage.serialized
def update_task(pid:str,tid:str,patch:dict,verified:bool=False)->dict:
    tasks=_read(_p(pid)/'tasks.json',[]);found=None
    for t in tasks:
        if t['id']==tid:
            if 'status' in patch:
                st=str(patch['status']);
                if st not in SAFE_STATUS:raise ValueError('status không hợp lệ')
                if st == 'done' and not verified: raise ValueError('Task completion requires executor verification')
                if st in {'running','done'}:
                    by={x['id']:x for x in tasks}
                    if any(by.get(d,{}).get('status')!='done' for d in t.get('depends_on',[])): raise ValueError('Dependencies are not complete')
                if t['status'] in {'done','cancelled'} and st!=t['status']: raise ValueError('Terminal task cannot be restarted')
                if st=='running' and t['status']!='running': t['attempts']=int(t.get('attempts',0))+1
                t['status']=st
            if any(k in patch for k in ('title','description')) and t['status']!='todo': raise ValueError('Only queued tasks can be edited')
            for k in ('planner','verification','agent_run_id'):
                if k in patch and verified: t[k]=patch[k]
            if any(k in patch and str(patch[k])!=t.get(k) for k in ('title','description')):
                approvals=_read(_p(pid)/'approvals.json',[])
                for approval in approvals:
                    if approval['task_id']==tid and approval['status'] in {'pending','approved'}:approval['status']='superseded'
                _write(_p(pid)/'approvals.json',approvals)
            for k in ('title','description','last_result'):
                if k in patch:t[k]=str(patch[k])[:12000]
            t['updated_at']=time.time();found=t;break
    if not found:raise FileNotFoundError(tid)
    _write(_p(pid)/'tasks.json',tasks);_sync(pid,tasks);return found

@storage.serialized
def ready_tasks(pid:str)->list[dict]:
    tasks=_read(_p(pid)/'tasks.json',[]);by={t['id']:t for t in tasks};out=[]
    for t in tasks:
        if t['status']!='todo':continue
        if all(by.get(d,{}).get('status')=='done' for d in t.get('depends_on',[])):out.append(t)
    return out

@storage.serialized
def request_approval(pid:str,tid:str,summary:str,actions:list[dict]|None=None)->dict:
    task=next((t for t in _read(_p(pid)/'tasks.json',[]) if t['id']==tid),None)
    if not task:raise FileNotFoundError(tid)
    arr=_read(_p(pid)/'approvals.json',[]);a={'id':'approval-'+uuid.uuid4().hex[:10],'task_id':tid,'summary':summary[:4000],'actions':actions or [],'status':'pending','created_at':time.time(),'resolved_at':None};arr.append(a);_write(_p(pid)/'approvals.json',arr);update_task(pid,tid,{'status':'waiting_approval'});return a

@storage.serialized
def resolve_approval(pid:str,aid:str,approved:bool)->dict:
    arr=_read(_p(pid)/'approvals.json',[]);found=None
    for a in arr:
        if a['id']==aid and a['status']=='pending':a['status']='approved' if approved else 'rejected';a['resolved_at']=time.time();found=a;break
    if not found:raise FileNotFoundError(aid)
    _write(_p(pid)/'approvals.json',arr);update_task(pid,found['task_id'],{'status':'todo' if approved else 'blocked'});return found

@storage.serialized
def checkpoint(pid:str,note:str='')->dict:
    g=get(pid);arr=_read(_p(pid)/'checkpoints.json',[]);cp={'id':'cp-'+uuid.uuid4().hex[:10],'created_at':time.time(),'note':note[:2000],'task_status':{t['id']:t['status'] for t in g['tasks']},'pending_approvals':[a['id'] for a in g['approvals'] if a['status']=='pending']};arr.append(cp);_write(_p(pid)/'checkpoints.json',arr[-100:]);return cp

@storage.serialized
def resume(pid:str)->dict:
    g=get(pid);return {'project':{k:g[k] for k in ('id','name','goal','status','task_count','done_count')},'ready':ready_tasks(pid),'waiting_approval':[a for a in g['approvals'] if a['status']=='pending'],'last_checkpoint':g['checkpoints'][-1] if g['checkpoints'] else None}

@storage.serialized
def recover_incomplete():
    recovered=[]
    for project in list_projects():
        pid=project['id'];tasks=_read(_p(pid)/'tasks.json',[])
        for task in tasks:
            if task['status'] in {'running','waiting_approval'} and (task['status']=='running' or task.get('agent_run_id')):
                task.update(status='blocked',last_result='Interrupted. Review evidence before retrying.',agent_run_id=None)
                recovered.append(task['id'])
        _write(_p(pid)/'tasks.json',tasks);_sync(pid,tasks)
        state=_read(_p(pid)/'supervisor.json',{})
        if state:
            state['active_task']=None;_write(_p(pid)/'supervisor.json',state)
    return recovered

@storage.serialized
def retry_task(pid,tid):
    task=next(t for t in get(pid)['tasks'] if t['id']==tid)
    if task['status']!='blocked':raise ValueError('Only blocked tasks can be retried')
    return update_task(pid,tid,{'status':'todo'})


def self_test():
    import tempfile
    global ROOT
    old=ROOT
    with tempfile.TemporaryDirectory() as d:
        ROOT=Path(d);p=create('Demo','Goal');a=add_task(p['id'],'Read');b=add_task(p['id'],'Write',depends_on=[a['id']],write_intent=True);assert len(ready_tasks(p['id']))==1;update_task(p['id'],a['id'],{'status':'done'},verified=True);assert ready_tasks(p['id'])[0]['id']==b['id'];ap=request_approval(p['id'],b['id'],'Need write');assert resume(p['id'])['waiting_approval'][0]['id']==ap['id'];resolve_approval(p['id'],ap['id'],True);checkpoint(p['id'],'ok');assert get(p['id'])['checkpoints']
    ROOT=old;print('PASS: project workspace')
if __name__=='__main__':self_test()
