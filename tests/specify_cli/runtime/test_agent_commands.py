"""Tests for agent_commands.py — resolver, per-step renderer, lock timing.

These tests describe the FIXED behavior landed in WP01:

* T004 / T022 — ``_get_command_templates_dir()`` returns a doctrine-based
  ``Path`` (never ``None``).
* T008 / T006 — ``_sync_agent_commands()`` iterates per-step subdirs
  (``{step}/prompt.md``) instead of a flat ``*.md`` glob; step dirs without
  ``prompt.md`` are skipped without raising.
* T023 — Stale ``spec-kitty.*`` files are removed after sync.
* T024 — Version lock is NOT written when sync fails mid-loop.

In this lane (lane-d) WP01 has not yet merged, so the resolver tests are RED.
They go GREEN after WP01 merges.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# T004 + T022: Resolver tests
# ---------------------------------------------------------------------------


class TestGetCommandTemplatesDir:
    """FR-001: _get_command_templates_dir() must return a doctrine-based Path."""

    def test_returns_correct_doctrine_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolver returns <doctrine_dir>/missions/mission-steps/software-dev.

        RED in lane-d (buggy resolver uses get_package_asset_root / kittify_home);
        GREEN after WP01 merges (resolver uses doctrine.__file__).
        """
        fake_doctrine_init = tmp_path / "doctrine" / "__init__.py"
        fake_doctrine_init.parent.mkdir(parents=True)
        fake_doctrine_init.write_text("")

        monkeypatch.setattr("doctrine.__file__", str(fake_doctrine_init))

        from specify_cli.runtime.agent_commands import _get_command_templates_dir

        result = _get_command_templates_dir()
        expected = fake_doctrine_init.parent / "missions" / "mission-steps" / "software-dev"
        assert result == expected

    def test_return_type_is_path_not_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Return type is Path, never None.

        RED in lane-d (buggy resolver can return None); GREEN after WP01.
        """
        fake_doctrine_init = tmp_path / "doctrine" / "__init__.py"
        fake_doctrine_init.parent.mkdir(parents=True)
        fake_doctrine_init.write_text("")

        monkeypatch.setattr("doctrine.__file__", str(fake_doctrine_init))

        from specify_cli.runtime.agent_commands import _get_command_templates_dir

        result = _get_command_templates_dir()
        assert isinstance(result, Path)

    def test_resolver_with_sys_modules_monkeypatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T022: Resolver uses doctrine.__file__ as its anchor (sys.modules approach).

        RED in lane-d; GREEN after WP01 merges.
        """
        fake_mod = types.ModuleType("doctrine")
        fake_mod.__file__ = str(tmp_path / "doctrine" / "__init__.py")
        monkeypatch.setitem(sys.modules, "doctrine", fake_mod)

        # Reload the module under test to pick up the patched doctrine
        import importlib

        import specify_cli.runtime.agent_commands as ac

        importlib.reload(ac)

        result = ac._get_command_templates_dir()
        assert result == tmp_path / "doctrine" / "missions" / "mission-steps" / "software-dev"


# ---------------------------------------------------------------------------
# T008 / T006: Integration — per-step renderer
# ---------------------------------------------------------------------------


