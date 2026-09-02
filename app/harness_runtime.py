#!/usr/bin/env python3
from __future__ import annotations
import storage
import hashlib,json,re,threading,time,uuid
from pathlib import Path
from typing import Any,Callable

ROOT=Path(__file__).resolve().parents[1];DATA=storage.DATA;STORE=DATA/'harness';SESSIONS=STORE/'sessions';RUNS=STORE/'runs';RESPONSES=STORE/'responses';SPILL=STORE/'spill'
_LOCK=threading.RLock();_SAFE=re.compile(r'[^a-zA-Z0-9._-]+');_REQUEST_ID=re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$');TRANSIENT_MARKERS=('timed out','timeout','temporarily unavailable','connection reset','connection refused','503','502','429')
# Inspired by DeepSeek Harness architecture concepts. Independent Orcha implementation.
def _ensure():
    for p in (STORE,SESSIONS,RUNS,RESPONSES,SPILL,STORE/'requests'):p.mkdir(parents=True,exist_ok=True)
def _safe(value,fallback='default',limit=100):
    out=_SAFE.sub('-',str(value or fallback)).strip('-._')[:limit];return (out or fallback)+('-'+hashlib.sha256(str(value).encode()).hexdigest()[:12] if str(value)!=out else '')
def _atomic_json(path,value):storage.atomic_json(path,value)
def request_id(value=None):
    raw=str(value or '').strip()
    if not raw:return 'req-'+uuid.uuid4().hex
    if not _REQUEST_ID.fullmatch(raw):raise ValueError('request_id không hợp lệ; dùng 1-128 ký tự a-z/A-Z/0-9/._:-')
    return raw
def _session_path(session_id):_ensure();return SESSIONS/f'{_safe(session_id)}.jsonl'
def _tail_rows(path,limit=200):
    if not path.exists():return []
    limit=max(1,min(int(limit or 200),1000))
    try:
        size=path.stat().st_size
        with path.open('rb') as f:f.seek(max(0,size-2*1024*1024));raw=f.read().decode('utf-8',errors='ignore')
        lines=raw.splitlines();lines=lines[1:] if size>2*1024*1024 and lines else lines
    except OSError:return []
    out=[]
    for line in lines[-limit:]:
        try:
            item=json.loads(line)
            if isinstance(item,dict):out.append(item)
        except Exception:continue
    return out
def events(session_id,limit=200):return _tail_rows(_session_path(session_id),limit)
@storage.serialized
def append_event(session_id,event_type,data=None,run_id=None):
    if not event_type or len(event_type)>80:raise ValueError('event_type không hợp lệ')
    data=dict(data or {});json.dumps(data,ensure_ascii=False)
    with _LOCK:
        p=_session_path(session_id);tail=_tail_rows(p,1);seq=int(tail[-1].get('seq',-1))+1 if tail else 0;row={'seq':seq,'time':time.time(),'type':event_type,'run_id':str(run_id or '') or None,'data':data}
        with p.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n');f.flush()
        return row
def _run_path(run_id):_ensure();return RUNS/f'{_safe(run_id,"run")}.json'
def _response_key(session_id,rid):
    canonical_session=_safe(session_id);key=hashlib.sha256((canonical_session+'\0'+rid).encode('utf-8')).hexdigest();return RESPONSES/f'{key}.json'
@storage.serialized
def reserve_request(session_id,rid,payload):
    _ensure();fingerprint=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest();p=STORE/'requests'/(_response_key(session_id,rid).stem+'.json');previous=storage.read_json(p,None)
    if previous:
        if previous['fingerprint']!=fingerprint:raise ValueError('request_id already used with a different payload')
        cached=cached_response(session_id,rid)
        if cached:return cached
        raise ValueError('Request already running or interrupted; review its result before creating a new request')
    storage.atomic_json(p,{'fingerprint':fingerprint,'created_at':time.time()});return None
@storage.serialized
def begin(session_id,rid,query,route=None):
    rid=request_id(rid);run_id='run-'+uuid.uuid4().hex[:16];row={'id':run_id,'session_id':str(session_id),'request_id':rid,'status':'running','started_at':time.time(),'updated_at':time.time(),'query_preview':str(query or '')[:1000],'route':dict(route or {}),'step':0,'error':None}
    with _LOCK:_atomic_json(_run_path(run_id),row);append_event(session_id,'turn/start',{'request_id':rid,'query':str(query or '')[:12000]},run_id)
    return row
