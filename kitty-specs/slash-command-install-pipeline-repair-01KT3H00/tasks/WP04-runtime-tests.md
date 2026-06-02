---
work_package_id: WP04
title: Runtime tests — agent_commands resolver, renderer, lock
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-012
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T008
- T022
- T023
- T024
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/runtime/
execution_mode: code_change
owned_files:
- tests/specify_cli/runtime/test_agent_commands.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Write unit and integration tests for the `agent_commands.py` fixes landed in WP01, covering the resolver (`_get_command_templates_dir`), the per-step renderer (`_sync_agent_commands`), and the post-sync lock write (`ensure_global_agent_commands`).

**Prerequisite**: WP01 merged.

```bash
spec-kitty agent action implement WP04 --agent claude
```

---

## Context

Target file: `tests/specify_cli/runtime/test_agent_commands.py`. WP01 committed a minimal failing ATDD stub (`test_resolver_returns_path_not_none`) to this file as its first commit. **Start by expanding that stub** into the full `TestGetCommandTemplatesDir` class rather than creating a new file from scratch. The stub is already RED→GREEN after WP01; WP04 adds the remaining test classes.

All tests must use `tmp_path` and `monkeypatch`. Tests must **not** read from or write to the real `~/.claude/commands/` directory — mock `doctrine.__file__` and `get_global_command_dir`. T004 and T022 are both methods in `TestGetCommandTemplatesDir`.

---

## Subtask T004 — Unit tests for resolver

In `tests/specify_cli/runtime/test_agent_commands.py`, add `TestGetCommandTemplatesDir`:

```python
class TestGetCommandTemplatesDir:
    def test_returns_correct_doctrine_path(self, tmp_path, monkeypatch):
        """Resolver returns <doctrine_dir>/missions/mission-steps/software-dev."""
        fake_doctrine = tmp_path / "doctrine" / "__init__.py"
        fake_doctrine.parent.mkdir(parents=True)
        fake_doctrine.write_text("")
        monkeypatch.setattr("doctrine.__file__", str(fake_doctrine))

        from specify_cli.runtime.agent_commands import _get_command_templates_dir
        result = _get_command_templates_dir()
        expected = fake_doctrine.parent / "missions" / "mission-steps" / "software-dev"
        assert result == expected

    def test_return_type_is_path_not_none(self, tmp_path, monkeypatch):
        """Return type is Path, never None."""
        fake_doctrine = tmp_path / "doctrine" / "__init__.py"
        fake_doctrine.parent.mkdir(parents=True)
        fake_doctrine.write_text("")
        monkeypatch.setattr("doctrine.__file__", str(fake_doctrine))

        from specify_cli.runtime.agent_commands import _get_command_templates_dir
        from pathlib import Path
        result = _get_command_templates_dir()
        assert isinstance(result, Path)
```

Validation: `pytest tests/specify_cli/runtime/test_agent_commands.py::TestGetCommandTemplatesDir -v` — 2 passing.

---

## Subtask T008 — Integration test: all commands written correctly

Add `TestSyncAgentCommandsIntegration`:

```python
class TestSyncAgentCommandsIntegration:
    def test_all_prompt_driven_commands_written(self, tmp_path, monkeypatch):
        """_sync_agent_commands writes one file per PROMPT_DRIVEN step-dir."""
        from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS

        # Build a fake templates dir with per-step subdirs
        templates_dir = tmp_path / "mission-steps" / "software-dev"
        for cmd in PROMPT_DRIVEN_COMMANDS:
            step_dir = templates_dir / cmd
            step_dir.mkdir(parents=True)
            (step_dir / "prompt.md").write_text(f"# {cmd} prompt")

        output_dir = tmp_path / "agent_output"
        output_dir.mkdir()

        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands._get_command_templates_dir",
            lambda: templates_dir,
        )
        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands.get_global_command_dir",
            lambda agent_key: output_dir,
        )

        from specify_cli.runtime.agent_commands import _sync_agent_commands
        _sync_agent_commands("claude", templates_dir, "claude")

        written = {p.stem.split(".")[1] for p in output_dir.glob("spec-kitty.*.md")}
        assert written == set(PROMPT_DRIVEN_COMMANDS)

    def test_missing_prompt_md_skipped(self, tmp_path, monkeypatch):
        """Step dirs without prompt.md are skipped without raising."""
        from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS
        templates_dir = tmp_path / "mission-steps" / "software-dev"
        # Create step dirs but omit prompt.md for all
        for cmd in PROMPT_DRIVEN_COMMANDS:
            (templates_dir / cmd).mkdir(parents=True)

        output_dir = tmp_path / "agent_output"
        output_dir.mkdir()

        from specify_cli.runtime.agent_commands import _sync_agent_commands
        # Must not raise
        _sync_agent_commands("claude", templates_dir, "claude")
        assert list(output_dir.iterdir()) == []
```