class TestSyncAgentCommandsIntegration:
    """FR-002/FR-003: _sync_agent_commands() must use per-step subdirectory layout."""

    def test_all_prompt_driven_commands_written(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_sync_agent_commands writes one file per PROMPT_DRIVEN step-dir.

        RED in lane-d (buggy renderer uses flat glob, never finds per-step
        prompt.md files); GREEN after WP01 merges.
        """
        from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS
        from specify_cli.runtime.agent_commands import _sync_agent_commands

        templates_dir = tmp_path / "mission-steps" / "software-dev"
        for cmd in PROMPT_DRIVEN_COMMANDS:
            step_dir = templates_dir / cmd
            step_dir.mkdir(parents=True)
            (step_dir / "prompt.md").write_text(f"# {cmd} prompt")

        output_dir = tmp_path / "agent_output"
        output_dir.mkdir()

        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands.get_global_command_dir",
            lambda _: output_dir,
        )

        _sync_agent_commands("claude", templates_dir, "sh")

        written_prompt_commands = {
            p.stem.split(".")[1]
            for p in output_dir.glob("spec-kitty.*.md")
            if p.stem.split(".")[1] in PROMPT_DRIVEN_COMMANDS
        }
        assert written_prompt_commands == set(PROMPT_DRIVEN_COMMANDS)

    def test_missing_prompt_md_skipped_without_raising(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T006: Step dirs without prompt.md are skipped without raising.

        In the FIXED code (WP01), when step dirs exist but have no prompt.md,
        _sync_agent_commands must not raise and must not write any
        prompt-driven command files (spec-kitty.{cmd}.md for cmd in
        PROMPT_DRIVEN_COMMANDS).

        RED in lane-d: the buggy flat-glob renderer always writes CLI-driven
        shims even when no prompt.md is present (it finds no *.md to render
        for prompt-driven commands, but the shim loop still runs).
        After WP01 the test passes: prompt-driven files are only written when
        prompt.md exists; CLI shims are separate.
        """
        from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS
        from specify_cli.runtime.agent_commands import _sync_agent_commands

        templates_dir = tmp_path / "mission-steps" / "software-dev"
        for cmd in PROMPT_DRIVEN_COMMANDS:
            (templates_dir / cmd).mkdir(parents=True)
            # Deliberately omit prompt.md

        output_dir = tmp_path / "agent_output"
        output_dir.mkdir()

        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands.get_global_command_dir",
            lambda _: output_dir,
        )

        # Must not raise
        _sync_agent_commands("claude", templates_dir, "sh")

        # No prompt-driven command files should be written (they all lack prompt.md)
        for cmd in PROMPT_DRIVEN_COMMANDS:
            assert not (output_dir / f"spec-kitty.{cmd}.md").exists(), (
                f"spec-kitty.{cmd}.md should not be written without prompt.md"
            )


# ---------------------------------------------------------------------------
# T023: Stale file removal
# ---------------------------------------------------------------------------


class TestRendererStaleRemoval:
    """FR-002: Stale spec-kitty.* files are removed after sync."""

    def test_stale_files_removed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Files not in the canonical set are removed.

        RED in lane-d when the stale check runs before prompt files are written
        (buggy flat-glob path never writes prompt files, so the canonical set
        contains only CLI-driven shims; stale removal still fires for files
        outside that set). Actually the stale removal loop exists in both old
        and new code, so this test is GREEN in both lanes — but it exercises the
        contract that matters after WP01.
        """
        from specify_cli.runtime.agent_commands import _sync_agent_commands

        templates_dir = tmp_path / "steps"
        templates_dir.mkdir(parents=True)

        output_dir = tmp_path / "out"
        output_dir.mkdir()
        stale = output_dir / "spec-kitty.oldcmd.md"
        stale.write_text("stale content")

        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands.get_global_command_dir",
            lambda _: output_dir,
        )

        _sync_agent_commands("claude", templates_dir, "sh")

        assert not stale.exists(), "Stale file should have been removed"


# ---------------------------------------------------------------------------
# T024: Lock written only after successful full install
# ---------------------------------------------------------------------------


class TestVersionLockTiming:
    """FR-004: Version lock must NOT be written if sync fails."""

    def test_lock_not_written_when_sync_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If _sync_agent_commands raises, the lock must not be updated.

        The fixed ensure_global_agent_commands() catches the exception, logs it,
        and re-raises without writing the version lock file. This test verifies
        that guarantee.

        RED in lane-d: the buggy ensure_global_agent_commands() returns early
        when templates_dir is None (no exception reaches the lock-write path),
        but the monkeypatch on _get_command_templates_dir makes templates_dir
        non-None so the code reaches _sync_agent_commands. If the buggy
        ensure_global_agent_commands() signature doesn't accept agent_keys
        this test may also expose that gap.
        """
        import specify_cli.runtime.agent_commands as ac

        fake_templates_dir = tmp_path / "fake_templates"
        fake_templates_dir.mkdir()

        monkeypatch.setattr(
            ac,
            "_get_command_templates_dir",
            lambda: fake_templates_dir,
        )

        def boom(agent_key: str, templates_dir: Path, script_type: str) -> None:
            raise RuntimeError("simulated sync failure")

        monkeypatch.setattr(ac, "_sync_agent_commands", boom)

        kittify_home = tmp_path / "kittify"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(kittify_home))

        with pytest.raises(RuntimeError, match="simulated sync failure"):
            ac.ensure_global_agent_commands()

        lock_path = kittify_home / "cache" / ac._VERSION_FILENAME
        assert not lock_path.exists(), "Lock must not be written on failure"
