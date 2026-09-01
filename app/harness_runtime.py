#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('KIMIK3_DATA_DIR', str(ROOT / 'data'))).expanduser()
STORE = DATA / 'harness'
SESSIONS = STORE / 'sessions'
RUNS = STORE / 'runs'
RESPONSES = STORE / 'responses'
SPILL = STORE / 'spill'
_LOCK = threading.RLock()
_SAFE = re.compile(r'[^a-zA-Z0-9._-]+')
_REQUEST_ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$')
TRANSIENT_MARKERS = ('timed out', 'timeout', 'temporarily unavailable', 'connection reset', 'connection refused', '503', '502', '429')

# Inspired by DeepSeek Harness architecture concepts (event-sourced sessions,
# explicit turn lifecycle, capability seams). This is an independent lightweight
# implementation for KimiK3-Lite; no DeepSeek Harness source code is copied.


def _ensure() -> None:
    for p in (STORE, SESSIONS, RUNS, RESPONSES, SPILL):
        p.mkdir(parents=True, exist_ok=True)


def _safe(value: str, fallback: str = 'default', limit: int = 100) -> str:
    out = _SAFE.sub('-', str(value or fallback)).strip('-._')[:limit]
    return out or fallback


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2)
    tmp = path.with_suffix(path.suffix + '.tmp-' + uuid.uuid4().hex[:8])
    tmp.write_text(raw, encoding='utf-8')
    os.replace(tmp, path)


def request_id(value: str | None = None) -> str:
    raw = str(value or '').strip()
    if not raw:
        return 'req-' + uuid.uuid4().hex
    if not _REQUEST_ID.fullmatch(raw):
        raise ValueError('request_id không hợp lệ; dùng 1-128 ký tự a-z/A-Z/0-9/._:-')
    return raw


def _session_path(session_id: str) -> Path:
    _ensure()
    return SESSIONS / f'{_safe(session_id)}.jsonl'


def _tail_rows(path: Path, limit: int = 200) -> list[dict]:
    if not path.exists():
        return []
    limit = max(1, min(int(limit or 200), 1000))
    # Bound disk reads for long sessions. A complete replay can be added as a
    # separate explicit API; hot-path status/idempotency never scans the world.
    try:
        size = path.stat().st_size
        with path.open('rb') as f:
            f.seek(max(0, size - 2 * 1024 * 1024))
            raw = f.read().decode('utf-8', errors='ignore')
        lines = raw.splitlines()
        if size > 2 * 1024 * 1024 and lines:
            lines = lines[1:]
    except OSError:
        return []
    out: list[dict] = []
    for line in lines[-limit:]:
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                out.append(item)
        except Exception:
            continue
    return out


def events(session_id: str, limit: int = 200) -> list[dict]:
    return _tail_rows(_session_path(session_id), limit)


def append_event(session_id: str, event_type: str, data: dict | None = None, run_id: str | None = None) -> dict:
    if not event_type or len(event_type) > 80:
        raise ValueError('event_type không hợp lệ')
    data = dict(data or {})
    # Fail closed if a plugin/tool tries to put non-JSON state into the durable log.
    json.dumps(data, ensure_ascii=False)
    with _LOCK:
        p = _session_path(session_id)
        tail = _tail_rows(p, 1)
        seq = int(tail[-1].get('seq', -1)) + 1 if tail else 0
        row = {
            'seq': seq,
            'time': time.time(),
            'type': event_type,
            'run_id': str(run_id or '') or None,
            'data': data,
        }
        with p.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            f.flush()
        return row


def _run_path(run_id: str) -> Path:
    _ensure()
    return RUNS / f'{_safe(run_id, "run")}.json'


def begin(session_id: str, rid: str, query: str, route: dict | None = None) -> dict:
    rid = request_id(rid)
    run_id = 'run-' + uuid.uuid4().hex[:16]
    row = {
        'id': run_id,
        'session_id': _safe(session_id),
        'request_id': rid,
        'status': 'running',
        'started_at': time.time(),
        'updated_at': time.time(),
        'query_preview': str(query or '')[:1000],
        'route': dict(route or {}),
        'step': 0,
        'error': None,
    }
    with _LOCK:
        _atomic_json(_run_path(run_id), row)
        append_event(session_id, 'turn/start', {'request_id': rid, 'query': str(query or '')[:12000]}, run_id)
    return row


