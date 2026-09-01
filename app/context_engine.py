from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('KIMIK3_DATA_DIR', str(ROOT / 'data'))).expanduser()
SESSIONS = DATA / 'sessions'

TEXT_EXTS = {'.md', '.txt', '.json', '.jsonl', '.yaml', '.yml', '.toml'}


def approx_tokens(text: str) -> int:
    """Cheap local token estimate. It is deliberately an estimate, not tokenizer output."""
    if not text:
        return 0
    return max(1, int(math.ceil(len(text) / 3.6)))


def _safe_id(value: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9_.-]+', '-', str(value or 'default')).strip('-')
    return (value or 'default')[:80]


def _session_path(session_id: str) -> Path:
    SESSIONS.mkdir(parents=True, exist_ok=True)
    return SESSIONS / f'{_safe_id(session_id)}.jsonl'


def append_turn(session_id: str, user: str, assistant: str) -> None:
    p = _session_path(session_id)
    row = {'ts': time.time(), 'user': str(user)[:20000], 'assistant': str(assistant)[:30000]}
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def load_turns(session_id: str, limit: int = 24) -> list[dict]:
    p = _session_path(session_id)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding='utf-8', errors='ignore').splitlines()[-max(1, limit):]:
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                out.append(item)
        except Exception:
            pass
    return out


def history_text(session_id: str, token_budget: int = 900) -> str:
    """Return recent conversation from newest backwards within a small working-set budget."""
    chosen = []
    used = 0
    for turn in reversed(load_turns(session_id, 32)):
        block = f"User: {turn.get('user', '')}\nAssistant: {turn.get('assistant', '')}"
        cost = approx_tokens(block)
        if chosen and used + cost > token_budget:
            break
        chosen.append(block)
        used += cost
        if used >= token_budget:
            break
    return '\n\n'.join(reversed(chosen))


def _tree_tokens(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    total = files = 0
    for p in path.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            if p.stat().st_size > 1024 * 1024:
                continue
            text = p.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        total += approx_tokens(text)
        files += 1
    return total, files


def _file_tokens(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return 0, 0
    count = 0
    try:
        obj = json.loads(text)
        count = len(obj) if isinstance(obj, (list, dict)) else 1
    except Exception:
        count = 1 if text.strip() else 0
    return approx_tokens(text), count


def context_snapshot(
    index_records: list[dict],
    memory_items: list[dict],
    session_id: str = 'default',
    virtual_limit: int = 1_000_000,
    working_limit: int = 4096,
    native_limit: int = 40960,
    working_used: int = 0,
) -> dict:
    project_tokens = sum(approx_tokens(str(x.get('text', ''))) for x in index_records)
    memory_tokens = sum(approx_tokens(str(x.get('text', ''))) for x in memory_items)
    turns = load_turns(session_id, 64)
    history_tokens = sum(
        approx_tokens(str(x.get('user', ''))) + approx_tokens(str(x.get('assistant', ''))) for x in turns
    )
    skills_tokens, skills_count = _tree_tokens(ROOT / 'skills')
    mcp_tokens, mcp_count = _file_tokens(DATA / 'mcp_tools.json')
    if not mcp_tokens:
        mcp_tokens, mcp_count = _file_tokens(ROOT / 'config' / 'mcp.json')
    agents_tokens, agents_count = _file_tokens(DATA / 'custom_agents.json')

    rows = [
        {'key': 'skills', 'label': 'Skills', 'tokens': skills_tokens, 'count': skills_count},
        {'key': 'project', 'label': 'Project knowledge', 'tokens': project_tokens, 'count': len(index_records)},
        {'key': 'memory', 'label': 'Memory', 'tokens': memory_tokens, 'count': len(memory_items)},
        {'key': 'history', 'label': 'Conversation', 'tokens': history_tokens, 'count': len(turns)},
        {'key': 'mcp', 'label': 'MCP tools', 'tokens': mcp_tokens, 'count': mcp_count},
        {'key': 'agents', 'label': 'Custom agents', 'tokens': agents_tokens, 'count': agents_count},
    ]
    indexed_total = sum(x['tokens'] for x in rows)
    used = min(indexed_total, virtual_limit)
    free = max(0, virtual_limit - used)
    for row in rows:
        row['percent'] = round((row['tokens'] / virtual_limit) * 100, 2) if virtual_limit else 0
    rows.append({'key': 'free', 'label': 'Free space', 'tokens': free, 'count': 0,
                 'percent': round((free / virtual_limit) * 100, 2) if virtual_limit else 0})
    return {
        'virtual': {
            'limit_tokens': virtual_limit,
            'used_tokens': used,
            'indexed_total_tokens': indexed_total,
            'overflow_tokens': max(0, indexed_total - virtual_limit),
            'percent': round((used / virtual_limit) * 100, 2) if virtual_limit else 0,
            'rows': rows,
        },
        'working': {
            'limit_tokens': working_limit,
            'used_tokens': min(max(0, working_used), working_limit),
            'percent': round((min(max(0, working_used), working_limit) / working_limit) * 100, 2) if working_limit else 0,
        },
        'native': {'limit_tokens': native_limit},
        'session_id': _safe_id(session_id),
        'estimate': True,
    }
