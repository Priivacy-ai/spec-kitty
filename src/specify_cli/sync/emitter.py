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
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ulid
from rich.console import Console

from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.core.payload_shaping import apply_keep_none_fields
from specify_cli.core.saas_sync_config import sync_active
from kernel.clock import now_utc_iso, parse_iso
from specify_cli.event_journal import (
    DRAIN_BLOCKED_MISSING_AUTH,
    DRAIN_BLOCKED_MISSING_TEAM,
    DRAIN_BLOCKED_SAAS_DISABLED,
    CaptureGateState,
    classify_drain_blocked_reason,
)
from specify_cli.mission_metadata import mission_number_from_slug
from specify_cli.proof.events import (
    PROOF_EVENT_REQUIRED_FIELDS,
    PROOF_EVENT_TYPES,
    PROOF_SCHEMA_VERSION,
    build_proof_payload,
    infer_proof_aggregate,
)
from specify_cli.status import (
    emission_artifact_verdicts,
    event_verdicts,
    get_all_lane_values,
)
from specify_cli.status_lanes import CANONICAL_LANES
from spec_kitty_events import normalize_event_id as _normalize_event_id

from .clock import LamportClock
from .config import SyncConfig
from .feature_flags import is_saas_sync_enabled
from .queue import OfflineQueue

# ``routing.is_sync_enabled_for_checkout`` is deliberately NOT imported here any more
# (#3030 M1-1). It answers for ``Path.cwd()``, and every consent question this module
# asks is now keyed on the *event's own* ``project_uuid`` through ``sync/consent.py``.
# Re-adding it would reintroduce the cwd-vs-identity substitution in a module whose
# emitter is a long-lived singleton under ``SyncRuntime``. Tests that steered the old
# seam were patching a name production no longer consults.

logger = logging.getLogger(__name__)

# Single-source of truth for all canonical lane values (incl. genesis).
# Derived from specify_cli.status.models.Lane so no parallel hardcoded list
# is needed here (T021, WP04).
_CANONICAL_LANE_VALUES: frozenset[str] = get_all_lane_values()

# Display lanes (genesis excluded): genesis is a valid event ``from_lane`` (the
# seed source) but never a ``to_lane`` — a ``to_lane=genesis`` payload is
# non-canonical and must be rejected by the SaaS validator too (review m2).
# Single-sourced from CANONICAL_LANES (genesis-free by definition) — review F-02.
_DISPLAY_LANE_VALUES: frozenset[str] = frozenset(CANONICAL_LANES)

if TYPE_CHECKING:
    from .client import WebSocketClient
    from .git_metadata import GitMetadata, GitMetadataResolver
    from .layout_generation import LayoutGenerationAuthority
    from .project_context import ProjectSyncContext
    from .project_identity import ProjectIdentity
    from .project_store import ProjectUnitOfWork

_console = Console(stderr=True)

# --- Process-level captured-failure surface (WP05, IC-05 / FR-001 + FR-010) ---
#
# The machine-observable half of the emitter's non-fatal capture contract. ``_emit``
# still never raises (its ~30 ``emit_*`` callers assume emission cannot throw); a
# capture that cannot land is recorded here, out-of-band, so the command epilogue
# (WP04's consumer) can inspect it WITHOUT a filesystem rescan — mirroring
# ``AgentProfileRepository.skipped_profiles``. The human-readable warning is the
# complementary, throttled half (a residual systemic fault is loud-once-and-counted,
# never a per-event storm). The signal is strictly a flag/counter — never an
# exception threaded back through the ``emit_*`` surface.
_SITE_JOURNAL_CAPTURE = "event journal capture"
_SITE_EXPLICIT_CONTEXT_CAPTURE = "Explicit-context event capture"


@dataclass(frozen=True, slots=True)
class CapturedFailure:
    """One unrecoverable capture failure, safe to surface at the command epilogue.

    Carries only a ``site`` label and an exception ``summary`` — never the event
    envelope, payload, correlation ids, or credential material. The emitter is the
    identity-selection surface; this record must not become an exfiltration channel.
    """

    site: str
    summary: str


class _CapturedFailureRegistry:
    """Per-invocation record of swallowed capture failures + warning throttle.

    ``record`` counts every failure (INV-1 must see the true count) and returns
    whether the human warning should print — at most once per distinct
    ``(site, exception-type)`` key so a burst cannot become a per-event storm.
    Recording happens before the console decision so the count stays exact even
    when the warning is throttled or the console is suppressed.
    """

    __slots__ = ("_records", "_warned_keys")

    def __init__(self) -> None:
        self._records: list[CapturedFailure] = []
        self._warned_keys: set[str] = set()

    def record(self, site: str, exc: BaseException) -> bool:
        self._records.append(CapturedFailure(site=site, summary=repr(exc)))
        key = f"{site}:{type(exc).__name__}"
        if key in self._warned_keys:
            return False
        self._warned_keys.add(key)
        return True

    def snapshot(self) -> tuple[CapturedFailure, ...]:
        return tuple(self._records)

    def reset(self) -> None:
        self._records.clear()
        self._warned_keys.clear()


_captured_failures_registry = _CapturedFailureRegistry()


def captured_failures() -> tuple[CapturedFailure, ...]:
    """Return the capture failures recorded since the last reset (no rescan)."""
    return _captured_failures_registry.snapshot()


def reset_captured_failures() -> None:
    """Clear the process-level capture-failure surface.

    Call at command entry so the flag is per-invocation and never leaks across a
    long-lived process or across missions — a later clean command must not report
    someone else's failure.
    """
    _captured_failures_registry.reset()


def _record_capture_failure(site: str, exc: BaseException) -> None:
    """Record a swallowed capture failure, then warn (throttled) — record first.

    Record-then-warn ordering keeps the counter exact even when the warning is
    suppressed by the throttle. Both swallow sites route through here so a mixed
    burst across the two sites is bounded (one warning per distinct site), never
    doubled or per-event.
    """
    should_warn = _captured_failures_registry.record(site, exc)
    if should_warn:
        _console.print(
            f"[yellow]Warning: {site} failed: {exc} "
            f"(repeats suppressed; see the end-of-command capture summary)[/yellow]"
        )


def _get_project_identity() -> ProjectIdentity:
    """Lazily load and resolve project identity.

    Uses lazy import to prevent circular dependency issues.
    Returns empty ProjectIdentity in non-project contexts.
    """
    from .project_identity import ProjectIdentity
    from specify_cli.identity.project import resolve_identity
    from specify_cli.task_utils import find_repo_root, TaskCliError

    try:
        repo_root = find_repo_root()
    except TaskCliError:
        # Non-project context; return empty identity to trigger queue-only
        return ProjectIdentity()

    # Read/emit path: resolve identity WITHOUT persisting (#2263, FR-002/FR-003).
    return resolve_identity(repo_root)


def _create_git_resolver() -> GitMetadataResolver:
    """Lazily create GitMetadataResolver with repo root and config override."""
    from .git_metadata import GitMetadataResolver
    from specify_cli.identity.project import resolve_identity
    from specify_cli.task_utils import find_repo_root, TaskCliError

    try:
        repo_root = find_repo_root()
    except TaskCliError:
        # Non-project context; return resolver that will produce None values
        return GitMetadataResolver(repo_root=Path.cwd())

    # Read/emit path: resolve identity WITHOUT persisting (#2263, FR-002/FR-003).
    identity = resolve_identity(repo_root)
    return GitMetadataResolver(
        repo_root=repo_root,
        repo_slug_override=identity.repo_slug,
    )


def _build_payload_via_model(
    model_cls: type,
    /,
    *,
    keep_none_fields: tuple[str, ...] = (),
    **fields: Any,
) -> dict[str, Any] | None:
    """Construct a payload dict via a canonical pydantic model.

    Returns ``None`` on validation failure so the producer can preserve
    its historical contract of "invalid input -> silently skip emission"
    rather than raising. The warning emitted via the console mirrors the
    pre-refactor behavior in :func:`EventEmitter._validate_payload`.

    Phase 2 of issues Priivacy-ai/spec-kitty#1198 / #1200 — routes every
    producer's payload through the canonical model so schema drift
    becomes an emit-time error, while preserving the historical
    return-None contract for callers that test invalid-input rejection.

    ``keep_none_fields`` enumerates Optional fields whose ``None`` value
    must remain in the wire payload (e.g. ``MissionCreated.mission_number``
    where the canonical contract distinguishes pre-merge nullity from
    field absence). All other ``None``-valued optionals are dropped to
    preserve the historical "field absent when not set" shape. The
    exclude_none/keep-none shaping itself is the shared CORE-tier
    primitive :func:`specify_cli.core.payload_shaping.apply_keep_none_fields`
    (#2407) — only this function's validation-failure policy (catch and
    warn, return ``None``) is INTEGRATION-specific and stays here.
    """
    from pydantic import ValidationError

    try:
        instance = model_cls(**fields)
    except ValidationError as exc:
        _console.print(f"[yellow]Warning: {model_cls.__name__} payload validation failed: {exc}[/yellow]")
        return None
    return apply_keep_none_fields(instance, keep_none_fields=keep_none_fields)


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
_FEATURE_SLUG_PATTERN = re.compile(r"^(?:\d{3}-[a-z0-9-]+|[a-z0-9]+(?:-[a-z0-9]+)*-[0-9A-HJKMNP-TV-Z]{8})$")
_FEATURE_NUMBER_PATTERN = re.compile(r"^\d{3}$")
_SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")
# Canonical dossier snapshot-hash (WP01/FR-003): ``sha256:``-prefixed digest.
# The bare 64-hex form is also accepted for backward compatibility with drift
# baselines recorded before the one-time re-baseline (WP05); genuinely
# malformed values are still rejected.
_CANONICAL_SNAPSHOT_HASH_RE = re.compile(r"^(?:sha256:)?[a-f0-9]{64}$")


