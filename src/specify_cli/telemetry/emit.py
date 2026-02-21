"""Emit telemetry events for agent execution tracking.

Provides a fire-and-forget ``emit_execution_event()`` that:
- Generates a ULID (or UUID fallback) event ID
- Ticks a file-backed Lamport clock
- Persists an ``Event`` to a per-feature JSONL store
- Swallows all exceptions to avoid disrupting the orchestrator
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specify_cli.spec_kitty_events.clock import LamportClock
from specify_cli.spec_kitty_events.models import Event
from specify_cli.telemetry._clock import FileClockStorage
from specify_cli.telemetry.store import SimpleJsonStore

logger = logging.getLogger(__name__)


def _generate_event_id() -> str:
    """Return a 26-char ULID string, falling back to uuid4 hex prefix."""
    try:
        from ulid import ULID

        return str(ULID())
    except Exception:
        import uuid

        return uuid.uuid4().hex[:26]


def emit_execution_event(
    feature_dir: Path,
    feature_slug: str,
    wp_id: str,
    agent: str,
    role: str,
    *,
    model: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_usd: float | None = None,
    duration_ms: int = 0,
    success: bool = True,
    error: str | None = None,
    exit_code: int = 0,
    node_id: str = "cli",
) -> None:
    """Emit an ExecutionEvent to the feature's JSONL telemetry log.

    This function is **fire-and-forget**: any exception is logged as a
    warning and silently swallowed so that telemetry never blocks the
    orchestrator pipeline.

    Args:
        feature_dir: Path to ``kitty-specs/<feature>/``.
        feature_slug: Feature identifier (used as aggregate_id).
        wp_id: Work package ID (e.g. ``"WP01"``).
        agent: Agent identifier (e.g. ``"claude"``).
        role: ``"implementer"`` or ``"reviewer"``.
        model: LLM model name if known.
        input_tokens: Input token count if known.
        output_tokens: Output token count if known.
        cost_usd: Estimated cost in USD if known.
        duration_ms: Execution duration in milliseconds.
        success: Whether the invocation succeeded.
        error: Error message if the invocation failed.
        exit_code: Process exit code.
        node_id: Logical node ID for the Lamport clock.
    """
    try:
        # Tick Lamport clock — use wp_id-qualified node to avoid
        # contention when multiple WPs run concurrently via asyncio.
        effective_node = f"{node_id}:{wp_id}"
        clock_path = feature_dir / ".telemetry-clock.json"
        clock = LamportClock(
            node_id=effective_node,
            storage=FileClockStorage(clock_path),
        )
        lamport_value = clock.tick()

        # Build payload
        payload: dict[str, Any] = {
            "wp_id": wp_id,
            "agent": agent,
            "role": role,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
            "exit_code": exit_code,
        }

        event = Event(
            event_id=_generate_event_id(),
            event_type="ExecutionEvent",
            aggregate_id=feature_slug,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            node_id=effective_node,
            lamport_clock=lamport_value,
            causation_id=None,
        )

        store = SimpleJsonStore(feature_dir / "execution.events.jsonl")
        store.save_event(event)

    except Exception as e:
        logger.warning("Telemetry emission failed for %s/%s: %s", feature_slug, wp_id, e)
