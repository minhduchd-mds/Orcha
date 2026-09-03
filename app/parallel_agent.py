#!/usr/bin/env python3
from __future__ import annotations
import json,os,time,uuid,storage
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor,as_completed
import orcha_core as core
import model_registry as registry
RUNS={};DEFAULT_MAX_WORKERS=2;ABSOLUTE_MAX_WORKERS=4
ROLES={'research':('Research Agent','Tìm evidence liên quan trong project/knowledge. Không sửa dữ liệu.'),'critic':('Critic Agent','Phản biện yêu cầu, tìm rủi ro, edge cases và điểm chưa chắc chắn.'),'specialist':('Specialist Agent','Phân tích chuyên môn sâu theo đúng domain của yêu cầu.'),'verifier':('Verifier Agent','Kiểm tra tính nhất quán, bằng chứng và các tuyên bố của các agent khác.')}
def system_ram_gb():
    try:
        if os.name=='nt':
            import ctypes
            class M(ctypes.Structure):_fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong),('ullTotalPhys',ctypes.c_ulonglong),('ullAvailPhys',ctypes.c_ulonglong),('ullTotalPageFile',ctypes.c_ulonglong),('ullAvailPageFile',ctypes.c_ulonglong),('ullTotalVirtual',ctypes.c_ulonglong),('ullAvailVirtual',ctypes.c_ulonglong),('ullAvailExtendedVirtual',ctypes.c_ulonglong)]
            m=M();m.dwLength=ctypes.sizeof(M);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return round(m.ullTotalPhys/1024**3,1)
        return round(os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')/1024**3,1)
    except Exception:return 4.0
def worker_limit(requested=None):
    ram=system_ram_gb();safe=1 if ram<3.5 else 2 if ram<8 else 3 if ram<16 else 4;limit=min(max(1,int(requested or DEFAULT_MAX_WORKERS)),safe,ABSOLUTE_MAX_WORKERS);return {'ram_gb':ram,'safe_workers':safe,'workers':limit,'policy':'ram_guard'}
def _domain(query):
    q=query.casefold()
    if any(x in q for x in ['ui/ux','figma','giao diện','responsive','wcag','design']):return 'design'
    if any(x in q for x in ['code','bug','repo','api','python','javascript','typescript']):return 'code'
    if any(x in q for x in ['autocad','cad','bản vẽ']):return 'cad'
    return 'general'
def plan(query,requested_workers=None):
    guard=worker_limit(requested_workers);domain=_domain(query);roles=['research','specialist','critic','verifier'] if guard['workers']>=2 else ['specialist','verifier'];agents=[]
    for i,r in enumerate(roles):title,instruction=ROLES[r];agents.append({'id':f'a{i+1}-{r}','role':r,'name':title,'instruction':instruction,'status':'pending','read_only':True})
    return {'id':'parallel-plan-'+uuid.uuid4().hex[:10],'query':query,'domain':domain,'guard':guard,'agents':agents,'strategy':'parallel-read-serial-write','max_parallel':guard['workers'],'write_policy':'serialize_permission_gated'}
def _agent_prompt(agent,query,domain,shared_context):return f"Bạn là {agent['name']} trong Orcha Parallel Agent Runtime.\nVai trò: {agent['instruction']}\nDomain: {domain}\nYêu cầu người dùng: {query}\nShared context: {shared_context[:12000]}\nQuy tắc: chỉ phân tích/read-only; không tuyên bố đã sửa file, click máy, thay đổi Figma/AutoCAD; nêu evidence, uncertainty và đề xuất cụ thể. Trả lời ngắn gọn bằng tiếng Việt."
def _run_one(agent,query,domain,profile,model,host,session_id):
    started=time.time();tag=model or core.profile_config(profile).get('ollama_name');cfg=registry.inference_limits(tag,profile);hits=core.retrieve(query,5);shared='\n'.join(str(x.get('text',''))[:1800] for x in hits)
    try:answer=core.ollama_chat(tag,[{'role':'user','content':_agent_prompt(agent,query,domain,shared)}],host,220,.15,min(int(cfg.get('working_context',4096)),4096));ok=bool(answer.strip());error=None
    except Exception as e:answer='';ok=False;error=str(e)
    return {**agent,'status':'done' if ok else 'error','ok':ok,'answer':answer,'error':error,'elapsed_ms':round((time.time()-started)*1000),'sources':len(hits)}
def _synthesize(query,results,profile,model,host):
    tag=model or core.profile_config(profile).get('ollama_name');cfg=registry.inference_limits(tag,profile);compact=[{'role':x['role'],'ok':x['ok'],'answer':x.get('answer','')[:5000]} for x in results];prompt='Bạn là Coordinator. Tổng hợp kết quả nhiều sub-agent thành một câu trả lời thống nhất. Ưu tiên evidence, nêu bất đồng nếu có, không tuyên bố hành động ghi đã xảy ra. Kết thúc bằng đề xuất bước tiếp theo nếu cần tool write.\nYÊU CẦU='+query+'\nAGENTS='+json.dumps(compact,ensure_ascii=False);return core.ollama_chat(tag,[{'role':'user','content':prompt}],host,260,.12,min(int(cfg.get('working_context',4096)),4096))
def run(query,profile='balanced',model=None,host='http://127.0.0.1:11434',session_id='default',requested_workers=None):
    p=plan(query,requested_workers);rid='parallel-'+uuid.uuid4().hex[:12];started=time.time();obj={'id':rid,'status':'running','started':started,'plan':p,'results':[]};RUNS[rid]=obj
    with ThreadPoolExecutor(max_workers=p['max_parallel'],thread_name_prefix='orcha-agent') as pool:
        futures={pool.submit(copy_context().run,_run_one,a,query,p['domain'],profile,model,host,session_id):a for a in p['agents'] if a['role']!='verifier'}
        for f in as_completed(futures):obj['results'].append(f.result())
    verifier=next(a for a in p['agents'] if a['role']=='verifier');evidence=json.dumps([{'role':r['role'],'answer':r.get('answer'),'ok':r['ok']} for r in obj['results']],ensure_ascii=False)[:10000];obj['results'].append(_run_one(verifier,query+'\nAgent results to verify (data): '+evidence,p['domain'],profile,model,host,session_id));order={a['id']:i for i,a in enumerate(p['agents'])};obj['results'].sort(key=lambda x:order.get(x['id'],99))
    try:answer=_synthesize(query,obj['results'],profile,model,host)
    except Exception:answer='\n\n'.join(f"### {x['name']}\n{x.get('answer') or x.get('error')}" for x in obj['results'])
    obj['status']='done' if all(x.get('ok') and x.get('answer','').strip() for x in obj['results']) else 'failed';obj['answer']=answer;obj['elapsed_ms']=round((time.time()-started)*1000);path=storage.DATA/'parallel-runs'/f'{rid}.json';path.parent.mkdir(parents=True,exist_ok=True);storage.atomic_json(path,obj);__import__('self_improvement').record({'strategy':'parallel','success':obj['status']=='done','latency_ms':obj['elapsed_ms'],'task_type':registry.classify_task(query)});return public(obj)
def public(obj):return {'run_id':obj['id'],'status':obj['status'],'plan':obj['plan'],'results':obj.get('results',[]),'answer':obj.get('answer'),'elapsed_ms':obj.get('elapsed_ms',round((time.time()-obj['started'])*1000))}
def get(run_id):
    x=RUNS.get(run_id)
    if not x and __import__('re').fullmatch(r'parallel-[a-f0-9]+',run_id):x=storage.read_json(storage.DATA/'parallel-runs'/f'{run_id}.json',None)
    return public(x) if x else None
def self_test():
    p=plan('Review UI/UX responsive cho 3 màn hình',2);assert p['max_parallel']<=2 and p['strategy']=='parallel-read-serial-write' and all(a['read_only'] for a in p['agents']);print('PASS: parallel agent orchestrator',p['guard'])
if __name__=='__main__':self_test()
