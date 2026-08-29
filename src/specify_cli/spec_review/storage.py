"""Canonical, non-overwriting persistence for host-built spec-review runs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import os
from pathlib import Path
import secrets

import yaml

from kernel.clock import UTC, datetime, now_utc
from mission_runtime import CommitTarget, MissionArtifactKind, placement_seam, resolve_artifact_surface

from specify_cli.spec_review.models import SpecReviewRun


_MAX_COLLISION_RETRIES = 8


class SpecReviewWriteError(RuntimeError):
    """A local failure that deliberately excludes review content."""

    def __init__(self, code: str, target: Path) -> None:
        super().__init__(f"{code}: {target}")
        self.code = code
        self.target = target


@dataclass(frozen=True)
class StoredSpecReview:
    """Metadata returned after a review run is durably published."""

    path: Path
    run_id: str
    commit_target: CommitTarget


def new_spec_review_run_id(now: datetime | None = None) -> str:
    """Create an ASCII ID with a sortable UTC timestamp and nonce."""
    timestamp = (now or now_utc()).astimezone(UTC)
    return f"run-{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{secrets.token_hex(6)}"


def store_spec_review(
    *,
    repo_root: Path,
    mission_slug: str,
    run: SpecReviewRun,
    next_run_id: Callable[[], str] = new_spec_review_run_id,
) -> StoredSpecReview:
    """Persist *run* under its canonical PRIMARY mission surface.

    Directory and commit target come exclusively from runtime seams. A collision
    retries only local file naming; this function never repeats a model call.
    """
    if run.mission != mission_slug:
        raise ValueError("run mission does not match persistence mission")

    resolved = resolve_artifact_surface(repo_root, mission_slug, MissionArtifactKind.SPEC_REVIEW)
    target = placement_seam(repo_root, mission_slug).write_target(MissionArtifactKind.SPEC_REVIEW)
    try:
        reviews_dir = _validated_reviews_dir(resolved.path)
    except SpecReviewWriteError:
        raise
    except OSError as exc:
        raise SpecReviewWriteError(
            "SPEC_REVIEW_WRITE_INVALID_SURFACE", resolved.path / "reviews"
        ) from exc
    current_run = run
    for attempt in range(_MAX_COLLISION_RETRIES):
        final_path = reviews_dir / f"spec-review-{current_run.run_id}.yaml"
        try:
            _publish_exclusive(final_path, _serialize_run(current_run))
        except FileExistsError:
            if attempt == _MAX_COLLISION_RETRIES - 1:
                raise SpecReviewWriteError("SPEC_REVIEW_WRITE_COLLISION", final_path) from None
            current_run = replace(current_run, run_id=next_run_id())
            continue
        except OSError as exc:
            raise SpecReviewWriteError("SPEC_REVIEW_WRITE_FAILED", final_path) from exc
        return StoredSpecReview(path=final_path, run_id=current_run.run_id, commit_target=target)
    raise AssertionError("bounded collision loop must return or raise")


def _validated_reviews_dir(mission_root: Path) -> Path:
    """Create/verify the one permitted child immediately before opening a file."""
    root = mission_root.resolve(strict=True)
    if not root.is_dir():
        raise SpecReviewWriteError("SPEC_REVIEW_WRITE_INVALID_SURFACE", mission_root)
    reviews = root / "reviews"
    if reviews.exists() and reviews.is_symlink():
        raise SpecReviewWriteError("SPEC_REVIEW_WRITE_SYMLINK", reviews)
    reviews.mkdir(exist_ok=True)
    resolved_reviews = reviews.resolve(strict=True)
    try:
        resolved_reviews.relative_to(root)
    except ValueError as exc:
        raise SpecReviewWriteError("SPEC_REVIEW_WRITE_ESCAPE", reviews) from exc
    if not resolved_reviews.is_dir() or resolved_reviews.name != "reviews":
        raise SpecReviewWriteError("SPEC_REVIEW_WRITE_INVALID_SURFACE", reviews)
    return resolved_reviews


def _publish_exclusive(final_path: Path, content: str) -> None:
    """Publish complete content without ever replacing an existing result."""
    temp_path = final_path.parent / f".{final_path.name}.{secrets.token_hex(8)}.tmp"
    try:
        with temp_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        # Same-filesystem link is exclusive (EEXIST on collision) and never
        # overwrites a final name. It is supported on project Windows/Unix FSes.
        os.link(temp_path, final_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _serialize_run(run: SpecReviewRun) -> str:
    """Emit plain YAML scalars/maps, never Python datetime or enum tags."""
    assert run.summary is not None  # guaranteed by SpecReviewRun.__post_init__
    document: dict[str, object] = {
        "schema": run.schema,
        "run_id": run.run_id,
        "mission": run.mission,
        "spec_sha256": run.spec_sha256,
        "transport": run.transport,
        "requested_model_route": run.requested_model_route,
        "actual_model": run.actual_model,
        "rubric_version": run.rubric_version,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat(),
        "status": run.status.value,
        "diagnostic_code": run.diagnostic_code.value if run.diagnostic_code else None,
        "findings": [
            {
                "identifier": finding.identifier,
                "lens": finding.lens,
                "severity": finding.severity,
                "title": finding.title,
                "evidence": {"line_start": finding.evidence.line_start, "line_end": finding.evidence.line_end},
                "claim": finding.claim,
                "remediation": finding.remediation,
            }
            for finding in run.findings
        ],
        "summary": {
            "total": run.summary.total,
            "severity_1": run.summary.severity_1,
            "severity_2": run.summary.severity_2,
            "severity_3": run.summary.severity_3,
            "severity_4": run.summary.severity_4,
            "severity_5": run.summary.severity_5,
        },
    }
    if run.paid_pricing is not None:
        document["paid_pricing"] = run.paid_pricing.consent_document()
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
