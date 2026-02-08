"""Tests for status reconcile module.

All git operations are mocked via subprocess.run to avoid
needing real git repositories in unit tests.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.status.models import Lane, StatusEvent, StatusSnapshot
from specify_cli.status.reconcile import (
    CommitInfo,
    ReconcileResult,
    _generate_reconciliation_events,
    _get_current_lane,
    _lane_advancement_chain,
    format_reconcile_report,
    reconcile,
    reconcile_result_to_json,
    scan_for_wp_commits,
)


# ── Fixtures ──────────────────────────────────────────────────────


def _make_snapshot(
    feature_slug: str = "034-test-feature",
    wp_lanes: dict[str, str] | None = None,
) -> StatusSnapshot:
    """Factory for StatusSnapshot."""
    wp_states = {}
    summary = {lane.value: 0 for lane in Lane}

    if wp_lanes:
        for wp_id, lane_str in wp_lanes.items():
            wp_states[wp_id] = {
                "lane": lane_str,
                "actor": "test",
                "last_transition_at": "2026-01-01T00:00:00+00:00",
                "last_event_id": "01AAAAAAAAAAAAAAAAAAAAAAAA",
                "force_count": 0,
            }
            summary[lane_str] = summary.get(lane_str, 0) + 1

    return StatusSnapshot(
        feature_slug=feature_slug,
        materialized_at="2026-01-01T00:00:00+00:00",
        event_count=0,
        last_event_id=None,
        work_packages=wp_states,
        summary=summary,
    )


def _make_commit_info(
    sha: str = "abc1234",
    branch: str = "034-test-feature-WP01",
    message: str = "feat(WP01): implement thing",
    author: str = "test-agent",
    date: str = "2026-01-01T12:00:00+00:00",
) -> CommitInfo:
    """Factory for CommitInfo."""
    return CommitInfo(
        sha=sha,
        branch=branch,
        message=message,
        author=author,
        date=date,
    )


# ── CommitInfo dataclass tests ────────────────────────────────────


class TestCommitInfo:
    def test_creation_and_field_access(self):
        ci = CommitInfo(
            sha="abc1234def5678",
            branch="034-feature-WP01",
            message="feat(WP01): add models",
            author="alice",
            date="2026-02-08T12:00:00Z",
        )
        assert ci.sha == "abc1234def5678"
        assert ci.branch == "034-feature-WP01"
        assert ci.message == "feat(WP01): add models"
        assert ci.author == "alice"
        assert ci.date == "2026-02-08T12:00:00Z"

    def test_frozen(self):
        ci = _make_commit_info()
        with pytest.raises(AttributeError):
            ci.sha = "changed"


# ── scan_for_wp_commits tests ────────────────────────────────────


class TestScanForWpCommits:
    @patch("specify_cli.status.reconcile.subprocess.run")
    def test_finds_branches(self, mock_run, tmp_path):
        """Branch listing returns WP references, parsed correctly."""
        # Branch listing response
        branch_output = (
            "  034-test-feature-WP01\n"
            "  034-test-feature-WP02\n"
            "  remotes/origin/034-test-feature-WP03\n"
        )
        # Log response for each branch
        log_output = "abc1234deadbeef\nfeat(WP01): add models\nalice\n2026-01-01T00:00:00Z\n"
        # Grep response (empty, no commit message matches)
        grep_output = ""

        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "branch" in cmd_str and "-a" in cmd_str:
                result.stdout = branch_output
            elif "log" in cmd_str and "--grep" in cmd_str:
                result.stdout = grep_output
            elif "log" in cmd_str and "-1" in cmd_str:
                result.stdout = log_output
            else:
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        commits = scan_for_wp_commits(tmp_path, "034-test-feature")

        assert "WP01" in commits
        assert "WP02" in commits
        assert "WP03" in commits
        assert len(commits["WP01"]) >= 1
        assert commits["WP01"][0].sha.startswith("abc1234")

    @patch("specify_cli.status.reconcile.subprocess.run")
    def test_finds_commit_messages(self, mock_run, tmp_path):
        """Commit message grep finds WP IDs in messages."""
        branch_output = ""
        # The grep command uses --grep={feature_slug} and --format=%H %s
        # Messages must contain the feature slug AND have WP IDs
        grep_output = (
            "abc1234 034-test-feature WP03: implement status models\n"
            "def5678 034-test-feature WP03: handle edge case\n"
        )
        detail_output = "alice\n2026-01-01T00:00:00Z\n"

        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "branch" in cmd_str and "-a" in cmd_str:
                result.stdout = branch_output
            elif "log" in cmd_str and "--grep" in cmd_str:
                result.stdout = grep_output
            elif "log" in cmd_str and "-1" in cmd_str:
                result.stdout = detail_output
            else:
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        commits = scan_for_wp_commits(tmp_path, "034-test-feature")

        assert "WP03" in commits
        assert len(commits["WP03"]) == 2

    @patch("specify_cli.status.reconcile.subprocess.run")
    def test_empty_repo(self, mock_run, tmp_path):
        """No matching branches or commits returns empty dict."""
        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        commits = scan_for_wp_commits(tmp_path, "034-test-feature")
        assert commits == {}

    @patch("specify_cli.status.reconcile.subprocess.run")
    def test_timeout_handling(self, mock_run, tmp_path):
        """subprocess.TimeoutExpired is caught gracefully."""
        def side_effect(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 30)

        mock_run.side_effect = side_effect

        # Should not raise -- timeout is caught and logged
        commits = scan_for_wp_commits(tmp_path, "034-test-feature")
        assert commits == {}

    def test_nonexistent_repo(self, tmp_path):
        """Non-existent repo path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            scan_for_wp_commits(tmp_path / "does-not-exist", "034-test-feature")


