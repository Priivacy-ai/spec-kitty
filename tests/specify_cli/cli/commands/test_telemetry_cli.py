"""Integration tests for the telemetry CLI commands."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.telemetry import app
from specify_cli.spec_kitty_events.models import Event
from specify_cli.telemetry.store import SimpleJsonStore

runner = CliRunner()


def _make_event_id(n: int) -> str:
    return f"01HXYZ{str(n).zfill(20)}"


def _seed_events(
    feature_dir: Path,
    events: list[dict],
) -> None:
    """Write events to a feature's execution.events.jsonl."""
    feature_dir.mkdir(parents=True, exist_ok=True)
    store = SimpleJsonStore(feature_dir / "execution.events.jsonl")
    for i, ev_kwargs in enumerate(events, start=1):
        ev = Event(
            event_id=ev_kwargs.get("event_id", _make_event_id(i)),
            event_type="ExecutionEvent",
            aggregate_id=ev_kwargs.get("aggregate_id", feature_dir.name),
            timestamp=ev_kwargs.get("timestamp", datetime.now(timezone.utc)),
            node_id=ev_kwargs.get("node_id", "cli"),
            lamport_clock=ev_kwargs.get("lamport_clock", i),
            payload={
                "wp_id": ev_kwargs.get("wp_id", "WP01"),
                "agent": ev_kwargs.get("agent", "claude"),
                "model": ev_kwargs.get("model", "claude-sonnet-4-20250514"),
                "input_tokens": ev_kwargs.get("input_tokens", 1000),
                "output_tokens": ev_kwargs.get("output_tokens", 500),
                "cost_usd": ev_kwargs.get("cost_usd", None),
                "success": ev_kwargs.get("success", True),
            },
        )
        store.save_event(ev)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Create a project with kitty-specs dir."""
    ks = tmp_path / "kitty-specs"
    ks.mkdir()
    return tmp_path


def _invoke(args: list[str], repo_root: Path) -> object:
    """Invoke the telemetry CLI with mocked repo root.
    
    Note: Typer promotes a single-command group to a flat command,
    so we strip the leading 'cost' argument if present.
    """
    if args and args[0] == "cost":
        args = args[1:]
    with patch(
        "specify_cli.cli.commands.agent.telemetry.find_repo_root",
        return_value=repo_root,
    ):
        return runner.invoke(app, args)


class TestCostWithEvents:
    def test_basic_table_output(self, project: Path) -> None:
        feature_dir = project / "kitty-specs" / "043-test-feature"
        _seed_events(feature_dir, [
            {"agent": "claude", "input_tokens": 1000, "output_tokens": 500},
            {"agent": "claude", "input_tokens": 2000, "output_tokens": 1000},
        ])
        result = _invoke(["cost"], project)
        assert result.exit_code == 0
        assert "Cost Report" in result.output
        assert "claude" in result.output
        assert "TOTAL" in result.output

    def test_multiple_agents(self, project: Path) -> None:
        feature_dir = project / "kitty-specs" / "043-test-feature"
        _seed_events(feature_dir, [
            {"agent": "claude", "input_tokens": 1000, "output_tokens": 500, "event_id": _make_event_id(1)},
            {"agent": "copilot", "input_tokens": 2000, "output_tokens": 800, "event_id": _make_event_id(2)},
        ])
        result = _invoke(["cost"], project)
        assert result.exit_code == 0
        assert "claude" in result.output
        assert "copilot" in result.output


class TestCostEmptyProject:
    def test_no_events(self, project: Path) -> None:
        result = _invoke(["cost"], project)
        assert result.exit_code == 0
        assert "No execution events found" in result.output

    def test_no_kitty_specs(self, tmp_path: Path) -> None:
        result = _invoke(["cost"], tmp_path)
        assert result.exit_code == 0
        assert "No execution events found" in result.output

    def test_not_in_repo(self) -> None:
        from specify_cli.tasks_support import TaskCliError

        with patch(
            "specify_cli.cli.commands.agent.telemetry.find_repo_root",
            side_effect=TaskCliError("not a repo"),
        ):
            result = runner.invoke(app, [])
        assert result.exit_code == 1
        assert "Not inside a spec-kitty project" in result.output

    def test_invalid_since_date(self, project: Path) -> None:
        result = _invoke(["cost", "--since", "not-a-date"], project)
        assert result.exit_code == 1
        assert "Invalid date format" in result.output


class TestCostJsonOutput:
    def test_json_output_parseable(self, project: Path) -> None:
        feature_dir = project / "kitty-specs" / "043-test-feature"
        _seed_events(feature_dir, [
            {"agent": "claude", "input_tokens": 1000, "output_tokens": 500},
        ])
        result = _invoke(["cost", "--json"], project)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["group_key"] == "claude"
        assert data[0]["group_by"] == "agent"
        assert data[0]["total_input_tokens"] == 1000
        assert data[0]["total_output_tokens"] == 500
        assert data[0]["event_count"] == 1

    def test_json_multiple_groups(self, project: Path) -> None:
        feature_dir = project / "kitty-specs" / "043-test-feature"
        _seed_events(feature_dir, [
            {"agent": "claude", "event_id": _make_event_id(1)},
            {"agent": "copilot", "event_id": _make_event_id(2)},
        ])
        result = _invoke(["cost", "--json"], project)
        data = json.loads(result.output)
        assert len(data) == 2
        keys = {d["group_key"] for d in data}
        assert keys == {"claude", "copilot"}


class TestCostFeatureFilter:
    def test_feature_filter_matches(self, project: Path) -> None:
        feat1 = project / "kitty-specs" / "043-telemetry"
        feat2 = project / "kitty-specs" / "044-other"
        _seed_events(feat1, [{"agent": "claude", "event_id": _make_event_id(1)}])
        _seed_events(feat2, [{"agent": "copilot", "event_id": _make_event_id(2)}])
        result = _invoke(["cost", "--feature", "043", "--json"], project)
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["group_key"] == "claude"

    def test_feature_no_match(self, project: Path) -> None:
        feat1 = project / "kitty-specs" / "043-telemetry"
        _seed_events(feat1, [{"agent": "claude"}])
        result = _invoke(["cost", "--feature", "999"], project)
        assert result.exit_code == 0
        assert "No features matching" in result.output


class TestCostGroupBy:
    def test_group_by_model(self, project: Path) -> None:
        feature_dir = project / "kitty-specs" / "043-test-feature"
        _seed_events(feature_dir, [
            {"model": "claude-sonnet-4-20250514", "event_id": _make_event_id(1)},
            {"model": "gpt-4o", "event_id": _make_event_id(2)},
        ])
        result = _invoke(["cost", "--group-by", "model", "--json"], project)
        data = json.loads(result.output)
        keys = {d["group_key"] for d in data}
        assert "claude-sonnet-4-20250514" in keys
        assert "gpt-4o" in keys

    def test_group_by_feature(self, project: Path) -> None:
        feat1 = project / "kitty-specs" / "043-telemetry"
        feat2 = project / "kitty-specs" / "044-other"
        _seed_events(feat1, [{"event_id": _make_event_id(1), "aggregate_id": "043-telemetry"}])
        _seed_events(feat2, [{"event_id": _make_event_id(2), "aggregate_id": "044-other"}])
        result = _invoke(["cost", "--group-by", "feature", "--json"], project)
        data = json.loads(result.output)
        keys = {d["group_key"] for d in data}
        assert "043-telemetry" in keys
        assert "044-other" in keys


class TestCostTimeframeFilter:
    def test_since_filter(self, project: Path) -> None:
        feature_dir = project / "kitty-specs" / "043-test-feature"
        _seed_events(feature_dir, [
            {
                "agent": "claude",
                "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "event_id": _make_event_id(1),
            },
            {
                "agent": "copilot",
                "timestamp": datetime(2026, 6, 1, tzinfo=timezone.utc),
                "event_id": _make_event_id(2),
            },
        ])
        result = _invoke(
            ["cost", "--since", "2026-03-01T00:00:00+00:00", "--json"],
            project,
        )
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["group_key"] == "copilot"

    def test_until_filter(self, project: Path) -> None:
        feature_dir = project / "kitty-specs" / "043-test-feature"
        _seed_events(feature_dir, [
            {
                "agent": "claude",
                "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "event_id": _make_event_id(1),
            },
            {
                "agent": "copilot",
                "timestamp": datetime(2026, 6, 1, tzinfo=timezone.utc),
                "event_id": _make_event_id(2),
            },
        ])
        result = _invoke(
            ["cost", "--until", "2026-03-01T00:00:00+00:00", "--json"],
            project,
        )
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["group_key"] == "claude"
