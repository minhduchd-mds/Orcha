# KimiK3-Lite v7.1 — Durable Agent Team

> Architecture adaptation, not a source port. KimiK3-Lite independently implements selected ideas from DeepSeek Harness Agent Team/Subagent documentation in Python for a low-RAM local desktop runtime.

## Upstream concepts studied

The v7.1 design focuses on these DeepSeek Harness patterns:

- Durable Team identity and roster separate from transient worker status.
- Durable mailbox where queueing and delivery acknowledgement are distinct facts.
- Shared task DAG with revision/CAS mutation instead of blind last-write-wins updates.
- Persistent child/subagent identity that survives process restarts even when the live worker does not.
- Agent inbox/control as a bounded coordination surface rather than hidden cross-thread state.
- Fail-loud capability negotiation: unsupported requested features are rejected instead of silently ignored.
- Child/member-first teardown before the Team root is considered settled.
- Replay from durable events to rebuild UI/read models.

## KimiK3-Lite implementation

### `app/team_runtime.py`

Stores one append-only JSONL stream per Team under the local application data directory. Event families include:

- `team/created`, `team/interrupted`, `team/settled`
- `member/upsert`
- `task/upsert`
- `message/queued`, `message/delivered`
- `control/steer`, `control/cancel`

`fold(team_id)` rebuilds the Team state from those events. The UI can therefore read a Team after restart without depending on the old process's in-memory `RUNS` map.

### Member identity

Each DAG node receives a stable member id in the form `<team-id>:<node-id>`. Runtime phase and worker thread are not the identity. On restart the member remains visible in the durable Team view even though its old thread is gone.

### Task CAS

Every task snapshot carries a monotonically increasing `revision`. `update_task()` requires `expected_revision`; a stale mutation raises a revision conflict. Dependencies are validated and cycles are refused.

This is intentionally stronger than the previous v6.7 in-memory DAG, which had no durable concurrency token.

### Durable mailbox

A Team message is first written as `message/queued`; delivery is a separate `message/delivered` event. The folded mailbox marks delivery by message id. Sender and target must belong to the same Team (or the root session), preventing arbitrary cross-Team addressing.

### Steer and cancel

v7.1 supports cooperative control at model-step boundaries:

- `steer` queues an instruction that is consumed before the target's next model request.
- `cancel` sets a live cancellation flag and records the durable control event.

The implementation does **not** claim to hard-kill an Ollama HTTP request already executing. Cancellation is checked before and immediately after a model step; therefore UI labels it `cooperative-step-boundary`.

### Fail-loud capabilities

Each Team node declares `requires`. `team_runtime.require_capabilities()` raises `UNSUPPORTED_CAPABILITY` when a required capability is absent. v7.1 does not silently remove behavior from a node.

### Restart recovery

Open durable Teams are marked `interrupted` on v7.1 startup. They are visible for inspection but are not automatically resumed. This avoids replaying an ambiguous side effect after a crash/restart.

### Async Team API

`POST /api/agents/team/start` returns immediately with `run_id` and `team_id`, allowing Studio to poll `/api/agents/team/runs/<id>` while the worker executes. This enables live Task/Inbox views and cooperative steer/cancel controls.

Additional APIs:

- `GET /api/agents/team/state?team=<id>`
- `GET /api/agents/team/tasks?team=<id>`
- `GET /api/agents/team/mailbox?team=<id>`
- `GET /api/agents/team/events?team=<id>`
- `POST /api/agents/team/control`
- `POST /api/agents/team/task/update`
- `POST /api/agents/team/recover`

## UI contract

Agent Team Inspector now has three views:

1. **Graph** — DAG node state plus steer/cancel controls for running nodes.
2. **Tasks** — task id, status, revision and blockers.
3. **Inbox** — recent queued/delivered messages with sender/target attribution.

The UI polls the async run instead of blocking the chat request until the entire Team is finished.

## Safety boundaries

- Team workers remain read-only analysis workers in this version.
- Existing write tools still run through the existing Permission Engine / serial write lane.
- No arbitrary plugin code loading is introduced.
- No model-generated shell is introduced.
- Interrupted teams are not auto-resumed.
- Cancel is cooperative and is not presented as a hard process kill.

## Deliberate differences from DeepSeek Harness

KimiK3-Lite does not port Cordis, DeepSeek's TypeScript service graph, their exact Team event schema, or their continuation manager. v7.1 keeps the existing Python/Ollama runtime and implements only the stable contracts useful to the product.

A later v7.x can add a single canonical Team/session event log across Harness + Agent Team, durable cold continuation for read-only workers, and stronger mailbox delivery recovery once replay compatibility tests are mature.
