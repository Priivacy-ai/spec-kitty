"""Plan interview flow with Widen Mode affordance (FR-002, WP08 T044).

Applies the same ``[w]iden`` pattern as the charter and specify interview
flows to the ``plan`` interview surface.  Each question opened here records
a Decision Moment with ``origin_flow=PLAN``.

Public API:
    run_plan_interview(questions, repo_root, mission_slug, console, actor)
        Drive a list of (question_id, question_text) through the widen-enabled
        interview loop and return a dict of answers.

This module is intentionally thin — it reuses helpers from
``specify_cli.widen.interview_helpers`` and the same WidenFlow/WidenPendingStore
infrastructure already used by charter.py and specify_interview.py.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from rich.console import Console

__all__ = ["run_plan_interview"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_actor() -> str:
    """Return the git user email or ``'cli'`` as fallback."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        email = result.stdout.strip()
        if email:
            return email
    except Exception:  # noqa: BLE001
        pass
    return "cli"


def _get_mission_id(repo_root: Path, mission_slug: str) -> str | None:
    """Read mission_id (ULID) from kitty-specs/<slug>/meta.json."""
    meta_path = repo_root / "kitty-specs" / mission_slug / "meta.json"
    with contextlib.suppress(Exception):
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return data.get("mission_id") or None
    return None


