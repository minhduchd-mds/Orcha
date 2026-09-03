"""Durable FIFO mailbox for agent-team steering and cold resume."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import storage


class DurableMailbox:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or (storage.DATA / "agent-mailbox"))
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe(value: str) -> str:
        import hashlib
        import re
        raw = str(value or "default")
        clean = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-._")[:100] or "default"
        return clean if clean == raw else clean + "-" + hashlib.sha256(raw.encode()).hexdigest()[:12]

    def _path(self, team_id: str, target: str) -> Path:
        return self.root / self._safe(team_id) / f"{self._safe(target)}.jsonl"

    @storage.serialized
    def enqueue(self, team_id: str, target: str, payload: dict, message_id: str | None = None) -> dict:
        if not isinstance(payload, dict):
            raise TypeError("mailbox payload must be an object")
        path = self._path(team_id, target)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = self._rows(team_id, target)
        mid = str(message_id or ("msg-" + uuid.uuid4().hex[:16]))
        existing = next((x for x in rows if x.get("id") == mid), None)
        if existing:
            return existing
        seq = max([int(x.get("seq", -1)) for x in rows] or [-1]) + 1
        row = {"id": mid, "seq": seq, "queued_at": time.time(), "payload": payload, "delivered_at": None}
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return row

    def _rows(self, team_id: str, target: str) -> list[dict]:
        path = self._path(team_id, target)
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict) and row.get("id") is not None:
                    rows.append(row)
            except ValueError:
                continue
        # latest record for a message id wins, but ordering always follows original seq
        by_id = {}
        for row in rows:
            prior = by_id.get(row.get("id"))
            if prior is None or float(row.get("updated_at") or row.get("queued_at") or 0) >= float(prior.get("updated_at") or prior.get("queued_at") or 0):
                by_id[row.get("id")] = row
        return sorted(by_id.values(), key=lambda x: (int(x.get("seq", 0)), float(x.get("queued_at", 0))))

    def pending(self, team_id: str, target: str, limit: int = 1000) -> list[dict]:
        rows = [x for x in self._rows(team_id, target) if not x.get("delivered_at")]
        return rows[:max(1, min(int(limit or 1000), 10000))]

    @storage.serialized
    def ack(self, team_id: str, target: str, message_id: str) -> dict:
        rows = self._rows(team_id, target)
        row = next((x for x in rows if x.get("id") == message_id), None)
        if not row:
            raise KeyError("unknown mailbox message")
        if row.get("delivered_at"):
            return row
        updated = {**row, "delivered_at": time.time(), "updated_at": time.time()}
        path = self._path(team_id, target)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(updated, ensure_ascii=False, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return updated

    def replay(self, team_id: str, target: str) -> list[dict]:
        """Return all undelivered messages in durable FIFO order for cold resume."""
        return self.pending(team_id, target, limit=10000)


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        box = DurableMailbox(Path(td))
        a = box.enqueue("t", "critic", {"text": "first"}, "m1")
        b = box.enqueue("t", "critic", {"text": "second"}, "m2")
        box.enqueue("t", "critic", {"text": "duplicate ignored"}, "m1")
        assert [x["id"] for x in box.replay("t", "critic")] == ["m1", "m2"]
        box.ack("t", "critic", a["id"])
        assert [x["id"] for x in box.replay("t", "critic")] == ["m2"]
        c = box.enqueue("t", "critic", {"text": "third"}, "m3")
        assert c["seq"] == 2
        assert box.enqueue("t", "critic", {"text": "do not reuse delivered id"}, "m1")["seq"] == 0
        assert b["seq"] == 1
    print("PASS: durable mailbox fifo/dedupe/ack/monotonic-seq")


if __name__ == "__main__":
    self_test()
