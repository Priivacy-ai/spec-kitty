"""Public API for event emission.

Provides thread-safe singleton access to EventEmitter and
convenience functions for emitting each event type.

Usage:
    from specify_cli.sync.events import emit_wp_status_changed

    emit_wp_status_changed("WP01", "planned", "doing")
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .emitter import EventEmitter

_emitter: EventEmitter | None = None
_lock = threading.Lock()


def get_emitter() -> EventEmitter:
    """Get the singleton EventEmitter instance.

    Thread-safe via double-checked locking pattern.
    Lazily initializes on first access.

    Also ensures project identity exists before creating the emitter,
    logging a warning (but not failing) if identity can't be resolved.
    """
    global _emitter
    if _emitter is None:
        with _lock:
            if _emitter is None:
                # Ensure identity exists before creating emitter
                import logging
                logger = logging.getLogger(__name__)
                try:
                    from .project_identity import ensure_identity
                    from specify_cli.tasks_support import find_repo_root, TaskCliError
                    try:
                        repo_root = find_repo_root()
                        ensure_identity(repo_root)
                    except TaskCliError:
                        logger.debug("Non-project context; identity will be empty")
                except Exception as e:
                    logger.warning(f"Could not ensure identity: {e}")

                from .emitter import EventEmitter
                _emitter = EventEmitter()
    return _emitter


def reset_emitter() -> None:
    """Reset the singleton (for testing only)."""
    global _emitter
    with _lock:
        _emitter = None


# ── Convenience Functions ─────────────────────────────────────


def emit_wp_status_changed(
    wp_id: str,
    previous_status: str,
    new_status: str,
    changed_by: str = "user",
    feature_slug: str | None = None,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit WPStatusChanged event via singleton."""
    return get_emitter().emit_wp_status_changed(
        wp_id=wp_id,
        previous_status=previous_status,
        new_status=new_status,
        changed_by=changed_by,
        feature_slug=feature_slug,
        causation_id=causation_id,
    )


def emit_wp_created(
    wp_id: str,
    title: str,
    feature_slug: str,
    dependencies: list[str] | None = None,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit WPCreated event via singleton."""
    return get_emitter().emit_wp_created(
        wp_id=wp_id,
        title=title,
        feature_slug=feature_slug,
        dependencies=dependencies,
        causation_id=causation_id,
    )


def emit_wp_assigned(
    wp_id: str,
    agent_id: str,
    phase: str,
    retry_count: int = 0,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit WPAssigned event via singleton."""
    return get_emitter().emit_wp_assigned(
        wp_id=wp_id,
        agent_id=agent_id,
        phase=phase,
        retry_count=retry_count,
        causation_id=causation_id,
    )


def emit_feature_created(
    feature_slug: str,
    feature_number: str,
    target_branch: str,
    wp_count: int,
    created_at: str | None = None,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit FeatureCreated event via singleton."""
    return get_emitter().emit_feature_created(
        feature_slug=feature_slug,
        feature_number=feature_number,
        target_branch=target_branch,
        wp_count=wp_count,
        created_at=created_at,
        causation_id=causation_id,
    )


def emit_feature_completed(
    feature_slug: str,
    total_wps: int,
    completed_at: str | None = None,
    total_duration: str | None = None,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit FeatureCompleted event via singleton."""
    return get_emitter().emit_feature_completed(
        feature_slug=feature_slug,
        total_wps=total_wps,
        completed_at=completed_at,
        total_duration=total_duration,
        causation_id=causation_id,
    )


def emit_history_added(
    wp_id: str,
    entry_type: str,
    entry_content: str,
    author: str = "user",
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit HistoryAdded event via singleton."""
    return get_emitter().emit_history_added(
        wp_id=wp_id,
        entry_type=entry_type,
        entry_content=entry_content,
        author=author,
        causation_id=causation_id,
    )


def emit_error_logged(
    error_type: str,
    error_message: str,
    wp_id: str | None = None,
    stack_trace: str | None = None,
    agent_id: str | None = None,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit ErrorLogged event via singleton."""
    return get_emitter().emit_error_logged(
        error_type=error_type,
        error_message=error_message,
        wp_id=wp_id,
        stack_trace=stack_trace,
        agent_id=agent_id,
        causation_id=causation_id,
    )


def emit_dependency_resolved(
    wp_id: str,
    dependency_wp_id: str,
    resolution_type: str,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit DependencyResolved event via singleton."""
    return get_emitter().emit_dependency_resolved(
        wp_id=wp_id,
        dependency_wp_id=dependency_wp_id,
        resolution_type=resolution_type,
        causation_id=causation_id,
    )
