#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/'config'/'models.json'
USER_REGISTRY=Path(os.environ.get('KIMIK3_DATA_DIR',str(ROOT/'data'))).expanduser()/'models.json'
ID=re.compile(r'^[a-z0-9][a-z0-9._-]{1,63}$')


def _load(path:Path)->dict:
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return {'version':1,'models':[]}
def _save(path:Path,obj:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def total_ram_gb()->float:
    try:
        if os.name=='nt':
            import ctypes
            class M(ctypes.Structure):
                _fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong),('ullTotalPhys',ctypes.c_ulonglong),('ullAvailPhys',ctypes.c_ulonglong),('ullTotalPageFile',ctypes.c_ulonglong),('ullAvailPageFile',ctypes.c_ulonglong),('ullTotalVirtual',ctypes.c_ulonglong),('ullAvailVirtual',ctypes.c_ulonglong),('sullAvailExtendedVirtual',ctypes.c_ulonglong)]
            m=M();m.dwLength=ctypes.sizeof(M);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return round(m.ullTotalPhys/(1024**3),1)
        pages=os.sysconf('SC_PHYS_PAGES');size=os.sysconf('SC_PAGE_SIZE');return round((pages*size)/(1024**3),1)
    except Exception:return 0.0

def list_models()->list[dict]:
    base=_load(REGISTRY).get('models',[]);user=_load(USER_REGISTRY).get('models',[])
    by={str(x.get('id')):dict(x) for x in base if x.get('id')}
    for x in user:
        if x.get('id'):by[str(x['id'])]=dict(x)
    ram=total_ram_gb()
    out=[]
    for x in by.values():
        y=dict(x);y['ram_ok']=not ram or ram>=float(y.get('min_ram_gb') or 0);y['system_ram_gb']=ram;out.append(y)
    return sorted(out,key=lambda x:(not bool(x.get('builtin')),str(x.get('name','')).lower()))

def get(mid:str)->dict|None:return next((x for x in list_models() if x.get('id')==mid),None)

def save_model(spec:dict)->dict:
    mid=str(spec.get('id') or '').strip().lower()
    if not ID.match(mid):raise ValueError('Model id không hợp lệ')
    if get(mid) and bool(get(mid).get('builtin')):raise ValueError('Không ghi đè model hệ thống')
    tag=str(spec.get('ollama_tag') or '').strip()
    if not tag or len(tag)>120:raise ValueError('Thiếu Ollama tag')
    obj={
      'id':mid,'name':str(spec.get('name') or mid)[:80],'ollama_tag':tag,
      'size_mb':max(1,int(spec.get('size_mb') or 500)),'min_ram_gb':max(1,float(spec.get('min_ram_gb') or 4)),
      'native_context':max(512,int(spec.get('native_context') or 4096)),
      'modalities':[x for x in spec.get('modalities',[]) if x in {'text','image','audio'}] or ['text'],
      'capabilities':{k:max(0,min(100,int(v))) for k,v in (spec.get('capabilities') or {}).items() if k in {'chat','vietnamese','code','reasoning','tools','vision','uiux'}},
      'roles':[str(x)[:32] for x in (spec.get('roles') or [])[:12]],'description':str(spec.get('description') or '')[:400],
      'builtin':False,'created_at':int(time.time())}
    data=_load(USER_REGISTRY);items=[x for x in data.get('models',[]) if x.get('id')!=mid]+[obj];data['models']=items;_save(USER_REGISTRY,data);return obj

def delete_model(mid:str)->bool:
    if get(mid) and bool(get(mid).get('builtin')):return False
    data=_load(USER_REGISTRY);items=data.get('models',[]);new=[x for x in items if x.get('id')!=mid];data['models']=new;_save(USER_REGISTRY,data);return len(new)!=len(items)

def classify_task(text:str,has_image:bool=False)->str:
    t=(text or '').lower()
    if has_image or any(k in t for k in ['ui/ux','giao diện','screenshot','layout','figma','wireframe','màn hình','thiết kế','design']):return 'uiux'
    if any(k in t for k in ['code','bug','refactor','typescript','python','review mã','kiến trúc']):return 'code'
    if any(k in t for k in ['lập kế hoạch','phân tích sâu','reason','workflow','agent']):return 'reasoning'
    return 'chat'

def route(text:str,has_image:bool=False,preferred:str='auto')->dict:
    models=list_models();ram=total_ram_gb();task=classify_task(text,has_image)
    if preferred!='auto':
        m=get(preferred)
        if m:return {'task':task,'selected':m,'reason':'user-selected','system_ram_gb':ram}
    candidates=[m for m in models if m.get('ram_ok')]
    if not candidates:candidates=models
    key='uiux' if task=='uiux' else task
    def score(m):
        c=m.get('capabilities') or {};s=int(c.get(key,c.get('chat',0)))
        if task=='uiux' and has_image and 'image' not in m.get('modalities',[]):s-=60
        if 'default' in m.get('roles',[]):s+=3
        return s
    chosen=max(candidates,key=score) if candidates else None
    return {'task':task,'selected':chosen,'reason':'capability+ram','system_ram_gb':ram,'candidates':[{'id':m.get('id'),'score':score(m)} for m in candidates]}

def runtime_model(selected:dict|None,has_image:bool=False)->dict:
    """Resolve the actual Ollama model used for a request.

    Composite vision profiles are not suitable as plain text chat models. When no image is
    attached, use their declared companion model and keep the selected composite profile in
    route metadata so the UI can still show the user's choice.
    """
    selected=dict(selected or {})
    if selected.get('composite') and not has_image:
        companion=get(str(selected.get('companion_model') or 'balanced')) or get('balanced')
        if companion:
            return {'model':str(companion.get('ollama_tag') or ''),'selected':companion,'reason':'composite-text-companion','composite':selected}
    return {'model':str(selected.get('ollama_tag') or ''),'selected':selected,'reason':'selected-model','composite':None}

def self_test():
    assert get('balanced');assert classify_task('đánh giá UI/UX screenshot')=='uiux';assert classify_task('tìm hiểu thiết kế Apple')=='uiux';r=route('review code');assert r.get('selected')
    ui=get('uiux-vision-lite');x=runtime_model(ui,False);assert x.get('selected',{}).get('id')=='balanced' and x.get('reason')=='composite-text-companion'
    y=runtime_model(ui,True);assert y.get('selected',{}).get('id')=='uiux-vision-lite'
    print('PASS: model registry/router + composite text companion')

if __name__=='__main__':self_test()
