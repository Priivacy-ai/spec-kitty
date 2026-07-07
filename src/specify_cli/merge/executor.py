"""Lane-based merge executor for the merge seam.

Mission #2057 (decompose ``cli/commands/merge.py``) — IC-10 / WP10 (HIGH-RISK).

Relocates ``_run_lane_based_merge`` (the global-lock wrapper) and the CC-102
``_run_lane_based_merge_locked`` driver out of the command shim, decomposing the
driver into phase helpers (each <= 15 CC) that thread shared mutable state via
the :class:`_MergeRunState` dataclass — never closures (INV-3). The decomposition
preserves, byte-for-byte:

* INV-5 — the #1827 ordering: baseline RECORD (post-target-merge, pre-
  bookkeeping-commit, in ``_phase_capture_and_baseline``) → bookkeeping
  ``safe_commit`` → baseline ASSERT (post-commit) — the commit and the assert
  run in ``_phase_commit_and_assert`` in exactly that order.
* INV-6 — the ``_restore_final_bookkeeping_snapshots(...)``-then-reraise rollback
  sites, each with identical exception-class scoping.

Lazy imports inside the phases stay lazy (C-007). One-way import: this module
never imports the command shim.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from specify_cli.lanes.merge import MissionMergeResult
    from specify_cli.lanes.models import LanesManifest

from specify_cli.cli.helpers import console
from specify_cli.core.constants import KITTIFY_DIR
from specify_cli.coordination.surface_resolver import (
    is_under_worktrees_segment,
    resolve_status_surface,
)
from specify_cli.core.git_ops import has_remote, run_command
from specify_cli.core.paths import get_main_repo_root
from specify_cli.git.bookkeeping_commit import commit_merge_bookkeeping
from specify_cli.git.commit_helpers import SafeCommitRecoveryFailed
from specify_cli.git.sparse_checkout import require_no_sparse_checkout
from specify_cli.lanes.persistence import require_lanes_json
from specify_cli.merge._constants import _STATUS_FILENAME, logger
from specify_cli.merge.baseline import (
    BaselineMergeCommitError,
    assert_baseline_merge_commit_on_target as _assert_baseline_merge_commit_on_target,
    record_baseline_merge_commit as _record_baseline_merge_commit,
)
from specify_cli.merge.bookkeeping_projection import (
    _capture_bookkeeping_snapshots,
    _project_status_bookkeeping_to_target,
    _restore_final_bookkeeping_snapshots,
    _target_bookkeeping_status_paths,
    _target_branch_still_at_baseline,
)
from specify_cli.merge.config import MergeStrategy
from specify_cli.merge.done_bookkeeping import (
    _assert_merged_wps_done_on_target,
    _record_merged_wps_done_for_merge,
    _resolve_merge_actor,
)
from specify_cli.merge.git_probes import (
    _branch_trees_equal,
    _classify_porcelain_lines,
    _emit_remediation_hint,
    _is_linear_history_rejection,
    _lane_already_integrated,
    _paths_have_status_changes,
    _raw_porcelain_status,
    _refresh_primary_checkout_after_merge,
)
from specify_cli.merge.ordering import (
    _assign_planning_only_mission_number_if_needed,
    _bake_mission_number_into_mission_branch,
)
from specify_cli.merge.preflight import (
    _check_mission_branch,
    _effective_push_requested,
    _enforce_canonical_status_history,
    _enforce_planning_artifact_target_branch,
    _enforce_review_artifact_consistency,
    _warn_or_confirm_hollow_reviews,
)
from specify_cli.merge.push_preflight import _enforce_target_branch_sync_preflight
from specify_cli.merge.resolve import _load_or_create_merge_state
from specify_cli.merge.state import (
    MergeLockError,
    MergeState,
    acquire_merge_lock,
    clear_state,
    get_state_path,
    release_merge_lock,
)
from specify_cli.merge.workspace import _worktree_removal_delay, cleanup_merge_workspace
from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.missions._read_path_resolver import (
    _canonicalize_primary_read_handle,
    candidate_feature_dir_for_mission,
    primary_feature_dir_for_mission,
    resolve_planning_read_dir,
)
from mission_runtime import MissionArtifactKind
from specify_cli.post_merge.stale_assertions import StaleAssertionReport, run_check
from specify_cli.sync.events import emit_diff_summary_recorded, emit_mission_closed
from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
from mission_runtime import is_coordination_artifact_residue_path

_GLOBAL_MERGE_LOCK_ID = "__global_merge__"


def _emit_merge_diff_summary(
    *,
    repo_root: Path,
    mission_id: str | None,  # WP04/FR-004: ULID or None; legacy missions skip diff emit
    base_ref: str,
    head_ref: str = "HEAD",
    phase_name: str = "accept",
) -> None:
    """Emit one mission-level diff summary for the merged mission."""
    if mission_id is None:
        # Legacy mission without canonical ULID: skip diff summary emission.
        return
    ret, output, _ = run_command(
        ["git", "diff", "--numstat", f"{base_ref}..{head_ref}"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret != 0:
        return

    files_changed = 0
    lines_added = 0
    lines_deleted = 0
    for line in output.splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 2:
            continue
        files_changed += 1
        added_raw, deleted_raw = parts[0], parts[1]
        if added_raw.isdigit():
            lines_added += int(added_raw)
        if deleted_raw.isdigit():
            lines_deleted += int(deleted_raw)

    if files_changed == 0 and lines_added == 0 and lines_deleted == 0:
        return

    emit_diff_summary_recorded(
        mission_id=mission_id,
        base_ref=base_ref,
        head_ref=head_ref,
        files_changed=files_changed,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        phase_name=phase_name,
        source="git-numstat",
    )


@dataclass
class _MergeRunState:
    """Shared mutable state threaded through the merge phase helpers (INV-3).

    Each phase takes this object, mutates the documented fields, and returns
    None; ``_run_lane_based_merge_locked`` becomes the linear phase caller.
    """

    # Inputs / identity
    main_repo: Path
    mission_slug: str
    canonical_id: str  # for path-based workspace management; slug for legacy missions
    canonical_mission_id: str | None  # WP04/FR-004: ULID or None; for mission_id event fields only
    feature_dir: Path
    target_feature_dir: Path
    lanes_manifest: LanesManifest
    all_wp_ids: list[str]
    push: bool
    delete_branch: bool
    remove_worktree: bool
    strategy: MergeStrategy
    assume_yes: bool
    planning_artifact_only: bool

    # Loaded / derived during the run
    state: MergeState
    is_resume: bool
    any_lane_had_unintegrated_code: bool = False
    target_baseline_sha: str = "HEAD~1"
    baseline_mission_id: str | None = None
    done_marked_before_target: bool = False
    mission_already_applied: bool = False
    mission_number_meta_path: Path | None = None
    baseline_meta_path: Path | None = None
    stale_report: StaleAssertionReport | None = None

    # Paths
    canonical_events_path: Path | None = None
    canonical_status_path: Path | None = None
    merge_state_path: Path | None = None
    target_events_path: Path | None = None
    target_status_path: Path | None = None

    # Rollback snapshots
    pre_target_bookkeeping_snapshots: dict[Path, bytes | None] = field(default_factory=dict)
    final_bookkeeping_snapshots: dict[Path, bytes | None] = field(default_factory=dict)


def _phase_gates_and_state(run: _MergeRunState) -> None:
    """Banner, merge gates, and bootstrap/hollow-review history guards.

    The review-artifact consistency gate runs in ``_run_lane_based_merge_locked``
    BEFORE merge-state is created (so a rejected mission writes no state.json).
    """
    from specify_cli.policy.config import load_policy_config
    from specify_cli.policy.merge_gates import evaluate_merge_gates

    lanes_manifest = run.lanes_manifest

    if run.is_resume:
        console.print(
            f"[bold cyan]Resuming[/bold cyan] merge for {run.mission_slug} "
            f"({len(run.state.completed_wps)}/{len(run.state.wp_order)} WPs already done)"
        )

    console.print(f"[bold]Lane-based merge for {run.mission_slug}[/bold]")
    console.print(f"  Mission branch: {lanes_manifest.mission_branch}")
    console.print(f"  Lanes: {', '.join(ln.lane_id for ln in lanes_manifest.lanes)}")
    if run.planning_artifact_only:
        console.print(
            "  [dim]Planning-artifact-only mission: target branch already "
            "contains deliverables; branch merge steps will be skipped.[/dim]"
        )

    policy = load_policy_config(run.main_repo)
    gate_eval = evaluate_merge_gates(
        run.feature_dir,
        run.mission_slug,
        run.all_wp_ids,
        policy.merge_gates,
        run.main_repo,
    )
    for gate in gate_eval.gates:
        icon = "[green]✓[/green]" if gate.verdict == "pass" else "[yellow]⚠[/yellow]" if not gate.blocking else "[red]✗[/red]"
        console.print(f"  {icon} Gate {gate.gate_name}: {gate.details}")
    if not gate_eval.overall_pass:
        console.print("\n[red]Error:[/red] Merge gates failed.")
        raise typer.Exit(1)

    # -- Bootstrap-only canonical history guard (issue #1069) --
    _enforce_canonical_status_history(
        feature_dir=run.feature_dir,
        mission_slug=run.mission_slug,
        wp_ids=run.all_wp_ids,
    )
    _warn_or_confirm_hollow_reviews(
        feature_dir=run.feature_dir,
        wp_ids=run.all_wp_ids,
        assume_yes=run.assume_yes,
    )


def _phase_merge_lanes(run: _MergeRunState) -> None:
    """Merge each lane branch into the mission branch (skipping integrated lanes)."""
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.compute import is_planning_lane
    from specify_cli.lanes.merge import merge_lane_to_mission

    lanes_manifest = run.lanes_manifest
    for lane in lanes_manifest.lanes:
        if run.planning_artifact_only and is_planning_lane(lane):
            console.print(
                f"  [green]✓[/green] {lane.lane_id} already on {lanes_manifest.target_branch}"
            )
            continue

        # FR-037: skip ONLY when the lane branch is already fully integrated into
        # the mission branch (real tree state), never on the ``done`` proxy.
        _lane_branch = lane_branch_name(
            run.mission_slug,
            lane.lane_id,
            planning_base_branch=lanes_manifest.target_branch,
        )
        if not is_planning_lane(lane) and _lane_already_integrated(
            run.main_repo, _lane_branch, lanes_manifest.mission_branch
        ):
            console.print(
                f"  [dim]Skipping {lane.lane_id} (already integrated into "
                f"{lanes_manifest.mission_branch})[/dim]"
            )
            continue
        run.any_lane_had_unintegrated_code = True

        console.print(f"  [dim]Checking and merging {lane.lane_id}...[/dim]")
        lane_result = merge_lane_to_mission(run.main_repo, run.mission_slug, lane.lane_id, lanes_manifest)
        if lane_result.success:
            console.print(f"  [green]✓[/green] {lane.lane_id} → {lanes_manifest.mission_branch}")
        else:
            # T005: tolerate already-merged lanes on retry
            already_merged = any("already" in e.lower() or "up to date" in e.lower() or "ancestor" in e.lower() for e in lane_result.errors)
            if run.is_resume and already_merged:
                console.print(f"  [dim]{lane.lane_id} already merged, continuing[/dim]")
            else:
                for error in lane_result.errors:
                    console.print(f"  [red]✗[/red] {lane.lane_id}: {error}")
                raise typer.Exit(1)


def _phase_baseline_and_surface(run: _MergeRunState) -> None:
    """Capture target baseline SHA, resolve canonical mission_id + status surface paths."""
    lanes_manifest = run.lanes_manifest
    # -- Capture target baseline SHA for post-merge diff/review checks (T013) --
    _ret, target_baseline_sha, _err = run_command(
        ["git", "rev-parse", lanes_manifest.target_branch],
        capture=True,
        check_return=False,
        cwd=run.main_repo,
    )
    run.target_baseline_sha = target_baseline_sha.strip() if _ret == 0 else "HEAD~1"

    # -- Resolve the canonical mission_id (ULID) to gate modern-mission invariants --
    # FR (#2186): baseline identity is a PRIMARY_METADATA read. Route it onto the
    # PRIMARY anchor (``target_feature_dir`` is the pre-routed
    # ``primary_feature_dir_for_mission(_canonicalize_primary_read_handle(…))`` —
    # the SAME primary leg the :1000/:1022 identity reads use). Reading off the
    # coord-aware ``run.feature_dir`` STATUS leg lands on the meta-less / sentinel
    # ``-coord`` husk for a coord-topology mission → a None/wrong baseline id.
    # ``run.feature_dir`` stays the coord STATUS leg, untouched (C-001).
    try:
        run.baseline_mission_id = resolve_mission_identity(
            run.target_feature_dir
        ).mission_id
    except Exception:  # noqa: BLE001 — meta.json may be missing/corrupt for legacy missions
        run.baseline_mission_id = None

    status_surface_path = resolve_status_surface(run.main_repo, run.mission_slug)
    run.done_marked_before_target = (
        is_under_worktrees_segment(status_surface_path) and not run.planning_artifact_only
    )
    run.canonical_events_path = status_surface_path
    run.canonical_status_path = status_surface_path.parent / _STATUS_FILENAME
    run.merge_state_path = get_state_path(run.main_repo, run.state.mission_id)


def _phase_bake_and_pre_target_done(run: _MergeRunState) -> None:
    """Bake mission_number on the mission branch and pre-target done bookkeeping."""
    lanes_manifest = run.lanes_manifest
    if run.planning_artifact_only:
        console.print(
            f"  [dim]Skipping mission branch merge; {lanes_manifest.target_branch} "
            "is the planning artifact branch.[/dim]"
        )
        run.mission_already_applied = True
        return

    # -- WP10/T053/T055: assign dense integer mission_number on mission branch --
    _bake_mission_number_into_mission_branch(
        main_repo=run.main_repo,
        mission_slug=run.mission_slug,
        mission_branch=lanes_manifest.mission_branch,
        target_branch=lanes_manifest.target_branch,
        dry_run=False,
        merge_state=run.state,
    )

    if run.done_marked_before_target:
        assert run.canonical_events_path is not None
        assert run.canonical_status_path is not None
        assert run.merge_state_path is not None
        run.pre_target_bookkeeping_snapshots.update(
            _capture_bookkeeping_snapshots(
                run.main_repo,
                run.canonical_events_path,
                run.canonical_status_path,
                run.merge_state_path,
            )
        )
        # Modern coordination-backed missions must carry done events in the
        # mission branch before it is merged to target.
        try:
            _record_merged_wps_done_for_merge(
                main_repo=run.main_repo,
                feature_dir=run.feature_dir,
                mission_slug=run.mission_slug,
                lanes_manifest=lanes_manifest,
                target_branch=lanes_manifest.target_branch,
                merge_state=run.state,
                all_wp_ids=run.all_wp_ids,
            )
        except Exception:
            _restore_final_bookkeeping_snapshots(run.pre_target_bookkeeping_snapshots)
            raise


def _restore_pre_target_if_at_baseline(run: _MergeRunState) -> None:
    """Roll back the pre-target snapshots iff the target never advanced (INV-6).

    Behavior-preserving extraction of the repeated mission-to-target rollback
    guard (identical at every failure exit). Restores ONLY when done events were
    recorded pre-target AND the target branch still points at the pre-merge
    baseline — i.e. the mission→target merge made no progress.
    """
    if run.done_marked_before_target and _target_branch_still_at_baseline(
        run.main_repo,
        run.lanes_manifest.target_branch,
        run.target_baseline_sha,
    ):
        _restore_final_bookkeeping_snapshots(run.pre_target_bookkeeping_snapshots)


def _reject_zero_diff_noop_squash(run: _MergeRunState) -> None:
    """FR-037 fail-loud: refuse a zero-code no-op squash when lane work remains."""
    console.print(
        "[red]Error:[/red] Mission→target merge integrated zero lane "
        "diffs but un-integrated lane work remains. Refusing to report a "
        "zero-code squash as success (#1772 FR-037)."
    )
    console.print(
        f"  Mission branch: {run.lanes_manifest.mission_branch}; "
        f"target: {run.lanes_manifest.target_branch}. "
        "Inspect the lane branches and rerun, or `spec-kitty merge --abort`."
    )
    _restore_pre_target_if_at_baseline(run)
    raise typer.Exit(1)


def _handle_mission_merge_result(
    run: _MergeRunState,
    mission_result: MissionMergeResult,
    *,
    mission_integrated_into_target: bool,
) -> None:
    """Process the mission→target result: fail-loud / retry-tolerance / success log."""
    lanes_manifest = run.lanes_manifest
    run.mission_already_applied = getattr(mission_result, "already_applied", False) is True
    if (
        run.mission_already_applied
        and not run.planning_artifact_only
        and (run.any_lane_had_unintegrated_code or not mission_integrated_into_target)
    ):
        _reject_zero_diff_noop_squash(run)

    if not mission_result.success:
        # T005: tolerate already-merged on retry
        already_merged = any("already" in e.lower() or "up to date" in e.lower() for e in mission_result.errors)
        if run.is_resume and already_merged:
            console.print(f"[dim]{lanes_manifest.mission_branch} already merged into {lanes_manifest.target_branch}[/dim]")
        else:
            for error in mission_result.errors:
                console.print(f"[red]Error:[/red] {error}")
            _restore_pre_target_if_at_baseline(run)
            raise typer.Exit(1)
    else:
        console.print(f"\n[green]✓[/green] {lanes_manifest.mission_branch} → {lanes_manifest.target_branch}")
        if run.mission_already_applied:
            console.print("  [dim]Mission changes already present on target; continuing bookkeeping.[/dim]")
        if mission_result.commit:
            console.print(f"  Commit: {mission_result.commit[:7]}")


def _phase_mission_to_target(run: _MergeRunState) -> None:
    """Merge the mission branch into the target branch (honoring strategy)."""
    if run.planning_artifact_only:
        return

    from specify_cli.lanes.merge import merge_mission_to_target

    lanes_manifest = run.lanes_manifest
    # FR-037 (#1772 Bug 3): gate the no-op squash recovery on tree equivalence.
    _mission_integrated_into_target = _branch_trees_equal(
        run.main_repo,
        lanes_manifest.mission_branch,
        lanes_manifest.target_branch,
    )
    _allow_noop = run.is_resume and _mission_integrated_into_target
    console.print(f"  [dim]Merging mission branch into {lanes_manifest.target_branch}...[/dim]")
    try:
        mission_result = merge_mission_to_target(
            run.main_repo,
            run.mission_slug,
            lanes_manifest,
            strategy=run.strategy,
            allow_already_applied=_allow_noop,
        )
    except Exception:
        _restore_pre_target_if_at_baseline(run)
        raise
    _handle_mission_merge_result(
        run, mission_result, mission_integrated_into_target=_mission_integrated_into_target
    )


def _phase_capture_and_baseline(run: _MergeRunState) -> None:
    """Refresh checkout, capture final snapshots, plan mission_number, RECORD #1827 baseline."""
    # -- WP05/T006 FR-013: Post-merge working-tree refresh --
    _refresh_primary_checkout_after_merge(run.main_repo)

    assert run.canonical_events_path is not None
    assert run.canonical_status_path is not None
    assert run.merge_state_path is not None
    if not run.done_marked_before_target:
        run.final_bookkeeping_snapshots.update(
            _capture_bookkeeping_snapshots(
                run.main_repo,
                run.canonical_events_path,
                run.canonical_status_path,
                run.merge_state_path,
            )
        )
    target_events_path, target_status_path = _target_bookkeeping_status_paths(
        main_repo=run.main_repo,
        mission_slug=run.mission_slug,
        status_feature_dir=run.feature_dir,
    )
    target_meta_path = run.target_feature_dir / "meta.json"
    run.final_bookkeeping_snapshots.update(
        _capture_bookkeeping_snapshots(
            run.main_repo,
            target_events_path,
            target_status_path,
            target_meta_path,
        )
    )
    run.target_events_path = target_events_path
    run.target_status_path = target_status_path

    if run.planning_artifact_only:
        run.mission_number_meta_path = _assign_planning_only_mission_number_if_needed(
            run.main_repo,
            run.feature_dir,
        )

    # INV-5: record the #1827 baseline AFTER the target merge, BEFORE the
    # bookkeeping commit. On failure restore the final snapshots then exit.
    try:
        run.baseline_meta_path = _record_baseline_merge_commit(
            run.target_feature_dir,
            run.target_baseline_sha,
            mission_id=run.baseline_mission_id,
        )
    except BaselineMergeCommitError as exc:
        _restore_final_bookkeeping_snapshots(run.final_bookkeeping_snapshots)
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


