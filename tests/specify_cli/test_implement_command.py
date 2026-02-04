"""Unit tests for implement command."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import typer

from specify_cli.cli.commands.implement import (
    _ensure_vcs_in_meta,
    detect_feature_context,
    find_wp_file,
    implement,
    validate_workspace_path,
)
from specify_cli.core.vcs import VCSBackend


def create_meta_json(feature_dir: Path, vcs: str = "git") -> Path:
    """Helper to create meta.json in a feature directory."""
    meta_path = feature_dir / "meta.json"
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta_content = {
        "feature_number": feature_dir.name.split("-")[0],
        "feature_slug": feature_dir.name,
        "created_at": "2026-01-17T00:00:00Z",
    }
    if vcs:
        meta_content["vcs"] = vcs
    meta_path.write_text(json.dumps(meta_content, indent=2))
    return meta_path


class TestDetectFeatureContext:
    """Tests for detect_feature_context()."""

    def test_detect_from_feature_branch(self, tmp_path):
        """Test detection from feature branch (###-feature-name)."""
        # Create minimal repo structure
        (tmp_path / ".kittify").mkdir()
        feature_dir = tmp_path / "kitty-specs" / "010-workspace-per-wp"
        feature_dir.mkdir(parents=True)

        with patch("specify_cli.tasks_support.find_repo_root") as mock_find_root:
            mock_find_root.return_value = tmp_path

            with patch("specify_cli.core.feature_detection._get_main_repo_root") as mock_main_root:
                mock_main_root.return_value = tmp_path

                with patch("specify_cli.core.feature_detection._detect_from_git_branch") as mock_git:
                    mock_git.return_value = "010-workspace-per-wp"

                    number, slug = detect_feature_context()

                    assert number == "010"
                    assert slug == "010-workspace-per-wp"

    def test_detect_from_wp_branch(self, tmp_path):
        """Test detection from WP branch (###-feature-name-WP##)."""
        # Create minimal repo structure
        (tmp_path / ".kittify").mkdir()
        feature_dir = tmp_path / "kitty-specs" / "010-workspace-per-wp"
        feature_dir.mkdir(parents=True)

        with patch("specify_cli.tasks_support.find_repo_root") as mock_find_root:
            mock_find_root.return_value = tmp_path

            with patch("specify_cli.core.feature_detection._get_main_repo_root") as mock_main_root:
                mock_main_root.return_value = tmp_path

                with patch("specify_cli.core.feature_detection._detect_from_git_branch") as mock_git:
                    # Git detection strips -WP## suffix automatically
                    mock_git.return_value = "010-workspace-per-wp"

                    number, slug = detect_feature_context()

                    assert number == "010"
                    # When on a WP branch, the full branch name is NOT returned,
                    # only the feature slug (minus -WP##)
                    # Pattern 2 extracts the feature slug without -WP##
                    assert slug == "010-workspace-per-wp"

    def test_detect_from_directory(self, tmp_path):
        """Test detection from current directory path."""
        # Create minimal repo structure
        (tmp_path / ".kittify").mkdir()
        feature_dir = tmp_path / "kitty-specs" / "010-test-feature" / "tasks"
        feature_dir.mkdir(parents=True)

        with patch("specify_cli.tasks_support.find_repo_root") as mock_find_root:
            mock_find_root.return_value = tmp_path

            with patch("subprocess.run") as mock_run:
                # Git command fails
                mock_run.return_value = MagicMock(returncode=1, stdout="")

                with patch("pathlib.Path.cwd") as mock_cwd:
                    mock_cwd.return_value = feature_dir

                    number, slug = detect_feature_context()

                    assert number == "010"
                    assert slug == "010-test-feature"

    def test_detect_failure(self):
        """Test failure when context cannot be detected."""
        with patch("subprocess.run") as mock_run:
            # Git command fails
            mock_run.return_value = MagicMock(returncode=1, stdout="")

            with patch("pathlib.Path.cwd") as mock_cwd:
                # Current directory doesn't contain feature pattern
                mock_cwd.return_value = Path("/repo/src/tests")

                with pytest.raises(typer.Exit):
                    detect_feature_context()


class TestFindWpFile:
    """Tests for find_wp_file()."""

    def test_find_wp_file_success(self, tmp_path):
        """Test finding WP file successfully."""
        # Create test structure
        tasks_dir = tmp_path / "kitty-specs" / "010-feature" / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_file = tasks_dir / "WP01-setup.md"
        wp_file.write_text("# WP01")

        result = find_wp_file(tmp_path, "010-feature", "WP01")

        assert result == wp_file

    def test_find_wp_file_not_found(self, tmp_path):
        """Test error when WP file not found."""
        # Create tasks dir but no WP file
        tasks_dir = tmp_path / "kitty-specs" / "010-feature" / "tasks"
        tasks_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="WP file not found"):
            find_wp_file(tmp_path, "010-feature", "WP01")

    def test_find_wp_file_tasks_dir_missing(self, tmp_path):
        """Test error when tasks directory doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Tasks directory not found"):
            find_wp_file(tmp_path, "010-feature", "WP01")


class TestValidateWorkspacePath:
    """Tests for validate_workspace_path()."""

    def test_path_doesnt_exist(self, tmp_path):
        """Test when workspace path doesn't exist (should create)."""
        workspace = tmp_path / "workspace"

        result = validate_workspace_path(workspace, "WP01")

        assert result is False  # Should create

    def test_path_exists_valid_worktree(self, tmp_path):
        """Test when workspace exists and is valid worktree (should reuse)."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("subprocess.run") as mock_run:
            # git rev-parse succeeds (valid worktree)
            mock_run.return_value = MagicMock(returncode=0)

            result = validate_workspace_path(workspace, "WP01")

            assert result is True  # Reuse existing
            mock_run.assert_called_once()

    def test_path_exists_invalid_worktree(self, tmp_path):
        """Test when workspace exists but is not valid worktree (error)."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("subprocess.run") as mock_run:
            # git rev-parse fails (not a worktree)
            mock_run.return_value = MagicMock(returncode=1)

            with pytest.raises(typer.Exit):
                validate_workspace_path(workspace, "WP01")


