#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

import studio_server_v66 as v66
import agent_team as team

class H67(v66.H66):
    def _team_index(self):
        p=Path(v66.v65.core.ROOT)/'studio'/'index.html';text=p.read_text(encoding='utf-8')
        text=text.replace('</head>','<link rel="stylesheet" href="/parallel-agents.css"><link rel="stylesheet" href="/agent-team.css"></head>')
        text=text.replace('</body>','<script src="/parallel-agents.js"></script><script src="/agent-team.js"></script></body>')
        text=text.replace('Local Workspace · v6.4','Local Workspace · v6.7')
        raw=text.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path in {'/','/index.html'}:return self._team_index()
        if path=='/health':
            c=team.capacity();return self.send_json(200,{'ok':True,'version':'6.7.0','agent_team':True,'dependency_graph':True,'shared_memory':True,'conflict_resolver':True,'max_team_agents':c['max_team_agents'],'max_parallel':c.get('workers'),'serial_write':True})
        if path=='/api/agents/team/capacity':return self.send_json(200,team.capacity())
        if path.startswith('/api/agents/team/runs/'):
            r=team.get(path.rsplit('/',1)[-1]);return self.send_json(200,r) if r else self.send_json(404,{'error':'Không tìm thấy team run'})
        return super().do_GET()
    def do_POST(self):
        path=urlsplit(self.path).path
        if path.startswith('/api/agents/team/'):
            try:b=self.body()
            except Exception:return self.send_json(400,{'error':'invalid json'})
            try:
                q=str(b.get('message') or b.get('query') or '').strip();workers=b.get('workers')
                if path=='/api/agents/team/plan':
                    if not q:return self.send_json(400,{'error':'Thiếu query'})
                    return self.send_json(200,team.plan(q,workers))
                if path=='/api/agents/team/run':
                    if not q:return self.send_json(400,{'error':'Thiếu query'})
                    return self.send_json(200,team.run(q,str(b.get('profile') or self.server.profile),b.get('model') or None,self.server.ollama,str(b.get('session_id') or 'default'),workers))
            except Exception as e:return self.send_json(409,{'error':str(e)})
        return super().do_POST()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=11435);ap.add_argument('--ollama',default='http://127.0.0.1:11434');ap.add_argument('--profile',default='balanced');ap.add_argument('--model');a=ap.parse_args();cfg=v66.v65.v64.legacy.profiles().get(a.profile) or v66.v65.v64.legacy.profiles()['balanced'];v66.v65.v64.legacy.workflows.ensure();v66.v65.v64.legacy.start_ollama(a.ollama);srv=ThreadingHTTPServer((a.host,a.port),H67);srv.ollama=a.ollama;srv.profile=a.profile;srv.model=a.model or cfg['ollama_name'];srv.model_mode='auto';print(f'Orcha v6.7 Studio http://{a.host}:{a.port}');srv.serve_forever()
if __name__=='__main__':main()
