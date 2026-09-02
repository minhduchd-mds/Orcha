#!/usr/bin/env python3
from __future__ import annotations

import json, os, re, threading, time, uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('ORCHA_DATA_DIR') or os.environ.get('KIMIK3_DATA_DIR') or str(ROOT/'data')).expanduser()
HUB = DATA/'data-hub'
SOURCES = HUB/'sources.json'
STATE = HUB/'state.json'
DOCS = HUB/'documents'
MAX_BYTES = 5 * 1024 * 1024
MIN_INTERVAL = 15
SUPPORTED = {'json','rss','atom','text'}


def _read(path:Path, default:Any):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def _write(path:Path,obj:Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(path)

def _safe_id(v:str)->str:
    s=''.join(c for c in str(v).strip().lower().replace(' ','-') if c.isalnum() or c in '-_')[:64]
    if not s or s.startswith('.') or '..' in s:raise ValueError('source id không hợp lệ')
    return s

def _safe_url(url:str)->str:
    p=urlparse(str(url).strip())
    if p.scheme not in {'http','https'} or not p.netloc:raise ValueError('Chỉ hỗ trợ URL http/https')
    if len(url)>2048:raise ValueError('URL quá dài')
    return url

def list_sources()->list[dict]:
    return _read(SOURCES,{'sources':[]}).get('sources',[])

def save_source(spec:dict)->dict:
    sid=_safe_id(spec.get('id') or spec.get('name') or ('source-'+uuid.uuid4().hex[:8]))
    kind=str(spec.get('type') or 'json').lower()
    if kind not in SUPPORTED:raise ValueError('Loại source chưa hỗ trợ')
    interval=max(MIN_INTERVAL,min(int(spec.get('interval_minutes') or 60),10080))
    src={'id':sid,'name':str(spec.get('name') or sid)[:120],'type':kind,'url':_safe_url(str(spec.get('url') or '')),
         'enabled':bool(spec.get('enabled',True)),'interval_minutes':interval,
         'headers_env':{str(k)[:80]:str(v)[:120] for k,v in (spec.get('headers_env') or {}).items()},
         'created_at':float(spec.get('created_at') or time.time()),'updated_at':time.time()}
    data=_read(SOURCES,{'version':1,'sources':[]});rows=[x for x in data.get('sources',[]) if x.get('id')!=sid]+[src];data['sources']=rows;_write(SOURCES,data);return src

def set_enabled(sid:str,enabled:bool)->dict:
    sid=_safe_id(sid);rows=list_sources();found=None
    for x in rows:
        if x.get('id')==sid:x['enabled']=bool(enabled);x['updated_at']=time.time();found=x;break
    if not found:raise FileNotFoundError(sid)
    _write(SOURCES,{'version':1,'sources':rows});return found

def _headers(src:dict)->dict:
    out={'User-Agent':'Orcha/7.4 DataHub'}
    for header,envname in (src.get('headers_env') or {}).items():
        val=os.environ.get(str(envname))
        if val:out[str(header)]=val
    return out

def _fetch(src:dict)->tuple[bytes,str]:
    req=Request(src['url'],headers=_headers(src),method='GET')
    with urlopen(req,timeout=15) as r:
        ctype=str(r.headers.get('content-type') or '')[:200]
        raw=r.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('Source vượt giới hạn 5 MB mỗi lần sync')
    return raw,ctype

def _txt(v:Any)->str:
    if v is None:return ''
    if isinstance(v,(dict,list)):return json.dumps(v,ensure_ascii=False)
    return str(v)

def _json_docs(raw:bytes,src:dict)->list[dict]:
    obj=json.loads(raw.decode('utf-8','replace'));rows=obj if isinstance(obj,list) else [obj]
    out=[]
    for i,x in enumerate(rows[:1000]):
        if isinstance(x,dict):title=_txt(x.get('title') or x.get('name') or x.get('id') or f'item {i+1}');text=_txt(x)
        else:title=f'item {i+1}';text=_txt(x)
        out.append({'title':title[:300],'text':text[:20000],'source_url':src['url']})
    return out

def _feed_docs(raw:bytes,src:dict)->list[dict]:
    root=ET.fromstring(raw)
    out=[]
    for node in list(root.findall('.//item'))+list(root.findall('.//{*}entry')):
        def val(name):
            n=node.find(name) or node.find('{*}'+name);return ''.join(n.itertext()).strip() if n is not None else ''
        title=val('title') or 'Untitled';link=val('link');desc=val('description') or val('summary') or val('content')
        out.append({'title':title[:300],'text':desc[:20000],'source_url':link or src['url']})
        if len(out)>=500:break
    return out

def _text_docs(raw:bytes,src:dict)->list[dict]:
    text=raw.decode('utf-8','replace');text=re.sub(r'\x00+','',text)
    return [{'title':src.get('name') or src['id'],'text':text[:200000],'source_url':src['url']}]

def parse(raw:bytes,src:dict)->list[dict]:
    kind=src.get('type')
    if kind=='json':return _json_docs(raw,src)
    if kind in {'rss','atom'}:return _feed_docs(raw,src)
    return _text_docs(raw,src)

def sync_source(sid:str)->dict:
    sid=_safe_id(sid);src=next((x for x in list_sources() if x.get('id')==sid),None)
    if not src:raise FileNotFoundError(sid)
    if not src.get('enabled'):return {'id':sid,'status':'disabled'}
    started=time.time()
    try:
        raw,ctype=_fetch(src);docs=parse(raw,src)
        stamp=int(time.time());folder=DOCS/sid;folder.mkdir(parents=True,exist_ok=True)
        _write(folder/'latest.json',{'source':src,'synced_at':stamp,'content_type':ctype,'documents':docs})
        state=_read(STATE,{});state[sid]={'status':'ok','last_sync':stamp,'documents':len(docs),'duration_ms':round((time.time()-started)*1000)};_write(STATE,state)
        return {'id':sid,**state[sid]}
    except Exception as exc:
        state=_read(STATE,{});state[sid]={'status':'error','last_sync':int(time.time()),'error':str(exc)[:500],'duration_ms':round((time.time()-started)*1000)};_write(STATE,state)
        return {'id':sid,**state[sid]}

def status()->dict:
    state=_read(STATE,{})
    return {'sources':len(list_sources()),'enabled':sum(bool(x.get('enabled')) for x in list_sources()),'state':state,'policy':{'network_read_only':True,'credentials_from_env_only':True,'max_fetch_mb':5,'min_interval_minutes':MIN_INTERVAL}}

def sync_due(now:float|None=None)->list[dict]:
    now=now or time.time();state=_read(STATE,{});out=[]
    for src in list_sources():
        if not src.get('enabled'):continue
        last=float((state.get(src['id']) or {}).get('last_sync') or 0);interval=max(MIN_INTERVAL,int(src.get('interval_minutes') or 60))*60
        if now-last>=interval:out.append(sync_source(src['id']))
    return out

class Scheduler:
    def __init__(self,period_seconds:int=60):self.period=max(30,int(period_seconds));self.stop_event=threading.Event();self.thread=None
    def start(self):
        if self.thread and self.thread.is_alive():return self
        def loop():
            while not self.stop_event.wait(self.period):
                try:sync_due()
                except Exception:pass
        self.thread=threading.Thread(target=loop,name='orcha-data-sync',daemon=True);self.thread.start();return self
    def stop(self):self.stop_event.set()

def self_test():
    sample={'id':'demo','name':'Demo','type':'json','url':'https://example.com/data.json','interval_minutes':1}
    assert _safe_id('Demo Source')=='demo-source';assert save_source(sample)['interval_minutes']==15
    docs=parse(b'[{"title":"A","value":1}]',sample);assert docs and docs[0]['title']=='A'
    assert status()['policy']['credentials_from_env_only']
    print('PASS: Orcha Data Hub')
if __name__=='__main__':self_test()
