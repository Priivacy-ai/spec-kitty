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
from specify_cli.git.sparse_checkout import (
    SparseCheckoutPreflightError,
    require_no_sparse_checkout,
)
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json
from specify_cli.merge.config import MergeStrategy, load_merge_config
from specify_cli.merge.ordering import assign_next_mission_number
from specify_cli.merge.state import (
    MergeLockError,
    MergeState,
    acquire_merge_lock,
    clear_state,
    load_state,
    needs_number_assignment,
    release_merge_lock,
    save_state,
)
from specify_cli.mission_metadata import resolve_mission_identity, write_meta
from specify_cli.merge.workspace import _worktree_removal_delay, cleanup_merge_workspace
from specify_cli.post_merge.stale_assertions import StaleAssertionReport, run_check
from specify_cli.sync import emit_diff_summary_recorded, emit_mission_closed
from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
from specify_cli.status.wp_metadata import read_wp_frontmatter
from specify_cli.tasks_support import TaskCliError, find_repo_root

logger = logging.getLogger(__name__)

# T011 — FR-009: push-error parser tokens (locked tuple — do not reorder or extend without a spec change)
LINEAR_HISTORY_REJECTION_TOKENS: tuple[str, ...] = (
    "merge commits",
    "linear history",
    "fast-forward only",
    "GH006",
    "non-fast-forward",
)


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
                )
            except TransitionError as exc:
                console.print(f"[yellow]Warning:[/yellow] Failed to mark {wp_id} approved before done: {exc}")
                return
        lane = _Lane.APPROVED

    if lane != _Lane.APPROVED:
        console.print(f"[yellow]Warning:[/yellow] {wp_id} is in lane '{lane.value}', not approved; skipping automatic move to done after merge.")
        return

    try:
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


