---
work_package_id: WP03
title: DossierReconciler — Rebuild and Verify
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- FR-006
tracker_refs:
- '#2180'
planning_base_branch: feat/dossier-parity-reconciler
merge_target_branch: feat/dossier-parity-reconciler
branch_strategy: Planning artifacts for this mission were generated on feat/dossier-parity-reconciler. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dossier-parity-reconciler unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Reconciler
assignee: ''
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "2873249"
history:
- at: '2026-07-20T06:13:30Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/dossier/reconciler.py
create_intent:
- src/specify_cli/dossier/reconciler.py
- tests/dossier/test_reconciler.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dossier/reconciler.py
- tests/dossier/test_reconciler.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 — DossierReconciler (Rebuild and Verify)

## ⚡ Do This First: Load Agent Profile

Load your assigned profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role: `implementer`) before anything else.

## Objective

Build the `DossierReconciler`: a pure component that rebuilds a dossier projection from source, computes its canonical hash (WP01), compares it to the recorded/emitted hash, and returns a structured `ReconciliationResult` — either PARITY, or DIVERGENCE with the differing artifact paths named. Fail-closed: any inability to compute or compare is an error, never a default "parity" (C-005, FR-006).

## Context

- New module `src/specify_cli/dossier/reconciler.py`. Pure domain logic — no request/DB coupling; reusable as a library API (WP04 exposes it).
- Reuses WP01's canonical hash. Rebuild reads the same source the dossier is built from (artifacts / event stream); this WP does not change the hash definition.

## Subtasks

### T010 — Scaffold + campsite
Create the reconciler module skeleton and the test file. Note the source surfaces it reads (dossier artifacts / index).

### T011 — Red acceptance tests (FR-005, FR-006; AS-2/AS-3/AS-4)
In `tests/dossier/test_reconciler.py` add failing tests: AS-2 (rebuild of an unchanged projection reports PARITY, zero differing artifacts); AS-3 (one artifact differs → DIVERGENCE naming that artifact, and the result is fail-loud, not success); AS-4 (churn-only change → still PARITY via WP01's projection input).

### T012 — Implement rebuild-from-source (FR-004)
Rebuild the dossier projection from source and compute its canonical hash via WP01.

### T013 — Implement compare + result (FR-005, NFR-004)
Compare rebuilt vs recorded hash; return `ReconciliationResult` = PARITY | DIVERGENCE(named artifacts). Every DIVERGENCE names ≥1 specific artifact (NFR-004) — no bare "mismatch".

### T014 — Fail-closed enforcement (FR-006, C-005) [P]
Any exception or inability to compute/compare returns an explicit error result, never a default parity. Add a test that a compute failure surfaces an error, not success.

## Branch Strategy

Planning branch: `feat/dossier-parity-reconciler`; final merge target: same. Worktrees per-lane from `lanes.json`.

## Definition of Done

- `DossierReconciler` returns PARITY / named-DIVERGENCE; AS-2/AS-3/AS-4 green.
- Fail-closed proven (compute failure → error, never parity).
- Pure (no request/DB coupling), ready for WP04 to expose as CLI + API.
- ruff + mypy clean; ≥90% changed-code coverage.

## Risks / Reviewer Guidance

- Fail-closed is the security-relevant property — reviewer specifically probes the no-`else: proceed` discipline (mirror the bind-verify pattern).
- Confirm DIVERGENCE always names artifacts; a bare boolean mismatch is a defect.

## Activity Log

- 2026-07-20T06:55:58Z – claude:sonnet:python-pedro:implementer – shell_pid=2839700 – Assigned agent via action command
- 2026-07-20T07:06:33Z – claude:sonnet:python-pedro:implementer – shell_pid=2839700 – DossierReconciler (pure, WP01-backed): rebuild source projection -> canonical snapshot hash via compute_dossier_snapshot_hash, compare to recorded/emitted hash, structured ReconciliationResult PARITY|DIVERGENCE(named artifacts)|ERROR. Fail-closed (C-005/FR-006): compute/normalize/inconsistent-record failures return ERROR, never default parity; result is truthy only on PARITY; no else:proceed. AS-2/AS-3/AS-4 covered. Tests: 16 passed (tests/dossier/test_reconciler.py); full dossier suite 352 passed (no regression). Lint: ruff check + ruff format --check exit 0; mypy --strict clean. Fail-closed proven: compute-failure hash_fn -> ERROR, malformed source entry -> ERROR, recorded_hash inconsistent with recorded projection -> ERROR. Stable entrypoint at specify_cli.dossier.reconciler for WP04 to wrap; __init__.py left untouched (other-lane coordination file). No CLI (WP04).
- 2026-07-20T07:07:39Z – claude:sonnet:reviewer:reviewer – shell_pid=2873249 – Started review via action command
- 2026-07-20T07:10:28Z – user – shell_pid=2873249 – Review passed: DossierReconciler pure rebuild+compare returns PARITY/named-DIVERGENCE/ERROR, fail-closed (C-005) with PARITY-only truthiness and no else:proceed; reuses WP01 compute_dossier_snapshot_hash (C-001, not re-implemented); AS-2/AS-3(NFR-004 named artifacts)/AS-4 covered; 16 tests pass, ruff+mypy --strict clean; scope limited to owned files (init/hasher/indexer deltas are WP01 dependency merge).
