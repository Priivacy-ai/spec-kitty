"""Shared review-cycle invariant boundary.

This module owns only rejected review-cycle artifact invariants:
artifact creation, required frontmatter validation, canonical pointer
construction/resolution, legacy feedback pointer normalization, and rejected
ReviewResult derivation.
"""

from __future__ import annotations

from mission_runtime import MissionArtifactKind, placement_seam
from specify_cli.agent_tasks_ports import CoordCommitRouter, MissionHandle
from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.git.protection_policy import ProtectionPolicy
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from specify_cli.review.artifacts import (
    REVIEW_ARTIFACT_VERDICTS,
    AffectedFile,
    ReviewCycleArtifact,
)
from specify_cli.status import ReviewResult

UTC_SECOND_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
REVIEW_FEEDBACK_SENTINELS = frozenset({"force-override", "action-review-claim"})

_REVIEW_CYCLE_FILE_RE = re.compile(r"^review-cycle-(?P<cycle>[1-9][0-9]*)\.md$")


def _review_cycle_wp_dir(repo_root: Path, mission_slug: str, wp_slug: str) -> Path:
    """Return the PRIMARY-home ``tasks/<wp>`` dir for a review-cycle artifact.

    FR-001 (coord-commit-integrity): ``review-cycle-N.md`` is a
    ``WORK_PACKAGE_TASK`` artifact — a PRIMARY-partition kind (data-model.md) — so
    it lives with its WP on the primary ``target_branch`` under ``tasks/<wp>/``,
    NEVER the coordination husk. This is the ONE resolver the READ seam
    (:func:`resolve_review_cycle_pointer`) and the WRITE seam
    (:func:`create_rejected_review_cycle`) share, so both converge on the same
    PRIMARY home. It routes through
    :func:`mission_runtime.placement_seam` ``.read_dir(WORK_PACKAGE_TASK)``,
    retiring the lenient kind-aware ``resolve_planning_read_dir`` fold (and,
    historically, the kind-blind ``candidate_feature_dir_for_mission`` fold that
    resolved the coord worktree for a coord-topology mission — #2646/#2697/#2275).
    ``MissionSelectorAmbiguous`` propagates unchanged (no silent pick — C-009).
    """
    # ``placement_seam(...).read_dir`` is typed ``-> Path`` but mypy widens it to
    # ``Any`` through the ``follow_imports=skip`` boundary on ``specify_cli.*``;
    # bind explicitly so the join's return narrows back to ``Path``.
    mission_dir: Path = placement_seam(repo_root, mission_slug).read_dir(
        MissionArtifactKind.WORK_PACKAGE_TASK
    )
    return mission_dir / "tasks" / wp_slug


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
class ResolvedReviewCyclePointer:
    """Resolution result for review feedback references."""

    reference: str
    path: Path | None
    kind: Literal["canonical", "legacy", "sentinel", "path"]
    warnings: tuple[str, ...] = ()

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
        # ``assert_safe_path_segment`` is typed ``-> str`` but mypy widens it to
        # ``Any`` through the ``follow_imports=skip`` boundary on ``specify_cli.*``;
        # bind explicitly so the declared ``str`` return narrows back.
        safe_segment: str = assert_safe_path_segment(value)
        return safe_segment
    except ValueError as exc:
        raise ReviewCycleError(f"{name} is not a safe path segment: {exc}") from exc


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
    if artifact.verdict not in REVIEW_ARTIFACT_VERDICTS:
        raise ReviewCycleError(
            "review cycle artifact verdict must be one of "
            f"{sorted(REVIEW_ARTIFACT_VERDICTS)}, got {artifact.verdict!r}"
        )
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
        parts = validate_review_cycle_pointer(value)
        # #2136/#2164 + FR-001: resolve the mission dir through the SAME shared
        # resolver the WRITE seam uses (``create_rejected_review_cycle`` →
        # ``_review_cycle_wp_dir``) rather than a raw ``kitty-specs/<mission_slug>``
        # join. ``review-cycle-N.md`` is a WORK_PACKAGE_TASK (PRIMARY) artifact, so
        # the resolver lands on the PRIMARY ``tasks/<wp>/`` home for every handle
        # form (a bare ``mid8`` / human slug names the on-disk ``<slug>-<mid8>`` dir
        # only after canonicalization, so a raw join would compose a DIVERGENT
        # path). Read seam and write seam thus converge on the same PRIMARY home;
        # ``MissionSelectorAmbiguous`` propagates (no silent pick — C-009).
        candidate = (
            _review_cycle_wp_dir(repo_root, parts.mission_slug, parts.wp_slug)
            / parts.filename
        ).resolve()
        if not candidate.exists() or not candidate.is_file():
            return ResolvedReviewCyclePointer(reference=value, path=None, kind="canonical")
        try:
            validate_review_artifact_file(candidate)
        except ValueError:
            return ResolvedReviewCyclePointer(reference=value, path=None, kind="canonical")
        return ResolvedReviewCyclePointer(reference=value, path=candidate, kind="canonical")

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


