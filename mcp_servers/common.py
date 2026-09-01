#!/usr/bin/env python3
from __future__ import annotations
import json, sys, traceback
from typing import Callable, Any


def text_result(text: str, structured: Any=None) -> dict:
    out={'content':[{'type':'text','text':str(text)}]}
    if structured is not None: out['structuredContent']=structured
    return out


class Server:
    def __init__(self,name: str,version: str='1.0.0'):
        self.name=name; self.version=version; self.tools: dict[str,dict]={}; self.handlers: dict[str,Callable]={}

    def tool(self,name: str,description: str,input_schema: dict|None=None):
        def deco(fn: Callable):
            self.tools[name]={'name':name,'description':description,'inputSchema':input_schema or {'type':'object','properties':{}}}
            self.handlers[name]=fn; return fn
        return deco

    def response(self,rid,result=None,error=None):
        obj={'jsonrpc':'2.0','id':rid}
        if error is not None: obj['error']={'code':-32000,'message':str(error)}
        else: obj['result']=result
        sys.stdout.write(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n'); sys.stdout.flush()

    def handle(self,msg: dict):
        if 'id' not in msg: return
        rid=msg.get('id'); method=msg.get('method'); params=msg.get('params') or {}
        try:
            if method=='initialize':
                return self.response(rid,{'protocolVersion':params.get('protocolVersion','2025-06-18'),'capabilities':{'tools':{'listChanged':False}},'serverInfo':{'name':self.name,'version':self.version}})
            if method=='tools/list': return self.response(rid,{'tools':list(self.tools.values())})
            if method=='tools/call':
                name=str(params.get('name','')); fn=self.handlers.get(name)
                if not fn: return self.response(rid,error='Unknown tool: '+name)
                value=fn(params.get('arguments') or {})
                if isinstance(value,dict) and ('content' in value or 'structuredContent' in value): result=value
                else: result=text_result(json.dumps(value,ensure_ascii=False) if not isinstance(value,str) else value,value)
                return self.response(rid,result)
            return self.response(rid,error='Unsupported method: '+str(method))
        except Exception as exc:
            print(traceback.format_exc(),file=sys.stderr,flush=True)
            return self.response(rid,error=str(exc))

    def run(self):
        for line in sys.stdin:
            line=line.strip()
            if not line: continue
            try: msg=json.loads(line)
            except Exception: continue
            self.handle(msg)


def run(server: Server): server.run()
