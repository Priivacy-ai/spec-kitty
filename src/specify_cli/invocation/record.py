"""InvocationRecord Pydantic v2 model and MinimalViableTrailPolicy.

Validation rules:
- invocation_id must be a valid ULID (26 chars)
- started_at must be ISO-8601 UTC
- event discriminator must be "started" or "completed"
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


class InvocationRecord(BaseModel):
    """v1 JSONL event record. Each invocation produces one file with two events."""

    event: Literal["started", "completed"]
    invocation_id: str  # ULID (26 chars)
    profile_id: str
    action: str  # canonical action token
    request_text: str = ""
    governance_context_hash: str = ""  # first 16 hex chars of SHA-256
    governance_context_available: bool = True
    actor: str = "unknown"  # "claude" | "operator" | "unknown"
    router_confidence: str | None = None  # "exact" | "canonical_verb" | "domain_keyword"
    started_at: str = ""  # ISO-8601 UTC
    # completed event fields (null until profile-invocation complete)
    completed_at: str | None = None
    outcome: Literal["done", "failed", "abandoned"] | None = None
    evidence_ref: str | None = None

    # Additive optional field (FR-008): derived from CLI entry command via derive_mode().
    # None for pre-mission records (legacy invocations that predate WP06).
    # Serialised as the enum value string (e.g. "advisory"); excluded when None.
    mode_of_work: str | None = None

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Tier policy dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TierPolicy:
    """Configuration for a single trail tier."""

    name: str
    mandatory: bool
    description: str
    storage_path: str
    promotion_trigger: str = ""


@dataclass(frozen=True)
class MinimalViableTrailPolicy:
    """
    The three-tier minimal viable trail contract.
    Every Spec Kitty action's audit trail requirements.

    Tier 1 (every_invocation): mandatory. One InvocationRecord in local JSONL before executor returns.
    Tier 2 (evidence_artifact): optional. EvidenceArtifact when invocation produces checkable output.
    Tier 3 (durable_project_state): optional. kitty-specs/ / doctrine artifact only for domain-state changes.
    """

    tier_1: TierPolicy
    tier_2: TierPolicy
    tier_3: TierPolicy


MINIMAL_VIABLE_TRAIL_POLICY = MinimalViableTrailPolicy(
    tier_1=TierPolicy(
        name="every_invocation",
        mandatory=True,
        description=("One InvocationRecord written locally before executor returns. Applies to all advise / ask / do invocations."),
        storage_path=".kittify/events/profile-invocations/{invocation_id}.jsonl",
    ),
    tier_2=TierPolicy(
        name="evidence_artifact",
        mandatory=False,
        description=(
            "Optional EvidenceArtifact for invocations that produce checkable output. Created when caller passes --evidence to profile-invocation complete."
        ),
        storage_path=".kittify/evidence/{invocation_id}/",
        promotion_trigger="caller sets evidence_ref on profile-invocation complete",
    ),
    tier_3=TierPolicy(
        name="durable_project_state",
        mandatory=False,
        description=(
            "Promotion to kitty-specs/ or doctrine artifacts only when invocation "
            "changes project-domain state. Applies to specify, plan, tasks, merge, accept only."
        ),
        storage_path="kitty-specs/{mission_slug}/",
        promotion_trigger="spec, plan, tasks, merge, accept commands only",
    ),
)


# ---------------------------------------------------------------------------
# Tier eligibility
# ---------------------------------------------------------------------------

# Actions that qualify for Tier 3 (durable project state changes)
TIER_3_ACTIONS: frozenset[str] = frozenset(
    {
        "specify",
        "plan",
        "tasks",
        "merge",
        "accept",
    }
)


@dataclass(frozen=True)
class TierEligibility:
    """Which trail tiers apply to a given invocation."""

    tier_1: bool = True  # always True — every invocation has Tier 1
    tier_2: bool = False  # True if evidence_ref is set on completed event
    tier_3: bool = False  # True if action is in TIER_3_ACTIONS


def tier_eligible(record: InvocationRecord) -> TierEligibility:
    """Determine which trail tiers apply to a completed InvocationRecord."""
    return TierEligibility(
        tier_1=True,
        tier_2=record.evidence_ref is not None,
        tier_3=record.action in TIER_3_ACTIONS,
    )


# ---------------------------------------------------------------------------
# Evidence artifact promotion (Tier 2)
# ---------------------------------------------------------------------------


@dataclass
class EvidenceArtifact:
    """A Tier 2 evidence artifact written to the evidence base directory."""

    invocation_id: str
    directory: Path
    evidence_file: Path
    record_snapshot: Path


# ---------------------------------------------------------------------------
# Profile-invocation lifecycle pair (WP05 / data-model.md §4)
# ---------------------------------------------------------------------------


ProfileInvocationPhase = Literal["started", "completed", "failed"]


@dataclass(frozen=True)
class ProfileInvocationRecord:
    """Paired profile-invocation lifecycle record (WP05).

    Captures one phase of a public action `next` issued. For every `started`
    record there should eventually be exactly one paired `completed` or
    `failed` record sharing the same ``canonical_action_id``.

    See data-model.md §4 and contracts/invocation-lifecycle.md.
    """

    canonical_action_id: str
    phase: ProfileInvocationPhase
    at: _dt.datetime
    agent: str
    mission_id: str
    wp_id: str | None = None
    reason: str | None = None
    # Optional tag set by the writer for ergonomic filtering. Not part of the
    # canonical schema; ignored by readers that don't recognise it.
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the on-disk JSON shape (sorted-key stable).

        Optional fields are omitted when None for line-stability with the
        contract example. ``metadata`` is omitted when empty.
        """
        payload: dict[str, Any] = {
            "canonical_action_id": self.canonical_action_id,
            "phase": self.phase,
            "at": _ensure_iso_utc(self.at),
            "agent": self.agent,
            "mission_id": self.mission_id,
            "wp_id": self.wp_id,
            "reason": self.reason,
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileInvocationRecord:
        """Parse from the on-disk JSON shape.

        Tolerates missing optional fields. Coerces ``at`` from ISO string.
        """
        at_raw = data.get("at")
        if isinstance(at_raw, _dt.datetime):
            at_value = at_raw
        elif isinstance(at_raw, str) and at_raw:
            at_value = _dt.datetime.fromisoformat(at_raw)
        else:
            raise ValueError("ProfileInvocationRecord requires 'at' (ISO-8601 string or datetime)")

        metadata_raw = data.get("metadata") or {}
        metadata: dict[str, str] = {}
        if isinstance(metadata_raw, dict):
            for k, v in metadata_raw.items():
                metadata[str(k)] = str(v)

        phase_raw = data.get("phase")
        if phase_raw not in ("started", "completed", "failed"):
            raise ValueError(f"ProfileInvocationRecord.phase must be started|completed|failed, got {phase_raw!r}")

        return cls(
            canonical_action_id=str(data["canonical_action_id"]),
            phase=phase_raw,
            at=at_value,
            agent=str(data["agent"]),
            mission_id=str(data["mission_id"]),
            wp_id=(str(data["wp_id"]) if data.get("wp_id") is not None else None),
            reason=(str(data["reason"]) if data.get("reason") is not None else None),
            metadata=metadata,
        )

    def to_json_line(self) -> str:
        """Serialise to a single JSON line (sorted keys for stability)."""
        return json.dumps(self.to_dict(), sort_keys=True)


def _ensure_iso_utc(dt: _dt.datetime) -> str:
    """Return ISO-8601 string. Naive datetimes are assumed UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.UTC)
    return dt.isoformat()


def promote_to_evidence(
    record: InvocationRecord,
    evidence_base_dir: Path,
    content: str,
) -> EvidenceArtifact:
    """
    Create a Tier 2 EvidenceArtifact at evidence_base_dir/<invocation_id>/.

    Creates:
      - evidence_base_dir/<invocation_id>/evidence.md  (caller-supplied content)
      - evidence_base_dir/<invocation_id>/record.json  (snapshot of invocation record)
    """
    artifact_dir = evidence_base_dir / record.invocation_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = artifact_dir / "evidence.md"
    record_file = artifact_dir / "record.json"
    evidence_file.write_text(content, encoding="utf-8")
    record_file.write_text(json.dumps(record.model_dump(), indent=2), encoding="utf-8")
    return EvidenceArtifact(
        invocation_id=record.invocation_id,
        directory=artifact_dir,
        evidence_file=evidence_file,
        record_snapshot=record_file,
    )
