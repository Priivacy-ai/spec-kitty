"""Widen Mode flow orchestration.

``WidenFlow.run_widen_mode()`` is the single entry point called by
charter/specify/plan interview loops when the user presses ``w``.

Sequence (per plan.md §5):
  1. Audience review (WP04) — fetch default audience, trim, confirm.
  2. POST widen (WP01 SaasClient) — call the widen endpoint.
  3. Render success panel with Slack thread URL (T025).
  4. [b/c] pause-semantics prompt (FR-007) — default BLOCK.

Returns :class:`~specify_cli.widen.models.WidenFlowResult` — never raises.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from specify_cli.saas_client import SaasClient, SaasClientError
from specify_cli.widen.audience import run_audience_review
from specify_cli.widen.models import AudienceSelection, WidenAction, WidenFlowResult


class WidenFlow:
    """Orchestrates the inline Widen Mode UX from interview loops.

    Args:
        saas_client: Authenticated :class:`~specify_cli.saas_client.SaasClient`.
        repo_root: Absolute path to the repo root (used for future store access).
        console: Rich :class:`~rich.console.Console` used for all output and
            interactive prompts.
    """

    def __init__(
        self,
        saas_client: SaasClient,
        repo_root: Path,
        console: Console,
    ) -> None:
        self._client = saas_client
        self._repo_root = repo_root
        self._console = console

    # ------------------------------------------------------------------
    # T021 — Public entry point
    # ------------------------------------------------------------------

    def run_widen_mode(
        self,
        decision_id: str,
        mission_id: str,
        mission_slug: str,  # noqa: ARG002  # reserved for store path construction
        question_text: str,
        actor: str,  # noqa: ARG002  # reserved for audit/event logging
    ) -> WidenFlowResult:
        """Orchestrate Widen Mode: audience review -> POST widen -> [b/c] prompt.

        Called by the interview loop when the user presses ``w``.  Always
        returns a :class:`~specify_cli.widen.models.WidenFlowResult`; never
        raises to the caller.

        Args:
            decision_id: ULID of the DecisionPoint being widened.
            mission_id: Canonical ULID of the mission (for audience-default fetch).
            mission_slug: Human-readable mission slug (for sidecar state path).
            question_text: Full text of the interview question being widened.
            actor: Identity string for the actor (e.g. ``"owner"``).

        Returns:
            :class:`~specify_cli.widen.models.WidenFlowResult` with
            ``action = CANCEL | BLOCK | CONTINUE``.
        """
        # Step 1 — Audience review (WP04).
        selection = run_audience_review(
            saas_client=self._client,
            mission_id=mission_id,
            question_text=question_text,
            console=self._console,
        )
        if selection is None:
            # User canceled or SaaS error during audience fetch.
            return WidenFlowResult(action=WidenAction.CANCEL)

        # Step 2 — POST /api/v1/decision-points/{id}/widen (T022).
        widen_response = self._post_widen(decision_id, selection.user_ids)
        if widen_response is None:
            # SaaS error during widen POST — messages already printed.
            return WidenFlowResult(action=WidenAction.CANCEL)

        # Step 3 — Render success panel with Slack thread URL (T025).
        self._render_widen_success(selection, question_text, widen_response)

        # Step 4 — [b/c] pause-semantics prompt (T023).
        action = self._prompt_pause_semantics(question_text, widen_response)
        return WidenFlowResult(
            action=action,
            decision_id=decision_id,
            invited=selection.display_names,
        )

    # ------------------------------------------------------------------
    # T022 — Widen POST call
    # ------------------------------------------------------------------

    def _post_widen(
        self,
        decision_id: str,
        invited: list[int],
    ) -> dict[str, object] | None:
        """Call ``POST /api/v1/decision-points/{id}/widen``.

        Returns the raw response dict on success, or ``None`` on any
        :class:`~specify_cli.saas_client.SaasClientError`.  Error messages
        are printed to the console before returning ``None``.

        Args:
            decision_id: ULID of the DecisionPoint.
            invited: Trimmed invite list from the audience review step.

        Returns:
            Response dict (``decision_id``, ``widened_at``, …) or ``None``.
        """
        try:
            response = self._client.post_widen(decision_id, invited)
            # Normalise to a plain dict so downstream code is type-safe
            # regardless of whether post_widen returns a TypedDict or a
            # Pydantic model.
            return dict(response)
        except SaasClientError as exc:
            self._console.print(f"[red]Widen failed:[/red] {exc}")
            self._console.print("Returning to interview prompt.")
            return None

    # ------------------------------------------------------------------
    # T025 — Render success panel
    # ------------------------------------------------------------------

    def _render_widen_success(
        self,
        selection: AudienceSelection,
        question_text: str,
        response: dict[str, object],
    ) -> None:
        """Render the "Widened ✓" success panel (§3 CLI contracts).

        Shows the invite list, the truncated question text, and the Slack
        thread URL (if available).

        Args:
            selection: Confirmed invite list with display names and user IDs.
            question_text: Full question text (truncated to 50 chars in panel).
            response: Raw response dict from :meth:`_post_widen`.
        """
        invited = selection.display_names
        if len(invited) == 0:
            invited_str = "(no participants)"
        elif len(invited) == 1:
            invited_str = invited[0]
        elif len(invited) == 2:
            invited_str = f"{invited[0]} and {invited[1]}"
        else:
            invited_str = f"{', '.join(invited[:-1])}, and {invited[-1]}"

        q_short = question_text[:50]
        slack_url: str | None = response.get("slack_thread_url")  # type: ignore[assignment]
        thread_line = f"\nThread: {slack_url}" if slack_url else ""

        self._console.print(
            Panel(
                f"Slack thread created. {invited_str} have been invited to discuss:\n"
                f'  "{q_short}"{thread_line}',
                title="Widened ✓",
            )
        )

    # ------------------------------------------------------------------
    # T023 — [b/c] pause-semantics prompt
    # ------------------------------------------------------------------

    def _prompt_pause_semantics(
        self,
        question_text: str,  # noqa: ARG002  # kept for future context-aware rendering
        response: dict[str, object],  # noqa: ARG002  # kept for future context-aware rendering
    ) -> WidenAction:
        """Render the ``[b/c]`` pause-semantics prompt (FR-007).

        Default is ``BLOCK``: pressing Enter (empty input) or any non-``c``
        input returns :attr:`~specify_cli.widen.models.WidenAction.BLOCK`.

        On :class:`EOFError` (non-interactive environment, CI) the method
        defaults to ``BLOCK`` gracefully.

        Args:
            question_text: Text of the widened question (reserved for future
                context-aware rendering).
            response: Raw widen POST response dict (reserved for future
                context-aware rendering).

        Returns:
            :attr:`~specify_cli.widen.models.WidenAction.BLOCK` or
            :attr:`~specify_cli.widen.models.WidenAction.CONTINUE`.
        """
        try:
            raw = self._console.input(
                "Block here or continue with other questions? [bold][b/c][/bold] (default: b): "
            )
        except EOFError:
            # Non-interactive environment — default to BLOCK (FR-007).
            return WidenAction.BLOCK

        choice = raw.strip().lower()
        if choice == "c":
            self._console.print(
                "Question parked as pending. You'll be prompted to resolve it at end of interview."
            )
            return WidenAction.CONTINUE

        # Any other input (Enter, "b", anything else) → BLOCK (FR-007).
        return WidenAction.BLOCK
