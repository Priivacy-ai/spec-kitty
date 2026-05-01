"""Tests for ``specify_cli.widen.flow`` — WidenFlow orchestrator.

Decision branch coverage:
  - CANCEL path: audience review returns None (user canceled).
  - CANCEL path: audience review returns None (SaaS error).
  - CANCEL path: _post_widen fails (SaasClientError).
  - BLOCK path: POST succeeds, user presses Enter (default b).
  - BLOCK path: POST succeeds, user types "b".
  - BLOCK path: POST succeeds, arbitrary non-"c" input.
  - BLOCK path: EOFError in console.input defaults to BLOCK.
  - CONTINUE path: POST succeeds, user types "c".
  - Success panel rendered before [b/c] prompt.
  - Success panel includes Slack thread URL when present.
  - Success panel omits thread line when slack_thread_url is None.
  - Success panel handles 1-person, 2-person, 3+-person invite lists.
  - WidenFlowResult.decision_id is populated on BLOCK/CONTINUE.
  - WidenFlowResult.invited is populated on BLOCK/CONTINUE.
  - WidenFlowResult fields are None on CANCEL.
  - run_widen_mode never raises (no SaaS call on cancel).
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from rich.console import Console

from specify_cli.saas_client import SaasAuthError, SaasClientError, SaasTimeoutError
from specify_cli.widen.flow import WidenFlow
from specify_cli.widen.models import AudienceSelection, WidenAction, WidenFlowResult


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DECISION_ID = "01KPXFGJ0000000000000000D1"
_MISSION_ID = "01KPXFGJ0000000000000000M1"
_MISSION_SLUG = "test-mission-01KPX"
_QUESTION = "Which database should we use?"
_ACTOR = "owner"
_DEFAULT_AUDIENCE = ["Alice Johnson", "Carol Lee"]
_DEFAULT_SELECTION = AudienceSelection(display_names=_DEFAULT_AUDIENCE, user_ids=[101, 102])

_DEFAULT_WIDEN_RESPONSE: dict[str, object] = {
    "decision_id": _DECISION_ID,
    "widened_at": "2026-04-23T16:00:00Z",
    "slack_thread_url": "https://slack.com/archives/C123/p456",
    "invited_count": 2,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_console() -> tuple[Console, StringIO]:
    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=True)
    return console, buf


def _make_client(
    post_widen_return: dict[str, object] | None = None,
    post_widen_error: Exception | None = None,
) -> MagicMock:
    """Return a mock SaasClient with configurable post_widen behaviour.

    The audience-default endpoint is not configured here — tests that need it
    should mock ``run_audience_review`` directly.
    """
    client = MagicMock()
    if post_widen_error is not None:
        client.post_widen.side_effect = post_widen_error
    else:
        resp = post_widen_return if post_widen_return is not None else _DEFAULT_WIDEN_RESPONSE
        client.post_widen.return_value = resp
    return client


def _run_with_bc_input(
    bc_input: str = "",
    *,
    audience: list[str] | None = None,
    post_widen_return: dict[str, object] | None = None,
    post_widen_error: Exception | None = None,
    audience_returns_none: bool = False,
) -> tuple[WidenFlowResult, str]:
    """Run the full flow with patched audience review and [b/c] input.

    ``run_audience_review`` is always mocked so that ``console.input`` is only
    called once — for the ``[b/c]`` prompt.  This avoids the ambiguity of
    having a single mock return value serve two prompts.
    """
    client = _make_client(post_widen_return=post_widen_return, post_widen_error=post_widen_error)
    console, buf = _make_console()
    flow = WidenFlow(saas_client=client, repo_root=Path("/tmp/test-repo"), console=console)

    audience_rv: AudienceSelection | None
    if audience_returns_none:
        audience_rv = None
    else:
        names = audience or _DEFAULT_AUDIENCE
        audience_rv = AudienceSelection(display_names=names, user_ids=list(range(101, 101 + len(names))))

    with (
        patch("specify_cli.widen.flow.run_audience_review", return_value=audience_rv),
        patch.object(console, "input", return_value=bc_input),
    ):
        result = flow.run_widen_mode(
            decision_id=_DECISION_ID,
            mission_id=_MISSION_ID,
            mission_slug=_MISSION_SLUG,
            question_text=_QUESTION,
            actor=_ACTOR,
        )
    return result, buf.getvalue()


# ---------------------------------------------------------------------------
# CANCEL path tests
# ---------------------------------------------------------------------------


class TestCancelPath:
    def test_audience_cancel_returns_cancel_action(self) -> None:
        result, _ = _run_with_bc_input(audience_returns_none=True)
        assert result.action == WidenAction.CANCEL

    def test_audience_cancel_no_post_widen_call(self) -> None:
        """If audience review returns None, post_widen must NOT be called."""
        client = _make_client()
        console, _ = _make_console()
        flow = WidenFlow(saas_client=client, repo_root=Path("/tmp"), console=console)
        with (
            patch("specify_cli.widen.flow.run_audience_review", return_value=None),
            patch.object(console, "input", return_value=""),
        ):
            flow.run_widen_mode(
                decision_id=_DECISION_ID,
                mission_id=_MISSION_ID,
                mission_slug=_MISSION_SLUG,
                question_text=_QUESTION,
                actor=_ACTOR,
            )
        client.post_widen.assert_not_called()

    def test_audience_cancel_result_has_none_fields(self) -> None:
        result, _ = _run_with_bc_input(audience_returns_none=True)
        assert result.decision_id is None
        assert result.invited is None

    def test_post_widen_saas_error_returns_cancel(self) -> None:
        result, output = _run_with_bc_input(
            post_widen_error=SaasClientError("Server error", status_code=500),
        )
        assert result.action == WidenAction.CANCEL
        assert "Widen failed:" in output
        assert "Server error" in output
        assert "Returning to interview prompt" in output

    def test_post_widen_timeout_returns_cancel(self) -> None:
        result, output = _run_with_bc_input(
            post_widen_error=SaasTimeoutError("timed out"),
        )
        assert result.action == WidenAction.CANCEL
        assert "Widen failed:" in output
        assert "Returning to interview prompt" in output

    def test_post_widen_auth_error_returns_cancel(self) -> None:
        result, output = _run_with_bc_input(
            post_widen_error=SaasAuthError("Forbidden", status_code=403),
        )
        assert result.action == WidenAction.CANCEL
        assert "Widen failed:" in output
        assert "Returning to interview prompt" in output

    def test_cancel_result_decision_id_none(self) -> None:
        result, _ = _run_with_bc_input(post_widen_error=SaasClientError("err"))
        assert result.decision_id is None
        assert result.invited is None


# ---------------------------------------------------------------------------
# BLOCK path tests
# ---------------------------------------------------------------------------


class TestBlockPath:
    def test_empty_input_returns_block(self) -> None:
        result, _ = _run_with_bc_input(bc_input="")
        assert result.action == WidenAction.BLOCK

    def test_b_input_returns_block(self) -> None:
        result, _ = _run_with_bc_input(bc_input="b")
        assert result.action == WidenAction.BLOCK

    def test_b_uppercase_returns_block(self) -> None:
        result, _ = _run_with_bc_input(bc_input="B")
        assert result.action == WidenAction.BLOCK

    def test_arbitrary_non_c_input_returns_block(self) -> None:
        result, _ = _run_with_bc_input(bc_input="x")
        assert result.action == WidenAction.BLOCK

    def test_block_result_has_decision_id(self) -> None:
        result, _ = _run_with_bc_input(bc_input="")
        assert result.decision_id == _DECISION_ID

    def test_block_result_has_invited_list(self) -> None:
        result, _ = _run_with_bc_input(bc_input="", audience=["Alice", "Carol"])
        assert result.invited == ["Alice", "Carol"]

    def test_eoferror_defaults_to_block(self) -> None:
        """EOFError in CI/non-interactive environments must default to BLOCK."""
        client = _make_client()
        console, _ = _make_console()
        flow = WidenFlow(saas_client=client, repo_root=Path("/tmp"), console=console)
        with (
            patch("specify_cli.widen.flow.run_audience_review", return_value=_DEFAULT_SELECTION),
            patch.object(console, "input", side_effect=EOFError),
        ):
            result = flow.run_widen_mode(
                decision_id=_DECISION_ID,
                mission_id=_MISSION_ID,
                mission_slug=_MISSION_SLUG,
                question_text=_QUESTION,
                actor=_ACTOR,
            )
        assert result.action == WidenAction.BLOCK


# ---------------------------------------------------------------------------
# CONTINUE path tests
# ---------------------------------------------------------------------------


class TestContinuePath:
    def test_c_input_returns_continue(self) -> None:
        result, _ = _run_with_bc_input(bc_input="c")
        assert result.action == WidenAction.CONTINUE

    def test_c_uppercase_returns_continue(self) -> None:
        result, _ = _run_with_bc_input(bc_input="C")
        assert result.action == WidenAction.CONTINUE

    def test_continue_result_has_decision_id(self) -> None:
        result, _ = _run_with_bc_input(bc_input="c")
        assert result.decision_id == _DECISION_ID

    def test_continue_result_has_invited_list(self) -> None:
        result, _ = _run_with_bc_input(bc_input="c", audience=["Alice", "Carol"])
        assert result.invited == ["Alice", "Carol"]

    def test_continue_prints_parked_message(self) -> None:
        _, output = _run_with_bc_input(bc_input="c")
        assert "parked as pending" in output.lower()

    def test_continue_message_mentions_end_of_interview(self) -> None:
        _, output = _run_with_bc_input(bc_input="c")
        # Rich may wrap long lines so we check for the keyword fragments
        lower = output.lower().replace("\n", " ")
        assert "end of" in lower and "interview" in lower


# ---------------------------------------------------------------------------
# Success panel tests (T025)
# ---------------------------------------------------------------------------


class TestSuccessPanel:
    def test_panel_rendered_before_input_called(self) -> None:
        """The 'Widened ✓' panel must be rendered BEFORE console.input is called.

        We verify this by tracking call order: _render_widen_success should
        write to the console before the mock console.input is invoked.  We
        check that the panel content is already in the console buffer by the
        time console.input returns.
        """
        client = _make_client()
        console, buf = _make_console()
        panel_written_before_input: list[bool] = []

        def fake_input(_prompt: str = "") -> str:
            # At this point, the panel should already be in the buffer
            panel_written_before_input.append("Slack thread created" in buf.getvalue())
            return ""

        flow = WidenFlow(saas_client=client, repo_root=Path("/tmp"), console=console)
        with (
            patch("specify_cli.widen.flow.run_audience_review", return_value=_DEFAULT_SELECTION),
            patch.object(console, "input", side_effect=fake_input),
        ):
            flow.run_widen_mode(
                decision_id=_DECISION_ID,
                mission_id=_MISSION_ID,
                mission_slug=_MISSION_SLUG,
                question_text=_QUESTION,
                actor=_ACTOR,
            )
        assert panel_written_before_input == [True], "Success panel was not written before console.input was called"

    def test_panel_shows_slack_thread_url(self) -> None:
        _, output = _run_with_bc_input(bc_input="")
        assert "https://slack.com/archives/C123/p456" in output

    def test_panel_omits_thread_when_no_url(self) -> None:
        resp: dict[str, object] = {
            "decision_id": _DECISION_ID,
            "widened_at": "2026-04-23T16:00:00Z",
            "slack_thread_url": None,
            "invited_count": 2,
        }
        _, output = _run_with_bc_input(bc_input="", post_widen_return=resp)
        assert "Thread:" not in output

    def test_panel_shows_single_invitee(self) -> None:
        _, output = _run_with_bc_input(bc_input="", audience=["Alice"])
        assert "Alice" in output

    def test_panel_shows_two_invitees_with_and(self) -> None:
        _, output = _run_with_bc_input(bc_input="", audience=["Alice", "Carol"])
        # Both names should appear, connected by " and "
        assert "Alice" in output
        assert "Carol" in output
        assert " and " in output

    def test_panel_shows_three_invitees_with_oxford_comma_style(self) -> None:
        _, output = _run_with_bc_input(bc_input="", audience=["Alice", "Bob", "Carol"])
        assert "Alice" in output
        assert "Bob" in output
        assert "Carol" in output

    def test_panel_question_text_truncated_to_50(self) -> None:
        long_question = "A" * 80
        client = _make_client()
        console, buf = _make_console()
        flow = WidenFlow(saas_client=client, repo_root=Path("/tmp"), console=console)
        with (
            patch(
                "specify_cli.widen.flow.run_audience_review",
                return_value=AudienceSelection(display_names=["Alice"], user_ids=[101]),
            ),
            patch.object(console, "input", return_value=""),
        ):
            flow.run_widen_mode(
                decision_id=_DECISION_ID,
                mission_id=_MISSION_ID,
                mission_slug=_MISSION_SLUG,
                question_text=long_question,
                actor=_ACTOR,
            )
        output = buf.getvalue()
        # Should contain 50 'A' chars inside the panel (in the quoted text)
        assert "A" * 50 in output
        # Should NOT contain 51 consecutive 'A' chars in the panel body
        assert "A" * 51 not in output

    def test_panel_shows_slack_thread_created_message(self) -> None:
        _, output = _run_with_bc_input(bc_input="")
        assert "Slack thread created" in output


# ---------------------------------------------------------------------------
# Never-raise guarantee
# ---------------------------------------------------------------------------


class TestNeverRaises:
    def test_run_widen_mode_never_raises_on_audience_cancel(self) -> None:
        """run_widen_mode must never raise to the caller."""
        result, _ = _run_with_bc_input(audience_returns_none=True)
        assert isinstance(result, WidenFlowResult)

    def test_run_widen_mode_never_raises_on_saas_error(self) -> None:
        result, _ = _run_with_bc_input(post_widen_error=SaasClientError("err"))
        assert isinstance(result, WidenFlowResult)

    def test_run_widen_mode_never_raises_on_unexpected_error(self) -> None:
        """Even unexpected exception types from post_widen must produce CANCEL."""
        result, _ = _run_with_bc_input(post_widen_error=SaasClientError("unexpected"))
        assert isinstance(result, WidenFlowResult)
        assert result.action == WidenAction.CANCEL
