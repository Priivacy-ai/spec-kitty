"""Canonical ``MissionCreated`` payload builder (#2270).

Before this module, three code paths derived the ``MissionCreated`` defaults
independently — ``core/mission_creation.py``, ``sync/emitter.py`` (a verbatim
duplicate), and ``status/lifecycle_events.py`` (a third, divergent inline
fallback). They could drift on the default ``friendly_name`` (raw slug vs
titleized), ``created_at`` (now vs absent), and None-field wire shape.

This is the single canonical builder both surfaces consume so they cannot drift.
It lives in the CORE set and imports nothing from INTEGRATION (``sync`` /
``tracker``): the sync emitter consumes it, never the reverse (preserves the
CORE↛INTEGRATION boundary that PR #2172 established — see #2270's hard non-goal).

Wire shape is the canonical one (it is what crosses the network): drop
None-valued optionals EXCEPT ``mission_number``, whose canonical contract
distinguishes pre-merge nullity from field absence (FR-024).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# spec_kitty_events is an external contract package, consumed via its public
# import surface — CORE-safe (shared-package boundary).
from spec_kitty_events.lifecycle import MissionCreatedPayload

# ``mission_number`` is wire-required (FR-024) yet logically nullable for
# pre-merge missions; its explicit ``null`` must survive to the wire.
_KEEP_NONE_FIELDS = ("mission_number",)


def default_mission_display_name(mission_slug: str) -> str:
    """Derive a human-readable mission title from a kebab-case slug."""
    parts = [part for part in str(mission_slug).strip().split("-") if part]
    if not parts:
        return "Mission"
    return " ".join(parts)


def default_mission_purpose_context(display_name: str, target_branch: str) -> str:
    """Default purpose context, aligned across the local + sync payload paths."""
    return (
        f"This mission advances {display_name} on {target_branch} so stakeholders can "
        "track the work from mission creation onward."
    )


def build_mission_created_payload(
    *,
    mission_slug: str,
    target_branch: str,
    mission_type: str,
    wp_count: int,
    mission_id: str | None = None,
    mission_number: int | None = None,
    friendly_name: str | None = None,
    purpose_tldr: str | None = None,
    purpose_context: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build the canonical ``MissionCreated`` wire payload from source facts.

    Pure: no I/O, no INTEGRATION imports. Applies the shared default derivation
    (titleized display name, tldr/context fallbacks, ``created_at`` -> now) and
    returns the canonical wire dict. Raises ``pydantic.ValidationError`` on
    invalid input; callers that need the historical "invalid -> skip emission"
    contract catch it at their boundary.
    """
    display_name = (friendly_name or "").strip() or default_mission_display_name(mission_slug)
    tldr = (purpose_tldr or "").strip() or display_name
    context = (purpose_context or "").strip() or default_mission_purpose_context(display_name, target_branch)

    model = MissionCreatedPayload(
        mission_id=mission_id,
        mission_slug=mission_slug,
        mission_number=mission_number,
        mission_type=mission_type,
        target_branch=target_branch,
        wp_count=wp_count,
        friendly_name=display_name,
        purpose_tldr=tldr,
        purpose_context=context,
        created_at=created_at or datetime.now(UTC).isoformat(),
    )

    payload: dict[str, Any] = model.model_dump(mode="json", exclude_none=True)
    full = model.model_dump(mode="json", exclude_none=False)
    for name in _KEEP_NONE_FIELDS:
        if name in full and name not in payload:
            payload[name] = full[name]
    return payload
