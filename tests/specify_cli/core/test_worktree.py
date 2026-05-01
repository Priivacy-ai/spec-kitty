"""Tests for workspace strategy routing in core/worktree.py.

Verifies:
- code_change WPs create standard git worktrees with full repository checkouts.
- planning_artifact WPs return repo_root directly (no worktree created).
- Both execution modes avoid any file-hiding workspace mechanism.
- create_wp_workspace() routes correctly for both execution modes.
- create_wp_workspace() accepts WPMetadata in addition to raw dicts.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.core.worktree import create_wp_workspace
from specify_cli.status.wp_metadata import WPMetadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frontmatter(
    execution_mode: str = "code_change",
    wp_id: str = "WP01",
    mission_slug: str = "test-feature",
    owned_files: list[str] | None = None,
) -> WPMetadata:
    return WPMetadata(
        work_package_id=wp_id,
        execution_mode=execution_mode,
        owned_files=owned_files or [],
        feature_slug=mission_slug,
    )


def _make_successful_vcs_result(workspace_path: Path) -> MagicMock:
    result = MagicMock()
    result.success = True
    result.error = None
    return result


# ---------------------------------------------------------------------------
# T018/T019: planning_artifact routing
# ---------------------------------------------------------------------------


class TestPlanningArtifactWorkspace:
    """planning_artifact WPs must return repo_root — no worktree created."""

    def test_returns_repo_root(self, tmp_path: Path) -> None:
        """planning_artifact WP returns repo_root directly."""
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"
        result = create_wp_workspace(
            repo_root=tmp_path,
            workspace_path=workspace_path,
            workspace_name="kitty/mission-test-feature-lane-a",
            wp_frontmatter=_make_frontmatter(execution_mode="planning_artifact"),
        )
        assert result == tmp_path

    def test_does_not_create_worktree_dir(self, tmp_path: Path) -> None:
        """planning_artifact WP does NOT create a worktree directory."""
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"
        create_wp_workspace(
            repo_root=tmp_path,
            workspace_path=workspace_path,
            workspace_name="kitty/mission-test-feature-lane-a",
            wp_frontmatter=_make_frontmatter(execution_mode="planning_artifact"),
        )
        assert not workspace_path.exists()

    def test_no_vcs_call_for_planning_artifact(self, tmp_path: Path) -> None:
        """planning_artifact WP never calls vcs.create_workspace()."""
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"
        with patch("specify_cli.core.worktree.get_vcs") as mock_get_vcs:
            create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="kitty/mission-test-feature-lane-a",
                wp_frontmatter=_make_frontmatter(execution_mode="planning_artifact"),
            )
            mock_get_vcs.assert_not_called()

    def test_raises_if_repo_root_missing(self, tmp_path: Path) -> None:
        """planning_artifact raises ValueError if repo_root doesn't exist."""
        missing_root = tmp_path / "does-not-exist"
        workspace_path = tmp_path / ".worktrees" / "WP01"
        with pytest.raises(ValueError, match="repo_root does not exist"):
            create_wp_workspace(
                repo_root=missing_root,
                workspace_path=workspace_path,
                workspace_name="WP01",
                wp_frontmatter=_make_frontmatter(execution_mode="planning_artifact"),
            )


# ---------------------------------------------------------------------------
# T018: code_change routing
# ---------------------------------------------------------------------------


