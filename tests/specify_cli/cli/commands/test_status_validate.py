"""CLI integration tests for `spec-kitty agent status validate`.

Tests the command via typer's CliRunner, verifying exit codes,
human-readable output, and JSON output.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.status import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    event_id: str = "01HXYZ0123456789ABCDEFGHJK",
    feature_slug: str = "034-test-feature",
    wp_id: str = "WP01",
    from_lane: str = "planned",
    to_lane: str = "claimed",
    at: str = "2026-02-08T12:00:00Z",
    actor: str = "claude-opus",
    force: bool = False,
    execution_mode: str = "worktree",
    reason: str | None = None,
    review_ref: str | None = None,
    evidence: dict | None = None,
) -> dict:
    event: dict = {
        "event_id": event_id,
        "feature_slug": feature_slug,
        "wp_id": wp_id,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "at": at,
        "actor": actor,
        "force": force,
        "execution_mode": execution_mode,
    }
    if reason is not None:
        event["reason"] = reason
    if review_ref is not None:
        event["review_ref"] = review_ref
    if evidence is not None:
        event["evidence"] = evidence
    return event


def _setup_feature(
    tmp_path: Path,
    feature_slug: str = "034-test-feature",
    events: list[dict] | None = None,
    materialize: bool = True,
    wp_files: dict[str, str] | None = None,
) -> Path:
    """Set up a feature directory with optional events and WP files.

    Returns the feature_dir path.
    """
    feature_dir = tmp_path / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True)

    # Write events file
    if events:
        lines = [json.dumps(e, sort_keys=True) for e in events]
        (feature_dir / "status.events.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

        # Materialize snapshot
        if materialize:
            from specify_cli.status.reducer import materialize as do_materialize
            do_materialize(feature_dir)

    # Write WP files
    if wp_files:
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        for wp_id, lane in wp_files.items():
            content = f"""---
work_package_id: {wp_id}
title: Test {wp_id}
lane: {lane}
---

