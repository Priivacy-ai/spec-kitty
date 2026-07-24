"""Review artifact consistency gates for release signoff."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

from mission_runtime import MissionArtifactKind
from specify_cli.review.artifacts import rejected_review_artifact_for_terminal_lane
from specify_cli.status import materialize
from specify_cli.status import ReviewOverride

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


def _resolve_partition_read_dir(feature_dir: Path, kind: MissionArtifactKind) -> Path:
    """Resolve the mission dir that OWNS ``kind`` for ``feature_dir``'s mission.

    FR-006 / gate-execution-context C1 (#2885): the review-artifact gate needs two
    facts that live in two different partitions — a WP's **lane state**
    (``STATUS_STATE``, coordination-branch-owned for a coord-topology mission) and
    its **review-cycle artifacts** (``WORK_PACKAGE_TASK``, PRIMARY-partition for
    every topology). Each MUST resolve from its own declared home; a single
    caller-supplied directory is correct for at most one of the two. Routed through
    the ONE affirmative surface→filesystem seam (lifecycle-gate-execution-context
    WP02): a PRIMARY-partition kind resolves the primary mission dir for every
    topology, a COORD-partition kind resolves the coordination husk when its
    worktree is materialised.

    ``feature_dir.name`` is the mission slug for every caller — the primary
    ``kitty-specs/<slug>`` and the coord husk ``…-coord/kitty-specs/<slug>`` both
    end in ``<slug>`` — so the resolved partition is IDENTICAL no matter which
    surface the caller passed. That is precisely why the dry-run preview (handed a
    primary dir) and the real consolidation (handed the coord husk) now AGREE
    (SC-002): each re-resolves both partitions from the mission identity rather than
    trusting the dir it was handed.

    When no workspace root can be derived (a bare non-git test fixture with no
    coordination worktree), the mission directory IS its own sole partition and is
    returned unchanged. This is the flat self-home answer, NOT the coord degradation
    that produced #2885 — that defect was reading LANE STATE off a caller dir that
    pointed at the PRIMARY partition (empty status log → every WP stateless → gate
    passed a rejected review by default); resolving lane state from its own
    ``STATUS_STATE`` home is what removes it. ``resolve_artifact_surface`` is typed
    but widened to ``Any`` across the ``follow_imports=skip`` boundary on
    ``specify_cli.*``; bind the ``.path`` result explicitly so the declared ``Path``
    narrows back.
    """
    from mission_runtime import resolve_artifact_surface
    from specify_cli.core.paths import WorkspaceRootNotFound, resolve_canonical_root

    try:
        repo_root = resolve_canonical_root(feature_dir)
    except WorkspaceRootNotFound:
        return feature_dir
    resolved: Path = resolve_artifact_surface(repo_root, feature_dir.name, kind).path
    return resolved


def _resolve_lane_state_read_dir(feature_dir: Path) -> Path:
    """Resolve the ``STATUS_STATE`` home (coord husk for a materialised coord mission)."""
    return _resolve_partition_read_dir(feature_dir, MissionArtifactKind.STATUS_STATE)


def _resolve_review_cycle_read_dir(feature_dir: Path) -> Path:
    """Resolve the ``WORK_PACKAGE_TASK`` home (PRIMARY mission dir for every topology)."""
    return _resolve_partition_read_dir(feature_dir, MissionArtifactKind.WORK_PACKAGE_TASK)


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
    feature_dir: Path,
    wp_ids: list[str] | None = None,
) -> list[ReviewArtifactFinding]:
    """Return review artifact findings that block merge readiness.

    Two facts, two partitions (FR-006 / #2885). Neither is trusted from the single
    ``feature_dir`` the caller happened to pass — that trust WAS #2885: the dry-run
    preview handed a PRIMARY dir, so ``materialize`` read an empty status log (a
    coord mission keeps its authoritative log on the coordination husk), every WP
    looked stateless, and the gate passed a rejected review by default while the
    real consolidation — handed the coord husk — refused. The **lane snapshot** now
    resolves from its ``STATUS_STATE`` home and the **review-cycle artifacts** from
    their ``WORK_PACKAGE_TASK`` home, so both callers resolve the same two surfaces
    and AGREE (SC-002).
    """
    lane_state_dir = _resolve_lane_state_read_dir(feature_dir)
    review_cycle_dir = _resolve_review_cycle_read_dir(feature_dir)
    snapshot = materialize(lane_state_dir)
    selected_wp_ids = wp_ids or sorted(snapshot.work_packages)
    findings: list[ReviewArtifactFinding] = []

    for wp_id in selected_wp_ids:
        state = snapshot.work_packages.get(wp_id)
        if state is None:
            continue
        lane = str(state.get("lane", ""))
        snapshot_override = _snapshot_review_override(state)
        for artifact_dir in _artifact_dirs_for_wp(review_cycle_dir, wp_id):
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
    feature_dir: Path,
    *,
    wp_ids: list[str] | None = None,
) -> ReviewArtifactPreflightResult:
    """Run the review-artifact consistency gate and wrap the result.

    This is the single implementation path shared by ``merge`` and
    ``merge --dry-run`` so the two surfaces cannot drift. Callers that need
    rendering can call ``ReviewArtifactPreflightResult.diagnostics()``.
    """
    findings = find_rejected_review_artifact_conflicts(feature_dir, wp_ids)
    return ReviewArtifactPreflightResult(findings=tuple(findings))
