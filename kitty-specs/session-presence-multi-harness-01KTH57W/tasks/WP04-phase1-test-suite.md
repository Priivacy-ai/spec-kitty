---
work_package_id: WP04
title: Phase 1 Test Suite
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-005
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: pr/session-presence-multi-harness
merge_target_branch: pr/session-presence-multi-harness
branch_strategy: Planning artifacts for this mission were generated on pr/session-presence-multi-harness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/session-presence-multi-harness unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
agent: claude
history:
- date: '2026-06-07'
  status: planned
  note: Initial WP creation
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/session_presence/
execution_mode: code_change
owned_files:
- tests/specify_cli/session_presence/__init__.py
- tests/specify_cli/session_presence/conftest.py
- tests/specify_cli/session_presence/test_content.py
- tests/specify_cli/session_presence/test_upgrade_checker.py
- tests/specify_cli/session_presence/test_markdown_rules_writer.py
- tests/specify_cli/session_presence/test_claude_code_writer.py
- tests/specify_cli/session_presence/test_claude_code_hook.py
- tests/specify_cli/session_presence/test_manager.py
- tests/specify_cli/cli/commands/test_session_start.py
- tests/specify_cli/upgrade/migrations/test_m_session_presence_claude_code.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Write the complete test suite for all Phase 1 modules. Every new source module introduced in WP01–WP03 gets a dedicated test module. All tests must pass with `pytest`; zero ruff/mypy issues.

## Context

The tests form the acceptance gate for Phase 1. No test stubs — full coverage of happy paths, idempotency, error/edge cases, and the exit-0 guarantee for `session-start`.

**No network calls in tests** — mock `UpgradeChecker.check_in_background()` and `get_available_version()`. Use `tmp_path` (pytest fixture) for all filesystem operations.

**Implementation command**:
```bash
spec-kitty agent action implement WP04 --agent claude
```

---

## Branch Strategy

- **Planning base**: `pr/session-presence-multi-harness`
- **Merge target**: `pr/session-presence-multi-harness`

---

## Subtask T017 — conftest.py + test_content.py

**Purpose**: Shared fixtures for all `session_presence` tests, plus complete coverage of `SessionPresenceContent.render()`.

**`tests/specify_cli/session_presence/__init__.py`**: Empty file.

**`tests/specify_cli/session_presence/conftest.py`**:
```python
import pytest
from pathlib import Path
from specify_cli.session_presence.content import SessionPresenceContent

@pytest.fixture
def healthy_content():
    return SessionPresenceContent("3.2.0", "my-project", "healthy", None)

@pytest.fixture
def upgrade_content():
    return SessionPresenceContent("3.2.0", "my-project", "upgrade-available", "3.3.0")

@pytest.fixture
def migration_content():
    return SessionPresenceContent("3.2.0", "my-project", "migration-required", None)

@pytest.fixture
def claude_project(tmp_path):
    """A minimal spec-kitty project directory with .kittify/ and .claude/."""
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".claude").mkdir()
    return tmp_path
```

**`tests/specify_cli/session_presence/test_content.py`** — required cases:
- `render()` for `healthy`: contains version, project slug, `(healthy)`, both usage patterns, no upgrade/migration lines
- `render()` for `upgrade-available`: contains upgrade line with `available_version`; does NOT contain migration line
- `render()` for `migration-required`: contains migration warning; does NOT contain upgrade line
- `render()` starts with `SECTION_OPEN` and ends with `SECTION_CLOSE + "\n"`
- `render()` contains exactly one `SECTION_OPEN` and one `SECTION_CLOSE`
- `frozen=True`: attempting `content.version = "x"` raises `FrozenInstanceError`

---

## Subtask T018 — test_upgrade_checker.py

**Purpose**: Cover cache hit/miss logic and the guarantee that `check_in_background()` never raises.

**`tests/specify_cli/session_presence/test_upgrade_checker.py`** — required cases:
- **Cache miss** (no file): `get_available_version()` returns `None`
- **Cache hit within TTL**: returns cached `latest_version`; `check_in_background()` is NOT called
- **Cache stale** (age > TTL): returns last known value; `check_in_background()` IS called
- **Cache malformed JSON**: returns `None`, no exception raised
- **`check_in_background()` with subprocess failure**: mock `subprocess.Popen` to raise `OSError`; verify `check_in_background()` returns without raising
- **`check_in_background()` with any exception**: bare `except Exception` catches it; function returns `None`

All tests must use `tmp_path` and monkeypatch `CACHE_PATH` to avoid touching `~/.kittify/`.

---

## Subtask T019 — test_markdown_rules_writer.py

**Purpose**: Full coverage of `MarkdownRulesWriter` in both append modes.

**`tests/specify_cli/session_presence/test_markdown_rules_writer.py`** — required cases:

**append_mode=True (e.g., CLAUDE.md)**:
- First write on non-existent file: creates file with section
- First write on existing file (no section): appends section; existing content preserved
- Re-write (section already present): replaces section; no duplicates; surrounding content preserved
- `remove()` on file with section: strips section; surrounding content preserved
- `remove()` on file without section: no-op
- `has_presence()` returns True/False correctly

