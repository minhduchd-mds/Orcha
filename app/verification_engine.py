#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Verification recipes are host-owned argv arrays. The model can request a
# verification profile but cannot inject shell text or arbitrary commands.
PY_COMPILE = [
    'app/kimik3_lite.py', 'app/context_engine.py', 'app/workflow_engine.py',
    'app/studio_server.py', 'app/studio_server_v64.py', 'app/studio_server_v65.py',
    'app/studio_server_v66.py', 'app/studio_server_v67.py', 'app/studio_server_v68.py',
    'app/studio_server_v69.py', 'app/harness_runtime.py', 'app/verification_engine.py',
    'app/hermes_runtime.py', 'app/agent_runtime.py', 'app/mcp_gateway.py',
    'app/permission_engine.py', 'app/model_registry.py', 'app/parallel_agent.py',
    'app/agent_team.py', 'app/self_improvement.py', 'app/maintenance.py',
]
SELF_TESTS = [
    'app/harness_runtime.py', 'app/model_registry.py', 'app/hermes_runtime.py',
    'app/permission_engine.py', 'app/mcp_gateway.py', 'app/parallel_agent.py',
    'app/agent_team.py', 'app/self_improvement.py', 'app/maintenance.py',
]
JS_CHECKS = [
    'studio/app.js', 'studio/model-manager.js', 'studio/design-agent.js',
    'studio/parallel-agents.js', 'studio/agent-team.js', 'studio/final-intelligence.js',
    'studio/hermes.js', 'studio/harness.js',
]


def _run(argv: list[str], cwd: Path, timeout: int) -> dict:
    started = time.perf_counter()
    try:
        cp = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True,
            timeout=max(1, min(int(timeout), 180)), shell=False,
        )
        return {
            'argv': argv,
            'ok': cp.returncode == 0,
            'returncode': cp.returncode,
            'elapsed_ms': round((time.perf_counter() - started) * 1000),
            'stdout': cp.stdout[-5000:],
            'stderr': cp.stderr[-5000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            'argv': argv, 'ok': False, 'returncode': None,
            'elapsed_ms': round((time.perf_counter() - started) * 1000),
            'stdout': str(exc.stdout or '')[-3000:], 'stderr': 'verification timeout',
        }
    except Exception as exc:
        return {'argv': argv, 'ok': False, 'returncode': None, 'elapsed_ms': 0, 'stdout': '', 'stderr': str(exc)[:3000]}


def recipes(root: str | Path = ROOT) -> list[dict]:
    root = Path(root).resolve()
    rows: list[dict] = []
    py = [x for x in PY_COMPILE if (root / x).exists()]
    if py:
        rows.append({'id': 'python-compile', 'label': 'Python compile', 'argv': [sys.executable, '-m', 'py_compile', *py]})
    for i, path in enumerate(SELF_TESTS):
        if (root / path).exists():
            rows.append({'id': 'self-' + Path(path).stem, 'label': 'Self test ' + Path(path).stem, 'argv': [sys.executable, path]})
    node = shutil.which('node')
    if node:
        for path in JS_CHECKS:
            if (root / path).exists():
                rows.append({'id': 'node-' + Path(path).stem, 'label': 'JS syntax ' + Path(path).name, 'argv': [node, '--check', path]})
    return rows


def verify(root: str | Path = ROOT, profile: str = 'fast', timeout_per_check: int = 45) -> dict:
    root = Path(root).resolve()
    if root != ROOT.resolve():
        raise ValueError('Verifier v1 chỉ chạy trên source bundle KimiK3-Lite đã tin cậy')
    available = recipes(root)
    if profile == 'fast':
        selected = [x for x in available if x['id'] in {'python-compile', 'self-harness_runtime', 'self-model_registry', 'self-hermes_runtime'} or x['id'].startswith('node-app') or x['id'].startswith('node-harness')]
    elif profile == 'full':
        selected = available
    else:
        raise ValueError('profile verifier chỉ nhận fast hoặc full')
    started = time.time()
    results = []
    for recipe in selected:
        result = _run(list(recipe['argv']), root, timeout_per_check)
        result['id'] = recipe['id']; result['label'] = recipe['label']
        results.append(result)
        if not result['ok'] and profile == 'fast':
            break
    return {
        'profile': profile,
        'ok': bool(results) and all(x['ok'] for x in results),
        'checks': results,
        'started_at': started,
        'finished_at': time.time(),
        'security': {'shell': False, 'host_owned_recipes': True, 'model_argv': False},
    }


def self_test() -> None:
    rows = recipes(ROOT)
    assert any(x['id'] == 'python-compile' for x in rows)
    assert all(isinstance(x['argv'], list) and x['argv'] for x in rows)
    print('PASS: safe verification recipes')


if __name__ == '__main__':
    if '--run-fast' in sys.argv:
        print(json.dumps(verify(ROOT, 'fast'), ensure_ascii=False, indent=2))
    else:
        self_test()
