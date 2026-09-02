# Orcha v7 — DeepSeek Harness Architecture Study

> Status: architecture adaptation, not a fork. Orcha does **not** copy DeepSeek Harness source code. It adopts selected architecture contracts in a small Python/vanilla-JS form suitable for a low-RAM, local-first runtime.

## Sources reviewed

Primary upstream: `deepseek-ai/deepseek-harness` (`master`, developer preview, MIT).

The v7 design was derived from the upstream README and architecture documentation, especially:

- `README.md` — everything-is-a-plugin / Cordis composition and developer-preview warning.
- `SAFETY.md` — sandbox/approval are risk reduction, not a security boundary.
- `docs/architecture.md` — profiles/bundles, capability seams, durable session events, turn/step flow and the invariant **model-visible means logged**.
- `docs/agent-lifecycle.md` — explicit turn/start → step/start → request → tool calls/results → step/end → turn/end, cancellation and request-error recovery.
- `docs/tool-execution-pipeline.md` and `docs/subsystems/tools.md` — pre-execute policy, monotonic guards, approval, execution wrappers, post-execute normalization, immutable final result and explicit concurrency metadata.
- `docs/subsystems/session.md` — append-only typed session log as the source of truth.
- `docs/subsystems/persistence.md` — flush/checkpoint ownership and crash recovery that closes an orphaned turn as `interrupted` instead of deleting history.
- `docs/subsystems/compaction.md` — bounded context, tool-result pruning and safe surface replacement.
- `docs/development.md` — focused local gates plus exhaustive CI, explicit release blockers and generated-contract checks.

DeepSeek Harness is rapidly changing; its README explicitly warns of compatibility-breaking changes. Orcha therefore implements stable concepts rather than importing its runtime or tying the product to Cordis/Node.

## Architecture decisions for v7

### 1. Durable event log beside live coordination

`app/harness_runtime.py` writes an append-only JSONL event stream per session. Durable facts use explicit event types such as `turn/start`, `step/start`, `user/message`, `request/header`, `request/error`, `assistant/message`, and `turn/end`.

The Hermes layer remains live orchestration/control metadata. The Harness log is the durable execution trace used for replay/debugging and crash accounting.

### 2. Explicit request identity

Retries are identified by `request_id`, not by matching user text. This fixes an earlier issue where a legitimate repeated sentence within a short time window could be suppressed as a duplicate.

Missing request ids are generated server-side. Supplied ids are validated. Completed responses are persisted in an idempotency cache keyed by canonical session id + request id.

### 3. Crash-safe checkpoints

Each request receives a persisted run checkpoint written via temporary-file + atomic replace. On startup, a checkpoint still marked `running` is closed as `interrupted`; it is never silently deleted and never automatically resumes a possible side effect.

This mirrors the important upstream distinction between durable history and live execution ownership.

### 4. Capability seams without arbitrary plugin execution

`CapabilityRegistry` provides replaceable in-process capability registrations and hooks with reversible disposal. Orcha deliberately does **not** auto-load arbitrary third-party Python code. External Skills/MCP remain subject to validation and Permission Engine policy.

This preserves the useful “everything is replaceable” direction without turning the desktop app into an untrusted code loader.

### 5. Guarded tool results

Large tool results are normalized and spilled to local disk. The model-facing observation receives bounded head/tail evidence plus a local spill reference instead of injecting an unbounded result into Working Context.

Tool argument/result boundaries remain JSON-oriented. Computer typing remains redacted by the Action Log.

### 6. No blind retry of side effects

Only direct model/vision requests may retry automatically, and only for transient failures. A complete Agent Executor run is never automatically retried because an earlier attempt may already have produced an approved side effect.

Failure classes: `transient`, `permission`, `validation`, `cancelled`, `runtime`, `interrupted`.

### 7. Stall and repetition guards

Tool plans are deduplicated by stable tool-name + canonical-arguments signature. Repeated identical execution is blocked rather than allowed to loop. Existing `MAX_ACTIONS=6` remains the hard per-run proposal bound.

### 8. Host-owned verification recipes

`app/verification_engine.py` executes only fixed argv recipes owned by the application, with `shell=False`, bounded timeouts and captured output. The model cannot provide an arbitrary shell command to the verifier.

`fast` verifies Python compilation plus core Harness/model/Hermes and JS syntax. `full` adds local self-tests. GitHub Actions remains the release authority for Windows/macOS packaging.

### 9. Harness Inspector

Orcha exposes a compact Harness Inspector showing durable-event, recovery, spill and stall-guard state, recent runs and a user-triggered `Verify fast` action. This is operational evidence, not an intelligence score.

### 10. Security authority remains unchanged

The Permission Engine remains authoritative:

- Green/read-only can auto-run.
- Yellow/write/input requires confirmation according to policy.
- Red/dangerous operations remain denied.
- No model-generated shell is introduced by the v7 Harness layer.
- Agent state is not automatically resumed across a restart when a side effect could be ambiguous.

## Hybrid extension in Orcha v7.4

Orcha is now **local-first, not local-only**. The Harness safety model also applies when adding hybrid capabilities:

- Data Hub background sync is a network **read-only** lane.
- External source credentials are referenced from environment variables, not persisted inline.
- Mobile Runtime may choose on-device, trusted desktop peer or private remote provider based on device/privacy policy.
- A hybrid fallback must not silently bypass project privacy or Permission Engine rules.

## Known boundaries

Orcha v7 is intentionally not a full DeepSeek Harness port. It does not implement Cordis, the upstream bundle/profile format, PTC, arbitrary plugin code, remote sandbox providers, or a full event-derived model-history rewrite. Orcha keeps its Python runtime, Ollama-compatible local models, Virtual Context/RAG, Skills, MCP, Hermes control plane and low-RAM design.

A future v7.x can progressively make the Harness session log the single canonical transcript, then retire duplicated history storage after migration tests prove replay equivalence.

## Verification contract

A v7 PR is mergeable only after:

1. Python compile passes for current and inherited servers.
2. Harness request-id, retry taxonomy, stall guard and capability registry self-tests pass.
3. Agent runtime dedupe/stall self-test passes.
4. UI JavaScript syntax checks pass.
5. Text-only UI/UX composite routing still resolves to its companion model.
6. Malformed API values fail safe to defaults.
7. Existing Team/Parallel/MCP regression gates remain green.
8. Windows launcher points to the current Orcha server runtime.
9. macOS launcher/DMG points to the current Orcha server runtime.
10. Main build emits Orcha Windows Portable + macOS DMG.

## Attribution and license

Architecture study source: DeepSeek AI, **DeepSeek Harness**, MIT License. This repository's implementation is independently written. If future work ports actual upstream source instead of ideas/contracts, copied portions must carry the upstream copyright/license notice and be tracked explicitly in third-party notices.
