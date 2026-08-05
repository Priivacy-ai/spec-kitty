"""Review artifact consistency gates for release signoff."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

from mission_runtime import MissionArtifactKind
from specify_cli.review.artifacts import (
    TERMINAL_REVIEW_LANES,
    LatestReviewArtifactVerdict,
    latest_review_artifact_verdict,
)
from specify_cli.status import materialize_snapshot
from specify_cli.status import ReviewOverride, ReviewResult

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
    its **review-cycle artifacts**. Review-cycle artifacts are NOT resolved through
    this generic helper (see :func:`_artifact_dirs_for_wp`'s own docstring for why
    and how) — this helper's sole remaining caller is
    :func:`_resolve_lane_state_read_dir`. Each partition MUST resolve from its own
    declared home; a single caller-supplied directory is correct for at most one of
    the two. Routed through the ONE affirmative surface→filesystem seam
    (lifecycle-gate-execution-context WP02): a PRIMARY-partition kind resolves the
    primary mission dir for every topology, a COORD-partition kind resolves the
    coordination husk when its worktree is materialised.

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


def _artifact_dirs_for_wp(feature_dir: Path, wp_id: str) -> Path:
    """T059 (FR-007): the SINGLE resolved review-cycle directory for *wp_id*.

    Narrowed from the pre-T059 multi-candidate fan-out (the exact
    ``tasks/<wp_id>`` dir plus every ``tasks/<wp_id>-*`` sibling — a
    deliberate tolerance for the slug-derivation divergence T057 fixes) to
    ONE directory, now that WP08's reconciliation has run against this
    repository (evidenced in this WP's Activity Log: ``spec-kitty doctor
    review-cycle-reconcile --json`` reports 194 findings across 45 missions,
    every one classified ``deleted_coord_branch_absorption`` — the
    steady-state, always-PRIMARY-absorbing class this resolver's own
    absorption fallback below already lands on; ZERO findings carry the
    riskier ``live_coord_pre_adr_primary_record`` class a naive narrowing
    could strand) and T057 gives every consumer a correctly-disambiguated
    ``wp_slug``.

    Resolves through :func:`specify_cli.review.cycle._review_cycle_wp_dir`
    (the T058 owner function), at its DEFAULT ``kind`` — i.e. the SAME
    ``MissionArtifactKind.WORK_PACKAGE_TASK`` (PRIMARY, every topology) the
    WRITE seam and the arbiter resolve through. Every site the retired
    fan-out named — ``feature_dir / "tasks" / wp_id`` and
    ``feature_dir / "tasks" / f"{wp_id}-*"`` — collapses into this one call.

    **WP13 finding (disclosed, not silently worked around): this gate does
    NOT opt into ``kind=REVIEW_CYCLE``, despite ADR 2026-08-03-1 designating
    review-cycle artifacts COORD-partition.** Empirically verified (a
    throwaway probe against the ``coord_topology_mission`` fixture, driving
    the REAL production writer :func:`create_rejected_review_cycle` then
    calling this gate): opting ONLY this gate into ``kind=REVIEW_CYCLE``
    while the WRITE seam stays ``WORK_PACKAGE_TASK``-anchored (per
    ``_review_cycle_wp_dir``'s own disclosed finding) makes the writer and
    this gate resolve to DIFFERENT directories the moment a coord-topology
    mission's coordination worktree is materialised — the gate would then
    find NOTHING where the writer just wrote a genuine rejection, silently
    passing a rejected review. That is precisely the fail-open class of
    defect C-001 exists to prevent, and reproduces it as a NEW regression
    this WP would introduce, not merely fail to fix. T062's "COORD wins when
    both partitions hold a genuine record" conflict rule is consequently
    NOT implemented by this WP: it requires the WRITE-side flip first (see
    ``_review_cycle_wp_dir``'s own docstring for why that flip is not yet
    safe), so gate and writer keep agreeing. See this WP's final report.

    ``feature_dir`` may be either mission surface (PRIMARY or the coord
    husk) — mirroring :func:`_resolve_partition_read_dir`'s own convention —
    since ``feature_dir.name`` is the mission slug either way. A bare non-git
    test fixture (no workspace root derivable) degrades to a flat
    ``feature_dir / "tasks" / <slug>`` join — the SAME degrade
    ``_resolve_partition_read_dir`` uses for that edge case — but still
    resolves *slug* through :func:`_wp_slug_candidates` (T057's own matcher,
    reused directly since it needs no ``repo_root``/``placement_seam``): this
    module's own test suite (``tests/post_merge/test_review_artifact_
    consistency.py``, via ``tests/reliability/fixtures/mission.py``) seeds
    plain, non-git mission trees whose review-cycle content lives at a
    hyphen-suffixed ``tasks/<wp_id>-<slug>/`` dir, so falling back to the
    BARE ``wp_id`` here (skipping slug resolution entirely) would silently
    stop finding it -- reproducing the exact divergence T057 exists to close.
    """
    from specify_cli.cli.commands.agent.tasks_materialization import (
        WpSlugAmbiguous,
        _resolve_wp_slug,
        _wp_slug_candidates,
    )
    from specify_cli.core.paths import WorkspaceRootNotFound, resolve_canonical_root
    from specify_cli.review.cycle import _review_cycle_wp_dir

    mission_slug = feature_dir.name
    try:
        repo_root = resolve_canonical_root(feature_dir)
    except WorkspaceRootNotFound:
        tasks_dir = feature_dir / "tasks"
        candidates = _wp_slug_candidates(tasks_dir, wp_id) if tasks_dir.exists() else []
        if len(candidates) > 1:
            raise WpSlugAmbiguous(
                f"task id {wp_id!r} matches multiple tasks/ files resolving to "
                f"different slugs: {', '.join(candidates)}. Rename so exactly "
                "one file matches this task id before retrying."
            ) from None
        flat_slug = candidates[0] if candidates else wp_id
        return feature_dir / "tasks" / flat_slug

    wp_slug = _resolve_wp_slug(repo_root, mission_slug, wp_id)
    # Deliberately NO ``kind=`` override -- see this function's own docstring
    # ("WP13 finding") for why this gate stays on ``_review_cycle_wp_dir``'s
    # default (``WORK_PACKAGE_TASK``), matching the WRITE seam exactly.
    resolved: Path = _review_cycle_wp_dir(repo_root, mission_slug, wp_slug)
    return resolved


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


def _event_sourced_gate_verdict(state: Mapping[str, Any]) -> str | None:
    """FR-001 (WP07/T029): the event log's own opinion on this WP's verdict.

    Returns ``"approved"`` / ``"changes_requested"`` when the reduced snapshot's
    ``review_result`` slot carries a recorded verdict — the event log is
    authoritative for *which* verdict is current, so either value overrides
    whatever the frontmatter's latest review-cycle artifact says (T029's two
    disagreement tests: event-approved-over-frontmatter-rejected, and the
    reverse).

    Returns ``None`` when the event log has no opinion for gate-clearing
    purposes — this DELIBERATELY collapses two distinct
    :class:`~specify_cli.status.reducer.ReviewResultLookup` outcomes that stay
    distinguishable upstream:

    - the slot is entirely ABSENT (un-migrated mission / WP never exited
      ``in_review`` — T027's fallback case), and
    - the slot is present but ``None`` (a ``--force`` exit from ``in_review``
      that supplied no ``ReviewResult`` — T028's "no verdict was ever
      recorded" case).

    Both cases mean the same thing for THIS gate specifically: the event log
    has nothing to add, so the pre-existing frontmatter-only answer
    (``latest_review_artifact_verdict`` / the terminal-lane rejection check
    below) is the correct — and only remaining — signal. This is a narrow,
    local collapse for gate-clearing purposes only; it is not a re-assertion
    that the two cases are the same thing (they are not — see
    :class:`~specify_cli.status.reducer.ReviewResultLookup`'s own docstring).

    Decodes the ``review_result`` slot locally (mirrors
    :func:`_snapshot_review_override`'s existing convention in this module)
    rather than importing ``specify_cli.status.reducer``'s
    ``review_result_from_state`` directly: this package must import only
    through the ``specify_cli.status`` public facade
    (``tests/architectural/test_status_module_boundary.py``'s SR-2 repo-wide
    AST gate), and ``review_result_from_state`` is not on that facade's
    ``__all__`` (``status/__init__.py`` is outside this WP's owned-files
    surface — see this WP's Activity Log for the escalation note).
    """
    if "review_result" not in state:
        return None
    raw = state["review_result"]
    if not isinstance(raw, Mapping):
        return None
    try:
        return str(ReviewResult.from_dict(dict(raw)).verdict)
    except (KeyError, TypeError, ValueError):
        return None


def _resolve_terminal_verdict_conflict(
    lane: str,
    artifact_state: LatestReviewArtifactVerdict,
    event_verdict: str | None,
) -> LatestReviewArtifactVerdict | None:
    """FR-001 precedence: apply the event-sourced verdict over the frontmatter
    artifact's own verdict field for terminal-lane ("approved"/"done") gate
    purposes, when the event log has an opinion.

    Returns the artifact metadata to report as a blocking finding, or ``None``
    when the WP is not blocked. Order matters:

    1. A non-terminal lane is never blocked (unchanged from the pre-WP07
       behaviour).
    2. A complete arbiter override (``has_override``) already clears the gate
       unconditionally (FR-010) — checked BEFORE ``event_verdict`` so the T026
       precedence rule holds: an override clears the gate over a
       ``review_result`` of ``"changes_requested"`` without erasing that
       ``review_result`` value anywhere (this function only decides
       gate-clearing; it never mutates a slot).
    3. ``event_verdict == "approved"``: the event wins — not blocked, even if
       the frontmatter's latest artifact still reads ``"rejected"``.
    4. ``event_verdict == "changes_requested"``: the event wins — blocked,
       even if the frontmatter's latest artifact reads ``"approved"`` (the
       reverse-disagreement case). The reported ``verdict`` is the
       event-sourced value: FR-001 makes the event authoritative for *which*
       verdict is current, so that is the honest answer to "what verdict is
       this finding about", even though the artifact file's OWN frontmatter
       field disagrees.
    5. ``event_verdict is None``: the event log has no opinion (T027 absent /
       T028 null, collapsed by :func:`_event_sourced_gate_verdict`) — defer
       entirely to the pre-existing frontmatter-only answer, unchanged from
       the pre-WP07 behaviour.
    """
    if lane not in TERMINAL_REVIEW_LANES:
        return None
    if artifact_state.has_override:
        return None
    if event_verdict == "approved":
        return None
    if event_verdict == "changes_requested":
        return LatestReviewArtifactVerdict(
            path=artifact_state.path,
            cycle_number=artifact_state.cycle_number,
            verdict=event_verdict,
            has_override=False,
        )
    return artifact_state if artifact_state.verdict == "rejected" else None


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
    preview handed a PRIMARY dir, so the reduce read an empty status log (a
    coord mission keeps its authoritative log on the coordination husk), every WP
    looked stateless, and the gate passed a rejected review by default while the
    real consolidation — handed the coord husk — refused. The **lane snapshot** now
    resolves from its ``STATUS_STATE`` home, and each WP's **review-cycle
    artifact** resolves through :func:`_artifact_dirs_for_wp` (T058's owner
    function, ``MissionArtifactKind.WORK_PACKAGE_TASK`` — PRIMARY, every
    topology, matching the WRITE seam exactly; see that function's own
    docstring for the disclosed reason it does not opt into
    ``REVIEW_CYCLE``) — so both callers resolve the same two surfaces and
    AGREE (SC-002).

    Reduces via the read-only :func:`materialize_snapshot`, NOT :func:`materialize`
    (#2934): this is a merge-readiness *check*, so it must not mutate the working
    tree. ``materialize`` writes ``status.json`` as a side effect; on a mission
    whose event log is empty/absent that write orphans a derived ``status.json``
    with no backing ``status.events.jsonl`` (the invalid state ``validate`` flags),
    which the merge then commits alone. A gate reads; it does not persist.

    **FR-001 (WP07/T029)**: in addition to the frontmatter-parsing check
    (unchanged, and still the sole answer for a WP whose event log has no
    opinion — see :func:`_event_sourced_gate_verdict`), each WP's event-sourced
    ``review_result`` reducer slot is now also consulted. When the two
    disagree, the event wins per FR-001 — see
    :func:`_resolve_terminal_verdict_conflict` for the exact precedence.
    ``cli/commands/review/_lane_gate.py``'s ``check_wp_lanes`` (Gate 1) calls
    this same function, so it consults the event-sourced answer too, with no
    separate call needed there (traced, not assumed — WP07 Activity Log).

    **T059 (FR-007)**: each WP now resolves exactly ONE review-cycle
    directory (:func:`_artifact_dirs_for_wp`, narrowed from the pre-T059
    multi-candidate fan-out) — see that function's own docstring for the
    WP08-reconciliation evidence this narrowing is safe against this
    repository's stranded records.
    """
    lane_state_dir = _resolve_lane_state_read_dir(feature_dir)
    snapshot = materialize_snapshot(lane_state_dir)
    selected_wp_ids = wp_ids or sorted(snapshot.work_packages)
    findings: list[ReviewArtifactFinding] = []

    for wp_id in selected_wp_ids:
        state = snapshot.work_packages.get(wp_id)
        if state is None:
            continue
        lane = str(state.get("lane", ""))
        snapshot_override = _snapshot_review_override(state)
        event_verdict = _event_sourced_gate_verdict(state)
        artifact_dir = _artifact_dirs_for_wp(feature_dir, wp_id)
        latest_path = _latest_review_artifact_path(artifact_dir)
        if latest_path is None:
            continue
        try:
            artifact_state = latest_review_artifact_verdict(
                artifact_dir, snapshot_override=snapshot_override
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
            continue
        if artifact_state is None:
            continue
        conflict = _resolve_terminal_verdict_conflict(
            lane, artifact_state, event_verdict
        )
        if conflict is None:
            continue
        findings.append(
            RejectedReviewArtifactFinding(
                wp_id=wp_id,
                lane=lane,
                artifact_path=conflict.path,
                cycle_number=conflict.cycle_number,
                verdict=conflict.verdict,
            )
        )

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
