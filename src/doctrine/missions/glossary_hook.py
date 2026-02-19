"""Glossary pipeline hook for mission primitive execution.

This module provides the concrete integration point between the mission
framework and the glossary middleware pipeline. Mission executors use
``execute_with_glossary()`` to run any primitive function through the
glossary pipeline before the primitive body executes.

The hook is metadata-driven: it only runs the pipeline when
``glossary_check`` is enabled (the default per FR-020). When disabled,
the primitive runs without glossary checks.

Usage from a mission executor::

    from specify_cli.missions.glossary_hook import execute_with_glossary

    result = execute_with_glossary(
        primitive_fn=run_specify_step,
        context=ctx,
        repo_root=Path("."),
    )

This module satisfies WP09 success criterion #2: pipeline attaches to
mission primitives automatically when ``glossary_check: enabled`` metadata
is present.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from specify_cli.glossary.attachment import (
    GlossaryAwarePrimitiveRunner,
    read_glossary_check_metadata,
)
from specify_cli.glossary.strictness import Strictness

logger = logging.getLogger(__name__)


def execute_with_glossary(
    primitive_fn: Callable[..., Any],
    context: Any,
    repo_root: Path,
    runtime_strictness: Optional[Strictness] = None,
    interaction_mode: str = "interactive",
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute a mission primitive with glossary checks.

    This is the main entry point for wiring the glossary pipeline into
    mission execution. It:

    1. Checks whether glossary checks are enabled for this step
       (via context metadata or defaults).
    2. If enabled, runs the full glossary middleware pipeline
       (extraction -> check -> clarification -> gate -> resume)
       on the context before executing the primitive.
    3. Executes the primitive function with the (possibly modified) context.
    4. Returns whatever the primitive function returns.

    Args:
        primitive_fn: The mission primitive function to execute.
            Must accept a PrimitiveExecutionContext as first argument.
        context: PrimitiveExecutionContext for this step.
        repo_root: Path to repository root.
        runtime_strictness: CLI ``--strictness`` override (highest precedence).
        interaction_mode: ``"interactive"`` or ``"non-interactive"``.
        *args: Extra positional arguments forwarded to primitive_fn.
        **kwargs: Extra keyword arguments forwarded to primitive_fn.

    Returns:
        Whatever primitive_fn returns.

    Raises:
        BlockedByConflict: If unresolved conflicts block generation
            (after clarification has had its chance to resolve them).
        DeferredToAsync: If user deferred conflict resolution.
        AbortResume: If user aborted resume.
    """
    # Check metadata to decide if glossary checks should run
    step_metadata = getattr(context, "metadata", {}) or {}
    if not read_glossary_check_metadata(step_metadata):
        logger.debug(
            "Glossary checks disabled for step=%s, skipping pipeline",
            getattr(context, "step_id", "unknown"),
        )
        return primitive_fn(context, *args, **kwargs)

    logger.info(
        "Running glossary pipeline for step=%s",
        getattr(context, "step_id", "unknown"),
    )

    runner = GlossaryAwarePrimitiveRunner(
        repo_root=repo_root,
        runtime_strictness=runtime_strictness,
        interaction_mode=interaction_mode,
    )
    return runner.execute(primitive_fn, context, *args, **kwargs)
