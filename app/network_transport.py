#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config' / 'network.json'


def _read_config() -> dict[str, Any]:
    try:
        return json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else {}
    except Exception:
        return {}


@dataclass(frozen=True)
class NetworkConfig:
    proxy: str | None = None
    no_proxy: tuple[str, ...] = ()
    timeout: float = 30.0
    tls_verify: bool = True

    @classmethod
    def load(cls) -> 'NetworkConfig':
        raw = _read_config().get('network', _read_config())
        proxy = str(raw.get('proxy') or os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY') or '').strip() or None
        no_proxy_raw = raw.get('no_proxy') or os.environ.get('NO_PROXY') or os.environ.get('no_proxy') or ''
        if isinstance(no_proxy_raw, str):
            no_proxy = tuple(x.strip().lower() for x in no_proxy_raw.split(',') if x.strip())
        else:
            no_proxy = tuple(str(x).strip().lower() for x in no_proxy_raw if str(x).strip())
        timeout = max(0.1, float(raw.get('timeout') or os.environ.get('ORCHA_NETWORK_TIMEOUT') or 30.0))
        tls_verify = str(raw.get('tls_verify', os.environ.get('ORCHA_TLS_VERIFY', 'true'))).lower() not in {'0', 'false', 'no', 'off'}
        return cls(proxy=proxy, no_proxy=no_proxy, timeout=timeout, tls_verify=tls_verify)


def _host_matches_no_proxy(host: str, patterns: tuple[str, ...]) -> bool:
    host = host.split(':', 1)[0].strip('[]').lower()
    for pattern in patterns:
        pattern = pattern.lstrip('.')
        if pattern == '*' or host == pattern or host.endswith('.' + pattern):
            return True
    return False


def _opener(url: str, cfg: NetworkConfig):
    host = urllib.parse.urlsplit(url).hostname or ''
    handlers: list[Any] = []
    if cfg.proxy and not _host_matches_no_proxy(host, cfg.no_proxy):
        handlers.append(urllib.request.ProxyHandler({'http': cfg.proxy, 'https': cfg.proxy}))
    else:
        handlers.append(urllib.request.ProxyHandler({}))
    context = ssl.create_default_context() if cfg.tls_verify else ssl._create_unverified_context()
    handlers.append(urllib.request.HTTPSHandler(context=context))
    return urllib.request.build_opener(*handlers)


def request_json(method: str, url: str, payload: Any = None, *, headers: dict[str, str] | None = None, timeout: float | None = None) -> Any:
    cfg = NetworkConfig.load()
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    merged = {'Accept': 'application/json', **(headers or {})}
    if data is not None:
        merged.setdefault('Content-Type', 'application/json')
    req = urllib.request.Request(url, data=data, headers=merged, method=method.upper())
    try:
        with _opener(url, cfg).open(req, timeout=float(timeout or cfg.timeout)) as response:
            raw = response.read()
            return json.loads(raw.decode('utf-8')) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {exc.code} for {url}: {detail[:500]}') from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f'Network request failed for {url}: {exc.reason}') from exc


def get_json(url: str, *, timeout: float | None = None, headers: dict[str, str] | None = None) -> Any:
    return request_json('GET', url, headers=headers, timeout=timeout)


def post_json(url: str, payload: Any, *, timeout: float | None = None, headers: dict[str, str] | None = None) -> Any:
    return request_json('POST', url, payload, headers=headers, timeout=timeout)


def self_test():
    cfg = NetworkConfig(proxy='http://proxy.local:8080', no_proxy=('localhost', '127.0.0.1'))
    assert _host_matches_no_proxy('localhost', cfg.no_proxy)
    assert _host_matches_no_proxy('api.localhost', cfg.no_proxy)
    assert not _host_matches_no_proxy('example.com', cfg.no_proxy)
    print('PASS: unified network transport config + no_proxy matching')


if __name__ == '__main__':
    self_test()
