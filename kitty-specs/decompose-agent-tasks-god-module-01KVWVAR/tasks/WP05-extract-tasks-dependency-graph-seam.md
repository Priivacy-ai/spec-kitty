---
work_package_id: WP05
title: Extract tasks_dependency_graph seam
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
merge_target_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-decompose-agent-tasks-god-module-01KVWVAR. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-decompose-agent-tasks-god-module-01KVWVAR unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 2 - Seam extraction
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2433942"
history:
- at: '2026-06-24T13:22:13Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_dependency_graph.py
create_intent:
- src/specify_cli/cli/commands/agent/tasks_dependency_graph.py
- tests/specify_cli/cli/commands/agent/test_tasks_dependency_readiness.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_dependency_graph.py
- tests/specify_cli/cli/commands/agent/test_tasks_dependency_readiness.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Extract `tasks_dependency_graph` seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` on `authoritative_surface: src/specify_cli/cli/commands/agent/tasks_dependency_graph.py`.

---

## Objective

Extract the **dependent-gating glue** (`_check_dependent_warnings`,
`_behind_commits_touch_only_planning_artifacts`, and the dependent-warning slice of `move_task`) into
`tasks_dependency_graph.py`, and add the readiness-gating tests research flagged as missing
(FR-003, FR-004). Behavior-preserving. Depends on WP02.

## Context

- `research.md §4`: `core/dependency_graph.py` imports only `status.py` (no cycle) — extraction is LOW
  risk. **The two `core/dependency_graph.py` call sites (`tasks.py:1215/1221` in move_task,
  `4603/4604` in validate_workflow) STAY in the shim**; this seam holds the *gating/warning glue*, not
  the graph library itself.
- **Ownership**: own the new files; minimal out-of-map edit to `tasks.py` (move the dependent-warning
  helpers, thin the `move_task` slice that calls them). `tasks.py` owned by WP07.

## Helpers / logic to move (verify current ranges)

`_check_dependent_warnings` (~80 LOC), `_behind_commits_touch_only_planning_artifacts` (~52 LOC), and
the dependent-gating block inside `move_task` (the for_review dependent-warning evidence path, ~50 LOC)
— extract as a function taking explicit inputs (wp_id, feature_dir, graph) so it's testable without the
full `move_task` flow.

## Subtasks

### T018 — Create `tasks_dependency_graph.py`; move helpers
Move the two helpers + extract the `move_task` dependent-gating slice into a pure function. Re-import
`build_dependency_graph`/`get_dependents` from `core.dependency_graph` inside the seam. One-way imports;
keep graceful fallbacks for the subprocess git calls in `_behind_commits_touch_only_planning_artifacts`.

### T019 — Thin the `move_task` dependent-warning slice (out-of-map)
Replace the inline block with a call to the seam function. Behavior identical. Record out-of-map
rationale. (The deeper `move_task` thinning continues in other WPs / WP07 sweep.)

### T020 — Add readiness-gating tests
Create `test_tasks_dependency_readiness.py`. Cover: "WP01 blocked by WP02 in_progress → cannot
transition", dependents surfaced correctly by `get_dependents`, and the planning-artifact-only
behind-commit path. ≥90% on the new module. This fills the research-flagged readiness coverage gap.

### T021 — Prove suites green
`PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ -q -p no:cacheprovider`. Golden green.

## Branch Strategy

- Lanes merge into the mission branch **kitty/mission-decompose-agent-tasks-god-module-01KVWVAR** (PRs to `main` at mission end; `main` is protected). Depends on **WP02**. Worktree per lane.

## Definition of Done

- [ ] `tasks_dependency_graph.py` created; dependent-gating helpers + move_task slice extracted as a pure function.
- [ ] The two `core/dependency_graph.py` call sites remain in the shim (no relocation, no cycle).
- [ ] `move_task` dependent-warning slice thinned via seam call; behavior identical.
- [ ] `test_tasks_dependency_readiness.py` covers readiness gating, ≥90% on the module.
- [ ] Golden contract test green; full `agent/` suite green; ruff + mypy --strict clean.

## Risks

- **Subprocess git calls** — preserve graceful fallback on detached HEAD / missing refs.
- **Don't relocate the graph lib** — only the gating glue moves; the `core/dependency_graph` call sites
  stay in the shim to avoid introducing a cycle.

## Reviewer guidance

Confirm no import cycle introduced, the graph-lib call sites stayed in the shim, readiness-gating tests
are meaningful, and the golden contract test is green.

## Activity Log

- 2026-06-24T15:17:44Z – claude:opus:randy-reducer:implementer – shell_pid=2402385 – Assigned agent via action command
- 2026-06-24T15:32:30Z – claude:opus:randy-reducer:implementer – shell_pid=2402385 – tasks_dependency_graph seam: gating glue + compute_incomplete_dependents extracted, graph-lib calls stay in shim (no cycle), 414 tests green, 97% coverage
- 2026-06-24T15:32:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=2433942 – Started review via action command
- 2026-06-24T15:36:48Z – user – shell_pid=2433942 – Review passed: seam extracted behavior-preserving; helpers moved verbatim (try/except:continue->contextlib.suppress matches global S110-ignore in pyproject; dict type-args tightened, no runtime change); compute_incomplete_dependents pure extraction preserves dependent-warning logic; NO CYCLE - build_dependency_graph/get_dependents stay in tasks.py validate_workflow (lines 51,4292-93); one-way imports (seam never imports tasks.py), __all__ re-exports, no noqa/type-ignore; git subprocess fallbacks (detached HEAD/missing ref->False) preserved exactly; 414 tests + golden contract test_tasks_cli_contract.py green; seam coverage 97% (only uncovered: defensive except fallback line 80-81); readiness tests drive real gating via append_event seeding, not synthetic; scope clean 3 files, no pyproject/uv.lock/stray.
- 2026-06-24T17:14:35Z – user – shell_pid=2433942 – Moved to done
