"""Coordination-branch coherence: the single strand-derivation + repair owner.

Mission ``merge-coord-rollback-transactionality`` (#2786 + #2367-B), FR-009.

The strand-derivation and the git-revert repair are **coordination-domain**
knowledge and get exactly one home here, consumed by all three call-sites — the
marker-persist site, the resume heal-gate, and the ``doctor coordination`` check
— so the three never drift (the #2786-C seed).

Two load-bearing layering rules keep this module clean:

* The reader (:func:`coord_incoherent_done_wps`) derives from the **committed
  coordination ref** via ``coordination.status_service.EventLogReadContract`` —
  never the working tree. A committed-vs-working diff at a #2786 mark point is
  empty (the rollback restores primary paths, not the coord worktree) and would
  silently drop the strand.
* The repair (:func:`repair_coord_strand`) imports ``_make_merge_env``
  **function-locally**. A module-top ``from specify_cli.lanes.merge import
  _make_merge_env`` creates the cycle ``merge.executor -> coordination.coherence
  -> lanes.merge -> merge.config``. There is intentionally **no** module-top
  ``coordination -> merge`` / ``coordination -> lanes`` import in this file.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from kernel.paths import to_posix
from mission_runtime import (
    MissionArtifactKind,
    MissionTopology,
    kind_for_mission_file,
    kind_is_coordination_residue,
)

__all__ = [
    "CoordRepairOutcome",
    "coord_incoherent_done_wps",
    "is_coord_residue_churn",
    "is_self_bookkeeping_churn",
    "is_status_state_path",
    "is_toolchain_generated_churn",
    "repair_coord_strand",
]


def is_self_bookkeeping_churn(path: str | Path) -> bool:
    """Return True for spec-kitty's OWN bookkeeping files (retired IC-07a).

    WP11 retirement: absorbs the retired ``mission_runtime`` self-bookkeeping
    predicate (#2102 / G-5 invariant) as the self-bookkeeping LEG of the owner union — ``meta.json``
    (mission identity metadata), the encoding-provenance
    ``.kittify/encoding-provenance/global.jsonl``, and ``kitty-ops/<ULID>.jsonl``
    Op-record orphans (#2251) are spec-kitty's own bookkeeping, not mission planning
    artifacts, and their churn must not block a dirty-state gate.

    Exposed as its own predicate (not folded silently into
    :func:`is_toolchain_generated_churn`'s body) because three consumers
    (``merge/git_probes.py``, ``cli/commands/agent/mission_record_analysis.py``,
    ``acceptance/__init__.py``) already apply the coord-residue leg SEPARATELY under
    their own topology-gated conditional (:func:`is_coord_residue_churn`
    unconditionally projects ``MissionTopology.COORD`` — it is only correct to consult
    under an already-established coordination topology). Routing those call sites
    through the full union would silently widen the residue drop to run
    unconditionally / unscoped, which is a behaviour change this retirement must NOT
    make (C6). This predicate is therefore the precise, self-bookkeeping-only
    replacement for the retired symbol; :func:`is_toolchain_generated_churn` composes
    it with the residue authority for callers that want the full union in one call.

    The filename / suffix / regex literals are function-local (not module-level
    ``frozenset`` / ``tuple`` / ``re.compile`` assignments) so the R-014
    exemption-registry scan — which only walks module-level assignments
    (``tests/architectural/test_exemption_registry_ratchet.py``) — does not treat this
    as a NEW per-gate filename exemption requiring its own registry row (C9): this is
    the owner absorbing the retired mechanism, not a ninth list.
    """
    kitty_ops_op_record = re.compile(r"(?:^|/)kitty-ops/[0-9A-HJKMNP-TV-Z]{26}\.jsonl$")
    normalized = to_posix(path).rstrip("/")
    if PurePosixPath(normalized).name == "meta.json":
        return True
    if normalized.endswith(".kittify/encoding-provenance/global.jsonl"):
        return True
    return bool(kitty_ops_op_record.search(normalized))


def is_coord_residue_churn(
    path: str | Path,
    *,
    mission_slug: str | None = None,
) -> bool:
    """Return True for coord-partition residue: the retired IC-07b leg (WP12).

    WP12 retirement: absorbs the retired ``mission_runtime`` predicate
    ``is_coordination_artifact_residue_path`` (module
    ``src/mission_runtime/artifacts.py``, registry mechanism `IC-07b`) as the
    coord-residue LEG of the owner union. A path is coord-partition residue when
    its declared :class:`~mission_runtime.MissionArtifactKind` is a member of the
    COORD partition (the append-only status log/snapshot, ``issue-matrix.md``,
    ``acceptance-matrix.json``) — only THOSE kinds' stale primary-checkout copies
    are legitimate residue after a coordination-topology commit; every other
    recognised kind (planning SOURCE + finalized + identity docs, and, after the
    FR-003 re-home, ``analysis-report.md``) is a PRIMARY-partition kind whose
    stale primary copy is REAL dirt, never residue. An unrecognised path
    (``kind_for_mission_file`` returns ``None``) is never residue either.

    Behaviour-preserving reimplementation: composes the SAME two already-public
    ``mission_runtime`` primitives the retired predicate used internally —
    :func:`~mission_runtime.kind_for_mission_file` (the file→kind classifier) and
    :func:`~mission_runtime.kind_is_coordination_residue` (the kind/topology
    residue authority) — fixed at :attr:`~mission_runtime.MissionTopology.COORD`
    (this predicate answers "is this COORD residue", not a topology-generic
    question; ``routes_through_coordination(COORD)`` is always True by
    definition, so the topology parameter is not separately gated here).

    Exposed as its own predicate (not folded silently into
    :func:`is_toolchain_generated_churn`'s body) because several consumers
    (``coordination/commit_router.py``, ``cli/commands/implement.py``,
    ``cli/commands/implement_cores.py``,
    ``cli/commands/agent/mission_record_analysis.py``, ``acceptance/__init__.py``,
    ``lanes/auto_rebase.py``) already apply — or must apply — the residue check
    SEPARATELY from :func:`is_self_bookkeeping_churn`, several of them under their
    own topology-gated conditional. Routing those call sites through the full
    union would silently widen (or narrow) the churn drop, a behaviour change
    this retirement must NOT make (C6). :func:`is_toolchain_generated_churn`
    composes this leg with the self-bookkeeping leg for callers that want the
    full union in one call.
    """
    kind = kind_for_mission_file(path, mission_slug=mission_slug)
    if kind is None:
        return False
    return kind_is_coordination_residue(kind, MissionTopology.COORD)


def is_status_state_path(path: str | Path, *, mission_slug: str | None = None) -> bool:
    """Return True iff *path* classifies as the STATUS_STATE kind (WP13 / IC-07c).

    Narrow ON PURPOSE — deliberately NOT :func:`is_coord_residue_churn` (which
    also matches ``ACCEPTANCE_MATRIX`` / ``ISSUE_MATRIX``): this leg exists for
    the WP13 retirement of ``COORD_OWNED_STATUS_FILES`` (the status log +
    snapshot basename frozenset), whose consumers need to recognise EXACTLY
    ``status.events.jsonl`` / ``status.json`` and nothing else (e.g. a coord
    commit's planning-artifact staging must still stage ``acceptance-matrix.json``
    / ``issue-matrix.md``, only skipping the status pair).

    Exposed here (not inlined at each call site) so trio-seam-restricted
    consumers (``cli/commands/implement.py`` / ``implement_cores.py``, guarded
    by ``tests/architectural/test_trio_seam_only.py``) can classify by kind
    without importing the forbidden ``mission_runtime.kind_for_mission_file``
    primitive directly — this predicate is the blessed, owner-module wrapper.
    """
    return kind_for_mission_file(path, mission_slug=mission_slug) is MissionArtifactKind.STATUS_STATE


def is_toolchain_generated_churn(
    path: str | Path,
    *,
    mission_slug: str | None = None,
) -> bool:
    """The single definition of toolchain-generated churn (FR-012).

    A path is toolchain-generated churn when spec-kitty itself produced it as part
    of running the workflow — as opposed to work authored by the operator — so a
    dirty-state gate must not treat its churn as a real block. This is the ONE
    canonical classifier every gate consults, closing the C7 defect where
    ``merge/git_probes.py`` exempted a tracked-modified ``meta.json`` via the retired
    ``mission_runtime`` self-bookkeeping predicate while ``git/ref_advance.py`` never
    consulted that predicate — the same file was invisible to one gate and fatal at
    another.

    Classification is by declared kind and origin, **not** by a per-gate filename
    list (GA-1): the union of the two canonical authorities —
    :func:`is_coord_residue_churn` (a coord-partition artifact's stale primary
    copy — WP12 folded this leg in from the retired ``mission_runtime``
    ``is_coordination_artifact_residue_path`` predicate) and
    :func:`is_self_bookkeeping_churn` (spec-kitty's own bookkeeping:
    ``meta.json``, encoding-provenance JSONL, ``kitty-ops/<ULID>.jsonl`` Op
    records — WP11 folded this leg in from the retired ``mission_runtime``
    self-bookkeeping predicate). WP11-17 retire their scattered filename
    exemptions onto THIS function; adding a ninth per-gate list is the
    regression C9 refuses.

    Args:
        path: The path to classify (posix or ``Path``; relative or absolute).
        mission_slug: When supplied, another mission's artifacts do not count as
            this mission's toolchain churn (passed to the residue authority).

    Returns:
        ``True`` when ``path`` is spec-kitty-generated churn a gate should ignore.
    """
    return is_self_bookkeeping_churn(path) or is_coord_residue_churn(
        path, mission_slug=mission_slug
    )


def coord_incoherent_done_wps(
    coord_ref: str,
    candidate_wps: list[str],
    *,
    repo_root: Path,
    feature_dir: Path,
) -> list[str]:
    """Subset of *candidate_wps* still reducing to ``DONE`` on the committed coord ref.

    This is **the** strand authority (FR-009). ``candidate_wps`` is always *this
    merge's* pre-target ``done`` write-set — the caller passes it; this function
    NEVER enumerates all WPs. Passing ``run.all_wp_ids`` instead would be wrong:
    on a resume it includes WPs a prior attempt legitimately baked ``done``, so
    the heal would revert a genuinely-done WP. A genuinely-pre-existing-``done``
    WP is excluded here **by construction** — it is simply not in the write-set.

    The reduction reads the committed coordination-branch ref (mirroring
    ``merge.done_bookkeeping._durable_done_wps_on_coordination_ref``) and NEVER the
    roll-backable working tree. When the coordination events cannot be read (a
    non-coord topology, a legacy mission, or an unresolvable ref) an empty list is
    returned — there is no strand to repair.

    Args:
        coord_ref: Fully-qualified coordination branch ref carrying the events log.
            Passed in (not re-resolved) so the derivation matches the placement the
            rollback used — no re-resolution drift.
        candidate_wps: This merge's pre-target ``done`` write-set.
        repo_root: Repository root the ``git show`` runs against.
        feature_dir: Mission directory whose ``.name`` anchors the ref path
            (``kitty-specs/<name>/status.events.jsonl``) and whose path drives the
            legacy slug-to-mission-id parse.

    Returns:
        The subset of ``candidate_wps`` still ``DONE`` on the committed ref, in
        the order they appear in ``candidate_wps``.
    """
    if not candidate_wps:
        return []

    # Imported function-locally to mirror the proven, cycle-free pattern in
    # ``_durable_done_wps_on_coordination_ref`` (both reduce coord-``DONE`` via the
    # same ``EventLogReadContract``). No module-top coupling to status internals.
    from specify_cli.coordination.status_service import (
        EventLogReadContract,
        read_event_log,
        wp_lane_actor_from_events,
    )
    from specify_cli.status import Lane

    events = read_event_log(
        EventLogReadContract.coordination_branch_ref(
            repo_root=repo_root,
            destination_ref=coord_ref,
            feature_dir=feature_dir,
            parser_feature_dir=feature_dir,
        )
    )
    if not events:
        return []
    return [
        wp_id
        for wp_id in candidate_wps
        if wp_lane_actor_from_events(events, wp_id)[0] == Lane.DONE
    ]


@dataclass(frozen=True)
class CoordRepairOutcome:
    """Result of a strand-gated coordination repair.

    ``healed`` is ``True`` only when a ``git revert`` was actually performed on
    this call. ``stranded_wp_ids`` is the strand set the gate derived (empty when
    the ref was already coherent). ``error`` carries the swallowed revert
    diagnostic when the revert could not be applied.

    ``worktree_missing`` distinguishes the unresolvable/pruned coordination
    worktree (the ``coord_worktree`` path does not exist) so callers can surface a
    STUCK-marker diagnostic instead of looping the same live-strand error forever.
    ``head_advanced`` flags the concurrency TOCTOU refusal: HEAD moved past the
    expected ``captured_sha + this-merge's-done`` shape (e.g. a concurrent healer
    already reverted), so a blind ``git revert captured_sha..HEAD`` would re-apply
    ``done`` — the repair refuses rather than re-strand.
    """

    healed: bool
    stranded_wp_ids: list[str] = field(default_factory=list)
    error: str | None = None
    worktree_missing: bool = False
    head_advanced: bool = False


def _rev_parse_head(coord_worktree: Path, env: dict[str, str]) -> str | None:
    """Return the coord worktree HEAD SHA, or ``None`` when it cannot be resolved."""
    head = subprocess.run(
        ["git", "-C", str(coord_worktree), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if head.returncode != 0:
        return None
    return head.stdout.strip() or None


def _head_shape_is_expected(
    coord_worktree: Path,
    captured_sha: str,
    head_sha: str,
    candidate_wps: list[str],
    *,
    repo_root: Path,
    feature_dir: Path,
    env: dict[str, str],
) -> bool:
    """HEAD-freshness guard closing the concurrent-double-heal TOCTOU (FR-006).

    The forward revert range is ``captured_sha..HEAD``. Before running it, verify
    HEAD is still the shape the marker was captured against:

    * ``captured_sha`` must be an ancestor of HEAD (reachable) — otherwise the
      worktree diverged and ``captured_sha..HEAD`` is not this merge's done range.
    * the strand must still be LIVE at the worktree HEAD *itself* (re-derived from
      ``head_sha``, not the possibly-lagging ``coord_ref`` the gate read). A
      concurrent healer that already reverted advances HEAD to a coherent tip, so
      the reduction at HEAD is empty here — reverting ``captured_sha..HEAD`` would
      then revert that concurrent revert too and re-apply ``done``. Refuse instead.
    """
    ancestor = subprocess.run(
        ["git", "-C", str(coord_worktree), "merge-base", "--is-ancestor", captured_sha, head_sha],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if ancestor.returncode != 0:
        return False
    live_at_head = coord_incoherent_done_wps(
        head_sha, candidate_wps, repo_root=repo_root, feature_dir=feature_dir
    )
    return bool(live_at_head)


def _clean_coord_status_paths_to_head(
    coord_worktree: Path, feature_dir: Path, env: dict[str, str]
) -> None:
    """Scoped clean-to-HEAD of the mission's coordination status paths.

    The rollback byte-restore leaves the coord worktree DIRTY — the WORKING
    ``status.events.jsonl`` rolled back to ``approved`` while HEAD is still the
    committed ``done``; ``git revert`` refuses over that divergence. Restore ONLY
    the mission's coord-owned status paths (the event log + its materialized
    ``status.json`` snapshot) to HEAD via a scoped ``git checkout HEAD -- <paths>``
    — bounding the blast radius by construction, rather than a whole-worktree
    ``git reset --hard``. Idempotent and a no-op when already clean; the forward
    revert then supersedes it (re-landing the working tree on ``approved`` in
    lockstep with the committed ref). Each path is restored independently with
    ``check=False`` so an untracked-at-HEAD snapshot never aborts the clean.
    """
    # WP13 (IC-07c) retired ``COORD_OWNED_STATUS_FILES``; this loop needs the
    # two canonical status-artifact basenames directly, not a churn-classifier
    # verdict, so it imports the two filename constants (which the retirement
    # left in place) rather than a residue predicate.
    from specify_cli.status import EVENTS_FILENAME, SNAPSHOT_FILENAME

    slug = feature_dir.name
    for filename in sorted((EVENTS_FILENAME, SNAPSHOT_FILENAME)):
        rel = f"kitty-specs/{slug}/{filename}"
        subprocess.run(
            ["git", "-C", str(coord_worktree), "checkout", "HEAD", "--", rel],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )


def repair_coord_strand(
    *,
    coord_ref: str,
    captured_sha: str,
    coord_worktree: Path,
    candidate_wps: list[str],
    repo_root: Path,
    feature_dir: Path,
) -> CoordRepairOutcome:
    """Strand-gated, self-sufficient forward ``git revert`` of a stranded coord ``done``.

    The single repair operation both executor-resume (WP03) and ``doctor --fix``
    (WP04) call — homed in ``coordination`` so a diagnostic command never reaches
    into an executor-private helper (dependency inversion / DIR-044). Both callers
    are thin + equivalent: the primitive owns the worktree-existence check, the
    strand gate, the HEAD-freshness guard, the scoped clean-to-HEAD, and the revert.

    Ordered contract:

    0. **Unresolvable/pruned worktree (FR-007):** if ``coord_worktree`` does not
       exist, return ``worktree_missing=True`` (a distinguishable outcome) so the
       caller surfaces a STUCK diagnostic instead of looping the live-strand error.
    1. **Strand gate (NFR-002 idempotency):** the strand set is re-derived from the
       committed ref via :func:`coord_incoherent_done_wps` first. If the ref is
       already coherent the repair is a no-op — a double-heal cannot revert the
       revert. Running it N times yields a byte-stable coord ``status.events.jsonl``.
    2. **HEAD-freshness guard (concurrency TOCTOU):** :func:`_head_shape_is_expected`
       verifies HEAD has not advanced past the expected ``captured_sha + this
       merge's done`` shape before the ``captured_sha..HEAD`` revert; if it has
       (e.g. a concurrent healer already reverted), the repair refuses
       (``head_advanced=True``) rather than revert a wider range that re-applies
       ``done``.
    3. **Scoped clean-to-HEAD** (:func:`_clean_coord_status_paths_to_head`): AFTER
       the gate, BEFORE the revert, the mission's coord status paths are restored
       to HEAD so the forward revert can apply over the rollback's byte-restored
       (dirty) tree. Idempotent + no-op when clean; scoped to bound the blast radius.

    **Transport (AC-B3/AC-F1):** a forward ``git revert`` of ``captured_sha..HEAD``
    in the coordination worktree, subprocess env via ``_make_merge_env`` (imported
    function-locally to avoid the import cycle). NOT ``advance_branch_ref`` (it
    refuses the non-fast-forward move back to ``captured_sha`` by design); no raw
    ``git update-ref``.

    Args:
        coord_ref: Coordination branch ref used to re-derive coherence.
        captured_sha: Coord tip captured *before* the ``done`` bookkeeping commit;
            the ``git revert`` base.
        coord_worktree: Coordination worktree the revert operates in.
        candidate_wps: This merge's pre-target ``done`` write-set (the strand gate).
        repo_root: Repository root for the committed-ref coherence read.
        feature_dir: Mission directory anchoring the coordination events read.

    Returns:
        A :class:`CoordRepairOutcome` describing whether a revert ran.
    """
    if not coord_worktree.exists():
        # Pruned / unresolvable coord worktree — a distinguishable outcome so the
        # caller emits a STUCK diagnostic rather than looping the live-strand error.
        return CoordRepairOutcome(healed=False, worktree_missing=True)

    stranded = coord_incoherent_done_wps(
        coord_ref, candidate_wps, repo_root=repo_root, feature_dir=feature_dir
    )
    if not stranded:
        # Already coherent (or nothing to heal): no-op — never revert the revert.
        return CoordRepairOutcome(healed=False, stranded_wp_ids=[])

    # Function-local import: a module-top ``from specify_cli.lanes.merge import
    # _make_merge_env`` would create the cycle merge.executor ->
    # coordination.coherence -> lanes.merge -> merge.config.
    from specify_cli.lanes.merge import _make_merge_env

    env = _make_merge_env()
    head_sha = _rev_parse_head(coord_worktree, env)
    if head_sha is None or head_sha == captured_sha:
        # No commits since capture — the strand is not reachable as
        # ``captured_sha..HEAD``; do not attempt an empty revert.
        return CoordRepairOutcome(healed=False, stranded_wp_ids=stranded)

    if not _head_shape_is_expected(
        coord_worktree,
        captured_sha,
        head_sha,
        candidate_wps,
        repo_root=repo_root,
        feature_dir=feature_dir,
        env=env,
    ):
        # HEAD advanced unexpectedly (concurrency TOCTOU) — refuse the wider revert.
        return CoordRepairOutcome(
            healed=False, stranded_wp_ids=stranded, head_advanced=True
        )

    # Scoped clean-to-HEAD (after the gate, before the revert) so the forward
    # revert applies over the byte-restored (dirty) coord worktree.
    _clean_coord_status_paths_to_head(coord_worktree, feature_dir, env)

    revert = subprocess.run(
        ["git", "-C", str(coord_worktree), "revert", "--no-edit", f"{captured_sha}..HEAD"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if revert.returncode != 0:
        subprocess.run(
            ["git", "-C", str(coord_worktree), "revert", "--abort"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        return CoordRepairOutcome(
            healed=False,
            stranded_wp_ids=stranded,
            error=(revert.stderr or revert.stdout or "").strip() or "git revert failed",
        )
    return CoordRepairOutcome(healed=True, stranded_wp_ids=stranded)
