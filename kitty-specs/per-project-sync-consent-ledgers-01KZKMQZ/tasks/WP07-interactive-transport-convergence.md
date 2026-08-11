---
work_package_id: WP07
title: Interactive transport convergence
dependencies:
- WP06
requirement_refs:
- FR-005
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-016
- FR-017
- FR-018
- FR-025
- FR-027
- FR-031
- NFR-003
- NFR-004
- NFR-007
- C-002
- C-003
- C-005
- C-007
- C-010
planning_base_branch: feat/per-project-sync-consent
merge_target_branch: feat/per-project-sync-consent
branch_strategy: Planning artifacts for this mission were generated on feat/per-project-sync-consent. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/per-project-sync-consent unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
history:
- at: '2026-08-09T17:05:36Z'
  actor: planner
  action: Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/delivery/dispatcher.py
create_intent:
- tests/delivery/test_dispatcher.py
- tests/delivery/test_liveness_predicate_before_limit_3030.py
- tests/delivery/test_cross_project_refusal_state_3030.py
- tests/sync/test_body_drain_consent_3030.py
- tests/sync/test_interactive_transport_convergence.py
- tests/sync/test_saas_refusal_parking.py
- tests/sync/test_sender_context_convergence.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/delivery/dispatcher.py
- src/specify_cli/delivery/consent_gate.py
- src/specify_cli/delivery/ledger.py
- src/specify_cli/delivery/receivers.py
- src/specify_cli/delivery/targets.py
- src/specify_cli/sync/client.py
- src/specify_cli/sync/__init__.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/events.py
- src/specify_cli/sync/runtime_event_emitter.py
- src/specify_cli/sync/transport_attempts.py
- src/specify_cli/sync/body_transport.py
- src/specify_cli/sync/body_upload.py
- src/specify_cli/sync/dossier_pipeline.py
- src/specify_cli/dossier/emitter_adapter.py
- src/specify_cli/dossier/events.py
- src/specify_cli/sync/local_commit.py
- src/specify_cli/sync/history_import/pipeline.py
- src/specify_cli/sync/history_import/upload.py
- src/specify_cli/sync/history_disclosure.py
- src/specify_cli/sync/project_store.py
- src/specify_cli/core/upstream_contract.json
- kitty-specs/064-complete-mission-identity-cutover/contracts/upstream-3.0.0-shape.json
- src/specify_cli/saas_client/client.py
- src/specify_cli/tracker/saas_client.py
- tests/delivery/test_cross_project_refusal_state_3030.py
- tests/delivery/test_dispatcher.py
- tests/delivery/test_project_store_ledger.py
- tests/delivery/test_receivers.py
- tests/delivery/test_targets.py
- tests/delivery/test_liveness_predicate_before_limit_3030.py
- tests/cli/commands/test_sync_import_history.py
- tests/contract/test_body_sync.py
- tests/specify_cli/core/test_contract_gate.py
- tests/sync/conftest.py
- tests/sync/test_body_drain_consent_3030.py
- tests/sync/test_body_transport.py
- tests/sync/test_interactive_transport_convergence.py
- tests/sync/test_history_import_consent_3030.py
- tests/sync/test_history_import_pipeline.py
- tests/sync/test_history_import_upload.py
- tests/sync/test_history_disclosure.py
- tests/sync/test_project_sync_context.py
- tests/dossier/test_emitter_adapter.py
- tests/dossier/test_events.py
- tests/status/test_emit_fanout_after_adapter.py
- tests/sync/test_dossier_pipeline.py
- tests/sync/test_dossier_trigger.py
- tests/sync/test_saas_refusal_parking.py
- tests/sync/test_sender_context_convergence.py
- tests/sync/test_transport_attempt_recovery.py
role: implementer
tags: []
tracker_refs:
- Priivacy-ai/spec-kitty#3262
- Priivacy-ai/spec-kitty#3030
- Priivacy-ai/spec-kitty#3108
- Priivacy-ai/spec-kitty#3135
---

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

Read WP01's sender census, the pinned WP05 contract attestation, and WP06's merged
attempt/lease API. Do not reimplement those authorities in an adapter.

## Objective

