"""Integration tests for CLI status commands (emit & materialize)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.status import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json(output: str) -> dict:
    """Extract the first JSON object from possibly multi-line output.

    The SaaS fan-out and sync modules can print extra diagnostic lines
    to stdout. This helper finds the first line that parses as JSON.
    """
    for line in output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No valid JSON found in output:\n{output}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    """Create a minimal feature directory with kitty-specs structure."""
    fd = tmp_path / "kitty-specs" / "034-test-feature"
    fd.mkdir(parents=True)
    # Create a tasks directory with at least one WP file (for realism)
    tasks_dir = fd / "tasks"
    tasks_dir.mkdir()
    wp_file = tasks_dir / "WP01-test-task.md"
    wp_file.write_text(
        "---\nwork_package_id: WP01\ntitle: Test Task\nlane: planned\n---\n\n# WP01\n",
        encoding="utf-8",
    )
    return fd


@pytest.fixture
def feature_dir_with_events(feature_dir: Path) -> Path:
    """Feature directory pre-populated with a valid events file."""
    event = {
        "event_id": "01HXYZ0000000000000000TEST",
        "feature_slug": "034-test-feature",
        "wp_id": "WP01",
        "from_lane": "planned",
        "to_lane": "claimed",
        "at": "2026-02-08T12:00:00+00:00",
        "actor": "test-agent",
        "force": False,
        "execution_mode": "worktree",
        "reason": None,
        "review_ref": None,
        "evidence": None,
    }
    events_path = feature_dir / "status.events.jsonl"
    events_path.write_text(
        json.dumps(event, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return feature_dir


def _patch_detection(tmp_path: Path, feature_slug: str = "034-test-feature"):
    """Return a dictionary of patches for feature detection and repo root."""
    return {
        "locate_project_root": patch(
            "specify_cli.cli.commands.agent.status.locate_project_root",
            return_value=tmp_path,
        ),
        "get_main_repo_root": patch(
            "specify_cli.cli.commands.agent.status.get_main_repo_root",
            return_value=tmp_path,
        ),
        "detect_feature_slug": patch(
            "specify_cli.cli.commands.agent.status.detect_feature_slug",
            return_value=feature_slug,
        ),
        "saas_fan_out": patch(
            "specify_cli.status.emit._saas_fan_out",
        ),
    }


# ---------------------------------------------------------------------------
# Emit tests
# ---------------------------------------------------------------------------


class TestEmitCommand:
    """Tests for ``spec-kitty agent status emit``."""

    def test_emit_valid_transition(self, tmp_path: Path, feature_dir: Path):
        """A valid planned -> claimed transition should succeed."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
            patches["saas_fan_out"],
        ):
            result = runner.invoke(
                app,
                [
                    "emit",
                    "WP01",
                    "--to",
                    "claimed",
                    "--actor",
                    "test-agent",
                    "--feature",
                    "034-test-feature",
                ],
            )

        assert result.exit_code == 0, f"stdout: {result.output}"
        assert "WP01" in result.output
        assert "claimed" in result.output

        # Verify events file was created
        events_path = feature_dir / "status.events.jsonl"
        assert events_path.exists()

    def test_emit_invalid_transition_exits_1(self, tmp_path: Path, feature_dir: Path):
        """An illegal transition (planned -> done without evidence) should fail."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
            patches["saas_fan_out"],
        ):
            result = runner.invoke(
                app,
                [
                    "emit",
                    "WP01",
                    "--to",
                    "done",
                    "--actor",
                    "test-agent",
                    "--feature",
                    "034-test-feature",
                ],
            )

        assert result.exit_code == 1, f"stdout: {result.output}"
        # Should have some error output about invalid transition
        assert "Error" in result.output or "error" in result.output

    def test_emit_json_output(self, tmp_path: Path, feature_dir: Path):
        """--json flag should produce valid parseable JSON."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
            patches["saas_fan_out"],
        ):
            result = runner.invoke(
                app,
                [
                    "emit",
                    "WP01",
                    "--to",
                    "claimed",
                    "--actor",
                    "test-agent",
                    "--feature",
                    "034-test-feature",
                    "--json",
                ],
            )

        assert result.exit_code == 0, f"stdout: {result.output}"
        data = _extract_json(result.output)
        assert "event_id" in data
        assert data["wp_id"] == "WP01"
        assert data["to_lane"] == "claimed"
        assert data["actor"] == "test-agent"

    def test_emit_evidence_json_parsing(self, tmp_path: Path, feature_dir: Path):
        """Valid --evidence-json should be parsed and passed through."""
        patches = _patch_detection(tmp_path)

        # Build up state: planned -> claimed -> in_progress -> for_review
        transitions = [
            "claimed",
            "in_progress",
            "for_review",
        ]
        for to_lane in transitions:
            with (
                patches["locate_project_root"],
                patches["get_main_repo_root"],
                patches["detect_feature_slug"],
                patches["saas_fan_out"],
            ):
                r = runner.invoke(
                    app,
                    [
                        "emit",
                        "WP01",
                        "--to",
                        to_lane,
                        "--actor",
                        "test-agent",
                        "--feature",
                        "034-test-feature",
                    ],
                )
                assert r.exit_code == 0, f"Failed at {to_lane}: {r.output}"

        # Now transition to done with evidence
        evidence = {
            "review": {
                "reviewer": "alice",
                "verdict": "approved",
                "reference": "PR#1",
            }
        }
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
            patches["saas_fan_out"],
        ):
            result = runner.invoke(
                app,
                [
                    "emit",
                    "WP01",
                    "--to",
                    "done",
                    "--actor",
                    "test-agent",
                    "--feature",
                    "034-test-feature",
                    "--evidence-json",
                    json.dumps(evidence),
                    "--json",
                ],
            )

        assert result.exit_code == 0, f"stdout: {result.output}"
        data = _extract_json(result.output)
        assert data["to_lane"] == "done"

    def test_emit_invalid_evidence_json(self, tmp_path: Path, feature_dir: Path):
        """Invalid --evidence-json should produce a clear error and exit 1."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
            patches["saas_fan_out"],
        ):
            result = runner.invoke(
                app,
                [
                    "emit",
                    "WP01",
                    "--to",
                    "done",
                    "--actor",
                    "test-agent",
                    "--feature",
                    "034-test-feature",
                    "--evidence-json",
                    "not valid json",
                ],
            )

        assert result.exit_code == 1, f"stdout: {result.output}"
        assert "Invalid JSON" in result.output or "error" in result.output.lower()

    def test_emit_invalid_evidence_json_output_json(self, tmp_path: Path, feature_dir: Path):
        """Invalid --evidence-json with --json flag should produce JSON error."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
            patches["saas_fan_out"],
        ):
            result = runner.invoke(
                app,
                [
                    "emit",
                    "WP01",
                    "--to",
                    "done",
                    "--actor",
                    "test-agent",
                    "--feature",
                    "034-test-feature",
                    "--evidence-json",
                    "{bad",
                    "--json",
                ],
            )

        assert result.exit_code == 1
        data = _extract_json(result.output)
        assert "error" in data

    def test_emit_force_transition(self, tmp_path: Path, feature_dir: Path):
        """--force flag should allow bypassing guard conditions."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
            patches["saas_fan_out"],
        ):
            result = runner.invoke(
                app,
                [
                    "emit",
                    "WP01",
                    "--to",
                    "in_progress",
                    "--actor",
                    "test-agent",
                    "--feature",
                    "034-test-feature",
                    "--force",
                    "--reason",
                    "resuming after crash",
                ],
            )

        assert result.exit_code == 0, f"stdout: {result.output}"


# ---------------------------------------------------------------------------
# Materialize tests
# ---------------------------------------------------------------------------


class TestMaterializeCommand:
    """Tests for ``spec-kitty agent status materialize``."""

    def test_materialize_command(self, tmp_path: Path, feature_dir_with_events: Path):
        """Materialize should rebuild status.json from events."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
        ):
            result = runner.invoke(
                app,
                [
                    "materialize",
                    "--feature",
                    "034-test-feature",
                ],
            )

        assert result.exit_code == 0, f"stdout: {result.output}"
        assert "Materialized" in result.output
        assert "034-test-feature" in result.output

        # Verify status.json was created
        status_json = feature_dir_with_events / "status.json"
        assert status_json.exists()

    def test_materialize_json_output(self, tmp_path: Path, feature_dir_with_events: Path):
        """--json flag should produce the full snapshot as JSON."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
        ):
            result = runner.invoke(
                app,
                [
                    "materialize",
                    "--feature",
                    "034-test-feature",
                    "--json",
                ],
            )

        assert result.exit_code == 0, f"stdout: {result.output}"
        data = _extract_json(result.output)
        assert "feature_slug" in data
        assert "event_count" in data
        assert "work_packages" in data
        assert "summary" in data
        assert data["event_count"] == 1
        assert "WP01" in data["work_packages"]

    def test_materialize_no_events(self, tmp_path: Path, feature_dir: Path):
        """Missing event log should produce an error message."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
        ):
            result = runner.invoke(
                app,
                [
                    "materialize",
                    "--feature",
                    "034-test-feature",
                ],
            )

        assert result.exit_code == 1, f"stdout: {result.output}"
        assert "No event log" in result.output or "error" in result.output.lower()

    def test_materialize_no_events_json(self, tmp_path: Path, feature_dir: Path):
        """Missing event log with --json should produce JSON error."""
        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
        ):
            result = runner.invoke(
                app,
                [
                    "materialize",
                    "--feature",
                    "034-test-feature",
                    "--json",
                ],
            )

        assert result.exit_code == 1
        data = _extract_json(result.output)
        assert "error" in data

    def test_materialize_multiple_events(self, tmp_path: Path, feature_dir: Path):
        """Materialize should handle multiple events correctly."""
        events = [
            {
                "event_id": "01HXYZ0000000000000000AAA1",
                "feature_slug": "034-test-feature",
                "wp_id": "WP01",
                "from_lane": "planned",
                "to_lane": "claimed",
                "at": "2026-02-08T12:00:00+00:00",
                "actor": "agent-a",
                "force": False,
                "execution_mode": "worktree",
                "reason": None,
                "review_ref": None,
                "evidence": None,
            },
            {
                "event_id": "01HXYZ0000000000000000AAA2",
                "feature_slug": "034-test-feature",
                "wp_id": "WP01",
                "from_lane": "claimed",
                "to_lane": "in_progress",
                "at": "2026-02-08T12:01:00+00:00",
                "actor": "agent-a",
                "force": False,
                "execution_mode": "worktree",
                "reason": None,
                "review_ref": None,
                "evidence": None,
            },
            {
                "event_id": "01HXYZ0000000000000000AAA3",
                "feature_slug": "034-test-feature",
                "wp_id": "WP02",
                "from_lane": "planned",
                "to_lane": "claimed",
                "at": "2026-02-08T12:02:00+00:00",
                "actor": "agent-b",
                "force": False,
                "execution_mode": "worktree",
                "reason": None,
                "review_ref": None,
                "evidence": None,
            },
        ]
        events_path = feature_dir / "status.events.jsonl"
        lines = [json.dumps(e, sort_keys=True) for e in events]
        events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        patches = _patch_detection(tmp_path)
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
        ):
            result = runner.invoke(
                app,
                [
                    "materialize",
                    "--feature",
                    "034-test-feature",
                    "--json",
                ],
            )

        assert result.exit_code == 0, f"stdout: {result.output}"
        data = _extract_json(result.output)
        assert data["event_count"] == 3
        assert len(data["work_packages"]) == 2
        assert "WP01" in data["work_packages"]
        assert "WP02" in data["work_packages"]


