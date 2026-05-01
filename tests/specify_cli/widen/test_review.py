"""Tests for specify_cli.widen.review — run_candidate_review and helpers.

Coverage:
- _emit_summarization_request: §5.1 format substrings, participants, truncation
- _read_llm_response: valid JSON, parse failure, timeout
- _parse_candidate: valid raw dict, bad source_hint, missing keys
- _make_fallback_candidate: always llm_timed_out=True, MANUAL source
- _determine_source: MANUAL on empty candidate, MANUAL on blank edit,
    MISSION_OWNER_OVERRIDE on >30% change, SLACK_EXTRACTION on minor change
- _handle_accept: calls dm_service.resolve_decision, prints resolved
- _handle_edit: editor used, minor edit → SLACK_EXTRACTION, major → OVERRIDE
- _handle_edit: None from click.edit falls back to original text
- _handle_defer: calls dm_service.defer_decision, prints deferred, default rationale
- run_candidate_review: accept path returns CandidateReview
- run_candidate_review: edit path returns CandidateReview
- run_candidate_review: defer path returns CandidateReview
- run_candidate_review: KeyboardInterrupt at prompt → None
- run_candidate_review: EOFError at prompt → None
- run_candidate_review: LLM timeout → fallback path, renders §5.3 message
- run_candidate_review: invalid choice re-prompts before accepting valid choice
- run_candidate_review: LLM timeout + accept empty
- run_candidate_review: LLM parse failure (malformed JSON) → fallback
- _read_llm_response: multi-line JSON spread across multiple reads
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from rich.console import Console

from specify_cli.widen.models import CandidateReview, DiscussionFetch, SummarySource
from specify_cli.widen.review import (
    _determine_source,
    _emit_summarization_request,
    _handle_accept,
    _handle_defer,
    _handle_edit,
    _make_fallback_candidate,
    _parse_candidate,
    _read_llm_response,
    run_candidate_review,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_discussion(
    participants: list[str] | None = None,
    message_count: int = 3,
    thread_url: str | None = "https://slack.com/archives/C001/p1234",
    messages: list[str] | None = None,
    truncated: bool = False,
) -> DiscussionFetch:
    return DiscussionFetch(
        participants=participants or ["Alice", "Bob"],
        message_count=message_count,
        thread_url=thread_url,
        messages=messages or ["[Alice] Hello", "[Bob] World", "[Alice] OK"],
        truncated=truncated,
    )


def _console_with_capture() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    console = Console(file=buf, highlight=False, markup=True)
    return console, buf


def make_dm_service() -> MagicMock:
    svc = MagicMock()
    svc.resolve_decision.return_value = MagicMock()
    svc.defer_decision.return_value = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# _emit_summarization_request
# ---------------------------------------------------------------------------


class TestEmitSummarizationRequest:
    def test_header_contains_decision_id(self) -> None:
        console, buf = _console_with_capture()
        discussion = make_discussion()
        _emit_summarization_request("DEC001", "What database?", discussion, console)
        output = buf.getvalue()
        assert "WIDEN SUMMARIZATION REQUEST" in output
        assert "DEC001" in output

    def test_header_contains_question(self) -> None:
        console, buf = _console_with_capture()
        discussion = make_discussion()
        _emit_summarization_request("DEC001", "What database?", discussion, console)
        output = buf.getvalue()
        assert "What database?" in output

    def test_participants_listed(self) -> None:
        console, buf = _console_with_capture()
        discussion = make_discussion(participants=["Alice Johnson", "Carol Lee"])
        _emit_summarization_request("DEC001", "Q?", discussion, console)
        output = buf.getvalue()
        assert "Alice Johnson" in output
        assert "Carol Lee" in output

    def test_message_count_shown(self) -> None:
        console, buf = _console_with_capture()
        discussion = make_discussion(message_count=7)
        _emit_summarization_request("DEC001", "Q?", discussion, console)
        output = buf.getvalue()
        assert "7" in output

    def test_thread_url_shown(self) -> None:
        console, buf = _console_with_capture()
        discussion = make_discussion(thread_url="https://slack.com/xyz")
        _emit_summarization_request("DEC001", "Q?", discussion, console)
        output = buf.getvalue()
        assert "https://slack.com/xyz" in output

    def test_no_thread_url_shows_unavailable(self) -> None:
        console, buf = _console_with_capture()
        discussion = make_discussion(thread_url=None)
        _emit_summarization_request("DEC001", "Q?", discussion, console)
        output = buf.getvalue()
        assert "unavailable" in output

    def test_messages_rendered(self) -> None:
        console, buf = _console_with_capture()
        discussion = make_discussion(messages=["[Alice] First message"])
        _emit_summarization_request("DEC001", "Q?", discussion, console)
        output = buf.getvalue()
        assert "[Alice] First message" in output

    def test_truncation_notice_when_truncated(self) -> None:
        msgs = [f"[Alice] msg {i}" for i in range(55)]
        console, buf = _console_with_capture()
        discussion = DiscussionFetch(
            participants=["Alice"],
            message_count=55,
            thread_url=None,
            messages=msgs,
            truncated=True,
        )
        _emit_summarization_request("DEC001", "Q?", discussion, console)
        output = buf.getvalue()
        assert "truncated" in output

    def test_json_response_block_shown(self) -> None:
        console, buf = _console_with_capture()
        discussion = make_discussion()
        _emit_summarization_request("DEC001", "Q?", discussion, console)
        output = buf.getvalue()
        assert "candidate_summary" in output
        assert "candidate_answer" in output
        assert "source_hint" in output


# ---------------------------------------------------------------------------
# _read_llm_response
# ---------------------------------------------------------------------------


class TestReadLlmResponse:
    def test_valid_json_parsed(self) -> None:
        payload = json.dumps(
            {
                "candidate_summary": "Team chose Postgres",
                "candidate_answer": "PostgreSQL",
                "source_hint": "slack_extraction",
            }
        )
        stdin = io.StringIO(payload + "\n")
        result = _read_llm_response(timeout=1.0, _stdin=stdin)
        assert result is not None
        assert result["candidate_answer"] == "PostgreSQL"

    def test_json_embedded_in_prose(self) -> None:
        payload = (
            'Here is the output:\n'
            '{"candidate_summary":"S","candidate_answer":"A","source_hint":"slack_extraction"}\n'
            'End.\n'
        )
        stdin = io.StringIO(payload)
        result = _read_llm_response(timeout=1.0, _stdin=stdin)
        assert result is not None
        assert result["candidate_summary"] == "S"

    def test_malformed_json_returns_none(self) -> None:
        stdin = io.StringIO("{not: valid json}\n")
        result = _read_llm_response(timeout=1.0, _stdin=stdin)
        assert result is None

    def test_empty_stdin_returns_none(self) -> None:
        stdin = io.StringIO("")
        result = _read_llm_response(timeout=0.05, _stdin=stdin)
        assert result is None

    def test_multiline_json(self) -> None:
        payload = (
            '{\n'
            '  "candidate_summary": "Multi-line",\n'
            '  "candidate_answer": "Yes",\n'
            '  "source_hint": "slack_extraction"\n'
            '}\n'
        )
        stdin = io.StringIO(payload)
        result = _read_llm_response(timeout=1.0, _stdin=stdin)
        assert result is not None
        assert result["candidate_answer"] == "Yes"


# ---------------------------------------------------------------------------
# _parse_candidate
# ---------------------------------------------------------------------------


class TestParseCandidate:
    def test_valid_dict(self) -> None:
        raw = {
            "candidate_summary": "Postgres it is",
            "candidate_answer": "PostgreSQL",
            "source_hint": "slack_extraction",
        }
        discussion = make_discussion()
        result = _parse_candidate(raw, "D01", discussion)
        assert result.candidate_answer == "PostgreSQL"
        assert result.source_hint == SummarySource.SLACK_EXTRACTION
        assert result.llm_timed_out is False

    def test_bad_source_hint_defaults_to_slack_extraction(self) -> None:
        raw = {
            "candidate_summary": "S",
            "candidate_answer": "A",
            "source_hint": "unknown_value",
        }
        discussion = make_discussion()
        result = _parse_candidate(raw, "D01", discussion)
        assert result.source_hint == SummarySource.SLACK_EXTRACTION

    def test_missing_keys_use_empty_strings(self) -> None:
        discussion = make_discussion()
        result = _parse_candidate({}, "D01", discussion)
        assert result.candidate_summary == ""
        assert result.candidate_answer == ""


# ---------------------------------------------------------------------------
# _make_fallback_candidate
# ---------------------------------------------------------------------------


class TestMakeFallbackCandidate:
    def test_fallback_is_manual_and_timed_out(self) -> None:
        discussion = make_discussion()
        result = _make_fallback_candidate("D01", discussion)
        assert result.llm_timed_out is True
        assert result.source_hint == SummarySource.MANUAL
        assert result.candidate_answer == ""
        assert result.candidate_summary == ""


# ---------------------------------------------------------------------------
# _determine_source  (T039)
# ---------------------------------------------------------------------------


class TestDetermineSource:
    def test_empty_candidate_returns_manual(self) -> None:
        assert _determine_source("", "Some answer") == SummarySource.MANUAL

    def test_blank_edit_returns_manual(self) -> None:
        assert _determine_source("PostgreSQL", "   ") == SummarySource.MANUAL

    def test_empty_edit_returns_manual(self) -> None:
        assert _determine_source("PostgreSQL", "") == SummarySource.MANUAL

    def test_identical_edit_returns_slack_extraction(self) -> None:
        assert _determine_source("PostgreSQL.", "PostgreSQL.") == SummarySource.SLACK_EXTRACTION

    def test_minor_edit_returns_slack_extraction(self) -> None:
        # Tiny punctuation fix — well under 30%
        assert _determine_source("PostgreSQL", "PostgreSQL.") == SummarySource.SLACK_EXTRACTION

    def test_major_edit_returns_override(self) -> None:
        # Completely different answer — >30% edit distance
        assert (
            _determine_source("PostgreSQL.", "PostgreSQL with replicas.")
            == SummarySource.MISSION_OWNER_OVERRIDE
        )

    def test_complete_rewrite_returns_override(self) -> None:
        assert (
            _determine_source("Use PostgreSQL", "Actually use MySQL for legacy reasons")
            == SummarySource.MISSION_OWNER_OVERRIDE
        )

    def test_whitespace_only_candidate_returns_manual(self) -> None:
        assert _determine_source("   ", "Some answer") == SummarySource.MANUAL


# ---------------------------------------------------------------------------
# _handle_accept  (T036)
# ---------------------------------------------------------------------------


class TestHandleAccept:
    def test_calls_resolve_decision(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        _handle_accept(candidate, "my-mission", Path("/repo"), svc, "tester", console)
        svc.resolve_decision.assert_called_once()
        kwargs = svc.resolve_decision.call_args.kwargs
        assert kwargs["final_answer"] == "PostgreSQL"
        assert kwargs["decision_id"] == "D01"
        assert kwargs["summary_json"] == {"text": "S", "source": "slack_extraction"}

    def test_accept_persists_slack_extraction_provenance(self) -> None:
        """_handle_accept always uses SLACK_EXTRACTION as source (C-005)."""
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D02",
            discussion_fetch=discussion,
            candidate_summary="The team agreed on Postgres",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        _handle_accept(candidate, "my-mission", Path("/repo"), svc, "tester", console)
        kwargs = svc.resolve_decision.call_args.kwargs
        assert kwargs["summary_json"]["source"] == SummarySource.SLACK_EXTRACTION.value
        assert kwargs["summary_json"]["text"] == "The team agreed on Postgres"

    def test_prints_resolved(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="Ans",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        _handle_accept(candidate, "m", Path("/r"), svc, "actor", console)
        assert "resolved" in buf.getvalue().lower()

    def test_decision_error_surfaces_clear_message_and_returns_false(self) -> None:
        """DecisionError must print a visible error and return False (not silently suppress)."""
        from specify_cli.decisions.models import DecisionErrorCode
        from specify_cli.decisions.service import DecisionError

        console, buf = _console_with_capture()
        svc = make_dm_service()
        svc.resolve_decision.side_effect = DecisionError(
            code=DecisionErrorCode.TERMINAL_CONFLICT
        )
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="",
            candidate_answer="A",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        # Should not raise; must return False
        result = _handle_accept(candidate, "m", Path("/r"), svc, "actor", console)
        assert result is False
        # Must NOT print the false-positive "Decision resolved." message
        assert "resolved" not in buf.getvalue().lower()

    def test_accept_returns_true_on_success(self) -> None:
        """_handle_accept returns True when resolve_decision succeeds."""
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        result = _handle_accept(candidate, "m", Path("/r"), svc, "actor", console)
        assert result is True


# ---------------------------------------------------------------------------
# _handle_edit  (T037)
# ---------------------------------------------------------------------------


class TestHandleEdit:
    def test_minor_edit_uses_slack_extraction(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        # click.edit returns same text (minor edit)
        with patch("specify_cli.widen.review.click.edit", return_value="PostgreSQL."):
            _handle_edit(candidate, "m", Path("/r"), svc, "actor", console)
        svc.resolve_decision.assert_called_once()
        assert "resolved" in buf.getvalue().lower()
        kwargs = svc.resolve_decision.call_args.kwargs
        assert kwargs["summary_json"] == {"text": "S", "source": "slack_extraction"}

    def test_major_edit_prompts_rationale(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        with (
            patch("specify_cli.widen.review.click.edit", return_value="MySQL for legacy reasons"),
            patch.object(console, "input", return_value="team decision"),
        ):
            _handle_edit(candidate, "m", Path("/r"), svc, "actor", console)
        kwargs = svc.resolve_decision.call_args.kwargs
        assert kwargs["rationale"] == "team decision"
        assert kwargs["summary_json"]["source"] == SummarySource.MISSION_OWNER_OVERRIDE.value

    def test_major_edit_persists_mission_owner_override_provenance(self) -> None:
        """Material edit (>30% change) → source=mission_owner_override (C-005)."""
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D03",
            discussion_fetch=discussion,
            candidate_summary="Team summary",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        with (
            patch("specify_cli.widen.review.click.edit", return_value="MySQL for legacy reasons"),
            patch.object(console, "input", return_value=""),
        ):
            _handle_edit(candidate, "m", Path("/r"), svc, "actor", console)
        kwargs = svc.resolve_decision.call_args.kwargs
        assert kwargs["summary_json"]["source"] == SummarySource.MISSION_OWNER_OVERRIDE.value
        assert kwargs["summary_json"]["text"] == "Team summary"

    def test_manual_source_persisted_when_candidate_is_blank(self) -> None:
        """When the original candidate_answer is blank, source=manual (C-005).

        _determine_source returns MANUAL when candidate_answer.strip() is empty.
        click.edit returns None → edited falls back to prefill (empty), so
        _determine_source("", "") → MANUAL.
        """
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D04",
            discussion_fetch=discussion,
            candidate_summary="Summary",
            candidate_answer="",  # blank candidate → MANUAL
            source_hint=SummarySource.MANUAL,
        )
        # click.edit returns None (no change); edited falls back to prefill=""
        with (
            patch("specify_cli.widen.review.click.edit", return_value=None),
            patch.object(console, "input", return_value=""),
        ):
            _handle_edit(candidate, "m", Path("/r"), svc, "actor", console)
        kwargs = svc.resolve_decision.call_args.kwargs
        assert kwargs["summary_json"]["source"] == SummarySource.MANUAL.value

    def test_none_from_editor_falls_back_to_original(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        # click.edit returns None (no $EDITOR set)
        with patch("specify_cli.widen.review.click.edit", return_value=None):
            _handle_edit(candidate, "m", Path("/r"), svc, "actor", console)
        kwargs = svc.resolve_decision.call_args.kwargs
        assert kwargs["final_answer"] == "PostgreSQL"

    def test_keyboard_interrupt_at_rationale_prompt(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        with (
            patch("specify_cli.widen.review.click.edit", return_value="Completely different answer here"),
            patch.object(console, "input", side_effect=KeyboardInterrupt),
        ):
            _handle_edit(candidate, "m", Path("/r"), svc, "actor", console)
        # Should still resolve (with rationale=None)
        svc.resolve_decision.assert_called_once()

    def test_decision_error_surfaces_clear_message_and_returns_false(self) -> None:
        """DecisionError on resolve must print a visible error and return False."""
        from specify_cli.decisions.models import DecisionErrorCode
        from specify_cli.decisions.service import DecisionError

        console, buf = _console_with_capture()
        svc = make_dm_service()
        svc.resolve_decision.side_effect = DecisionError(
            code=DecisionErrorCode.TERMINAL_CONFLICT
        )
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        with patch("specify_cli.widen.review.click.edit", return_value="PostgreSQL."):
            result = _handle_edit(candidate, "m", Path("/r"), svc, "actor", console)
        assert result is False
        # Must NOT print the false-positive "Decision resolved." message
        assert "resolved" not in buf.getvalue().lower()

    def test_edit_returns_true_on_success(self) -> None:
        """_handle_edit returns True when resolve_decision succeeds."""
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="PostgreSQL",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        with patch("specify_cli.widen.review.click.edit", return_value="PostgreSQL."):
            result = _handle_edit(candidate, "m", Path("/r"), svc, "actor", console)
        assert result is True


# ---------------------------------------------------------------------------
# _handle_defer  (T038)
# ---------------------------------------------------------------------------


class TestHandleDefer:
    def test_calls_defer_decision(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="S",
            candidate_answer="A",
            source_hint=SummarySource.SLACK_EXTRACTION,
        )
        with patch.object(console, "input", return_value="waiting for team"):
            _handle_defer(candidate, "m", Path("/r"), svc, "actor", console)
        svc.defer_decision.assert_called_once()
        kwargs = svc.defer_decision.call_args.kwargs
        assert kwargs["rationale"] == "waiting for team"

    def test_default_rationale_on_keyboard_interrupt(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="",
            candidate_answer="",
            source_hint=SummarySource.MANUAL,
        )
        with patch.object(console, "input", side_effect=KeyboardInterrupt):
            _handle_defer(candidate, "m", Path("/r"), svc, "actor", console)
        kwargs = svc.defer_decision.call_args.kwargs
        assert "deferred" in kwargs["rationale"]

    def test_prints_deferred(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()
        candidate = CandidateReview(
            decision_id="D01",
            discussion_fetch=discussion,
            candidate_summary="",
            candidate_answer="",
            source_hint=SummarySource.MANUAL,
        )
        with patch.object(console, "input", return_value="will decide later"):
            _handle_defer(candidate, "m", Path("/r"), svc, "actor", console)
        assert "deferred" in buf.getvalue().lower()


# ---------------------------------------------------------------------------
# run_candidate_review (T035 integration)
# ---------------------------------------------------------------------------


def _run_review_with_responses(
    llm_response_dict: dict | None,
    user_choice: str,
    extra_inputs: list[str] | None = None,
) -> tuple[CandidateReview | None, str]:
    """Helper: fake stdin for LLM + Console input for user interaction."""
    console, buf = _console_with_capture()
    svc = make_dm_service()
    discussion = make_discussion()

    all_inputs = [user_choice] + (extra_inputs or [])
    input_iter = iter(all_inputs)

    def fake_input(_prompt: str = "") -> str:
        try:
            return next(input_iter)
        except StopIteration:
            raise EOFError("no more inputs") from None

    with (
        patch.object(console, "input", side_effect=fake_input),
        patch("specify_cli.widen.review._read_llm_response", return_value=llm_response_dict),
    ):
        result = run_candidate_review(
            discussion_data=discussion,
            decision_id="D01",
            question_text="Which database?",
            mission_slug="test-mission",
            repo_root=Path("/fake/repo"),
            console=console,
            dm_service=svc,
            actor="tester",
        )

    return result, buf.getvalue()


class TestRunCandidateReview:
    def test_accept_path_returns_candidate_review(self) -> None:
        llm_payload = {
            "candidate_summary": "Team chose Postgres",
            "candidate_answer": "PostgreSQL",
            "source_hint": "slack_extraction",
        }
        result, output = _run_review_with_responses(llm_payload, "a")
        assert isinstance(result, CandidateReview)
        assert result.candidate_answer == "PostgreSQL"

    def test_defer_path_returns_candidate_review(self) -> None:
        llm_payload = {
            "candidate_summary": "S",
            "candidate_answer": "A",
            "source_hint": "slack_extraction",
        }
        result, output = _run_review_with_responses(llm_payload, "d", extra_inputs=["need more info"])
        assert isinstance(result, CandidateReview)

    def test_edit_path_returns_candidate_review(self) -> None:
        llm_payload = {
            "candidate_summary": "S",
            "candidate_answer": "A",
            "source_hint": "slack_extraction",
        }
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()

        with (
            patch.object(console, "input", return_value="e"),
            patch("specify_cli.widen.review._read_llm_response", return_value=llm_payload),
            patch("specify_cli.widen.review.click.edit", return_value="A edited"),
        ):
            result = run_candidate_review(
                discussion_data=discussion,
                decision_id="D01",
                question_text="Q?",
                mission_slug="m",
                repo_root=Path("/r"),
                console=console,
                dm_service=svc,
                actor="actor",
            )
        assert isinstance(result, CandidateReview)

    def test_keyboard_interrupt_at_prompt_returns_none(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()

        with (
            patch.object(console, "input", side_effect=KeyboardInterrupt),
            patch("specify_cli.widen.review._read_llm_response", return_value=None),
        ):
            result = run_candidate_review(
                discussion_data=discussion,
                decision_id="D01",
                question_text="Q?",
                mission_slug="m",
                repo_root=Path("/r"),
                console=console,
                dm_service=svc,
                actor="actor",
            )
        assert result is None

    def test_eof_error_at_prompt_returns_none(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()

        with (
            patch.object(console, "input", side_effect=EOFError),
            patch("specify_cli.widen.review._read_llm_response", return_value=None),
        ):
            result = run_candidate_review(
                discussion_data=discussion,
                decision_id="D01",
                question_text="Q?",
                mission_slug="m",
                repo_root=Path("/r"),
                console=console,
                dm_service=svc,
                actor="actor",
            )
        assert result is None

    def test_llm_timeout_renders_fallback_message(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()

        inputs = iter(["a"])

        def fake_input(_prompt: str = "") -> str:
            return next(inputs)

        with (
            patch.object(console, "input", side_effect=fake_input),
            patch("specify_cli.widen.review._read_llm_response", return_value=None),
        ):
            result = run_candidate_review(
                discussion_data=discussion,
                decision_id="D01",
                question_text="Q?",
                mission_slug="m",
                repo_root=Path("/r"),
                console=console,
                dm_service=svc,
                actor="actor",
            )
        output = buf.getvalue()
        assert "timed out" in output.lower() or "invalid" in output.lower()
        assert isinstance(result, CandidateReview)
        assert result.llm_timed_out is True

    def test_invalid_choice_reprompts(self) -> None:
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()

        # First input is invalid, second is valid
        choices = iter(["x", "a"])

        def fake_input(_prompt: str = "") -> str:
            return next(choices)

        llm_payload = {"candidate_summary": "S", "candidate_answer": "A", "source_hint": "slack_extraction"}
        with (
            patch.object(console, "input", side_effect=fake_input),
            patch("specify_cli.widen.review._read_llm_response", return_value=llm_payload),
        ):
            result = run_candidate_review(
                discussion_data=discussion,
                decision_id="D01",
                question_text="Q?",
                mission_slug="m",
                repo_root=Path("/r"),
                console=console,
                dm_service=svc,
                actor="actor",
            )
        assert isinstance(result, CandidateReview)
        assert "Invalid choice" in buf.getvalue()

    def test_llm_timeout_accept_empty(self) -> None:
        """Timeout path + accept empty still resolves (§5.3 accept empty)."""
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()

        inputs = iter(["a"])

        def fake_input(_prompt: str = "") -> str:
            return next(inputs)

        with (
            patch.object(console, "input", side_effect=fake_input),
            patch("specify_cli.widen.review._read_llm_response", return_value=None),
        ):
            result = run_candidate_review(
                discussion_data=discussion,
                decision_id="D01",
                question_text="Q?",
                mission_slug="m",
                repo_root=Path("/r"),
                console=console,
                dm_service=svc,
                actor="actor",
            )
        assert result is not None
        assert result.llm_timed_out is True
        svc.resolve_decision.assert_called_once()

    def test_panel_shows_question_and_answer(self) -> None:
        """Candidate panel includes question text and proposed answer (§6)."""
        console, buf = _console_with_capture()
        svc = make_dm_service()
        discussion = make_discussion()

        inputs = iter(["a"])

        def fake_input(_prompt: str = "") -> str:
            return next(inputs)

        llm_payload = {
            "candidate_summary": "Great summary",
            "candidate_answer": "The answer",
            "source_hint": "slack_extraction",
        }

        with (
            patch.object(console, "input", side_effect=fake_input),
            patch("specify_cli.widen.review._read_llm_response", return_value=llm_payload),
        ):
            run_candidate_review(
                discussion_data=discussion,
                decision_id="D01",
                question_text="Which database?",
                mission_slug="m",
                repo_root=Path("/r"),
                console=console,
                dm_service=svc,
                actor="actor",
            )
        output = buf.getvalue()
        assert "Which database?" in output
        assert "The answer" in output
        assert "Great summary" in output
