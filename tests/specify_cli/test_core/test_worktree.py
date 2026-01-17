"""Unit tests for worktree management utilities."""

from __future__ import annotations

import subprocess
import warnings
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from specify_cli.core.worktree import (
    create_feature_worktree,
    get_next_feature_number,
    setup_feature_directory,
    validate_feature_structure,
)


class TestGetNextFeatureNumber:
    """Tests for get_next_feature_number function."""

    def test_returns_1_when_no_features_exist(self, tmp_path: Path):
        """Should return 1 when no features exist."""
        # Setup: Empty repo
        result = get_next_feature_number(tmp_path)
        assert result == 1

    def test_scans_kitty_specs_directory(self, tmp_path: Path):
        """Should scan kitty-specs/ for feature numbers."""
        # Setup: Create features in kitty-specs/
        specs_dir = tmp_path / "kitty-specs"
        specs_dir.mkdir()
        (specs_dir / "001-feature-one").mkdir()
        (specs_dir / "002-feature-two").mkdir()
        (specs_dir / "005-feature-five").mkdir()

        result = get_next_feature_number(tmp_path)
        assert result == 6

    def test_scans_worktrees_directory(self, tmp_path: Path):
        """Should scan .worktrees/ for feature numbers."""
        # Setup: Create features in .worktrees/
        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "003-worktree-feature").mkdir()
        (worktrees_dir / "007-another-feature").mkdir()

        result = get_next_feature_number(tmp_path)
        assert result == 8

    def test_scans_both_directories(self, tmp_path: Path):
        """Should scan both kitty-specs/ and .worktrees/ and use highest number."""
        # Setup: Features in both directories
        specs_dir = tmp_path / "kitty-specs"
        specs_dir.mkdir()
        (specs_dir / "001-feature").mkdir()
        (specs_dir / "003-feature").mkdir()

        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "002-feature").mkdir()
        (worktrees_dir / "010-feature").mkdir()

        result = get_next_feature_number(tmp_path)
        assert result == 11

    def test_ignores_non_numeric_directories(self, tmp_path: Path):
        """Should ignore directories that don't start with ###."""
        # Setup: Mix of valid and invalid directory names
        specs_dir = tmp_path / "kitty-specs"
        specs_dir.mkdir()
        (specs_dir / "001-valid").mkdir()
        (specs_dir / "invalid-name").mkdir()
        (specs_dir / "README.md").touch()
        (specs_dir / "abc-not-number").mkdir()

        result = get_next_feature_number(tmp_path)
        assert result == 2

    def test_handles_missing_directories(self, tmp_path: Path):
        """Should handle missing kitty-specs/ and .worktrees/ gracefully."""
        # No directories created
        result = get_next_feature_number(tmp_path)
        assert result == 1

    def test_handles_malformed_feature_numbers_gracefully(self, tmp_path: Path):
        """Should skip directories with invalid numbers gracefully."""
        # Setup: Mix valid and invalid feature directories
        specs_dir = tmp_path / "kitty-specs"
        specs_dir.mkdir()
        (specs_dir / "001-valid").mkdir()
        (specs_dir / "abc-invalid").mkdir()  # Not a number
        (specs_dir / "00x-invalid").mkdir()  # Invalid format

        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "002-valid").mkdir()
        (worktrees_dir / "xyz-invalid").mkdir()

        result = get_next_feature_number(tmp_path)
        # Should only count 001 and 002, so next is 3
        assert result == 3


