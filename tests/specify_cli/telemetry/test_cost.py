"""Tests for cost tracking and pricing table functionality."""

from datetime import datetime, timezone

import pytest

from specify_cli.spec_kitty_events.models import Event
from specify_cli.telemetry.cost import (
    CostSummary,
    cost_summary,
    load_pricing_table,
)


def _make_event_id(n: int) -> str:
    """Generate a 26-character event ID for testing."""
    return f"01HXYZ{str(n).zfill(20)}"


def make_event(
    *,
    event_id: str | None = None,
    event_num: int = 1,
    aggregate_id: str = "test-feature",
    lamport_clock: int = 1,
    node_id: str = "cli",
    wp_id: str = "WP01",
    agent: str = "claude",
    model: str = "claude-sonnet-4-20250514",
    input_tokens: int | None = 1000,
    output_tokens: int | None = 500,
    cost_usd: float | None = None,
    success: bool = True,
) -> Event:
    """Factory for creating test events."""
    if event_id is None:
        event_id = _make_event_id(event_num)
    return Event(
        event_id=event_id,
        event_type="ExecutionEvent",
        aggregate_id=aggregate_id,
        timestamp=datetime.now(timezone.utc),
        node_id=node_id,
        lamport_clock=lamport_clock,
        causation_id=None,
        payload={
            "wp_id": wp_id,
            "agent": agent,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "success": success,
        },
    )


def test_cost_summary_by_agent():
    """Test grouping by agent with 4 events for 2 agents."""
    events = [
        make_event(event_num=1, agent="claude", input_tokens=1000, output_tokens=500),
        make_event(event_num=2, agent="claude", input_tokens=2000, output_tokens=1000),
        make_event(event_num=3, agent="copilot", input_tokens=1500, output_tokens=750),
        make_event(event_num=4, agent="copilot", input_tokens=500, output_tokens=250),
    ]

    summaries = cost_summary(events, group_by="agent")

    assert len(summaries) == 2

    # Find claude summary
    claude = next(s for s in summaries if s.group_key == "claude")
    assert claude.group_by == "agent"
    assert claude.total_input_tokens == 3000
    assert claude.total_output_tokens == 1500
    assert claude.event_count == 2
    assert claude.estimated_cost_usd > 0  # Should be estimated

    # Find copilot summary
    copilot = next(s for s in summaries if s.group_key == "copilot")
    assert copilot.total_input_tokens == 2000
    assert copilot.total_output_tokens == 1000
    assert copilot.event_count == 2


def test_cost_summary_by_model():
    """Test grouping by model with different models."""
    events = [
        make_event(event_num=1, model="claude-sonnet-4-20250514", input_tokens=1000, output_tokens=500),
        make_event(event_num=2, model="gpt-4.1", input_tokens=1000, output_tokens=500),
        make_event(event_num=3, model="claude-sonnet-4-20250514", input_tokens=2000, output_tokens=1000),
    ]

    summaries = cost_summary(events, group_by="model")

    assert len(summaries) == 2

    claude = next(s for s in summaries if s.group_key == "claude-sonnet-4-20250514")
    assert claude.group_by == "model"
    assert claude.total_input_tokens == 3000
    assert claude.total_output_tokens == 1500
    assert claude.event_count == 2

    gpt = next(s for s in summaries if s.group_key == "gpt-4.1")
    assert gpt.total_input_tokens == 1000
    assert gpt.total_output_tokens == 500
    assert gpt.event_count == 1


def test_cost_summary_by_feature():
    """Test grouping by feature (aggregate_id)."""
    events = [
        make_event(event_num=1, aggregate_id="043-telemetry", input_tokens=1000, output_tokens=500),
        make_event(event_num=2, aggregate_id="044-reporting", input_tokens=1500, output_tokens=750),
        make_event(event_num=3, aggregate_id="043-telemetry", input_tokens=2000, output_tokens=1000),
    ]

    summaries = cost_summary(events, group_by="feature")

    assert len(summaries) == 2

    telemetry = next(s for s in summaries if s.group_key == "043-telemetry")
    assert telemetry.group_by == "feature"
    assert telemetry.total_input_tokens == 3000
    assert telemetry.total_output_tokens == 1500
    assert telemetry.event_count == 2

    reporting = next(s for s in summaries if s.group_key == "044-reporting")
    assert reporting.total_input_tokens == 1500
    assert reporting.total_output_tokens == 750
    assert reporting.event_count == 1


