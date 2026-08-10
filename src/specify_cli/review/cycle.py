"""Shared review-cycle invariant boundary.

This module owns only rejected review-cycle artifact invariants:
artifact creation, required frontmatter validation, canonical pointer
construction/resolution, legacy feedback pointer normalization, and rejected
ReviewResult derivation.
"""

from __future__ import annotations

from kernel.clock import UTC_SECOND_TIMESTAMP_FORMAT, now_utc
from mission_runtime import MissionArtifactKind, placement_seam
from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    CoordCommitRouter,
    MissionHandle,
)
from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.git.protection_policy import ProtectionPolicy
import logging
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from specify_cli.review.artifacts import (
    AffectedFile,
    ReviewCycleArtifact,
)
from specify_cli.status import (
    ReviewResult,
    emission_event_verdict,
    feature_status_lock,
    git_operation_in_progress,
)

logger = logging.getLogger(__name__)

# FR-004 (kernel-clock-single-door WP03): defined once on the door
# (kernel.clock.UTC_SECOND_TIMESTAMP_FORMAT), imported above; call sites here
# are untouched (package remediation is WP13c's job).
REVIEW_FEEDBACK_SENTINELS = frozenset({"force-override", "action-review-claim"})

#: T042 (FR-002/mechanism shared with WP11): the commit call's own retry-on-
#: contention bound. Small and fixed -- a lock-contention window measured in
#: milliseconds, not a long-running outage -- per plan.md's Risks section
#: ("do not attempt exponential backoff at a multi-second scale here").
_COMMIT_CONTENTION_MAX_ATTEMPTS = 3
_COMMIT_CONTENTION_RETRY_SLEEP_SECONDS = 0.15

_REVIEW_CYCLE_FILE_RE = re.compile(r"^review-cycle-(?P<cycle>[1-9][0-9]*)\.md$")