class TestCreateFeatureWorktree:
    """Tests for create_feature_worktree function."""

    def test_creates_worktree_with_branch(self, tmp_path: Path, monkeypatch):
        """Should create git worktree with proper branch name."""
        # Setup: Git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        # Create initial commit
        (tmp_path / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Execute
        worktree_path, feature_dir = create_feature_worktree(
            tmp_path, "test-feature", feature_number=1
        )

        # Verify
        assert worktree_path == tmp_path / ".worktrees" / "001-test-feature"
        assert worktree_path.exists()
        assert worktree_path.is_dir()
        assert feature_dir == worktree_path / "kitty-specs" / "001-test-feature"
        assert feature_dir.exists()

    def test_auto_detects_feature_number(self, tmp_path: Path):
        """Should auto-detect next feature number when not provided."""
        # Setup: Existing features
        specs_dir = tmp_path / "kitty-specs"
        specs_dir.mkdir()
        (specs_dir / "001-existing").mkdir()
        (specs_dir / "002-existing").mkdir()

        # Setup: Git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        (tmp_path / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Execute
        worktree_path, feature_dir = create_feature_worktree(tmp_path, "new-feature")

        # Verify
        assert worktree_path == tmp_path / ".worktrees" / "003-new-feature"
        assert feature_dir == worktree_path / "kitty-specs" / "003-new-feature"

    def test_raises_error_when_worktree_exists(self, tmp_path: Path):
        """Should raise FileExistsError when worktree path already exists."""
        # Setup: Pre-existing directory (not a valid worktree)
        worktree_path = tmp_path / ".worktrees" / "001-test-feature"
        worktree_path.mkdir(parents=True)

        # Execute & Verify
        with pytest.raises(FileExistsError, match="Worktree path already exists"):
            create_feature_worktree(tmp_path, "test-feature", feature_number=1)

    def test_reuses_existing_valid_worktree(self, tmp_path: Path):
        """Should reuse existing valid git worktree instead of raising error."""
        # Setup: Create valid git worktree
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        (tmp_path / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create first worktree
        worktree_path1, feature_dir1 = create_feature_worktree(
            tmp_path, "test-feature", feature_number=1
        )

        # Execute: Try to create same worktree again
        worktree_path2, feature_dir2 = create_feature_worktree(
            tmp_path, "test-feature", feature_number=1
        )

        # Verify: Should return same paths
        assert worktree_path1 == worktree_path2
        assert feature_dir1 == feature_dir2

    def test_raises_error_on_git_failure(self, tmp_path: Path):
        """Should raise RuntimeError when workspace creation fails."""
        # Setup: Not a git repo - workspace creation will fail
        # Note: RuntimeError wraps the underlying subprocess or VCS error
        with pytest.raises(RuntimeError, match="Failed to create workspace"):
            create_feature_worktree(tmp_path, "test-feature", feature_number=1)


class TestSetupFeatureDirectory:
    """Tests for setup_feature_directory function."""

    def test_creates_standard_subdirectories(self, tmp_path: Path):
        """Should create checklists/, research/, and tasks/ subdirectories."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        worktree_path = tmp_path
        repo_root = tmp_path

        # Execute
        setup_feature_directory(feature_dir, worktree_path, repo_root, create_symlinks=False)

        # Verify
        assert (feature_dir / "checklists").exists()
        assert (feature_dir / "checklists").is_dir()
        assert (feature_dir / "research").exists()
        assert (feature_dir / "research").is_dir()
        assert (feature_dir / "tasks").exists()
        assert (feature_dir / "tasks").is_dir()

    def test_creates_tasks_gitkeep(self, tmp_path: Path):
        """Should create tasks/.gitkeep file."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        worktree_path = tmp_path
        repo_root = tmp_path

        # Execute
        setup_feature_directory(feature_dir, worktree_path, repo_root, create_symlinks=False)

        # Verify
        assert (feature_dir / "tasks" / ".gitkeep").exists()
        assert (feature_dir / "tasks" / ".gitkeep").is_file()

    def test_creates_tasks_readme(self, tmp_path: Path):
        """Should create tasks/README.md with frontmatter format documentation."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        worktree_path = tmp_path
        repo_root = tmp_path

        # Execute
        setup_feature_directory(feature_dir, worktree_path, repo_root, create_symlinks=False)

        # Verify
        readme = feature_dir / "tasks" / "README.md"
        assert readme.exists()
        content = readme.read_text()
        assert "# Tasks Directory" in content
        assert "lane:" in content
        assert "YAML frontmatter" in content

    def test_copies_spec_template_when_exists(self, tmp_path: Path):
        """Should copy spec template to spec.md when template exists."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        worktree_path = tmp_path
        repo_root = tmp_path

        # Create template
        template_dir = repo_root / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "spec-template.md"
        template_file.write_text("# Feature Specification Template")

        # Execute
        setup_feature_directory(feature_dir, worktree_path, repo_root, create_symlinks=False)

        # Verify
        spec_file = feature_dir / "spec.md"
        assert spec_file.exists()
        assert spec_file.read_text() == "# Feature Specification Template"

    def test_creates_empty_spec_when_no_template(self, tmp_path: Path):
        """Should create empty spec.md when no template exists."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        worktree_path = tmp_path
        repo_root = tmp_path

        # Execute
        setup_feature_directory(feature_dir, worktree_path, repo_root, create_symlinks=False)

        # Verify
        spec_file = feature_dir / "spec.md"
        assert spec_file.exists()
        assert spec_file.read_text() == ""

    def test_copies_memory_directory_when_symlinks_disabled(self, tmp_path: Path):
        """Should copy memory/ directory when create_symlinks=False."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        worktree_path = tmp_path / ".worktrees" / "001-test"
        worktree_path.mkdir(parents=True)  # Create worktree directory
        repo_root = tmp_path

        # Create memory directory in main repo
        memory_dir = repo_root / ".kittify" / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "constitution.md").write_text("Constitution content")

        # Execute
        setup_feature_directory(feature_dir, worktree_path, repo_root, create_symlinks=False)

        # Verify
        worktree_memory = worktree_path / ".kittify" / "memory"
        assert worktree_memory.exists()
        assert worktree_memory.is_dir()
        assert not worktree_memory.is_symlink()
        assert (worktree_memory / "constitution.md").read_text() == "Constitution content"

    @patch("platform.system")
    def test_uses_copy_on_windows(self, mock_system: Mock, tmp_path: Path):
        """Should use file copy instead of symlinks on Windows."""
        # Setup
        mock_system.return_value = "Windows"
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        worktree_path = tmp_path / ".worktrees" / "001-test"
        worktree_path.mkdir(parents=True)  # Create worktree directory
        repo_root = tmp_path

        # Create memory directory
        memory_dir = repo_root / ".kittify" / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "test.md").write_text("test")

        # Execute (with create_symlinks=True, but Windows should override)
        setup_feature_directory(feature_dir, worktree_path, repo_root, create_symlinks=True)

        # Verify
        worktree_memory = worktree_path / ".kittify" / "memory"
        assert worktree_memory.exists()
        assert not worktree_memory.is_symlink()  # Should be copied, not symlinked

    def test_handles_existing_kittify_directory(self, tmp_path: Path):
        """Should handle existing .kittify directory and replace symlink."""
        # Setup
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        worktree_path = tmp_path / ".worktrees" / "001-test"
        worktree_path.mkdir(parents=True)
        repo_root = tmp_path

        # Create memory directory in main repo
        memory_dir = repo_root / ".kittify" / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "file.md").write_text("content")

        # Create AGENTS.md
        (repo_root / ".kittify" / "AGENTS.md").write_text("# Agents")

        # Pre-create worktree .kittify with a symlink that needs replacing
        worktree_kittify = worktree_path / ".kittify"
        worktree_kittify.mkdir()
        worktree_memory = worktree_kittify / "memory"
        worktree_memory.mkdir()  # Create as directory first
        (worktree_memory / "old.md").write_text("old")

        # Execute - should replace the directory with symlink/copy
        setup_feature_directory(feature_dir, worktree_path, repo_root, create_symlinks=False)

        # Verify memory was replaced
        assert worktree_memory.exists()
        assert (worktree_memory / "file.md").exists()
        assert not (worktree_memory / "old.md").exists()


