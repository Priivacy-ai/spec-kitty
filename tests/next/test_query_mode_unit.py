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


def _make_mock_decision(
    is_query: bool = False,
    mission_state: str = "specify",
    *,
    agent: str | None = "claude",
    preview_step: str | None = None,
):
    from specify_cli.next.decision import Decision, DecisionKind

    return Decision(
        kind=DecisionKind.query if is_query else DecisionKind.step,
        agent=agent,
        mission_slug="069-test",
        mission="069-test",
        mission_state=mission_state,
        timestamp="2026-04-07T00:00:00+00:00",
        is_query=is_query,
        preview_step=preview_step,
    )


class TestQueryModeDoesNotAdvance:
    def test_bare_call_invokes_query_not_decide(self, tmp_path: Path) -> None:
        """When --result is omitted, query_current_state() is called, not decide_next()."""
        mock_decision = _make_mock_decision(is_query=True, mission_state="specify")

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch("specify_cli.next.runtime_bridge.query_current_state", return_value=mock_decision) as mock_query,
            patch("specify_cli.cli.commands.next_cmd.decide_next") as mock_decide,
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test", "--json"],
            )

        mock_query.assert_called_once()
        mock_decide.assert_not_called()

    def test_query_mode_allows_missing_agent(self, tmp_path: Path) -> None:
        mock_decision = _make_mock_decision(is_query=True, mission_state="not_started", preview_step="discovery", agent=None)

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch("specify_cli.next.runtime_bridge.query_current_state", return_value=mock_decision) as mock_query,
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--mission", "069-test", "--json"],
            )

        assert result.exit_code == 0
        mock_query.assert_called_once_with(None, "069-test", tmp_path)

    def test_result_success_still_requires_agent(self, tmp_path: Path) -> None:
        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--mission", "069-test", "--result", "success", "--json"],
            )

        assert result.exit_code == 1
        assert "--agent is required when --result is provided" in result.output

    def test_answer_requires_agent_when_used_without_result(self, tmp_path: Path) -> None:
        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--mission", "069-test", "--answer", "yes", "--json"],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "--agent is required when --answer is provided" in data["error"]

    def test_answer_is_processed_before_query_output(self, tmp_path: Path) -> None:
        mock_decision = _make_mock_decision(is_query=True, mission_state="not_started", preview_step="discovery")

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch("specify_cli.cli.commands.next_cmd._handle_answer", return_value="input:approval") as mock_answer,
            patch("specify_cli.next.runtime_bridge.query_current_state", return_value=mock_decision),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--mission", "069-test", "--agent", "claude", "--answer", "yes", "--json"],
            )

        assert result.exit_code == 0
        mock_answer.assert_called_once()
        data = json.loads(result.output)
        assert data["answered"] == "input:approval"
        assert data["answer"] == "yes"

    def test_human_output_still_begins_with_query_label_after_answer(self, tmp_path: Path) -> None:
        mock_decision = _make_mock_decision(is_query=True, mission_state="not_started", preview_step="discovery")

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch("specify_cli.cli.commands.next_cmd._handle_answer", return_value="input:approval"),
            patch("specify_cli.next.runtime_bridge.query_current_state", return_value=mock_decision),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--mission", "069-test", "--agent", "claude", "--answer", "yes"],
            )

        first_line = result.output.splitlines()[0]
        assert first_line == "[QUERY — no result provided, state not advanced]"
        assert "Answered decision: input:approval" in result.output


class TestQueryModeOutput:
    def test_human_output_begins_with_query_label(self, tmp_path: Path) -> None:
        """SC-003: first line of stdout is the verbatim query label."""
        mock_decision = _make_mock_decision(is_query=True, mission_state="specify")

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch("specify_cli.next.runtime_bridge.query_current_state", return_value=mock_decision),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test"],
            )

        lines = result.output.strip().split("\n")
        assert lines[0] == "[QUERY \u2014 no result provided, state not advanced]"

    def test_json_output_includes_is_query_true(self, tmp_path: Path) -> None:
        """JSON output includes is_query: true."""
        mock_decision = _make_mock_decision(is_query=True)

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch("specify_cli.next.runtime_bridge.query_current_state", return_value=mock_decision),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test", "--json"],
            )

        data = json.loads(result.output)
        assert data.get("is_query") is True

    def test_human_output_shows_not_started_preview_step(self, tmp_path: Path) -> None:
        mock_decision = _make_mock_decision(is_query=True, mission_state="not_started", preview_step="discovery")

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch("specify_cli.next.runtime_bridge.query_current_state", return_value=mock_decision),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--mission", "069-test"],
            )

        assert "Mission: 069-test @ not_started" in result.output
        assert "Next step: discovery" in result.output

    def test_json_kind_is_query(self, tmp_path: Path) -> None:
        """JSON output kind field is 'query'."""
        mock_decision = _make_mock_decision(is_query=True)

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch("specify_cli.next.runtime_bridge.query_current_state", return_value=mock_decision),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test", "--json"],
            )

        data = json.loads(result.output)
        assert data.get("kind") == "query"
        assert data.get("is_query") is True


