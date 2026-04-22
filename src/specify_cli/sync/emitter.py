"""EventEmitter: core event creation and dispatch for CLI sync.

Outbound SaaS payload contract (FR-024, ADR 2026-04-09-1, WP06):
  All mission-lifecycle events (MissionCreated, MissionClosed,
  MissionOriginBound) use ``aggregate_id = mission_id`` (a ULID) as
  the canonical machine-facing identity.  The human-readable slug and
  numeric identifier survive as display-metadata fields in the payload:

    ``aggregate_id``   — mission_id (ULID) — primary join key for SaaS
    ``payload.mission_id``     — same ULID, for payload-level consumers
    ``payload.mission_slug``   — human slug (display / backward compat)
    ``payload.mission_number`` — int | None (None for pre-merge missions)

  WP-level event emitters (WPStatusChanged, WPCreated, WPAssigned,
  DependencyResolved, HistoryAdded) are NOT affected; they use
  ``aggregate_id = wp_id``.

  Error events use ``aggregate_id = wp_id`` or ``"error"``; also
  NOT affected.

  The SaaS-side schema update is tracked in spec-kitty-saas#47 (WP12).
  Remove ``mission_slug`` display fields after that PR lands.
"""

from __future__ import annotations

import json
import logging
import platform
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ulid
from rich.console import Console

from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.spec_kitty_events import normalize_event_id as _normalize_event_id

from .clock import LamportClock
from .config import SyncConfig
from .queue import OfflineQueue
from .routing import is_sync_enabled_for_checkout

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .client import WebSocketClient
    from .git_metadata import GitMetadata, GitMetadataResolver
    from .project_identity import ProjectIdentity

_console = Console(stderr=True)


def _get_project_identity() -> ProjectIdentity:
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


def _create_git_resolver() -> GitMetadataResolver:
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
_SCHEMA: dict | None = None
_SCHEMA_PATH = Path(__file__).resolve().parent / "_events_schema.json"


def _load_contract_schema() -> dict | None:
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

