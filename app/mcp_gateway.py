#!/usr/bin/env python3
from __future__ import annotations
import storage
import json, sys, time
import threading
from pathlib import Path
from typing import Any
import mcp_transport as transport
import permission_engine as perms

ROOT=Path(__file__).resolve().parents[1];DATA=storage.DATA;CONFIG=ROOT/'config'/'mcp.json'
_PROBE_CACHE={};WRITE_LOCK=threading.RLock()
READ_PERMISSIONS=frozenset({'project.search','filesystem.read','filesystem.list','context.read','memory.read','git.read','browser.read','computer.read'})
BUILTIN_TOOLS=[
 {'name':'project.search','description':'Search indexed local project context.','permission':'project.search','server':'builtin'},
 {'name':'filesystem.read_text','description':'Read a repository file or an exact file already indexed by Orcha.','permission':'filesystem.read','server':'builtin'},
 {'name':'filesystem.list','description':'List a directory inside the Orcha repository.','permission':'filesystem.list','server':'builtin'},
 {'name':'context.stats','description':'Read context inventory and limits.','permission':'context.read','server':'builtin'}]

def config():
    try:
        x=json.loads(CONFIG.read_text(encoding='utf-8'));return x if isinstance(x,dict) else {'version':2,'servers':[]}
    except Exception:return {'version':2,'servers':[]}
def _platform_ok(server):
    platforms=server.get('platforms') or [];return not platforms or sys.platform in [str(x) for x in platforms]
def _server(sid):return next((s for s in config().get('servers',[]) if isinstance(s,dict) and str(s.get('id'))==sid),None)
def _external_tools(include_disabled=True):
    out=[]
    for server in config().get('servers',[]):
        if not isinstance(server,dict):continue
        enabled=bool(server.get('enabled',True));available=enabled and _platform_ok(server)
        if not include_disabled and not available:continue
        sid=str(server.get('id') or server.get('name') or 'mcp')
        for t in server.get('tools',[]):
            if isinstance(t,str):item={'name':t,'description':'','permission':'unknown'}
            elif isinstance(t,dict) and t.get('name'):item=dict(t)
            else:continue
            out.append({**item,'server':sid,'external':True,'enabled':enabled,'available':available,'platform_ok':_platform_ok(server)})
    return out

def list_tools(session_id='default',skill_permissions=None,include_disabled=True):
    tools=[{**x,'available':True,'enabled':True} for x in BUILTIN_TOOLS]+_external_tools(include_disabled)
    for tool in tools:tool['inputSchema']=tool_schema(tool['name'])
    return [perms.classify_tool(x,skill_permissions,session_id) for x in tools]

_SCHEMA_CACHE={}
def tool_schema(name):
    if not _SCHEMA_CACHE:
        import ast
        for path in (ROOT/'mcp_servers').glob('*_server.py'):
            tree=ast.parse(path.read_text(encoding='utf-8'))
            for node in tree.body:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    for dec in node.decorator_list:
                        if isinstance(dec,ast.Call) and isinstance(dec.func,ast.Attribute) and dec.func.attr=='tool':
                            try:_SCHEMA_CACHE[ast.literal_eval(dec.args[0])]=ast.literal_eval(dec.args[2]) if len(dec.args)>2 else {'type':'object','properties':{}}
                            except (ValueError,TypeError):pass
        _SCHEMA_CACHE.update({'project.search':{'type':'object','required':['query'],'properties':{'query':{'type':'string'},'top_k':{'type':'integer'}}},'filesystem.read_text':{'type':'object','required':['path'],'properties':{'path':{'type':'string'}}},'filesystem.list':{'type':'object','properties':{'path':{'type':'string'}}},'context.stats':{'type':'object','properties':{}}})
    return _SCHEMA_CACHE.get(name,{'type':'object','properties':{}})

