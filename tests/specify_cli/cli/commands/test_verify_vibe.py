"""Tests for verify-setup vibe detection (T027).

Confirms that TOOL_LABELS includes vibe and that check_tool_for_tracker
correctly reports it as present or absent.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from specify_cli.cli.commands.verify import TOOL_LABELS
from specify_cli.core.tool_checker import check_tool_for_tracker
from specify_cli.cli import StepTracker

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# T027-A: TOOL_LABELS registry includes vibe
# ---------------------------------------------------------------------------


def test_tool_labels_includes_vibe() -> None:
    """TOOL_LABELS must include an entry with key 'vibe'."""
    keys = [key for key, _label in TOOL_LABELS]
    assert "vibe" in keys, f"'vibe' not found in TOOL_LABELS; found: {keys}"


def test_tool_labels_vibe_label() -> None:
    """The vibe entry in TOOL_LABELS must have a recognizable label."""
    label_map = dict(TOOL_LABELS)
    assert "vibe" in label_map
    assert "Vibe" in label_map["vibe"] or "vibe" in label_map["vibe"].lower()


# ---------------------------------------------------------------------------
# T027-B: vibe detected when on PATH
# ---------------------------------------------------------------------------


def test_check_tool_vibe_present() -> None:
    """check_tool_for_tracker marks vibe as available when shutil.which returns a path."""
    tracker = StepTracker("test")
    tracker.add("vibe", "Mistral Vibe")

    with patch("specify_cli.core.tool_checker.shutil.which", return_value="/usr/local/bin/vibe"):
        result = check_tool_for_tracker("vibe", tracker)

    assert result is True


# ---------------------------------------------------------------------------
# T027-C: vibe reported missing when not on PATH
# ---------------------------------------------------------------------------


def test_check_tool_vibe_absent() -> None:
    """check_tool_for_tracker marks vibe as not found when shutil.which returns None."""
    tracker = StepTracker("test")
    tracker.add("vibe", "Mistral Vibe")

    with patch("specify_cli.core.tool_checker.shutil.which", return_value=None):
        result = check_tool_for_tracker("vibe", tracker)

    assert result is False


# ---------------------------------------------------------------------------
# T027-D: AGENT_TOOL_REQUIREMENTS has a stable install URL for vibe
# ---------------------------------------------------------------------------


def test_agent_tool_requirements_vibe_url() -> None:
    """AGENT_TOOL_REQUIREMENTS['vibe'] must point to a stable GitHub URL."""
    from specify_cli.core.config import AGENT_TOOL_REQUIREMENTS

    assert "vibe" in AGENT_TOOL_REQUIREMENTS
    tool_name, url = AGENT_TOOL_REQUIREMENTS["vibe"]
    assert tool_name == "vibe"
    assert "github.com" in url or "mistral" in url, (
        f"Expected stable URL for vibe, got: {url}"
    )
