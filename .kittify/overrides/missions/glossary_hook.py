"""Bridge module: wires mission primitives to the glossary pipeline via kernel registry.

This module provides the concrete integration point between the mission
framework and the glossary middleware pipeline. Mission executors use
``execute_with_glossary()`` to run any primitive function through the
glossary pipeline before the primitive body executes.

The hook is metadata-driven: it only runs the pipeline when
``glossary_check`` is enabled (the default per FR-020). When disabled,
the primitive runs without glossary checks.

Dependency contract
-------------------
This module depends only on ``kernel.glossary_runner`` — it does **not**
import from ``specify_cli``.  The concrete runner
(``GlossaryAwarePrimitiveRunner``) is registered into the kernel registry
by ``specify_cli`` at startup via ``kernel.glossary_runner.register()``.

If no runner has been registered (e.g. in pure-doctrine tests or
third-party integrations), the primitive executes without glossary checks.

Usage from a mission executor::

    from doctrine.missions.glossary_hook import execute_with_glossary

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
from typing import Any
from collections.abc import Callable

from kernel.glossary_types import Strictness
from kernel.glossary_runner import get_runner

logger = logging.getLogger(__name__)


def _read_glossary_check_metadata(step_metadata: dict[str, Any]) -> bool:
    """Read glossary_check metadata from a mission step definition.

    Args:
        step_metadata: Step metadata dictionary from mission.yaml.

    Returns:
        True if glossary checks are enabled for this step, False otherwise.
        Default is True (enabled) per FR-020.
    """
    value = step_metadata.get("glossary_check")

    if value is None:
        return True  # enabled by default (FR-020)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        if value.lower() == "disabled":
            return False
        if value.lower() == "enabled":
            return True

    return True  # unknown value -> safe default: enabled


def execute_with_glossary(
    primitive_fn: Callable[..., Any],
    context: Any,
    repo_root: Path,
    runtime_strictness: Strictness | None = None,
    interaction_mode: str = "interactive",
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute a mission primitive with glossary checks.

    This is the main entry point for wiring the glossary pipeline into
    mission execution. It:

    1. Checks whether glossary checks are enabled for this step
       (via context metadata or defaults).
    2. If enabled and a runner is registered, runs the full glossary
       middleware pipeline on the context before executing the primitive.
    3. If no runner is registered, executes the primitive directly
       (graceful degradation).
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
    step_metadata = getattr(context, "metadata", {}) or {}
    if not _read_glossary_check_metadata(step_metadata):
        logger.debug(
            "Glossary checks disabled for step=%s, skipping pipeline",
            getattr(context, "step_id", "unknown"),
        )
        return primitive_fn(context, *args, **kwargs)

    runner_cls = get_runner()
    if runner_cls is None:
        logger.debug(
            "No glossary runner registered; executing primitive directly for step=%s",
            getattr(context, "step_id", "unknown"),
        )
        return primitive_fn(context, *args, **kwargs)

    logger.info(
        "Running glossary pipeline for step=%s",
        getattr(context, "step_id", "unknown"),
    )

    runner = runner_cls(
        repo_root=repo_root,
        runtime_strictness=runtime_strictness,
        interaction_mode=interaction_mode,
    )
    return runner.execute(primitive_fn, context, *args, **kwargs)
