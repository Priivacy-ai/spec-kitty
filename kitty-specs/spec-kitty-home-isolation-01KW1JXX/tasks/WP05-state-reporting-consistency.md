---
work_package_id: WP05
title: State reporting consistency (doctor + contract)
dependencies:
- WP01
requirement_refs:
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: fix/spec-kitty-home-isolation
merge_target_branch: fix/spec-kitty-home-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/spec-kitty-home-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spec-kitty-home-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
phase: Phase 2 - Reroute
assignee: ''
agent: claude
shell_pid: '37267'
history:
- at: '2026-06-26T11:06:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/state/
create_intent:
- tests/state/test_doctor_spec_kitty_home.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/state/doctor.py
- src/specify_cli/state/contract.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – State reporting consistency (doctor + contract)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

Make `state doctor` resolve/report the **same** global-sync root the runtime actually uses, and ensure `StateRoot.GLOBAL_SYNC` resolution reflects the authoritative base. Covers FR-009, FR-010.

- **DONE when**: under `SPEC_KITTY_HOME` set or unset, `state doctor`'s reported global-sync root equals `get_runtime_root().base` (SC-004).

## Context & Constraints

- Depends on **WP01**. Import `from specify_cli.paths import get_runtime_root`.
- `state/contract.py` `STATE_SURFACES` are **declarative relative patterns** (e.g. `config.toml`, `credentials`, `clock.json`, `queues/queue-<hash>.db`, `trackers/<scope>.db`) — keep them as the single source of relative patterns. The **absolute** resolution happens in `state/doctor.py` and is what must adopt `get_runtime_root().base`.
- `.venv` is warm — use `.venv/bin/...`.

### Current call sites (verified)

| File:line | Today | Target |
|-----------|-------|--------|
| `state/doctor.py:141` | `Path.home() / ".spec-kitty" / surface.path_pattern` | `get_runtime_root().base / surface.path_pattern` |
| `state/doctor.py:253` `global_sync` | `Path.home() / ".spec-kitty"` | `get_runtime_root().base` |
| `state/contract.py:23` `StateRoot.GLOBAL_SYNC` | enum (comment says `~/.spec-kitty/`) | keep enum; ensure any resolver uses the authoritative base |

## Branch Strategy

- **Strategy**: shared-feature-branch
- **Planning base branch**: fix/spec-kitty-home-isolation
- **Merge target branch**: fix/spec-kitty-home-isolation

## Subtasks & Detailed Guidance

### Subtask T018 – Reroute doctor global-sync resolution

- **Steps**: In `state/doctor.py`, replace both `Path.home() / ".spec-kitty"` occurrences (lines ~141 and ~253) with `get_runtime_root().base`. The per-surface join (`/ surface.path_pattern`) stays the same.
- **Files**: `src/specify_cli/state/doctor.py`

### Subtask T019 – Contract resolution consistency

- **Steps**: Inspect `state/contract.py` for any place that materializes an absolute GLOBAL_SYNC path or a hardcoded `~/.spec-kitty`. If resolution lives only in `doctor.py`, update the `StateRoot.GLOBAL_SYNC` comment to reference the authoritative root and add a short docstring/comment noting that resolution is via `get_runtime_root().base`. Do not change the relative surface patterns.
- **Files**: `src/specify_cli/state/contract.py`

### Subtask T020 [P] – Doctor tests

- **Steps**: Add `tests/state/test_doctor_spec_kitty_home.py` asserting that the doctor's reported/used global-sync root equals `get_runtime_root().base` under env set vs unset (monkeypatched HOME). Prefer testing the resolution helper directly; if doctor only exposes results via a report, assert the reported root path.
- **Files**: `tests/state/test_doctor_spec_kitty_home.py`
- **Parallel?**: Yes.

## Test Strategy

- `.venv/bin/pytest tests/state/ -q`
- `.venv/bin/ruff check src/specify_cli/state tests/state` and `.venv/bin/mypy src/specify_cli/state`

## Risks & Mitigations

- Keep `STATE_SURFACES` as the single source of relative patterns; change only absolute resolution.
- If `contract.py` exposes a resolver used elsewhere, route it through `get_runtime_root().base` too (grep `grep -rn "GLOBAL_SYNC" src`).

## Review Guidance

- Confirm both doctor occurrences rerouted and the reported root matches `get_runtime_root().base`.
- Confirm surface patterns unchanged.

## Activity Log

- 2026-06-26T11:06:32Z – system – Prompt created.

### Updating Status

Use `spec-kitty agent tasks move-task WP05 --to <status>`.
