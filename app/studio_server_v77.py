#!/usr/bin/env python3
from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

import data_sync
import harness_runtime as harness
import studio_server_v70 as v70


class H77(v70.H70):
    def do_GET(self):
        if urlsplit(self.path).path == '/health':
            return self.send_json(200,{
                'ok':True,
                'product':'Orcha',
                'category':'Autonomous Work Platform',
                'version':'7.7.0',
                'ui_foundation':True,
                'ui_contract':True,
                'visual_baseline':'kimi-derived-orcha',
                'claude_frontend_quality_rules':True,
                'claude_can_override_visual_baseline':False,
                'outline_icons':True,
                'product_copy':'Orcha',
                'inspector_toggle':True,
                'icon_composer':True,
                'native_prompt_free_data_hub':True,
                'reference_lab':True,
                'local_first':True,
                'hybrid_data':True,
                'mobile_runtime_foundation':True,
                'hermes_foundation':True,
                'deepseek_harness_patterns':True,
                'event_sourced_runs':True,
                'crash_recovery':True,
                'tool_result_spill':True,
                'verification_recipes':True,
                'project_workspace':True,
                'autonomous_project_planner':True,
                'project_executor_supervisor':True,
                'auto_read_only_tasks':True,
                'write_background_execution':False,
                'persistent_tasks':True,
                'resume':True,
                'approval_inbox':True,
                'checkpoints':True,
                'planner_write_requires_approval':True,
                'permission_engine_authoritative':True,
                'api_security':True,
                'data_sync':data_sync.status(),
                'harness':harness.status(),
            })
        return super().do_GET()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--host',default='127.0.0.1')
    ap.add_argument('--port',type=int,default=11435)
    ap.add_argument('--ollama',default='http://127.0.0.1:11434')
    ap.add_argument('--profile',default='balanced')
    ap.add_argument('--model')
    a=ap.parse_args()
    cfg=v70.v69._legacy_v64().legacy.profiles().get(a.profile) or v70.v69._legacy_v64().legacy.profiles()['balanced']
    v70.v69._legacy_v64().legacy.workflows.ensure()
    recovered=harness.recover_incomplete()
    v70.v69._legacy_v64().legacy.start_ollama(a.ollama)
    data_sync.Scheduler().start()
    srv=ThreadingHTTPServer((a.host,a.port),H77)
    srv.ollama=a.ollama
    srv.profile=a.profile
    srv.model=a.model or cfg['ollama_name']
    srv.model_mode='auto'
    print(f'Orcha v7.7 http://{a.host}:{a.port} · recovered={len(recovered)} · UI Contract=locked · outline icons=on')
    srv.serve_forever()


if __name__=='__main__':
    main()
