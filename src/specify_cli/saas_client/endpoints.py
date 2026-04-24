"""Lightweight response TypedDicts for SaaS endpoint shapes.

These are intentionally thin — they mirror the JSON structures returned by
spec-kitty-saas #110 and #111 without imposing pydantic validation overhead
in the client layer.  Heavier validation (pydantic models) lives in the
consuming modules (e.g. ``specify_cli.widen``).

Keeping response shapes here prevents circular imports: modules inside
``specify_cli.widen`` can import from here without importing the full client.
"""

from __future__ import annotations

from typing import TypedDict


class WidenResponse(TypedDict):
    """Shape of a successful POST /api/v1/decision-points/{id}/widen response.

    Matches the ``widen_endpoint_response`` object in widen-state.schema.json.
    ``slack_thread_url`` and ``invited_count`` are nullable/optional.
    """

    decision_id: str
    widened_at: str
    slack_thread_url: str | None
    invited_count: int | None


class DiscussionMessage(TypedDict):
    """A single message within a discussion thread."""

    author: str
    text: str
    timestamp: str | None


class DiscussionData(TypedDict):
    """Shape of GET /api/v1/decision-points/{id}/discussion response."""

    decision_id: str
    participants: list[str]
    messages: list[DiscussionMessage]
    thread_url: str | None
    message_count: int
