"""T020 — Tests for ClaudeCodeHookRegistrar.

Covers all settings.json edge cases: absent, empty, malformed, idempotency,
preservation of other entries, and atomic writes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from specify_cli.session_presence.hooks.claude_code_hook import (
    SESSION_START_EVENT,
    STOP_EVENT,
    ClaudeCodeHookRegistrar,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]
_CMD = "spec-kitty session-start"
_SETTINGS_REL = ".claude/settings.json"


def _settings_path(project_root: Path) -> Path:
    return project_root / _SETTINGS_REL


def _read_settings(project_root: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_settings_path(project_root).read_text(encoding="utf-8")))


def _write_settings(project_root: Path, data: dict[str, Any]) -> None:
    _settings_path(project_root).parent.mkdir(parents=True, exist_ok=True)
    _settings_path(project_root).write_text(json.dumps(data), encoding="utf-8")


def _invalid_backups(project_root: Path) -> list[Path]:
    return sorted(_settings_path(project_root).parent.glob("settings.json.invalid.*"))


class TestRegister:
    def test_creates_settings_json_if_absent(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar()
        reg.register(claude_project, _CMD)
        assert _settings_path(claude_project).exists()

    def test_adds_hook_to_empty_session_start(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar()
        reg.register(claude_project, _CMD)
        data = _read_settings(claude_project)
        entries = data["hooks"]["SessionStart"]
        assert any(
            any(
                h.get("type") == "command" and h.get("command") == _CMD
                for h in entry.get("hooks", [])
            )
            for entry in entries
        )

    def test_idempotent_double_register(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar()
        reg.register(claude_project, _CMD)
        reg.register(claude_project, _CMD)
        data = _read_settings(claude_project)
        entries = data["hooks"]["SessionStart"]
        matching = [
            h
            for entry in entries
            for h in entry.get("hooks", [])
            if h.get("command") == _CMD
        ]
        assert len(matching) == 1

    def test_preserves_existing_session_start_entries(self, claude_project: Path) -> None:
        existing_entry = {
            "hooks": [{"type": "command", "command": "other-tool start"}]
        }
        _write_settings(
            claude_project,
            {"hooks": {"SessionStart": [existing_entry]}},
        )
        reg = ClaudeCodeHookRegistrar()
        reg.register(claude_project, _CMD)
        data = _read_settings(claude_project)
        entries = data["hooks"]["SessionStart"]
        commands = [
            h.get("command")
            for entry in entries
            for h in entry.get("hooks", [])
        ]
        assert "other-tool start" in commands
        assert _CMD in commands

    def test_handles_malformed_json(self, claude_project: Path) -> None:
        _settings_path(claude_project).write_text("NOT JSON", encoding="utf-8")
        reg = ClaudeCodeHookRegistrar()
        reg.register(claude_project, _CMD)  # Should not raise
        # File should now be valid JSON
        data = _read_settings(claude_project)
        assert "hooks" in data
        backups = _invalid_backups(claude_project)
        assert len(backups) == 1
        backup = backups[0]
        assert backup.read_text(encoding="utf-8") == "NOT JSON"

    def test_handles_non_object_json_without_losing_original(
        self, claude_project: Path
    ) -> None:
        original = '["not", "an", "object"]'
        _settings_path(claude_project).write_text(original, encoding="utf-8")
        reg = ClaudeCodeHookRegistrar()
        reg.register(claude_project, _CMD)
        data = _read_settings(claude_project)
        assert "hooks" in data
        backups = _invalid_backups(claude_project)
        assert len(backups) == 1
        backup = backups[0]
        assert backup.read_text(encoding="utf-8") == original

    def test_creates_valid_structure_from_empty(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar()
        reg.register(claude_project, _CMD)
        data = _read_settings(claude_project)
        assert isinstance(data.get("hooks"), dict)
        assert isinstance(data["hooks"].get("SessionStart"), list)

    @pytest.mark.requires_symlinks
    def test_rejects_symlinked_claude_dir_escape(self, claude_project: Path) -> None:
        outside = claude_project.parent / f"{claude_project.name}-outside-claude"
        outside.mkdir()
        protected = outside / "settings.json"
        protected.write_text("DO_NOT_OVERWRITE\n", encoding="utf-8")
        (claude_project / ".claude").rmdir()
        try:
            os.symlink(outside, claude_project / ".claude", target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported on this platform")

        reg = ClaudeCodeHookRegistrar()
        with pytest.raises(ValueError, match="escapes project root"):
            reg.register(claude_project, _CMD)

        assert protected.read_text(encoding="utf-8") == "DO_NOT_OVERWRITE\n"

    @pytest.mark.requires_symlinks
    def test_rejects_symlinked_settings_file_escape(self, claude_project: Path) -> None:
        outside = claude_project.parent / f"{claude_project.name}-outside-settings"
        outside.mkdir()
        protected = outside / "settings.json"
        protected.write_text("DO_NOT_OVERWRITE\n", encoding="utf-8")
        _settings_path(claude_project).parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(protected, _settings_path(claude_project))
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported on this platform")

        reg = ClaudeCodeHookRegistrar()
        with pytest.raises(ValueError, match="escapes project root"):
            reg.register(claude_project, _CMD)

        assert protected.read_text(encoding="utf-8") == "DO_NOT_OVERWRITE\n"


class TestUnregister:
    def test_removes_only_spec_kitty_entry(self, claude_project: Path) -> None:
        other_cmd = "other-tool start"
        _write_settings(
            claude_project,
            {
                "hooks": {
                    "SessionStart": [
                        {"hooks": [{"type": "command", "command": other_cmd}]},
                        {"hooks": [{"type": "command", "command": _CMD}]},
                    ]
                }
            },
        )
        reg = ClaudeCodeHookRegistrar()
        reg.unregister(claude_project, _CMD)
        data = _read_settings(claude_project)
        entries = data["hooks"]["SessionStart"]
        commands = [
            h.get("command")
            for entry in entries
            for h in entry.get("hooks", [])
        ]
        assert _CMD not in commands
        assert other_cmd in commands

    def test_leaves_empty_list_when_last_entry_removed(
        self, claude_project: Path
    ) -> None:
        _write_settings(
            claude_project,
            {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": _CMD}]}]}},
        )
        reg = ClaudeCodeHookRegistrar()
        reg.unregister(claude_project, _CMD)
        data = _read_settings(claude_project)
        # Key must be kept, not deleted, but list may be empty or have empty entries
        assert "SessionStart" in data["hooks"]

    def test_noop_when_entry_not_present(self, claude_project: Path) -> None:
        _write_settings(
            claude_project,
            {"hooks": {"SessionStart": []}},
        )
        original_mtime = _settings_path(claude_project).stat().st_mtime
        reg = ClaudeCodeHookRegistrar()
        reg.unregister(claude_project, _CMD)  # no-op
        # File should not be rewritten if command wasn't found
        new_mtime = _settings_path(claude_project).stat().st_mtime
        assert new_mtime == original_mtime

    def test_noop_when_file_absent(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar()
        reg.unregister(claude_project, _CMD)  # Must not raise


class TestIsRegistered:
    def test_returns_true_when_registered(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar()
        reg.register(claude_project, _CMD)
        assert reg.is_registered(claude_project, _CMD) is True

    def test_returns_false_when_not_registered(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar()
        assert reg.is_registered(claude_project, _CMD) is False

    def test_returns_false_when_file_absent(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar()
        assert reg.is_registered(claude_project, _CMD) is False


class TestAtomicWrite:
    def test_temp_file_cleaned_up_on_write_error(self, claude_project: Path) -> None:
        """All writes are atomic: temp file is removed on error."""
        reg = ClaudeCodeHookRegistrar()
        settings = _settings_path(claude_project)

        with patch("os.replace", side_effect=OSError("disk full")), pytest.raises(OSError):
            reg.register(claude_project, _CMD)

        # No .tmp file should be left behind, including the shared writer's
        # hidden temp-file prefix.
        assert not list(settings.parent.glob("*settings.json*.tmp"))


class TestStopEvent:
    """WP06 T024/T027 — registrar generalized to the Stop hook event key."""

    _STOP_CMD = "spec-kitty session-stop"

    def test_register_stop_hook(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar(STOP_EVENT)
        reg.register(claude_project, self._STOP_CMD)
        data = _read_settings(claude_project)
        commands = [
            h["command"]
            for entry in data["hooks"]["Stop"]
            for h in entry["hooks"]
        ]
        assert commands == [self._STOP_CMD]
        assert reg.is_registered(claude_project, self._STOP_CMD) is True

    def test_stop_register_idempotent(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar(STOP_EVENT)
        reg.register(claude_project, self._STOP_CMD)
        reg.register(claude_project, self._STOP_CMD)
        data = _read_settings(claude_project)
        assert len(data["hooks"]["Stop"]) == 1

    def test_stop_preserves_foreign_stop_entries(self, claude_project: Path) -> None:
        _write_settings(
            claude_project,
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other-tool stop"}]}]}},
        )
        ClaudeCodeHookRegistrar(STOP_EVENT).register(claude_project, self._STOP_CMD)
        data = _read_settings(claude_project)
        commands = [
            h["command"]
            for entry in data["hooks"]["Stop"]
            for h in entry["hooks"]
        ]
        assert "other-tool stop" in commands
        assert self._STOP_CMD in commands

    def test_stop_register_preserves_session_start_entries(self, claude_project: Path) -> None:
        """Registering the Stop hook never touches existing SessionStart entries."""
        ClaudeCodeHookRegistrar(SESSION_START_EVENT).register(claude_project, _CMD)
        ClaudeCodeHookRegistrar(STOP_EVENT).register(claude_project, self._STOP_CMD)
        data = _read_settings(claude_project)
        start_commands = [
            h["command"]
            for entry in data["hooks"]["SessionStart"]
            for h in entry["hooks"]
        ]
        assert start_commands == [_CMD]
        assert ClaudeCodeHookRegistrar(SESSION_START_EVENT).is_registered(claude_project, _CMD)

    def test_stop_is_registered_independent_of_session_start(self, claude_project: Path) -> None:
        ClaudeCodeHookRegistrar(SESSION_START_EVENT).register(claude_project, _CMD)
        assert ClaudeCodeHookRegistrar(STOP_EVENT).is_registered(claude_project, _CMD) is False

    def test_stop_unregister_removes_only_stop_entry(self, claude_project: Path) -> None:
        ClaudeCodeHookRegistrar(SESSION_START_EVENT).register(claude_project, _CMD)
        ClaudeCodeHookRegistrar(STOP_EVENT).register(claude_project, self._STOP_CMD)
        ClaudeCodeHookRegistrar(STOP_EVENT).unregister(claude_project, self._STOP_CMD)
        assert ClaudeCodeHookRegistrar(STOP_EVENT).is_registered(claude_project, self._STOP_CMD) is False
        assert ClaudeCodeHookRegistrar(SESSION_START_EVENT).is_registered(claude_project, _CMD) is True

    def test_default_event_key_is_session_start(self, claude_project: Path) -> None:
        """Backward compatibility: no-arg construction still targets SessionStart."""
        ClaudeCodeHookRegistrar().register(claude_project, _CMD)
        data = _read_settings(claude_project)
        assert "SessionStart" in data["hooks"]
        assert "Stop" not in data["hooks"]
