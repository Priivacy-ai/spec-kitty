"""Tests for worktree topology analysis.

Tests cover:
1. WPTopologyEntry and FeatureTopology data structures
2. Stacking detection (has_stacking property)
3. materialize_worktree_topology with filesystem fixtures
4. render_topology_json output format
5. render_topology_text output format
6. Flat features (no stacking) produce no topology output
7. Linear chain (WP01 → WP02 → WP03)
8. Diamond pattern (WP01 → WP02, WP01 → WP03, both → WP04)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from specify_cli.core.worktree_topology import (
    WPTopologyEntry,
    FeatureTopology,
    render_topology_json,
    render_topology_text,
    materialize_worktree_topology,
    _resolve_base_wp,
)


# ============================================================================
# Data structure tests
# ============================================================================


class TestWPTopologyEntry:
    def test_defaults(self):
        entry = WPTopologyEntry(
            wp_id="WP01",
            branch_name="feat-WP01",
            base_branch="main",
            base_wp=None,
        )
        assert entry.wp_id == "WP01"
        assert entry.dependencies == []
        assert entry.lane == "planned"
        assert entry.worktree_exists is False
        assert entry.commits_ahead_of_base == 0

    def test_stacked_entry(self):
        entry = WPTopologyEntry(
            wp_id="WP03",
            branch_name="feat-WP03",
            base_branch="feat-WP01",
            base_wp="WP01",
            dependencies=["WP01"],
            lane="doing",
            worktree_exists=True,
            commits_ahead_of_base=5,
        )
        assert entry.base_wp == "WP01"
        assert entry.commits_ahead_of_base == 5


class TestFeatureTopology:
    def _make_topology(self, entries):
        return FeatureTopology(
            feature_slug="002-feature",
            target_branch="main",
            entries=entries,
        )

    def test_has_stacking_false_when_flat(self):
        topology = self._make_topology([
            WPTopologyEntry(wp_id="WP01", branch_name="feat-WP01", base_branch="main", base_wp=None),
            WPTopologyEntry(wp_id="WP02", branch_name="feat-WP02", base_branch="main", base_wp=None),
        ])
        assert topology.has_stacking is False

    def test_has_stacking_true_when_stacked(self):
        topology = self._make_topology([
            WPTopologyEntry(wp_id="WP01", branch_name="feat-WP01", base_branch="main", base_wp=None),
            WPTopologyEntry(wp_id="WP02", branch_name="feat-WP02", base_branch="feat-WP01", base_wp="WP01"),
        ])
        assert topology.has_stacking is True

    def test_get_entry(self):
        topology = self._make_topology([
            WPTopologyEntry(wp_id="WP01", branch_name="feat-WP01", base_branch="main", base_wp=None),
            WPTopologyEntry(wp_id="WP02", branch_name="feat-WP02", base_branch="main", base_wp=None),
        ])
        assert topology.get_entry("WP01").wp_id == "WP01"
        assert topology.get_entry("WP02").wp_id == "WP02"
        assert topology.get_entry("WP99") is None

    def test_get_actual_base_for_wp_stacked(self):
        topology = self._make_topology([
            WPTopologyEntry(wp_id="WP01", branch_name="feat-WP01", base_branch="main", base_wp=None),
            WPTopologyEntry(wp_id="WP03", branch_name="feat-WP03", base_branch="feat-WP01", base_wp="WP01"),
        ])
        assert topology.get_actual_base_for_wp("WP03") == "feat-WP01"
        assert topology.get_actual_base_for_wp("WP01") == "main"

    def test_get_actual_base_for_wp_unknown(self):
        topology = self._make_topology([])
        assert topology.get_actual_base_for_wp("WP99") == "main"


# ============================================================================
# _resolve_base_wp tests
# ============================================================================


class TestResolveBaseWP:
    def test_base_is_wp_branch(self):
        wp_branches = {"WP01": "feat-WP01", "WP02": "feat-WP02"}
        assert _resolve_base_wp("feat-WP01", "002-feature", wp_branches) == "WP01"

    def test_base_is_target_branch(self):
        wp_branches = {"WP01": "feat-WP01", "WP02": "feat-WP02"}
        assert _resolve_base_wp("main", "002-feature", wp_branches) is None

    def test_base_is_unknown_branch(self):
        wp_branches = {"WP01": "feat-WP01"}
        assert _resolve_base_wp("some-other-branch", "002-feature", wp_branches) is None


# ============================================================================
# render_topology_json tests
# ============================================================================


class TestRenderTopologyJson:
    def _make_stacked_topology(self):
        return FeatureTopology(
            feature_slug="002-event-driven",
            target_branch="main",
            entries=[
                WPTopologyEntry(
                    wp_id="WP01", branch_name="002-event-WP01",
                    base_branch="main", base_wp=None,
                    lane="done", worktree_exists=True, commits_ahead_of_base=3,
                ),
                WPTopologyEntry(
                    wp_id="WP02", branch_name="002-event-WP02",
                    base_branch="main", base_wp=None,
                    lane="doing", worktree_exists=True, commits_ahead_of_base=5,
                ),
                WPTopologyEntry(
                    wp_id="WP03", branch_name="002-event-WP03",
                    base_branch="002-event-WP01", base_wp="WP01",
                    lane="doing", worktree_exists=True, commits_ahead_of_base=2,
                ),
                WPTopologyEntry(
                    wp_id="WP04", branch_name=None,
                    base_branch=None, base_wp=None,
                    dependencies=["WP02", "WP03"], lane="planned",
                ),
            ],
        )

    def test_json_markers(self):
        topology = self._make_stacked_topology()
        lines = render_topology_json(topology, "WP03")
        assert lines[0] == "<!-- WORKTREE_TOPOLOGY -->"
        assert lines[-1] == "<!-- /WORKTREE_TOPOLOGY -->"

    def test_json_parseable(self):
        topology = self._make_stacked_topology()
        lines = render_topology_json(topology, "WP03")
        # Extract JSON between markers
        json_str = "\n".join(lines[1:-1])
        payload = json.loads(json_str)
        assert payload["feature"] == "002-event-driven"
        assert payload["target_branch"] == "main"
        assert payload["current_wp"] == "WP03"
        assert payload["stacked"] is True

    def test_your_base_for_stacked_wp(self):
        topology = self._make_stacked_topology()
        lines = render_topology_json(topology, "WP03")
        payload = json.loads("\n".join(lines[1:-1]))
        assert payload["your_base"] == {"branch": "002-event-WP01", "wp": "WP01"}
        assert "NOT main" in payload["note"]

    def test_your_base_for_non_stacked_wp(self):
        topology = self._make_stacked_topology()
        lines = render_topology_json(topology, "WP01")
        payload = json.loads("\n".join(lines[1:-1]))
        assert payload["your_base"] is None

    def test_diff_command_uses_actual_base(self):
        topology = self._make_stacked_topology()
        lines = render_topology_json(topology, "WP03")
        payload = json.loads("\n".join(lines[1:-1]))
        assert payload["diff_command"] == "git diff 002-event-WP01..HEAD"

    def test_entries_list(self):
        topology = self._make_stacked_topology()
        lines = render_topology_json(topology, "WP03")
        payload = json.loads("\n".join(lines[1:-1]))
        assert len(payload["entries"]) == 4
        # WP04 has no branch but has dependencies
        wp04 = payload["entries"][3]
        assert wp04["branch"] is None
        assert wp04["dependencies"] == ["WP02", "WP03"]


# ============================================================================
# render_topology_text tests
# ============================================================================


class TestRenderTopologyText:
    def test_box_structure(self):
        topology = FeatureTopology(
            feature_slug="002-feature",
            target_branch="main",
            entries=[
                WPTopologyEntry(wp_id="WP01", branch_name="feat-WP01",
                                base_branch="main", base_wp=None, lane="done"),
                WPTopologyEntry(wp_id="WP02", branch_name="feat-WP02",
                                base_branch="feat-WP01", base_wp="WP01", lane="doing"),
            ],
        )
        lines = render_topology_text(topology, "WP02")
        assert lines[0].startswith("╔")
        assert lines[-1].startswith("╚")
        assert any("WORKTREE TOPOLOGY" in line for line in lines)

    def test_current_wp_highlighted(self):
        topology = FeatureTopology(
            feature_slug="002-feature",
            target_branch="main",
            entries=[
                WPTopologyEntry(wp_id="WP01", branch_name="feat-WP01",
                                base_branch="main", base_wp=None, lane="done"),
                WPTopologyEntry(wp_id="WP02", branch_name="feat-WP02",
                                base_branch="feat-WP01", base_wp="WP01", lane="doing"),
            ],
        )
        lines = render_topology_text(topology, "WP02")
        wp02_lines = [l for l in lines if "WP02" in l and "→" in l]
        assert len(wp02_lines) > 0

    def test_non_current_wp_not_highlighted(self):
        topology = FeatureTopology(
            feature_slug="002-feature",
            target_branch="main",
            entries=[
                WPTopologyEntry(wp_id="WP01", branch_name="feat-WP01",
                                base_branch="main", base_wp=None, lane="done"),
                WPTopologyEntry(wp_id="WP02", branch_name="feat-WP02",
                                base_branch="feat-WP01", base_wp="WP01", lane="doing"),
            ],
        )
        lines = render_topology_text(topology, "WP02")
        # WP01 line should have space marker, not arrow
        wp01_lines = [l for l in lines if "WP01" in l and "[done]" in l]
        for line in wp01_lines:
            # The marker before WP01 should be a space, not →
            idx = line.index("WP01")
            assert line[idx - 2] == " "


# ============================================================================
# materialize_worktree_topology tests (with mocking)
# ============================================================================


class TestMaterializeWorktreeTopology:
    """Test materialization with mocked dependencies."""

    @patch("specify_cli.core.worktree_topology.list_contexts")
    @patch("specify_cli.core.worktree_topology.build_dependency_graph")
    @patch("specify_cli.core.worktree_topology.topological_sort")
    @patch("specify_cli.core.worktree_topology.get_feature_target_branch")
    @patch("specify_cli.core.worktree_topology.get_main_repo_root")
    @patch("specify_cli.core.worktree_topology.read_frontmatter")
    def test_flat_feature_no_stacking(
        self, mock_read_fm, mock_main_root, mock_target, mock_topo,
        mock_dep_graph, mock_list_ctx, tmp_path,
    ):
        """Flat feature where all WPs branch from main."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        feature_dir = repo_root / "kitty-specs" / "002-feature" / "tasks"
        feature_dir.mkdir(parents=True)

        # Create WP files
        (feature_dir / "WP01-setup.md").write_text("---\nwork_package_id: WP01\nlane: done\n---\n")
        (feature_dir / "WP02-impl.md").write_text("---\nwork_package_id: WP02\nlane: doing\n---\n")

        mock_main_root.return_value = repo_root
        mock_target.return_value = "main"
        mock_dep_graph.return_value = {"WP01": [], "WP02": []}
        mock_topo.return_value = ["WP01", "WP02"]

        # Both WPs based on main
        ctx1 = MagicMock()
        ctx1.wp_id = "WP01"
        ctx1.feature_slug = "002-feature"
        ctx1.branch_name = "002-feature-WP01"
        ctx1.base_branch = "main"

        ctx2 = MagicMock()
        ctx2.wp_id = "WP02"
        ctx2.feature_slug = "002-feature"
        ctx2.branch_name = "002-feature-WP02"
        ctx2.base_branch = "main"

        mock_list_ctx.return_value = [ctx1, ctx2]

        # Mock read_frontmatter for lane detection
        def fake_read_fm(path):
            if "WP01" in str(path):
                return ({"work_package_id": "WP01", "lane": "done"}, "")
            return ({"work_package_id": "WP02", "lane": "doing"}, "")

        mock_read_fm.side_effect = fake_read_fm

        topology = materialize_worktree_topology(repo_root, "002-feature")

        assert topology.feature_slug == "002-feature"
        assert topology.target_branch == "main"
        assert topology.has_stacking is False
        assert len(topology.entries) == 2

    @patch("specify_cli.core.worktree_topology.list_contexts")
    @patch("specify_cli.core.worktree_topology.build_dependency_graph")
    @patch("specify_cli.core.worktree_topology.topological_sort")
    @patch("specify_cli.core.worktree_topology.get_feature_target_branch")
    @patch("specify_cli.core.worktree_topology.get_main_repo_root")
    @patch("specify_cli.core.worktree_topology.read_frontmatter")
    def test_linear_chain_stacking(
        self, mock_read_fm, mock_main_root, mock_target, mock_topo,
        mock_dep_graph, mock_list_ctx, tmp_path,
    ):
        """Linear chain: WP01 → WP02 → WP03 (each branches from previous)."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        feature_dir = repo_root / "kitty-specs" / "002-feature" / "tasks"
        feature_dir.mkdir(parents=True)

        for wp in ["WP01", "WP02", "WP03"]:
            (feature_dir / f"{wp}.md").write_text(f"---\nwork_package_id: {wp}\nlane: doing\n---\n")

        mock_main_root.return_value = repo_root
        mock_target.return_value = "main"
        mock_dep_graph.return_value = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"]}
        mock_topo.return_value = ["WP01", "WP02", "WP03"]

        ctx1 = MagicMock(wp_id="WP01", feature_slug="002-feature",
                         branch_name="002-WP01", base_branch="main")
        ctx2 = MagicMock(wp_id="WP02", feature_slug="002-feature",
                         branch_name="002-WP02", base_branch="002-WP01")
        ctx3 = MagicMock(wp_id="WP03", feature_slug="002-feature",
                         branch_name="002-WP03", base_branch="002-WP02")
        mock_list_ctx.return_value = [ctx1, ctx2, ctx3]

        def fake_read_fm(path):
            for wp in ["WP01", "WP02", "WP03"]:
                if wp in str(path):
                    return ({"work_package_id": wp, "lane": "doing"}, "")
            return ({}, "")

        mock_read_fm.side_effect = fake_read_fm

        topology = materialize_worktree_topology(repo_root, "002-feature")

        assert topology.has_stacking is True
        assert len(topology.entries) == 3

        # WP01 bases on main (no stacking)
        assert topology.entries[0].base_wp is None
        # WP02 bases on WP01
        assert topology.entries[1].base_wp == "WP01"
        # WP03 bases on WP02
        assert topology.entries[2].base_wp == "WP02"

    @patch("specify_cli.core.worktree_topology.list_contexts")
    @patch("specify_cli.core.worktree_topology.build_dependency_graph")
    @patch("specify_cli.core.worktree_topology.topological_sort")
    @patch("specify_cli.core.worktree_topology.get_feature_target_branch")
    @patch("specify_cli.core.worktree_topology.get_main_repo_root")
    @patch("specify_cli.core.worktree_topology.read_frontmatter")
    def test_diamond_pattern(
        self, mock_read_fm, mock_main_root, mock_target, mock_topo,
        mock_dep_graph, mock_list_ctx, tmp_path,
    ):
        """Diamond: WP01 → WP02 and WP03, both → WP04."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        feature_dir = repo_root / "kitty-specs" / "002-feature" / "tasks"
        feature_dir.mkdir(parents=True)

        for wp in ["WP01", "WP02", "WP03", "WP04"]:
            (feature_dir / f"{wp}.md").write_text(f"---\nwork_package_id: {wp}\nlane: doing\n---\n")

        mock_main_root.return_value = repo_root
        mock_target.return_value = "main"
        mock_dep_graph.return_value = {
            "WP01": [], "WP02": ["WP01"], "WP03": ["WP01"], "WP04": ["WP02", "WP03"],
        }
        mock_topo.return_value = ["WP01", "WP02", "WP03", "WP04"]

        ctx1 = MagicMock(wp_id="WP01", feature_slug="002-feature",
                         branch_name="002-WP01", base_branch="main")
        ctx2 = MagicMock(wp_id="WP02", feature_slug="002-feature",
                         branch_name="002-WP02", base_branch="002-WP01")
        ctx3 = MagicMock(wp_id="WP03", feature_slug="002-feature",
                         branch_name="002-WP03", base_branch="002-WP01")
        # WP04 bases on WP03 (one of its two deps)
        ctx4 = MagicMock(wp_id="WP04", feature_slug="002-feature",
                         branch_name="002-WP04", base_branch="002-WP03")
        mock_list_ctx.return_value = [ctx1, ctx2, ctx3, ctx4]

        def fake_read_fm(path):
            for wp in ["WP01", "WP02", "WP03", "WP04"]:
                if wp in str(path):
                    return ({"work_package_id": wp, "lane": "doing"}, "")
            return ({}, "")

        mock_read_fm.side_effect = fake_read_fm

        topology = materialize_worktree_topology(repo_root, "002-feature")

        assert topology.has_stacking is True
        assert len(topology.entries) == 4

        # WP02 and WP03 both base on WP01
        assert topology.entries[1].base_wp == "WP01"
        assert topology.entries[2].base_wp == "WP01"

        # WP04 bases on WP03
        assert topology.entries[3].base_wp == "WP03"

    @patch("specify_cli.core.worktree_topology.list_contexts")
    @patch("specify_cli.core.worktree_topology.build_dependency_graph")
    @patch("specify_cli.core.worktree_topology.topological_sort")
    @patch("specify_cli.core.worktree_topology.get_feature_target_branch")
    @patch("specify_cli.core.worktree_topology.get_main_repo_root")
    @patch("specify_cli.core.worktree_topology.read_frontmatter")
    def test_wp_without_context_gets_none_base(
        self, mock_read_fm, mock_main_root, mock_target, mock_topo,
        mock_dep_graph, mock_list_ctx, tmp_path,
    ):
        """WP with no workspace context (not yet implemented) gets None for base."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        feature_dir = repo_root / "kitty-specs" / "002-feature" / "tasks"
        feature_dir.mkdir(parents=True)
        (feature_dir / "WP01.md").write_text("---\nwork_package_id: WP01\nlane: planned\n---\n")

        mock_main_root.return_value = repo_root
        mock_target.return_value = "main"
        mock_dep_graph.return_value = {"WP01": []}
        mock_topo.return_value = ["WP01"]
        mock_list_ctx.return_value = []  # No contexts (WP not implemented yet)

        def fake_read_fm(path):
            return ({"work_package_id": "WP01", "lane": "planned"}, "")

        mock_read_fm.side_effect = fake_read_fm

        topology = materialize_worktree_topology(repo_root, "002-feature")

        assert len(topology.entries) == 1
        entry = topology.entries[0]
        assert entry.branch_name is None
        assert entry.base_branch is None
        assert entry.base_wp is None
        assert entry.worktree_exists is False


# ============================================================================
# Integration: render_topology_json for stacked features
# ============================================================================


class TestRenderTopologyJsonIntegration:
    def test_stacked_wp_gets_correct_note(self):
        topology = FeatureTopology(
            feature_slug="002-feature",
            target_branch="main",
            entries=[
                WPTopologyEntry(
                    wp_id="WP01", branch_name="002-WP01",
                    base_branch="main", base_wp=None,
                    lane="done", worktree_exists=True, commits_ahead_of_base=10,
                ),
                WPTopologyEntry(
                    wp_id="WP03", branch_name="002-WP03",
                    base_branch="002-WP01", base_wp="WP01",
                    lane="doing", worktree_exists=True, commits_ahead_of_base=2,
                ),
            ],
        )
        lines = render_topology_json(topology, "WP03")
        payload = json.loads("\n".join(lines[1:-1]))

        # Should tell agent it stacks on WP01, NOT main
        assert "WP01" in payload["note"]
        assert "NOT main" in payload["note"]
        assert payload["diff_command"] == "git diff 002-WP01..HEAD"

    def test_non_stacked_wp_in_stacked_feature(self):
        """A WP based on main in a feature that has stacking elsewhere."""
        topology = FeatureTopology(
            feature_slug="002-feature",
            target_branch="main",
            entries=[
                WPTopologyEntry(
                    wp_id="WP01", branch_name="002-WP01",
                    base_branch="main", base_wp=None, lane="done",
                    worktree_exists=True, commits_ahead_of_base=10,
                ),
                WPTopologyEntry(
                    wp_id="WP02", branch_name="002-WP02",
                    base_branch="main", base_wp=None, lane="doing",
                    worktree_exists=True, commits_ahead_of_base=5,
                ),
                WPTopologyEntry(
                    wp_id="WP03", branch_name="002-WP03",
                    base_branch="002-WP01", base_wp="WP01", lane="doing",
                    worktree_exists=True, commits_ahead_of_base=2,
                ),
            ],
        )
        lines = render_topology_json(topology, "WP02")
        payload = json.loads("\n".join(lines[1:-1]))

        # WP02 is based on main, but feature has stacking
        assert payload["your_base"] is None
        assert payload["diff_command"] == "git diff main..HEAD"
        assert "Other WPs" in payload["note"]
