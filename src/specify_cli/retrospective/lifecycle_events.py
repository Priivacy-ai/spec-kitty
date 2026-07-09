"""Canonical retrospective lifecycle event types and emit helpers (WP03 — T015).

Defines the three canonical event types that join the mission-level event log
(kitty-specs/<mission_slug>/status.events.jsonl) when a retrospective is
captured, fails, or is skipped under strict policy.

Source of truth:
    kitty-specs/retrospective-default-policy-01KS049J/contracts/retrospective-events.contract.md

spec_kitty_events surface inspection result (2026-05-19):
    ``RetrospectiveCaptured``, ``RetrospectiveCaptureFailed``, and the new-shape
    ``RetrospectiveSkipped`` (with ``policy_source`` / ``skip_reason_source`` fields)
    were NOT found at the top-level ``spec_kitty_events`` public surface.
    The existing ``RetrospectiveSkippedPayload`` in ``spec_kitty_events.retrospective``
    has a different shape (no ``policy_source``), lives at a sub-path (violating FR-024
    if imported from there), and is for a legacy event schema.
    Therefore all three types are defined locally in this module.

FR-024 compliance:
    This module does NOT import from ``spec_kitty_events.models.*`` or any other
    sub-path of ``spec_kitty_events``. The architectural test
    ``tests/architectural/test_events_tracker_public_imports.py`` enforces this.
"""

from __future__ import annotations

