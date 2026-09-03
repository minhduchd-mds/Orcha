"""Project execution: atomic claims, explicit writes, durable evidence and recovery."""
from __future__ import annotations
import json
import time
import uuid
import storage
import agent_runtime
import project_workspace as projects

MAX_SAFE_RETRIES=2

def _state_path(pid):return projects._p(pid)/'supervisor.json'
def _read(pid):return storage.read_json(_state_path(pid),{'project_id':pid,'paused':False,'active_task':None,'runs':[]})
def _write(pid,obj):obj['updated_at']=time.time();storage.atomic_json(_state_path(pid),obj);return obj

@storage.serialized
def status(pid):
    g=projects.get(pid);s=_read(pid)
    return {**s,'ready_count':len(projects.ready_tasks(pid)),'pending_approval_count':sum(a['status']=='pending' for a in g['approvals']),
            'progress':{'done':g['done_count'],'total':g['task_count']},'policy':{'auto_read_only':True,'permission_engine_authoritative':True}}

@storage.serialized
def pause(pid):
    s=_read(pid);s['paused']=True
    if s.get('active_task'):
        task=next((t for t in projects.get(pid)['tasks'] if t['id']==s['active_task']),{})
        run=agent_runtime.RUNS.get(task.get('agent_run_id'))
        if run:agent_runtime.cancel_run(run['id'],run['session_id'])
    return _write(pid,s)

@storage.serialized
def resume(pid):s=_read(pid);s['paused']=False;return _write(pid,s)

def _approval_for(g,tid):
    rows=[a for a in g['approvals'] if a['task_id']==tid]
    return rows[-1]['status'] if rows else None

def _verify_result(result,write=False):
    agent=result.get('agent') or {};obs=agent.get('observations') or []
    valid=bool(str(result.get('answer') or '').strip()) and agent.get('status')=='done'
    clean=not agent.get('pending_confirmations') and not agent.get('denied_tools') and all(x.get('ok') for x in obs)
    import mcp_gateway
    tools={x['name']:x for x in mcp_gateway.list_tools()}
    writes=[x for x in obs if x.get('ok') and tools.get(x.get('tool'),{}).get('permission') not in mcp_gateway.READ_PERMISSIONS]
    evidence=bool(result.get('sources')) or any(x.get('ok') and x.get('tool')!='context.stats' and x.get('result') for x in obs)
    ok=bool(valid and clean and evidence and (not write or writes))
    return {'ok':ok,'reason':'verified' if ok else 'Missing successful evidence or incomplete execution','observations':len(obs),'write_observations':len(writes)}

@storage.serialized
def _claim(pid,tid=None,explicit=False):
    g=projects.get(pid);s=_read(pid)
    if s.get('paused'):return None,{'status':'paused'}
    if s.get('active_task'):return None,{'status':'busy'}
    task=next((x for x in (g['tasks'] if tid else projects.ready_tasks(pid)) if not tid or x['id']==tid),None)
    if not task:return None,{'status':'idle'}
    if task['status'] not in {'todo','waiting_approval'}:raise ValueError('Task is not executable')
    if task.get('write_intent'):
        approved=_approval_for(g,task['id'])
        if approved!='approved':
            if approved!='pending':projects.request_approval(pid,task['id'],'Review this write task before explicit execution: '+task['title'])
            return None,{'status':'waiting_approval'}
        if not explicit:return None,{'status':'permission_gate'}
    if task.get('agent_run_id'):raise ValueError('Continue the existing agent run')
    projects.update_task(pid,task['id'],{'status':'running'})
    s['active_task']=task['id'];_write(pid,s)
    return task,None

def _query(pid,task):
    g=projects.get(pid);deps=[{'title':t['title'],'result':t.get('last_result','')[:4000]} for t in g['tasks'] if t['id'] in task.get('depends_on',[])]
    return json.dumps({'project_goal':g['goal'],'task':task['title'],'instruction':task['description'],
                      'acceptance':task.get('planner',{}).get('acceptance',[]),'dependency_results':deps},ensure_ascii=False)

