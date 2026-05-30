"""Merge command implementation.

Lane worktrees are the only supported execution topology. Merge always follows
the same two-step flow:
1. Merge each lane branch into the mission branch.
2. Merge the mission branch into the target branch.

Recovery semantics (WP01 / 067):
- MergeState is created at merge start and updated after each WP mark-done.
- On interruption, rerunning ``merge`` detects the existing state and resumes.
- ``--resume`` explicitly triggers resume; ``--abort`` cleans up state and exits.
- ``cleanup_merge_workspace`` preserves state.json so recovery works.
- ``clear_state`` is called only after confirmed full completion.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import time
from pathlib import Path

import typer
from rich.console import Console

from specify_cli import __version__ as SPEC_KITTY_VERSION
from specify_cli.cli.helpers import console, show_banner
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.git_ops import has_remote, run_command
from specify_cli.core.git_preflight import build_git_preflight_failure_payload, run_git_preflight
from specify_cli.core.paths import get_feature_target_branch, get_main_repo_root
from specify_cli.git import safe_commit
from specify_cli.git.commit_helpers import SafeCommitRecoveryFailed
from specify_cli.git.sparse_checkout import (
    SparseCheckoutPreflightError,
    require_no_sparse_checkout,
)
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json
from specify_cli.merge.config import MergeStrategy, load_merge_config
from specify_cli.merge.ordering import assign_next_mission_number
from specify_cli.merge.preflight import (
    TargetBranchSyncStatus,
    inspect_target_branch_sync,
    refresh_target_branch_tracking_ref,
    target_branch_sync_remediation,
)
from specify_cli.merge.state import (
    MergeLockError,
    MergeState,
    abort_git_merge,
    acquire_merge_lock,
    clear_state,
    load_state,
    needs_number_assignment,
    release_merge_lock,
    save_state,
)
from specify_cli.mission_metadata import load_meta, resolve_mission_identity, write_meta
from specify_cli.merge.workspace import _worktree_removal_delay, cleanup_merge_workspace, get_merge_runtime_dir
from specify_cli.post_merge.review_artifact_consistency import (
    REJECTED_REVIEW_ARTIFACT_CONFLICT,
    REJECTED_REVIEW_ARTIFACT_REMEDIATION,
    format_review_artifact_conflict,
    review_artifact_conflict_diagnostic,
    run_review_artifact_consistency_preflight,
)
from specify_cli.post_merge.stale_assertions import StaleAssertionReport, run_check
from specify_cli.sync import emit_diff_summary_recorded, emit_mission_closed
from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
from specify_cli.status.wp_metadata import read_wp_frontmatter
from specify_cli.task_utils import TaskCliError, find_repo_root

logger = logging.getLogger(__name__)

TARGET_BRANCH_NOT_SYNCHRONIZED = "TARGET_BRANCH_NOT_SYNCHRONIZED"
TARGET_BRANCH_SYNC_INVARIANT = "local_target_branch_must_match_tracking_branch"
_STATUS_EVENTS_FILENAME = "status.events.jsonl"
_STATUS_FILENAME = "status.json"

# T011 — FR-009: push-error parser tokens (locked tuple — do not reorder or extend without a spec change)
LINEAR_HISTORY_REJECTION_TOKENS: tuple[str, ...] = (
    "merge commits",
    "linear history",
    "fast-forward only",
    "GH006",
    "non-fast-forward",
)

MissionBranchBlocker = dict[str, str | bool]


class BaselineMergeCommitError(RuntimeError):
    """Raised when the post-merge review baseline cannot be recorded or verified.

    Modern lane missions (those whose ``meta.json`` carries a canonical
    ``mission_id``) MUST land ``baseline_merge_commit`` on the target branch.
    When the baseline is missing, the working meta is absent/corrupt, or the
    committed target meta lacks the expected value, downstream
    ``spec-kitty review`` raises ``MISSION_REVIEW_MODE_MISMATCH``. We surface
    that failure loudly at merge time instead of letting an apparently
    successful merge ship a mission that cannot be reviewed post-merge.
    """


def _classify_porcelain_lines(
    lines: list[str],
    expected_paths: set[str],
) -> tuple[list[str], int]:
    """Classify ``git status --porcelain`` lines into offending vs ignored.

    Returns a 2-tuple ``(offending_lines, skipped_untracked_count)`` where:

    * ``offending_lines`` — lines that represent unexpected divergence from HEAD
      (tracked modifications, deletions, renames, …).
    * ``skipped_untracked_count`` — number of ``??`` (untracked) lines that were
      silently dropped because untracked files cannot diverge from HEAD.

    Lines whose path component is in *expected_paths* are also dropped because
    the immediately-following safe_commit will persist those files and they are
    therefore expected to be dirty at this point in the flow.

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
        "[cyan]merge.strategy: squash[/cyan] in [cyan].kittify/config.yaml[/cyan].\n"
    )


