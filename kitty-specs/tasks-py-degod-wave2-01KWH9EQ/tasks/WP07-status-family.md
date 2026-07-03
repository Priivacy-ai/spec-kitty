---
work_package_id: WP07
title: status family relocation
dependencies:
- WP06
requirement_refs:
- FR-001
- FR-012
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
phase: Phase 3 - Family relocations
assignee: ''
agent: claude
history:
- at: '2026-07-02T12:53:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – status family relocation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Relocate the status family — `_do_status` (tasks.py:4431 region) + 14 `_st_*` glue +
`_StatusState` + `_default_status_ports` — VERBATIM into NEW
`src/specify_cli/cli/commands/agent/tasks_status_cmd.py` (named `_cmd` to avoid clashing
with the existing `tasks_status_view.py` pure core); thin the wrapper; re-point the
`status` ratchet entry (FR-012).

By this point WP04 has already deleted `_StatusRender` — `_default_status_ports`
constructs `RealRender(console=console, indent=2)`; it moves as-is. The status byte case
(indent=2) is the acceptance tripwire.

**Shared-surface note**: edits `tasks.py`, the coord-harness ratchet block, and the
gate-file ceiling — sequential shared surfaces.

## Context & Constraints

- WP05/WP06 Activity Logs — the proven family-move recipe; copy it.
- `research.md` D2/D3 (status leg), D7 (seam symbols this family calls — `console` ×5 is
  patched: keep the module `console` binding in `tasks.py` and route via `_tasks.console`
  where the moved code references it).
- The `status` command's `--json` leg emits via `print(ports.render.json_envelope(result))`
  — that call moves verbatim inside `_do_status`.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T031 – Create `tasks_status_cmd.py`

- **Steps**: Cut VERBATIM (`grep -nE '^def _st_|class _StatusState|def _default_status_ports|def _do_status' tasks.py`); seam-bridge routing for D7 symbols (`_tasks.console`, `_tasks.locate_project_root`, shared helpers, …); no module-level `tasks` import; module named `tasks_status_cmd.py` (docstring notes the `_view` core distinction).
- **Files**: new module (~450–600 lines), `tasks.py` deletions.

### Subtask T032 – Thin the wrapper + bindings

- **Steps**: `status` `@app.command` wrapper → thin delegate (typer signature frozen by help fixtures); `tasks.py` binds back moved symbols tests touch (`grep -rn "tasks\._st_\|_StatusState\|_default_status_ports" tests/`).

### Subtask T033 – Ratchet re-point: status

- **Steps**: Update the WP05-built `{floored_name: (module, qualname)}` map:
  `"status": (tasks_status_cmd, "_do_status")` — and ADD the new module to the coverage
  session's `include=[...]` set. Floors unchanged; the vacuous-fallback removal (WP05)
  stays: a 0-arc floored function hard-fails. **Acceptance evidence**: a demonstrated
  RED fire of the re-pointed entry (paste failing output, restore) — not a recorded
  percentage.
- **Files**: `test_tasks_cli_contract_coord.py` (ratchet block only — WP05's diff-scope rule applies).

### Subtask T034 – Parity guard + ceiling ratchet

- **Steps**: Full parity guard — the indent=2 status byte case is the headline check; targeted surface; `_CEILING` lowered same-commit; mypy strict src+tests together; ruff; seam-checklist rows appended to the committed `seam-checklist.md` with is-identity tests for every moved patched symbol.

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py -q  # ratchet touched
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/tasks/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_tasks_command_surface.py -q
python -m mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_status_cmd.py <touched tests>
```

## Risks & Mitigations

- **Indent-leg byte drift** → the WP01 status byte case; run per subtask.
- **Name confusion with `tasks_status_view.py`** → `_cmd` suffix + docstrings; imports reviewed.
- **`console` patch seam** (×5): binding + `_tasks.console` routing — spot-check one patching test.

## Review Guidance

- Verbatim-move diff; wrapper thin; ratchet floors unchanged, target re-pointed.
- Status byte case green with fixtures unmodified.
- No stray references to the deleted `_StatusRender` reintroduced.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
