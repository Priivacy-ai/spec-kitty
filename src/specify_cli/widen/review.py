"""Candidate review step for Widen Mode.

Implements ``run_candidate_review()`` — the function that:
1. Emits a structured WIDEN SUMMARIZATION REQUEST block to stdout (§5.1 contract).
2. Reads the active LLM session's JSON response from stdin within a timeout (§5.2).
3. Parses the response into a ``CandidateReview`` model.
4. Renders a ``rich.Panel`` showing the question, candidate summary, and proposed answer (§6).
5. Handles ``[a]ccept`` / ``[e]dit`` / ``[d]efer`` (§6.1–6.3).
6. Falls back to a blank-candidate path on LLM timeout or parse failure (§5.3).

Prompt-contract model (R-7):
    The CLI is a subprocess of the active LLM session.  Printing to stdout
    causes the LLM to read the instruction block as tool output and respond on
    stdin.  No API calls are made; this is the natural I/O channel.
"""

from __future__ import annotations

import contextlib
import difflib
import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel

from specify_cli.widen.models import CandidateReview, DiscussionFetch, SummarySource

__all__ = ["run_candidate_review"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default timeout in seconds for reading the LLM JSON response from stdin.
#: Override with the ``SPEC_KITTY_WIDEN_SUMMARIZE_TIMEOUT`` environment variable.
SUMMARIZE_TIMEOUT: float = float(os.environ.get("SPEC_KITTY_WIDEN_SUMMARIZE_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# T033 — Emit LLM Summarization Request instruction block (§5.1)
# ---------------------------------------------------------------------------


def _emit_summarization_request(
    decision_id: str,
    question_text: str,
    discussion: DiscussionFetch,
    console: Console,
) -> None:
    """Print the §5.1 WIDEN SUMMARIZATION REQUEST block to stdout.

    The active LLM session reads this as tool output and responds with a JSON
    block containing ``candidate_summary``, ``candidate_answer``, and
    ``source_hint``.
    """
    # Box header — exactly as specified in §5.1
    header_lines = [
        "╔══════════════════════════════════════════════════════════════════╗",
        "║  WIDEN SUMMARIZATION REQUEST                                     ║",
        f"║  decision_id: {decision_id:<48}║",
        f"║  question: {question_text[:52]:<54}║",
        "╚══════════════════════════════════════════════════════════════════╝",
    ]

    participants_str = ", ".join(discussion.participants) if discussion.participants else "(none)"
    thread_url = discussion.thread_url or "unavailable"

    body_lines = [
        "",
        "[DISCUSSION DATA]",
        f"Participants: {participants_str}",
        f"Message count: {discussion.message_count}",
        f"Thread URL: {thread_url}",
        "",
        "--- Messages ---",
    ]

    messages_shown = discussion.messages[:50]
    for msg in messages_shown:
        body_lines.append(msg)

    if discussion.truncated or len(discussion.messages) > 50:
        extra = discussion.message_count - len(messages_shown)
        if extra > 0:
            body_lines.append(f"... ({extra} more messages truncated)")

    body_lines += [
        "---",
        "",
        "Based on the discussion above, please produce a candidate summary and answer.",
        "Respond with ONLY the following JSON block (no prose before or after):",
        "",
        "```json",
        "{",
        '  "candidate_summary": "<concise summary of the discussion consensus>",',
        '  "candidate_answer": "<proposed answer to the question above>",',
        '  "source_hint": "slack_extraction"',
        "}",
        "```",
    ]

    for line in header_lines + body_lines:
        console.print(line, markup=False, highlight=False)


# ---------------------------------------------------------------------------
# T034 — Read + Parse LLM JSON response (with timeout)
# ---------------------------------------------------------------------------


def _read_llm_response(
    timeout: float = SUMMARIZE_TIMEOUT,
    _stdin: Any = None,
) -> dict[str, Any] | None:
    """Read the LLM JSON response from stdin within *timeout* seconds.

    The LLM is expected to respond with a JSON object containing
    ``candidate_summary``, ``candidate_answer``, and ``source_hint``.
    JSON extraction is tolerant: the entire stdin buffer until EOF or a blank
    line is gathered, then the first ``{...}`` block is extracted.

    Args:
        timeout: Seconds to wait for stdin input.  Defaults to
            ``SUMMARIZE_TIMEOUT`` (30 s or env-overridden).
        _stdin:  Injectable stdin for testing (defaults to ``sys.stdin``).

    Returns:
        Parsed dict on success, ``None`` on timeout or parse failure.
    """
    stdin = _stdin if _stdin is not None else sys.stdin

    lines: list[str] = []
    finished = threading.Event()

    def _reader() -> None:  # pragma: no cover — thread body
        try:
            for line in stdin:
                lines.append(line)
                # Stop collecting after we see a closing brace on its own line
                stripped = line.strip()
                if stripped == "}":
                    break
        except Exception:
            pass
        finally:
            finished.set()

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if not lines:
        return None  # timeout or no data

    raw = "".join(lines).strip()
    # Extract JSON object — tolerant of surrounding fences or prose
    match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
    if not match:
        # Try a greedier match for nested-ish objects
        match = re.search(r"\{.*?\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        return dict(json.loads(match.group()))
    except (json.JSONDecodeError, ValueError):
        return None


def _parse_candidate(
    raw: dict[str, Any],
    decision_id: str,
    discussion: DiscussionFetch,
) -> CandidateReview:
    """Build a ``CandidateReview`` from a successfully-parsed LLM JSON dict."""
    source_raw = raw.get("source_hint", "slack_extraction")
    try:
        source = SummarySource(source_raw)
    except ValueError:
        source = SummarySource.SLACK_EXTRACTION

    return CandidateReview(
        decision_id=decision_id,
        discussion_fetch=discussion,
        candidate_summary=str(raw.get("candidate_summary", "")),
        candidate_answer=str(raw.get("candidate_answer", "")),
        source_hint=source,
        llm_timed_out=False,
    )


def _make_fallback_candidate(
    decision_id: str,
    discussion: DiscussionFetch,
) -> CandidateReview:
    """Return a blank ``CandidateReview`` for the timeout / parse-failure path."""
    return CandidateReview(
        decision_id=decision_id,
        discussion_fetch=discussion,
        candidate_summary="",
        candidate_answer="",
        source_hint=SummarySource.MANUAL,
        llm_timed_out=True,
    )


# ---------------------------------------------------------------------------
# T039 — Provenance assignment logic
# ---------------------------------------------------------------------------


def _determine_source(candidate_answer: str, edited_answer: str) -> SummarySource:
    """Assign ``SummarySource`` based on how the owner changed the candidate answer.

    Rules (data-model.md §4, §6.2 contract):
    - Empty candidate + non-empty edit → ``MANUAL`` (wrote from scratch).
    - Edit is empty or blank → ``MANUAL`` (deleted everything).
    - Normalised edit-distance > 30 % of candidate length → ``MISSION_OWNER_OVERRIDE``.
    - Otherwise → ``SLACK_EXTRACTION`` (minor / no change).

    Uses ``difflib.SequenceMatcher`` as a stdlib approximation to Levenshtein.
    """
    if not candidate_answer.strip():
        return SummarySource.MANUAL  # no candidate to compare against

    if not edited_answer.strip():
        return SummarySource.MANUAL  # owner deleted everything

    ratio = difflib.SequenceMatcher(None, candidate_answer, edited_answer).ratio()
    # ratio=1.0 → identical; 0.0 → completely different
    edit_distance_fraction = 1.0 - ratio
    if edit_distance_fraction > 0.30:
        return SummarySource.MISSION_OWNER_OVERRIDE

    return SummarySource.SLACK_EXTRACTION


# ---------------------------------------------------------------------------
# T036 — [a]ccept path
# ---------------------------------------------------------------------------


def _handle_accept(
    candidate: CandidateReview,
    mission_slug: str,
    repo_root: Path,
    dm_service: Any,
    actor: str,
    console: Console,
) -> bool:
    """Accept candidate answer as-is (§6.1).

    Calls ``resolve_decision`` with ``source=slack_extraction``.
    No rationale prompt per C-006.

    Returns:
        ``True`` on successful persistence; ``False`` when a
        ``DecisionError`` prevents the write-back (user is notified).
    """
    from specify_cli.decisions.service import DecisionError  # local import

    final = candidate.candidate_answer
    try:
        dm_service.resolve_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=candidate.decision_id,
            final_answer=final,
            summary_json={
                "text": candidate.candidate_summary,
                "source": SummarySource.SLACK_EXTRACTION.value,
            },
            actor=actor,
        )
    except DecisionError as exc:
        console.print(f"[red]Write-back failed: {exc}. Your answer was NOT saved.[/red]")
        return False
    console.print("[green]Decision resolved.[/green]")
    return True


# ---------------------------------------------------------------------------
# T037 — [e]dit path + material-edit detection
# ---------------------------------------------------------------------------


def _handle_edit(
    candidate: CandidateReview,
    mission_slug: str,
    repo_root: Path,
    dm_service: Any,
    actor: str,
    console: Console,
) -> bool:
    """Open ``$EDITOR`` pre-filled with candidate answer (§6.2).

    Detects material change, optionally prompts for rationale, then resolves.

    Returns:
        ``True`` on successful persistence; ``False`` when a
        ``DecisionError`` prevents the write-back (user is notified).
    """
    from specify_cli.decisions.service import DecisionError  # local import

    prefill = candidate.candidate_answer
    # click.edit returns None when no EDITOR is set or user makes no change in
    # certain environments; fall back to the original text.
    edited_raw = click.edit(text=prefill)
    edited = (edited_raw or prefill).strip()

    source = _determine_source(prefill, edited)

    rationale: str | None = None
    if source in (SummarySource.MISSION_OWNER_OVERRIDE, SummarySource.MANUAL):
        try:
            rationale = console.input("Optional rationale (press Enter to skip): ").strip() or None
        except (KeyboardInterrupt, EOFError):
            rationale = None

    final = edited if edited else prefill
    try:
        dm_service.resolve_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=candidate.decision_id,
            final_answer=final,
            summary_json={
                "text": candidate.candidate_summary,
                "source": source.value,
            },
            rationale=rationale,
            actor=actor,
        )
    except DecisionError as exc:
        console.print(f"[red]Write-back failed: {exc}. Your answer was NOT saved.[/red]")
        return False
    console.print("[green]Decision resolved.[/green]")
    return True


# ---------------------------------------------------------------------------
# T038 — [d]efer path
# ---------------------------------------------------------------------------


def _handle_defer(
    candidate: CandidateReview,
    mission_slug: str,
    repo_root: Path,
    dm_service: Any,
    actor: str,
    console: Console,
) -> None:
    """Defer the decision with a required rationale (§6.3)."""
    from specify_cli.decisions.service import DecisionError  # local import

    try:
        rationale = console.input("Rationale for deferral (required): ").strip()
    except (KeyboardInterrupt, EOFError):
        rationale = ""

    with contextlib.suppress(DecisionError):
        dm_service.defer_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=candidate.decision_id,
            rationale=rationale or "deferred during candidate review",
            actor=actor,
        )
    console.print("[yellow]Decision deferred.[/yellow]")


# ---------------------------------------------------------------------------
# T035 — run_candidate_review — main entry point
# ---------------------------------------------------------------------------


def run_candidate_review(
    discussion_data: DiscussionFetch,
    decision_id: str,
    question_text: str,
    mission_slug: str,
    repo_root: Path,
    console: Console,
    dm_service: Any,
    actor: str,
) -> CandidateReview | None:
    """Full candidate-review flow for a widened decision point.

    Workflow:
    1. Emit §5.1 WIDEN SUMMARIZATION REQUEST block to stdout.
    2. Read LLM JSON response from stdin (30 s timeout).
    3. Parse into ``CandidateReview``; fall back on timeout / parse failure.
    4. Render §6 Candidate Review Panel.
    5. Prompt owner for ``[a]ccept`` / ``[e]dit`` / ``[d]efer``.
    6. Dispatch to the appropriate handler and return the ``CandidateReview``.

    Returns:
        The ``CandidateReview`` on accept or edit (decision resolved).
        The ``CandidateReview`` on defer (decision deferred, still pending).
        ``None`` only if the user cancels (KeyboardInterrupt / EOFError at the
        prompt before choosing an action).
    """
    # ------------------------------------------------------------------
    # Step 1 — emit instruction block
    # ------------------------------------------------------------------
    _emit_summarization_request(decision_id, question_text, discussion_data, console)

    # ------------------------------------------------------------------
    # Step 2+3 — read + parse LLM response
    # ------------------------------------------------------------------
    raw = _read_llm_response(timeout=SUMMARIZE_TIMEOUT)

    candidate = _parse_candidate(raw, decision_id, discussion_data) if raw is not None else _make_fallback_candidate(decision_id, discussion_data)

    # ------------------------------------------------------------------
    # Step 4 — render Candidate Review Panel
    # ------------------------------------------------------------------
    if candidate.llm_timed_out:
        # §5.3 fallback message
        console.print("[yellow]Summarization timed out or produced invalid output.[/yellow]")
        console.print("Showing raw discussion. Please write the answer manually.")
        console.print()
        console.print("[a]ccept empty | [e]dit (blank pre-fill) | [d]efer")
    else:
        summary_display = candidate.candidate_summary or "(no summary)"
        answer_display = candidate.candidate_answer or "(no answer)"

        panel_text = f"Question: {question_text}\n\nSummary:\n  {summary_display}\n\nProposed answer:\n  {answer_display}"
        console.print(Panel(panel_text, title="Candidate Review", expand=False))

    # ------------------------------------------------------------------
    # Step 5 — prompt owner
    # ------------------------------------------------------------------
    while True:
        try:
            choice = console.input("[a]ccept | [e]dit | [d]efer: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            # User cancelled — return None
            return None

        if choice in ("a", "accept"):
            _handle_accept(candidate, mission_slug, repo_root, dm_service, actor, console)
            return candidate

        if choice in ("e", "edit"):
            _handle_edit(candidate, mission_slug, repo_root, dm_service, actor, console)
            return candidate

        if choice in ("d", "defer"):
            _handle_defer(candidate, mission_slug, repo_root, dm_service, actor, console)
            return candidate

        console.print("[yellow]Invalid choice. Please enter 'a' (accept), 'e' (edit), or 'd' (defer).[/yellow]")