def _strip_frontmatter(text: str) -> str:
    """Return *text* with any leading YAML frontmatter block removed.

    Tolerant counterpart to :meth:`ReviewCycleArtifact.from_file`'s stricter
    parse (which raises on anything that isn't well-formed frontmatter): when
    *text* does not open with a ``---`` delimited block, it is returned
    unchanged. Used only for the T003 content-identity comparison below, never
    for authoritative artifact parsing — reuses the same delimiter-finding
    algorithm ``ReviewCycleArtifact.from_file`` uses, so both readings of "the
    body" agree.
    """
    if not text.startswith("---"):
        return text
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    closing = rest.find("\n---")
    if closing == -1:
        return text
    body_raw = rest[closing + 4:]
    return body_raw.lstrip("\n")


def _normalize_whitespace(text: str) -> str:
    """Collapse whitespace runs for the T003 content-identity comparison."""
    return re.sub(r"\s+", " ", text).strip()


def _guard_feedback_source_provenance(
    *, feedback_source: Path, body: str, sub_artifact_dir: Path
) -> None:
    """Refuse a *feedback_source* that is itself a prior review-cycle artifact.

    Closes #2996(b) (fabricated duplicate) and #990 (content-wrapping) as the
    identical mechanism: a ``feedback_source`` that resolves — by path OR by
    content — to one of this WP's own ``review-cycle-N.md`` files must never
    be read as "new" reviewer feedback (research.md R2).

    Path-identity and content-identity are checked independently (neither
    short-circuits the other's necessity): a feedback file living at a
    ``review-cycle-N.md``-shaped path inside *sub_artifact_dir* is refused
    even if its content has been hand-edited to no longer match any existing
    cycle's body — only a genuine path check catches that case.
    """
    resolved_feedback = feedback_source.resolve()
    resolved_dir = sub_artifact_dir.resolve()
    if (
        resolved_feedback.parent == resolved_dir
        and _REVIEW_CYCLE_FILE_RE.fullmatch(resolved_feedback.name) is not None
    ):
        raise ReviewCycleError(
            "feedback_source is this WP's own review-cycle artifact "
            f"({resolved_feedback.name}); pass the underlying reviewer "
            "feedback instead of a prior review-cycle artifact."
        )

    if not resolved_dir.exists():
        return
    normalized_feedback_body = _normalize_whitespace(_strip_frontmatter(body))
    for candidate in sorted(resolved_dir.glob("review-cycle-*.md")):
        try:
            candidate_body = ReviewCycleArtifact.from_file(candidate).body
        except ValueError:
            candidate_body = _strip_frontmatter(candidate.read_text(encoding="utf-8"))
        if _normalize_whitespace(candidate_body) == normalized_feedback_body:
            raise ReviewCycleError(
                "feedback_source content duplicates a prior review-cycle "
                f"artifact ({candidate.name}) verbatim; pass distinct "
                "reviewer feedback instead of reusing a previous cycle's "
                "content."
            )


