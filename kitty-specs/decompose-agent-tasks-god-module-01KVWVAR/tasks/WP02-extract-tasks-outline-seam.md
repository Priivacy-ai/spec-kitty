---
work_package_id: WP02
title: Extract tasks_outline seam
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
merge_target_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-decompose-agent-tasks-god-module-01KVWVAR. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-decompose-agent-tasks-god-module-01KVWVAR unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 2 - Seam extraction
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2273815"
history:
- at: '2026-06-24T13:22:13Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_outline.py
create_intent:
- src/specify_cli/cli/commands/agent/tasks_outline.py
- tests/specify_cli/cli/commands/agent/test_tasks_outline.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_outline.py
- tests/specify_cli/cli/commands/agent/test_tasks_outline.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Extract `tasks_outline` seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` on `authoritative_surface: src/specify_cli/cli/commands/agent/tasks_outline.py`.

---

## Objective

Extract the tasks.md / manifest **parsing and WP-id resolution** helpers out of `tasks.py` into a new,
independently-importable module `tasks_outline.py`, with isolated unit tests (FR-003, FR-004). This is
a **behavior-preserving move** — no logic changes. First seam; sets the pattern for WP03–06.

## Context

- Source: `src/specify_cli/cli/commands/agent/tasks.py` (4633 LOC). See
  `kitty-specs/decompose-agent-tasks-god-module-01KVWVAR/research.md §2` for the seam map.
- WP01 created `test_tasks_cli_contract.py` — it MUST stay green throughout this WP.
- **Ownership note**: you own the new files only. You will make a *small, justified out-of-map edit*
  to `tasks.py` (delete the moved block, add an import) — `tasks.py` is formally owned by WP07, which
  runs after you. Keep your `tasks.py` edit minimal: move code + wire the import, nothing else.

## Helpers to move (from research §2 — verify exact current line ranges before moving)

`_normalize_task_id_input`, `_match_history_wp_heading`, `_extract_pipe_table_wp_id`,
`_resolve_history_wp_id`, `_is_pipe_table_task_row`, `_parse_pipe_table_header`, `_wp_id_exists`,
`_resolve_wp_id`, plus the WP/inline regex constants they use (`_WP_HEADING_RE`, `_WP_ID_TITLE_RE`,
`_QUALIFIED_TASK_ID_RE` if outline-local). ~180 LOC total.

## Subtasks

### T006 — Create `tasks_outline.py` and move the helpers
Create `src/specify_cli/cli/commands/agent/tasks_outline.py`. Move the listed helpers verbatim
(behavior-preserving). Bring along only the constants/imports they need. Keep function names and
signatures identical so call sites change by import only. **One-way imports**: `tasks_outline` must
NOT import from `tasks.py` (INV-2).

### T007 — Wire `tasks.py` to the seam (out-of-map, minimal)
In `tasks.py`, delete the moved definitions and add `from specify_cli.cli.commands.agent.tasks_outline import (...)`.
If any external test or module imports these names from `tasks.py` by path, add a re-export so paths
keep working (check with a quick grep across `tests/` and `src/`). Record the one-line rationale for
the out-of-map `tasks.py` edit in your WP history.

### T008 — Add isolated unit tests
Create `tests/specify_cli/cli/commands/agent/test_tasks_outline.py`. Test each moved parser directly
(checkbox rows, pipe-table headers, WP-id resolution from headings/pipe-tables, qualified→bare id
normalization, edge cases like code-block lines that must be ignored). Target ≥90% coverage on the
new module (NFR-002).

### T009 — Prove suites green
Run the golden contract test, the new seam test, and the existing tasks suite:
`PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ -q -p no:cacheprovider`. All green.

## Branch Strategy

- Base/merge branch: the mission branch **kitty/mission-decompose-agent-tasks-god-module-01KVWVAR** (lanes merge here; PRs to `main` at mission end, since `main` is protected).
- Depends on **WP01** — branch from the base that includes WP01's golden tests.
- Worktree allocated per `lanes.json` lane during implement.

## Definition of Done

- [ ] `tasks_outline.py` exists; listed helpers moved verbatim; no import back into `tasks.py`.
- [ ] `tasks.py` imports from the seam; moved block deleted; re-exports added if needed.
- [ ] `test_tasks_outline.py` covers each parser directly, ≥90% on the new module.
- [ ] Golden CLI contract test (WP01) still green — byte-identical surface.
- [ ] Full `agent/` suite green; `ruff` + `mypy --strict` clean; no new suppressions.

## Risks

- **Hidden coupling**: a moved helper may reference a `tasks.py`-local constant — move or import it too.
- **Path-import breakage**: tests importing `from ...tasks import _resolve_wp_id` will break unless
  re-exported. Grep first.
- **Scope creep**: do NOT also thin `move_task`/`status` here — just move the outline helpers.

## Reviewer guidance

Verify the move is behavior-preserving (diff should be move + import, no logic edits), one-way imports
hold, the golden contract test is untouched and green, and the new tests exercise the parsers directly
rather than through the CLI.

## Activity Log

- 2026-06-24T14:07:08Z – claude:opus:randy-reducer:implementer – shell_pid=2244127 – Assigned agent via action command
- 2026-06-24T14:21:36Z – claude:opus:randy-reducer:implementer – shell_pid=2244127 – tasks_outline seam extracted (behavior-preserving move); full agent suite + golden contract green; 100% coverage on new module
- 2026-06-24T14:22:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=2273815 – Started review via action command
- 2026-06-24T14:28:33Z – user – shell_pid=2273815 – Review passed: behavior-preserving move verified (char-identical modulo documented str() coercions on untyped RE2 groups); one-way imports hold (tasks_outline imports no tasks.py); re-exports cover all external path-importers; agent/ suite 398 passed + golden contract green; 100% coverage on tasks_outline.py (50 direct parser tests); ruff + mypy --strict clean; scope clean (3 files, no pyproject/uv.lock, no new prod suppressions). _wp_id_exists dead code is pre-existing (dead on base too), preserved verbatim as specified.
- 2026-06-24T17:14:29Z – user – shell_pid=2273815 – Moved to done