class TestCodeChangeWorkspace:
    """code_change WPs must create standard full-checkout worktrees."""

    def test_calls_vcs_create_workspace(self, tmp_path: Path) -> None:
        """code_change WP delegates to vcs.create_workspace() when workspace does not exist."""
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"
        # workspace_path does NOT exist before the call

        mock_vcs = MagicMock()
        mock_vcs.create_workspace.return_value = _make_successful_vcs_result(workspace_path)

        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs):
            result = create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="kitty/mission-test-feature-lane-a",
                wp_frontmatter=_make_frontmatter(execution_mode="code_change"),
            )

        assert mock_vcs.create_workspace.called
        assert result == workspace_path

    def test_no_sparse_exclude_passed(self, tmp_path: Path) -> None:
        """code_change WP does not pass removed legacy workspace arguments."""
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"
        # workspace_path does NOT exist before the call

        mock_vcs = MagicMock()
        mock_vcs.create_workspace.return_value = _make_successful_vcs_result(workspace_path)

        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs):
            create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="kitty/mission-test-feature-lane-a",
                wp_frontmatter=_make_frontmatter(execution_mode="code_change"),
            )

        call_kwargs = mock_vcs.create_workspace.call_args
        # Verify sparse_exclude is NOT a keyword argument in the call
        assert "sparse_exclude" not in call_kwargs.kwargs
        # Verify it was not passed positionally as a 6th positional arg (self + 5 params max)
        positional = call_kwargs.args if call_kwargs.args else ()
        assert len(positional) <= 5

    def test_returns_workspace_path(self, tmp_path: Path) -> None:
        """code_change WP returns workspace_path after creation."""
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"
        # workspace_path does NOT exist before the call

        mock_vcs = MagicMock()
        mock_vcs.create_workspace.return_value = _make_successful_vcs_result(workspace_path)

        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs):
            result = create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="kitty/mission-test-feature-lane-a",
                wp_frontmatter=_make_frontmatter(execution_mode="code_change"),
            )

        assert result == workspace_path

    def test_raises_on_vcs_failure(self, tmp_path: Path) -> None:
        """code_change WP raises RuntimeError if vcs.create_workspace() fails."""
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"

        mock_vcs = MagicMock()
        fail_result = MagicMock()
        fail_result.success = False
        fail_result.error = "branch already exists"
        mock_vcs.create_workspace.return_value = fail_result

        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs), pytest.raises(RuntimeError, match="branch already exists"):
            create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="kitty/mission-test-feature-lane-a",
                wp_frontmatter=_make_frontmatter(execution_mode="code_change"),
            )

    def test_reuses_existing_valid_worktree(self, tmp_path: Path) -> None:
        """code_change WP reuses an existing workspace that has a .git marker."""
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"
        workspace_path.mkdir(parents=True)
        (workspace_path / ".git").write_text("gitdir: fake\n")

        with patch("specify_cli.core.worktree.get_vcs") as mock_get_vcs:
            result = create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="kitty/mission-test-feature-lane-a",
                wp_frontmatter=_make_frontmatter(execution_mode="code_change"),
            )
            # Should NOT call vcs when reusing
            mock_get_vcs.assert_not_called()

        assert result == workspace_path

    def test_raises_if_existing_dir_is_not_worktree(self, tmp_path: Path) -> None:
        """code_change WP raises FileExistsError if dir exists without .git marker."""
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"
        workspace_path.mkdir(parents=True)
        # No .git file/dir — not a valid worktree

        with patch("specify_cli.core.worktree.get_vcs"), pytest.raises(FileExistsError, match="not a worktree"):
            create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="kitty/mission-test-feature-lane-a",
                wp_frontmatter=_make_frontmatter(execution_mode="code_change"),
            )


# ---------------------------------------------------------------------------
# T018: execution_mode default / unknown values
# ---------------------------------------------------------------------------


class TestExecutionModeDefaults:
    """Verify fallback behaviour for absent or unknown execution_mode values."""

    def test_missing_execution_mode_defaults_to_code_change(self, tmp_path: Path) -> None:
        """Frontmatter without execution_mode behaves as code_change."""
        from specify_cli.status.wp_metadata import WPMetadata

        workspace_path = tmp_path / ".worktrees" / "WP99"
        frontmatter = WPMetadata(work_package_id="WP99")  # no execution_mode

        mock_vcs = MagicMock()
        fail_result = MagicMock()
        fail_result.success = False
        fail_result.error = "test"
        mock_vcs.create_workspace.return_value = fail_result

        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs), pytest.raises(RuntimeError):
            create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="WP99",
                wp_frontmatter=frontmatter,
            )
        mock_vcs.create_workspace.assert_called_once()

    def test_unknown_execution_mode_defaults_to_code_change(self, tmp_path: Path) -> None:
        """Unknown execution_mode value falls back to code_change."""
        from specify_cli.status.wp_metadata import WPMetadata

        workspace_path = tmp_path / ".worktrees" / "WP99"
        frontmatter = WPMetadata(
            work_package_id="WP99",
            execution_mode="totally_unknown_value",
        )

        mock_vcs = MagicMock()
        fail_result = MagicMock()
        fail_result.success = False
        fail_result.error = "test"
        mock_vcs.create_workspace.return_value = fail_result

        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs), pytest.raises(RuntimeError):
            create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="WP99",
                wp_frontmatter=frontmatter,
            )
        mock_vcs.create_workspace.assert_called_once()


