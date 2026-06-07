"""T020 — Tests for ClaudeCodeHookRegistrar.

Covers all settings.json edge cases: absent, empty, malformed, idempotency,
preservation of other entries, and atomic writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.session_presence.hooks.claude_code_hook import ClaudeCodeHookRegistrar

_CMD = "spec-kitty session-start"
_SETTINGS_REL = ".claude/settings.json"


def _settings_path(project_root: Path) -> Path:
    return project_root / _SETTINGS_REL


def _read_settings(project_root: Path) -> dict:  # type: ignore[type-arg]
    return json.loads(_settings_path(project_root).read_text(encoding="utf-8"))


def _write_settings(project_root: Path, data: dict) -> None:  # type: ignore[type-arg]
    _settings_path(project_root).parent.mkdir(parents=True, exist_ok=True)
    _settings_path(project_root).write_text(json.dumps(data), encoding="utf-8")


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

    def test_creates_valid_structure_from_empty(self, claude_project: Path) -> None:
        reg = ClaudeCodeHookRegistrar()
        reg.register(claude_project, _CMD)
        data = _read_settings(claude_project)
        assert isinstance(data.get("hooks"), dict)
        assert isinstance(data["hooks"].get("SessionStart"), list)


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

        # No .tmp file should be left behind
        tmp_file = settings.with_suffix(".tmp")
        assert not tmp_file.exists()
