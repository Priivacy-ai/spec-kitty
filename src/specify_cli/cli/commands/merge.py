"""Merge command implementation.

Lane worktrees are the only supported execution topology. Merge always follows
the same two-step flow:
1. Merge each lane branch into the mission branch.
2. Merge the mission branch into the target branch.

Planning-artifact-only missions are the exception: their artifacts are already
committed to the target branch, so merge performs closeout bookkeeping directly
on that target branch without requiring a mission branch.

Recovery semantics (WP01 / 067):
- MergeState is created at merge start and updated after each WP mark-done.
- On interruption, rerunning ``merge`` detects the existing state and resumes.
- ``--resume`` explicitly triggers resume; ``--abort`` cleans up state and exits.
- ``cleanup_merge_workspace`` preserves state.json so recovery works.
- ``clear_state`` is called only after confirmed full completion.
"""

# ─────────────────────────────────────────────────────────────────────────────
# #2057 DECOMPOSITION SHIM (matches the #2056 / #1623 convention).
#
# This module is the thin Typer command-registration shim for ``spec-kitty
# merge``. The former ~3383-LOC / maxCC-102 god-module was decomposed into
# cohesive, independently-tested seams under ``specify_cli/merge/``:
#
#   _constants.py            shared literals / type aliases / logger
#   git_probes.py            branch/tree/porcelain git primitives (+ public
#                            ``path_is_under_worktrees``)
#   resolve.py               slug / merge-state / target-branch resolution
#   preflight.py             git / target / mission-branch / canonical-status /
#                            review-artifact / hollow-review preflights
#   push_preflight.py        publish-layer push/target-sync preflight (#1706)
#   forecast.py              ``--dry-run`` preview + JSON/human payload build
#   ordering.py              mission-number bake cluster (+ merge ordering)
#   done_bookkeeping.py      done/approved emission + done asserts + reconcile
#   bookkeeping_projection.py status-surface trust + snapshot/restore + projection
#   executor.py              ``_run_lane_based_merge[_locked]`` + the phase helpers
#
# RULES (do NOT regress):
#   * This shim owns ONLY the ``merge`` command, its dispatch helpers, and the
#     re-export ``__all__`` (kept byte-stable so the 3 src consumers +
#     ~41 importing test files need zero edits — INV-4 / FR-006).
#   * One-way imports: seams never import this shim (no cycles — C-006/INV-2).
#   * Extract new responsibilities into a seam; never grow this module.
#
# De-godding effort: https://github.com/Priivacy-ai/spec-kitty/issues/2057
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations


from specify_cli.core.constants import KITTIFY_DIR
from specify_cli.missions._read_path_resolver import (
    candidate_feature_dir_for_mission,
)
import json
from typing import TYPE_CHECKING

import typer

