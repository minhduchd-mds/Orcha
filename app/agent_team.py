#!/usr/bin/env python3
from __future__ import annotations
import json, os, time, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import kimik3_lite as core
import parallel_agent as parallel

RUNS:dict[str,dict]={}
DATA=Path(os.environ.get('KIMIK3_DATA_DIR',str(core.DATA))).expanduser()
TEAM_DIR=DATA/'agent-teams'

ROLE_PROMPTS={
 'research':'Thu thập evidence từ project knowledge và chỉ nêu điều có căn cứ.',
 'specialist':'Phân tích chuyên sâu yêu cầu, tìm rủi ro và đề xuất thực thi.',
 'critic':'Phản biện kết quả trước đó, chỉ ra mâu thuẫn, thiếu sót và giả định yếu.',
 'verifier':'Kiểm tra tính nhất quán, evidence và acceptance criteria trước khi kết luận.',
 'synthesizer':'Tổng hợp kết quả agent thành câu trả lời ngắn gọn, ưu tiên evidence và nêu bất đồng còn lại.'}

def capacity()->dict:
    c=parallel.worker_limit();return {**c,'strategy':'dependency-graph','max_team_agents':4,'write_lane':'serial-permission-gated'}

def _budget(workers:int)->dict:
    c=capacity();ram=float(c.get('ram_gb') or 4);per=max(512,min(2048,int(4096/max(1,workers))));return {'workers':workers,'token_budget_per_agent':per,'team_token_budget':per*workers,'ram_gb':ram}

def plan(query:str,workers:int|None=None)->dict:
    cap=capacity();w=max(1,min(int(workers or cap.get('workers') or 1),4));nodes=[
      {'id':'research','role':'research','name':'Research Agent','depends_on':[],'read_only':True},
      {'id':'specialist','role':'specialist','name':'Specialist Agent','depends_on':[],'read_only':True},
      {'id':'critic','role':'critic','name':'Critic Agent','depends_on':['research','specialist'],'read_only':True},
      {'id':'verifier','role':'verifier','name':'Verifier Agent','depends_on':['research','specialist'],'read_only':True},
      {'id':'synthesis','role':'synthesizer','name':'Synthesis','depends_on':['critic','verifier'],'read_only':True},
    ];
    if w==1:
        for n in nodes[1:]: n['depends_on']=[nodes[nodes.index(n)-1]['id']]
    return {'id':'team-plan-'+uuid.uuid4().hex[:10],'query':query,'nodes':nodes,'edges':[{'from':d,'to':n['id']} for n in nodes for d in n['depends_on']],'capacity':cap,'budget':_budget(w),'policy':'parallel-read-serial-write'}

def _context(query:str)->str:
    try:
        hits=core.retrieve(query,6);return '\n\n'.join(f"[{i+1}] {x.get('path','')}\n{x.get('text','')[:1600]}" for i,x in enumerate(hits))
    except Exception:return ''

def _call(role:str,query:str,shared:dict,profile:str,model:str|None,host:str,budget:int)->dict:
    cfg=core.profile_config(profile);tag=model or cfg.get('ollama_name');deps='\n\n'.join(f"{k}: {v.get('output','')}" for k,v in shared.items());ctx=_context(query) if role in {'research','specialist'} else ''
    prompt=f"ROLE: {ROLE_PROMPTS[role]}\nYÊU CẦU: {query}\nSHARED RESULTS:\n{deps or '(chưa có)'}\nPROJECT EVIDENCE:\n{ctx or '(không có)'}\nTrả lời tiếng Việt, tối đa {budget} tokens. Không tuyên bố đã sửa file/tool."
    started=time.time()
    try:out=core.ollama_chat(tag,[{'role':'user','content':prompt}],host,budget,.12,min(int(cfg.get('working_context',4096)),4096));return {'ok':True,'output':out,'elapsed_ms':round((time.time()-started)*1000)}
    except Exception as e:return {'ok':False,'output':'','error':str(e),'elapsed_ms':round((time.time()-started)*1000)}

