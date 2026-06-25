---
work_package_id: WP07
title: _coordination_doctor + drift CC19 decompose (H2 func-local merge import)
dependencies:
- WP06
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-007
tracker_refs:
- '2059'
planning_base_branch: prog/2059-doctor
merge_target_branch: prog/2059-doctor
branch_strategy: Planning artifacts for this mission were generated on prog/2059-doctor. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2059-doctor unless the human explicitly redirects the landing branch.
created_at: '2026-06-24T19:54:56+00:00'
subtasks:
- T019
- T020
- T021
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3382630"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/_coordination_doctor.py
create_intent:
- src/specify_cli/cli/commands/_coordination_doctor.py
- tests/specify_cli/cli/commands/test_coordination_doctor.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_coordination_doctor.py
- tests/specify_cli/cli/commands/test_coordination_doctor.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Extract the coordination / git-health cluster (K) into `_coordination_doctor.py`, **decompose `_check_lane_sparse_checkout_drift` (CC19)** into ≤15-CC tested helpers, and — critically — **keep the `merge.path_is_under_worktrees` import FUNCTION-LOCAL (H2)** to avoid a `doctor↔merge` module-load cycle.

## Context

- Cluster K (research §2, lines 3017-3434): `DoctorFinding` (dataclass), `_MIN_GIT_VERSION` const, `_detect_git_version`, `_check_git_version`, `_check_tracked_worktrees_content` (CC14), `_check_coordination_worktree_health` (CC14), `_check_lane_sparse_checkout_drift` (CC19), `coordination_health` cmd (CC15).
- **H2:** `_check_tracked_worktrees_content` (3103) imports `specify_cli.cli.commands.merge.path_is_under_worktrees` *inside the function body*. This is deliberate — hoisting to module scope reintroduces the `doctor↔merge` cycle. Keep it function-local in the sibling.
- `coordination_health` cmd (CC15) is at the ceiling — keep it ≤15.
- The command's exit contract: 0 / 1 if any `error` finding.

## Subtasks

### T019 — Create `_coordination_doctor.py` + decompose
- Move Cluster K into the sibling, importing shared infra from `_doctor_shared`. Decompose `_check_lane_sparse_checkout_drift` (CC19) into ≤15-CC sub-helpers (e.g. per-lane scan, drift classification, finding assembly). Keep `coordination_health` ≤15.
- **Keep `from specify_cli.cli.commands.merge import path_is_under_worktrees` INSIDE `_check_tracked_worktrees_content`** — never at module top.
- `ruff check --select C901` on the sibling → zero findings.

### T020 — Delegate
- `coordination` command body becomes a thin shell delegating to the sibling, preserving the 0/1 exit contract (1 iff any `error` finding).

### T021 — Focused tests + cycle check
- `test_coordination_doctor.py`: per-helper tests for git-version detect/check, tracked-worktree content, coordination-worktree health, and the decomposed drift branches. ≥90% coverage.
- Assert no `doctor↔merge` cycle: `python -c "import specify_cli.cli.commands.doctor; import specify_cli.cli.commands.merge"` clean; `git grep -n "path_is_under_worktrees" _coordination_doctor.py` shows it inside the function only.
- WP01 golden green.

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Worktrees per `lanes.json`. Commit with `--to-branch prog/2059-doctor`; transitions from the primary checkout CWD.

## Test Strategy (ATDD)

RED per-helper + drift-branch tests before extraction; GREEN after. Import-cycle regression test; golden green.

## Out-of-map edits

- `src/specify_cli/cli/commands/doctor.py` — delegate the `coordination` body. Owned by WP11; sequential chain → no concurrent writer.

## Definition of Done

- Cluster K in `_coordination_doctor.py`; `_check_lane_sparse_checkout_drift` CC19 + `coordination_health` decomposed/kept ≤15 (C901 clean).
- `merge.path_is_under_worktrees` import stays function-local; no `doctor↔merge` cycle (H2 / I-6).
- 0/1 exit contract preserved (golden green); ≥90% coverage; ruff + mypy --strict clean, zero new suppressions.

## Risks

- Hoisting `path_is_under_worktrees` to module scope reintroduces the `doctor↔merge` cycle (H2) — **rejection criterion**.
- Relocating the drift checker at CC19 fails the gate.

## Reviewer Guidance

Recommended reviewer: standard. Verify the `merge` import is function-local (grep), the import-cycle regression test passes, drift checker decomposed (C901 clean), 0/1 exit unchanged, ≥90% coverage.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP06; H2 func-local merge import + drift CC19).
- 2026-06-24T21:50:19Z – claude:opus:randy-reducer:implementer – shell_pid=3325486 – Assigned agent via action command
- 2026-06-24T22:03:12Z – claude:opus:randy-reducer:implementer – shell_pid=3325486 – Cluster K extracted; drift CC19 decomposed; merge import func-local (H2); no cycle; 91% cov; golden green
- 2026-06-24T22:03:14Z – claude:opus:reviewer-renata:reviewer – shell_pid=3382630 – Started review via action command
- 2026-06-24T22:03:18Z – user – shell_pid=3382630 – Cluster K in _coordination_doctor; _check_lane_sparse_checkout_drift CC19 decomposed + coordination_health <=15CC (C901 clean); H2/I-6 honored: merge.path_is_under_worktrees func-local (AST+import-cycle tests pass); 0/1 exit byte-preserved (golden+test_doctor_coordination green); DoctorFinding+check helpers re-export; 91% coverage; mypy --strict clean