class TestBuildPromptSafe:
    def test_build_prompt_safe_suppresses_stdout_noise(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from specify_cli.next.decision import _build_prompt_safe

        def noisy_build_prompt(**_kwargs):
            print("noisy stdout")
            return None, tmp_path / "prompt.md"

        with patch("specify_cli.next.prompt_builder.build_prompt", side_effect=noisy_build_prompt):
            result = _build_prompt_safe(
                action="implement",
                feature_dir=tmp_path,
                mission_slug="069-test",
                wp_id="WP01",
                agent="claude",
                repo_root=tmp_path,
                mission_type="software-dev",
            )

        assert result == str(tmp_path / "prompt.md")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


class TestQueryCurrentStateErrorPaths:
    """Cover the three error-handling branches in query_current_state() (runtime_bridge.py).

    These tests exercise lines 575, 591-592, and 610-611 which are otherwise
    unreachable via CLI-level tests.
    """

    def test_missing_feature_dir_returns_unknown_state(self, tmp_path: Path) -> None:
        """Line 575: feature_dir does not exist → Decision with mission_state='unknown'."""
        from specify_cli.next.runtime_bridge import query_current_state

        # tmp_path / "kitty-specs" / "069-missing" does NOT exist
        decision = query_current_state("claude", "069-missing", tmp_path)

        assert decision.is_query is True
        assert decision.mission_state == "unknown"
        assert decision.kind == "query"

    def test_ephemeral_query_run_exception_returns_unknown_state(self, tmp_path: Path) -> None:
        """Ephemeral fresh-query bootstrap failure degrades to an unknown decision."""
        from specify_cli.next.runtime_bridge import query_current_state

        feature_dir = tmp_path / "kitty-specs" / "069-test"
        feature_dir.mkdir(parents=True)

        with (
            patch("specify_cli.next.runtime_bridge._existing_run_ref", return_value=None),
            patch("specify_cli.next.runtime_bridge._start_ephemeral_query_run", side_effect=RuntimeError("run init failed")),
            patch("specify_cli.next.runtime_bridge.get_mission_type", return_value="software-dev"),
            patch("specify_cli.next.runtime_bridge._compute_wp_progress", return_value=None),
        ):
            decision = query_current_state("claude", "069-test", tmp_path)

        assert decision.is_query is True
        assert decision.mission_state == "unknown"

    def test_read_snapshot_exception_returns_unknown_step(self, tmp_path: Path) -> None:
        """Lines 610-611: _read_snapshot raises → step falls back to 'unknown', query still works."""
        from specify_cli.next.runtime_bridge import query_current_state
        from unittest.mock import MagicMock

        feature_dir = tmp_path / "kitty-specs" / "069-test"
        feature_dir.mkdir(parents=True)

        mock_run_ref = MagicMock()
        mock_run_ref.run_dir = str(tmp_path / "run")

        with (
            patch("specify_cli.next.runtime_bridge.get_or_start_run", return_value=mock_run_ref),
            patch("specify_cli.next.runtime_bridge.get_mission_type", return_value="software-dev"),
            patch("specify_cli.next.runtime_bridge._compute_wp_progress", return_value=None),
            patch("spec_kitty_runtime.engine._read_snapshot", side_effect=Exception("snapshot read failed")),
        ):
            decision = query_current_state("claude", "069-test", tmp_path)

        assert decision.is_query is True
        assert decision.mission_state == "unknown"  # graceful fallback

    def test_invalid_first_step_raises_clear_validation_error(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import QueryModeValidationError, query_current_state
        from unittest.mock import MagicMock

        feature_dir = tmp_path / "kitty-specs" / "069-test"
        feature_dir.mkdir(parents=True)

        mock_run_ref = MagicMock()
        mock_run_ref.run_dir = str(tmp_path / "run")
        mock_run_ref.run_id = "run-123"

        snapshot = MagicMock()
        snapshot.completed_steps = []
        snapshot.pending_decisions = {}
        snapshot.decisions = {}
        snapshot.issued_step_id = None
        snapshot.policy_snapshot = MagicMock()

        blocked = MagicMock()
        blocked.kind = "blocked"
        blocked.step_id = None

        with (
            patch("specify_cli.next.runtime_bridge._existing_run_ref", return_value=mock_run_ref),
            patch("specify_cli.next.runtime_bridge.get_mission_type", return_value="software-dev"),
            patch("specify_cli.next.runtime_bridge._compute_wp_progress", return_value=None),
            patch("spec_kitty_runtime.engine._read_snapshot", return_value=snapshot),
            patch("specify_cli.next.runtime_bridge.load_mission_template_file", return_value=MagicMock()),
            patch("spec_kitty_runtime.planner.plan_next", return_value=blocked),
        ):
            with pytest.raises(QueryModeValidationError, match="has no issuable first step"):
                query_current_state("claude", "069-test", tmp_path)

    def test_pending_decision_metadata_is_preserved_in_query_mode(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import query_current_state
        from unittest.mock import MagicMock

        feature_dir = tmp_path / "kitty-specs" / "069-test"
        feature_dir.mkdir(parents=True)

        mock_run_ref = MagicMock()
        mock_run_ref.run_dir = str(tmp_path / "run")
        mock_run_ref.run_id = "run-123"

        snapshot = MagicMock()
        snapshot.completed_steps = ["discovery"]
        snapshot.pending_decisions = {"input:approval": {"status": "pending"}}
        snapshot.decisions = {"input:approval": {"status": "pending"}}
        snapshot.issued_step_id = "collect_input"
        snapshot.policy_snapshot = MagicMock()

        decision_required = MagicMock()
        decision_required.kind = "decision_required"
        decision_required.step_id = "collect_input"
        decision_required.decision_id = "input:approval"
        decision_required.input_key = "approval"
        decision_required.question = "Approve?"
        decision_required.options = ["yes", "no"]

        with (
            patch("specify_cli.next.runtime_bridge._existing_run_ref", return_value=mock_run_ref),
            patch("specify_cli.next.runtime_bridge.get_mission_type", return_value="software-dev"),
            patch("specify_cli.next.runtime_bridge._compute_wp_progress", return_value=None),
            patch("spec_kitty_runtime.engine._read_snapshot", return_value=snapshot),
            patch("specify_cli.next.runtime_bridge.load_mission_template_file", return_value=MagicMock()),
            patch("spec_kitty_runtime.planner.plan_next", return_value=decision_required),
        ):
            decision = query_current_state("claude", "069-test", tmp_path)

        assert decision.mission_state == "collect_input"
        assert decision.step_id == "collect_input"
        assert decision.decision_id == "input:approval"
        assert decision.input_key == "approval"
        assert decision.question == "Approve?"
        assert decision.options == ["yes", "no"]


class TestQueryModeErrorOutput:
    def test_json_query_validation_failure_returns_error_document(self, tmp_path: Path) -> None:
        from specify_cli.next.runtime_bridge import QueryModeValidationError

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch(
                "specify_cli.next.runtime_bridge.query_current_state",
                side_effect=QueryModeValidationError("Mission 'software-dev' has no issuable first step for run '069-test'"),
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--mission", "069-test", "--json"],
            )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "has no issuable first step" in data["error"]


class TestResultSuccessStillAdvances:
    def test_result_success_calls_decide_not_query(self, tmp_path: Path) -> None:
        """C-005: --result success retains its advancing behavior."""
        from specify_cli.next.decision import Decision, DecisionKind

        mock_decision = Decision(
            kind=DecisionKind.step,
            agent="claude",
            mission_slug="069-test",
            mission="069-test",
            mission_state="plan",
            timestamp="2026-04-07T00:00:00+00:00",
        )

        with (
            patch("specify_cli.cli.commands.next_cmd.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.next_cmd.require_explicit_feature", return_value="069-test"),
            patch("specify_cli.cli.commands.next_cmd.decide_next", return_value=mock_decision) as mock_decide,
            patch("specify_cli.next.runtime_bridge.query_current_state") as mock_query,
            patch("specify_cli.mission_v1.events.emit_event"),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--agent", "claude", "--mission", "069-test", "--result", "success", "--json"],
            )

        mock_decide.assert_called_once()
        mock_query.assert_not_called()
