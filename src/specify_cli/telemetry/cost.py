"""Cost tracking and aggregation for LLM telemetry events."""

import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Any

import yaml

from specify_cli.spec_kitty_events.models import Event

logger = logging.getLogger(__name__)

_PRICING_PATH = Path(__file__).resolve().parent / "_pricing.yaml"
_pricing_cache: dict[str, dict[str, float]] | None = None


def load_pricing_table() -> dict[str, dict[str, float]]:
    """Load pricing table from YAML file (cached after first load)."""
    global _pricing_cache
    if _pricing_cache is not None:
        return _pricing_cache
    if not _PRICING_PATH.exists():
        logger.warning("Pricing table not found: %s", _PRICING_PATH)
        _pricing_cache = {}
        return _pricing_cache
    with open(_PRICING_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _pricing_cache = data.get("models", {})
    return _pricing_cache


@dataclass
class CostSummary:
    """Aggregated cost metrics for a group of events."""

    group_key: str
    group_by: str
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    estimated_cost_usd: float
    event_count: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "group_key": self.group_key,
            "group_by": self.group_by,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "event_count": self.event_count,
        }


def cost_summary(events: list[Event], group_by: str = "agent") -> list[CostSummary]:
    """
    Aggregate cost metrics from events, grouped by specified key.

    Args:
        events: List of telemetry events
        group_by: Grouping key - "agent", "model", "feature", or "role"

    Returns:
        List of CostSummary objects sorted by total_cost_usd descending

    Notes:
        - If cost_usd is None: estimate from pricing table
        - If cost_usd is explicitly set (including 0.0): use as-is, don't estimate
        - Unknown models: cost = 0.0
        - None tokens treated as 0
    """
    if not events:
        return []

    pricing_table = load_pricing_table()
    groups: dict[str, dict[str, Any]] = {}

    for event in events:
        payload = event.payload

        # Determine group key
        if group_by == "agent":
            key = payload.get("agent", "unknown")
        elif group_by == "model":
            key = payload.get("model", "unknown")
        elif group_by == "feature":
            key = event.aggregate_id
        elif group_by == "role":
            key = payload.get("role", "unknown")
        else:
            raise ValueError(f"Invalid group_by: {group_by}")

        # Initialize group if needed
        if key not in groups:
            groups[key] = {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0,
                "estimated_cost_usd": 0.0,
                "event_count": 0,
            }

        group = groups[key]

        # Extract token counts (treat None as 0)
        input_tokens = payload.get("input_tokens") or 0
        output_tokens = payload.get("output_tokens") or 0
        cost_usd = payload.get("cost_usd")

        group["total_input_tokens"] += input_tokens
        group["total_output_tokens"] += output_tokens
        group["event_count"] += 1

        # Cost calculation logic
        if cost_usd is None:
            # None means not reported - estimate from pricing table
            model = payload.get("model", "unknown")
            model_pricing = pricing_table.get(model, {})
            input_price = model_pricing.get("input_per_1k", 0.0)
            output_price = model_pricing.get("output_per_1k", 0.0)

            estimated = round((input_tokens * input_price / 1000.0) + (output_tokens * output_price / 1000.0), 6)
            group["estimated_cost_usd"] += estimated
            group["total_cost_usd"] += estimated
        else:
            # Explicit cost (including 0.0) - use as-is, don't estimate
            group["total_cost_usd"] += round(cost_usd, 6)

    # Convert to CostSummary objects
    summaries = [
        CostSummary(
            group_key=key,
            group_by=group_by,
            total_input_tokens=data["total_input_tokens"],
            total_output_tokens=data["total_output_tokens"],
            total_cost_usd=data["total_cost_usd"],
            estimated_cost_usd=data["estimated_cost_usd"],
            event_count=data["event_count"],
        )
        for key, data in groups.items()
    ]

    # Sort by total_cost_usd descending
    summaries.sort(key=lambda s: s.total_cost_usd, reverse=True)

    return summaries