# ── _generate_reconciliation_events tests ─────────────────────────


class TestGenerateReconciliationEvents:
    def test_wp_in_planned_with_commits(self):
        """WP in planned with commits produces transition to claimed."""
        snapshot = _make_snapshot(wp_lanes={"WP01": "planned"})
        commit_map = {"WP01": [_make_commit_info()]}
        merged_wps: set[str] = set()

        events, details = _generate_reconciliation_events(
            "034-test-feature", snapshot, commit_map, merged_wps,
        )

        assert len(events) >= 1
        assert events[0].wp_id == "WP01"
        assert events[0].from_lane == Lane.PLANNED
        assert events[0].to_lane == Lane.CLAIMED
        assert events[0].actor == "reconcile"
        assert events[0].execution_mode == "direct_repo"

    def test_wp_in_in_progress_with_merged_branch(self):
        """WP in in_progress with merged branch produces transition to for_review."""
        snapshot = _make_snapshot(wp_lanes={"WP02": "in_progress"})
        commit_map = {"WP02": [_make_commit_info()]}
        merged_wps = {"WP02"}

        events, details = _generate_reconciliation_events(
            "034-test-feature", snapshot, commit_map, merged_wps,
        )

        assert len(events) >= 1
        # Should advance from in_progress to for_review
        assert any(
            e.wp_id == "WP02" and e.to_lane == Lane.FOR_REVIEW
            for e in events
        )

    def test_wp_already_at_correct_lane(self):
        """WP already at correct lane produces no events."""
        snapshot = _make_snapshot(wp_lanes={"WP01": "in_progress"})
        commit_map = {"WP01": [_make_commit_info()]}
        merged_wps: set[str] = set()

        events, details = _generate_reconciliation_events(
            "034-test-feature", snapshot, commit_map, merged_wps,
        )

        # WP01 is in_progress with commits but not merged -- no advancement needed
        assert len(events) == 0

    def test_terminal_wp_no_events(self):
        """WP in done produces no events even with new commits."""
        snapshot = _make_snapshot(wp_lanes={"WP01": "done"})
        commit_map = {"WP01": [_make_commit_info()]}
        merged_wps: set[str] = set()

        events, details = _generate_reconciliation_events(
            "034-test-feature", snapshot, commit_map, merged_wps,
        )

        assert len(events) == 0
        assert any("terminal" in d for d in details)

    def test_blocked_wp_produces_detail_no_events(self):
        """WP in blocked produces detail message but no events."""
        snapshot = _make_snapshot(wp_lanes={"WP01": "blocked"})
        commit_map = {"WP01": [_make_commit_info()]}
        merged_wps: set[str] = set()

        events, details = _generate_reconciliation_events(
            "034-test-feature", snapshot, commit_map, merged_wps,
        )

        assert len(events) == 0
        assert any("blocked" in d for d in details)

    def test_events_have_correct_actor_and_mode(self):
        """All generated events use actor=reconcile, execution_mode=direct_repo."""
        snapshot = _make_snapshot(wp_lanes={"WP01": "planned"})
        commit_map = {"WP01": [_make_commit_info()]}
        merged_wps = {"WP01"}

        events, _ = _generate_reconciliation_events(
            "034-test-feature", snapshot, commit_map, merged_wps,
        )

        for event in events:
            assert event.actor == "reconcile"
            assert event.execution_mode == "direct_repo"
            assert event.force is False


