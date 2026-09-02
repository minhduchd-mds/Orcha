# Orcha Changelog

> Product name from v7.4 onward: **Orcha**. Older tags/releases may still contain the historical **KimiK3-Lite** name; those artifacts are not rewritten.

## v7.4.0 — Orcha Rebrand + Hybrid Data + Mobile Runtime Foundation

- Rebrand product-facing UI/docs/package naming to **Orcha — Autonomous Work Platform**.
- Positioning changes from local-only assistant to **local-first, hybrid-capable autonomous work platform**.
- Add `data_sync.py` Data Hub foundation: JSON API, RSS, Atom and text HTTP sources.
- Add background read-only scheduler, minimum 15-minute source interval, 5 MB fetch guard and local sync state/cache.
- Source auth headers reference environment variables; secret values are not stored in source config.
- Add Data Hub UI for source add/pause/sync/status.
- Add `mobile_runtime.py` model/runtime selector using OS, RAM, storage, battery, thermal, network, installed-model state and privacy mode.
- Add Mobile Runtime UI and API; selector can return `on_device`, `peer_or_remote` or `defer`.
- `privacy=strict` never silently routes data to a remote provider when local execution is unavailable.
- Add `ORCHA_DATA_DIR`; `KIMIK3_DATA_DIR` remains migration fallback only.
- macOS app becomes `Orcha.app`; release assets become `Orcha-vX.Y.Z-*`.

## v7.3.0 — Project Executor & Supervisor

- Persistent Supervisor state per Project.
- Dependency-aware execution of ready tasks.
- Background automation is read-only only.
- Write-intent tasks stop at Project Approval and still remain subject to Permission Engine.
- Safe retry cap for read-only execution.
- Verification gate before a task is marked done.
- Pause / resume / single-step / run-until-blocked controls.
- Supervisor dashboard with progress, ready queue, approvals and run history.

## v7.2.0 — Autonomous Project Planner

- Goal → milestone → task decomposition.
- Task dependency graph.
- Automatic task classification.
- Skill matching and model routing per task.
- Single / parallel / team strategy recommendation.
- Per-task RAM and Working Context budget metadata.
- Write-intent detection with mandatory approval flag.
- Planner Workspace UI and materialize-to-project flow.

## v7.1.0 — Project Agent Workspace

- Persistent Project store.
- Project goal/progress metadata.
- Durable task queue and dependencies.
- Approval Inbox for write-intent tasks.
- Checkpoint and resume without replaying side effects.
- Project Workspace UI integrated with Harness/Hermes.

## v7.0.0 — Event-Sourced Harness + Reliability

- Adapt selected architecture patterns from `deepseek-ai/deepseek-harness`; implementation is independently written.
- Add append-only session events, explicit turn/step lifecycle, request checkpoints and capability seams.
- `request_id` becomes the idempotency key instead of matching repeated user text.
- Running requests at restart close as `interrupted`, never silently auto-resume ambiguous side effects.
- Add failure taxonomy, bounded retry for direct model/vision transient failures, dedupe/Stall Guard and hard cap 6 tool proposals.
- Large tool results spill to local disk with bounded model-visible preview.
- Add host-owned verification recipes with `shell=False` and timeouts.
- Add Harness Inspector and preserve Team/Parallel/MCP regression gates.

## v6.9.0 — Hermes Foundation + Chat Reliability

- Add lightweight Hermes-inspired control plane, durable transcripts and request idempotency.
- Conversation-first router sends informational queries direct; skill/side-effect intents enter Agent Executor.
- Add local agent roster, peer-message bus, steer/cancel registry and protected-instruction path policy.
- Fix text-only routing when a composite vision profile is selected by using its Balanced companion.
- Launcher detects and replaces stale runtime occupying the Studio port.

## v6.8.0 — Final Intelligence & Hardening

- Add local outcome/lesson learning and performance score for `single / parallel / team` strategies.
- Add Agent Performance Inspector and user feedback.
- Keep fixed safety guard: no self-modifying executable code, no automatic permission escalation, no red-tool auto-run.
- Add security audit and local backup.

## v6.7.0 — Agent Team + Dependency Graph

- Add DAG-based Agent Team runtime.
- Research + Specialist → Critic + Verifier → Synthesis.
- Independent nodes may run in parallel under RAM Guard; downstream nodes wait for dependencies.
- Shared Team Memory and basic conflict resolution.
- Keep `parallel-read-serial-write` policy.

## v6.6.0 — Parallel Agent Orchestrator

- Add RAM-aware parallel agent runtime; 4 GB machines default to at most 2 concurrent workers.
- Coordinator decomposes work into Research, Specialist, Critic and Verifier roles.
- Read/reasoning can run concurrently; side effects remain serialized through Permission Gate.

## v6.0.0 — Virtual Context + Intelligence Inspector

- Introduce three-column Workspace/Inspector layout.
- Add Virtual Context, bounded Working Set and Native Context distinction.
- Add local Context Engine/RAG and operational KII heuristic.
- KII remains an operational score, not IQ or an academic benchmark.

## v5.x — Desktop Foundation

- Add Windows/macOS thin desktop launchers and packaging.
- Edge/Chrome App Mode, first-run model setup, local RAG indexing and workflow UI.
- Historical data path used `KIMIK3_DATA_DIR`; Orcha v7.4 prefers `ORCHA_DATA_DIR` while preserving migration compatibility.
