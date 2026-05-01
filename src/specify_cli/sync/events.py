"""Public API for event emission.

Provides thread-safe singleton access to EventEmitter and
convenience functions for emitting each event type.

Usage:
    from specify_cli.sync.events import emit_wp_status_changed

    emit_wp_status_changed("WP01", "planned", "in_progress")
"""

from __future__ import annotations

import logging
import threading
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .feature_flags import is_saas_sync_enabled

if TYPE_CHECKING:
    from .emitter import EventEmitter

_emitter: EventEmitter | None = None
_lock = threading.Lock()
logger = logging.getLogger(__name__)


def _resolve_repo_root() -> Path | None:
    """Resolve the current repo root, or None outside project context."""
    try:
        from specify_cli.task_utils import TaskCliError, find_repo_root

        return find_repo_root()
    except TaskCliError:
        logger.debug("Non-project context; repo root unavailable for sync daemon")
        return None


def _ensure_dashboard_sync_daemon(repo_root: Path | None, *, ensure_daemon: bool = True) -> None:
    """Keep the machine-global sync daemon alive for authenticated sync sessions."""
    if not ensure_daemon or repo_root is None or not is_saas_sync_enabled():
        return

    if not (repo_root / ".kittify").is_dir():
        return

    try:
        from specify_cli.auth import get_token_manager

        if not get_token_manager().is_authenticated:
            return
    except Exception as exc:
        logger.debug("Skipping dashboard daemon health check: %s", exc)
        return

    try:
        from .daemon import DaemonIntent, ensure_sync_daemon_running

        outcome = ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED)
        if outcome.started:
            pass  # Daemon is up; continue.
        elif outcome.skipped_reason == "rollout_disabled":
            # Unreachable: the is_saas_sync_enabled() check at line 45 already
            # bailed before we get here. Present only as a defensive branch.
            pass
        elif outcome.skipped_reason == "policy_manual":
            logger.debug("Background sync in manual mode; skipping daemon auto-start")
        elif outcome.skipped_reason == "intent_local_only":
            # Unreachable by construction — this function passes REMOTE_REQUIRED.
            assert False, "intent_local_only reached in REMOTE_REQUIRED path"  # noqa: B011
        elif outcome.skipped_reason is not None and outcome.skipped_reason.startswith("start_failed:"):
            logger.warning("Could not ensure global sync daemon: %s", outcome.skipped_reason)
    except Exception as exc:
        logger.warning("Could not ensure global sync daemon: %s", exc)


def _ensure_dashboard_sync_daemon_for_active_project(*, ensure_daemon: bool = True) -> Path | None:
    """Resolve the active project and keep its dashboard daemon healthy."""
    repo_root = _resolve_repo_root()
    _ensure_dashboard_sync_daemon(repo_root, ensure_daemon=ensure_daemon)
    return repo_root


def _request_dashboard_sync(repo_root: Path | None) -> None:
    """Ask the machine-global sync daemon to flush queued work soon."""
    if repo_root is None or not is_saas_sync_enabled():
        return

    try:
        from .daemon import get_sync_daemon_status

        status = get_sync_daemon_status(timeout=0.2)
        if not status.healthy or not status.url:
            return

        trigger_url = f"{status.url.rstrip('/')}/api/sync/trigger"
        if status.token:
            trigger_url = f"{trigger_url}?token={urllib.parse.quote(status.token)}"

        with urllib.request.urlopen(trigger_url, timeout=0.2) as response:  # nosec B310 — trigger_url is always the localhost dashboard endpoint
            if response.status not in {200, 202}:
                logger.debug("Dashboard sync trigger returned HTTP %s", response.status)
    except Exception as exc:
        logger.debug("Dashboard sync trigger skipped: %s", exc)


def _resolve_mission_id_for_slug(repo_root: Path | None, mission_slug: str | None) -> str | None:
    """Best-effort lookup of the canonical mission_id for a mission slug."""
    if repo_root is None or not mission_slug:
        return None

    feature_dir = repo_root / "kitty-specs" / mission_slug
    if not feature_dir.is_dir():
        return None

    try:
        from specify_cli.mission_metadata import resolve_mission_identity

        return resolve_mission_identity(feature_dir).mission_id
    except Exception as exc:
        logger.debug("Could not resolve mission_id for %s: %s", mission_slug, exc)
        return None


