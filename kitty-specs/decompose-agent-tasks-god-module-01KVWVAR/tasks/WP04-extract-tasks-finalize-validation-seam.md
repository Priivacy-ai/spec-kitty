---
work_package_id: WP04
title: Extract tasks_finalize_validation seam
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
- T014
- T015
- T016
- T017
phase: Phase 2 - Seam extraction
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2384810"
history:
- at: '2026-06-24T13:22:13Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_finalize_validation.py
create_intent:
- src/specify_cli/cli/commands/agent/tasks_finalize_validation.py
- tests/specify_cli/cli/commands/agent/test_tasks_finalize_validation.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_finalize_validation.py
- tests/specify_cli/cli/commands/agent/test_tasks_finalize_validation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Extract `tasks_finalize_validation` seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` on `authoritative_surface: src/specify_cli/cli/commands/agent/tasks_finalize_validation.py`.

---

## Objective

Extract **dependency/cycle validation + lane-metadata helpers + the validation core of
`finalize_tasks`** into `tasks_finalize_validation.py`, thinning the `finalize_tasks` command body
(FR-003, FR-004). Behavior-preserving. Depends on WP02.

## Context

- See `research.md §2`. The `finalize-tasks` command has STRONG existing coverage
  (`test_tasks_canonical_cleanup.py`, ownership-validation tests) — lean on it; preserve the
  "disagree-loud" dependency-conflict detection exactly.
- **Ownership**: own the new files; minimal out-of-map edit to `tasks.py` (extract the validation core
  + lane helpers, leave a thin `finalize_tasks` body that calls the seam). `tasks.py` owned by WP07.

## Helpers / logic to move (verify current ranges)

Lane helpers: `_is_backward_transition`, `_lane_targets_for_emit`, `_wp_lane_from_status_events`,
`_read_transactional_wp_lane`. Plus the **cycle-detection + dependency-frontmatter-write loop** from
inside `finalize_tasks` (~120 LOC) — extract as pure functions taking explicit inputs (tasks.md
content / parsed deps / feature_dir) and returning validation results, so they're testable without the
CLI. Keep `bootstrap_canonical_state` invocation in the thinned command body or a thin wrapper.

## Subtasks

### T014 — Create `tasks_finalize_validation.py`; move helpers + validation core
Move the lane helpers verbatim. Extract the cycle/dependency validation loop from `finalize_tasks`
into named pure functions (e.g. `validate_dependency_graph(...)`, `compute_wp_frontmatter_updates(...)`).
Preserve the disagree-loud conflict semantics. One-way imports.

### T015 — Thin `finalize_tasks` in `tasks.py` (out-of-map)
Replace the extracted inline logic with calls to the seam. The command body becomes: resolve context →
call seam validators → emit/commit/JSON. Keep behavior identical. Record out-of-map rationale.

### T016 — Add unit tests
Create `test_tasks_finalize_validation.py`. Test cycle detection, conflicting-dependency disagree-loud,
valid graphs, and the frontmatter-update computation — directly against the extracted pure functions.
≥90% on the new module.

### T017 — Prove suites green
`PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ -q -p no:cacheprovider`, especially
`test_tasks_canonical_cleanup.py`. Golden contract test green.

## Branch Strategy

- Lanes merge into the mission branch **kitty/mission-decompose-agent-tasks-god-module-01KVWVAR** (PRs to `main` at mission end; `main` is protected). Depends on **WP02**. Worktree per lane.

## Definition of Done

- [ ] `tasks_finalize_validation.py` created; lane helpers + validation core extracted as pure, testable functions.
- [ ] `finalize_tasks` body thinned to orchestration; behavior identical (disagree-loud preserved).
- [ ] `test_tasks_finalize_validation.py` ≥90% on the module; existing finalize tests green.
- [ ] Golden contract test green; full `agent/` suite green; ruff + mypy --strict clean.

## Risks

- **Disagree-loud regression** — the conflict-detection path is subtle; assert it explicitly in tests.
- **Hidden state** — the validation loop may read `feature_dir`/frontmatter; pass these as explicit args
  rather than reaching back into command-local state.
- **bootstrap coupling** — keep `bootstrap_canonical_state` ordering unchanged.

## Reviewer guidance

Verify the extracted validators are pure (explicit inputs/outputs), the thinned `finalize_tasks` is
behavior-identical, disagree-loud is tested, and `test_tasks_canonical_cleanup.py` is untouched & green.

## Activity Log

- 2026-06-24T14:56:52Z – claude:opus:randy-reducer:implementer – shell_pid=2358269 – Assigned agent via action command
- 2026-06-24T15:11:07Z – claude:opus:randy-reducer:implementer – shell_pid=2358269 – tasks_finalize_validation seam: pure validators extracted, disagree-loud preserved byte-for-byte, 430 tests + canonical_cleanup green, 100% coverage
- 2026-06-24T15:11:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=2384810 – Started review via action command
- 2026-06-24T15:17:08Z – user – shell_pid=2384810 – Review passed: behavior-preserving extraction verified. Disagree-loud guard + message byte-identical to original; coverage/cycle/preserve-existing/write-loop semantics and bootstrap_canonical_state ordering all preserved. Validators genuinely pure; compute_wp_frontmatter_updates side-effect-free with writes gated on validate_only in command body. One-way imports (seam never imports tasks.py), __all__ re-exports, no noqa/type:ignore. 100% coverage on new module via real-path tests; 430 agent tests + canonical_cleanup + golden contract green; ruff/mypy --strict clean. WP04 commit touches exactly the 3 intended files; no pyproject/uv.lock/dep changes.
- 2026-06-24T17:14:33Z – user – shell_pid=2384810 – Moved to done