from specify_cli import __version__ as SPEC_KITTY_VERSION
from specify_cli.cli.helpers import console, show_banner
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.paths import get_main_repo_root
from specify_cli.git.sparse_checkout import (
    SparseCheckoutPreflightError,
)
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError
from specify_cli.merge.baseline import (
    BaselineMergeCommitError,
    _read_committed_meta_json,
    _recorded_baseline_from_working_meta,
    assert_baseline_merge_commit_on_target as _assert_baseline_merge_commit_on_target,
    record_baseline_merge_commit as _record_baseline_merge_commit,
)
from specify_cli.merge.config import MergeStrategy, load_merge_config
# WP02 (#2057): shared literals/type-aliases/logger live in the merge seam's
# ``_constants`` module so later seams import them from one home (S1192-safe).
# Re-imported here (and re-exported via ``__all__``) so the public surface and
# every importer stay byte-stable (FR-003, C-008, INV-8).
from specify_cli.merge._constants import (
    HollowReviewWarnings,
    LINEAR_HISTORY_REJECTION_TOKENS,
    MissionBranchBlocker,
    TARGET_BRANCH_NOT_SYNCHRONIZED,
    TARGET_BRANCH_SYNC_INVARIANT,
    _SAFE_PATH_SEGMENT_DIAGNOSTIC,
    _STATUS_EVENTS_FILENAME,
    _STATUS_FILENAME,
    logger,
)
# WP03 (#2057): low-level git probes/primitives live in the merge seam's
# ``git_probes`` module. Re-imported here (and re-exported via ``__all__``) so
# external consumers (doctor.py, agent/mission.py) and ~41 test files keep
# importing them — esp. the PUBLIC ``path_is_under_worktrees`` — with zero edits
# (FR-006, C-006). One-way import: ``git_probes`` never imports this shim.
from specify_cli.merge.git_probes import (
    _branch_trees_equal,
    _classify_porcelain_lines,
    _emit_remediation_hint,
    _has_branch_ref,
    _is_git_repo,
    _is_linear_history_rejection,
    _lane_already_integrated,
    _paths_have_status_changes,
    _raw_porcelain_status,
    _refresh_primary_checkout_after_merge,
    path_is_under_worktrees,
)
# WP06 (#2057): the merge --dry-run forecast (preview + payload build) lives in
# the merge seam's ``forecast`` module; the command body delegates to it.
from specify_cli.merge.forecast import run_dry_run_forecast
# WP08 (#2057): done/approved transition emission, the done asserts, resume
# reconcile, and the per-WP recording loop live in the merge seam's
# ``done_bookkeeping`` module. _mark_wp_merged_done + the asserts are re-exported
# from the shim so orchestrator_api/commands.py and tests import unchanged
# (FR-006). One-way import: ``done_bookkeeping`` never imports this shim.
from specify_cli.merge.done_bookkeeping import (
    _assert_merged_wps_done_on_target,
    _assert_merged_wps_reached_done,
    _has_transition_to,
    _mark_wp_merged_done,
    _reconcile_completed_wps_for_resume,
    _resolve_merge_actor,
)
# WP10 (#2057): the lane-based merge executor (the global-lock wrapper + the
# decomposed CC-102 locked driver + the diff-summary helper) lives in the merge
# seam's ``executor`` module. Re-imported here (and re-exported via __all__) so
# the command body + the test/integration-imported _run_lane_based_merge[_locked]
# / _emit_merge_diff_summary keep importing from the shim (FR-006). One-way
# import: ``executor`` never imports this shim.
from specify_cli.merge.executor import (
    _emit_merge_diff_summary,
    _run_lane_based_merge,
    _run_lane_based_merge_locked,
)
# WP09 (#2057): status-surface trust + final-bookkeeping snapshot/restore +
# coord->target projection live in the merge seam's ``bookkeeping_projection``
# module. Re-imported here (and re-exported via __all__) so test-imported trust /
# snapshot / projection symbols keep importing from the shim with zero edits
# (FR-006, INV-6). One-way import: the seam never imports this shim.
from specify_cli.merge.bookkeeping_projection import (
    _assert_bookkeeping_snapshot_path_is_trusted,
    _assert_status_path_within_target_surface,
    _assert_status_surface_path_is_trusted,
    _capture_bookkeeping_snapshots,
    _project_status_bookkeeping_to_target,
    _restore_final_bookkeeping_snapshots,
    _target_bookkeeping_status_paths,
    _target_branch_still_at_baseline,
    _validate_mission_slug_path_segment,
)
# WP04 (#2057): slug / merge-state / target-branch resolution lives in the merge
# seam's ``resolve`` module (consuming merge/state.py). Re-imported here (and
# re-exported via ``__all__``) so test-imported resolvers keep importing from
# the shim with zero edits (FR-006, C-002). One-way import: ``resolve`` never
# imports this shim.
from specify_cli.merge.resolve import (
    _cleanup_merge_workspaces_for_state,
    _clear_merge_state_for_mission,
    _load_merge_state_entry_for_mission,
    _load_merge_state_for_mission,
    _load_or_create_merge_state,
    _resolve_mission_slug,
    _resolve_target_branch,
)
# WP07 (#2057): the mission-number bake cluster lives in the merge seam's
# ``ordering`` module (next to assign_next_mission_number). Re-imported here so
# the shim body + the test-imported ``_bake_mission_number_into_mission_branch``
# (re-exported via __all__) keep working with zero edits (FR-006). Lazy imports
# inside the bake cluster stay lazy (C-007).
from specify_cli.merge.ordering import (
    _bake_mission_number_into_mission_branch,
)
# WP05 (#2057): git / target-branch / mission-branch / canonical-status /
# review-artifact / hollow-review preflights live in the merge seam's
# ``preflight`` module. Re-imported here (and re-exported via ``__all__``) so
# test-imported preflight symbols keep importing from the shim with zero edits
# (FR-006, C-002). One-way import: ``preflight`` never imports this shim.
from specify_cli.merge.preflight import (
    _check_mission_branch,
    _collect_hollow_review_warnings,
    _effective_push_requested,
    _enforce_canonical_status_history,
    _enforce_git_preflight,
    _enforce_planning_artifact_target_branch,
    _enforce_review_artifact_consistency,
    _validate_target_branch,
    _warn_or_confirm_hollow_reviews,
    target_branch_sync_remediation,
)
# WP05 (#2057): the push/target-sync preflight + its diagnostic payloads live in
# the publish-layer ``push_preflight`` module (domain ``preflight`` stays
# network-free, issue #1706). Re-exported for the test-imported surface.
from specify_cli.merge.push_preflight import (
    _enforce_target_branch_sync_preflight,
    _target_branch_sync_payload,
)
from specify_cli.merge.state import (
    abort_git_merge,
    clear_state,
    load_state,
)
from specify_cli.merge.workspace import get_merge_runtime_dir
from specify_cli.post_merge.retrospective_terminus import run_retrospective_postcondition
from specify_cli.task_utils import TaskCliError, find_repo_root
# WP05 (#2057): the git-ops primitive ``run_command`` and the git-preflight
# entrypoint ``run_git_preflight`` / payload builder
# ``build_git_preflight_failure_payload`` were relocated to ``core.git_ops`` /
# ``core.git_preflight`` by the decomposition. Re-imported here so the historical
# ``merge.<symbol>`` patch targets that ~several test modules monkeypatch keep
# resolving against the shim (FR-006, patch-target stability). Deliberately NOT
# in ``__all__``: ``__all__`` membership only affects ``from merge import *`` and
# nothing imports these FROM this shim, so listing them trips the dead-symbol
# gate. One-way import: the core modules never import this shim.
from specify_cli.core.git_ops import (
    run_command,  # noqa: F401 — re-exported as a monkeypatch target for tests/agent/test_commands.py + sparse-checkout integration tests; not part of the public *-import surface
)
from specify_cli.core.git_preflight import (
    build_git_preflight_failure_payload,  # noqa: F401 — re-exported as a monkeypatch target for the git-preflight tests; not part of the public *-import surface
    run_git_preflight,  # noqa: F401 — re-exported as a monkeypatch target for the git-preflight tests; not part of the public *-import surface
)

