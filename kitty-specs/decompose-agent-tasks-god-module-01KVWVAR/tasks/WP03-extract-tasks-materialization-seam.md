---
work_package_id: WP03
title: Extract tasks_materialization seam
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
- T010
- T011
- T012
- T013
phase: Phase 2 - Seam extraction
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2346201"
history:
- at: '2026-06-24T13:22:13Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_materialization.py
create_intent:
- src/specify_cli/cli/commands/agent/tasks_materialization.py
- tests/specify_cli/cli/commands/agent/test_tasks_materialization.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_materialization.py
- tests/specify_cli/cli/commands/agent/test_tasks_materialization.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Extract `tasks_materialization` seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` on `authoritative_surface: src/specify_cli/cli/commands/agent/tasks_materialization.py`.

---

## Objective

Extract **frontmatter/file persistence + markdown-row mutation** helpers from `tasks.py` into
`tasks_materialization.py`, with unit tests that include write-failure/error paths (FR-003, FR-004).
Behavior-preserving move. Depends on WP02 (may import outline parsers).

## Context

- See `research.md §2`. WP01 golden test + WP02 outline seam must stay green.
- **Ownership**: own the new files; make a minimal out-of-map edit to `tasks.py` (delete moved block +
  import). `tasks.py` is owned by WP07.
- This seam may import from `tasks_outline` (allowed seam↔seam); never import `tasks.py`.

## Helpers to move (verify current line ranges first)

`_collect_status_artifacts`, `_persist_inline_subtask_status`, `_materialize_inline_subtask_status`,
`_update_pipe_table_status`, `_resolve_checkbox`, `_resolve_pipe_table`, `_persist_review_artifact_override`,
`_persist_review_feedback`, plus the `_INLINE_SUBTASKS_RE` constant. ~185 LOC. Note: `TaskIdResult` /
`TaskIdResolutionOutcome` / `TaskIdResolutionFormat` are returned by some of these — decide whether the
enums/dataclass move here or to a small shared location, and re-export from `tasks.py` if needed.

## Subtasks

### T010 — Create `tasks_materialization.py`; move helpers
Move the listed persistence + markdown-mutation helpers verbatim. Bring needed constants/imports
(`write_text_within_directory`, `task_utils.*`, `Path`, `datetime`). One-way imports only.

### T011 — Wire `tasks.py` (out-of-map, minimal)
Delete moved defs, add the import, add re-exports for any path-imported names (grep `tests/`+`src/`
first). Record the one-line out-of-map rationale.

### T012 — Add unit tests incl. error paths
Create `test_tasks_materialization.py`. Cover checkbox/pipe-table/inline mutation, the
"prioritize status col → parallel → last cell" logic of `_update_pipe_table_status`, and
**error/edge paths**: write failure, invalid YAML, missing file. Target ≥90% on the new module —
research flagged materialization error paths as a coverage gap, so this is where the +80 LOC of new
tests land.

### T013 — Prove suites green
`PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ -q -p no:cacheprovider` — golden + outline +
materialization + existing all green.

## Branch Strategy

- Lanes merge into the mission branch **kitty/mission-decompose-agent-tasks-god-module-01KVWVAR** (PRs to `main` at mission end; `main` is protected). Depends on **WP02** — branch from a base including WP01+WP02. Worktree per lane.

## Definition of Done

- [ ] `tasks_materialization.py` created; helpers moved verbatim; no back-import to `tasks.py`.
- [ ] `tasks.py` wired via import; moved block deleted; re-exports where needed.
- [ ] `test_tasks_materialization.py` covers mutation + error paths, ≥90% on the module.
- [ ] Golden contract test still green; full `agent/` suite green; ruff + mypy --strict clean.

## Risks

- **Markdown regex brittleness** — cover all three row formats and the column-priority logic.
- **Enum/dataclass placement** — if `TaskIdResult` moves, `mark_status` in `tasks.py` must still import
  it; re-export to avoid breaking the contract.
- **File I/O** — preserve existing `write_text_within_directory(root=...)` safety; don't change write
  semantics.

## Reviewer guidance

Confirm move is behavior-preserving, error-path tests are meaningful (not just happy-path), enum/dataclass
re-exports keep `mark_status` working, and the golden contract test is green.

## Activity Log

- 2026-06-24T14:29:58Z – claude:opus:randy-reducer:implementer – shell_pid=2293557 – Assigned agent via action command
- 2026-06-24T14:42:42Z – claude:opus:randy-reducer:implementer – shell_pid=2293557 – tasks_materialization seam extracted (behavior-preserving); full agent suite green; error-path tests added; ≥90% coverage
- 2026-06-24T14:43:21Z – claude:opus:reviewer-renata:reviewer – shell_pid=2323554 – Started review via action command
- 2026-06-24T14:48:36Z – user – shell_pid=2323554 – Moved to planned
- 2026-06-24T14:49:38Z – claude:opus:randy-reducer:implementer – shell_pid=2338943 – Started implementation via action command
- 2026-06-24T14:53:34Z – claude:opus:randy-reducer:implementer – shell_pid=2338943 – Cycle-1 fix: stray '-' file removed; net kitty-specs tree matches mission (benign lane status-commit pollution, --force); code diff unchanged from approved cycle-1 review
- 2026-06-24T14:53:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=2346201 – Started review via action command
- 2026-06-24T14:56:05Z – user – shell_pid=2346201 – Cycle 2 approved: stray '-' file confirmed absent from HEAD tree; materialization seam code unchanged from cycle-1 validated review; full agent suite green (435 passed/2 xfailed); one-way imports verified (no back-import to tasks.py, only tasks_outline seam). --force used per orchestrator-confirmed benign kitty-specs status-commit pollution (net tree matches mission branch, merge-safe per WP03 prompt note 4); not a WP03 code defect.
- 2026-06-24T17:14:49Z – user – shell_pid=2346201 – Superseded rejection artifact (cycle re-approved); mission merged into mission branch with all lanes integrated, 515 tests green
