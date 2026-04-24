"""Integration tests for the plan command widen affordance (FR-002).

These tests verify that ``spec-kitty plan`` invokes ``run_plan_interview``
with widen-mode infrastructure after scaffolding plan.md.

Coverage:
- CANCEL path: ``w`` typed → CANCEL → re-prompts same question → normal answer.
- CONTINUE path: ``w`` typed → CONTINUE → WidenPendingEntry written to store.
- BLOCK path: ``w`` typed → BLOCK → blocked prompt loop; resolved via local answer.
- Widen NOT shown when prereqs absent (no SaaS token).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.lifecycle import (
    PLAN_WIDEN_QUESTIONS,
    plan,
)
from specify_cli.widen.models import (
    PrereqState,
    WidenAction,
    WidenFlowResult,
)
from specify_cli.widen.state import WidenPendingStore

# ---------------------------------------------------------------------------
# Test app / helpers
# ---------------------------------------------------------------------------

_app = typer.Typer()
_app.command()(plan)

runner = CliRunner()

MISSION_SLUG = "test-plan-widen"
MISSION_ID = "01KWIDENPLANTESTMISSION0001"

_N_QUESTIONS = len(PLAN_WIDEN_QUESTIONS)


def _setup_repo(tmp_path: Path) -> Path:
    """Create a minimal repo structure with .kittify/ and a mission meta.json."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    mission_dir = tmp_path / "kitty-specs" / MISSION_SLUG
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_id": MISSION_ID, "mission_slug": MISSION_SLUG}),
        encoding="utf-8",
    )
    return tmp_path


def _make_inputs(answers: list[str]) -> str:
    """Build newline-joined input string for the question loop."""
    return "\n".join(answers) + "\n"


# ---------------------------------------------------------------------------
# Widen absent (no prereqs satisfied)
# ---------------------------------------------------------------------------


