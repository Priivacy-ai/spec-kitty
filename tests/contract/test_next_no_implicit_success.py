"""Contract test: bare ``spec-kitty next`` does not advance state (FR-019, WP04/T018).

A bare call (no ``--result``) MUST be a query, not an outcome. The CLI
bridge must pass ``result=None`` to the runtime, and the runtime must
treat ``result is None`` as a read-only query.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app

pytestmark = pytest.mark.fast
runner = CliRunner()


@pytest.fixture(autouse=True)
def _skip_root_project_schema_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep command-unit tests isolated from the checkout's project metadata."""
    monkeypatch.setattr("specify_cli.locate_project_root", lambda: None)


def _make_query_decision(mission_state: str = "specify"):
    from specify_cli.next.decision import Decision, DecisionKind

    return Decision(
        kind=DecisionKind.query,
        agent="claude",
        mission_slug="fixture-mission",
        mission="software-dev",
        mission_state=mission_state,
        timestamp="2026-04-26T00:00:00+00:00",
        is_query=True,
        mission_type="software-dev",
    )


class TestBareNextDoesNotAdvance:
    """FR-019 contract: a bare next is a query, not an outcome."""

    def test_bare_next_calls_query_not_decide(self, tmp_path: Path) -> None:
        """Without --result, query_current_state runs and decide_next does not."""
        decision = _make_query_decision(mission_state="specify")

        with (
            patch(
                "specify_cli.cli.commands.next_cmd.locate_project_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.next_cmd.resolve_selector",
                return_value=SimpleNamespace(canonical_value="fixture-mission"),
            ),
            patch(
                "specify_cli.next.runtime_bridge.query_current_state",
                return_value=decision,
            ) as mock_query,
            patch("specify_cli.cli.commands.next_cmd.decide_next") as mock_decide,
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--mission", "fixture-mission", "--json"],
            )

        # Query mode must run; decide_next (which advances state) must not.
        mock_query.assert_called_once()
        mock_decide.assert_not_called()
        assert result.exit_code == 0, result.output

    def test_bare_next_does_not_emit_mission_next_invoked(self, tmp_path: Path) -> None:
        """Bare next must not write a mission-next-invoked event (no advance)."""
        decision = _make_query_decision()

        with (
            patch(
                "specify_cli.cli.commands.next_cmd.locate_project_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.next_cmd.resolve_selector",
                return_value=SimpleNamespace(canonical_value="fixture-mission"),
            ),
            patch(
                "specify_cli.next.runtime_bridge.query_current_state",
                return_value=decision,
            ),
            patch("specify_cli.cli.commands.next_cmd._emit_mission_next_invoked") as mock_emit,
        ):
            runner.invoke(cli_app, ["next", "--mission", "fixture-mission", "--json"])

        mock_emit.assert_not_called()

    def test_query_mode_returns_decision_kind_query(self, tmp_path: Path) -> None:
        decision = _make_query_decision(mission_state="implementing")

        with (
            patch(
                "specify_cli.cli.commands.next_cmd.locate_project_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.next_cmd.resolve_selector",
                return_value=SimpleNamespace(canonical_value="fixture-mission"),
            ),
            patch(
                "specify_cli.next.runtime_bridge.query_current_state",
                return_value=decision,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["next", "--mission", "fixture-mission", "--json"],
            )

        # JSON output must include kind=query and is_query=True.
        assert '"kind": "query"' in result.output
        assert '"is_query": true' in result.output

    def test_explicit_success_uses_decide_next(self, tmp_path: Path) -> None:
        """When --result success is provided, decide_next runs (advance path)."""
        from specify_cli.next.decision import Decision, DecisionKind

        # WP02 / #844: kind=step now requires a non-null, on-disk-resolvable
        # prompt_file (C1/C2). Materialize one under tmp_path.
        prompt = tmp_path / "implement.md"
        prompt.write_text("# implement", encoding="utf-8")

        decision = Decision(
            kind=DecisionKind.step,
            agent="claude",
            mission_slug="fixture-mission",
            mission="software-dev",
            mission_state="implementing",
            timestamp="2026-04-26T00:00:00+00:00",
            mission_type="software-dev",
            action="implement",
            prompt_file=str(prompt),
        )

        with (
            patch(
                "specify_cli.cli.commands.next_cmd.locate_project_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.next_cmd.resolve_selector",
                return_value=SimpleNamespace(canonical_value="fixture-mission"),
            ),
            patch(
                "specify_cli.cli.commands.next_cmd.decide_next",
                return_value=decision,
            ) as mock_decide,
            patch("specify_cli.cli.commands.next_cmd._emit_mission_next_invoked"),
            patch("specify_cli.next.runtime_bridge.query_current_state") as mock_query,
        ):
            runner.invoke(
                cli_app,
                [
                    "next",
                    "--agent",
                    "claude",
                    "--mission",
                    "fixture-mission",
                    "--result",
                    "success",
                    "--json",
                ],
            )

        mock_decide.assert_called_once()
        mock_query.assert_not_called()