def _is_already_widened(widen_store: Any, decision_id: str) -> bool:
    """Return True if *decision_id* is already pending in the store."""
    with contextlib.suppress(Exception):
        return any(e.decision_id == decision_id for e in widen_store.list_pending())
    return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_plan_interview(  # noqa: C901
    questions: list[tuple[str, str]],
    repo_root: Path,
    mission_slug: str,
    console: Console,
    actor: str | None = None,
) -> dict[str, str]:
    """Drive a plan interview with the Widen Mode affordance.

    Args:
        questions:    List of ``(question_id, question_text)`` pairs in order.
        repo_root:    Absolute path to the repo root.
        mission_slug: Mission slug (e.g. ``'my-mission-01ABC'``).
        console:      Rich Console for output.
        actor:        Git user email; resolved automatically if None.

    Returns:
        A dict mapping ``question_id`` to the owner's answer.  Empty string
        for questions that were widened (pending-external-input) or deferred.
    """
    import typer

    from specify_cli.decisions import service as _dm_service
    from specify_cli.decisions.models import OriginFlow as _DmOriginFlow
    from specify_cli.decisions.service import DecisionError as _DecisionError
    from specify_cli.widen.interview_helpers import (
        render_already_widened_prompt,
        run_end_of_interview_pending_pass,
    )

    if actor is None:
        actor = _resolve_actor()

    # ------------------------------------------------------------------
    # Prereq check + widen infrastructure setup (non-fatal)
    # ------------------------------------------------------------------
    prereq_state: Any = None
    widen_flow: Any = None
    widen_store: Any = None
    saas_client: Any = None

    try:
        from specify_cli.saas_client import SaasClient
        from specify_cli.widen import check_prereqs
        from specify_cli.widen.flow import WidenFlow
        from specify_cli.widen.state import WidenPendingStore

        saas_client = SaasClient.from_env(repo_root)
        _team_slug: str = ""
        with contextlib.suppress(Exception):
            from specify_cli.saas_client.auth import load_auth_context

            _auth_ctx = load_auth_context(repo_root)
            _team_slug = _auth_ctx.team_slug or ""

        prereq_state = check_prereqs(saas_client, team_slug=_team_slug)
        if prereq_state.all_satisfied:
            widen_flow = WidenFlow(saas_client, repo_root, console)
            widen_store = WidenPendingStore(repo_root, mission_slug)
    except Exception:  # noqa: BLE001
        pass  # non-fatal; [w] will be suppressed

    mission_id = _get_mission_id(repo_root, mission_slug)

    answers: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Question loop
    # ------------------------------------------------------------------
    for question_id, question_text in questions:
        default_value = ""

        # Open a Decision Moment (non-fatal)
        current_decision_id: str | None = None
        with contextlib.suppress(_DecisionError, Exception):
            dm_response = _dm_service.open_decision(
                repo_root=repo_root,
                mission_slug=mission_slug,
                origin_flow=_DmOriginFlow.PLAN,
                step_id=f"plan.{question_id}",
                input_key=question_id,
                question=question_text,
                options=(),
                actor=actor,
            )
            current_decision_id = dm_response.decision_id

        # T045 — Already-widened question prompt
        _already_widened = (
            widen_store is not None
            and current_decision_id is not None
            and _is_already_widened(widen_store, current_decision_id)
        )
        if _already_widened and saas_client is not None:
            render_already_widened_prompt(
                question_text=question_text,
                decision_id=current_decision_id,  # type: ignore[arg-type]
                mission_slug=mission_slug,
                repo_root=repo_root,
                saas_client=saas_client,
                widen_store=widen_store,
                dm_service=_dm_service,
                actor=actor,
                console=console,
            )
            answers[question_id] = ""
            continue  # next question

        # Build hint line
        widen_suffix = ""
        if (
            prereq_state is not None
            and prereq_state.all_satisfied
            and widen_flow is not None
            and widen_store is not None
            and current_decision_id is not None
            and not _already_widened
        ):
            widen_suffix = " | [w]iden"
        hint_line = (
            f"[enter]=accept default | [text]=type answer{widen_suffix}"
            " | [d]efer | [!cancel]"
        )
        console.print(f"[dim]{hint_line}[/dim]")

        # Prompt
        user_answer = ""
        while True:
            try:
                raw = typer.prompt(question_text, default=default_value)
            except (KeyboardInterrupt, EOFError):
                raise typer.Exit() from None

            if (
                raw.strip().lower() == "w"
                and widen_flow is not None
                and current_decision_id is not None
                and mission_id is not None
            ):
                from datetime import UTC, datetime

                from specify_cli.widen.models import WidenAction, WidenPendingEntry

                result = widen_flow.run_widen_mode(
                    decision_id=current_decision_id,
                    mission_id=mission_id,
                    mission_slug=mission_slug,
                    question_text=question_text,
                    actor=actor,
                )

                if result.action == WidenAction.CANCEL:
                    console.print(f"[dim]{hint_line}[/dim]")
                    continue  # re-prompt

                if result.action == WidenAction.BLOCK:
                    from specify_cli.cli.commands.charter import _run_blocked_prompt_loop

                    _run_blocked_prompt_loop(
                        decision_id=result.decision_id or current_decision_id,
                        question_text=question_text,
                        invited=result.invited,
                        mission_slug=mission_slug,
                        repo_root=repo_root,
                        console=console,
                        saas_client=saas_client,
                        actor=actor,
                    )
                    user_answer = ""
                    break

                if result.action == WidenAction.CONTINUE:
                    if widen_store is not None:
                        with contextlib.suppress(Exception):
                            widen_store.add_pending(
                                WidenPendingEntry(
                                    decision_id=result.decision_id or current_decision_id,
                                    mission_slug=mission_slug,
                                    question_id=f"plan.{question_id}",
                                    question_text=question_text,
                                    entered_pending_at=datetime.now(tz=UTC),
                                    widen_endpoint_response={},
                                )
                            )
                    user_answer = ""
                    break

                # Unknown action
                user_answer = raw
                break

            else:
                user_answer = raw
                break

        answers[question_id] = user_answer

        # Terminal DM event (non-fatal)
        if current_decision_id is not None:
            if user_answer.strip().lower() == "!cancel":
                with contextlib.suppress(Exception):
                    _dm_service.cancel_decision(
                        repo_root=repo_root,
                        mission_slug=mission_slug,
                        decision_id=current_decision_id,
                        rationale="owner canceled during plan interview",
                        actor=actor,
                    )
            elif user_answer.strip():
                with contextlib.suppress(Exception):
                    _dm_service.resolve_decision(
                        repo_root=repo_root,
                        mission_slug=mission_slug,
                        decision_id=current_decision_id,
                        final_answer=user_answer,
                        actor=actor,
                    )
            else:
                with contextlib.suppress(Exception):
                    _dm_service.defer_decision(
                        repo_root=repo_root,
                        mission_slug=mission_slug,
                        decision_id=current_decision_id,
                        rationale="owner deferred during plan interview",
                        actor=actor,
                    )

    # ------------------------------------------------------------------
    # T040 — End-of-interview pending pass (FR-010)
    # ------------------------------------------------------------------
    if widen_store is not None and saas_client is not None:
        run_end_of_interview_pending_pass(
            widen_store=widen_store,
            saas_client=saas_client,
            mission_slug=mission_slug,
            repo_root=repo_root,
            console=console,
            dm_service=_dm_service,
            actor=actor,
        )

    return answers