def _bake_mission_number_into_mission_branch(
    main_repo: Path,
    mission_slug: str,
    mission_branch: str,
    target_branch: str,
    *,
    dry_run: bool = False,
) -> int | None:
    """Assign and persist a dense integer ``mission_number`` for a pre-merge mission.

    Implements WP10 / FR-044 / T053:

    1. Scan the target branch's ``kitty-specs/`` view for the next available
       integer (``max + 1``, or ``1`` if empty).
    2. Check the mission branch's ``meta.json`` — if it already has an integer
       ``mission_number`` that matches the freshly-computed value or is already
       present on the target branch, this is a no-op (idempotent on retry).
    3. In dry-run mode, log the value but do not write or commit.
    4. Otherwise, create a detached worktree at the mission branch tip, update
       ``meta.json`` in place, commit the change, and fast-forward the mission
       branch ref so the integer lands in the eventual mission→target merge.

    The caller MUST hold the global merge lock
    (``acquire_merge_lock("__global_merge__", ...)``) for the duration.

    **Retry safety**: The assignment always re-derives from the target branch
    tip.  If a prior run assigned a number from a stale target and the push
    failed, re-running after ``git fetch`` will see the updated target and
    compute the correct next value — the stale number in the mission branch's
    ``meta.json`` is overwritten.

    Returns:
        The assigned integer if a new number was written; ``None`` if the
        target branch's ``meta.json`` already has the number or in dry-run mode.
    """
    import json as _json
    import subprocess as _subprocess
    import tempfile as _tempfile

    def _is_git_repo(path: Path) -> bool:
        probe = _subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(path),
            capture_output=True,
            text=True,
        )
        return probe.returncode == 0 and probe.stdout.strip() == "true"

    def _has_branch_ref(path: Path, ref_name: str) -> bool:
        probe = _subprocess.run(
            ["git", "rev-parse", "--verify", f"{ref_name}^{{commit}}"],
            cwd=str(path),
            capture_output=True,
            text=True,
        )
        return probe.returncode == 0

    if not _is_git_repo(main_repo):
        logger.warning(
            "Skipping mission_number bake for %s: %s is not a git repository",
            mission_slug,
            main_repo,
        )
        return None

    # -- Step 1: Check the TARGET branch's meta.json for this mission.
    # If the target already has an integer mission_number for this mission,
    # it was assigned in a prior successful merge — true no-op.
    # We do NOT check the mission branch's copy, because a stale assignment
    # from a failed push must be re-derivable on retry.
    tmp_dir = _tempfile.mkdtemp(prefix="kitty-numassign-")
    tmp_path = Path(tmp_dir)
    next_number: int
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
            # Fall back to scanning main_repo's working tree.  Best effort.
            scan_root = main_repo
            scan_specs = main_repo / "kitty-specs"
        else:
            scan_root = tmp_path
            scan_specs = tmp_path / "kitty-specs"

        # Check if the target branch already has this mission with a number
        target_meta_path = scan_specs / mission_slug / "meta.json"
        if target_meta_path.exists():
            target_meta = _json.loads(target_meta_path.read_text(encoding="utf-8"))
            existing_on_target = target_meta.get("mission_number") if isinstance(target_meta, dict) else None
            if isinstance(existing_on_target, int) and not isinstance(existing_on_target, bool):
                logger.debug(
                    "Mission %s already has mission_number=%d on target branch %s; no-op",
                    mission_slug, existing_on_target, target_branch,
                )
                return None

        # Compute next number from the target branch's kitty-specs/ view
        next_number = assign_next_mission_number(scan_root, scan_specs)
    finally:
        _subprocess.run(
            ["git", "worktree", "remove", str(tmp_path), "--force"],
            cwd=str(main_repo),
            capture_output=True,
        )

    if dry_run:
        console.print(
            f"[cyan]would assign[/cyan] mission_number={next_number} to mission {mission_slug}"
        )
        return None

    # -- Step 2: Write the integer into meta.json on the mission branch.
    # Always write (overwrite a stale value from a prior failed attempt).
    mission_tmp_dir = _tempfile.mkdtemp(prefix="kitty-numwrite-")
    mission_tmp_path = Path(mission_tmp_dir)
    try:
        if not _has_branch_ref(main_repo, mission_branch):
            logger.warning(
                "Skipping mission_number bake for %s: branch %s does not exist",
                mission_slug,
                mission_branch,
            )
            return None

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
            return None

        meta_path = mission_tmp_path / "kitty-specs" / mission_slug / "meta.json"
        if not meta_path.exists():
            logger.warning(
                "meta.json missing on mission branch %s for %s; cannot bake mission_number",
                mission_branch,
                mission_slug,
            )
            return None

        # Read, mutate, write preserving sort_keys + 2-space indent + trailing newline.
        meta_data = _json.loads(meta_path.read_text(encoding="utf-8"))
        if not isinstance(meta_data, dict):
            logger.warning(
                "meta.json for %s is not a JSON object; cannot bake mission_number",
                mission_slug,
            )
            return None

        meta_data["mission_number"] = next_number
        # Route all meta.json mutations through the canonical writer API.
        # Use validate=False to preserve merge-time tolerance for legacy/partial
        # mission metadata while still enforcing atomic writes + standard format.
        write_meta(meta_path.parent, meta_data, validate=False)

        # Stage and commit the change on the mission branch.
        rel_meta = meta_path.relative_to(mission_tmp_path)
        _subprocess.run(
            ["git", "add", str(rel_meta)],
            cwd=str(mission_tmp_path),
            capture_output=True,
            check=True,
        )
        commit_msg = f"chore({mission_slug}): assign mission_number={next_number}"
        _subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                commit_msg,
            ],
            cwd=str(mission_tmp_path),
            capture_output=True,
            check=True,
        )

        # Get the new commit and fast-forward the mission branch ref.
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
    finally:
        _subprocess.run(
            ["git", "worktree", "remove", str(mission_tmp_path), "--force"],
            cwd=str(main_repo),
            capture_output=True,
        )

    console.print(
        f"[green]Assigned[/green] mission_number={next_number} to mission {mission_slug}"
    )
    logger.info("Assigned mission_number=%d to mission %s", next_number, mission_slug)
    return next_number


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
    if state is not None and state.completed_wps:
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

    # -- Capture merge-base SHA for post-merge stale-assertion check (T013) --
    _ret, merge_base_sha, _err = run_command(
        ["git", "merge-base", "HEAD", lanes_manifest.target_branch],
        capture=True,
        check_return=False,
        cwd=main_repo,
    )
    merge_base_sha = merge_base_sha.strip() if _ret == 0 else "HEAD~1"

    # -- WP10/T053/T055: assign dense integer mission_number on mission branch --
    # Inside the global merge lock (acquire_merge_lock("__global_merge__"))
    # which serializes ALL merge operations — same-mission and cross-mission.
    # This guarantees the max+1 scan sees the most recent target state.
    _bake_mission_number_into_mission_branch(
        main_repo=main_repo,
        mission_slug=mission_slug,
        mission_branch=lanes_manifest.mission_branch,
        target_branch=lanes_manifest.target_branch,
        dry_run=False,
    )

    # -- Mission-to-target merge (T010: honor strategy for this step only) --
    console.print(f"  [dim]Merging mission branch into {lanes_manifest.target_branch}...[/dim]")
    mission_result = merge_mission_to_target(main_repo, mission_slug, lanes_manifest, strategy=strategy)
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
        if mission_result.commit:
            console.print(f"  Commit: {mission_result.commit[:7]}")

    # -- WP05/T006 FR-013: Post-merge working-tree refresh --
    # Re-sync the primary checkout against HEAD so any paths that git left out
    # (the observed legacy sparse-checkout case — Priivacy-ai/spec-kitty#588)
    # are restored before we record done transitions and persist the final
    # housekeeping commit. Running this refresh after writing status.events.jsonl
    # would clobber the freshly-recorded done transitions back to HEAD.
    # This is a no-op on a clean full checkout. Do not abort on failure: the
    # WP01 commit-layer backstop is the final safety net.
    _ret_checkout, _out_checkout, _err_checkout = run_command(
        ["git", "checkout", "HEAD", "--", "."],
        capture=True,
        check_return=False,
        cwd=main_repo,
    )
    if _ret_checkout != 0:
        console.print(
            f"[yellow]Warning:[/yellow] post-merge working-tree refresh failed: "
            f"{(_err_checkout or '').strip()}"
        )

    # -- WP01/T003 FR-003: Refresh the index against on-disk reality --
    # ``git checkout HEAD -- .`` restores file content to match HEAD, but the
    # cached stat info in the index can still trail real on-disk state after
    # worktree churn (mtime/inode changes), producing phantom ``D ``/`` M``
    # entries in subsequent ``git status`` calls. ``git update-index
    # --refresh`` reconciles the index stats with the working tree without
    # touching any blobs. Treat divergence as informational — never fail.
    _ret_refresh, _out_refresh, _err_refresh = run_command(
        ["git", "update-index", "--refresh"],
        capture=True,
        check_return=False,
        cwd=main_repo,
    )
    if _ret_refresh != 0:
        # Non-zero is expected when files truly differ from HEAD (e.g.
        # the two status files we are about to safe_commit). Log and move
        # on — the working-tree invariant check below is the contract.
        logger.debug(
            "post-merge index refresh reported divergence (this is informational): %s",
            (_out_refresh or _err_refresh or "").strip(),
        )

    # -- T001: Mark WPs done with per-WP state tracking --
    console.print("  [dim]Recording merged work packages as done...[/dim]")
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
            f"kitty-specs/{mission_slug}/status.events.jsonl",
            f"kitty-specs/{mission_slug}/status.json",
        }
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
    safe_commit(
        repo_path=main_repo,
        files_to_commit=[
            feature_dir / "status.events.jsonl",
            feature_dir / "status.json",
        ],
        commit_message=f"chore({mission_slug}): record done transitions for merged WPs",
        allow_empty=False,
    )

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
            base_ref=merge_base_sha,
            head_ref="HEAD",
            repo_root=main_repo,
        )
    except Exception as exc:  # noqa: BLE001
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

    # -- T002: Cleanup workspace (preserves state.json) then clear state --
    cleanup_merge_workspace(canonical_id, main_repo)
    clear_state(main_repo, canonical_id)

    _emit_merge_diff_summary(
        repo_root=main_repo,
        mission_id=canonical_id,
        base_ref=merge_base_sha,
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
        mission_slug_raw = (mission or feature or "").strip() or None
        resolved = _resolve_mission_slug(repo_root, mission_slug_raw)
        if resolved:
            cleared = clear_state(repo_root, resolved)
            cleanup_merge_workspace(resolved, repo_root)
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

        # WP10/T053: dry-run preview of merge-time mission_number assignment.
        feature_dir_for_preview = (
            get_main_repo_root(repo_root) / "kitty-specs" / resolved_feature
        )
        would_assign_number: int | None = None
        if needs_number_assignment(feature_dir_for_preview):
            try:
                would_assign_number = assign_next_mission_number(
                    get_main_repo_root(repo_root),
                    get_main_repo_root(repo_root) / "kitty-specs",
                )
            except Exception as exc:  # noqa: BLE001
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

    # -- Post-merge: Suggest mission review --
    console.print("\n[cyan]Next:[/cyan] Run [bold]/spec-kitty-mission-review[/bold] to audit the merged mission for spec→code fidelity, drift, risks, and security.")


__all__ = [
    "_has_transition_to",
    "_assert_merged_wps_reached_done",
    "_mark_wp_merged_done",
    "_run_lane_based_merge",
    "_is_linear_history_rejection",
    "_emit_remediation_hint",
    "_bake_mission_number_into_mission_branch",
    "LINEAR_HISTORY_REJECTION_TOKENS",
    "merge",
]
