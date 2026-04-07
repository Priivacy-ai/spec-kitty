"""Compatibility helpers for tracked mission identity fields."""

from __future__ import annotations

from typing import Any


def with_tracked_mission_slug_aliases(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose both canonical ``mission_slug`` and legacy ``feature_slug`` fields."""

    enriched = dict(payload)

    mission_slug = enriched.get("mission_slug")
    feature_slug = enriched.get("feature_slug")

    if mission_slug is None and feature_slug is not None:
        enriched["mission_slug"] = feature_slug
    elif feature_slug is None and mission_slug is not None:
        enriched["feature_slug"] = mission_slug

    return enriched
