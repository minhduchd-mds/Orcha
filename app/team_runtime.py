#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import kimik3_lite as core

DATA = Path(os.environ.get('KIMIK3_DATA_DIR', str(core.DATA))).expanduser()
ROOT = DATA / 'agent-teams-v2'
TEAMS = ROOT / 'teams'
_LOCK = threading.RLock()
_SAFE = re.compile(r'[^a-zA-Z0-9._-]+')
_LIVE_CANCEL: dict[tuple[str, str], threading.Event] = {}
_LIVE_STEER: dict[tuple[str, str], list[str]] = {}

AVAILABLE_CAPABILITIES = {
    'llm', 'retrieval', 'shared_memory', 'durable_mailbox',
    'task_cas', 'cold_view', 'cooperative_control',
}


def _ensure() -> None:
    TEAMS.mkdir(parents=True, exist_ok=True)


def _safe(value: str, fallback: str = 'default', limit: int = 120) -> str:
    out = _SAFE.sub('-', str(value or fallback)).strip('-._')[:limit]
    return out or fallback


def _path(team_id: str) -> Path:
    _ensure()
    return TEAMS / f'{_safe(team_id, "team")}.jsonl'


def _rows(team_id: str, limit: int | None = None) -> list[dict]:
    p = _path(team_id)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding='utf-8', errors='ignore').splitlines():
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
        except Exception:
            continue
    if limit is not None:
        return out[-max(1, min(int(limit), 1000)):]
    return out


def append(team_id: str, event_type: str, data: dict | None = None) -> dict:
    if not event_type or len(event_type) > 80:
        raise ValueError('team event type không hợp lệ')
    payload = dict(data or {})
    json.dumps(payload, ensure_ascii=False)
    with _LOCK:
        rows = _rows(team_id, 1)
        seq = int(rows[-1].get('seq', -1)) + 1 if rows else 0
        row = {'seq': seq, 'time': time.time(), 'type': event_type, 'data': payload}
        with _path(team_id).open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            f.flush()
        return row


def events(team_id: str, limit: int = 200) -> list[dict]:
    return _rows(team_id, max(1, min(int(limit or 200), 1000)))


def fold(team_id: str) -> dict:
    state = {
        'id': _safe(team_id, 'team'), 'status': 'unknown', 'root_session_id': None,
        'query': '', 'members': {}, 'tasks': {}, 'mailbox': [], 'controls': [],
        'created_at': None, 'updated_at': None,
    }
    delivered: set[str] = set()
    for row in _rows(team_id):
        typ = row.get('type'); data = row.get('data') if isinstance(row.get('data'), dict) else {}
        state['updated_at'] = row.get('time')
        if typ == 'team/created':
            state.update({'status': 'running', 'root_session_id': data.get('root_session_id'), 'query': data.get('query', ''), 'created_at': row.get('time')})
        elif typ == 'member/upsert':
            member = dict(data.get('member') or {})
            if member.get('id'):
                state['members'][member['id']] = member
        elif typ == 'task/upsert':
            task = dict(data.get('task') or {})
            if task.get('id'):
                state['tasks'][task['id']] = task
        elif typ == 'message/queued':
            msg = dict(data.get('message') or {})
            if msg.get('id'):
                state['mailbox'].append(msg)
        elif typ == 'message/delivered':
            if data.get('message_id'):
                delivered.add(str(data['message_id']))
        elif typ in {'control/steer', 'control/cancel'}:
            state['controls'].append({'type': typ, **data, 'time': row.get('time')})
        elif typ == 'team/interrupted':
            state['status'] = 'interrupted'
        elif typ == 'team/settled':
            state['status'] = str(data.get('status') or 'done')
    for msg in state['mailbox']:
        msg['delivered'] = msg.get('id') in delivered
    return state


def create(root_session_id: str, query: str, team_id: str | None = None) -> dict:
    tid = _safe(team_id or ('team-' + uuid.uuid4().hex[:14]), 'team')
    if _path(tid).exists() and _rows(tid, 1):
        raise ValueError('team id đã tồn tại')
    append(tid, 'team/created', {'root_session_id': _safe(root_session_id), 'query': str(query or '')[:12000]})
    return fold(tid)


def member_id(team_id: str, node_id: str) -> str:
    return f'{_safe(team_id)}:{_safe(node_id)}'


def upsert_member(team_id: str, node_id: str, name: str, role: str, phase: str = 'active', error: str | None = None) -> dict:
    mid = member_id(team_id, node_id)
    old = fold(team_id)['members'].get(mid, {})
    member = {
        'id': mid, 'node_id': _safe(node_id), 'name': str(name or node_id)[:120],
        'role': str(role or 'agent')[:80], 'phase': str(phase or 'active')[:40],
        'created_at': old.get('created_at') or time.time(), 'updated_at': time.time(),
    }
    if error:
        member['error'] = str(error)[:1000]
    append(team_id, 'member/upsert', {'member': member})
    return member


