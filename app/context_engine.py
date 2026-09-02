from __future__ import annotations
import storage
import json,math,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=storage.DATA;SESSIONS=DATA/'sessions';TEXT_EXTS={'.md','.txt','.json','.jsonl','.yaml','.yml','.toml'}
def approx_tokens(text):return 0 if not text else max(1,int(math.ceil(len(text)/3.6)))
def _safe_id(value):
    import hashlib
    original=str(value or 'default');safe=re.sub(r'[^a-zA-Z0-9_.-]+','-',original).strip('-._')[:80] or 'default';return safe+('-'+hashlib.sha256(original.encode()).hexdigest()[:12] if safe!=original else '')
def _session_path(session_id):SESSIONS.mkdir(parents=True,exist_ok=True);return SESSIONS/f'{_safe_id(session_id)}.jsonl'
@storage.serialized
def append_turn(session_id,user,assistant):
    p=_session_path(session_id);row={'ts':time.time(),'user':str(user)[:20000],'assistant':str(assistant)[:30000]}
    with p.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
def load_turns(session_id,limit=24):
    p=_session_path(session_id)
    if not p.exists():return []
    with p.open('rb') as stream:size=p.stat().st_size;stream.seek(max(0,size-2*1024*1024));raw=stream.read().decode('utf-8',errors='ignore')
    lines=raw.splitlines()[1:] if size>2*1024*1024 else raw.splitlines();out=[]
    for line in lines[-max(1,limit):]:
        try:
            item=json.loads(line)
            if isinstance(item,dict):out.append(item)
        except Exception:pass
    return out
def history_text(session_id,token_budget=900):
    if token_budget<=0:return ''
    chosen=[];used=0
    for turn in reversed(load_turns(session_id,32)):
        block=f"User: {turn.get('user','')}\nAssistant: {turn.get('assistant','')}";cost=approx_tokens(block)
        if used+cost>token_budget:
            if not chosen:chosen.append(block[-max(1,int(token_budget*3.6)):])
            break
        chosen.append(block);used+=cost
        if used>=token_budget:break
    return '\n\n'.join(reversed(chosen))
def bound_messages(messages,budget):
    remaining=max(0,int(budget*3.6));out=[];system=[m for m in messages if m.get('role')=='system'];others=[m for m in messages if m.get('role')!='system']
    for m in system:
        text=str(m.get('content',''))[:remaining];remaining-=len(text);out.append({**m,'content':text})
    tail=[]
    for m in reversed(others):
        if remaining<=0:break
        text=str(m.get('content',''))[-remaining:];remaining-=len(text);tail.append({**m,'content':text})
    return out+list(reversed(tail))
def _tree_tokens(path):
    if not path.exists():return 0,0
    total=files=0
    for p in path.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:continue
        try:
            if p.stat().st_size>1024*1024:continue
            text=p.read_text(encoding='utf-8',errors='ignore')
        except OSError:continue
        total+=approx_tokens(text);files+=1
    return total,files
def _file_tokens(path):
    if not path.exists():return 0,0
    try:text=path.read_text(encoding='utf-8',errors='ignore')
    except OSError:return 0,0
    try:
        obj=json.loads(text);count=len(obj) if isinstance(obj,(list,dict)) else 1
    except Exception:count=1 if text.strip() else 0
    return approx_tokens(text),count
def context_snapshot(index_records,memory_items,session_id='default',virtual_limit=1_000_000,working_limit=4096,native_limit=40960,working_used=0):
    project_tokens=sum(approx_tokens(str(x.get('text',''))) for x in index_records);memory_tokens=sum(approx_tokens(str(x.get('text',''))) for x in memory_items);turns=load_turns(session_id,64);history_tokens=sum(approx_tokens(str(x.get('user','')))+approx_tokens(str(x.get('assistant',''))) for x in turns);skills_tokens,skills_count=_tree_tokens(ROOT/'skills');mcp_tokens,mcp_count=_file_tokens(DATA/'mcp_tools.json')
    if not mcp_tokens:mcp_tokens,mcp_count=_file_tokens(ROOT/'config'/'mcp.json')
    agents_tokens,agents_count=_file_tokens(DATA/'custom_agents.json');rows=[{'key':'skills','label':'Skills','tokens':skills_tokens,'count':skills_count},{'key':'project','label':'Project knowledge','tokens':project_tokens,'count':len(index_records)},{'key':'memory','label':'Memory','tokens':memory_tokens,'count':len(memory_items)},{'key':'history','label':'Conversation','tokens':history_tokens,'count':len(turns)},{'key':'mcp','label':'MCP tools','tokens':mcp_tokens,'count':mcp_count},{'key':'agents','label':'Custom agents','tokens':agents_tokens,'count':agents_count}];indexed_total=sum(x['tokens'] for x in rows);used=min(indexed_total,virtual_limit);free=max(0,virtual_limit-used)
    for row in rows:row['percent']=round((row['tokens']/virtual_limit)*100,2) if virtual_limit else 0
    rows.append({'key':'free','label':'Free space','tokens':free,'count':0,'percent':round((free/virtual_limit)*100,2) if virtual_limit else 0})
    return {'virtual':{'limit_tokens':virtual_limit,'used_tokens':used,'indexed_total_tokens':indexed_total,'overflow_tokens':max(0,indexed_total-virtual_limit),'percent':round((used/virtual_limit)*100,2) if virtual_limit else 0,'rows':rows},'working':{'limit_tokens':working_limit,'used_tokens':max(0,working_used),'overflow_tokens':max(0,working_used-working_limit),'percent':round((min(max(0,working_used),working_limit)/working_limit)*100,2) if working_limit else 0},'native':{'limit_tokens':native_limit},'session_id':_safe_id(session_id),'estimate':True}