class TestImplementCommand:
    """Integration tests for implement command."""

    def test_implement_no_dependencies(self, tmp_path):
        """Test implement WP01 creates workspace from main."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01"
        )

        # Workspace path that will be "created"
        workspace_path = tmp_path / ".worktrees" / "010-feature-WP01"

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                # Mock VCS detection to return git
                with patch("specify_cli.cli.commands.implement.get_vcs") as mock_get_vcs:
                    mock_vcs = MagicMock()
                    mock_vcs.backend = VCSBackend.GIT
                    mock_vcs.get_workspace_info.return_value = None  # Workspace doesn't exist
                    mock_vcs.create_workspace.return_value = MagicMock(
                        success=True,
                        workspace=MagicMock(name="010-feature-WP01", path=workspace_path),
                        error=None,
                    )
                    mock_get_vcs.return_value = mock_vcs

                    with patch("subprocess.run") as mock_run:
                        # Mock git commands for resolve_primary_branch
                        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")

                        # Run implement
                        implement("WP01", base=None)

                        # Verify vcs.create_workspace was called
                        mock_vcs.create_workspace.assert_called_once()
                        call_kwargs = mock_vcs.create_workspace.call_args[1]
                        assert call_kwargs["workspace_name"] == "010-feature-WP01"
                        assert "sparse_exclude" in call_kwargs
                        assert "kitty-specs/" in call_kwargs["sparse_exclude"]

    def test_implement_with_base(self, tmp_path):
        """Test implement WP02 --base WP01 creates workspace from WP01 branch."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP02-feature.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            '---\nwork_package_id: WP02\ndependencies: ["WP01"]\n---\n# WP02'
        )

        # Create base workspace
        base_workspace = tmp_path / ".worktrees" / "010-feature-WP01"
        base_workspace.mkdir(parents=True)

        # Workspace path that will be "created"
        workspace_path = tmp_path / ".worktrees" / "010-feature-WP02"

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                # Mock VCS detection to return git
                with patch("specify_cli.cli.commands.implement.get_vcs") as mock_get_vcs:
                    mock_vcs = MagicMock()
                    mock_vcs.backend = VCSBackend.GIT

                    # First call for new workspace (returns None), second for base workspace
                    def get_workspace_info_side_effect(path):
                        if "WP01" in str(path):
                            return MagicMock(
                                name="010-feature-WP01",
                                path=base_workspace,
                                current_branch="010-feature-WP01",
                                is_stale=False,
                            )
                        return None  # Workspace doesn't exist

                    mock_vcs.get_workspace_info.side_effect = get_workspace_info_side_effect
                    mock_vcs.create_workspace.return_value = MagicMock(
                        success=True,
                        workspace=MagicMock(name="010-feature-WP02", path=workspace_path),
                        error=None,
                    )
                    mock_get_vcs.return_value = mock_vcs

                    with patch("subprocess.run") as mock_run:
                        # Mock git commands for branch verification
                        mock_run.return_value = MagicMock(returncode=0, stdout="")

                        # Run implement
                        implement("WP02", base="WP01")

                        # Verify vcs.create_workspace was called with base branch
                        mock_vcs.create_workspace.assert_called_once()
                        call_kwargs = mock_vcs.create_workspace.call_args[1]
                        assert call_kwargs["workspace_name"] == "010-feature-WP02"
                        assert call_kwargs["base_branch"] == "010-feature-WP01"

    def test_implement_missing_base_workspace(self, tmp_path):
        """Test error when base workspace doesn't exist."""
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP02-feature.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            '---\nwork_package_id: WP02\ndependencies: ["WP01"]\n---\n# WP02'
        )

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                # Mock VCS detection to return git
                with patch("specify_cli.cli.commands.implement.get_vcs") as mock_get_vcs:
                    mock_vcs = MagicMock()
                    mock_vcs.backend = VCSBackend.GIT
                    mock_vcs.get_workspace_info.return_value = None  # Workspace doesn't exist
                    mock_get_vcs.return_value = mock_vcs

                    # Base workspace doesn't exist
                    with pytest.raises(typer.Exit):
                        implement("WP02", base="WP01")

    def test_implement_has_deps_no_base_flag(self, tmp_path):
        """Test error when WP has dependencies but --base not provided."""
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP02-feature.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            '---\nwork_package_id: WP02\ndependencies: ["WP01"]\n---\n# WP02'
        )

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                # No --base flag provided
                with pytest.raises(typer.Exit):
                    implement("WP02", base=None)

    def test_implement_workspace_already_exists(self, tmp_path):
        """Test reusing existing valid workspace."""
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01"
        )

        # Create existing workspace
        workspace = tmp_path / ".worktrees" / "010-feature-WP01"
        workspace.mkdir(parents=True)

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                with patch("subprocess.run") as mock_run:
                    # Mock git commands for resolve_primary_branch and planning artifact check
                    mock_run.return_value = MagicMock(returncode=0, stdout="main\n")

                    # Mock VCS detection to return git
                    with patch("specify_cli.cli.commands.implement.get_vcs") as mock_get_vcs:
                        mock_vcs = MagicMock()
                        mock_vcs.backend = VCSBackend.GIT
                        # Workspace already exists
                        mock_vcs.get_workspace_info.return_value = MagicMock(
                            name="010-feature-WP01",
                            path=workspace,
                            current_branch="010-feature-WP01",
                            is_stale=False,
                        )
                        mock_get_vcs.return_value = mock_vcs

                        # Run implement - should reuse existing
                        implement("WP01", base=None)

                        # Verify vcs.create_workspace was NOT called (reusing existing)
                        mock_vcs.create_workspace.assert_not_called()

    def test_workspace_naming_convention(self, tmp_path):
        """Test workspace naming follows convention."""
        # Use the feature slug that will be detected
        feature_dir = tmp_path / "kitty-specs" / "010-workspace-per-wp"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01"
        )

        # Workspace path that will be "created"
        workspace_path = tmp_path / ".worktrees" / "010-workspace-per-wp-WP01"

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-workspace-per-wp")

                # Mock VCS detection to return git
                with patch("specify_cli.cli.commands.implement.get_vcs") as mock_get_vcs:
                    mock_vcs = MagicMock()
                    mock_vcs.backend = VCSBackend.GIT
                    mock_vcs.get_workspace_info.return_value = None  # Workspace doesn't exist
                    mock_vcs.create_workspace.return_value = MagicMock(
                        success=True,
                        workspace=MagicMock(name="010-workspace-per-wp-WP01", path=workspace_path),
                        error=None,
                    )
                    mock_get_vcs.return_value = mock_vcs

                    with patch("subprocess.run") as mock_run:
                        # Mock git commands for resolve_primary_branch
                        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")

                        # Run implement
                        implement("WP01", base=None)

                        # Verify workspace naming convention
                        mock_vcs.create_workspace.assert_called_once()
                        call_kwargs = mock_vcs.create_workspace.call_args[1]
                        # Workspace name should be: ###-feature-WP##
                        assert call_kwargs["workspace_name"] == "010-workspace-per-wp-WP01"
                        # Verify workspace path
                        assert str(call_kwargs["workspace_path"]).endswith(".worktrees/010-workspace-per-wp-WP01")


