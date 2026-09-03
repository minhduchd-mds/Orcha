"""Lifecycle-owned append-only session persistence.

Independent Orcha implementation inspired by durable session-handle patterns.
A writer owns one SessionHandle lifecycle; readers use SessionStore.read().
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Iterable

import storage


class SessionHandle:
    def __init__(self, path: Path, mode: str = "a"):
        if mode not in {"a", "r"}:
            raise ValueError("mode must be 'a' or 'r'")
        self.path = Path(path)
        self.mode = mode
        self._closed = False
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("a", encoding="utf-8", newline="\n") if mode == "a" else None

    @property
    def closed(self) -> bool:
        return self._closed

    def read(self, limit: int = 1000) -> list[dict]:
        limit = max(1, min(int(limit or 1000), 10000))
        if not self.path.exists():
            return []
        rows: list[dict] = []
        with self.path.open("r", encoding="utf-8") as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        rows.append(row)
                except (ValueError, TypeError):
                    continue
        return rows[-limit:]

    def append(self, row: dict) -> dict:
        if self.mode != "a":
            raise PermissionError("read-only session handle")
        if self._closed or self._stream is None:
            raise ValueError("session handle is closed")
        if not isinstance(row, dict):
            raise TypeError("session row must be an object")
        payload = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._stream.write(payload + "\n")
        return row

    def append_many(self, rows: Iterable[dict]) -> int:
        count = 0
        for row in rows:
            self.append(row)
            count += 1
        return count

    def flush(self) -> None:
        if self.mode != "a" or self._closed or self._stream is None:
            return
        with self._lock:
            self._stream.flush()
            os.fsync(self._stream.fileno())

    def close(self) -> None:
        if self._closed:
            return
        if self._stream is not None:
            self.flush()
            self._stream.close()
        self._closed = True

    def __enter__(self) -> "SessionHandle":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class SessionStore:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or (storage.DATA / "harness" / "sessions-v2"))
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe(session_id: str) -> str:
        import hashlib
        import re
        raw = str(session_id or "default")
        clean = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-._")[:100] or "default"
        return clean if clean == raw else clean + "-" + hashlib.sha256(raw.encode()).hexdigest()[:12]

    def path(self, session_id: str) -> Path:
        return self.root / f"{self._safe(session_id)}.jsonl"

    def create(self, session_id: str) -> SessionHandle:
        path = self.path(session_id)
        if path.exists() and path.stat().st_size:
            raise FileExistsError(f"session already exists: {session_id}")
        return SessionHandle(path, "a")

    def open(self, session_id: str) -> SessionHandle:
        return SessionHandle(self.path(session_id), "a")

    def read(self, session_id: str, limit: int = 1000) -> list[dict]:
        return SessionHandle(self.path(session_id), "r").read(limit)

    def stat(self, session_id: str) -> dict:
        path = self.path(session_id)
        return {"session_id": str(session_id), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}

    def list(self) -> list[dict]:
        rows = []
        for path in self.root.glob("*.jsonl"):
            rows.append({"name": path.stem, "bytes": path.stat().st_size, "mtime": path.stat().st_mtime})
        return sorted(rows, key=lambda x: x["mtime"], reverse=True)


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        store = SessionStore(Path(td))
        with store.create("alpha") as handle:
            handle.append({"seq": 0, "type": "turn/start"})
            handle.flush()
            assert handle.read()[-1]["seq"] == 0
        assert handle.closed
        with store.open("alpha") as handle2:
            handle2.append({"seq": 1, "type": "turn/end"})
        assert [x["seq"] for x in store.read("alpha")] == [0, 1]
    print("PASS: session handle lifecycle/flush/read")


if __name__ == "__main__":
    self_test()