# ---------------------------------------------------------------------------
# End-to-end (emit then materialize)
# ---------------------------------------------------------------------------


class TestEmitThenMaterialize:
    """End-to-end tests: emit events, then materialize."""

    def test_emit_then_materialize(self, tmp_path: Path, feature_dir: Path):
        """Emit a transition, then materialize and verify the snapshot."""
        patches = _patch_detection(tmp_path)

        # Emit
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
            patches["saas_fan_out"],
        ):
            emit_result = runner.invoke(
                app,
                [
                    "emit",
                    "WP01",
                    "--to",
                    "claimed",
                    "--actor",
                    "test-agent",
                    "--feature",
                    "034-test-feature",
                    "--json",
                ],
            )
        assert emit_result.exit_code == 0, f"stdout: {emit_result.output}"

        # Materialize
        with (
            patches["locate_project_root"],
            patches["get_main_repo_root"],
            patches["detect_feature_slug"],
        ):
            mat_result = runner.invoke(
                app,
                [
                    "materialize",
                    "--feature",
                    "034-test-feature",
                    "--json",
                ],
            )
        assert mat_result.exit_code == 0, f"stdout: {mat_result.output}"

        snapshot = _extract_json(mat_result.output)
        assert snapshot["event_count"] >= 1
        assert "WP01" in snapshot["work_packages"]
        assert snapshot["work_packages"]["WP01"]["lane"] == "claimed"
