"""Widen Mode helpers for the ``charter interview`` subcommand (WP06 split).

These helpers manage the blocked-prompt widening loop and the per-question
dispatch into ``WidenFlow``. They are public-by-convention (the legacy
``_schedule_inactivity_reminder``, ``_run_blocked_prompt_loop`` etc. are
imported by other modules and by tests) and are re-exported from the package
``__init__`` for backward compatibility.
"""
from __future__ import annotations

from specify_cli.missions._read_path_resolver import candidate_feature_dir_for_mission
import contextlib
import threading
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel

from specify_cli.decisions import service as _dm_service
from specify_cli.decisions.service import DecisionError as _DecisionError
from specify_cli.mission_metadata import load_meta_or_empty

#: Sentinel PrereqState used when widen prereqs are unavailable.
#: Defined lazily as a module-level constant after first import of PrereqState.
_WIDEN_PREREQS_ABSENT_CACHE: Any = None


def _get_widen_prereqs_absent() -> Any:
    """Return a fully-absent PrereqState (lazy singleton)."""
    global _WIDEN_PREREQS_ABSENT_CACHE  # noqa: PLW0603
    if _WIDEN_PREREQS_ABSENT_CACHE is None:
        try:
            from specify_cli.widen.models import PrereqState

            _WIDEN_PREREQS_ABSENT_CACHE = PrereqState(
                teamspace_ok=False,
                slack_ok=False,
                saas_reachable=False,
            )
        except ImportError:
            return None
    return _WIDEN_PREREQS_ABSENT_CACHE


def _get_mission_id(repo_root: Path, mission_slug: str) -> str | None:
    """Read mission_id (ULID) from kitty-specs/<slug>/meta.json.

    Returns ``None`` if the file is absent or malformed.
    """
    # load_meta_or_empty (post-#2091 silent contract) absorbs a missing or
    # malformed meta.json to {}, matching the prior contextlib.suppress absorption.
    feature_dir = candidate_feature_dir_for_mission(repo_root, mission_slug)
    data = load_meta_or_empty(feature_dir)
    return data.get("mission_id") or None


def _is_already_widened(widen_store: Any, decision_id: str) -> bool:
    """Return True if *decision_id* already has a pending widen entry."""
    with contextlib.suppress(Exception):
        return any(e.decision_id == decision_id for e in widen_store.list_pending())
    return False


def _schedule_inactivity_reminder(
    console: Console,
    delay_seconds: int = 3600,
) -> threading.Timer:
    """Schedule an inactivity reminder for the blocked widen prompt (NFR-004).

    The timer fires once after *delay_seconds* (default 60 min).  It is a
    daemon thread so it will not prevent process exit.
    """

    def _remind() -> None:
        console.print(
            "\n[yellow]Still waiting on widened discussion.[/yellow] "
            "Check Slack, type a local answer, or press d to defer.\n"
            "Waiting > ",
            end="",
        )

    timer = threading.Timer(delay_seconds, _remind)
    timer.daemon = True
    timer.start()
    return timer


def _render_waiting_panel(
    console: Console,
    question_text: str,
    invited: list[str] | None,
    slack_thread_url: str | None = None,
) -> None:
    """Render the §4 Waiting-for-discussion panel (contracts/cli-contracts.md §4)."""
    participants_line = ", ".join(invited) if invited else "(none)"
    thread_line = f"Slack thread: {slack_thread_url}" if slack_thread_url else "Slack thread: (pending)"
    console.print(
        Panel(
            f"Question: {question_text}\n"
            f"Participants: {participants_line}\n"
            f"{thread_line}",
            title="Waiting for widened discussion",
        )
    )
    console.print(
        "\nOptions:\n"
        "  [f]etch & review   — fetch current discussion and produce candidate\n"
        "  <type an answer>   — resolve locally right now (closes Slack thread)\n"
        "  [d]efer            — defer this question for later\n"
    )


def _resolve_locally(
    decision_id: str,
    mission_slug: str,
    repo_root: Path,
    final_answer: str,
    actor: str,
    console: Console,
) -> bool:
    """FR-018: resolve with source=manual at the blocked widen prompt."""
    try:
        _dm_service.resolve_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=decision_id,
            final_answer=final_answer,
            actor=actor,
        )
    except _DecisionError as exc:
        console.print(
            f"[red]Write-back failed: {exc}. Your answer was NOT saved.[/red]"
        )
        return False
    console.print("[green]Resolved locally.[/green] SaaS will close the Slack thread shortly.")
    return True