def test_explicit_cost_used():
    """Test that explicit cost_usd is used as-is."""
    events = [
        make_event(event_num=1, input_tokens=1000, output_tokens=500, cost_usd=0.15),
        make_event(event_num=2, input_tokens=2000, output_tokens=1000, cost_usd=0.25),
    ]

    summaries = cost_summary(events, group_by="agent")

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.total_cost_usd == 0.40  # 0.15 + 0.25
    assert summary.estimated_cost_usd == 0.0  # No estimation done


def test_estimated_cost_from_pricing():
    """Test cost estimation when cost_usd is None."""
    events = [
        make_event(
            event_num=1,
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=None,
        ),
    ]

    summaries = cost_summary(events, group_by="agent")

    assert len(summaries) == 1
    summary = summaries[0]
    # claude-sonnet-4-20250514: input=0.003/1k, output=0.015/1k
    # Expected: (1000 * 0.003 / 1000) + (500 * 0.015 / 1000) = 0.003 + 0.0075 = 0.0105
    assert summary.estimated_cost_usd == pytest.approx(0.0105, abs=1e-6)
    assert summary.total_cost_usd == pytest.approx(0.0105, abs=1e-6)


def test_zero_cost_not_estimated():
    """Test that explicit cost_usd=0.0 is NOT estimated."""
    events = [
        make_event(
            event_num=1,
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.0,  # Explicit zero
        ),
    ]

    summaries = cost_summary(events, group_by="agent")

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.total_cost_usd == 0.0
    assert summary.estimated_cost_usd == 0.0  # No estimation


def test_unknown_model_zero_cost():
    """Test that unknown models result in zero cost."""
    events = [
        make_event(
            event_num=1,
            model="unknown-model-xyz",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=None,
        ),
    ]

    summaries = cost_summary(events, group_by="agent")

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.total_cost_usd == 0.0
    assert summary.estimated_cost_usd == 0.0


def test_empty_events():
    """Test that empty event list returns empty summary."""
    summaries = cost_summary([], group_by="agent")
    assert summaries == []


def test_none_tokens_treated_as_zero():
    """Test that None token values are treated as 0."""
    events = [
        make_event(event_num=1, input_tokens=None, output_tokens=None, cost_usd=None),
        make_event(event_num=2, input_tokens=1000, output_tokens=500, cost_usd=None),
    ]

    summaries = cost_summary(events, group_by="agent")

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.total_input_tokens == 1000  # 0 + 1000
    assert summary.total_output_tokens == 500  # 0 + 500
    assert summary.event_count == 2


def test_sort_by_cost_descending():
    """Test that summaries are sorted by total_cost_usd descending."""
    events = [
        make_event(event_num=1, agent="cheap", input_tokens=100, output_tokens=50, cost_usd=0.01),
        make_event(event_num=2, agent="expensive", input_tokens=1000, output_tokens=500, cost_usd=1.00),
        make_event(event_num=3, agent="medium", input_tokens=500, output_tokens=250, cost_usd=0.10),
    ]

    summaries = cost_summary(events, group_by="agent")

    assert len(summaries) == 3
    assert summaries[0].group_key == "expensive"
    assert summaries[0].total_cost_usd == 1.00
    assert summaries[1].group_key == "medium"
    assert summaries[1].total_cost_usd == 0.10
    assert summaries[2].group_key == "cheap"
    assert summaries[2].total_cost_usd == 0.01


def test_pricing_table_loads():
    """Test that pricing table loads successfully with known models."""
    pricing = load_pricing_table()

    assert isinstance(pricing, dict)
    assert len(pricing) > 0

    # Verify known models exist
    assert "claude-sonnet-4-20250514" in pricing
    assert "gpt-4.1" in pricing
    assert "gemini-2.5-pro" in pricing

    # Verify structure
    claude_pricing = pricing["claude-sonnet-4-20250514"]
    assert "input_per_1k" in claude_pricing
    assert "output_per_1k" in claude_pricing
    assert claude_pricing["input_per_1k"] == 0.003
    assert claude_pricing["output_per_1k"] == 0.015