def _assert_acyclic(tasks: dict[str, dict]) -> None:
    visiting: set[str] = set(); done: set[str] = set()
    def visit(task_id: str) -> None:
        if task_id in done:
            return
        if task_id in visiting:
            raise ValueError('task graph có cycle')
        visiting.add(task_id)
        for dep in tasks.get(task_id, {}).get('blocked_by', []):
            if dep not in tasks:
                raise ValueError('blocked_by tham chiếu task không tồn tại: ' + str(dep))
            visit(str(dep))
        visiting.remove(task_id); done.add(task_id)
    for key in tasks:
        visit(key)


def create_task(team_id: str, task_id: str, subject: str, description: str = '', blocked_by: list[str] | None = None, write_scopes: list[str] | None = None) -> dict:
    state = fold(team_id)
    tid = _safe(task_id, 'task')
    if tid in state['tasks']:
        raise ValueError('task đã tồn tại: ' + tid)
    task = {
        'id': tid, 'revision': 1, 'subject': str(subject or tid)[:200],
        'description': str(description or '')[:2000], 'status': 'pending',
        'owner_id': None, 'blocked_by': [_safe(x, 'task') for x in (blocked_by or [])],
        'write_scopes': [str(x)[:300] for x in (write_scopes or [])[:20]],
        'updated_at': time.time(),
    }
    candidate = dict(state['tasks']); candidate[tid] = task; _assert_acyclic(candidate)
    append(team_id, 'task/upsert', {'task': task})
    return task


def update_task(team_id: str, task_id: str, expected_revision: int, action: str, owner_id: str | None = None) -> dict:
    state = fold(team_id); tid = _safe(task_id, 'task'); task = dict(state['tasks'].get(tid) or {})
    if not task:
        raise KeyError('không tìm thấy task')
    if int(task.get('revision') or 0) != int(expected_revision):
        raise ValueError(f'task revision conflict: expected {expected_revision}, current {task.get("revision")}')
    allowed = {'start', 'complete', 'release', 'block', 'delete'}
    if action not in allowed:
        raise ValueError('task action không hợp lệ')
    if action == 'start':
        blockers = [x for x in task.get('blocked_by', []) if state['tasks'].get(x, {}).get('status') != 'completed']
        if blockers:
            raise ValueError('task còn blocker: ' + ', '.join(blockers))
        task['status'] = 'in_progress'; task['owner_id'] = str(owner_id or '') or None
    elif action == 'complete':
        task['status'] = 'completed'; task['owner_id'] = str(owner_id or task.get('owner_id') or '') or None
    elif action == 'release':
        task['status'] = 'pending'; task['owner_id'] = None
    elif action == 'block':
        task['status'] = 'blocked'; task['owner_id'] = None
    elif action == 'delete':
        task['status'] = 'deleted'; task['owner_id'] = None
    task['revision'] = int(task.get('revision') or 0) + 1; task['updated_at'] = time.time()
    append(team_id, 'task/upsert', {'task': task})
    return task


def queue_message(team_id: str, sender_id: str, target_id: str, content: str, delivery: str = 'quiet') -> dict:
    if delivery not in {'quiet', 'wakeup'}:
        raise ValueError('delivery phải là quiet hoặc wakeup')
    state = fold(team_id)
    valid = set(state['members']) | {str(state.get('root_session_id') or '')}
    if sender_id not in valid or target_id not in valid:
        raise ValueError('sender/target không thuộc team')
    msg = {
        'id': 'msg-' + uuid.uuid4().hex[:16], 'sender_id': sender_id,
        'target_id': target_id, 'delivery': delivery, 'content': str(content or '')[:12000],
        'created_at': time.time(),
    }
    append(team_id, 'message/queued', {'message': msg})
    return msg


def deliver_message(team_id: str, message_id: str) -> dict:
    state = fold(team_id); msg = next((x for x in state['mailbox'] if x.get('id') == message_id), None)
    if not msg:
        raise KeyError('không tìm thấy team message')
    if not msg.get('delivered'):
        append(team_id, 'message/delivered', {'message_id': message_id})
    return {**msg, 'delivered': True}


def pending_mailbox(team_id: str, target_id: str | None = None) -> list[dict]:
    rows = [x for x in fold(team_id)['mailbox'] if not x.get('delivered')]
    if target_id:
        rows = [x for x in rows if x.get('target_id') == target_id]
    return rows