class TestValidateFeatureStructure:
    """Tests for validate_feature_structure function."""

    def test_validates_missing_feature_directory(self, tmp_path: Path):
        """Should return error when feature directory doesn't exist."""
        # Setup
        feature_dir = tmp_path / "nonexistent"

        # Execute
        result = validate_feature_structure(feature_dir)

        # Verify
        assert result["valid"] is False
        assert "Feature directory not found" in result["errors"][0]
        assert result["warnings"] == []

    def test_validates_missing_spec_file(self, tmp_path: Path):
        """Should return error when spec.md is missing."""
        # Setup
        feature_dir = tmp_path / "001-test"
        feature_dir.mkdir()

        # Execute
        result = validate_feature_structure(feature_dir)

        # Verify
        assert result["valid"] is False
        assert "Missing required file: spec.md" in result["errors"]

    def test_warns_about_missing_directories(self, tmp_path: Path):
        """Should return warnings when recommended directories are missing."""
        # Setup
        feature_dir = tmp_path / "001-test"
        feature_dir.mkdir()
        (feature_dir / "spec.md").write_text("spec")

        # Execute
        result = validate_feature_structure(feature_dir)

        # Verify
        assert result["valid"] is True  # Not an error, just warnings
        assert "Missing recommended directory: checklists/" in result["warnings"]
        assert "Missing recommended directory: research/" in result["warnings"]
        assert "Missing recommended directory: tasks/" in result["warnings"]

    def test_validates_complete_structure(self, tmp_path: Path):
        """Should pass validation when all required files and directories exist."""
        # Setup
        feature_dir = tmp_path / "001-test"
        feature_dir.mkdir()
        (feature_dir / "spec.md").write_text("spec")
        (feature_dir / "checklists").mkdir()
        (feature_dir / "research").mkdir()
        (feature_dir / "tasks").mkdir()

        # Execute
        result = validate_feature_structure(feature_dir)

        # Verify
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []

    def test_validates_tasks_md_when_requested(self, tmp_path: Path):
        """Should validate tasks.md exists when check_tasks=True."""
        # Setup
        feature_dir = tmp_path / "001-test"
        feature_dir.mkdir()
        (feature_dir / "spec.md").write_text("spec")

        # Execute
        result = validate_feature_structure(feature_dir, check_tasks=True)

        # Verify
        assert result["valid"] is False
        assert "Missing required file: tasks.md" in result["errors"]

    def test_includes_paths_in_result(self, tmp_path: Path):
        """Should include important paths in validation result."""
        # Setup
        feature_dir = tmp_path / "001-test"
        feature_dir.mkdir()
        (feature_dir / "spec.md").write_text("spec")
        (feature_dir / "checklists").mkdir()
        (feature_dir / "research").mkdir()
        (feature_dir / "tasks").mkdir()

        # Execute
        result = validate_feature_structure(feature_dir)

        # Verify
        assert "paths" in result
        assert result["paths"]["spec_file"] == str(feature_dir / "spec.md")
        assert result["paths"]["checklists_dir"] == str(feature_dir / "checklists")
        assert result["paths"]["research_dir"] == str(feature_dir / "research")
        assert result["paths"]["tasks_dir"] == str(feature_dir / "tasks")
        assert result["paths"]["feature_dir"] == str(feature_dir)


