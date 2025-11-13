import sys
from pathlib import Path

import pytest

from specify_cli.cli.step_tracker import StepTracker
import specify_cli.core.tool_checker as tool_checker
from specify_cli.core.tool_checker import (
    check_all_tools,
    check_tool,
    check_tool_for_tracker,
    get_tool_version,
)


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
    tracker = DummyTracker()
    monkeypatch.setattr(tool_checker.shutil, "which", lambda cmd: "/usr/bin/fake" if cmd == "codex" else None)

    assert check_tool_for_tracker("codex", tracker) is True
    assert check_tool_for_tracker("missing", tracker) is False
    assert tracker.completed and tracker.errored


def test_check_tool_prefers_claude_override(tmp_path, monkeypatch):
    fake_cli = tmp_path / "claude"
    fake_cli.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(tool_checker, "CLAUDE_LOCAL_PATH", fake_cli)
    monkeypatch.setattr(tool_checker.shutil, "which", lambda _: None)

    assert check_tool("claude", "hint") is True
    assert check_tool("totally-missing", "hint") is False


def test_get_tool_version_uses_command(monkeypatch):
    version = get_tool_version(sys.executable)
    assert version and "Python" in version


def test_check_all_tools_accepts_custom_requirements(monkeypatch):
    monkeypatch.setattr(
        tool_checker.shutil,
        "which",
        lambda cmd: "/usr/bin/python" if cmd == sys.executable else None,
    )
    results = check_all_tools({"py": (sys.executable, "https://example.com"), "missing": ("nope", "https://example.com")})
    assert results["py"][0] is True
    assert results["missing"][0] is False