def _defer_from_blocked_prompt(
    decision_id: str,
    mission_slug: str,
    repo_root: Path,
    actor: str,
    console: Console,
) -> bool:
    """T032: defer the widened decision from the blocked prompt."""
    try:
        rationale = console.input("Rationale for deferral (press Enter to skip): ").strip()
    except (KeyboardInterrupt, EOFError):
        rationale = ""

    try:
        _dm_service.defer_decision(
            repo_root=repo_root,
            mission_slug=mission_slug,
            decision_id=decision_id,
            rationale=rationale or "deferred from blocked widen prompt",
            actor=actor,
        )
    except _DecisionError as exc:
        console.print(
            f"[red]Write-back failed: {exc}. Your deferral was NOT saved.[/red]"
        )
        return False
    console.print("[yellow]Decision deferred.[/yellow]")
    return True


def _fetch_and_review_from_blocked(
    decision_id: str,
    mission_slug: str,
    question_text: str,
    repo_root: Path,
    saas_client: Any,
    actor: str,
    console: Console,
) -> bool:
    """T031: fetch discussion + run candidate review from the blocked prompt.

    Returns True if the decision was resolved or deferred (loop should exit).
    """
    from specify_cli.saas_client import SaasClientError

    console.print("Fetching discussion...")
    try:
        discussion_raw = saas_client.fetch_discussion(decision_id)
    except SaasClientError as exc:
        console.print(f"[yellow]Discussion fetch failed:[/yellow] {exc}")
        console.print("You can type a local answer or press d to defer.")
        return False

    # WP07 review stub — run_candidate_review not yet implemented.
    # Fall back to informational display and return False so the user
    # can still type a local answer or defer.
    try:
        from specify_cli.widen.review import run_candidate_review

        result = run_candidate_review(
            discussion_data=discussion_raw,
            decision_id=decision_id,
            question_text=question_text,
            mission_slug=mission_slug,
            repo_root=repo_root,
            console=console,
            dm_service=_dm_service,
            actor=actor,
        )
        return result is not None
    except (ImportError, AttributeError):
        # WP07 stub not yet implemented — display raw data.
        console.print(
            f"[dim]Participants: {', '.join(discussion_raw.participants)}[/dim]\n"
            f"[dim]Messages: {discussion_raw.message_count}[/dim]\n"
            "[dim]Candidate review not yet available (WP07). "
            "Type a local answer or press d to defer.[/dim]"
        )
        return False


def _resolve_dm_terminal(
    *,
    repo_root: Path,
    mission_slug: str,
    decision_id: str,
    actual_answer: str,
    actor: str,
) -> None:
    """Apply the correct Decision Moment terminal transition after a question answer.

    Rules (FR-012):
    - ``!cancel`` → cancel (question not applicable)
    - non-empty → resolve
    - empty → defer
    """
    if actual_answer.strip().lower() == "!cancel":
        with contextlib.suppress(_DecisionError):
            _dm_service.cancel_decision(
                repo_root=repo_root,
                mission_slug=mission_slug,
                decision_id=decision_id,
                rationale="owner canceled during charter interview (question not applicable)",
                actor=actor,
            )
    elif actual_answer.strip():
        with contextlib.suppress(_DecisionError):
            _dm_service.resolve_decision(
                repo_root=repo_root,
                mission_slug=mission_slug,
                decision_id=decision_id,
                final_answer=actual_answer,
                actor=actor,
            )
    else:
        with contextlib.suppress(_DecisionError):
            _dm_service.defer_decision(
                repo_root=repo_root,
                mission_slug=mission_slug,
                decision_id=decision_id,
                rationale="owner deferred during charter interview",
                actor=actor,
            )


def _prompt_one_question(
    *,
    question_id: str,
    prompt_text: str,
    default_value: str,
    hint_line: str,
    widen_flow: Any,
    widen_store: Any,
    current_decision_id: str | None,
    mission_id: str | None,
    mission_slug: str | None,
    repo_root: Path,
    console: Console,
    saas_client: Any,
    actor: str,
    answers_override: dict[str, str],
) -> str:
    """Prompt the user for a single interview question, handling widen dispatch.

    Returns the final answer string (may be empty for widen-pending / defer paths).
    """
    console.print(f"[dim]{hint_line}[/dim]")

    user_answer = ""
    while True:
        user_answer = typer.prompt(prompt_text, default=default_value)

        if (
            user_answer.strip().lower() == "w"
            and widen_flow is not None
            and current_decision_id is not None
            and mission_id is not None
            and mission_slug is not None
        ):
            _answer, _should_break = _dispatch_widen_input(
                widen_flow=widen_flow,
                current_decision_id=current_decision_id,
                mission_id=mission_id,
                mission_slug=mission_slug,
                question_id=question_id,
                prompt_text=prompt_text,
                hint_line=hint_line,
                widen_store=widen_store,
                answers_override=answers_override,
                repo_root=repo_root,
                console=console,
                saas_client=saas_client,
                actor=actor,
            )
            if _answer is None and not _should_break:
                continue  # CANCEL — re-prompt
            if _answer is not None:
                user_answer = _answer
            break

        else:
            break

    if question_id not in answers_override:
        answers_override[question_id] = user_answer

    return answers_override[question_id]


