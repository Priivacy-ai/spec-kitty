---
work_package_id: WP06
title: End-to-end CLI proof + create-window + traversal
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: feat/read-side-surface-resolver-adoption
merge_target_branch: feat/read-side-surface-resolver-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/read-side-surface-resolver-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-side-surface-resolver-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2435348"
history:
- at: '2026-06-20T14:30:00Z'
  actor: claude
  note: WP authored from plan IC-06 (SC-002/SC-005/FR-004). The CLI-level proof the matrix cannot give.
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_read_cli_surface_adoption.py
- tests/mission_runtime/test_read_path_create_window_invariant.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- tests/specify_cli/cli/commands/test_read_cli_surface_adoption.py
- tests/mission_runtime/test_read_path_create_window_invariant.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Add the **CLI-level end-to-end proof the equivalence matrix CANNOT give** (it tests resolver primitives, never a read CLI), plus the create-window invariant and traversal-rejection. (IC-06; SC-002, SC-005, FR-004)

## Context (squad-mandated — the matrix is not enough)
- The 01KVGCE8 matrix only exercises `resolve_mission_read_path`/`resolve_status_surface_with_anchor`/`MissionStatus.load` — NO read CLI. So flipping the `*/bare` cells (WP04) proves the PRIMITIVE derives mid8, NOT that any CLI routes through the seam. This WP is the missing end-to-end proof.

## Subtasks
### T022 — Per-CLI bare-slug coord e2e (SC-002)
- `tests/specify_cli/cli/commands/test_read_cli_surface_adoption.py`: build a **coord-fresh** mission (real `.worktrees/<slug>-<mid8>-coord/` layout, 26-char ULID). Drive **`agent tasks status`** (the spec's primary-scenario exemplar + the F7 `tasks.py:4047` flagship), `agent context`, `agent mission`, `decision`, `acceptance` with the **BARE slug**; assert each resolved on-disk dir equals the **coordination-worktree** dir (NOT the primary checkout). Also assert `<slug>-<mid8>` resolves the same (no regression). **`agent tasks status` is mandatory here** — it is the headline residual whose fix is otherwise CLI-unproven (the matrix tests primitives, never a CLI).
### T023 — Create-window invariant (SC-005, #1718)
- `tests/mission_runtime/test_read_path_create_window_invariant.py`: a coordination_branch-DECLARED-but-UNMATERIALIZED mission + bare slug → read resolves PRIMARY (even though mid8 is derived non-empty). Mutation: make the seam route a declared-unmaterialized coord through `resolve_status_surface_with_anchor` → this test FAILS (the #1718 guard).
### T024 — Traversal-rejection + no-regression (FR-004, NFR-002)
- Traversal handle (`"../etc"`, `"a/b"`) through a read CLI / the seam → rejected at `assert_safe_path_segment` (raises, no path composed). No-regression: a quick sweep of the touched read-CLI suites stays green.

## Branch Strategy
Planning/base + merge target: `feat/read-side-surface-resolver-adoption`. Worktree per lane. Depends **WP01 + WP02 + WP03** (the seam + the migrations).

## Definition of Done
- [ ] Per-CLI bare-slug × coord-fresh → COORD dir (NOT primary) for **tasks status**/context/mission/decision/acceptance; `<slug>-<mid8>` unchanged.
- [ ] Create-window invariant: declared-unmaterialized coord + bare slug → PRIMARY; mutation (route via surface) FAILS the test.
- [ ] Traversal handle rejected (FR-004).
- [ ] ruff + mypy --strict clean; the new modules + touched suites green.

## Risks / Reviewer guidance
- **Risk**: a born-green e2e test (passing without the seam). Construct it so it would FAIL on the pre-adoption tree (read primary) — confirm it asserts the COORD dir specifically.
- **Reviewer**: confirm the e2e asserts the coord-worktree dir (not just "a dir"); confirm the create-window mutation genuinely bites; realistic fixtures (ULID, real coord layout).

## Activity Log

- 2026-06-20T17:03:21Z – claude:opus:python-pedro:implementer – shell_pid=2403664 – Assigned agent via action command
- 2026-06-20T17:28:40Z – claude:opus:python-pedro:implementer – shell_pid=2403664 – per-CLI bare-slug coord e2e (tasks status/context/mission/decision/acceptance → coord dir); create-window→primary; traversal rejected; 21 passed; lane 2b101b828
- 2026-06-20T17:28:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=2435348 – Started review via action command
- 2026-06-20T17:48:40Z – user – shell_pid=2435348 – reviewer-renata APPROVE: genuine anti-born-green e2e (tasks status/context/mission would-fail-on-base verified), create-window bites, traversal rejects, 21 passed
