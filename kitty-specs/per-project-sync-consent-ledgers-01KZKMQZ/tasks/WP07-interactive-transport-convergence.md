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
- src/specify_cli/delivery/dispatcher.py
- src/specify_cli/delivery/consent_gate.py
- src/specify_cli/sync/client.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/events.py
- src/specify_cli/sync/runtime_event_emitter.py
- src/specify_cli/sync/body_transport.py
- src/specify_cli/sync/body_upload.py
- src/specify_cli/sync/dossier_pipeline.py
- src/specify_cli/dossier/emitter_adapter.py
- src/specify_cli/sync/local_commit.py
- src/specify_cli/sync/history_import/upload.py
- src/specify_cli/saas_client/client.py
- src/specify_cli/tracker/saas_client.py
- tests/delivery/test_cross_project_refusal_state_3030.py
- tests/delivery/test_dispatcher.py
- tests/delivery/test_liveness_predicate_before_limit_3030.py
- tests/sync/test_body_drain_consent_3030.py
- tests/sync/test_interactive_transport_convergence.py
- tests/sync/test_saas_refusal_parking.py
- tests/sync/test_sender_context_convergence.py
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

- 2026-08-10T02:25:00Z – codex – Sequentially assigned the existing body-drain consent, dispatcher liveness-before-limit, and cross-project refusal-state suites to WP07 because making those callers green requires the WP06 attempt/lease and WP07 correlated final-gate/parking wiring; WP04 owns only the repository boundary and must not restore a shared-store caller compatibility path.
- 2026-08-10T18:47:24Z – codex – Corrected pre-allocation ownership metadata: T032's live event relay (`src/specify_cli/sync/events.py`) and the three already-assigned regression suites are now explicit WP07-owned files, and lane-e now retains those paths plus the already-owned dispatcher suite. This is a governance-only correction with no production scope expansion. The normal finalizer was not rerun because its live-mission topology rewrite is tracked in #3311; existing lane identities, status history, and planning provenance are preserved. Documentary `later_owner` drift in the architecture census remains for an explicitly owned later correction.
