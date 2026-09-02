#!/usr/bin/env python3
from __future__ import annotations
import storage
import json, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = storage.DATA
POLICY = ROOT / 'config' / 'permissions.json'
GRANTS = DATA / 'permission_grants.json'

DEFAULT_POLICY = {
    'default': 'confirm',
    'rules': {
        'project.search': 'auto',
        'filesystem.read': 'auto',
        'filesystem.list': 'auto',
        'git.read': 'auto',
        'browser.read': 'auto',
        'computer.read': 'auto',
        'computer.focus': 'auto',
        'context.read': 'auto',
        'memory.read': 'auto',
        'filesystem.write': 'confirm',
        'browser.write': 'confirm',
        'computer.input': 'confirm',
        'computer.launch': 'confirm',
        'git.write': 'confirm',
        'shell.execute': 'deny',
        'system.admin': 'deny',
    }
}

RISK = {
    'auto': 'green',
    'confirm': 'yellow',
    'deny': 'red',
}


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def policy() -> dict:
    cfg = _load(POLICY, DEFAULT_POLICY)
    if not isinstance(cfg, dict):
        cfg = DEFAULT_POLICY
    cfg.setdefault('default', 'confirm')
    cfg.setdefault('rules', {})
    return cfg


def grants() -> list[dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    out = _load(GRANTS, [])
    return out if isinstance(out, list) else []


def _save(items: list[dict]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    storage.atomic_json(GRANTS, items[-200:])


@storage.serialized
def grant(permission: str, scope: str = 'session', ttl_seconds: int = 3600, session_id: str = 'default', action_key: str | None = None) -> dict:
    if scope not in {'once', 'session'}: raise ValueError('Scope must be once or session')
    if scope == 'once' and not action_key: raise ValueError('An exact action is required')
    if decision(permission, session_id=session_id)['decision'] == 'deny': raise ValueError('Permission denied by policy')
    now = time.time()
    item = {
        'permission': permission,
        'scope': scope,
        'session_id': session_id,
        'created_at': now,
        'expires_at': now + min(3600, max(1, ttl_seconds)),
        'action_key': action_key if scope == 'once' else None,
    }
    items = [x for x in grants() if not (x.get('permission') == permission and x.get('session_id') == session_id)]
    items.append(item); _save(items)
    return item


@storage.serialized
def revoke(permission: str | None = None, session_id: str = 'default') -> int:
    old = grants()
    if permission:
        new = [x for x in old if not (x.get('permission') == permission and x.get('session_id') == session_id)]
    else:
        new = [x for x in old if x.get('session_id') != session_id]
    _save(new)
    return len(old) - len(new)


def _granted(permission: str, session_id: str) -> bool:
    now = time.time()
    for x in grants():
        if x.get('permission') != permission or x.get('session_id') != session_id:
            continue
        if x.get('scope') == 'session' and float(x.get('expires_at') or 0) > now:
            return True
    return False


def decision(permission: str, skill_permissions: dict | None = None, session_id: str = 'default') -> dict:
    cfg = policy(); rules = cfg.get('rules', {})
    rank = {'auto': 0, 'confirm': 1, 'deny': 2}
    mode = rules.get(permission, cfg.get('default', 'confirm'))
    if mode not in rank: mode = 'deny'
    requested = (skill_permissions or {}).get(permission)
    if requested in rank and rank[requested] > rank[mode]: mode = requested
    if mode == 'confirm' and _granted(permission, session_id):
        mode = 'auto'
    return {
        'permission': permission,
        'decision': mode,
        'risk': RISK.get(mode, 'yellow'),
        'granted': mode == 'auto',
    }


def classify_tool(tool: dict, skill_permissions: dict | None = None, session_id: str = 'default') -> dict:
    permission = str(tool.get('permission') or 'unknown')
    d = decision(permission, skill_permissions, session_id)
    return {**tool, **d}


@storage.serialized
def action_granted(permission, session_id, action_key, consume=False):
    if not action_key: return False
    items = grants()
    for item in items:
        if (item.get('scope') == 'once' and item.get('permission') == permission
                and item.get('session_id') == session_id and item.get('action_key') == action_key
                and item.get('expires_at', 0) > time.time()):
            if consume:
                items.remove(item); _save(items)
            return True
    return False


def self_test() -> None:
    assert decision('filesystem.read')['decision'] == 'auto'
    assert decision('shell.execute')['decision'] == 'deny'
    assert decision('filesystem.write')['risk'] == 'yellow'
    print('PASS: permission engine')


if __name__ == '__main__':
    self_test()


@storage.serialized
def revoke_action(action_key,session_id):
    items=grants();remaining=[g for g in items if not (g.get('action_key')==action_key and g.get('session_id')==session_id)]
    _save(remaining)
    return len(items)-len(remaining)
