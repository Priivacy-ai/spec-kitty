---
work_package_id: WP02
title: Sync state rerouting
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-004
- FR-005
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: fix/spec-kitty-home-isolation
merge_target_branch: fix/spec-kitty-home-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/spec-kitty-home-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spec-kitty-home-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - Reroute
assignee: ''
agent: claude
shell_pid: '35375'
history:
- at: '2026-06-26T11:06:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/sync/test_spec_kitty_home_paths.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/config.py
- src/specify_cli/sync/queue.py
- src/specify_cli/sync/daemon.py
- src/specify_cli/sync/clock.py
- tests/sync/test_offline_queue.py
- tests/sync/test_config_background_daemon.py
- tests/sync/test_daemon_owner_record.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Sync state rerouting

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

Route all **sync** global state through `get_runtime_root().base`, **preserving each POSIX suffix** so unset behavior is byte-identical (NFR-001). Covers FR-001 (config), FR-004/FR-005 (queues + active scope), FR-006 (daemon), FR-007 (clock).

- **DONE when**: with `SPEC_KITTY_HOME` set, sync config, queue DBs (auth + unauth), active queue scope, daemon state/log/lock, and the Lamport clock all resolve under it; with it unset, POSIX paths equal today's `~/.spec-kitty/...` exactly.

## Context & Constraints

- Depends on **WP01** (`get_runtime_root()` now honors `SPEC_KITTY_HOME`). Import via `from specify_cli.paths import get_runtime_root`.
- **CRITICAL — preserve POSIX flat layout** (research.md D3). Do NOT swap to `RuntimeRoot.daemon_dir`/etc. on POSIX:
  - daemon root = `base` (flat), NOT `base/daemon`.
  - `_sync_root` POSIX = `base / "sync"` (this equals `sync_dir`).
- The `.venv` is already warm — use `.venv/bin/...` directly.

### Current call sites (verified)

| File:line | Today | Target |
|-----------|-------|--------|
| `sync/config.py:31` | `Path.home() / '.spec-kitty'` | `get_runtime_root().base` |
| `sync/queue.py:362` `_spec_kitty_dir()` | `Path.home() / ".spec-kitty"` | `get_runtime_root().base` |
| `sync/daemon.py:75` `_sync_root` (POSIX) | `Path.home() / ".spec-kitty" / "sync"` | `get_runtime_root().base / "sync"` |
| `sync/daemon.py:89` `_daemon_root` (POSIX) | `Path.home() / ".spec-kitty"` | `get_runtime_root().base` |
| `sync/daemon.py:94` `SPEC_KITTY_DIR` constant | `Path.home() / ".spec-kitty"` | lazy function returning `get_runtime_root().base` |
| `sync/clock.py:37,80` | `Path.home() / ".spec-kitty" / "clock.json"` | `get_runtime_root().base / "clock.json"` |

## Branch Strategy

- **Strategy**: shared-feature-branch
- **Planning base branch**: fix/spec-kitty-home-isolation
- **Merge target branch**: fix/spec-kitty-home-isolation

## Subtasks & Detailed Guidance

### Subtask T006 – Reroute SyncConfig

- **Steps**: In `sync/config.py` `SyncConfig.__init__`, set `self.config_dir = get_runtime_root().base` and keep `self.config_file = self.config_dir / 'config.toml'`. Resolve lazily in `__init__` (called per instance), not at import.
- **Files**: `src/specify_cli/sync/config.py`

### Subtask T007 – Reroute queue _spec_kitty_dir()

- **Steps**: In `sync/queue.py`, change `_spec_kitty_dir()` to `return get_runtime_root().base`. Verify all consumers keep their suffixes: `_credentials_path` → `base/credentials`, `_auth_session_store_dir` → `base/auth`, `_legacy_queue_db_path` → `base/queue.db`, `_scoped_queue_dir` → `base/queues`, `_active_scope_path` → `base/active_queue_scope`, and `get_max_queue_size` (reads `config.toml`). No suffix changes.
- **Files**: `src/specify_cli/sync/queue.py`

### Subtask T008 – Reroute daemon + de-constant SPEC_KITTY_DIR

- **Steps**:
  1. `_sync_root()` POSIX branch → `get_runtime_root().base / "sync"`; keep the existing Windows branch (`get_runtime_root().sync_dir`) — now env-aware via WP01.
  2. `_daemon_root()` POSIX branch → `get_runtime_root().base` (flat). Keep Windows branch.
  3. Replace module-level `SPEC_KITTY_DIR = Path.home() / _SPEC_KITTY_DIRNAME` with a **function** (e.g. `def _spec_kitty_dir() -> Path: return get_runtime_root().base`) and update all in-module references. If external modules import `SPEC_KITTY_DIR`, grep first (`grep -rn "SPEC_KITTY_DIR" src tests`) and migrate them or keep a lazy module-level `__getattr__` shim.
- **Files**: `src/specify_cli/sync/daemon.py`
- **Notes**: This is the import-time-evaluation trap (research.md D5) — must be lazy so env + test monkeypatching work.

### Subtask T009 – Reroute clock

- **Steps**: In `sync/clock.py`, change the `LamportClock` `_storage_path` `default_factory` lambda and the `load()` default to `get_runtime_root().base / "clock.json"`.
- **Files**: `src/specify_cli/sync/clock.py`

### Subtask T010 [P] – Sync tests

- **Steps**: Add `tests/sync/test_spec_kitty_home_paths.py` asserting, under `SPEC_KITTY_HOME` set vs unset (monkeypatched HOME):
  - `SyncConfig().config_file` under env root; `default_queue_db_path()` (auth + unauth); `_active_scope_path()`; daemon `_sync_root`/`_daemon_root`; `LamportClock.load()` default.
  - unset POSIX equals `~/.spec-kitty/...`.
  - Update existing `tests/sync/test_offline_queue.py`, `test_config_background_daemon.py`, `test_daemon_owner_record.py` only if the reroute changed an asserted path; keep them green.
- **Files**: `tests/sync/*`
- **Parallel?**: Yes.

## Test Strategy

- `.venv/bin/pytest tests/sync/ -q` (note: daemon/real-port tests may need serial `-n0` — see CLAUDE.md). For focused run: `.venv/bin/pytest tests/sync/test_spec_kitty_home_paths.py -q`.
- `.venv/bin/ruff check src/specify_cli/sync tests/sync` and `.venv/bin/mypy src/specify_cli/sync`.

## Risks & Mitigations

- POSIX flat-layout regression → use `base` + literal suffix, never `RuntimeRoot.daemon_dir`/`tracker_dir`.
- Import-time constant → make lazy; grep for external importers of `SPEC_KITTY_DIR`.
- Real-port daemon tests are OS-global → run serially per CLAUDE.md.

## Review Guidance

- Confirm every POSIX suffix is byte-identical to the table above.
- Confirm `SPEC_KITTY_DIR` is no longer evaluated at import.
- Confirm Windows branches still delegate to `get_runtime_root()` (now env-aware).

## Activity Log

- 2026-06-26T11:06:32Z – system – Prompt created.

### Updating Status

Use `spec-kitty agent tasks move-task WP02 --to <status>`.
