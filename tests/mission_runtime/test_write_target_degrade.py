"""Tests for the shared write-target degrade helper (FR-005, WP04).

This module tests the public entry points (decision_log and bookkeeping_commit)
to verify observable behavior through their call sites, confirming that each
preserves its distinct degrade policy (fail-open vs. fail-closed).

Red-first assertion: in the no-``meta.json`` bootstrap window:
- decision_log's resolve returns ``CommitTarget(ref=destination_ref)`` (fail-open)
- bookkeeping_commit's resolve **raises** when its branch is None (fail-closed)

See spec: FR-005, C-004; plan IC-06a.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest import mock

import pytest

from mission_runtime import CommitTarget, MissionArtifactKind, resolve_write_target_or_degrade
from specify_cli.events.decision_log import DecisionGitLog
from specify_cli.git.bookkeeping_commit import commit_merge_bookkeeping
from mission_runtime import ActionContextError

# CI-gate visibility (test_gate_coverage.py / test_pytest_marker_convention.py /
# test_same_tier_uniqueness.py): pure-logic, tmp_path-only tests with no
# subprocess/git overhead -- same tier as the sibling
# ``tests/mission_runtime/test_artifact_home.py``.
pytestmark = [pytest.mark.fast]


class TestResolveWriteTargetOrDegrade:
    """Test the shared helper directly."""

    def test_helper_returns_degrade_ref_when_mission_missing(self, tmp_path: Path) -> None:
        """When mission meta.json doesn't exist, the helper returns the degrade_ref."""
        result = resolve_write_target_or_degrade(
            repo_root=tmp_path,
            mission_slug="nonexistent-mission",
            kind=MissionArtifactKind.DECISION_LOG,
            degrade_ref="destination",
        )
        assert isinstance(result, CommitTarget)
        assert result.ref == "destination"

    def test_helper_kind_parameterized(self, tmp_path: Path) -> None:
        """Helper accepts kind parameter (behavior tested via integration below)."""
        result = resolve_write_target_or_degrade(
            repo_root=tmp_path,
            mission_slug="nonexistent",
            kind=MissionArtifactKind.PRIMARY_METADATA,
            degrade_ref="fallback",
        )
        assert result.ref == "fallback"


class TestDecisionLogFailOpen:
    """Test decision_log preserves fail-open behavior through the helper."""

    def test_decision_log_returns_degrade_ref_on_missing_meta(
        self, tmp_path: Path
    ) -> None:
        """decision_log._resolve_default_target returns degrade_ref when mission missing."""
        destination_ref = "coord-branch"
        target = DecisionGitLog._resolve_default_target(
            repo_root=tmp_path,
            mission_slug="bootstrap-mission-no-meta",
            destination_ref=destination_ref,
        )
        # Fail-open: returns the caller's degrade_ref
        assert isinstance(target, CommitTarget)
        assert target.ref == destination_ref


class TestBookkeepingCommitFailClosed:
    """Test bookkeeping_commit preserves fail-closed behavior through the helper."""

    def test_bookkeeping_raises_when_branch_none_and_mission_missing(
        self, tmp_path: Path
    ) -> None:
        """bookkeeping_commit raises ActionContextError when branch=None + mission missing."""
        with pytest.raises(ActionContextError) as exc_info:
            commit_merge_bookkeeping(
                repo_root=tmp_path,
                worktree_root=tmp_path,
                mission_slug="bootstrap-mission-no-meta",
                message="test commit",
                paths=(tmp_path / "dummy.txt",),
                branch=None,  # Fail-closed: no fallback allowed
            )
        # Verify the error mentions the fail-closed reason
        assert "requires" in str(exc_info.value).lower() or "branch" in str(exc_info.value).lower()

    def test_bookkeeping_uses_branch_as_degrade_when_supplied(
        self, tmp_path: Path
    ) -> None:
        """bookkeeping_commit uses branch as degrade_ref when supplied (no metadata)."""
        # Create a dummy file to commit
        dummy_file = tmp_path / "dummy.txt"
        dummy_file.write_text("test content")

        # Mock safe_commit to avoid actual git operations
        with mock.patch("specify_cli.git.bookkeeping_commit.safe_commit") as mock_safe_commit:
            mock_safe_commit.return_value = mock.MagicMock()
            commit_merge_bookkeeping(
                repo_root=tmp_path,
                worktree_root=tmp_path,
                mission_slug="bootstrap-mission-no-meta",
                message="test commit",
                paths=(dummy_file,),
                branch="fallback-branch",  # Provided degrade path
            )
            # Verify safe_commit was called with the fallback branch
            assert mock_safe_commit.called
            call_args = mock_safe_commit.call_args
            assert call_args.kwargs["target"].ref == "fallback-branch"