def _review_cycle_wp_dir(
    repo_root: Path,
    mission_slug: str,
    wp_slug: str,
    *,
    kind: MissionArtifactKind = MissionArtifactKind.WORK_PACKAGE_TASK,
) -> Path:
    """Return the ``tasks/<wp>`` dir a review-cycle artifact reads/writes,
    on disk.

    **ADR 2026-08-03-1 designates ``review-cycle-N.md`` as
    ``MissionArtifactKind.REVIEW_CYCLE`` — COORD-partition per-work-package
    bookkeeping under a coordination topology, PRIMARY otherwise.** This is
    the ONE owner function every consumer in this mission's scope routes
    through — the READ seam (:func:`resolve_review_cycle_pointer`), the WRITE
    seam (:func:`create_rejected_review_cycle`), and the arbiter
    (:func:`specify_cli.review.arbiter.persist_arbiter_decision`) all resolve
    through this single call (FR-007), parametrized by ``kind`` so each
    consumer states which partition rule it wants rather than re-deriving the
    directory independently.

    **FR-011 correction (WP06): the merge-time gate does NOT opt into
    ``REVIEW_CYCLE`` here.** An earlier revision of this docstring claimed
    the merge-time gate (:mod:`specify_cli.post_merge.review_artifact_consistency`)
    was this function's one ``kind=REVIEW_CYCLE`` caller; verified against the
    live tree, that module never calls ``_review_cycle_wp_dir`` at all -- it
    resolves its own read directory through a separate helper
    (``_resolve_partition_read_dir``). No caller in this mission's scope
    currently passes ``kind=MissionArtifactKind.REVIEW_CYCLE`` to this
    function; every real call site (the READ seam, the WRITE seam, the
    arbiter, ``tasks_materialization.py::_persist_review_feedback``,
    ``workflow_executor.py``, ``workflow_cores.py``,
    ``tasks_verdict_persistence.py``) relies on the ``WORK_PACKAGE_TASK``
    default below and passes no ``kind`` argument.

    ``kind`` defaults to ``MissionArtifactKind.WORK_PACKAGE_TASK`` (PRIMARY,
    for every topology) — every real caller relies on this default and passes
    no ``kind`` argument. A caller MAY instead pass
    ``kind=MissionArtifactKind.REVIEW_CYCLE`` to resolve the ADR-designated
    COORD-under-coord-topology home (absorbing
    ``CoordinationBranchDeleted``/``StatusReadPathNotFound`` to the PRIMARY
    home for pre-ADR missions, per the ADR's "exception absorption" migration
    rule) — no production caller opts into this branch today (verified above);
    it remains a designed, reachable code path for a future consumer, not
    dead code (see ``kind is MissionArtifactKind.REVIEW_CYCLE`` below).

    **WP13 finding (disclosed, not silently worked around): the WRITE-side
    default cannot yet change to ``REVIEW_CYCLE``.** Trying
    ``kind=REVIEW_CYCLE`` as the DEFAULT (so a coord-topology mission's
    review-cycle WRITE physically lands in the already-materialised
    coordination worktree, not the primary checkout) reproducibly broke a
    currently-green, un-owned regression test:
    ``tests/coordination/test_analysis_report_rehome.py::
    test_review_cycle_authored_lands_on_coord_ref_and_is_absent_on_primary``
    (WP04's own re-pin for this ADR) asserts the artifact's REPO-ROOT-RELATIVE
    path is ``kitty-specs/<slug>/tasks/<wp>/review-cycle-1.md`` — i.e. the
    PHYSICAL write lands in the PRIMARY working tree even though
    ``commit_router.commit_artifact``'s path-based classification (WP04, T015)
    already stages that SAME content onto the COORD branch via git plumbing,
    independent of the physical write location. Defaulting to
    ``REVIEW_CYCLE`` would move the physical write into the separate
    coordination worktree directory instead, breaking that assertion.

    **Historical second hazard — CLOSED in this mission (WP05).** An earlier
    draft of this disclosure named a second, reader-side hazard:
    ``tasks_verdict_persistence.py::resolve_review_verdict_facts`` deriving the
    verdict-read directory via a bare PRIMARY-anchored ``wp_path`` join that
    ignored any kind-aware resolver, so flipping the WRITE default to COORD
    would have left that reader blind to a real, current rejection (a fail-open
    regression on a safety-critical guard). WP05 (FR-002) migrated that reader
    onto the coord-aware ``_resolve_verdict_read_feature_dir`` (STATUS_STATE
    placement), so it now co-resolves with every other verdict consumer and the
    hazard no longer exists — see
    ``tests/coordination/test_verdict_dir_co_resolution.py``.

    That leaves the ``test_analysis_report_rehome`` PHYSICAL-write assertion as
    the sole remaining reason this WP does not ship a WRITE-side default flip.
    Opting a single consumer such as the merge-time gate into
    ``kind=REVIEW_CYCLE`` would be independently safe (it never touches
    ``_review_cycle_wp_dir``'s write-side default) — but per FR-011's
    correction above, no consumer has actually done so yet. A follow-up WP that
    flips the write-side default must re-verify ``test_analysis_report_rehome.py``
    (plus recheck the three already-flagged unrouted sites WP04's own
    ``verdict_seam_IC04.yaml`` fragment names: ``workflow.py::review``,
    ``workflow_cores.py::has_prior_rejection``,
    ``workflow_executor.py::implement_try_render_fix_mode_prompt``) in the SAME
    change before the WRITE-side default can safely flip. See this WP's final
    report for the full citations.

    **FR-007 wording reconciliation (WP06).** This mission's census
    (``tests/architectural/verdict_seam_census.yaml``) marks THIS function
    ``status: retire`` (source WP08/IC08) — a future WP is expected to retire
    ``_review_cycle_wp_dir`` itself once the write-side default safely flips
    (the hazards above are resolved) and every consumer routes through the
    canonical placement resolver directly. Until then, the COORD→PRIMARY
    exception-absorption fallback implemented in the ``kind is
    MissionArtifactKind.REVIEW_CYCLE`` branch below is **relocated** into
    that eventual canonical placement resolver, not "preserved verbatim" (an
    earlier spec revision's phrasing, corrected by research.md) — its
    rationale re-scopes to the surviving write/prose-locate seam once the
    retired verdict read-path (WP05's collapse) no longer exercises it.

    Historically retires the lenient kind-aware ``resolve_planning_read_dir``
    fold (and the kind-blind ``candidate_feature_dir_for_mission`` fold that
    resolved the coord worktree for a coord-topology mission —
    #2646/#2697/#2275). ``MissionSelectorAmbiguous`` propagates unchanged (no
    silent pick — C-009).
    """
    seam = placement_seam(repo_root, mission_slug)
    if kind is MissionArtifactKind.REVIEW_CYCLE:
        # Function-local import: avoids a module-load cycle between
        # review/cycle.py and the coordination/missions modules (the same
        # H2/I-6 precedent ``_review_cycle_reconcile_doctor.py`` documents for
        # its own identical absorption pattern).
        from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

        try:
            # ``placement_seam(...).read_dir`` is typed ``-> Path`` but mypy
            # widens it to ``Any`` through the ``follow_imports=skip``
            # boundary on ``specify_cli.*``; bind explicitly so the join's
            # return narrows back to ``Path``.
            mission_dir: Path = seam.read_dir(MissionArtifactKind.REVIEW_CYCLE)
        except StatusReadPathNotFound:
            # ``CoordinationBranchDeleted`` is a ``StatusReadPathNotFound``
            # subclass, so this single except also covers that specific case
            # (the ADR's "exception absorption" migration rule).
            mission_dir = seam.read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)
        return mission_dir / "tasks" / wp_slug

    resolved_dir: Path = seam.read_dir(kind)
    return resolved_dir / "tasks" / wp_slug


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
    """Validate required review artifact fields.

    FR-003/SC-007 (WP06): this no longer validates a ``verdict`` field --
    ``ReviewCycleArtifact`` carries no such field (WP05 retired every reader
    that treated the artifact's frontmatter as verdict authority; the event
    log, via ``status.event_sourced_review_result``, is now the sole
    authority). Validating a field the schema no longer has would be dead
    code, not a defensive check.
    """
    if artifact.cycle_number < 1:
        raise ReviewCycleError("review artifact cycle_number must be positive")
    _validate_segment("wp_id", artifact.wp_id)
    _validate_segment("mission_slug", artifact.mission_slug)
    if not str(artifact.reviewer_agent).strip():
        raise ReviewCycleError("review artifact reviewer_agent is required")
    if not str(artifact.reviewed_at).strip():
        raise ReviewCycleError("review artifact reviewed_at is required")
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
        # #2136/#2164 + FR-001/FR-007 (WP13): resolve the mission dir through the
        # SAME shared owner function the WRITE seam uses (``create_rejected_
        # review_cycle`` -> ``_review_cycle_wp_dir``) rather than a raw
        # ``kitty-specs/<mission_slug>`` join. ADR 2026-08-03-1 designates
        # ``review-cycle-N.md`` as a REVIEW_CYCLE artifact (COORD-partition
        # under a coordination topology, PRIMARY otherwise); ``_review_cycle_
        # wp_dir`` deliberately still resolves the PRIMARY WORK_PACKAGE_TASK
        # home only (see that function's own docstring for the disclosed
        # safety finding blocking the full flip), so for every handle form
        # this and the write seam converge on the SAME home (a bare ``mid8``
        # / human slug names the on-disk ``<slug>-<mid8>`` dir only after
        # canonicalization, so a raw join would compose a DIVERGENT path).
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


