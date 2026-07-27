---
work_package_id: WP04
title: Tracker state rerouting
dependencies:
- WP01
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: fix/spec-kitty-home-isolation
merge_target_branch: fix/spec-kitty-home-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/spec-kitty-home-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spec-kitty-home-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
phase: Phase 2 - Reroute
assignee: ''
agent: claude
shell_pid: '37267'
history:
- at: '2026-06-26T11:06:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tracker/
create_intent:
- tests/tracker/test_spec_kitty_home_paths.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/tracker/credentials.py
- src/specify_cli/tracker/store.py
- tests/tracker/test_credentials_windows_paths.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Tracker state rerouting

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

Route **tracker** credentials and the tracker DB through `get_runtime_root().base` (single-root decision C-003), preserving POSIX flat suffixes. Covers FR-008.

- **DONE when**: with `SPEC_KITTY_HOME` set, tracker credentials and the tracker DB resolve under it; with it unset, POSIX equals `~/.spec-kitty/credentials` and `~/.spec-kitty/trackers/...`.

## Context & Constraints

- Depends on **WP01**. Import `from specify_cli.paths import get_runtime_root`.
- **CRITICAL — POSIX flat layout** (research.md D3): POSIX tracker creds root = `base` (then `credentials`), which is **not** `RuntimeRoot.tracker_dir` (`base/tracker`). Keep the flat POSIX suffix to satisfy NFR-001. The Windows branch already uses `get_runtime_root().tracker_dir` — now env-aware; leave it.
- `.venv` is warm — use `.venv/bin/...`.

### Current call sites (verified)

| File:line | Today | Target |
|-----------|-------|--------|
| `tracker/credentials.py:39` `_tracker_root()` (POSIX) | `Path.home() / ".spec-kitty"` | `get_runtime_root().base` |
| `tracker/store.py:14` `_spec_kitty_dir()` | `Path.home() / ".spec-kitty"` | `get_runtime_root().base` |
| `tracker/store.py:18` `_trackers_dir()` | `_spec_kitty_dir() / "trackers"` | unchanged (now env-aware via the above) |

## Branch Strategy

- **Strategy**: shared-feature-branch
- **Planning base branch**: fix/spec-kitty-home-isolation
- **Merge target branch**: fix/spec-kitty-home-isolation

## Subtasks & Detailed Guidance

### Subtask T015 – Reroute tracker credentials (POSIX)

- **Steps**: In `tracker/credentials.py`, change the POSIX branch of `_tracker_root()` to `return get_runtime_root().base`. Keep the existing Windows branch (`get_runtime_root().tracker_dir`). Downstream `credentials` suffix is unchanged.
- **Files**: `src/specify_cli/tracker/credentials.py`

### Subtask T016 – Reroute tracker store

- **Steps**: In `tracker/store.py`, change `_spec_kitty_dir()` to `return get_runtime_root().base`. `_trackers_dir()` (= `base/trackers`) and `default_tracker_db_path()` follow automatically. Keep `trackers` suffix.
- **Files**: `src/specify_cli/tracker/store.py`

### Subtask T017 [P] – Tracker tests

- **Steps**: Add `tests/tracker/test_spec_kitty_home_paths.py` asserting (env set vs unset, monkeypatched HOME + platform):
  - `_tracker_root()` (POSIX flat → `base`; Windows → `tracker_dir`) under env root.
  - `default_tracker_db_path(<scope>)` under env root → `base/trackers/<scope>.db`.
  - unset POSIX equals `~/.spec-kitty/credentials` and `~/.spec-kitty/trackers/...`.
  - Update `tests/tracker/test_credentials_windows_paths.py` only where the reroute changed an asserted path; keep green.
- **Files**: `tests/tracker/*`
- **Parallel?**: Yes.

## Test Strategy

- `.venv/bin/pytest tests/tracker/ -q`
- `.venv/bin/ruff check src/specify_cli/tracker tests/tracker` and `.venv/bin/mypy src/specify_cli/tracker`

## Risks & Mitigations

- POSIX flat vs Windows nested divergence → keep flat POSIX suffix (`credentials`), Windows `tracker_dir`. Do not unify.

## Review Guidance

- Confirm POSIX flat suffix preserved and Windows branch left delegating to `tracker_dir`.
- Confirm DB path = `base/trackers/<scope>.db`.

## Activity Log

- 2026-06-26T11:06:32Z – system – Prompt created.

### Updating Status

Use `spec-kitty agent tasks move-task WP04 --to <status>`.
