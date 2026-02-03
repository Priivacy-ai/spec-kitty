"""EventEmitter: core event creation and dispatch for CLI sync."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ulid import ULID

from .clock import LamportClock
from .config import SyncConfig
from .queue import OfflineQueue

if TYPE_CHECKING:
    from .auth import AuthClient
    from .client import WebSocketClient

logger = logging.getLogger(__name__)


# Valid enum values matching events.schema.json
VALID_EVENT_TYPES = frozenset({
    "WPStatusChanged",
    "WPCreated",
    "WPAssigned",
    "FeatureCreated",
    "FeatureCompleted",
    "HistoryAdded",
    "ErrorLogged",
    "DependencyResolved",
})

VALID_AGGREGATE_TYPES = frozenset({"WorkPackage", "Feature"})

VALID_STATUSES = frozenset({"planned", "doing", "for_review", "done"})
VALID_PHASES = frozenset({"implementation", "review"})
VALID_ERROR_TYPES = frozenset({"validation", "runtime", "network", "auth", "unknown"})
VALID_ENTRY_TYPES = frozenset({"note", "review", "error", "comment"})
VALID_RESOLUTION_TYPES = frozenset({"completed", "skipped", "merged"})


class ConnectionStatus:
    """Connection status constants."""

    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    OFFLINE = "Offline"
    BATCH_MODE = "Offline - Batch Mode"


@dataclass
class EventEmitter:
    """Core event emitter managing event creation and dispatch.

    Manages Lamport clock, authentication context, offline queue,
    and optional WebSocket client for real-time sync.

    Use get_emitter() from events.py to access the singleton instance.
    Do NOT instantiate directly in production code.
    """

    clock: LamportClock = field(default_factory=LamportClock.load)
    config: SyncConfig = field(default_factory=SyncConfig)
    queue: OfflineQueue = field(default_factory=OfflineQueue)
    _auth: AuthClient | None = field(default=None, repr=False)
    ws_client: WebSocketClient | None = field(default=None, repr=False)

    @property
    def auth(self) -> AuthClient:
        """Lazy-load AuthClient to avoid circular imports."""
        if self._auth is None:
            from .auth import AuthClient
            self._auth = AuthClient()
        return self._auth

    def get_connection_status(self) -> str:
        """Return current connection status."""
        if self.ws_client is not None:
            return self.ws_client.get_status()
        return ConnectionStatus.OFFLINE

    def generate_causation_id(self) -> str:
        """Generate a ULID for correlating batch events."""
        return str(ULID())

    # ── Event Builders ────────────────────────────────────────────

    def emit_wp_status_changed(
        self,
        wp_id: str,
        previous_status: str,
        new_status: str,
        changed_by: str = "user",
        feature_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit WPStatusChanged event (FR-008)."""
        payload = {
            "wp_id": wp_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "changed_by": changed_by,
            "feature_slug": feature_slug,
        }
        return self._emit(
            event_type="WPStatusChanged",
            aggregate_id=wp_id,
            aggregate_type="WorkPackage",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_wp_created(
        self,
        wp_id: str,
        title: str,
        feature_slug: str,
        dependencies: list[str] | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit WPCreated event (FR-009)."""
        payload = {
            "wp_id": wp_id,
            "title": title,
            "dependencies": dependencies or [],
            "feature_slug": feature_slug,
        }
        return self._emit(
            event_type="WPCreated",
            aggregate_id=wp_id,
            aggregate_type="WorkPackage",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_wp_assigned(
        self,
        wp_id: str,
        agent_id: str,
        phase: str,
        retry_count: int = 0,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit WPAssigned event (FR-010)."""
        payload = {
            "wp_id": wp_id,
            "agent_id": agent_id,
            "phase": phase,
            "retry_count": retry_count,
        }
        return self._emit(
            event_type="WPAssigned",
            aggregate_id=wp_id,
            aggregate_type="WorkPackage",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_feature_created(
        self,
        feature_slug: str,
        feature_number: str,
        target_branch: str,
        wp_count: int,
        created_at: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit FeatureCreated event (FR-011)."""
        payload: dict[str, Any] = {
            "feature_slug": feature_slug,
            "feature_number": feature_number,
            "target_branch": target_branch,
            "wp_count": wp_count,
        }
        if created_at is not None:
            payload["created_at"] = created_at
        return self._emit(
            event_type="FeatureCreated",
            aggregate_id=feature_slug,
            aggregate_type="Feature",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_feature_completed(
        self,
        feature_slug: str,
        total_wps: int,
        completed_at: str | None = None,
        total_duration: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit FeatureCompleted event (FR-012)."""
        payload: dict[str, Any] = {
            "feature_slug": feature_slug,
            "total_wps": total_wps,
        }
        if completed_at is not None:
            payload["completed_at"] = completed_at
        if total_duration is not None:
            payload["total_duration"] = total_duration
        return self._emit(
            event_type="FeatureCompleted",
            aggregate_id=feature_slug,
            aggregate_type="Feature",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_history_added(
        self,
        wp_id: str,
        entry_type: str,
        entry_content: str,
        author: str = "user",
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit HistoryAdded event (FR-013)."""
        payload = {
            "wp_id": wp_id,
            "entry_type": entry_type,
            "entry_content": entry_content,
            "author": author,
        }
        return self._emit(
            event_type="HistoryAdded",
            aggregate_id=wp_id,
            aggregate_type="WorkPackage",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_error_logged(
        self,
        error_type: str,
        error_message: str,
        wp_id: str | None = None,
        stack_trace: str | None = None,
        agent_id: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit ErrorLogged event (FR-014)."""
        payload: dict[str, Any] = {
            "error_type": error_type,
            "error_message": error_message,
        }
        if wp_id is not None:
            payload["wp_id"] = wp_id
        if stack_trace is not None:
            payload["stack_trace"] = stack_trace
        if agent_id is not None:
            payload["agent_id"] = agent_id

        aggregate_id = wp_id if wp_id is not None else "error"
        aggregate_type = "WorkPackage" if wp_id is not None else "Feature"
        return self._emit(
            event_type="ErrorLogged",
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            payload=payload,
            causation_id=causation_id,
        )

    def emit_dependency_resolved(
        self,
        wp_id: str,
        dependency_wp_id: str,
        resolution_type: str,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit DependencyResolved event (FR-015)."""
        payload = {
            "wp_id": wp_id,
            "dependency_wp_id": dependency_wp_id,
            "resolution_type": resolution_type,
        }
        return self._emit(
            event_type="DependencyResolved",
            aggregate_id=wp_id,
            aggregate_type="WorkPackage",
            payload=payload,
            causation_id=causation_id,
        )

    # ── Internal dispatch ─────────────────────────────────────────

    def _emit(
        self,
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        payload: dict[str, Any],
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Build, validate, and route an event. Non-blocking: never raises."""
        try:
            # Tick clock for causal ordering
            clock_value = self.clock.tick()

            # Resolve team_slug from auth
            team_slug = self._get_team_slug()

            # Build event dict
            event: dict[str, Any] = {
                "event_id": str(ULID()),
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "aggregate_type": aggregate_type,
                "payload": payload,
                "node_id": self.clock.node_id,
                "lamport_clock": clock_value,
                "causation_id": causation_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "team_slug": team_slug,
            }

            # Validate event structure
            if not self._validate_event(event):
                return None

            # Route: WebSocket if connected and authenticated, else queue
            self._route_event(event)
            return event

        except Exception as e:
            logger.warning("Event emission failed: %s", e)
            return None

    def _get_team_slug(self) -> str:
        """Get team_slug from AuthClient. Returns 'local' if unavailable."""
        try:
            if hasattr(self.auth, "get_team_slug"):
                slug = self.auth.get_team_slug()
                if slug:
                    return slug
        except Exception as e:
            logger.warning("Could not resolve team_slug: %s", e)
        return "local"

    def _validate_event(self, event: dict[str, Any]) -> bool:
        """Validate event against schema constraints.

        Returns True if valid, False if invalid (logged and discarded).
        """
        try:
            # Check required fields
            required = {
                "event_id", "event_type", "aggregate_id", "aggregate_type",
                "payload", "node_id", "lamport_clock", "timestamp", "team_slug",
            }
            missing = required - set(event.keys())
            if missing:
                logger.warning("Event missing required fields: %s", missing)
                return False

            # Check event_type is valid
            if event["event_type"] not in VALID_EVENT_TYPES:
                logger.warning("Invalid event_type: %s", event["event_type"])
                return False

            # Check aggregate_type is valid
            if event["aggregate_type"] not in VALID_AGGREGATE_TYPES:
                logger.warning("Invalid aggregate_type: %s", event["aggregate_type"])
                return False

            # Check lamport_clock is non-negative integer
            if not isinstance(event["lamport_clock"], int) or event["lamport_clock"] < 0:
                logger.warning("Invalid lamport_clock: %s", event["lamport_clock"])
                return False

            return True

        except Exception as e:
            logger.warning("Event validation error: %s", e)
            return False

    def _route_event(self, event: dict[str, Any]) -> bool:
        """Route event to WebSocket or offline queue.

        Returns True if event was sent/queued successfully.
        """
        try:
            # Check if authenticated
            authenticated = False
            try:
                if hasattr(self.auth, "is_authenticated"):
                    authenticated = self.auth.is_authenticated()
            except Exception:
                pass

            # If authenticated and WebSocket connected, send directly
            if authenticated and self.ws_client is not None and self.ws_client.connected:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule send for later if we're in an async context
                        asyncio.ensure_future(self.ws_client.send_event(event))
                    else:
                        loop.run_until_complete(self.ws_client.send_event(event))
                    return True
                except Exception as e:
                    logger.warning("WebSocket send failed, queueing: %s", e)
                    # Fall through to queue

            # Queue event for later sync
            return self.queue.queue_event(event)

        except Exception as e:
            logger.warning("Event routing failed: %s", e)
            return False
