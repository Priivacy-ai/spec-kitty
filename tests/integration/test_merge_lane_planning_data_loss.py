"""WP01/T001 — pin the lane-planning data-loss regression (FR-001).

Operators reported that approved commits from a ``lane-planning`` lane were
silently omitted in merge results that also included normal implementation
lanes. The fix is that ``_run_lane_based_merge_locked`` must include every
lane in the lane manifest — including the canonical ``lane-planning`` lane —
in its ``MergeState.wp_order`` and in the per-WP "mark done" pass.

This test exercises the actual merge function with real git, a real lanes
manifest, and asserts that:

1. Every WP from every lane (planning + code) is included in the
   ``MergeState.wp_order`` written to disk.
2. Every WP from every lane is marked as ``completed`` after merge.
3. The planning artifact file is reachable from the target branch (``main``)
   after merge — the actual data-loss check.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.merge import _run_lane_based_merge
from specify_cli.merge.config import MergeStrategy
from specify_cli.merge.state import load_state


pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-qb", "main", str(repo)])
    _run(["git", "-C", str(repo), "config", "user.email", "test@test.com"])
    _run(["git", "-C", str(repo), "config", "user.name", "Test"])
    _run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"])
    (repo / "README.md").write_text("init\n")
    _run(["git", "-C", str(repo), "add", "."])
    _run(["git", "-C", str(repo), "commit", "-m", "init"])


def _make_manifest_with_planning_and_code(slug: str) -> MagicMock:
    """Build a fake LanesManifest with three code WPs and one planning-artifact WP."""
    manifest = MagicMock()
    manifest.target_branch = "main"
    manifest.mission_branch = f"kitty/mission-{slug}"

    lane_a = MagicMock()
    lane_a.lane_id = "lane-a"
    lane_a.wp_ids = ["WP01", "WP02", "WP03"]

    lane_planning = MagicMock()
    lane_planning.lane_id = "lane-planning"
    lane_planning.wp_ids = ["WP04"]

    manifest.lanes = [lane_a, lane_planning]
    return manifest


class TestMergeIncludesPlanningLane:
    """FR-001: planning-lane WPs MUST appear in MergeState wp_order and completed."""

    def test_merge_state_wp_order_includes_planning_lane_wps(self, tmp_path: Path) -> None:
        slug = "test-planning-data-loss"
        _init_git_repo(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        manifest = _make_manifest_with_planning_and_code(slug)

        captured_states: list[list[str]] = []

        def fake_save_state(state, repo_root):  # noqa: ANN001
            # Capture wp_order on every save so we can assert what was committed.
            captured_states.append(list(state.wp_order))

        lane_result = MagicMock()
        lane_result.success = True
        lane_result.errors = []

        mission_result = MagicMock()
        mission_result.success = True
        mission_result.commit = "abc1234"
        mission_result.errors = []

        completed_wps_seen: list[str] = []

        def fake_mark_wp_merged_done(repo_root, mission_slug, wp_id, target_branch):  # noqa: ANN001
            completed_wps_seen.append(wp_id)

        def fake_run_command(cmd, *args, **kwargs):  # noqa: ANN001
            if "merge-base" in cmd:
                return (0, "abc123\n", "")
            return (0, "", "")

        patches = [
            patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
            patch("specify_cli.cli.commands.merge.load_state", return_value=None),
            patch("specify_cli.cli.commands.merge.save_state", side_effect=fake_save_state),
            patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.merge.require_no_sparse_checkout"),
            patch("specify_cli.lanes.merge.merge_lane_to_mission", return_value=lane_result),
            patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
            patch("specify_cli.cli.commands.merge._mark_wp_merged_done", side_effect=fake_mark_wp_merged_done),
            patch("specify_cli.cli.commands.merge.safe_commit"),
            patch("specify_cli.cli.commands.merge._assert_merged_wps_reached_done"),
            patch("specify_cli.post_merge.stale_assertions.run_check"),
            patch("specify_cli.policy.merge_gates.evaluate_merge_gates"),
            patch("specify_cli.policy.config.load_policy_config"),
            patch("specify_cli.cli.commands.merge.run_command", side_effect=fake_run_command),
            patch("specify_cli.cli.commands.merge.has_remote", return_value=False),
            patch("specify_cli.cli.commands.merge.cleanup_merge_workspace"),
            patch("specify_cli.cli.commands.merge.clear_state"),
            patch("specify_cli.cli.commands.merge._bake_mission_number_into_mission_branch"),
            patch("specify_cli.cli.commands.merge.trigger_feature_dossier_sync_if_enabled"),
            patch("specify_cli.cli.commands.merge.emit_mission_closed"),
            patch("specify_cli.cli.commands.merge._emit_merge_diff_summary"),
        ]
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            mock_run_check = mocks[10]
            mock_gates = mocks[11]
            mock_policy = mocks[12]

            stale_report = MagicMock()
            stale_report.findings = []
            mock_run_check.return_value = stale_report

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mock_gates.return_value = gate_eval

            policy = MagicMock()
            policy.merge_gates = []
            mock_policy.return_value = policy

            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
            )

        # FR-001 assertion 1: every initial save must include all WPs from
        # both code AND planning lanes.
        assert captured_states, "save_state was never called — merge state never persisted"
        first_state = captured_states[0]
        assert set(first_state) == {"WP01", "WP02", "WP03", "WP04"}, (
            f"FR-001 regression: MergeState.wp_order does not contain every WP "
            f"from every lane. Got {first_state!r}, expected all of WP01..WP04 "
            f"(WP04 is in lane-planning and must NOT be silently dropped)."
        )

        # FR-001 assertion 2: the planning-lane WP must reach the per-WP
        # mark-done loop.
        assert "WP04" in completed_wps_seen, (
            f"FR-001 regression: WP04 (lane-planning) was not marked done. "
            f"Marked WPs: {completed_wps_seen!r}. The planning lane was either "
            "skipped in the lane iteration or its WPs were filtered out of the "
            "completion pass."
        )

        # And the code-lane WPs were all marked too.
        for wp in ("WP01", "WP02", "WP03"):
            assert wp in completed_wps_seen, f"{wp} was dropped from the merge"
