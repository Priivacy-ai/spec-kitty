"""Canonical status models for spec-kitty work package lifecycle.

Defines the 7-lane state machine data types: Lane enum, StatusEvent,
DoneEvidence (with ReviewApproval, RepoEvidence, VerificationResult),
and StatusSnapshot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Lane(StrEnum):
    """7-lane canonical work package lifecycle states."""

    PLANNED = "planned"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    FOR_REVIEW = "for_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELED = "canceled"


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
            verification=[
                VerificationResult.from_dict(v)
                for v in data.get("verification", [])
            ],
        )


@dataclass(frozen=True)
class StatusEvent:
    """Immutable record of a single lane transition.

    Each event is one line in status.events.jsonl.
    """

    event_id: str  # ULID
    feature_slug: str  # e.g. "034-feature-name"
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

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "event_id": self.event_id,
            "feature_slug": self.feature_slug,
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
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusEvent:
        evidence_data = data.get("evidence")
        return cls(
            event_id=data["event_id"],
            feature_slug=data["feature_slug"],
            wp_id=data["wp_id"],
            from_lane=Lane(data["from_lane"]),
            to_lane=Lane(data["to_lane"]),
            at=data["at"],
            actor=data["actor"],
            force=data["force"],
            execution_mode=data["execution_mode"],
            reason=data.get("reason"),
            review_ref=data.get("review_ref"),
            evidence=DoneEvidence.from_dict(evidence_data)
            if evidence_data
            else None,
            policy_metadata=data.get("policy_metadata"),
        )


@dataclass
class StatusSnapshot:
    """Materialized current state of all WPs in a feature (status.json).

    Produced by the deterministic reducer from the canonical event log.
    """

    feature_slug: str
    materialized_at: str  # ISO 8601 UTC
    event_count: int
    last_event_id: str | None
    work_packages: dict[str, dict[str, Any]]  # WP ID -> WPState
    summary: dict[str, int]  # lane -> count

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_slug": self.feature_slug,
            "materialized_at": self.materialized_at,
            "event_count": self.event_count,
            "last_event_id": self.last_event_id,
            "work_packages": self.work_packages,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusSnapshot:
        return cls(
            feature_slug=data["feature_slug"],
            materialized_at=data["materialized_at"],
            event_count=data["event_count"],
            last_event_id=data.get("last_event_id"),
            work_packages=data["work_packages"],
            summary=data["summary"],
        )