# ── Lane advancement chain tests ──────────────────────────────────


class TestLaneAdvancementChain:
    def test_single_step(self):
        chain = _lane_advancement_chain(Lane.PLANNED, Lane.CLAIMED)
        assert chain == [(Lane.PLANNED, Lane.CLAIMED)]

    def test_multi_step(self):
        chain = _lane_advancement_chain(Lane.PLANNED, Lane.FOR_REVIEW)
        assert len(chain) == 3
        assert chain[0] == (Lane.PLANNED, Lane.CLAIMED)
        assert chain[1] == (Lane.CLAIMED, Lane.IN_PROGRESS)
        assert chain[2] == (Lane.IN_PROGRESS, Lane.FOR_REVIEW)

    def test_no_advancement_needed(self):
        chain = _lane_advancement_chain(Lane.IN_PROGRESS, Lane.PLANNED)
        assert chain == []

    def test_blocked_lane(self):
        chain = _lane_advancement_chain(Lane.BLOCKED, Lane.DONE)
        assert chain == []


# ── reconcile() function tests ────────────────────────────────────


class TestReconcile:
    @patch("specify_cli.status.reconcile.scan_for_wp_commits")
    @patch("specify_cli.status.reconcile._get_merged_wps")
    @patch("specify_cli.status.reconcile.read_events")
    def test_detects_drift(self, mock_events, mock_merged, mock_scan, tmp_path):
        """Reconcile detects drift when WP is planned but has commits."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)

        mock_events.return_value = []
        mock_scan.return_value = {
            "WP01": [_make_commit_info()],
        }
        mock_merged.return_value = set()

        result = reconcile(
            feature_dir=feature_dir,
            repo_root=tmp_path,
            target_repos=[tmp_path],
            dry_run=True,
        )

        assert result.drift_detected is True
        assert len(result.suggested_events) >= 1
        assert result.target_repos_scanned == 1

    @patch("specify_cli.status.reconcile.scan_for_wp_commits")
    @patch("specify_cli.status.reconcile._get_merged_wps")
    @patch("specify_cli.status.reconcile.read_events")
    def test_no_drift(self, mock_events, mock_merged, mock_scan, tmp_path):
        """Reconcile returns no drift when no WP commits found."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)

        mock_events.return_value = []
        mock_scan.return_value = {}
        mock_merged.return_value = set()

        result = reconcile(
            feature_dir=feature_dir,
            repo_root=tmp_path,
            target_repos=[tmp_path],
            dry_run=True,
        )

        assert result.drift_detected is False
        assert len(result.suggested_events) == 0

    @patch("specify_cli.status.reconcile.scan_for_wp_commits")
    @patch("specify_cli.status.reconcile._get_merged_wps")
    @patch("specify_cli.status.reconcile.read_events")
    def test_dry_run_no_persistence(self, mock_events, mock_merged, mock_scan, tmp_path):
        """Dry-run does not write any files."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)

        mock_events.return_value = []
        mock_scan.return_value = {
            "WP01": [_make_commit_info()],
        }
        mock_merged.return_value = set()

        # Record files before
        files_before = set(feature_dir.rglob("*"))

        result = reconcile(
            feature_dir=feature_dir,
            repo_root=tmp_path,
            target_repos=[tmp_path],
            dry_run=True,
        )

        # No new files should be created
        files_after = set(feature_dir.rglob("*"))
        assert files_before == files_after

    @patch("specify_cli.status.reconcile.materialize")
    @patch("specify_cli.status.reconcile.append_event")
    @patch("specify_cli.status.reconcile.resolve_phase")
    @patch("specify_cli.status.reconcile.scan_for_wp_commits")
    @patch("specify_cli.status.reconcile._get_merged_wps")
    @patch("specify_cli.status.reconcile.read_events")
    def test_apply_emits_events(
        self, mock_events, mock_merged, mock_scan,
        mock_phase, mock_append, mock_materialize, tmp_path,
    ):
        """Apply mode emits events through append_event."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)

        mock_events.return_value = []
        mock_scan.return_value = {
            "WP01": [_make_commit_info()],
        }
        mock_merged.return_value = set()
        mock_phase.return_value = (1, "test")

        result = reconcile(
            feature_dir=feature_dir,
            repo_root=tmp_path,
            target_repos=[tmp_path],
            dry_run=False,
        )

        assert mock_append.call_count >= 1
        assert mock_materialize.call_count == 1

    @patch("specify_cli.status.reconcile.resolve_phase")
    @patch("specify_cli.status.reconcile.scan_for_wp_commits")
    @patch("specify_cli.status.reconcile._get_merged_wps")
    @patch("specify_cli.status.reconcile.read_events")
    def test_apply_rejected_at_phase_0(
        self, mock_events, mock_merged, mock_scan, mock_phase, tmp_path,
    ):
        """Apply mode raises ValueError when phase is 0."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)

        mock_events.return_value = []
        mock_scan.return_value = {
            "WP01": [_make_commit_info()],
        }
        mock_merged.return_value = set()
        mock_phase.return_value = (0, "test phase 0")

        with pytest.raises(ValueError, match="Phase 0"):
            reconcile(
                feature_dir=feature_dir,
                repo_root=tmp_path,
                target_repos=[tmp_path],
                dry_run=False,
            )

    def test_invalid_target_repo(self, tmp_path):
        """Non-existent target repo path populates errors."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)

        result = reconcile(
            feature_dir=feature_dir,
            repo_root=tmp_path,
            target_repos=[tmp_path / "does-not-exist"],
            dry_run=True,
        )

        assert len(result.errors) >= 1
        assert "does not exist" in result.errors[0]


