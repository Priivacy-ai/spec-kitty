"""Tests for the status doctor health check framework."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.status.doctor import (
    Category,
    DoctorResult,
    Finding,
    Severity,
    check_drift,
    check_orphan_workspaces,
    check_stale_claims,
    run_doctor,
)


def _create_events_file(feature_dir: Path, wp_states: dict[str, str], timestamp: str, feature_slug: str = "034-test") -> None:
    """Create a minimal status.events.jsonl matching the given WP states.

    Prevents doctor from flagging 'status.json exists but events file missing'.
    """
    events = []
    for wp_id, lane in wp_states.items():
        events.append(json.dumps({
            "event_id": f"01EVT{wp_id}",
            "feature_slug": feature_slug,
            "wp_id": wp_id,
            "from_lane": "planned",
            "to_lane": lane,
            "at": timestamp,
            "actor": "agent",
            "force": False,
            "execution_mode": "worktree",
        }))
    (feature_dir / "status.events.jsonl").write_text(
        "\n".join(events) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# DoctorResult and Finding dataclass tests
# ---------------------------------------------------------------------------


class TestFinding:
    """Tests for the Finding dataclass."""

    def test_finding_construction(self):
        finding = Finding(
            severity=Severity.WARNING,
            category=Category.STALE_CLAIM,
            wp_id="WP01",
            message="Test message",
            recommended_action="Test action",
        )
        assert finding.severity == Severity.WARNING
        assert finding.category == Category.STALE_CLAIM
        assert finding.wp_id == "WP01"
        assert finding.message == "Test message"
        assert finding.recommended_action == "Test action"

    def test_finding_with_none_wp_id(self):
        finding = Finding(
            severity=Severity.ERROR,
            category=Category.ORPHAN_WORKSPACE,
            wp_id=None,
            message="Orphan detected",
            recommended_action="Clean up",
        )
        assert finding.wp_id is None


class TestDoctorResult:
    """Tests for the DoctorResult dataclass."""

    def test_healthy_result(self):
        result = DoctorResult(feature_slug="034-test")
        assert result.is_healthy is True
        assert result.has_errors is False
        assert result.has_warnings is False
        assert result.findings == []

    def test_result_with_warnings(self):
        result = DoctorResult(
            feature_slug="034-test",
            findings=[
                Finding(
                    severity=Severity.WARNING,
                    category=Category.STALE_CLAIM,
                    wp_id="WP01",
                    message="stale",
                    recommended_action="fix",
                ),
            ],
        )
        assert result.is_healthy is False
        assert result.has_warnings is True
        assert result.has_errors is False

    def test_result_with_errors(self):
        result = DoctorResult(
            feature_slug="034-test",
            findings=[
                Finding(
                    severity=Severity.ERROR,
                    category=Category.MATERIALIZATION_DRIFT,
                    wp_id=None,
                    message="drift",
                    recommended_action="fix",
                ),
            ],
        )
        assert result.is_healthy is False
        assert result.has_errors is True

    def test_result_with_mixed_severity(self):
        result = DoctorResult(
            feature_slug="034-test",
            findings=[
                Finding(
                    severity=Severity.WARNING,
                    category=Category.STALE_CLAIM,
                    wp_id="WP01",
                    message="stale",
                    recommended_action="fix",
                ),
                Finding(
                    severity=Severity.ERROR,
                    category=Category.MATERIALIZATION_DRIFT,
                    wp_id=None,
                    message="drift",
                    recommended_action="fix",
                ),
            ],
        )
        assert result.has_warnings is True
        assert result.has_errors is True

    def test_findings_by_category(self):
        result = DoctorResult(
            feature_slug="034-test",
            findings=[
                Finding(
                    severity=Severity.WARNING,
                    category=Category.STALE_CLAIM,
                    wp_id="WP01",
                    message="stale claim",
                    recommended_action="fix",
                ),
                Finding(
                    severity=Severity.WARNING,
                    category=Category.ORPHAN_WORKSPACE,
                    wp_id=None,
                    message="orphan",
                    recommended_action="clean",
                ),
                Finding(
                    severity=Severity.WARNING,
                    category=Category.STALE_CLAIM,
                    wp_id="WP02",
                    message="another stale",
                    recommended_action="fix",
                ),
            ],
        )
        stale = result.findings_by_category(Category.STALE_CLAIM)
        assert len(stale) == 2
        orphan = result.findings_by_category(Category.ORPHAN_WORKSPACE)
        assert len(orphan) == 1
        drift = result.findings_by_category(Category.MATERIALIZATION_DRIFT)
        assert len(drift) == 0


# ---------------------------------------------------------------------------
# Severity and Category enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    def test_severity_values(self):
        assert Severity.WARNING == "warning"
        assert Severity.ERROR == "error"

    def test_category_values(self):
        assert Category.STALE_CLAIM == "stale_claim"
        assert Category.ORPHAN_WORKSPACE == "orphan_workspace"
        assert Category.MATERIALIZATION_DRIFT == "materialization_drift"
        assert Category.DERIVED_VIEW_DRIFT == "derived_view_drift"


# ---------------------------------------------------------------------------
# check_stale_claims tests
# ---------------------------------------------------------------------------


class TestCheckStaleClaims:
    """Tests for stale claim detection."""

    def _make_snapshot(self, wp_states: dict) -> dict:
        """Helper to create a snapshot dict."""
        return {"work_packages": wp_states}

    def test_stale_claimed_detected(self, tmp_path: Path):
        """WP in claimed for 10 days with threshold 7 -> finding."""
        ten_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=10)
        ).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "claimed",
                    "actor": "claude-agent",
                    "last_transition_at": ten_days_ago,
                }
            }
        )
        findings = check_stale_claims(
            tmp_path, snapshot, claimed_threshold_days=7
        )
        assert len(findings) == 1
        assert findings[0].category == Category.STALE_CLAIM
        assert findings[0].wp_id == "WP01"
        assert "claimed" in findings[0].message
        assert "10 days" in findings[0].message
        assert "claude-agent" in findings[0].message

    def test_stale_in_progress_detected(self, tmp_path: Path):
        """WP in in_progress for 20 days with threshold 14 -> finding."""
        twenty_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=20)
        ).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP02": {
                    "lane": "in_progress",
                    "actor": "codex-agent",
                    "last_transition_at": twenty_days_ago,
                }
            }
        )
        findings = check_stale_claims(
            tmp_path, snapshot, in_progress_threshold_days=14
        )
        assert len(findings) == 1
        assert findings[0].wp_id == "WP02"
        assert "in_progress" in findings[0].message
        assert "20 days" in findings[0].message

    def test_no_stale_within_threshold(self, tmp_path: Path):
        """WP in claimed for 3 days with threshold 7 -> no finding."""
        three_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=3)
        ).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": three_days_ago,
                }
            }
        )
        findings = check_stale_claims(
            tmp_path, snapshot, claimed_threshold_days=7
        )
        assert len(findings) == 0

    def test_done_not_stale(self, tmp_path: Path):
        """WP in done for 100 days -> no finding (terminal state)."""
        hundred_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=100)
        ).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "done",
                    "actor": "reviewer",
                    "last_transition_at": hundred_days_ago,
                }
            }
        )
        findings = check_stale_claims(tmp_path, snapshot)
        assert len(findings) == 0

    def test_canceled_not_stale(self, tmp_path: Path):
        """WP in canceled for 100 days -> no finding (terminal state)."""
        hundred_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=100)
        ).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "canceled",
                    "actor": "user",
                    "last_transition_at": hundred_days_ago,
                }
            }
        )
        findings = check_stale_claims(tmp_path, snapshot)
        assert len(findings) == 0

    def test_blocked_not_stale(self, tmp_path: Path):
        """WP in blocked for 30 days -> no finding (blocking is intentional)."""
        thirty_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=30)
        ).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "blocked",
                    "actor": "agent",
                    "last_transition_at": thirty_days_ago,
                }
            }
        )
        findings = check_stale_claims(tmp_path, snapshot)
        assert len(findings) == 0

    def test_for_review_not_stale(self, tmp_path: Path):
        """WP in for_review for 30 days -> no finding."""
        thirty_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=30)
        ).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "for_review",
                    "actor": "agent",
                    "last_transition_at": thirty_days_ago,
                }
            }
        )
        findings = check_stale_claims(tmp_path, snapshot)
        assert len(findings) == 0

    def test_custom_thresholds(self, tmp_path: Path):
        """Custom thresholds are respected."""
        two_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=2)
        ).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": two_days_ago,
                }
            }
        )
        # With default threshold (7 days), no finding
        findings_default = check_stale_claims(tmp_path, snapshot)
        assert len(findings_default) == 0

        # With custom threshold (1 day), finding
        findings_custom = check_stale_claims(
            tmp_path, snapshot, claimed_threshold_days=1
        )
        assert len(findings_custom) == 1

    def test_missing_last_transition_at(self, tmp_path: Path):
        """WP without last_transition_at is skipped, no crash."""
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                }
            }
        )
        findings = check_stale_claims(tmp_path, snapshot)
        assert len(findings) == 0

    def test_malformed_timestamp(self, tmp_path: Path):
        """WP with malformed timestamp is skipped, no crash."""
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": "not-a-date",
                }
            }
        )
        findings = check_stale_claims(tmp_path, snapshot)
        assert len(findings) == 0

    def test_empty_work_packages(self, tmp_path: Path):
        """Empty work_packages dict -> no findings."""
        snapshot = self._make_snapshot({})
        findings = check_stale_claims(tmp_path, snapshot)
        assert len(findings) == 0

    def test_multiple_stale_wps(self, tmp_path: Path):
        """Multiple stale WPs produce multiple findings."""
        old = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "claimed",
                    "actor": "a1",
                    "last_transition_at": old,
                },
                "WP02": {
                    "lane": "in_progress",
                    "actor": "a2",
                    "last_transition_at": old,
                },
                "WP03": {
                    "lane": "done",
                    "actor": "a3",
                    "last_transition_at": old,
                },
            }
        )
        findings = check_stale_claims(
            tmp_path,
            snapshot,
            claimed_threshold_days=7,
            in_progress_threshold_days=14,
        )
        assert len(findings) == 2
        wp_ids = {f.wp_id for f in findings}
        assert wp_ids == {"WP01", "WP02"}

    def test_actor_unknown_when_missing(self, tmp_path: Path):
        """Actor defaults to 'unknown' in message when not in snapshot."""
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        snapshot = self._make_snapshot(
            {
                "WP01": {
                    "lane": "claimed",
                    "last_transition_at": old,
                }
            }
        )
        findings = check_stale_claims(
            tmp_path, snapshot, claimed_threshold_days=7
        )
        assert len(findings) == 1
        assert "unknown" in findings[0].message


# ---------------------------------------------------------------------------
# check_orphan_workspaces tests
# ---------------------------------------------------------------------------


class TestCheckOrphanWorkspaces:
    """Tests for orphan workspace detection."""

    def test_orphan_worktree_detected(self, tmp_path: Path):
        """All WPs done + worktree exists -> finding."""
        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "034-test-feature-WP01").mkdir()
        (worktrees_dir / "034-test-feature-WP02").mkdir()

        snapshot = {
            "work_packages": {
                "WP01": {"lane": "done"},
                "WP02": {"lane": "done"},
            }
        }
        findings = check_orphan_workspaces(
            tmp_path, "034-test-feature", snapshot
        )
        assert len(findings) == 2
        assert all(
            f.category == Category.ORPHAN_WORKSPACE for f in findings
        )

    def test_no_orphan_active_wps(self, tmp_path: Path):
        """Worktree exists, but WP01 is still in_progress -> no finding."""
        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "034-test-feature-WP01").mkdir()

        snapshot = {
            "work_packages": {
                "WP01": {"lane": "in_progress"},
                "WP02": {"lane": "done"},
            }
        }
        findings = check_orphan_workspaces(
            tmp_path, "034-test-feature", snapshot
        )
        assert len(findings) == 0

    def test_all_done_no_worktrees(self, tmp_path: Path):
        """All WPs done + no worktrees -> no finding."""
        snapshot = {
            "work_packages": {
                "WP01": {"lane": "done"},
            }
        }
        findings = check_orphan_workspaces(
            tmp_path, "034-test-feature", snapshot
        )
        assert len(findings) == 0

    def test_no_worktrees_directory(self, tmp_path: Path):
        """No .worktrees/ directory -> no finding."""
        snapshot = {
            "work_packages": {
                "WP01": {"lane": "done"},
            }
        }
        findings = check_orphan_workspaces(
            tmp_path, "034-test-feature", snapshot
        )
        assert len(findings) == 0

    def test_mixed_terminal_states(self, tmp_path: Path):
        """Some done, some canceled (all terminal) + worktree -> finding."""
        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "034-test-feature-WP01").mkdir()

        snapshot = {
            "work_packages": {
                "WP01": {"lane": "done"},
                "WP02": {"lane": "canceled"},
            }
        }
        findings = check_orphan_workspaces(
            tmp_path, "034-test-feature", snapshot
        )
        assert len(findings) == 1

    def test_empty_work_packages(self, tmp_path: Path):
        """Empty work_packages -> no findings."""
        snapshot = {"work_packages": {}}
        findings = check_orphan_workspaces(
            tmp_path, "034-test-feature", snapshot
        )
        assert len(findings) == 0

    def test_worktree_file_not_dir_ignored(self, tmp_path: Path):
        """Worktree path that is a file (not directory) is filtered out."""
        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        # Create a file, not a directory
        (worktrees_dir / "034-test-feature-WP01").write_text("not a dir")

        snapshot = {
            "work_packages": {
                "WP01": {"lane": "done"},
            }
        }
        findings = check_orphan_workspaces(
            tmp_path, "034-test-feature", snapshot
        )
        assert len(findings) == 0

    def test_unrelated_worktrees_not_flagged(self, tmp_path: Path):
        """Worktrees for other features are not flagged."""
        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "999-other-feature-WP01").mkdir()

        snapshot = {
            "work_packages": {
                "WP01": {"lane": "done"},
            }
        }
        findings = check_orphan_workspaces(
            tmp_path, "034-test-feature", snapshot
        )
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# check_drift tests
# ---------------------------------------------------------------------------


class TestCheckDrift:
    """Tests for drift detection delegation."""

    def test_no_validation_engine_returns_empty(self, tmp_path: Path):
        """When validation engine is not available -> empty findings, no crash."""
        # The default state is that specify_cli.status.validate doesn't exist.
        # We patch the import to raise ImportError.
        with patch.dict(
            "sys.modules", {"specify_cli.status.validate": None}
        ):
            findings = check_drift(tmp_path)
        assert findings == []

    def test_import_error_graceful(self, tmp_path: Path):
        """ImportError during validation import -> empty findings."""
        # This is the natural case - WP11 not merged yet
        findings = check_drift(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# run_doctor integration tests
# ---------------------------------------------------------------------------


class TestRunDoctor:
    """Tests for the main run_doctor entry point."""

    def test_feature_dir_not_exist_raises(self, tmp_path: Path):
        """Feature directory does not exist -> FileNotFoundError."""
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError, match="does not exist"):
            run_doctor(
                feature_dir=nonexistent,
                feature_slug="034-test",
                repo_root=tmp_path,
            )

    def test_clean_feature_healthy(self, tmp_path: Path):
        """Feature with no events and no status.json -> healthy (nothing to check)."""
        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        result = run_doctor(
            feature_dir=feature_dir,
            feature_slug="034-test",
            repo_root=tmp_path,
        )
        assert result.is_healthy is True
        assert result.feature_slug == "034-test"

    def test_healthy_feature_with_active_wps(self, tmp_path: Path):
        """Active WPs within thresholds, no worktrees -> healthy."""
        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        recent = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat()
        status_data = {
            "feature_slug": "034-test",
            "materialized_at": recent,
            "event_count": 2,
            "last_event_id": "01ABC",
            "work_packages": {
                "WP01": {
                    "lane": "in_progress",
                    "actor": "agent",
                    "last_transition_at": recent,
                    "last_event_id": "01ABC",
                    "force_count": 0,
                },
            },
            "summary": {"in_progress": 1},
        }
        (feature_dir / "status.json").write_text(
            json.dumps(status_data), encoding="utf-8"
        )
        # Doctor checks for events file existence alongside status.json
        events = [
            json.dumps({"event_id": "01AAA", "feature_slug": "034-test", "wp_id": "WP01", "from_lane": "planned", "to_lane": "claimed", "at": recent, "actor": "agent", "force": False, "execution_mode": "worktree"}),
            json.dumps({"event_id": "01ABC", "feature_slug": "034-test", "wp_id": "WP01", "from_lane": "claimed", "to_lane": "in_progress", "at": recent, "actor": "agent", "force": False, "execution_mode": "worktree"}),
        ]
        (feature_dir / "status.events.jsonl").write_text(
            "\n".join(events) + "\n", encoding="utf-8"
        )

        result = run_doctor(
            feature_dir=feature_dir,
            feature_slug="034-test",
            repo_root=tmp_path,
        )
        assert result.is_healthy is True

    def test_stale_claim_detected_via_status_json(self, tmp_path: Path):
        """Stale claimed WP detected via status.json."""
        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        status_data = {
            "feature_slug": "034-test",
            "materialized_at": old,
            "event_count": 1,
            "last_event_id": "01ABC",
            "work_packages": {
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": old,
                    "last_event_id": "01ABC",
                    "force_count": 0,
                },
            },
            "summary": {"claimed": 1},
        }
        (feature_dir / "status.json").write_text(
            json.dumps(status_data), encoding="utf-8"
        )
        # Create events file so doctor doesn't flag missing events
        events = [
            json.dumps({"event_id": "01ABC", "feature_slug": "034-test", "wp_id": "WP01", "from_lane": "planned", "to_lane": "claimed", "at": old, "actor": "agent", "force": False, "execution_mode": "worktree"}),
        ]
        (feature_dir / "status.events.jsonl").write_text(
            "\n".join(events) + "\n", encoding="utf-8"
        )

        result = run_doctor(
            feature_dir=feature_dir,
            feature_slug="034-test",
            repo_root=tmp_path,
            stale_claimed_days=7,
        )
        assert result.is_healthy is False
        assert result.has_warnings is True
        assert len(result.findings) == 1
        assert result.findings[0].category == Category.STALE_CLAIM

    def test_orphan_detected_via_status_json(self, tmp_path: Path):
        """Orphan worktree detected when all WPs are terminal."""
        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "034-test-WP01").mkdir()

        status_data = {
            "feature_slug": "034-test",
            "materialized_at": "2026-01-01T00:00:00Z",
            "event_count": 1,
            "last_event_id": "01ABC",
            "work_packages": {
                "WP01": {
                    "lane": "done",
                    "actor": "reviewer",
                    "last_transition_at": "2026-01-01T00:00:00Z",
                    "last_event_id": "01ABC",
                    "force_count": 0,
                },
            },
            "summary": {"done": 1},
        }
        (feature_dir / "status.json").write_text(
            json.dumps(status_data), encoding="utf-8"
        )
        _create_events_file(feature_dir, {"WP01": "done"}, "2026-01-01T00:00:00Z")

        result = run_doctor(
            feature_dir=feature_dir,
            feature_slug="034-test",
            repo_root=tmp_path,
        )
        assert result.is_healthy is False
        assert len(result.findings_by_category(Category.ORPHAN_WORKSPACE)) == 1

    def test_stale_and_orphan_combined(self, tmp_path: Path):
        """Multiple issues detected in a single doctor run."""
        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        worktrees_dir = tmp_path / ".worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "034-other-WP01").mkdir()

        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        status_data = {
            "feature_slug": "034-test",
            "materialized_at": old,
            "event_count": 2,
            "last_event_id": "01ABC",
            "work_packages": {
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": old,
                    "last_event_id": "01ABC",
                    "force_count": 0,
                },
                "WP02": {
                    "lane": "in_progress",
                    "actor": "agent2",
                    "last_transition_at": old,
                    "last_event_id": "01DEF",
                    "force_count": 0,
                },
            },
            "summary": {"claimed": 1, "in_progress": 1},
        }
        (feature_dir / "status.json").write_text(
            json.dumps(status_data), encoding="utf-8"
        )
        _create_events_file(feature_dir, {"WP01": "claimed", "WP02": "in_progress"}, old)

        result = run_doctor(
            feature_dir=feature_dir,
            feature_slug="034-test",
            repo_root=tmp_path,
            stale_claimed_days=7,
            stale_in_progress_days=7,
        )
        # Should have stale claims for WP01 (claimed) and WP02 (in_progress)
        # No orphan because not all WPs are terminal
        stale_findings = [f for f in result.findings if f.category == Category.STALE_CLAIM]
        assert len(stale_findings) == 2

    def test_corrupted_status_json_returns_healthy(self, tmp_path: Path):
        """Corrupted status.json with no event log -> healthy (nothing to check)."""
        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "status.json").write_text(
            "not valid json", encoding="utf-8"
        )

        result = run_doctor(
            feature_dir=feature_dir,
            feature_slug="034-test",
            repo_root=tmp_path,
        )
        # snapshot is None because JSON is corrupt and no events exist
        assert result.is_healthy is True

    def test_snapshot_from_events_when_no_status_json(self, tmp_path: Path):
        """When status.json missing but events exist, snapshot is built from events."""
        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        event = {
            "event_id": "01HXYZ0123456789ABCDEFGHJK",
            "feature_slug": "034-test",
            "wp_id": "WP01",
            "from_lane": "planned",
            "to_lane": "claimed",
            "at": old,
            "actor": "agent",
            "force": False,
            "execution_mode": "worktree",
        }
        events_file = feature_dir / "status.events.jsonl"
        events_file.write_text(
            json.dumps(event) + "\n", encoding="utf-8"
        )

        result = run_doctor(
            feature_dir=feature_dir,
            feature_slug="034-test",
            repo_root=tmp_path,
            stale_claimed_days=7,
        )
        assert result.is_healthy is False
        stale_findings = [f for f in result.findings if f.category == Category.STALE_CLAIM]
        assert len(stale_findings) == 1
        assert stale_findings[0].wp_id == "WP01"


# ---------------------------------------------------------------------------
# CLI tests (unit-level, not requiring full project)
# ---------------------------------------------------------------------------


class TestDoctorCLI:
    """Tests for the CLI doctor command."""

    def test_doctor_cli_json_output(self, tmp_path: Path):
        """CLI doctor --json produces parseable JSON."""
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.status import app

        runner = CliRunner()

        # Mock the resolution chain to use our temp directory
        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        recent = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat()
        status_data = {
            "feature_slug": "034-test",
            "materialized_at": recent,
            "event_count": 1,
            "last_event_id": "01EVTWP01",
            "work_packages": {
                "WP01": {
                    "lane": "in_progress",
                    "actor": "agent",
                    "last_transition_at": recent,
                    "last_event_id": "01EVTWP01",
                    "force_count": 0,
                },
            },
            "summary": {"in_progress": 1},
        }
        (feature_dir / "status.json").write_text(
            json.dumps(status_data), encoding="utf-8"
        )
        _create_events_file(feature_dir, {"WP01": "in_progress"}, recent)

        with patch(
            "specify_cli.cli.commands.agent.status._resolve_feature_dir",
            return_value=(feature_dir, "034-test", tmp_path),
        ):
            result = runner.invoke(app, ["doctor", "--json"])

        # Exit code 0 for healthy
        assert result.exit_code == 0
        # Output should contain valid JSON
        output = result.output.strip()
        parsed = json.loads(output)
        assert parsed["healthy"] is True
        assert parsed["feature_slug"] == "034-test"
        assert parsed["findings"] == []

    def test_doctor_cli_healthy_exit_0(self, tmp_path: Path):
        """Healthy feature -> exit code 0."""
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.status import app

        runner = CliRunner()

        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        with patch(
            "specify_cli.cli.commands.agent.status._resolve_feature_dir",
            return_value=(feature_dir, "034-test", tmp_path),
        ):
            result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "Healthy" in result.output

    def test_doctor_cli_issues_exit_1(self, tmp_path: Path):
        """Stale claim -> exit code 1."""
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.status import app

        runner = CliRunner()

        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        status_data = {
            "feature_slug": "034-test",
            "materialized_at": old,
            "event_count": 1,
            "last_event_id": "01EVTWP01",
            "work_packages": {
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": old,
                    "last_event_id": "01EVTWP01",
                    "force_count": 0,
                },
            },
            "summary": {"claimed": 1},
        }
        (feature_dir / "status.json").write_text(
            json.dumps(status_data), encoding="utf-8"
        )
        _create_events_file(feature_dir, {"WP01": "claimed"}, old)

        with patch(
            "specify_cli.cli.commands.agent.status._resolve_feature_dir",
            return_value=(feature_dir, "034-test", tmp_path),
        ):
            result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 1
        assert "Issues found" in result.output

    def test_doctor_cli_json_with_findings(self, tmp_path: Path):
        """CLI --json with findings produces structured output."""
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.status import app

        runner = CliRunner()

        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        status_data = {
            "feature_slug": "034-test",
            "materialized_at": old,
            "event_count": 1,
            "last_event_id": "01EVTWP01",
            "work_packages": {
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": old,
                    "last_event_id": "01EVTWP01",
                    "force_count": 0,
                },
            },
            "summary": {"claimed": 1},
        }
        (feature_dir / "status.json").write_text(
            json.dumps(status_data), encoding="utf-8"
        )
        _create_events_file(feature_dir, {"WP01": "claimed"}, old)

        with patch(
            "specify_cli.cli.commands.agent.status._resolve_feature_dir",
            return_value=(feature_dir, "034-test", tmp_path),
        ):
            result = runner.invoke(app, ["doctor", "--json"])

        assert result.exit_code == 1
        output = result.output.strip()
        parsed = json.loads(output)
        assert parsed["healthy"] is False
        assert len(parsed["findings"]) == 1
        finding = parsed["findings"][0]
        assert finding["severity"] == "warning"
        assert finding["category"] == "stale_claim"
        assert finding["wp_id"] == "WP01"
        assert "claimed" in finding["message"]
        assert finding["recommended_action"]  # Non-empty

    def test_doctor_cli_feature_not_found(self, tmp_path: Path):
        """Feature directory not found -> exit code 1."""
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.status import app

        runner = CliRunner()

        nonexistent = tmp_path / "kitty-specs" / "999-missing"

        with patch(
            "specify_cli.cli.commands.agent.status._resolve_feature_dir",
            return_value=(nonexistent, "999-missing", tmp_path),
        ):
            result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_doctor_cli_custom_thresholds(self, tmp_path: Path):
        """Custom threshold flags are passed through."""
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.status import app

        runner = CliRunner()

        feature_dir = tmp_path / "kitty-specs" / "034-test"
        feature_dir.mkdir(parents=True)

        # 2 days ago - below default 7-day threshold but above custom 1-day
        two_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=2)
        ).isoformat()
        status_data = {
            "feature_slug": "034-test",
            "materialized_at": two_days_ago,
            "event_count": 1,
            "last_event_id": "01EVTWP01",
            "work_packages": {
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": two_days_ago,
                    "last_event_id": "01EVTWP01",
                    "force_count": 0,
                },
            },
            "summary": {"claimed": 1},
        }
        (feature_dir / "status.json").write_text(
            json.dumps(status_data), encoding="utf-8"
        )
        _create_events_file(feature_dir, {"WP01": "claimed"}, two_days_ago)

        # Default threshold: healthy
        with patch(
            "specify_cli.cli.commands.agent.status._resolve_feature_dir",
            return_value=(feature_dir, "034-test", tmp_path),
        ):
            result_default = runner.invoke(app, ["doctor", "--json"])
        assert result_default.exit_code == 0

        # Custom threshold: finding
        with patch(
            "specify_cli.cli.commands.agent.status._resolve_feature_dir",
            return_value=(feature_dir, "034-test", tmp_path),
        ):
            result_custom = runner.invoke(
                app,
                ["doctor", "--json", "--stale-claimed-days", "1"],
            )
        assert result_custom.exit_code == 1