def _has_transition_to(feature_dir: Path, wp_id: str, to_lane: str) -> bool:
    """Check whether the event log already contains a transition for *wp_id* to *to_lane*.

    This dedup guard prevents duplicate events when ``_mark_wp_merged_done`` is
    called again on retry/resume.
    """
    from specify_cli.status.store import read_events

    return any(event.wp_id == wp_id and event.to_lane == to_lane for event in read_events(feature_dir))


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
    feature_dir = repo_root / "kitty-specs" / mission_slug
    wp_path = None
    for candidate in sorted((feature_dir / "tasks").glob(f"{wp_id}*.md")):
        wp_path = candidate
        break
    if wp_path is None or not wp_path.exists():
        console.print(f"[yellow]Warning:[/yellow] Could not locate WP file for {wp_id}; skipping merge-complete status update.")
        return

    metadata, _body = read_wp_frontmatter(wp_path)
    from specify_cli.status.lane_reader import get_wp_lane
    from specify_cli.status.models import DoneEvidence, ReviewApproval
    from specify_cli.status.emit import emit_status_transition, TransitionError
    from specify_cli.status.history_parser import extract_done_evidence
    from specify_cli.status.transitions import resolve_lane_alias

    from specify_cli.status.models import Lane as _Lane

    lane_str = resolve_lane_alias(get_wp_lane(feature_dir, wp_id))
    lane = _Lane(lane_str)
    if lane == _Lane.DONE:
        return

    # Dedup guard: if we already have a done transition in the log, skip everything.
    if _has_transition_to(feature_dir, wp_id, "done"):
        logger.debug("Dedup: %s already has 'done' transition, skipping", wp_id)
        return

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
    if lane in _pre_approved_lanes and evidence is not None:
        # Dedup guard for the intermediate approved transition
        if _has_transition_to(feature_dir, wp_id, "approved"):
            logger.debug("Dedup: %s already has 'approved' transition, skipping emit", wp_id)
        else:
            try:
                emit_status_transition(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    wp_id=wp_id,
                    to_lane="approved",
                    actor="merge",
                    reason=f"Recorded prior review approval for merged {wp_id}",
                    evidence=evidence.to_dict(),
                    workspace_context=f"merge:{repo_root}",
                    repo_root=repo_root,
                    ensure_sync_daemon=False,
                    sync_dossier=False,
                    policy_metadata={
                        "merge_phase": "lane_integrated",
                        "target_branch": target_branch,
                    },
                )
            except TransitionError as exc:
                console.print(f"[yellow]Warning:[/yellow] Failed to mark {wp_id} approved before done: {exc}")
                return
        lane = _Lane.APPROVED

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
        emit_status_transition(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            to_lane="done",
            actor="merge",
            reason=f"Merged {wp_id} into {target_branch}",
            evidence=evidence.to_dict(),
            workspace_context=f"merge:{repo_root}",
            repo_root=repo_root,
            ensure_sync_daemon=False,
            sync_dossier=False,
            policy_metadata={
                "merge_phase": "lane_integrated",
                "target_branch": target_branch,
            },
        )
    except TransitionError as exc:
        console.print(f"[yellow]Warning:[/yellow] Failed to mark {wp_id} done after merge: {exc}")


