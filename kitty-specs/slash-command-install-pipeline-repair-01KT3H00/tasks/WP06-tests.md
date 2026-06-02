---
work_package_id: WP06
title: Test Coverage — resolver, renderer, lock, doctor audit, fix scope, idempotency
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-010
- FR-011
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Depends on WP01-WP04. Can run in parallel with WP05. Run: spec-kitty agent action implement WP06 --agent claude'
subtasks:
- T022
- T023
- T024
- T025
- T026
- T027
- T028
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/
execution_mode: code_change
owned_files:
- tests/specify_cli/runtime/test_agent_commands_resolver.py
- tests/specify_cli/runtime/test_agent_commands_renderer.py
- tests/specify_cli/cli/commands/test_doctor_slash_audit.py
- tests/specify_cli/cli/commands/test_doctor_slash_fix.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Wait for confirmation before proceeding.

---

## Objective

Write comprehensive tests for all code changes introduced in WP01–WP04. WP01–WP04 each included their own targeted tests; this WP writes the remaining coverage, fills any gaps, and runs `mypy --strict` verification across all changed modules.

**Prerequisites**: WP01, WP02, WP03, WP04 must be merged. Can run in parallel with WP05.

```bash
spec-kitty agent action implement WP06 --agent claude
```

---

## Context

WP01–WP04 each include test files. Before adding tests, check what already exists:

```bash
ls tests/specify_cli/runtime/test_agent_commands*.py
ls tests/specify_cli/cli/commands/test_doctor_slash*.py
```

This WP fills remaining gaps and consolidates coverage. Do not duplicate tests already written by WP01–WP04 — check existing test content first and only add what is missing.

### Test patterns used in this codebase

- `pytest` with `tmp_path` and `monkeypatch` fixtures
- No global state mutation — all tests scope to `tmp_path`
- Deferred imports inside test functions when patching module-level names
- `typer.testing.CliRunner` for CLI subcommand tests

---

## Subtask T022 — Test: resolver correct doctrine path

**File**: `tests/specify_cli/runtime/test_agent_commands_resolver.py`

Verify the following if not already covered by WP01:

```python
def test_resolver_path_matches_doctrine_package_structure(tmp_path, monkeypatch):
    """Resolved path ends in missions/mission-steps/software-dev."""
    # Arrange: fake doctrine with __file__ pointing to tmp_path/doctrine/__init__.py
    import types, sys
    fake_pkg_dir = tmp_path / "doctrine"
    fake_pkg_dir.mkdir()
    init = fake_pkg_dir / "__init__.py"
    init.write_text("")
    steps = fake_pkg_dir / "missions" / "mission-steps" / "software-dev"
    steps.mkdir(parents=True)

    fake_doctrine = types.ModuleType("doctrine")
    fake_doctrine.__file__ = str(init)
    monkeypatch.setitem(sys.modules, "doctrine", fake_doctrine)

    from specify_cli.runtime.agent_commands import _get_command_templates_dir
    result = _get_command_templates_dir()

    assert result == steps
    assert result.name == "software-dev"


def test_resolver_never_returns_none(tmp_path, monkeypatch):
    """_get_command_templates_dir never returns None after fix."""
    import types, sys, inspect
    from specify_cli.runtime import agent_commands
    hints = inspect.get_annotations(agent_commands._get_command_templates_dir, eval_str=True)
    # Return type must be Path, not Optional[Path]
    from pathlib import Path
    assert "Path | None" not in str(hints.get("return", "")), \
        "Return type must be Path, not Path | None"
```

---

## Subtask T023 — Test: per-step iteration writes all 15 commands

**File**: `tests/specify_cli/runtime/test_agent_commands_renderer.py`

Write integration-style tests if not fully covered by WP02:

```python
def test_all_8_prompt_driven_commands_written(tmp_path, monkeypatch):
    """All 8 prompt-driven commands are written after the renderer fix."""
    from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS
    # ... setup fake steps dir, monkeypatch doctrine and AGENT_COMMAND_CONFIG ...
    # ... call _sync_agent_commands("claude", steps_dir, "bash") ...
    # Assert each prompt-driven command file exists in output_dir

def test_stale_files_removed(tmp_path, monkeypatch):
    """spec-kitty.* files for removed commands are deleted."""
    # Create an extra spec-kitty.obsolete.md in output_dir
    # Run _sync_agent_commands
    # Assert spec-kitty.obsolete.md is gone

def test_missing_prompt_md_in_step_dir_skipped_gracefully(tmp_path, monkeypatch, caplog):
    """A step dir without prompt.md is skipped with a warning, not an exception."""
    # Create steps_dir with one step dir missing prompt.md
    # Run _sync_agent_commands
    # Assert no exception raised
    # Assert warning logged for the missing step
```

---

## Subtask T024 — Test: lock written only after full install success

**File**: `tests/specify_cli/runtime/test_agent_commands_renderer.py` (or a new `test_agent_commands_lock.py`)

