#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import agent_runtime as agents
import hermes_runtime as hermes
import kimik3_lite as core
import model_registry as registry
import studio_server_v68 as v68


def _legacy_v64():
    return v68.v67.v66.v65.v64


class H69(v68.H68):
    def _index69(self):
        p = Path(core.ROOT) / 'studio' / 'index.html'
        text = p.read_text(encoding='utf-8')
        text = text.replace(
            '</head>',
            '<link rel="stylesheet" href="/parallel-agents.css">'
            '<link rel="stylesheet" href="/agent-team.css">'
            '<link rel="stylesheet" href="/final-intelligence.css">'
            '<link rel="stylesheet" href="/hermes.css"></head>',
        )
        text = text.replace(
            '</body>',
            '<script src="/parallel-agents.js"></script>'
            '<script src="/agent-team.js"></script>'
            '<script src="/final-intelligence.js"></script>'
            '<script src="/hermes.js"></script></body>',
        )
        text = text.replace('Local Workspace · v6.4', 'Local Workspace · v6.9')
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
            return self._index69()
        if path == '/health':
            base = hermes.status()
            return self.send_json(200, {
                'ok': True,
                'version': '6.9.0',
                'hermes_foundation': True,
                'conversation_router': True,
                'request_idempotency': True,
                'composite_text_companion_fix': True,
                'peer_bus': True,
                'steer_cancel_control': True,
                'hermes': base,
            })
        if path == '/api/hermes/status':
            return self.send_json(200, hermes.status())
        if path == '/api/hermes/agents':
            return self.send_json(200, hermes.agent_roster())
        if path == '/api/hermes/session':
            sid = str(query.get('session', ['default'])[0])
            limit = int(query.get('limit', ['100'])[0])
            return self.send_json(200, hermes.transcript(sid, limit))
        if path == '/api/hermes/peers':
            limit = int(query.get('limit', ['100'])[0])
            return self.send_json(200, hermes.peer_history(limit))
        if path == '/api/hermes/runs':
            limit = int(query.get('limit', ['50'])[0])
            return self.send_json(200, hermes.control_runs(limit))
        return super().do_GET()

    def _chat69(self, b: dict):
        user = str(b.get('message') or '').strip()
        sid = str(b.get('session_id') or 'default')
        request_id = str(b.get('request_id') or '').strip()
        images = b.get('images') if isinstance(b.get('images'), list) else []
        if not user:
            return self.send_json(400, {'error': 'Thiếu nội dung'})

        cached = hermes.cached_response(sid, request_id)
        if cached:
            cached = dict(cached)
            cached['idempotent_replay'] = True
            return self.send_json(200, cached)
        duplicate = hermes.recent_duplicate(sid, user, 3)
        if duplicate:
            duplicate = dict(duplicate)
            duplicate['duplicate_suppressed'] = True
            return self.send_json(200, duplicate)

        preferred = str(b.get('model_id') or getattr(self.server, 'model_mode', 'auto') or 'auto')
        model_route = registry.route(user, bool(images), preferred)
        selected = model_route.get('selected') or registry.get('balanced') or {}
        selected_id = str(selected.get('id') or 'balanced')
        hroute = hermes.route_request(user, bool(b.get('agent', False)))

        try:
            if images and selected_id == 'uiux-vision-lite':
                result = _legacy_v64().uiux_pipeline(user, images, self.server, str(b.get('mode', 'auto')), sid)
                hroute = {**hroute, 'mode': 'design-composite', 'reason': 'image+uiux'}
            else:
                runtime = registry.runtime_model(selected, bool(images))
                model = str(runtime.get('model') or self.server.model)
                if hroute.get('mode') == 'agent':
                    result = agents.run(user, self.server.profile, model, self.server.ollama, str(b.get('mode', 'auto')), sid)
                else:
                    result = core.answer_query(
                        user,
                        self.server.profile,
                        model,
                        self.server.ollama,
                        str(b.get('mode', 'auto')),
                        int(b.get('top_k', 6)),
                        int(b.get('timeout', 300)),
                        sid,
                    )
                result['model_route'] = {
                    **model_route,
                    'runtime_selected': runtime.get('selected'),
                    'runtime_reason': runtime.get('reason'),
                }
            result['hermes'] = {
                'route': hroute,
                'request_id': request_id,
                'framework': 'v2026.8.31-inspired',
            }
            hermes.record_turn(sid, request_id, user, result, hroute)
            return self.send_json(200, result)
        except Exception as e:
            fallback = registry.get('balanced')
            if fallback and fallback.get('ram_ok'):
                try:
                    model = str(fallback.get('ollama_tag') or self.server.model)
                    result = core.answer_query(user, 'balanced', model, self.server.ollama, str(b.get('mode', 'auto')), 6, 300, sid)
                    result['model_route'] = {
                        'task': model_route.get('task'),
                        'selected': fallback,
                        'runtime_selected': fallback,
                        'reason': 'hermes-fallback',
                        'previous_error': str(e),
                    }
                    result['hermes'] = {'route': {**hroute, 'fallback': True}, 'request_id': request_id}
                    hermes.record_turn(sid, request_id, user, result, hroute)
                    return self.send_json(200, result)
                except Exception:
                    pass
            return self.send_json(502, {'error': str(e), 'hermes_route': hroute})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == '/api/chat':
            try:
                b = self.body()
            except Exception:
                return self.send_json(400, {'error': 'invalid json'})
            return self._chat69(b)
        if path.startswith('/api/hermes/'):
            try:
                b = self.body()
            except Exception:
                return self.send_json(400, {'error': 'invalid json'})
            try:
                if path == '/api/hermes/peer':
                    return self.send_json(200, hermes.peer_message(
                        str(b.get('source') or 'general'),
                        str(b.get('target') or ''),
                        str(b.get('text') or ''),
                        str(b.get('session_id') or 'default'),
                    ))
                if path == '/api/hermes/run/register':
                    return self.send_json(200, hermes.register_control_run(str(b.get('kind') or 'subagent'), b.get('metadata') if isinstance(b.get('metadata'), dict) else {}))
                if path == '/api/hermes/run/steer':
                    return self.send_json(200, hermes.steer(str(b.get('run_id') or ''), str(b.get('instruction') or '')))
                if path == '/api/hermes/run/cancel':
                    return self.send_json(200, hermes.cancel(str(b.get('run_id') or '')))
                if path == '/api/hermes/protected-write':
                    p = str(b.get('path') or '')
                    return self.send_json(200, {'path': p, 'requires_confirmation': hermes.protected_write(p)})
            except Exception as e:
                return self.send_json(409, {'error': str(e)})
        return super().do_POST()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=11435)
    ap.add_argument('--ollama', default='http://127.0.0.1:11434')
    ap.add_argument('--profile', default='balanced')
    ap.add_argument('--model')
    a = ap.parse_args()
    cfg = _legacy_v64().legacy.profiles().get(a.profile) or _legacy_v64().legacy.profiles()['balanced']
    _legacy_v64().legacy.workflows.ensure()
    _legacy_v64().legacy.start_ollama(a.ollama)
    srv = ThreadingHTTPServer((a.host, a.port), H69)
    srv.ollama = a.ollama
    srv.profile = a.profile
    srv.model = a.model or cfg['ollama_name']
    srv.model_mode = 'auto'
    print(f'KimiK3-Lite v6.9 Studio http://{a.host}:{a.port}')
    srv.serve_forever()


if __name__ == '__main__':
    main()
