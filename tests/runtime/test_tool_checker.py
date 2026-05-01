"""Scope: tool checker unit tests — no real git or subprocesses."""

import pytest
import sys


from specify_cli.cli.step_tracker import StepTracker
import specify_cli.core.tool_checker as tool_checker
from specify_cli.core.tool_checker import (
    check_all_tools,
    check_tool,
    check_tool_for_tracker,
    get_tool_version,
)

pytestmark = pytest.mark.fast


class DummyTracker(StepTracker):
    def __init__(self):
        super().__init__("dummy")
        self.completed = []
        self.errored = []

    def complete(self, key, detail=""):
        super().complete(key, detail)
        self.completed.append((key, detail))

    def error(self, key, detail=""):
        super().error(key, detail)
        self.errored.append((key, detail))


def test_check_tool_for_tracker_reports(monkeypatch):
    """Present tool completes tracker step; missing tool errors it."""
    # Arrange
    tracker = DummyTracker()
    monkeypatch.setattr(tool_checker.shutil, "which", lambda cmd: "/usr/bin/fake" if cmd == "codex" else None)
    # Assumption check
    assert tracker.completed == []
    # Act / Assert
    assert check_tool_for_tracker("codex", tracker) is True
    assert check_tool_for_tracker("missing", tracker) is False
    assert tracker.completed and tracker.errored


def test_check_tool_prefers_claude_override(tmp_path, monkeypatch):
    """CLAUDE_LOCAL_PATH override is preferred over PATH lookup."""
    # Arrange
    fake_cli = tmp_path / "claude"
    fake_cli.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(tool_checker, "CLAUDE_LOCAL_PATH", fake_cli)
    monkeypatch.setattr(tool_checker.shutil, "which", lambda _: None)
    # Assumption check
    assert fake_cli.exists()
    # Act / Assert
    assert check_tool("claude", "hint") is True
    assert check_tool("totally-missing", "hint") is False


def test_get_tool_version_uses_command(monkeypatch):
    """get_tool_version returns a non-empty version string for the Python binary."""
    # Arrange — use current Python executable
    # Assumption check
    assert sys.executable
    # Act
    version = get_tool_version(sys.executable)
    # Assert
    assert version and "Python" in version


def test_check_all_tools_accepts_custom_requirements(monkeypatch):
    """check_all_tools returns True/False entries for present/missing tools."""
    # Arrange
    monkeypatch.setattr(
        tool_checker.shutil,
        "which",
        lambda cmd: "/usr/bin/python" if cmd == sys.executable else None,
    )
    # Assumption check
    assert sys.executable
    # Act
    results = check_all_tools(
        {"py": (sys.executable, "https://example.com"), "missing": ("nope", "https://example.com")}
    )
    # Assert
    assert results["py"][0] is True
    assert results["missing"][0] is False
