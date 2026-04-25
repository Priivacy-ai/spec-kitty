"""Audience selection for Widen Mode.

Implements ``run_audience_review()`` — the inline UX for presenting the default
audience to the mission owner, accepting trim input, confirming the invite list,
and returning the confirmed list (or ``None`` on cancel).

Called by ``WidenFlow.run_widen_mode()`` immediately after the user presses ``w``.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from specify_cli.saas_client import (
    SaasAuthError,
    SaasClient,
    SaasClientError,
    SaasTimeoutError,
)
from specify_cli.saas_client.endpoints import AudienceMember
from specify_cli.widen.models import AudienceSelection


def _member_display_name(member: AudienceMember) -> str:
    if not isinstance(member, dict):
        return str(member)
    return str(member.get("display_name") or member.get("email") or member.get("user_id") or "")


def _member_user_id(member: AudienceMember) -> int | None:
    if not isinstance(member, dict):
        return None
    value = member.get("user_id")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_audience_input(raw: str, default_audience: list[str]) -> tuple[list[str], list[str]]:
    """Parse audience trim input.

    - Empty string → return default_audience unchanged (no unknowns).
    - Comma-separated names → return subset (case-insensitive match from
      default_audience).
    - Unknown names → include in list as-is, also returned in second element.
    - Only commas / whitespace → treat as empty → return full default list.

    Returns:
        A tuple of (result_list, unknown_names).
    """
    raw = raw.strip()
    if not raw:
        return list(default_audience), []

    names = [n.strip() for n in raw.split(",") if n.strip()]
    if not names:
        # User typed only commas or spaces — treat as empty
        return list(default_audience), []

    lower_map = {name.lower(): name for name in default_audience}
    result: list[str] = []
    unknown: list[str] = []
    for name in names:
        if name.lower() in lower_map:
            result.append(lower_map[name.lower()])
        else:
            result.append(name)  # unknown name — include as-is
            unknown.append(name)
    return result, unknown


def _warn_unknown(unknown: list[str], console: Console) -> None:
    """Print a warning for audience names not in the default list."""
    if unknown:
        console.print(
            f"[yellow]Note:[/yellow] {', '.join(unknown)} not in default audience — including anyway."
        )


def _prompt_audience(console: Console) -> str | None:
    """Prompt for audience input.

    Returns:
        Raw input string, or ``None`` on cancel (typed "cancel" or Ctrl+C).
    """
    try:
        raw = console.input("[bold]Audience >[/bold] ")
        if raw.strip().lower() == "cancel":
            console.print("\n[dim]Widen canceled.[/dim]")
            return None
        return raw
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Widen canceled.[/dim]")
        return None


def run_audience_review(
    saas_client: SaasClient,
    mission_id: str,
    question_text: str,
    console: Console,
) -> AudienceSelection | None:
    """Fetch default audience, render review Panel, accept trim input.

    Returns trimmed list on confirm, None on cancel (FR-006).

    Args:
        saas_client: Authenticated SaaS client.
        mission_id: ULID or slug identifying the mission.
        question_text: Text of the question being widened (used in Panel title).
        console: Rich Console for rendering output and prompting.

    Returns:
        Confirmed display names and Teamspace user IDs to pass to SaaS, or
        ``None`` if the user canceled or a SaaS error occurred.
    """
    # --- T020: Fetch audience from SaaS with typed error handling ---
    try:
        default_audience = saas_client.get_audience_default(mission_id)
    except SaasTimeoutError:
        console.print("[red]Widen failed:[/red] SaaS request timed out.")
        console.print("Returning to interview prompt.")
        return None
    except SaasAuthError:
        console.print("[red]Widen failed:[/red] Authentication error — check SPEC_KITTY_SAAS_TOKEN.")
        console.print("Returning to interview prompt.")
        return None
    except SaasClientError as exc:
        console.print(f"[red]Widen failed:[/red] {exc}")
        console.print("Returning to interview prompt.")
        return None

    # --- T016: Handle empty audience ---
    if not default_audience:
        console.print("[yellow]Warning:[/yellow] No default audience configured for this mission.")
        return None

    display_names = [_member_display_name(member) for member in default_audience]
    display_names = [name for name in display_names if name]
    user_id_by_display = {
        _member_display_name(member).lower(): _member_user_id(member)
        for member in default_audience
        if _member_display_name(member)
    }
    if not display_names:
        console.print("[yellow]Warning:[/yellow] No usable default audience configured for this mission.")
        return None

    # --- T016: Render audience review Panel ---
    title = f"Widen: {question_text[:60]}"
    audience_names = ", ".join(display_names)
    panel_body = (
        "Default audience for this decision:\n"
        f"  {audience_names}\n"
        "\n"
        "[Enter] to confirm, or type comma-separated names to trim.\n"
        'Type "cancel" or press Ctrl+C to abort.'
    )
    console.print(Panel(panel_body, title=title))

    # --- T018: Prompt for audience input ---
    raw = _prompt_audience(console)
    if raw is None:
        return None

    # --- T017: Parse trim input ---
    trimmed, unknown = _parse_audience_input(raw, display_names)
    _warn_unknown(unknown, console)

    user_ids: list[int] = []
    missing_ids: list[str] = []
    for name in trimmed:
        user_id = user_id_by_display.get(name.lower())
        if user_id is None:
            missing_ids.append(name)
        else:
            user_ids.append(user_id)

    if missing_ids:
        console.print(
            "[red]Widen failed:[/red] SaaS audience entries are missing Teamspace user IDs for "
            f"{', '.join(missing_ids)}."
        )
        console.print("Returning to interview prompt.")
        return None

    # --- T019: Confirmation display ---
    console.print(f"Audience confirmed: {', '.join(trimmed)} ({len(trimmed)} members)")
    console.print("Calling widen endpoint...")

    return AudienceSelection(display_names=trimmed, user_ids=user_ids)