# {wp_id}
"""
            (tasks_dir / f"{wp_id}-test.md").write_text(content, encoding="utf-8")

    return feature_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidateCommand:
    """Tests for the validate CLI command."""

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_clean_feature(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """Valid log, matching snapshot -> exit 0, no errors."""
        feature_slug = "034-test-feature"
        events = [
            _make_event(
                from_lane="planned",
                to_lane="claimed",
                at="2026-02-08T12:00:00Z",
            ),
        ]
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=events,
            wp_files={"WP01": "claimed"},
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (1, "built-in default")

        result = runner.invoke(app, ["validate", "--feature", feature_slug])
        assert result.exit_code == 0
        assert "PASS" in result.output

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_illegal_transition(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """Log with planned -> done (illegal) -> exit 1, error reported."""
        feature_slug = "034-test-feature"
        events = [
            _make_event(
                from_lane="planned",
                to_lane="done",
                at="2026-02-08T12:00:00Z",
            ),
        ]
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=events,
            wp_files={"WP01": "done"},
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (1, "built-in default")

        result = runner.invoke(app, ["validate", "--feature", feature_slug])
        assert result.exit_code == 1
        assert "FAIL" in result.output

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_missing_evidence(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """Done event without evidence -> exit 1."""
        feature_slug = "034-test-feature"
        events = [
            _make_event(
                from_lane="for_review",
                to_lane="done",
                at="2026-02-08T12:00:00Z",
            ),
        ]
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=events,
            wp_files={"WP01": "done"},
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (1, "built-in default")

        result = runner.invoke(app, ["validate", "--feature", feature_slug])
        assert result.exit_code == 1

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_materialization_drift_phase1_warning(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """Phase 1: materialization drift is a warning, not an error."""
        feature_slug = "034-test-feature"
        events = [
            _make_event(
                from_lane="planned",
                to_lane="claimed",
                at="2026-02-08T12:00:00Z",
            ),
        ]
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=events,
            wp_files={"WP01": "claimed"},
        )

        # Tamper with the snapshot
        snapshot_path = feature_dir / "status.json"
        data = json.loads(snapshot_path.read_text())
        data["event_count"] = 999
        snapshot_path.write_text(
            json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (1, "built-in default")

        result = runner.invoke(app, ["validate", "--feature", feature_slug])
        # Phase 1: drift is warning, so should still pass
        assert result.exit_code == 0
        assert "Warning" in result.output or "PASS" in result.output

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_materialization_drift_phase2_error(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """Phase 2: materialization drift is an error."""
        feature_slug = "034-test-feature"
        events = [
            _make_event(
                from_lane="planned",
                to_lane="claimed",
                at="2026-02-08T12:00:00Z",
            ),
        ]
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=events,
            wp_files={"WP01": "claimed"},
        )

        # Tamper with the snapshot
        snapshot_path = feature_dir / "status.json"
        data = json.loads(snapshot_path.read_text())
        data["event_count"] = 999
        snapshot_path.write_text(
            json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (2, "built-in default")

        result = runner.invoke(app, ["validate", "--feature", feature_slug])
        # Phase 2: drift is error, should fail
        assert result.exit_code == 1
        assert "FAIL" in result.output

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_frontmatter_drift(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """Frontmatter lane manually changed: drift reported."""
        feature_slug = "034-test-feature"
        events = [
            _make_event(
                from_lane="planned",
                to_lane="claimed",
                at="2026-02-08T12:00:00Z",
            ),
        ]
        # WP file says "done" but canonical state is "claimed"
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=events,
            wp_files={"WP01": "done"},
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (2, "built-in default")

        result = runner.invoke(app, ["validate", "--feature", feature_slug])
        assert result.exit_code == 1

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_json_output(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """--json produces valid JSON with all expected fields."""
        feature_slug = "034-test-feature"
        events = [
            _make_event(
                from_lane="planned",
                to_lane="claimed",
                at="2026-02-08T12:00:00Z",
            ),
        ]
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=events,
            wp_files={"WP01": "claimed"},
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (1, "built-in default")

        result = runner.invoke(
            app, ["validate", "--feature", feature_slug, "--json"]
        )
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["feature_slug"] == feature_slug
        assert data["phase"] == 1
        assert "phase_source" in data
        assert data["passed"] is True
        assert isinstance(data["errors"], list)
        assert isinstance(data["warnings"], list)
        assert data["error_count"] == 0
        assert data["warning_count"] == 0

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_json_output_with_errors(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """--json with errors produces JSON with error details."""
        feature_slug = "034-test-feature"
        events = [
            _make_event(
                from_lane="planned",
                to_lane="done",  # illegal
                at="2026-02-08T12:00:00Z",
            ),
        ]
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=events,
            wp_files={"WP01": "done"},
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (1, "built-in default")

        result = runner.invoke(
            app, ["validate", "--feature", feature_slug, "--json"]
        )
        assert result.exit_code == 1

        data = json.loads(result.output)
        assert data["passed"] is False
        assert data["error_count"] > 0
        assert len(data["errors"]) > 0

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_no_events(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """No event log: no errors, exit 0."""
        feature_slug = "034-test-feature"
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=None,
            materialize=False,
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (1, "built-in default")

        result = runner.invoke(app, ["validate", "--feature", feature_slug])
        assert result.exit_code == 0

    @patch("specify_cli.cli.commands.agent.status.locate_project_root")
    @patch("specify_cli.cli.commands.agent.status.get_main_repo_root")
    @patch("specify_cli.cli.commands.agent.status.detect_feature_slug")
    @patch("specify_cli.status.phase.resolve_phase")
    def test_validate_no_events_json(
        self,
        mock_phase,
        mock_detect,
        mock_main_root,
        mock_locate,
        tmp_path,
    ):
        """No events + JSON output -> valid JSON, passed=true."""
        feature_slug = "034-test-feature"
        feature_dir = _setup_feature(
            tmp_path,
            feature_slug,
            events=None,
            materialize=False,
        )

        mock_locate.return_value = tmp_path
        mock_main_root.return_value = tmp_path
        mock_detect.return_value = feature_slug
        mock_phase.return_value = (1, "built-in default")

        result = runner.invoke(
            app, ["validate", "--feature", feature_slug, "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["passed"] is True
        assert data["error_count"] == 0
