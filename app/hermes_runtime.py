#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path

import skill_runtime as skills

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config' / 'hermes.json'
DATA = Path(os.environ.get('KIMIK3_DATA_DIR', str(ROOT / 'data'))).expanduser()
STORE = DATA / 'hermes'
SESSIONS = STORE / 'sessions'
PEERS = STORE / 'peer_messages.jsonl'
RUNS = STORE / 'control_runs.json'
_LOCK = threading.RLock()
_SAFE = re.compile(r'[^a-zA-Z0-9._-]+')

ACTION_TERMS = (
    'tạo ', 'tao ', 'sửa ', 'sua ', 'xóa ', 'xoa ', 'mở ', 'mo ', 'chạy ', 'chay ',
    'thực hiện', 'thuc hien', 'click', 'nhập ', 'nhap ', 'ghi file', 'lưu ', 'luu ',
    'autocad', ' cad ', 'build ', 'deploy ', 'refactor ', 'fix ', 'index ', 'clone ',
)


def _ensure():
    SESSIONS.mkdir(parents=True, exist_ok=True)
    STORE.mkdir(parents=True, exist_ok=True)


def config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding='utf-8'))
    except Exception:
        return {
            'version': 1,
            'agents': [
                {'id': 'general', 'name': 'General', 'role': 'chat'},
                {'id': 'research', 'name': 'Research', 'role': 'read'},
                {'id': 'builder', 'name': 'Builder', 'role': 'action'},
                {'id': 'verifier', 'name': 'Verifier', 'role': 'verify'},
            ],
        }


def agent_roster() -> list[dict]:
    return [dict(x) for x in config().get('agents', []) if isinstance(x, dict)]


def _sid(session_id: str) -> str:
    x = _SAFE.sub('-', str(session_id or 'default')).strip('-._')[:100]
    return x or 'default'


def _session_path(session_id: str) -> Path:
    _ensure()
    return SESSIONS / f'{_sid(session_id)}.jsonl'


def transcript(session_id: str, limit: int = 100) -> list[dict]:
    p = _session_path(session_id)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding='utf-8', errors='ignore').splitlines():
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            pass
    return rows[-max(1, min(int(limit or 100), 500)):]


def cached_response(session_id: str, request_id: str) -> dict | None:
    rid = str(request_id or '').strip()
    if not rid:
        return None
    for row in reversed(transcript(session_id, 200)):
        if row.get('request_id') == rid and isinstance(row.get('response'), dict):
            return row['response']
    return None


def recent_duplicate(session_id: str, user: str, seconds: int = 3) -> dict | None:
    now = time.time()
    q = str(user or '').strip()
    if not q:
        return None
    for row in reversed(transcript(session_id, 20)):
        if now - float(row.get('ts') or 0) > max(1, int(seconds)):
            break
        if row.get('user') == q and isinstance(row.get('response'), dict):
            return row['response']
    return None