def probe_server(sid,force=False):
    if sid=='builtin':return {'id':'builtin','name':'Orcha Local Tools','status':'ready','ok':True,'tools':len(BUILTIN_TOOLS),'transport':'in-process'}
    server=_server(sid)
    if not server:return {'id':sid,'status':'missing','ok':False,'tools':0}
    base={'id':sid,'name':str(server.get('name') or sid),'transport':str(server.get('transport') or 'stdio'),'enabled':bool(server.get('enabled',True)),'platform_ok':_platform_ok(server)}
    if not base['enabled']:return {**base,'ok':False,'status':'disabled','tools':len(server.get('tools') or [])}
    if not base['platform_ok']:return {**base,'ok':False,'status':'unsupported','tools':len(server.get('tools') or [])}
    now=time.time();cached=_PROBE_CACHE.get(sid)
    if cached and not force and now-cached[0]<15:return cached[1]
    if server.get('transport')!='stdio':result={**base,'ok':False,'status':'unsupported_transport','tools':len(server.get('tools') or [])}
    else:
        p=transport.probe(server,5.0);result={**base,**p,'tools':p.get('count',0)}
    _PROBE_CACHE[sid]=(now,result);return result

def list_servers(probe=False):
    out=[probe_server('builtin')]
    for s in config().get('servers',[]):
        if not isinstance(s,dict):continue
        sid=str(s.get('id') or s.get('name') or 'mcp')
        if probe:out.append(probe_server(sid))
        else:out.append({'id':sid,'name':str(s.get('name') or sid),'transport':str(s.get('transport') or 'stdio'),'enabled':bool(s.get('enabled',True)),'platform_ok':_platform_ok(s),'status':'configured' if s.get('enabled',True) and _platform_ok(s) else ('unsupported' if not _platform_ok(s) else 'disabled'),'tools':len(s.get('tools') or [])})
    return out

def _indexed_paths():
    import orcha_core as core
    return {Path(row['path']).expanduser().resolve() for row in core.load_index() if row.get('path')}
def _allowed_read(path):
    import orcha_core as core
    p=path.expanduser().resolve()
    if not p.is_file() or p.stat().st_size>2*1024*1024:return False
    if p.name.startswith('.env') or '.git' in p.parts or p.is_relative_to(DATA):return False
    if core._PROJECT.get() is not None:return p in _indexed_paths()
    return p.is_relative_to(ROOT) or p in _indexed_paths()
def _search_index(query,top_k=6):
    import orcha_core as core
    return core.retrieve(query,max(1,min(int(top_k),12)))
def _context_stats(session_id='default'):
    import orcha_core as core
    return core.context_status(session_id=session_id)
def _normalize_external(value):
    if not isinstance(value,dict):return value
    if value.get('isError'):raise transport.MCPError('External tool reported failure: '+str(value.get('content',''))[:1000])
    if 'structuredContent' in value:return value['structuredContent']
    content=value.get('content')
    if isinstance(content,list):
        texts=[str(x.get('text','')) for x in content if isinstance(x,dict) and x.get('type')=='text']
        if texts:
            joined='\n'.join(texts)
            try:return json.loads(joined)
            except Exception:return joined
    return value