def _phase_record_done_and_project(run: _MergeRunState) -> None:
    """Mark WPs done (post-target path) and project status bookkeeping to target."""
    lanes_manifest = run.lanes_manifest
    # -- T001: Mark WPs done with per-WP state tracking --
    if not run.done_marked_before_target:
        try:
            _record_merged_wps_done_for_merge(
                main_repo=run.main_repo,
                feature_dir=run.feature_dir,
                mission_slug=run.mission_slug,
                lanes_manifest=lanes_manifest,
                target_branch=lanes_manifest.target_branch,
                merge_state=run.state,
                all_wp_ids=run.all_wp_ids,
            )
        except Exception:
            _restore_final_bookkeeping_snapshots(run.final_bookkeeping_snapshots)
            raise

    try:
        target_events_path, target_status_path = _project_status_bookkeeping_to_target(
            main_repo=run.main_repo,
            mission_slug=run.mission_slug,
            status_feature_dir=run.feature_dir,
        )
    except Exception:
        _restore_final_bookkeeping_snapshots(run.final_bookkeeping_snapshots)
        raise
    run.target_events_path = target_events_path
    run.target_status_path = target_status_path


def _phase_porcelain_invariant(run: _MergeRunState) -> None:
    """WP05/T007 FR-014: post-merge working-tree invariant before the housekeeping commit."""
    _ret_status, _out_status = _raw_porcelain_status(run.main_repo)
    if _ret_status != 0:
        console.print(
            "[yellow]Warning:[/yellow] post-merge invariant check skipped: "
            f"git status --porcelain returned {_ret_status}"
        )
        return

    expected_paths: set[str] = set()
    if run.baseline_meta_path is not None:
        expected_paths.add(str(run.baseline_meta_path.relative_to(run.main_repo)))
    if run.mission_number_meta_path is not None:
        expected_paths.add(str(run.mission_number_meta_path.relative_to(run.main_repo)))

    def _is_coord_residue(path_part: str) -> bool:
        return is_coordination_artifact_residue_path(
            path_part, mission_slug=run.mission_slug
        )

    offending_lines, _skipped_untracked = _classify_porcelain_lines(
        (_out_status or "").splitlines(),
        expected_paths,
        residue_predicate=_is_coord_residue,
    )
    if not offending_lines:
        return

    console.print(
        "[red]Error:[/red] Post-merge working-tree invariant violated. "
        "The following paths diverge from HEAD unexpectedly:"
    )
    for line in offending_lines:
        console.print(f"  {line}")
    deleted_or_modified = any(
        len(line) >= 2 and (line[1] in ("D", "M") or line[0] in ("D", "M"))
        for line in offending_lines
    )
    if deleted_or_modified:
        console.print(
            "\nThis may indicate a sparse-checkout or filter-driver issue. Run\n"
            "  spec-kitty doctor sparse-checkout --fix\n"
            "before retrying the merge."
        )
    else:
        console.print(
            "\nUnexpected working-tree state after merge. "
            "Run `git status` to investigate before retrying."
        )
    _restore_final_bookkeeping_snapshots(run.final_bookkeeping_snapshots)
    raise typer.Exit(1)


