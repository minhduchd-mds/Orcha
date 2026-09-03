#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

import studio_server_v65 as v65
import parallel_agent as parallel

class H66(v65.H65):
    def _parallel_index(self):
        p=Path(v65.core.ROOT)/'studio'/'index.html'
        text=p.read_text(encoding='utf-8')
        text=text.replace('</head>','<link rel="stylesheet" href="/parallel-agents.css"></head>')
        text=text.replace('</body>','<script src="/parallel-agents.js"></script></body>')
        text=text.replace('Local Workspace · v6.4','Local Workspace · v6.6')
        raw=text.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path in {'/','/index.html'}:return self._parallel_index()
        if path=='/health':
            guard=parallel.worker_limit();return self.send_json(200,{'ok':True,'version':'6.6.0','design_agent':True,'parallel_agents':True,'parallel_policy':'ram-aware-read-only','max_parallel':guard.get('workers'),'ram_gb':guard.get('ram_gb'),'serial_write':True})
        if path.startswith('/api/agents/parallel/runs/'):
            r=parallel.get(path.rsplit('/',1)[-1]);return self.send_json(200,r) if r else self.send_json(404,{'error':'Không tìm thấy parallel run'})
        if path=='/api/agents/parallel/capacity':return self.send_json(200,parallel.worker_limit())
        return super().do_GET()
    def do_POST(self):
        path=urlsplit(self.path).path
        if path.startswith('/api/agents/parallel/'):
            try:b=self.body()
            except Exception:return self.send_json(400,{'error':'invalid json'})
            try:
                q=str(b.get('message') or b.get('query') or '').strip();workers=b.get('workers')
                if path=='/api/agents/parallel/plan':
                    if not q:return self.send_json(400,{'error':'Thiếu query'})
                    return self.send_json(200,parallel.plan(q,workers))
                if path=='/api/agents/parallel/run':
                    if not q:return self.send_json(400,{'error':'Thiếu query'})
                    profile=str(b.get('profile') or self.server.profile);model=b.get('model') or None;session=str(b.get('session_id') or 'default')
                    return self.send_json(200,parallel.run(q,profile,model,self.server.ollama,session,workers))
            except Exception as e:return self.send_json(409,{'error':str(e)})
        return super().do_POST()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=11435);ap.add_argument('--ollama',default='http://127.0.0.1:11434');ap.add_argument('--profile',default='balanced');ap.add_argument('--model');a=ap.parse_args();cfg=v65.v64.legacy.profiles().get(a.profile) or v65.v64.legacy.profiles()['balanced'];v65.v64.legacy.workflows.ensure();v65.v64.legacy.start_ollama(a.ollama);srv=ThreadingHTTPServer((a.host,a.port),H66);srv.ollama=a.ollama;srv.profile=a.profile;srv.model=a.model or cfg['ollama_name'];srv.model_mode='auto';print(f'Orcha v6.6 Studio http://{a.host}:{a.port}');srv.serve_forever()
if __name__=='__main__':main()
