#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import kimik3_lite as core
import parallel_agent as parallel
import team_runtime as team

RUNS: dict[str, dict] = {}
DATA = Path(os.environ.get('KIMIK3_DATA_DIR', str(core.DATA))).expanduser()
TEAM_DIR = DATA / 'agent-teams'
_RUN_LOCK = threading.RLock()

ROLE_PROMPTS = {
    'research': 'Thu thập evidence từ project knowledge và chỉ nêu điều có căn cứ.',
    'specialist': 'Phân tích chuyên sâu yêu cầu, tìm rủi ro và đề xuất thực thi.',
    'critic': 'Phản biện kết quả trước đó, chỉ ra mâu thuẫn, thiếu sót và giả định yếu.',
    'verifier': 'Kiểm tra tính nhất quán, evidence và acceptance criteria trước khi kết luận.',
    'synthesizer': 'Tổng hợp kết quả agent thành câu trả lời ngắn gọn, ưu tiên evidence và nêu bất đồng còn lại.',
}


def capacity() -> dict:
    c = parallel.worker_limit()
    return {
        **c,
        'strategy': 'durable-dependency-graph',
        'max_team_agents': 4,
        'write_lane': 'serial-permission-gated',
        'durable_mailbox': True,
        'task_cas': True,
        'live_control': 'cooperative-step-boundary',
    }


def _budget(workers: int) -> dict:
    c = capacity(); ram = float(c.get('ram_gb') or 4)
    per = max(512, min(2048, int(4096 / max(1, workers))))
    return {'workers': workers, 'token_budget_per_agent': per, 'team_token_budget': per * workers, 'ram_gb': ram}


def plan(query: str, workers: int | None = None) -> dict:
    cap = capacity(); w = max(1, min(int(workers or cap.get('workers') or 1), 4))
    nodes = [
        {'id': 'research', 'role': 'research', 'name': 'Research Agent', 'depends_on': [], 'read_only': True, 'requires': ['llm', 'retrieval', 'shared_memory']},
        {'id': 'specialist', 'role': 'specialist', 'name': 'Specialist Agent', 'depends_on': [], 'read_only': True, 'requires': ['llm', 'retrieval', 'shared_memory']},
        {'id': 'critic', 'role': 'critic', 'name': 'Critic Agent', 'depends_on': ['research', 'specialist'], 'read_only': True, 'requires': ['llm', 'shared_memory']},
        {'id': 'verifier', 'role': 'verifier', 'name': 'Verifier Agent', 'depends_on': ['research', 'specialist'], 'read_only': True, 'requires': ['llm', 'shared_memory']},
        {'id': 'synthesis', 'role': 'synthesizer', 'name': 'Synthesis', 'depends_on': ['critic', 'verifier'], 'read_only': True, 'requires': ['llm', 'shared_memory']},
    ]
    if w == 1:
        for i, node in enumerate(nodes[1:], 1):
            node['depends_on'] = [nodes[i - 1]['id']]
    return {
        'id': 'team-plan-' + uuid.uuid4().hex[:10], 'query': query, 'nodes': nodes,
        'edges': [{'from': d, 'to': n['id']} for n in nodes for d in n['depends_on']],
        'capacity': cap, 'budget': _budget(w), 'policy': 'parallel-read-serial-write',
    }


def _context(query: str) -> str:
    try:
        hits = core.retrieve(query, 6)
        return '\n\n'.join(f"[{i+1}] {x.get('path', '')}\n{x.get('text', '')[:1600]}" for i, x in enumerate(hits))
    except Exception:
        return ''


def _call(node: dict, query: str, shared: dict, profile: str, model: str | None, host: str, budget: int, team_id: str, member_id: str) -> dict:
    team.require_capabilities(node.get('requires') or [])
    if team.is_cancelled(team_id, member_id):
        return {'ok': False, 'output': '', 'error': 'cancelled before model step', 'cancelled': True, 'elapsed_ms': 0}
    steering = team.consume_steering(team_id, member_id)
    cfg = core.profile_config(profile); tag = model or cfg.get('ollama_name')
    deps = '\n\n'.join(f"{k}: {v.get('output', '')}" for k, v in shared.items())
    ctx = _context(query) if node['role'] in {'research', 'specialist'} else ''
    steer_text = '\n'.join('- ' + x for x in steering) if steering else '(không có)'
    prompt = (
        f"ROLE: {ROLE_PROMPTS[node['role']]}\nYÊU CẦU: {query}\n"
        f"STEERING MỚI:\n{steer_text}\nSHARED RESULTS:\n{deps or '(chưa có)'}\n"
        f"PROJECT EVIDENCE:\n{ctx or '(không có)'}\n"
        f"Trả lời tiếng Việt, tối đa {budget} tokens. Không tuyên bố đã sửa file/tool."
    )
    started = time.time()
    try:
        out = core.ollama_chat(tag, [{'role': 'user', 'content': prompt}], host, budget, .12, min(int(cfg.get('working_context', 4096)), 4096))
        if team.is_cancelled(team_id, member_id):
            return {'ok': False, 'output': '', 'error': 'cancelled after current model step', 'cancelled': True, 'elapsed_ms': round((time.time() - started) * 1000)}
        return {'ok': True, 'output': out, 'steering_applied': steering, 'elapsed_ms': round((time.time() - started) * 1000)}
    except Exception as e:
        return {'ok': False, 'output': '', 'error': str(e), 'elapsed_ms': round((time.time() - started) * 1000)}


