"""Integration tests for canonical acceptance — status.events.jsonl is sole authority.

Verifies that:
- Acceptance reads canonical state (materialize()) instead of Activity Log
- Missing event log gives explicit error, not silent fallback
- record_acceptance() produces identical metadata structure for all paths
- Falsified Activity Log is ignored when canonical state disagrees
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from specify_cli.acceptance import collect_feature_summary
from specify_cli.feature_metadata import load_meta, record_acceptance
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_meta() -> dict[str, Any]:
    """Return a minimal valid meta dict with all required fields."""
    return {
        "feature_number": "099",
        "slug": "099-test-feature",
        "feature_slug": "099-test-feature",
        "friendly_name": "Test Feature",
        "mission": "software-dev",
        "target_branch": "main",
        "created_at": "2026-03-18T00:00:00+00:00",
    }


def _make_event(
    feature_slug: str,
    wp_id: str,
    from_lane: str,
    to_lane: str,
    *,
    event_id: str = "01TESTABCDEFGHIJKLMNOPQRST",
    at: str = "2026-03-18T12:00:00+00:00",
    actor: str = "test-agent",
) -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        feature_slug=feature_slug,
        wp_id=wp_id,
        from_lane=Lane(from_lane),
        to_lane=Lane(to_lane),
        at=at,
        actor=actor,
        force=False,
        execution_mode="worktree",
    )


def _write_wp_file(
    tasks_dir: Path,
    wp_id: str,
    *,
    lane: str = "done",
    title: str = "Test WP",
    agent: str = "test-agent",
    assignee: str = "test-agent",
    shell_pid: str = "12345",
    include_activity_log: bool = True,
    activity_log_lane: str | None = None,
) -> Path:
    """Create a WP markdown file with frontmatter in flat tasks directory."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    wp_path = tasks_dir / f"{wp_id}.md"

    fm = (
        f"---\n"
        f'work_package_id: "{wp_id}"\n'
        f'title: "{title}"\n'
        f'lane: "{lane}"\n'
        f'agent: "{agent}"\n'
        f'assignee: "{assignee}"\n'
        f'shell_pid: "{shell_pid}"\n'
        f"---\n"
    )

    body = f"\n# {title}\n\nSome description.\n"
    if include_activity_log:
        log_lane = activity_log_lane or lane
        body += (
            f"\n## Activity Log\n\n"
            f"- 2026-03-18T12:00:00Z -- {agent} -- lane={log_lane} -- Started work\n"
        )

    wp_path.write_text(fm + body, encoding="utf-8")
    return wp_path


def _setup_feature(
    tmp_path: Path,
    feature_slug: str = "099-test-feature",
    wp_ids: list[str] | None = None,
    *,
    all_done: bool = True,
    include_events: bool = True,
    include_activity_log: bool = True,
    activity_log_lane: str | None = None,
    wp_lanes: dict[str, str] | None = None,
) -> Path:
    """Scaffold a complete feature directory for testing.

    Returns the feature directory path.
    """
    if wp_ids is None:
        wp_ids = ["WP01", "WP02"]

    feature_dir = tmp_path / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True)
    tasks_dir = feature_dir / "tasks"

    # Write meta.json
    meta = _minimal_meta()
    meta["feature_number"] = feature_slug.split("-")[0]
    meta["slug"] = feature_slug
    meta["feature_slug"] = feature_slug
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Write required artifacts
    for artifact in ["spec.md", "plan.md", "tasks.md"]:
        (feature_dir / artifact).write_text(
            f"# {artifact}\n\n- [x] All tasks done\n", encoding="utf-8"
        )

    # Determine per-WP lanes
    if wp_lanes is None:
        default_lane = "done" if all_done else "in_progress"
        wp_lanes = dict.fromkeys(wp_ids, default_lane)

    # Write WP files
    for wp_id in wp_ids:
        lane = wp_lanes.get(wp_id, "done")
        _write_wp_file(
            tasks_dir,
            wp_id,
            lane=lane,
            include_activity_log=include_activity_log,
            activity_log_lane=activity_log_lane,
        )

    # Write canonical events
    if include_events:
        counter = 0
        for wp_id in wp_ids:
            target_lane = wp_lanes.get(wp_id, "done")
            # Build transition chain: planned -> claimed -> in_progress -> done
            transitions = [
                ("planned", "claimed"),
                ("claimed", "in_progress"),
                ("in_progress", "for_review"),
                ("for_review", "approved"),
            ]
            if target_lane == "done":
                transitions.append(("approved", "done"))

            for from_l, to_l in transitions:
                counter += 1
                event = _make_event(
                    feature_slug,
                    wp_id,
                    from_l,
                    to_l,
                    event_id=f"01TEST{wp_id}{counter:020d}",
                    at=f"2026-03-18T{12 + counter:02d}:00:00+00:00",
                )
                append_event(feature_dir, event)
                # Stop if we've reached the target lane
                if to_l == target_lane:
                    break

    return feature_dir


