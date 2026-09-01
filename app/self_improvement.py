#!/usr/bin/env python3
from __future__ import annotations
import json, os, time, uuid
from collections import defaultdict
from pathlib import Path

DATA=Path(os.environ.get('KIMIK3_DATA_DIR',str(Path(__file__).resolve().parents[1]/'data'))).expanduser()
DIR=DATA/'learning';EVENTS=DIR/'outcomes.jsonl';STATE=DIR/'strategy_scores.json';LESSONS=DIR/'lessons.jsonl'
STRATEGIES=('single','parallel','team')

def _read_json(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def _write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def scores()->dict:
    s=_read_json(STATE,{})
    for k in STRATEGIES:s.setdefault(k,{'score':50.0,'runs':0,'success':0,'avg_latency_ms':0.0,'updated_at':0})
    return s

def _safe_strategy(v):return v if v in STRATEGIES else 'single'

def record(payload:dict)->dict:
    strategy=_safe_strategy(str(payload.get('strategy') or 'single'));success=bool(payload.get('success'));rating=max(0,min(5,int(payload.get('rating') or (5 if success else 1))));lat=max(0,int(payload.get('latency_ms') or 0));task_type=str(payload.get('task_type') or 'general')[:80];note=str(payload.get('note') or '')[:1200]
    event={'id':'out-'+uuid.uuid4().hex[:12],'ts':time.time(),'strategy':strategy,'success':success,'rating':rating,'latency_ms':lat,'task_type':task_type,'note':note}
    DIR.mkdir(parents=True,exist_ok=True)
    with EVENTS.open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    s=scores();x=s[strategy];old_runs=int(x['runs']);new_runs=old_runs+1;x['runs']=new_runs;x['success']=int(x['success'])+(1 if success else 0);x['avg_latency_ms']=round(((float(x['avg_latency_ms'])*old_runs)+lat)/new_runs,1);target=(rating/5)*100;alpha=.18;x['score']=round(max(0,min(100,float(x['score'])*(1-alpha)+target*alpha)),1);x['updated_at']=event['ts'];_write_json(STATE,s)
    if note or not success:
        lesson={'id':'lesson-'+uuid.uuid4().hex[:10],'ts':event['ts'],'task_type':task_type,'strategy':strategy,'lesson':note or 'Tác vụ không thành công; ưu tiên verification và giảm độ phức tạp ở lần tương tự.','source_event':event['id']}
        with LESSONS.open('a',encoding='utf-8') as f:f.write(json.dumps(lesson,ensure_ascii=False)+'\n')
    return {'event':event,'scores':s}

def recent_lessons(limit:int=30)->list[dict]:
    if not LESSONS.exists():return []
    out=[]
    for line in LESSONS.read_text(encoding='utf-8',errors='ignore').splitlines()[-max(1,min(limit,200)):]:
        try:out.append(json.loads(line))
        except Exception:pass
    return list(reversed(out))

def recommend(task_type:str='general',ram_gb:float=4)->dict:
    s=scores();allowed=['single']
    if ram_gb>=3.5:allowed.append('parallel')
    if ram_gb>=4:allowed.append('team')
    ranked=sorted(allowed,key=lambda k:(s[k]['score'],s[k]['runs']),reverse=True);selected=ranked[0]
    if s[selected]['runs']<3:selected='team' if 'team' in allowed else ('parallel' if 'parallel' in allowed else 'single')
    return {'selected':selected,'allowed':allowed,'reason':'local performance score + RAM guard','scores':{k:s[k] for k in allowed},'task_type':task_type}

def dashboard()->dict:
    s=scores();events=[]
    if EVENTS.exists():
        for line in EVENTS.read_text(encoding='utf-8',errors='ignore').splitlines()[-100:]:
            try:events.append(json.loads(line))
            except Exception:pass
    total=len(events);success=sum(1 for e in events if e.get('success'));avg=round(sum(int(e.get('latency_ms') or 0) for e in events)/total,1) if total else 0
    return {'scoreboard':s,'recent_runs':total,'success_rate':round(success*100/total,1) if total else 0,'avg_latency_ms':avg,'lessons':recent_lessons(12),'safety':{'self_modify_code':False,'auto_permission_escalation':False,'red_tools_auto_run':False}}

def self_test():
    s=scores();assert set(STRATEGIES)<=set(s);r=recommend('test',4);assert r['selected'] in STRATEGIES;d=dashboard();assert d['safety']['self_modify_code'] is False;print('PASS: safe self improvement')
if __name__=='__main__':self_test()
