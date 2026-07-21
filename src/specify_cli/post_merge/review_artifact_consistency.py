"""Review artifact consistency gates for release signoff."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

from specify_cli.missions._read_path_resolver import resolve_planning_read_dir
from specify_cli.review.artifacts import rejected_review_artifact_for_terminal_lane
from specify_cli.status import materialize
from specify_cli.status import ReviewOverride
from mission_runtime import MissionArtifactKind

REJECTED_REVIEW_ARTIFACT_CONFLICT = "REJECTED_REVIEW_ARTIFACT_CONFLICT"
REJECTED_REVIEW_ARTIFACT_INVARIANT = (
    "terminal_wp_latest_review_artifact_must_not_be_rejected"
)
REJECTED_REVIEW_ARTIFACT_REMEDIATION = [
    "Run another review cycle that writes an approved review-cycle artifact.",
    "Or move the WP out of approved/done before merge.",
]
REVIEW_ARTIFACT_SCHEMA_INVALID = "REVIEW_ARTIFACT_SCHEMA_INVALID"
REVIEW_ARTIFACT_SCHEMA_INVARIANT = "review_cycle_frontmatter_must_match_schema"
REVIEW_ARTIFACT_SCHEMA_REMEDIATION = [
    "Repair or regenerate the review-cycle artifact frontmatter.",
    "Ensure affected_files is a list of mappings with path keys.",
    "Retry merge after the artifact parses cleanly.",
]


@dataclass(frozen=True)
class RejectedReviewArtifactFinding:
    """A terminal WP whose latest review artifact is still rejected."""

    wp_id: str
    lane: str
    artifact_path: Path
    cycle_number: int
    verdict: str


@dataclass(frozen=True)
class ReviewArtifactSchemaFinding:
    """A WP whose latest review artifact cannot be parsed as schema-valid frontmatter."""

    wp_id: str
    lane: str
    artifact_path: Path
    schema_error: str


ReviewArtifactFinding = RejectedReviewArtifactFinding | ReviewArtifactSchemaFinding


def _artifact_dirs_for_wp(feature_dir: Path, wp_id: str) -> list[Path]:
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return []

    exact = tasks_dir / wp_id
    candidates: list[Path] = []
    if exact.is_dir():
        candidates.append(exact)

    candidates.extend(
        sorted(
            path
            for path in tasks_dir.iterdir()
            if path.is_dir() and path.name.startswith(f"{wp_id}-") and path not in candidates
        )
    )
    return candidates


def _snapshot_review_override(state: Mapping[str, Any]) -> ReviewOverride | None:
    """Resolve the event-sourced ``review`` override from a reduced WP snapshot.

    FR-009 (WP09): the reduced ``review`` snapshot slot is the single authority
    for override recognition — this post-merge consistency check is the third leg
    of the both-halves pair (alongside the write emit and the merge-gate read), so
    it must resolve the override from the same slot rather than re-parsing artifact
    frontmatter. Returns ``None`` when the slot is absent or malformed; an
    incomplete override is carried through and rejected by ``ReviewOverride``'s
    ``complete`` predicate downstream.
    """
    review_raw = state.get("review")
    if not isinstance(review_raw, Mapping):
        return None
    try:
        return ReviewOverride.from_dict(review_raw)
    except (KeyError, TypeError, ValueError):
        return None


def _review_cycle_number(path: Path) -> int:
    match = re.search(r"review-cycle-(\d+)\.md$", path.name)
    return int(match.group(1)) if match else 0


def _latest_review_artifact_path(artifact_dir: Path) -> Path | None:
    candidates = list(artifact_dir.glob("review-cycle-*.md"))
    if not candidates:
        return None
    candidates.sort(key=_review_cycle_number)
    return candidates[-1]


def _schema_error_message(exc: ValueError, artifact_path: Path) -> str:
    """Strip machine-local paths from parser errors; path is reported separately."""
    message = str(exc)
    prefixes = (
        f"Missing or invalid field in review artifact {artifact_path}: ",
        f"Failed to parse YAML frontmatter in {artifact_path}: ",
        f"Cannot read review artifact file {artifact_path}: ",
        f"Review artifact file has no YAML frontmatter: {artifact_path}",
        f"Review artifact file has no closing '---' delimiter: {artifact_path}",
        f"YAML frontmatter in {artifact_path} is not a mapping",
    )
    for prefix in prefixes:
        if message.startswith(prefix):
            stripped = message[len(prefix) :].strip()
            return stripped or message.replace(str(artifact_path), "").strip(": ")
    return message.replace(str(artifact_path), "<review artifact>")


def find_rejected_review_artifact_conflicts(
    repo_root: Path,
    mission_slug: str,
    wp_ids: list[str] | None = None,
) -> list[ReviewArtifactFinding]:
    """Return review artifact findings that block merge readiness.

    Resolves two independent partitions rather than reading both off one
    caller-supplied ``feature_dir`` (#2412-adjacent field report): review-cycle
    artifacts under ``tasks/`` are ``WORK_PACKAGE_TASK``, PRIMARY-partition for
    every topology; WP lane state comes from ``STATUS_STATE``, which stays on
    the coordination branch for a coord-topology mission. A single shared
    directory can only ever be correct for one of the two -- for a
    coord-topology mission the PRIMARY checkout carries no authoritative
    status log, and the coordination worktree's on-disk copy of a WP's review
    artifacts can be stale or an untracked stray file. Resolving each by its
    own kind is what keeps a stale/wrong copy on either side from silently
    shadowing the truth on the other.
    """
    task_dir = resolve_planning_read_dir(
        repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    status_dir = resolve_planning_read_dir(
        repo_root, mission_slug, kind=MissionArtifactKind.STATUS_STATE
    )
    snapshot = materialize(status_dir)
    selected_wp_ids = wp_ids or sorted(snapshot.work_packages)
    findings: list[ReviewArtifactFinding] = []

    for wp_id in selected_wp_ids:
        state = snapshot.work_packages.get(wp_id)
        if state is None:
            continue
        lane = str(state.get("lane", ""))
        snapshot_override = _snapshot_review_override(state)
        for artifact_dir in _artifact_dirs_for_wp(task_dir, wp_id):
            latest_path = _latest_review_artifact_path(artifact_dir)
            if latest_path is None:
                continue
            try:
                rejected = rejected_review_artifact_for_terminal_lane(
                    artifact_dir, lane, snapshot_override=snapshot_override
                )
            except ValueError as exc:
                findings.append(
                    ReviewArtifactSchemaFinding(
                        wp_id=wp_id,
                        lane=lane,
                        artifact_path=latest_path,
                        schema_error=_schema_error_message(exc, latest_path),
                    )
                )
                break
            if rejected is None:
                continue
            findings.append(
                RejectedReviewArtifactFinding(
                    wp_id=wp_id,
                    lane=lane,
                    artifact_path=rejected.path,
                    cycle_number=rejected.cycle_number,
                    verdict=rejected.verdict,
                )
            )
            break

    return findings


def format_review_artifact_conflict(
    finding: RejectedReviewArtifactFinding,
    *,
    repo_root: Path | None = None,
) -> str:
    """Render one finding with a stable path for operator diagnostics."""
    path = finding.artifact_path
    if repo_root is not None:
        with suppress(ValueError):
            path = path.relative_to(repo_root)
    return (
        f"{finding.wp_id} is lane '{finding.lane}', but latest review artifact "
        f"{path} has verdict '{finding.verdict}' (cycle {finding.cycle_number})."
    )


def format_review_artifact_finding(
    finding: ReviewArtifactFinding,
    *,
    repo_root: Path | None = None,
) -> str:
    """Render one review artifact finding with stable path context."""
    if isinstance(finding, RejectedReviewArtifactFinding):
        return format_review_artifact_conflict(finding, repo_root=repo_root)

    path = finding.artifact_path
    if repo_root is not None:
        with suppress(ValueError):
            path = path.relative_to(repo_root)
    return (
        f"{finding.wp_id} has malformed latest review artifact {path}: "
        f"{finding.schema_error}"
    )


def review_artifact_conflict_diagnostic(
    finding: RejectedReviewArtifactFinding,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Return the stable diagnostic contract payload for one conflict."""
    path = finding.artifact_path
    if repo_root is not None:
        with suppress(ValueError):
            path = path.relative_to(repo_root)
    return {
        "diagnostic_code": REJECTED_REVIEW_ARTIFACT_CONFLICT,
        "branch_or_work_package": finding.wp_id,
        "violated_invariant": REJECTED_REVIEW_ARTIFACT_INVARIANT,
        "remediation": REJECTED_REVIEW_ARTIFACT_REMEDIATION,
        "lane": finding.lane,
        "latest_review_cycle_path": str(path),
        "latest_review_cycle_verdict": finding.verdict,
        "review_cycle_number": finding.cycle_number,
    }


def review_artifact_schema_diagnostic(
    finding: ReviewArtifactSchemaFinding,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Return the stable diagnostic payload for a malformed review artifact."""
    path = finding.artifact_path
    if repo_root is not None:
        with suppress(ValueError):
            path = path.relative_to(repo_root)
    return {
        "diagnostic_code": REVIEW_ARTIFACT_SCHEMA_INVALID,
        "branch_or_work_package": finding.wp_id,
        "violated_invariant": REVIEW_ARTIFACT_SCHEMA_INVARIANT,
        "remediation": REVIEW_ARTIFACT_SCHEMA_REMEDIATION,
        "lane": finding.lane,
        "latest_review_cycle_path": str(path),
        "schema_error": finding.schema_error,
    }


def review_artifact_finding_diagnostic(
    finding: ReviewArtifactFinding,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Return the stable diagnostic payload for any review artifact finding."""
    if isinstance(finding, RejectedReviewArtifactFinding):
        return review_artifact_conflict_diagnostic(finding, repo_root=repo_root)
    return review_artifact_schema_diagnostic(finding, repo_root=repo_root)


@dataclass(frozen=True)
class ReviewArtifactPreflightResult:
    """Structured result of the review-artifact consistency preflight.

    Shared by both the real-merge gate (raises on failure) and the
    ``merge --dry-run`` preview surface (renders diagnostics and exits non-zero).
    """

    findings: tuple[ReviewArtifactFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings

    def diagnostics(
        self,
        *,
        repo_root: Path | None = None,
    ) -> list[dict[str, object]]:
        """Return the stable diagnostic payloads, one per finding."""
        return [
            review_artifact_finding_diagnostic(finding, repo_root=repo_root)
            for finding in self.findings
        ]


def run_review_artifact_consistency_preflight(
    repo_root: Path,
    mission_slug: str,
    *,
    wp_ids: list[str] | None = None,
) -> ReviewArtifactPreflightResult:
    """Run the review-artifact consistency gate and wrap the result.

    This is the single implementation path shared by ``merge`` and
    ``merge --dry-run`` so the two surfaces cannot drift. Callers that need
    rendering can call ``ReviewArtifactPreflightResult.diagnostics()``.
    """
    findings = find_rejected_review_artifact_conflicts(repo_root, mission_slug, wp_ids)
    return ReviewArtifactPreflightResult(findings=tuple(findings))