def record_turn(session_id: str, request_id: str, user: str, response: dict, route: dict) -> dict:
    _ensure()
    rec = {
        'id': 'turn-' + uuid.uuid4().hex[:12],
        'ts': time.time(),
        'request_id': str(request_id or ''),
        'user': str(user or '')[:12000],
        'route': route,
        'response': response,
    }
    with _LOCK:
        if request_id and cached_response(session_id, request_id):
            return rec
        with _session_path(session_id).open('a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return rec


def route_request(query: str, agent_requested: bool = True) -> dict:
    q = str(query or '').strip()
    low = ' ' + q.casefold() + ' '
    skill = skills.match_skill(q)
    action = any(k in low for k in ACTION_TERMS)
    if not agent_requested:
        mode = 'direct'
        reason = 'agent-disabled'
    elif skill:
        mode = 'agent'
        reason = 'matched-skill'
    elif action:
        mode = 'agent'
        reason = 'action-intent'
    else:
        mode = 'direct'
        reason = 'conversation-first'
    return {
        'mode': mode,
        'reason': reason,
        'skill': {'id': skill.get('id'), 'name': skill.get('name')} if skill else None,
        'agent_requested': bool(agent_requested),
    }


def _load_runs() -> dict:
    _ensure()
    try:
        x = json.loads(RUNS.read_text(encoding='utf-8'))
        return x if isinstance(x, dict) else {}
    except Exception:
        return {}


def _save_runs(rows: dict):
    _ensure()
    RUNS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


def register_control_run(kind: str, metadata: dict | None = None) -> dict:
    with _LOCK:
        rows = _load_runs()
        rid = 'hermes-' + uuid.uuid4().hex[:12]
        rows[rid] = {
            'id': rid,
            'kind': str(kind or 'subagent')[:40],
            'status': 'running',
            'created_at': time.time(),
            'updated_at': time.time(),
            'steering': [],
            'metadata': metadata or {},
        }
        _save_runs(rows)
        return rows[rid]


def steer(run_id: str, instruction: str) -> dict:
    with _LOCK:
        rows = _load_runs()
        row = rows.get(str(run_id))
        if not row:
            raise KeyError('Không tìm thấy Hermes run')
        row.setdefault('steering', []).append({'ts': time.time(), 'instruction': str(instruction or '')[:2000]})
        row['updated_at'] = time.time()
        _save_runs(rows)
        return row


def cancel(run_id: str) -> dict:
    with _LOCK:
        rows = _load_runs()
        row = rows.get(str(run_id))
        if not row:
            raise KeyError('Không tìm thấy Hermes run')
        row['status'] = 'cancelled'
        row['updated_at'] = time.time()
        _save_runs(rows)
        return row


def control_runs(limit: int = 50) -> list[dict]:
    rows = list(_load_runs().values())
    return sorted(rows, key=lambda x: float(x.get('updated_at') or 0), reverse=True)[:max(1, min(limit, 200))]


def peer_message(source: str, target: str, text: str, session_id: str = 'default') -> dict:
    roster = {x.get('id') for x in agent_roster()}
    source = str(source or 'general')
    target = str(target or '').strip()
    if source not in roster or target not in roster:
        raise ValueError('Agent peer không hợp lệ')
    rec = {
        'id': 'peer-' + uuid.uuid4().hex[:12],
        'ts': time.time(),
        'session_id': _sid(session_id),
        'source': source,
        'target': target,
        'text': str(text or '')[:6000],
    }
    _ensure()
    with _LOCK, PEERS.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return rec


def peer_history(limit: int = 100) -> list[dict]:
    _ensure()
    if not PEERS.exists():
        return []
    out = []
    for line in PEERS.read_text(encoding='utf-8', errors='ignore').splitlines():
        try:
            x = json.loads(line)
            if isinstance(x, dict):
                out.append(x)
        except Exception:
            pass
    return out[-max(1, min(limit, 500)):]


def protected_write(path: str) -> bool:
    p = str(path or '').replace('\\', '/').lower()
    return (
        p.endswith('/agents.md') or p == 'agents.md' or
        '/skills/' in '/' + p or p.startswith('skills/') or
        '/memory' in '/' + p or
        p.endswith('/config/hermes.json') or p == 'config/hermes.json'
    )


def status() -> dict:
    return {
        'framework': 'Hermes-inspired local control plane',
        'version': 1,
        'agents': agent_roster(),
        'features': {
            'conversation_router': True,
            'durable_transcript': True,
            'request_idempotency': True,
            'peer_bus': True,
            'steer_cancel_control': True,
            'protected_instruction_policy': True,
        },
        'safety': {
            'peer_local_only': True,
            'protected_write_requires_confirmation': True,
            'copies_hermes_source': False,
        },
    }


def self_test():
    assert route_request('Thiết kế Apple có nguyên tắc gì?', True)['mode'] == 'direct'
    assert route_request('Tạo layer WALL trong AutoCAD', True)['mode'] == 'agent'
    assert protected_write('skills/test/SKILL.md')
    assert not protected_write('docs/readme.md')
    print('PASS: Hermes routing + safety skeleton')


if __name__ == '__main__':
    self_test()
