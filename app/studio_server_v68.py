#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

import studio_server_v67 as v67
import self_improvement as learn
import maintenance

class H68(v67.H67):
    def _index68(self):
        p=Path(v67.v66.v65.core.ROOT)/'studio'/'index.html';text=p.read_text(encoding='utf-8')
        text=text.replace('</head>','<link rel="stylesheet" href="/parallel-agents.css"><link rel="stylesheet" href="/agent-team.css"><link rel="stylesheet" href="/final-intelligence.css"></head>')
        text=text.replace('</body>','<script src="/parallel-agents.js"></script><script src="/agent-team.js"></script><script src="/final-intelligence.js"></script></body>')
        text=text.replace('Local Workspace · v6.4','Local Workspace · v6.8')
        raw=text.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path in {'/','/index.html'}:return self._index68()
        if path=='/health':
            c=v67.team.capacity();return self.send_json(200,{'ok':True,'version':'6.8.0','agent_team':True,'safe_learning':True,'performance_dashboard':True,'backup':True,'security_audit':True,'max_parallel':c.get('workers'),'self_modify_code':False,'auto_permission_escalation':False})
        if path=='/api/learning/dashboard':return self.send_json(200,learn.dashboard())
        if path=='/api/learning/lessons':return self.send_json(200,learn.recent_lessons(50))
        if path=='/api/maintenance/security':return self.send_json(200,maintenance.security_audit())
        if path=='/api/maintenance/backups':return self.send_json(200,maintenance.list_backups())
        return super().do_GET()
    def do_POST(self):
        path=urlsplit(self.path).path
        if path.startswith('/api/learning/') or path.startswith('/api/maintenance/'):
            try:b=self.body()
            except Exception:return self.send_json(400,{'error':'invalid json'})
            try:
                if path=='/api/learning/outcome':return self.send_json(200,learn.record(b))
                if path=='/api/learning/recommend':
                    ram=float(b.get('ram_gb') or v67.team.capacity().get('ram_gb') or 4);return self.send_json(200,learn.recommend(str(b.get('task_type') or 'general'),ram))
                if path=='/api/maintenance/backup':return self.send_json(200,maintenance.backup())
                if path=='/api/maintenance/security/run':return self.send_json(200,maintenance.security_audit())
            except Exception as e:return self.send_json(409,{'error':str(e)})
        return super().do_POST()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=11435);ap.add_argument('--ollama',default='http://127.0.0.1:11434');ap.add_argument('--profile',default='balanced');ap.add_argument('--model');a=ap.parse_args();cfg=v67.v66.v65.v64.legacy.profiles().get(a.profile) or v67.v66.v65.v64.legacy.profiles()['balanced'];v67.v66.v65.v64.legacy.workflows.ensure();v67.v66.v65.v64.legacy.start_ollama(a.ollama);srv=ThreadingHTTPServer((a.host,a.port),H68);srv.ollama=a.ollama;srv.profile=a.profile;srv.model=a.model or cfg['ollama_name'];srv.model_mode='auto';print(f'Orcha v6.8 Studio http://{a.host}:{a.port}');srv.serve_forever()
if __name__=='__main__':main()