# ── JSON serialization tests ──────────────────────────────────────


class TestReconcileResultJson:
    def test_empty_result(self):
        result = ReconcileResult()
        output = reconcile_result_to_json(result)

        assert output["drift_detected"] is False
        assert output["suggested_events"] == []
        assert output["details"] == []
        assert output["errors"] == []
        assert output["stats"]["target_repos_scanned"] == 0
        assert output["stats"]["wps_analyzed"] == 0

    def test_with_events(self):
        import ulid

        event = StatusEvent(
            event_id=str(ulid.ULID()),
            feature_slug="034-test-feature",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-01-01T00:00:00Z",
            actor="reconcile",
            force=False,
            execution_mode="direct_repo",
        )
        result = ReconcileResult(
            suggested_events=[event],
            drift_detected=True,
            details=["WP01: planned -> claimed (1 commit(s) found)"],
            target_repos_scanned=1,
            wps_analyzed=1,
        )

        output = reconcile_result_to_json(result)

        assert output["drift_detected"] is True
        assert len(output["suggested_events"]) == 1
        assert output["suggested_events"][0]["wp_id"] == "WP01"
        assert output["suggested_events"][0]["actor"] == "reconcile"
        assert output["stats"]["target_repos_scanned"] == 1

        # Verify it's JSON-serializable
        json_str = json.dumps(output)
        parsed = json.loads(json_str)
        assert parsed["drift_detected"] is True


# ── format_reconcile_report tests ─────────────────────────────────


class TestFormatReconcileReport:
    def test_no_drift_report(self, capsys):
        """No drift report prints success message."""
        result = ReconcileResult(
            target_repos_scanned=1,
            wps_analyzed=5,
        )
        format_reconcile_report(result)

        captured = capsys.readouterr()
        assert "No drift detected" in captured.out

    def test_drift_report_has_table(self, capsys):
        """Drift report includes table output."""
        import ulid

        event = StatusEvent(
            event_id=str(ulid.ULID()),
            feature_slug="034-test-feature",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-01-01T00:00:00Z",
            actor="reconcile",
            force=False,
            execution_mode="direct_repo",
            reason="1 commit(s) found",
        )
        result = ReconcileResult(
            suggested_events=[event],
            drift_detected=True,
            details=["WP01: planned -> claimed"],
            target_repos_scanned=1,
            wps_analyzed=1,
        )
        format_reconcile_report(result)

        captured = capsys.readouterr()
        assert "WP01" in captured.out
        assert "planned" in captured.out
        assert "claimed" in captured.out


# ── Helper function tests ─────────────────────────────────────────


class TestGetCurrentLane:
    def test_wp_in_snapshot(self):
        snapshot = _make_snapshot(wp_lanes={"WP01": "in_progress"})
        assert _get_current_lane(snapshot, "WP01") == Lane.IN_PROGRESS

    def test_wp_not_in_snapshot(self):
        snapshot = _make_snapshot()
        assert _get_current_lane(snapshot, "WP99") == Lane.PLANNED

    def test_invalid_lane_defaults_planned(self):
        snapshot = _make_snapshot()
        snapshot.work_packages["WP01"] = {"lane": "invalid_lane"}
        assert _get_current_lane(snapshot, "WP01") == Lane.PLANNED
