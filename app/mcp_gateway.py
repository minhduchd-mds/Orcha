#!/usr/bin/env python3
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any

import permission_engine as perms

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('KIMIK3_DATA_DIR', str(ROOT/'data'))).expanduser()
CONFIG = ROOT / 'config' / 'mcp.json'
INDEX = DATA / 'index.jsonl'

BUILTIN_TOOLS = [
    {'name':'project.search','description':'Search indexed local project context.','permission':'project.search','server':'builtin'},
    {'name':'filesystem.read_text','description':'Read a repository file or an exact file already indexed by KimiK3.','permission':'filesystem.read','server':'builtin'},
    {'name':'filesystem.list','description':'List a directory inside the KimiK3 repository.','permission':'filesystem.list','server':'builtin'},
    {'name':'context.stats','description':'Read context inventory and limits.','permission':'context.read','server':'builtin'},
]


def config() -> dict:
    try:
        x = json.loads(CONFIG.read_text(encoding='utf-8'))
        return x if isinstance(x, dict) else {'servers': []}
    except Exception:
        return {'version': 1, 'servers': []}


def _external_tools() -> list[dict]:
    out=[]
    for server in config().get('servers', []):
        if not isinstance(server, dict) or not server.get('enabled', True):
            continue
        sid=str(server.get('id') or server.get('name') or 'mcp')
        for t in server.get('tools', []):
            if isinstance(t, str):
                out.append({'name':t,'description':'','permission':'confirm','server':sid,'external':True})
            elif isinstance(t, dict) and t.get('name'):
                out.append({**t,'server':sid,'external':True})
    return out


def list_tools(session_id: str='default', skill_permissions: dict|None=None) -> list[dict]:
    return [perms.classify_tool(x, skill_permissions, session_id) for x in BUILTIN_TOOLS + _external_tools()]


def list_servers() -> list[dict]:
    return [{'id':'builtin','name':'KimiK3 Local Tools','transport':'in-process','enabled':True,'status':'ready','tools':len(BUILTIN_TOOLS)}] + [
        {
            'id': str(s.get('id') or s.get('name') or 'mcp'),
            'name': str(s.get('name') or s.get('id') or 'MCP Server'),
            'transport': str(s.get('transport') or 'stdio'),
            'enabled': bool(s.get('enabled', True)),
            'status': 'configured' if s.get('enabled', True) else 'disabled',
            'tools': len(s.get('tools') or []),
        }
        for s in config().get('servers', []) if isinstance(s, dict)
    ]


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
        if p == ROOT or ROOT in p.parents: return True
    except Exception: pass
    return p in _indexed_paths()


def _search_index(query: str, top_k: int=6) -> list[dict]:
    import kimik3_lite as core
    return core.retrieve(query, max(1,min(int(top_k),12)))


def _context_stats(session_id: str='default') -> dict:
    import kimik3_lite as core
    return core.context_status(session_id=session_id)


def call_tool(name: str, arguments: dict[str,Any]|None=None, session_id: str='default', skill_permissions: dict|None=None) -> dict:
    arguments=arguments or {}
    tool=next((x for x in BUILTIN_TOOLS + _external_tools() if x.get('name')==name),None)
    if not tool: return {'ok':False,'error':'unknown_tool','tool':name}
    gate=perms.classify_tool(tool,skill_permissions,session_id)
    if gate['decision']=='deny': return {'ok':False,'status':'denied','tool':name,'permission':gate['permission'],'risk':gate['risk']}
    if gate['decision']=='confirm': return {'ok':False,'status':'needs_confirmation','tool':name,'permission':gate['permission'],'risk':gate['risk']}
    if tool.get('external'):
        return {'ok':False,'status':'not_connected','tool':name,'server':tool.get('server'),'message':'External MCP transport is registered but execution is not enabled in Batch 1.'}
    try:
        if name=='project.search':
            result=_search_index(str(arguments.get('query','')),int(arguments.get('top_k',6)))
        elif name=='filesystem.read_text':
            p=Path(str(arguments.get('path','')))
            if not _allowed_read(p): return {'ok':False,'status':'denied','tool':name,'error':'path_not_allowed'}
            result=p.read_text(encoding='utf-8',errors='ignore')[:20000]
        elif name=='filesystem.list':
            p=Path(str(arguments.get('path') or ROOT)).expanduser().resolve()
            if not (p==ROOT or ROOT in p.parents): return {'ok':False,'status':'denied','tool':name,'error':'path_not_allowed'}
            result=[{'name':x.name,'type':'dir' if x.is_dir() else 'file'} for x in sorted(p.iterdir())[:300]]
        elif name=='context.stats': result=_context_stats(session_id)
        else: return {'ok':False,'error':'not_implemented','tool':name}
        return {'ok':True,'status':'done','tool':name,'result':result}
    except Exception as exc:
        return {'ok':False,'status':'error','tool':name,'error':str(exc)}


def self_test() -> None:
    names={x['name'] for x in list_tools()}
    assert {'project.search','filesystem.read_text','context.stats'} <= names
    assert call_tool('filesystem.list',{'path':str(ROOT)})['ok']
    assert call_tool('context.stats',{})['ok']
    assert call_tool('unknown',{})['error']=='unknown_tool'
    print('PASS: MCP gateway')


if __name__=='__main__': self_test()
