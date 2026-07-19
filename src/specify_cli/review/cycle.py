"""Shared review-cycle invariant boundary.

This module owns only rejected review-cycle artifact invariants:
artifact creation, required frontmatter validation, canonical pointer
construction/resolution, legacy feedback pointer normalization, and rejected
ReviewResult derivation.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.missions._read_path_resolver import (
    _canonicalize_primary_read_handle,
    candidate_feature_dir_for_mission,
    primary_feature_dir_for_mission,
)

from specify_cli.review.artifacts import (
    AffectedFile,
    ReviewCycleArtifact,
    _review_cycle_suffix,
)

from specify_cli.status import ReviewResult

UTC_SECOND_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
REVIEW_FEEDBACK_SENTINELS = frozenset({"force-override", "action-review-claim"})
REVIEW_CYCLE_MIGRATION_REQUIRED_CODE = "REVIEW_CYCLE_MIGRATION_REQUIRED"

_REVIEW_CYCLE_FILE_RE = re.compile(r"^review-cycle-(?P<cycle>[1-9][0-9]*)\.md$")
_WP_ID_FROM_SLUG_RE = re.compile(r"^(WP\d+)\b")

ReviewCycleCompatibilityState = Literal["canonical", "empty", "migration_required"]


class ReviewCycleError(ValueError):
    """Raised when a review-cycle invariant cannot be satisfied."""


@dataclass(frozen=True)
class ReviewCyclePointerParts:
    """Validated canonical review-cycle pointer segments."""

    mission_slug: str
    wp_slug: str
    filename: str

    @property
    def cycle_number(self) -> int:
        match = _REVIEW_CYCLE_FILE_RE.match(self.filename)
        if match is None:  # pragma: no cover - impossible after validation
            raise ReviewCycleError(f"Invalid review-cycle filename: {self.filename}")
        return int(match.group("cycle"))


@dataclass(frozen=True)
class ReviewCycleCompatibility:
    """Compatibility classification for review-cycle read attempts."""

    state: ReviewCycleCompatibilityState
    reason: str
    reason_code: str | None
    canonical_home: Path
    opposite_home: Path
    diagnostics: tuple[str, ...] = ()
    latest_cycle: int | None = None
    latest_path: Path | None = None


def _serialize_json_migration_payload(
    mission_slug: str,
    wp_id: str,
    compatibility: ReviewCycleCompatibility,
) -> dict[str, Any]:
    """Build the exact migration payload for typed migration refusal."""
    return {
        "status": "error",
        "error_code": REVIEW_CYCLE_MIGRATION_REQUIRED_CODE,
        "mission_slug": mission_slug,
        "wp_id": wp_id,
        "artifact_kind": "review_cycle",
        "state": compatibility.state,
        "canonical_home": str(compatibility.canonical_home),
        "opposite_home": str(compatibility.opposite_home),
        "reason": compatibility.reason,
        "diagnostics": list(compatibility.diagnostics),
        "recovery": "resolve review-cycle migration before retrying rejection writes or reads",
    }


@dataclass(frozen=True)
class ResolvedReviewCyclePointer:
    """Resolution result for review feedback references."""

    reference: str
    path: Path | None
    kind: Literal["canonical", "legacy", "sentinel", "path"]
    state: ReviewCycleCompatibilityState = "empty"
    warnings: tuple[str, ...] = ()
    reason: str | None = None
    canonical_home: Path | None = None
    opposite_home: Path | None = None
    diagnostics: tuple[str, ...] = ()

    @property
    def is_resolved(self) -> bool:
        return self.path is not None


@dataclass(frozen=True)
class CreatedRejectedReviewCycle:
    """Validated rejected review cycle ready for status mutation."""

    artifact_path: Path
    pointer: str
    artifact: ReviewCycleArtifact
    review_result: ReviewResult
    warnings: tuple[str, ...] = ()


def _validate_segment(name: str, value: str) -> str:
    """Return a single safe path segment or raise ReviewCycleError.

    Delegates to the canonical ``assert_safe_path_segment`` (FR-001 / WP01) and
    re-raises any ``ValueError`` as ``ReviewCycleError`` to preserve the call-site
    contract (C-001: migrate, don't wrap — no parallel mechanism).
    """
    try:
        return cast(str, assert_safe_path_segment(value))
    except ValueError as exc:
        raise ReviewCycleError(f"{name} is not a safe path segment: {exc}") from exc


def _expected_wp_id_from_slug(wp_slug: str) -> str | None:
    """Infer a WP identifier from a canonical slug (``WPXX-...``)."""
    match = _WP_ID_FROM_SLUG_RE.match(wp_slug)
    if match is None:
        return None
    return match.group(1)


def _canonical_and_opposite_homes(
    repo_root: Path, mission_slug: str, wp_slug: str
) -> tuple[Path, Path]:
    """Return canonical and opposite review-cycle homes for typed compatibility checks."""
    canonical_home = (
        candidate_feature_dir_for_mission(repo_root, mission_slug)
        / "tasks"
        / wp_slug
    )
    opposite_home = (
        primary_feature_dir_for_mission(
            repo_root, _canonicalize_primary_read_handle(repo_root, mission_slug)
        )
        / "tasks"
        / wp_slug
    )
    return canonical_home, opposite_home


def _scan_home_for_compatibility(
    home: Path,
    mission_slug: str,
    wp_id: str | None,
    *,
    role: str,
) -> ReviewCycleCompatibility:
    """Scan a review-cycle home and report canonical validity diagnostics."""
    if not home.exists() or not home.is_dir():
        return ReviewCycleCompatibility(
            state="empty",
            reason="no-review-cycle-home",
            reason_code=None,
            canonical_home=home,
            opposite_home=home,
        )

    diagnostics: list[str] = []
    valid_pairs: list[tuple[int, Path]] = []
    for candidate in home.glob("review-cycle-*.md"):
        suffix = _review_cycle_suffix(candidate)
        if suffix is None:
            diagnostics.append(f"{role}: malformed review-cycle filename: {candidate.name}")
            continue

        try:
            artifact = validate_review_artifact_file(candidate)
        except ValueError as exc:
            diagnostics.append(f"{role}: unreadable or invalid artifact {candidate.name}: {exc}")
            continue

        if artifact.cycle_number != suffix:
            diagnostics.append(
                f"{role}: cycle-number mismatch for {candidate.name}: suffix={suffix}, artifact={artifact.cycle_number}"
            )
            continue
        if artifact.mission_slug != mission_slug:
            diagnostics.append(
                f"{role}: mission_slug mismatch for {candidate.name}: "
                f"expected {mission_slug}, got {artifact.mission_slug}"
            )
            continue
        if wp_id and artifact.wp_id != wp_id:
            diagnostics.append(
                f"{role}: wp_id mismatch for {candidate.name}: expected {wp_id}, got {artifact.wp_id}"
            )
            continue
        valid_pairs.append((suffix, candidate))

    if diagnostics:
        reason = diagnostics[0]
    elif valid_pairs:
        reason = "valid-home"
    else:
        reason = "no-valid-review-cycle-artifacts"

    latest_cycle: int | None = None
    latest_path: Path | None = None
    if valid_pairs:
        latest_cycle, latest_path = max(valid_pairs, key=lambda item: item[0])

    state: ReviewCycleCompatibilityState = "migration_required"
    if diagnostics:
        state = "migration_required"
    elif valid_pairs:
        state = "canonical"
    else:
        state = "empty"

    return ReviewCycleCompatibility(
        state=state,
        reason=reason,
        reason_code="REVIEW_CYCLE_HOME_INVALID" if diagnostics else None,
        canonical_home=home,
        opposite_home=home,
        diagnostics=tuple(diagnostics),
        latest_cycle=latest_cycle,
        latest_path=latest_path,
    )


def resolve_review_cycle_compatibility(
    repo_root: Path,
    mission_slug: str,
    wp_slug: str,
    wp_id: str | None = None,
) -> ReviewCycleCompatibility:
    """Classify the typed review-cycle compatibility state for canonical access."""
    canonical_home, opposite_home = _canonical_and_opposite_homes(
        repo_root, mission_slug, wp_slug
    )
    expected_wp_id = wp_id
    if expected_wp_id is None:
        expected_wp_id = _expected_wp_id_from_slug(wp_slug)

    canonical_scan = _scan_home_for_compatibility(
        canonical_home,
        mission_slug=mission_slug,
        wp_id=expected_wp_id,
        role="canonical",
    )
    opposite_scan = _scan_home_for_compatibility(
        opposite_home,
        mission_slug=mission_slug,
        wp_id=expected_wp_id,
        role="opposite",
    )

    if canonical_scan.state == "migration_required":
        return canonical_scan

    if canonical_scan.state == "canonical":
        return canonical_scan

    if opposite_scan.state == "canonical":
        return ReviewCycleCompatibility(
            state="migration_required",
            reason="opposite-home-only-review-cycle-history",
            reason_code="OPPOSITE_HOME_ONLY",
            canonical_home=canonical_scan.canonical_home,
            opposite_home=opposite_scan.canonical_home,
            diagnostics=opposite_scan.diagnostics,
            latest_cycle=opposite_scan.latest_cycle,
            latest_path=opposite_scan.latest_path,
        )

    if opposite_scan.state == "migration_required":
        return ReviewCycleCompatibility(
            state="migration_required",
            reason="opposite-home-invalid-review-cycle-history",
            reason_code=opposite_scan.reason_code,
            canonical_home=canonical_scan.canonical_home,
            opposite_home=opposite_scan.canonical_home,
            diagnostics=(
                *opposite_scan.diagnostics,
                "opposite-home review-cycle history is present but incompatible",
            ),
            latest_cycle=opposite_scan.latest_cycle,
            latest_path=opposite_scan.latest_path,
        )

    return ReviewCycleCompatibility(
        state="empty",
        reason="no-review-cycle-history",
        reason_code=None,
        canonical_home=canonical_scan.canonical_home,
        opposite_home=opposite_scan.canonical_home,
    )


def _resolve_git_common_dir(repo_root: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    raw_value = result.stdout.strip()
    if not raw_value:
        return None
    common_dir = Path(raw_value)
    if not common_dir.is_absolute():
        common_dir = (repo_root / common_dir).resolve()
    return common_dir


def build_review_cycle_pointer(mission_slug: str, wp_slug: str, filename: str) -> str:
    """Return a canonical ``review-cycle://`` pointer after validation."""
    parts = ReviewCyclePointerParts(
        mission_slug=_validate_segment("mission_slug", mission_slug),
        wp_slug=_validate_segment("wp_slug", wp_slug),
        filename=_validate_review_cycle_filename(filename),
    )
    return f"review-cycle://{parts.mission_slug}/{parts.wp_slug}/{parts.filename}"


def _validate_review_cycle_filename(filename: str) -> str:
    candidate = _validate_segment("filename", filename)
    if _REVIEW_CYCLE_FILE_RE.fullmatch(candidate) is None:
        raise ReviewCycleError("filename must match review-cycle-N.md")
    return candidate


def validate_review_cycle_pointer(pointer: str) -> ReviewCyclePointerParts:
    """Parse and validate a canonical review-cycle pointer."""
    value = pointer.strip()
    if not value.startswith("review-cycle://"):
        raise ReviewCycleError("review-cycle pointer must start with review-cycle://")

    relative = value[len("review-cycle://") :]
    raw_parts = relative.split("/")
    if len(raw_parts) != 3:
        raise ReviewCycleError("review-cycle pointer must have mission/wp/file segments")

    return ReviewCyclePointerParts(
        mission_slug=_validate_segment("mission_slug", raw_parts[0]),
        wp_slug=_validate_segment("wp_slug", raw_parts[1]),
        filename=_validate_review_cycle_filename(raw_parts[2]),
    )


def validate_review_artifact(artifact: ReviewCycleArtifact) -> None:
    """Validate required review artifact fields and rejected-review semantics."""
    if artifact.cycle_number < 1:
        raise ReviewCycleError("review artifact cycle_number must be positive")
    _validate_segment("wp_id", artifact.wp_id)
    _validate_segment("mission_slug", artifact.mission_slug)
    if not str(artifact.reviewer_agent).strip():
        raise ReviewCycleError("review artifact reviewer_agent is required")
    if not str(artifact.reviewed_at).strip():
        raise ReviewCycleError("review artifact reviewed_at is required")
    if artifact.verdict != "rejected":
        raise ReviewCycleError("rejected review cycle artifact must have verdict: rejected")
    if not str(artifact.body).strip():
        raise ReviewCycleError("review artifact body is required")


def validate_review_artifact_file(path: Path) -> ReviewCycleArtifact:
    """Load and validate a persisted review-cycle artifact."""
    artifact = ReviewCycleArtifact.from_file(path)
    validate_review_artifact(artifact)
    return artifact


def resolve_review_cycle_pointer(repo_root: Path, pointer: str) -> ResolvedReviewCyclePointer:
    """Resolve canonical and legacy review feedback references.

    Sentinels return a structured no-artifact result. Canonical pointers are
    validated and must point at a readable, valid review-cycle artifact. Legacy
    ``feedback://`` references resolve through the git common-dir with a warning.
    """
    value = pointer.strip()
    if not value:
        return ResolvedReviewCyclePointer(reference=pointer, path=None, kind="path")
    if value in REVIEW_FEEDBACK_SENTINELS:
        return ResolvedReviewCyclePointer(reference=value, path=None, kind="sentinel")

    if value.startswith("review-cycle://"):
        try:
            parts = validate_review_cycle_pointer(value)
        except ReviewCycleError:
            compatibility = ReviewCycleCompatibility(
                state="migration_required",
                reason="malformed review-cycle pointer",
                reason_code="MALFORMED_POINTER",
                canonical_home=repo_root,
                opposite_home=repo_root,
            )
            return ResolvedReviewCyclePointer(
                reference=value,
                path=None,
                kind="canonical",
                state="migration_required",
                reason=compatibility.reason,
                canonical_home=compatibility.canonical_home,
                opposite_home=compatibility.opposite_home,
                diagnostics=(compatibility.reason,),
            )

        compatibility = resolve_review_cycle_compatibility(
            repo_root,
            mission_slug=parts.mission_slug,
            wp_slug=parts.wp_slug,
            wp_id=_expected_wp_id_from_slug(parts.wp_slug),
        )
        if compatibility.state == "migration_required":
            return ResolvedReviewCyclePointer(
                reference=value,
                path=None,
                kind="canonical",
                state="migration_required",
                reason=compatibility.reason,
                canonical_home=compatibility.canonical_home,
                opposite_home=compatibility.opposite_home,
                diagnostics=compatibility.diagnostics,
            )

        # #2136/#2164: resolve the mission dir through the SAME topology-aware fold
        # the WRITE seam uses (``create_rejected_review_cycle`` →
        # ``candidate_feature_dir_for_mission``) rather than a raw
        # ``kitty-specs/<mission_slug>`` join. The pointer's mission_slug
        # is whatever handle the emitting writer was given; a bare ``mid8`` / human
        # slug names the on-disk ``<slug>-<mid8>`` dir only after canonicalization,
        # so the raw join would compose a DIVERGENT path from where the artifact was
        # written. The shared resolver converges every handle form on the one dir and
        # propagates ``MissionSelectorAmbiguous`` (no silent pick — C-009).
        candidate = (
            compatibility.canonical_home / parts.filename
        ).resolve()
        if not candidate.exists() or not candidate.is_file():
            return ResolvedReviewCyclePointer(
                reference=value,
                path=None,
                kind="canonical",
                state=compatibility.state,
                canonical_home=compatibility.canonical_home,
                opposite_home=compatibility.opposite_home,
            )
        try:
            validate_review_artifact_file(candidate)
        except ValueError:
            return ResolvedReviewCyclePointer(
                reference=value,
                path=None,
                kind="canonical",
                state="migration_required",
                reason="target artifact is malformed",
                canonical_home=compatibility.canonical_home,
                opposite_home=compatibility.opposite_home,
                diagnostics=(
                    *compatibility.diagnostics,
                    f"target artifact malformed: {candidate.name}",
                ),
            )
        return ResolvedReviewCyclePointer(
            reference=value,
            path=candidate,
            kind="canonical",
            state="canonical",
            canonical_home=compatibility.canonical_home,
            opposite_home=compatibility.opposite_home,
        )

    if value.startswith("feedback://"):
        relative = value[len("feedback://") :]
        raw_parts = relative.split("/")
        if len(raw_parts) != 3:
            return ResolvedReviewCyclePointer(
                reference=value,
                path=None,
                kind="legacy",
                warnings=("Legacy feedback pointer is malformed.",),
            )
        try:
            mission_slug = _validate_segment("mission_slug", raw_parts[0])
            wp_slug = _validate_segment("wp_slug", raw_parts[1])
            filename = _validate_segment("filename", raw_parts[2])
        except ReviewCycleError as exc:
            return ResolvedReviewCyclePointer(
                reference=value,
                path=None,
                kind="legacy",
                warnings=(f"Legacy feedback pointer is invalid: {exc}",),
            )
        common_dir = _resolve_git_common_dir(repo_root)
        warning = "Legacy feedback:// pointer is deprecated; use review-cycle:// artifacts."
        if common_dir is None:
            return ResolvedReviewCyclePointer(reference=value, path=None, kind="legacy", warnings=(warning,))
        candidate = (common_dir / "spec-kitty" / "feedback" / mission_slug / wp_slug / filename).resolve()
        return ResolvedReviewCyclePointer(
            reference=value,
            path=candidate if candidate.exists() and candidate.is_file() else None,
            kind="legacy",
            warnings=(warning,),
        )

    legacy = Path(value).expanduser()
    candidate = legacy if legacy.is_absolute() else repo_root / legacy
    candidate = candidate.resolve()
    return ResolvedReviewCyclePointer(
        reference=value,
        path=candidate if candidate.exists() and candidate.is_file() else None,
        kind="path",
    )


def create_rejected_review_cycle(
    *,
    main_repo_root: Path,
    mission_slug: str,
    wp_id: str,
    wp_slug: str,
    feedback_source: Path,
    reviewer_agent: str = "unknown",
    affected_files: list[dict[str, str]] | None = None,
) -> CreatedRejectedReviewCycle:
    """Create and validate a rejected review-cycle artifact before mutation."""
    if not feedback_source.exists():
        raise ReviewCycleError(f"Review feedback file not found: {feedback_source}")
    if not feedback_source.is_file():
        raise ReviewCycleError(f"Review feedback path is not a file: {feedback_source}")

    body = feedback_source.read_text(encoding="utf-8")
    if not body.strip():
        raise ReviewCycleError(f"Review feedback file is empty: {feedback_source}")

    safe_mission_slug = _validate_segment("mission_slug", mission_slug)
    safe_wp_slug = _validate_segment("wp_slug", wp_slug)
    safe_wp_id = _validate_segment("wp_id", wp_id)

    compatibility = resolve_review_cycle_compatibility(
        main_repo_root,
        mission_slug=safe_mission_slug,
        wp_slug=safe_wp_slug,
        wp_id=safe_wp_id,
    )
    if compatibility.state == "migration_required":
        raise ReviewCycleError(f"{compatibility.reason}: {compatibility.reason_code or 'review-cycle migration required'}")

    sub_artifact_dir = candidate_feature_dir_for_mission(main_repo_root, safe_mission_slug) / "tasks" / safe_wp_slug
    cycle_n = ReviewCycleArtifact.next_cycle_number(sub_artifact_dir)
    filename = _validate_review_cycle_filename(f"review-cycle-{cycle_n}.md")
    pointer = build_review_cycle_pointer(safe_mission_slug, safe_wp_slug, filename)

    parsed_affected: list[AffectedFile] = []
    for affected in affected_files or []:
        parsed_affected.append(
            AffectedFile(
                path=affected["path"],
                line_range=affected.get("line_range"),
            )
        )

    artifact = ReviewCycleArtifact(
        cycle_number=cycle_n,
        wp_id=safe_wp_id,
        mission_slug=safe_mission_slug,
        reviewer_agent=reviewer_agent or "unknown",
        verdict="rejected",
        reviewed_at=datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT),
        affected_files=parsed_affected,
        body=body,
    )
    validate_review_artifact(artifact)

    artifact_path = sub_artifact_dir / filename
    artifact.write(artifact_path)
    validate_review_artifact_file(artifact_path)

    review_result = ReviewResult(
        reviewer=artifact.reviewer_agent,
        verdict="changes_requested",
        reference=pointer,
        feedback_path=str(artifact_path),
    )
    return CreatedRejectedReviewCycle(
        artifact_path=artifact_path,
        pointer=pointer,
        artifact=artifact,
        review_result=review_result,
    )
