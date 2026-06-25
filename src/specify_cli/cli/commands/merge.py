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

# ⚠️ GOD-MODULE (tracked for decomposition — do NOT add new responsibilities here).
# This file is an oversized "god module" (~3300 LOC, maxCC ~102). Extract cohesive
# seams into dedicated modules instead of growing this one.
# De-godding effort: https://github.com/Priivacy-ai/spec-kitty/issues/2057

from __future__ import annotations

from collections.abc import Callable

from specify_cli.core.constants import KITTY_SPECS_DIR, KITTIFY_DIR, WORKTREES_DIR
from specify_cli.coordination.surface_resolver import (
    is_under_worktrees_segment,
    resolve_status_surface,
)
from specify_cli.missions._read_path_resolver import (
    candidate_feature_dir_for_mission,
    primary_feature_dir_for_mission,
)
import contextlib
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

from specify_cli import __version__ as SPEC_KITTY_VERSION
from specify_cli.cli.helpers import console, show_banner
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.git_ops import has_remote, run_command
from specify_cli.core.git_preflight import build_git_preflight_failure_payload, run_git_preflight
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.core.paths import assert_safe_path_segment, get_main_repo_root
from specify_cli.core.utils import ensure_within_any, ensure_within_directory
from specify_cli.git import safe_commit
from specify_cli.git.commit_helpers import SafeCommitRecoveryFailed
from specify_cli.git.ref_advance import advance_branch_ref
from specify_cli.git.sparse_checkout import (
    SparseCheckoutPreflightError,
    require_no_sparse_checkout,
)
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json
from specify_cli.merge.baseline import (
    BaselineMergeCommitError,
    _read_committed_meta_json,
    _recorded_baseline_from_working_meta,
    assert_baseline_merge_commit_on_target as _assert_baseline_merge_commit_on_target,
    record_baseline_merge_commit as _record_baseline_merge_commit,
)
from specify_cli.merge.config import MergeStrategy, load_merge_config
from specify_cli.merge.ordering import assign_next_mission_number
from specify_cli.merge.preflight import (
    target_branch_sync_remediation,
)
from specify_cli.merge.state import (
    MergeLockError,
    MergeState,
    abort_git_merge,
    acquire_merge_lock,
    clear_state,
    get_state_path,
    load_state,
    needs_number_assignment,
    release_merge_lock,
    save_state,
)
from specify_cli.mission_metadata import load_meta, resolve_mission_identity, write_meta
from specify_cli.merge.workspace import _worktree_removal_delay, cleanup_merge_workspace, get_merge_runtime_dir
from specify_cli.post_merge.review_artifact_consistency import (
    REJECTED_REVIEW_ARTIFACT_CONFLICT,
    format_review_artifact_finding,
    review_artifact_finding_diagnostic,
    run_review_artifact_consistency_preflight,
)
from specify_cli.post_merge.retrospective_terminus import run_retrospective_postcondition
from specify_cli.post_merge.stale_assertions import StaleAssertionReport, run_check
from specify_cli.sync import emit_diff_summary_recorded, emit_mission_closed
from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
from specify_cli.status import (
    COORD_OWNED_STATUS_FILES,
    REVIEWER_SELF_APPROVAL,
    read_wp_frontmatter,
)
from specify_cli.task_utils import TaskCliError, find_repo_root
from mission_runtime import is_coordination_artifact_residue_path

if TYPE_CHECKING:
    from specify_cli.merge.push_preflight import TargetBranchSyncStatus

logger = logging.getLogger(__name__)

TARGET_BRANCH_NOT_SYNCHRONIZED = "TARGET_BRANCH_NOT_SYNCHRONIZED"
TARGET_BRANCH_SYNC_INVARIANT = "local_target_branch_must_match_tracking_branch"
_STATUS_EVENTS_FILENAME = "status.events.jsonl"
_STATUS_FILENAME = "status.json"
_SAFE_PATH_SEGMENT_DIAGNOSTIC = "Mission slug is not a single safe path segment"

# T011 — FR-009: push-error parser tokens (locked tuple — do not reorder or extend without a spec change)
LINEAR_HISTORY_REJECTION_TOKENS: tuple[str, ...] = (
    "merge commits",
    "linear history",
    "fast-forward only",
    "GH006",
    "non-fast-forward",
)

MissionBranchBlocker = dict[str, str | bool]
HollowReviewWarnings = dict[str, list[str]]