@storage.serialized
def checkpoint(run,event_type,data=None):
    run=dict(run);run['updated_at']=time.time();run['step']=int(run.get('step') or 0)+1 if event_type=='step/start' else run.get('step',0)
    with _LOCK:_atomic_json(_run_path(str(run['id'])),run);append_event(str(run.get('session_id') or 'default'),event_type,data or {},str(run['id']))
    return run
@storage.serialized
def cache_response(session_id,rid,response):
    rid=request_id(rid)
    with _LOCK:_atomic_json(_response_key(session_id,rid),{'session_id':str(session_id),'request_id':rid,'response':response,'time':time.time()})
def cached_response(session_id,rid):
    raw=str(rid or '').strip()
    if not raw or not _REQUEST_ID.fullmatch(raw):return None
    try:
        obj=json.loads(_response_key(session_id,raw).read_text(encoding='utf-8'));return obj.get('response') if isinstance(obj.get('response'),dict) else None
    except Exception:return None
@storage.serialized
def finish(run,response):
    run=dict(run);run['status']='waiting_permission' if response.get('agent',{}).get('status')=='waiting_permission' else ('done' if response.get('agent',{}).get('status','done')=='done' else 'error');run['updated_at']=time.time()
    if run['status']!='waiting_permission':run['ended_at']=run['updated_at']
    with _LOCK:
        _atomic_json(_run_path(str(run['id'])),run);append_event(str(run.get('session_id') or 'default'),'assistant/message',{'answer':str(response.get('answer') or '')[:24000]},str(run['id']));append_event(str(run.get('session_id') or 'default'),'turn/wait' if run['status']=='waiting_permission' else 'turn/end',{'reason':{'kind':run['status']}},str(run['id']));cache_response(str(run.get('session_id') or 'default'),str(run.get('request_id') or ''),response)
    return run
@storage.serialized
def fail(run,error):
    run=dict(run);run['status']='error';run['updated_at']=time.time();run['ended_at']=run['updated_at'];run['error']={'kind':classify_error(error),'message':str(error)[:2000]}
    with _LOCK:_atomic_json(_run_path(str(run['id'])),run);append_event(str(run.get('session_id') or 'default'),'request/error',run['error'],str(run['id']));append_event(str(run.get('session_id') or 'default'),'turn/end',{'reason':{'kind':'failed','error':run['error']['kind']}},str(run['id']))
    return run
@storage.serialized
def recover_incomplete(limit=500):
    _ensure();recovered=[]
    with _LOCK:
        for p in RUNS.glob('run-*.json'):
            try:row=json.loads(p.read_text(encoding='utf-8'))
            except Exception:continue
            if row.get('status') in {'running','waiting_permission'}:
                row['status']='interrupted';row['updated_at']=time.time();row['ended_at']=row['updated_at'];row['error']={'kind':'interrupted','message':'Runtime restarted before turn/end'};_atomic_json(p,row);append_event(str(row.get('session_id') or 'default'),'turn/end',{'reason':{'kind':'interrupted'}},str(row.get('id') or ''));recovered.append(row)
    return recovered
def runs(limit=50):
    _ensure();out=[]
    for p in RUNS.glob('run-*.json'):
        try:
            row=json.loads(p.read_text(encoding='utf-8'))
            if isinstance(row,dict):out.append(row)
        except Exception:continue
    out.sort(key=lambda x:float(x.get('updated_at') or 0),reverse=True);return out[:max(1,min(int(limit or 50),500))]
def classify_error(error):
    text=str(error).casefold()
    if any(x in text for x in ('permission','denied','forbidden','unauthorized')):return 'permission'
    if any(x in text for x in ('invalid','validation','missing','thiếu','không hợp lệ')):return 'validation'
    if any(x in text for x in TRANSIENT_MARKERS):return 'transient'
    if any(x in text for x in ('cancel','abort')):return 'cancelled'
    return 'runtime'
def retryable(error):return classify_error(error)=='transient'
def call_with_retry(fn,attempts=2,base_delay=.2):
    attempts=max(1,min(int(attempts or 1),3));last=None
    for i in range(attempts):
        try:return fn()
        except BaseException as exc:
            last=exc
            if i+1>=attempts or not retryable(exc):raise
            time.sleep(min(1.0,max(0.0,base_delay)*(2**i)))
    raise last or RuntimeError('retry loop ended unexpectedly')