_WP_ID_PATTERN = re.compile(r"^WP\d{2}$")
_FEATURE_SLUG_PATTERN = re.compile(
    r"^(?:\d{3}-[a-z0-9-]+|[a-z0-9]+(?:-[a-z0-9]+)*-[0-9A-HJKMNP-TV-Z]{8})$"
)
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
    "BuildRegistered": {
        "required": {"build_id", "repo_slug"},
        "validators": {
            "build_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "node_id": _is_nullable_string,
            "project_uuid": _is_nullable_string,
            "project_slug": _is_nullable_string,
            "project_name": _is_nullable_string,
            "repo_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "branch": _is_nullable_string,
            "head_commit": _is_nullable_string,
            "developer_name": _is_nullable_string,
            "machine_name": _is_nullable_string,
            "workspace_path": _is_nullable_string,
        },
    },
    "BuildHeartbeat": {
        "required": {"build_id", "repo_slug"},
        "validators": {
            "build_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "node_id": _is_nullable_string,
            "project_uuid": _is_nullable_string,
            "project_slug": _is_nullable_string,
            "project_name": _is_nullable_string,
            "repo_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "branch": _is_nullable_string,
            "head_commit": _is_nullable_string,
            "developer_name": _is_nullable_string,
            "machine_name": _is_nullable_string,
            "workspace_path": _is_nullable_string,
            "remote_head": _is_nullable_string,
            "ahead_of_remote": lambda v: isinstance(v, int) and v >= 0,
            "behind_remote": lambda v: isinstance(v, int) and v >= 0,
            "recent_commits": lambda v: isinstance(v, list),
        },
    },
    "WPStatusChanged": {
        "required": {"wp_id", "from_lane", "to_lane"},
        "validators": {
            "wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            "from_lane": lambda v: v in {"planned", "claimed", "in_progress", "in_review", "for_review", "approved", "done", "blocked", "canceled"},
            "to_lane": lambda v: v in {"planned", "claimed", "in_progress", "in_review", "for_review", "approved", "done", "blocked", "canceled"},
            "actor": lambda v: isinstance(v, str) if v is not None else True,
            "mission_slug": lambda v: _is_nullable_string(v),
            "policy_metadata": lambda v: v is None or isinstance(v, dict),
        },
    },
    "WPCreated": {
        "required": {"wp_id", "title", "mission_slug"},
        "validators": {
            "wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            "title": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "dependencies": lambda v: isinstance(v, list)
            and all(isinstance(item, str) and _WP_ID_PATTERN.match(item) for item in v),
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
    "MissionCreated": {
        # mission_number is int | None (FR-044, WP02): None for pre-merge,
        # int for post-merge.  mission_id (ULID) is the aggregate identity.
        "required": {"mission_slug", "mission_number", "target_branch", "wp_count"},
        "validators": {
            "mission_slug": lambda v: isinstance(v, str) and bool(_FEATURE_SLUG_PATTERN.match(v)),
            "mission_number": lambda v: v is None or (isinstance(v, int) and v >= 0),
            "target_branch": lambda v: isinstance(v, str) and len(v) >= 1,
            "wp_count": lambda v: isinstance(v, int) and v >= 0,
            "created_at": lambda v: _is_datetime_string(v),
        },
    },
    "MissionClosed": {
        "required": {"mission_slug", "total_wps"},
        "validators": {
            "mission_slug": lambda v: isinstance(v, str) and len(v) >= 1,
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
    # WP04: Dossier events
    "MissionDossierArtifactIndexed": {
        "required": {"mission_slug", "artifact_key", "artifact_class", "relative_path", "content_hash_sha256", "size_bytes", "required_status"},
        "validators": {
            "mission_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "artifact_key": lambda v: isinstance(v, str) and len(v) >= 1,
            "artifact_class": lambda v: v in {"input", "workflow", "output", "evidence", "policy", "runtime", "other"},
            "relative_path": lambda v: isinstance(v, str) and len(v) >= 1,
            "content_hash_sha256": lambda v: isinstance(v, str) and bool(re.match(r"^[a-f0-9]{64}$", v)),
            "size_bytes": lambda v: isinstance(v, int) and v >= 0,
            "wp_id": _is_nullable_string,
            "step_id": _is_nullable_string,
            "required_status": lambda v: v in {"required", "optional"},
        },
    },
    "MissionDossierArtifactMissing": {
        "required": {"mission_slug", "artifact_key", "artifact_class", "expected_path_pattern", "reason_code", "blocking"},
        "validators": {
            "mission_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "artifact_key": lambda v: isinstance(v, str) and len(v) >= 1,
            "artifact_class": lambda v: v in {"input", "workflow", "output", "evidence", "policy", "runtime", "other"},
            "expected_path_pattern": lambda v: isinstance(v, str) and len(v) >= 1,
            "reason_code": lambda v: v in {"not_found", "unreadable", "invalid_format", "deleted_after_scan"},
            "reason_detail": _is_nullable_string,
            "blocking": lambda v: isinstance(v, bool),
        },
    },
    "MissionDossierSnapshotComputed": {
        "required": {"mission_slug", "parity_hash_sha256", "artifact_counts", "completeness_status", "snapshot_id"},
        "validators": {
            "mission_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "parity_hash_sha256": lambda v: isinstance(v, str) and bool(re.match(r"^[a-f0-9]{64}$", v)),
            "artifact_counts": lambda v: isinstance(v, dict),
            "completeness_status": lambda v: v in {"complete", "incomplete", "unknown"},
            "snapshot_id": lambda v: isinstance(v, str) and len(v) >= 1,
        },
    },
    "MissionDossierParityDriftDetected": {
        "required": {"mission_slug", "local_parity_hash", "baseline_parity_hash", "severity"},
        "validators": {
            "mission_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "local_parity_hash": lambda v: isinstance(v, str) and bool(re.match(r"^[a-f0-9]{64}$", v)),
            "baseline_parity_hash": lambda v: isinstance(v, str) and bool(re.match(r"^[a-f0-9]{64}$", v)),
            "missing_in_local": lambda v: isinstance(v, list),
            "missing_in_baseline": lambda v: isinstance(v, list),
            "severity": lambda v: v in {"info", "warning", "error"},
        },
    },
    "MissionOriginBound": {
        "required": {
            "mission_slug", "provider", "external_issue_id",
            "external_issue_key", "external_issue_url", "title",
        },
        "validators": {
            "mission_slug": lambda v: isinstance(v, str) and bool(_FEATURE_SLUG_PATTERN.match(v)),
            "provider": lambda v: v in {"jira", "linear"},
            "external_issue_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "external_issue_key": lambda v: isinstance(v, str) and len(v) >= 1,
            "external_issue_url": lambda v: isinstance(v, str) and len(v) >= 1,
            "title": lambda v: isinstance(v, str) and len(v) >= 1,
        },
    },
}

VALID_EVENT_TYPES = frozenset(_PAYLOAD_RULES.keys())
VALID_AGGREGATE_TYPES = frozenset({"Build", "WorkPackage", "Mission", "MissionDossier"})


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
        return ulid.new().str
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
    ws_client: WebSocketClient | None = field(default=None, repr=False)
    _pending_tasks: set = field(default_factory=set, repr=False)
    _identity: ProjectIdentity | None = field(default=None, repr=False)
    _git_resolver: GitMetadataResolver | None = field(default=None, repr=False)

    def _get_identity(self) -> ProjectIdentity:
        """Get cached project identity, lazily loading on first access.

        Identity is resolved once per emitter lifetime to avoid repeated I/O.
        """
        if self._identity is None:
            self._identity = _get_project_identity()
        return self._identity

    def _get_git_metadata(self) -> GitMetadata:
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

    @staticmethod
    def _is_authenticated() -> bool:
        """Check authentication via the process-wide TokenManager."""
        try:
            from specify_cli.auth import get_token_manager

            return bool(get_token_manager().is_authenticated)
        except Exception:
            return False

    @staticmethod
    def _current_team_slug() -> str | None:
        """Return the preferred ingress team slug (team id) from the active session, if any."""
        try:
            from specify_cli.auth import get_token_manager
            from specify_cli.auth.session import get_private_team_id

            session = get_token_manager().get_current_session()
            if session is None or not session.teams:
                return None
            private_team_id = get_private_team_id(session.teams)
            if private_team_id:
                return private_team_id
            for team in session.teams:
                if team.id == session.default_team_id:
                    return team.id
            return session.teams[0].id
        except Exception:
            return None

    @staticmethod
    def _get_developer_name() -> str | None:
        """Return the current user display name for build lifecycle events."""
        try:
            from specify_cli.auth import get_token_manager

            session = get_token_manager().get_current_session()
            if session is None:
                return None
            if isinstance(session.name, str) and session.name:
                return session.name
            if isinstance(session.email, str) and session.email:
                return session.email
        except Exception:
            return None
        return None

    @staticmethod
    def _get_machine_name() -> str | None:
        """Return a user-facing machine label for build provenance."""
        try:
            machine_name = platform.node().strip()
        except Exception:
            return None
        return machine_name or None

    def _get_workspace_path(self) -> str | None:
        """Return the current checkout root for build provenance."""
        resolver_root = getattr(self._git_resolver, "repo_root", None)
        if isinstance(resolver_root, Path):
            return str(resolver_root.resolve())

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return None

        workspace_path = result.stdout.strip() if result.returncode == 0 else ""
        return str(Path(workspace_path).resolve()) if workspace_path else None

    def get_connection_status(self) -> str:
        """Return current connection status."""
        if self.ws_client is not None:
            return self.ws_client.get_status()
        return ConnectionStatus.OFFLINE

    def generate_causation_id(self) -> str:
        """Generate a ULID for correlating batch events."""
        return _generate_ulid()

    def _build_lifecycle_payload(self) -> dict[str, Any]:
        """Build the common payload used by build lifecycle events."""
        identity = self._get_identity()
        git_meta = self._get_git_metadata()

        return {
            "build_id": identity.build_id,
            "node_id": identity.node_id or self.clock.node_id,
            "project_uuid": str(identity.project_uuid) if identity.project_uuid else None,
            "project_slug": identity.project_slug,
            "project_name": identity.project_slug,
            "repo_slug": git_meta.repo_slug,
            "branch": git_meta.git_branch,
            "head_commit": git_meta.head_commit_sha,
            "developer_name": self._get_developer_name(),
            "machine_name": self._get_machine_name(),
            "workspace_path": self._get_workspace_path(),
        }

    # ── Event Builders ────────────────────────────────────────────

    def emit_build_registered(
        self,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit BuildRegistered for the current project/build identity."""
        identity = self._get_identity()
        payload = self._build_lifecycle_payload()
        aggregate_id = identity.build_id or identity.node_id or "build"
        return self._emit(
            event_type="BuildRegistered",
            aggregate_id=aggregate_id,
            aggregate_type="Build",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_build_heartbeat(
        self,
        remote_head: str | None = None,
        ahead_of_remote: int | None = None,
        behind_remote: int | None = None,
        recent_commits: list[str] | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit BuildHeartbeat for the current project/build identity."""
        identity = self._get_identity()
        payload = self._build_lifecycle_payload()
        if remote_head is not None:
            payload["remote_head"] = remote_head
        if ahead_of_remote is not None:
            payload["ahead_of_remote"] = ahead_of_remote
        if behind_remote is not None:
            payload["behind_remote"] = behind_remote
        if recent_commits is not None:
            payload["recent_commits"] = recent_commits

        aggregate_id = identity.build_id or identity.node_id or "build"
        return self._emit(
            event_type="BuildHeartbeat",
            aggregate_id=aggregate_id,
            aggregate_type="Build",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_wp_status_changed(
        self,
        wp_id: str,
        from_lane: str,
        to_lane: str,
        actor: str = "user",
        mission_slug: str | None = None,
        mission_id: str | None = None,
        causation_id: str | None = None,
        policy_metadata: dict | None = None,
    ) -> dict[str, Any] | None:
        """Emit WPStatusChanged event (FR-008)."""
        payload = {
            "wp_id": wp_id,
            "from_lane": from_lane,
            "to_lane": to_lane,
            "actor": actor,
            "mission_slug": mission_slug,
            "policy_metadata": policy_metadata,
        }
        if mission_id is not None:
            payload["mission_id"] = mission_id
        return self._emit(
            event_type="WPStatusChanged",
            aggregate_id=wp_id,
            aggregate_type="WorkPackage",
            payload=payload,
            causation_id=causation_id,
            envelope_fields={
                "from_lane": from_lane,
                "to_lane": to_lane,
                "actor": actor,
            },
        )

    def emit_wp_created(
        self,
        wp_id: str,
        title: str,
        mission_slug: str,
        mission_id: str | None = None,
        dependencies: list[str] | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit WPCreated event (FR-009)."""
        payload = {
            "wp_id": wp_id,
            "title": title,
            "dependencies": dependencies or [],
            "mission_slug": mission_slug,
        }
        if mission_id is not None:
            payload["mission_id"] = mission_id
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

    def emit_mission_created(
        self,
        mission_slug: str,
        mission_number: int | None,
        target_branch: str,
        wp_count: int,
        created_at: str | None = None,
        causation_id: str | None = None,
        mission_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit MissionCreated event (FR-011, FR-024).

        ``mission_id`` is the canonical aggregate identity (ULID from meta.json).
        ``aggregate_id`` is set to ``mission_id`` when provided, enabling the SaaS
        side to join events without relying on mutable slug strings (ADR 2026-04-09-1).

        Payload always includes:
          - ``mission_id``     — ULID primary key (equals aggregate_id when present)
          - ``mission_slug``   — human display string (never used as join key)
          - ``mission_number`` — int | None (None for pre-merge, int for post-merge)
        """
        payload: dict[str, Any] = {
            "mission_slug": mission_slug,
            "mission_number": mission_number,
            "target_branch": target_branch,
            "wp_count": wp_count,
        }
        if created_at is not None:
            payload["created_at"] = created_at
        # mission_id is the aggregate identity (FR-024).  Always include in
        # payload when present so SaaS consumers see both the join key and
        # display slug.  aggregate_id switches from mission_slug → mission_id
        # when mission_id is available; legacy call sites that omit mission_id
        # fall back to mission_slug for backward compat during the drift window.
        effective_aggregate_id = mission_slug
        if mission_id is not None:
            payload["mission_id"] = mission_id
            effective_aggregate_id = mission_id
        return self._emit(
            event_type="MissionCreated",
            aggregate_id=effective_aggregate_id,
            aggregate_type="Mission",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_mission_closed(
        self,
        mission_slug: str,
        total_wps: int,
        completed_at: str | None = None,
        total_duration: str | None = None,
        causation_id: str | None = None,
        mission_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit MissionClosed event (FR-012, FR-024).

        ``mission_id`` is the canonical aggregate identity (ULID from meta.json).
        ``aggregate_id`` is set to ``mission_id`` when provided (ADR 2026-04-09-1).

        Payload always includes:
          - ``mission_id``   — ULID primary key (when present)
          - ``mission_slug`` — human display string (backward compat)
        """
        payload: dict[str, Any] = {
            "mission_slug": mission_slug,
            "total_wps": total_wps,
        }
        if completed_at is not None:
            payload["completed_at"] = completed_at
        if total_duration is not None:
            payload["total_duration"] = total_duration
        # mission_id is the aggregate identity (FR-024).
        effective_aggregate_id = mission_slug
        if mission_id is not None:
            payload["mission_id"] = mission_id
            effective_aggregate_id = mission_id
        return self._emit(
            event_type="MissionClosed",
            aggregate_id=effective_aggregate_id,
            aggregate_type="Mission",
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
        aggregate_type = "WorkPackage" if wp_id is not None else "Mission"
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

    def emit_mission_origin_bound(
        self,
        mission_slug: str,
        provider: str,
        external_issue_id: str,
        external_issue_key: str,
        external_issue_url: str,
        title: str,
        causation_id: str | None = None,
        mission_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit MissionOriginBound event (observational telemetry, FR-024).

        ``mission_id`` is the canonical aggregate identity (ULID from meta.json).
        ``aggregate_id`` is set to ``mission_id`` when provided (ADR 2026-04-09-1).

        Payload always includes:
          - ``mission_id``   — ULID primary key (when present)
          - ``mission_slug`` — human display string (backward compat)
        """
        payload: dict[str, Any] = {
            "mission_slug": mission_slug,
            "provider": provider,
            "external_issue_id": external_issue_id,
            "external_issue_key": external_issue_key,
            "external_issue_url": external_issue_url,
            "title": title,
        }
        # mission_id is the aggregate identity (FR-024).
        effective_aggregate_id = mission_slug
        if mission_id is not None:
            payload["mission_id"] = mission_id
            effective_aggregate_id = mission_id
        return self._emit(
            event_type="MissionOriginBound",
            aggregate_id=effective_aggregate_id,
            aggregate_type="Mission",
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
        envelope_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Build, validate, and route an event. Non-blocking: never raises."""
        try:
            if not is_sync_enabled_for_checkout():
                logger.debug("Sync disabled for current checkout; dropping %s", event_type)
                return None

            # Tick clock for causal ordering
            clock_value = self.clock.tick()
            logger.debug(
                "Emitting %s event with Lamport clock: %d",
                event_type, clock_value,
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
                "schema_version": "3.0.0",
                "build_id": identity.build_id or "",
                "payload": payload,
                "node_id": self.clock.node_id,
                "lamport_clock": clock_value,
                "causation_id": causation_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "team_slug": team_slug,
                "project_uuid": str(identity.project_uuid) if identity.project_uuid else None,
                "project_slug": identity.project_slug,
                # Git correlation fields (Feature 033)
                "git_branch": git_meta.git_branch,
                "head_commit_sha": git_meta.head_commit_sha,
                "repo_slug": git_meta.repo_slug,
            }
            if envelope_fields:
                event.update(envelope_fields)

            # Validate event structure and payload
            if not self._validate_event(event):
                return None

            # Contract gate: validate envelope against upstream contract
            try:
                validate_outbound_payload(event, "envelope")
            except Exception as gate_err:
                _console.print(f"[yellow]Warning: Envelope contract gate failed: {gate_err}[/yellow]")
                return None

            # Check project_uuid: if missing, queue only (no WebSocket send)
            if not event.get("project_uuid"):
                _console.print(
                    "[yellow]Warning: Event missing project_uuid; queued locally only[/yellow]"
                )
                self.queue.queue_event(event)
                return event

            # Route: WebSocket if connected and authenticated, else queue
            self._route_event(event)
            return event

        except Exception as e:
            _console.print(f"[yellow]Warning: Event emission failed: {e}[/yellow]")
            return None

    def _get_team_slug(self) -> str:
        """Get team_slug from the active TokenManager session. Returns 'local' if unavailable."""
        try:
            slug = self._current_team_slug()
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
                _console.print(
                    f"[yellow]Warning: Invalid aggregate_type: "
                    f"{event.get('aggregate_type')}[/yellow]"
                )
                return False

            # 3. Validate event_type is one of the 8 known types
            event_type = event["event_type"]
            if event_type not in VALID_EVENT_TYPES:
                _console.print(
                    f"[yellow]Warning: Unknown event_type: {event_type}[/yellow]"
                )
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
            return self._validate_payload(event_type, event["payload"])

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
            _console.print(
                f"[yellow]Warning: {event_type} payload missing required "
                f"fields: {missing}[/yellow]"
            )
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
            # Check if authenticated (via TokenManager)
            authenticated = self._is_authenticated()

            # If authenticated and WebSocket connected, send directly
            if authenticated and self.ws_client is not None and self.ws_client.connected:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        task = asyncio.ensure_future(self.ws_client.send_event(event))
                        self._pending_tasks.add(task)
                        task.add_done_callback(self._pending_tasks.discard)
                    else:
                        loop.run_until_complete(self.ws_client.send_event(event))
                    return True
                except Exception as e:
                    _console.print(
                        f"[yellow]Warning: WebSocket send failed, "
                        f"queueing: {e}[/yellow]"
                    )
                    # Fall through to queue

            # Queue event for later sync
            return self.queue.queue_event(event)

        except Exception as e:
            _console.print(
                f"[yellow]Warning: Event routing failed: {e}[/yellow]"
            )
            return False