class TestBookkeepingCommitResolvesFirstOnBranchNone:
    """Regression pin (WP04 review-cycle-1 fix): ``branch=None`` must NOT raise
    unconditionally -- resolution is always attempted FIRST, and the
    fail-closed raise fires only once resolution has genuinely failed.

    This is the exact production path ``post_merge/retrospective_terminus.py``
    drives: it calls :func:`commit_merge_bookkeeping` with no ``branch=``
    (defaults ``None``). Post-merge/close the mission IS resolvable, so this
    must return the placement-port target and commit -- not raise.
    """

    def test_branch_none_with_resolvable_mission_returns_placement_target(
        self, tmp_path: Path
    ) -> None:
        mission_slug = "017-my-test-mission"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps(
                {"mission_id": "01HXYZ0000000000000000000A", "mission_slug": mission_slug}
            ),
            encoding="utf-8",
        )
        dummy_file = tmp_path / "dummy.txt"
        dummy_file.write_text("test content", encoding="utf-8")

        resolved_target = CommitTarget(ref="kitty/mission-017-placement-target")
        with (
            # ``candidate_feature_dir_for_mission`` is imported LOCALLY inside
            # ``_mission_meta_exists`` (a lazy, in-function import -- see the
            # module docstring's circular-import note), so the patch target is
            # its origin module, not a (nonexistent) module-level attribute on
            # ``write_target_degrade`` itself.
            mock.patch(
                "specify_cli.missions._read_path_resolver.candidate_feature_dir_for_mission",
                return_value=feature_dir,
            ),
            mock.patch(
                "mission_runtime.write_target_degrade.resolve_placement_only",
                return_value=resolved_target,
            ) as mock_resolve,
            mock.patch("specify_cli.git.bookkeeping_commit.safe_commit") as mock_safe_commit,
        ):
            mock_safe_commit.return_value = mock.MagicMock()
            commit_merge_bookkeeping(
                repo_root=tmp_path,
                worktree_root=tmp_path,
                mission_slug=mission_slug,
                message="test commit",
                paths=(dummy_file,),
                branch=None,  # no degrade path supplied -- mission IS resolvable
            )

        # The placement port WAS consulted -- proves resolution is attempted
        # before any raise, not skipped in favor of an upfront fail-closed exit.
        mock_resolve.assert_called_once()
        # And ITS target (not a degrade to ref=None) reached safe_commit.
        assert mock_safe_commit.called
        call_args = mock_safe_commit.call_args
        assert call_args.kwargs["target"] is resolved_target
        assert call_args.kwargs["target"].ref == "kitty/mission-017-placement-target"


class TestScenario004VerbatimCloneRemoval:
    """Integration test: verify 0 verbatim clones remain (SC-004)."""

    def test_no_verbatim_mission_meta_exists_clones(self) -> None:
        """SC-004: exactly one ``_mission_meta_exists`` definition exists in
        ``src/`` -- the extracted helper module. The two verbatim clones that
        used to live in ``decision_log.py`` and ``bookkeeping_commit.py`` are
        gone; this is a real AST-based assertion, not a placeholder ``pass``.
        """
        src_root = Path(__file__).resolve().parents[2] / "src"
        helper_module = src_root / "mission_runtime" / "write_target_degrade.py"
        assert helper_module.is_file()

        def _defines_mission_meta_exists(py_file: Path) -> bool:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            return any(
                isinstance(node, ast.FunctionDef) and node.name == "_mission_meta_exists"
                for node in ast.walk(tree)
            )

        defining_files = [
            py_file for py_file in src_root.rglob("*.py") if _defines_mission_meta_exists(py_file)
        ]
        assert defining_files == [helper_module], (
            "expected exactly one _mission_meta_exists definition (the extracted "
            f"helper module), found: {defining_files}"
        )
