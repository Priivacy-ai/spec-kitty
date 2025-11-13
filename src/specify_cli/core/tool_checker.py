"""Tool availability helpers for Spec Kitty."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Mapping, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.cli import StepTracker

from specify_cli.core.config import AGENT_TOOL_REQUIREMENTS

CLAUDE_LOCAL_PATH = Path.home() / ".claude" / "local" / "claude"


def check_tool_for_tracker(tool: str, tracker: "StepTracker") -> bool:
    """Check if a tool is installed and update the provided StepTracker instance."""
    if shutil.which(tool):
        tracker.complete(tool, "available")
        return True
    tracker.error(tool, "not found")
    return False


def check_tool(tool: str, install_hint: str) -> bool:
    """Return True when the tool is available on PATH (with Claude CLI override)."""
    if tool == "claude" and CLAUDE_LOCAL_PATH.exists() and CLAUDE_LOCAL_PATH.is_file():
        return True
    return shutil.which(tool) is not None


def get_tool_version(command: str) -> str | None:
    """Return the version string for a tool if the convention '<tool> --version' succeeds."""
    try:
        result = subprocess.run(
            [command, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None

    output = (result.stdout or result.stderr or "").strip()
    return output or None


def check_all_tools(
    requirements: Mapping[str, Tuple[str, str]] | None = None,
) -> Dict[str, Tuple[bool, str]]:
    """Check tool availability for all known agents, returning {agent: (ok, detail)}."""
    results: Dict[str, Tuple[bool, str]] = {}
    entries = requirements or AGENT_TOOL_REQUIREMENTS
    for agent, (tool, url) in entries.items():
        ok = check_tool(tool, url)
        detail = get_tool_version(tool) if ok else url
        results[agent] = (ok, detail or url)
    return results


__all__ = [
    "check_all_tools",
    "check_tool",
    "check_tool_for_tracker",
    "get_tool_version",
]
