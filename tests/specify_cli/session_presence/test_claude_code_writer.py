"""T020 — Tests for ClaudeCodeWriter.

Verifies that ClaudeCodeWriter delegates to both MarkdownRulesWriter and
ClaudeCodeHookRegistrar, and that has_presence() requires both artefacts.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.session_presence.content import SessionPresenceContent
from specify_cli.session_presence.writers.claude_code import (
    SESSION_START_CMD,
    SESSION_STOP_CMD,
    ClaudeCodeWriter,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _content() -> SessionPresenceContent:
    return SessionPresenceContent("3.2.0", "test-project", "healthy", None)


class TestWrite:
    def test_write_calls_super_and_hook_registrar(self, tmp_path: Path) -> None:
        """write() must call MarkdownRulesWriter.write() AND ClaudeCodeHookRegistrar.register()."""
        writer = ClaudeCodeWriter()
        with (
            patch(
                "specify_cli.session_presence.writers.claude_code.MarkdownRulesWriter.write"
            ) as mock_md_write,
            patch(
                "specify_cli.session_presence.writers.claude_code.ClaudeCodeHookRegistrar.register"
            ) as mock_hook_reg,
        ):
            writer.write(tmp_path, _content())
        mock_md_write.assert_called_once_with(tmp_path, _content())
        registered = [call.args for call in mock_hook_reg.call_args_list]
        assert (tmp_path, SESSION_START_CMD) in registered
        assert (tmp_path, SESSION_STOP_CMD) in registered


class TestRemove:
    def test_remove_calls_super_and_hook_unregistrar(self, tmp_path: Path) -> None:
        """remove() must call MarkdownRulesWriter.remove() AND ClaudeCodeHookRegistrar.unregister()."""
        writer = ClaudeCodeWriter()
        with (
            patch(
                "specify_cli.session_presence.writers.claude_code.MarkdownRulesWriter.remove"
            ) as mock_md_remove,
            patch(
                "specify_cli.session_presence.writers.claude_code.ClaudeCodeHookRegistrar.unregister"
            ) as mock_hook_unreg,
        ):
            writer.remove(tmp_path)
        mock_md_remove.assert_called_once_with(tmp_path)
        unregistered = [call.args for call in mock_hook_unreg.call_args_list]
        assert (tmp_path, SESSION_START_CMD) in unregistered
        assert (tmp_path, SESSION_STOP_CMD) in unregistered


class TestHasPresenceStopHook:
    """WP06 — has_presence() additionally requires the Stop hook."""

    def test_false_when_stop_hook_missing(self, claude_project: Path) -> None:
        """A pre-WP06 project (SessionStart only) reports incomplete presence."""
        from specify_cli.session_presence.content import SECTION_CLOSE, SECTION_OPEN

        (claude_project / ".claude" / "CLAUDE.md").write_text(
            f"{SECTION_OPEN}\nSome content\n{SECTION_CLOSE}\n", encoding="utf-8"
        )
        (claude_project / ".claude" / "settings.json").write_text(
            '{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "spec-kitty session-start"}]}]}}',
            encoding="utf-8",
        )
        assert ClaudeCodeWriter().has_presence(claude_project) is False

    def test_write_registers_stop_hook(self, claude_project: Path) -> None:
        import json as _json

        ClaudeCodeWriter().write(claude_project, _content())
        data = _json.loads(
            (claude_project / ".claude" / "settings.json").read_text(encoding="utf-8")
        )
        stop_commands = [
            h["command"] for entry in data["hooks"]["Stop"] for h in entry["hooks"]
        ]
        assert stop_commands == [SESSION_STOP_CMD]


class TestHasPresence:
    def test_false_when_claude_md_section_missing(self, claude_project: Path) -> None:
        """has_presence() is False when CLAUDE.md section is missing, even if hook exists."""
        # Register hook but don't write CLAUDE.md
        settings = claude_project / ".claude" / "settings.json"
        settings.write_text(
            '{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "spec-kitty session-start"}]}]}}',
            encoding="utf-8",
        )
        writer = ClaudeCodeWriter()
        assert writer.has_presence(claude_project) is False

    def test_false_when_hook_missing(self, claude_project: Path) -> None:
        """has_presence() is False when hook is missing, even if CLAUDE.md section exists."""
        from specify_cli.session_presence.content import SECTION_CLOSE, SECTION_OPEN

        claude_md = claude_project / ".claude" / "CLAUDE.md"
        claude_md.write_text(
            f"{SECTION_OPEN}\nSome content\n{SECTION_CLOSE}\n", encoding="utf-8"
        )
        # No settings.json
        writer = ClaudeCodeWriter()
        assert writer.has_presence(claude_project) is False

    def test_true_when_both_present(self, claude_project: Path) -> None:
        """has_presence() is True only when BOTH artefacts are present."""
        writer = ClaudeCodeWriter()
        writer.write(claude_project, _content())
        assert writer.has_presence(claude_project) is True

    def test_false_when_neither_present(self, claude_project: Path) -> None:
        """has_presence() is False when neither artefact is present."""
        writer = ClaudeCodeWriter()
        assert writer.has_presence(claude_project) is False
