#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import agent_team as team
import kimik3_lite as core
import studio_server_v70 as v70


def _limit(query: dict, key: str, default: int, maximum: int) -> int:
    try:
        return max(1, min(int(query.get(key, [str(default)])[0]), maximum))
    except (TypeError, ValueError):
        return default


class H71(v70.H70):
    def _index71(self):
        p = Path(core.ROOT) / 'studio' / 'index.html'
        text = p.read_text(encoding='utf-8')
        text = text.replace(
            '</head>',
            '<link rel="stylesheet" href="/parallel-agents.css">'
            '<link rel="stylesheet" href="/agent-team.css">'
            '<link rel="stylesheet" href="/final-intelligence.css">'
            '<link rel="stylesheet" href="/hermes.css">'
            '<link rel="stylesheet" href="/harness.css"></head>',
        )
        text = text.replace(
            '</body>',
            '<script src="/parallel-agents.js"></script>'
            '<script src="/agent-team.js"></script>'
            '<script src="/final-intelligence.js"></script>'
            '<script src="/hermes.js"></script>'
            '<script src="/harness.js"></script></body>',
        )
        text = text.replace('Local Workspace · v6.4', 'Local Workspace · v7.1')
        raw = text.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        q = urlsplit(self.path); path = q.path; query = parse_qs(q.query)
        if path in {'/', '/index.html'}:
            return self._index71()
        if path == '/health':
            return self.send_json(200, {
                'ok': True, 'version': '7.1.0', 'hermes_foundation': True,
                'deepseek_harness_patterns': True, 'durable_agent_team': True,
                'durable_mailbox': True, 'task_revision_cas': True,
                'persistent_member_identity': True, 'cold_team_view': True,
                'cooperative_steer_cancel': True,
                'team': team.capacity(), 'harness': v70.harness.status(),
            })
        if path == '/api/agents/team/state':
            tid = str(query.get('team', [''])[0]).strip()
            if not tid:
                return self.send_json(400, {'error': 'Thiếu team'})
            return self.send_json(200, team.state(tid))
        if path == '/api/agents/team/tasks':
            tid = str(query.get('team', [''])[0]).strip()
            if not tid:
                return self.send_json(400, {'error': 'Thiếu team'})
            return self.send_json(200, team.tasks(tid))
        if path == '/api/agents/team/mailbox':
            tid = str(query.get('team', [''])[0]).strip()
            if not tid:
                return self.send_json(400, {'error': 'Thiếu team'})
            return self.send_json(200, team.mailbox(tid))
        if path == '/api/agents/team/events':
            tid = str(query.get('team', [''])[0]).strip()
            if not tid:
                return self.send_json(400, {'error': 'Thiếu team'})
            return self.send_json(200, team.events(tid, _limit(query, 'limit', 100, 500)))
        return super().do_GET()

    def do_POST(self):
        path = urlsplit(self.path).path
        if path in {
            '/api/agents/team/start', '/api/agents/team/control',
            '/api/agents/team/task/update', '/api/agents/team/recover',
        }:
            try:
                b = self.body()
            except Exception:
                return self.send_json(400, {'error': 'invalid json'})
            try:
                if path == '/api/agents/team/start':
                    q = str(b.get('message') or b.get('query') or '').strip()
                    if not q:
                        return self.send_json(400, {'error': 'Thiếu query'})
                    return self.send_json(202, team.start(
                        q, str(b.get('profile') or self.server.profile), b.get('model') or None,
                        self.server.ollama, str(b.get('session_id') or 'default'), b.get('workers'),
                    ))
                if path == '/api/agents/team/control':
                    return self.send_json(200, team.control(
                        str(b.get('run_id') or ''), str(b.get('target') or ''),
                        str(b.get('action') or ''), str(b.get('instruction') or ''),
                    ))
                if path == '/api/agents/team/task/update':
                    return self.send_json(200, team.update_task(
                        str(b.get('team_id') or ''), str(b.get('task_id') or ''),
                        int(b.get('expected_revision')), str(b.get('action') or ''),
                        str(b.get('owner_id') or '') or None,
                    ))
                if path == '/api/agents/team/recover':
                    return self.send_json(200, {'recovered': team.recover()})
            except Exception as exc:
                return self.send_json(409, {'error': str(exc)})
        return super().do_POST()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=11435)
    ap.add_argument('--ollama', default='http://127.0.0.1:11434')
    ap.add_argument('--profile', default='balanced')
    ap.add_argument('--model')
    a = ap.parse_args()
    cfg = v70.v69._legacy_v64().legacy.profiles().get(a.profile) or v70.v69._legacy_v64().legacy.profiles()['balanced']
    v70.v69._legacy_v64().legacy.workflows.ensure()
    recovered_harness = v70.harness.recover_incomplete()
    recovered_teams = team.recover()
    v70.v69._legacy_v64().legacy.start_ollama(a.ollama)
    srv = ThreadingHTTPServer((a.host, a.port), H71)
    srv.ollama = a.ollama; srv.profile = a.profile; srv.model = a.model or cfg['ollama_name']; srv.model_mode = 'auto'
    print(f'KimiK3-Lite v7.1 Studio http://{a.host}:{a.port} · harness={len(recovered_harness)} team={len(recovered_teams)}')
    srv.serve_forever()


if __name__ == '__main__':
    main()
