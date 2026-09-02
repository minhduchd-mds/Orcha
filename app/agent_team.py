#!/usr/bin/env python3
from __future__ import annotations
import storage,json,time,uuid,copy
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor,as_completed
import kimik3_lite as core
import parallel_agent as parallel
RUNS={};DATA=storage.DATA;TEAM_DIR=DATA/'agent-teams'
ROLE_PROMPTS={'research':'Thu thập evidence từ project knowledge và chỉ nêu điều có căn cứ.','specialist':'Phân tích chuyên sâu yêu cầu, tìm rủi ro và đề xuất thực thi.','critic':'Phản biện kết quả trước đó, chỉ ra mâu thuẫn, thiếu sót và giả định yếu.','verifier':'Kiểm tra tính nhất quán, evidence và acceptance criteria trước khi kết luận.','synthesizer':'Tổng hợp kết quả agent thành câu trả lời ngắn gọn, ưu tiên evidence và nêu bất đồng còn lại.'}
def capacity():
    c=parallel.worker_limit();return {**c,'strategy':'dependency-graph','max_team_agents':4,'write_lane':'serial-permission-gated'}
def _budget(workers):
    c=capacity();ram=float(c.get('ram_gb') or 4);per=max(512,min(2048,int(4096/max(1,workers))));return {'workers':workers,'token_budget_per_agent':per,'team_token_budget':per*workers,'ram_gb':ram}
def plan(query,workers=None):
    w=parallel.worker_limit(workers)['workers'];nodes=[{'id':'research','role':'research','name':'Research Agent','depends_on':[],'read_only':True},{'id':'specialist','role':'specialist','name':'Specialist Agent','depends_on':[],'read_only':True},{'id':'critic','role':'critic','name':'Critic Agent','depends_on':['research','specialist'],'read_only':True},{'id':'verifier','role':'verifier','name':'Verifier Agent','depends_on':['research','specialist'],'read_only':True},{'id':'synthesis','role':'synthesizer','name':'Synthesis','depends_on':['critic','verifier'],'read_only':True}]
    if w==1:
        for n in nodes[1:]:n['depends_on']=[nodes[nodes.index(n)-1]['id']]
    return {'id':'team-plan-'+uuid.uuid4().hex[:10],'query':query,'nodes':nodes,'edges':[{'from':d,'to':n['id']} for n in nodes for d in n['depends_on']],'capacity':capacity(),'budget':_budget(w),'policy':'parallel-read-serial-write'}
def _context(query):
    try:return '\n\n'.join(f"[{i+1}] {x.get('path','')}\n{x.get('text','')[:1600]}" for i,x in enumerate(core.retrieve(query,6)))
    except Exception:return ''
def _call(role,query,shared,profile,model,host,budget):
    tag=model or core.profile_config(profile).get('ollama_name');cfg=__import__('model_registry').inference_limits(tag,profile);deps='\n\n'.join(f"{k}: {v.get('output','')}" for k,v in shared.items());ctx=_context(query) if role in {'research','specialist'} else '';prompt=f"ROLE: {ROLE_PROMPTS[role]}\nYÊU CẦU: {query}\nSHARED RESULTS:\n{deps or '(chưa có)'}\nPROJECT EVIDENCE:\n{ctx or '(không có)'}\nTrả lời tiếng Việt, tối đa {budget} tokens. Không tuyên bố đã sửa file/tool.";started=time.time()
    try:out=core.ollama_chat(tag,[{'role':'user','content':prompt}],host,220,.12,min(int(cfg.get('working_context',4096)),4096),num_predict=budget);return {'ok':bool(out.strip()),'output':out,'elapsed_ms':round((time.time()-started)*1000)}
    except Exception as e:return {'ok':False,'output':'','error':str(e),'elapsed_ms':round((time.time()-started)*1000)}
def _resolve_conflicts(shared):return {'count':None,'items':[],'resolution':'See critic and verifier evidence; no automatic conflict score'}
def run(query,profile='balanced',model=None,host='http://127.0.0.1:11434',session_id='default',workers=None):
    p=plan(query,workers);rid='team-'+uuid.uuid4().hex[:12];run={'id':rid,'status':'running','query':query,'plan':p,'nodes':{},'shared_memory':{},'started_at':time.time(),'session_id':session_id};RUNS[rid]=run;pending={n['id']:dict(n,status='pending') for n in p['nodes']};budget=p['budget']['token_budget_per_agent'];max_workers=p['budget']['workers']
    while pending:
        ready=[n for n in pending.values() if all(run['nodes'].get(d,{}).get('status')=='done' for d in n['depends_on'])]
        if not ready:break
        batch=[n for n in ready if n['id']!='synthesis'][:max_workers] or ready[:1]
        with ThreadPoolExecutor(max_workers=max(1,min(max_workers,len(batch)))) as ex:
            fut={ex.submit(copy_context().run,_call,n['role'],query,copy.deepcopy(run['shared_memory']),profile,model,host,budget):n for n in batch}
            for f in as_completed(fut):
                n=fut[f];r=f.result();state={**n,**r,'status':'done' if r.get('ok') else 'error'};run['nodes'][n['id']]=state
                if r.get('ok'):run['shared_memory'][n['id']]={'output':r.get('output','')[:12000]}
                pending.pop(n['id'],None)
        if any(run['nodes'].get(d,{}).get('status')=='error' for n in pending.values() for d in n['depends_on']):
            for nid,n in list(pending.items()):
                if any(run['nodes'].get(d,{}).get('status')=='error' for d in n['depends_on']):run['nodes'][nid]={**n,'status':'blocked','error':'dependency failed'};pending.pop(nid)
    run['conflicts']=_resolve_conflicts(run['shared_memory']);answer=(run['nodes'].get('synthesis') or {}).get('output') or (run['nodes'].get('verifier') or {}).get('output') or (run['nodes'].get('specialist') or {}).get('output') or 'Agent Team chưa tạo được kết quả.'
    for nid,n in pending.items():run['nodes'][nid]={**n,'status':'blocked','error':'dependency incomplete'}
    run['status']='done' if len(run['nodes'])==len(p['nodes']) and all(n.get('status')=='done' for n in run['nodes'].values()) else 'failed';run['elapsed_ms']=round((time.time()-run['started_at'])*1000);TEAM_DIR.mkdir(parents=True,exist_ok=True);storage.atomic_json(TEAM_DIR/f'{rid}.json',run);__import__('self_improvement').record({'strategy':'team','success':run['status']=='done','latency_ms':run['elapsed_ms'],'task_type':__import__('model_registry').classify_task(query)});return {'answer':answer,'team':public(run)}
def public(run):return {'run_id':run['id'],'status':run['status'],'plan':run['plan'],'nodes':run['nodes'],'conflicts':run.get('conflicts',{}),'elapsed_ms':run.get('elapsed_ms',0),'shared_keys':list(run.get('shared_memory',{}))}
def get(run_id):
    r=RUNS.get(run_id)
    if not r and __import__('re').fullmatch(r'team-[a-f0-9]+',run_id):r=storage.read_json(TEAM_DIR/f'{run_id}.json',None)
    return public(r) if r else None
def self_test():
    p=plan('Review UI/UX và code',2);assert len(p['nodes'])==5 and any(e['from']=='research' and e['to']=='critic' for e in p['edges']) and p['policy']=='parallel-read-serial-write' and p['budget']['workers']<=2;print('PASS: agent team graph')
if __name__=='__main__':self_test()
