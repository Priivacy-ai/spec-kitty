"""Tests for dashboard diagnostics helpers."""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

import specify_cli
from specify_cli.dashboard import diagnostics


def _install_manifest_stubs(monkeypatch, worktree_path: Path) -> None:
    """Provide lightweight manifest + worktree stubs for diagnostics tests."""

    class FakeManifest:
        def __init__(self, kittify_dir: Path) -> None:
            self.kittify_dir = kittify_dir
            self.active_mission = "software-dev"

        def get_expected_files(self) -> dict[str, list[str]]:
            return {
                "commands": ["commands/tasks.md"],
                "templates": ["templates/base.md"],
            }

        def check_files(self) -> dict[str, dict[str, str]]:
            return {
                "present": {"commands/tasks.md": "commands"},
                "missing": {"templates/base.md": "templates"},
                "modified": {},
                "extra": [],
            }

    class FakeWorktreeStatus:
        def __init__(self, repo_root: Path) -> None:
            self.repo_root = repo_root

        def get_worktree_summary(self) -> dict[str, int]:
            return {
                "total_features": 1,
                "active_worktrees": 1,
                "merged_features": 0,
                "in_development": 1,
                "not_started": 0,
            }

        def get_all_features(self) -> list[str]:
            return ["004-modular-code-refactoring"]

        def get_feature_status(self, feature: str) -> dict[str, object]:
            return {
                "state": "in_development",
                "branch_exists": True,
                "branch_merged": False,
                "worktree_exists": True,
                "worktree_path": str(worktree_path),
                "artifacts_in_main": ["spec.md"],
                "artifacts_in_worktree": ["spec.md"],
            }

    fake_module = types.ModuleType("specify_cli.manifest")
    fake_module.FileManifest = FakeManifest  # type: ignore[attr-defined]
    fake_module.WorktreeStatus = FakeWorktreeStatus  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "specify_cli.manifest", fake_module)

    # Also ensure the relative import used inside run_diagnostics picks up the stub.
    monkeypatch.setitem(sys.modules, "specify_cli.dashboard.manifest", fake_module)


class _DummyAcceptanceError(Exception):
    """Lightweight exception stand-in for AcceptanceError."""


def _configure_common_patches(monkeypatch, worktree_path: Path) -> None:
    """Set up shared dependency stubs."""
    _install_manifest_stubs(monkeypatch, worktree_path)

    # Create fake acceptance module for the corrected import path
    fake_acceptance = types.ModuleType("specify_cli.acceptance")
    fake_acceptance.detect_feature_slug = lambda repo_root, cwd: "004-modular-code-refactoring"  # type: ignore[attr-defined]
    fake_acceptance.AcceptanceError = _DummyAcceptanceError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "specify_cli.acceptance", fake_acceptance)


def test_run_diagnostics_reports_manifest_and_worktree_state(monkeypatch, tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / ".kittify").mkdir()
    worktree_dir = project_dir / ".worktrees"
    worktree_dir.mkdir()

    _configure_common_patches(monkeypatch, worktree_dir)

    def fake_run(args, cwd=None, capture_output=False, text=False, check=False):  # noqa: D401 - pytest helper
        """Return the active branch name for diagnostics."""
        assert args == ['git', 'branch', '--show-current']
        assert cwd == project_dir
        return types.SimpleNamespace(stdout='feature/testing\n', returncode=0)

    monkeypatch.setattr(diagnostics.subprocess, "run", fake_run)

    result = diagnostics.run_diagnostics(project_dir)

    assert result["git_branch"] == "feature/testing"
    assert result["worktrees_exist"] is True
    assert result["file_integrity"]["total_expected"] == 2
    assert result["file_integrity"]["total_missing"] == 1
    assert result["worktree_overview"]["active_worktrees"] == 1
    assert result["all_features"][0]["name"] == "004-modular-code-refactoring"
    assert result["current_feature"]["detected"] is True
    assert any(msg.startswith("Mission integrity") for msg in result["observations"])


def test_run_diagnostics_records_git_branch_errors(monkeypatch, tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    worktree_dir = project_dir / ".worktrees"
    worktree_dir.mkdir()

    _configure_common_patches(monkeypatch, worktree_dir)

    def failing_run(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, ['git', 'branch', '--show-current'])

    monkeypatch.setattr(diagnostics.subprocess, "run", failing_run)

    result = diagnostics.run_diagnostics(project_dir)

    assert result["git_branch"] is None
    assert "Could not detect git branch" in result["issues"]
    assert result["current_feature"]["detected"] is True