def _resolve_conflicts(shared: dict) -> dict:
    texts = [v.get('output', '') for k, v in shared.items() if k in {'research', 'specialist', 'critic', 'verifier'} and v.get('output')]
    conflicts = []
    if len(texts) >= 2:
        neg = sum('không ' in t.casefold() or 'chưa ' in t.casefold() for t in texts)
        pos = sum('nên ' in t.casefold() or 'cần ' in t.casefold() for t in texts)
        if neg and pos:
            conflicts.append('Có quan điểm/độ chắc chắn khác nhau giữa các agent; ưu tiên Verifier và evidence.')
    return {'count': len(conflicts), 'items': conflicts, 'resolution': 'verifier-evidence-priority'}


def _persist_run(run: dict) -> None:
    TEAM_DIR.mkdir(parents=True, exist_ok=True)
    path = TEAM_DIR / f"{run['id']}.json"
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def _init_run(query: str, profile: str, model: str | None, host: str, session_id: str, workers: int | None) -> dict:
    p = plan(query, workers); rid = 'team-' + uuid.uuid4().hex[:12]
    durable = team.create(session_id, query)
    run = {
        'id': rid, 'team_id': durable['id'], 'status': 'running', 'query': query, 'plan': p,
        'nodes': {}, 'shared_memory': {}, 'started_at': time.time(), 'session_id': session_id,
        'profile': profile, 'model': model, 'host': host, 'answer': None,
    }
    for node in p['nodes']:
        member = team.upsert_member(durable['id'], node['id'], node['name'], node['role'], 'active')
        node['member_id'] = member['id']
    for node in p['nodes']:
        team.create_task(durable['id'], node['id'], node['name'], ROLE_PROMPTS[node['role']], node['depends_on'], [])
    with _RUN_LOCK:
        RUNS[rid] = run
        _persist_run(run)
    return run


def _execute(run: dict) -> dict:
    p = run['plan']; pending = {n['id']: dict(n, status='pending') for n in p['nodes']}
    budget = p['budget']['token_budget_per_agent']; max_workers = p['budget']['workers']; team_id = run['team_id']
    root_id = str(team.fold(team_id).get('root_session_id') or 'default')
    try:
        while pending:
            ready = [n for n in pending.values() if all(run['nodes'].get(d, {}).get('status') == 'done' for d in n['depends_on'])]
            if not ready:
                break
            batch = [n for n in ready if n['id'] != 'synthesis'][:max_workers] or ready[:1]
            started_tasks: dict[str, dict] = {}
            for node in batch:
                state = team.fold(team_id); task = state['tasks'][node['id']]
                started_tasks[node['id']] = team.update_task(team_id, node['id'], task['revision'], 'start', node['member_id'])
                msg = team.queue_message(team_id, root_id, node['member_id'], f"Task {node['id']}: {run['query']}", 'wakeup')
                team.deliver_message(team_id, msg['id'])
                run['nodes'][node['id']] = {**node, 'status': 'running', 'started_at': time.time()}
            _persist_run(run)
            snapshot = dict(run['shared_memory'])
            with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(batch))), thread_name_prefix='kimik3-team') as ex:
                fut = {ex.submit(_call, node, run['query'], snapshot, run['profile'], run['model'], run['host'], budget, team_id, node['member_id']): node for node in batch}
                for f in as_completed(fut):
                    node = fut[f]
                    try:
                        result = f.result()
                    except Exception as exc:
                        result = {'ok': False, 'output': '', 'error': str(exc), 'elapsed_ms': 0}
                    status = 'done' if result.get('ok') else ('cancelled' if result.get('cancelled') else 'error')
                    state = {**node, **result, 'status': status}
                    run['nodes'][node['id']] = state
                    if result.get('ok'):
                        run['shared_memory'][node['id']] = {'output': result.get('output', '')[:12000]}
                    task = team.fold(team_id)['tasks'][node['id']]
                    team.update_task(team_id, node['id'], task['revision'], 'complete' if result.get('ok') else 'block', node['member_id'])
                    team.upsert_member(team_id, node['id'], node['name'], node['role'], 'done' if result.get('ok') else status, result.get('error'))
                    reply = result.get('output') or result.get('error') or status
                    msg = team.queue_message(team_id, node['member_id'], root_id, str(reply)[:12000], 'quiet')
                    team.deliver_message(team_id, msg['id'])
                    pending.pop(node['id'], None)
                    _persist_run(run)
            failed = {k for k, v in run['nodes'].items() if v.get('status') in {'error', 'cancelled', 'blocked'}}
            if failed:
                for nid, node in list(pending.items()):
                    if any(d in failed for d in node['depends_on']):
                        run['nodes'][nid] = {**node, 'status': 'blocked', 'error': 'dependency failed or cancelled'}
                        task = team.fold(team_id)['tasks'][nid]
                        team.update_task(team_id, nid, task['revision'], 'block')
                        team.upsert_member(team_id, nid, node['name'], node['role'], 'failed', 'dependency failed or cancelled')
                        pending.pop(nid, None)
                _persist_run(run)
        conflicts = _resolve_conflicts(run['shared_memory']); run['conflicts'] = conflicts
        answer = (run['nodes'].get('synthesis') or {}).get('output') or (run['nodes'].get('verifier') or {}).get('output') or (run['nodes'].get('specialist') or {}).get('output') or 'Agent Team chưa tạo được kết quả.'
        run['answer'] = answer
        run['status'] = 'done' if any(v.get('status') == 'done' for v in run['nodes'].values()) else 'error'
    except Exception as exc:
        run['status'] = 'error'; run['error'] = str(exc)[:2000]
    run['elapsed_ms'] = round((time.time() - run['started_at']) * 1000)
    team.settle(team_id, 'done' if run['status'] == 'done' else 'failed')
    _persist_run(run)
    return {'answer': run.get('answer') or run.get('error') or 'Agent Team lỗi.', 'team': public(run)}


