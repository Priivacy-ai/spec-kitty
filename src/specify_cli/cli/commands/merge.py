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
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json
from specify_cli.merge.config import MergeStrategy, load_merge_config
from specify_cli.merge.state import MergeState, clear_state, load_state, save_state
from specify_cli.merge.workspace import _worktree_removal_delay, cleanup_merge_workspace
from specify_cli.post_merge.stale_assertions import StaleAssertionReport, run_check
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


def _is_linear_history_rejection(stderr: str) -> bool:
    """Return True if git push stderr indicates a linear-history rejection.

    Case-insensitive substring match against the locked token list.
    Fail-open: returns False for unrecognised rejection messages.
    """
    haystack = stderr.lower()
    return any(token.lower() in haystack for token in LINEAR_HISTORY_REJECTION_TOKENS)


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

    lane = resolve_lane_alias(get_wp_lane(feature_dir, wp_id))
    if lane == "done":
        return

    # Dedup guard: if we already have a done transition in the log, skip everything.
    if _has_transition_to(feature_dir, wp_id, "done"):
        logger.debug("Dedup: %s already has 'done' transition, skipping", wp_id)
        return

    evidence = extract_done_evidence(metadata, wp_id)
    if evidence is None:
        if lane == "approved":
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

    if lane in {"planned", "claimed", "in_progress", "for_review"} and evidence is not None:
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
                )
            except TransitionError as exc:
                console.print(f"[yellow]Warning:[/yellow] Failed to mark {wp_id} approved before done: {exc}")
                return
        lane = "approved"

    if lane != "approved":
        console.print(f"[yellow]Warning:[/yellow] {wp_id} is in lane '{lane}', not approved; skipping automatic move to done after merge.")
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
    from specify_cli.status.store import StoreError
    from specify_cli.status.transitions import resolve_lane_alias

    feature_dir = repo_root / "kitty-specs" / mission_slug

    try:
        incomplete: list[str] = []
        for wp_id in wp_ids:
            lane = resolve_lane_alias(get_wp_lane(feature_dir, wp_id))
            if lane != "done":
                incomplete.append(f"{wp_id}={lane}")
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
        return parsed

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
    """
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.compute import PLANNING_LANE_ID
    from specify_cli.lanes.merge import merge_lane_to_mission, merge_mission_to_target
    from specify_cli.policy.config import load_policy_config
    from specify_cli.policy.merge_gates import evaluate_merge_gates

    main_repo = get_main_repo_root(repo_root)
    feature_dir = main_repo / "kitty-specs" / mission_slug
    lanes_manifest = require_lanes_json(feature_dir)
    if target_override:
        lanes_manifest.target_branch = target_override

    # -- T001: MergeState lifecycle: load or create --
    all_wp_ids = [wp for lane in lanes_manifest.lanes for wp in lane.wp_ids]
    state = load_state(main_repo, mission_slug)
    is_resume = False
    if state is not None and state.completed_wps:
        is_resume = True
        console.print(f"[bold cyan]Resuming[/bold cyan] merge for {mission_slug} ({len(state.completed_wps)}/{len(state.wp_order)} WPs already done)")
    else:
        state = MergeState(
            mission_id=mission_slug,
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

    # -- Mission-to-target merge (T010: honor strategy for this step only) --
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

    # -- T001: Mark WPs done with per-WP state tracking --
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

    # -- T013: Stale-assertion check (WP01 library import — NOT subprocess) --
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
    cleanup_merge_workspace(mission_slug, main_repo)
    clear_state(main_repo, mission_slug)

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
        }
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
        )
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
    "LINEAR_HISTORY_REJECTION_TOKENS",
    "merge",
]
