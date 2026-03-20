"""Tests for WP02: Active-Mission Fallback Removal (feature 054).

Validates:
- FileManifest no longer has active_mission attribute
- verify_enhanced resolves mission from feature-level meta.json
- mission CLI shows 'No active feature detected' when no feature context
- Production callers (verify.py, api.py) wire feature_dir through
"""

from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# --------------------------------------------------------------------------- #
# _resolve_feature_dir (verify.py helper) tests
# --------------------------------------------------------------------------- #

def test_resolve_feature_dir_with_explicit_feature(tmp_path: Path) -> None:
    """_resolve_feature_dir returns feature directory when given an explicit slug."""
    from specify_cli.cli.commands.verify import _resolve_feature_dir

    project_root = tmp_path / "project"
    feature_dir = project_root / "kitty-specs" / "099-research-feature"
    feature_dir.mkdir(parents=True)

    # Mock detect_feature to return a context with the feature directory
    mock_ctx = MagicMock()
    mock_ctx.slug = "099-research-feature"
    mock_ctx.directory = feature_dir

    with patch("specify_cli.cli.commands.verify.detect_feature", return_value=mock_ctx):
        result = _resolve_feature_dir(project_root, feature="099-research-feature")

    assert result == feature_dir


def test_resolve_feature_dir_returns_none_when_no_feature(tmp_path: Path) -> None:
    """_resolve_feature_dir returns None when no feature can be detected."""
    from specify_cli.cli.commands.verify import _resolve_feature_dir

    with patch("specify_cli.cli.commands.verify.detect_feature", return_value=None):
        result = _resolve_feature_dir(tmp_path)

    assert result is None


def test_resolve_feature_dir_returns_none_on_exception(tmp_path: Path) -> None:
    """_resolve_feature_dir returns None when detect_feature raises."""
    from specify_cli.cli.commands.verify import _resolve_feature_dir

    with patch("specify_cli.cli.commands.verify.detect_feature", side_effect=RuntimeError("boom")):
        result = _resolve_feature_dir(tmp_path)

    assert result is None


# --------------------------------------------------------------------------- #
# Realistic worktree test: NO detect_feature mock
# --------------------------------------------------------------------------- #


def test_resolve_feature_dir_from_worktree_without_mock(tmp_path: Path) -> None:
    """_resolve_feature_dir finds features when called from a worktree CWD.

    This test creates a realistic directory layout:
      main_repo/
        .git/                        (real git dir marker)
        .git/worktrees/my-wt/        (worktree gitdir)
        .kittify/                    (project marker)
        kitty-specs/099-research-feature/meta.json
      worktree/
        .git  (file: "gitdir: <main>/.git/worktrees/my-wt")

    Calling _resolve_feature_dir(worktree_root, feature=...) must still
    resolve the feature directory under main_repo/kitty-specs/ because
    worktrees lack kitty-specs/ via sparse checkout.
    """
    from specify_cli.cli.commands.verify import _resolve_feature_dir

    # --- Set up main repo ---
    main_repo = tmp_path / "main_repo"
    main_repo.mkdir()
    (main_repo / ".git").mkdir()  # Real .git directory (not a file)
    (main_repo / ".kittify").mkdir()

    feature_dir = main_repo / "kitty-specs" / "099-research-feature"
    feature_dir.mkdir(parents=True)
    meta = {"mission": "research", "feature_slug": "099-research-feature"}
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    # --- Set up git worktree gitdir ---
    wt_gitdir = main_repo / ".git" / "worktrees" / "my-wt"
    wt_gitdir.mkdir(parents=True)

    # --- Set up the worktree root ---
    worktree_root = tmp_path / "worktree"
    worktree_root.mkdir()
    # .git is a *file* with a gitdir: pointer (this is how real worktrees work)
    (worktree_root / ".git").write_text(f"gitdir: {wt_gitdir}\n")
    # Worktrees have .kittify/ (shared/linked) but NOT kitty-specs/
    (worktree_root / ".kittify").mkdir()
    # Do NOT create kitty-specs/ here — that's the whole point

    # Mock git branch detection to avoid needing a real git repo
    with patch("specify_cli.core.feature_detection._detect_from_git_branch", return_value=None):
        result = _resolve_feature_dir(worktree_root, feature="099-research-feature")

    assert result is not None, (
        "_resolve_feature_dir returned None; feature detection failed to "
        "resolve through worktree .git pointer to main repo kitty-specs/"
    )
    assert result == feature_dir
    assert result.is_dir()