def _phase_commit_and_assert(run: _MergeRunState) -> None:
    """INV-5: bookkeeping safe_commit → done-on-target assert → baseline assert (post-commit)."""
    lanes_manifest = run.lanes_manifest
    assert run.target_events_path is not None
    assert run.target_status_path is not None
    # -- T012: FR-019 — Persist done events to git BEFORE any worktree removal --
    files_to_commit = [run.target_events_path, run.target_status_path]
    if run.mission_number_meta_path is not None:
        files_to_commit.append(run.mission_number_meta_path)
    if run.baseline_meta_path is not None:
        files_to_commit.append(run.baseline_meta_path)
    files_to_commit = list(dict.fromkeys(files_to_commit))

    has_bookkeeping_changes = _paths_have_status_changes(run.main_repo, files_to_commit)
    if has_bookkeeping_changes:
        try:
            commit_merge_bookkeeping(
                repo_root=run.main_repo,
                worktree_root=run.main_repo,
                branch=lanes_manifest.target_branch,
                message=f"chore({run.mission_slug}): record done transitions for merged WPs",
                paths=tuple(files_to_commit),
            )
        except Exception as exc:
            if not (isinstance(exc, SafeCommitRecoveryFailed) and exc.commit_sha is not None):
                _restore_final_bookkeeping_snapshots(run.final_bookkeeping_snapshots)
            raise
    else:
        console.print("  [dim]No post-merge bookkeeping changes to commit; continuing cleanup.[/dim]")

    _assert_merged_wps_done_on_target(
        run.main_repo,
        run.mission_slug,
        lanes_manifest.target_branch,
        run.all_wp_ids,
        feature_dir=run.feature_dir,
        mission_id=run.baseline_mission_id,
    )

    # -- Post-merge baseline invariant (assert AFTER the commit landed) --
    try:
        _assert_baseline_merge_commit_on_target(
            run.main_repo,
            run.mission_slug,
            lanes_manifest.target_branch,
            run.target_baseline_sha,
            feature_dir=run.target_feature_dir,
            mission_id=run.baseline_mission_id,
        )
    except BaselineMergeCommitError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


