#!/usr/bin/env python3
from __future__ import annotations
import time
from pathlib import Path
import model_registry as registry
import network_transport as network

DATA=Path(__file__).resolve().parents[1]/'data'/'model-benchmarks.json'

def declared_score(m:dict)->int:
    c=m.get('capabilities') or {};vals=[int(v) for v in c.values() if isinstance(v,(int,float))]
    return round(sum(vals)/len(vals)) if vals else 0

def compare(ids:list[str])->dict:
    rows=[]
    for mid in ids:
        m=registry.get(mid)
        if not m:continue
        rows.append({'id':mid,'name':m.get('name'),'declared_score':declared_score(m),'size_mb':m.get('size_mb'),'min_ram_gb':m.get('min_ram_gb'),'native_context':m.get('native_context'),'capabilities':m.get('capabilities') or {},'ram_ok':m.get('ram_ok')})
    return {'models':rows,'winner':max(rows,key=lambda x:x['declared_score'])['id'] if rows else None,'note':'Declared score là metadata ban đầu, không phải benchmark học thuật.'}

def _chat(tag,prompt,host,timeout=90):
    body={'model':tag,'messages':[{'role':'user','content':prompt}],'stream':False,'think':False,'options':{'temperature':0,'num_ctx':2048}}
    t=time.perf_counter();d=network.post_json(host.rstrip('/')+'/api/chat',body,timeout=timeout)
    return str(d.get('message',{}).get('content','')).strip(),time.perf_counter()-t

def benchmark(mid:str,host='http://127.0.0.1:11434')->dict:
    m=registry.get(mid)
    if not m:raise ValueError('Không tìm thấy model')
    tag=str(m.get('ollama_tag') or '')
    prompts=[('vi','Trả lời đúng một câu tiếng Việt: Vì sao hierarchy quan trọng trong giao diện?'),('reasoning','Một form có 12 trường bắt buộc trên mobile. Nêu 3 ưu tiên UX ngắn gọn.'),('tools','Trả JSON duy nhất {"tool":"project.search","query":"button"}.')]
    scores={};lat=[]
    for key,p in prompts:
        text,sec=_chat(tag,p,host);lat.append(sec)
        if key=='vi':scores[key]=100 if any(ch in text.lower() for ch in ['giao diện','người dùng','thông tin','thị giác']) else 60
        elif key=='reasoning':scores[key]=min(100,40+(20 if len(text)>80 else 0)+(20 if any(x in text for x in ['1.','2.','3.','- ']) else 0))
        else:scores[key]=100 if 'project.search' in text and 'query' in text else 45
    result={'id':mid,'model':tag,'timestamp':int(time.time()),'latency_s':round(sum(lat)/len(lat),2),'scores':scores,'runtime_score':round(sum(scores.values())/len(scores)),'declared_score':declared_score(m)}
    try:
        import json
        DATA.parent.mkdir(parents=True,exist_ok=True);old=json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else {};old[mid]=result;DATA.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:pass
    return result

def last(mid:str|None=None):
    try:
        import json
        d=json.loads(DATA.read_text(encoding='utf-8'))
    except Exception:d={}
    return d.get(mid) if mid else d

def self_test():
    c=compare(['max','balanced']);assert len(c['models'])==2;assert c['winner'];print('PASS: model benchmark')
if __name__=='__main__':self_test()
