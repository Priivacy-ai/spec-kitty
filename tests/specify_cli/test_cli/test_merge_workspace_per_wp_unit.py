"""Unit tests for workspace-per-WP merge logic (no git subprocess overhead).

Extracted from test_merge_workspace_per_wp.py to shift-left: these tests
exercise the same decision logic but mock the git boundary, running in
milliseconds instead of seconds.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.merge import (
    _build_workspace_per_wp_merge_plan,
    detect_worktree_structure,
    extract_feature_slug,
    extract_wp_id,
    find_wp_worktrees,
    merge_workspace_per_wp,
    validate_wp_ready_for_merge,
)
from specify_cli.core.vcs import VCSBackend
import specify_cli.cli.commands.merge as merge_module

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Pure-logic helpers (zero I/O)
# ---------------------------------------------------------------------------


class TestExtractFeatureSlug:
    """Tests for extract_feature_slug — pure string parsing."""

    def test_extracts_from_wp_branch(self):
        assert extract_feature_slug("010-workspace-per-wp-WP01") == "010-workspace-per-wp"
        assert extract_feature_slug("005-my-feature-WP12") == "005-my-feature"

    def test_returns_as_is_for_legacy_branch(self):
        assert extract_feature_slug("008-unified-cli") == "008-unified-cli"
        assert extract_feature_slug("main") == "main"

    def test_handles_edge_cases(self):
        assert extract_feature_slug("WP01") == "WP01"  # no prefix
        assert extract_feature_slug("") == ""
        assert extract_feature_slug("feature-WP99") == "feature"


class TestExtractWpId:
    """Tests for extract_wp_id — pure Path parsing."""

    def test_extracts_wp_id(self):
        assert extract_wp_id(Path(".worktrees/010-feature-WP01")) == "WP01"
        assert extract_wp_id(Path(".worktrees/010-feature-WP12")) == "WP12"

    def test_returns_none_for_legacy(self):
        assert extract_wp_id(Path(".worktrees/008-unified-cli")) is None

    def test_handles_edge_cases(self):
        assert extract_wp_id(Path("WP01")) is None  # no dash prefix
        assert extract_wp_id(Path(".worktrees/feature-WP1")) is None  # only 1 digit
        assert extract_wp_id(Path(".worktrees/feature-WP001")) is None  # 3 digits


# ---------------------------------------------------------------------------
# detect_worktree_structure — filesystem + optional git branch listing
# ---------------------------------------------------------------------------


class TestDetectWorktreeStructureMocked:
    """detect_worktree_structure with mocked filesystem and git."""

    def test_detects_workspace_per_wp_from_directory_pattern(self, tmp_path):
        """WP dirs present → workspace-per-wp."""
        wt = tmp_path / ".worktrees"
        wt.mkdir()
        (wt / "010-feature-WP01").mkdir()
        (wt / "010-feature-WP02").mkdir()

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(merge_module, "_list_wp_branches", return_value=[]),
        ):
            assert detect_worktree_structure(tmp_path, "010-feature") == "workspace-per-wp"

    def test_detects_legacy(self, tmp_path):
        """Legacy dir present, no WP dirs → legacy."""
        wt = tmp_path / ".worktrees"
        wt.mkdir()
        (wt / "008-legacy-feature").mkdir()

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(merge_module, "_list_wp_branches", return_value=[]),
        ):
            assert detect_worktree_structure(tmp_path, "008-legacy-feature") == "legacy"

    def test_detects_none_when_no_worktrees_dir(self, tmp_path):
        with patch.object(merge_module, "get_main_repo_root", return_value=tmp_path):
            assert detect_worktree_structure(tmp_path, "999-nope") == "none"

    def test_detects_none_when_no_matches(self, tmp_path):
        wt = tmp_path / ".worktrees"
        wt.mkdir()
        (wt / "other-feature-WP01").mkdir()

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(merge_module, "_list_wp_branches", return_value=[]),
        ):
            assert detect_worktree_structure(tmp_path, "999-nope") == "none"

    def test_wp_takes_precedence_over_legacy_in_mixed(self, tmp_path):
        """When both legacy dir and WP dirs exist, WP wins."""
        wt = tmp_path / ".worktrees"
        wt.mkdir()
        (wt / "010-mixed-feature").mkdir()
        (wt / "010-mixed-feature-WP01").mkdir()

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(merge_module, "_list_wp_branches", return_value=[]),
        ):
            assert detect_worktree_structure(tmp_path, "010-mixed-feature") == "workspace-per-wp"

    def test_detects_wp_from_branch_listing_when_dirs_pruned(self, tmp_path):
        """Worktree dirs removed but branches remain → still workspace-per-wp."""
        wt = tmp_path / ".worktrees"
        wt.mkdir()

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(
                merge_module,
                "_list_wp_branches",
                return_value=[("WP01", "010-feature-WP01")],
            ),
        ):
            assert detect_worktree_structure(tmp_path, "010-feature") == "workspace-per-wp"

    def test_resolves_main_repo_from_worktree(self, tmp_path):
        """When called from inside a worktree, gets main repo root."""
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        wt = main_repo / ".worktrees"
        wt.mkdir()
        (wt / "010-feature-WP01").mkdir()
        worktree_cwd = wt / "010-feature-WP01"

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=main_repo),
            patch.object(merge_module, "_list_wp_branches", return_value=[]),
        ):
            assert detect_worktree_structure(worktree_cwd, "010-feature") == "workspace-per-wp"


# ---------------------------------------------------------------------------
# find_wp_worktrees — filesystem glob + git branch fallback
# ---------------------------------------------------------------------------


class TestFindWpWorktreesMocked:
    """find_wp_worktrees with mocked filesystem and git."""

    def test_finds_worktrees_from_directories(self, tmp_path):
        wt = tmp_path / ".worktrees"
        wt.mkdir()
        for n in [1, 2, 3]:
            (wt / f"010-feature-WP{n:02d}").mkdir()

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(merge_module, "_list_wp_branches", return_value=[]),
        ):
            result = find_wp_worktrees(tmp_path, "010-feature")

        assert len(result) == 3
        assert [wp_id for _, wp_id, _ in result] == ["WP01", "WP02", "WP03"]
        assert [branch for _, _, branch in result] == ["010-feature-WP01", "010-feature-WP02", "010-feature-WP03"]

    def test_returns_empty_when_no_matches(self, tmp_path):
        wt = tmp_path / ".worktrees"
        wt.mkdir()

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(merge_module, "_list_wp_branches", return_value=[]),
        ):
            result = find_wp_worktrees(tmp_path, "999-missing")

        assert result == []

    def test_branch_fallback_fills_missing_dirs(self, tmp_path):
        """When dirs are pruned but branches exist, still finds WPs."""
        wt = tmp_path / ".worktrees"
        wt.mkdir()
        (wt / "010-feature-WP01").mkdir()  # Only WP01 dir exists

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(
                merge_module,
                "_list_wp_branches",
                return_value=[
                    ("WP01", "010-feature-WP01"),
                    ("WP02", "010-feature-WP02"),
                ],
            ),
        ):
            result = find_wp_worktrees(tmp_path, "010-feature")

        assert len(result) == 2
        assert [wp_id for _, wp_id, _ in result] == ["WP01", "WP02"]

    def test_sorts_by_wp_number(self, tmp_path):
        wt = tmp_path / ".worktrees"
        wt.mkdir()
        for n in [3, 1, 2]:
            (wt / f"010-feature-WP{n:02d}").mkdir()

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(merge_module, "_list_wp_branches", return_value=[]),
        ):
            result = find_wp_worktrees(tmp_path, "010-feature")

        assert [wp_id for _, wp_id, _ in result] == ["WP01", "WP02", "WP03"]


# ---------------------------------------------------------------------------
# validate_wp_ready_for_merge — subprocess boundary
# ---------------------------------------------------------------------------


class TestValidateWpReadyForMergeMocked:
    """validate_wp_ready_for_merge with mocked subprocess."""

    def test_valid_clean_worktree(self, tmp_path):
        worktree = tmp_path / "wt"
        worktree.mkdir()

        with patch("subprocess.run") as mock_run:
            # rev-parse succeeds, status clean
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git rev-parse --verify
                MagicMock(stdout=""),  # git status --porcelain
            ]
            valid, msg = validate_wp_ready_for_merge(tmp_path, worktree, "branch-WP01")

        assert valid is True
        assert msg == ""

    def test_missing_branch(self, tmp_path):
        worktree = tmp_path / "wt"
        worktree.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128)
            valid, msg = validate_wp_ready_for_merge(tmp_path, worktree, "bad-branch")

        assert valid is False
        assert "does not exist" in msg

    def test_uncommitted_changes(self, tmp_path):
        worktree = tmp_path / "wt"
        worktree.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # branch exists
                MagicMock(stdout="M file.txt\n"),  # dirty
            ]
            valid, msg = validate_wp_ready_for_merge(tmp_path, worktree, "branch-WP01")

        assert valid is False
        assert "uncommitted changes" in msg

    def test_missing_worktree_path_is_ok(self, tmp_path):
        """If worktree dir was pruned, validation passes (branch-only merge)."""
        absent = tmp_path / "does-not-exist"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            valid, msg = validate_wp_ready_for_merge(tmp_path, absent, "branch-WP01")

        assert valid is True
        assert msg == ""


# ---------------------------------------------------------------------------
# _build_workspace_per_wp_merge_plan — ancestry logic
# ---------------------------------------------------------------------------


class TestBuildMergePlanMocked:
    """Test merge plan building with mocked git ancestry checks."""

    def _make_workspaces(self, *wp_ids, slug="010-feature"):
        """Helper to build workspace tuples."""
        return [(Path(f".worktrees/{slug}-{wp_id}"), wp_id, f"{slug}-{wp_id}") for wp_id in wp_ids]

    def test_independent_branches_all_kept(self, tmp_path):
        ws = self._make_workspaces("WP01", "WP02", "WP03")

        with (
            patch.object(merge_module, "_branch_is_ancestor", return_value=False),
            patch.object(merge_module, "_order_wp_workspaces", return_value=ws),
        ):
            plan = _build_workspace_per_wp_merge_plan(
                tmp_path,
                "010-feature",
                "main",
                ws,
            )

        assert len(plan["effective_wp_workspaces"]) == 3
        assert plan["skipped_already_in_target"] == []
        assert plan["skipped_ancestor_of"] == {}

    def test_linear_chain_prunes_to_tip(self, tmp_path):
        ws = self._make_workspaces("WP01", "WP02", "WP03")

        def is_ancestor(repo, branch_a, branch_b):
            # WP01 < WP02 < WP03 (linear chain)
            order = {"010-feature-WP01": 0, "010-feature-WP02": 1, "010-feature-WP03": 2, "main": -1}
            a_idx = order.get(branch_a, -1)
            b_idx = order.get(branch_b, -1)
            return a_idx < b_idx and a_idx >= 0 and b_idx >= 0

        with (
            patch.object(merge_module, "_branch_is_ancestor", side_effect=is_ancestor),
            patch.object(merge_module, "_order_wp_workspaces", return_value=ws),
        ):
            plan = _build_workspace_per_wp_merge_plan(
                tmp_path,
                "010-feature",
                "main",
                ws,
            )

        effective_branches = [b for _, _, b in plan["effective_wp_workspaces"]]
        assert effective_branches == ["010-feature-WP03"]
        assert "010-feature-WP01" in plan["skipped_ancestor_of"]
        assert "010-feature-WP02" in plan["skipped_ancestor_of"]

    def test_already_merged_branches_skipped(self, tmp_path):
        ws = self._make_workspaces("WP01")

        def is_ancestor(repo, branch_a, branch_b):
            # WP01 is ancestor of main → already merged
            return branch_a == "010-feature-WP01" and branch_b == "main"

        with (
            patch.object(merge_module, "_branch_is_ancestor", side_effect=is_ancestor),
            patch.object(merge_module, "_order_wp_workspaces", return_value=ws),
        ):
            plan = _build_workspace_per_wp_merge_plan(
                tmp_path,
                "010-feature",
                "main",
                ws,
            )

        assert plan["effective_wp_workspaces"] == []
        assert len(plan["skipped_already_in_target"]) == 1
        assert (
            "already integrated" in plan["reason_summary"][0].lower() or "skipped" in plan["reason_summary"][0].lower()
        )

    def test_reason_summary_for_single_effective_tip(self, tmp_path):
        ws = self._make_workspaces("WP01", "WP02")

        def is_ancestor(repo, branch_a, branch_b):
            return branch_a == "010-feature-WP01" and branch_b == "010-feature-WP02"

        with (
            patch.object(merge_module, "_branch_is_ancestor", side_effect=is_ancestor),
            patch.object(merge_module, "_order_wp_workspaces", return_value=ws),
        ):
            plan = _build_workspace_per_wp_merge_plan(
                tmp_path,
                "010-feature",
                "main",
                ws,
            )

        assert len(plan["effective_wp_workspaces"]) == 1
        assert any("single effective tip" in r.lower() for r in plan["reason_summary"])


# ---------------------------------------------------------------------------
# merge_workspace_per_wp — dry-run output paths
# ---------------------------------------------------------------------------


class TestMergeWorkspacePerWpDryRunMocked:
    """Dry-run output formatting with fully mocked internals."""

    def test_json_dry_run_empty_feature(self, tmp_path, capsys):
        from specify_cli.cli import StepTracker

        tracker = StepTracker("Merge")
        tracker.add("merge", "Merge feature branch")

        with (
            patch.object(merge_module, "get_main_repo_root", return_value=tmp_path),
            patch.object(merge_module, "find_wp_worktrees", return_value=[]),
        ):
            merge_workspace_per_wp(
                repo_root=tmp_path,
                merge_root=tmp_path,
                feature_slug="999-missing",
                current_branch="feature/test",
                target_branch="main",
                strategy="merge",
                delete_branch=False,
                remove_worktree=False,
                push=False,
                dry_run=True,
                json_output=True,
                tracker=tracker,
            )

        payload = capsys.readouterr().out.strip().splitlines()[-1]
        data = json.loads(payload)
        assert data["feature_slug"] == "999-missing"
        assert data["effective_wp_branches"] == []
        assert "No WP branches/worktrees found" in data["reason_summary"][0]

    def test_human_dry_run_squash_push_cleanup(self, tmp_path, capsys, monkeypatch):
        from specify_cli.cli import StepTracker

        existing = tmp_path / ".worktrees" / "030-feature-WP01"
        existing.mkdir(parents=True)
        missing = tmp_path / ".worktrees" / "030-feature-WP02"

        wp_workspaces = [
            (existing, "WP01", "030-feature-WP01"),
            (missing, "WP02", "030-feature-WP02"),
        ]
        merge_plan = {
            "all_wp_workspaces": wp_workspaces,
            "effective_wp_workspaces": wp_workspaces,
            "skipped_already_in_target": [],
            "skipped_ancestor_of": {},
            "reason_summary": [],
        }

        monkeypatch.setattr(merge_module, "get_main_repo_root", lambda _: tmp_path)
        monkeypatch.setattr(merge_module, "find_wp_worktrees", lambda *a, **kw: wp_workspaces)
        monkeypatch.setattr(merge_module, "validate_wp_ready_for_merge", lambda *a, **kw: (True, ""))
        monkeypatch.setattr(merge_module, "_build_workspace_per_wp_merge_plan", lambda *a, **kw: merge_plan)

        tracker = StepTracker("Merge")
        tracker.add("verify", "Verify readiness")
        tracker.add("checkout", "Switch to main")
        tracker.add("merge", "Merge WPs")
        tracker.add("worktree", "Remove worktrees")
        tracker.add("branch", "Delete branches")

        merge_workspace_per_wp(
            repo_root=tmp_path,
            merge_root=tmp_path,
            feature_slug="030-feature",
            current_branch="feature/test",
            target_branch="main",
            strategy="squash",
            delete_branch=True,
            remove_worktree=True,
            push=True,
            dry_run=True,
            json_output=False,
            tracker=tracker,
        )

        output = capsys.readouterr().out
        assert "Dry run - would execute" in output
        assert "git merge --squash 030-feature-WP01" in output
        assert "git merge --squash 030-feature-WP02" in output
        assert "git push origin main" in output
        assert "git branch -d 030-feature-WP01" in output
        assert "git branch -d 030-feature-WP02" in output
        assert "# skip worktree removal for WP02 (path not present)" in output


# ---------------------------------------------------------------------------
# VCS abstraction — detection logic with mocked backends
# ---------------------------------------------------------------------------


class TestVCSDetectionMocked:
    """VCS backend detection with mocked availability checks."""

    def test_detects_git_backend(self, tmp_path):
        (tmp_path / ".git").mkdir()

        from specify_cli.core.vcs import detection

        detection.is_jj_available.cache_clear()

        with patch.object(detection, "is_jj_available", return_value=False):
            from specify_cli.core.vcs import get_vcs

            vcs = get_vcs(tmp_path)
            assert vcs.backend == VCSBackend.GIT

    def test_falls_back_to_git_when_jj_unavailable(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".jj").mkdir()

        from specify_cli.core.vcs import detection

        detection.is_jj_available.cache_clear()

        with patch.object(detection, "is_jj_available", return_value=False):
            from specify_cli.core.vcs import get_vcs

            vcs = get_vcs(tmp_path)
            assert vcs.backend == VCSBackend.GIT