def _phase_dossier_and_stale(run: _MergeRunState) -> None:
    """Dossier sync + stale-assertion advisory scan (failures never abort)."""
    console.print("  [dim]Syncing dossier state for the merged mission...[/dim]")
    trigger_feature_dossier_sync_if_enabled(
        run.feature_dir,
        run.mission_slug,
        run.main_repo,
    )

    console.print("  [dim]Running stale-assertion check...[/dim]")
    try:
        run.stale_report = run_check(
            base_ref=run.target_baseline_sha,
            head_ref="HEAD",
            repo_root=run.main_repo,
        )
    except Exception as exc:  # noqa: BLE001 — stale-assertion check is advisory; a failure must never abort an otherwise-successful merge
        logger.warning("Stale-assertion check failed: %s", exc)
        run.stale_report = None


def _phase_push(run: _MergeRunState) -> None:
    """Push the target branch to origin when requested (and a remote exists)."""
    lanes_manifest = run.lanes_manifest
    if not (run.push and has_remote(run.main_repo)):
        return
    _ret_push, _out_push, stderr_push = run_command(
        ["git", "push", "origin", lanes_manifest.target_branch],
        capture=True,
        check_return=False,
        cwd=run.main_repo,
    )
    if _ret_push != 0:
        if _is_linear_history_rejection(stderr_push):
            _emit_remediation_hint(console)
        console.print(f"[red]Error:[/red] Push failed: {stderr_push.strip() or _out_push.strip()}")
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] Pushed {lanes_manifest.target_branch} to origin")