```python
def test_version_lock_not_written_on_partial_failure(tmp_path, monkeypatch):
    """Version lock must not advance when sync raises mid-loop."""
    # Monkeypatch _sync_agent_commands to raise after first agent
    # Run ensure_global_agent_commands (mocked to call sync)
    # Assert lock file not updated / still at old version

def test_version_lock_written_after_successful_full_install(tmp_path, monkeypatch):
    """Version lock advances to current version after successful install."""
    # Mock all sync calls to succeed
    # Run ensure_global_agent_commands
    # Assert lock file contains current CLI version
```

---

## Subtask T025 — Test: doctor audit false-positive prevention

**File**: `tests/specify_cli/cli/commands/test_doctor_slash_audit.py`

Verify the key false-positive scenario if not already covered by WP03:

```python
def test_doctor_skills_does_not_report_healthy_when_command_missing(tmp_path, monkeypatch, capsys):
    """doctor skills must not output 'healthy' when a slash command file is absent."""
    # Setup: claude in config.available
    # Setup: delete spec-kitty.specify.md from mocked global dir
    # Invoke doctor skills
    # Assert: exit_code != 0 OR output contains "gap" / "missing"
    # Assert: output does NOT contain "all configured agents healthy"
```

---

## Subtask T026 — Test: `--fix` scope guard

**File**: `tests/specify_cli/cli/commands/test_doctor_slash_fix.py`

```python
def test_fix_does_not_touch_unconfigured_agent_dirs(tmp_path, monkeypatch):
    """--fix must not install files for agents not in config.available."""
    # Config: only claude in config.available
    # Setup: gemini command dir exists at tmp_path/gemini_cmds/
    # Invoke: doctor skills --fix
    # Assert: gemini_cmds/ is empty / unchanged
    # Assert: only claude command dir has files written

def test_fix_only_acts_on_agents_in_agent_command_config(tmp_path, monkeypatch):
    """--fix ignores agents in config but not in AGENT_COMMAND_CONFIG."""
    # Config: "unknownagent" in config.available (not in AGENT_COMMAND_CONFIG)
    # Invoke: doctor skills --fix
    # Assert: no crash, no file creation for unknownagent
```

---

## Subtask T027 — Test: `--fix` idempotency

**File**: `tests/specify_cli/cli/commands/test_doctor_slash_fix.py`

```python
def test_fix_is_noop_when_all_commands_present(tmp_path, monkeypatch):
    """Running --fix when all commands present makes no filesystem changes."""
    # Setup: all 15 command files present with correct version markers
    # Record mtimes
    # Invoke: doctor skills --fix
    # Assert: all mtimes unchanged (use os.stat().st_mtime_ns)
    # Assert: exit code 0

def test_fix_is_idempotent_across_two_runs(tmp_path, monkeypatch):
    """Running --fix twice produces identical final state."""
    # Setup: one command missing
    # Run 1: --fix → repairs it
    # Run 2: --fix → no change
    # Assert: file content identical after both runs
```

---

## Subtask T028 — mypy --strict verification

Run `mypy --strict` across all modules changed in this mission:

```bash
uv run mypy --strict \
  src/specify_cli/runtime/agent_commands.py \
  src/specify_cli/cli/commands/doctor.py
```

Fix any type errors found. Common issues to watch for:
- Missing return type annotations on new functions
- `list[str] | None` vs `list[str]` in function signatures
- Missing imports for `Path`, `dataclass`, etc.
- `SlashCommandGap` dataclass field types

All errors must be zero before this WP is considered done.

---

## Definition of Done

- [ ] All test files listed in `owned_files` exist and are non-empty
- [ ] `pytest tests/specify_cli/runtime/test_agent_commands_resolver.py -v` — all pass
- [ ] `pytest tests/specify_cli/runtime/test_agent_commands_renderer.py -v` — all pass
- [ ] `pytest tests/specify_cli/cli/commands/test_doctor_slash_audit.py -v` — all pass
- [ ] `pytest tests/specify_cli/cli/commands/test_doctor_slash_fix.py -v` — all pass
- [ ] `mypy --strict src/specify_cli/runtime/agent_commands.py src/specify_cli/cli/commands/doctor.py` — zero errors
- [ ] `ruff check tests/specify_cli/runtime/ tests/specify_cli/cli/commands/test_doctor_slash*.py` — zero violations
- [ ] No test duplicates WP01–WP04 tests (check before writing)

## Risks

- Tests that mock `~/.claude/commands/` or other home-dir paths must scope to `tmp_path` — never mutate real global state.
- `ensure_global_agent_commands()` acquires a file lock. Tests calling it must either mock the lock or use `tmp_path` for the cache directory.
- `mypy --strict` on `doctor.py` (a large file) may surface pre-existing issues not related to this mission. Only fix issues in functions touched by WP03/WP04. Open a separate issue for any pre-existing mypy errors found.
