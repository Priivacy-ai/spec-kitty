---
work_package_id: WP05
title: tasks.py move-task strangle
dependencies:
- WP01
requirement_refs:
- C-001
- C-005
- C-006
- FR-004
- FR-005
- NFR-004
tracker_refs: []
planning_base_branch: design/coord-primary-partition-lock
merge_target_branch: design/coord-primary-partition-lock
branch_strategy: Planning artifacts for this mission were generated on design/coord-primary-partition-lock. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-primary-partition-lock unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1713716"
history:
- at: '2026-07-07T20:40:00+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_move_task.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_placement.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_placement.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` (implementer) via `/ad-hoc-profile-load`. Read `spec.md`, `plan.md` (IC-03),
`research.md` (D6), `contracts/seam-api.md`. Authoritative over siblings (C-005). Depends on **WP01**.
Implement via `spec-kitty agent action implement WP05 --agent claude`.

## Objective

Route the `tasks.py` move-task / mark-status write cluster through `seam.write_target(STATUS_STATE)`,
extracting a placement helper from `_mt_commit_wp_file` first so it stays ≤15, and **reconciling with
the just-landed PR #2438 review-regression-gate code** on this surface. Red-first (C-006).

## Context

- `move-task` bookkeeping is a coordination/lifecycle artifact (`STATUS_STATE`) → coord surface for
  coord-routing missions.
- **PR #2438 (review-regression-gate) landed on `tasks_move_task.py`** this cycle — read the current
  code before editing; do not regress its `move-task --to for_review` gate.

## Subtasks

### T022 — Red-first
- Failing test proving the move-task/mark-status commit derives placement from the checkout / inline lane selection rather than the seam.

### T023 — Extract placement helper (≤15) before routing
- `_mt_commit_wp_file` (:1252) is at cyclomatic 13. Extract the placement-resolution into a helper
  BEFORE adding seam routing, so the function stays ≤15 (S3776 headroom).

### T024 — Route + reconcile #2438
- Route the move-task/mark-status write cluster (still derives from `st.target_branch`/`workspace.branch_name`, confirmed NOT yet routed) through `seam.write_target(STATUS_STATE)`. Verify the
  #2438 review-regression-gate at `move-task --to for_review` still fires and passes.
- **Reconcile with the existing coord pre-gate** `_skip_target_branch_commit` (`tasks_move_task.py:238`) that already skips the `target_branch` commit on coord missions — the seam routing must compose with (not double up on) that skip-gate. (Prior #2154 routing was the READ leg only.)

### T025 — Tests + regression
- move-task bookkeeping lands on the coord surface for coord missions, primary for non-coord; #2438 gate green.

### T026 — Campsite (Sonar)
- Hoist status-event field literals only if inside functions you edit (see table).

## Campsite (Sonar issues in owned files)

| File | Rule | Location | Class | Action |
|------|------|----------|-------|--------|
| `tasks_move_task.py` | S3776 | `_mt_commit_wp_file` (13) | SAFE | Extract placement helper; keep ≤15 |
| `tasks_move_task.py` | S1192 | `'to_lane'` ×7, `'event_id'` ×5, `'utf-8'` ×8, `'[/dim]'` ×3 | ADJACENT | Hoist only inside functions you edit |

## Branch Strategy

Base / merge target `design/coord-primary-partition-lock`. Worktree per computed lane. Authoritative
(C-005): siblings rebase onto our routing here.

## Definition of Done

- move-task/mark-status cluster routes via `seam.write_target(STATUS_STATE)`; `_mt_commit_wp_file` ≤15.
- #2438 review-regression-gate still green.
- Red-first + regression green; `ruff` + `mypy` clean.

## Risks & Reviewer guidance

- **Reconcile with #2438** — reviewer confirms the just-landed move-task gate is not regressed.
- STATUS_STATE is a coord-partition kind — verify coord missions commit bookkeeping to the coord surface, non-coord to primary (C-002 unchanged mapping).

## Activity Log

- 2026-07-07T22:45:26Z – claude:sonnet:python-pedro:implementer – shell_pid=1503078 – Assigned agent via action command
- 2026-07-07T23:20:00Z – claude:sonnet:python-pedro:implementer – shell_pid=1503078 – Ready; #2438 gate + skip-gate reconciled; ruff exit 0
- 2026-07-07T23:20:55Z – claude:opus:reviewer-renata:reviewer – shell_pid=1713716 – Started review via action command
- 2026-07-07T23:28:40Z – user – shell_pid=1713716 – Review passed (reviewer-renata): Red-first genuine (3 new symbols absent pre-impl -> AttributeError). STATUS_STATE routing via placement_seam(...).write_target(STATUS_STATE) in _mt_resolve_status_placement_ref; coord->coord-branch, flat->target_branch verified (C-002 unchanged). #2438 gate (_mt_run_pre_review_gate) untouched + green (99 gate/seam/coord tests pass); coord skip-gate _skip_target_branch_commit (tasks_shared.py:369) untouched and composed-with (placement resolves FIRST, unconditionally). Sync commit 58530efd9 verbatim from design branch (3 prod files byte-match; two shared prod files 0-deletion additive; sole deletion is PR#2438 coverage-floor value). Complexity: C901 clean (_mt_commit_wp_file extracted, <=15). ruff clean; mypy clean under canonical CI invocation (mypy --strict src/specify_cli) - isolated per-file no-any-return is a follow_imports=skip artifact, not present in the gate. 8 placement tests pass. S1192 encoding literal hoisted (_WP_FILE_WRITE_ENCODING, 3 sites). No dead code, no terminology regressions.