Make every interactive hosted sender consume one immutable ProjectSyncContext,
one durable DeliveryAttempt, and the WP06 lease/final gate. Each project-bearing
item carries its own UUID and target-scoped admission generation/audience.

## Sender inventory

Cover direct dispatcher HTTP, batch Event, WebSocket Event, runtime event relay,
body upload/drain, dossier pipeline/adapter, final/exit sync, reconnect flush,
LocalCommit, history/preflight, generic SaaS client, and tracker-hosted client.
Tracker Channel 2 remains a narrowing control and cannot grant.

## Subtask T031 — Red-first interactive convergence ATDD

Commit a public-entry-point sender test that fails on the planning base and
proves final-gate ordering, per-write correlation in mixed batches/WebSockets,
and an admitted positive control. Keep it separate from WP01's green harness.

## Subtask T032 — Dispatcher, events, WebSocket, and LocalCommit

Thread context/attempt/lease through dispatcher HTTP, Event batch, WebSocket
Event, relay, reconnect/final flush, and LocalCommit. Preserve Authorization
header WebSocket auth. Remove cwd, active target, login, repo slug, and request
defaults as identity sources. A mixed request never uses request-wide proof.

The dispatcher live path records exactly one canonical WP06 attempt/result per
event. Adapt the delivery ledger as a read/status projection over those
dispatcher attempts; do not write a second legacy-shaped attempt, ignore rows
whose metadata shape differs, or parse an undocumented string identity. Retain
legacy repository compatibility only for callers that have not entered the
canonical transport path.

Preserve one real receiver batch call after all per-item attempts are durably
prepared and final-gated under the project lease. The transport-native identity
must be serialized on the wire and equal the result correlation key; hash the
exact disclosed representation. Extend WP06 only through a typed public
attempt/result projection, typed existing-attempt recovery, and supported
same-attempt prepared resume. Do not duplicate its private JSON parser, match
exception text, or collapse known pending/retryable rejection into response
uncertainty.

## Subtask T033 — Body, dossier, and history paths

Converge body upload/drain, dossier pipeline/adapter, and history/preflight on the
same protocol. Keep sealed history unavailable to ordinary selection; only
WP03's exact confirmed capability may disclose it. Local capture remains allowed
while egress is denied.

## Subtask T034 — Generic SaaS and tracker-hosted adapters

Converge both clients without adding an independent store or grant seam. Preserve
#3030's consent-bearing selection, SQL identity filter, and terminal parking; add
the lease final check. Keep #3108/PR #3135 separate and narrowing-only.

## Subtask T035 — Correlation, refusal, and recovery proof

For every interactive family, assert exact project UUID/audience/generation and
native correlation. `project_not_admitted` is terminal for only the correlated
item and is never transiently retried. Mutants removing the final gate,
cross-pairing context, or minting a fresh recovery identity must fail.

## Branch Strategy

Run `spec-kitty agent action implement WP07 --agent <name>` after WP06 approval.
Use the computed lane and governed merge only. Do not mutate hosted state or
publish.

## Test strategy

Use local fake HTTP/WebSocket endpoints and exact sanitized byte assertions. Run
the three owned tests plus focused dispatcher, WebSocket, body, LocalCommit,
history, tracker-consent, and #3030 tests; then ruff and strict mypy.
Sequentially migrate `tests/delivery/test_dispatcher.py` from its retired
`set_project_consent(..., True)` fixture to the WP03 project-owned explicit
opt-in authority while preserving every dispatcher behavior assertion. This
compatibility migration belongs to WP07; earlier WPs must not edit the suite.
Sequentially migrate `tests/sync/test_body_drain_consent_3030.py` while wiring
body drain through the WP06 attempt/lease and WP07 final gate; WP04 must not
preserve or test a live shared-store caller path to keep this suite green.
The existing dispatcher liveness-before-limit and cross-project refusal-state
#3030 suites are also sequentially assigned here: their load-bearing assertions
depend on WP07's dispatcher, correlated refusal, parking, and final-gate wiring,
not on a WP04 repository compatibility shim.

## Definition of Done

- Every interactive census row uses context, attempt, lease, and final gate.
- Mixed batch/WebSocket proof is per item, never request-wide.
- Typed refusal parks only the correlated write.
- Native identities survive recovery and no authority is inferred from ambient
  process or tracker state.