def _guard_feedback_source_provenance(
    *, feedback_source: Path, sub_artifact_dir: Path
) -> None:
    """Refuse a *feedback_source* that IS a prior review-cycle artifact.

    Closes #2996(b) (fabricated duplicate) and #990 (content-wrapping) as the
    identical mechanism: a ``feedback_source`` that resolves — by path OR by
    content — to one of this WP's own ``review-cycle-N.md`` files must never
    be read as "new" reviewer feedback (research.md R2).

    Path-identity and content-identity are checked independently (neither
    short-circuits the other's necessity): a feedback file living at a
    ``review-cycle-N.md``-shaped path inside *sub_artifact_dir* is refused
    even if its content has been hand-edited to no longer match any existing
    cycle's body — only a genuine path check catches that case.

    T045 (FR-004/SC-001 narrowing, operator-sanctioned): the content leg used
    to be a body-EQUALITY comparison against every prior cycle's stored body
    (both sides run through frontmatter-stripping + whitespace normalization —
    fold ``ca53e0bbd``, M4 of the adversarial squad on PR #3156). That
    mechanism refused ANY exact-content match, including a genuinely DISTINCT
    reviewer's honest re-report of the same defect in the same words — which
    FR-004/SC-001 require to be admissible ("a reviewer can re-report a
    recurring defect using byte-identical feedback"). The content leg is
    narrowed to a SELF-CONTAINED question that does not need the old
    equality comparison at all: does *feedback_source* itself PARSE as a
    ``ReviewCycleArtifact`` (valid frontmatter + required fields)? A byte-copy
    of a stored verdict record parses successfully (it IS a verdict record,
    regardless of which prior cycle it copies or whether that cycle is even
    readable) and stays refused — preserving C-002's guarantee that a verdict
    record re-submitted as feedback is refused, by path AND content. Plain
    reviewer prose — even prose that is byte-identical to a prior cycle's
    stored body — does not parse (no YAML frontmatter mapping) and is now
    admitted, closing FR-004's gap. This mechanism change retires
    ``_content_identity``/``_strip_frontmatter``/``_normalize_whitespace``
    (no longer called): the GUARANTEE those helpers protected (#990/#2996(b))
    is preserved by the parse-check below, per C-002's "mechanism may change,
    guarantee may not weaken."

    Residual, consciously accepted (do not treat as a gap to close later): a
    byte-copy of an artifact whose frontmatter has been manually stripped
    parses AS PROSE, not as an artifact, so it is now admitted too — at that
    point the input is textually indistinguishable from a reviewer re-typing
    the same prose verbatim, which FR-004 explicitly licenses. No rule can
    separate "a human re-typed this" from "a machine stripped the
    frontmatter off a copy" once the frontmatter is gone; this is the
    necessary, honest cost of closing FR-004's gap, not an oversight.
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

    try:
        ReviewCycleArtifact.from_file(feedback_source)
    except (ValueError, OSError):
        return
    raise ReviewCycleError(
        "feedback_source content parses as a review-cycle artifact "
        f"({feedback_source.name}); pass distinct reviewer feedback instead "
        "of a prior review-cycle artifact's content."
    )


def _commit_failure_message(
    *,
    wp_id: str,
    mission_slug: str,
    cycle_number: int,
    artifact_path: Path,
    result: CommitArtifactResult,
    exhausted_contention_retries: bool,
) -> str:
    """Build the hard-failure message for a non-``"committed"`` commit result.

    T042: distinguishes "exhausted contention retries" (the probe kept firing
    across every retry) from a plain, non-transient commit failure, so an
    operator/log-reader can tell the two apart rather than seeing an
    identical message for both.
    """
    prefix = (
        f"Exhausted contention retries committing review-cycle-{cycle_number} "
        "artifact"
        if exhausted_contention_retries
        else f"Failed to commit review-cycle-{cycle_number} artifact"
    )
    return (
        f"{prefix} for {wp_id} on {mission_slug} (status={result.status!r}): "
        f"{result.diagnostic or 'no diagnostic provided'}. The artifact "
        f"was written to {artifact_path} but is NOT committed."
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
) -> bool:
    """Best-effort commit of a written review-cycle artifact (D-PLAN-11/T026).

    T004/#2697: reuses the SAME ``commit_artifact`` port capability
    ``tasks_mark_status.py``/``tasks_map_requirements.py`` already call — no
    new commit/staging mechanism. ``review-cycle-N.md`` is ADR 2026-08-03-1's
    ``REVIEW_CYCLE`` kind, so this call passes ``kind=REVIEW_CYCLE``. This
    ``kind`` argument is SEPARATE from ``_review_cycle_wp_dir``'s own
    directory resolution (which deliberately still resolves
    ``WORK_PACKAGE_TASK`` — see that function's docstring): the commit
    router's ``_group_files_by_partition`` re-classifies each committed file
    by its OWN path-derived kind and overrides whatever kind the caller
    passes.

    **WP05 (verdict-seam-write-unification-01KZ9Q35, T026/D-PLAN-11)
    DEMOTE**: with every verdict reader now on the event authority
    (``status.event_sourced_review_result`` — this mission's reader
    collapse), this per-file ``.md`` commit is no longer the authoritative
    durable act; ``status.emit.emit_status_transition``'s ``review_result``
    append is (contracts/verdict-durability-write.md G1/NFR-004). A
    non-``"committed"`` result — including exhausted contention retries — is
    now a logged **WARNING**, never a raised ``ReviewCycleError``: this
    function returns ``False`` instead. The retry loop is KEPT as
    best-effort-render defense-in-depth (a transient index-lock contention
    still gets a few bounded retries before giving up), but is no longer
    *authoritative* machinery — the caller no longer unwinds (unlinks) the
    just-written artifact on a failed/incomplete commit, since an
    uncommitted-but-written ``.md`` is tolerated now that it is not the
    verdict's authority. Returns ``True`` iff the artifact was durably
    committed.

    T042 (FR-002 mechanism, shared with WP11): ``CommitRouterResult.status``
    is a closed four-value ``Literal`` that collapses any git-level failure
    (including an ``index.lock`` collision) to ``"error"`` with no signal
    distinguishing "lost a race for the index" from "the commit failed for
    some other reason." The buildable form uses the EXISTING public probe
    ``specify_cli.status.views.git_operation_in_progress`` (whose
    ``_GIT_OP_MARKERS`` already include ``"index.lock"``): on a
    ``status == "error"`` result, retry the SAME ``commit_artifact`` call,
    bounded, ONLY when the probe corroborates a git operation is genuinely in
    progress right now. This retry loop lives ENTIRELY outside T041's
    ``feature_status_lock`` scope (NFR-006 forbids holding an inter-process
    lock across a ``git`` subprocess invocation).
    """
    message = (
        f"chore: Record review-cycle-{cycle_number} ({verdict}) for {wp_id} on "
        f"{mission_slug}"
    )
    mission = MissionHandle(repo_root=main_repo_root, mission_slug=mission_slug)
    policy = ProtectionPolicy.resolve(main_repo_root)

    attempt = 1
    while True:
        result = commit_router.commit_artifact(
            mission,
            (artifact_path,),
            message,
            kind=MissionArtifactKind.REVIEW_CYCLE,
            policy=policy,
        )
        if result.status == "committed":
            return True

        contending = result.status == "error" and git_operation_in_progress(main_repo_root)
        if not contending or attempt >= _COMMIT_CONTENTION_MAX_ATTEMPTS:
            logger.warning(
                "%s",
                _commit_failure_message(
                    wp_id=wp_id,
                    mission_slug=mission_slug,
                    cycle_number=cycle_number,
                    artifact_path=artifact_path,
                    result=result,
                    exhausted_contention_retries=contending,
                ),
            )
            return False
        time.sleep(_COMMIT_CONTENTION_RETRY_SLEEP_SECONDS)
        attempt += 1


def _allocate_and_write_review_cycle_locked(
    *,
    main_repo_root: Path,
    mission_slug: str,
    wp_id: str,
    sub_artifact_dir: Path,
    reviewer_agent: str,
    affected_files: list[AffectedFile],
    body: str,
) -> tuple[ReviewCycleArtifact, Path, str]:
    """Allocate the next cycle number, build, write, and validate the artifact.

    T041/FR-005 scope: this function's ``with feature_status_lock(...)`` body
    is the ENTIRE critical section this WP serializes — cycle-number
    allocation through the write and its post-write validation, and NOTHING
    past it. The commit call (:func:`_commit_review_cycle_artifact`) is a git
    subprocess invocation and stays OUTSIDE this lock (NFR-006 forbids
    holding an inter-process lock across a ``git`` subprocess).

    FR-003/SC-007 (WP06): no longer takes a ``verdict`` parameter --
    ``ReviewCycleArtifact`` carries no such field. The caller
    (:func:`create_rejected_review_cycle`) still threads its own ``verdict``
    parameter into the event-side :class:`~specify_cli.status.ReviewResult`
    and the best-effort commit message; neither of those is this function's
    concern.

    This is a DIFFERENT, disjoint critical section from ``_mt_execute``'s own
    ``feature_status_lock`` acquisition over the status-event emit
    (``tasks_move_task.py`` calls ``_mt_finalize_plan`` — which reaches this
    writer — BEFORE ``_mt_execute`` acquires its own lock instance). The two
    do not serialize against each other: this WP's FR-005 scope is
    deliberately narrowed to (cycle-number-allocation + artifact-write) only,
    not the wider (artifact, status-event) pair, which would require
    restructuring the caller's control flow and is out of this WP's reach.
    ``feature_status_lock`` is thread-reentrant (a thread-local depth
    counter), so a caller that already holds it may safely call in without
    deadlocking.

    T043: a write or post-write-validation failure unlinks the just-written
    file WHILE STILL HOLDING the lock (the ``try/except`` is nested inside
    the ``with`` block, not after it), so a racing second writer can never
    observe the orphan mid-cleanup and mistake it for a legitimate prior
    cycle.
    """
    with feature_status_lock(main_repo_root, mission_slug):
        cycle_n = ReviewCycleArtifact.next_cycle_number(sub_artifact_dir)
        filename = _validate_review_cycle_filename(f"review-cycle-{cycle_n}.md")
        artifact = ReviewCycleArtifact(
            cycle_number=cycle_n,
            wp_id=wp_id,
            mission_slug=mission_slug,
            reviewer_agent=reviewer_agent or "unknown",
            reviewed_at=now_utc().strftime(UTC_SECOND_TIMESTAMP_FORMAT),
            affected_files=affected_files,
            body=body,
        )
        validate_review_artifact(artifact)

        artifact_path = sub_artifact_dir / filename
        try:
            artifact.write(artifact_path)
            validate_review_artifact_file(artifact_path)
        except ReviewCycleError:
            artifact_path.unlink(missing_ok=True)
            raise

    return artifact, artifact_path, filename


def create_rejected_review_cycle(
    *,
    main_repo_root: Path,
    mission_slug: str,
    wp_id: str,
    wp_slug: str,
    feedback_source: Path | None = None,
    body: str | None = None,
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

    Exactly one of ``feedback_source`` / ``body`` must be supplied:

    * ``feedback_source`` — a real, caller-supplied reviewer-feedback file.
      Routes through :func:`_guard_feedback_source_provenance` (path- AND
      content-identity checks) because this is the shape #990/#2996(b) guard
      against: a reviewer accidentally or maliciously re-submitting a prior
      cycle's own artifact as "new" feedback.
    * ``body`` — a body the CALLER ITSELF generated (e.g. the machine's
      synthesized ``"Approved by {reviewer}: {reference}"`` approval note).
      Bypasses the provenance guard entirely: a self-generated body is
      categorically not the attack the guard exists to refuse, and routing
      it through the content-identity arm produces a false collision when
      the same deterministic inputs (reviewer, ``--note``) repeat across
      cycles (M1 — adversarial squad finding on PR #3156). There is no
      on-disk file to path-check either, so the path-identity arm is moot
      for this leg.
    """
    if (feedback_source is None) == (body is None):
        raise ReviewCycleError(
            "create_rejected_review_cycle requires exactly one of "
            "feedback_source or body"
        )

    safe_mission_slug = _validate_segment("mission_slug", mission_slug)
    safe_wp_slug = _validate_segment("wp_slug", wp_slug)
    safe_wp_id = _validate_segment("wp_id", wp_id)
    # FR-001/FR-007 write-in-home: land the review-cycle artifact in its
    # ``tasks/<wp>/`` home via the shared owner function (``_review_cycle_
    # wp_dir`` -- deliberately still PRIMARY/WORK_PACKAGE_TASK-anchored; see
    # that function's own docstring for the disclosed reason ADR 2026-08-03-1's
    # full COORD-under-coord-topology flip is not yet shipped) — not a
    # caller-derived, kind-blind join. This fixes both this direct
    # site AND the move-task ``--review-feedback-file`` caller (which passes
    # no pre-resolved dir), from this one edit.
    sub_artifact_dir = _review_cycle_wp_dir(main_repo_root, safe_mission_slug, safe_wp_slug)

    if feedback_source is not None:
        if not feedback_source.exists():
            raise ReviewCycleError(f"Review feedback file not found: {feedback_source}")
        if not feedback_source.is_file():
            raise ReviewCycleError(
                f"Review feedback path is not a file: {feedback_source}"
            )
        resolved_body = feedback_source.read_text(encoding="utf-8")
        if not resolved_body.strip():
            raise ReviewCycleError(f"Review feedback file is empty: {feedback_source}")
        _guard_feedback_source_provenance(
            feedback_source=feedback_source,
            sub_artifact_dir=sub_artifact_dir,
        )
    else:
        assert body is not None
        if not body.strip():
            raise ReviewCycleError("Review feedback body is empty")
        resolved_body = body

    parsed_affected: list[AffectedFile] = [
        AffectedFile(path=affected["path"], line_range=affected.get("line_range"))
        for affected in affected_files or []
    ]

    # T040/T041 (FR-005/NFR-006): allocation, artifact construction, the
    # write, and post-write validation are ONE critical section serialized
    # under ``feature_status_lock`` — see
    # ``_allocate_and_write_review_cycle_locked``'s docstring for the exact
    # scope and why the commit call below must stay outside it.
    artifact, artifact_path, filename = _allocate_and_write_review_cycle_locked(
        main_repo_root=main_repo_root,
        mission_slug=safe_mission_slug,
        wp_id=safe_wp_id,
        sub_artifact_dir=sub_artifact_dir,
        reviewer_agent=reviewer_agent,
        affected_files=parsed_affected,
        body=resolved_body,
    )
    pointer = build_review_cycle_pointer(safe_mission_slug, safe_wp_slug, filename)

    if commit_router is not None:
        try:
            _commit_review_cycle_artifact(
                commit_router,
                main_repo_root=main_repo_root,
                mission_slug=safe_mission_slug,
                wp_id=safe_wp_id,
                artifact_path=artifact_path,
                cycle_number=artifact.cycle_number,
                verdict=verdict,
            )
        except Exception:
            # M2 (adversarial squad, PR #3156): an INFRASTRUCTURE failure in
            # the commit attempt itself (a raw exception from the router /
            # mission-resolution layer -- e.g. ``MissionSelectorAmbiguous`` or
            # an ``OSError`` from the underlying git invocation) must not
            # leave an orphaned, uncommitted artifact on disk. Without this
            # rollback, a rejection retry hits the content-identity guard
            # against its own orphan ("duplicates a prior review-cycle
            # artifact") and is refused forever, while an approval retry
            # short-circuits at the "latest.verdict != rejected" no-op check
            # (the orphan's verdict is already "approved") and silently
            # reports success despite the write never being committed. The
            # failure state must be "no artifact", not "uncommitted
            # artifact", so a caller can simply retry the same operation.
            # This unlink is deliberately OUTSIDE ``feature_status_lock``
            # (T041) — each concurrent writer already holds a DISTINCT,
            # serialized-allocation ``artifact_path`` by the time it reaches
            # this line, so no racing writer can ever observe or be confused
            # by another writer's own orphan cleanup.
            #
            # WP05 (verdict-seam-write-unification-01KZ9Q35, T026/D-PLAN-11)
            # NARROWED this except's practical scope (not its shape):
            # ``_commit_review_cycle_artifact`` no longer raises
            # ``ReviewCycleError`` for a non-``"committed"`` result (that is
            # now a best-effort WARNING returning ``False`` -- the ``.md``
            # commit is demoted, no longer the authoritative durable act).
            # This ``except Exception`` therefore now only ever fires for a
            # genuine infra exception the router/mission-resolution layer
            # raises directly (the ``MissionSelectorAmbiguous``/``OSError``
            # case above), which is a distinct, more severe failure than "the
            # commit attempt completed but returned a non-committed status" —
            # out of T026's best-effort-render scope, so still rolled back and
            # re-raised, matching the pre-existing convention: a rollback must
            # never silently swallow the triggering failure.
            artifact_path.unlink(missing_ok=True)
            raise

    review_result = ReviewResult(
        reviewer=artifact.reviewer_agent,
        # WP05 (verdict-seam-write-unification-01KZ9Q35, T025): routed through
        # the canonical artifact<->event verdict bridge (FR-005) instead of
        # re-inlining the ``rejected``/``changes_requested`` equivalence here
        # -- ``verdict`` is this function's own ``Literal["approved",
        # "rejected"]`` parameter, i.e. exactly
        # :data:`~specify_cli.status.verdict_vocab.EmissionArtifactVerdict`,
        # so :func:`~specify_cli.status.verdict_vocab.emission_event_verdict`
        # (the emission-scoped bridge -- this constructs an EMITTED
        # ``review_result``) is the correct conversion, not the general
        # four-value :func:`~specify_cli.status.verdict_vocab.to_event_verdict`.
        verdict=emission_event_verdict(verdict),
        reference=pointer,
        feedback_path=str(artifact_path),
    )
    return CreatedRejectedReviewCycle(
        artifact_path=artifact_path,
        pointer=pointer,
        artifact=artifact,
        review_result=review_result,
    )
