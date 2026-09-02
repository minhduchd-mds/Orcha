#!/usr/bin/env python3
from __future__ import annotations
import storage
import json,os,re,threading,time,uuid,socket,ipaddress,http.client,hashlib
from urllib.parse import urljoin,urlparse
from xml.etree import ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=storage.DATA;HUB=DATA/'data-hub';SOURCES=HUB/'sources.json';STATE=HUB/'state.json';DOCS=HUB/'documents';MAX_BYTES=5*1024*1024;MIN_INTERVAL=15;SUPPORTED={'json','rss','atom','text'};_SYNC_LOCKS={};_LOCK=threading.Lock()
def _read(path,default):return storage.read_json(path,default)
def _write(path,obj):storage.atomic_json(path,obj)
def _safe_id(v):
    s=''.join(c for c in str(v).strip().lower().replace(' ','-') if c.isalnum() or c in '-_')[:64]
    if not s or s.startswith('.') or '..' in s:raise ValueError('source id không hợp lệ')
    return s
def _safe_url(url):
    p=urlparse(str(url).strip())
    if p.scheme not in {'http','https'} or not p.netloc:raise ValueError('Chỉ hỗ trợ URL http/https')
    if p.username or p.password:raise ValueError('Do not put credentials in URLs')
    if len(url)>2048:raise ValueError('URL quá dài')
    return url
def list_sources():return _read(SOURCES,{'sources':[]}).get('sources',[])
@storage.serialized
def save_source(spec):
    sid=_safe_id(spec.get('id') or spec.get('name') or ('source-'+uuid.uuid4().hex[:8]));kind=str(spec.get('type') or 'json').lower()
    if kind not in SUPPORTED:raise ValueError('Loại source chưa hỗ trợ')
    interval=max(MIN_INTERVAL,min(int(spec.get('interval_minutes') or 60),10080));src={'id':sid,'name':str(spec.get('name') or sid)[:120],'type':kind,'url':_safe_url(str(spec.get('url') or '')),'enabled':bool(spec.get('enabled',True)),'interval_minutes':interval,'headers_env':{str(k)[:80]:str(v)[:120] for k,v in (spec.get('headers_env') or {}).items()},'project_id':spec.get('project_id'),'use_for_retrieval':bool(spec.get('use_for_retrieval',True)),'allow_private_network':spec.get('allow_private_network') is True,'created_at':float(spec.get('created_at') or time.time()),'updated_at':time.time()};data=_read(SOURCES,{'version':1,'sources':[]});data['sources']=[x for x in data.get('sources',[]) if x.get('id')!=sid]+[src];_write(SOURCES,data);return src
@storage.serialized
def set_enabled(sid,enabled):
    sid=_safe_id(sid);rows=list_sources();found=None
    for x in rows:
        if x.get('id')==sid:x['enabled']=bool(enabled);x['updated_at']=time.time();found=x;break
    if not found:raise FileNotFoundError(sid)
    _write(SOURCES,{'version':1,'sources':rows});return found
def _headers(src):
    out={'User-Agent':'Orcha/7.6 DataHub'}
    for header,envname in (src.get('headers_env') or {}).items():
        val=os.environ.get(str(envname))
        if not re.fullmatch(r'ORCHA_SOURCE_[A-Z0-9_]+',str(envname)):raise ValueError('Credential variable must start with ORCHA_SOURCE_')
        if str(header).lower() in {'host','cookie','content-length','connection'}:raise ValueError('Reserved source header')
        if val:
            if urlparse(src['url']).scheme!='https':raise ValueError('Credentials require HTTPS')
            out[str(header)]=val
    return out
def _fetch(src):
    url=src['url'];headers=_headers(src);origin=(urlparse(url).scheme,urlparse(url).netloc)
    for _ in range(5):
        _safe_url(url);parts=urlparse(url);port=parts.port or (443 if parts.scheme=='https' else 80);addresses=socket.getaddrinfo(parts.hostname,port,type=socket.SOCK_STREAM)
        if not addresses:raise ValueError('Source host has no address')
        for address in addresses:
            ip=ipaddress.ip_address(address[4][0])
            if not ip.is_global and not src.get('allow_private_network'):raise ValueError('Private network source requires explicit opt-in')
        ip=addresses[0][4][0];cls=http.client.HTTPSConnection if parts.scheme=='https' else http.client.HTTPConnection;connection=cls(parts.hostname,port,timeout=15);connection._create_connection=lambda address,timeout=None,source_address=None:socket.create_connection((ip,port),timeout,source_address)
        try:
            connection.request('GET',parts.path+('?' + parts.query if parts.query else '') or '/',headers=headers);response=connection.getresponse()
            if response.status in {301,302,303,307,308}:
                location=response.getheader('Location')
                if not location:raise ValueError('Redirect missing location')
                url=urljoin(url,location)
                if (urlparse(url).scheme,urlparse(url).netloc)!=origin:headers={'User-Agent':'Orcha/7.6 DataHub'}
                continue
            if response.status>=400:raise ValueError('Source HTTP '+str(response.status))
            raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise ValueError('Source exceeds 5 MB')
            return raw,str(response.getheader('Content-Type') or '')[:200]
        finally:connection.close()
    raise ValueError('Too many source redirects')
