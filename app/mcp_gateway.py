#!/usr/bin/env python3
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
from typing import Any

import mcp_transport as transport
import permission_engine as perms

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('KIMIK3_DATA_DIR', str(ROOT/'data'))).expanduser()
CONFIG = ROOT / 'config' / 'mcp.json'
INDEX = DATA / 'index.jsonl'
_PROBE_CACHE: dict[str, tuple[float, dict]] = {}

BUILTIN_TOOLS = [
    {'name':'project.search','description':'Search indexed local project context.','permission':'project.search','server':'builtin'},
    {'name':'filesystem.read_text','description':'Read a repository file or an exact file already indexed by KimiK3.','permission':'filesystem.read','server':'builtin'},
    {'name':'filesystem.list','description':'List a directory inside the KimiK3 repository.','permission':'filesystem.list','server':'builtin'},
    {'name':'context.stats','description':'Read context inventory and limits.','permission':'context.read','server':'builtin'},
]


def config() -> dict:
    try:
        x=json.loads(CONFIG.read_text(encoding='utf-8'))
        return x if isinstance(x,dict) else {'version':2,'servers':[]}
    except Exception:
        return {'version':2,'servers':[]}


def _platform_ok(server: dict) -> bool:
    platforms=server.get('platforms') or []
    return not platforms or sys.platform in [str(x) for x in platforms]


def _server(sid: str) -> dict|None:
    return next((s for s in config().get('servers',[]) if isinstance(s,dict) and str(s.get('id'))==sid),None)


def _external_tools(include_disabled: bool=True) -> list[dict]:
    out=[]
    for server in config().get('servers',[]):
        if not isinstance(server,dict): continue
        enabled=bool(server.get('enabled',True)); available=enabled and _platform_ok(server)
        if not include_disabled and not available: continue
        sid=str(server.get('id') or server.get('name') or 'mcp')
        for t in server.get('tools',[]):
            if isinstance(t,str): item={'name':t,'description':'','permission':'unknown'}
            elif isinstance(t,dict) and t.get('name'): item=dict(t)
            else: continue
            out.append({**item,'server':sid,'external':True,'enabled':enabled,'available':available,'platform_ok':_platform_ok(server)})
    return out


def list_tools(session_id: str='default', skill_permissions: dict|None=None, include_disabled: bool=True) -> list[dict]:
    tools=[{**x,'available':True,'enabled':True} for x in BUILTIN_TOOLS]+_external_tools(include_disabled)
    return [perms.classify_tool(x,skill_permissions,session_id) for x in tools]


def probe_server(sid: str, force: bool=False) -> dict:
    if sid=='builtin': return {'id':'builtin','name':'KimiK3 Local Tools','status':'ready','ok':True,'tools':len(BUILTIN_TOOLS),'transport':'in-process'}
    server=_server(sid)
    if not server: return {'id':sid,'status':'missing','ok':False,'tools':0}
    base={'id':sid,'name':str(server.get('name') or sid),'transport':str(server.get('transport') or 'stdio'),'enabled':bool(server.get('enabled',True)),'platform_ok':_platform_ok(server)}
    if not base['enabled']: return {**base,'ok':False,'status':'disabled','tools':len(server.get('tools') or [])}
    if not base['platform_ok']: return {**base,'ok':False,'status':'unsupported','tools':len(server.get('tools') or [])}
    now=time.time(); cached=_PROBE_CACHE.get(sid)
    if cached and not force and now-cached[0]<15: return cached[1]
    if server.get('transport')!='stdio': result={**base,'ok':False,'status':'unsupported_transport','tools':len(server.get('tools') or [])}
    else:
        p=transport.probe(server,5.0); result={**base,**p,'tools':p.get('count',0)}
    _PROBE_CACHE[sid]=(now,result); return result


def list_servers(probe: bool=False) -> list[dict]:
    out=[probe_server('builtin')]
    for s in config().get('servers',[]):
        if not isinstance(s,dict): continue
        sid=str(s.get('id') or s.get('name') or 'mcp')
        if probe: out.append(probe_server(sid))
        else:
            out.append({'id':sid,'name':str(s.get('name') or sid),'transport':str(s.get('transport') or 'stdio'),'enabled':bool(s.get('enabled',True)),'platform_ok':_platform_ok(s),'status':'configured' if s.get('enabled',True) and _platform_ok(s) else ('unsupported' if not _platform_ok(s) else 'disabled'),'tools':len(s.get('tools') or [])})
    return out