def call_tool(name,arguments=None,session_id='default',skill_permissions=None,read_only=False,action_key=None):
    arguments=arguments or {};tool=next((x for x in [{**b,'available':True,'enabled':True} for b in BUILTIN_TOOLS]+_external_tools(True) if x.get('name')==name),None)
    if not tool:return {'ok':False,'error':'unknown_tool','tool':name}
    gate=perms.classify_tool(tool,skill_permissions,session_id)
    if read_only and gate['permission'] not in READ_PERMISSIONS:return {'ok':False,'status':'denied','tool':name,'error':'read_only_execution'}
    if gate['decision']=='deny':return {'ok':False,'status':'denied','tool':name,'permission':gate['permission'],'risk':gate['risk']}
    if gate['decision']=='confirm' and not perms.action_granted(gate['permission'],session_id,action_key,consume=True):return {'ok':False,'status':'needs_confirmation','tool':name,'permission':gate['permission'],'risk':gate['risk']}
    if tool.get('external') and not tool.get('available'):return {'ok':False,'status':'unavailable','tool':name,'server':tool.get('server')}
    try:
        validate_arguments(tool_schema(name),arguments)
        if name=='project.search':result=_search_index(str(arguments.get('query','')),int(arguments.get('top_k',6)))
        elif name=='filesystem.read_text':
            p=Path(str(arguments.get('path',''))).expanduser().resolve()
            if not _allowed_read(p):return {'ok':False,'status':'denied','tool':name,'error':'path_not_allowed'}
            result=p.read_text(encoding='utf-8',errors='ignore')[:20000]
        elif name=='filesystem.list':
            p=Path(str(arguments.get('path') or ROOT)).expanduser().resolve()
            if not (p==ROOT or ROOT in p.parents):return {'ok':False,'status':'denied','tool':name,'error':'path_not_allowed'}
            result=[{'name':x.name,'type':'dir' if x.is_dir() else 'file'} for x in sorted(p.iterdir())[:300]]
        elif name=='context.stats':result=_context_stats(session_id)
        elif tool.get('external'):
            server=_server(str(tool.get('server')))
            if not server:return {'ok':False,'status':'missing_server','tool':name}
            if server.get('transport')!='stdio':return {'ok':False,'status':'unsupported_transport','tool':name}
            with WRITE_LOCK if gate['permission'] not in READ_PERMISSIONS else __import__('contextlib').nullcontext():result=_normalize_external(transport.call(server,name,arguments,25.0))
        else:return {'ok':False,'error':'not_implemented','tool':name}
        return {'ok':True,'status':'done','tool':name,'server':tool.get('server'),'result':result}
    except Exception as exc:return {'ok':False,'status':'error','tool':name,'server':tool.get('server'),'error':str(exc)}

def validate_arguments(schema,args):
    import math
    def check(spec,value,path):
        types={'string':str,'integer':int,'number':(int,float),'array':list,'object':dict,'boolean':bool};kind=spec.get('type');expected=types.get(kind)
        if expected and (not isinstance(value,expected) or isinstance(value,bool) and kind in {'integer','number'}):raise ValueError('Invalid argument type: '+path)
        if 'enum' in spec and value not in spec['enum']:raise ValueError('Invalid argument value: '+path)
        if isinstance(value,float) and not math.isfinite(value):raise ValueError('Nonfinite argument: '+path)
        if isinstance(value,dict):
            for key in spec.get('required',[]):
                if key not in value:raise ValueError('Missing argument: '+path+'.'+key)
            properties=spec.get('properties',{})
            for key,item in value.items():
                if spec.get('additionalProperties') is False and key not in properties:raise ValueError('Unknown argument: '+path+'.'+key)
                check(properties.get(key,{}),item,path+'.'+key)
        if isinstance(value,list):
            if len(value)<spec.get('minItems',0) or len(value)>spec.get('maxItems',10000):raise ValueError('Invalid array size: '+path)
            for i,item in enumerate(value):check(spec.get('items',{}),item,path+'['+str(i)+']')
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            if value<spec.get('minimum',float('-inf')) or value>spec.get('maximum',float('inf')):raise ValueError('Argument outside limits: '+path)
    if not isinstance(args,dict):raise ValueError('Tool arguments must be an object')
    check(schema,args,'arguments')

def self_test():
    names={x['name'] for x in list_tools()};assert {'project.search','filesystem.read_text','context.stats'}<=names;assert call_tool('filesystem.list',{'path':str(ROOT)})['ok'];assert call_tool('context.stats',{})['ok'];assert call_tool('unknown',{})['error']=='unknown_tool';servers=list_servers(False);assert any(x['id']=='computer' for x in servers);print('PASS: MCP gateway')
if __name__=='__main__':self_test()
