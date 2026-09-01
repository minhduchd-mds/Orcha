#!/usr/bin/env python3
from __future__ import annotations
import json, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('KIMIK3_DATA_DIR', str(ROOT/'data'))).expanduser()
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
    GRANTS.write_text(json.dumps(items[-200:], ensure_ascii=False, indent=2), encoding='utf-8')


def grant(permission: str, scope: str = 'session', ttl_seconds: int = 3600, session_id: str = 'default') -> dict:
    now = time.time()
    item = {
        'permission': permission,
        'scope': scope,
        'session_id': session_id,
        'created_at': now,
        'expires_at': now + max(60, ttl_seconds) if scope == 'session' else 0,
    }
    items = [x for x in grants() if not (x.get('permission') == permission and x.get('session_id') == session_id)]
    items.append(item); _save(items)
    return item


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
        if x.get('scope') == 'always' or float(x.get('expires_at') or 0) > now:
            return True
    return False


def decision(permission: str, skill_permissions: dict | None = None, session_id: str = 'default') -> dict:
    cfg = policy(); rules = cfg.get('rules', {})
    mode = None
    if isinstance(skill_permissions, dict):
        mode = skill_permissions.get(permission)
    if mode not in {'auto', 'confirm', 'deny'}:
        mode = rules.get(permission, cfg.get('default', 'confirm'))
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


def self_test() -> None:
    assert decision('filesystem.read')['decision'] == 'auto'
    assert decision('shell.execute')['decision'] == 'deny'
    assert decision('filesystem.write')['risk'] == 'yellow'
    print('PASS: permission engine')


if __name__ == '__main__':
    self_test()