def _commit_review_cycle_artifact(
    commit_router: CoordCommitRouter,
    *,
    main_repo_root: Path,
    mission_slug: str,
    wp_id: str,
    artifact_path: Path,
    cycle_number: int,
    verdict: str,
) -> None:
    """Commit a written review-cycle artifact via the ``commit_artifact`` port.

    T004/#2697: reuses the SAME ``commit_artifact`` port capability
    ``tasks_mark_status.py``/``tasks_map_requirements.py`` already call — no
    new commit/staging mechanism. ``review-cycle-N.md`` is a
    ``WORK_PACKAGE_TASK`` (PRIMARY-partition) artifact, matching
    ``_review_cycle_wp_dir``'s own resolution.

    Cycle 2 fix (#2697 durability): unlike the two existing ``commit_artifact``
    callers (``tasks_mark_status.py``/``tasks_map_requirements.py``), which
    treat a non-``"committed"`` result as a best-effort warning because the
    mutation they are committing (subtask status, WP-requirement mapping)
    already succeeded independently of the commit, this call site has no such
    fallback: an uncommitted ``review-cycle-N.md`` IS the exact defect this
    mission exists to close (#2697 — "the writer's output was never
    git-committed... lands untracked in whatever branch happens to be checked
    out"). A warn-and-continue here would silently reintroduce that bug with
    zero signal to the caller, so any non-``"committed"`` status (including
    ``"unchanged"`` — which should not occur for a freshly written file, but
    is treated as a failure rather than assumed safe) is raised as a hard
    ``ReviewCycleError`` carrying the router's diagnostic.
    """
    result = commit_router.commit_artifact(
        MissionHandle(repo_root=main_repo_root, mission_slug=mission_slug),
        (artifact_path,),
        f"chore: Record review-cycle-{cycle_number} ({verdict}) for {wp_id} on "
        f"{mission_slug}",
        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
        policy=ProtectionPolicy.resolve(main_repo_root),
    )
    if result.status != "committed":
        raise ReviewCycleError(
            f"Failed to commit review-cycle-{cycle_number} artifact for "
            f"{wp_id} on {mission_slug} (status={result.status!r}): "
            f"{result.diagnostic or 'no diagnostic provided'}. The artifact "
            f"was written to {artifact_path} but is NOT committed."
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
    verdict: Literal["approved", "rejected"] = "rejected",
    commit_router: CoordCommitRouter | None = None,
) -> CreatedRejectedReviewCycle:
    """Create, validate, and (optionally) commit a review-cycle artifact.

    ``verdict`` defaults to ``"rejected"`` so every pre-existing caller keeps
    behaving unchanged (C-002 / backward compatibility). ``commit_router`` is
    optional for the same reason: callers that do not thread a commit
    capability keep today's write-only, uncommitted behavior. The production
    ``move-task`` call site MUST supply it — T004/#2697 durability is only
    real when the caller opts in.
    """
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
    # FR-001 write-in-home: land the review-cycle artifact in its PRIMARY
    # ``tasks/<wp>/`` home (WORK_PACKAGE_TASK partition) via the shared resolver —
    # NOT the kind-blind coord husk. This fixes both this direct site AND the
    # move-task ``--review-feedback-file`` caller (which passes no pre-resolved
    # dir), from this one edit.
    sub_artifact_dir = _review_cycle_wp_dir(main_repo_root, safe_mission_slug, safe_wp_slug)

    _guard_feedback_source_provenance(
        feedback_source=feedback_source, body=body, sub_artifact_dir=sub_artifact_dir
    )

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
        verdict=verdict,
        reviewed_at=datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT),
        affected_files=parsed_affected,
        body=body,
    )
    validate_review_artifact(artifact)

    artifact_path = sub_artifact_dir / filename
    artifact.write(artifact_path)
    validate_review_artifact_file(artifact_path)

    if commit_router is not None:
        _commit_review_cycle_artifact(
            commit_router,
            main_repo_root=main_repo_root,
            mission_slug=safe_mission_slug,
            wp_id=safe_wp_id,
            artifact_path=artifact_path,
            cycle_number=cycle_n,
            verdict=verdict,
        )

    review_result = ReviewResult(
        reviewer=artifact.reviewer_agent,
        verdict="approved" if verdict == "approved" else "changes_requested",
        reference=pointer,
        feedback_path=str(artifact_path),
    )
    return CreatedRejectedReviewCycle(
        artifact_path=artifact_path,
        pointer=pointer,
        artifact=artifact,
        review_result=review_result,
    )