class TestPlanWidenAbsent:
    """[w]iden must NOT appear when prereqs are not met."""

    def test_widen_not_shown_without_prereqs(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        inputs = _make_inputs([""] * _N_QUESTIONS)
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with (
                patch(
                    "specify_cli.cli.commands.lifecycle.agent_feature.setup_plan",
                    return_value=None,
                ),
                patch(
                    "specify_cli.cli.commands.lifecycle.locate_project_root",
                    return_value=tmp_path,
                ),
                patch(
                    "specify_cli.widen.check_prereqs",
                    return_value=PrereqState(
                        teamspace_ok=False,
                        slack_ok=False,
                        saas_reachable=False,
                    ),
                ),
            ):
                result = runner.invoke(
                    _app,
                    ["--mission", MISSION_SLUG],
                    input=inputs,
                    catch_exceptions=False,
                )
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, result.output
        assert "[w]iden" not in result.output


# ---------------------------------------------------------------------------
# Widen CANCEL path
# ---------------------------------------------------------------------------


class TestPlanWidenCancelPath:
    """CANCEL: typing w → CANCEL → re-prompts same question → continues."""

    def test_cancel_path_reprompts_and_continues(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)

        cancel_result = WidenFlowResult(action=WidenAction.CANCEL)
        mock_flow = MagicMock()
        mock_flow.run_widen_mode.return_value = cancel_result

        prereq_ok = PrereqState(teamspace_ok=True, slack_ok=True, saas_reachable=True)

        # Q1: "w" → CANCEL → "My approach"; Q2..N: accept defaults
        q1_inputs = ["w", "My approach"]
        remaining_q = [""] * (_N_QUESTIONS - 1)
        inputs = _make_inputs(q1_inputs + remaining_q)

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with (
                patch(
                    "specify_cli.cli.commands.lifecycle.agent_feature.setup_plan",
                    return_value=None,
                ),
                patch(
                    "specify_cli.cli.commands.lifecycle.locate_project_root",
                    return_value=tmp_path,
                ),
                patch(
                    "specify_cli.saas_client.client.SaasClient.from_env",
                    return_value=MagicMock(has_token=True),
                ),
                patch(
                    "specify_cli.widen.check_prereqs",
                    return_value=prereq_ok,
                ),
                patch(
                    "specify_cli.widen.flow.WidenFlow",
                    return_value=mock_flow,
                ),
                patch(
                    "specify_cli.widen.state.WidenPendingStore",
                ) as mock_store_cls,
            ):
                mock_store_inst = MagicMock()
                mock_store_inst.list_pending.return_value = []
                mock_store_cls.return_value = mock_store_inst

                result = runner.invoke(
                    _app,
                    ["--mission", MISSION_SLUG],
                    input=inputs,
                    catch_exceptions=False,
                )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        mock_flow.run_widen_mode.assert_called_once()


# ---------------------------------------------------------------------------
# Widen CONTINUE path
# ---------------------------------------------------------------------------


class TestPlanWidenContinuePath:
    """CONTINUE: typing w → CONTINUE → WidenPendingEntry written; question skipped."""

    def test_continue_path_writes_pending_entry(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)

        decision_id = "01KPLANWIDENCONTINUE00001"
        continue_result = WidenFlowResult(
            action=WidenAction.CONTINUE,
            decision_id=decision_id,
            invited=["Carol Lee"],
        )
        mock_flow = MagicMock()
        mock_flow.run_widen_mode.return_value = continue_result

        prereq_ok = PrereqState(teamspace_ok=True, slack_ok=True, saas_reachable=True)

        real_store = WidenPendingStore(tmp_path, MISSION_SLUG)

        # Q1: "w" → CONTINUE (skipped); Q2..N: accept defaults
        q1_inputs = ["w"]
        remaining_q = [""] * (_N_QUESTIONS - 1)
        inputs = _make_inputs(q1_inputs + remaining_q)

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with (
                patch(
                    "specify_cli.cli.commands.lifecycle.agent_feature.setup_plan",
                    return_value=None,
                ),
                patch(
                    "specify_cli.cli.commands.lifecycle.locate_project_root",
                    return_value=tmp_path,
                ),
                patch(
                    "specify_cli.saas_client.client.SaasClient.from_env",
                    return_value=MagicMock(has_token=True),
                ),
                patch(
                    "specify_cli.widen.check_prereqs",
                    return_value=prereq_ok,
                ),
                patch(
                    "specify_cli.widen.flow.WidenFlow",
                    return_value=mock_flow,
                ),
                patch(
                    "specify_cli.widen.state.WidenPendingStore",
                    return_value=real_store,
                ),
                patch(
                    "specify_cli.widen.interview_helpers.run_end_of_interview_pending_pass",
                    MagicMock(),
                ),
            ):
                result = runner.invoke(
                    _app,
                    ["--mission", MISSION_SLUG],
                    input=inputs,
                    catch_exceptions=False,
                )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        mock_flow.run_widen_mode.assert_called_once()

        pending = real_store.list_pending()
        assert len(pending) == 1
        assert pending[0].decision_id == decision_id
        assert pending[0].mission_slug == MISSION_SLUG
        assert pending[0].question_id.startswith("plan.")


# ---------------------------------------------------------------------------
# Widen BLOCK path
# ---------------------------------------------------------------------------


class TestPlanWidenBlockPath:
    """BLOCK: typing w → BLOCK → blocked-prompt loop; resolved via local answer."""

    def test_block_path_resolves_via_local_answer(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)

        decision_id = "01KPLANWIDENBLOCK000000001"
        block_result = WidenFlowResult(
            action=WidenAction.BLOCK,
            decision_id=decision_id,
            invited=["Dave Eng"],
        )
        mock_flow = MagicMock()
        mock_flow.run_widen_mode.return_value = block_result

        prereq_ok = PrereqState(teamspace_ok=True, slack_ok=True, saas_reachable=True)

        # Q1: "w" → BLOCK → "local plan answer"; Q2..N: accept defaults
        q1_inputs = ["w", "local plan answer"]
        remaining_q = [""] * (_N_QUESTIONS - 1)
        inputs = _make_inputs(q1_inputs + remaining_q)

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with (
                patch(
                    "specify_cli.cli.commands.lifecycle.agent_feature.setup_plan",
                    return_value=None,
                ),
                patch(
                    "specify_cli.cli.commands.lifecycle.locate_project_root",
                    return_value=tmp_path,
                ),
                patch(
                    "specify_cli.saas_client.client.SaasClient.from_env",
                    return_value=MagicMock(has_token=True),
                ),
                patch(
                    "specify_cli.widen.check_prereqs",
                    return_value=prereq_ok,
                ),
                patch(
                    "specify_cli.widen.flow.WidenFlow",
                    return_value=mock_flow,
                ),
                patch(
                    "specify_cli.widen.state.WidenPendingStore",
                ) as mock_store_cls,
            ):
                mock_store_inst = MagicMock()
                mock_store_inst.list_pending.return_value = []
                mock_store_cls.return_value = mock_store_inst

                result = runner.invoke(
                    _app,
                    ["--mission", MISSION_SLUG],
                    input=inputs,
                    catch_exceptions=False,
                )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        mock_flow.run_widen_mode.assert_called_once()
        assert "Resolved locally" in result.output
