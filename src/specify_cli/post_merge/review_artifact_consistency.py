"""Review artifact consistency gates for release signoff."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from specify_cli.review.artifacts import rejected_review_artifact_for_terminal_lane
from specify_cli.status.reducer import materialize

REJECTED_REVIEW_ARTIFACT_CONFLICT = "REJECTED_REVIEW_ARTIFACT_CONFLICT"
REJECTED_REVIEW_ARTIFACT_INVARIANT = (
    "terminal_wp_latest_review_artifact_must_not_be_rejected"
)
REJECTED_REVIEW_ARTIFACT_REMEDIATION = [
    "Run another review cycle that writes an approved review-cycle artifact.",
    "Or move the WP out of approved/done before merge.",
]


@dataclass(frozen=True)
class RejectedReviewArtifactFinding:
    """A terminal WP whose latest review artifact is still rejected."""

    wp_id: str
    lane: str
    artifact_path: Path
    cycle_number: int
    verdict: str


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


def find_rejected_review_artifact_conflicts(
    feature_dir: Path,
    wp_ids: list[str] | None = None,
) -> list[RejectedReviewArtifactFinding]:
    """Return approved/done WPs whose latest review artifact is rejected."""
    snapshot = materialize(feature_dir)
    selected_wp_ids = wp_ids or sorted(snapshot.work_packages)
    findings: list[RejectedReviewArtifactFinding] = []

    for wp_id in selected_wp_ids:
        state = snapshot.work_packages.get(wp_id)
        if state is None:
            continue
        lane = str(state.get("lane", ""))
        for artifact_dir in _artifact_dirs_for_wp(feature_dir, wp_id):
            rejected = rejected_review_artifact_for_terminal_lane(artifact_dir, lane)
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