def _resolve_conflicts(shared:dict)->dict:
    texts=[v.get('output','') for k,v in shared.items() if k in {'research','specialist','critic','verifier'} and v.get('output')]
    conflicts=[]
    if len(texts)>=2:
        neg=sum('không ' in t.casefold() or 'chưa ' in t.casefold() for t in texts);pos=sum('nên ' in t.casefold() or 'cần ' in t.casefold() for t in texts)
        if neg and pos:conflicts.append('Có quan điểm/độ chắc chắn khác nhau giữa các agent; ưu tiên Verifier và evidence.')
    return {'count':len(conflicts),'items':conflicts,'resolution':'verifier-evidence-priority'}

def run(query:str,profile:str='balanced',model:str|None=None,host:str='http://127.0.0.1:11434',session_id:str='default',workers:int|None=None)->dict:
    p=plan(query,workers);rid='team-'+uuid.uuid4().hex[:12];run={'id':rid,'status':'running','query':query,'plan':p,'nodes':{},'shared_memory':{},'started_at':time.time(),'session_id':session_id};RUNS[rid]=run
    pending={n['id']:dict(n,status='pending') for n in p['nodes']};budget=p['budget']['token_budget_per_agent'];max_workers=p['budget']['workers']
    while pending:
        ready=[n for n in pending.values() if all(run['nodes'].get(d,{}).get('status')=='done' for d in n['depends_on'])]
        if not ready:break
        batch=[n for n in ready if n['id']!='synthesis'][:max_workers] or ready[:1]
        with ThreadPoolExecutor(max_workers=max(1,min(max_workers,len(batch)))) as ex:
            fut={ex.submit(_call,n['role'],query,run['shared_memory'],profile,model,host,budget):n for n in batch}
            for f in as_completed(fut):
                n=fut[f];r=f.result();state={**n,**r,'status':'done' if r.get('ok') else 'error'};run['nodes'][n['id']]=state
                if r.get('ok'):run['shared_memory'][n['id']]={'output':r.get('output','')[:12000]}
                pending.pop(n['id'],None)
        if any(run['nodes'].get(d,{}).get('status')=='error' for n in pending.values() for d in n['depends_on']):
            for nid,n in list(pending.items()):
                if any(run['nodes'].get(d,{}).get('status')=='error' for d in n['depends_on']):run['nodes'][nid]={**n,'status':'blocked','error':'dependency failed'};pending.pop(nid)
    conflicts=_resolve_conflicts(run['shared_memory']);run['conflicts']=conflicts
    answer=(run['nodes'].get('synthesis') or {}).get('output') or (run['nodes'].get('verifier') or {}).get('output') or (run['nodes'].get('specialist') or {}).get('output') or 'Agent Team chưa tạo được kết quả.'
    run['status']='done';run['elapsed_ms']=round((time.time()-run['started_at'])*1000);TEAM_DIR.mkdir(parents=True,exist_ok=True);(TEAM_DIR/f'{rid}.json').write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8');return {'answer':answer,'team':public(run)}

def public(run:dict)->dict:
    return {'run_id':run['id'],'status':run['status'],'plan':run['plan'],'nodes':run['nodes'],'conflicts':run.get('conflicts',{}),'elapsed_ms':run.get('elapsed_ms',0),'shared_keys':list(run.get('shared_memory',{}))}

def get(run_id:str)->dict|None:
    r=RUNS.get(run_id);return public(r) if r else None

def self_test():
    p=plan('Review UI/UX và code',2);assert len(p['nodes'])==5;assert any(e['from']=='research' and e['to']=='critic' for e in p['edges']);assert p['policy']=='parallel-read-serial-write';assert p['budget']['workers']<=2;print('PASS: agent team graph')
if __name__=='__main__':self_test()
