#!/usr/bin/env python3
from __future__ import annotations
import storage
import json,os,re,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REGISTRY=ROOT/'config'/'models.json';USER_REGISTRY=storage.DATA/'models.json';ID=re.compile(r'^[a-z0-9][a-z0-9._-]{1,63}$')
def _load(path):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return {'version':1,'models':[]}
def _save(path,obj):path.parent.mkdir(parents=True,exist_ok=True);storage.atomic_json(path,obj)
def total_ram_gb():
    try:
        if os.name=='nt':
            import ctypes
            class M(ctypes.Structure):_fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong),('ullTotalPhys',ctypes.c_ulonglong),('ullAvailPhys',ctypes.c_ulonglong),('ullTotalPageFile',ctypes.c_ulonglong),('ullAvailPageFile',ctypes.c_ulonglong),('ullTotalVirtual',ctypes.c_ulonglong),('ullAvailVirtual',ctypes.c_ulonglong),('sullAvailExtendedVirtual',ctypes.c_ulonglong)]
            m=M();m.dwLength=ctypes.sizeof(M);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return round(m.ullTotalPhys/(1024**3),1)
        return round((os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE'))/(1024**3),1)
    except Exception:return 0.0
def list_models():
    base=_load(REGISTRY).get('models',[]);user=_load(USER_REGISTRY).get('models',[]);by={str(x.get('id')):dict(x) for x in base if x.get('id')}
    for x in user:
        if x.get('id'):by[str(x['id'])]=dict(x)
    ram=total_ram_gb();out=[]
    for x in by.values():y=dict(x);y['ram_ok']=not ram or ram>=float(y.get('min_ram_gb') or 0);y['system_ram_gb']=ram;out.append(y)
    return sorted(out,key=lambda x:(not bool(x.get('builtin')),str(x.get('name','')).lower()))
def get(mid):return next((x for x in list_models() if x.get('id')==mid),None)
@storage.serialized
def save_model(spec):
    mid=str(spec.get('id') or '').strip().lower()
    if not ID.match(mid):raise ValueError('Model id không hợp lệ')
    if get(mid) and bool(get(mid).get('builtin')):raise ValueError('Không ghi đè model hệ thống')
    tag=str(spec.get('ollama_tag') or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}',tag):raise ValueError('Thiếu Ollama tag')
    obj={'id':mid,'name':str(spec.get('name') or mid)[:80],'ollama_tag':tag,'size_mb':max(1,int(spec.get('size_mb') or 500)),'min_ram_gb':max(1,float(spec.get('min_ram_gb') or 4)),'native_context':max(512,int(spec.get('native_context') or 4096)),'modalities':[x for x in spec.get('modalities',[]) if x in {'text','image','audio'}] or ['text'],'capabilities':{k:max(0,min(100,int(v))) for k,v in (spec.get('capabilities') or {}).items() if k in {'chat','vietnamese','code','reasoning','tools','vision','uiux'}},'roles':[str(x)[:32] for x in (spec.get('roles') or [])[:12]],'description':str(spec.get('description') or '')[:400],'builtin':False,'created_at':int(time.time())};data=_load(USER_REGISTRY);data['models']=[x for x in data.get('models',[]) if x.get('id')!=mid]+[obj];_save(USER_REGISTRY,data);return obj
@storage.serialized
def delete_model(mid):
    if get(mid) and bool(get(mid).get('builtin')):return False
    data=_load(USER_REGISTRY);items=data.get('models',[]);new=[x for x in items if x.get('id')!=mid];data['models']=new;_save(USER_REGISTRY,data);return len(new)!=len(items)
def classify_task(text,has_image=False):
    t=(text or '').lower()
    if has_image or any(k in t for k in ['ui/ux','giao diện','screenshot','layout','figma','wireframe','màn hình','thiết kế','design']):return 'uiux'
    if any(k in t for k in ['code','bug','refactor','typescript','python','review mã','kiến trúc']):return 'code'
    if any(k in t for k in ['lập kế hoạch','phân tích sâu','reason','workflow','agent']):return 'reasoning'
    return 'chat'
def canonical_tag(tag):
    tag=str(tag);return tag if ':' in tag.rsplit('/',1)[-1] else tag+':latest'
def installed_tags(host):
    with urllib.request.urlopen(host.rstrip('/')+'/api/tags',timeout=5) as response:data=json.load(response)
    return {canonical_tag(x.get('name') or x.get('model') or '') for x in data.get('models',[])}
def runtime_model(selected,has_image=False):
    selected=dict(selected or {})
    if selected.get('composite') and not has_image:
        companion=get(str(selected.get('companion_model') or 'balanced')) or get('balanced')
        if companion:return {'model':str(companion.get('ollama_tag') or ''),'selected':companion,'reason':'composite-text-companion','composite':selected}
    return {'model':str(selected.get('ollama_tag') or ''),'selected':selected,'reason':'selected-model','composite':None}
def route(text,has_image=False,preferred='auto',host=None):
    models=list_models();ram=total_ram_gb();task=classify_task(text,has_image)
    if host:
        available=installed_tags(host);models=[m for m in models if canonical_tag(m.get('ollama_tag','')) in available and (not m.get('composite') or canonical_tag(runtime_model(m,False).get('model','')) in available)]
    if has_image:models=[m for m in models if 'image' in m.get('modalities',[])]
    if preferred!='auto':
        m=next((m for m in models if m['id']==preferred and m.get('ram_ok')),None)
        if not m:raise ValueError('Selected model unavailable, incompatible, or exceeds RAM budget')
        return {'task':task,'selected':m,'reason':'user-selected','system_ram_gb':ram}
    candidates=[m for m in models if m.get('ram_ok')]
    if not candidates and host:raise ValueError('No installed model fits this task and RAM budget; install a compatible model')
    key='uiux' if task=='uiux' else task
    def score(m):
        c=m.get('capabilities') or {};s=int(c.get(key,c.get('chat',0)));return s-60 if task=='uiux' and has_image and 'image' not in m.get('modalities',[]) else s+(3 if 'default' in m.get('roles',[]) else 0)
    chosen=max(candidates,key=score) if candidates else None;return {'task':task,'selected':chosen,'reason':'capability+ram','system_ram_gb':ram,'candidates':[{'id':m.get('id'),'score':score(m)} for m in candidates]}
def inference_limits(model,profile='balanced'):
    import orcha_core as core
    cfg=core.profile_config(profile);registered=next((m for m in list_models() if canonical_tag(m.get('ollama_tag',''))==canonical_tag(model)),{});native=int(registered.get('native_context') or cfg.get('native_context',4096));working=min(native,int(cfg.get('working_context',4096)),max(512,int(core._WORKING_LIMIT.get() or native)));return {**cfg,'working_context':working,'native_context':native}
def execution_model(query,host,preferred='auto',tag=None):
    if tag:
        registered=next((m for m in list_models() if canonical_tag(m['ollama_tag'])==canonical_tag(tag)),None)
        if not registered:raise ValueError('Register the model before executing it')
        preferred=registered['id']
    selected=route(query,False,str(preferred or 'auto'),host=host)['selected'];return runtime_model(selected,False)['model']
def self_test():
    assert get('balanced');assert get('logic-08b');assert classify_task('đánh giá UI/UX screenshot')=='uiux';r=route('review code');assert r.get('selected');ui=get('uiux-vision-lite');x=runtime_model(ui,False);assert x.get('selected',{}).get('id')=='balanced';assert runtime_model(ui,True).get('selected',{}).get('id')=='uiux-vision-lite';print('PASS: model registry/router + composite text companion')
if __name__=='__main__':self_test()