def _assert_merged_wps_reached_done(
    repo_root: Path,
    mission_slug: str,
    wp_ids: list[str],
) -> None:
    """Fail the merge if merged WPs did not reach ``done`` in the event log."""
    from specify_cli.status.lane_reader import get_wp_lane
    from specify_cli.status.models import Lane
    from specify_cli.status.store import StoreError
    from specify_cli.status.transitions import resolve_lane_alias

    feature_dir = repo_root / "kitty-specs" / mission_slug

    try:
        incomplete: list[str] = []
        for wp_id in wp_ids:
            lane = Lane(resolve_lane_alias(get_wp_lane(feature_dir, wp_id)))
            if lane != Lane.DONE:
                incomplete.append(f"{wp_id}={lane.value}")
    except StoreError as exc:
        console.print(
            "[red]Error:[/red] Post-merge status validation failed: "
            f"could not read {feature_dir / 'status.events.jsonl'} ({exc})"
        )
        raise typer.Exit(1) from exc

    if incomplete:
        console.print(
            "[red]Error:[/red] Post-merge status validation failed: "
            "merged WPs did not reach done in the canonical event log."
        )
        console.print(f"  Offending WPs: {', '.join(incomplete)}")
        raise typer.Exit(1)


def _reconcile_completed_wps_for_resume(
    *,
    feature_dir: Path,
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
        if _has_transition_to(feature_dir, wp_id, "done")
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
            scan_specs = main_repo / "kitty-specs"
        else:
            scan_root = tmp_path
            scan_specs = tmp_path / "kitty-specs"

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

        meta_path = mission_tmp_path / "kitty-specs" / mission_slug / "meta.json"
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
        _subprocess.run(
            ["git", "update-ref", f"refs/heads/{mission_branch}", new_sha],
            cwd=str(main_repo),
            capture_output=True,
            check=True,
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
) -> tuple[bool, MissionBranchBlocker | None]:
    """Check whether the expected mission branch exists locally.

    Dry-run and real merge both use this as a read-only preflight. Missing
    branches are reported as structured blockers; this function never creates
    the branch.
    """
    expected_branch = f"kitty/mission-{mission_slug}"
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


def _resolve_target_branch(
    repo_root: Path,
    mission_slug: str | None,
    explicit_target: str | None,
) -> tuple[str, str | None]:
    """Resolve target branch and its provenance."""
    if explicit_target is not None:
        return explicit_target, "flag"

    if mission_slug:
        feature_dir = repo_root / "kitty-specs" / mission_slug
        if feature_dir.exists():
            return get_feature_target_branch(repo_root, mission_slug), "meta.json"

    from specify_cli.core.git_ops import resolve_primary_branch

    return resolve_primary_branch(repo_root), "primary_branch"


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


def _record_baseline_merge_commit(
    feature_dir: Path,
    baseline_commit: str | None,
    *,
    mission_id: str | None = None,
) -> Path | None:
    """Persist the post-merge review baseline in mission meta.json.

    ``baseline_merge_commit`` anchors post-merge review diffs. It should point
    at the target-branch baseline before the mission lands, not at the final
    housekeeping commit produced by merge.

    For **modern lane missions** (``mission_id`` is set — the canonical ULID
    introduced by mission 083), an empty baseline, a missing ``meta.json``, or
    corrupt JSON is a HARD failure: we raise :class:`BaselineMergeCommitError`
    so the merge stops loudly instead of shipping a mission that
    ``spec-kitty review --mode post-merge`` cannot anchor
    (``MISSION_REVIEW_MODE_MISMATCH``).

    For **legacy missions** (no ``mission_id``) the historical soft behavior is
    preserved: the function logs a warning and returns ``None`` so the merge
    proceeds without a baseline.
    """
    is_modern = bool(mission_id and str(mission_id).strip())

    if not baseline_commit or not baseline_commit.strip():
        if is_modern:
            raise BaselineMergeCommitError(
                f"Cannot record baseline_merge_commit for modern mission "
                f"{feature_dir.name}: no target baseline SHA was captured."
            )
        return None

    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        if is_modern:
            raise BaselineMergeCommitError(
                f"Cannot record baseline_merge_commit for modern mission "
                f"{feature_dir.name}: meta.json is missing."
            )
        logger.warning(
            "Cannot record baseline_merge_commit for %s: meta.json is missing",
            feature_dir.name,
        )
        return None

    try:
        meta = load_meta(feature_dir)
    except ValueError as exc:
        if is_modern:
            raise BaselineMergeCommitError(
                f"Cannot record baseline_merge_commit for modern mission "
                f"{feature_dir.name}: meta.json is invalid ({exc})."
            ) from exc
        logger.warning(
            "Cannot record baseline_merge_commit for %s: %s",
            feature_dir.name,
            exc,
        )
        return None

    if meta is None:
        if is_modern:
            raise BaselineMergeCommitError(
                f"Cannot record baseline_merge_commit for modern mission "
                f"{feature_dir.name}: meta.json could not be loaded."
            )
        return None

    existing = meta.get("baseline_merge_commit")
    if existing and str(existing).strip():
        return None

    meta["baseline_merge_commit"] = baseline_commit.strip()
    write_meta(feature_dir, meta, validate=False)
    return meta_path


def _assert_baseline_merge_commit_on_target(
    main_repo: Path,
    mission_slug: str,
    target_branch: str,
    expected_baseline: str | None,
    *,
    feature_dir: Path | None = None,
    mission_id: str | None = None,
) -> None:
    """Fail the merge if ``baseline_merge_commit`` did not land on *target_branch*.

    Mirrors :func:`_assert_merged_wps_reached_done`: it reads the target
    branch's COMMITTED ``kitty-specs/<slug>/meta.json`` via
    ``git show <target>:<path>`` and asserts ``baseline_merge_commit`` is both
    present and equal to the baseline that was actually RECORDED for this
    mission. This is the post-commit invariant that closes the gap behind
    ``MISSION_REVIEW_MODE_MISMATCH``: it proves the baseline is durable in git
    history (not just in the working tree) before any worktree removal or
    branch cleanup runs.

    The expected baseline is read from the recorded mission ``meta.json`` in
    *feature_dir* (the idempotent value written by
    :func:`_record_baseline_merge_commit`) and only falls back to
    *expected_baseline* when that is unavailable. This is deliberate:
    ``target_baseline_sha`` is re-derived from the live target HEAD on every
    invocation, so on ``spec-kitty merge --resume`` — after a prior run already
    landed the mission/bookkeeping commits — the live HEAD has advanced past the
    original baseline. Comparing the committed value against a re-derived HEAD
    would spuriously fail an otherwise-correct resume; comparing it against the
    recorded value does not.

    Only enforced for **modern missions** (``mission_id`` set). Legacy missions
    never carry a baseline and are skipped.
    """
    if not (mission_id and str(mission_id).strip()):
        return

    recorded = ""
    if feature_dir is not None:
        try:
            working_meta = load_meta(feature_dir)
        except ValueError:
            working_meta = None
        if isinstance(working_meta, dict):
            recorded = str(working_meta.get("baseline_merge_commit") or "").strip()

    expected = recorded or (expected_baseline or "").strip()
    if not expected:
        raise BaselineMergeCommitError(
            f"Cannot verify baseline_merge_commit for modern mission "
            f"{mission_slug}: no recorded baseline SHA was found."
        )

    meta_rel = f"kitty-specs/{mission_slug}/meta.json"
    ret, out, err = run_command(
        ["git", "show", f"{target_branch}:{meta_rel}"],
        capture=True,
        check_return=False,
        cwd=main_repo,
    )
    if ret != 0:
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"could not read {meta_rel} from {target_branch} "
            f"({(err or '').strip() or 'git show failed'})."
        )

    try:
        committed_meta = json.loads(out)
    except json.JSONDecodeError as exc:
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"committed {meta_rel} on {target_branch} is not valid JSON ({exc})."
        ) from exc

    if not isinstance(committed_meta, dict):
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"committed {meta_rel} on {target_branch} is not a JSON object."
        )

    committed_baseline = str(committed_meta.get("baseline_merge_commit") or "").strip()
    if not committed_baseline:
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"baseline_merge_commit is missing from committed {meta_rel} on "
            f"{target_branch}. Downstream `spec-kitty review --mode post-merge` "
            f"would fail with MISSION_REVIEW_MODE_MISMATCH."
        )

    if committed_baseline != expected:
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"committed baseline_merge_commit ({committed_baseline}) on "
            f"{target_branch} does not match the captured baseline ({expected})."
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
) -> dict[str, object]:
    remediation = target_branch_sync_remediation(
        status,
        mission_slug=mission_slug,
        mission_branch=mission_branch,
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
    json_output: bool = False,
) -> None:
    """Stop merge before mutation when the target branch is not synced."""
    refresh = refresh_target_branch_tracking_ref(repo_root, target_branch)
    if not refresh.success:
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

    status = inspect_target_branch_sync(repo_root, target_branch)
    if status.is_safe:
        return

    payload = _target_branch_sync_payload(
        status,
        mission_slug=mission_slug,
        mission_branch=mission_branch,
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
    from specify_cli.status.lifecycle_events import has_non_bootstrap_status_history

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

    console.print(
        "[red]Error:[/red] Review artifact consistency gate failed. "
        "Approved/done work packages cannot have a latest rejected review artifact."
    )
    for finding in findings:
        diagnostic = review_artifact_conflict_diagnostic(
            finding,
            repo_root=repo_root,
        )
        console.print(
            f"  - {format_review_artifact_conflict(finding, repo_root=repo_root)}"
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
        console.print(
            f"    latest_review_cycle_verdict: {diagnostic['latest_review_cycle_verdict']}"
        )
        for line in REJECTED_REVIEW_ARTIFACT_REMEDIATION:
            console.print(f"    remediation: {line}")
    console.print(
        f"  Mission: {mission_slug}"
    )
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
    feature_dir = main_repo / "kitty-specs" / mission_slug

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

    lanes_manifest = require_lanes_json(feature_dir)
    if target_override:
        lanes_manifest.target_branch = target_override

    _enforce_target_branch_sync_preflight(
        main_repo,
        target_branch=lanes_manifest.target_branch,
        mission_slug=mission_slug,
        mission_branch=lanes_manifest.mission_branch,
    )

    branch_ok, branch_blocker = _check_mission_branch(mission_slug, main_repo)
    if not branch_ok:
        assert branch_blocker is not None
        console.print(
            "[red]Error:[/red] Missing mission branch: "
            f"{branch_blocker['expected_branch']}. "
            f"Run: {branch_blocker['remediation']}"
        )
        raise typer.Exit(1)

    # -- Resolve canonical mission_id from meta.json (P2 fix: use ULID, not slug) --
    identity = resolve_mission_identity(feature_dir)
    canonical_id = identity.mission_id or mission_slug  # fallback for legacy missions without ULID

    # -- Acquire global merge lock to serialize concurrent merges --
    # The lock is keyed by a well-known sentinel so that merges of DIFFERENT
    # missions also serialize against each other.  This is required because
    # mission_number assignment (WP10) computes max(existing)+1 from the
    # target branch — two concurrent merges scanning the same target tip
    # would compute the same next number.
    _GLOBAL_MERGE_LOCK_ID = "__global_merge__"
    if not acquire_merge_lock(_GLOBAL_MERGE_LOCK_ID, main_repo):
        raise MergeLockError(_GLOBAL_MERGE_LOCK_ID, main_repo / ".kittify" / "runtime" / "merge" / _GLOBAL_MERGE_LOCK_ID / "lock")

    try:
        _run_lane_based_merge_locked(
            main_repo=main_repo,
            mission_slug=mission_slug,
            canonical_id=canonical_id,
            feature_dir=feature_dir,
            lanes_manifest=lanes_manifest,
            push=push,
            delete_branch=delete_branch,
            remove_worktree=remove_worktree,
            strategy=strategy,
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
) -> None:
    """Inner merge flow, called with the global merge lock held."""
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.compute import PLANNING_LANE_ID
    from specify_cli.lanes.merge import merge_lane_to_mission, merge_mission_to_target
    from specify_cli.policy.config import load_policy_config
    from specify_cli.policy.merge_gates import evaluate_merge_gates

    # -- T001: MergeState lifecycle: load or create --
    all_wp_ids = [wp for lane in lanes_manifest.lanes for wp in lane.wp_ids]
    state = load_state(main_repo, canonical_id)
    is_resume = False
    if state is not None:
        is_resume = True
        console.print(f"[bold cyan]Resuming[/bold cyan] merge for {mission_slug} ({len(state.completed_wps)}/{len(state.wp_order)} WPs already done)")
    else:
        state = MergeState(
            mission_id=canonical_id,
            mission_slug=mission_slug,
            target_branch=lanes_manifest.target_branch,
            wp_order=all_wp_ids,
        )
        save_state(state, main_repo)

    completed_set = set(state.completed_wps)

    console.print(f"[bold]Lane-based merge for {mission_slug}[/bold]")
    console.print(f"  Mission branch: {lanes_manifest.mission_branch}")
    console.print(f"  Lanes: {', '.join(ln.lane_id for ln in lanes_manifest.lanes)}")

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

    _enforce_review_artifact_consistency(
        repo_root=main_repo,
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_ids=all_wp_ids,
    )

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

    # -- Lane merges (skip lanes whose WPs are all already completed) --
    for lane in lanes_manifest.lanes:
        lane_wp_set = set(lane.wp_ids)
        if lane_wp_set.issubset(completed_set):
            console.print(f"  [dim]Skipping {lane.lane_id} (all WPs already done)[/dim]")
            continue

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

    # -- Mission-to-target merge (T010: honor strategy for this step only) --
    console.print(f"  [dim]Merging mission branch into {lanes_manifest.target_branch}...[/dim]")
    mission_result = merge_mission_to_target(
        main_repo,
        mission_slug,
        lanes_manifest,
        strategy=strategy,
        allow_already_applied=is_resume,
    )
    mission_already_applied = getattr(mission_result, "already_applied", False) is True
    if not mission_result.success:
        # T005: tolerate already-merged on retry
        already_merged = any("already" in e.lower() or "up to date" in e.lower() for e in mission_result.errors)
        if is_resume and already_merged:
            console.print(f"[dim]{lanes_manifest.mission_branch} already merged into {lanes_manifest.target_branch}[/dim]")
        else:
            for error in mission_result.errors:
                console.print(f"[red]Error:[/red] {error}")
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

    try:
        baseline_meta_path = _record_baseline_merge_commit(
            feature_dir,
            target_baseline_sha,
            mission_id=_baseline_mission_id,
        )
    except BaselineMergeCommitError as exc:
        # Modern lane mission could not record its post-merge review baseline.
        # Fail loudly — an apparently successful merge that drops the baseline
        # produces MISSION_REVIEW_MODE_MISMATCH downstream.
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    # If the final bookkeeping commit fails after done events are emitted,
    # restore the canonical status artifacts to their pre-emit bytes. This
    # keeps the merge path aligned with the #1348 dangling-event invariant.
    _merge_events_path = feature_dir / _STATUS_EVENTS_FILENAME
    _merge_status_path = feature_dir / _STATUS_FILENAME
    _pre_done_event_size = (
        _merge_events_path.stat().st_size if _merge_events_path.exists() else 0
    )
    _pre_done_status_bytes = (
        _merge_status_path.read_bytes() if _merge_status_path.exists() else None
    )

    # -- T001: Mark WPs done with per-WP state tracking --
    console.print("  [dim]Recording merged work packages as done...[/dim]")
    completed_set = _reconcile_completed_wps_for_resume(
        feature_dir=feature_dir,
        merge_state=state,
        repo_root=main_repo,
    )
    for lane in lanes_manifest.lanes:
        for wp_id in lane.wp_ids:
            if wp_id in completed_set:
                console.print(f"  [dim]Skipping {wp_id} (already recorded as done)[/dim]")
                continue

            state.set_current_wp(wp_id)
            save_state(state, main_repo)

            _mark_wp_merged_done(main_repo, mission_slug, wp_id, lanes_manifest.target_branch)

            state.mark_wp_complete(wp_id)
            save_state(state, main_repo)
            completed_set.add(wp_id)

    _assert_merged_wps_reached_done(main_repo, mission_slug, all_wp_ids)

    # -- WP05/T007 FR-014: Post-merge working-tree invariant --
    # After the refresh, `git status --porcelain` MUST report at most the two
    # status files that the immediately-following safe_commit is going to
    # persist. Any other path diverging from HEAD indicates that something
    # (sparse-checkout, a stale lock, a filter driver) silently dropped paths
    # during the merge and must stop the flow before the housekeeping commit
    # papers over it.
    _ret_status, _out_status, _err_status = run_command(
        ["git", "status", "--porcelain"],
        capture=True,
        check_return=False,
        cwd=main_repo,
    )
    if _ret_status == 0:
        expected_paths = {
            f"kitty-specs/{mission_slug}/{_STATUS_EVENTS_FILENAME}",
            f"kitty-specs/{mission_slug}/{_STATUS_FILENAME}",
        }
        if baseline_meta_path is not None:
            expected_paths.add(str(baseline_meta_path.relative_to(main_repo)))
        offending_lines, _skipped_untracked = _classify_porcelain_lines(
            (_out_status or "").splitlines(),
            expected_paths,
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
            raise typer.Exit(1)
    else:
        console.print(
            f"[yellow]Warning:[/yellow] post-merge invariant check skipped: "
            f"git status failed ({(_err_status or '').strip()})"
        )

    # -- T012: FR-019 — Persist done events to git BEFORE any worktree removal --
    files_to_commit = [
        feature_dir / _STATUS_EVENTS_FILENAME,
        feature_dir / _STATUS_FILENAME,
    ]
    if baseline_meta_path is not None:
        files_to_commit.append(baseline_meta_path)

    has_bookkeeping_changes = _paths_have_status_changes(main_repo, files_to_commit)
    may_skip_empty_bookkeeping = is_resume or mission_already_applied
    if has_bookkeeping_changes or not may_skip_empty_bookkeeping:
        try:
            safe_commit(
                repo_root=main_repo,
                worktree_root=main_repo,
                destination_ref=lanes_manifest.target_branch,
                message=f"chore({mission_slug}): record done transitions for merged WPs",
                paths=tuple(files_to_commit),
            )
        except Exception as exc:
            if not (isinstance(exc, SafeCommitRecoveryFailed) and exc.commit_sha is not None):
                with contextlib.suppress(OSError):
                    if _merge_events_path.exists():
                        with _merge_events_path.open("ab") as _fh:
                            _fh.truncate(_pre_done_event_size)
                with contextlib.suppress(OSError):
                    if _pre_done_status_bytes is None:
                        _merge_status_path.unlink(missing_ok=True)
                    else:
                        _merge_status_path.write_bytes(_pre_done_status_bytes)
            raise
    else:
        console.print("  [dim]No post-merge bookkeeping changes to commit; continuing cleanup.[/dim]")

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
            feature_dir=feature_dir,
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
        delay = _worktree_removal_delay()
        for idx, lane in enumerate(lanes_manifest.lanes):
            wt_path = main_repo / ".worktrees" / f"{mission_slug}-{lane.lane_id}"
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
            if lane.lane_id == PLANNING_LANE_ID:
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
        for finding in stale_report.findings:
            console.print(f"  [{finding.confidence}] {finding.test_file.name}:{finding.test_line} — {finding.hint}")


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
        resolved = _resolve_mission_slug(repo_root, mission_slug_raw)
        if resolved:
            cleared = clear_state(repo_root, resolved)
            cleanup_merge_workspace(resolved, repo_root)
            # WP07 / FR-016: --abort also tears down the coordination
            # worktree (idempotent; no-op for legacy missions without
            # coordination state). Done here so partial-state aborts
            # leave the workspace in the same shape as a clean run.
            try:
                from specify_cli.coordination import CoordinationWorkspace
                from specify_cli.mission_metadata import load_meta as _load_meta

                _main_for_abort = get_main_repo_root(repo_root)
                _feature_dir_for_abort = _main_for_abort / "kitty-specs" / resolved
                _meta_for_abort = _load_meta(_feature_dir_for_abort)
                _mid8_for_abort = (
                    str(_meta_for_abort.get("mid8", "")).strip()
                    if isinstance(_meta_for_abort, dict)
                    else ""
                )
                if _mid8_for_abort:
                    CoordinationWorkspace.teardown(
                        _main_for_abort,
                        resolved,
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
        _legacy_state_path = repo_root / ".kittify" / "merge-state.json"
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
        resolved = _resolve_mission_slug(repo_root, mission_slug_raw)
        existing_state = load_state(repo_root, resolved)
        if existing_state is None:
            console.print("[red]Error:[/red] No interrupted merge to resume.")
            raise typer.Exit(1)
        console.print(
            f"[bold cyan]Resume requested[/bold cyan] for {existing_state.mission_slug} ({len(existing_state.completed_wps)}/{len(existing_state.wp_order)} done)"
        )
        # Fall through to the normal merge flow which will detect the state

    _enforce_git_preflight(repo_root, json_output=json_output)

    # T009 — FR-005/FR-006: Resolve strategy: CLI flag > config > default (SQUASH)
    resolved_strategy: MergeStrategy = strategy or load_merge_config(repo_root).strategy or MergeStrategy.SQUASH

    mission_slug = (mission or feature or "").strip() or None
    resolved_feature = _resolve_mission_slug(repo_root, mission_slug)

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
            lanes_manifest = require_lanes_json(get_main_repo_root(repo_root) / "kitty-specs" / resolved_feature)
        except (MissingLanesError, CorruptLanesError) as exc:
            error_msg = str(exc)
            if json_output:
                print(json.dumps({"spec_kitty_version": SPEC_KITTY_VERSION, "error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1) from exc

        feature_dir_for_preview = (
            get_main_repo_root(repo_root) / "kitty-specs" / resolved_feature
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
                print(
                    json.dumps(
                        {
                            "spec_kitty_version": SPEC_KITTY_VERSION,
                            "mission_slug": resolved_feature,
                            "target_branch": resolved_target_branch,
                            "blocked": True,
                            "blockers": diagnostics,
                            "diagnostic_code": REJECTED_REVIEW_ARTIFACT_CONFLICT,
                        }
                    )
                )
            else:
                console.print(
                    "[red]Error:[/red] Review artifact consistency gate failed. "
                    "Approved/done work packages cannot have a latest rejected review artifact."
                )
                for finding in review_artifact_preflight.findings:
                    console.print(
                        f"  - {format_review_artifact_conflict(finding, repo_root=main_repo_for_diag)}"
                    )
                    console.print(
                        f"    diagnostic_code: {REJECTED_REVIEW_ARTIFACT_CONFLICT}"
                    )
                    console.print(
                        f"    branch_or_work_package: {finding.wp_id}"
                    )
                    for line in REJECTED_REVIEW_ARTIFACT_REMEDIATION:
                        console.print(f"    remediation: {line}")
                console.print(f"  Mission: {resolved_feature}")
            raise typer.Exit(1)

        # WP10/T053: dry-run preview of merge-time mission_number assignment.
        would_assign_number: int | None = None
        if needs_number_assignment(feature_dir_for_preview):
            try:
                would_assign_number = assign_next_mission_number(
                    get_main_repo_root(repo_root),
                    get_main_repo_root(repo_root) / "kitty-specs",
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
        )
    except SparseCheckoutPreflightError as exc:
        # WP05/T020: surface sparse-checkout preflight as user-facing error
        # and exit non-zero WITHOUT writing any merge state.
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except (MissingLanesError, CorruptLanesError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    # -- Post-merge: Suggest mission review and retrospective review/synthesis --
    # The mission's retrospective.yaml is captured earlier at the runtime
    # terminus (HiC prompt or autonomous facilitator), not by merge. The two
    # commands below operate on an already-authored record: `summary` is a
    # cross-mission view; `synthesize` applies any staged proposals (dry-run
    # by default — pass `--apply` to mutate). They do not create content.
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
    "BaselineMergeCommitError",
    "_mark_wp_merged_done",
    "_run_lane_based_merge",
    "_is_linear_history_rejection",
    "_emit_remediation_hint",
    "_check_mission_branch",
    "_has_branch_ref",
    "_enforce_target_branch_sync_preflight",
    "_enforce_review_artifact_consistency",
    "_bake_mission_number_into_mission_branch",
    "LINEAR_HISTORY_REJECTION_TOKENS",
    "merge",
]
