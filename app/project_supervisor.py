#!/usr/bin/env python3
from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any

import agent_runtime
import project_workspace as projects

MAX_SAFE_RETRIES=2


def _state_path(pid:str)->Path:
    return projects._p(pid)/'supervisor.json'

def _read(pid:str)->dict:
    p=_state_path(pid)
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return {'project_id':pid,'paused':False,'active_task':None,'runs':[],'updated_at':0}

def _write(pid:str,obj:dict)->dict:
    obj['updated_at']=time.time();projects._write(_state_path(pid),obj);return obj

def status(pid:str)->dict:
    g=projects.get(pid);s=_read(pid)
    pending=[a for a in g.get('approvals',[]) if a.get('status')=='pending']
    return {**s,'ready_count':len(projects.ready_tasks(pid)),'pending_approval_count':len(pending),'progress':{'done':g.get('done_count',0),'total':g.get('task_count',0)},'policy':{'auto_read_only':True,'write_requires_project_approval':True,'permission_engine_authoritative':True,'max_safe_retries':MAX_SAFE_RETRIES}}

def pause(pid:str)->dict:
    s=_read(pid);s['paused']=True;return _write(pid,s)

def resume(pid:str)->dict:
    s=_read(pid);s['paused']=False;return _write(pid,s)

def _approval_for(g:dict,tid:str)->str|None:
    rows=[a for a in g.get('approvals',[]) if a.get('task_id')==tid]
    if any(a.get('status')=='pending' for a in rows):return 'pending'
    if any(a.get('status')=='approved' for a in rows):return 'approved'
    if any(a.get('status')=='rejected' for a in rows):return 'rejected'
    return None

def _ensure_write_approval(pid:str,task:dict)->dict:
    g=projects.get(pid);state=_approval_for(g,task['id'])
    if state=='pending':return {'status':'waiting_approval'}
    if state=='rejected':projects.update_task(pid,task['id'],{'status':'blocked','last_result':'Project approval rejected'});return {'status':'blocked'}
    if state=='approved':
        # Project approval never bypasses tool-level Permission Engine. Keep the task queued for
        # explicit execution so a write side effect cannot be replayed by a background supervisor.
        projects.update_task(pid,task['id'],{'status':'blocked','last_result':'Project approved; explicit execution still required by Permission Engine'})
        return {'status':'permission_gate'}
    projects.request_approval(pid,task['id'],'Supervisor phát hiện task có write-intent. Cần duyệt project trước khi thực thi.',[])
    return {'status':'waiting_approval'}

def _verify_result(result:dict)->dict:
    agent=result.get('agent') if isinstance(result,dict) else None
    answer=str((result or {}).get('answer') or '').strip()
    pending=(agent or {}).get('pending_confirmations') or []
    denied=(agent or {}).get('denied_tools') or []
    ok=bool(answer) and (agent or {}).get('status')=='done' and not pending and not denied
    return {'ok':ok,'answer_chars':len(answer),'pending_permissions':len(pending),'denied_tools':len(denied),'reason':'verified' if ok else 'agent-not-cleanly-complete'}

def _run_read_task(pid:str,task:dict,profile:str,model:str|None,host:str,session_id:str)->dict:
    query=(task.get('title') or '')+'\n'+(task.get('description') or '')+'\nChỉ thực hiện thao tác read-only. Không ghi/sửa/xóa dữ liệu. Trả evidence và kết quả kiểm chứng.'
    last_error=''
    for attempt in range(1,MAX_SAFE_RETRIES+1):
        projects.update_task(pid,task['id'],{'status':'running'})
        try:
            result=agent_runtime.run(query,profile,model,host,'auto',session_id)
            check=_verify_result(result)
            if check['ok']:
                answer=str(result.get('answer') or '')[:12000]
                projects.update_task(pid,task['id'],{'status':'done','last_result':answer})
                projects.checkpoint(pid,f"Supervisor verified task {task['id']} attempt {attempt}")
                return {'status':'done','attempt':attempt,'verification':check,'answer':answer,'agent_run_id':((result.get('agent') or {}).get('run_id'))}
            if (result.get('agent') or {}).get('pending_confirmations'):
                projects.update_task(pid,task['id'],{'status':'waiting_approval','last_result':'Agent requested tool permission; supervisor paused task'})
                return {'status':'waiting_permission','attempt':attempt,'verification':check,'agent':result.get('agent')}
            last_error=check['reason']
        except Exception as exc:
            last_error=str(exc)[:1000]
        if attempt<MAX_SAFE_RETRIES:time.sleep(.05)
    projects.update_task(pid,task['id'],{'status':'blocked','last_result':'Supervisor failed verification: '+last_error})
    return {'status':'blocked','attempt':MAX_SAFE_RETRIES,'error':last_error}

def tick(pid:str,profile:str='balanced',model:str|None=None,host:str='http://127.0.0.1:11434',session_id:str='project-supervisor')->dict:
    s=_read(pid)
    if s.get('paused'):return {'status':'paused','supervisor':status(pid)}
    ready=projects.ready_tasks(pid)
    if not ready:return {'status':'idle','supervisor':status(pid)}
    task=ready[0];s['active_task']=task['id'];_write(pid,s)
    if task.get('write_intent'):
        outcome=_ensure_write_approval(pid,task)
    else:
        outcome=_run_read_task(pid,task,profile,model,host,session_id+'-'+pid)
    s=_read(pid);s['active_task']=None;s.setdefault('runs',[]).append({'id':'sup-'+uuid.uuid4().hex[:10],'task_id':task['id'],'title':task.get('title'),'at':time.time(),**{k:v for k,v in outcome.items() if k not in {'answer','agent'}}});s['runs']=s['runs'][-100:];_write(pid,s)
    return {'task':task,'outcome':outcome,'supervisor':status(pid)}

def run_until_blocked(pid:str,max_steps:int=8,**kwargs)->dict:
    rows=[]
    for _ in range(max(1,min(int(max_steps),20))):
        r=tick(pid,**kwargs);rows.append(r)
        st=r.get('status') or (r.get('outcome') or {}).get('status')
        if st in {'paused','idle','waiting_approval','waiting_permission','permission_gate','blocked'}:break
        if (r.get('outcome') or {}).get('status')!='done':break
    return {'project_id':pid,'steps':rows,'supervisor':status(pid)}

def self_test():
    import tempfile
    old=projects.ROOT
    with tempfile.TemporaryDirectory() as d:
        projects.ROOT=Path(d)
        p=projects.create('Demo','Goal');a=projects.add_task(p['id'],'Read','inspect only');b=projects.add_task(p['id'],'Write','save output',[a['id']],True)
        assert status(p['id'])['ready_count']==1
        pause(p['id']);assert status(p['id'])['paused'];resume(p['id']);assert not status(p['id'])['paused']
        projects.update_task(p['id'],a['id'],{'status':'done'});x=tick(p['id']);assert (x.get('outcome') or {}).get('status')=='waiting_approval'
        assert projects.get(p['id'])['approvals'][0]['task_id']==b['id']
    projects.ROOT=old;print('PASS: project supervisor safety/dependency')
if __name__=='__main__':self_test()