def action_signature(name,arguments=None):return hashlib.sha256(json.dumps({'name':str(name),'arguments':arguments or {}},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:20]
def repeated_action(actions,name,arguments=None,max_repeat=2):
    sig=action_signature(name,arguments);return sum(action_signature(str(x.get('tool') or ''),x.get('arguments') if isinstance(x.get('arguments'),dict) else {})==sig for x in actions)>=max(1,int(max_repeat))
def normalize_tool_result(run_id,call_id,value,limit=12000):
    try:safe_value=value;raw=json.dumps(safe_value,ensure_ascii=False,sort_keys=True)
    except Exception:safe_value={'repr':repr(value)[:4000],'non_json':True};raw=json.dumps(safe_value,ensure_ascii=False,sort_keys=True)
    if len(raw)<=max(1000,int(limit)):return {'spilled':False,'value':safe_value}
    folder=SPILL/_safe(run_id,'run');folder.mkdir(parents=True,exist_ok=True);p=folder/f'{_safe(call_id,"call")}.json';storage.atomic_text(p,raw);keep=max(500,int(limit)//4);return {'spilled':True,'path':str(p),'chars':len(raw),'preview':raw[:keep]+'\n…[tool result spilled to disk]…\n'+raw[-keep:]}
class CapabilityRegistry:
    def __init__(self):self._items={};self._hooks={};self._lock=threading.RLock()
    def register(self,name,provider):
        key=str(name or '').strip()
        if not key:raise ValueError('capability name trống')
        with self._lock:
            if key in self._items:raise ValueError('capability đã tồn tại: '+key)
            self._items[key]=provider
        def dispose():
            with self._lock:
                if self._items.get(key) is provider:self._items.pop(key,None)
        return dispose
    def get(self,name):return self._items.get(str(name))
    def hook(self,event,fn):
        key=str(event or '').strip()
        with self._lock:self._hooks.setdefault(key,[]).append(fn)
        def dispose():
            with self._lock:
                rows=self._hooks.get(key,[])
                if fn in rows:rows.remove(fn)
        return dispose
    def emit(self,event,payload):
        value=payload
        for fn in list(self._hooks.get(str(event),[])):value=fn(value)
        return value
CAPABILITIES=CapabilityRegistry()
def status():
    _ensure();return {'version':1,'architecture':'event-sourced-lightweight-harness','source_inspiration':'DeepSeek Harness architecture/docs; independent implementation','features':{'append_only_events':True,'run_checkpoints':True,'crash_recovery':True,'request_idempotency':True,'bounded_hot_reads':True,'tool_result_spill':True,'transient_retry':True,'stall_guard':True,'capability_seams':True},'safety':{'external_plugin_code_auto_load':False,'permission_engine_remains_authority':True,'model_generated_shell':False},'runs':len(list(RUNS.glob('run-*.json')))}
def self_test():
    assert request_id('abc-1')=='abc-1'
    try:request_id('../bad id');raise AssertionError('invalid request id accepted')
    except ValueError:pass
    assert _response_key('a/b','r')!=_response_key('a-b','r');assert repeated_action([{'tool':'a','arguments':{'x':1}},{'tool':'a','arguments':{'x':1}}],'a',{'x':1});assert classify_error('connection refused')=='transient';assert classify_error('permission denied')=='permission';normalized=normalize_tool_result('self-test','non-json',object());assert not normalized['spilled'] and normalized['value'].get('non_json');r=CapabilityRegistry();dispose=r.register('x',1);assert r.get('x')==1;dispose();assert r.get('x') is None;print('PASS: harness event/idempotency/retry/stall/capability contracts')
if __name__=='__main__':self_test()
@storage.serialized
def bind_agent(run,agent):agent['harness_run_id']=run['id'];run['agent_run_id']=agent['id'];_atomic_json(_run_path(run['id']),run)
@storage.serialized
def refresh_agent_response(run_id,response):
    run=storage.read_json(_run_path(run_id),None)
    if not run:return
    prior=cached_response(run['session_id'],run['request_id']) or {};return finish(run,{**prior,**response})