def _txt(v):return '' if v is None else (json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else str(v))
def _json_docs(raw,src):
    obj=json.loads(raw.decode('utf-8','replace'));rows=obj if isinstance(obj,list) else [obj];out=[]
    for i,x in enumerate(rows[:1000]):
        if isinstance(x,dict):title=_txt(x.get('title') or x.get('name') or x.get('id') or f'item {i+1}');text=_txt(x)
        else:title=f'item {i+1}';text=_txt(x)
        out.append({'title':title[:300],'text':text[:20000],'source_url':src['url']})
    return out
def _feed_docs(raw,src):
    root=ET.fromstring(raw);out=[]
    for node in list(root.findall('.//item'))+list(root.findall('.//{*}entry')):
        def val(name):
            n=node.find(name)
            if n is None:n=node.find('{*}'+name)
            if n is None:return ''
            return n.get('href','') if name=='link' and n.get('href') else ''.join(n.itertext()).strip()
        title=val('title') or 'Untitled';link=val('link');desc=val('description') or val('summary') or val('content');out.append({'title':title[:300],'text':desc[:20000],'source_url':link or src['url']})
        if len(out)>=500:break
    return out
def _text_docs(raw,src):return [{'title':src.get('name') or src['id'],'text':re.sub(r'\x00+','',raw.decode('utf-8','replace'))[:200000],'source_url':src['url']}]
def parse(raw,src):return _json_docs(raw,src) if src.get('type')=='json' else (_feed_docs(raw,src) if src.get('type') in {'rss','atom'} else _text_docs(raw,src))
def _sync_source(sid):
    sid=_safe_id(sid);src=next((x for x in list_sources() if x.get('id')==sid),None)
    if not src:raise FileNotFoundError(sid)
    if not src.get('enabled'):return {'id':sid,'status':'disabled'}
    started=time.time()
    try:
        raw,ctype=_fetch(src);docs=parse(raw,src);stamp=int(time.time());folder=DOCS/sid;folder.mkdir(parents=True,exist_ok=True)
        with storage.transaction():_write(folder/'latest.json',{'source':src,'synced_at':stamp,'content_hash':hashlib.sha256(raw).hexdigest(),'content_type':ctype,'documents':docs})
        with storage.transaction():state=_read(STATE,{});state[sid]={'status':'ok','last_sync':stamp,'documents':len(docs),'duration_ms':round((time.time()-started)*1000)};_write(STATE,state)
        return {'id':sid,**state[sid]}
    except Exception as exc:
        with storage.transaction():state=_read(STATE,{});state[sid]={'status':'error','last_sync':int(time.time()),'error':str(exc)[:500],'duration_ms':round((time.time()-started)*1000)};_write(STATE,state)
        return {'id':sid,**state[sid]}
def sync_source(sid):
    with _LOCK:lock=_SYNC_LOCKS.setdefault(sid,threading.Lock())
    if not lock.acquire(blocking=False):return {'id':sid,'status':'running'}
    try:return _sync_source(sid)
    finally:lock.release()
def evidence(project_id=None):
    for source in list_sources():
        if not source.get('enabled') or not source.get('use_for_retrieval') or source.get('project_id')!=project_id:continue
        path=DOCS/source['id']/'latest.json';snapshot=_read(path,{})
        for i,doc in enumerate(snapshot.get('documents',[])):yield {'path':str(path),'chunk':i,'text':doc.get('title','')+'\n'+doc.get('text',''),'source_url':doc.get('source_url'),'synced_at':snapshot.get('synced_at'),'project_id':project_id}
def status():
    state=_read(STATE,{});return {'sources':len(list_sources()),'enabled':sum(bool(x.get('enabled')) for x in list_sources()),'state':state,'policy':{'network_read_only':True,'credentials_from_env_only':True,'max_fetch_mb':5,'min_interval_minutes':MIN_INTERVAL}}
def sync_due(now=None):
    now=now or time.time();state=_read(STATE,{});out=[]
    for src in list_sources():
        if not src.get('enabled'):continue
        last=float((state.get(src['id']) or {}).get('last_sync') or 0);interval=max(MIN_INTERVAL,int(src.get('interval_minutes') or 60))*60
        if now-last>=interval:out.append(sync_source(src['id']))
    return out
class Scheduler:
    def __init__(self,period_seconds=60):self.period=max(30,int(period_seconds));self.stop_event=threading.Event();self.thread=None
    def start(self):
        if self.thread and self.thread.is_alive():return self
        def loop():
            while not self.stop_event.wait(self.period):
                try:sync_due()
                except Exception:pass
        self.thread=threading.Thread(target=loop,name='orcha-data-sync',daemon=True);self.thread.start();return self
    def stop(self):self.stop_event.set()
def self_test():
    sample={'id':'demo','name':'Demo','type':'json','url':'https://example.com/data.json','interval_minutes':1};assert _safe_id('Demo Source')=='demo-source';assert save_source(sample)['interval_minutes']==15;docs=parse(b'[{"title":"A","value":1}]',sample);assert docs and docs[0]['title']=='A';assert status()['policy']['credentials_from_env_only'];print('PASS: Orcha Data Hub')
if __name__=='__main__':self_test()
