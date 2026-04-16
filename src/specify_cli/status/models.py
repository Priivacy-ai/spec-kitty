"""Canonical status models for spec-kitty work package lifecycle.

Defines the 9-lane state machine data types: Lane enum, StatusEvent,
DoneEvidence (with ReviewApproval, RepoEvidence, VerificationResult),
StatusSnapshot, and AgentAssignment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar, Optional

from specify_cli.core.identity_aliases import with_tracked_mission_slug_aliases
from specify_cli.mission_metadata import mission_identity_fields


class Lane(StrEnum):
    """9-lane canonical work package lifecycle states."""

    PLANNED = "planned"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    FOR_REVIEW = "for_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELED = "canceled"


def get_all_lanes() -> tuple[Lane, ...]:
    """Return all Lane enum members as a tuple.

    Use this instead of hardcoding lane lists or counts.
    Tests and production code should derive lane-dependent values from this.
    """
    return tuple(Lane)


def get_all_lane_values() -> frozenset[str]:
    """Return all canonical lane string values as a frozenset.

    Convenience for validators and mapping checks that operate on strings.
    """
    return frozenset(lane.value for lane in Lane)


ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


@dataclass(frozen=True)
class RepoEvidence:
    """Evidence of code changes in a repository."""

    repo: str
    branch: str
    commit: str  # 7-40 hex chars
    files_touched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "repo": self.repo,
            "branch": self.branch,
            "commit": self.commit,
        }
        if self.files_touched:
            d["files_touched"] = list(self.files_touched)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoEvidence:
        return cls(
            repo=data["repo"],
            branch=data["branch"],
            commit=data["commit"],
            files_touched=data.get("files_touched", []),
        )


@dataclass(frozen=True)
class VerificationResult:
    """Result of a verification command (test suite, linter, etc.)."""

    command: str
    result: str  # "pass", "fail", or "skip"
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "result": self.result,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationResult:
        return cls(
            command=data["command"],
            result=data["result"],
            summary=data["summary"],
        )


@dataclass(frozen=True)
class ReviewApproval:
    """Reviewer approval or change request record."""

    reviewer: str
    verdict: str  # "approved" or "changes_requested"
    reference: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer": self.reviewer,
            "verdict": self.verdict,
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewApproval:
        return cls(
            reviewer=data["reviewer"],
            verdict=data["verdict"],
            reference=data["reference"],
        )


@dataclass(frozen=True)
class DoneEvidence:
    """Evidence payload required for done transitions."""

    review: ReviewApproval
    repos: list[RepoEvidence] = field(default_factory=list)
    verification: list[VerificationResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"review": self.review.to_dict()}
        if self.repos:
            d["repos"] = [r.to_dict() for r in self.repos]
        if self.verification:
            d["verification"] = [v.to_dict() for v in self.verification]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DoneEvidence:
        return cls(
            review=ReviewApproval.from_dict(data["review"]),
            repos=[RepoEvidence.from_dict(r) for r in data.get("repos", [])],
            verification=[VerificationResult.from_dict(v) for v in data.get("verification", [])],
        )


@dataclass(frozen=True)
class ReviewResult:
    """Structured review outcome required for all outbound in_review transitions.

    Unifies the currently asymmetric approval (DoneEvidence.review: ReviewApproval)
    and rejection (review_ref: str) recording paths into a single typed contract.
    """

    reviewer: str
    verdict: str  # "approved" or "changes_requested"
    reference: str  # Approval ref or feedback:// URI
    feedback_path: str | None = None  # Resolved path to feedback file (rejection only)


@dataclass(frozen=True)
class StatusEvent:
    """Immutable record of a single lane transition.

    Each event is one line in status.events.jsonl.

    Wire-format evolution (FR-023, ADR 2026-04-09-1):
    - Legacy events: carry only ``mission_slug`` for mission identity.
    - New events (post-WP05): carry both ``mission_slug`` AND ``mission_id``
      (the ULID from meta.json).  ``mission_id`` is the canonical
      machine-facing identity; ``mission_slug`` is retained for human
      readability and backward compatibility.
    """

    event_id: str  # ULID
    mission_slug: str  # e.g. "034-feature-name"
    wp_id: str  # e.g. "WP01"
    from_lane: Lane
    to_lane: Lane
    at: str  # ISO 8601 UTC
    actor: str
    force: bool
    execution_mode: str  # "worktree" or "direct_repo"
    reason: str | None = None
    review_ref: str | None = None
    evidence: DoneEvidence | None = None
    policy_metadata: dict[str, Any] | None = None
    # mission_id (ULID) added in WP05; None for legacy events read from disk
    # before the migration, or for missions that pre-date mission_id minting.
    mission_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "event_id": self.event_id,
            "mission_slug": self.mission_slug,
            "wp_id": self.wp_id,
            "from_lane": str(self.from_lane),
            "to_lane": str(self.to_lane),
            "at": self.at,
            "actor": self.actor,
            "force": self.force,
            "execution_mode": self.execution_mode,
            "reason": self.reason,
            "review_ref": self.review_ref,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "policy_metadata": self.policy_metadata,
        }
        if self.mission_id is not None:
            d["mission_id"] = self.mission_id
        return d

    # Legacy lane name aliases from older event log formats.
    # Note: "in_review" was formerly aliased to "for_review" but is now a
    # first-class Lane member (promoted in mission 065 WP05).
    _LANE_ALIASES: ClassVar[dict[str, str]] = {}

    @classmethod
    def _coerce_lane(cls, value: str) -> Lane:
        return Lane(cls._LANE_ALIASES.get(value, value))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusEvent:
        evidence_data = data.get("evidence")
        return cls(
            event_id=data["event_id"],
            mission_slug=data.get("mission_slug") or data.get("feature_slug", ""),
            wp_id=data["wp_id"],
            from_lane=cls._coerce_lane(data["from_lane"]),
            to_lane=cls._coerce_lane(data["to_lane"]),
            at=data["at"],
            actor=data["actor"],
            force=data["force"],
            execution_mode=data["execution_mode"],
            reason=data.get("reason"),
            review_ref=data.get("review_ref"),
            evidence=DoneEvidence.from_dict(evidence_data) if evidence_data else None,
            policy_metadata=data.get("policy_metadata"),
            mission_id=data.get("mission_id"),  # None for legacy events
        )


@dataclass
class StatusSnapshot:
    """Materialized current state of all WPs in a feature (status.json).

    Produced by the deterministic reducer from the canonical event log.
    """

    mission_slug: str
    materialized_at: str  # ISO 8601 UTC
    event_count: int
    last_event_id: str | None
    work_packages: dict[str, dict[str, Any]]  # WP ID -> WPState
    summary: dict[str, int]  # lane -> count
    mission_number: str | None = None
    mission_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = with_tracked_mission_slug_aliases(
            {
                **mission_identity_fields(
                    self.mission_slug,
                    self.mission_number,
                    self.mission_type,
                ),
                "materialized_at": self.materialized_at,
                "event_count": self.event_count,
                "last_event_id": self.last_event_id,
                "work_packages": self.work_packages,
                "summary": self.summary,
            }
        )
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusSnapshot:
        feature_slug = data.get("mission_slug") or data.get("feature_slug")
        if feature_slug is None:
            raise KeyError("mission_slug")
        return cls(
            mission_slug=feature_slug,
            materialized_at=data["materialized_at"],
            event_count=data["event_count"],
            last_event_id=data.get("last_event_id"),
            work_packages=data["work_packages"],
            summary=data["summary"],
            mission_number=data.get("mission_number"),
            mission_type=data.get("mission_type"),
        )


@dataclass(frozen=True)
class AgentAssignment:
    """Resolved agent assignment with complete context.

    Represents the fully-resolved agent assigned to a work package,
    including the tool (AI agent type), model, optional profile ID, and role.

    This value object is the output of legacy coercion and fallback resolution
    from WPMetadata.resolved_agent(). It provides a clean, typed interface for
    consumers to access agent assignment context.

    Attributes:
        tool: AI agent identifier (e.g., 'claude', 'copilot', 'gemini', 'cursor').
        model: Model identifier (e.g., 'claude-opus-4-6', 'gpt-4-turbo').
        profile_id: Optional profile identifier for agent configuration override.
        role: Optional role for this assignment (e.g., 'reviewer', 'implementer').

    Example:
        >>> assignment = wp_metadata.resolved_agent()
        >>> print(assignment.tool)  # 'claude'
        >>> print(assignment.model)  # 'claude-opus-4-6'
    """

    tool: str
    model: str
    profile_id: str | None = None
    role: str | None = None


@dataclass
class TransitionRequest:
    """All inputs for a single status transition.

    Consolidates the 19 parameters of ``emit_status_transition`` into one
    typed object so call sites are self-documenting and the function
    signature stays stable as new fields are added.
    """

    # Mission identity
    feature_dir: Path | None = None
    mission_dir: Path | None = None
    mission_slug: str | None = None
    _legacy_mission_slug: str | None = None
    repo_root: Path | None = None
    # Transition target
    wp_id: str | None = None
    to_lane: str | None = None
    force: bool = False
    reason: str | None = None
    # Actor
    actor: str | None = None
    execution_mode: str = "worktree"
    # Evidence
    evidence: dict[str, Any] | None = None
    review_ref: str | None = None
    review_result: Any = None
    # Guard hints (callers may pre-compute these; emit derives them otherwise)
    workspace_context: str | None = None
    subtasks_complete: bool | None = None
    implementation_evidence_present: bool | None = None
    policy_metadata: dict[str, Any] | None = None


@dataclass
class GuardContext:
    """Inputs required by guard condition evaluators.

    Consolidates the 10 keyword-only parameters shared between
    ``validate_transition`` and ``_run_guard`` so guard functions
    receive a single typed context object instead of an expanding
    keyword list.
    """

    actor: str | None = None
    workspace_context: str | None = None
    subtasks_complete: bool | None = None
    implementation_evidence_present: bool | None = None
    reason: str | None = None
    review_ref: str | None = None
    evidence: Any = None
    force: bool = False
    review_result: Any = None
    current_actor: str | None = None
