#!/usr/bin/env python3
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / 'skills'


def _scalar(v: str) -> Any:
    v = v.strip()
    if not v:
        return ''
    if v.lower() in {'true', 'false'}:
        return v.lower() == 'true'
    if v.startswith('[') and v.endswith(']'):
        return [x.strip().strip('"\'') for x in v[1:-1].split(',') if x.strip()]
    try:
        return int(v)
    except ValueError:
        return v.strip('"\'')


def _frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith('---'):
        return {}, text
    parts = text.split('---', 2)
    if len(parts) < 3:
        return {}, text
    raw, body = parts[1], parts[2].lstrip('\n')
    data: dict[str, Any] = {}
    stack: list[tuple[int, dict]] = [(-1, data)]
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip(' '))
        stripped = line.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if ':' not in stripped:
            continue
        key, value = stripped.split(':', 1)
        key = key.strip(); value = value.strip()
        if value:
            parent[key] = _scalar(value)
        else:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
    return data, body


def _section(body: str, title: str) -> str:
    m = re.search(rf'(?ims)^#+\s*{re.escape(title)}\s*$\n(.*?)(?=^#+\s|\Z)', body)
    return m.group(1).strip() if m else ''


def _bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r'(?m)^\s*(?:[-*]|\d+[.)])\s+(.+)$', text)]


def load_skill(path: Path) -> dict:
    text = path.read_text(encoding='utf-8', errors='ignore')
    meta, body = _frontmatter(text)
    sid = str(meta.get('id') or path.parent.name)
    triggers = meta.get('triggers', [])
    if isinstance(triggers, dict):
        triggers = list(triggers.values())
    if isinstance(triggers, str):
        triggers = [triggers]
    # Also accept trigger bullets from an optional body section.
    triggers = [str(x) for x in triggers] + _bullets(_section(body, 'Triggers'))
    workflow = _bullets(_section(body, 'Workflow'))
    permissions = meta.get('permissions', {}) if isinstance(meta.get('permissions', {}), dict) else {}
    requires = meta.get('requires', {}) if isinstance(meta.get('requires', {}), dict) else {}
    return {
        'id': sid,
        'name': str(meta.get('name') or sid.replace('-', ' ').title()),
        'version': str(meta.get('version') or '1.0.0'),
        'description': str(meta.get('description') or _section(body, 'Objective')[:300]),
        'triggers': list(dict.fromkeys(x.strip() for x in triggers if x.strip())),
        'permissions': permissions,
        'requires': requires,
        'workflow': workflow,
        'rules': _bullets(_section(body, 'Rules')),
        'verification': _bullets(_section(body, 'Verification')),
        'path': str(path),
        'body': body,
    }


def list_skills() -> list[dict]:
    if not SKILLS_DIR.exists():
        return []
    out = []
    for p in sorted(SKILLS_DIR.glob('*/SKILL.md')):
        try:
            out.append(load_skill(p))
        except Exception as exc:
            out.append({'id': p.parent.name, 'name': p.parent.name, 'error': str(exc), 'path': str(p)})
    return out


def match_skill(query: str) -> dict | None:
    q = query.casefold()
    scored: list[tuple[float, dict]] = []
    for skill in list_skills():
        score = 0.0
        for trigger in skill.get('triggers', []):
            t = trigger.casefold().strip()
            if not t:
                continue
            if t in q:
                score += 5.0 + min(len(t) / 10.0, 3.0)
            else:
                words = [w for w in re.findall(r'[\wÀ-ỹ]+', t) if len(w) > 2]
                score += sum(0.6 for w in words if w in q)
        name = skill.get('name', '').casefold()
        if name and name in q:
            score += 4
        if score > 0:
            scored.append((score, skill))
    if not scored:
        return None
    score, skill = max(scored, key=lambda x: x[0])
    return {**skill, 'match_score': round(score, 2)}


def compact_skill(skill: dict | None) -> dict | None:
    if not skill:
        return None
    return {k: skill.get(k) for k in ('id','name','version','description','triggers','permissions','requires','workflow','rules','verification','path','match_score')}


def self_test() -> None:
    sample = '''---\nid: demo\nname: Demo\nversion: 1.0\npermissions:\n  filesystem.read: auto\n---\n# Objective\nTest\n# Workflow\n1. Read input\n2. Verify output\n'''
    meta, body = _frontmatter(sample)
    assert meta['id'] == 'demo'
    assert meta['permissions']['filesystem.read'] == 'auto'
    assert _bullets(_section(body, 'Workflow')) == ['Read input', 'Verify output']
    print('PASS: skill runtime')


if __name__ == '__main__':
    self_test()
    print(json.dumps([compact_skill(x) for x in list_skills()], ensure_ascii=False, indent=2))