def test_diagnostics_mode_resolves_main_repo_root(tmp_path: Path) -> None:
    """_run_diagnostics_mode uses locate_project_root() (not Path.cwd()).

    When CWD is a worktree, locate_project_root() resolves the main repo
    root where kitty-specs/ lives, enabling feature detection.
    """
    from specify_cli.cli.commands.verify import _run_diagnostics_mode

    main_repo = tmp_path / "main_repo"
    main_repo.mkdir()
    (main_repo / ".kittify").mkdir()

    feature_dir = main_repo / "kitty-specs" / "099-research-feature"
    feature_dir.mkdir(parents=True)
    meta = {"mission": "research", "feature_slug": "099-research-feature"}
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    captured_path = {}

    def fake_run_diagnostics(project_path, *, feature_dir=None):
        captured_path["project_path"] = project_path
        captured_path["feature_dir"] = feature_dir
        return {
            "project_path": str(project_path),
            "active_mission": "research" if feature_dir else "no feature context",
        }

    mock_ctx = MagicMock()
    mock_ctx.slug = "099-research-feature"
    mock_ctx.directory = feature_dir

    with (
        # locate_project_root returns main repo, not CWD
        patch("specify_cli.cli.commands.verify.locate_project_root", return_value=main_repo),
        patch("specify_cli.cli.commands.verify.detect_feature", return_value=mock_ctx),
        patch("specify_cli.cli.commands.verify.run_diagnostics", side_effect=fake_run_diagnostics),
    ):
        _run_diagnostics_mode(json_output=True, check_tools=False, feature="099-research-feature")

    # The project_path passed to run_diagnostics should be the main repo root,
    # NOT whatever Path.cwd() happens to be.
    assert captured_path["project_path"] == main_repo
    assert captured_path["feature_dir"] == feature_dir


# --------------------------------------------------------------------------- #
# verify_setup production caller wiring tests
# --------------------------------------------------------------------------- #

def test_verify_setup_passes_feature_dir_to_run_enhanced_verify(tmp_path: Path) -> None:
    """verify_setup should detect feature_dir and pass it to run_enhanced_verify."""
    from specify_cli.cli.commands.verify import verify_setup

    feature_dir = tmp_path / "kitty-specs" / "099-research-feature"
    feature_dir.mkdir(parents=True)

    mock_ctx = MagicMock()
    mock_ctx.slug = "099-research-feature"
    mock_ctx.directory = feature_dir

    captured_kwargs = {}

    def fake_run_enhanced_verify(**kwargs):
        captured_kwargs.update(kwargs)
        return {"environment": {"active_mission": "research"}}

    with (
        patch("specify_cli.cli.commands.verify.find_repo_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.verify.get_project_root_or_exit", return_value=tmp_path),
        patch("specify_cli.cli.commands.verify.check_version_compatibility"),
        patch("specify_cli.cli.commands.verify.detect_feature", return_value=mock_ctx),
        patch("specify_cli.cli.commands.verify.run_enhanced_verify", side_effect=fake_run_enhanced_verify),
    ):
        # Call with json_output to avoid console rendering issues, and skip tool checks
        verify_setup(
            feature="099-research-feature",
            json_output=True,
            check_files=False,
            check_tools=False,
            diagnostics=False,
        )

    assert captured_kwargs.get("feature_dir") == feature_dir


def test_diagnostics_mode_passes_feature_dir_to_run_diagnostics(tmp_path: Path) -> None:
    """_run_diagnostics_mode should detect feature_dir and pass it to run_diagnostics."""
    from specify_cli.cli.commands.verify import _run_diagnostics_mode

    feature_dir = tmp_path / "kitty-specs" / "099-research-feature"
    feature_dir.mkdir(parents=True)

    mock_ctx = MagicMock()
    mock_ctx.slug = "099-research-feature"
    mock_ctx.directory = feature_dir

    captured_kwargs = {}

    def fake_run_diagnostics(project_path, *, feature_dir=None):
        captured_kwargs["feature_dir"] = feature_dir
        return {
            "project_path": str(project_path),
            "active_mission": "research" if feature_dir else "no feature context",
        }

    with (
        patch("specify_cli.cli.commands.verify.detect_feature", return_value=mock_ctx),
        patch("specify_cli.cli.commands.verify.run_diagnostics", side_effect=fake_run_diagnostics),
    ):
        _run_diagnostics_mode(json_output=True, check_tools=False, feature="099-research-feature")

    assert captured_kwargs.get("feature_dir") == feature_dir


# --------------------------------------------------------------------------- #
# api.py handle_diagnostics wiring test
# --------------------------------------------------------------------------- #

def test_api_handle_diagnostics_passes_feature_dir(tmp_path: Path) -> None:
    """APIHandler.handle_diagnostics should detect active feature and pass feature_dir."""
    import io

    feature_dir = tmp_path / "kitty-specs" / "099-research-feature"
    feature_dir.mkdir(parents=True)

    captured_kwargs = {}

    def fake_run_diagnostics(project_path, *, feature_dir=None):
        captured_kwargs["feature_dir"] = feature_dir
        return {"active_mission": "research" if feature_dir else "no feature context"}

    def fake_scan_all_features(project_path):
        return [{"id": "099-research-feature", "path": "kitty-specs/099-research-feature"}]

    def fake_resolve_active_feature(project_path, features):
        return features[0] if features else None

    with (
        patch("specify_cli.dashboard.handlers.api.run_diagnostics", side_effect=fake_run_diagnostics),
        patch("specify_cli.dashboard.handlers.api.scan_all_features", side_effect=fake_scan_all_features),
        patch("specify_cli.dashboard.handlers.api.resolve_active_feature", side_effect=fake_resolve_active_feature),
    ):
        from specify_cli.dashboard.handlers.api import APIHandler

        handler = MagicMock(spec=APIHandler)
        handler.project_dir = str(tmp_path)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = io.BytesIO()

        # Call the unbound method with our mock handler
        APIHandler.handle_diagnostics(handler)

    assert captured_kwargs.get("feature_dir") == feature_dir