# ---------------------------------------------------------------------------
# T020: verify legacy file-filtering hooks are absent from the VCS layer
# ---------------------------------------------------------------------------


class TestNoSparseCheckoutInVCS:
    """Verify that legacy file-hiding workspace hooks are absent from the VCS layer."""

    def test_vcs_create_workspace_has_no_sparse_param(self) -> None:
        """GitVCS.create_workspace() must not accept sparse_exclude parameter."""
        import inspect
        from specify_cli.core.vcs.git import GitVCS

        sig = inspect.signature(GitVCS.create_workspace)
        assert "sparse_exclude" not in sig.parameters, "sparse_exclude must be removed from GitVCS.create_workspace()"

    def test_protocol_create_workspace_has_no_sparse_param(self) -> None:
        """VCSProtocol.create_workspace() must not declare sparse_exclude."""
        import inspect
        from specify_cli.core.vcs.protocol import VCSProtocol

        sig = inspect.signature(VCSProtocol.create_workspace)
        assert "sparse_exclude" not in sig.parameters, "sparse_exclude must be removed from VCSProtocol.create_workspace()"

    def test_git_vcs_has_no_apply_sparse_checkout_method(self) -> None:
        """Legacy sparse helper must not exist on GitVCS."""
        from specify_cli.core.vcs.git import GitVCS

        assert not hasattr(GitVCS, "_apply_sparse_checkout"), "_apply_sparse_checkout must be deleted from GitVCS"


# ---------------------------------------------------------------------------
# WPMetadata typed input support
# ---------------------------------------------------------------------------


class TestWPMetadataInput:
    """Verify create_wp_workspace accepts WPMetadata in addition to raw dicts."""

    def test_planning_artifact_with_wp_metadata(self, tmp_path: Path) -> None:
        """planning_artifact WP via WPMetadata returns repo_root."""
        from specify_cli.status.wp_metadata import WPMetadata

        meta = WPMetadata(
            work_package_id="WP01",
            title="Test WP",
            dependencies=[],
            execution_mode="planning_artifact",
            owned_files=["docs/spec.md"],
            feature_slug="test-feature",
        )
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"
        result = create_wp_workspace(
            repo_root=tmp_path,
            workspace_path=workspace_path,
            workspace_name="kitty/mission-test-feature-lane-a",
            wp_frontmatter=meta,
        )
        assert result == tmp_path

    def test_code_change_with_wp_metadata(self, tmp_path: Path) -> None:
        """code_change WP via WPMetadata delegates to VCS."""
        from specify_cli.status.wp_metadata import WPMetadata

        meta = WPMetadata(
            work_package_id="WP01",
            title="Test WP",
            dependencies=[],
            execution_mode="code_change",
        )
        workspace_path = tmp_path / ".worktrees" / "test-feature-lane-a"

        mock_vcs = MagicMock()
        mock_vcs.create_workspace.return_value = _make_successful_vcs_result(workspace_path)

        with patch("specify_cli.core.worktree.get_vcs", return_value=mock_vcs):
            result = create_wp_workspace(
                repo_root=tmp_path,
                workspace_path=workspace_path,
                workspace_name="kitty/mission-test-feature-lane-a",
                wp_frontmatter=meta,
            )

        assert result == workspace_path
        mock_vcs.create_workspace.assert_called_once()