def test_cost_summary_to_dict():
    """Test CostSummary serialization to dictionary."""
    summary = CostSummary(
        group_key="claude",
        group_by="agent",
        total_input_tokens=3000,
        total_output_tokens=1500,
        total_cost_usd=0.123456789,  # More than 6 decimals
        estimated_cost_usd=0.987654321,
        event_count=5,
    )

    result = summary.to_dict()

    assert result == {
        "group_key": "claude",
        "group_by": "agent",
        "total_input_tokens": 3000,
        "total_output_tokens": 1500,
        "total_cost_usd": 0.123457,  # Rounded to 6 decimals
        "estimated_cost_usd": 0.987654,
        "event_count": 5,
    }


def test_invalid_group_by():
    """Test that invalid group_by raises ValueError."""
    events = [make_event(event_num=1)]

    with pytest.raises(ValueError, match="Invalid group_by"):
        cost_summary(events, group_by="invalid")


def test_cost_summary_by_role():
    """Test grouping by role (phase) for per-phase cost breakdown."""
    events = [
        make_event(event_num=1, agent="claude", input_tokens=5000, output_tokens=2000, cost_usd=0.50),
        make_event(event_num=2, agent="claude", input_tokens=3000, output_tokens=1000, cost_usd=0.30),
        make_event(event_num=3, agent="copilot", input_tokens=8000, output_tokens=4000, cost_usd=1.00),
        make_event(event_num=4, agent="claude", input_tokens=2000, output_tokens=500, cost_usd=0.15),
    ]
    # Add role to payloads
    events[0].payload["role"] = "specifier"
    events[1].payload["role"] = "planner"
    events[2].payload["role"] = "implementer"
    events[3].payload["role"] = "specifier"

    summaries = cost_summary(events, group_by="role")

    assert len(summaries) == 3

    specifier = next(s for s in summaries if s.group_key == "specifier")
    assert specifier.group_by == "role"
    assert specifier.total_input_tokens == 7000  # 5000 + 2000
    assert specifier.total_output_tokens == 2500  # 2000 + 500
    assert specifier.event_count == 2
    assert specifier.total_cost_usd == 0.65  # 0.50 + 0.15

    planner = next(s for s in summaries if s.group_key == "planner")
    assert planner.event_count == 1
    assert planner.total_cost_usd == 0.30

    implementer = next(s for s in summaries if s.group_key == "implementer")
    assert implementer.event_count == 1
    assert implementer.total_cost_usd == 1.00


def test_cost_summary_by_role_unknown_fallback():
    """Test that events without role field are grouped under 'unknown'."""
    events = [
        make_event(event_num=1, cost_usd=0.10),
        make_event(event_num=2, cost_usd=0.20),
    ]
    # Don't add role to payloads — should default to "unknown"

    summaries = cost_summary(events, group_by="role")

    assert len(summaries) == 1
    assert summaries[0].group_key == "unknown"
    assert summaries[0].event_count == 2
    assert summaries[0].total_cost_usd == pytest.approx(0.30)


def test_mixed_cost_scenarios():
    """Test mix of explicit costs, estimated costs, and zero costs."""
    events = [
        make_event(event_num=1, agent="claude", cost_usd=None, input_tokens=1000, output_tokens=500),  # Estimated
        make_event(event_num=2, agent="claude", cost_usd=0.20, input_tokens=0, output_tokens=0),  # Explicit
        make_event(event_num=3, agent="claude", cost_usd=0.0, input_tokens=1000, output_tokens=500),  # Explicit zero
    ]

    summaries = cost_summary(events, group_by="agent")

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.event_count == 3
    # Total should include estimated + explicit + explicit zero
    # Estimated: ~0.0105, Explicit: 0.20, Zero: 0.0
    assert summary.total_cost_usd > 0.20
    assert summary.estimated_cost_usd == pytest.approx(0.0105, abs=1e-6)  # Only from e1
