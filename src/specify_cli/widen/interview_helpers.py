"""Shared helpers for end-of-interview pending pass and already-widened prompts.

These helpers are shared by charter, specify, and plan interview flows.

Public API:
    run_end_of_interview_pending_pass(...)
        Surface any WidenPendingStore entries at interview exit and resolve
        them via run_candidate_review (T040 / T041 / T042).

    render_already_widened_prompt(...)
        Show the §1.3 already-widened prompt when a question already has a
        pending widen entry (T045).
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

__all__ = [
    "render_already_widened_prompt",
    "render_widen_hint_if_present",
    "run_end_of_interview_pending_pass",
]


# ---------------------------------------------------------------------------
# T049 — [WIDEN-HINT] prefix detection + dim render (FR-021)
# ---------------------------------------------------------------------------

_WIDEN_HINT_PREFIX = "[WIDEN-HINT] "


def render_widen_hint_if_present(question_context: str, console: Console) -> None:
    """Detect ``[WIDEN-HINT]`` prefix in question context and render as dim hint.

    Scans every line of *question_context* for lines that start with the
    ``[WIDEN-HINT] `` prefix.  When found, the prefix is stripped and the
    remainder is printed as ``[dim]`` text via *console*.

    This is a forward-looking capability for harness LLM integration.  In V1
    the harness LLM may prepend widen hints to the question context string;
    this helper renders them before the normal question prompt.

    Args:
        question_context: The full context string for the current question.
        console:          Rich Console to print to.
    """
    for line in question_context.splitlines():
        if line.startswith(_WIDEN_HINT_PREFIX):
            hint_text = line[len(_WIDEN_HINT_PREFIX):]
            console.print(f"[dim]{hint_text}[/dim]")


# ---------------------------------------------------------------------------
# T041 — Resolve one pending entry (fetch + review)
# ---------------------------------------------------------------------------


def _resolve_pending_entry(
    entry: Any,
    store: Any,
    saas_client: Any,
    mission_slug: str,
    repo_root: Path,
    console: Console,
    dm_service: Any,
    actor: str,
) -> None:
    """Fetch discussion + run candidate review for one pending widen entry.

    Removes the entry from the store after any terminal action (accept, edit,
    defer) or on unexpected exception (T042 — always-progress rule).

    Args:
        entry:        A WidenPendingEntry.
        store:        WidenPendingStore to remove from on completion.
        saas_client:  SaasClient used to fetch the discussion thread.
        mission_slug: Mission slug for Decision Moment write-back.
        repo_root:    Repo root path.
        console:      Rich Console.
        dm_service:   Decisions service module (``specify_cli.decisions.service``).
        actor:        Git user email / fallback identifier.
    """
    from specify_cli.saas_client import SaasClientError
    from specify_cli.widen.models import DiscussionFetch
    from specify_cli.widen.review import run_candidate_review

    console.print(
        f"      Widened at: {entry.entered_pending_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )

    # T042 — always remove from store even on unexpected failure.
    # Wrap the entire body so any exception (fetch failure, validation error,
    # run_candidate_review error) is suppressed and the interview always progresses.
    try:
        # Fetch discussion from SaaS
        console.print("      Fetching discussion...")
        try:
            raw = saas_client.fetch_discussion(entry.decision_id)
            # raw may be a DiscussionFetch already (from mocks) or a raw dict
            discussion = (
                raw if isinstance(raw, DiscussionFetch) else DiscussionFetch.model_validate(raw)
            )
        except SaasClientError as exc:
            console.print(
                f"      [yellow]Fetch failed:[/yellow] {exc}. "
                "You can still type an answer manually."
            )
            discussion = DiscussionFetch(
                participants=[],
                message_count=0,
                thread_url=None,
                messages=[],
                truncated=False,
            )
        except Exception:  # noqa: BLE001
            # Unexpected error during fetch/validation → use empty fallback
            discussion = DiscussionFetch(
                participants=[],
                message_count=0,
                thread_url=None,
                messages=[],
                truncated=False,
            )

        run_candidate_review(
            discussion_data=discussion,
            decision_id=entry.decision_id,
            question_text=entry.question_text,
            mission_slug=mission_slug,
            repo_root=repo_root,
            console=console,
            dm_service=dm_service,
            actor=actor,
        )
    except Exception:  # noqa: BLE001
        pass  # never block the interview
    finally:
        with contextlib.suppress(Exception):
            store.remove_pending(entry.decision_id)


# ---------------------------------------------------------------------------
# T040 — End-of-interview pending pass (FR-010)
# ---------------------------------------------------------------------------


def run_end_of_interview_pending_pass(
    *,
    widen_store: Any,
    saas_client: Any,
    mission_slug: str,
    repo_root: Path,
    console: Console,
    dm_service: Any,
    actor: str,
) -> None:
    """Surface any pending widen entries at interview exit and resolve them.

    If ``widen_store`` is ``None`` or the store is empty, this is a silent
    no-op (idempotent).

    Shows the §7 Panel from ``contracts/cli-contracts.md`` when there are
    pending entries, then iterates through each one.

    Args:
        widen_store:  WidenPendingStore instance (or None if unavailable).
        saas_client:  SaasClient for fetching discussions.
        mission_slug: Mission slug.
        repo_root:    Repo root path.
        console:      Rich Console.
        dm_service:   Decisions service module.
        actor:        Git actor identifier.
    """
    if widen_store is None:
        return

    pending = _safe_list_pending(widen_store)
    if not pending:
        return

    n = len(pending)
    noun = "questions are" if n != 1 else "question is"
    console.print(
        Panel(
            f"{n} widened {noun} still pending. "
            "Resolve them before finalizing the interview.",
            title="Pending Widened Questions",
        )
    )

    for idx, entry in enumerate(pending, start=1):
        console.print(f"({idx}/{n}) Question: {entry.question_text}")
        _resolve_pending_entry(
            entry=entry,
            store=widen_store,
            saas_client=saas_client,
            mission_slug=mission_slug,
            repo_root=repo_root,
            console=console,
            dm_service=dm_service,
            actor=actor,
        )


def _safe_list_pending(store: Any) -> list[Any]:
    """Return store.list_pending() or [] on any exception."""
    try:
        result = store.list_pending()
        return list(result)
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# T045 — Already-widened question prompt (§1.3 contract)
# ---------------------------------------------------------------------------


def render_already_widened_prompt(
    *,
    question_text: str,
    decision_id: str,
    mission_slug: str,
    repo_root: Path,
    saas_client: Any,
    widen_store: Any,
    dm_service: Any,
    actor: str,
    console: Console,
) -> None:
    """Show the §1.3 already-widened prompt for a question already in widen-pending.

    Options:
      [f]etch & resolve — run run_candidate_review() then remove from store.
      <local answer>    — resolve locally then remove from store.
      [d]efer           — defer the decision; remove from store.
      [!cancel]         — raise typer.Exit() immediately.

    Args:
        question_text: The human-readable question.
        decision_id:   The decision ULID already in the pending store.
        mission_slug:  Mission slug.
        repo_root:     Repo root path.
        saas_client:   SaasClient for fetching discussions.
        widen_store:   WidenPendingStore.
        dm_service:    Decisions service module.
        actor:         Git actor identifier.
        console:       Rich Console.
    """
    import typer

    from specify_cli.saas_client import SaasClientError
    from specify_cli.widen.models import DiscussionFetch
    from specify_cli.widen.review import run_candidate_review

    console.print(f"{question_text} [dim][pending-external-input][/dim]")
    hint = "[f]etch & resolve | [local answer]=type answer | [d]efer | [!cancel]"
    console.print(f"[dim]{hint}[/dim]")

    while True:
        try:
            raw = console.input("").strip()
        except (KeyboardInterrupt, EOFError):
            # Treat interrupt like !cancel
            raise typer.Exit() from None

        if raw.lower() == "f":
            # Fetch + review path
            try:
                fetched = saas_client.fetch_discussion(decision_id)
                discussion = fetched if isinstance(fetched, DiscussionFetch) else DiscussionFetch.model_validate(fetched)
            except (SaasClientError, Exception) as exc:  # noqa: BLE001
                console.print(
                    f"[yellow]Fetch failed:[/yellow] {exc}. "
                    "Type a local answer or press d to defer."
                )
                discussion = DiscussionFetch(
                    participants=[],
                    message_count=0,
                    thread_url=None,
                    messages=[],
                    truncated=False,
                )
            try:
                run_candidate_review(
                    discussion_data=discussion,
                    decision_id=decision_id,
                    question_text=question_text,
                    mission_slug=mission_slug,
                    repo_root=repo_root,
                    console=console,
                    dm_service=dm_service,
                    actor=actor,
                )
            finally:
                with contextlib.suppress(Exception):
                    widen_store.remove_pending(decision_id)
            return

        elif raw.lower() in ("d", "defer", "[d]efer"):
            # Defer path — also removes from store
            try:
                rationale = (
                    console.input(
                        "Rationale for deferral (press Enter to skip): "
                    ).strip()
                )
            except (KeyboardInterrupt, EOFError):
                rationale = ""

            with contextlib.suppress(Exception):
                dm_service.defer_decision(
                    repo_root=repo_root,
                    mission_slug=mission_slug,
                    decision_id=decision_id,
                    rationale=rationale or "deferred from already-widened prompt",
                    actor=actor,
                )
            console.print("[yellow]Decision deferred.[/yellow]")
            with contextlib.suppress(Exception):
                widen_store.remove_pending(decision_id)
            return

        elif raw.lower() == "!cancel":
            raise typer.Exit()

        elif raw:
            # Plain text → local resolve
            with contextlib.suppress(Exception):
                dm_service.resolve_decision(
                    repo_root=repo_root,
                    mission_slug=mission_slug,
                    decision_id=decision_id,
                    final_answer=raw,
                    actor=actor,
                )
            console.print(
                "[green]Resolved locally.[/green] "
                "SaaS will close the Slack thread shortly."
            )
            with contextlib.suppress(Exception):
                widen_store.remove_pending(decision_id)
            return

        else:
            # Empty input — re-show hint
            console.print(f"[dim]{hint}[/dim]")
