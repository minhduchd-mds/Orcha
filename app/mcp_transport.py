#!/usr/bin/env python3
from __future__ import annotations
import json, os, queue, subprocess, sys, threading, time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _expand(value: str) -> str:
    value = str(value)
    if value == '@python':
        return sys.executable
    return value.replace('{root}', str(ROOT)).replace('{python}', sys.executable)


class MCPError(RuntimeError):
    pass


class StdioClient:
    """Small synchronous MCP stdio client.

    A client instance owns one subprocess. Messages are newline-delimited JSON-RPC.
    The runtime intentionally starts configured commands only; model output cannot
    choose or alter the executable command.
    """

    def __init__(self, server: dict, timeout: float = 12.0):
        self.server = dict(server)
        self.timeout = float(timeout)
        self.proc: subprocess.Popen | None = None
        self.seq = 0
        self._q: queue.Queue = queue.Queue()
        self._reader: threading.Thread | None = None

    def start(self) -> None:
        if self.proc and self.proc.poll() is None:
            return
        command = _expand(str(self.server.get('command') or ''))
        args = [_expand(str(x)) for x in (self.server.get('args') or [])]
        if not command:
            raise MCPError('MCP server command is empty')
        env = os.environ.copy()
        for k, v in (self.server.get('env') or {}).items():
            env[str(k)] = _expand(str(v))
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
        self.proc = subprocess.Popen(
            [command, *args], cwd=str(ROOT), env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace', bufsize=1,
            creationflags=flags,
        )
        self._reader = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader.start()
        self.initialize()

    def _reader_loop(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._q.put(json.loads(line))
            except Exception:
                self._q.put({'_invalid': line})

    def _send(self, obj: dict) -> None:
        if not self.proc or self.proc.poll() is not None or not self.proc.stdin:
            raise MCPError('MCP server is not running')
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n')
        self.proc.stdin.flush()

    def notify(self, method: str, params: dict | None = None) -> None:
        self._send({'jsonrpc':'2.0','method':method,'params':params or {}})

    def request(self, method: str, params: dict | None = None) -> Any:
        self.seq += 1; rid = self.seq
        self._send({'jsonrpc':'2.0','id':rid,'method':method,'params':params or {}})
        deadline = time.time() + self.timeout
        parked=[]
        try:
            while time.time() < deadline:
                try:
                    msg = self._q.get(timeout=max(.05, deadline-time.time()))
                except queue.Empty:
                    break
                if msg.get('id') != rid:
                    parked.append(msg); continue
                if msg.get('error'):
                    err=msg['error']; raise MCPError(str(err.get('message') or err))
                return msg.get('result')
            raise MCPError(f'MCP timeout calling {method}')
        finally:
            for msg in parked:
                self._q.put(msg)

    def initialize(self) -> dict:
        result = self.request('initialize', {
            'protocolVersion': str(self.server.get('protocol_version') or '2025-06-18'),
            'capabilities': {},
            'clientInfo': {'name':'KimiK3-Lite','version':'6.1.0'},
        }) or {}
        self.notify('notifications/initialized', {})
        return result

    def list_tools(self) -> list[dict]:
        result=self.request('tools/list', {}) or {}
        return result.get('tools', []) if isinstance(result, dict) else []

    def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        return self.request('tools/call', {'name':name,'arguments':arguments or {}})

    def close(self) -> None:
        if not self.proc: return
        try:
            if self.proc.stdin: self.proc.stdin.close()
        except Exception: pass
        try: self.proc.terminate(); self.proc.wait(timeout=1.5)
        except Exception:
            try: self.proc.kill()
            except Exception: pass
        self.proc=None

    def __enter__(self): self.start(); return self
    def __exit__(self,*_): self.close()


def probe(server: dict, timeout: float=5.0) -> dict:
    try:
        with StdioClient(server, timeout) as c:
            tools=c.list_tools()
            return {'ok':True,'status':'ready','tools':tools,'count':len(tools)}
    except Exception as exc:
        return {'ok':False,'status':'offline','error':str(exc),'tools':[],'count':0}


def call(server: dict, tool: str, arguments: dict|None=None, timeout: float=20.0) -> Any:
    with StdioClient(server, timeout) as c:
        return c.call_tool(tool, arguments or {})


def self_test() -> None:
    assert _expand('@python') == sys.executable
    assert '{root}' not in _expand('{root}/x')
    print('PASS: MCP stdio transport')


if __name__=='__main__': self_test()