def _is_datetime_string(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        candidate = value.replace("Z", "+00:00")
        parse_iso(candidate)
        return True
    except ValueError:
        return False


def _is_nullable_string(value: Any) -> bool:
    return value is None or (isinstance(value, str))


def _is_dict(value: Any) -> bool:
    return isinstance(value, dict)


def _is_actor_payload(value: Any) -> bool:
    """Proof-schema actor: a ``{actor_id, actor_type}`` dict (mission-run /
    next-step / decision / proof events). Distinct from :func:`_is_actor_field`
    below, which accepts the FR-006 resolved-actor ``{role, tool, profile,
    model}`` shape for ``WPStatusChanged``/``WPCreated`` — the two actor
    concepts have different schemas and must not be conflated.
    """
    if not isinstance(value, dict):
        return False
    actor_id = value.get("actor_id")
    actor_type = value.get("actor_type")
    return isinstance(actor_id, str) and len(actor_id.strip()) >= 1 and actor_type in {"human", "llm", "service"}


def _is_actor_field(value: Any) -> bool:
    """FR-006: accept ``Union[str, Dict]`` for ``WPStatusChanged``/``WPCreated``
    ``actor`` — a nonempty string (the historical bare-tool shape) OR a
    nonempty dict (the resolved-actor ``{role, tool, profile, model}`` shape
    from :func:`specify_cli.status.emit.build_resolved_actor`). Rejects an
    empty string and an empty dict; does NOT require the proof-schema
    ``actor_id``/``actor_type`` keys (:func:`_is_actor_payload`) — that is a
    different actor concept and would wrongly reject a valid resolved actor.
    """
    if isinstance(value, str):
        return len(value) >= 1
    return isinstance(value, dict) and len(value) >= 1


def _is_non_negative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def _is_sha256_hex(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_HEX_RE.match(value))


def _is_canonical_snapshot_hash(value: Any) -> bool:
    """Validate a canonical dossier snapshot hash (FR-008).

    Accepts the canonical ``sha256:``-prefixed digest emitted after the
    migration (WP02) and the bare 64-hex form still carried by drift baselines
    recorded before the one-time re-baseline (WP05). Rejects any other shape.
    """
    return isinstance(value, str) and bool(_CANONICAL_SNAPSHOT_HASH_RE.match(value))


def _is_probability(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1


def _is_proof_subject(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    subject_type = value.get("subject_type")
    subject_id = value.get("subject_id")
    if not isinstance(subject_id, str) or not subject_id.strip():
        return False
    if subject_type == "work_package":
        wp_id = value.get("wp_id")
        return isinstance(wp_id, str) and bool(_WP_ID_PATTERN.match(wp_id))
    if subject_type == "mission":
        return isinstance(value.get("mission_id"), str) or isinstance(value.get("mission_slug"), str)
    if subject_type == "mission_run":
        return isinstance(value.get("run_id"), str)
    return subject_type in {"review", "pull_request"}


_PROOF_ARTIFACT_REF_KINDS: frozenset[str] = frozenset(
    {
        "file",
        "log",
        "junit",
        "coverage",
        "report",
        "url",
        "commit",
        "pull_request",
        "benchmark",
        "security_scan",
        "other",
    }
)


def _is_proof_artifact_ref(ref: Any) -> bool:
    """Validate a single artifact-ref mapping."""
    if not isinstance(ref, dict):
        return False
    if not isinstance(ref.get("uri"), str) or not ref.get("uri"):
        return False
    if ref.get("kind") not in _PROOF_ARTIFACT_REF_KINDS:
        return False
    sha256 = ref.get("sha256")
    if sha256 is not None and not _is_sha256_hex(sha256):
        return False
    size_bytes = ref.get("size_bytes")
    return not (size_bytes is not None and (not isinstance(size_bytes, int) or size_bytes < 0))


def _is_proof_artifact_refs(value: Any) -> bool:
    if not isinstance(value, list) or len(value) > 20:
        return False
    return all(_is_proof_artifact_ref(ref) for ref in value)


def _is_hex_digest(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_HEX_RE.match(value))


#: Validators shared by every proof event type.
_BASE_PROOF_VALIDATORS: dict[str, Any] = {
    "proof_schema_version": lambda v: v == PROOF_SCHEMA_VERSION,
    "subject": _is_proof_subject,
    "source": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
    "actor": _is_actor_payload,
    "confidence": _is_probability,
    "occurred_at": _is_datetime_string,
    "observed_at": _is_datetime_string,
    "artifact_refs": _is_proof_artifact_refs,
    "summary": lambda v: isinstance(v, dict),
    "idempotency_key": _is_hex_digest,
}

#: Valid ``verdict`` values for a ``ReviewProofRecorded`` proof event: the
#: two-value event vocabulary plus the two-value emission-scoped artifact
#: vocabulary -- routed through the canonical bridge (FR-005) instead of
#: re-inlining the ``rejected``/``changes_requested`` equivalence -- plus the
#: two proof-event-only extra states (``commented``/``unknown``) this schema
#: also accepts (outside the artifact<->event bridge's scope).
_REVIEW_PROOF_VERDICTS: frozenset[str] = event_verdicts() | emission_artifact_verdicts() | {"commented", "unknown"}

#: Per-event-type extra validators merged on top of :data:`_BASE_PROOF_VALIDATORS`.
_PROOF_EVENT_VALIDATORS: dict[str, dict[str, Any]] = {
    "ProofItemRecorded": {
        "proof_kind": lambda v: v in {"artifact", "claim", "observation", "note", "other"},
    },
    "ReviewProofRecorded": {
        "review_kind": lambda v: v in {"code_review", "qa", "mission_review", "security_review", "other"},
        "verdict": lambda v: v in _REVIEW_PROOF_VERDICTS,
        "review_ref": _is_nullable_string,
    },
    "TestEvidenceCaptured": {
        "test_command": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
        "exit_code": lambda v: isinstance(v, int) and v >= 0,
        "status": lambda v: v in {"passed", "failed", "error", "skipped"},
        "runner": _is_nullable_string,
        "cwd": _is_nullable_string,
        "duration_ms": lambda v: isinstance(v, int) and v >= 0,
        "total_tests": lambda v: isinstance(v, int) and v >= 0,
        "passed_tests": lambda v: isinstance(v, int) and v >= 0,
        "failed_tests": lambda v: isinstance(v, int) and v >= 0,
        "skipped_tests": lambda v: isinstance(v, int) and v >= 0,
        "failure_summary": _is_nullable_string,
        "branch": _is_nullable_string,
        "commit": _is_nullable_string,
        "build_id": _is_nullable_string,
    },
    "BenchmarkEvidenceAttached": {
        "benchmark_name": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
        "benchmark_suite": _is_nullable_string,
        "baseline_ref": _is_nullable_string,
        "comparison_ref": _is_nullable_string,
    },
    "SecurityScanCompleted": {
        "scanner": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
        "status": lambda v: v in {"passed", "failed", "completed", "error"},
        "findings_summary": lambda v: isinstance(v, dict),
    },
    "PullRequestLineageRecorded": {
        "provider": lambda v: v in {"github", "gitlab", "bitbucket", "other"},
        "repository": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
        "pull_request_url": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
        "pull_request_number": lambda v: isinstance(v, int) and v >= 1,
        "base_ref": _is_nullable_string,
        "head_ref": _is_nullable_string,
    },
    "HumanApprovalRecorded": {
        "approver": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
        "approval_status": lambda v: v in {"approved", "rejected", "requested_changes", "acknowledged"},
        "approval_ref": _is_nullable_string,
    },
}


def _proof_validators_for(event_type: str) -> dict[str, Any]:
    validators: dict[str, Any] = dict(_BASE_PROOF_VALIDATORS)
    validators.update(_PROOF_EVENT_VALIDATORS.get(event_type, {}))
    return validators


_DOSSIER_VALIDATE_EVENT_DELEGATE = object()  # sentinel: see is_dossier_delegate() below


def is_dossier_delegate(rules: object) -> bool:
    """True if *rules* is the dossier validate_event() delegation sentinel."""
    return rules is _DOSSIER_VALIDATE_EVENT_DELEGATE


_PAYLOAD_RULES: dict[str, dict[str, Any] | object] = {
    "BuildRegistered": {
        # Local-first registration (issue #1074): build_id + project_uuid scope
        # are sufficient. repo_slug is optional enrichment for git-backed
        # checkouts; fresh / detached / local-only projects MUST still
        # register so the SaaS side can materialize them once auth resolves.
        "required": {"build_id"},
        "validators": {
            "build_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "node_id": _is_nullable_string,
            "project_uuid": _is_nullable_string,
            "project_slug": _is_nullable_string,
            "project_name": _is_nullable_string,
            "repo_slug": _is_nullable_string,
            "branch": _is_nullable_string,
            "head_commit": _is_nullable_string,
            "developer_name": _is_nullable_string,
            "machine_name": _is_nullable_string,
            "workspace_path": _is_nullable_string,
        },
    },
    "BuildHeartbeat": {
        # See BuildRegistered note above; repo_slug is enrichment only.
        "required": {"build_id"},
        "validators": {
            "build_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "node_id": _is_nullable_string,
            "project_uuid": _is_nullable_string,
            "project_slug": _is_nullable_string,
            "project_name": _is_nullable_string,
            "repo_slug": _is_nullable_string,
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
        "required": {"mission_slug", "wp_id", "from_lane", "to_lane", "actor", "execution_mode"},
        "validators": {
            "wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            # genesis is valid as a from_lane (seed source) but never a to_lane
            # (review m2). Both single-sourced from Lane — no hardcoded list.
            "from_lane": lambda v: v in _CANONICAL_LANE_VALUES,
            "to_lane": lambda v: v in _DISPLAY_LANE_VALUES,
            # FR-006: Union[str, Dict] — a resolved-actor payload
            # ({role, tool, profile, model}) must not be rejected as non-string.
            "actor": _is_actor_field,
            "mission_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "force": lambda v: isinstance(v, bool),
            "reason": _is_nullable_string,
            "review_ref": _is_nullable_string,
            "execution_mode": lambda v: v in {"worktree", "direct_repo"},
            "evidence": lambda v: v is None or isinstance(v, dict),
        },
    },
    "WPCreated": {
        # Aligned to canonical events 5.1.0 wp_created_payload schema
        # (issue Priivacy-ai/spec-kitty#1203 mask 1): wp_title (not title),
        # depends_on (not dependencies), actor required.
        "required": {"wp_id", "wp_title", "mission_slug", "actor"},
        "validators": {
            "wp_id": lambda v: isinstance(v, str) and bool(_WP_ID_PATTERN.match(v)),
            "wp_title": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            # FR-006: Union[str, Dict] — see WPStatusChanged.actor above.
            "actor": _is_actor_field,
            "depends_on": lambda v: isinstance(v, list) and all(isinstance(item, str) and _WP_ID_PATTERN.match(item) for item in v),
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
        "required": {
            "mission_slug",
            "mission_number",
            "mission_type",
            "target_branch",
            "wp_count",
            "friendly_name",
            "purpose_tldr",
            "purpose_context",
        },
        "validators": {
            "mission_slug": lambda v: isinstance(v, str) and bool(_FEATURE_SLUG_PATTERN.match(v)),
            "mission_number": lambda v: v is None or (isinstance(v, int) and v >= 0),
            "mission_type": lambda v: isinstance(v, str) and len(v) >= 1,
            "target_branch": lambda v: isinstance(v, str) and len(v) >= 1,
            "wp_count": lambda v: isinstance(v, int) and v >= 0,
            "friendly_name": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
            "purpose_tldr": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
            "purpose_context": lambda v: isinstance(v, str) and len(v.strip()) >= 1,
            "mission_id": _is_nullable_string,
            "created_at": lambda v: _is_datetime_string(v),
        },
    },
    "MissionClosed": {
        "required": {"mission_slug", "mission_number", "mission_type"},
        "validators": {
            "mission_slug": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_number": lambda v: isinstance(v, int) and v >= 1,
            "mission_type": lambda v: isinstance(v, str) and len(v) >= 1,
        },
    },
    "MissionStarted": {
        "required": {"mission_id", "mission_type", "initial_phase", "actor"},
        "validators": {
            "mission_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_type": lambda v: isinstance(v, str) and len(v) >= 1,
            "initial_phase": lambda v: isinstance(v, str) and len(v) >= 1,
            "actor": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_slug": _is_nullable_string,
        },
    },
    "MissionCompleted": {
        "required": {"mission_id", "mission_type", "final_phase", "actor"},
        "validators": {
            "mission_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_type": lambda v: isinstance(v, str) and len(v) >= 1,
            "final_phase": lambda v: isinstance(v, str) and len(v) >= 1,
            "actor": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_slug": _is_nullable_string,
        },
    },
    "PhaseEntered": {
        "required": {"mission_id", "phase_name", "actor"},
        "validators": {
            "mission_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "phase_name": lambda v: isinstance(v, str) and len(v) >= 1,
            "previous_phase": _is_nullable_string,
            "actor": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_slug": _is_nullable_string,
        },
    },
    "MissionRunStarted": {
        "required": {"run_id", "mission_type", "actor"},
        "validators": {
            "run_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_type": lambda v: isinstance(v, str) and len(v) >= 1,
            "actor": _is_actor_payload,
            "mission_id": _is_nullable_string,
            "mission_slug": _is_nullable_string,
        },
    },
    "NextStepIssued": {
        "required": {"run_id", "step_id", "agent_id", "actor"},
        "validators": {
            "run_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "step_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "agent_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "actor": _is_actor_payload,
            "mission_id": _is_nullable_string,
            "mission_slug": _is_nullable_string,
        },
    },
    "NextStepAutoCompleted": {
        "required": {"run_id", "step_id", "agent_id", "result", "actor"},
        "validators": {
            "run_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "step_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "agent_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "result": lambda v: v in {"success", "failed", "blocked"},
            "actor": _is_actor_payload,
            "mission_id": _is_nullable_string,
            "mission_slug": _is_nullable_string,
        },
    },
    "DecisionInputRequested": {
        "required": {"run_id", "decision_id", "step_id", "question", "actor"},
        "validators": {
            "run_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "decision_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "step_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "question": lambda v: isinstance(v, str) and len(v) >= 1,
            "options": lambda v: isinstance(v, list),
            "input_key": _is_nullable_string,
            "actor": _is_actor_payload,
            "mission_id": _is_nullable_string,
            "mission_slug": _is_nullable_string,
        },
    },
    "DecisionInputAnswered": {
        "required": {"run_id", "decision_id", "answer", "actor"},
        "validators": {
            "run_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "decision_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "answer": lambda v: isinstance(v, str) and len(v) >= 1,
            "actor": _is_actor_payload,
            "mission_id": _is_nullable_string,
            "mission_slug": _is_nullable_string,
        },
    },
    "MissionRunCompleted": {
        "required": {"run_id", "mission_type", "actor"},
        "validators": {
            "run_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "mission_type": lambda v: isinstance(v, str) and len(v) >= 1,
            "actor": _is_actor_payload,
            "mission_id": _is_nullable_string,
            "mission_slug": _is_nullable_string,
        },
    },
    "TokenUsageRecorded": {
        "required": {
            "mission_id",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "estimated_cost_usd",
            "source",
        },
        "validators": {
            "mission_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "run_id": _is_nullable_string,
            "step_id": _is_nullable_string,
            "wp_id": _is_nullable_string,
            "phase_name": _is_nullable_string,
            "actor": lambda v: v is None or _is_actor_payload(v),
            "provider": _is_nullable_string,
            "model": _is_nullable_string,
            "input_tokens": lambda v: isinstance(v, int) and v >= 0,
            "output_tokens": lambda v: isinstance(v, int) and v >= 0,
            "total_tokens": lambda v: isinstance(v, int) and v >= 0,
            "estimated_cost_usd": _is_non_negative_number,
            "source": lambda v: isinstance(v, str) and len(v) >= 1,
        },
    },
    "DiffSummaryRecorded": {
        "required": {
            "mission_id",
            "base_ref",
            "head_ref",
            "files_changed",
            "lines_added",
            "lines_deleted",
            "source",
        },
        "validators": {
            "mission_id": lambda v: isinstance(v, str) and len(v) >= 1,
            "run_id": _is_nullable_string,
            "step_id": _is_nullable_string,
            "wp_id": _is_nullable_string,
            "phase_name": _is_nullable_string,
            "base_ref": lambda v: isinstance(v, str) and len(v) >= 1,
            "head_ref": lambda v: isinstance(v, str) and len(v) >= 1,
            "files_changed": lambda v: isinstance(v, int) and v >= 0,
            "lines_added": lambda v: isinstance(v, int) and v >= 0,
            "lines_deleted": lambda v: isinstance(v, int) and v >= 0,
            "source": lambda v: isinstance(v, str) and len(v) >= 1,
        },
    },
    **{
        event_type: {
            "required": set(PROOF_EVENT_REQUIRED_FIELDS[event_type]),
            "validators": _proof_validators_for(event_type),
        }
        for event_type in sorted(PROOF_EVENT_TYPES)
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
    # Dossier events — namespaced envelope (spec-kitty-events >= 5.0.0).
    # The canonical sub-object shapes live in specify_cli/dossier/events.py
    # (LocalNamespaceTuple, ArtifactIdentity, ContentHashRef). See
    # Priivacy-ai/spec-kitty#1047 for the migration from the legacy flat
    # envelope.
    "MissionDossierArtifactIndexed": _DOSSIER_VALIDATE_EVENT_DELEGATE,
    "MissionDossierArtifactMissing": _DOSSIER_VALIDATE_EVENT_DELEGATE,
    "MissionDossierSnapshotComputed": _DOSSIER_VALIDATE_EVENT_DELEGATE,
    "MissionDossierParityDriftDetected": _DOSSIER_VALIDATE_EVENT_DELEGATE,
    "MissionOriginBound": {
        "required": {
            "mission_slug",
            "provider",
            "external_issue_id",
            "external_issue_key",
            "external_issue_url",
            "title",
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


@dataclass(frozen=True)
class TokenUsageMetadata:
    """Optional ``TokenUsageRecorded`` fields, bundled into one params object.

    S107: ``emit_token_usage_recorded`` is a two-layer signature — this
    module's :meth:`EventEmitter.emit_token_usage_recorded` and
    ``sync.events.emit_token_usage_recorded`` (the singleton wrapper) both
    threaded these 8 fields as individual keyword parameters. Bundling them
    here and passing ``metadata`` through both layers keeps each below the
    parameter-count ceiling.
    """

    run_id: str | None = None
    step_id: str | None = None
    wp_id: str | None = None
    phase_name: str | None = None
    actor: dict[str, Any] | None = None
    provider: str | None = None
    model: str | None = None
    causation_id: str | None = None


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
    # The singleton may be constructed outside a project.  A project-owned
    # OfflineQueue can only be minted from an active store unit + layout
    # authority, so there is intentionally no ambient/path-backed default.
    queue: OfflineQueue | None = None
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
        """Resolve the ingress team slug via the strict shared helper. SYNC.

        Returns the user's Private Teamspace id, or ``None`` when no Private
        Teamspace is available. On ``None`` the shared helper has already
        emitted the structured warning and emission of any event that
        requires an ingress team-id MUST be skipped.
        """
        try:
            from specify_cli.auth import get_token_manager
            from specify_cli.sync._team import resolve_private_team_id_for_ingress

            return resolve_private_team_id_for_ingress(
                get_token_manager(),
                endpoint="/api/v1/events/batch/",
            )
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("emitter._get_team_slug: ingress resolver raised: %s", exc)
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
        # S5713: ``FileNotFoundError`` derives from ``OSError``, already caught below.
        except (OSError, subprocess.TimeoutExpired):
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
        """Emit BuildRegistered for the current project/build identity.

        Phase 1 of issues Priivacy-ai/spec-kitty#1198 / #1200 ships the
        canonical :class:`spec_kitty_events.build_lifecycle.BuildRegisteredPayload`
        with a restrictive surface (``repo_slug``, ``git_branch``,
        ``head_commit_sha``) — build/node identity moves to the envelope.
        The legacy payload shape (build_id, node_id, project_uuid, …)
        is preserved on the wire for SaaS materializer compatibility
        until the Phase 3 SaaS adapter lands; canonical fields are
        additionally validated through the model so producer-time drift
        of any of the three canonical fields is caught here.
        """
        from spec_kitty_events.build_lifecycle import BuildRegisteredPayload

        identity = self._get_identity()
        base = self._build_lifecycle_payload()
        # Canonical-payload validation: catches drift on the three
        # fields the Phase-1 contract owns. Done strictly via the
        # pydantic model so any future tightening on these fields is
        # an emit-time error.
        if (
            _build_payload_via_model(
                BuildRegisteredPayload,
                repo_slug=base.get("repo_slug"),
                git_branch=base.get("branch"),
                head_commit_sha=base.get("head_commit"),
            )
            is None
        ):
            return None
        aggregate_id = identity.build_id or identity.node_id or "build"
        return self._emit(
            event_type="BuildRegistered",
            aggregate_id=aggregate_id,
            aggregate_type="Build",
            payload=base,
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
        """Emit BuildHeartbeat for the current project/build identity.

        Phase 1 canonical model is
        :class:`spec_kitty_events.build_lifecycle.BuildHeartbeatPayload`
        — see ``emit_build_registered`` for the canonical-vs-wire
        envelope discussion. Validation of the canonical fields runs
        through the model; the wire payload preserves the historical
        identity fields until Phase 3.
        """
        from spec_kitty_events.build_lifecycle import BuildHeartbeatPayload

        identity = self._get_identity()
        base = self._build_lifecycle_payload()
        if remote_head is not None:
            base["remote_head"] = remote_head
        if ahead_of_remote is not None:
            base["ahead_of_remote"] = ahead_of_remote
        if behind_remote is not None:
            base["behind_remote"] = behind_remote
        if recent_commits is not None:
            base["recent_commits"] = recent_commits

        # Canonical-payload validation on the seven fields Phase 1 owns.
        if (
            _build_payload_via_model(
                BuildHeartbeatPayload,
                repo_slug=base.get("repo_slug"),
                git_branch=base.get("branch"),
                head_commit_sha=base.get("head_commit"),
                remote_head=remote_head,
                ahead_of_remote=ahead_of_remote,
                behind_remote=behind_remote,
                recent_commits=recent_commits,
            )
            is None
        ):
            return None
        aggregate_id = identity.build_id or identity.node_id or "build"
        return self._emit(
            event_type="BuildHeartbeat",
            aggregate_id=aggregate_id,
            aggregate_type="Build",
            payload=base,
            causation_id=causation_id,
        )

    def emit_wp_status_changed(
        self,
        wp_id: str,
        from_lane: str,
        to_lane: str,
        actor: str = "user",
        mission_slug: str | None = None,
        causation_id: str | None = None,
        force: bool = False,
        reason: str | None = None,
        review_ref: str | None = None,
        execution_mode: str | None = None,
        evidence: dict[str, Any] | None = None,
        occurred_at: str | None = None,
        **legacy_kwargs: Any,
    ) -> dict[str, Any] | None:
        """Emit WPStatusChanged event (FR-008).

        ``occurred_at`` is the producer occurrence time (``StatusEvent.at``
        from the canonical local status event). When provided, the wire
        envelope's ``timestamp`` will equal this value; otherwise the emitter
        mints a fresh ``datetime.now(UTC).isoformat()``.
        """
        unexpected_kwargs = sorted(set(legacy_kwargs) - {"mission_id", "policy_metadata"})
        if unexpected_kwargs:
            unexpected = ", ".join(unexpected_kwargs)
            raise TypeError(f"emit_wp_status_changed() got unexpected keyword argument(s): {unexpected}")
        evidence_payload = evidence
        if evidence_payload is not None and not evidence_payload.get("repos"):
            git_meta = self._get_git_metadata()
            evidence_payload = {
                **evidence_payload,
                "repos": [
                    {
                        "repo": git_meta.repo_slug or "local",
                        "branch": git_meta.git_branch or "unknown",
                        "commit": git_meta.head_commit_sha or "unknown",
                    }
                ],
            }
        from spec_kitty_events.status import StatusTransitionPayload

        resolved_mission_slug = mission_slug or "unknown-mission"
        # Construct via canonical StatusTransitionPayload (Phase 1
        # already covers this type and now enforces semantic
        # validation for review-rejection transitions). The model
        # accepts string lanes via alias resolution and validates
        # ``force`` / ``reason`` invariants. Invalid input -> return
        # None (preserved historical contract).
        payload = _build_payload_via_model(
            StatusTransitionPayload,
            wp_id=wp_id,
            from_lane=from_lane,
            to_lane=to_lane,
            actor=actor,
            mission_slug=resolved_mission_slug,
            force=force,
            reason=reason,
            review_ref=review_ref,
            execution_mode=execution_mode or "direct_repo",
            evidence=evidence_payload,
        )
        if payload is None:
            return None
        # Do NOT pass envelope_fields=...; the canonical envelope keys are
        # already nested inside ``payload``. Duplicating them at the top
        # level violates the SaaS schema with
        # ``Additional properties are not allowed ('actor' was unexpected)``
        # and rejects every WPStatusChanged batch with HTTP 400. See issue
        # Priivacy-ai/spec-kitty#1188.
        return self._emit(
            event_type="WPStatusChanged",
            aggregate_id=wp_id,
            aggregate_type="WorkPackage",
            payload=payload,
            causation_id=causation_id,
            occurred_at=occurred_at,
        )

    def emit_wp_created(
        self,
        wp_id: str,
        title: str,
        mission_slug: str,
        mission_id: str | None = None,
        dependencies: list[str] | None = None,
        causation_id: str | None = None,
        actor: str = "cli",
    ) -> dict[str, Any] | None:
        """Emit WPCreated event (FR-009).

        The canonical ``wp_created_payload`` schema (events 5.1.0) lists
        ``wp_title``, ``depends_on``, ``actor`` as required and forbids
        any extras (``additionalProperties: false``). The function keeps
        ``title`` / ``dependencies`` as parameter names for caller
        compatibility but **renames them at the payload boundary** to
        ``wp_title`` / ``depends_on``. ``mission_id`` is kept on the
        function signature but is no longer placed in the payload (it
        isn't in the canonical allowed set). See issue
        Priivacy-ai/spec-kitty#1203 mask 1.
        """
        from spec_kitty_events.project_lifecycle import WPCreatedPayload

        del mission_id  # accepted for caller compatibility; not in canonical payload (#1203)
        payload = _build_payload_via_model(
            WPCreatedPayload,
            wp_id=wp_id,
            wp_title=title,
            depends_on=list(dependencies or []),
            mission_slug=mission_slug,
            actor=actor,
        )
        if payload is None:
            return None
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
        """Emit WPAssigned event (FR-010).

        Payload constructed via canonical
        :class:`spec_kitty_events.project_lifecycle.WPAssignedPayload`
        (Phase 1 of issues Priivacy-ai/spec-kitty#1198 / #1200).
        """
        from spec_kitty_events.project_lifecycle import WPAssignedPayload

        payload = _build_payload_via_model(
            WPAssignedPayload,
            wp_id=wp_id,
            agent_id=agent_id,
            phase=phase,
            retry_count=retry_count,
        )
        if payload is None:
            return None
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
        mission_type: str = "software-dev",
        friendly_name: str | None = None,
        purpose_tldr: str | None = None,
        purpose_context: str | None = None,
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
        # Canonical payload construction (#2270): one CORE builder shared with
        # the local lifecycle path so the two cannot drift. The builder raises
        # on invalid input; preserve this producer's historical
        # "invalid -> skip emission" contract by catching and returning None.
        from pydantic import ValidationError

        from specify_cli.core.mission_payload import build_mission_created_payload

        try:
            payload = build_mission_created_payload(
                mission_slug=mission_slug,
                target_branch=target_branch,
                mission_type=mission_type,
                wp_count=wp_count,
                mission_id=mission_id,
                mission_number=mission_number,
                friendly_name=friendly_name,
                purpose_tldr=purpose_tldr,
                purpose_context=purpose_context,
                created_at=created_at,
            )
        except ValidationError as exc:
            _console.print(f"[yellow]Warning: MissionCreatedPayload validation failed: {exc}[/yellow]")
            return None
        effective_aggregate_id = mission_slug
        if mission_id is not None:
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
        mission_number: int | None = None,
        mission_type: str = "software-dev",
    ) -> dict[str, Any] | None:
        """Emit MissionClosed event (FR-012, FR-024).

        ``mission_id`` is the canonical aggregate identity (ULID from meta.json).
        ``aggregate_id`` is set to ``mission_id`` when provided (ADR 2026-04-09-1).

        The payload follows spec-kitty-events ``MissionClosedPayload`` exactly.
        Historical close details such as ``total_wps`` and close timestamps are
        intentionally not emitted in the TeamSpace payload.
        """
        from spec_kitty_events.lifecycle import MissionClosedPayload

        del total_wps, completed_at, total_duration
        resolved_number = mission_number if mission_number is not None else mission_number_from_slug(mission_slug)
        if resolved_number is None or resolved_number < 1:
            # MissionClosedPayload requires ge=1; legacy callers pass 0
            # for pre-merge missions. Coerce to 1 — Phase 3 (SaaS adapter)
            # will tighten this when canonical-only mission_number
            # propagation lands across all repos.
            resolved_number = 1
        payload = _build_payload_via_model(
            MissionClosedPayload,
            mission_slug=mission_slug,
            mission_number=resolved_number,
            mission_type=mission_type,
        )
        if payload is None:
            return None
        # mission_id is the aggregate identity (FR-024).
        effective_aggregate_id = mission_slug
        if mission_id is not None:
            effective_aggregate_id = mission_id
        return self._emit(
            event_type="MissionClosed",
            aggregate_id=effective_aggregate_id,
            aggregate_type="Mission",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_mission_started(
        self,
        mission_id: str,
        mission_type: str,
        initial_phase: str,
        actor: str,
        mission_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit MissionStarted for a runtime-backed mission."""
        payload: dict[str, Any] = {
            "mission_id": mission_id,
            "mission_type": mission_type,
            "initial_phase": initial_phase,
            "actor": actor,
        }
        if mission_slug is not None:
            payload["mission_slug"] = mission_slug
        return self._emit(
            event_type="MissionStarted",
            aggregate_id=mission_id,
            aggregate_type="Mission",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_phase_entered(
        self,
        mission_id: str,
        phase_name: str,
        actor: str,
        previous_phase: str | None = None,
        mission_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit PhaseEntered for a runtime-backed mission."""
        payload: dict[str, Any] = {
            "mission_id": mission_id,
            "phase_name": phase_name,
            "previous_phase": previous_phase,
            "actor": actor,
        }
        if mission_slug is not None:
            payload["mission_slug"] = mission_slug
        return self._emit(
            event_type="PhaseEntered",
            aggregate_id=mission_id,
            aggregate_type="Mission",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_mission_completed(
        self,
        mission_id: str,
        mission_type: str,
        final_phase: str,
        actor: str,
        mission_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit MissionCompleted for a runtime-backed mission."""
        payload: dict[str, Any] = {
            "mission_id": mission_id,
            "mission_type": mission_type,
            "final_phase": final_phase,
            "actor": actor,
        }
        if mission_slug is not None:
            payload["mission_slug"] = mission_slug
        return self._emit(
            event_type="MissionCompleted",
            aggregate_id=mission_id,
            aggregate_type="Mission",
            payload=payload,
            causation_id=causation_id,
        )

    @staticmethod
    def _jsonify(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "__dict__"):
            return {key: EventEmitter._jsonify(val) for key, val in vars(value).items()}
        if isinstance(value, dict):
            return {str(key): EventEmitter._jsonify(val) for key, val in value.items()}
        if isinstance(value, tuple):
            return [EventEmitter._jsonify(item) for item in value]
        if isinstance(value, list):
            return [EventEmitter._jsonify(item) for item in value]
        return value

    @staticmethod
    def _payload_dict(payload: Any) -> dict[str, Any]:
        data = EventEmitter._jsonify(payload)
        if not isinstance(data, dict):
            raise TypeError("payload must serialize to a dict")
        return data

    def emit_mission_run_started(
        self,
        payload: Any,
        *,
        mission_id: str | None = None,
        mission_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit MissionRunStarted via the canonical sync envelope."""
        data = self._payload_dict(payload)
        if mission_id is not None:
            data["mission_id"] = mission_id
        if mission_slug is not None:
            data["mission_slug"] = mission_slug
        return self._emit(
            event_type="MissionRunStarted",
            aggregate_id=mission_id or str(data.get("run_id") or mission_slug or "mission-run"),
            aggregate_type="Mission",
            payload=data,
            causation_id=causation_id,
        )

    def emit_next_step_issued(
        self,
        payload: Any,
        *,
        mission_id: str | None = None,
        mission_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit NextStepIssued via the canonical sync envelope."""
        data = self._payload_dict(payload)
        if mission_id is not None:
            data["mission_id"] = mission_id
        if mission_slug is not None:
            data["mission_slug"] = mission_slug
        return self._emit(
            event_type="NextStepIssued",
            aggregate_id=mission_id or str(data.get("run_id") or mission_slug or "mission-run"),
            aggregate_type="Mission",
            payload=data,
            causation_id=causation_id,
        )

    def emit_next_step_auto_completed(
        self,
        payload: Any,
        *,
        mission_id: str | None = None,
        mission_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit NextStepAutoCompleted via the canonical sync envelope."""
        data = self._payload_dict(payload)
        if mission_id is not None:
            data["mission_id"] = mission_id
        if mission_slug is not None:
            data["mission_slug"] = mission_slug
        return self._emit(
            event_type="NextStepAutoCompleted",
            aggregate_id=mission_id or str(data.get("run_id") or mission_slug or "mission-run"),
            aggregate_type="Mission",
            payload=data,
            causation_id=causation_id,
        )

    def emit_decision_input_requested(
        self,
        payload: Any,
        *,
        mission_id: str | None = None,
        mission_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit DecisionInputRequested via the canonical sync envelope."""
        data = self._payload_dict(payload)
        if mission_id is not None:
            data["mission_id"] = mission_id
        if mission_slug is not None:
            data["mission_slug"] = mission_slug
        return self._emit(
            event_type="DecisionInputRequested",
            aggregate_id=mission_id or str(data.get("run_id") or mission_slug or "mission-run"),
            aggregate_type="Mission",
            payload=data,
            causation_id=causation_id,
        )

    def emit_decision_input_answered(
        self,
        payload: Any,
        *,
        mission_id: str | None = None,
        mission_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit DecisionInputAnswered via the canonical sync envelope."""
        data = self._payload_dict(payload)
        if mission_id is not None:
            data["mission_id"] = mission_id
        if mission_slug is not None:
            data["mission_slug"] = mission_slug
        return self._emit(
            event_type="DecisionInputAnswered",
            aggregate_id=mission_id or str(data.get("run_id") or mission_slug or "mission-run"),
            aggregate_type="Mission",
            payload=data,
            causation_id=causation_id,
        )

    def emit_mission_run_completed(
        self,
        payload: Any,
        *,
        mission_id: str | None = None,
        mission_slug: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit MissionRunCompleted via the canonical sync envelope."""
        data = self._payload_dict(payload)
        if mission_id is not None:
            data["mission_id"] = mission_id
        if mission_slug is not None:
            data["mission_slug"] = mission_slug
        return self._emit(
            event_type="MissionRunCompleted",
            aggregate_id=mission_id or str(data.get("run_id") or mission_slug or "mission-run"),
            aggregate_type="Mission",
            payload=data,
            causation_id=causation_id,
        )

    def emit_token_usage_recorded(
        self,
        mission_id: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        estimated_cost_usd: float,
        source: str,
        *,
        metadata: TokenUsageMetadata | None = None,
    ) -> dict[str, Any] | None:
        """Emit TokenUsageRecorded for trustworthy runtime usage data.

        ``metadata`` bundles the optional tail — ``run_id``, ``step_id``,
        ``wp_id``, ``phase_name``, ``actor``, ``provider``, ``model``,
        ``causation_id`` — into one params object (S107: this dropped the
        declared-parameter count from 14 to 7). Threaded through unchanged
        from the ``sync.events.emit_token_usage_recorded`` wrapper, which
        accepts the same ``metadata`` object (the two-layer signature).
        """
        metadata = metadata or TokenUsageMetadata()
        payload: dict[str, Any] = {
            "mission_id": mission_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "source": source,
        }
        if metadata.run_id is not None:
            payload["run_id"] = metadata.run_id
        if metadata.step_id is not None:
            payload["step_id"] = metadata.step_id
        if metadata.wp_id is not None:
            payload["wp_id"] = metadata.wp_id
        if metadata.phase_name is not None:
            payload["phase_name"] = metadata.phase_name
        if metadata.actor is not None:
            payload["actor"] = metadata.actor
        if metadata.provider is not None:
            payload["provider"] = metadata.provider
        if metadata.model is not None:
            payload["model"] = metadata.model
        return self._emit(
            event_type="TokenUsageRecorded",
            aggregate_id=mission_id,
            aggregate_type="Mission",
            payload=payload,
            causation_id=metadata.causation_id,
        )

    def emit_diff_summary_recorded(
        self,
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
        """Emit DiffSummaryRecorded for stable reviewable diffs."""
        payload: dict[str, Any] = {
            "mission_id": mission_id,
            "base_ref": base_ref,
            "head_ref": head_ref,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "source": source,
        }
        if run_id is not None:
            payload["run_id"] = run_id
        if step_id is not None:
            payload["step_id"] = step_id
        if wp_id is not None:
            payload["wp_id"] = wp_id
        if phase_name is not None:
            payload["phase_name"] = phase_name
        return self._emit(
            event_type="DiffSummaryRecorded",
            aggregate_id=mission_id,
            aggregate_type="Mission",
            payload=payload,
            causation_id=causation_id,
        )

    def emit_proof_event(
        self,
        event_type: str,
        payload: Any,
        *,
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit one of the CLI-owned proof/evidence event types."""
        try:
            data = build_proof_payload(
                event_type,
                self._enrich_proof_subject(payload),
            )
        except Exception as exc:
            _console.print(f"[yellow]Warning: {event_type} payload validation failed: {exc}[/yellow]")
            return None

        aggregate_type, aggregate_id = infer_proof_aggregate(data)
        return self._emit(
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            payload=data,
            causation_id=causation_id,
            occurred_at=str(data.get("occurred_at") or ""),
        )

    def _enrich_proof_subject(self, payload: Any) -> dict[str, Any]:
        data = self._payload_dict(payload)
        subject = data.get("subject")
        if not isinstance(subject, dict):
            return data

        enriched = dict(subject)
        identity = self._get_identity()
        git_meta = self._get_git_metadata()

        if identity.project_uuid is not None:
            enriched.setdefault("project_uuid", str(identity.project_uuid))
        if identity.project_slug:
            enriched.setdefault("project_slug", identity.project_slug)
        if identity.build_id:
            enriched.setdefault("build_id", identity.build_id)
        if git_meta.repo_slug:
            enriched.setdefault("repo_slug", git_meta.repo_slug)
        if git_meta.git_branch:
            enriched.setdefault("git_branch", git_meta.git_branch)
        if git_meta.head_commit_sha:
            enriched.setdefault("head_commit_sha", git_meta.head_commit_sha)

        team_slug = self._get_team_slug() if is_saas_sync_enabled() else self._get_cached_private_team_slug()
        if team_slug:
            enriched.setdefault("team_slug", team_slug)

        data["subject"] = enriched
        return data

    def emit_history_added(
        self,
        wp_id: str,
        entry_type: str,
        entry_content: str,
        author: str = "user",
        causation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Emit HistoryAdded event (FR-013).

        Payload constructed via canonical
        :class:`spec_kitty_events.project_lifecycle.HistoryAddedPayload`
        (Phase 1 of issues Priivacy-ai/spec-kitty#1198 / #1200).
        """
        from spec_kitty_events.project_lifecycle import HistoryAddedPayload

        payload = _build_payload_via_model(
            HistoryAddedPayload,
            wp_id=wp_id,
            entry_type=entry_type,
            entry_content=entry_content,
            author=author,
        )
        if payload is None:
            return None
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
        """Emit ErrorLogged event (FR-014).

        Payload constructed via canonical
        :class:`spec_kitty_events.project_lifecycle.ErrorLoggedPayload`
        (Phase 1 of issues Priivacy-ai/spec-kitty#1198 / #1200).
        """
        from spec_kitty_events.project_lifecycle import ErrorLoggedPayload

        payload = _build_payload_via_model(
            ErrorLoggedPayload,
            error_type=error_type,
            error_message=error_message,
            wp_id=wp_id,
            stack_trace=stack_trace,
            agent_id=agent_id,
        )
        if payload is None:
            return None

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
        """Emit DependencyResolved event (FR-015).

        Payload constructed via canonical
        :class:`spec_kitty_events.project_lifecycle.DependencyResolvedPayload`
        (Phase 1 of issues Priivacy-ai/spec-kitty#1198 / #1200).
        """
        from spec_kitty_events.project_lifecycle import DependencyResolvedPayload

        payload = _build_payload_via_model(
            DependencyResolvedPayload,
            wp_id=wp_id,
            dependency_wp_id=dependency_wp_id,
            resolution_type=resolution_type,
        )
        if payload is None:
            return None
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
        from spec_kitty_events.lifecycle import MissionOriginBoundPayload

        payload = _build_payload_via_model(
            MissionOriginBoundPayload,
            mission_slug=mission_slug,
            provider=provider,
            external_issue_id=external_issue_id,
            external_issue_key=external_issue_key,
            external_issue_url=external_issue_url,
            title=title,
            mission_id=mission_id,
        )
        if payload is None:
            return None
        # mission_id is the aggregate identity (FR-024).
        effective_aggregate_id = mission_slug
        if mission_id is not None:
            effective_aggregate_id = mission_id
        return self._emit(
            event_type="MissionOriginBound",
            aggregate_id=effective_aggregate_id,
            aggregate_type="Mission",
            payload=payload,
            causation_id=causation_id,
        )

    # ── Internal dispatch ─────────────────────────────────────────

    # Drain blocked reason taxonomy — see issue #1072.
    #
    # Tokens are the canonical closed vocabulary from
    # ``specify_cli.event_journal.models`` — delivery selection
    # (``specify_cli.delivery.selection``) fail-closes on any token it does
    # not recognise, so a private spelling here would strand every stamped
    # row as terminally blocked.
    #
    # ``None``               event is ready to drain to SaaS.
    # ``"saas_disabled"``    SaaS sync is off machine-wide, or **this event's
    #                        own project** has not consented to hosted sync
    #                        (#3030 M1-1; it used to mean "the checkout cwd
    #                        happens to be in"). Terminal for selection:
    #                        consent refusal must not ship.
    # ``"missing_auth"``     no authenticated session; drain cannot ship.
    # ``"missing_team"``     authenticated but the strict Private Teamspace
    #                        resolver returned None (ingress safety).
    #
    # The flag is captured at emit time as a diagnostic. The drain loop
    # re-resolves on every tick, so a previously-blocked event becomes
    # eligible once the underlying condition clears (login, opt-in,
    # private team materialized). Ingress safety is preserved:
    # ``missing_team`` events are never shipped via direct ingress because
    # the drain side re-checks the resolver and skips the batch when it
    # still returns None.
    DRAIN_BLOCKED_REASONS = frozenset(
        {DRAIN_BLOCKED_SAAS_DISABLED, DRAIN_BLOCKED_MISSING_AUTH, DRAIN_BLOCKED_MISSING_TEAM}
    )

    def _classify_drain_blocked_reason(self, team_slug: str | None, *, project_uuid: str | None = None) -> str | None:
        """Return a drain-blocked reason for the current emission context.

        Order matters: the most coarse-grained gate (sync feature flag)
        wins so operators see "the checkout is opted out" rather than a
        downstream symptom like "missing_team".

        **M1's recorded exclusion for this method was wrong and is withdrawn
        (#3030 M1-1).** It claimed this field is the legacy offline queue's advisory
        diagnostic and that "nothing reads this value to decide whether anything
        ships", so a cwd-derived ``is_sync_enabled_for_checkout()`` read was harmless
        here. :meth:`_route_event` reads exactly this value to decide whether to
        publish the envelope over the WebSocket — a live egress path, injected with a
        connected client by ``SyncRuntime``. The premise was false and the field was
        load-bearing.

        So consent is resolved from *project_uuid* — the event's own identity, the
        value the row is stamped with — via :meth:`_project_consents_to_capture`, the
        same single resolver the capture gate, the drain, the body upload and the
        LocalCommit flush use (C-003: no second copy of the precedence chain).

        Two things this fixes beyond the leak. The cwd read denied in the *other*
        direction too: with no readable checkout for the project — the daemon's usual
        case — ``resolve_checkout_sync_routing`` returns ``None`` and every event of
        every project was stamped ``sync_disabled``, so the WebSocket publish was dead
        for consenting projects as well. And ``sync status``'s per-reason counts now
        describe the project that was actually asked about.

        :meth:`_route_event` re-checks consent independently before publishing rather
        than trusting this field. That is deliberate: a *diagnostic* must not be the
        only thing standing between a non-consenting project and the network.
        """
        try:
            if not is_saas_sync_enabled():
                return DRAIN_BLOCKED_SAAS_DISABLED
            if not self._project_consents_to_capture(project_uuid):
                return DRAIN_BLOCKED_SAAS_DISABLED
        except Exception:
            # Routing config errors should not destroy event durability;
            # treat as drain-blocked so the operator can re-evaluate
            # later via ``sync status --check``.
            return DRAIN_BLOCKED_SAAS_DISABLED

        try:
            if not self._is_authenticated():
                return DRAIN_BLOCKED_MISSING_AUTH
        except Exception:
            return DRAIN_BLOCKED_MISSING_AUTH

        if team_slug is None:
            return DRAIN_BLOCKED_MISSING_TEAM

        return None

    @staticmethod
    def _offered_consent_roots() -> list[Path]:
        """The checkout available to offer ``sync/consent.py`` for its level-1 read.

        Offering the working directory here is **narrowing-only**, not the cwd
        shortcut this method exists to remove: ``consent._project_local_votes``
        ignores any root whose ``.kittify/config.yaml`` declares a *different*
        ``project_uuid``, so a root can only ever answer for its own project. When
        the emitter is standing in project B and the event belongs to A, B's file is
        discarded and the chain falls through to the uuid-keyed index — which is the
        correct answer for A.

        Without offering it, the project-local level would be unreachable on every
        real capture and a committed, reviewable in-repo refusal would silently not
        be honoured (the same gap ``delivery/selection.py`` documents for the drain).
        """
        try:
            from specify_cli.core.paths import locate_project_root

            root = locate_project_root(Path.cwd().resolve())
        # An unreadable cwd is absence, not a decision.
        except Exception:  # noqa: BLE001
            return []
        return [root] if root is not None else []

    def _project_consents_to_capture(self, project_uuid: str | None) -> bool:
        """Does the project *this event belongs to* consent to hosted sync? (#3030 M1)

        Resolved from the event's own ``project_uuid`` down ``sync/consent.py``'s one
        chain — the same resolver the drain, the body upload and the LocalCommit
        flush use (C-003: no second copy of the precedence chain).

        Despite the ``_capture`` in the name it is the module's **one** consent
        predicate, with three consumers: the capture gate (M1),
        :meth:`_classify_drain_blocked_reason`, and the WebSocket publish decision in
        :meth:`_route_event` (M1-1). The question is identical in all three — "may
        this project's data leave the machine?" — and answering it in one place is
        what stops the reported state and the enforced state from drifting apart.

        This replaces ``is_sync_enabled_for_checkout()`` called with no argument, i.e.
        against ``Path.cwd()``. That read answered for whichever project the process
        happened to be standing in while the row was stamped with the identity from
        ``_get_identity()``, which caches for the emitter's lifetime. The two agree in
        a short-lived CLI process and diverge under the long-lived ``SyncRuntime``
        singleton the moment anything calls ``os.chdir`` — the cwd-vs-identity defect
        T025 names for body uploads and T027 for local-commit frames.

        The leaking direction was already closed downstream (the drain keys on the
        stored uuid, so a row stamped A cannot ship on B's grant); what this fixes is
        **silent capture loss** — a consenting project's event dropped because cwd
        refused, or stamped ``saas_disabled`` from cwd's answer, which
        ``delivery/selection.py`` treats as terminal and therefore permanently
        unselectable.

        An unresolvable uuid is denied, never waved through: NFR-001's second half is
        that an event whose project cannot be identified can never be shown to belong
        to a consenting one. Fails **closed** on error, departing from this module's
        habit of swallowing and continuing — here that instinct would convert an
        unanswerable consent question into a stored payload (FR-003's rule).
        """
        if not project_uuid:
            return False
        try:
            from .consent import consented_project_uuids

            return bool(consented_project_uuids([project_uuid], checkout_roots=self._offered_consent_roots()))
        # Inability to determine consent is not consent.
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Could not resolve hosted-sync consent for project %s; refusing capture: %s",
                project_uuid,
                exc,
            )
            return False

    def _capture_gate_state(self, team_slug: str | None, *, project_uuid: str | None = None) -> CaptureGateState:
        """Snapshot the drain gates for the journal's blocked-reason audit (T017).

        ``checkout_enabled`` is resolved from *project_uuid* — the event's own
        identity, the value the row is stamped with — and not from the working
        directory (#3030 M1); see :meth:`_project_consents_to_capture`. It keeps the
        name ``checkout_enabled`` because that is the ``CaptureGateState`` field
        ``classify_drain_blocked_reason`` reads, but the question it now answers is
        "does *this event's project* consent?".

        Defensive on the machine-global gates: a read failure there is treated as
        "blocked" so capture still records a durable, audit-tagged row and never
        raises (contract §2 bullet 3). Per-project consent is the one gate that fails
        closed to *no row at all*, because that is the confidentiality boundary.
        """
        try:
            saas_enabled = is_saas_sync_enabled()
        except Exception:
            saas_enabled = False
        checkout_enabled = self._project_consents_to_capture(project_uuid)
        try:
            authenticated = self._is_authenticated()
        except Exception:
            authenticated = False
        return CaptureGateState(
            saas_enabled=saas_enabled,
            checkout_enabled=checkout_enabled,
            authenticated=authenticated,
            team_slug=team_slug,
        )

    def _capture_to_journal(
        self,
        *,
        event_id: str,
        event_type: str,
        event: dict[str, Any],
        occurred_at: str,
        team_slug: str | None,
    ) -> None:
        """Capture the full envelope in its project-owned journal/outbox.

        Capture is local and therefore independent of hosted consent (FR-006).
        The event's UUID selects the physical project store; cwd, team, login,
        and active-target defaults cannot select or widen it. The queue append
        persists the journal entry and outbox task atomically before egress.
        """
        del event_id, event_type, occurred_at, team_slug
        try:
            self._queue_event_locally(event)
        except Exception as exc:
            # Record into the process-level surface first (so the count is exact
            # even when the console warning is throttled), then warn. Stays
            # non-fatal + capture-is-local: no re-raise, no consent coupling.
            _record_capture_failure(_SITE_JOURNAL_CAPTURE, exc)

    def _emit(
        self,
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        payload: dict[str, Any],
        causation_id: str | None = None,
        envelope_fields: dict[str, Any] | None = None,
        occurred_at: str | None = None,
        project_context: ProjectSyncContext | None = None,
        project_unit: ProjectUnitOfWork | None = None,
        project_layout: LayoutGenerationAuthority | None = None,
    ) -> dict[str, Any] | None:
        """Build, validate, and route an event. Non-blocking: never raises.

        ``occurred_at`` carries the producer occurrence time that the canonical
        event contract (Rule R-T-01 in spec-kitty-events) requires on the
        envelope ``timestamp`` field. Callers that already have a local
        lane-transition time (e.g. ``StatusEvent.at``) MUST pass it here so
        the wire envelope preserves that value. When ``occurred_at`` is
        ``None``, the emitter mints ``datetime.now(UTC).isoformat()`` - the
        right behavior for events created at emission time (build heartbeat,
        dossier emission, etc.).

        Local durability is unconditional (issue #1072): the on-disk outbox
        is appended before any auth / sync / team / network gate can drop the
        event. Remote drain eligibility is captured in ``drain_blocked_reason``
        on the envelope; the drain loop re-evaluates each tick and only ships
        events whose blockers have cleared.
        """
        if project_context is not None or project_unit is not None or project_layout is not None:
            if project_context is None or project_unit is None or project_layout is None:
                _console.print("[yellow]Warning: Explicit-context event capture requires context, unit, and layout authority[/yellow]")
                return None
            return self._emit_for_project_context(
                event_type=event_type,
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                payload=payload,
                causation_id=causation_id,
                envelope_fields=envelope_fields,
                occurred_at=occurred_at,
                project_context=project_context,
                project_unit=project_unit,
                project_layout=project_layout,
            )
        try:
            # Tick clock for causal ordering — local fact, always recorded.
            clock_value = self.clock.tick()
            logger.debug(
                "Emitting %s event with Lamport clock: %d",
                event_type,
                clock_value,
            )

            # Resolve identity, team_slug (may be None), and git metadata.
            # When the global SaaS feature flag is disabled, avoid even
            # touching the direct-ingress Teamspace resolver; feature-disabled
            # runs should not emit feature-specific warnings.
            identity = self._get_identity()
            team_slug = self._get_team_slug() if is_saas_sync_enabled() else None
            git_meta = self._get_git_metadata()

            # Classify the drain blocker (None means ready to ship). Keyed on the
            # identity this event is about to be stamped with, not on cwd (#3030
            # M1-1) — ``_route_event`` turns a ``None`` here into a WebSocket publish.
            # Snapshot the gates once (T017) and classify through the journal's
            # canonical classifier so the stamped token is always a member of the
            # closed vocabulary delivery selection recognises.
            gate_state = self._capture_gate_state(
                team_slug,
                project_uuid=str(identity.project_uuid) if identity.project_uuid else None,
            )
            drain_blocked_reason = classify_drain_blocked_reason(gate_state)

            event_id = _generate_ulid()

            # Build event dict with identity fields.
            # canonical-producer-exempt: #1248 -- central CLI wire-envelope assembly.
            event: dict[str, Any] = {
                "event_id": event_id,
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "aggregate_type": aggregate_type,
                "schema_version": "3.0.0",
                "build_id": identity.build_id or "",
                "payload": payload,
                "node_id": self.clock.node_id,
                "lamport_clock": clock_value,
                "causation_id": causation_id,
                "correlation_id": causation_id or event_id,
                "timestamp": occurred_at if occurred_at is not None else now_utc_iso(),
                "team_slug": team_slug,
                "project_uuid": str(identity.project_uuid) if identity.project_uuid else None,
                "project_slug": identity.project_slug,
                # Git correlation fields (Feature 033)
                "git_branch": git_meta.git_branch,
                "head_commit_sha": git_meta.head_commit_sha,
                "repo_slug": git_meta.repo_slug,
                # Local-first diagnostic (issue #1072). Drain logic uses
                # this for diagnostics + counting; eligibility is decided
                # at drain time by re-resolving the underlying conditions.
                "drain_blocked_reason": drain_blocked_reason,
            }
            if envelope_fields:
                event.update(envelope_fields)

            # WP02 / FR-005 + FR-006, C-008: the single canonical arming gate for
            # the emission surface. Placed AFTER the envelope is fully
            # constructed and BEFORE ``_capture_to_journal`` (~2280), the
            # missing-uuid branch (~2308), ``_route_event`` (~2633), and
            # ``_queue_event_locally`` (~2651). Gating ``_route_event`` alone
            # MISSES the direct ``get_emitter().emit_*()`` path (init.py, merge,
            # etc.), which reaches capture/queue without ever touching routing.
            # We RETURN the constructed envelope (never ``None``) so the
            # emit_*-returns-non-None contract (tests/contract/test_event_envelope.py
            # and siblings) stays green, while capture/persist/route/queue — and
            # the "project sync store is locked" / "Event routing failed"
            # warnings — are all skipped on the inactive default path.
            if not sync_active():
                return event

            self._capture_to_journal(
                event_id=event_id,
                event_type=event_type,
                event=event,
                occurred_at=str(event["timestamp"]),
                team_slug=team_slug,
            )

            # Validate event structure and payload. Validation tolerates
            # team_slug=None for pending-routing events (issue #1072).
            if not self._validate_event(event):
                return None

            # Contract gate: validate envelope against upstream contract.
            # The upstream contract does not require team_slug at envelope
            # level, so pending-routing events pass without modification.
            try:
                validate_outbound_payload(event, "envelope")
            except Exception as gate_err:
                _console.print(f"[yellow]Warning: Envelope contract gate failed: {gate_err}[/yellow]")
                return None

            # Local outbox is the durable surface; always append before
            # making remote routing decisions.
            # Check project_uuid: if missing, queue only (no WebSocket send)
            if not event.get("project_uuid"):
                _console.print("[yellow]Warning: Event missing project_uuid; queued locally only[/yellow]")
                # Local-only, and never published: an event whose project cannot be
                # identified can never be shown to belong to a consenting one
                # (NFR-001). The write itself is deliberately not consent-gated — see
                # the recorded judgement above ``_route_event``.
                self._queue_event_locally(event)
                return event

            if not self._route_event(event):
                # ``_route_event`` returns ``True`` iff the event durably landed
                # in a project-owned outbox; ``False`` means it did NOT (no
                # resolvable outbox, the queue refused/was full, or the append
                # raised and was caught). The old behavior discarded this bool and
                # returned the envelope truthy (#3517), so the 11 ``if event is
                # not None`` gates in ``events.py`` still fired
                # ``_publish_event_via_sync_daemon`` — which publishes the
                # in-memory event over loopback WITHOUT reading the outbox.
                #
                # Tradeoff (adversarial review finding 2a): live publish and local
                # durability are independent channels, so on a *transient* outbox
                # failure with a healthy daemon the old path did achieve a
                # best-effort live delivery — but with no durable record behind
                # it, so nothing could re-deliver it if the daemon/downstream
                # dropped it. That "delivered but unrecoverable" state is the
                # silent-false-success #3517/#3549 target: the outbox is the
                # eventual-delivery source of truth, and publishing what it can't
                # back reports success the system can't stand behind. We
                # deliberately trade that best-effort live window for a legible
                # failure — warn on the same stderr surface the sibling
                # non-durable arms above use, and return ``None`` so the publish
                # gates skip it. The transient-vs-permanent distinction (retry
                # past a busy queue) is the bounded-retry redesign that stays with
                # #3549's sync owners — out of scope here. Never-raise preserved.
                _console.print(
                    "[yellow]Warning: Event did not durably queue; "
                    "dropping from publication[/yellow]"
                )
                return None
            return event

        except Exception as e:
            _console.print(f"[yellow]Warning: Event emission failed: {e}[/yellow]")
            return None

    def _emit_for_project_context(
        self,
        *,
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        payload: dict[str, Any],
        causation_id: str | None,
        envelope_fields: dict[str, Any] | None,
        occurred_at: str | None,
        project_context: ProjectSyncContext,
        project_unit: ProjectUnitOfWork,
        project_layout: LayoutGenerationAuthority,
    ) -> dict[str, Any] | None:
        """Capture one event locally under exact store-minted authority.

        This explicit-context seam never consults cwd, cached emitter identity,
        auth, team, git, or request defaults and never invokes WebSocket or HTTP
        routing. It writes only to the canonical project journal/outbox; the
        dispatcher independently revalidates authority before any later egress.
        """
        from .project_context import validate_project_sync_context_authority
        from .queue import OfflineQueue

        try:
            validate_project_sync_context_authority(project_context)
            if project_unit.store_identity is not project_context.store_identity:
                raise ValueError("project unit does not match the explicit project context")
            event_id = _generate_ulid()
            timestamp = occurred_at if occurred_at is not None else now_utc_iso()
            # canonical-producer-exempt: #1248 -- explicit-context local envelope assembly.
            event: dict[str, Any] = {
                "event_id": event_id,
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "aggregate_type": aggregate_type,
                "schema_version": "3.0.0",
                "build_id": "",
                "payload": payload,
                "node_id": self.clock.node_id,
                "lamport_clock": self.clock.tick(),
                "causation_id": causation_id,
                "correlation_id": causation_id or event_id,
                "timestamp": timestamp,
                "team_slug": None,
                "project_uuid": project_context.project_uuid.storage_token,
                "project_slug": None,
                "git_branch": None,
                "head_commit_sha": None,
                "repo_slug": None,
                "drain_blocked_reason": None,
            }
            if envelope_fields:
                protected = {
                    "project_uuid",
                    "event_id",
                    "correlation_id",
                }
                if protected.intersection(envelope_fields):
                    raise ValueError("explicit-context emission cannot override project or event identity")
                event.update(envelope_fields)
            if not self._validate_event(event):
                return None
            validate_outbound_payload(event, "envelope")

            queued = OfflineQueue(project_unit, project_layout).queue_event(event)
            if not queued:
                raise RuntimeError("canonical project outbox refused dossier event capture")
            return event
        except Exception as exc:
            # Live-reproduced swallow (``mission create`` hit this five times while
            # authoring this mission). Record into the same process-level surface
            # first, then still ``return None`` (explicit-context contract: a refused
            # capture yields ``None``). The internal refusal ``RuntimeError`` stays
            # caught here — now observable, never stderr-only.
            _record_capture_failure(_SITE_EXPLICIT_CONTEXT_CAPTURE, exc)
            return None

    def _get_team_slug(self) -> str | None:
        """Get team_slug from the active TokenManager session.

        Returns the user's Private Teamspace id, or ``None`` when no Private
        Teamspace is available for direct ingress (FR-002/FR-007 of the
        private-teamspace-ingress-safeguards mission). On ``None`` the
        caller MUST skip event emission rather than fall back to a shared
        or ``"local"`` team value.
        """
        try:
            slug = self._current_team_slug()
            if slug:
                return slug
        except Exception as e:
            _console.print(f"[yellow]Warning: Could not resolve team_slug: {e}[/yellow]")
        return None

    @staticmethod
    def _get_cached_private_team_slug() -> str | None:
        """Read Private Teamspace id from cached auth session without ingress I/O."""
        try:
            from specify_cli.auth import get_token_manager
            from specify_cli.auth.session import require_private_team_id

            session = get_token_manager().get_current_session()
            if session is None:
                return None
            return require_private_team_id(session)
        except Exception:
            return None

    def _validate_event(self, event: dict[str, Any]) -> bool:
        """Validate event against spec-kitty-events models and payload schemas.

        Validates both the envelope (via spec-kitty-events Event model) and
        the per-event-type payload (via rules derived from events.schema.json).
        Returns True if valid, False if invalid (warned and discarded).
        """
        try:
            from spec_kitty_events import Event as EventModel

            # 1. Validate envelope via spec-kitty-events Pydantic model
            # spec-kitty-events 4.0.0 added build_id, project_uuid, correlation_id
            # as required fields; fall back to safe defaults for events emitted
            # under 3.x schema that lack these fields.
            # canonical-producer-exempt: #1248 -- kwargs fed to canonical EventModel.
            model_data = {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "aggregate_id": event["aggregate_id"],
                "payload": event["payload"],
                "timestamp": event["timestamp"],
                "node_id": event["node_id"],
                "lamport_clock": event["lamport_clock"],
                "causation_id": event.get("causation_id"),
                "build_id": event.get("build_id") or "unknown",
                "project_uuid": event.get("project_uuid") or "00000000-0000-0000-0000-000000000000",
                "correlation_id": event.get("correlation_id") or event["event_id"],
            }
            EventModel(**model_data)

            # 2. Validate fields the library model doesn't cover.
            # team_slug=None is a valid "pending routing" state for
            # locally-durable events (issue #1072). Reject only when the
            # value is present but malformed (non-string).
            team_slug_value = event.get("team_slug")
            if team_slug_value is not None and not isinstance(team_slug_value, str):
                _console.print("[yellow]Warning: Event team_slug has non-string value[/yellow]")
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
            return self._validate_payload(event_type, event["payload"])

        except Exception as e:
            _console.print(f"[yellow]Warning: Event validation failed: {e}[/yellow]")
            return False

    def _validate_dossier_payload(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Delegate dossier payload validation to spec_kitty_events.conformance.

        FR-006: replaces the four hand-maintained dossier ``_PAYLOAD_RULES``
        entries with the canonical, dual-layer (Pydantic + JSON Schema)
        validator the ``spec_kitty_events`` package ships. Translates
        ``ConformanceResult.valid`` into this method's existing ``bool``
        contract, printing a warning naming the real violation (NFR-002:
        emitter.py's visibility contract stays a printed warning).
        """
        from spec_kitty_events.conformance import validate_event

        result = validate_event(payload, event_type, strict=True)
        if not result.valid:
            violations = [str(v) for v in (*result.model_violations, *result.schema_violations)]
            _console.print(f"[yellow]Warning: {event_type} payload invalid: {'; '.join(violations)}[/yellow]")
        return result.valid

    def _validate_payload(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Validate payload fields against per-event-type schema rules.

        Rules are derived from contracts/events.schema.json definitions.
        """
        rules = _PAYLOAD_RULES.get(event_type)
        if rules is None:
            return True  # No rules = no validation needed

        if is_dossier_delegate(rules):
            return self._validate_dossier_payload(event_type, payload)

        # rules is not the dossier delegation sentinel at this point, so it
        # is the generic {"required": ..., "validators": ...} dict shape.
        # `raise`, not `assert` -- `assert` is stripped under `python -O`,
        # which would leave `rules["required"]` below silently misbehaving
        # against a non-dict instead of failing loudly (WP02-ASSERT-RAISE).
        if not isinstance(rules, dict):
            raise TypeError(
                f"_PAYLOAD_RULES[{event_type!r}] is neither the dossier "
                f"delegation sentinel nor a dict; got {type(rules).__name__}"
            )

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
                    _console.print(f"[yellow]Warning: {event_type} payload field '{field_name}' has invalid value: {value!r}[/yellow]")
                    return False

        return True

    # Recorded judgement — the legacy offline queue's unconditional write (#3030 M1-1
    # secondary finding). ``self.queue.queue_event(event)`` below, and the missing-uuid
    # branch in ``_emit``, run for every emitted event including one whose project has
    # not consented, writing the full wire envelope — ``project_slug`` (a client
    # engagement name) and the payload — into the machine-global
    # ``~/.spec-kitty/queue.db`` shared by every local project.
    #
    # DECISION: not gated. Three reasons, in order of weight.
    #
    # 1. It is not egress. The store has no sender left. WP02 removed the
    #    queue-backed drain (FR-012); ``sync/batch.py``'s senders have no live caller,
    #    and that absence is itself pinned by
    #    ``tests/sync/test_no_queue_drain_constructed_3030.py``. The two remaining
    #    readers are read-only — ``sync diagnose`` validates rows locally, and
    #    ``background._unauthenticated_sync_result`` classifies them. Verified by
    #    grepping every ``drain_queue`` / ``process_batch_results`` call site, not
    #    assumed: assuming "nothing reads this" is the exact mistake M1-1 corrected.
    # 2. Gating it would be data loss, not confidentiality. This queue is the
    #    documented unconditional local outbox (issue #1072) — appended before any
    #    auth / sync / team / network gate can drop the event, so a later opt-in can
    #    replay it. Refusing the write would turn "this project has not opted in to
    #    *hosted* sync" into "this project's local event history is discarded". FR-002
    #    governs what leaves the machine; nothing in this mission asks for local
    #    history to be destroyed, and C-002 already forbids the migration from
    #    deleting rows for the same reason. The retention half is pinned explicitly in
    #    ``tests/sync/test_ws_publish_consent_3030.py`` so the decision cannot be
    #    reversed by accident in either direction.
    # 3. The residual exposure is real and already has an owner. Confidential text
    #    pooled at rest in a machine-global store is what C-006 records as this
    #    mission's remaining open *collection* surface, whose recorded remedy is an
    #    explicit operator purge — FR-016 / WP08, for which
    #    ``OfflineQueue.remove_project_events`` already exists.
    #
    # WHAT WOULD FLIP IT: if a queue-backed sender is ever restored, this write
    # becomes egress and must be gated on consent *first*. That is a precondition on
    # restoring the drain, not a follow-up ticket.
    def _route_event(self, event: dict[str, Any]) -> bool:
        """Capture to the local outbox without performing direct transport.

        The former opportunistic ``ws_client.send_event`` branch had no exact
        project context, durable delivery attempt, lease, admission audience, or
        acknowledgement. A connected client therefore never authorizes egress here.
        WP08's runtime publisher owns the admitted WebSocket path through the WP06
        transport gate; this legacy method preserves local durability only.
        """
        try:
            # Unconditional local durability, deliberately (issue #1072) and
            # deliberately not consent-gated — see the recorded judgement above.
            return self._queue_event_locally(event)

        except Exception as e:
            _console.print(f"[yellow]Warning: Event routing failed: {e}[/yellow]")
            return False

    def _queue_event_locally(self, event: dict[str, Any]) -> bool:
        """Capture through an attached or transient exact project outbox."""
        if self.queue is not None:
            return self.queue.queue_event(event)
        from .project_identity import resolve_event_project_uuid
        from .project_store import ProjectSyncStore
        from .queue import OfflineQueue

        project_uuid = resolve_event_project_uuid(event)
        if project_uuid is None:
            logger.debug("Event %s has no project-owned outbox", event.get("event_id"))
            return False
        store = ProjectSyncStore(project_uuid)
        # Resolve/drive the machine layout cutover BEFORE opening this write's
        # unit-of-work (WP03 live-path completion, IC-05 / FR-003). The layout
        # lock is not re-entrant: driven from inside an open UoW the cutover copy
        # contends on the held store lock and cannot land, which surfaced
        # ``LayoutCutoverIncompleteError`` on the live emit path. Out here the lock
        # is free, so a legacy-with-data root completes its cutover to PROJECT_ONLY
        # and the write below lands in the project store. Greenfield / already-
        # migrated roots return in a single peek; only legacy data drives a copy.
        # A genuinely-unrecoverable resolution (escape hatch, foreign migration)
        # propagates to the caller's now-observable capture site, never silently.
        store.layout_generation().resolve_layout_for_write()
        with store.unit_of_work() as unit:
            return OfflineQueue(unit, store.layout_generation()).queue_event(event)

    def _queue_if_async_send_failed(self, completed: object, event: dict[str, Any]) -> None:
        """Queue an event if a fire-and-forget WebSocket send fails later."""
        try:
            exception = completed.exception()  # type: ignore[attr-defined]
        except Exception as exc:
            exception = exc
        if exception is None:
            return
        logger.debug("Async WebSocket send failed; queueing event %s: %s", event.get("event_id"), exception)
        try:
            self._queue_event_locally(event)
        except Exception as queue_exc:
            logger.warning("Failed to queue event %s after async send failure: %s", event.get("event_id"), queue_exc)

    @property
    def git_resolver(self):
        return self._git_resolver