def _phase_cleanup_worktrees_and_branches(run: _MergeRunState) -> None:
    """Worktree removal + lane/mission branch deletion + coordination teardown."""
    from specify_cli.lanes.branch_naming import lane_branch_name, worktree_dir_name, worktree_path
    from specify_cli.lanes.compute import is_planning_lane
    from specify_cli.workspace import delete_context

    lanes_manifest = run.lanes_manifest
    # -- T005: Worktree removal with retry tolerance and macOS FSEvents delay --
    if run.remove_worktree:
        delay = _worktree_removal_delay()
        for idx, lane in enumerate(lanes_manifest.lanes):
            wt_path = worktree_path(
                run.main_repo,
                run.mission_slug,
                mission_id=run.baseline_mission_id,
                lane_id=lane.lane_id,
            )
            if wt_path.exists():
                run_command(
                    ["git", "worktree", "remove", str(wt_path), "--force"],
                    cwd=run.main_repo,
                    check_return=False,
                )
                console.print(f"  Removed worktree: {wt_path.name}")
                if delay > 0 and idx < len(lanes_manifest.lanes) - 1:
                    time.sleep(delay)
            else:
                logger.debug("Worktree %s does not exist, skipping removal", wt_path)

        # FR-005/LC-6 (#1842 WP03): tombstone each lane's workspace-context
        # JSON when its worktree is removed at merge completion. The tombstone
        # is deliberately nested under ``remove_worktree``: the context JSON
        # *describes* the worktree, so the two are torn down together — a
        # ``--no-remove-worktree`` merge intentionally keeps BOTH the worktree
        # and its context (never orphaning one from the other).
        # ``delete_context`` itself is a pure, order-independent unlink — it
        # targets the legacy ``<slug>-<lane>`` filename ``save_context`` always
        # writes (mission_id=None, matching the workspace/context.py grammar),
        # and silently no-ops for a lane that never saved a context (e.g. a
        # planning-artifact lane) or one already tombstoned.
        for lane in lanes_manifest.lanes:
            workspace_name = worktree_dir_name(run.mission_slug, mission_id=None, lane_id=lane.lane_id)
            delete_context(run.main_repo, workspace_name)

    # -- T005: Branch deletion with retry tolerance --
    if run.delete_branch:
        for lane in lanes_manifest.lanes:
            if is_planning_lane(lane):
                continue
            branch_name = lane_branch_name(run.mission_slug, lane.lane_id)
            ret, _, _ = run_command(
                ["git", "rev-parse", "--verify", f"refs/heads/{branch_name}"],
                capture=True,
                check_return=False,
                cwd=run.main_repo,
            )
            if ret == 0:
                run_command(
                    ["git", "branch", "-D", branch_name],
                    cwd=run.main_repo,
                    check_return=False,
                )
            else:
                logger.debug("Branch %s does not exist, skipping deletion", branch_name)

        ret, _, _ = run_command(
            ["git", "rev-parse", "--verify", f"refs/heads/{lanes_manifest.mission_branch}"],
            capture=True,
            check_return=False,
            cwd=run.main_repo,
        )
        if ret == 0:
            run_command(
                ["git", "branch", "-D", lanes_manifest.mission_branch],
                cwd=run.main_repo,
                check_return=False,
            )
        else:
            logger.debug("Mission branch %s does not exist, skipping deletion", lanes_manifest.mission_branch)
        console.print(f"  Cleaned up {len(lanes_manifest.lanes)} lane branch(es) + mission branch")

    # -- WP07 / FR-016 / SC-10: Coordination worktree teardown --
    #
    # The shared ``teardown_coordination_topology`` seam (FR-004) persists the
    # retrospective to its durable home BEFORE destroying the worktree
    # (persist-before-destroy, FR-005), then performs the idempotent worktree
    # removal that safely no-ops for legacy missions that never created a
    # coordination worktree (FR-017). Without this seam, the coordination
    # worktree is destroyed here while ``run_retrospective_postcondition`` fires
    # only afterwards in the outer ``merge()`` — the merge-path destroy-before-
    # persist ordering bug. Destroy stays best-effort inside the seam; persist
    # runs OUTSIDE that swallow.
    if run.remove_worktree:
        from specify_cli.coordination.teardown import teardown_coordination_topology
        from specify_cli.mission_metadata import load_meta as _load_meta

        _meta_for_teardown = _load_meta(run.feature_dir)
        _mid8_for_teardown = (
            str(_meta_for_teardown.get("mid8", "")).strip()
            if isinstance(_meta_for_teardown, dict)
            else ""
        )
        teardown_coordination_topology(
            run.main_repo,
            run.mission_slug,
            _mid8_for_teardown,
        )
        logger.debug(
            "Coordination topology teardown for %s-%s completed",
            run.mission_slug,
            _mid8_for_teardown,
        )


