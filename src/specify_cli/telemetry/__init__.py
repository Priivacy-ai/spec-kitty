"""Telemetry package for agent execution event tracking.

Provides JSONL-backed event storage, query layer, cost tracking,
and CLI commands for agent telemetry in spec-kitty 2.x.
"""

from specify_cli.telemetry.store import SimpleJsonStore
from specify_cli.telemetry.emit import emit_execution_event
from specify_cli.telemetry.query import (
    EventFilter,
    query_execution_events,
    query_project_events,
)
from specify_cli.telemetry.cost import CostSummary, cost_summary, load_pricing_table

__all__ = [
    "SimpleJsonStore",
    "EventFilter",
    "query_execution_events",
    "query_project_events",
    "emit_execution_event",
    "CostSummary",
    "cost_summary",
    "load_pricing_table",
]
