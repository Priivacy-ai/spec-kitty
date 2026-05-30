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
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from specify_cli.configured_command import ConfiguredCommandUnsupported, run_configured_command
from specify_cli.mission_metadata import mission_identity_fields, resolve_mission_identity


def _split_known_fields(
    cls: type[Any],
    data: dict[str, Any],
    *,
    exclude: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    excluded = exclude or set()
    known = {f.name for f in fields(cls)} - {"extras"} - excluded
    kwargs = {key: value for key, value in data.items() if key in known}
    extras = {key: value for key, value in data.items() if key not in known and key not in excluded}
    return kwargs, extras


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
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcceptanceCriterion:
        kwargs, extras = _split_known_fields(cls, data)
        return cls(**kwargs, extras=extras)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extras = data.pop("extras", {}) or {}
        data.update(extras)
        return data


@dataclass
class NegativeInvariant:
    """A negative invariant — something that must NOT exist."""

    invariant_id: str
    description: str
    verification_method: str  # "grep_absence" | "route_check" | "custom_command"
    verification_command: str | None = None
    result: str = "pending"  # "confirmed_absent" | "still_present" | "pending"
    evidence: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NegativeInvariant:
        kwargs, extras = _split_known_fields(cls, data)
        return cls(**kwargs, extras=extras)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extras = data.pop("extras", {}) or {}
        data.update(extras)
        return data


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
    extras: dict[str, Any] = field(default_factory=dict)

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
        data = {
            **mission_identity_fields(
                self.mission_slug,
                self.mission_number,
                self.mission_type,
            ),
            "overall_verdict": self.overall_verdict,
            "criteria": [c.to_dict() for c in self.criteria],
            "negative_invariants": [ni.to_dict() for ni in self.negative_invariants],
        }
        data.update(self.extras)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcceptanceMatrix:
        kwargs, extras = _split_known_fields(cls, data, exclude={"overall_verdict"})
        identity = mission_identity_fields(
            data["mission_slug"],
            data.get("mission_number"),
            data.get("mission_type"),
        )
        return cls(
            mission_slug=identity["mission_slug"],
            criteria=[
                AcceptanceCriterion.from_dict(c) for c in data.get("criteria", [])
            ],
            negative_invariants=[
                NegativeInvariant.from_dict(ni) for ni in data.get("negative_invariants", [])
            ],
            mission_number=kwargs.get("mission_number", identity["mission_number"]),
            mission_type=kwargs.get("mission_type", identity["mission_type"]),
            extras=extras,
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


# Marker dropped into scaffolded criteria so operators (and reviewers) can
# tell a placeholder row apart from a real, authored acceptance criterion.
SCAFFOLD_TODO_MARKER = "TODO: replace with a real acceptance criterion"


def scaffold_acceptance_matrix(
    feature_dir: Path,
    mission_slug: str,
    requirement_ids: list[str] | None = None,
) -> Path | None:
    """Author a minimal, schema-valid ``acceptance-matrix.json`` for a feature.

    Lane-based features require ``acceptance-matrix.json`` to exist before the
    acceptance gate will run (see ``specify_cli.acceptance``). This helper
    scaffolds a minimal but schema-valid matrix at task-finalization time so the
    artifact is never silently missing.

    The scaffold is **idempotent**: an existing ``acceptance-matrix.json`` is
    never overwritten, so operator-curated criteria survive re-runs.

    When ``requirement_ids`` are supplied (e.g. functional requirement ids from
    ``spec.md``), one ``pending`` criterion is derived per requirement. When no
    requirement ids are available, a single placeholder criterion carrying
    :data:`SCAFFOLD_TODO_MARKER` is written so the file is valid yet obviously
    awaiting real content.

    Args:
        feature_dir: The ``kitty-specs/<slug>/`` directory for the mission.
        mission_slug: Feature slug (e.g. ``010-lane-only-runtime``).
        requirement_ids: Optional functional requirement ids to seed criteria.

    Returns:
        Path to the scaffolded (or pre-existing) ``acceptance-matrix.json``.
    """
    path = feature_dir / MATRIX_FILENAME
    if path.exists():
        # Respect operator-curated content; idempotent re-runs must not clobber.
        return path

    criteria: list[AcceptanceCriterion] = []
    for req_id in requirement_ids or []:
        criteria.append(
            AcceptanceCriterion(
                criterion_id=req_id,
                description=f"Verify {req_id} is satisfied",
                proof_type="automated_test",
                pass_fail="pending",  # noqa: S106
                notes=SCAFFOLD_TODO_MARKER,
            )
        )

    if not criteria:
        # Empty-but-valid scaffold with an explicit TODO marker. A single
        # placeholder keeps the JSON schema-valid while signalling clearly that
        # no real criteria have been authored yet.
        criteria.append(
            AcceptanceCriterion(
                criterion_id="AC-001",
                description=SCAFFOLD_TODO_MARKER,
                proof_type="automated_test",
                pass_fail="pending",  # noqa: S106
                notes=SCAFFOLD_TODO_MARKER,
            )
        )

    matrix = AcceptanceMatrix(mission_slug=mission_slug, criteria=criteria)
    return write_acceptance_matrix(feature_dir, matrix)


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
            extras=ni.extras,
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
            extras=ni.extras,
        )

    result = subprocess.run(
        [
            "grep",
            "-r",
            "--exclude=acceptance-matrix.json",
            "--exclude-dir=.git",
            "--",
            ni.verification_command,
            ".",
        ],
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
            extras=ni.extras,
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
            extras=ni.extras,
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
            extras=ni.extras,
        )

    try:
        result = run_configured_command(
            ni.verification_command,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
    except ConfiguredCommandUnsupported as exc:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="pending",
            evidence=str(exc),
            extras=ni.extras,
        )
    except OSError as exc:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="still_present",
            evidence=f"Command failed to start: {exc}",
            extras=ni.extras,
        )
    if result.returncode == 0:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="confirmed_absent",
            evidence=f"Command exited 0: {result.stdout.strip()[:200]}",
            extras=ni.extras,
        )
    else:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="still_present",
            evidence=f"Command exited {result.returncode}: {result.stderr.strip()[:200]}",
            extras=ni.extras,
        )