class TestVCSAbstraction:
    """Tests for VCS abstraction layer integration in worktree module."""

    def test_create_worktree_uses_vcs_abstraction(self, tmp_path: Path):
        """Should use VCS abstraction to create workspace."""
        # Setup: Git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        (tmp_path / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Mock the VCS abstraction to verify it's called
        mock_result = MagicMock()
        mock_result.success = True
        mock_vcs = MagicMock()
        mock_vcs.create_workspace.return_value = mock_result
        mock_vcs.is_repo.return_value = False

        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs):
            worktree_path, feature_dir = create_feature_worktree(
                tmp_path, "test-feature", feature_number=1
            )

            # Verify VCS abstraction was called
            mock_vcs.create_workspace.assert_called_once()
            call_kwargs = mock_vcs.create_workspace.call_args.kwargs
            assert call_kwargs["workspace_name"] == "001-test-feature"
            assert call_kwargs["repo_root"] == tmp_path

    def test_create_worktree_falls_back_to_git_with_warning(self, tmp_path: Path):
        """Should fall back to direct git commands with deprecation warning when VCS fails."""
        # Setup: Git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        (tmp_path / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Mock VCS to fail
        with patch("specify_cli.core.worktree.get_vcs", side_effect=Exception("VCS failed")):
            # Capture deprecation warning
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                worktree_path, feature_dir = create_feature_worktree(
                    tmp_path, "fallback-test", feature_number=99
                )

                # Verify deprecation warning was raised
                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "VCS abstraction failed" in str(w[0].message)
                assert "falling back to direct git commands" in str(w[0].message)

            # Verify worktree was still created via fallback
            assert worktree_path.exists()
            assert feature_dir.exists()

    def test_create_worktree_raises_on_vcs_and_fallback_failure(self, tmp_path: Path):
        """Should raise RuntimeError when VCS and git fallback both fail."""
        # Setup: NOT a git repo - so fallback will fail too
        # (don't run git init)

        # Mock VCS to return failure result
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Workspace creation failed"
        mock_vcs = MagicMock()
        mock_vcs.create_workspace.return_value = mock_result
        mock_vcs.is_repo.return_value = False

        # VCS fails, fallback fails (not a git repo), should raise
        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs):
            with pytest.raises(RuntimeError, match="Failed to create workspace"):
                create_feature_worktree(tmp_path, "fail-test", feature_number=88)

    def test_create_worktree_detects_existing_vcs_workspace(self, tmp_path: Path):
        """Should detect and reuse existing VCS workspace."""
        # Setup: Pre-existing workspace directory with .git
        worktree_path = tmp_path / ".worktrees" / "001-test-feature"
        worktree_path.mkdir(parents=True)
        (worktree_path / ".git").touch()  # Minimal marker

        # Mock VCS to recognize it as valid repo
        mock_vcs = MagicMock()
        mock_vcs.is_repo.return_value = True

        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs):
            worktree_result, feature_dir = create_feature_worktree(
                tmp_path, "test-feature", feature_number=1
            )

            # Should return the existing path
            assert worktree_result == worktree_path
            assert feature_dir == worktree_path / "kitty-specs" / "001-test-feature"
