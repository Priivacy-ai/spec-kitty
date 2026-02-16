"""Metadata-driven glossary pipeline attachment to mission primitives (WP09).

This module provides the mechanism to attach the glossary middleware pipeline
to mission primitive execution. The attachment is driven by metadata in step
definitions: ``glossary_check: enabled`` (or the default, which is enabled
per FR-020).

Usage as a callable processor::

    processor = attach_glossary_pipeline(
        repo_root=Path("."),
        runtime_strictness=Strictness.MEDIUM,
        interaction_mode="interactive",
    )
    processed_context = processor(context)

Usage as a decorator on mission primitive functions::

    @glossary_enabled(repo_root=Path("."))
    def my_primitive(context: PrimitiveExecutionContext) -> dict:
        # Glossary pipeline runs automatically before this body
        return {"result": "ok"}

Usage as a direct wrapper::

    result_context = run_with_glossary(
        context=ctx,
        repo_root=Path("."),
        runtime_strictness=Strictness.OFF,
    )
"""

from __future__ import annotations

import functools
import logging
import time
from pathlib import Path
from typing import Any, Callable, Optional

from specify_cli.glossary.exceptions import (
    AbortResume,
    BlockedByConflict,
    DeferredToAsync,
)
from specify_cli.glossary.pipeline import create_standard_pipeline
from specify_cli.glossary.strictness import Strictness

logger = logging.getLogger(__name__)


def attach_glossary_pipeline(
    repo_root: Path,
    runtime_strictness: Optional[Strictness] = None,
    interaction_mode: str = "interactive",
) -> Callable[[Any], Any]:
    """Create a glossary pipeline processor for mission primitives.

    Builds the standard 5-layer pipeline and returns a callable that
    processes any PrimitiveExecutionContext through it.

    Args:
        repo_root: Path to repository root.
        runtime_strictness: CLI ``--strictness`` override (highest precedence).
        interaction_mode: ``"interactive"`` or ``"non-interactive"``.

    Returns:
        A function that accepts a PrimitiveExecutionContext and returns
        the processed context. The function may raise BlockedByConflict,
        DeferredToAsync, or AbortResume.
    """
    pipeline = create_standard_pipeline(
        repo_root=repo_root,
        runtime_strictness=runtime_strictness,
        interaction_mode=interaction_mode,
    )

    def process_with_glossary(context: Any) -> Any:
        """Process context through the glossary middleware pipeline.

        Args:
            context: PrimitiveExecutionContext to process.

        Returns:
            Processed context with glossary fields populated.

        Raises:
            BlockedByConflict: Generation blocked by unresolved conflicts.
            DeferredToAsync: Conflict resolution deferred.
            AbortResume: User aborted resume.
        """
        start = time.perf_counter()
        try:
            result = pipeline.process(context)
            elapsed = time.perf_counter() - start
            logger.info(
                "Glossary pipeline completed in %.3fs for step=%s",
                elapsed,
                getattr(context, "step_id", "unknown"),
            )
            return result
        except (BlockedByConflict, DeferredToAsync, AbortResume):
            elapsed = time.perf_counter() - start
            logger.info(
                "Glossary pipeline halted after %.3fs for step=%s",
                elapsed,
                getattr(context, "step_id", "unknown"),
            )
            raise

    return process_with_glossary


def read_glossary_check_metadata(step_metadata: dict[str, Any]) -> bool:
    """Read glossary_check metadata from a mission step definition.

    This function interprets the ``glossary_check`` field from mission.yaml
    step definitions.

    Args:
        step_metadata: Step metadata dictionary from mission.yaml.

    Returns:
        True if glossary checks are enabled for this step, False otherwise.
        Default is True (enabled) per FR-020.
    """
    value = step_metadata.get("glossary_check")

    if value is None:
        # Not specified -> enabled by default (FR-020)
        return True

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        if value.lower() == "disabled":
            return False
        if value.lower() == "enabled":
            return True

    # Unknown value -> treat as enabled (safe default)
    return True


def run_with_glossary(
    context: Any,
    repo_root: Path,
    runtime_strictness: Optional[Strictness] = None,
    interaction_mode: str = "interactive",
) -> Any:
    """Run the glossary pipeline on a PrimitiveExecutionContext.

    This is the primary hook point for mission primitive executors.
    Call this before executing the primitive logic to ensure glossary
    checks run when ``glossary_check`` is enabled (the default).

    Args:
        context: PrimitiveExecutionContext to process.
        repo_root: Path to repository root.
        runtime_strictness: CLI ``--strictness`` override (highest precedence).
        interaction_mode: ``"interactive"`` or ``"non_interactive"``.

    Returns:
        Processed context with glossary fields populated.

    Raises:
        BlockedByConflict: Generation blocked by unresolved conflicts.
        DeferredToAsync: Conflict resolution deferred.
        AbortResume: User aborted resume.
    """
    processor = attach_glossary_pipeline(
        repo_root=repo_root,
        runtime_strictness=runtime_strictness,
        interaction_mode=interaction_mode,
    )
    return processor(context)


def glossary_enabled(
    repo_root: Path,
    runtime_strictness: Optional[Strictness] = None,
    interaction_mode: str = "interactive",
) -> Callable:
    """Decorator that runs the glossary pipeline before a mission primitive.

    The decorated function's first positional argument must be a
    ``PrimitiveExecutionContext``. The pipeline processes the context
    before the function body executes.

    Args:
        repo_root: Path to repository root.
        runtime_strictness: CLI ``--strictness`` override (highest precedence).
        interaction_mode: ``"interactive"`` or ``"non_interactive"``.

    Returns:
        Decorator function.

    Example::

        @glossary_enabled(repo_root=Path("."))
        def execute_specify(context: PrimitiveExecutionContext) -> dict:
            # context has already been processed by the glossary pipeline
            return {"result": context.effective_strictness}
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(context: Any, *args: Any, **kwargs: Any) -> Any:
            processed = run_with_glossary(
                context=context,
                repo_root=repo_root,
                runtime_strictness=runtime_strictness,
                interaction_mode=interaction_mode,
            )
            return fn(processed, *args, **kwargs)
        return wrapper
    return decorator