# ---------------------------------------------------------------------------
# T013 Test Cases
# ---------------------------------------------------------------------------


class TestCanonicalStateAuthority:
    """Acceptance reads canonical status.events.jsonl, not Activity Log."""

    def test_acceptance_succeeds_with_deleted_activity_log(self, tmp_path: Path) -> None:
        """Activity Log deleted from all WP files -- acceptance still works.

        This is the primary success gate from the WP prompt: canonical state
        is the sole authority for determining WP lane status.
        """
        _setup_feature(
            tmp_path,
            all_done=True,
            include_events=True,
            include_activity_log=False,  # No Activity Log in WP files
        )

        # Mock git calls to avoid needing a real repo
        with patch("specify_cli.acceptance.run_git") as mock_git, \
             patch("specify_cli.acceptance.git_status_lines", return_value=[]):
            mock_git.return_value.stdout = "main\n"
            summary = collect_feature_summary(
                tmp_path,
                "099-test-feature",
                strict_metadata=False,
            )

        # Activity issues should be empty -- canonical state says all done
        assert summary.activity_issues == [], (
            f"Expected no activity issues, got: {summary.activity_issues}"
        )
        assert summary.all_done

    def test_all_done_uses_canonical_lane_not_frontmatter(self, tmp_path: Path) -> None:
        """Canonical state is 'done' for all WPs but frontmatter lane is 'for_review'.

        This is the exact regression from the Codex review: the lanes dict
        bucketing used wp.current_lane (frontmatter) so all_done returned False
        even though canonical state said done. After the fix, canonical lane
        drives the lanes dict, so all_done returns True.
        """
        # Frontmatter says for_review, but canonical events say done
        _setup_feature(
            tmp_path,
            wp_ids=["WP01", "WP02"],
            include_events=True,
            include_activity_log=True,
            wp_lanes={
                "WP01": "done",
                "WP02": "done",
            },
        )

        # Overwrite WP files to have frontmatter lane=for_review
        tasks_dir = tmp_path / "kitty-specs" / "099-test-feature" / "tasks"
        for wp_id in ["WP01", "WP02"]:
            _write_wp_file(
                tasks_dir,
                wp_id,
                lane="for_review",  # Frontmatter says for_review
                include_activity_log=True,
                activity_log_lane="for_review",
            )

        with patch("specify_cli.acceptance.run_git") as mock_git, \
             patch("specify_cli.acceptance.git_status_lines", return_value=[]):
            mock_git.return_value.stdout = "main\n"
            summary = collect_feature_summary(
                tmp_path,
                "099-test-feature",
                strict_metadata=False,
            )

        # Canonical state says done => lanes["done"] should have both WPs
        assert summary.all_done, (
            f"all_done should be True when canonical state is done. "
            f"lanes={summary.lanes}, activity_issues={summary.activity_issues}"
        )
        assert "WP01" in summary.lanes.get("done", [])
        assert "WP02" in summary.lanes.get("done", [])
        assert summary.lanes.get("for_review", []) == [], (
            f"for_review lane should be empty, got: {summary.lanes.get('for_review')}"
        )
        assert summary.activity_issues == [], (
            f"Expected no activity issues, got: {summary.activity_issues}"
        )

    def test_acceptance_fails_despite_falsified_activity_log(self, tmp_path: Path) -> None:
        """Activity Log says 'done' but canonical state says 'for_review'.

        Canonical state must win -- falsified Activity Log is ignored.
        """
        _setup_feature(
            tmp_path,
            wp_ids=["WP01", "WP02"],
            include_events=True,
            include_activity_log=True,
            activity_log_lane="done",  # Activity Log claims done
            wp_lanes={
                "WP01": "done",
                "WP02": "for_review",  # But canonical state says for_review
            },
        )

        with patch("specify_cli.acceptance.run_git") as mock_git, \
             patch("specify_cli.acceptance.git_status_lines", return_value=[]):
            mock_git.return_value.stdout = "main\n"
            summary = collect_feature_summary(
                tmp_path,
                "099-test-feature",
                strict_metadata=False,
            )

        # Should have an activity issue for WP02
        assert any(
            "WP02" in issue and "for_review" in issue
            for issue in summary.activity_issues
        ), f"Expected canonical lane mismatch for WP02, got: {summary.activity_issues}"

    def test_acceptance_fails_with_missing_event_log(self, tmp_path: Path) -> None:
        """No status.events.jsonl -- explicit error, not Activity Log fallback."""
        _setup_feature(
            tmp_path,
            all_done=True,
            include_events=False,  # No event log
            include_activity_log=True,
        )

        with patch("specify_cli.acceptance.run_git") as mock_git, \
             patch("specify_cli.acceptance.git_status_lines", return_value=[]):
            mock_git.return_value.stdout = "main\n"
            summary = collect_feature_summary(
                tmp_path,
                "099-test-feature",
                strict_metadata=False,
            )

        # Should have explicit error about missing canonical state
        assert any(
            "status.events.jsonl" in issue
            for issue in summary.activity_issues
        ), f"Expected missing event log error, got: {summary.activity_issues}"
        assert any(
            "canonical state" in issue.lower() or "No canonical state" in issue
            for issue in summary.activity_issues
        ), f"Expected actionable error message, got: {summary.activity_issues}"

    def test_wp_with_no_events_reports_no_canonical_state(self, tmp_path: Path) -> None:
        """WP exists in task files but has no events in the log."""
        feature_dir = _setup_feature(
            tmp_path,
            wp_ids=["WP01", "WP02"],
            include_events=False,
            include_activity_log=False,
        )

        # Write events only for WP01
        for i, (from_l, to_l) in enumerate([
            ("planned", "claimed"),
            ("claimed", "in_progress"),
            ("in_progress", "for_review"),
            ("for_review", "approved"),
            ("approved", "done"),
        ], start=1):
            event = _make_event(
                "099-test-feature", "WP01", from_l, to_l,
                event_id=f"01TESTWP01{i:020d}",
                at=f"2026-03-18T{12 + i:02d}:00:00+00:00",
            )
            append_event(feature_dir, event)

        with patch("specify_cli.acceptance.run_git") as mock_git, \
             patch("specify_cli.acceptance.git_status_lines", return_value=[]):
            mock_git.return_value.stdout = "main\n"
            summary = collect_feature_summary(
                tmp_path,
                "099-test-feature",
                strict_metadata=False,
            )

        # WP02 should be flagged as missing canonical state
        assert any(
            "WP02" in issue and "no canonical state" in issue
            for issue in summary.activity_issues
        ), f"Expected WP02 missing state error, got: {summary.activity_issues}"

        # WP01 should be fine (canonical state says done)
        assert not any(
            "WP01" in issue
            for issue in summary.activity_issues
        ), f"WP01 should not have issues, got: {summary.activity_issues}"

    def test_acceptance_fails_with_empty_event_log(self, tmp_path: Path) -> None:
        """Empty status.events.jsonl triggers feature-level error.

        If the file exists but is empty, materialize() returns a snapshot with
        no work_packages. This must produce the same feature-level error as a
        missing file, not fall through to per-WP messages.
        """
        feature_dir = _setup_feature(
            tmp_path,
            wp_ids=["WP01", "WP02"],
            include_events=False,  # Don't auto-create events
            include_activity_log=True,
        )

        # Create an empty status.events.jsonl (file exists but no events)
        events_file = feature_dir / "status.events.jsonl"
        events_file.write_text("", encoding="utf-8")

        with patch("specify_cli.acceptance.run_git") as mock_git, \
             patch("specify_cli.acceptance.git_status_lines", return_value=[]):
            mock_git.return_value.stdout = "main\n"
            summary = collect_feature_summary(
                tmp_path,
                "099-test-feature",
                strict_metadata=False,
            )

        # Should have the feature-level error, not per-WP messages
        assert any(
            "No canonical state found" in issue
            for issue in summary.activity_issues
        ), f"Expected feature-level 'No canonical state found' error, got: {summary.activity_issues}"

        # Verify it's the feature-level message (mentions feature name), not per-WP
        feature_level_errors = [
            issue for issue in summary.activity_issues
            if "No canonical state found for feature" in issue
        ]
        assert len(feature_level_errors) >= 1, (
            f"Expected at least one feature-level error, got: {summary.activity_issues}"
        )