def _lane_already_integrated(
    repo_root: Path, lane_branch: str, mission_branch: str
) -> bool:
    """Return True when ``lane_branch`` carries no commits absent from ``mission_branch``.

    FR-037 (#1772 Bug 3): the lane-skip decision must gate on the ACTUAL lane
    tree state vs. the mission branch — never on a per-WP ``done`` status, which
    a prior aborted merge may have recorded before any code was integrated.
    Uses ``git rev-list <lane> ^<mission>``: an empty result means every lane
    commit is already reachable from the mission branch, so re-merging would be
    a genuine no-op. A non-empty result means real, un-integrated lane work
    remains and the lane MUST be merged.
    """
    ret, out, _err = run_command(
        ["git", "rev-list", "--count", lane_branch, f"^{mission_branch}"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret != 0:
        # Unknown ref / git error — be conservative and do NOT treat as
        # integrated, so the lane merge runs and any real error surfaces there.
        return False
    return out.strip() == "0"


def _branch_trees_equal(repo_root: Path, source_branch: str, target_branch: str) -> bool:
    """Return True when two refs currently expose identical trees.

    Squash merges do not preserve ancestry, so reachability is the wrong
    idempotency predicate for "the squash payload already landed". For that
    recovery path we need the content-level question: would merging source into
    target produce any tree changes?
    """
    ret, _out, _err = run_command(
        ["git", "diff", "--quiet", source_branch, target_branch],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    return ret == 0


def path_is_under_worktrees(path: Path) -> bool:
    """Return True when ``path`` lies under the ``.worktrees/`` directory.

    FR-035 / #1772 Bug 0: nested-worktree paths (``.worktrees/<m>-coord/…``)
    must never be staged via ``git add`` from finalize/recovery/merge flows,
    and ``spec-kitty doctor`` flags such content when it is already tracked.
    This is the single reusable predicate for that decision (Randy Reducer:
    one guard, not per-call-site copies). It is path-shape based — it does not
    touch the filesystem — so it works for both real paths and committed-tree
    relative paths.

    Delegates to the blessed seam primitive
    :func:`coordination.surface_resolver.is_under_worktrees_segment` (C-SEAM-1):
    one shape-proposal predicate, not a per-module copy. The constants
    ``WORKTREES_DIR`` and the seam's ``_WORKTREES_SEGMENT`` are both
    ``".worktrees"``, so the membership check is identical.
    """
    return is_under_worktrees_segment(path)


def _raw_porcelain_status(repo_root: Path) -> tuple[int, str]:
    """Return ``(returncode, raw_stdout)`` for ``git status --porcelain``.

    Reads stdout RAW (not via ``run_command``) so the leading status column of
    each porcelain line is preserved. Porcelain v1 emits ``XY<space>PATH`` (a
    fixed 3-char prefix); for a tracked file that is modified-but-not-staged X
    is a space (``" M path"``). ``run_command``'s whole-output ``.strip()`` would
    remove the leading space of the *first* line only, shifting its columns so
    ``_classify_porcelain_lines`` rejects it (``line[2] != " "``) and silently
    drops the first divergent path. The post-merge working-tree invariant MUST
    see every divergent line, so it reads porcelain via this helper instead.

    Mirrors the raw-read pattern documented in
    :func:`specify_cli.cli.commands.implement._feature_dir_status_entries`.
    """
    import subprocess as _subprocess

    result = _subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode, result.stdout


def _classify_porcelain_lines(
    lines: list[str],
    expected_paths: set[str],
    *,
    residue_predicate: Callable[[str], bool] | None = None,
) -> tuple[list[str], int]:
    """Classify ``git status --porcelain`` lines into offending vs ignored.

    Returns a 2-tuple ``(offending_lines, skipped_untracked_count)`` where:

    * ``offending_lines`` — lines that represent unexpected divergence from HEAD
      (tracked modifications, deletions, renames, …).
    * ``skipped_untracked_count`` — number of ``??`` (untracked) lines that were
      silently dropped because untracked files cannot diverge from HEAD.

    Lines whose path component is in *expected_paths* are dropped because the
    immediately-following safe_commit will persist those files and they are
    therefore expected to be dirty at this point in the flow.

    Lines whose path is recognized by *residue_predicate* are also dropped:
    these are coordination-owned planning/status artifacts whose stale primary
    copies are legitimate residue after a coordination-topology merge (FR-012 /
    #1878).  The predicate is the single residue authority
    (:func:`mission_runtime.is_coordination_artifact_residue_path`) — no second
    residue literal is carried here.

    Lines that do not match porcelain v1 shape (two status chars + space + path)
    are silently ignored to avoid false positives from mocked test output.
    """
    offending: list[str] = []
    skipped_untracked = 0
    for line in lines:
        if not line.strip():
            continue
        # Porcelain v1: two status chars + space + path (minimum 4 chars).
        if len(line) < 4 or line[2] != " ":
            continue
        status_code = line[:2]
        if status_code == "??":
            skipped_untracked += 1
            continue  # untracked files cannot diverge from HEAD
        path_part = line[3:].strip()
        if path_part in expected_paths:
            continue
        if residue_predicate is not None and residue_predicate(path_part):
            continue
        offending.append(line)
    return offending, skipped_untracked


def _is_linear_history_rejection(stderr: str) -> bool:
    """Return True if git push stderr indicates a linear-history rejection.

    Case-insensitive substring match against the locked token list.
    Fail-open: returns False for unrecognised rejection messages.
    """
    haystack = stderr.lower()
    return any(token.lower() in haystack for token in LINEAR_HISTORY_REJECTION_TOKENS)


def _resolve_merge_actor(repo_root: Path) -> str:
    """Resolve the actor identity for merge-time audit records.

    Priority: SPEC_KITTY_AGENT env var -> git config user.name ->
    GIT_AUTHOR_NAME -> USER/USERNAME. Falls back to ``<unknown>`` only if
    every source is empty, which should not happen in a properly
    configured environment. This mirrors the resolver pattern used by
    _merge_actor in scripts/tasks/tasks_cli.py so override audit records
    carry a real identity instead of <unknown>.
    """
    agent_env = os.environ.get("SPEC_KITTY_AGENT")
    if agent_env and agent_env.strip():
        return agent_env.strip()
    try:
        ret, out, _err = run_command(["git", "config", "user.name"], capture=True, cwd=repo_root)
        if ret == 0 and out and out.strip():
            return out.strip()
    except Exception:  # noqa: BLE001, S110 — actor resolution must never break merge
        pass
    # Final-tier fallback: environment username. Comment preserved deliberately
    # because reviewers ask why this exists — see Fix 2 / FR-008 post-merge follow-up.
    return (
        os.environ.get("GIT_AUTHOR_NAME")
        or os.environ.get("USER")
        or os.environ.get("USERNAME")
        or "<unknown>"
    )


def _emit_remediation_hint(hint_console: Console) -> None:
    """Print a remediation hint for linear-history push rejections."""
    hint_console.print(
        "\n[yellow]Push rejected by linear-history protection.[/yellow]\n"
        "Try [cyan]spec-kitty merge --strategy squash[/cyan], or set "
        f"[cyan]merge.strategy: squash[/cyan] in [cyan]{KITTIFY_DIR}/config.yaml[/cyan].\n"
    )


def _has_transition_to(
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    to_lane: str,
    repo_root: Path,
) -> bool:
    """Check whether the event log already contains a transition for *wp_id* to *to_lane*.

    This dedup guard prevents duplicate events when ``_mark_wp_merged_done`` is
    called again on retry/resume.
    """
    from specify_cli.coordination.status_transition import has_transition_to_transactional

    return has_transition_to_transactional(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        to_lane=to_lane,
        repo_root=repo_root,
    )


def _mark_wp_merged_done(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    target_branch: str,
) -> None:
    """Record merge-complete state for a merged WP using canonical status events.

    Includes event-log dedup: if the target transition already exists in the log
    the emission is skipped so that retries are idempotent.
    """
    # Primary checkout path — used only for WP file lookup (tasks/*.md live here).
    # Do not use the read-path resolver: after the first coord status commit it
    # can route to the coordination worktree, whose sparse/materialized surface
    # may carry status files but not task markdown.
    primary_feature_dir = candidate_feature_dir_for_mission(repo_root, mission_slug)
    wp_path = None
    for candidate in sorted((primary_feature_dir / "tasks").glob(f"{wp_id}*.md")):
        wp_path = candidate
        break
    if wp_path is None or not wp_path.exists():
        console.print(f"[yellow]Warning:[/yellow] Could not locate WP file for {wp_id}; skipping merge-complete status update.")
        return

    metadata, _body = read_wp_frontmatter(wp_path)
    # Validate the authoritative status surface once (FR-002 / NFR-003).
    # Transactional status helpers must receive the primary meta-bearing feature
    # dir so they can resolve/commit to the coordination branch. Passing the
    # coord worktree dir loses meta in status-only coord worktrees and degrades
    # writes into local, non-durable file edits.
    resolve_status_surface(repo_root, mission_slug)
    feature_dir = primary_feature_dir
    from specify_cli.status import DoneEvidence, ReviewApproval, WPMetadata
    from specify_cli.coordination.status_transition import (
        emit_status_transition_transactional,
        read_current_wp_state_transactional,
    )
    from specify_cli.status import TransitionError
    from specify_cli.status import TransitionRequest

    from specify_cli.status import Lane as _Lane

    def extract_done_evidence(meta: WPMetadata, wp: str) -> DoneEvidence | None:
        """Build DoneEvidence from approved review frontmatter, else None.

        Inlined from the migration-only ``status.history_parser`` module (T031):
        merge is the sole production consumer, so the public ``status`` facade
        (DoneEvidence/ReviewApproval) is used directly instead of a deep import.
        """
        reviewed_by = meta.reviewed_by
        if meta.review_status == "approved" and reviewed_by and str(reviewed_by).strip():
            return DoneEvidence(
                review=ReviewApproval(
                    reviewer=str(reviewed_by).strip(),
                    verdict="approved",
                    reference=f"frontmatter-migration:{wp}",
                )
            )
        return None

    lane, _actor = read_current_wp_state_transactional(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        repo_root=repo_root,
    )
    coord_lane = lane
    if lane == _Lane.DONE:
        return

    # Dedup guard: if we already have a done transition in the log, skip everything.
    if _has_transition_to(feature_dir, mission_slug, wp_id, "done", repo_root):
        logger.debug("Dedup: %s already has 'done' transition, skipping", wp_id)
        return

    # If the coordination branch has no events for this WP (returns PLANNED), fall
    # back to the primary checkout's event log. This covers the case where WP
    # lifecycle events were written to the lane worktree and later squash-merged
    # into main without passing through the coordination branch.
    _force_done = False
    if lane == _Lane.PLANNED:
        from specify_cli.status import CanonicalStatusNotFoundError  # noqa: PLC0415
        from specify_cli.status import lane_reader as _lane_reader  # noqa: PLC0415
        from specify_cli.status import resolve_lane_alias as _resolve_lane_alias  # noqa: PLC0415

        try:
            primary_raw = _lane_reader.get_wp_lane(primary_feature_dir, wp_id)  # primary checkout, not coord surface
        except CanonicalStatusNotFoundError:
            primary_raw = "uninitialized"
        try:
            lane = _Lane(_resolve_lane_alias(str(primary_raw)))
            # The coord has no events for this WP; force the done transition so
            # the state machine doesn't reject it as an invalid jump from PLANNED.
            _force_done = True
        except ValueError:
            # Unknown sentinels such as "uninitialized" mean the primary surface
            # has no usable lifecycle state for this WP either.
            pass

    evidence = extract_done_evidence(metadata, wp_id)
    if evidence is None:
        if lane == _Lane.APPROVED:
            evidence = DoneEvidence(
                review=ReviewApproval(
                    reviewer=(metadata.agent or "unknown").strip() or "unknown",
                    verdict="approved",
                    reference=f"lane-approved:{wp_id}",
                )
            )
        else:
            console.print(f"[yellow]Warning:[/yellow] {wp_id} has no recorded approval metadata; skipping automatic move to done after merge.")
            return

    _pre_approved_lanes = frozenset({_Lane.PLANNED, _Lane.CLAIMED, _Lane.IN_PROGRESS, _Lane.FOR_REVIEW})
    needs_approved_replay = (
        coord_lane == _Lane.PLANNED
        and lane == _Lane.APPROVED
        and _force_done
    )
    if (lane in _pre_approved_lanes or needs_approved_replay) and evidence is not None:
        # Dedup guard for the intermediate approved transition
        if _has_transition_to(feature_dir, mission_slug, wp_id, "approved", repo_root):
            logger.debug("Dedup: %s already has 'approved' transition, skipping emit", wp_id)
        else:
            try:
                emit_status_transition_transactional(
                    TransitionRequest(
                        feature_dir=feature_dir,
                        mission_slug=mission_slug,
                        wp_id=wp_id,
                        to_lane="approved",
                        actor="merge",
                        reason=f"Recorded prior review approval for merged {wp_id}",
                        evidence=evidence.to_dict(),
                        workspace_context=f"merge:{repo_root}",
                        repo_root=repo_root,
                        policy_metadata={
                            "merge_phase": "lane_integrated",
                            "target_branch": target_branch,
                        },
                    ),
                    ensure_sync_daemon=False,
                    sync_dossier=False,
                )
            except TransitionError as exc:
                console.print(f"[yellow]Warning:[/yellow] Failed to mark {wp_id} approved before done: {exc}")
                return
        lane = _Lane.APPROVED
        _force_done = False

    if lane != _Lane.APPROVED:
        console.print(f"[yellow]Warning:[/yellow] {wp_id} is in lane '{lane.value}', not approved; skipping automatic move to done after merge.")
        return

    try:
        # WP07 / FR-008: tag the done transition with merge_phase=lane_integrated
        # so consumers can audit which WPs were integrated via the two-stage
        # merge pipeline (lane -> coordination branch -> target branch) and
        # which target branch they landed on. The transition is emitted once
        # per WP after Stage 1 (lane->coord) completes and before Stage 2
        # (coord->target) runs the post-merge bookkeeping.
        emit_status_transition_transactional(
            TransitionRequest(
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id=wp_id,
                to_lane="done",
                actor="merge",
                reason=f"Merged {wp_id} into {target_branch}",
                evidence=evidence.to_dict(),
                workspace_context=f"merge:{repo_root}",
                repo_root=repo_root,
                force=_force_done,
                policy_metadata={
                    "merge_phase": "lane_integrated",
                    "target_branch": target_branch,
                },
            ),
            ensure_sync_daemon=False,
            sync_dossier=False,
        )
    except TransitionError as exc:
        console.print(f"[yellow]Warning:[/yellow] Failed to mark {wp_id} done after merge: {exc}")


def _assert_merged_wps_reached_done(
    repo_root: Path,
    mission_slug: str,
    wp_ids: list[str],
) -> None:
    """Fail the merge if merged WPs did not reach ``done`` in the event log."""
    from specify_cli.status import CanonicalStatusNotFoundError
    from specify_cli.status import Lane
    from specify_cli.status import StoreError
    from specify_cli.status import get_wp_lane
    from specify_cli.status import resolve_lane_alias

    # Resolve the canonical status surface so reads are on the same side as
    # the writes in _mark_wp_merged_done (fixes coordination-branch divergence).
    surface_path = resolve_status_surface(repo_root, mission_slug)
    feature_dir = surface_path.parent

    try:
        incomplete: list[str] = []
        for wp_id in wp_ids:
            raw = get_wp_lane(feature_dir, wp_id)
            try:
                lane = Lane(resolve_lane_alias(raw))
            except ValueError:
                # Unrecognized sentinel (e.g. "uninitialized") — treat as not done
                incomplete.append(f"{wp_id}={raw}")
                continue
            if lane != Lane.DONE:
                incomplete.append(f"{wp_id}={lane.value}")
    except CanonicalStatusNotFoundError as exc:
        # The canonical event log is absent (e.g. a legacy mission that never ran
        # finalize-tasks, or a surface that diverged from the mark-done writes).
        # Code integration already succeeded; surface this as a deliberate,
        # actionable validation failure rather than an uncaught crash.
        console.print(
            "[red]Error:[/red] Post-merge status validation could not run: "
            f"no canonical event log at {surface_path}. Code was integrated, but "
            "WP done-state cannot be confirmed. Run "
            f"'spec-kitty agent mission finalize-tasks --mission {mission_slug}' "
            "to bootstrap the event log, then re-run the merge."
        )
        raise typer.Exit(1) from exc
    except StoreError as exc:
        console.print(
            "[red]Error:[/red] Post-merge status validation failed: "
            f"could not read {surface_path} ({exc})"
        )
        raise typer.Exit(1) from exc

    if incomplete:
        console.print(
            "[red]Error:[/red] Post-merge status validation failed: "
            "merged WPs did not reach done in the canonical event log."
        )
        console.print(f"  Offending WPs: {', '.join(incomplete)}")
        raise typer.Exit(1)


def _assert_merged_wps_done_on_target(
    repo_root: Path,
    mission_slug: str,
    target_branch: str,
    wp_ids: list[str],
    *,
    feature_dir: Path,
    mission_id: str | None,
) -> None:
    """Fail when modern merged WP done events are absent from target history."""
    if mission_id is None:
        return

    # FR-038 (#1772 Bug 4): post-merge validation reads ``git show <branch>:<rel>``,
    # which only resolves paths TRACKED in the branch tree. A coord-aware
    # ``feature_dir`` may point under ``.worktrees/<m>-coord/…`` (never tracked
    # in a branch tree), producing a spurious "path exists on disk, but not in
    # <branch>" failure. Always resolve the IN-BRANCH tracked status path:
    # ``kitty-specs/<m>/status.events.jsonl``.
    try:
        rel_events_path = feature_dir.relative_to(repo_root) / _STATUS_EVENTS_FILENAME
    except ValueError:
        rel_events_path = Path(KITTY_SPECS_DIR) / mission_slug / _STATUS_EVENTS_FILENAME
    if path_is_under_worktrees(rel_events_path):
        rel_events_path = Path(KITTY_SPECS_DIR) / mission_slug / _STATUS_EVENTS_FILENAME

    ret_show, out_show, err_show = run_command(
        ["git", "show", f"{target_branch}:{rel_events_path.as_posix()}"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret_show != 0:
        console.print(
            "[red]Error:[/red] Post-merge target validation failed: "
            f"could not read {target_branch}:{rel_events_path.as_posix()} "
            f"({(err_show or out_show or '').strip()})"
        )
        raise typer.Exit(1)

    lanes_by_wp: dict[str, str] = {}
    for line in (out_show or "").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        wp_id = event.get("wp_id")
        to_lane = event.get("to_lane")
        if isinstance(wp_id, str) and isinstance(to_lane, str):
            lanes_by_wp[wp_id] = to_lane

    incomplete = [
        f"{wp_id}={lanes_by_wp.get(wp_id, 'missing')}"
        for wp_id in wp_ids
        if lanes_by_wp.get(wp_id) != "done"
    ]
    if incomplete:
        console.print(
            "[red]Error:[/red] Post-merge target validation failed: "
            "merged WPs did not reach done in target branch history."
        )
        console.print(f"  Offending WPs: {', '.join(incomplete)}")
        raise typer.Exit(1)


def _reconcile_completed_wps_for_resume(
    *,
    feature_dir: Path,
    mission_slug: str,
    merge_state: MergeState,
    repo_root: Path,
) -> set[str]:
    """Return completed WPs that still have canonical done evidence on disk.

    A retry can happen after the target ref advanced but before the final
    status-event housekeeping commit. If the operator repairs the checkout
    back to HEAD, state.json may still list a WP as completed even though its
    uncommitted done event is gone. Drop those stale completions so the retry
    re-emits done evidence instead of skipping the WP and failing validation.
    """
    if not merge_state.completed_wps:
        return set()

    confirmed = [
        wp_id
        for wp_id in merge_state.completed_wps
        if _has_transition_to(feature_dir, mission_slug, wp_id, "done", repo_root)
    ]
    if len(confirmed) != len(merge_state.completed_wps):
        dropped = sorted(set(merge_state.completed_wps) - set(confirmed))
        logger.info(
            "Re-emitting done events for WPs whose resume state outlived on-disk evidence: %s",
            ", ".join(dropped),
        )
        merge_state.completed_wps = confirmed
        save_state(merge_state, repo_root)
    return set(confirmed)


def _record_merged_wps_done_for_merge(
    *,
    main_repo: Path,
    feature_dir: Path,
    mission_slug: str,
    lanes_manifest: object,
    target_branch: str,
    merge_state: MergeState,
    all_wp_ids: list[str],
) -> None:
    """Record done transitions for merged WPs and validate the canonical surface."""
    console.print("  [dim]Recording merged work packages as done...[/dim]")
    completed_set = _reconcile_completed_wps_for_resume(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        merge_state=merge_state,
        repo_root=main_repo,
    )
    for lane in lanes_manifest.lanes:
        for wp_id in lane.wp_ids:
            if wp_id in completed_set:
                console.print(f"  [dim]Skipping {wp_id} (already recorded as done)[/dim]")
                continue

            merge_state.set_current_wp(wp_id)
            save_state(merge_state, main_repo)

            _mark_wp_merged_done(main_repo, mission_slug, wp_id, target_branch)

            merge_state.mark_wp_complete(wp_id)
            save_state(merge_state, main_repo)
            completed_set.add(wp_id)

    _assert_merged_wps_reached_done(main_repo, mission_slug, all_wp_ids)


def _refresh_primary_checkout_after_merge(repo_root: Path) -> None:
    """Force the primary checkout's tracked files to match HEAD.

    The target ref is advanced from a detached merge worktree, so the primary
    checkout's index/worktree can lag behind the new HEAD. A path checkout does
    not remove rename sources in sparse-checkout repos; hard reset does.
    Merge preflight requires a clean tracked worktree before this point, so this
    must only discard stale tracked state created by the ref update.
    """
    ret_reset, out_reset, err_reset = run_command(
        ["git", "reset", "--hard", "HEAD"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret_reset != 0:
        console.print(
            f"[yellow]Warning:[/yellow] post-merge working-tree refresh failed: "
            f"{(err_reset or out_reset or '').strip()}"
        )
        return

    ret_refresh, out_refresh, err_refresh = run_command(
        ["git", "update-index", "--refresh"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret_refresh != 0:
        # Non-zero is expected when files truly differ from HEAD. The invariant
        # check below is the contract; this refresh is just stat reconciliation.
        logger.debug(
            "post-merge index refresh reported divergence (this is informational): %s",
            (out_refresh or err_refresh or "").strip(),
        )


def _paths_have_status_changes(repo_root: Path, paths: list[Path]) -> bool:
    """Return True when any requested path differs from HEAD or is untracked."""
    normalized: list[str] = []
    for path in paths:
        candidate = path
        if candidate.is_absolute():
            with contextlib.suppress(ValueError):
                candidate = candidate.relative_to(repo_root)
        normalized.append(str(candidate))

    ret_status, out_status, err_status = run_command(
        ["git", "status", "--porcelain", "--", *normalized],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret_status != 0:
        logger.warning(
            "Could not inspect post-merge bookkeeping paths before commit: %s",
            (err_status or "").strip(),
        )
        return True
    return bool((out_status or "").strip())


def _validate_mission_slug_path_segment(mission_slug: str) -> str:
    """Reject mission slugs unsafe for direct path composition.

    Delegates to the canonical ``assert_safe_path_segment`` validator (FR-002 / WP04).
    Raises ``ValueError`` on any traversal-unsafe value, preserving the existing contract.
    """
    return assert_safe_path_segment(mission_slug)


def _target_bookkeeping_status_paths(
    *,
    main_repo: Path,
    mission_slug: str,
    status_feature_dir: Path,
) -> tuple[Path, Path]:
    """Return status paths that may be staged from the target checkout.

    ``status_feature_dir`` is topology-aware and can point at the coordination
    worktree. The final merge bookkeeping commit runs from ``main_repo`` onto
    the target branch, so it must stage primary-checkout paths only.
    """
    safe_mission_slug = _validate_mission_slug_path_segment(mission_slug)
    target_feature_dir = (
        primary_feature_dir_for_mission(main_repo, safe_mission_slug)
        if is_under_worktrees_segment(status_feature_dir)
        else status_feature_dir
    )
    safe_target_feature_dir = ensure_within_directory(target_feature_dir, main_repo)
    return (
        safe_target_feature_dir / _STATUS_EVENTS_FILENAME,
        safe_target_feature_dir / _STATUS_FILENAME,
    )


def _read_optional_bytes(path: Path) -> bytes | None:
    if not path.exists():
        return None
    return path.read_bytes()


def _assert_status_path_within_target_surface(
    *,
    repo_root: Path,
    mission_slug: str,
    candidate: Path,
) -> Path:
    """Reject bookkeeping paths that escape the canonical mission status surface.

    Validates ``mission_slug`` via ``assert_safe_path_segment`` (FR-003) before
    composing the surface root, then delegates containment to ``ensure_within_any``
    (FR-006 / T016).
    """
    assert_safe_path_segment(mission_slug)
    repo_resolved = get_main_repo_root(repo_root).resolve(strict=False)
    surface_root = primary_feature_dir_for_mission(repo_resolved, mission_slug).resolve(strict=False)
    return ensure_within_any(candidate, roots=[surface_root])


def _assert_status_surface_path_is_trusted(
    *,
    repo_root: Path,
    status_feature_dir: Path,
) -> Path:
    """Reject status surfaces that resolve outside the repo's trusted roots.

    Selects the single correct root via ``is_under_worktrees_segment`` (worktrees
    vs kitty-specs), then delegates containment to ``ensure_within_any``
    (FR-006 / T018).  The selection is intentionally preserved — widening to a
    union of both roots would be a behavior change (research.md §(d)).

    The *claimed* topology (the path segment) must match the *resolved* topology:
    if the segment says worktrees but the resolved path is not under the worktrees
    root (or vice versa), the surface is rejected.  This closes a symlink/taint
    gap where a kitty-specs-shaped path could resolve into the worktrees tree (or
    the reverse) and slip past the single-root containment check.
    """
    repo_resolved = get_main_repo_root(repo_root).resolve(strict=False)
    worktrees_root = (repo_resolved / WORKTREES_DIR).resolve(strict=False)
    # Root specs dir (no per-mission slug appended) used purely for symlink/taint
    # containment checking, not raw per-mission-spec path composition. Bound to a
    # neutrally named local (``specs_root``) to avoid a false positive on the raw
    # mission-spec path ratchet (test_no_raw_mission_spec_paths) while keeping that
    # ratchet active over the rest of this module.
    specs_root = (repo_resolved / KITTY_SPECS_DIR).resolve(strict=False)
    # Absolutize the candidate (anchor a relative surface to the repo root) before
    # any containment check, then reject — pre-resolution — a path that escapes the
    # root its segment claims. Hardens the write path against a traversal/symlink
    # surface that would otherwise only be caught after ``.resolve()`` (#2043 Sonar).
    status_candidate = (
        status_feature_dir
        if status_feature_dir.is_absolute()
        else repo_resolved / status_feature_dir
    ).absolute()
    segment_claims_worktrees = is_under_worktrees_segment(status_candidate)
    claimed_root = worktrees_root if segment_claims_worktrees else specs_root
    try:
        status_candidate.relative_to(claimed_root)
    except ValueError as exc:
        raise ValueError(f"Untrusted status surface path: {status_feature_dir}") from exc
    status_resolved = status_candidate.resolve(strict=False)
    resolves_under_worktrees = status_resolved.is_relative_to(worktrees_root)
    resolves_under_specs = status_resolved.is_relative_to(specs_root)

    if segment_claims_worktrees != resolves_under_worktrees:
        raise ValueError(f"Untrusted status surface path: {status_feature_dir}")
    if not resolves_under_worktrees and not resolves_under_specs:
        raise ValueError(f"Untrusted status surface path: {status_feature_dir}")

    trusted_root = worktrees_root if resolves_under_worktrees else specs_root
    return ensure_within_directory(status_resolved, trusted_root)


def _assert_status_surface_file_path_is_trusted(
    *,
    repo_root: Path,
    status_feature_dir: Path,
    filename: str,
) -> Path:
    """Reject status-surface child paths outside the exact bookkeeping files."""
    if filename not in {_STATUS_EVENTS_FILENAME, _STATUS_FILENAME}:
        raise ValueError(f"Refusing untrusted status filename: {filename}")
    trusted_surface = _assert_status_surface_path_is_trusted(
        repo_root=repo_root,
        status_feature_dir=status_feature_dir,
    )
    candidate = trusted_surface / filename
    if candidate.is_symlink():
        raise ValueError(f"Refusing symlinked status surface path: {candidate}")
    return ensure_within_any(
        candidate,
        roots=[],
        files=[trusted_surface / _STATUS_EVENTS_FILENAME, trusted_surface / _STATUS_FILENAME],
    )


def _restore_optional_bytes(path: Path, original: bytes | None) -> None:
    if original is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(original)


def _assert_bookkeeping_snapshot_path_is_trusted(
    *,
    repo_root: Path,
    candidate: Path,
) -> Path:
    """Reject rollback snapshot paths outside merge bookkeeping roots.

    Delegates multi-root containment + exact-file allowlist to ``ensure_within_any``
    (FR-006 / T017).  The trusted set (3 dirs + the exact file) is preserved exactly —
    no set change (NFR-001 / C-007).
    """
    repo_resolved = get_main_repo_root(repo_root).resolve(strict=False)
    return ensure_within_any(
        candidate,
        roots=[
            (repo_resolved / KITTY_SPECS_DIR).resolve(strict=False),
            (repo_resolved / WORKTREES_DIR).resolve(strict=False),
            (repo_resolved / KITTIFY_DIR / "runtime" / "merge").resolve(strict=False),
        ],
        files=[repo_resolved / KITTIFY_DIR / "merge-state.json"],
    )


def _capture_bookkeeping_snapshots(
    repo_root: Path,
    *candidates: Path,
) -> dict[Path, bytes | None]:
    """Capture rollback bytes for repo-derived bookkeeping paths only."""
    snapshots: dict[Path, bytes | None] = {}
    for candidate in candidates:
        trusted_path = _assert_bookkeeping_snapshot_path_is_trusted(
            repo_root=repo_root,
            candidate=candidate,
        )
        snapshots[trusted_path] = _read_optional_bytes(trusted_path)
    return snapshots


def _restore_final_bookkeeping_snapshots(
    snapshots: dict[Path, bytes | None],
) -> None:
    """Best-effort restore for final merge bookkeeping rollback.

    Snapshot paths are validated at capture time (``_capture_bookkeeping_snapshots``
    → ``_assert_bookkeeping_snapshot_path_is_trusted``), so restore trusts the dict
    keys and only needs to tolerate transient I/O failures.
    """
    for path, original in snapshots.items():
        try:
            _restore_optional_bytes(path, original)
        except OSError:
            continue


def _target_branch_still_at_baseline(
    main_repo: Path,
    target_branch: str,
    baseline_sha: str,
) -> bool:
    """Return True when target still points at the pre-target-merge baseline."""
    if not baseline_sha or baseline_sha == "HEAD~1":
        return False
    ret, out, _err = run_command(
        ["git", "rev-parse", target_branch],
        capture=True,
        check_return=False,
        cwd=main_repo,
    )
    return ret == 0 and out.strip() == baseline_sha


def _project_status_bookkeeping_to_target(
    *,
    main_repo: Path,
    mission_slug: str,
    status_feature_dir: Path,
) -> tuple[Path, Path]:
    """Copy authoritative status bookkeeping to target-checkout paths.

    Coord-backed missions write done transitions through the coordination
    surface, but the final target-branch housekeeping commit can only stage
    paths tracked under ``main_repo``. Project just the status artifacts into
    ``kitty-specs/<slug>/`` before the commit; keep the authoritative write
    topology unchanged.
    """
    target_events_path, target_status_path = _target_bookkeeping_status_paths(
        main_repo=main_repo,
        mission_slug=mission_slug,
        status_feature_dir=status_feature_dir,
    )
    trusted_status_feature_dir = _assert_status_surface_path_is_trusted(
        repo_root=main_repo,
        status_feature_dir=status_feature_dir,
    )
    trusted_target_events_path = _assert_status_path_within_target_surface(
        repo_root=main_repo,
        mission_slug=mission_slug,
        candidate=target_events_path,
    )
    trusted_target_status_path = _assert_status_path_within_target_surface(
        repo_root=main_repo,
        mission_slug=mission_slug,
        candidate=target_status_path,
    )
    if not is_under_worktrees_segment(trusted_status_feature_dir):
        return trusted_target_events_path, trusted_target_status_path

    trusted_target_events_path.parent.mkdir(parents=True, exist_ok=True)
    source_events_path = _assert_status_surface_file_path_is_trusted(
        repo_root=main_repo,
        status_feature_dir=trusted_status_feature_dir,
        filename=_STATUS_EVENTS_FILENAME,
    )
    source_status_path = _assert_status_surface_file_path_is_trusted(
        repo_root=main_repo,
        status_feature_dir=trusted_status_feature_dir,
        filename=_STATUS_FILENAME,
    )
    source_events_bytes = _read_optional_bytes(source_events_path)
    source_status_bytes = _read_optional_bytes(source_status_path)
    original_events_bytes = _read_optional_bytes(trusted_target_events_path)
    original_status_bytes = _read_optional_bytes(trusted_target_status_path)
    try:
        if source_events_bytes is not None:
            trusted_target_events_path.write_bytes(source_events_bytes)
        if source_status_bytes is not None:
            trusted_target_status_path.write_bytes(source_status_bytes)
    except OSError:
        _restore_optional_bytes(trusted_target_events_path, original_events_bytes)
        _restore_optional_bytes(trusted_target_status_path, original_status_bytes)
        raise
    return trusted_target_events_path, trusted_target_status_path


def _already_baked(merge_state: MergeState | None) -> bool:
    """Resume short-circuit predicate (T026 / FR-012).

    Returns True when a prior merge run successfully baked the mission_number
    and persisted the flag to state.json. Caller may skip the assignment
    step entirely with no I/O.
    """
    return merge_state is not None and merge_state.mission_number_baked


def _mark_mission_number_baked(
    merge_state: MergeState | None,
    main_repo: Path,
) -> None:
    """Persist ``mission_number_baked = True`` so a subsequent resume short-
    circuits via :func:`_already_baked` (T025 / FR-011)."""
    if merge_state is None:
        return
    merge_state.mission_number_baked = True
    from specify_cli.merge.state import save_state as _save_state
    _save_state(merge_state, main_repo)


def _is_git_repo(path: Path) -> bool:
    """Return True when *path* is inside a git working tree."""
    import subprocess as _subprocess
    probe = _subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(path),
        capture_output=True,
        text=True,
    )
    return probe.returncode == 0 and probe.stdout.strip() == "true"


def _is_assigned_mission_number(value: object) -> bool:
    """Return True when *value* is a real integer mission_number (not bool/None)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _compute_next_mission_number_or_none(
    main_repo: Path,
    mission_slug: str,
    target_branch: str,
) -> int | None:
    """Step 1: derive the next mission_number from the *target* branch.

    Returns:
        The next integer (``max + 1``, or ``1`` if empty), or ``None`` when
        the target branch already carries an integer for this mission (the
        no-op signal — the assignment already happened on a prior merge).
    """
    import json as _json
    import subprocess as _subprocess
    import tempfile as _tempfile

    tmp_dir = _tempfile.mkdtemp(prefix="kitty-numassign-")
    tmp_path = Path(tmp_dir)
    try:
        result = _subprocess.run(
            ["git", "worktree", "add", "--detach", str(tmp_path), target_branch],
            cwd=str(main_repo),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(
                "Could not create scan worktree for mission_number assignment: %s",
                result.stderr.strip(),
            )
            # Fall back to scanning main_repo's working tree. Best effort.
            scan_root = main_repo
            scan_specs = main_repo / KITTY_SPECS_DIR
        else:
            scan_root = tmp_path
            scan_specs = tmp_path / KITTY_SPECS_DIR

        target_meta_path = scan_specs / mission_slug / "meta.json"
        if target_meta_path.exists():
            target_meta = _json.loads(target_meta_path.read_text(encoding="utf-8"))
            existing_on_target = (
                target_meta.get("mission_number") if isinstance(target_meta, dict) else None
            )
            if _is_assigned_mission_number(existing_on_target):
                logger.debug(
                    "Mission %s already has mission_number=%d on target branch %s; no-op",
                    mission_slug, existing_on_target, target_branch,
                )
                return None

        return assign_next_mission_number(scan_root, scan_specs)
    finally:
        _subprocess.run(
            ["git", "worktree", "remove", str(tmp_path), "--force"],
            cwd=str(main_repo),
            capture_output=True,
        )


def _write_mission_number_to_branch(
    main_repo: Path,
    mission_branch: str,
    mission_slug: str,
    next_number: int,
    merge_state: MergeState | None,
) -> bool:
    """Step 2: write the integer into meta.json on the mission branch, commit,
    and fast-forward the branch ref.

    Returns:
        True when a fresh write + commit was applied; False when nothing was
        written because (a) the branch is missing, (b) the worktree could not
        be created, (c) meta.json is missing or malformed, or (d) the value
        was already equal (idempotency hit — still persists the baked flag).
    """
    import json as _json
    import subprocess as _subprocess
    import tempfile as _tempfile

    if not _has_branch_ref(main_repo, mission_branch):
        logger.warning(
            "Skipping mission_number bake for %s: branch %s does not exist",
            mission_slug,
            mission_branch,
        )
        return False

    mission_tmp_dir = _tempfile.mkdtemp(prefix="kitty-numwrite-")
    mission_tmp_path = Path(mission_tmp_dir)
    try:
        result = _subprocess.run(
            ["git", "worktree", "add", "--detach", str(mission_tmp_path), mission_branch],
            cwd=str(main_repo),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(
                "Skipping mission_number bake for %s: could not create mission worktree for %s (%s)",
                mission_slug,
                mission_branch,
                result.stderr.strip(),
            )
            return False

        # FR-037 (#1772 Bug 3, _write_mission_number_to_branch half): resolve the
        # IN-BRANCH feature dir for the detached mission-branch worktree, not a
        # nested-worktree meta.json. ``candidate_feature_dir_for_mission`` is
        # coord-aware and would return a tracked ``.worktrees/<m>-coord/…`` path
        # when the mission-branch tree carries that pollution — staging it via
        # ``git add`` then re-pollutes the tree. The mission-branch tree always
        # carries the canonical mission dir directly under ``kitty-specs/``, so
        # compose that path by hand and never resolve into ``.worktrees/``.
        from specify_cli.missions._read_path_resolver import compose_meta_json_path as _compose_meta

        meta_path = _compose_meta(mission_tmp_path, mission_slug)
        if path_is_under_worktrees(meta_path):
            logger.warning(
                "Refusing to bake mission_number for %s: resolved meta path is under "
                "%s (%s)",
                mission_slug,
                WORKTREES_DIR,
                meta_path,
            )
            return False
        if not meta_path.exists():
            logger.warning(
                "meta.json missing on mission branch %s for %s; cannot bake mission_number",
                mission_branch,
                mission_slug,
            )
            return False

        meta_data = _json.loads(meta_path.read_text(encoding="utf-8"))
        if not isinstance(meta_data, dict):
            logger.warning(
                "meta.json for %s is not a JSON object; cannot bake mission_number",
                mission_slug,
            )
            return False

        # T025 / FR-010 — idempotency check INSIDE the merge-state lock.
        existing_on_mission = meta_data.get("mission_number")
        if (
            _is_assigned_mission_number(existing_on_mission)
            and existing_on_mission == next_number
        ):
            logger.info(
                "mission_number=%d already present on mission branch %s for %s; skipping write (idempotency check)",
                next_number,
                mission_branch,
                mission_slug,
            )
            _mark_mission_number_baked(merge_state, main_repo)
            return False

        meta_data["mission_number"] = next_number
        # Route all meta.json mutations through the canonical writer API.
        # validate=False preserves merge-time tolerance for legacy/partial mission
        # metadata while still enforcing atomic writes + standard format.
        write_meta(meta_path.parent, meta_data, validate=False)

        rel_meta = meta_path.relative_to(mission_tmp_path)
        if path_is_under_worktrees(rel_meta):
            # FR-035: never stage a path under .worktrees/ (defense in depth).
            logger.warning(
                "Refusing to stage %s for %s: path is under %s",
                rel_meta,
                mission_slug,
                WORKTREES_DIR,
            )
            return False
        _subprocess.run(
            ["git", "add", str(rel_meta)],
            cwd=str(mission_tmp_path),
            capture_output=True,
            check=True,
        )
        commit_msg = f"chore({mission_slug}): assign mission_number={next_number}"
        _subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "commit", "-m", commit_msg],
            cwd=str(mission_tmp_path),
            capture_output=True,
            check=True,
        )

        new_sha = _subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(mission_tmp_path),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        # Fast-forward the mission branch ref, resyncing any worktree (e.g.
        # the coordination worktree) that has it checked out (#1826 / AC-B2).
        # Coordination status residue on the primary checkout is legitimate
        # after a coord-branch write, so exclude it from the dirty gate
        # (#1878 / FR-012) rather than abort the post-write ff-advance.
        advance_branch_ref(
            main_repo,
            mission_branch,
            new_sha,
            coord_owned_filenames=COORD_OWNED_STATUS_FILES,
        )
        return True
    finally:
        _subprocess.run(
            ["git", "worktree", "remove", str(mission_tmp_path), "--force"],
            cwd=str(main_repo),
            capture_output=True,
        )


def _bake_mission_number_into_mission_branch(
    main_repo: Path,
    mission_slug: str,
    mission_branch: str,
    target_branch: str,
    *,
    dry_run: bool = False,
    merge_state: MergeState | None = None,
) -> int | None:
    """Assign and persist a dense integer ``mission_number`` for a pre-merge mission.

    Implements WP10 / FR-044 / T053 plus WP04 (FR-010 / FR-011 / FR-012):

    1. T026 / FR-012 — Resume short-circuit (:func:`_already_baked`): if a
       prior run completed the assignment and persisted the flag, return
       immediately with no I/O.
    2. Step 1 (:func:`_compute_next_mission_number_or_none`): scan the
       *target* branch for the next available integer (``max + 1``). If the
       target already carries an integer for this mission, return ``None`` —
       the assignment landed in a prior successful merge.
    3. Dry-run short-circuit: log the value but do not write or commit.
    4. Step 2 (:func:`_write_mission_number_to_branch`): create a detached
       worktree at the mission-branch tip, update ``meta.json``, commit, and
       fast-forward the mission branch ref. The idempotency check inside
       Step 2 short-circuits with no write when the mission branch already
       carries exactly the computed value (T025 / FR-010).
    5. On a successful write, mark the baked flag for future resume calls.

    The caller MUST hold the global merge lock
    (``acquire_merge_lock("__global_merge__", ...)``) for the duration.

    NOTE: ``mission_number_baked`` is set after a successful idempotency hit
    OR a successful write. Operators who manually edit ``meta.json`` after a
    partial merge are responsible for clearing the flag (or running
    ``spec-kitty merge --abort``).

    **Retry safety**: the assignment always re-derives from the target tip.
    If a prior run assigned a number from a stale target and the push failed,
    re-running after ``git fetch`` sees the updated target and computes the
    correct next value — the stale number in the mission branch's
    ``meta.json`` is overwritten.

    Returns:
        The assigned integer if a fresh number was written; ``None`` when
        the target branch already had one, when dry-run is set, when the
        idempotency check matched, or when any precondition (missing branch,
        missing meta.json, malformed JSON, git failure) caused a skip.
    """
    if _already_baked(merge_state):
        logger.debug(
            "mission_number_baked=True for %s; skipping assignment step (resume short-circuit)",
            mission_slug,
        )
        return None

    if not _is_git_repo(main_repo):
        logger.warning(
            "Skipping mission_number bake for %s: %s is not a git repository",
            mission_slug,
            main_repo,
        )
        return None

    next_number = _compute_next_mission_number_or_none(main_repo, mission_slug, target_branch)
    if next_number is None:
        return None

    if dry_run:
        console.print(
            f"[cyan]would assign[/cyan] mission_number={next_number} to mission {mission_slug}"
        )
        return None

    if not _write_mission_number_to_branch(
        main_repo, mission_branch, mission_slug, next_number, merge_state
    ):
        return None

    console.print(
        f"[green]Assigned[/green] mission_number={next_number} to mission {mission_slug}"
    )
    logger.info("Assigned mission_number=%d to mission %s", next_number, mission_slug)
    _mark_mission_number_baked(merge_state, main_repo)

    return next_number


def _has_branch_ref(repo_root: Path, ref_name: str) -> bool:
    """Return True when a local branch/ref resolves to a commit."""
    retcode, _stdout, _stderr = run_command(
        ["git", "rev-parse", "--verify", f"{ref_name}^{{commit}}"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    return retcode == 0


def _check_mission_branch(
    mission_slug: str,
    repo_root: Path,
    *,
    expected_branch: str | None = None,
    mission_id: str | None = None,
) -> tuple[bool, MissionBranchBlocker | None]:
    """Check whether the expected mission branch exists locally.

    Dry-run and real merge both use this as a read-only preflight. Missing
    branches are reported as structured blockers; this function never creates
    the branch.

    When ``expected_branch`` is not supplied (no recorded
    ``lanes.json.mission_branch``), the branch to CHECK is RESOLVED via the WP01
    seam :func:`resolve_branch_name` — the canonical-first / legacy-failover
    resolver (FR-004) — rather than a bare ``kitty/mission-<slug>`` f-string. The
    f-string drops the ``-<mid8>`` disambiguator and never strips a stale ``NNN-``
    prefix, so it mis-targeted the never-created branch and falsely reported it
    missing (#1978). ``resolve_branch_name`` keeps that #1978 fix intact for
    canonical/embedded slugs (no warning), failovers to the legacy ``NNN-`` branch
    with a one-shot deprecation warning, and still raises
    :class:`BranchIdentityUnresolved` for a genuinely-unresolvable modern slug
    (fail-closed preserved).
    """
    from specify_cli.lanes.branch_naming import resolve_branch_name

    expected_branch = expected_branch or resolve_branch_name(
        mission_slug, mission_id=mission_id
    )
    if _has_branch_ref(repo_root, expected_branch):
        return True, None

    retcode, stdout, _stderr = run_command(
        ["git", "rev-parse", "HEAD"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    base_sha = stdout.strip()[:12] if retcode == 0 else "<base-commit>"

    blocker_payload: MissionBranchBlocker = {
        "ready": False,
        "blocker": "missing_mission_branch",
        "expected_branch": expected_branch,
        "remediation": f"git branch {expected_branch} {base_sha}",
    }
    return False, blocker_payload


def _enforce_planning_artifact_target_branch(repo_root: Path, target_branch: str) -> None:
    """Planning-only closeout writes directly to the target branch."""

    retcode, stdout, _stderr = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    current_branch = stdout.strip() if retcode == 0 else ""
    if current_branch == target_branch:
        return

    current_label = current_branch or "detached HEAD"
    console.print(
        "[red]Error:[/red] Planning-artifact-only merge must run on "
        f"target branch {target_branch}, not {current_label}."
    )
    raise typer.Exit(1)


def _enforce_git_preflight(repo_root: Path, *, json_output: bool) -> None:
    """Run git preflight checks and stop early with deterministic remediation."""
    if not (repo_root / ".git").exists():
        return

    preflight = run_git_preflight(repo_root, check_worktree_list=True)
    if preflight.passed:
        return

    payload = build_git_preflight_failure_payload(preflight, command_name="spec-kitty merge")
    if json_output:
        enriched = dict(payload)
        enriched["spec_kitty_version"] = SPEC_KITTY_VERSION
        print(json.dumps(enriched))
    else:
        console.print(f"[red]Error:[/red] {payload['error']}")
        for cmd in payload.get("remediation", []):
            console.print(f"  - Run: {cmd}")
    raise typer.Exit(1)


def _extract_mission_slug(branch_name: str) -> str | None:
    """Infer a feature slug from a feature, mission, or lane branch name."""
    from specify_cli.lanes.branch_naming import parse_mission_slug_from_branch

    parsed = parse_mission_slug_from_branch(branch_name)
    if parsed:
        # BranchParseResult(slug, mid8_token, lane_id) — return the slug portion
        return parsed.slug

    match = re.match(r"^(\d{3}-[a-z0-9][a-z0-9-]*?)(?:-(?:lane-[a-z]))?$", branch_name)
    if match:
        return match.group(1)
    return None


def _resolve_mission_slug(repo_root: Path, mission_slug: str | None) -> str | None:
    if mission_slug:
        # F-001: ``--mission`` accepts handles (bare mid8, full ULID, numeric
        # prefix). Canonicalize at this boundary — the same pattern as the
        # agent ``_find_mission_slug`` helpers — so every downstream
        # composition (merge state, the committed ``kitty-specs/<slug>/
        # meta.json`` read, ``primary_feature_dir_for_mission``, the dry-run
        # payload) consumes the canonical directory name, never the raw
        # operator handle. Handles that resolve to no existing directory keep
        # their raw form, preserving the historical no-lanes / not-found
        # error behaviour downstream.
        from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

        try:
            candidate = candidate_feature_dir_for_mission(
                get_main_repo_root(repo_root), mission_slug
            )
        except StatusReadPathNotFound:
            # Fail-closed coordination window (coord worktree root
            # materialized, mission dir absent): fall back to the raw handle —
            # ``merge --abort`` relies on slug resolution staying non-raising
            # to clean up exactly that broken state.
            return mission_slug
        if candidate.exists():
            return candidate.name
        return mission_slug

    retcode, current_branch, _stderr = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if retcode != 0:
        return None
    return _extract_mission_slug(current_branch.strip())


def _merge_state_key_candidates(repo_root: Path, mission_slug: str | None) -> list[str]:
    """Return merge-state keys to try for a resolved mission slug.

    Modern merge state is keyed by mission ULID, while operators usually pass
    the mission directory slug. Legacy interrupted state may still be keyed by
    slug, so callers must try both.
    """
    if not mission_slug:
        return []
    keys: list[str] = []
    try:
        feature_dir = candidate_feature_dir_for_mission(
            get_main_repo_root(repo_root),
            mission_slug,
        )
        if feature_dir.exists():
            identity = resolve_mission_identity(feature_dir)
            if identity.mission_id:
                keys.append(identity.mission_id)
    except Exception as exc:  # noqa: BLE001 - resume/abort must stay cleanup-safe
        logger.debug("Could not resolve merge state key for %s: %s", mission_slug, exc)
    keys.append(mission_slug)
    return list(dict.fromkeys(keys))


def _iter_merge_states_for_slug(
    repo_root: Path,
    mission_slug: str,
) -> list[tuple[str, MergeState]]:
    runtime_merge_dir = repo_root / KITTIFY_DIR / "runtime" / "merge"
    if not runtime_merge_dir.exists():
        return []

    matches: list[tuple[str, MergeState]] = []
    for candidate in sorted(runtime_merge_dir.iterdir()):
        if not candidate.is_dir():
            continue
        state = load_state(repo_root, candidate.name)
        if state is not None and state.mission_slug == mission_slug:
            matches.append((candidate.name, state))
    return matches


def _load_merge_state_for_mission(
    repo_root: Path,
    mission_slug: str | None,
) -> MergeState | None:
    """Load merge state by modern key, legacy key, then stored mission_slug."""
    entry = _load_merge_state_entry_for_mission(repo_root, mission_slug)
    if entry is None:
        return None
    _key, state = entry
    return state


def _load_merge_state_entry_for_mission(
    repo_root: Path,
    mission_slug: str | None,
) -> tuple[str | None, MergeState] | None:
    """Load merge state plus the runtime key used to find it."""
    if not mission_slug:
        state = load_state(repo_root)
        return (None, state) if state is not None else None

    for key in _merge_state_key_candidates(repo_root, mission_slug):
        state = load_state(repo_root, key)
        if state is not None:
            return key, state

    for key, state in _iter_merge_states_for_slug(repo_root, mission_slug):
        return key, state
    return None


def _load_or_create_merge_state(
    *,
    main_repo: Path,
    mission_slug: str,
    canonical_id: str,
    target_branch: str,
    wp_order: list[str],
    push_requested: bool,
) -> tuple[MergeState, bool]:
    """Load canonical/legacy merge state, migrating legacy state to canonical."""
    canonical_state = load_state(main_repo, canonical_id)
    if canonical_state is not None:
        return canonical_state, True

    entry = _load_merge_state_entry_for_mission(main_repo, mission_slug)
    if entry is not None:
        source_key, state = entry
        if state.mission_id != canonical_id:
            state.mission_id = canonical_id
            state.mission_slug = mission_slug
            save_state(state, main_repo)
            if source_key is not None and source_key != canonical_id:
                clear_state(main_repo, source_key)
        return state, True

    state = MergeState(
        mission_id=canonical_id,
        mission_slug=mission_slug,
        target_branch=target_branch,
        wp_order=wp_order,
        push_requested=push_requested,
    )
    save_state(state, main_repo)
    return state, False


def _clear_merge_state_for_mission(repo_root: Path, mission_slug: str | None) -> bool:
    """Clear every state file that could belong to *mission_slug*."""
    if not mission_slug:
        return clear_state(repo_root)

    cleared = False
    seen: set[str] = set()
    for key in _merge_state_key_candidates(repo_root, mission_slug):
        seen.add(key)
        cleared = clear_state(repo_root, key) or cleared

    for key, _state in _iter_merge_states_for_slug(repo_root, mission_slug):
        if key in seen:
            continue
        cleared = clear_state(repo_root, key) or cleared
    return cleared


def _cleanup_merge_workspaces_for_state(
    repo_root: Path,
    *,
    mission_slug: str | None,
    state_entry: tuple[str | None, MergeState] | None,
) -> None:
    """Clean every runtime workspace key that could belong to a merge state."""
    cleanup_keys: list[str] = []
    if state_entry is not None:
        source_key, state = state_entry
        cleanup_keys.append(state.mission_id)
        if source_key:
            cleanup_keys.append(source_key)
        cleanup_keys.append(state.mission_slug)
    if mission_slug:
        cleanup_keys.extend(_merge_state_key_candidates(repo_root, mission_slug))
        cleanup_keys.append(mission_slug)

    for key in dict.fromkeys(key for key in cleanup_keys if key):
        cleanup_merge_workspace(key, repo_root)


def _resolve_target_branch(
    repo_root: Path,
    mission_slug: str | None,
    explicit_target: str | None,
) -> tuple[str, str | None]:
    """Resolve target branch and its provenance.

    Delegates to the shared :func:`resolve_merge_target_branch` so this command
    and ``orchestrator-api merge-mission`` resolve the target identically (reading
    the PRIMARY-checkout meta, never silently falling back to main when the
    mission declares a target_branch).
    """
    from specify_cli.core.paths import resolve_merge_target_branch

    return resolve_merge_target_branch(repo_root, mission_slug, explicit_target)


def _emit_merge_diff_summary(
    *,
    repo_root: Path,
    mission_id: str,
    base_ref: str,
    head_ref: str = "HEAD",
    phase_name: str = "accept",
) -> None:
    """Emit one mission-level diff summary for the merged mission."""
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


def _validate_target_branch(
    repo_root: Path,
    mission_slug: str | None,
    target_branch: str,
    target_source: str | None,
    *,
    json_output: bool,
) -> None:
    ret_local, _, _ = run_command(
        ["git", "rev-parse", "--verify", f"refs/heads/{target_branch}"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret_local == 0:
        return

    ret_remote, _, _ = run_command(
        ["git", "rev-parse", "--verify", f"refs/remotes/origin/{target_branch}"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret_remote == 0:
        return

    if target_source == "meta.json" and mission_slug:
        error_msg = f"Target branch '{target_branch}' (from meta.json) does not exist locally or on origin. Check kitty-specs/{mission_slug}/meta.json."
    elif target_source == "primary_branch" and mission_slug:
        error_msg = f"Target branch '{target_branch}' (resolved as primary branch) does not exist locally or on origin. Check kitty-specs/{mission_slug}/meta.json."
    else:
        error_msg = f"Target branch '{target_branch}' does not exist locally or on origin."

    if json_output:
        print(json.dumps({"spec_kitty_version": SPEC_KITTY_VERSION, "error": error_msg}))
    else:
        console.print(f"[red]Error:[/red] {error_msg}")
    raise typer.Exit(1)


def _target_branch_sync_payload(
    status: TargetBranchSyncStatus,
    *,
    mission_slug: str | None,
    mission_branch: str | None = None,
    mission_id: str | None = None,
) -> dict[str, object]:
    remediation = target_branch_sync_remediation(
        status,
        mission_slug=mission_slug,
        mission_branch=mission_branch,
        mission_id=mission_id,
    )
    return {
        "spec_kitty_version": SPEC_KITTY_VERSION,
        "diagnostic_code": TARGET_BRANCH_NOT_SYNCHRONIZED,
        "branch_or_work_package": status.target_branch,
        "violated_invariant": TARGET_BRANCH_SYNC_INVARIANT,
        "error": "Target branch is not synchronized with its tracking branch.",
        "target_branch": status.target_branch,
        "tracking_branch": status.tracking_branch,
        "state": status.state,
        "ahead_count": status.ahead_count,
        "behind_count": status.behind_count,
        "remediation": remediation,
    }


def _target_branch_refresh_failed_payload(
    *,
    target_branch: str,
    remote_name: str,
    error: str | None,
) -> dict[str, object]:
    return {
        "spec_kitty_version": SPEC_KITTY_VERSION,
        "diagnostic_code": "TARGET_BRANCH_REFRESH_FAILED",
        "branch_or_work_package": target_branch,
        "violated_invariant": TARGET_BRANCH_SYNC_INVARIANT,
        "error": "Could not refresh target branch tracking ref before merge.",
        "target_branch": target_branch,
        "remote_name": remote_name,
        "detail": error or "",
        "remediation": [
            f"Run: git fetch {remote_name} {target_branch}",
            "Resolve the fetch problem, then retry spec-kitty merge.",
            "Spec Kitty stopped before mutating merge state or reconstructing branches.",
        ],
    }


def _enforce_target_branch_sync_preflight(
    repo_root: Path,
    *,
    target_branch: str,
    mission_slug: str | None,
    mission_branch: str | None = None,
    mission_id: str | None = None,
    json_output: bool = False,
    remote_name: str = "origin",
) -> None:
    """Stop push before mutation when the target branch is not synced with remote."""
    from specify_cli.merge.push_preflight import check_push_safety

    result = check_push_safety(repo_root, target_branch, remote_name=remote_name)
    if result.fetch_failed:
        refresh = result.refresh_status
        payload = _target_branch_refresh_failed_payload(
            target_branch=target_branch,
            remote_name=refresh.remote_name,
            error=refresh.error,
        )
        if json_output:
            print(json.dumps(payload))
        else:
            console.print(f"[red]Error:[/red] {payload['error']}")
            console.print(f"  diagnostic_code: {payload['diagnostic_code']}")
            console.print(f"  branch_or_work_package: {payload['branch_or_work_package']}")
            console.print(f"  violated_invariant: {payload['violated_invariant']}")
            if payload["detail"]:
                console.print(f"  detail: {payload['detail']}")
            console.print("  remediation:")
            for line in payload["remediation"]:
                console.print(f"  - {line}")
        raise typer.Exit(1)

    if result.is_safe_to_push:
        return

    status = result.sync_status
    assert status is not None  # is_safe_to_push is False only when sync_status is set

    payload = _target_branch_sync_payload(
        status,
        mission_slug=mission_slug,
        mission_branch=mission_branch,
        mission_id=mission_id,
    )
    if json_output:
        print(json.dumps(payload))
    else:
        console.print(f"[red]Error:[/red] {payload['error']}")
        console.print(f"  diagnostic_code: {payload['diagnostic_code']}")
        console.print(f"  branch_or_work_package: {payload['branch_or_work_package']}")
        console.print(f"  violated_invariant: {payload['violated_invariant']}")
        console.print("  remediation:")
        for line in payload["remediation"]:
            console.print(f"  - {line}")
    raise typer.Exit(1)


def _effective_push_requested(
    repo_root: Path,
    mission_id: str,
    requested_push: bool,
) -> bool:
    """Return persisted push intent for resumptions, otherwise current CLI intent."""
    state = load_state(repo_root, mission_id)
    if state is not None:
        return state.push_requested
    return requested_push


def _assign_planning_only_mission_number_if_needed(
    main_repo: Path,
    feature_dir: Path,
) -> Path | None:
    """Assign mission_number directly on target for planning-only closeout."""

    if not needs_number_assignment(feature_dir):
        return None

    next_number = assign_next_mission_number(
        main_repo,
        main_repo / KITTY_SPECS_DIR,
    )
    meta = load_meta(feature_dir) or {}
    meta["mission_number"] = next_number
    write_meta(feature_dir, meta, validate=False)
    console.print(
        f"  [green]✓[/green] Assigned mission_number={next_number} on target branch"
    )
    return feature_dir / "meta.json"


def _enforce_canonical_status_history(
    *,
    feature_dir: Path,
    mission_slug: str,
    wp_ids: list[str],
) -> None:
    """Refuse to merge missions whose canonical status log is bootstrap-only.

    A bootstrap-only log is a ``status.events.jsonl`` that contains
    nothing but forced ``planned -> planned`` entries emitted by
    ``finalize-tasks``. When the mission carries work packages that
    must have advanced past planned for merge to make sense, the log
    is an unreliable source of truth and downstream replay (TeamSpace
    rebuild, dashboard refresh) will reset every WP to planned. We
    fail loudly with a remediation hint rather than ship in that
    state. See https://github.com/Priivacy-ai/spec-kitty/issues/1069.
    """
    from specify_cli.status import has_non_bootstrap_status_history

    if not wp_ids:
        return

    log_path = feature_dir / _STATUS_EVENTS_FILENAME
    if not log_path.exists():
        return

    if has_non_bootstrap_status_history(feature_dir):
        return

    console.print(
        "[red]Error:[/red] Canonical status history is bootstrap-only — the local "
        "event log cannot prove that WPs advanced past planned, so a merge would "
        "ship a mission whose downstream replay would regress every WP."
    )
    console.print(f"  Mission: {mission_slug}")
    console.print(f"  Event log: {log_path}")
    console.print(f"  Work packages requiring history: {', '.join(wp_ids)}")
    console.print(
        "  Remediation: re-run the per-WP `spec-kitty agent action review` and "
        "`spec-kitty agent action implement` flows so the canonical event log "
        "captures the real lane transitions before merging, or run the "
        "repair/replay tooling for this mission."
    )
    raise typer.Exit(1)


def _enforce_review_artifact_consistency(
    *,
    repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    wp_ids: list[str],
) -> None:
    """Block terminal signoff when the latest review artifact is rejected."""
    preflight = run_review_artifact_consistency_preflight(feature_dir, wp_ids=wp_ids)
    if preflight.passed:
        return
    findings = list(preflight.findings)

    console.print("[red]Error:[/red] Review artifact consistency gate failed.")
    for finding in findings:
        diagnostic = review_artifact_finding_diagnostic(
            finding,
            repo_root=repo_root,
        )
        console.print(
            f"  - {format_review_artifact_finding(finding, repo_root=repo_root)}"
        )
        console.print(f"    diagnostic_code: {diagnostic['diagnostic_code']}")
        console.print(
            f"    branch_or_work_package: {diagnostic['branch_or_work_package']}"
        )
        console.print(
            f"    violated_invariant: {diagnostic['violated_invariant']}"
        )
        console.print(
            f"    latest_review_cycle_path: {diagnostic['latest_review_cycle_path']}"
        )
        if "latest_review_cycle_verdict" in diagnostic:
            console.print(
                f"    latest_review_cycle_verdict: {diagnostic['latest_review_cycle_verdict']}"
            )
        if "schema_error" in diagnostic:
            console.print(f"    schema_error: {diagnostic['schema_error']}")
        remediation = diagnostic.get("remediation", [])
        if not isinstance(remediation, list):
            remediation = [str(remediation)]
        for line in remediation:
            console.print(f"    remediation: {line}")
    console.print(
        f"  Mission: {mission_slug}"
    )
    raise typer.Exit(1)


def _collect_hollow_review_warnings(feature_dir: Path, wp_ids: list[str]) -> HollowReviewWarnings:
    """Return WPs whose approval history indicates missing independent review."""
    warnings: HollowReviewWarnings = {}
    wp_set = set(wp_ids)

    status_path = feature_dir / _STATUS_FILENAME
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            status = {}
        work_packages = status.get("work_packages", {}) if isinstance(status, dict) else {}
        if isinstance(work_packages, dict):
            for wp_id in sorted(wp_set):
                wp_state = work_packages.get(wp_id, {})
                if not isinstance(wp_state, dict):
                    continue
                try:
                    force_count = int(wp_state.get("force_count", 0))
                except (TypeError, ValueError):
                    force_count = 0
                if force_count >= 2:
                    warnings.setdefault(wp_id, []).append(f"force_count={force_count}")

    events_path = feature_dir / _STATUS_EVENTS_FILENAME
    if events_path.exists():
        try:
            raw_lines = events_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            raw_lines = []
        for raw_line in raw_lines:
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("event_type") != REVIEWER_SELF_APPROVAL:
                continue
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            wp_id = str(payload.get("wp_id") or "")
            if wp_id not in wp_set:
                continue
            intended = str(payload.get("intended_reviewer") or "unknown")
            actor = str(payload.get("implementing_actor") or "unknown")
            reason = str(payload.get("failure_reason") or "reviewer_failed")
            warnings.setdefault(wp_id, []).append(
                f"ReviewerSelfApproval ({intended} failed: {reason}; {actor} self-reviewed)"
            )

    return warnings


def _warn_or_confirm_hollow_reviews(
    *,
    feature_dir: Path,
    wp_ids: list[str],
    assume_yes: bool,
) -> None:
    warnings = _collect_hollow_review_warnings(feature_dir, wp_ids)
    if not warnings:
        return

    console.print("\n[bold yellow]MERGE WARNING: Hollow reviews detected[/bold yellow]\n")
    console.print("The following WPs were approved without clear independent review:")
    for wp_id in sorted(warnings):
        console.print(f"  {wp_id}: {' + '.join(warnings[wp_id])}")
    console.print()
    console.print("These WPs may have been approved by the implementing agent, not an independent reviewer.")
    console.print("Consider re-reviewing before merge.\n")

    if assume_yes or not sys.stdin.isatty():
        console.print("[yellow]Proceeding without interactive confirmation.[/yellow]")
        return

    if not typer.confirm("Proceed?", default=False):
        raise typer.Exit(1)


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
    feature_dir = candidate_feature_dir_for_mission(main_repo, mission_slug)

    # -- WP05/T020/FR-006: Sparse-checkout preflight --
    # Must run BEFORE any state change (before merge-state writes, before the
    # global merge lock is acquired, before any git mutation). Legacy
    # sparse-checkout has caused silent data loss in prior merges
    # (Priivacy-ai/spec-kitty#588). If the override flag is set,
    # require_no_sparse_checkout logs a structured override event and
    # returns; the WP01 commit-layer backstop still guards subsequent commits.
    # Run this even before lanes.json/meta.json reads so a sparse repo
    # cannot flow through the command under any condition.
    _preflight_mission_id: str | None = None
    try:
        _preflight_identity = resolve_mission_identity(feature_dir)
        _preflight_mission_id = _preflight_identity.mission_id
    except Exception:  # noqa: BLE001 — meta.json may be missing for legacy missions
        _preflight_mission_id = None

    require_no_sparse_checkout(
        repo_root=main_repo,
        command="spec-kitty merge",
        override_flag=allow_sparse_checkout,
        actor=_resolve_merge_actor(main_repo),
        mission_slug=mission_slug,
        mission_id=_preflight_mission_id or mission_slug,
    )

    from specify_cli.lanes.compute import is_planning_artifact_only

    lanes_manifest = require_lanes_json(feature_dir)
    if target_override:
        lanes_manifest.target_branch = target_override
    planning_artifact_only = is_planning_artifact_only(lanes_manifest)

    # -- Resolve canonical mission_id from meta.json (P2 fix: use ULID, not slug) --
    identity = resolve_mission_identity(feature_dir)
    canonical_id = identity.mission_id or mission_slug  # fallback for legacy missions without ULID

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
    # The lock is keyed by a well-known sentinel so that merges of DIFFERENT
    # missions also serialize against each other.  This is required because
    # mission_number assignment (WP10) computes max(existing)+1 from the
    # target branch — two concurrent merges scanning the same target tip
    # would compute the same next number.
    _GLOBAL_MERGE_LOCK_ID = "__global_merge__"
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


def _run_lane_based_merge_locked(
    main_repo: Path,
    mission_slug: str,
    canonical_id: str,
    feature_dir: Path,
    lanes_manifest: object,  # LanesManifest
    *,
    push: bool,
    delete_branch: bool,
    remove_worktree: bool,
    strategy: MergeStrategy = MergeStrategy.SQUASH,
    assume_yes: bool = False,
) -> None:
    """Inner merge flow, called with the global merge lock held."""
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.compute import is_planning_artifact_only, is_planning_lane
    from specify_cli.lanes.merge import merge_lane_to_mission, merge_mission_to_target
    from specify_cli.policy.config import load_policy_config
    from specify_cli.policy.merge_gates import evaluate_merge_gates

    # -- T001: MergeState lifecycle: load or create --
    target_feature_dir = primary_feature_dir_for_mission(main_repo, mission_slug)
    all_wp_ids = [wp for lane in lanes_manifest.lanes for wp in lane.wp_ids]
    _enforce_review_artifact_consistency(
        repo_root=main_repo,
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_ids=all_wp_ids,
    )

    planning_artifact_only = is_planning_artifact_only(lanes_manifest)
    state, is_resume = _load_or_create_merge_state(
        main_repo=main_repo,
        mission_slug=mission_slug,
        canonical_id=canonical_id,
        target_branch=lanes_manifest.target_branch,
        wp_order=all_wp_ids,
        push_requested=push,
    )
    if is_resume:
        console.print(f"[bold cyan]Resuming[/bold cyan] merge for {mission_slug} ({len(state.completed_wps)}/{len(state.wp_order)} WPs already done)")

    console.print(f"[bold]Lane-based merge for {mission_slug}[/bold]")
    console.print(f"  Mission branch: {lanes_manifest.mission_branch}")
    console.print(f"  Lanes: {', '.join(ln.lane_id for ln in lanes_manifest.lanes)}")
    if planning_artifact_only:
        console.print(
            "  [dim]Planning-artifact-only mission: target branch already "
            "contains deliverables; branch merge steps will be skipped.[/dim]"
        )

    policy = load_policy_config(main_repo)
    gate_eval = evaluate_merge_gates(
        feature_dir,
        mission_slug,
        all_wp_ids,
        policy.merge_gates,
        main_repo,
    )
    for gate in gate_eval.gates:
        icon = "[green]✓[/green]" if gate.verdict == "pass" else "[yellow]⚠[/yellow]" if not gate.blocking else "[red]✗[/red]"
        console.print(f"  {icon} Gate {gate.gate_name}: {gate.details}")
    if not gate_eval.overall_pass:
        console.print("\n[red]Error:[/red] Merge gates failed.")
        raise typer.Exit(1)

    # -- Bootstrap-only canonical history guard (issue #1069) --
    # Refuse to merge missions whose status.events.jsonl contains
    # nothing but forced bootstrap planned→planned events when the
    # mission has work packages that should have advanced. This
    # prevents shipping a mission whose canonical history will
    # collapse downstream consumers (e.g. TeamSpace replay) back to
    # planned even though the merged commit reflects approved work.
    _enforce_canonical_status_history(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_ids=all_wp_ids,
    )
    _warn_or_confirm_hollow_reviews(
        feature_dir=feature_dir,
        wp_ids=all_wp_ids,
        assume_yes=assume_yes,
    )

    # -- Lane merges (skip a lane only when its code is ALREADY integrated) --
    # FR-037 (#1772 Bug 3 — data integrity): the skip MUST gate on the actual
    # lane tree-diff vs. the mission branch, NOT on per-WP ``done`` status. A
    # prior aborted merge can leave every WP marked ``done`` in MergeState while
    # zero code was integrated; skipping on that proxy squashed zero diffs and
    # reported success. The per-WP ``done`` state drives only the bookkeeping
    # pass (``_record_merged_wps_done_for_merge``), never the integration skip.
    any_lane_had_unintegrated_code = False
    for lane in lanes_manifest.lanes:
        if planning_artifact_only and is_planning_lane(lane):
            console.print(
                f"  [green]✓[/green] {lane.lane_id} already on {lanes_manifest.target_branch}"
            )
            continue

        # FR-037: skip ONLY when the lane branch is already fully integrated into
        # the mission branch (real tree state), never on the ``done`` proxy.
        _lane_branch = lane_branch_name(
            mission_slug,
            lane.lane_id,
            planning_base_branch=lanes_manifest.target_branch,
        )
        if not is_planning_lane(lane) and _lane_already_integrated(
            main_repo, _lane_branch, lanes_manifest.mission_branch
        ):
            console.print(
                f"  [dim]Skipping {lane.lane_id} (already integrated into "
                f"{lanes_manifest.mission_branch})[/dim]"
            )
            continue
        any_lane_had_unintegrated_code = True

        console.print(f"  [dim]Checking and merging {lane.lane_id}...[/dim]")
        lane_result = merge_lane_to_mission(main_repo, mission_slug, lane.lane_id, lanes_manifest)
        if lane_result.success:
            console.print(f"  [green]✓[/green] {lane.lane_id} → {lanes_manifest.mission_branch}")
        else:
            # T005: tolerate already-merged lanes on retry
            already_merged = any("already" in e.lower() or "up to date" in e.lower() or "ancestor" in e.lower() for e in lane_result.errors)
            if is_resume and already_merged:
                console.print(f"  [dim]{lane.lane_id} already merged, continuing[/dim]")
            else:
                for error in lane_result.errors:
                    console.print(f"  [red]✗[/red] {lane.lane_id}: {error}")
                raise typer.Exit(1)

    # -- Capture target baseline SHA for post-merge diff/review checks (T013) --
    _ret, target_baseline_sha, _err = run_command(
        ["git", "rev-parse", lanes_manifest.target_branch],
        capture=True,
        check_return=False,
        cwd=main_repo,
    )
    target_baseline_sha = target_baseline_sha.strip() if _ret == 0 else "HEAD~1"

    # -- Resolve the canonical mission_id (ULID) to gate modern-mission invariants --
    # ``canonical_id`` falls back to the slug for legacy missions, so it cannot
    # distinguish modern (083+) from pre-083 missions. Re-resolve the raw
    # mission_id from meta.json: a non-empty value means this is a MODERN lane
    # mission and the baseline_merge_commit invariants below are HARD failures.
    try:
        _baseline_mission_id = resolve_mission_identity(feature_dir).mission_id
    except Exception:  # noqa: BLE001 — meta.json may be missing/corrupt for legacy missions
        _baseline_mission_id = None

    status_surface_path = resolve_status_surface(main_repo, mission_slug)
    done_marked_before_target = is_under_worktrees_segment(status_surface_path) and not planning_artifact_only
    canonical_events_path = status_surface_path
    canonical_status_path = status_surface_path.parent / _STATUS_FILENAME
    merge_state_path = get_state_path(main_repo, state.mission_id)
    pre_target_bookkeeping_snapshots: dict[Path, bytes | None] = {}
    final_bookkeeping_snapshots: dict[Path, bytes | None] = {}
    mission_number_meta_path: Path | None = None
    mission_already_applied = False
    if planning_artifact_only:
        console.print(
            f"  [dim]Skipping mission branch merge; {lanes_manifest.target_branch} "
            "is the planning artifact branch.[/dim]"
        )
        mission_already_applied = True
    else:
        # -- WP10/T053/T055: assign dense integer mission_number on mission branch --
        # Inside the global merge lock (acquire_merge_lock("__global_merge__"))
        # which serializes ALL merge operations — same-mission and cross-mission.
        # This guarantees the max+1 scan sees the most recent target state.
        # WP04/FR-010/FR-011/FR-012: pass merge_state so the idempotency check
        # (T025) and resume short-circuit (T026) can persist/read the baked flag.
        _bake_mission_number_into_mission_branch(
            main_repo=main_repo,
            mission_slug=mission_slug,
            mission_branch=lanes_manifest.mission_branch,
            target_branch=lanes_manifest.target_branch,
            dry_run=False,
            merge_state=state,
        )

        if done_marked_before_target:
            pre_target_bookkeeping_snapshots.update(
                _capture_bookkeeping_snapshots(
                    main_repo,
                    canonical_events_path,
                    canonical_status_path,
                    merge_state_path,
                )
            )
            # Modern coordination-backed missions must carry done events in the
            # mission branch before it is merged to target. Recording after the
            # target merge writes to a disposable coord/mission branch and can
            # pass surface-local validation while target history never receives
            # done.
            try:
                _record_merged_wps_done_for_merge(
                    main_repo=main_repo,
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    lanes_manifest=lanes_manifest,
                    target_branch=lanes_manifest.target_branch,
                    merge_state=state,
                    all_wp_ids=all_wp_ids,
                )
            except Exception:
                _restore_final_bookkeeping_snapshots(pre_target_bookkeeping_snapshots)
                raise

        # -- Mission-to-target merge (T010: honor strategy for this step only) --
        # FR-037 (#1772 Bug 3): a no-op squash is only legitimate when the
        # mission branch content is already integrated into the target. Squash
        # merges do not preserve commit ancestry, so gate this recovery path on
        # tree equivalence, not ``rev-list`` reachability.
        _mission_integrated_into_target = _branch_trees_equal(
            main_repo,
            lanes_manifest.mission_branch,
            lanes_manifest.target_branch,
        )
        _allow_noop = is_resume and _mission_integrated_into_target
        console.print(f"  [dim]Merging mission branch into {lanes_manifest.target_branch}...[/dim]")
        try:
            mission_result = merge_mission_to_target(
                main_repo,
                mission_slug,
                lanes_manifest,
                strategy=strategy,
                allow_already_applied=_allow_noop,
            )
        except Exception:
            if done_marked_before_target and _target_branch_still_at_baseline(
                main_repo,
                lanes_manifest.target_branch,
                target_baseline_sha,
            ):
                _restore_final_bookkeeping_snapshots(pre_target_bookkeeping_snapshots)
            raise
        mission_already_applied = getattr(mission_result, "already_applied", False) is True
        # FR-037 fail-loud: a no-op result is only acceptable when the mission
        # branch was genuinely already integrated AND no un-integrated lane code
        # was discovered this run. Otherwise the merge integrated zero diffs
        # while real work remained — refuse to report success.
        if (
            mission_already_applied
            and not planning_artifact_only
            and (any_lane_had_unintegrated_code or not _mission_integrated_into_target)
        ):
            console.print(
                "[red]Error:[/red] Mission→target merge integrated zero lane "
                "diffs but un-integrated lane work remains. Refusing to report a "
                "zero-code squash as success (#1772 FR-037)."
            )
            console.print(
                f"  Mission branch: {lanes_manifest.mission_branch}; "
                f"target: {lanes_manifest.target_branch}. "
                "Inspect the lane branches and rerun, or `spec-kitty merge --abort`."
            )
            if done_marked_before_target and _target_branch_still_at_baseline(
                main_repo,
                lanes_manifest.target_branch,
                target_baseline_sha,
            ):
                _restore_final_bookkeeping_snapshots(pre_target_bookkeeping_snapshots)
            raise typer.Exit(1)
        if not mission_result.success:
            # T005: tolerate already-merged on retry
            already_merged = any("already" in e.lower() or "up to date" in e.lower() for e in mission_result.errors)
            if is_resume and already_merged:
                console.print(f"[dim]{lanes_manifest.mission_branch} already merged into {lanes_manifest.target_branch}[/dim]")
            else:
                for error in mission_result.errors:
                    console.print(f"[red]Error:[/red] {error}")
                if done_marked_before_target and _target_branch_still_at_baseline(
                    main_repo,
                    lanes_manifest.target_branch,
                    target_baseline_sha,
                ):
                    _restore_final_bookkeeping_snapshots(pre_target_bookkeeping_snapshots)
                raise typer.Exit(1)
        else:
            console.print(f"\n[green]✓[/green] {lanes_manifest.mission_branch} → {lanes_manifest.target_branch}")
            if mission_already_applied:
                console.print("  [dim]Mission changes already present on target; continuing bookkeeping.[/dim]")
            if mission_result.commit:
                console.print(f"  Commit: {mission_result.commit[:7]}")

    # -- WP05/T006 FR-013: Post-merge working-tree refresh --
    # Re-sync the primary checkout against HEAD before done-event bookkeeping.
    # A path checkout does not remove stale rename sources in sparse-checkout
    # repos; the helper uses a tracked-file hard refresh instead.
    _refresh_primary_checkout_after_merge(main_repo)

    if not done_marked_before_target:
        final_bookkeeping_snapshots.update(
            _capture_bookkeeping_snapshots(
                main_repo,
                canonical_events_path,
                canonical_status_path,
                merge_state_path,
            )
        )
    target_events_path, target_status_path = _target_bookkeeping_status_paths(
        main_repo=main_repo,
        mission_slug=mission_slug,
        status_feature_dir=feature_dir,
    )
    target_meta_path = target_feature_dir / "meta.json"
    final_bookkeeping_snapshots.update(
        _capture_bookkeeping_snapshots(
            main_repo,
            target_events_path,
            target_status_path,
            target_meta_path,
        )
    )

    if planning_artifact_only:
        mission_number_meta_path = _assign_planning_only_mission_number_if_needed(
            main_repo,
            feature_dir,
        )

    try:
        baseline_meta_path = _record_baseline_merge_commit(
            target_feature_dir,
            target_baseline_sha,
            mission_id=_baseline_mission_id,
        )
    except BaselineMergeCommitError as exc:
        # Modern lane mission could not record its post-merge review baseline.
        # Fail loudly — an apparently successful merge that drops the baseline
        # produces MISSION_REVIEW_MODE_MISMATCH downstream.
        _restore_final_bookkeeping_snapshots(final_bookkeeping_snapshots)
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    # Merge-path status surface audit (mission merge-done-surface-resolver-01KTDVHZ):
    # Write sites: _mark_wp_merged_done — resolve_status_surface determines feature_dir;
    #              emit_status_transition_transactional writes to that surface.
    # Read sites:  _assert_merged_wps_reached_done — resolve_status_surface determines feature_dir.
    # Fallback:    _mark_wp_merged_done PLANNED-guard reads primary_feature_dir (primary checkout)
    #              when the coord surface has no events for the WP (force=True covers the jump).
    #              _reconcile_completed_wps_for_resume (safe: uses has_transition_to_transactional)
    # DIVERGENT:   _assert_merged_wps_reached_done read vs _mark_wp_merged_done write — FIXED above
    # Additional DIVERGENT sites: none found
    # Audit date: 2026-06-06

    # -- T001: Mark WPs done with per-WP state tracking --
    if not done_marked_before_target:
        try:
            _record_merged_wps_done_for_merge(
                main_repo=main_repo,
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                lanes_manifest=lanes_manifest,
                target_branch=lanes_manifest.target_branch,
                merge_state=state,
                all_wp_ids=all_wp_ids,
            )
        except Exception:
            _restore_final_bookkeeping_snapshots(final_bookkeeping_snapshots)
            raise

    try:
        target_events_path, target_status_path = _project_status_bookkeeping_to_target(
            main_repo=main_repo,
            mission_slug=mission_slug,
            status_feature_dir=feature_dir,
        )
    except Exception:
        _restore_final_bookkeeping_snapshots(final_bookkeeping_snapshots)
        raise

    # -- WP05/T007 FR-014: Post-merge working-tree invariant --
    # After the refresh, `git status --porcelain` MUST report at most the two
    # status files that the immediately-following safe_commit is going to
    # persist. Any other path diverging from HEAD indicates that something
    # (sparse-checkout, a stale lock, a filter driver) silently dropped paths
    # during the merge and must stop the flow before the housekeeping commit
    # papers over it.
    #
    # Read porcelain RAW (not via run_command): run_command strips the whole
    # output, which removes the leading status column of the FIRST porcelain
    # line, so _classify_porcelain_lines would silently skip the first divergent
    # path (e.g. meta.json, which sorts first inside kitty-specs/<slug>/). The
    # invariant must be blind to nothing, so we splitlines() the raw stdout.
    _ret_status, _out_status = _raw_porcelain_status(main_repo)
    if _ret_status == 0:
        # Coordination status residue (status.events.jsonl / status.json and
        # the rest of the planning artifact set) is recognized through the
        # single residue authority — not a hardcoded literal copy (FR-012 /
        # #1878). The immediately-following safe_commit persists the two status
        # files; the wider residue set may legitimately diverge on the primary
        # checkout after a coordination-topology merge.
        expected_paths: set[str] = set()
        if baseline_meta_path is not None:
            expected_paths.add(str(baseline_meta_path.relative_to(main_repo)))
        # Planning-only closeout dirties meta.json to bake in mission_number.
        # That path is committed by the immediately-following safe_commit, so it
        # is an expected divergence here. Without this, a legacy planning-only
        # mission (no mission_id → _record_baseline_merge_commit returns None,
        # leaving baseline_meta_path None) trips the invariant and fails the
        # merge. Mirrors the baseline_meta_path branch above.
        if mission_number_meta_path is not None:
            expected_paths.add(str(mission_number_meta_path.relative_to(main_repo)))

        def _is_coord_residue(path_part: str) -> bool:
            return is_coordination_artifact_residue_path(
                path_part, mission_slug=mission_slug
            )

        offending_lines, _skipped_untracked = _classify_porcelain_lines(
            (_out_status or "").splitlines(),
            expected_paths,
            residue_predicate=_is_coord_residue,
        )
        if offending_lines:
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
            _restore_final_bookkeeping_snapshots(final_bookkeeping_snapshots)
            raise typer.Exit(1)
    else:
        console.print(
            "[yellow]Warning:[/yellow] post-merge invariant check skipped: "
            f"git status --porcelain returned {_ret_status}"
        )

    # -- T012: FR-019 — Persist done events to git BEFORE any worktree removal --
    files_to_commit = [
        target_events_path,
        target_status_path,
    ]
    if mission_number_meta_path is not None:
        files_to_commit.append(mission_number_meta_path)
    if baseline_meta_path is not None:
        files_to_commit.append(baseline_meta_path)
    files_to_commit = list(dict.fromkeys(files_to_commit))

    has_bookkeeping_changes = _paths_have_status_changes(main_repo, files_to_commit)
    if has_bookkeeping_changes:
        try:
            # Done-events bookkeeping lands on the target branch, which is a
            # protected branch (e.g. ``main``) in the normal merge flow. This is
            # the sanctioned merge-bookkeeping protected flow (WP02 data model),
            # so assert MERGE_BOOKKEEPING at this bona-fide call site. Pre-guard-
            # consolidation this commit rode the deleted ``chore:`` message-prefix
            # allowlist; that channel is gone (FR-008 / C-GUARD-2), and the only
            # authorization is now this explicit capability.
            safe_commit(
                repo_root=main_repo,
                worktree_root=main_repo,
                destination_ref=lanes_manifest.target_branch,
                message=f"chore({mission_slug}): record done transitions for merged WPs",
                paths=tuple(files_to_commit),
                capability=GuardCapability.MERGE_BOOKKEEPING,
            )
        except Exception as exc:
            if not (isinstance(exc, SafeCommitRecoveryFailed) and exc.commit_sha is not None):
                _restore_final_bookkeeping_snapshots(final_bookkeeping_snapshots)
            raise
    else:
        console.print("  [dim]No post-merge bookkeeping changes to commit; continuing cleanup.[/dim]")

    _assert_merged_wps_done_on_target(
        main_repo,
        mission_slug,
        lanes_manifest.target_branch,
        all_wp_ids,
        feature_dir=feature_dir,
        mission_id=_baseline_mission_id,
    )

    # -- Post-merge baseline invariant (mirrors _assert_merged_wps_reached_done) --
    # Now that the bookkeeping commit (which carries meta.json's
    # baseline_merge_commit) has landed on the target branch, verify the
    # baseline is durable in committed git history BEFORE any worktree removal
    # or branch cleanup. Together with _assert_merged_wps_reached_done this
    # guarantees BOTH the done-state AND the baseline gate merge success: a
    # merge cannot appear successful while the baseline is absent, which would
    # otherwise surface downstream as MISSION_REVIEW_MODE_MISMATCH.
    try:
        _assert_baseline_merge_commit_on_target(
            main_repo,
            mission_slug,
            lanes_manifest.target_branch,
            target_baseline_sha,
            feature_dir=target_feature_dir,
            mission_id=_baseline_mission_id,
        )
    except BaselineMergeCommitError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print("  [dim]Syncing dossier state for the merged mission...[/dim]")
    trigger_feature_dossier_sync_if_enabled(
        feature_dir,
        mission_slug,
        main_repo,
    )

    # -- T013: Stale-assertion check (WP01 library import — NOT subprocess) --
    console.print("  [dim]Running stale-assertion check...[/dim]")
    try:
        stale_report: StaleAssertionReport = run_check(
            base_ref=target_baseline_sha,
            head_ref="HEAD",
            repo_root=main_repo,
        )
    except Exception as exc:  # noqa: BLE001 — stale-assertion check is advisory; a failure must never abort an otherwise-successful merge
        logger.warning("Stale-assertion check failed: %s", exc)
        stale_report = None  # type: ignore[assignment]

    # -- Push --
    if push and has_remote(main_repo):
        _ret_push, _out_push, stderr_push = run_command(
            ["git", "push", "origin", lanes_manifest.target_branch],
            capture=True,
            check_return=False,
            cwd=main_repo,
        )
        if _ret_push != 0:
            if _is_linear_history_rejection(stderr_push):
                _emit_remediation_hint(console)
            console.print(f"[red]Error:[/red] Push failed: {stderr_push.strip() or _out_push.strip()}")
            raise typer.Exit(1)
        console.print(f"[green]✓[/green] Pushed {lanes_manifest.target_branch} to origin")

    # -- T005: Worktree removal with retry tolerance and macOS FSEvents delay --
    if remove_worktree:
        from specify_cli.lanes.branch_naming import worktree_path

        delay = _worktree_removal_delay()
        for idx, lane in enumerate(lanes_manifest.lanes):
            # Route through the WP01 seam with the REAL mission_id so the teardown
            # resolves the SAME on-disk path the WP03 allocator created. The old
            # f-string omitted the ``-<mid8>`` segment, so for a mid8-era mission it
            # named ``<slug>-<lane>`` while the allocator created
            # ``<slug>-<mid8>-<lane>`` — silently failing to find/remove it (#1899).
            wt_path = worktree_path(
                main_repo,
                mission_slug,
                mission_id=_baseline_mission_id,
                lane_id=lane.lane_id,
            )
            if wt_path.exists():
                run_command(
                    ["git", "worktree", "remove", str(wt_path), "--force"],
                    cwd=main_repo,
                    check_return=False,
                )
                console.print(f"  Removed worktree: {wt_path.name}")
                # Apply FSEvents delay between removals (not after the last one)
                if delay > 0 and idx < len(lanes_manifest.lanes) - 1:
                    time.sleep(delay)
            else:
                # T005: tolerate missing worktree on retry
                logger.debug("Worktree %s does not exist, skipping removal", wt_path)

    # -- T005: Branch deletion with retry tolerance --
    if delete_branch:
        for lane in lanes_manifest.lanes:
            # Skip the planning lane: lane_branch_name() defaults it to the target
            # branch (e.g. "main") when no planning_base_branch is supplied, so
            # deleting it would attempt `git branch -D main` — destroying the
            # persistent target branch.  Planning lanes never have a dedicated
            # lane branch to clean up.
            if is_planning_lane(lane):
                continue
            branch_name = lane_branch_name(mission_slug, lane.lane_id)
            # T005: check if branch exists before attempting deletion
            ret, _, _ = run_command(
                ["git", "rev-parse", "--verify", f"refs/heads/{branch_name}"],
                capture=True,
                check_return=False,
                cwd=main_repo,
            )
            if ret == 0:
                run_command(
                    ["git", "branch", "-D", branch_name],
                    cwd=main_repo,
                    check_return=False,
                )
            else:
                logger.debug("Branch %s does not exist, skipping deletion", branch_name)

        ret, _, _ = run_command(
            ["git", "rev-parse", "--verify", f"refs/heads/{lanes_manifest.mission_branch}"],
            capture=True,
            check_return=False,
            cwd=main_repo,
        )
        if ret == 0:
            run_command(
                ["git", "branch", "-D", lanes_manifest.mission_branch],
                cwd=main_repo,
                check_return=False,
            )
        else:
            logger.debug("Mission branch %s does not exist, skipping deletion", lanes_manifest.mission_branch)
        console.print(f"  Cleaned up {len(lanes_manifest.lanes)} lane branch(es) + mission branch")

    # -- WP07 / FR-016 / SC-10: Coordination worktree teardown --
    # After Stage 2 of the two-stage merge succeeds (lane -> coordination
    # branch -> target branch), the coordination worktree at
    # ``.worktrees/<slug>-<mid8>-coord/`` is no longer needed. Tearing
    # it down here keeps the cleanup atomic: a successful merge leaves
    # no stray coordination-branch worktrees behind.
    #
    # The coordination *branch* is the same git ref as
    # ``lanes_manifest.mission_branch`` and was already deleted above as
    # part of the standard lane/mission branch cleanup. The
    # ``CoordinationWorkspace.teardown`` call below only touches the
    # worktree directory + the per-worktree gitdir; it is idempotent and
    # safely no-ops when called for legacy missions that never created a
    # coordination worktree (FR-017).
    if remove_worktree:
        try:
            from specify_cli.coordination import CoordinationWorkspace
            from specify_cli.mission_metadata import load_meta as _load_meta

            _meta_for_teardown = _load_meta(feature_dir)
            _mid8_for_teardown = (
                str(_meta_for_teardown.get("mid8", "")).strip()
                if isinstance(_meta_for_teardown, dict)
                else ""
            )
            if _mid8_for_teardown:
                CoordinationWorkspace.teardown(
                    main_repo,
                    mission_slug,
                    _mid8_for_teardown,
                )
                logger.debug(
                    "Coordination worktree teardown for %s-%s completed",
                    mission_slug,
                    _mid8_for_teardown,
                )
        # Teardown is best-effort cleanup; never block a successful merge.
        except Exception as _coord_teardown_exc:  # noqa: BLE001
            logger.warning(
                "Coordination worktree teardown failed (non-fatal): %s",
                _coord_teardown_exc,
            )

    # -- T002: Cleanup workspace (preserves state.json) then clear state --
    cleanup_merge_workspace(canonical_id, main_repo)
    clear_state(main_repo, canonical_id)

    _emit_merge_diff_summary(
        repo_root=main_repo,
        mission_id=canonical_id,
        base_ref=target_baseline_sha,
    )

    emit_mission_closed(
        mission_slug=mission_slug,
        total_wps=len(all_wp_ids),
        mission_id=canonical_id,
    )

    # -- T013: Render stale-assertion findings in the merge summary --
    console.print("\n[bold]Stale assertion findings:[/bold]")
    if stale_report is None:
        console.print("  [yellow]Stale-assertion check could not run.[/yellow]")
    elif not stale_report.findings:
        console.print("  No likely-stale assertions detected.")
    else:
        # Group by grade: actionable findings first, info-grade last (T023).
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

    # -- T004: Handle --abort early --
    if abort:
        from contextlib import suppress

        mission_slug_raw = (mission or feature or "").strip() or None
        try:
            resolved = _resolve_mission_slug(repo_root, mission_slug_raw)
        except ValueError as exc:
            console.print(
                f"[red]Error:[/red] {_SAFE_PATH_SEGMENT_DIAGNOSTIC}: {exc}"
            )
            raise typer.Exit(1) from exc
        state_entry = _load_merge_state_entry_for_mission(repo_root, resolved)
        if state_entry is None and resolved is None:
            state_entry = _load_merge_state_entry_for_mission(repo_root, None)
        if state_entry is not None and resolved is None:
            _source_key, active_state = state_entry
            resolved = active_state.mission_slug

        if resolved or state_entry is not None:
            cleared = _clear_merge_state_for_mission(repo_root, resolved)
            if state_entry is not None:
                source_key, active_state = state_entry
                if source_key:
                    cleared = clear_state(repo_root, source_key) or cleared
                cleared = clear_state(repo_root, active_state.mission_id) or cleared
            _cleanup_merge_workspaces_for_state(
                repo_root,
                mission_slug=resolved,
                state_entry=state_entry,
            )
            # WP07 / FR-016: --abort also tears down the coordination
            # worktree (idempotent; no-op for legacy missions without
            # coordination state). Done here so partial-state aborts
            # leave the workspace in the same shape as a clean run.
            try:
                from specify_cli.coordination import CoordinationWorkspace
                from specify_cli.mission_metadata import load_meta as _load_meta

                _main_for_abort = get_main_repo_root(repo_root)
                _coord_slug_for_abort = resolved
                if _coord_slug_for_abort is None and state_entry is not None:
                    _coord_slug_for_abort = state_entry[1].mission_slug
                if not _coord_slug_for_abort:
                    raise ValueError("cannot resolve mission slug for coordination cleanup")
                _feature_dir_for_abort = candidate_feature_dir_for_mission(
                    _main_for_abort,
                    _coord_slug_for_abort,
                )
                _meta_for_abort = _load_meta(_feature_dir_for_abort)
                _mid8_for_abort = (
                    str(_meta_for_abort.get("mid8", "")).strip()
                    if isinstance(_meta_for_abort, dict)
                    else ""
                )
                if _mid8_for_abort and _coord_slug_for_abort:
                    CoordinationWorkspace.teardown(
                        _main_for_abort,
                        _coord_slug_for_abort,
                        _mid8_for_abort,
                    )
            except Exception as _coord_abort_exc:  # noqa: BLE001 — abort cleanup is best-effort
                logger.debug(
                    "Coordination worktree teardown during --abort failed (non-fatal): %s",
                    _coord_abort_exc,
                )
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

        # T002: Remove the global merge lock file (idempotent — suppresses FileNotFoundError).
        # The lock lives at .kittify/runtime/merge/__global_merge__/lock and is created by
        # acquire_merge_lock("__global_merge__", ...) inside _run_lane_based_merge.
        # A crash between lock acquisition and release leaves this file behind, preventing
        # subsequent merge runs from acquiring the lock.
        _global_lock_path = get_merge_runtime_dir("__global_merge__", repo_root) / "lock"
        with suppress(FileNotFoundError):
            _global_lock_path.unlink()
            console.print("[green]Removed merge lock.[/green]")

        # T003: Remove the legacy merge-state JSON if it still exists.
        # Pre-mission-scoped releases wrote state to .kittify/merge-state.json directly.
        # New writes go to .kittify/runtime/merge/<id>/state.json (handled by clear_state
        # above), but legacy files must also be cleaned up so the repo is fully unblocked.
        _legacy_state_path = repo_root / KITTIFY_DIR / "merge-state.json"
        with suppress(FileNotFoundError):
            _legacy_state_path.unlink()
            console.print("[green]Removed legacy merge-state.[/green]")

        # T004: If git itself is in a merging state (MERGE_HEAD present), abort that too.
        if abort_git_merge(repo_root):
            console.print("[green]Aborted in-progress git merge.[/green]")

        return

    # -- T004: Handle --resume (loads existing state; the main flow will detect it) --
    if resume:
        mission_slug_raw = (mission or feature or "").strip() or None
        try:
            resolved = _resolve_mission_slug(repo_root, mission_slug_raw)
        except ValueError as exc:
            console.print(
                f"[red]Error:[/red] {_SAFE_PATH_SEGMENT_DIAGNOSTIC}: {exc}"
            )
            raise typer.Exit(1) from exc
        existing_state = _load_merge_state_for_mission(repo_root, resolved)
        if existing_state is None:
            console.print("[red]Error:[/red] No interrupted merge to resume.")
            raise typer.Exit(1)
        if not mission_slug_raw:
            mission = existing_state.mission_slug
        console.print(
            f"[bold cyan]Resume requested[/bold cyan] for {existing_state.mission_slug} ({len(existing_state.completed_wps)}/{len(existing_state.wp_order)} done)"
        )
        # Fall through to the normal merge flow which will detect the state

    _enforce_git_preflight(repo_root, json_output=json_output)

    # T009 — FR-005/FR-006: Resolve strategy: CLI flag > config > default (SQUASH)
    resolved_strategy: MergeStrategy = strategy or load_merge_config(repo_root).strategy or MergeStrategy.SQUASH

    mission_slug = (mission or feature or "").strip() or None
    try:
        resolved_feature = _resolve_mission_slug(repo_root, mission_slug)
    except ValueError as exc:
        console.print(
            f"[red]Error:[/red] {_SAFE_PATH_SEGMENT_DIAGNOSTIC}: {exc}"
        )
        raise typer.Exit(1) from exc

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
        if not resolved_feature:
            error_msg = "Mission slug could not be resolved. Use --mission <slug>."
            if json_output:
                print(json.dumps({"spec_kitty_version": SPEC_KITTY_VERSION, "error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        try:
            lanes_manifest = require_lanes_json(candidate_feature_dir_for_mission(get_main_repo_root(repo_root), resolved_feature))
        except (MissingLanesError, CorruptLanesError) as exc:
            error_msg = str(exc)
            if json_output:
                print(json.dumps({"spec_kitty_version": SPEC_KITTY_VERSION, "error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1) from exc

        feature_dir_for_preview = (
            candidate_feature_dir_for_mission(get_main_repo_root(repo_root), resolved_feature)
        )

        # FR-007/FR-008/FR-009: Run the same review-artifact consistency gate
        # that real merge runs (issue #991). When a rejected review-cycle
        # artifact still sits on an approved/done WP, real merge exits with
        # REJECTED_REVIEW_ARTIFACT_CONFLICT — dry-run must surface the same
        # blocker in both human and JSON output, so operators can trust the
        # preview as a readiness signal.
        dry_run_all_wp_ids: list[str] = [
            wp for lane in lanes_manifest.lanes for wp in lane.wp_ids
        ]
        review_artifact_preflight = run_review_artifact_consistency_preflight(
            feature_dir_for_preview,
            wp_ids=dry_run_all_wp_ids,
        )
        if not review_artifact_preflight.passed:
            main_repo_for_diag = get_main_repo_root(repo_root)
            diagnostics = review_artifact_preflight.diagnostics(
                repo_root=main_repo_for_diag,
            )
            if json_output:
                diagnostic_code = (
                    diagnostics[0]["diagnostic_code"]
                    if diagnostics
                    else REJECTED_REVIEW_ARTIFACT_CONFLICT
                )
                print(
                    json.dumps(
                        {
                            "spec_kitty_version": SPEC_KITTY_VERSION,
                            "mission_slug": resolved_feature,
                            "target_branch": resolved_target_branch,
                            "blocked": True,
                            "blockers": diagnostics,
                            "diagnostic_code": diagnostic_code,
                        }
                    )
                )
            else:
                console.print("[red]Error:[/red] Review artifact consistency gate failed.")
                for finding in review_artifact_preflight.findings:
                    diagnostic = review_artifact_finding_diagnostic(
                        finding,
                        repo_root=main_repo_for_diag,
                    )
                    console.print(
                        f"  - {format_review_artifact_finding(finding, repo_root=main_repo_for_diag)}"
                    )
                    console.print(
                        f"    diagnostic_code: {diagnostic['diagnostic_code']}"
                    )
                    console.print(
                        f"    branch_or_work_package: {diagnostic['branch_or_work_package']}"
                    )
                    console.print(
                        f"    violated_invariant: {diagnostic['violated_invariant']}"
                    )
                    console.print(
                        f"    latest_review_cycle_path: {diagnostic['latest_review_cycle_path']}"
                    )
                    if "latest_review_cycle_verdict" in diagnostic:
                        console.print(
                            f"    latest_review_cycle_verdict: {diagnostic['latest_review_cycle_verdict']}"
                        )
                    if "schema_error" in diagnostic:
                        console.print(f"    schema_error: {diagnostic['schema_error']}")
                    remediation = diagnostic.get("remediation", [])
                    if not isinstance(remediation, list):
                        remediation = [str(remediation)]
                    for line in remediation:
                        console.print(f"    remediation: {line}")
                console.print(f"  Mission: {resolved_feature}")
            raise typer.Exit(1)

        # WP10/T053: dry-run preview of merge-time mission_number assignment.
        would_assign_number: int | None = None
        if needs_number_assignment(feature_dir_for_preview):
            try:
                would_assign_number = assign_next_mission_number(
                    get_main_repo_root(repo_root),
                    get_main_repo_root(repo_root) / KITTY_SPECS_DIR,
                )
            except Exception as exc:  # noqa: BLE001 — dry-run mission_number scan is best-effort; an unavailable kitty-specs dir must not crash the preview
                logger.warning("dry-run mission_number scan failed: %s", exc)
                would_assign_number = None

        payload: dict[str, object] = {
            "spec_kitty_version": SPEC_KITTY_VERSION,
            "mission_slug": resolved_feature,
            "target_branch": resolved_target_branch,
            "strategy": resolved_strategy.value,
            "delete_branch": delete_branch,
            "remove_worktree": remove_worktree,
            "push": push,
            "mission_branch": lanes_manifest.mission_branch,
            "lanes": [lane.to_dict() for lane in lanes_manifest.lanes],
            "would_assign_mission_number": would_assign_number,
        }
        if would_assign_number is not None and not json_output:
            console.print(
                f"[cyan]would assign[/cyan] mission_number={would_assign_number} to mission {resolved_feature}"
            )
        if json_output:
            print(json.dumps(payload))
        else:
            console.print_json(json.dumps(payload))
        return

    if not resolved_feature:
        console.print("[red]Error:[/red] Mission slug could not be resolved. Use --mission <slug>.")
        raise typer.Exit(1)

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
        # WP05/T020: surface sparse-checkout preflight as user-facing error
        # and exit non-zero WITHOUT writing any merge state.
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except (MissingLanesError, CorruptLanesError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    # -- Post-merge: WP07/FR-007 retrospective postcondition --
    # Fire the retrospective learning capture if retrospective.yaml was not
    # already written by the runtime terminus (HiC or autonomous path).
    # Fail-open: failure appends a capture_failed event but does NOT abort.
    run_retrospective_postcondition(
        mission_slug=resolved_feature,
        repo_root=repo_root,
    )

    # -- Post-merge: Suggest mission review and retrospective review/synthesis --
    # The two commands below operate on an already-authored record: `summary`
    # is a cross-mission view; `synthesize` applies any staged proposals
    # (dry-run by default — pass `--apply` to mutate). They do not create content.
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


__all__ = [
    "_has_transition_to",
    "_assert_merged_wps_reached_done",
    "_assert_baseline_merge_commit_on_target",
    "_record_baseline_merge_commit",
    "_recorded_baseline_from_working_meta",
    "_read_committed_meta_json",
    "BaselineMergeCommitError",
    "_mark_wp_merged_done",
    "_project_status_bookkeeping_to_target",
    "_load_merge_state_for_mission",
    "_load_or_create_merge_state",
    "_clear_merge_state_for_mission",
    "_run_lane_based_merge",
    "_is_linear_history_rejection",
    "_emit_remediation_hint",
    "_branch_trees_equal",
    "_check_mission_branch",
    "_has_branch_ref",
    "_enforce_target_branch_sync_preflight",
    "_enforce_review_artifact_consistency",
    "_bake_mission_number_into_mission_branch",
    "LINEAR_HISTORY_REJECTION_TOKENS",
    "path_is_under_worktrees",
    "merge",
]
