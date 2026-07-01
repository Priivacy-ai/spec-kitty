"""Unit tests for WP04: move_task guard skips safe_commit when coord+protected.

T021: _coord_topology_active returns True when coord worktree exists on disk.
T022: _coord_topology_active returns False when coord worktree absent.
T023: _coord_topology_active returns False for legacy slugs (no mid8 suffix).
T024: _coord_topology_active returns False on any import/OS error (defensive).
T025: guard condition: coord+protected causes _skip_target_commit=True.
T026: guard condition: coord active but target NOT protected → commit proceeds.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# T021 / T022 / T023 / T024: _coord_topology_active
# ---------------------------------------------------------------------------

class TestCoordTopologyActive:
    """Verify _coord_topology_active correctly detects coord worktree presence."""

    def _import_helper(self) -> object:
        from specify_cli.cli.commands.agent.tasks import _coord_topology_active
        return _coord_topology_active

    def test_returns_true_when_coord_worktree_exists(self, tmp_path: Path) -> None:
        """_coord_topology_active is True when coord worktree directory exists (T021)."""
        from specify_cli.cli.commands.agent.tasks import _coord_topology_active

        slug = "my-feature-01KT3YBD"
        mid8 = "01KT3YBD"
        base_slug = "my-feature"

        # Create the coord worktree directory (CoordinationWorkspace.worktree_path result)
        coord_path = tmp_path / ".worktrees" / f"{base_slug}-{mid8}-coord"
        coord_path.mkdir(parents=True)

        assert _coord_topology_active(tmp_path, slug) is True

    def test_returns_false_when_coord_worktree_absent(self, tmp_path: Path) -> None:
        """_coord_topology_active is False when no coord worktree directory (T022)."""
        from specify_cli.cli.commands.agent.tasks import _coord_topology_active

        slug = "my-feature-01KT3YBD"
        assert _coord_topology_active(tmp_path, slug) is False

    def test_returns_false_for_legacy_slug_without_mid8(self, tmp_path: Path) -> None:
        """Legacy slugs without ULID suffix yield mid8='' → no coord check → False (T023)."""
        from specify_cli.cli.commands.agent.tasks import _coord_topology_active

        slug = "legacy-feature"  # no mid8 tail
        # Even if we create what would be the coord path, the slug has no mid8
        assert _coord_topology_active(tmp_path, slug) is False

    def test_returns_false_on_import_error(self, tmp_path: Path) -> None:
        """If CoordinationWorkspace cannot be imported, returns False gracefully (T024)."""
        from specify_cli.cli.commands.agent.tasks import _coord_topology_active

        with patch.dict("sys.modules", {"specify_cli.coordination.workspace": None}):
            # Should not raise, returns False
            result = _coord_topology_active(tmp_path, "my-feature-01KT3YBD")
            assert result is False

    def test_returns_true_for_numeric_suffix_when_coord_worktree_exists(self, tmp_path: Path) -> None:
        """Numeric-only suffix is valid Crockford mid8 and can activate coord topology."""
        from specify_cli.cli.commands.agent.tasks import _coord_topology_active

        slug = "feature-12345678"
        coord_path = tmp_path / ".worktrees" / "feature-12345678-coord"
        coord_path.mkdir(parents=True)

        assert _coord_topology_active(tmp_path, slug) is True


# ---------------------------------------------------------------------------
# T025 / T026: guard condition logic
# ---------------------------------------------------------------------------

class TestMoveTaskGuardCondition:
    """Verify the _skip_target_commit guard logic in move_task (T025, T026)."""

    def _compute_skip(
        self,
        repo_root: Path,
        mission_slug: str,
        target_branch: str,
        coord_active: bool,
        protected: list[str],
    ) -> bool:
        """Replicate the guard logic from move_task without invoking the full CLI."""
        # This mirrors the exact guard condition in tasks.py:
        #   _skip_target_commit = _coord_topology_active(main_repo_root, mission_slug)
        #                         and target_branch in protected_branches(main_repo_root)
        return coord_active and target_branch in protected

    def test_skip_when_coord_active_and_target_protected(self, tmp_path: Path) -> None:
        """_skip_target_commit is True when coord is active AND target is protected (T025)."""
        skip = self._compute_skip(
            tmp_path,
            "my-feature-01KT3YBD",
            "main",
            coord_active=True,
            protected=["main", "develop"],
        )
        assert skip is True

    def test_no_skip_when_coord_active_but_target_not_protected(self, tmp_path: Path) -> None:
        """_skip_target_commit is False when coord active but target is not protected (T026)."""
        skip = self._compute_skip(
            tmp_path,
            "my-feature-01KT3YBD",
            "feature-branch",
            coord_active=True,
            protected=["main"],
        )
        assert skip is False

    def test_no_skip_when_coord_inactive_and_target_protected(self, tmp_path: Path) -> None:
        """_skip_target_commit is False when target is protected but coord is inactive."""
        skip = self._compute_skip(
            tmp_path,
            "legacy-feature",
            "main",
            coord_active=False,
            protected=["main"],
        )
        assert skip is False

    def test_no_skip_when_both_inactive_and_not_protected(self, tmp_path: Path) -> None:
        """_skip_target_commit is False when neither condition holds."""
        skip = self._compute_skip(
            tmp_path,
            "legacy-feature",
            "feature-branch",
            coord_active=False,
            protected=["main"],
        )
        assert skip is False

    def test_coord_topology_active_integrates_with_guard(self, tmp_path: Path) -> None:
        """End-to-end: coord worktree on disk → _skip_target_branch_commit True."""
        from specify_cli.cli.commands.agent.tasks import _skip_target_branch_commit

        slug = "my-feature-01KT3YBD"
        mid8 = "01KT3YBD"
        base_slug = "my-feature"

        # Create coord worktree so topology is active
        coord_path = tmp_path / ".worktrees" / f"{base_slug}-{mid8}-coord"
        coord_path.mkdir(parents=True)

        # Guard condition: coord_active AND target protected via ProtectionPolicy
        mock_policy = MagicMock()
        mock_policy.is_protected.return_value = True
        with patch(
            "specify_cli.cli.commands.agent.tasks.ProtectionPolicy.resolve",
            return_value=mock_policy,
        ):
            skip = _skip_target_branch_commit(tmp_path, slug, "main")

        assert skip is True

    def test_coord_status_events_path_reports_coord_worktree_path(
        self, tmp_path: Path
    ) -> None:
        """JSON payloads expose the coord status path in skip mode."""
        from specify_cli.cli.commands.agent.tasks import _coord_status_events_path

        slug = "my-feature-01KT3YBD"
        coord_path = (
            tmp_path
            / ".worktrees"
            / "my-feature-01KT3YBD-coord"
            / "kitty-specs"
            / slug
        )
        coord_path.mkdir(parents=True)

        assert _coord_status_events_path(tmp_path, slug) == (
            coord_path / "status.events.jsonl"
        )

    def test_coord_status_events_path_absent_for_legacy(
        self, tmp_path: Path
    ) -> None:
        """Legacy missions keep primary status path reporting."""
        from specify_cli.cli.commands.agent.tasks import _coord_status_events_path

        assert _coord_status_events_path(tmp_path, "legacy-feature") is None

    def test_skip_target_branch_commit_true_for_coord_protected_target(
        self, tmp_path: Path
    ) -> None:
        """Shared move-task guard bypasses early protected-branch refusal."""
        from specify_cli.cli.commands.agent.tasks import _skip_target_branch_commit

        slug = "my-feature-01KT3YBD"
        coord_path = tmp_path / ".worktrees" / "my-feature-01KT3YBD-coord"
        coord_path.mkdir(parents=True)

        mock_policy = MagicMock()
        mock_policy.is_protected.return_value = True
        with patch(
            "specify_cli.cli.commands.agent.tasks.ProtectionPolicy.resolve",
            return_value=mock_policy,
        ):
            assert _skip_target_branch_commit(tmp_path, slug, "main") is True

    def test_skip_target_branch_commit_false_for_legacy_protected_target(
        self, tmp_path: Path
    ) -> None:
        """Legacy missions still refuse auto-commit on protected branches."""
        from specify_cli.cli.commands.agent.tasks import _skip_target_branch_commit

        mock_policy = MagicMock()
        mock_policy.is_protected.return_value = True
        with patch(
            "specify_cli.cli.commands.agent.tasks.ProtectionPolicy.resolve",
            return_value=mock_policy,
        ):
            assert _skip_target_branch_commit(tmp_path, "legacy-feature", "main") is False