if TYPE_CHECKING:
    from pathlib import Path

    from specify_cli.merge.state import MergeState


def _resolve_slug_or_exit(repo_root: Path, mission: str | None, feature: str | None) -> str | None:
    """Resolve the operator-supplied mission/feature handle to a canonical slug.

    Shared by the abort/resume/main paths; raises ``typer.Exit(1)`` with the
    canonical path-segment diagnostic when the handle is traversal-unsafe.
    """
    mission_slug_raw = (mission or feature or "").strip() or None
    try:
        return _resolve_mission_slug(repo_root, mission_slug_raw)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {_SAFE_PATH_SEGMENT_DIAGNOSTIC}: {exc}")
        raise typer.Exit(1) from exc


def _teardown_coordination_for_abort(
    repo_root: Path,
    resolved: str | None,
    state_entry: tuple[str | None, MergeState] | None,
) -> None:
    """Best-effort coordination-worktree teardown during ``--abort`` (FR-016).

    Idempotent; a no-op for legacy missions without coordination state. Never
    raises — abort cleanup must leave the workspace in the same shape as a clean
    run even when teardown fails.
    """
    try:
        from specify_cli.coordination import CoordinationWorkspace
        from specify_cli.mission_metadata import load_meta as _load_meta

        main_for_abort = get_main_repo_root(repo_root)
        coord_slug = resolved
        if coord_slug is None and state_entry is not None:
            coord_slug = state_entry[1].mission_slug
        if not coord_slug:
            raise ValueError("cannot resolve mission slug for coordination cleanup")
        feature_dir = candidate_feature_dir_for_mission(main_for_abort, coord_slug)
        meta = _load_meta(feature_dir)
        mid8 = str(meta.get("mid8", "")).strip() if isinstance(meta, dict) else ""
        if mid8 and coord_slug:
            CoordinationWorkspace.teardown(main_for_abort, coord_slug, mid8)
    except Exception as exc:  # noqa: BLE001 — abort cleanup is best-effort
        logger.debug(
            "Coordination worktree teardown during --abort failed (non-fatal): %s", exc
        )