class TestVCSAbstraction:
    """Tests for VCS abstraction in implement command."""

    @pytest.mark.parametrize("backend", [
        "git",
        pytest.param("jj", marks=pytest.mark.jj),
    ])
    def test_implement_creates_workspace(self, tmp_path, backend):
        """Test implement creates workspace correctly for both VCS backends."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "015-feature"
        create_meta_json(feature_dir, vcs=backend)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01"
        )

        workspace_path = tmp_path / ".worktrees" / "015-feature-WP01"

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("015", "015-feature")

                # Mock VCS detection to return the specified backend
                with patch("specify_cli.cli.commands.implement.get_vcs") as mock_get_vcs:
                    mock_vcs = MagicMock()
                    mock_vcs.backend = VCSBackend(backend)
                    mock_vcs.get_workspace_info.return_value = None  # Workspace doesn't exist
                    mock_vcs.create_workspace.return_value = MagicMock(
                        success=True,
                        workspace=MagicMock(name="015-feature-WP01", path=workspace_path),
                        error=None,
                    )
                    mock_get_vcs.return_value = mock_vcs

                    with patch("subprocess.run") as mock_run:
                        # Mock git commands for resolve_primary_branch
                        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")

                        # Run implement
                        implement("WP01", base=None)

                        # Verify vcs.create_workspace was called
                        mock_vcs.create_workspace.assert_called_once()
                        call_kwargs = mock_vcs.create_workspace.call_args[1]
                        assert call_kwargs["workspace_name"] == "015-feature-WP01"

                        # Sparse_exclude is always used now (jj converted to git)
                        assert "sparse_exclude" in call_kwargs
                        assert "kitty-specs/" in call_kwargs["sparse_exclude"]

    def test_vcs_locking_in_meta_json(self, tmp_path):
        """Test VCS is stored and locked in meta.json on first workspace creation."""
        # Setup - meta.json WITHOUT vcs field
        feature_dir = tmp_path / "kitty-specs" / "015-feature"
        feature_dir.mkdir(parents=True)
        meta_path = feature_dir / "meta.json"
        meta_content = {
            "feature_number": "015",
            "feature_slug": "015-feature",
            "created_at": "2026-01-17T00:00:00Z",
        }
        meta_path.write_text(json.dumps(meta_content, indent=2))

        # Mock VCS detection
        with patch("specify_cli.cli.commands.implement.get_vcs") as mock_get_vcs:
            mock_vcs = MagicMock()
            mock_vcs.backend = VCSBackend.GIT
            mock_get_vcs.return_value = mock_vcs

            # Call helper function
            backend = _ensure_vcs_in_meta(feature_dir, tmp_path)

            # Verify VCS was locked
            assert backend == VCSBackend.GIT

            # Verify meta.json was updated
            updated_meta = json.loads(meta_path.read_text())
            assert updated_meta["vcs"] == "git"
            assert "vcs_locked_at" in updated_meta

    def test_vcs_already_locked(self, tmp_path):
        """Test VCS is converted from jj to git (jj no longer supported)."""
        # Setup - meta.json WITH vcs field already set to jj
        feature_dir = tmp_path / "kitty-specs" / "015-feature"
        create_meta_json(feature_dir, vcs="jj")

        # Call helper function
        backend = _ensure_vcs_in_meta(feature_dir, tmp_path)

        # Verify jj is converted to git
        assert backend == VCSBackend.GIT

    @pytest.mark.parametrize("backend", [
        "git",
        pytest.param("jj", marks=pytest.mark.jj),
    ])
    def test_stale_workspace_detection(self, tmp_path, backend):
        """Test stale workspace detection works for both backends."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "015-feature"
        create_meta_json(feature_dir, vcs=backend)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01"
        )

        workspace_path = tmp_path / ".worktrees" / "015-feature-WP01"
        workspace_path.mkdir(parents=True)

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("015", "015-feature")

                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="main\n")

                    with patch("specify_cli.cli.commands.implement.get_vcs") as mock_get_vcs:
                        mock_vcs = MagicMock()
                        mock_vcs.backend = VCSBackend(backend)
                        # Workspace exists and is STALE
                        mock_vcs.get_workspace_info.return_value = MagicMock(
                            name="015-feature-WP01",
                            path=workspace_path,
                            current_branch="015-feature-WP01",
                            is_stale=True,  # Workspace is stale
                        )
                        mock_get_vcs.return_value = mock_vcs

                        # Run implement - should warn about stale workspace
                        implement("WP01", base=None)

                        # Verify workspace was reused (not recreated)
                        mock_vcs.create_workspace.assert_not_called()
                        # Stale detection was triggered via workspace_info.is_stale

    @pytest.mark.parametrize("backend", [
        "git",
        pytest.param("jj", marks=pytest.mark.jj),
    ])
    def test_implement_with_base_flag(self, tmp_path, backend):
        """Test --base flag works for both backends."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "015-feature"
        create_meta_json(feature_dir, vcs=backend)
        wp_file = feature_dir / "tasks" / "WP02-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            '---\nwork_package_id: WP02\ndependencies: ["WP01"]\n---\n# WP02'
        )

        # Create base workspace
        base_workspace = tmp_path / ".worktrees" / "015-feature-WP01"
        base_workspace.mkdir(parents=True)

        workspace_path = tmp_path / ".worktrees" / "015-feature-WP02"

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("015", "015-feature")

                with patch("specify_cli.cli.commands.implement.get_vcs") as mock_get_vcs:
                    mock_vcs = MagicMock()
                    mock_vcs.backend = VCSBackend(backend)

                    def get_workspace_info_side_effect(path):
                        if "WP01" in str(path):
                            return MagicMock(
                                name="015-feature-WP01",
                                path=base_workspace,
                                current_branch="015-feature-WP01",
                                is_stale=False,
                            )
                        return None

                    mock_vcs.get_workspace_info.side_effect = get_workspace_info_side_effect
                    mock_vcs.create_workspace.return_value = MagicMock(
                        success=True,
                        workspace=MagicMock(name="015-feature-WP02", path=workspace_path),
                        error=None,
                    )
                    mock_get_vcs.return_value = mock_vcs

                    with patch("subprocess.run") as mock_run:
                        mock_run.return_value = MagicMock(returncode=0, stdout="")

                        # Run implement with --base
                        implement("WP02", base="WP01")

                        # Verify vcs.create_workspace was called with base branch
                        mock_vcs.create_workspace.assert_called_once()
                        call_kwargs = mock_vcs.create_workspace.call_args[1]
                        assert call_kwargs["workspace_name"] == "015-feature-WP02"
                        assert call_kwargs["base_branch"] == "015-feature-WP01"
