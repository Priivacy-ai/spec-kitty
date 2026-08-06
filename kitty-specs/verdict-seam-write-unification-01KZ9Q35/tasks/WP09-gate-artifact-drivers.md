---
work_package_id: WP09
title: Gate-artifact merge drivers + review-cycle driver relax (FR-014)
dependencies:
- WP05
requirement_refs:
- FR-009
- FR-014
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T044
- T045
- T046
- T047
- T048
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/merge_driver.py
create_intent:
- tests/review/test_review_cycle_merge_driver.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge_driver.py
- src/specify_cli/cli/commands/init.py
- tests/architectural/test_merge_reconciliation_class_guard.py
- tests/architectural/census/verdict_seam_IC04.yaml
- tests/review/test_review_cycle_merge_driver.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.

## Objective

Guarantee the row-aware matrix merge drivers are registered/active before the squash (defense-in-depth
for #2804), fix the `.md`→`.json` driver seed drift, and **downgrade the `spec-kitty-review-cycle`
fail-closed driver to non-aborting** now that the `.md` is non-authoritative prose (FR-014). Two
divergent best-effort renders must not abort an otherwise-clean squash.

## Context

- **Requirements**: FR-009 (driver-registration leg + `.md`→`.json` seed-drift fix), FR-014 (review-cycle
  driver relax under D3).
- **Contract**: [gate-artifact-write-surface.md](../contracts/gate-artifact-write-surface.md) — G2
  driver registration before squash, G3 seed-drift fix.
- **Decisions**: **D-PLAN-6** (with the `.md` non-authoritative and unread, the `spec-kitty-review-cycle`
  conflict-marker driver downgrades to non-aborting union/last-writer, not Exit(1); retiring it entirely
  is the fallback if no prose-merge is needed), **D-PLAN-16 / IC-06b** (shares `merge_driver.py`/`init.py`
  with FR-014; add `test_merge_reconciliation_class_guard.py`, `verdict_seam_IC04.yaml`,
  `test_review_cycle_merge_driver.py` to this surface set).
- **Sequencing**: depends on **WP05** — FR-014's relax is semantically gated on the `.md` being
  non-authoritative (WP05's demote + reader collapse). Serial with WP06 on the census, but WP09 owns a
  **separate** census shard (`census/verdict_seam_IC04.yaml`), not the main `verdict_seam_census.yaml`,
  so no race with WP06.
- **Coordinate with WP08**: WP08 retires `issue-matrix.md` on the write side; WP09 fixes the driver seed
  so the issue-matrix driver targets `.json` and is not inert.

## Subtasks

### T044 — Red-first: divergent best-effort `.md` renders must not abort the squash (FR-014)
- **Purpose**: Spec edge case — two divergent best-effort renders meet at merge and must not Exit(1).
- **Steps**: In new `tests/review/test_review_cycle_merge_driver.py`, drive two divergent
  `review-cycle-N.md` renders through the driver and assert the squash is **not** aborted. Red against
  the current fail-closed driver.
- **Files**: `tests/review/test_review_cycle_merge_driver.py`.
- **Validation**: fails before T045; green after.

### T045 — Downgrade `spec-kitty-review-cycle` driver to non-aborting (FR-014)
- **Purpose**: FR-014 / D-PLAN-6.
- **Steps**: In `merge_driver.py`, downgrade the review-cycle conflict-marker driver from fail-closed
  Exit(1) to non-aborting (union / last-writer on prose), or retire it if no prose-merge is needed.
  Update `test_merge_reconciliation_class_guard.py` to reflect the driver's new class.
- **Files**: `src/specify_cli/cli/commands/merge_driver.py`,
  `tests/architectural/test_merge_reconciliation_class_guard.py`.
- **Validation**: T044 green; the reconciliation-class guard reflects the non-aborting class.

### T046 — Guarantee row-aware matrix drivers registered/active before squash (G2)
- **Purpose**: FR-009 defense-in-depth — `-X theirs` must never clobber a filled matrix.
- **Steps**: In `merge_driver.py` + `init.py` (`.gitattributes` / `required_entries`), guarantee the
  `spec-kitty-acceptance-matrix` / `spec-kitty-issue-matrix` row-aware drivers are registered/active on
  the real merge repo before the squash. Note the pin's bare `git init` harness may lack
  `.gitattributes` — register within the merge flow, not only via a pre-seeded repo.
- **Files**: `src/specify_cli/cli/commands/merge_driver.py`, `src/specify_cli/cli/commands/init.py`.
- **Validation**: drivers active before squash in a real-merge test.

### T047 — Fix the `.md`→`.json` driver seed drift (G3)
- **Purpose**: FR-009 — `m_3_2_6_gate_artifact_merge_drivers` seeded the retired `.md` pattern, leaving
  the issue-matrix driver inert.
- **Steps**: Fix the seed so the issue-matrix driver targets `.json` (coordinate with WP08's
  `issue-matrix.md` retirement). Update `init.py` `required_entries` accordingly.
- **Files**: `src/specify_cli/cli/commands/init.py`, `src/specify_cli/cli/commands/merge_driver.py`.
- **Validation**: the issue-matrix driver matches the live `.json` artifact and is active.

### T048 — IC04 census shard reconcile
- **Purpose**: FR-006/C-004 — the FR-014 driver change reflected in the owned IC04 census shard.
- **Steps**: Update `census/verdict_seam_IC04.yaml` to the post-relax derived set. This shard is
  WP09-owned — no edit to the main `verdict_seam_census.yaml` (WP01/WP05/WP06 own that).
- **Files**: `tests/architectural/census/verdict_seam_IC04.yaml`.
- **Validation**: `pytest tests/architectural/test_verdict_seam_census.py -q` green (shard consistent).

## Branch Strategy note

`already-confirmed`; base == target. Prepare with `spec-kitty implement WP09`. Depends on WP05 (the
`.md` must be non-authoritative before the driver relax). Owns a separate census shard from WP06, so no
census race. Coordinate the seed-drift fix with WP08's `issue-matrix.md` retirement.

## Definition of Done

- FR-014: divergent best-effort renders do not abort the squash (T044/T045); the reconciliation-class
  guard reflects the non-aborting driver.
- FR-009: matrix drivers registered/active before squash (T046); `.md`→`.json` seed drift fixed (T047);
  IC04 census shard reconciled (T048).
- Gate: `pytest tests/review/test_review_cycle_merge_driver.py
  tests/architectural/test_merge_reconciliation_class_guard.py
  tests/architectural/test_verdict_seam_census.py -q` green; `ruff` + `mypy --strict` clean (NFR-003).

## Risks

- **Driver registration on the real merge repo** — the pin's bare `git init` harness lacks
  `.gitattributes`; register within the merge flow (T046).
- **Seed-drift / WP08 coupling** — the `.json` seed must match WP08's retired `issue-matrix.md`;
  coordinate so neither leaves the driver inert.

## Reviewer guidance

Confirm the review-cycle driver no longer Exit(1)s on divergent prose (T044 red-first). Confirm the
matrix drivers are active **before** the squash, not merely declared. Confirm no edit to the main
`verdict_seam_census.yaml` (only the owned IC04 shard).
