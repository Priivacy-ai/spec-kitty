---
work_package_id: WP08
title: Daemon and background convergence
dependencies:
- WP06
- WP07
requirement_refs:
- FR-001
- FR-003
- FR-005
- FR-007
- FR-008
- FR-011
- FR-021
- FR-025
- FR-027
- FR-028
- FR-029
- FR-031
- NFR-001
- NFR-003
- NFR-004
- NFR-007
- C-002
- C-003
- C-005
- C-007
planning_base_branch: feat/per-project-sync-consent
merge_target_branch: feat/per-project-sync-consent
branch_strategy: Planning artifacts for this mission were generated on feat/per-project-sync-consent. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/per-project-sync-consent unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T039
history:
- at: '2026-08-09T17:05:36Z'
  actor: planner
  action: Created by /spec-kitty.tasks
- at: '2026-08-11T15:10:00Z'
  actor: codex
  action: Rerolled WP08 from approved WP07 commit e46feceb. Runtime publication
    delegates to WebSocketClient.send_event so WP07 remains the sole WP06
    attempt/lease/final gate and exact EventAck authority; accepted and duplicate
    are the only positive outcomes, while refusal, mismatch, and timeout fail
    closed. Project-store discovery and body drain delegate to WP07/WP06 and the
    current T034 push_content_with_transport_gate API without holding a unit of
    work over I/O. Sequential ownership of the runtime assertions and egress
    architecture census records the removal of raw injection and the integrated
    T032/T033/T034 sender topology. Filed baseline #3318 remains out of scope.
- at: '2026-08-11T15:35:00Z'
  actor: codex
  action: Sequentially migrated four existing background/target test modules from
    retired shared OfflineQueue construction, non-authoritative consent grants,
    and readable queue-scope assumptions to ProjectSyncStore units, layout
    authority, durable opt-in, production discovery, and opaque target scopes.
    Node intent is preserved; no product surface was broadened beyond unwrapping
    the current ProjectOutboxTask in unauthenticated classification while leaving
    the durable task queued.
- at: '2026-08-11T16:05:00Z'
  actor: codex
  action: Sequentially migrated the ten-node body-drain consent integration suite
    from the retired shared queue and machine-index grant to project-owned stores,
    layout authority, durable opt-in/out, exact admission, and the public gated
    discovery drain. All ten refusal, retention, positive delivery, cwd isolation,
    unresolved identity, and anti-starvation intents remain executable.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/daemon.py
create_intent:
- tests/sync/test_daemon_project_isolation.py
- tests/sync/test_background_authority_convergence.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/runtime.py
- src/specify_cli/sync/background.py
- src/specify_cli/sync/daemon.py
- src/specify_cli/sync/owner.py
- tests/sync/test_target_authority_wiring.py
- tests/sync/test_daemon_project_isolation.py
- tests/sync/test_background_authority_convergence.py
- tests/sync/test_background.py
- tests/sync/test_background_body.py
- tests/sync/test_background_auth_backoff_3030.py
- tests/sync/test_body_drain_consent_3030.py
- tests/sync/test_runtime.py
- tests/sync/test_target_authority.py
- tests/architectural/test_egress_consent_boundary.py
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

Read WP01's daemon/current-writer census and merged WP02/WP03/WP04/WP06 APIs.
Migration quiesce belongs to WP10; this package owns live daemon/background paths.

## Objective

Converge daemon, runtime, and background discovery on project-owned authority,
deny-only hints, layout permits, and the durable transport protocol. A daemon
outside any checkout must keep project B live when A opts out.

The live daemon owner-record startup path is in scope. WP04 intentionally
removed legacy queue target helpers while retiring shared payload stores, so
WP08 must make `owner.py` consume canonical target identity without restoring a
legacy queue selector or treating an owner record as egress authority.
The target-coherence regression fixture is sequentially owned here because its
legacy reversible queue-scope setup cannot prove the post-WP04 opaque-scope
owner identity contract.

## Subtask T036 — Red-first daemon/background ATDD

Commit a public daemon/runtime test that fails on the planning base and proves A
opt-out does not stop B, directory enumeration creates nothing, and a possible
grant requires authoritative state. Include a positive admitted project.

## Subtask T037 — Authoritative discovery and transport convergence

Route daemon/runtime/background selection and sends through canonical project
identity, ProjectSyncContext, DeliveryAttempt, and the WP06 lease. Remove cwd,
long-lived grant caches, independent stores, and process-global defaults as
authority. A missing project/store is diagnosed without creation.

## Subtask T038 — Deny-only hints and layout permits

A fresh valid deny/revoke hint may skip payload-store open. Missing, expired,
malformed, pending, unknown, generation-mismatched, or possibly granted hints
must open project-owned authority before eligibility. No hint can grant. Every
background/current writer covered by this WP consumes WP04's pre-insert layout
permit; do not create a second layout API.

## Subtask T039 — Isolation, cache, and liveness proof

Prove enumerating project directories creates no store/consent, stale deny is
only a diagnosed liveness delay, and A operations open no B file/lock/table.
Continuously advance B through A revoke, process restart, hint expiry, and target
generation change. Mutants that grant from hints/cache/path or bypass layout
permits must fail.

## Branch Strategy

Run `spec-kitty agent action implement WP08 --agent <name>` only after the
sequential WP06 → WP07 dependency chain is approved: lane-e must contain the
approved WP07 `e46feceb` ancestry before lane-f begins. WP08 integrates WP07's
runtime EventAck transport and the shared architecture census, so it cannot
truthfully progress alongside WP07. Use the computed lane and governed merge
only; do not publish or mutate hosted state.

## Test strategy

Use temporary runtime roots, real subprocess daemons, open instrumentation, and
local fake transports. Run both owned tests plus focused discovery/hint/layout
tests, then ruff and strict mypy.

## Definition of Done

- Daemon/runtime/background rows use project authority and WP06 protocol.
- Hints can narrow only; uncertain cases read authority.
- Enumeration creates no store or consent.
- A opt-out/restart cannot stop or open B.
- Background writers consume the existing layout permit.

## Risks and reviewer guidance

Reject cached grant decisions, path/cwd identity, enumerate-by-opening, a second
layout marker, or global daemon shutdown on one-project revoke. Verify real
process behavior and physical opens, not only returned values.
