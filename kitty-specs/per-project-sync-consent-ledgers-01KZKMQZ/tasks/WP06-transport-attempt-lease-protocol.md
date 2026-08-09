---
work_package_id: WP06
title: Durable transport-attempt and lease protocol
dependencies:
- WP04
- WP05
requirement_refs:
- FR-005
- FR-007
- FR-008
- FR-009
- FR-011
- FR-016
- FR-017
- FR-025
- FR-027
- FR-030
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
- T026
- T027
- T028
- T029
- T030
history:
- at: '2026-08-09T17:05:36Z'
  actor: planner
  action: Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/transport_attempts.py
create_intent:
- src/specify_cli/sync/transport_attempts.py
- src/specify_cli/sync/transport_lease.py
- tests/sync/test_transport_attempt_recovery.py
- tests/sync/test_transport_result_lease.py
- tests/sync/test_transport_orphan_settlement.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/transport_attempts.py
- src/specify_cli/sync/transport_lease.py
- tests/sync/test_transport_attempt_recovery.py
- tests/sync/test_transport_result_lease.py
- tests/sync/test_transport_orphan_settlement.py
role: implementer
tags: []
tracker_refs:
- Priivacy-ai/spec-kitty#3262
- Priivacy-ai/spec-kitty-saas#585
---

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

Then read research Decisions 6 and 13, the transport-attempt state machine in
`data-model.md`, both contracts, and merged WP03–WP05 APIs. This package defines
the shared protocol only; it does not edit transport adapters.

## Objective

Establish one durable DeliveryAttempt protocol and one project-scoped,
cross-process transport/result lease. A sender persists an attempt before I/O,
performs its final eligibility check while holding the lease, and records only a
truthful result. Opt-out cancels not-started attempts and either settles or
irrevocably terminalizes orphaned in-flight attempts before returning. A late
recovery can never promote an orphan to success.

## Subtask T026 — Red-first protocol ATDD

Commit public-service tests that fail on the planning base for durable attempt
preparation, final-check/transport lease ordering, native-identity recovery, and
orphan settlement. Include admitted positive controls and deterministic barriers;
do not put these red assertions into WP01.

## Subtask T027 — Durable attempts and native reconciliation

Persist before network I/O: attempt ID, write kind, native
idempotency/correlation identity, project UUID, consent epoch/generation,
target/audience/admission generation, payload hash/reference, timestamps,
deadline, reconciliation strategy, and state. Event ID, LocalCommit hash, body
hash/task ID, history action identity, and admission operation key remain stable
across recovery.

After process death, recover `prepared`, `in_flight`, `unknown`, and
`terminal_unknown` truthfully. Query or retry only when the native protocol makes
the same identity safe; otherwise park for explicit operator action. Never mint a
fresh identity for a possibly disclosed payload.

## Subtask T028 — Project-scoped transport/result lease

Implement the per-project cross-process lease over WP02's store/layout authority.
Under the lease, immediately before transport start, revalidate current local
consent/epoch, exact target audience, admission generation, ownership, and kill
switch. A project-bearing write cannot start transport or record its genuine
result outside that lease. Use bounded, diagnosable deadlines; a process-local
mutex is insufficient.

## Subtask T029 — Opt-out settlement and orphan terminalization

Implement both orderings:

1. If opt-out wins before transport start, cancel the attempt and seal authority.
2. If transport already started and the worker remains live, opt-out waits for
   its genuine bounded result to be committed under the old generation.
3. If the worker dies or the response remains uncertain at the deadline, opt-out
   atomically records `terminal_unknown`, seals authority, and returns.

Remote revoke remains a separate durable operation and may be pending. After
opt-out returns, no old-generation attempt may start a write or record success.

## Subtask T030 — Protocol ordering and late-recovery proof

Force `before_attempt_commit`, `after_attempt_commit_before_send`,
`transport_started`, `response_received_before_result`, and `result_committed`.
Prove bounded completion, original-identity recovery, truthful duplicate/refusal,
and the compound sequence: kill during response uncertainty, invoke opt-out
immediately, allow it to terminalize, then run late recovery. Late recovery must
preserve `terminal_unknown` and may attach diagnostic remote evidence only; it
cannot promote success or automatically resend.

## Branch Strategy

Run `spec-kitty agent action implement WP06 --agent <name>` only after WP04 and
WP05 approval. Use the computed lane and governed merge. No hosted mutation,
push, PR, release, or deployment is authorized.

## Test strategy

Use local loopback/fake transports, real filesystem locks, real subprocess kills,
and monotonic test clocks. Run the three owned tests plus focused consent/admission
repository tests, ruff, and strict mypy on touched modules.

## Definition of Done

- Attempts are durable before I/O and preserve native identity.
- Final eligibility, transport start, and genuine result recording share one
  cross-process project lease.
- Opt-out returns only after live settlement or irreversible orphan
  terminalization.
- No late recovery promotes or resends a terminalized orphan.
- The protocol API is adapter-neutral and ready for WP07/WP08.

## Risks and reviewer guidance

Reviewers must inspect durable state across real process death and force both
lease orderings. Reject unlocked final checks, broad retry-on-unknown behavior,
fresh recovery identities, unbounded opt-out, or any late-success promotion after
`terminal_unknown`.