def _control_key(team_id: str, target_id: str) -> tuple[str, str]:
    return (_safe(team_id), str(target_id))


def steer(team_id: str, target_id: str, instruction: str) -> dict:
    state = fold(team_id)
    if target_id not in state['members']:
        raise KeyError('không tìm thấy team member')
    text = str(instruction or '').strip()
    if not text:
        raise ValueError('instruction trống')
    key = _control_key(team_id, target_id)
    with _LOCK:
        _LIVE_STEER.setdefault(key, []).append(text[:3000])
    append(team_id, 'control/steer', {'target_id': target_id, 'instruction': text[:3000]})
    return {'ok': True, 'target_id': target_id, 'queued': True}


def cancel(team_id: str, target_id: str) -> dict:
    state = fold(team_id)
    if target_id not in state['members']:
        raise KeyError('không tìm thấy team member')
    key = _control_key(team_id, target_id)
    with _LOCK:
        _LIVE_CANCEL.setdefault(key, threading.Event()).set()
    append(team_id, 'control/cancel', {'target_id': target_id})
    return {'ok': True, 'target_id': target_id, 'cancelled': True, 'mode': 'cooperative-step-boundary'}


def is_cancelled(team_id: str, target_id: str) -> bool:
    return bool(_LIVE_CANCEL.get(_control_key(team_id, target_id), threading.Event()).is_set())


def consume_steering(team_id: str, target_id: str) -> list[str]:
    key = _control_key(team_id, target_id)
    with _LOCK:
        rows = list(_LIVE_STEER.get(key, [])); _LIVE_STEER[key] = []
    return rows


def require_capabilities(required: list[str] | tuple[str, ...]) -> None:
    missing = [x for x in required if x not in AVAILABLE_CAPABILITIES]
    if missing:
        raise RuntimeError('UNSUPPORTED_CAPABILITY: ' + ', '.join(missing))


def settle(team_id: str, status: str = 'done') -> dict:
    state = fold(team_id)
    # Child/member state closes before the root Team is marked settled.
    for member in list(state['members'].values())[::-1]:
        if member.get('phase') not in {'done', 'failed', 'cancelled'}:
            upsert_member(team_id, member.get('node_id') or member['id'], member.get('name') or 'Agent', member.get('role') or 'agent', 'done' if status == 'done' else status)
    append(team_id, 'team/settled', {'status': status})
    return fold(team_id)


def recover_open_teams(limit: int = 300) -> list[str]:
    _ensure(); recovered: list[str] = []
    for p in list(TEAMS.glob('team-*.jsonl'))[:max(1, min(int(limit or 300), 1000))]:
        tid = p.stem; state = fold(tid)
        if state.get('status') == 'running':
            append(tid, 'team/interrupted', {'reason': 'runtime restart; side-effect state not auto-resumed'})
            recovered.append(tid)
    return recovered


def status() -> dict:
    _ensure()
    return {
        'version': 2, 'architecture': 'durable-team-event-log',
        'capabilities': sorted(AVAILABLE_CAPABILITIES),
        'features': {
            'durable_mailbox': True, 'task_revision_cas': True, 'persistent_member_identity': True,
            'cold_view': True, 'cooperative_steer_cancel': True, 'child_first_settle': True,
            'event_replay': True, 'fail_loud_capabilities': True,
        },
        'safety': {'auto_resume_side_effects': False, 'arbitrary_plugin_code': False},
    }


def self_test() -> None:
    tid = 'team-selftest-' + uuid.uuid4().hex[:8]
    p = _path(tid)
    try:
        create('root', 'test', tid)
        m = upsert_member(tid, 'research', 'Research', 'research')
        t1 = create_task(tid, 'a', 'A')
        t2 = create_task(tid, 'b', 'B', blocked_by=['a'])
        t1 = update_task(tid, 'a', t1['revision'], 'start', m['id'])
        t1 = update_task(tid, 'a', t1['revision'], 'complete', m['id'])
        t2 = update_task(tid, 'b', t2['revision'], 'start', m['id'])
        msg = queue_message(tid, 'root', m['id'], 'hello'); assert not msg.get('delivered')
        deliver_message(tid, msg['id']); assert not pending_mailbox(tid)
        steer(tid, m['id'], 'check edge cases'); assert consume_steering(tid, m['id'])
        cancel(tid, m['id']); assert is_cancelled(tid, m['id'])
        require_capabilities(['llm', 'retrieval'])
        assert fold(tid)['tasks']['b']['status'] == 'in_progress'
        print('PASS: durable team mailbox/task-CAS/control/replay')
    finally:
        try: p.unlink()
        except OSError: pass


if __name__ == '__main__':
    self_test()
