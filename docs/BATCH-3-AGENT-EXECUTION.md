# Batch 3 — Agent Execution & Observable Local Automation

KimiK3-Lite v6.2 adds a permission-gated execution loop on top of the v6.1 Skill + MCP foundation.

## Runtime flow

`User → Skill Router → Planner → Tool Proposal → Permission Gate → Execute → Observe → Verify → Answer`

The model can only choose registered tools. It cannot create executable commands. Tool execution is capped per run. Read-only tools may run automatically; yellow actions pause for confirmation; denied permissions never execute.

## Action Timeline

Each local action is appended to `data/action_timeline.jsonl`. Sensitive typed text is redacted and stored only as character count. AutoCAD create/dimension results can expose an explicit rollback descriptor using `autocad.entity.delete`.

## Computer Control

Windows Computer MCP now returns stable `element_id` values (`hwnd:<id>`) and supports `computer.ui.find`. Click/type prefer an element id; coordinates remain a fallback.

## AutoCAD

Structured tools support layer creation, line, lightweight polyline, text, circle, aligned dimension, entity delete by handle and document save. AutoCAD execution is Windows-only and requires an active AutoCAD COM session.

## Skill Builder

Studio can create safe `SKILL.md` files. Skill IDs are validated and permissions are limited to `auto`, `confirm`, or `deny`. Skill Builder does not write executable code.

## KII Benchmark

The local benchmark measures runtime readiness: retrieval, skill coverage, tooling, safety policy, memory and context. It is not an IQ score or an academic model benchmark.