def _dispatch_abort(repo_root: Path, mission: str | None, feature: str | None) -> None:
    """Handle ``merge --abort``: clear state, locks, legacy files, git merge, coord."""
    from contextlib import suppress

    resolved = _resolve_slug_or_exit(repo_root, mission, feature)
    state_entry = _load_merge_state_entry_for_mission(repo_root, resolved)
    if state_entry is None and resolved is None:
        state_entry = _load_merge_state_entry_for_mission(repo_root, None)
    if state_entry is not None and resolved is None:
        resolved = state_entry[1].mission_slug

    if resolved or state_entry is not None:
        cleared = _clear_merge_state_for_mission(repo_root, resolved)
        if state_entry is not None:
            source_key, active_state = state_entry
            if source_key:
                cleared = clear_state(repo_root, source_key) or cleared
            cleared = clear_state(repo_root, active_state.mission_id) or cleared
        _cleanup_merge_workspaces_for_state(
            repo_root, mission_slug=resolved, state_entry=state_entry
        )
        _teardown_coordination_for_abort(repo_root, resolved, state_entry)
        if cleared:
            console.print(f"[green]Aborted[/green] merge for {resolved}. State and workspace cleaned up.")
        else:
            console.print(f"[yellow]No active merge state found for {resolved}.[/yellow] Workspace cleaned up.")
    else:
        cleared = clear_state(repo_root)
        if cleared:
            console.print("[green]Aborted[/green] merge. State cleaned up.")
        else:
            console.print("[yellow]No active merge state to abort.[/yellow]")

    # T002: Remove the global merge lock file (idempotent — a crash between lock
    # acquisition and release in _run_lane_based_merge leaves it behind).
    _global_lock_path = get_merge_runtime_dir("__global_merge__", repo_root) / "lock"
    with suppress(FileNotFoundError):
        _global_lock_path.unlink()
        console.print("[green]Removed merge lock.[/green]")

    # T003: Remove the legacy .kittify/merge-state.json (pre-mission-scoped releases).
    _legacy_state_path = repo_root / KITTIFY_DIR / "merge-state.json"
    with suppress(FileNotFoundError):
        _legacy_state_path.unlink()
        console.print("[green]Removed legacy merge-state.[/green]")

    # T004: If git itself is mid-merge (MERGE_HEAD present), abort that too.
    if abort_git_merge(repo_root):
        console.print("[green]Aborted in-progress git merge.[/green]")


def _dispatch_resume(repo_root: Path, mission: str | None, feature: str | None) -> str | None:
    """Handle ``merge --resume``: require interrupted state; return the mission slug.

    Returns the mission slug to thread into the main flow (the operator may have
    omitted ``--mission``, in which case the stored slug is adopted).
    """
    mission_slug_raw = (mission or feature or "").strip() or None
    resolved = _resolve_slug_or_exit(repo_root, mission, feature)
    existing_state = _load_merge_state_for_mission(repo_root, resolved)
    if existing_state is None:
        console.print("[red]Error:[/red] No interrupted merge to resume.")
        raise typer.Exit(1)
    console.print(
        f"[bold cyan]Resume requested[/bold cyan] for {existing_state.mission_slug} "
        f"({len(existing_state.completed_wps)}/{len(existing_state.wp_order)} done)"
    )
    return existing_state.mission_slug if not mission_slug_raw else mission