def run(query: str, profile: str = 'balanced', model: str | None = None, host: str = 'http://127.0.0.1:11434', session_id: str = 'default', workers: int | None = None) -> dict:
    return _execute(_init_run(query, profile, model, host, session_id, workers))


def start(query: str, profile: str = 'balanced', model: str | None = None, host: str = 'http://127.0.0.1:11434', session_id: str = 'default', workers: int | None = None) -> dict:
    obj = _init_run(query, profile, model, host, session_id, workers)
    thread = threading.Thread(target=_execute, args=(obj,), daemon=True, name='kimik3-team-' + obj['id'][-6:])
    thread.start()
    return public(obj)


def public(run: dict) -> dict:
    team_id = run.get('team_id')
    durable = team.fold(team_id) if team_id else {}
    return {
        'run_id': run['id'], 'team_id': team_id, 'status': run.get('status'), 'plan': run['plan'],
        'nodes': run.get('nodes', {}), 'conflicts': run.get('conflicts', {}),
        'elapsed_ms': run.get('elapsed_ms', round((time.time() - run['started_at']) * 1000)),
        'shared_keys': list(run.get('shared_memory', {})), 'answer': run.get('answer'),
        'durable': {
            'status': durable.get('status'), 'members': list((durable.get('members') or {}).values()),
            'tasks': list((durable.get('tasks') or {}).values()),
            'mailbox_pending': sum(not x.get('delivered') for x in (durable.get('mailbox') or [])),
        },
    }


def get(run_id: str) -> dict | None:
    obj = RUNS.get(run_id)
    if obj:
        return public(obj)
    path = TEAM_DIR / f'{run_id}.json'
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
        return public(obj) if isinstance(obj, dict) else None
    except Exception:
        return None


def state(team_id: str) -> dict:
    return team.fold(team_id)


def mailbox(team_id: str) -> list[dict]:
    return team.fold(team_id).get('mailbox', [])


def tasks(team_id: str) -> list[dict]:
    return list(team.fold(team_id).get('tasks', {}).values())


def events(team_id: str, limit: int = 200) -> list[dict]:
    return team.events(team_id, limit)


def control(run_id: str, target: str, action: str, instruction: str = '') -> dict:
    info = get(run_id)
    if not info:
        raise KeyError('Không tìm thấy team run')
    team_id = str(info.get('team_id') or '')
    state_now = team.fold(team_id); members = state_now.get('members') or {}
    target_id = target if target in members else next((m['id'] for m in members.values() if m.get('node_id') == target), None)
    if not target_id:
        raise KeyError('Không tìm thấy target agent')
    if action == 'steer':
        return team.steer(team_id, target_id, instruction)
    if action == 'cancel':
        return team.cancel(team_id, target_id)
    raise ValueError('action phải là steer hoặc cancel')


def update_task(team_id: str, task_id: str, expected_revision: int, action: str, owner_id: str | None = None) -> dict:
    return team.update_task(team_id, task_id, expected_revision, action, owner_id)


def recover() -> list[str]:
    return team.recover_open_teams()


def self_test() -> None:
    p = plan('Review UI/UX và code', 2)
    assert len(p['nodes']) == 5
    assert any(e['from'] == 'research' and e['to'] == 'critic' for e in p['edges'])
    assert p['policy'] == 'parallel-read-serial-write'
    assert p['budget']['workers'] <= 2
    assert all(n.get('requires') for n in p['nodes'])
    team.require_capabilities(['llm', 'shared_memory'])
    print('PASS: durable agent team graph/capability contract')


if __name__ == '__main__':
    self_test()