def _indexed_paths() -> set[Path]:
    out=set()
    if not INDEX.exists(): return out
    for line in INDEX.read_text(encoding='utf-8',errors='ignore').splitlines():
        try:
            p=Path(json.loads(line).get('path','')).expanduser().resolve()
            if p.exists(): out.add(p)
        except Exception: pass
    return out


def _allowed_read(path: Path) -> bool:
    p=path.expanduser().resolve()
    try:
        if p==ROOT or ROOT in p.parents: return True
    except Exception: pass
    return p in _indexed_paths()


def _search_index(query: str, top_k: int=6) -> list[dict]:
    import kimik3_lite as core
    return core.retrieve(query,max(1,min(int(top_k),12)))


def _context_stats(session_id: str='default') -> dict:
    import kimik3_lite as core
    return core.context_status(session_id=session_id)


def _normalize_external(value: Any) -> Any:
    if not isinstance(value,dict): return value
    if 'structuredContent' in value: return value['structuredContent']
    content=value.get('content')
    if isinstance(content,list):
        texts=[str(x.get('text','')) for x in content if isinstance(x,dict) and x.get('type')=='text']
        if texts:
            joined='\n'.join(texts)
            try: return json.loads(joined)
            except Exception: return joined
    return value


def call_tool(name: str, arguments: dict[str,Any]|None=None, session_id: str='default', skill_permissions: dict|None=None) -> dict:
    arguments=arguments or {}
    tool=next((x for x in [{**b,'available':True,'enabled':True} for b in BUILTIN_TOOLS]+_external_tools(True) if x.get('name')==name),None)
    if not tool: return {'ok':False,'error':'unknown_tool','tool':name}
    gate=perms.classify_tool(tool,skill_permissions,session_id)
    if gate['decision']=='deny': return {'ok':False,'status':'denied','tool':name,'permission':gate['permission'],'risk':gate['risk']}
    if gate['decision']=='confirm': return {'ok':False,'status':'needs_confirmation','tool':name,'permission':gate['permission'],'risk':gate['risk']}
    if tool.get('external') and not tool.get('available'):
        return {'ok':False,'status':'unavailable','tool':name,'server':tool.get('server')}
    try:
        if name=='project.search': result=_search_index(str(arguments.get('query','')),int(arguments.get('top_k',6)))
        elif name=='filesystem.read_text':
            p=Path(str(arguments.get('path','')))
            if not _allowed_read(p): return {'ok':False,'status':'denied','tool':name,'error':'path_not_allowed'}
            result=p.read_text(encoding='utf-8',errors='ignore')[:20000]
        elif name=='filesystem.list':
            p=Path(str(arguments.get('path') or ROOT)).expanduser().resolve()
            if not (p==ROOT or ROOT in p.parents): return {'ok':False,'status':'denied','tool':name,'error':'path_not_allowed'}
            result=[{'name':x.name,'type':'dir' if x.is_dir() else 'file'} for x in sorted(p.iterdir())[:300]]
        elif name=='context.stats': result=_context_stats(session_id)
        elif tool.get('external'):
            server=_server(str(tool.get('server')))
            if not server: return {'ok':False,'status':'missing_server','tool':name}
            if server.get('transport')!='stdio': return {'ok':False,'status':'unsupported_transport','tool':name}
            result=_normalize_external(transport.call(server,name,arguments,25.0))
        else: return {'ok':False,'error':'not_implemented','tool':name}
        return {'ok':True,'status':'done','tool':name,'server':tool.get('server'),'result':result}
    except Exception as exc:
        return {'ok':False,'status':'error','tool':name,'server':tool.get('server'),'error':str(exc)}


def self_test() -> None:
    names={x['name'] for x in list_tools()}
    assert {'project.search','filesystem.read_text','context.stats'}<=names
    assert call_tool('filesystem.list',{'path':str(ROOT)})['ok']
    assert call_tool('context.stats',{})['ok']
    assert call_tool('unknown',{})['error']=='unknown_tool'
    servers=list_servers(False); assert any(x['id']=='computer' for x in servers)
    print('PASS: MCP gateway')


if __name__=='__main__': self_test()
