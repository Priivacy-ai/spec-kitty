"""EventEmitter: core event creation and dispatch for CLI sync."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import ulid
from rich.console import Console

from specify_cli.spec_kitty_events import normalize_event_id as _normalize_event_id

from .clock import LamportClock
from .config import SyncConfig
from .queue import OfflineQueue

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .auth import AuthClient
    from .client import WebSocketClient
    from .git_metadata import GitMetadata, GitMetadataResolver
    from .project_identity import ProjectIdentity

_console = Console(stderr=True)


def _get_project_identity() -> "ProjectIdentity":
    """Lazily load and resolve project identity.

    Uses lazy import to prevent circular dependency issues.
    Returns empty ProjectIdentity in non-project contexts.
    """
    from .project_identity import ensure_identity, ProjectIdentity
    from specify_cli.tasks_support import find_repo_root, TaskCliError

    try:
        repo_root = find_repo_root()
    except TaskCliError:
        # Non-project context; return empty identity to trigger queue-only
        return ProjectIdentity()

    return ensure_identity(repo_root)


def _create_git_resolver() -> "GitMetadataResolver":
    """Lazily create GitMetadataResolver with repo root and config override."""
    from .git_metadata import GitMetadataResolver
    from .project_identity import ensure_identity
    from specify_cli.tasks_support import find_repo_root, TaskCliError

    try:
        repo_root = find_repo_root()
    except TaskCliError:
        # Non-project context; return resolver that will produce None values
        return GitMetadataResolver(repo_root=Path.cwd())

    identity = ensure_identity(repo_root)
    return GitMetadataResolver(
        repo_root=repo_root,
        repo_slug_override=identity.repo_slug,
    )


# Load the contract schema once for payload-level validation
_SCHEMA: dict[str, Any] | None = None
_SCHEMA_PATH = Path(__file__).resolve().parent / "_events_schema.json"


def _load_contract_schema() -> dict[str, Any] | None:
    """Load the events JSON schema from the contracts directory.

    Falls back to the kitty-specs contract if available, otherwise returns None.
    """
    global _SCHEMA
    if _SCHEMA is not None:
        return _SCHEMA

    # Try multiple locations for the schema
    candidates = [
        Path(__file__).resolve().parent / "_events_schema.json",
    ]
    for path in candidates:
        if path.exists():
            with open(path) as f:
                _SCHEMA = json.load(f)
            return _SCHEMA

    return None


# Payload validation rules derived from contracts/events.schema.json
# Each entry maps event_type -> (required_fields, field_validators)
_ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")  # kept for test compat

# Broader ID validation via normalize_event_id (accepts ULID + UUID)
_WP_ID_PATTERN = re.compile(r"^WP\d{2}$")
_FEATURE_SLUG_PATTERN = re.compile(r"^\d{3}-[a-z0-9-]+$")
_FEATURE_NUMBER_PATTERN = re.compile(r"^\d{3}$")


def _is_datetime_string(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        candidate = value.replace("Z", "+00:00")
        datetime.fromisoformat(candidate)
        return True
    except ValueError:
        return False


def _is_nullable_string(value: Any) -> bool:
    return value is None or (isinstance(value, str))


_PAYLOAD_RULES: dict[str, dict[str, Any]] = {
    "WPStatusChanged": {
        "required": {"wp_id", "from_lane", "to_lane"},
        "validators": {
            "wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            "from_lane": lambda v: (
                v in {"planned", "claimed", "in_progress", "for_review", "done", "blocked", "canceled"}
            ),
            "to_lane": lambda v: (
                v in {"planned", "claimed", "in_progress", "for_review", "done", "blocked", "canceled"}
            ),
            "actor": lambda v: isinstance(v, str) if v is not None else True,
            "feature_slug": lambda v: _is_nullable_string(v),
            "policy_metadata": lambda v: v is None or isinstance(v, dict),
        },
    },
    "WPCreated": {
        "required": {"wp_id", "title", "feature_slug"},
        "validators": {
            "wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            "title": lambda v: isinstance(v, str) and len(v) >= 1,
            "feature_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "dependencies": lambda v: (
                isinstance(v, list) and all(isinstance(item, str) and _WP_ID_PATTERN.match(item) for item in v)
            ),
        },
    },
    "WPAssigned": {
        "required": {"wp_id", "agent_id", "phase"},
        "validators": {
            "wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            "agent_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "phase": lambda v: v in {"implementation", "review"},
            "retry_count": lambda v: isinstance(v, int) and v >= 0,
        },
    },
    "FeatureCreated": {
        "required": {"feature_slug", "feature_number", "target_branch", "wp_count"},
        "validators": {
            "feature_slug": lambda v: isinstance(v, str) and bool(_FEATURE_SLUG_PATTERN.match(v)),
            "feature_number": lambda v: isinstance(v, str) and bool(_FEATURE_NUMBER_PATTERN.match(v)),
            "target_branch": lambda v: isinstance(v, str) and len(v) >= 1,
            "wp_count": lambda v: isinstance(v, int) and v >= 0,
            "created_at": lambda v: _is_datetime_string(v),
        },
    },
    "FeatureCompleted": {
        "required": {"feature_slug", "total_wps"},
        "validators": {
            "feature_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "total_wps": lambda v: isinstance(v, int) and v >= 0,
            "completed_at": lambda v: _is_datetime_string(v),
            "total_duration": lambda v: _is_nullable_string(v),
        },
    },
    "HistoryAdded": {
        "required": {"wp_id", "entry_type", "entry_content"},
        "validators": {
            "wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            "entry_type": lambda v: v in {"note", "review", "error", "comment"},
            "entry_content": lambda v: isinstance(v, str) and len(v) >= 1,
            "author": lambda v: isinstance(v, str) if v is not None else True,
        },
    },
    "ErrorLogged": {
        "required": {"error_type", "error_message"},
        "validators": {
            "error_type": lambda v: v in {"validation", "runtime", "network", "auth", "unknown"},
            "error_message": lambda v: isinstance(v, str) and len(v) >= 1,
            "wp_id": _is_nullable_string,
            "stack_trace": _is_nullable_string,
            "agent_id": _is_nullable_string,
        },
    },
    "DependencyResolved": {
        "required": {"wp_id", "dependency_wp_id", "resolution_type"},
        "validators": {
            "wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            "dependency_wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            "resolution_type": lambda v: v in {"completed", "skipped", "merged"},
        },
    },
}

VALID_EVENT_TYPES = frozenset(_PAYLOAD_RULES.keys())
VALID_AGGREGATE_TYPES = frozenset({"WorkPackage", "Feature"})


class ConnectionStatus:
    """Connection status constants matching WP spec."""

    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    OFFLINE = "Offline"
    BATCH_MODE = "OfflineBatchMode"


def _generate_ulid() -> str:
    """Generate a new ULID string.

    Uses python-ulid (the project dependency). The WP spec references
    ulid.new().str which is the ulid-py package API. We prefer that
    when available, otherwise fall back to python-ulid's ULID().
    """
    if hasattr(ulid, "new"):
        return str(cast(Any, ulid.new()).str)
    return str(ulid.ULID())


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
    _identity: "ProjectIdentity | None" = field(default=None, repr=False)
    _git_resolver: "GitMetadataResolver | None" = field(default=None, repr=False)
    _background_tasks: set[asyncio.Task[Any]] = field(default_factory=set, repr=False)

    def _track_task(self, task: Any) -> None:
        """Retain background task references until completion."""
        if task is None or not hasattr(task, "add_done_callback"):
            return
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _get_identity(self) -> "ProjectIdentity":
        """Get cached project identity, lazily loading on first access.

        Identity is resolved once per emitter lifetime to avoid repeated I/O.
        """
        if self._identity is None:
            self._identity = _get_project_identity()
        return self._identity

    def _get_git_metadata(self) -> "GitMetadata":
        """Get per-event git metadata via cached resolver.

        Never raises: returns GitMetadata with None fields on any error.
        """
        from .git_metadata import GitMetadata

        try:
            if self._git_resolver is None:
                self._git_resolver = _create_git_resolver()
            return self._git_resolver.resolve()
        except Exception as e:
            logger.debug("Git metadata resolution failed: %s", e)
            return GitMetadata()

    @property
    def auth(self) -> AuthClient:
        """Lazy-load AuthClient to avoid circular imports."""
        if self._auth is None:
            from .auth import AuthClient as _AuthClient

            self._auth = cast(type[Any], _AuthClient)()
        return self._auth

    def get_connection_status(self) -> str:
        """Return current connection status."""
        if self.ws_client is not None:
            return self.ws_client.get_status()
        return ConnectionStatus.OFFLINE

    def generate_causation_id(self) -> str:
        """Generate a ULID for correlating batch events."""
        return _generate_ulid()

    # ── Event Builders ────────────────────────────────────────────

    def emit_wp_status_changed(
        self,
        wp_id: str,
        from_lane: str,
        to_lane: str,
        actor: str = "user",
        feature_slug: str | None = None,
        causation_id: str | None = None,
        policy_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Emit WPStatusChanged event (FR-008)."""
        payload = {
            "wp_id": wp_id,
            "from_lane": from_lane,
            "to_lane": to_lane,
            "actor": actor,
            "feature_slug": feature_slug,
            "policy_metadata": policy_metadata,
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
            logger.debug(
                "Emitting %s event with Lamport clock: %d",
                event_type,
                clock_value,
            )

            # Resolve identity and team_slug
            identity = self._get_identity()
            team_slug = self._get_team_slug()

            # Resolve per-event git metadata
            git_meta = self._get_git_metadata()

            # Build event dict with identity fields
            event: dict[str, Any] = {
                "event_id": _generate_ulid(),
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "aggregate_type": aggregate_type,
                "payload": payload,
                "node_id": self.clock.node_id,
                "lamport_clock": clock_value,
                "causation_id": causation_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "team_slug": team_slug,
                "project_uuid": str(identity.project_uuid) if identity.project_uuid else None,
                "project_slug": identity.project_slug,
                # Git correlation fields (Feature 033)
                "git_branch": git_meta.git_branch,
                "head_commit_sha": git_meta.head_commit_sha,
                "repo_slug": git_meta.repo_slug,
            }

            # Validate event structure and payload
            if not self._validate_event(event):
                return None

            # Check project_uuid: if missing, queue only (no WebSocket send)
            if not event.get("project_uuid"):
                _console.print("[yellow]Warning: Event missing project_uuid; queued locally only[/yellow]")
                self.queue.queue_event(event)
                return event

            # Route: WebSocket if connected and authenticated, else queue
            self._route_event(event)
            return event

        except Exception as e:
            _console.print(f"[yellow]Warning: Event emission failed: {e}[/yellow]")
            return None

    def _get_team_slug(self) -> str:
        """Get team_slug from AuthClient. Returns 'local' if unavailable."""
        try:
            if hasattr(self.auth, "get_team_slug"):
                slug = self.auth.get_team_slug()
                if slug:
                    return slug
        except Exception as e:
            _console.print(f"[yellow]Warning: Could not resolve team_slug: {e}[/yellow]")
        return "local"

    def _validate_event(self, event: dict[str, Any]) -> bool:
        """Validate event against spec-kitty-events models and payload schemas.

        Validates both the envelope (via spec-kitty-events Event model) and
        the per-event-type payload (via rules derived from events.schema.json).
        Returns True if valid, False if invalid (warned and discarded).
        """
        try:
            from specify_cli.spec_kitty_events import Event as EventModel

            # 1. Validate envelope via spec-kitty-events Pydantic model
            model_data = {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "aggregate_id": event["aggregate_id"],
                "payload": event["payload"],
                "timestamp": event["timestamp"],
                "node_id": event["node_id"],
                "lamport_clock": event["lamport_clock"],
                "causation_id": event.get("causation_id"),
            }
            EventModel(**model_data)

            # 2. Validate fields the library model doesn't cover
            if not event.get("team_slug"):
                _console.print("[yellow]Warning: Event missing team_slug[/yellow]")
                return False

            if event.get("aggregate_type") not in VALID_AGGREGATE_TYPES:
                _console.print(f"[yellow]Warning: Invalid aggregate_type: {event.get('aggregate_type')}[/yellow]")
                return False

            # 3. Validate event_type is one of the 8 known types
            event_type = event["event_type"]
            if event_type not in VALID_EVENT_TYPES:
                _console.print(f"[yellow]Warning: Unknown event_type: {event_type}[/yellow]")
                return False

            # 3b. Normalize + validate envelope IDs (ULID or UUID accepted)
            try:
                event["event_id"] = _normalize_event_id(event["event_id"])
            except (ValueError, TypeError):
                _console.print(f"[yellow]Warning: Invalid event_id: {event.get('event_id')!r}[/yellow]")
                return False

            causation_id = event.get("causation_id")
            if causation_id is not None:
                try:
                    event["causation_id"] = _normalize_event_id(causation_id)
                except (ValueError, TypeError):
                    _console.print(f"[yellow]Warning: Invalid causation_id: {causation_id!r}[/yellow]")
                    return False

            # Future-proof: normalize correlation_id if present
            correlation_id = event.get("correlation_id")
            if correlation_id is not None:
                try:
                    event["correlation_id"] = _normalize_event_id(correlation_id)
                except (ValueError, TypeError):
                    _console.print(f"[yellow]Warning: Invalid correlation_id: {correlation_id!r}[/yellow]")
                    return False

            # 4. Validate payload against per-event-type rules
            if not self._validate_payload(event_type, event["payload"]):
                return False

            return True

        except Exception as e:
            _console.print(f"[yellow]Warning: Event validation failed: {e}[/yellow]")
            return False

    def _validate_payload(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Validate payload fields against per-event-type schema rules.

        Rules are derived from contracts/events.schema.json definitions.
        """
        rules = _PAYLOAD_RULES.get(event_type)
        if rules is None:
            return True  # No rules = no validation needed

        # Check required fields
        missing = rules["required"] - set(payload.keys())
        if missing:
            _console.print(f"[yellow]Warning: {event_type} payload missing required fields: {missing}[/yellow]")
            return False

        # Run field-level validators
        for field_name, validator in rules["validators"].items():
            if field_name in payload:
                value = payload[field_name]
                if not validator(value):
                    _console.print(
                        f"[yellow]Warning: {event_type} payload field "
                        f"'{field_name}' has invalid value: {value!r}[/yellow]"
                    )
                    return False

        return True

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
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        send_task = asyncio.ensure_future(self.ws_client.send_event(event))
                        self._track_task(send_task)
                    else:
                        loop.run_until_complete(self.ws_client.send_event(event))
                    return True
                except Exception as e:
                    _console.print(f"[yellow]Warning: WebSocket send failed, queueing: {e}[/yellow]")
                    # Fall through to queue

            # Queue event for later sync
            return self.queue.queue_event(event)

        except Exception as e:
            _console.print(f"[yellow]Warning: Event routing failed: {e}[/yellow]")
            return False
