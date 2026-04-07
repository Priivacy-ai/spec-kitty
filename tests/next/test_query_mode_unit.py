"""Unit tests for spec-kitty next query mode (FR-012, FR-013)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app

pytestmark = pytest.mark.fast
runner = CliRunner()


def _make_mock_decision(is_query: bool = False, mission_state: str = "specify"):
    from specify_cli.next.decision import Decision, DecisionKind
    return Decision(
        kind=DecisionKind.query if is_query else DecisionKind.step,
        agent="claude",
        mission_slug="069-test",
        mission="069-test",
        mission_state=mission_state,
        timestamp="2026-04-07T00:00:00+00:00",
        is_query=is_query,
    )


class TestQueryModeDoesNotAdvance:
    def test_bare_call_invokes_query_not_decide(self, tmp_path: Path) -> None:
        """When --result is omitted, query_current_state() is called, not decide_next()."""
        mock_decision = _make_mock_decision(is_query=True, mission_state="specify")

        with patch("specify_cli.cli.commands.next_cmd.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.next_cmd.require_explicit_feature",
                   return_value="069-test"), \
             patch("specify_cli.next.runtime_bridge.query_current_state",
                   return_value=mock_decision) as mock_query, \
             patch("specify_cli.cli.commands.next_cmd.decide_next") as mock_decide:

            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test", "--json"],
            )

        mock_query.assert_called_once()
        mock_decide.assert_not_called()


class TestQueryModeOutput:
    def test_human_output_begins_with_query_label(self, tmp_path: Path) -> None:
        """SC-003: first line of stdout is the verbatim query label."""
        mock_decision = _make_mock_decision(is_query=True, mission_state="specify")

        with patch("specify_cli.cli.commands.next_cmd.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.next_cmd.require_explicit_feature",
                   return_value="069-test"), \
             patch("specify_cli.next.runtime_bridge.query_current_state",
                   return_value=mock_decision):

            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test"],
            )

        lines = result.output.strip().split("\n")
        assert lines[0] == "[QUERY \u2014 no result provided, state not advanced]"

    def test_json_output_includes_is_query_true(self, tmp_path: Path) -> None:
        """JSON output includes is_query: true."""
        mock_decision = _make_mock_decision(is_query=True)

        with patch("specify_cli.cli.commands.next_cmd.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.next_cmd.require_explicit_feature",
                   return_value="069-test"), \
             patch("specify_cli.next.runtime_bridge.query_current_state",
                   return_value=mock_decision):

            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test", "--json"],
            )

        data = json.loads(result.output)
        assert data.get("is_query") is True

    def test_json_kind_is_query(self, tmp_path: Path) -> None:
        """JSON output kind field is 'query'."""
        mock_decision = _make_mock_decision(is_query=True)

        with patch("specify_cli.cli.commands.next_cmd.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.next_cmd.require_explicit_feature",
                   return_value="069-test"), \
             patch("specify_cli.next.runtime_bridge.query_current_state",
                   return_value=mock_decision):

            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test", "--json"],
            )

        data = json.loads(result.output)
        assert data.get("kind") == "query"
        assert data.get("is_query") is True


class TestResultSuccessStillAdvances:
    def test_result_success_calls_decide_not_query(self, tmp_path: Path) -> None:
        """C-005: --result success retains its advancing behavior."""
        from specify_cli.next.decision import Decision, DecisionKind
        mock_decision = Decision(
            kind=DecisionKind.step, agent="claude", mission_slug="069-test",
            mission="069-test", mission_state="plan", timestamp="2026-04-07T00:00:00+00:00",
        )

        with patch("specify_cli.cli.commands.next_cmd.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.cli.commands.next_cmd.require_explicit_feature",
                   return_value="069-test"), \
             patch("specify_cli.cli.commands.next_cmd.decide_next",
                   return_value=mock_decision) as mock_decide, \
             patch("specify_cli.next.runtime_bridge.query_current_state") as mock_query, \
             patch("specify_cli.mission_v1.events.emit_event"):

            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test", "--result", "success", "--json"],
            )

        mock_decide.assert_called_once()
        mock_query.assert_not_called()
