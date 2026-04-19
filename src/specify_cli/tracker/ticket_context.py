"""Ticket context file management for mission-origin flows.

Provides two local artefacts written by ``mission create --from-ticket``:

* ``.kittify/ticket-context.md``  — full ticket content for the LLM to read
* ``.kittify/pending-origin.yaml`` — origin metadata for specify to pick up
  after the mission is created

Neither file contains auth credentials or provider-internal identifiers
that the user should not need to see.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


TICKET_CONTEXT_FILENAME = "ticket-context.md"
PENDING_ORIGIN_FILENAME = "pending-origin.yaml"


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def write_ticket_context(repo_root: Path, ticket: dict[str, Any]) -> Path:
    """Write ``.kittify/ticket-context.md`` from a normalized ticket dict.

    Returns the path to the written file.
    """
    kittify = repo_root / ".kittify"
    kittify.mkdir(exist_ok=True)
    path = kittify / TICKET_CONTEXT_FILENAME

    identifier = ticket.get("identifier", "")
    title = ticket.get("title", "")
    status = (ticket.get("state") or {}).get("name", "") or ticket.get("status", "")
    url = ticket.get("url", "")
    body = ticket.get("body", "") or ""
    assignee_info = ticket.get("assignee") or {}
    assignee = assignee_info.get("name") or assignee_info.get("id") or "(unassigned)"

    lines = [
        f"# {identifier}: {title}",
        "",
        f"**Status:** {status}",
        f"**Assignee:** {assignee}",
        f"**URL:** {url}",
        "",
    ]

    if body.strip():
        lines += ["---", "", body.strip(), ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_pending_origin(
    repo_root: Path,
    ticket: dict[str, Any],
    provider: str,
) -> Path:
    """Write ``.kittify/pending-origin.yaml`` for specify to consume.

    Returns the path to the written file.
    """
    kittify = repo_root / ".kittify"
    kittify.mkdir(exist_ok=True)
    path = kittify / PENDING_ORIGIN_FILENAME

    data = {
        "provider": provider,
        "issue_key": ticket.get("identifier", ""),
        "issue_id": ticket.get("external_issue_id") or ticket.get("id", ""),
        "title": ticket.get("title", ""),
        "url": ticket.get("url", ""),
        "status": (ticket.get("state") or {}).get("name", "") or ticket.get("status", ""),
    }

    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Read / clear helpers
# ---------------------------------------------------------------------------


def read_pending_origin(repo_root: Path) -> dict[str, Any] | None:
    """Read ``.kittify/pending-origin.yaml`` if it exists."""
    path = repo_root / ".kittify" / PENDING_ORIGIN_FILENAME
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return None


def clear_pending_origin(repo_root: Path) -> None:
    """Remove ``.kittify/pending-origin.yaml`` after specify has consumed it."""
    path = repo_root / ".kittify" / PENDING_ORIGIN_FILENAME
    if path.exists():
        path.unlink()