def _phase_finalize_and_summary(run: _MergeRunState) -> None:
    """Cleanup workspace + clear state, emit diff summary / mission-closed, render stale findings."""
    # -- T002: Cleanup workspace (preserves state.json) then clear state --
    cleanup_merge_workspace(run.canonical_id, run.main_repo)
    clear_state(run.main_repo, run.canonical_id)

    # WP04/FR-004: use canonical_mission_id (ULID or None) for mission_id event
    # fields — never canonical_id which may be the slug for legacy missions.
    _emit_merge_diff_summary(
        repo_root=run.main_repo,
        mission_id=run.canonical_mission_id,
        base_ref=run.target_baseline_sha,
    )

    emit_mission_closed(
        mission_slug=run.mission_slug,
        total_wps=len(run.all_wp_ids),
        mission_id=run.canonical_mission_id,
    )

    _render_stale_findings(run.stale_report)


def _render_stale_findings(stale_report: StaleAssertionReport | None) -> None:
    """Render the stale-assertion findings block in the merge summary (T013/T023)."""
    console.print("\n[bold]Stale assertion findings:[/bold]")
    if stale_report is None:
        console.print("  [yellow]Stale-assertion check could not run.[/yellow]")
        return
    if not stale_report.findings:
        console.print("  No likely-stale assertions detected.")
        return

    actionable = [f for f in stale_report.findings if f.confidence in ("high", "medium")]
    low_grade = [f for f in stale_report.findings if f.confidence == "low"]
    info_grade = [f for f in stale_report.findings if f.confidence == "info"]

    for finding in actionable:
        console.print(
            f"  [{finding.confidence}] {finding.test_file.name}:{finding.test_line} — {finding.hint}"
        )
    for finding in low_grade:
        console.print(
            f"  [{finding.confidence}] {finding.test_file.name}:{finding.test_line} — {finding.hint}"
        )
    if info_grade:
        console.print(
            f"  Note: {len(info_grade)} message-content assertion(s) skipped "
            "(info grade) — review manually if diagnostic text changed."
        )