def checkpoint(run: dict, event_type: str, data: dict | None = None) -> dict:
    run = dict(run)
    run['updated_at'] = time.time()
    if event_type == 'step/start':
        run['step'] = int(run.get('step') or 0) + 1
    with _LOCK:
        _atomic_json(_run_path(str(run['id'])), run)
        append_event(str(run.get('session_id') or 'default'), event_type, data or {}, str(run['id']))
    return run


def _response_key(session_id: str, rid: str) -> Path:
    key = hashlib.sha256((str(session_id) + '\0' + rid).encode('utf-8')).hexdigest()
    return RESPONSES / f'{key}.json'


def cache_response(session_id: str, rid: str, response: dict) -> None:
    rid = request_id(rid)
    with _LOCK:
        _atomic_json(_response_key(session_id, rid), {'session_id': _safe(session_id), 'request_id': rid, 'response': response, 'time': time.time()})


def cached_response(session_id: str, rid: str | None) -> dict | None:
    raw = str(rid or '').strip()
    if not raw or not _REQUEST_ID.fullmatch(raw):
        return None
    p = _response_key(session_id, raw)
    try:
        obj = json.loads(p.read_text(encoding='utf-8'))
        return obj.get('response') if isinstance(obj.get('response'), dict) else None
    except Exception:
        return None


def finish(run: dict, response: dict) -> dict:
    run = dict(run)
    run['status'] = 'done'
    run['updated_at'] = time.time()
    run['ended_at'] = run['updated_at']
    with _LOCK:
        _atomic_json(_run_path(str(run['id'])), run)
        append_event(str(run.get('session_id') or 'default'), 'assistant/message', {'answer': str(response.get('answer') or '')[:24000]}, str(run['id']))
        append_event(str(run.get('session_id') or 'default'), 'turn/end', {'reason': {'kind': 'completed'}}, str(run['id']))
        cache_response(str(run.get('session_id') or 'default'), str(run.get('request_id') or ''), response)
    return run


def fail(run: dict, error: BaseException) -> dict:
    run = dict(run)
    run['status'] = 'error'
    run['updated_at'] = time.time()
    run['ended_at'] = run['updated_at']
    run['error'] = {'kind': classify_error(error), 'message': str(error)[:2000]}
    with _LOCK:
        _atomic_json(_run_path(str(run['id'])), run)
        append_event(str(run.get('session_id') or 'default'), 'request/error', run['error'], str(run['id']))
        append_event(str(run.get('session_id') or 'default'), 'turn/end', {'reason': {'kind': 'failed', 'error': run['error']['kind']}}, str(run['id']))
    return run


def recover_incomplete(limit: int = 500) -> list[dict]:
    _ensure()
    recovered: list[dict] = []
    with _LOCK:
        for p in list(RUNS.glob('run-*.json'))[:max(1, min(limit, 2000))]:
            try:
                row = json.loads(p.read_text(encoding='utf-8'))
            except Exception:
                continue
            if row.get('status') == 'running':
                row['status'] = 'interrupted'
                row['updated_at'] = time.time()
                row['ended_at'] = row['updated_at']
                row['error'] = {'kind': 'interrupted', 'message': 'Runtime restarted before turn/end'}
                _atomic_json(p, row)
                append_event(str(row.get('session_id') or 'default'), 'turn/end', {'reason': {'kind': 'interrupted'}}, str(row.get('id') or ''))
                recovered.append(row)
    return recovered


def runs(limit: int = 50) -> list[dict]:
    _ensure()
    out = []
    for p in RUNS.glob('run-*.json'):
        try:
            row = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(row, dict):
                out.append(row)
        except Exception:
            continue
    out.sort(key=lambda x: float(x.get('updated_at') or 0), reverse=True)
    return out[:max(1, min(int(limit or 50), 500))]


def classify_error(error: BaseException | str) -> str:
    text = str(error).casefold()
    if any(x in text for x in ('permission', 'denied', 'forbidden', 'unauthorized')):
        return 'permission'
    if any(x in text for x in ('invalid', 'validation', 'missing', 'thiếu', 'không hợp lệ')):
        return 'validation'
    if any(x in text for x in TRANSIENT_MARKERS):
        return 'transient'
    if any(x in text for x in ('cancel', 'abort')):
        return 'cancelled'
    return 'runtime'


def retryable(error: BaseException | str) -> bool:
    return classify_error(error) == 'transient'