from specify_cli.core.constants import RETROSPECTIVE_FILENAME
from specify_cli.retrospective.writer import resolve_retrospective_home
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import ulid as _ulid_mod

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.retrospective.schema import (
    GenRetrospectiveRecord,
    ProvenanceKind,
    RecordValidationError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Actor type for the canonical event envelope
# ---------------------------------------------------------------------------

ActorKind = Literal["human", "agent", "runtime"]


@dataclass
class Actor:
    """Identity attribution in the canonical event envelope.

    Matches the Actor shape in contracts/retrospective-events.contract.md.
    """

    kind: ActorKind
    id: str
    display: str | None = None


# ---------------------------------------------------------------------------
# Canonical event envelope dataclasses
# ---------------------------------------------------------------------------


@dataclass
class RetrospectiveCaptured:
    """Emitted when retrospective generation succeeds and a record is on disk.

    Contract: contracts/retrospective-events.contract.md § RetrospectiveCaptured
    """

    # Common envelope fields
    schema_version: int = 1
    event_id: str = field(default_factory=str)          # ULID, set by emit helper
    lamport: int = 0
    at: str = field(default_factory=str)                 # RFC 3339, set by emit helper
    actor: Actor = field(default_factory=lambda: Actor(kind="runtime", id="unknown"))
    mission_id: str = ""
    mission_slug: str = ""
    wp_id: None = None
    force: bool = False
    execution_mode: Literal["worktree", "main"] = "main"

    # Event-specific fields
    findings_status: Literal["has_findings", "ran_no_findings"] = "ran_no_findings"
    record_path: str = ""
    generator_version: str = ""
    policy_source: dict[str, str] = field(default_factory=dict)
    provenance_kind: ProvenanceKind = "runtime_post_completion"
    proposal_count: int = 0
    evidence_ref_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSONL output."""
        return {
            "type": "RetrospectiveCaptured",
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "lamport": self.lamport,
            "at": self.at,
            "actor": {"kind": self.actor.kind, "id": self.actor.id, "display": self.actor.display},
            "mission_id": self.mission_id,
            "mission_slug": self.mission_slug,
            "wp_id": self.wp_id,
            "force": self.force,
            "execution_mode": self.execution_mode,
            "findings_status": self.findings_status,
            "record_path": self.record_path,
            "generator_version": self.generator_version,
            "policy_source": dict(self.policy_source),
            "provenance_kind": self.provenance_kind,
            "proposal_count": self.proposal_count,
            "evidence_ref_count": self.evidence_ref_count,
        }


@dataclass
class RetrospectiveCaptureFailed:
    """Emitted when retrospective generation fails under ``failure_policy: warn``.

    Does NOT fire under ``failure_policy: block`` (the completion-block event
    carries the failure) or ``enabled: false`` (no attempt made).

    Contract: contracts/retrospective-events.contract.md § RetrospectiveCaptureFailed
    """

    # Common envelope fields
    schema_version: int = 1
    event_id: str = field(default_factory=str)
    lamport: int = 0
    at: str = field(default_factory=str)
    actor: Actor = field(default_factory=lambda: Actor(kind="runtime", id="unknown"))
    mission_id: str = ""
    mission_slug: str = ""
    wp_id: None = None
    force: bool = False
    execution_mode: Literal["worktree", "main"] = "main"

    # Event-specific fields
    failure_category: Literal[
        "missing_artifacts",
        "generator_exception",
        "schema_validation_error",
        "io_error",
        "other",
    ] = "other"
    failure_message: str = ""
    remediation_hint: str | None = None
    policy_source: dict[str, str] = field(default_factory=dict)
    attempted_provenance_kind: ProvenanceKind = "runtime_post_completion"
    missing_artifacts: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSONL output."""
        return {
            "type": "RetrospectiveCaptureFailed",
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "lamport": self.lamport,
            "at": self.at,
            "actor": {"kind": self.actor.kind, "id": self.actor.id, "display": self.actor.display},
            "mission_id": self.mission_id,
            "mission_slug": self.mission_slug,
            "wp_id": self.wp_id,
            "force": self.force,
            "execution_mode": self.execution_mode,
            "failure_category": self.failure_category,
            "failure_message": self.failure_message,
            "remediation_hint": self.remediation_hint,
            "policy_source": dict(self.policy_source),
            "attempted_provenance_kind": self.attempted_provenance_kind,
            "missing_artifacts": self.missing_artifacts,
        }


@dataclass
class RetrospectiveSkipped:
    """Emitted when the strict gate is bypassed via ``--skip-retrospective``.

    Only emitted under strict policy (``timing: before_completion + failure_policy: block``
    AND ``enabled: true``). Never emitted under default policy (no gate to skip).

    Contract: contracts/retrospective-events.contract.md § RetrospectiveSkipped

    Invariant: ``skip_reason`` MUST be non-empty. The ``emit_skipped`` helper
    enforces this with a ``ValueError``.
    """

    # Common envelope fields
    schema_version: int = 1
    event_id: str = field(default_factory=str)
    lamport: int = 0
    at: str = field(default_factory=str)
    actor: Actor = field(default_factory=lambda: Actor(kind="human", id="unknown"))
    mission_id: str = ""
    mission_slug: str = ""
    wp_id: None = None
    force: bool = False
    execution_mode: Literal["worktree", "main"] = "main"

    # Event-specific fields
    skip_reason: str = ""                                # MUST be non-empty
    skip_reason_source: Literal[
        "cli_flag", "config_flag", "ci_environment"
    ] = "cli_flag"
    policy_source: dict[str, str] = field(default_factory=dict)
    bypassed_provenance_kind: Literal["runtime_strict_gate"] = "runtime_strict_gate"
    would_have_attempted: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSONL output."""
        return {
            "type": "RetrospectiveSkipped",
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "lamport": self.lamport,
            "at": self.at,
            "actor": {"kind": self.actor.kind, "id": self.actor.id, "display": self.actor.display},
            "mission_id": self.mission_id,
            "mission_slug": self.mission_slug,
            "wp_id": self.wp_id,
            "force": self.force,
            "execution_mode": self.execution_mode,
            "skip_reason": self.skip_reason,
            "skip_reason_source": self.skip_reason_source,
            "policy_source": dict(self.policy_source),
            "bypassed_provenance_kind": self.bypassed_provenance_kind,
            "would_have_attempted": self.would_have_attempted,
        }


# Union type for consumers that handle all three.
RetroLifecycleEvent = RetrospectiveCaptured | RetrospectiveCaptureFailed | RetrospectiveSkipped


# ---------------------------------------------------------------------------
# Internal JSONL append helper
# ---------------------------------------------------------------------------


def _generate_ulid() -> str:
    return str(_ulid_mod.ULID())


def _append_retro_lifecycle_event(feature_dir: Path, event_dict: dict[str, Any]) -> None:
    """Append a retrospective lifecycle event line to status.events.jsonl."""
    events_path = feature_dir / "status.events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event_dict, sort_keys=True)
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    logger.debug(
        "Appended %s (event_id=%s) to %s",
        event_dict.get("type"),
        event_dict.get("event_id"),
        events_path,
    )


def _next_lamport(feature_dir: Path) -> int:
    """Return the next lamport clock value by reading the last event in the log."""
    events_path = feature_dir / "status.events.jsonl"
    if not events_path.exists():
        return 1
    last_lamport = 0
    try:
        for raw in events_path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
                lp = obj.get("lamport", 0)
                if isinstance(lp, int) and lp > last_lamport:
                    last_lamport = lp
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return last_lamport + 1


# ---------------------------------------------------------------------------
# Public emit helpers
# ---------------------------------------------------------------------------


def emit_captured(
    record: GenRetrospectiveRecord,
    repo_root: Path,
    *,
    provenance_kind: ProvenanceKind,
    actor: Actor,
    execution_mode: Literal["worktree", "main"] = "main",
) -> RetrospectiveCaptured:
    """Emit a ``RetrospectiveCaptured`` event to the mission event log.

    Defense-in-depth: rejects ``provenance_kind == "synthesize_fabricate"`` AND
    ``record.findings_status == "has_findings"`` per T014 / FR-014 invariant.

    Args:
        record: The generator record that was captured.
        repo_root: Project root (for resolving kitty-specs path).
        provenance_kind: How the capture was invoked.
        actor: Who triggered the capture.
        execution_mode: Execution context (worktree or main).

    Returns:
        The ``RetrospectiveCaptured`` event dataclass (also written to JSONL).

    Raises:
        RecordValidationError: synthesize_fabricate + has_findings.
        ValueError: Empty mission_slug on record.
    """
    # Defense-in-depth: emit level also checks the invariant.
    if provenance_kind == "synthesize_fabricate" and record.findings_status == "has_findings":
        raise RecordValidationError(
            violation="synthesize_fabricate_findings_status_mismatch",
            detail=(
                "synthesize_fabricate provenance_kind MUST imply findings_status=ran_no_findings; "
                f"got findings_status={record.findings_status!r}. See data-model.md invariants."
            ),
        )

    if not record.mission_slug:
        raise ValueError("record.mission_slug must be non-empty to determine feature_dir")

    feature_dir = resolve_retrospective_home(repo_root, record.mission_slug)
    lamport = _next_lamport(feature_dir)
    event_id = _generate_ulid()
    at = now_utc_iso()

    # FR-001/003 (#2119): the record lives in the durable PRIMARY home for every
    # topology, resolved above through the single durable-home authority — never
    # the materialized ``-coord`` husk (the #1771 coord-leak this mission cures).
    canonical_path = feature_dir / RETROSPECTIVE_FILENAME

    event = RetrospectiveCaptured(
        schema_version=1,
        event_id=event_id,
        lamport=lamport,
        at=at,
        actor=actor,
        mission_id=record.mission_id,
        mission_slug=record.mission_slug,
        wp_id=None,
        force=False,
        execution_mode=execution_mode,
        findings_status=record.findings_status,
        record_path=str(canonical_path),
        generator_version=record.generator_version,
        policy_source=dict(record.policy_source),
        provenance_kind=provenance_kind,
        proposal_count=len(record.proposals),
        evidence_ref_count=len(record.evidence_refs),
    )

    _append_retro_lifecycle_event(feature_dir, event.to_dict())
    return event


def emit_capture_failed(
    mission_id: str,
    mission_slug: str,
    repo_root: Path,
    *,
    failure_category: Literal[
        "missing_artifacts",
        "generator_exception",
        "schema_validation_error",
        "io_error",
        "other",
    ],
    failure_message: str,
    remediation_hint: str | None,
    policy_source: dict[str, str],
    attempted_provenance_kind: ProvenanceKind,
    missing_artifacts: list[str] | None,
    actor: Actor,
    execution_mode: Literal["worktree", "main"] = "main",
) -> RetrospectiveCaptureFailed:
    """Emit a ``RetrospectiveCaptureFailed`` event to the mission event log.

    Args:
        mission_id: ULID mission identity.
        mission_slug: Human-readable mission slug (used to locate feature_dir).
        repo_root: Project root.
        failure_category: Structured failure classification.
        failure_message: Human-readable description (no stack traces).
        remediation_hint: Suggested next action, or None.
        policy_source: Resolver source-map snapshot.
        attempted_provenance_kind: What the capture would have been tagged as on success.
        missing_artifacts: Specific artifact paths when failure_category == "missing_artifacts".
        actor: Who triggered the capture attempt.
        execution_mode: Execution context.

    Returns:
        The ``RetrospectiveCaptureFailed`` event dataclass.
    """
    if not mission_slug:
        raise ValueError("mission_slug must be non-empty to determine feature_dir")

    feature_dir = resolve_retrospective_home(repo_root, mission_slug)
    lamport = _next_lamport(feature_dir)
    event_id = _generate_ulid()
    at = now_utc_iso()

    event = RetrospectiveCaptureFailed(
        schema_version=1,
        event_id=event_id,
        lamport=lamport,
        at=at,
        actor=actor,
        mission_id=mission_id,
        mission_slug=mission_slug,
        wp_id=None,
        force=False,
        execution_mode=execution_mode,
        failure_category=failure_category,
        failure_message=failure_message,
        remediation_hint=remediation_hint,
        policy_source=dict(policy_source),
        attempted_provenance_kind=attempted_provenance_kind,
        missing_artifacts=missing_artifacts,
    )

    _append_retro_lifecycle_event(feature_dir, event.to_dict())
    return event


def emit_skipped(
    mission_id: str,
    mission_slug: str,
    repo_root: Path,
    *,
    skip_reason: str,
    skip_reason_source: Literal["cli_flag", "config_flag", "ci_environment"],
    policy_source: dict[str, str],
    actor: Actor,
    would_have_attempted: bool = True,
    execution_mode: Literal["worktree", "main"] = "main",
) -> RetrospectiveSkipped:
    """Emit a ``RetrospectiveSkipped`` event to the mission event log.

    Only valid under strict policy paths (``timing: before_completion + failure_policy: block``
    AND ``enabled: true``). The ``skip_reason`` MUST be non-empty.

    Args:
        mission_id: ULID mission identity.
        mission_slug: Human-readable mission slug.
        repo_root: Project root.
        skip_reason: Operator-provided reason for the bypass. MUST be non-empty.
        skip_reason_source: Where the reason came from.
        policy_source: Resolver source-map snapshot.
        actor: The human (or automation) who invoked ``--skip-retrospective``.
        would_have_attempted: True if the runtime had loaded policy and was ready
            to dispatch. Always True today; reserved for future paths.
        execution_mode: Execution context.

    Returns:
        The ``RetrospectiveSkipped`` event dataclass.

    Raises:
        ValueError: ``skip_reason`` is empty.
    """
    if not skip_reason or not skip_reason.strip():
        raise ValueError("skip_reason MUST be non-empty per RetrospectiveSkipped contract")

    if not mission_slug:
        raise ValueError("mission_slug must be non-empty to determine feature_dir")

    feature_dir = resolve_retrospective_home(repo_root, mission_slug)
    lamport = _next_lamport(feature_dir)
    event_id = _generate_ulid()
    at = now_utc_iso()

    event = RetrospectiveSkipped(
        schema_version=1,
        event_id=event_id,
        lamport=lamport,
        at=at,
        actor=actor,
        mission_id=mission_id,
        mission_slug=mission_slug,
        wp_id=None,
        force=False,
        execution_mode=execution_mode,
        skip_reason=skip_reason,
        skip_reason_source=skip_reason_source,
        policy_source=dict(policy_source),
        bypassed_provenance_kind="runtime_strict_gate",
        would_have_attempted=would_have_attempted,
    )

    _append_retro_lifecycle_event(feature_dir, event.to_dict())
    return event
