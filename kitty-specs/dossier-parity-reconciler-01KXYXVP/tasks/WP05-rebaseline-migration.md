---
work_package_id: WP05
title: Snapshot-Hash Re-baseline Migration
dependencies:
- WP02
requirement_refs:
- FR-009
tracker_refs:
- '#2180'
planning_base_branch: feat/dossier-parity-reconciler
merge_target_branch: feat/dossier-parity-reconciler
branch_strategy: Planning artifacts for this mission were generated on feat/dossier-parity-reconciler. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dossier-parity-reconciler unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
phase: Phase 3 - Cutover
assignee: ''
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "2957090"
history:
- at: '2026-07-20T06:13:30Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/dossier/rebaseline.py
create_intent:
- src/specify_cli/dossier/rebaseline.py
- tests/dossier/test_rebaseline.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dossier/rebaseline.py
- tests/dossier/test_rebaseline.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 — Snapshot-Hash Re-baseline Migration

## ⚡ Do This First: Load Agent Profile

Load your assigned profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role: `implementer`) before anything else.

## Objective

Provide a one-time re-baseline that recomputes existing recorded snapshot hashes under the canonical definition, so content that did not change is NOT flagged divergent after the cutover (FR-009). Verify zero false-divergence across the local backlog (NFR-003).

## Context

- After WP02, emitted values use the canonical `sha256:` form; previously-recorded values use the retired concat/bare-hex form and are non-comparable. This WP recomputes/records them under the canonical definition.
- Acceptable because there are no live hosted customers (spec Assumption A-003) — historical hashes can be recomputed.
- Depends on WP02 (the canonical emit + validation must be in place).

## Subtasks

### T019 — Red tests (FR-009, NFR-003)
In `tests/dossier/test_rebaseline.py`: after re-baseline, unchanged content reconciles as PARITY (zero false-divergence); content that genuinely changed still diverges.

### T020 — Implement the re-baseline (FR-009)
Implement `src/specify_cli/dossier/rebaseline.py`: a one-time recompute of recorded snapshot hashes under the canonical definition. Idempotent (safe to re-run); no mutation of source artifacts (read-only over the repo, per the no-dirty-tree invariant #2263).

### T021 — Verify across the backlog (NFR-003) [P]
Prove zero false-divergence over a representative slice of the local backlog. Run focused type/style/coverage gates.

## Branch Strategy

Planning branch: `feat/dossier-parity-reconciler`; final merge target: same. Worktrees per-lane from `lanes.json`.

## Definition of Done

- Re-baseline recomputes recorded hashes under the canonical definition; idempotent; source-tree read-only.
- Unchanged content → zero false-divergence (NFR-003); genuine changes still diverge.
- ruff + mypy clean; ≥90% changed-code coverage.

## Risks / Reviewer Guidance

- Must not dirty the worktree (respect #2263) — reviewer confirms the re-baseline is read-only over source artifacts.
- Coordinate cutover with the companion server PR (C-003) so CLI and server re-baseline consistently; note any ordering requirement in the PR.

## Activity Log

- 2026-07-20T07:23:00Z – claude:sonnet:implementer:implementer – shell_pid=2912346 – Assigned agent via action command
- 2026-07-20T07:40:44Z – claude:sonnet:implementer:implementer – shell_pid=2912346 – Ready for review: one-time re-baseline migration. rebaseline.py recomputes recorded snapshot hashes via the live index->compute_snapshot pipeline (canonical WP01/WP02 def, C-001); idempotent; read-only over source (#2263); wired as 'spec-kitty migrate rebaseline-dossier-hashes'. 11/11 tests green; NFR-003 verified: 61/61 backlog snapshots re-baseline with 0 false-divergence (dry-run).
- 2026-07-20T07:41:48Z – claude:sonnet:reviewer:reviewer – shell_pid=2957090 – Started review via action command
