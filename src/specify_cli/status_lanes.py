"""Shared status-lane constants without importing status orchestration."""

from __future__ import annotations

CANONICAL_LANES: tuple[str, ...] = (
    "planned",
    "claimed",
    "in_progress",
    "for_review",
    "in_review",
    "approved",
    "done",
    "blocked",
    "canceled",
)

LANE_ALIASES: dict[str, str] = {
    "doing": "in_progress",
    # NOTE: "in_review" is NO LONGER an alias — it is a first-class lane (FR-012a)
}

TERMINAL_LANES: frozenset[str] = frozenset({"done", "canceled"})
