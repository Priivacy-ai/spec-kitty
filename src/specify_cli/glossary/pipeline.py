"""Glossary middleware pipeline orchestrator (WP09).

This module implements the GlossaryMiddlewarePipeline that composes all
middleware components into a sequential execution chain:

    Layer 1: GlossaryCandidateExtractionMiddleware (term extraction)
    Layer 2: SemanticCheckMiddleware (conflict detection)
    Layer 3: GenerationGateMiddleware (generation blocking)
    Layer 4: ClarificationMiddleware (interactive conflict resolution)
    Layer 5: ResumeMiddleware (checkpoint/resume)

The pipeline executes middleware in order, passing the context object
through each layer. Expected exceptions (BlockedByConflict, DeferredToAsync,
AbortResume) propagate to the caller. Unexpected exceptions are wrapped
in RuntimeError with the offending middleware's class name for debugging.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Protocol

from specify_cli.glossary.exceptions import (
    AbortResume,
    BlockedByConflict,
    DeferredToAsync,
)
from specify_cli.glossary.strictness import Strictness

logger = logging.getLogger(__name__)


class GlossaryMiddleware(Protocol):
    """Protocol for glossary middleware components.

    Every middleware must implement a ``process`` method that accepts
    a context object and returns the (possibly modified) context.
    """

    def process(self, context: Any) -> Any:
        """Process the execution context.

        Args:
            context: Current execution context (PrimitiveExecutionContext)

        Returns:
            Modified context (may add extracted_terms, conflicts, etc.)

        Raises:
            BlockedByConflict: If generation must be blocked.
            DeferredToAsync: If clarification is deferred.
            AbortResume: If resume is aborted by the user.
        """
        ...


class GlossaryMiddlewarePipeline:
    """Orchestrate glossary middleware components in a sequential pipeline.

    The pipeline:
    - Checks if glossary is enabled for the current step
    - Executes middleware in the order provided
    - Validates that each middleware returns a non-None context
    - Propagates expected exceptions (BlockedByConflict, DeferredToAsync, AbortResume)
    - Wraps unexpected exceptions in RuntimeError with middleware class name
    """

    def __init__(
        self,
        middleware: List[GlossaryMiddleware],
        skip_on_disabled: bool = True,
    ) -> None:
        """Initialize the pipeline.

        Args:
            middleware: Ordered list of middleware components.
            skip_on_disabled: When True, skip pipeline entirely if
                ``context.is_glossary_enabled()`` returns False.
        """
        self.middleware = list(middleware)
        self.skip_on_disabled = skip_on_disabled

    def process(self, context: Any) -> Any:
        """Execute the middleware pipeline.

        Args:
            context: Initial execution context. Must not be None.

        Returns:
            Final context after all middleware have executed.

        Raises:
            ValueError: If context is None.
            BlockedByConflict: If the generation gate blocks.
            DeferredToAsync: If clarification is deferred.
            AbortResume: If resume is aborted.
            RuntimeError: If a middleware raises an unexpected exception.
        """
        if context is None:
            raise ValueError("Pipeline context must not be None")

        # Check if glossary is enabled for this step
        if self.skip_on_disabled and hasattr(context, "is_glossary_enabled"):
            if not context.is_glossary_enabled():
                return context

        current_context = context
        for mw in self.middleware:
            try:
                result = mw.process(current_context)
            except (BlockedByConflict, DeferredToAsync, AbortResume):
                # Expected exceptions -- re-raise for the caller
                raise
            except Exception as e:
                raise RuntimeError(
                    f"Glossary middleware {mw.__class__.__name__} failed: {e}"
                ) from e

            if result is None:
                raise RuntimeError(
                    f"Glossary middleware {mw.__class__.__name__} returned None "
                    f"instead of a context object"
                )

            current_context = result

        return current_context


def create_standard_pipeline(
    repo_root: Path,
    runtime_strictness: Strictness | None = None,
    interaction_mode: str = "interactive",
) -> GlossaryMiddlewarePipeline:
    """Create the standard 5-layer glossary middleware pipeline.

    Args:
        repo_root: Path to repository root (for config loading and event logs).
        runtime_strictness: CLI ``--strictness`` override (highest precedence).
        interaction_mode: ``"interactive"`` or ``"non-interactive"``.
            In non-interactive mode, the clarification middleware defers all
            conflicts instead of prompting.

    Returns:
        Configured pipeline instance with 5 middleware layers in order:
        extraction -> semantic check -> generation gate -> clarification -> resume.
    """
    from specify_cli.glossary.checkpoint import ScopeRef  # noqa: F401 (used by store)
    from specify_cli.glossary.clarification import ClarificationMiddleware
    from specify_cli.glossary.middleware import (
        GlossaryCandidateExtractionMiddleware,
        GenerationGateMiddleware,
        ResumeMiddleware,
        SemanticCheckMiddleware,
    )
    from specify_cli.glossary.store import GlossaryStore

    # Create glossary store (in-memory, backed by event log)
    events_dir = repo_root / ".kittify" / "events" / "glossary"
    if not events_dir.exists():
        events_dir.mkdir(parents=True, exist_ok=True)

    # Use a default event log path -- the store doesn't need a real file
    # to function; it just needs to be initialized.
    store = GlossaryStore(event_log_path=events_dir / "default.events.jsonl")

    # Load seed files into store
    _load_seed_files_into_store(repo_root, store)

    # Determine prompt function for clarification
    prompt_fn = None  # Non-interactive: defer all conflicts
    # In interactive mode, the ClarificationMiddleware defaults to deferring
    # if no prompt_fn is provided, which is the correct behavior for now.
    # A real interactive prompt_fn would be wired in via the CLI layer.

    # Build middleware layers in order
    middleware: List[GlossaryMiddleware] = [
        # Layer 1: Extract term candidates from step inputs
        GlossaryCandidateExtractionMiddleware(repo_root=repo_root),
        # Layer 2: Resolve terms and detect conflicts
        SemanticCheckMiddleware(
            glossary_store=store,
            repo_root=repo_root,
        ),
        # Layer 3: Block generation on unresolved high-severity conflicts
        GenerationGateMiddleware(
            repo_root=repo_root,
            runtime_override=runtime_strictness,
        ),
        # Layer 4: Interactive conflict clarification
        ClarificationMiddleware(
            repo_root=repo_root,
            prompt_fn=prompt_fn,
        ),
        # Layer 5: Checkpoint/resume
        ResumeMiddleware(project_root=repo_root),
    ]

    return GlossaryMiddlewarePipeline(middleware=middleware)


def _load_seed_files_into_store(repo_root: Path, store: "GlossaryStore") -> None:
    """Load seed files from .kittify/glossaries/ into the glossary store.

    Args:
        repo_root: Repository root path.
        store: GlossaryStore to populate.
    """
    from specify_cli.glossary.scope import GlossaryScope, load_seed_file

    for scope in GlossaryScope:
        try:
            senses = load_seed_file(scope, repo_root)
            for sense in senses:
                store.add_sense(sense)
        except Exception as exc:
            logger.warning(
                "Failed to load seed file for scope %s: %s",
                scope.value,
                exc,
            )