def _dispatch_widen_input(  # noqa: C901
    *,
    widen_flow: Any,
    current_decision_id: str,
    mission_id: str,
    mission_slug: str,
    question_id: str,
    prompt_text: str,
    hint_line: str,
    widen_store: Any,
    answers_override: dict[str, str],
    repo_root: Any,
    console: Console,
    saas_client: Any,
    actor: str,
) -> tuple[str | None, bool]:
    """T028 — Dispatch ``w`` input to WidenFlow; return (user_answer, break_loop).

    Returns:
        (user_answer, should_break):
          - user_answer: None → continue inner loop (re-prompt); else the value to use.
          - should_break: True if the outer question loop should advance to next question.
    """
    from datetime import UTC, datetime

    from specify_cli.widen.models import WidenAction, WidenPendingEntry

    result = widen_flow.run_widen_mode(
        decision_id=current_decision_id,
        mission_id=mission_id,
        mission_slug=mission_slug,
        question_text=prompt_text,
        actor=actor,
    )

    if result.action == WidenAction.CANCEL:
        # Re-show hint and re-prompt the same question
        console.print(f"[dim]{hint_line}[/dim]")
        return None, False  # continue inner loop

    if result.action == WidenAction.BLOCK:
        # Enter the blocked-prompt loop (T029)
        _run_blocked_prompt_loop(
            decision_id=result.decision_id or current_decision_id,
            question_text=prompt_text,
            invited=result.invited,
            mission_slug=mission_slug,
            repo_root=repo_root,
            console=console,
            saas_client=saas_client,
            actor=actor,
        )
        answers_override[question_id] = ""
        return "", True  # advance to next question

    if result.action == WidenAction.CONTINUE:
        # Write WidenPendingEntry (T024 pattern — caller does persistence)
        if widen_store is not None:
            try:
                widen_store.add_pending(WidenPendingEntry(
                    decision_id=result.decision_id or current_decision_id,
                    mission_slug=mission_slug,
                    question_id=f"charter.{question_id}",
                    question_text=prompt_text,
                    entered_pending_at=datetime.now(tz=UTC),
                    widen_endpoint_response={},
                ))
            except Exception as exc:  # noqa: BLE001
                console.print(
                    "[red]Could not save pending widen marker: "
                    f"{exc}. Question was NOT parked.[/red]"
                )
                return None, False
        answers_override[question_id] = ""
        return "", True  # advance to next question

    # Unknown action — fall through to normal answer
    return None, True


def _run_blocked_prompt_loop(
    decision_id: str,
    question_text: str,
    invited: list[str] | None,
    mission_slug: str,
    repo_root: Path,
    console: Console,
    saas_client: Any,
    actor: str,
    slack_thread_url: str | None = None,
) -> None:
    """T029: block the interview at the widened question until resolved.

    Renders the waiting panel and loops on input until the decision is
    resolved via one of:
    - [f]etch & review → run_candidate_review()
    - plain text answer → decision.resolve(manual)
    - [d]efer → decision.defer()
    """
    _render_waiting_panel(console, question_text, invited, slack_thread_url)

    # NFR-004: inactivity reminder after 60 minutes
    _inactivity_timer = _schedule_inactivity_reminder(console)

    while True:
        try:
            raw = console.input("Waiting > ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Type d to defer or a local answer to resolve.[/dim]")
            continue

        cmd = raw.strip()

        if not cmd:
            # Blank line — re-show options summary
            console.print(
                "[dim][f]etch & review | <local answer> | [d]efer | [!cancel][/dim]"
            )
            continue
        elif cmd.lower() == "f":
            _inactivity_timer.cancel()
            resolved = _fetch_and_review_from_blocked(
                decision_id=decision_id,
                mission_slug=mission_slug,
                question_text=question_text,
                repo_root=repo_root,
                saas_client=saas_client,
                actor=actor,
                console=console,
            )
            if resolved:
                break
            # Not resolved — reschedule inactivity timer and loop
            _inactivity_timer = _schedule_inactivity_reminder(console)
        elif cmd.lower() == "d":
            _inactivity_timer.cancel()
            deferred = _defer_from_blocked_prompt(
                decision_id=decision_id,
                mission_slug=mission_slug,
                repo_root=repo_root,
                actor=actor,
                console=console,
            )
            if deferred:
                break
            _inactivity_timer = _schedule_inactivity_reminder(console)
        elif cmd.lower() == "!cancel":
            _inactivity_timer.cancel()
            console.print("[dim]Interview canceled.[/dim]")
            raise typer.Exit()
        else:
            # Plain text → local answer (FR-018)
            _inactivity_timer.cancel()
            resolved = _resolve_locally(
                decision_id=decision_id,
                mission_slug=mission_slug,
                repo_root=repo_root,
                final_answer=cmd,
                actor=actor,
                console=console,
            )
            if resolved:
                break
            _inactivity_timer = _schedule_inactivity_reminder(console)
