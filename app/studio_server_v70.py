#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import data_sync
import harness_runtime as harness
import kimik3_lite as core
import mobile_runtime
import project_workspace as projects
import project_planner as planner
import project_supervisor as supervisor
import reference_catalog
import studio_server_v69 as v69
import verification_engine as verifier


def _limit(query: dict, key: str, default: int, maximum: int) -> int:
    try:return max(1,min(int(query.get(key,[str(default)])[0]),maximum))
    except (TypeError,ValueError):return default


def _orcha_text(value):
    if not isinstance(value,str):return value
    return value.replace('KimiK3-Lite','Orcha').replace('KimiK3 Lite','Orcha').replace('KimiK3','Orcha')

# Legacy local model names may still carry the old product identity in their Modelfile.
# Normalize only the product-name surface in returned answers; do not rewrite evidence/tool output.
_legacy_answer_query=core.answer_query
def _brand_safe_answer(*args,**kwargs):
    result=_legacy_answer_query(*args,**kwargs)
    if isinstance(result,dict) and isinstance(result.get('answer'),str):result['answer']=_orcha_text(result['answer'])
    return result
core.answer_query=_brand_safe_answer

class H70(v69.H69):
    def _index70(self):
        p=Path(core.ROOT)/'studio'/'index.html';text=p.read_text(encoding='utf-8')
        text=text.replace('</head>','<link rel="stylesheet" href="/parallel-agents.css"><link rel="stylesheet" href="/agent-team.css"><link rel="stylesheet" href="/final-intelligence.css"><link rel="stylesheet" href="/hermes.css"><link rel="stylesheet" href="/harness.css"><link rel="stylesheet" href="/project-workspace.css"><link rel="stylesheet" href="/project-planner.css"><link rel="stylesheet" href="/project-supervisor.css"><link rel="stylesheet" href="/orcha-hybrid.css"><link rel="stylesheet" href="/ui-foundation.css"><link rel="stylesheet" href="/plugin-center.css"></head>')
        text=text.replace('</body>','<script src="/parallel-agents.js"></script><script src="/agent-team.js"></script><script src="/final-intelligence.js"></script><script src="/hermes.js"></script><script src="/harness.js"></script><script src="/project-workspace.js"></script><script src="/project-planner.js"></script><script src="/project-supervisor.js"></script><script src="/orcha-hybrid.js"></script><script src="/ui-foundation.js"></script><script src="/plugin-center.js"></script></body>')
        for old in ('Local Workspace · v6.4','Local Workspace · v6.8','Local Workspace · v7.0','Local Workspace · v7.2','Local Workspace · v7.3','Autonomous Work Platform · v7.4'):
            text=text.replace(old,'Autonomous Work Platform · v7.5')
        text=text.replace('KimiK3 Lite · Local Workspace','Orcha · Autonomous Work Platform').replace('<b>KimiK3 Lite</b>','<b>Orcha</b>').replace('<div class="logo">K</div>','<div class="logo">O</div>')
        text=text.replace('Anh muốn Kimi làm gì?','Anh muốn Orcha làm gì?').replace('Kimi cần quyền thực hiện','Orcha cần quyền thực hiện')
        text=text.replace('Local only','Hybrid · local-first').replace('Local intelligence','Orcha intelligence')
        raw=text.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        q=urlsplit(self.path);path=q.path;query=parse_qs(q.query)
        if path in {'/','/index.html'}:return self._index70()
        if path=='/health':return self.send_json(200,{'ok':True,'product':'Orcha','category':'Autonomous Work Platform','version':'7.5.0','ui_foundation':True,'inspector_toggle':True,'icon_composer':True,'native_prompt_free_data_hub':True,'reference_lab':True,'local_first':True,'hybrid_data':True,'mobile_runtime_foundation':True,'hermes_foundation':True,'deepseek_harness_patterns':True,'event_sourced_runs':True,'crash_recovery':True,'tool_result_spill':True,'verification_recipes':True,'project_workspace':True,'autonomous_project_planner':True,'project_executor_supervisor':True,'auto_read_only_tasks':True,'write_background_execution':False,'persistent_tasks':True,'resume':True,'approval_inbox':True,'checkpoints':True,'planner_write_requires_approval':True,'permission_engine_authoritative':True,'data_sync':data_sync.status(),'harness':harness.status()})
        if path=='/api/harness/status':return self.send_json(200,harness.status())
        if path=='/api/harness/events':return self.send_json(200,harness.events(str(query.get('session',['default'])[0]),_limit(query,'limit',100,500)))
        if path=='/api/harness/runs':return self.send_json(200,harness.runs(_limit(query,'limit',50,500)))
        if path=='/api/harness/recipes':return self.send_json(200,[{'id':x['id'],'label':x['label']} for x in verifier.recipes(core.ROOT)])
        if path=='/api/data/status':return self.send_json(200,data_sync.status())
        if path=='/api/data/sources':return self.send_json(200,data_sync.list_sources())
        if path=='/api/mobile/models':return self.send_json(200,mobile_runtime.catalog())
        if path=='/api/reference/plugins':return self.send_json(200,reference_catalog.load())
        if path=='/api/projects':return self.send_json(200,projects.list_projects())
        if path.startswith('/api/projects/'):
            parts=[x for x in path.split('/') if x]
            try:
                pid=parts[2]
                if len(parts)==3:return self.send_json(200,projects.get(pid))
                if len(parts)==4 and parts[3]=='resume':return self.send_json(200,projects.resume(pid))
                if len(parts)==4 and parts[3]=='ready':return self.send_json(200,projects.ready_tasks(pid))
                if len(parts)==4 and parts[3]=='supervisor':return self.send_json(200,supervisor.status(pid))
            except FileNotFoundError:return self.send_json(404,{'error':'Không tìm thấy project'})
            except Exception as e:return self.send_json(409,{'error':str(e)})
        return super().do_GET()
    def do_POST(self):
        path=urlsplit(self.path).path
        if path.startswith('/api/harness/'):
            try:b=self.body()
            except Exception:return self.send_json(400,{'error':'invalid json'})
            try:
                if path=='/api/harness/verify':return self.send_json(200,verifier.verify(core.ROOT,str(b.get('profile') or 'fast')))
                if path=='/api/harness/recover':return self.send_json(200,{'recovered':harness.recover_incomplete()})
            except Exception as exc:return self.send_json(409,{'error':str(exc)})
        if path=='/api/data/sources':
            try:b=self.body();return self.send_json(201,data_sync.save_source(b))
            except Exception as e:return self.send_json(409,{'error':str(e)})
        if path=='/api/data/sync':
            try:
                b=self.body();sid=str(b.get('source_id') or '')
                return self.send_json(200,data_sync.sync_source(sid) if sid else {'results':data_sync.sync_due(10**20)})
            except Exception as e:return self.send_json(409,{'error':str(e)})
        if path.startswith('/api/data/sources/') and path.endswith('/enabled'):
            try:b=self.body();sid=[x for x in path.split('/') if x][3];return self.send_json(200,data_sync.set_enabled(sid,bool(b.get('enabled'))))
            except Exception as e:return self.send_json(409,{'error':str(e)})
        if path=='/api/mobile/recommend':
            try:b=self.body();return self.send_json(200,mobile_runtime.recommend(b.get('device') or {},str(b.get('task') or ''),bool(b.get('has_image')),str(b.get('privacy') or 'balanced')))
            except Exception as e:return self.send_json(409,{'error':str(e)})
        if path=='/api/planner/plan':
            try:b=self.body();return self.send_json(200,planner.plan(str(b.get('goal') or ''),b.get('ram_gb')))
            except Exception as e:return self.send_json(409,{'error':str(e)})
        if path=='/api/projects' or path.startswith('/api/projects/'):
            try:b=self.body()
            except Exception:return self.send_json(400,{'error':'invalid json'})
            try:
                if path=='/api/projects':return self.send_json(201,projects.create(str(b.get('name') or ''),str(b.get('goal') or ''),b.get('id')))
                parts=[x for x in path.split('/') if x];pid=parts[2]
                if len(parts)==4 and parts[3]=='tasks':return self.send_json(201,projects.add_task(pid,str(b.get('title') or ''),str(b.get('description') or ''),b.get('depends_on') or [],bool(b.get('write_intent'))))
                if len(parts)==5 and parts[3]=='tasks':return self.send_json(200,projects.update_task(pid,parts[4],b))
                if len(parts)==4 and parts[3]=='approvals':return self.send_json(201,projects.request_approval(pid,str(b.get('task_id') or ''),str(b.get('summary') or ''),b.get('actions') or []))
                if len(parts)==5 and parts[3]=='approvals':return self.send_json(200,projects.resolve_approval(pid,parts[4],bool(b.get('approved'))))
                if len(parts)==4 and parts[3]=='checkpoint':return self.send_json(200,projects.checkpoint(pid,str(b.get('note') or '')))
                if len(parts)==4 and parts[3]=='materialize-plan':
                    p=b.get('plan') if isinstance(b.get('plan'),dict) else planner.plan(projects.get(pid).get('goal',''),b.get('ram_gb'))
                    return self.send_json(201,planner.materialize(projects,pid,p))
                if len(parts)==5 and parts[3]=='supervisor':
                    action=parts[4]
                    if action=='pause':return self.send_json(200,supervisor.pause(pid))
                    if action=='resume':return self.send_json(200,supervisor.resume(pid))
                    opts={'profile':str(b.get('profile') or self.server.profile),'model':b.get('model') or self.server.model,'host':self.server.ollama,'session_id':str(b.get('session_id') or 'project-supervisor')}
                    if action=='tick':return self.send_json(200,supervisor.tick(pid,**opts))
                    if action=='run':return self.send_json(200,supervisor.run_until_blocked(pid,int(b.get('max_steps') or 8),**opts))
            except FileNotFoundError:return self.send_json(404,{'error':'Không tìm thấy project/task/approval'})
            except Exception as e:return self.send_json(409,{'error':str(e)})
        return super().do_POST()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=11435);ap.add_argument('--ollama',default='http://127.0.0.1:11434');ap.add_argument('--profile',default='balanced');ap.add_argument('--model');a=ap.parse_args();cfg=v69._legacy_v64().legacy.profiles().get(a.profile) or v69._legacy_v64().legacy.profiles()['balanced'];v69._legacy_v64().legacy.workflows.ensure();recovered=harness.recover_incomplete();v69._legacy_v64().legacy.start_ollama(a.ollama);data_sync.Scheduler().start();srv=ThreadingHTTPServer((a.host,a.port),H70);srv.ollama=a.ollama;srv.profile=a.profile;srv.model=a.model or cfg['ollama_name'];srv.model_mode='auto';print(f'Orcha v7.5 http://{a.host}:{a.port} · recovered={len(recovered)} · UI Foundation=on · Reference Lab=on');srv.serve_forever()
if __name__=='__main__':main()
