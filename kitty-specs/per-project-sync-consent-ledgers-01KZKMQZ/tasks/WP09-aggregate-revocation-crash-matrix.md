---
work_package_id: WP09
title: Aggregate revocation and crash matrix
dependencies:
- WP07
- WP08
requirement_refs:
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
- C-005
- C-007
- C-010
planning_base_branch: feat/per-project-sync-consent
merge_target_branch: feat/per-project-sync-consent
branch_strategy: Planning artifacts for this mission were generated on feat/per-project-sync-consent. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/per-project-sync-consent unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
history:
- at: '2026-08-09T17:05:36Z'
  actor: planner
  action: Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/sync/test_transport_revocation_matrix.py
create_intent:
- tests/support/sync_transport_barriers.py
- tests/sync/test_transport_revocation_matrix.py
- tests/sync/test_transport_crash_matrix.py
execution_mode: code_change
owned_files:
- tests/architectural/test_egress_consent_boundary.py
- tests/architectural/test_sync_writer_census.py
- tests/support/sync_transport_barriers.py
- tests/sync/test_daemon_publish_consent_3030.py
- tests/sync/test_transport_revocation_matrix.py
- tests/sync/test_transport_crash_matrix.py
role: implementer
tags: []
tracker_refs:
- Priivacy-ai/spec-kitty#3262
- Priivacy-ai/spec-kitty#3030
---

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

Read WP01's complete sender census and all merged WP06–WP08 outputs. This is the
aggregate adversarial proof package; fix defects in their owning WPs rather than
silently weakening the matrix.

## Objective

Prove every interactive and daemon/background transport family obeys both revoke
orderings, every required hard-kill window, project isolation, and the exact
kill-during-response -> immediate opt-out -> late-recovery invariant.

## Subtask T040 — All-family synchronization harness

Build reusable test-only process barriers at `before_attempt_commit`,
`after_attempt_commit_before_send`, `transport_started`,
`response_received_before_result`, and `result_committed`. Bind each barrier to
project, attempt, native correlation, and adapter family so mixed concurrent
runs cannot cross-release.

Update the executable sender/writer censuses after WP07 and WP08 land. Correct
their final owner labels, enumerate every live runtime-event, dossier,
body-enqueue, background-discovery, and daemon control-plane row, and migrate the
existing daemon-publish regression to the canonical proof protocol. The census
must inspect per-symbol sinks rather than accepting a file merely because one
known sink in that file is allowlisted.

## Subtask T041 — Both revoke orderings for every family

For each census family, prove pause-before-start versus opt-out and
start-before-opt-out with genuine success, duplicate, terminal refusal, and
timeout. Assert exact request bytes, attempt/result generations, no post-return
network start or success, and another project progressing throughout.

## Subtask T042 — Hard-kill recovery matrix

Kill real subprocesses before send, during response uncertainty, and after remote
acceptance before result commit. Reconcilable protocols reuse the original
identity and record truthful outcomes. Non-reconcilable uncertainty parks without
automatic resend. Account/team/target/admission generation changes while queued
must fail closed.

## Subtask T043 — Compound opt-out/late-recovery case

For every family capable of response uncertainty: pause during response, kill
the worker, invoke opt-out immediately, let the bounded lease protocol record
`terminal_unknown` and return, then run late recovery. Assert no network resend,
no success promotion, no old-generation result rewrite, and no effect on project
B. This ordering is mandatory and cannot be inferred from three separate tests.

## Branch Strategy

Run `spec-kitty agent action implement WP09 --agent <name>` after WP07 and WP08
approval. Use the computed lane and governed merge only; do not publish or mutate
hosted state.

## Test strategy

Use real subprocesses and loopback/fake transports with exact byte capture. Run
both owned matrix tests, the WP06–WP08 owned suites, ruff, and strict mypy. Retain
the matrix result as input to WP11's immutable manifest.

## Definition of Done

- Every sender census row appears in the matrix.
- Both revoke orderings and every kill window pass for every applicable family.
- The compound kill/opt-out/late-recovery test preserves terminal uncertainty.
- A second project remains live and physically isolated throughout.

## Risks and reviewer guidance

Reject exception-only simulations, representative-family sampling, separately
tested steps claimed as the compound sequence, sleep-based races without
barriers, or an assertion limited to UI state rather than bytes and durable rows.