class TestOrchestratorParity:
    """Standard and orchestrator acceptance produce identical metadata structure."""

    def test_orchestrator_and_standard_acceptance_identical_structure(self, tmp_path: Path) -> None:
        """Both acceptance paths produce the same meta.json fields."""
        # Setup two identical features
        feature_std = _setup_feature(
            tmp_path / "standard",
            feature_slug="099-test-standard",
            all_done=True,
        )
        feature_orch = _setup_feature(
            tmp_path / "orchestrator",
            feature_slug="099-test-orchestrator",
            all_done=True,
        )

        # Standard acceptance via record_acceptance
        record_acceptance(
            feature_std,
            accepted_by="test-user",
            mode="local",
            from_commit="abc123",
            accept_commit="def456",
        )

        # Orchestrator acceptance via record_acceptance
        record_acceptance(
            feature_orch,
            accepted_by="test-user",
            mode="orchestrator",
        )

        meta_std = load_meta(feature_std)
        meta_orch = load_meta(feature_orch)

        assert meta_std is not None
        assert meta_orch is not None

        # Both should have the same structural fields
        acceptance_fields = {
            "accepted_at", "accepted_by", "acceptance_mode", "acceptance_history",
        }
        for field in acceptance_fields:
            assert field in meta_std, f"Standard meta missing field: {field}"
            assert field in meta_orch, f"Orchestrator meta missing field: {field}"

        # acceptance_history should be a list with at least one entry
        assert isinstance(meta_std["acceptance_history"], list)
        assert isinstance(meta_orch["acceptance_history"], list)
        assert len(meta_std["acceptance_history"]) >= 1
        assert len(meta_orch["acceptance_history"]) >= 1

        # Both history entries should have common fields
        std_entry = meta_std["acceptance_history"][-1]
        orch_entry = meta_orch["acceptance_history"][-1]
        common_fields = {"accepted_at", "accepted_by", "acceptance_mode"}
        for field in common_fields:
            assert field in std_entry, f"Standard history missing field: {field}"
            assert field in orch_entry, f"Orchestrator history missing field: {field}"

    def test_orchestrator_acceptance_includes_acceptance_mode(self, tmp_path: Path) -> None:
        """Orchestrator path now sets acceptance_mode (previously missing)."""
        feature_dir = _setup_feature(tmp_path, all_done=True)

        record_acceptance(
            feature_dir,
            accepted_by="orchestrator-bot",
            mode="orchestrator",
        )

        meta = load_meta(feature_dir)
        assert meta is not None
        assert meta["acceptance_mode"] == "orchestrator"

    def test_record_acceptance_produces_trailing_newline(self, tmp_path: Path) -> None:
        """record_acceptance() writes files with trailing newline (fixes orchestrator bug)."""
        feature_dir = _setup_feature(tmp_path, all_done=True)

        record_acceptance(
            feature_dir,
            accepted_by="test-user",
            mode="orchestrator",
        )

        meta_path = feature_dir / "meta.json"
        raw = meta_path.read_text(encoding="utf-8")
        assert raw.endswith("\n"), "meta.json should end with a trailing newline"
        assert not raw.endswith("\n\n"), "meta.json should not have double trailing newlines"


