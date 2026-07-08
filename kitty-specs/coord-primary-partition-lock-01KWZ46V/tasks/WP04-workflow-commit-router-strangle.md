---
work_package_id: WP04
title: workflow.py + commit_router strangle
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
- T016
- T017
- T018
- T019
- T020
- T021
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1696974"
history:
- at: '2026-07-07T20:40:00+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/workflow.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_workflow_placement_routing.py
- tests/specify_cli/coordination/test_commit_router_placement.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/coordination/commit_router.py
- tests/specify_cli/cli/commands/agent/test_workflow_placement_routing.py
- tests/specify_cli/coordination/test_commit_router_placement.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` (implementer) via `/ad-hoc-profile-load`. Read `spec.md`, `plan.md` (IC-03),
`research.md` (D6), `contracts/seam-api.md`. Authoritative over siblings (C-005). Depends on **WP01**.
Implement via `spec-kitty agent action implement WP04 --agent claude`.

## Objective

Route `workflow.py`'s inline `if coord_branch … else target_branch` lifecycle/status write
decisions through the seam via **one** `_resolve_workflow_placement` helper; keep the
`commit_router` write-decision functions ≤15 via extraction; rename the stale
`_planning_commit_worktree`. Red-first (C-006).

## Subtasks

### T016 — Red-first
- Failing test proving `workflow.py:487/503/549/1694` decide placement via an inline topology branch / checkout, not the seam.

### T017 — One placement helper, route the write sites
- Extract a single `_resolve_workflow_placement(kind)` that calls `seam.write_target(kind)`; route the inline `if coord_branch … else target_branch` write decisions through it. Post-rebase these are ~`:502` / `:552` / `:1699` (there are **~3 distinct `CommitTarget(ref=target_branch)` decisions, not the 4 originally cited** — `487/503` double-counted one `safe_commit`); **symbol-anchor the sites, don't trust the line numbers** (#2032 drift). Do NOT inline the seam call per-site (workflow.py is a 2830-line god file — one helper).

### T018 — commit_router extractions (stay ≤15)
- `commit_router.py` is the write-side placement decision point. Extract the placement-resolution logic so `_stage_artifacts_in_coord_worktree` (:376, at 13) and `commit_for_mission` (:98, at 11) stay comfortably ≤15 after any changes. Keep them routing through `artifact_home_for`.

### T019 — Rename stale `_planning_commit_worktree`
- `_planning_commit_worktree` (:475) name lies post-D2 (planning never transits coord). Rename/simplify to reflect its real role. **Keep its PRIMARY-kind guard `raise`** (a real invariant; not an `assert` — survives `python -O`). Do not delete it.

### T020 — Tests + regression
- workflow/status writes land partition-correct via the seam; extracted helpers ≤15; `_planning_commit_worktree` guard preserved; existing commit_router tests green.

### T021 — Campsite (Sonar)
- See table. Fix the genuine empty `except Exception: pass` at `workflow.py:1604`. Promote `commit_router`'s `'no_op_wrong_surface'` placement-outcome literal to a constant/enum (in-band strangle vocabulary).

## Campsite (Sonar issues in owned files)

| File | Rule | Location | Class | Action |
|------|------|----------|-------|--------|
| `commit_router.py` | S3776 | `commit_for_mission` (11), `_stage_artifacts_in_coord_worktree` (13) | SAFE | Extract placement logic; keep ≤15 |
| `commit_router.py` | S1192 | `'no_op_wrong_surface'`/`'unchanged'`/`'error'` | SAFE | Promote outcome literals to a constant/enum |
| `workflow.py` | empty-except | `except Exception: pass` ~l.1608 (dossier-sync, **unjustified**; symbol-anchor — #2032 drift) | SAFE | Narrow the except or add log + rationale comment |
| `workflow.py` | S1192 | `'Error: '` ×17, box-drawing ×9, `'unknown'` ×15, `'utf-8'` ×13 | ADJACENT/OUT | Hoist only literals inside functions you edit; else leave (tracked home = workflow.py decomposition) |

## Branch Strategy

Base / merge target `design/coord-primary-partition-lock`. Worktree per computed lane. Authoritative
(C-005): siblings rebase onto our routing on these shared surfaces.

## Definition of Done

- 4 workflow sites routed via one `_resolve_workflow_placement`; commit_router functions ≤15; `_planning_commit_worktree` renamed with guard preserved.
- The `workflow.py:1604` empty-except is fixed.
- Red-first + regression green; `ruff` + `mypy` clean.

## Risks & Reviewer guidance

- Do NOT inline the seam 4× in workflow.py — one helper (reviewer rejects 4× inline).
- The `_planning_commit_worktree` PRIMARY guard `raise` must remain (deleting it re-opens the split).
- commit_router is the write-side decision point — verify no coord/primary partition change (C-002).

## Activity Log

- 2026-07-07T22:45:17Z – claude:sonnet:python-pedro:implementer – shell_pid=1503078 – Assigned agent via action command
- 2026-07-07T23:17:36Z – claude:sonnet:python-pedro:implementer – shell_pid=1503078 – Ready; one helper not 4x inline; guard preserved; ruff exit 0
- 2026-07-07T23:18:37Z – claude:opus:reviewer-renata:reviewer – shell_pid=1696974 – Started review via action command
- 2026-07-07T23:25:19Z – user – shell_pid=1696974 – Review passed: red-first genuine (12/12 fail pre-fix, pass post-fix); ONE _resolve_workflow_placement helper with a single AST-pinned placement_seam call site routing all 3 write decisions (STATUS_STATE legacy leaf+receipt threaded via placement.ref; baseline WORK_PACKAGE_TASK); modern coord path unchanged (no C-002 partition change); guard preserved verbatim (early return for PRIMARY kinds) + sibling raise untouched + _planning_commit_worktree alias keeps external callers green (16 pass); commit_router funcs C901<=15; empty-except->logger.debug; outcome literals hoisted to Final constants; ruff+mypy clean; 264 coordination + 178 agent-workflow regression green.