def _run_lane_based_merge_locked(
    main_repo: Path,
    mission_slug: str,
    canonical_id: str,
    canonical_mission_id: str | None,
    feature_dir: Path,
    lanes_manifest: LanesManifest,
    *,
    push: bool,
    delete_branch: bool,
    remove_worktree: bool,
    strategy: MergeStrategy = MergeStrategy.SQUASH,
    assume_yes: bool = False,
) -> None:
    """Inner merge flow, called with the global merge lock held.

    Linear phase caller: each phase mutates the shared :class:`_MergeRunState`.
    The #1827 ordering (INV-5) and the snapshot-restore-on-exception sites (INV-6)
    are preserved exactly within and across the phase boundaries.
    """
    from specify_cli.lanes.compute import is_planning_artifact_only

    target_feature_dir = primary_feature_dir_for_mission(
        main_repo,
        _canonicalize_primary_read_handle(main_repo, mission_slug),
    )
    all_wp_ids = [wp for lane in lanes_manifest.lanes for wp in lane.wp_ids]
    planning_artifact_only = is_planning_artifact_only(lanes_manifest)

    # INV (ordering preserved from the pre-refactor monolith): the review-artifact
    # consistency gate runs BEFORE merge-state is loaded/created, so a rejected
    # mission fails without ever writing state.json (regression: schema preflight
    # must not write merge state).
    _enforce_review_artifact_consistency(
        repo_root=main_repo,
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_ids=all_wp_ids,
    )

    state, is_resume = _load_or_create_merge_state(
        main_repo=main_repo,
        mission_slug=mission_slug,
        canonical_id=canonical_id,
        target_branch=lanes_manifest.target_branch,
        wp_order=all_wp_ids,
        push_requested=push,
    )

    run = _MergeRunState(
        main_repo=main_repo,
        mission_slug=mission_slug,
        canonical_id=canonical_id,
        canonical_mission_id=canonical_mission_id,
        feature_dir=feature_dir,
        target_feature_dir=target_feature_dir,
        lanes_manifest=lanes_manifest,
        all_wp_ids=all_wp_ids,
        push=push,
        delete_branch=delete_branch,
        remove_worktree=remove_worktree,
        strategy=strategy,
        assume_yes=assume_yes,
        planning_artifact_only=planning_artifact_only,
        state=state,
        is_resume=is_resume,
    )

    _phase_gates_and_state(run)
    _phase_merge_lanes(run)
    _phase_baseline_and_surface(run)
    _phase_bake_and_pre_target_done(run)
    _phase_mission_to_target(run)
    _phase_capture_and_baseline(run)
    _phase_record_done_and_project(run)
    _phase_porcelain_invariant(run)
    _phase_commit_and_assert(run)
    _phase_dossier_and_stale(run)
    _phase_push(run)
    _phase_cleanup_worktrees_and_branches(run)
    _phase_finalize_and_summary(run)


