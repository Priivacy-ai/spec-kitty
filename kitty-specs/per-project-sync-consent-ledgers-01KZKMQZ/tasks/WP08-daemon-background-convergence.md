---
work_package_id: WP08
title: Daemon and background convergence
dependencies:
- WP06
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
- tests/sync/test_daemon_project_isolation.py
- tests/sync/test_background_authority_convergence.py
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

Run `spec-kitty agent action implement WP08 --agent <name>` after WP06 approval.
It may progress alongside WP07 because owned files do not overlap. Use the
computed lane and governed merge only; do not publish or mutate hosted state.

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