## Risks and reviewer guidance

Review every census row rather than a representative sample. Reject adapter-local
consent, request-wide generations, query-token WebSocket auth, generic retry of
typed refusal, or a tracker permission used as a hosted-sync grant.

## Activity Log

- 2026-08-11T14:05:00Z – codex – Recovered the independently approved T033 product slice onto authoritative aggregate `a22b22640b80bc76baf9552d541c1a92626ba75a` in an isolated integration worktree. The transfer applied the three T033 product checkpoints without committing, then applied the reviewed dirty correction patch; aggregate dispatcher/attempt APIs and mission metadata were retained. Verified that `upload.py` contains one receiver-target assertion in each distinct public upload entry point and no consecutive duplicate assertion. Formally recorded the already-granted same-UoW context factory and focused test (`project_store.py` / `test_project_sync_context.py`) in `owned_files`. Removed the unowned `test_events.py` delta entirely and moved its sole load-bearing raw-WebSocket retirement spy, assertion-for-assertion, into the already-owned sender convergence suite; the six legacy Event fixture nodes remain untouched and outside this slice. Ruff formatting remains intentionally green across every changed Python file; the large `sync.py` normalization is separately labeled by temporary preserved patches `/private/tmp/t033-cli-formatter-only.patch` (SHA-1 content digest `87f01aa2dab6d591dea60e81bf074ccb62d75dfb`, 1,499 lines) and `/private/tmp/t033-cli-semantic-on-formatted-base.patch` (SHA-1 content digest `c2c8d268ed58037217ea05990ec7c02122b3d457`, 215 lines), so reviewers can distinguish mechanical formatter movement from public confirmation-flow semantics without implying the temporary patches are durable Git objects. No lifecycle state, aggregate branch, or remote changed.

- 2026-08-11T12:10:00Z – codex – Recorded the narrow T033 contract-provenance amendment for the vendored `body_sync` shape and its original planning mirror/gate test: the already pinned SaaS WP04 commit/digest now makes `admission_generation` and `binding_audience` required rather than optional metadata. This does not reopen SaaS ownership or alter the attested canonical contract; it makes the Core compatibility gate enforce the proof already carried by the exact body wire bytes. The six remaining T032 Event fixture failures are not assigned here because their test files are absent from WP07 ownership; the ten background integration nodes remain WP08-owned. No lifecycle state changed.

- 2026-08-11T08:15:41Z – codex – Recorded the narrow sequential T033 remediation ownership for the real `sync import-history --apply` ATDD, the exact admission-proof-bearing body request/result compatibility suites, and the shared `temp_queue` fixture used by the complete `TestRouteEvent`/`TestOfflineQueue` boundary. These tests were previously unassigned; WP07 may migrate them only to the already-owned project-store/context/target/capability and body transport seams, without restoring path-selected live queues or changing WP10's later migration command scope. No lifecycle state changed.
- 2026-08-11T08:55:39Z – codex – Recorded the arbiter-granted WP03→WP07 sequential seam for a public filtered sealed-history preview and its focused test. T033 may stage only the exact synthesized import envelopes into a dedicated sealed epoch, leaving the current eligible epoch open, creating no outbox task or egress, and may confirm only that ordered epoch cohort; the existing all-history preview remains unchanged and unrelated sealed rows stay excluded. No lifecycle state changed.

- 2026-08-11T01:40:00Z – codex – Corrected the T032/T033 live interactive census: `EventEmitter._route_event()` still contained a SyncRuntime-injected raw `ws_client.send_event()` path with no project context, durable attempt, lease, exact admission audience, or acknowledgement. WP07 retires that opportunistic branch fail-closed while preserving local durability; WP08 owns the admitted WebSocket positive path through `SyncRuntime.publish_event` and the WP06 gate. No lifecycle state changed.

- 2026-08-11T01:25:00Z – codex – Recorded the narrow sequential WP04→WP07 active-unit context-factory amendment. T033 may add one public `ProjectSyncStore` method that mints the normal coherent context from the caller's already-active, exact store unit; `create_context()` must delegate to the same implementation. The seam rejects foreign or inactive units before reads and exists only to prove dossier event/body capture shares one connection without reopening the aggregate. No lifecycle state changed.

