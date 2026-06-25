# Requirements Checklist — #2056 mission.py remainder decomposition

Quality gate for the spec. Each item must hold before plan/tasks.

## Completeness

- [x] Overview states the target (mission.py 4125 LOC / 62 defs / 8 subcommands) and that this mission decomposes the REMAINDER (commit_router pipeline already extracted by 01KVMBD6).
- [x] Scope and out-of-scope are explicit (no #2058 tasks.py de-godding, no re-extraction of commit_for_mission, no new functionality).
- [x] The 3 mega-functions are named with LOC (finalize_tasks 1227, setup_plan 507, create_mission 281).
- [x] The 4 research-resolved seams are named (record-analysis / lifecycle-per-family / parsing-validation / feature-dir-resolution).

## Correctness of the critical constraint

- [x] Spec states the base is origin/main (c3814ec5a) and does NOT include #2058.
- [x] Spec states `_planning_commit_worktree` / `_resolve_planning_placement` are LIVE (tasks.py calls them) — verified by grep.
- [x] Disposition is RELOCATE into commit_router + repoint tasks.py, never delete (FR-007).
- [x] Reconciliation against commit_router's existing `_stage_artifacts_in_coord_worktree` is called out.

## Functional Requirements

- [x] FR-001 frozen 8-subcommand CLI surface (byte-for-byte) — Approved.
- [x] FR-002 #2056 pointer comment (matches #1623 convention) — Approved.
- [x] FR-003 decompose into the 4 seams; D first; one-way imports — Approved.
- [x] FR-004 per-seam focused tests ≥90%; direct unit tests for pure parsers/resolvers — Approved.
- [x] FR-005 internal decomposition of the 3 mega-functions to ≤15 CC with focused tests — Approved.
- [x] FR-006 shim re-exports every ~100 test-patched name — Approved.
- [x] FR-007 relocate planning-commit residue + repoint tasks.py (LIVE, do not delete) — Approved.

## NFRs / Constraints

- [x] NFR maxCC ≤15, ≥90% coverage, ruff + mypy --strict clean, no new suppressions.
- [x] C-001 no command/flag changes; C-002 canonical commit_router; C-003 behavior-preserving; C-004 no new suppressions; C-005 golden characterization test FIRST (WP01).

## Testability

- [x] Each FR maps to a verifiable success criterion (SC-1..SC-8).
- [x] Golden CLI characterization test is the named safety net and is sequenced first.
- [x] Invariants (INV-1..INV-9 in data-model.md) map to enforcing tests.
