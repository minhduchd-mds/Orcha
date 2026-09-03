# Orcha Changelog

> Product name from v7.4 onward: **Orcha**. Older tags/releases may still contain the historical **Orcha** name; those artifacts are not rewritten.

## v7.7.0 — UI Contract + Outline Icon System

- Lock the product visual baseline to the established warm-dark Orcha-era style already encoded in `studio/styles.css`; Orcha keeps that palette, density, radius and workspace language instead of inventing a new theme.
- Make Anthropic Claude Code `frontend-design` a **quality reference only**: hierarchy, typography discipline, structure, copy, restraint, responsive behavior, focus and self-critique may improve the product but may not override the Orcha visual baseline.
- Add `docs/ORCHA-UI-CONTRACT.md` with mandatory source priority, visual tokens, interaction rules, brand rules and merge gates.
- Upgrade `orcha-frontend-design` to v1.1 with mandatory Orcha-baseline-first rules and explicit Claude-subordinate behavior.
- Change product-facing static chat/UI source from the retired Orcha name to **Orcha**: title, brand, welcome text, Inspector label and permission dialog.
- Add runtime brand normalization so dynamically inserted assistant/UI text also surfaces the Orcha name; historical/compatibility identifiers remain allowed only outside product-facing UI.
- Standardize product icons as outline SVG: 24×24 viewBox, `fill=none`, `stroke=currentColor`, 1.8 stroke, round caps/joins.
- Replace legacy navigation/workflow/modal glyph controls with declarative outline-icon markers and a shared runtime icon registry.
- Make UI Foundation inherit the canonical `styles.css` token values rather than maintaining a second, drifting palette.
- Extend `scripts/verify.py` and Windows/macOS CI so builds fail when retired product copy returns to `studio/index.html`, when the outline-icon contract disappears, or when UI Foundation stops inheriting canonical tokens.
- Add v7.7 desktop runtime/launcher/package health contract with `ui_contract`, `outline_icons`, and `claude_can_override_visual_baseline=false`.

## v7.6.0 — Production Hardening & Reliability

- Selectively merge the verified hardening workspace onto v7.5 without overwriting UI Foundation, Data Hub modal, Reference Lab or `orcha-frontend-design`.
- Add loopback-only API security with Host/Origin/Fetch-Site guards, JSON/body limits and `X-Orcha-Token` session authentication for POST requests.
- Add same-origin authenticated Studio transport and token-aware Windows/macOS desktop control.
- Harden Permission Engine: global policy is the ceiling; once grants bind to the exact session/run/action/arguments and are consumed atomically.
- Move Agent Runtime to action → observation → re-plan; failed/denied/cancelled tools cannot be reported as completed work.
- Add transactional project/storage semantics, runtime DATA lease, DAG validation, idempotent plan materialization and interrupted-state recovery without replaying side effects.
- Harden Supervisor/Harness execution, request reservation/idempotency, evidence gates and explicit write execution while keeping Permission Engine authoritative.
- Add persistent MCP stdio pooling, `isError` preservation, schema validation, stderr bounds and serialized writes; side effects are never auto-retried.
- Partition Context/RAG by project and bound Working Context/inference budgets; Virtual Context remains searchable storage rather than native attention.
- Harden model routing, Data Hub SSRF/credential/private-network behavior, Mobile Runtime edge cases, Computer launch allowlist and AutoCAD rollback identity.
- Add SHA-256 backup/restore validation, keyboard/focus/permission-dialog accessibility guards and responsive navigation.
- Make `scripts/verify.py` the shared Windows/macOS verification gate; integrated v7.6 runs 26 module self-tests plus the hardening regression suite before packaging.
- Restore the generic build/release workflow after the v7.5 one-off release workflow was accidentally merged into `main`.

## v7.5.0 — UI Foundation + Reference Lab

- Add Inspector close/reopen control with persisted visibility state and responsive drawer behavior.
- Convert dense composer actions to icon-first controls with tooltip/`aria-label`, including Skill, Agent, Parallel Agent and Agent Team.
- Remove browser-native `prompt()` from Data Hub source creation; replace with a structured modal, validation, cancel/save states and preset cards.
- Add Data Hub reference presets for AI Templates Plugins, Sindre Sorhus Awesome and Anthropic Claude Code Frontend Design.
- Add **Extensions / Reference Lab** with searchable plugin/pattern catalog. It is discovery-only and never auto-installs or executes external code.
- Index the current top-level plugin/marketplace names surfaced by AI Templates and an Awesome discovery topic map.
- Add independently authored `orcha-frontend-design` skill: deliberate visual identity, icon toolbar rules, product dialogs, accessibility, reduced motion and self-critique.
- Add UI polish layer: stronger focus states, calmer spacing, micro-transitions, reduced-motion support and narrow-screen Inspector behavior.
- Normalize legacy model product-name output to Orcha at the response surface so old local Modelfiles do not leak the retired name into chat.
- Windows/macOS launcher and package contract move to v7.5 with CI gates for modal flow, icon accessibility and reference-catalog safety.

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
- Add `ORCHA_DATA_DIR`; `ORCHA_DATA_DIR` remains migration fallback only.
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
- Historical data path used `ORCHA_DATA_DIR`; Orcha v7.4 prefers `ORCHA_DATA_DIR` while preserving migration compatibility.
