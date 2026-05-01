"""Acceptance matrix — derived evidence view for feature acceptance.

The acceptance matrix is NOT an authoritative state source. The canonical
state authority remains status.events.jsonl + meta.json. This module
provides a structured evidence artifact that the acceptance gate reads
to validate evidence completeness before emitting transitions through
the existing event pipeline.

Persisted at kitty-specs/{mission_slug}/acceptance-matrix.json.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from specify_cli.mission_metadata import mission_identity_fields, resolve_mission_identity


@dataclass
class AcceptanceCriterion:
    """A single acceptance criterion with evidence."""

    criterion_id: str
    description: str
    proof_type: str  # "automated_test" | "manual_qa" | "code_review" | "negative_invariant"
    evidence: str | None = None
    pass_fail: str = "pending"  # noqa: S105  # "pass" | "fail" | "pending"
    verified_by: str | None = None
    verified_at: str | None = None
    notes: str | None = None


@dataclass
class NegativeInvariant:
    """A negative invariant — something that must NOT exist."""

    invariant_id: str
    description: str
    verification_method: str  # "grep_absence" | "route_check" | "custom_command"
    verification_command: str | None = None
    result: str = "pending"  # "confirmed_absent" | "still_present" | "pending"
    evidence: str | None = None


@dataclass
class AcceptanceMatrix:
    """Complete acceptance matrix for a feature.

    This is a derived evidence view. It does NOT participate in state
    transitions. The acceptance gate reads it to validate evidence
    completeness, then emits transitions through the event pipeline.
    """

    mission_slug: str
    criteria: list[AcceptanceCriterion] = field(default_factory=list)
    negative_invariants: list[NegativeInvariant] = field(default_factory=list)
    mission_number: str | None = None
    mission_type: str | None = None

    @property
    def overall_verdict(self) -> str:
        """Compute verdict from individual results."""
        all_items = [c.pass_fail for c in self.criteria] + [ni.result for ni in self.negative_invariants]
        if not all_items:
            return "pending"
        if any(v == "fail" or v == "still_present" for v in all_items):
            return "fail"
        if any(v == "pending" for v in all_items):
            return "pending"
        return "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            **mission_identity_fields(
                self.mission_slug,
                self.mission_number,
                self.mission_type,
            ),
            "overall_verdict": self.overall_verdict,
            "criteria": [asdict(c) for c in self.criteria],
            "negative_invariants": [asdict(ni) for ni in self.negative_invariants],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcceptanceMatrix:
        identity = mission_identity_fields(
            data["mission_slug"],
            data.get("mission_number"),
            data.get("mission_type"),
        )
        return cls(
            mission_slug=identity["mission_slug"],
            criteria=[
                AcceptanceCriterion(**c) for c in data.get("criteria", [])
            ],
            negative_invariants=[
                NegativeInvariant(**ni) for ni in data.get("negative_invariants", [])
            ],
            mission_number=identity["mission_number"],
            mission_type=identity["mission_type"],
        )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

MATRIX_FILENAME = "acceptance-matrix.json"


def write_acceptance_matrix(feature_dir: Path, matrix: AcceptanceMatrix) -> Path:
    """Write acceptance-matrix.json to the feature directory."""
    if (feature_dir / "meta.json").exists():
        identity = resolve_mission_identity(feature_dir)
        matrix.mission_slug = identity.mission_slug
        matrix.mission_number = (
            str(identity.mission_number)
            if identity.mission_number is not None
            else None
        )
        matrix.mission_type = identity.mission_type
    path = feature_dir / MATRIX_FILENAME
    path.write_text(
        json.dumps(matrix.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def read_acceptance_matrix(feature_dir: Path) -> AcceptanceMatrix | None:
    """Read acceptance-matrix.json. Returns None if absent."""
    path = feature_dir / MATRIX_FILENAME
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return AcceptanceMatrix.from_dict(data)


# ---------------------------------------------------------------------------
# Evidence validation
# ---------------------------------------------------------------------------


def validate_manual_evidence(criterion: AcceptanceCriterion) -> list[str]:
    """Validate that manual QA criteria have required evidence fields.

    Returns list of error messages. Empty means valid.
    """
    errors: list[str] = []
    if criterion.proof_type != "manual_qa":
        return errors
    if not criterion.evidence:
        errors.append(
            f"{criterion.criterion_id}: manual QA requires evidence (URL/screenshot)"
        )
    if not criterion.verified_at:
        errors.append(
            f"{criterion.criterion_id}: manual QA requires verified_at timestamp"
        )
    if not criterion.verified_by:
        errors.append(
            f"{criterion.criterion_id}: manual QA requires verified_by identity"
        )
    return errors


def validate_matrix_evidence(matrix: AcceptanceMatrix) -> list[str]:
    """Validate all evidence in the matrix. Returns list of errors."""
    errors: list[str] = []
    for criterion in matrix.criteria:
        errors.extend(validate_manual_evidence(criterion))
    return errors


# ---------------------------------------------------------------------------
# Negative invariant enforcement
# ---------------------------------------------------------------------------


def enforce_negative_invariants(
    repo_root: Path,
    invariants: list[NegativeInvariant],
) -> list[NegativeInvariant]:
    """Run all negative invariant checks. Returns updated invariants.

    Verification methods:
    - grep_absence: Run grep for pattern in repo, assert zero matches.
    - custom_command: Run a command, check exit code (0 = absent/pass).
    """
    results: list[NegativeInvariant] = []
    for ni in invariants:
        updated = _check_invariant(repo_root, ni)
        results.append(updated)
    return results


def _check_invariant(repo_root: Path, ni: NegativeInvariant) -> NegativeInvariant:
    """Run a single negative invariant check."""
    if ni.verification_method == "grep_absence":
        return _check_grep_absence(repo_root, ni)
    elif ni.verification_method == "custom_command":
        return _check_custom_command(repo_root, ni)
    else:
        # Unknown method — leave as pending
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="pending",
            evidence=f"Unknown verification method: {ni.verification_method}",
        )


def _check_grep_absence(repo_root: Path, ni: NegativeInvariant) -> NegativeInvariant:
    """Grep for pattern — zero matches means confirmed absent."""
    if not ni.verification_command:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="pending",
            evidence="No grep pattern specified in verification_command",
        )

    result = subprocess.run(
        ["grep", "-r", ni.verification_command, "."],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and not result.stdout.strip():
        # No matches — pattern is absent
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="confirmed_absent",
            evidence="grep found zero matches",
        )
    else:
        matches = result.stdout.strip().splitlines()[:5]
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="still_present",
            evidence=f"grep found matches: {'; '.join(matches)}",
        )


def _check_custom_command(repo_root: Path, ni: NegativeInvariant) -> NegativeInvariant:
    """Run custom command — exit code 0 means confirmed absent."""
    if not ni.verification_command:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="pending",
            evidence="No command specified in verification_command",
        )

    # User-authored acceptance matrices intentionally support shell snippets.
    result = subprocess.run(  # noqa: S602
        ni.verification_command,
        shell=True,  # nosec B602
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="confirmed_absent",
            evidence=f"Command exited 0: {result.stdout.strip()[:200]}",
        )
    else:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="still_present",
            evidence=f"Command exited {result.returncode}: {result.stderr.strip()[:200]}",
        )