def _publish_event_via_sync_daemon(event: dict[str, Any], repo_root: Path | None) -> None:
    """Best-effort real-time publish through the machine-global sync daemon."""
    if repo_root is None or not is_saas_sync_enabled():
        return

    try:
        from .daemon import get_sync_daemon_status

        status = get_sync_daemon_status(timeout=0.2)
        if not status.healthy or not status.url or not status.token:
            return

        request = urllib.request.Request(
            f"{status.url.rstrip('/')}/api/sync/publish",
            data=json.dumps({"token": status.token, "event": event}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=0.5) as response:  # nosec B310 — request URL is localhost sync daemon endpoint
            if response.status not in {200, 202}:
                logger.debug("Sync daemon publish returned HTTP %s", response.status)
    except Exception as exc:
        logger.debug("Sync daemon publish skipped: %s", exc)


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
                repo_root = _resolve_repo_root()

                # Ensure identity exists before creating emitter
                try:
                    from specify_cli.identity.project import ensure_identity

                    if repo_root is not None:
                        ensure_identity(repo_root)
                    else:
                        logger.debug("Non-project context; identity will be empty")
                except Exception as e:
                    logger.warning(f"Could not ensure identity: {e}")

                from .emitter import EventEmitter

                _emitter = EventEmitter()
                try:
                    from .runtime import get_runtime

                    get_runtime().attach_emitter(_emitter)
                except Exception as exc:
                    logger.warning("Could not attach emitter to sync runtime: %s", exc)
    return _emitter


def reset_emitter() -> None:
    """Reset the singleton (for testing only)."""
    global _emitter
    with _lock:
        _emitter = None


# ── Convenience Functions ─────────────────────────────────────


def emit_wp_status_changed(
    wp_id: str,
    from_lane: str,
    to_lane: str,
    actor: str = "user",
    mission_slug: str | None = None,
    mission_id: str | None = None,
    causation_id: str | None = None,
    policy_metadata: dict[str, Any] | None = None,
    force: bool = False,
    reason: str | None = None,
    review_ref: str | None = None,
    execution_mode: str | None = None,
    evidence: dict[str, Any] | None = None,
    *,
    ensure_daemon: bool = True,
) -> dict[str, Any] | None:
    """Emit WPStatusChanged event via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project(ensure_daemon=ensure_daemon)
    resolved_mission_id = mission_id or _resolve_mission_id_for_slug(repo_root, mission_slug)
    event = get_emitter().emit_wp_status_changed(
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        actor=actor,
        mission_slug=mission_slug,
        mission_id=resolved_mission_id,
        causation_id=causation_id,
        policy_metadata=policy_metadata,
        force=force,
        reason=reason,
        review_ref=review_ref,
        execution_mode=execution_mode,
        evidence=evidence,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event


def emit_wp_created(
    wp_id: str,
    title: str,
    mission_slug: str,
    mission_id: str | None = None,
    dependencies: list[str] | None = None,
    causation_id: str | None = None,
    *,
    ensure_daemon: bool = True,
) -> dict[str, Any] | None:
    """Emit WPCreated event via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project(ensure_daemon=ensure_daemon)
    resolved_mission_id = mission_id or _resolve_mission_id_for_slug(repo_root, mission_slug)
    event = get_emitter().emit_wp_created(
        wp_id=wp_id,
        title=title,
        mission_slug=mission_slug,
        mission_id=resolved_mission_id,
        dependencies=dependencies,
        causation_id=causation_id,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event


def emit_wp_assigned(
    wp_id: str,
    agent_id: str,
    phase: str,
    retry_count: int = 0,
    causation_id: str | None = None,
    *,
    ensure_daemon: bool = True,
) -> dict[str, Any] | None:
    """Emit WPAssigned event via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project(ensure_daemon=ensure_daemon)
    event = get_emitter().emit_wp_assigned(
        wp_id=wp_id,
        agent_id=agent_id,
        phase=phase,
        retry_count=retry_count,
        causation_id=causation_id,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event


def emit_mission_created(
    mission_slug: str,
    mission_number: int | None,
    target_branch: str,
    wp_count: int,
    mission_type: str = "software-dev",
    friendly_name: str | None = None,
    purpose_tldr: str | None = None,
    purpose_context: str | None = None,
    created_at: str | None = None,
    causation_id: str | None = None,
    mission_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit MissionCreated event via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project()
    event = get_emitter().emit_mission_created(
        mission_slug=mission_slug,
        mission_number=mission_number,
        mission_type=mission_type,
        target_branch=target_branch,
        wp_count=wp_count,
        friendly_name=friendly_name,
        purpose_tldr=purpose_tldr,
        purpose_context=purpose_context,
        created_at=created_at,
        causation_id=causation_id,
        mission_id=mission_id,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event



def emit_mission_closed(
    mission_slug: str,
    total_wps: int,
    completed_at: str | None = None,
    total_duration: str | None = None,
    causation_id: str | None = None,
    mission_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit MissionClosed event via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project()
    event = get_emitter().emit_mission_closed(
        mission_slug=mission_slug,
        total_wps=total_wps,
        completed_at=completed_at,
        total_duration=total_duration,
        causation_id=causation_id,
        mission_id=mission_id,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event



def emit_history_added(
    wp_id: str,
    entry_type: str,
    entry_content: str,
    author: str = "user",
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit HistoryAdded event via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project()
    event = get_emitter().emit_history_added(
        wp_id=wp_id,
        entry_type=entry_type,
        entry_content=entry_content,
        author=author,
        causation_id=causation_id,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event


def emit_error_logged(
    error_type: str,
    error_message: str,
    wp_id: str | None = None,
    stack_trace: str | None = None,
    agent_id: str | None = None,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit ErrorLogged event via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project()
    event = get_emitter().emit_error_logged(
        error_type=error_type,
        error_message=error_message,
        wp_id=wp_id,
        stack_trace=stack_trace,
        agent_id=agent_id,
        causation_id=causation_id,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event


def emit_dependency_resolved(
    wp_id: str,
    dependency_wp_id: str,
    resolution_type: str,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit DependencyResolved event via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project()
    event = get_emitter().emit_dependency_resolved(
        wp_id=wp_id,
        dependency_wp_id=dependency_wp_id,
        resolution_type=resolution_type,
        causation_id=causation_id,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event


def emit_token_usage_recorded(
    mission_id: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    estimated_cost_usd: float,
    source: str,
    *,
    run_id: str | None = None,
    step_id: str | None = None,
    wp_id: str | None = None,
    phase_name: str | None = None,
    actor: dict[str, Any] | None = None,
    provider: str | None = None,
    model: str | None = None,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit TokenUsageRecorded via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project()
    event = get_emitter().emit_token_usage_recorded(
        mission_id=mission_id,
        run_id=run_id,
        step_id=step_id,
        wp_id=wp_id,
        phase_name=phase_name,
        actor=actor,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        source=source,
        causation_id=causation_id,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event


def emit_diff_summary_recorded(
    mission_id: str,
    base_ref: str,
    head_ref: str,
    files_changed: int,
    lines_added: int,
    lines_deleted: int,
    source: str,
    *,
    run_id: str | None = None,
    step_id: str | None = None,
    wp_id: str | None = None,
    phase_name: str | None = None,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
    """Emit DiffSummaryRecorded via singleton."""
    repo_root = _ensure_dashboard_sync_daemon_for_active_project()
    event = get_emitter().emit_diff_summary_recorded(
        mission_id=mission_id,
        run_id=run_id,
        step_id=step_id,
        wp_id=wp_id,
        phase_name=phase_name,
        base_ref=base_ref,
        head_ref=head_ref,
        files_changed=files_changed,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        source=source,
        causation_id=causation_id,
    )
    if event is not None:
        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)
    return event