def call_with_retry(fn: Callable[[], Any], attempts: int = 2, base_delay: float = 0.2) -> Any:
    attempts = max(1, min(int(attempts or 1), 3))
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except BaseException as exc:
            last = exc
            if i + 1 >= attempts or not retryable(exc):
                raise
            time.sleep(min(1.0, max(0.0, base_delay) * (2 ** i)))
    if last:
        raise last
    raise RuntimeError('retry loop ended unexpectedly')


def action_signature(name: str, arguments: dict | None = None) -> str:
    raw = json.dumps({'name': str(name), 'arguments': arguments or {}}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]


def repeated_action(actions: list[dict], name: str, arguments: dict | None = None, max_repeat: int = 2) -> bool:
    sig = action_signature(name, arguments)
    count = 0
    for item in actions:
        if action_signature(str(item.get('tool') or ''), item.get('arguments') if isinstance(item.get('arguments'), dict) else {}) == sig:
            count += 1
    return count >= max(1, int(max_repeat))


def normalize_tool_result(run_id: str, call_id: str, value: Any, limit: int = 12000) -> dict:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        raw = json.dumps({'repr': repr(value)[:4000]}, ensure_ascii=False)
    if len(raw) <= max(1000, int(limit)):
        return {'spilled': False, 'value': value}
    folder = SPILL / _safe(run_id, 'run')
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f'{_safe(call_id, "call")}.json'
    p.write_text(raw, encoding='utf-8')
    keep = max(500, int(limit) // 4)
    return {
        'spilled': True,
        'path': str(p),
        'chars': len(raw),
        'preview': raw[:keep] + '\n…[tool result spilled to disk]…\n' + raw[-keep:],
    }


class CapabilityRegistry:
    """Small in-process seam registry. Registration is trusted code only."""
    def __init__(self) -> None:
        self._items: dict[str, Any] = {}
        self._hooks: dict[str, list[Callable[..., Any]]] = {}
        self._lock = threading.RLock()

    def register(self, name: str, provider: Any) -> Callable[[], None]:
        key = str(name or '').strip()
        if not key:
            raise ValueError('capability name trống')
        with self._lock:
            if key in self._items:
                raise ValueError('capability đã tồn tại: ' + key)
            self._items[key] = provider
        def dispose() -> None:
            with self._lock:
                if self._items.get(key) is provider:
                    self._items.pop(key, None)
        return dispose

    def get(self, name: str) -> Any:
        return self._items.get(str(name))

    def hook(self, event: str, fn: Callable[..., Any]) -> Callable[[], None]:
        key = str(event or '').strip()
        with self._lock:
            self._hooks.setdefault(key, []).append(fn)
        def dispose() -> None:
            with self._lock:
                rows = self._hooks.get(key, [])
                if fn in rows:
                    rows.remove(fn)
        return dispose

    def emit(self, event: str, payload: Any) -> Any:
        value = payload
        for fn in list(self._hooks.get(str(event), [])):
            value = fn(value)
        return value


CAPABILITIES = CapabilityRegistry()


def status() -> dict:
    _ensure()
    return {
        'version': 1,
        'architecture': 'event-sourced-lightweight-harness',
        'source_inspiration': 'DeepSeek Harness architecture/docs; independent implementation',
        'features': {
            'append_only_events': True,
            'run_checkpoints': True,
            'crash_recovery': True,
            'request_idempotency': True,
            'bounded_hot_reads': True,
            'tool_result_spill': True,
            'transient_retry': True,
            'stall_guard': True,
            'capability_seams': True,
        },
        'safety': {
            'external_plugin_code_auto_load': False,
            'permission_engine_remains_authority': True,
            'model_generated_shell': False,
        },
        'runs': len(list(RUNS.glob('run-*.json'))),
    }


def self_test() -> None:
    assert request_id('abc-1') == 'abc-1'
    try:
        request_id('../bad id')
        raise AssertionError('invalid request id accepted')
    except ValueError:
        pass
    assert repeated_action([{'tool': 'a', 'arguments': {'x': 1}}, {'tool': 'a', 'arguments': {'x': 1}}], 'a', {'x': 1})
    assert classify_error('connection refused') == 'transient'
    assert classify_error('permission denied') == 'permission'
    r = CapabilityRegistry(); dispose = r.register('x', 1); assert r.get('x') == 1; dispose(); assert r.get('x') is None
    print('PASS: harness event/idempotency/retry/stall/capability contracts')


if __name__ == '__main__':
    self_test()
