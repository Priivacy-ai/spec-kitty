"""Tests for WP02: Active-Mission Fallback Removal (feature 054).

Validates:
- FileManifest no longer has active_mission attribute
- verify_enhanced resolves mission from feature-level meta.json
- mission CLI shows 'No active feature detected' when no feature context
"""

from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest


# --------------------------------------------------------------------------- #
# verify_enhanced tests
# --------------------------------------------------------------------------- #

def test_verify_with_research_feature(tmp_path: Path) -> None:
    """Verify resolves mission to 'research' when feature meta.json says so."""
    from rich.console import Console

    from specify_cli.verify_enhanced import run_enhanced_verify

    # Set up project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    kittify_dir = project_root / ".kittify"
    kittify_dir.mkdir()

    # Do NOT create .kittify/active-mission (the whole point of this test)

    # Create feature directory with meta.json specifying research mission
    feature_dir = project_root / "kitty-specs" / "099-research-feature"
    feature_dir.mkdir(parents=True)
    meta = {"mission": "research", "feature_slug": "099-research-feature", "created_at": "2026-01-01"}
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    console = Console(file=open("/dev/null", "w"))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = types.SimpleNamespace(stdout="main\n", returncode=0)

        result = run_enhanced_verify(
            repo_root=project_root,
            project_root=project_root,
            cwd=project_root,
            feature="099-research-feature",
            json_output=True,
            check_files=False,
            console=console,
            feature_dir=feature_dir,
        )

    assert result["environment"]["active_mission"] == "research"


def test_verify_without_feature_dir_shows_no_context(tmp_path: Path) -> None:
    """Without feature_dir, active_mission should say 'no feature context'."""
    from rich.console import Console

    from specify_cli.verify_enhanced import run_enhanced_verify

    project_root = tmp_path / "project"
    project_root.mkdir()
    kittify_dir = project_root / ".kittify"
    kittify_dir.mkdir()

    console = Console(file=open("/dev/null", "w"))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = types.SimpleNamespace(stdout="main\n", returncode=0)

        result = run_enhanced_verify(
            repo_root=project_root,
            project_root=project_root,
            cwd=project_root,
            feature=None,
            json_output=True,
            check_files=False,
            console=console,
        )

    assert result["environment"]["active_mission"] == "no feature context"


def test_verify_resolves_mission_from_feature_slug(tmp_path: Path) -> None:
    """When feature slug is provided (not feature_dir), mission resolves from kitty-specs."""
    from rich.console import Console

    from specify_cli.verify_enhanced import run_enhanced_verify

    project_root = tmp_path / "project"
    project_root.mkdir()
    kittify_dir = project_root / ".kittify"
    kittify_dir.mkdir()

    feature_dir = project_root / "kitty-specs" / "042-my-feature"
    feature_dir.mkdir(parents=True)
    meta = {"mission": "documentation", "feature_slug": "042-my-feature", "created_at": "2026-01-01"}
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    console = Console(file=open("/dev/null", "w"))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = types.SimpleNamespace(stdout="main\n", returncode=0)

        result = run_enhanced_verify(
            repo_root=project_root,
            project_root=project_root,
            cwd=project_root,
            feature="042-my-feature",
            json_output=True,
            check_files=False,
            console=console,
        )

    assert result["environment"]["active_mission"] == "documentation"


# --------------------------------------------------------------------------- #
# mission CLI: current command – no-feature-context test
# --------------------------------------------------------------------------- #

def test_mission_current_no_feature_shows_message(tmp_path: Path) -> None:
    """When no feature is detected, 'mission current' should show a clear message."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.mission import app

    runner = CliRunner()

    with (
        patch("specify_cli.cli.commands.mission.get_project_root_or_exit", return_value=tmp_path),
        patch("specify_cli.cli.commands.mission.check_version_compatibility"),
        patch("specify_cli.cli.commands.mission._detect_current_feature", return_value=None),
    ):
        result = runner.invoke(app, ["current"])

    assert result.exit_code == 1
    assert "No active feature detected" in result.output
