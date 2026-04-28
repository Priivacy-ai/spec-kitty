"""Compatibility helpers for tracked mission identity fields."""

from __future__ import annotations

from typing import Any


def with_tracked_mission_slug_aliases(payload: dict[str, Any]) -> dict[str, Any]:
    """Backfill ``mission_slug`` from legacy ``feature_slug`` if missing.

    Read-compat only: ensures payloads originating from old serialised data
    (which used ``feature_slug``) are normalised to the canonical
    ``mission_slug`` key before use.  The legacy ``feature_slug`` key is
    intentionally *not* re-injected into output payloads — callers that
    serialise to disk (e.g. ``StatusSnapshot.to_dict``) will produce
    ``mission_slug``-only output going forward.
    """

    enriched = dict(payload)

    if enriched.get("mission_slug") is None and enriched.get("feature_slug") is not None:
        enriched["mission_slug"] = enriched["feature_slug"]

    return enriched
