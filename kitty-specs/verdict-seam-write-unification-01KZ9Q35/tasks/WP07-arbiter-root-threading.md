---
work_package_id: WP07
title: Arbiter root threading — persist_arbiter_decision receives the resolved root
dependencies:
- WP05
requirement_refs:
- FR-016
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/arbiter.py
create_intent:
- tests/review/test_arbiter_coord_root.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/arbiter.py
- tests/review/test_arbiter_coord_root.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.

## Objective

Thread the caller-resolved `main_repo_root` into `persist_arbiter_decision` and retire the
`feature_dir.parent.parent` self-inference, so an arbiter override under a **materialized coordination
topology** resolves the correct COORD root (and status-lock root). Confirm (do **not** repoint) that no
verdict frontmatter read survives in the arbiter — its verdict read (`get_arbiter_overrides_for_wp`) is
already event-sourced, and `arbiter.py:461`'s `.latest` reads only `cycle_number` (the override WRITE
path), not a verdict.

## Context

- **Requirement**: FR-016 (arbiter root threaded; coord fail-path). Red-first per the FR.
- **⚠️ Scope correction (squad #1)**: the arbiter's **verdict** read (`get_arbiter_overrides_for_wp`,
  `arbiter.py:481`) is **already event-sourced**; `arbiter.py:461` uses `ReviewCycleArtifact.latest`
  only for `cycle_number` on the override WRITE path (verified live — it never reads `.verdict`).
  Therefore **do NOT repoint `arbiter.py:461` to `event_sourced_review_result`** — doing so loses
  `cycle_number` and writes `review-cycle-0.md`. This WP is **root-threading only** (T036/T037); T038
  is a confirming assertion, not a repoint.
- **Decision**: plan **IC-05** — logic-independent; lands in the same PR as WP05/WP06 (serial writer
  surface).
- Verified anchors: `persist_arbiter_decision` (`arbiter.py:378`); the self-inference
  `main_repo_root = repo_root or feature_dir.parent.parent` (`:451`); `.latest` for `cycle_number`
  (`:461`, KEEP); event-sourced verdict read `get_arbiter_overrides_for_wp` (`:481`).
- **Out-of-map**: the caller `_run_arbiter_override` lives in `tasks_move_task.py` (WP04-owned for the
  vocab sweep). WP07 edits **only** the `_run_arbiter_override` call site there to pass the resolved
  `main_repo_root` — an out-of-map edit, safe because WP04 is strictly upstream (WP07 → WP05 → WP04) so
  no concurrent writer. Keep the edit localized to the call region, away from WP04's vocab region.

## Subtasks

### T036 — Red-first: arbiter override under coord topology resolves the COORD root
- **Purpose**: FR-016 anchor. Under a materialized coordination topology, an arbiter decision must land
  on the resolved COORD root, not `feature_dir.parent.parent` (which is the SINGLE_BRANCH/LANES root).
- **Steps**: In new `tests/review/test_arbiter_coord_root.py`, materialize a coord topology, drive an
  arbiter override, assert the decision + status-lock resolve the COORD root. Red against the current
  self-inference.
- **Files**: `tests/review/test_arbiter_coord_root.py`.
- **Validation**: fails before T037; green after.

### T037 — Thread `main_repo_root` into `persist_arbiter_decision`
- **Purpose**: Retire the self-inference.
- **Steps**: Change `persist_arbiter_decision` (`arbiter.py:378`) to require the caller-resolved
  `main_repo_root` (drop the `or feature_dir.parent.parent` fallback at `:451`). Update the caller
  `_run_arbiter_override` in `tasks_move_task.py` (out-of-map) to pass the resolved root. Keep the
  signature typed; no silent fallback.
- **Files**: `src/specify_cli/review/arbiter.py`; out-of-map `cli/commands/agent/tasks_move_task.py`.
- **Validation**: T036 green; grep confirms no `parent.parent` root inference remains on this path.

### T038 — Assert (do NOT repoint): no verdict frontmatter read survives in the arbiter
- **Purpose**: Squad #1 — the arbiter's verdict read is **already** event-sourced
  (`get_arbiter_overrides_for_wp`). `arbiter.py:461`'s `.latest` reads `cycle_number` only and MUST be
  kept. This subtask *proves* the invariant rather than changing the reader.
- **Steps**: Add an assertion (in `test_arbiter_coord_root.py`) that the arbiter resolves its verdict
  via the event authority and that **no** `review-cycle-*.md` frontmatter **verdict** read exists on the
  arbiter path. Explicitly confirm `.latest`/`.from_file` remain (cycle_number / prose) — do not delete
  or repoint them. If a genuine frontmatter *verdict* read is found, escalate to WP05 (owns the parser
  retirement); do not repoint `:461`.
- **Files**: `tests/review/test_arbiter_coord_root.py`.
- **Validation**: `pytest tests/review/ -k arbiter -q` green; `arbiter.py:461` `.latest` for
  `cycle_number` is intact; no verdict-frontmatter read on the arbiter path.

## Branch Strategy note

`already-confirmed`; base == target. Prepare with `spec-kitty implement WP07`. Depends on WP05 (the
event authority + collapse must be in place first). Same lane/PR as WP05/WP06. The `tasks_move_task.py`
call-site edit is out-of-map (WP04-owned) — localized and strictly downstream.

## Definition of Done

- FR-016: arbiter override under coord topology resolves the COORD root (T036); the self-inference is
  retired (T037); T038 asserts the arbiter's verdict read is already event-sourced and **no** verdict
  frontmatter read survives — **without** repointing `arbiter.py:461` (`.latest`/`cycle_number` kept).
- Gate: `pytest tests/review/ -k arbiter -q` green; `ruff` + `mypy --strict src/specify_cli/review`
  clean (NFR-003).

## Risks

- **Resolved-root availability at the call site** — verify `_run_arbiter_override` already has (or can
  cheaply obtain) the resolved `main_repo_root`; if not, thread it from its caller too (note it).
- **Out-of-map region collision** — keep the `tasks_move_task.py` edit away from WP04's vocab lines.

## Reviewer guidance

Confirm no `feature_dir.parent.parent` root inference survives on the arbiter path. Confirm the
arbiter's **verdict** read is `get_arbiter_overrides_for_wp` (event-sourced) and that `arbiter.py:461`
`.latest`/`cycle_number` is **unchanged** (repointing it is a regression — squad #1). Confirm the
coord-topology test is red-first.