---

## Subtask T022 — Add `sys.modules` monkeypatch method to `TestGetCommandTemplatesDir`

T022 is implemented as a **second method** inside the same `TestGetCommandTemplatesDir` class from T004 (not a separate class). This avoids near-duplicate test classes while covering both patching strategies.

Add this method to `TestGetCommandTemplatesDir`:

```python
    def test_resolver_with_sys_modules_monkeypatch(self, tmp_path, monkeypatch):
        """Resolver uses doctrine.__file__ as its anchor (sys.modules approach)."""
        import sys, types
        fake_mod = types.ModuleType("doctrine")
        fake_mod.__file__ = str(tmp_path / "doctrine" / "__init__.py")
        monkeypatch.setitem(sys.modules, "doctrine", fake_mod)

        from specify_cli.runtime.agent_commands import _get_command_templates_dir
        result = _get_command_templates_dir()
        assert result == tmp_path / "doctrine" / "missions" / "mission-steps" / "software-dev"
```

---

## Subtask T023 — Test: per-step iteration writes all 15 commands, removes stale files

Add `TestRendererStaleRemoval`:

```python
class TestRendererStaleRemoval:
    def test_stale_files_removed(self, tmp_path, monkeypatch):
        """Files for commands no longer in PROMPT_DRIVEN_COMMANDS are removed."""
        from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS
        from specify_cli.runtime.agent_commands import _sync_agent_commands

        templates_dir = tmp_path / "steps"
        for cmd in PROMPT_DRIVEN_COMMANDS:
            d = templates_dir / cmd
            d.mkdir(parents=True)
            (d / "prompt.md").write_text(f"# {cmd}")

        output_dir = tmp_path / "out"
        output_dir.mkdir()
        # Pre-populate a stale file
        stale = output_dir / "spec-kitty.oldcmd.md"
        stale.write_text("stale content")

        _sync_agent_commands("claude", templates_dir, "claude")

        assert not stale.exists(), "Stale file should have been removed"
        for cmd in PROMPT_DRIVEN_COMMANDS:
            assert (output_dir / f"spec-kitty.{cmd}.md").exists()
```

---

## Subtask T024 — Test: lock written only after successful full install

Add `TestVersionLockTiming`:

```python
class TestVersionLockTiming:
    def test_lock_not_written_when_sync_fails(self, tmp_path, monkeypatch):
        """Version lock must NOT be written if _sync_agent_commands raises."""
        import types
        fake_mod = types.ModuleType("doctrine")
        fake_mod.__file__ = str(tmp_path / "doctrine" / "__init__.py")
        (tmp_path / "doctrine").mkdir()
        monkeypatch.setitem(sys.modules, "doctrine", fake_mod)

        def boom(agent_key, templates_dir, script_type):
            raise RuntimeError("simulated sync failure")

        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands._sync_agent_commands", boom
        )
        lock_path = tmp_path / "lock"

        from specify_cli.runtime.agent_commands import ensure_global_agent_commands
        with pytest.raises(RuntimeError):
            ensure_global_agent_commands()

        # Lock file must not exist
        assert not any(lock_path.parent.glob("*.lock")), "Lock must not be written on failure"
```

---

## Definition of Done

- [ ] `tests/specify_cli/runtime/test_agent_commands.py` created with all 5 subtask test classes
- [ ] `pytest tests/specify_cli/runtime/test_agent_commands.py -v` — all tests pass, no warnings
- [ ] Tests do not touch real `~/.claude/commands/` or install real files
- [ ] `ruff check tests/specify_cli/runtime/test_agent_commands.py` — zero violations
- [ ] `mypy tests/specify_cli/runtime/test_agent_commands.py` — zero errors

## Risks

- `_sync_agent_commands` signature may differ from what's assumed — read `agent_commands.py` before writing stubs.
- The stale-file removal loop may require a specific output dir setup — confirm the function's stale-removal logic before writing T023.
- If `_get_command_templates_dir` is renamed, update all test references.
