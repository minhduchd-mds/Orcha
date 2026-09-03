"""Safe streamed tool-call delta assembly.

Identity fields are replace-on-non-empty; arguments are append-only fragments.
This prevents continuation deltas with empty/null id or name from erasing a
previously established tool identity.
"""
from __future__ import annotations

from dataclasses import dataclass


def _non_empty(value):
    return value if isinstance(value, str) and value.strip() else None


@dataclass
class ToolCallState:
    id: str | None = None
    name: str | None = None
    arguments: str = ""

    def apply(self, delta: dict | None) -> "ToolCallState":
        delta = delta or {}
        incoming_id = _non_empty(delta.get("id"))
        if incoming_id is not None:
            self.id = incoming_id
        fn = delta.get("function") if isinstance(delta.get("function"), dict) else {}
        incoming_name = _non_empty(fn.get("name"))
        if incoming_name is not None:
            self.name = incoming_name
        fragment = fn.get("arguments")
        if isinstance(fragment, str):
            self.arguments += fragment
        return self

    def validate(self) -> None:
        if not _non_empty(self.id):
            raise ValueError("tool call id missing")
        if not _non_empty(self.name):
            raise ValueError("tool call name missing")

    def as_dict(self) -> dict:
        self.validate()
        return {"id": self.id, "function": {"name": self.name, "arguments": self.arguments}}


class ToolCallDeltaMerger:
    def __init__(self):
        self._calls: dict[int, ToolCallState] = {}

    def apply(self, delta: dict) -> ToolCallState:
        index = int(delta.get("index", 0))
        state = self._calls.setdefault(index, ToolCallState())
        return state.apply(delta)

    def finalized(self) -> list[dict]:
        return [self._calls[i].as_dict() for i in sorted(self._calls)]


def self_test():
    merger = ToolCallDeltaMerger()
    merger.apply({"index": 0, "id": "call-a", "function": {"name": "project.search", "arguments": "{\"q\":"}})
    merger.apply({"index": 1, "id": "call-b", "function": {"name": "context.stats", "arguments": "{"}})
    merger.apply({"index": 0, "id": "", "function": {"name": None, "arguments": "\"x\"}"}})
    merger.apply({"index": 1, "id": None, "function": {"name": "", "arguments": "}"}})
    calls = merger.finalized()
    assert calls[0]["id"] == "call-a" and calls[0]["function"]["name"] == "project.search"
    assert calls[1]["id"] == "call-b" and calls[1]["function"]["name"] == "context.stats"
    assert calls[0]["function"]["arguments"] == "{\"q\":\"x\"}"
    print("PASS: streamed tool identity guard")


if __name__ == "__main__":
    self_test()
