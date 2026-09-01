#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import harness_runtime as harness
import kimik3_lite as core
import studio_server_v69 as v69
import verification_engine as verifier


def _limit(query: dict, key: str, default: int, maximum: int) -> int:
    try:
        return max(1, min(int(query.get(key, [str(default)])[0]), maximum))
    except (TypeError, ValueError):
        return default


class H70(v69.H69):
    def _index70(self):
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
        text = text.replace('Local Workspace · v6.4', 'Local Workspace · v7.0')
        raw = text.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        q = urlsplit(self.path)
        path = q.path
        query = parse_qs(q.query)
        if path in {'/', '/index.html'}:
            return self._index70()
        if path == '/health':
            return self.send_json(200, {
                'ok': True,
                'version': '7.0.0',
                'hermes_foundation': True,
                'deepseek_harness_patterns': True,
                'event_sourced_runs': True,
                'crash_recovery': True,
                'tool_result_spill': True,
                'verification_recipes': True,
                'harness': harness.status(),
            })
        if path == '/api/harness/status':
            return self.send_json(200, harness.status())
        if path == '/api/harness/events':
            sid = str(query.get('session', ['default'])[0])
            return self.send_json(200, harness.events(sid, _limit(query, 'limit', 100, 500)))
        if path == '/api/harness/runs':
            return self.send_json(200, harness.runs(_limit(query, 'limit', 50, 500)))
        if path == '/api/harness/recipes':
            rows = verifier.recipes(core.ROOT)
            return self.send_json(200, [{'id': x['id'], 'label': x['label']} for x in rows])
        return super().do_GET()

    def do_POST(self):
        path = urlsplit(self.path).path
        if path.startswith('/api/harness/'):
            try:
                b = self.body()
            except Exception:
                return self.send_json(400, {'error': 'invalid json'})
            try:
                if path == '/api/harness/verify':
                    profile = str(b.get('profile') or 'fast')
                    return self.send_json(200, verifier.verify(core.ROOT, profile))
                if path == '/api/harness/recover':
                    return self.send_json(200, {'recovered': harness.recover_incomplete()})
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
    cfg = v69._legacy_v64().legacy.profiles().get(a.profile) or v69._legacy_v64().legacy.profiles()['balanced']
    v69._legacy_v64().legacy.workflows.ensure()
    recovered = harness.recover_incomplete()
    v69._legacy_v64().legacy.start_ollama(a.ollama)
    srv = ThreadingHTTPServer((a.host, a.port), H70)
    srv.ollama = a.ollama
    srv.profile = a.profile
    srv.model = a.model or cfg['ollama_name']
    srv.model_mode = 'auto'
    print(f'KimiK3-Lite v7.0 Studio http://{a.host}:{a.port} · recovered={len(recovered)}')
    srv.serve_forever()


if __name__ == '__main__':
    main()