**append_mode=False (e.g., .cursor/rules/spec-kitty.mdc)**:
- First write: creates file with section as entire content
- Re-write: replaces entire file content; still exactly one section
- `remove()`: deletes the file
- `can_write()` returns False when parent directory does not exist

**Atomicity**: Write to a file while it's being written (use `monkeypatch` to make `os.replace` raise `OSError`); verify original file is unchanged.

---

## Subtask T020 — test_claude_code_writer.py + test_claude_code_hook.py

**Purpose**: Verify that `ClaudeCodeWriter` calls both the section writer and the hook registrar, and that `ClaudeCodeHookRegistrar` handles all settings.json edge cases.

**`test_claude_code_writer.py`** — required cases:
- `write()` calls `super().write()` AND `ClaudeCodeHookRegistrar().register()`
- `remove()` calls `super().remove()` AND `ClaudeCodeHookRegistrar().unregister()`
- `has_presence()` returns False when CLAUDE.md section is missing (even if hook exists)
- `has_presence()` returns False when hook is missing (even if CLAUDE.md section exists)
- `has_presence()` returns True only when BOTH are present

**`test_claude_code_hook.py`** — required cases:
- `register()` creates settings.json if absent
- `register()` adds hook to empty `SessionStart` list
- `register()` is idempotent — calling twice results in exactly one entry
- `register()` preserves existing `SessionStart` entries from other tools
- `register()` handles malformed JSON (treats as `{}`, creates valid file)
- `unregister()` removes only the spec-kitty entry; other entries preserved
- `unregister()` leaves `SessionStart: []` when list becomes empty (does not delete key)
- `unregister()` is a no-op when entry is not present
- `is_registered()` returns True/False correctly
- All writes are atomic (verify temp file removed on error)

---

## Subtask T021 — test_manager.py + test_session_start.py

**Purpose**: Cover `SessionPresenceManager` orchestration and the `session-start` command's exit-0 guarantee.

**`test_manager.py`** — required cases:
- `install()` calls `write()` for agents where `can_write=True` AND `has_presence=False`
- `install()` skips agents where `has_presence=True` (already present)
- `install()` skips `NullWriter` agents silently (no error)
- `install()` returns `InstallResult` with correct `changes` list
- `install()` catches writer exceptions and adds to `warnings` (does not raise)
- `update()` calls `write()` regardless of `has_presence`
- `update(dry_run=True)` does not call `write()`, returns change description
- `_build_content()` sets `health="migration-required"` when `project_needs_migration` returns True
- `_build_content()` sets `health="upgrade-available"` when avail version differs from installed

Use `unittest.mock.patch` to mock `get_writer()`, `project_needs_migration()`, `UpgradeChecker`, and `importlib.metadata.version`.

**`test_session_start.py`** — required cases:
- Invoked inside a spec-kitty project (`.kittify/` present): outputs `render()` result, exit 0
- Invoked outside a spec-kitty project (no `.kittify/`): no output, exit 0
- `_find_project_root()` walks up from a nested subdirectory to find `.kittify/`
- `_find_project_root()` returns `None` at filesystem root
- Exception in `SessionPresenceManager._build_content()`: exit 0, no traceback output
- Exception in `AgentConfig.load()`: exit 0, no output
- Use `typer.testing.CliRunner` for command invocation

---

## Subtask T022 — test_m_session_presence_claude_code.py

**Purpose**: Test the Phase 1 migration's detection and application logic.

**`tests/specify_cli/upgrade/migrations/test_m_session_presence_claude_code.py`** — required cases:
- `detect()` returns False for a project without `.kittify/`
- `detect()` returns False when `claude` is not in configured agents
- `detect()` returns True when CLAUDE.md section is missing (even if hook exists)
- `detect()` returns True when hook is missing (even if CLAUDE.md section exists)
- `detect()` returns False when both artefacts are present
- `apply()` writes CLAUDE.md section and settings.json hook (verify both files after apply)
- `apply(dry_run=True)` produces no filesystem changes (verify no new files)
- `apply()` is idempotent — applying twice leaves files in same state
- `runs_on_worktrees = False`
- Migration is registered in `MigrationRegistry` (test via registry lookup)

---

## Definition of Done

- [ ] `pytest tests/specify_cli/session_presence/ -v` passes (all tests green)
- [ ] `pytest tests/specify_cli/cli/commands/test_session_start.py -v` passes
- [ ] `pytest tests/specify_cli/upgrade/migrations/test_m_session_presence_claude_code.py -v` passes
- [ ] No test makes network calls (all subprocess and version check calls mocked)
- [ ] No test touches `~/.kittify/` (all cache operations use `tmp_path` monkeypatched paths)
- [ ] Zero ruff issues, zero mypy --strict issues in test files
- [ ] `CliRunner` used for all `session-start` tests (no subprocess invocation)

## Risks

- `typer.testing.CliRunner` may capture stdout differently than production. Verify that `typer.echo()` output appears in `result.output`.
- `FrozenInstanceError` test: this is `dataclasses.FrozenInstanceError` in Python 3.11+. Import from `dataclasses`.
- Mocking `importlib.metadata.version`: use `unittest.mock.patch("specify_cli.session_presence.manager.version", return_value="3.2.0")` or equivalent.
