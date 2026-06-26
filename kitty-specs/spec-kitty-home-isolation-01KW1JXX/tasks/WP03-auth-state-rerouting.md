---
work_package_id: WP03
title: Auth state rerouting
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: fix/spec-kitty-home-isolation
merge_target_branch: fix/spec-kitty-home-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/spec-kitty-home-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spec-kitty-home-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 2 - Reroute
assignee: ''
agent: claude
shell_pid: '37267'
history:
- at: '2026-06-26T11:06:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/auth/
create_intent:
- tests/auth/test_spec_kitty_home_paths.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/auth/secure_storage/file_fallback.py
- src/specify_cli/auth/secure_storage/windows_storage.py
- src/specify_cli/auth/token_manager.py
- tests/auth/test_secure_storage_file.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Auth state rerouting

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

Route the encrypted **auth** session store (POSIX + Windows) and the token refresh lock through `get_runtime_root()`. Covers FR-002 (session storage), FR-003 (refresh lock), NFR-005 (no secrets outside the resolved root).

- **DONE when**: with `SPEC_KITTY_HOME` set, the auth store dir and `refresh.lock` resolve under it on POSIX and Windows; with it unset, POSIX equals `~/.spec-kitty/auth/...`.

## Context & Constraints

- Depends on **WP01**. Import `from specify_cli.paths import get_runtime_root`.
- **Windows normalization decision** `DM-01KW1KDHVGWZ0QERDMV1CRJ15S` (research.md D4): `windows_storage.py` currently hardcodes `Path.home()/.spec-kitty/auth` even on Windows — normalize it to `get_runtime_root().auth_dir` (platformdirs base when unset). This **changes the unset-Windows path**; check for tests that pin the old value and update them, recording the rationale.
- `.venv` is warm — use `.venv/bin/...`.

### Current call sites (verified)

| File:line | Today | Target |
|-----------|-------|--------|
| `auth/secure_storage/file_fallback.py:36` `default_store_dir()` | `Path.home() / ".spec-kitty" / "auth"` | `get_runtime_root().base / "auth"` (== `auth_dir`) |
| `auth/secure_storage/windows_storage.py:15` | `Path.home() / ".spec-kitty" / "auth"` | `get_runtime_root().auth_dir` |
| `auth/token_manager.py:85` `_refresh_lock_path()` (POSIX) | `Path.home() / ".spec-kitty" / "auth" / "refresh.lock"` | `get_runtime_root().base / "auth" / "refresh.lock"` |

> The Windows branch of `_refresh_lock_path()` already uses `get_runtime_root().auth_dir / "refresh.lock"` — now env-aware via WP01; leave it.

## Branch Strategy

- **Strategy**: shared-feature-branch
- **Planning base branch**: fix/spec-kitty-home-isolation
- **Merge target branch**: fix/spec-kitty-home-isolation

## Subtasks & Detailed Guidance

### Subtask T011 – Reroute POSIX auth store

- **Steps**: In `file_fallback.py`, change `default_store_dir()` to `return get_runtime_root().base / "auth"` (equivalently `.auth_dir`). Keep the `auth` suffix.
- **Files**: `src/specify_cli/auth/secure_storage/file_fallback.py`

### Subtask T012 – Normalize Windows auth store

- **Steps**: In `windows_storage.py` `WindowsFileStorage.__init__`, replace the hardcoded `store_path = Path.home() / ".spec-kitty" / "auth"` default with `store_path = get_runtime_root().auth_dir`. This makes Windows consistent with the platformdirs base and honors `SPEC_KITTY_HOME`.
- **Files**: `src/specify_cli/auth/secure_storage/windows_storage.py`
- **Notes**: Document the normalization in the Activity Log; WP06 records it in CHANGELOG.

### Subtask T013 – Reroute refresh lock (POSIX)

- **Steps**: In `token_manager.py`, change the POSIX branch of `_refresh_lock_path()` to `return get_runtime_root().base / "auth" / "refresh.lock"`. Leave the Windows branch.
- **Files**: `src/specify_cli/auth/token_manager.py`

### Subtask T014 [P] – Auth tests

- **Steps**: Add `tests/auth/test_spec_kitty_home_paths.py` asserting (env set vs unset, monkeypatched HOME):
  - `file_fallback.default_store_dir()` under env root.
  - `_refresh_lock_path()` under env root (POSIX; and Windows-branch behavior via platform monkeypatch).
  - `WindowsFileStorage` default under env root (platform monkeypatched to win32).
  - Update `tests/auth/test_secure_storage_file.py` only where the reroute changed an asserted path; keep it green.
- **Files**: `tests/auth/*`
- **Parallel?**: Yes.

## Test Strategy

- `.venv/bin/pytest tests/auth/ -q`
- `.venv/bin/ruff check src/specify_cli/auth tests/auth` and `.venv/bin/mypy src/specify_cli/auth`

## Risks & Mitigations

- **Secret safety (NFR-005)**: ensure no auth material is written outside the resolved root; the reroute is the only path change.
- **Windows test pinning**: grep `grep -rn "spec-kitty/auth\|spec-kitty\", \"auth" tests/auth` and update pinned assertions to the normalized path.

## Review Guidance

- Confirm POSIX `auth` + `refresh.lock` suffixes preserved.
- Confirm Windows storage now uses `auth_dir` (not hardcoded `Path.home()`).
- Confirm no credential leakage outside the root.

## Activity Log

- 2026-06-26T11:06:32Z – system – Prompt created.

### Updating Status

Use `spec-kitty agent tasks move-task WP03 --to <status>`.
