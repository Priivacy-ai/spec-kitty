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

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "CoordRepairOutcome",
    "coord_incoherent_done_wps",
    "repair_coord_strand",
]


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
    from specify_cli.status import COORD_OWNED_STATUS_FILES

    slug = feature_dir.name
    for filename in sorted(COORD_OWNED_STATUS_FILES):
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