def _run_lane_based_merge(
    repo_root: Path,
    mission_slug: str,
    *,
    push: bool,
    delete_branch: bool,
    remove_worktree: bool,
    target_override: str | None = None,
    strategy: MergeStrategy = MergeStrategy.SQUASH,
    allow_sparse_checkout: bool = False,
    assume_yes: bool = False,
) -> None:
    """Execute the lane-only merge flow with MergeState lifecycle for recovery.

    Args:
        repo_root: Repository root.
        mission_slug: Feature slug.
        push: Push to origin after merge.
        delete_branch: Delete lane branches after merge.
        remove_worktree: Remove lane worktrees after merge.
        target_override: Override target branch.
        strategy: Merge strategy for the mission→target step (FR-005, FR-006).
            Lane→mission step always uses merge commits regardless of this value.
        allow_sparse_checkout: When True, bypass the sparse-checkout preflight
            (FR-008). The commit-layer backstop (WP01) still fires under this
            override — it is NOT disabled by this flag. Use of this override is
            logged via ``require_no_sparse_checkout``.
    """
    main_repo = get_main_repo_root(repo_root)
    # STATUS leg (C-001 / KEEP): ``feature_dir`` is threaded into
    # ``_run_lane_based_merge_locked`` as ``run.feature_dir`` and feeds the
    # coord-aware STATUS legs (``status_feature_dir``). It MUST stay on the
    # topology-aware resolver so the append-only event log resolves the coord
    # worktree for a coord-topology mission.
    feature_dir = candidate_feature_dir_for_mission(main_repo, mission_slug)
    # PRIMARY-partition reads (FR-002 #2185), routed per-leg DIRECTLY (NOT threaded
    # from the ``:887`` ``target_feature_dir`` anchor in the *locked* function): the
    # mission identity (PRIMARY_METADATA) and ``lanes.json`` (LANE_STATE) live ONLY
    # on the PRIMARY checkout post-#2106. Reading them off the coord-aware
    # ``feature_dir`` above lands on the STATUS-only husk → a missing/sentinel
    # ``meta.json`` and an absent ``lanes.json``. Resolve each by its real kind.
    primary_meta_dir = resolve_planning_read_dir(
        main_repo, mission_slug, kind=MissionArtifactKind.PRIMARY_METADATA
    )
    lanes_read_dir = resolve_planning_read_dir(
        main_repo, mission_slug, kind=MissionArtifactKind.LANE_STATE
    )

    # -- WP05/T020/FR-006: Sparse-checkout preflight (BEFORE any state change) --
    _preflight_mission_id: str | None = None
    try:
        _preflight_identity = resolve_mission_identity(primary_meta_dir)
        _preflight_mission_id = _preflight_identity.mission_id
    except Exception:  # noqa: BLE001 — meta.json may be missing for legacy missions
        _preflight_mission_id = None

    require_no_sparse_checkout(
        repo_root=main_repo,
        command="spec-kitty merge",
        override_flag=allow_sparse_checkout,
        actor=_resolve_merge_actor(main_repo),
        mission_slug=mission_slug,
        mission_id=_preflight_mission_id,  # WP04: str | None; slug fallback removed
    )

    from specify_cli.lanes.compute import is_planning_artifact_only

    lanes_manifest = require_lanes_json(lanes_read_dir)
    if target_override:
        lanes_manifest.target_branch = target_override
    planning_artifact_only = is_planning_artifact_only(lanes_manifest)

    # -- Resolve canonical mission_id from meta.json (WP04/FR-004) --
    identity = resolve_mission_identity(primary_meta_dir)
    # canonical_mission_id: ULID or None (for mission_id event fields; slug never written here).
    # canonical_id: for path-based workspace management — explicit slug fallback for
    # legacy missions without a backfilled ULID (NOT a mission_id field value).
    canonical_mission_id = identity.mission_id
    canonical_id = identity.mission_id if identity.mission_id is not None else mission_slug

    effective_push = _effective_push_requested(main_repo, canonical_id, push)
    if effective_push:
        _enforce_target_branch_sync_preflight(
            main_repo,
            target_branch=lanes_manifest.target_branch,
            mission_slug=mission_slug,
            mission_branch=lanes_manifest.mission_branch,
            mission_id=_preflight_mission_id,
        )

    if planning_artifact_only:
        _enforce_planning_artifact_target_branch(
            main_repo,
            lanes_manifest.target_branch,
        )
    else:
        branch_ok, branch_blocker = _check_mission_branch(
            mission_slug,
            main_repo,
            expected_branch=lanes_manifest.mission_branch,
            mission_id=_preflight_mission_id,
        )
        if not branch_ok:
            assert branch_blocker is not None
            console.print(
                "[red]Error:[/red] Missing mission branch: "
                f"{branch_blocker['expected_branch']}. "
                f"Run: {branch_blocker['remediation']}"
            )
            raise typer.Exit(1)

    # -- Acquire global merge lock to serialize concurrent merges --
    if not acquire_merge_lock(_GLOBAL_MERGE_LOCK_ID, main_repo):
        raise MergeLockError(
            _GLOBAL_MERGE_LOCK_ID,
            main_repo / KITTIFY_DIR / "runtime" / "merge" / _GLOBAL_MERGE_LOCK_ID / "lock",
        )

    try:
        _run_lane_based_merge_locked(
            main_repo=main_repo,
            mission_slug=mission_slug,
            canonical_id=canonical_id,
            canonical_mission_id=canonical_mission_id,
            feature_dir=feature_dir,
            lanes_manifest=lanes_manifest,
            push=effective_push,
            delete_branch=delete_branch,
            remove_worktree=remove_worktree,
            strategy=strategy,
            assume_yes=assume_yes,
        )
    finally:
        release_merge_lock(_GLOBAL_MERGE_LOCK_ID, main_repo)


__all__ = [
    "_run_lane_based_merge",
    "_run_lane_based_merge_locked",
    "_emit_merge_diff_summary",
    "_MergeRunState",
]