@storage.serialized
def _record(pid,task,result):
    check=_verify_result(result,task.get('write_intent',False));agent=result.get('agent') or {}
    waiting=bool(agent.get('pending_confirmations'))
    state='done' if check['ok'] else ('waiting_approval' if waiting else 'blocked')
    answer=str(result.get('answer') or agent.get('error') or check['reason'])[:12000]
    projects.update_task(pid,task['id'],{'status':state,'last_result':answer,'verification':check,
                        'agent_run_id':agent.get('run_id') if waiting else None},verified=True)
    storage.atomic_json(projects._p(pid)/'artifacts'/f"{task['id']}.json",{'task_id':task['id'],'result':result,'verification':check})
    s=_read(pid);s['active_task']=None;s.setdefault('runs',[]).append({'id':'sup-'+uuid.uuid4().hex[:10],'task_id':task['id'],'title':task['title'],'at':time.time(),'status':state,'verification':check});s['runs']=s['runs'][-100:];_write(pid,s)
    projects.checkpoint(pid,'Execution '+state+': '+task['title'])
    return {'status':'waiting_permission' if waiting else state,'verification':check,'answer':answer,'agent':agent}

def _execute_scoped(pid,tid=None,explicit=False,profile='balanced',model=None,host='http://127.0.0.1:11434',session_id='project-supervisor'):
    task,early=_claim(pid,tid,explicit)
    if early:return {**early,'supervisor':status(pid)}
    sid='project-'+pid+'-'+task['id'];meta=task.get('planner') or {}
    core=__import__('orcha_core');budget_token=core._WORKING_LIMIT.set(meta.get('working_context'))
    try:
        import model_registry
        try:route=model_registry.route(task['title']+' '+task['description'],False,str(meta.get('model_id') or 'auto'),host=host)
        except ValueError:route=model_registry.route(task['title']+' '+task['description'],False,'auto',host=host)
        selected=route.get('selected') or {};model=model or model_registry.runtime_model(selected,False).get('model')
        query=_query(pid,task)
        strategy=meta.get('strategy','single') if not task.get('write_intent') else 'single'
        if strategy in {'team','parallel'}:
            import agent_team,parallel_agent
            raw=(agent_team.run if strategy=='team' else parallel_agent.run)(query,profile,model,host,sid)
            runtime=raw.get('team') or raw
            result={'answer':raw.get('answer'),'sources':__import__('orcha_core').retrieve(query,6),
                    'agent':{'status':runtime.get('status'),'observations':[]},'strategy':strategy}
        else:
            result=agent_runtime.run(query,profile,model,host,'auto',sid,read_only=not task.get('write_intent'),skill_id=meta.get('skill_id'),on_start=lambda run:projects.update_task(pid,task['id'],{'agent_run_id':run['id']},verified=True))
    except Exception as exc:result={'answer':'','agent':{'status':'failed','error':str(exc)}}
    finally:core._WORKING_LIMIT.reset(budget_token)
    if 'route' in locals():result['model_route']={**route,'planner_model':meta.get('model_id')}
    if _read(pid).get('paused') and result.get('agent',{}).get('status')=='done':result['agent']['status']='cancelled'
    outcome=_record(pid,task,result)
    return {'task':task,'outcome':outcome,'supervisor':status(pid)}

def execute(pid,*args,**kwargs):
    import orcha_core as core
    with core.project_scope(pid):return _execute_scoped(pid,*args,**kwargs)


def tick(pid,**kwargs):return execute(pid,**kwargs)

def continue_task(pid,tid,scope='once',approved=True):
    with storage.transaction():
        g=projects.get(pid);task=next(x for x in g['tasks'] if x['id']==tid)
        if _read(pid).get('active_task'):raise ValueError('Project already executing')
        if _read(pid).get('paused'):raise ValueError('Project is paused')
        rid=task.get('agent_run_id');run=agent_runtime.RUNS.get(rid)
        if not run:raise ValueError('Run interrupted; review and retry task')
        if not approved:
            result={'answer':'Action rejected','agent':agent_runtime.cancel_run(rid,run['session_id'])}
            return _record(pid,task,result)
        agent_runtime.grant_action(rid,run['session_id'],scope)
        s=_read(pid);s['active_task']=tid;_write(pid,s)
    try:
        with __import__('orcha_core').project_scope(pid):result=agent_runtime.continue_run(rid,run['session_id'])
    except Exception as exc:result={'agent':{'status':'failed','error':str(exc)}}
    return _record(pid,task,result)

def run_until_blocked(pid,max_steps=8,**kwargs):
    rows=[]
    for _ in range(max(1,min(int(max_steps),20))):
        result=tick(pid,**kwargs);rows.append(result)
        if result.get('outcome',{}).get('status')!='done':break
    return {'project_id':pid,'steps':rows,'supervisor':status(pid)}

def self_test():
    assert not _verify_result({'answer':'failed','agent':{'status':'done','observations':[{'ok':False}]}})['ok']
    print('PASS: supervisor evidence gate')
if __name__=='__main__':self_test()