def _run_real_merge(
    repo_root: Path,
    *,
    resolved_feature: str,
    resolved_target_branch: str,
    resolved_strategy: MergeStrategy,
    delete_branch: bool,
    remove_worktree: bool,
    push: bool,
    allow_sparse_checkout: bool,
    yes: bool,
) -> None:
    """Run the real lane-based merge + post-merge retrospective / next-step hints."""
    try:
        _run_lane_based_merge(
            repo_root=repo_root,
            mission_slug=resolved_feature,
            push=push,
            delete_branch=delete_branch,
            remove_worktree=remove_worktree,
            target_override=resolved_target_branch,
            strategy=resolved_strategy,
            allow_sparse_checkout=allow_sparse_checkout,
            assume_yes=yes,
        )
    except SparseCheckoutPreflightError as exc:
        # WP05/T020: surface sparse-checkout preflight as a user-facing error and
        # exit non-zero WITHOUT writing any merge state.
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except (MissingLanesError, CorruptLanesError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    # -- Post-merge: WP07/FR-007 retrospective postcondition (fail-open) --
    run_retrospective_postcondition(mission_slug=resolved_feature, repo_root=repo_root)

    # -- Post-merge: suggest mission review + retrospective review/synthesis --
    console.print(
        "\n[cyan]Next:[/cyan] Run [bold]/spec-kitty-mission-review[/bold] "
        "to audit the merged mission for spec→code fidelity, drift, risks, and security."
    )
    console.print(
        "[cyan]Then, while context is fresh, review the retrospective that was"
        " captured at terminus:[/cyan]\n"
        "  [bold]spec-kitty retrospect summary[/bold] — cross-mission view\n"
        f"  [bold]spec-kitty agent retrospect synthesize --mission {resolved_feature}[/bold]"
        " — apply staged proposals (dry-run; add --apply to mutate)"
    )


@require_main_repo
def merge(
    strategy: MergeStrategy | None = typer.Option(
        None,
        "--strategy",
        help="Merge strategy for mission\u2192target step: merge | squash | rebase. Default: squash.",
    ),
    delete_branch: bool = typer.Option(True, "--delete-branch/--keep-branch", help="Delete lane branches after merge"),
    remove_worktree: bool = typer.Option(True, "--remove-worktree/--keep-worktree", help="Remove lane worktrees after merge"),
    push: bool = typer.Option(False, "--push", help="Push to origin after merge"),
    target_branch: str = typer.Option(None, "--target", help="Target branch to merge into (auto-detected)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
    json_output: bool = typer.Option(False, "--json", help="Output deterministic JSON (dry-run mode)"),
    mission: str = typer.Option(None, "--mission", help="Mission slug when merging from main branch"),
    feature: str = typer.Option(None, "--feature", hidden=True, help="Legacy alias for --mission"),
    resume: bool = typer.Option(False, "--resume", help="Resume an interrupted merge from the last incomplete WP"),
    abort: bool = typer.Option(False, "--abort", help="Abort an in-progress merge, cleaning up state and worktrees"),
    context_token: str = typer.Option(None, "--context", help="Unused compatibility flag"),
    keep_workspace: bool = typer.Option(False, "--keep-workspace", help="Unused compatibility flag"),
    allow_sparse_checkout: bool = typer.Option(
        False,
        "--allow-sparse-checkout",
        help=(
            "Proceed even if legacy sparse-checkout state is detected. "
            "Use of this override is logged. Does not bypass the commit-time "
            "data-loss backstop."
        ),
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Proceed after merge warnings without prompts"),
) -> None:
    """Merge a lane-based feature into its target branch."""
    del context_token, keep_workspace

    if not json_output:
        show_banner()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if abort:
        _dispatch_abort(repo_root, mission, feature)
        return

    if resume:
        mission = _dispatch_resume(repo_root, mission, feature)
        # Fall through to the normal merge flow which will detect the state.

    _enforce_git_preflight(repo_root, json_output=json_output)

    # T009 — FR-005/FR-006: Resolve strategy: CLI flag > config > default (SQUASH)
    resolved_strategy: MergeStrategy = strategy or load_merge_config(repo_root).strategy or MergeStrategy.SQUASH

    resolved_feature = _resolve_slug_or_exit(repo_root, mission, feature)

    # T004: Auto-detect existing state when running merge without --resume
    if not resume and resolved_feature:
        existing_state = load_state(repo_root, resolved_feature)
        if existing_state is not None and existing_state.remaining_wps:
            console.print(
                f"[bold cyan]Detected interrupted merge[/bold cyan] for {resolved_feature} "
                f"({len(existing_state.completed_wps)}/{len(existing_state.wp_order)} WPs done). "
                "Auto-resuming."
            )

    resolved_target_branch, target_source = _resolve_target_branch(repo_root, resolved_feature, target_branch)
    _validate_target_branch(
        repo_root,
        resolved_feature,
        resolved_target_branch,
        target_source,
        json_output=json_output,
    )

    if json_output and not dry_run:
        print(
            json.dumps(
                {
                    "spec_kitty_version": SPEC_KITTY_VERSION,
                    "error": "--json is currently supported with --dry-run only.",
                }
            )
        )
        raise typer.Exit(1)

    if dry_run:
        # WP06 (#2057): the dry-run preview + payload build lives in the
        # ``forecast`` seam. Behavior + JSON key set preserved byte-for-byte
        # (FR-001, FR-004); ``run_dry_run_forecast`` terminates the dry-run path.
        run_dry_run_forecast(
            repo_root=repo_root,
            resolved_feature=resolved_feature,
            resolved_target_branch=resolved_target_branch,
            resolved_strategy=resolved_strategy,
            delete_branch=delete_branch,
            remove_worktree=remove_worktree,
            push=push,
            json_output=json_output,
        )
        return

    if not resolved_feature:
        console.print("[red]Error:[/red] Mission slug could not be resolved. Use --mission <slug>.")
        raise typer.Exit(1)

    _run_real_merge(
        repo_root,
        resolved_feature=resolved_feature,
        resolved_target_branch=resolved_target_branch,
        resolved_strategy=resolved_strategy,
        delete_branch=delete_branch,
        remove_worktree=remove_worktree,
        push=push,
        allow_sparse_checkout=allow_sparse_checkout,
        yes=yes,
    )


__all__ = [
    "_has_transition_to",
    "_assert_merged_wps_reached_done",
    "_assert_merged_wps_done_on_target",
    "_reconcile_completed_wps_for_resume",
    "_assert_baseline_merge_commit_on_target",
    "_record_baseline_merge_commit",
    "_recorded_baseline_from_working_meta",
    "_read_committed_meta_json",
    "BaselineMergeCommitError",
    "_mark_wp_merged_done",
    "_project_status_bookkeeping_to_target",
    "_validate_mission_slug_path_segment",
    "_target_bookkeeping_status_paths",
    "_assert_status_path_within_target_surface",
    "_assert_status_surface_path_is_trusted",
    "_assert_bookkeeping_snapshot_path_is_trusted",
    "_capture_bookkeeping_snapshots",
    "_restore_final_bookkeeping_snapshots",
    "_target_branch_still_at_baseline",
    "_load_merge_state_for_mission",
    "_load_or_create_merge_state",
    "_clear_merge_state_for_mission",
    "_run_lane_based_merge",
    "_run_lane_based_merge_locked",
    "_emit_merge_diff_summary",
    "_classify_porcelain_lines",
    "_lane_already_integrated",
    "_raw_porcelain_status",
    "_paths_have_status_changes",
    "_resolve_merge_actor",
    "_refresh_primary_checkout_after_merge",
    "_effective_push_requested",
    "_enforce_canonical_status_history",
    "_enforce_planning_artifact_target_branch",
    "_warn_or_confirm_hollow_reviews",
    "_is_linear_history_rejection",
    "_emit_remediation_hint",
    "_branch_trees_equal",
    "_check_mission_branch",
    "_has_branch_ref",
    "_is_git_repo",
    "_enforce_target_branch_sync_preflight",
    "_enforce_review_artifact_consistency",
    "_collect_hollow_review_warnings",
    "_target_branch_sync_payload",
    "_bake_mission_number_into_mission_branch",
    "target_branch_sync_remediation",
    "TARGET_BRANCH_NOT_SYNCHRONIZED",
    "TARGET_BRANCH_SYNC_INVARIANT",
    "_STATUS_EVENTS_FILENAME",
    "_STATUS_FILENAME",
    "MissionBranchBlocker",
    "HollowReviewWarnings",
    "LINEAR_HISTORY_REJECTION_TOKENS",
    "path_is_under_worktrees",
    "merge",
]