class TestAcceptanceMetadataWrite:
    """record_acceptance() correctly writes and accumulates metadata."""

    def test_record_acceptance_sets_all_fields(self, tmp_path: Path) -> None:
        """Standard acceptance with all parameters."""
        feature_dir = _setup_feature(tmp_path, all_done=True)

        record_acceptance(
            feature_dir,
            accepted_by="reviewer",
            mode="pr",
            from_commit="abc123",
            accept_commit="def456",
        )

        meta = load_meta(feature_dir)
        assert meta is not None
        assert meta["accepted_by"] == "reviewer"
        assert meta["acceptance_mode"] == "pr"
        assert meta["accepted_from_commit"] == "abc123"
        assert meta["accept_commit"] == "def456"
        assert "accepted_at" in meta
        assert len(meta["acceptance_history"]) == 1

    def test_record_acceptance_without_commits(self, tmp_path: Path) -> None:
        """Orchestrator mode may not have commit info."""
        feature_dir = _setup_feature(tmp_path, all_done=True)

        record_acceptance(
            feature_dir,
            accepted_by="bot",
            mode="orchestrator",
        )

        meta = load_meta(feature_dir)
        assert meta is not None
        assert "accepted_from_commit" not in meta
        assert "accept_commit" not in meta

    def test_record_acceptance_clears_stale_commit_fields(self, tmp_path: Path) -> None:
        """Re-acceptance clears stale commit fields from prior run."""
        feature_dir = _setup_feature(tmp_path, all_done=True)

        # First acceptance with commits
        record_acceptance(
            feature_dir,
            accepted_by="user1",
            mode="local",
            from_commit="abc",
            accept_commit="def",
        )

        # Second acceptance without commits (orchestrator)
        record_acceptance(
            feature_dir,
            accepted_by="user2",
            mode="orchestrator",
        )

        meta = load_meta(feature_dir)
        assert meta is not None
        assert meta["accepted_by"] == "user2"
        assert meta["acceptance_mode"] == "orchestrator"
        # Stale commit fields should be cleared
        assert "accepted_from_commit" not in meta
        assert "accept_commit" not in meta
        # Both entries in history
        assert len(meta["acceptance_history"]) == 2