- 2026-08-11T00:40:00Z – codex – Recorded the sequential T032→T033 dossier-capture seam: T033 owns the minimal `sync/emitter.py` explicit `ProjectSyncContext` local-capture path and focused emitter/fanout proofs after the reviewed T032 dispatcher protocol checkpoint. The seam forbids cwd/cached identity authority and direct remote routing; later egress remains exclusively dispatcher-gated. No lifecycle state changed.

- 2026-08-10T02:25:00Z – codex – Sequentially assigned the existing body-drain consent, dispatcher liveness-before-limit, and cross-project refusal-state suites to WP07 because making those callers green requires the WP06 attempt/lease and WP07 correlated final-gate/parking wiring; WP04 owns only the repository boundary and must not restore a shared-store caller compatibility path.
- 2026-08-10T18:47:24Z – codex – Corrected pre-allocation ownership metadata: T032's live event relay (`src/specify_cli/sync/events.py`) and the three already-assigned regression suites are now explicit WP07-owned files, and lane-e now retains those paths plus the already-owned dispatcher suite. This is a governance-only correction with no production scope expansion. The normal finalizer was not rerun because its live-mission topology rewrite is tracked in #3311; existing lane identities, status history, and planning provenance are preserved. Documentary `later_owner` drift in the architecture census remains for an explicitly owned later correction.
- 2026-08-10T19:20:00Z – codex – Added sequential ownership of `src/specify_cli/cli/commands/sync.py` after the live dispatcher redesign proved final/exit sync must release transaction-bound journal/ledger UoWs before WP06's separately committed attempt/start/result phases. WP10 retains later migration-command ownership and now depends on WP07; the two packages may not edit this shared file concurrently.
- 2026-08-10T21:05:00Z – codex – Landed the first WP07 convergence slice: `delivery.consent_gate.execute_project_transport_disclosure()` now performs a committed WP06 prepare/recover phase, a committed final start under a live per-project lease, network I/O outside SQLite, and a committed terminal/unknown result phase while validating the exact project/target/account/teamspace/config/admission/binding tuple. `sync.body_transport.push_content_with_transport_gate()` is the canonical WP07 API for WP08's `background.py` caller and owns the body upload native identity/result mapping. Focused evidence: `pytest tests/sync/test_sender_context_convergence.py tests/delivery/test_dispatcher.py::test_post_empty_selection_short_circuits -q` passed 6/6; Ruff check/format and strict mypy passed on the touched slice. Broader assigned-suite sweep still requires compatibility migration from retired project-store APIs (`EventJournal(path)`, `SqliteDeliveryLedger(":memory:")`, `SqliteDeliveryTargetRegistry(":memory:")`, `OfflineQueue(db_path=...)`, and `set_project_consent(...)`), with WP09-owned architecture/daemon suites left untouched per acceptance-matrix ruling.
- 2026-08-10T22:05:00Z – codex – Corrected sequential WP05→WP07 ownership for the target-ID seam and lane scope. T032 requires one public target-ID derivation shared by target registration and dispatcher attempts; WP07 therefore owns the minimal `delivery/targets.py` API/test amendment rather than duplicating its hash algorithm. `delivery/receivers.py`, already task-owned for exact disclosed-byte serialization, is also restored to lane-e's write scope. No WP05 admission semantics are reopened.
- 2026-08-10T22:35:00Z – codex – Corrected T033 live-caller ownership before implementation crossed the boundary. The explicit history capability/context/target contract must be threaded by `history_import/pipeline.py`, and dossier event builders must forward the explicit context to the owned emitter adapter; otherwise the new gate is dead or suppresses every valid event. Their focused compatibility tests are sequentially assigned to WP07. This is an ownership correction only; WP03 remains the capability authority and WP04 remains the project-store authority.
- 2026-08-10T22:42:00Z – codex – Sequentially transferred the dossier registration wrapper in `sync/__init__.py` from approved WP04 to WP07. The wrapper is the only live bridge from the explicit dossier adapter into canonical local capture; without accepting the store-minted context, every valid dossier event fails closed with a signature error. WP07 may change only that explicit forwarding seam and its fanout regression, preserving WP04's repository exports and local-capture authority.
