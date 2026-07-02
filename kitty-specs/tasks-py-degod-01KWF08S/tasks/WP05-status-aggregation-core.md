---
work_package_id: WP05
title: status aggregation core (pure)
dependencies:
- WP04
requirement_refs:
- FR-002
- FR-006
- NFR-002
tracker_refs: []
planning_base_branch: design/degod-tasks-2116
merge_target_branch: design/degod-tasks-2116
branch_strategy: Planning artifacts for this mission were generated on design/degod-tasks-2116. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/degod-tasks-2116 unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
phase: Phase 3 - Pure cores
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "3152980"
history:
- at: '2026-07-01T15:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_status_view.py
create_intent:
- src/specify_cli/cli/commands/agent/tasks_status_view.py
- tests/specify_cli/cli/commands/agent/test_tasks_status_view.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_status_view.py
- tests/specify_cli/cli/commands/agent/test_tasks_status_view.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – status aggregation core (pure)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Extract the `status` compute/aggregation into a **pure aggregation core**, separated from rendering; wire by delete-and-sentinel.

- `build_status_view(StatusRequest)->StatusView` in `tasks_status_view.py` — pure; covers stale-fallback, `dependency_readiness`, kanban rollup, progress.
- `--cov-branch` unit tests cover each aggregation branch; fail on reverted extraction.
- Wiring deletes the inline aggregation block; sentinel proves drive; golden byte-identical.

## Context & Constraints

- Read `data-model.md` (§`StatusView`), `contracts/ports-and-cores.md` (`build_status_view`), `research.md` (D7).
- The core absorbs the **compute** (~49 aggregation calls today), not the drawing — rendering is the `Render` port's job (WP07/WP09).
- **Anti-shadow-code**: T024 deletes the inline block; T025 sentinel proves drive.
- **Ownership/leeway**: own the new core + test; the `status` edit is a documented leeway edit to `tasks.py` (owned by WP09); full thinning is WP07.

## Branch Strategy

- **Planning base branch**: `design/degod-tasks-2116`
- **Merge target branch**: `design/degod-tasks-2116`

## Subtasks & Detailed Guidance

### T022 — Failing-first per-branch unit test
`test_tasks_status_view.py` covering stale-verdict fallback, `dependency_readiness`, kanban lane rollup, progress percentages. `--cov-branch`. RED against base.

### T023 — Implement `build_status_view` (pure)
Pure aggregation over injected `events`/`workspaces`/`clock`/`dependency_graph`; no rendering, no I/O.

### T024 — Delete inline block + wire
Delete `status`' inline aggregation block; route through `build_status_view` (rendering stays inline). Golden byte-identical.

### T025 — Sentinel test + green
Fake-core sentinel proves the view drives output; run golden + per-core test; ruff+mypy clean.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_status_view.py tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q --cov-branch`

## Risks & Mitigations

- Pulling rendering into the core couples compute to output — keep `StatusView` a pure data structure.

## Review Guidance

- Confirm purity, branch coverage traced to golden `status` output, deleted inline block, sentinel drive, byte-identical golden.

## Activity Log

- 2026-07-01T15:16:35Z – system – Prompt created.
- 2026-07-01T22:12:04Z – claude:opus:randy-reducer:implementer – shell_pid=3077337 – Assigned agent via action command
- 2026-07-01T22:38:12Z – claude:opus:randy-reducer:implementer – shell_pid=3077337 – build_status_view pure core: 16 branches (--cov-branch 100%), inline aggregation DELETED + wired (both JSON + rich legs) + sentinel drives output; status confirmed read-only (no emit/commit/write side-effects); golden 42 byte-identical, strict mypy clean.
- 2026-07-01T22:39:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=3122415 – Started review via action command
- 2026-07-01T22:47:42Z – user – shell_pid=3122415 – Moved to planned
- 2026-07-01T22:48:27Z – claude:opus:randy-reducer:implementer – shell_pid=3142528 – Started implementation via action command
- 2026-07-01T22:53:25Z – claude:opus:randy-reducer:implementer – shell_pid=3142528 – Cycle 2: test file now strict-mypy clean (checked WITH src, CI-scope) — cast object→StaleCheckResult (2 sites) + list[dict[str,object]] type-arg; core untouched (verbatim dict[str,object] return preserved), 0 suppressions. 63 tests + golden green.
- 2026-07-01T22:53:37Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=3152980 – Started review via action command
- 2026-07-01T22:56:09Z – user – shell_pid=3152980 – Cycle-2 confirm: test strict-mypy clean checked WITH src (2 casts + type-arg), 0 suppressions, core untouched, 21+42 green. Aggregation substance approved prior cycle.
