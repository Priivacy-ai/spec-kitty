"""Merge command implementation.

Lane worktrees are the only supported execution topology. Merge always follows
the same two-step flow:
1. Merge each lane branch into the mission branch.
2. Merge the mission branch into the target branch.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import typer

from specify_cli import __version__ as SPEC_KITTY_VERSION
from specify_cli.cli.helpers import console, show_banner
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.git_ops import has_remote, run_command
from specify_cli.core.git_preflight import build_git_preflight_failure_payload, run_git_preflight
from specify_cli.core.paths import get_feature_target_branch, get_main_repo_root
from specify_cli.frontmatter import read_frontmatter
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json
from specify_cli.tasks_support import TaskCliError, find_repo_root


def _mark_wp_merged_done(
    repo_root: Path,
    feature_slug: str,
    wp_id: str,
    target_branch: str,
) -> None:
    """Record merge-complete state for a merged WP using canonical status events."""
    feature_dir = repo_root / "kitty-specs" / feature_slug
    wp_path = None
    for candidate in sorted((feature_dir / "tasks").glob(f"{wp_id}*.md")):
        wp_path = candidate
        break
    if wp_path is None or not wp_path.exists():
        console.print(
            f"[yellow]Warning:[/yellow] Could not locate WP file for {wp_id}; "
            "skipping merge-complete status update."
        )
        return

    frontmatter, _body = read_frontmatter(wp_path)
    from specify_cli.status.lane_reader import get_wp_lane
    from specify_cli.status.models import DoneEvidence, ReviewApproval
    from specify_cli.status.emit import emit_status_transition, TransitionError
    from specify_cli.status.history_parser import extract_done_evidence
    from specify_cli.status.transitions import resolve_lane_alias

    lane = resolve_lane_alias(get_wp_lane(feature_dir, wp_id))
    if lane == "done":
        return

    evidence = extract_done_evidence(frontmatter, wp_id)
    if evidence is None:
        if lane == "approved":
            evidence = DoneEvidence(
                review=ReviewApproval(
                    reviewer=str(frontmatter.get("agent", "unknown")).strip() or "unknown",
                    verdict="approved",
                    reference=f"lane-approved:{wp_id}",
                )
            )
        else:
            console.print(
                f"[yellow]Warning:[/yellow] {wp_id} has no recorded approval metadata; "
                "skipping automatic move to done after merge."
            )
            return

    if lane == "for_review":
        try:
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug=feature_slug,
                wp_id=wp_id,
                to_lane="approved",
                actor="merge",
                reason=f"Recorded prior review approval for merged {wp_id}",
                evidence=evidence.to_dict(),
                workspace_context=f"merge:{repo_root}",
                repo_root=repo_root,
            )
        except TransitionError as exc:
            console.print(
                f"[yellow]Warning:[/yellow] Failed to mark {wp_id} approved before done: {exc}"
            )
            return
        lane = "approved"

    if lane != "approved":
        console.print(
            f"[yellow]Warning:[/yellow] {wp_id} is in lane '{lane}', not approved; "
            "skipping automatic move to done after merge."
        )
        return

    try:
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=feature_slug,
            wp_id=wp_id,
            to_lane="done",
            actor="merge",
            reason=f"Merged {wp_id} into {target_branch}",
            evidence=evidence.to_dict(),
            workspace_context=f"merge:{repo_root}",
            repo_root=repo_root,
        )
    except TransitionError as exc:
        console.print(
            f"[yellow]Warning:[/yellow] Failed to mark {wp_id} done after merge: {exc}"
        )


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


def _extract_feature_slug(branch_name: str) -> str | None:
    """Infer a feature slug from a feature, mission, or lane branch name."""
    from specify_cli.lanes.branch_naming import parse_feature_slug_from_branch

    parsed = parse_feature_slug_from_branch(branch_name)
    if parsed:
        return parsed

    match = re.match(r"^(\d{3}-[a-z0-9][a-z0-9-]*?)(?:-(?:lane-[a-z]))?$", branch_name)
    if match:
        return match.group(1)
    return None


def _resolve_feature_slug(repo_root: Path, mission_slug: str | None) -> str | None:
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
    return _extract_feature_slug(current_branch.strip())


def _resolve_target_branch(
    repo_root: Path,
    feature_slug: str | None,
    explicit_target: str | None,
) -> tuple[str, str | None]:
    """Resolve target branch and its provenance."""
    if explicit_target is not None:
        return explicit_target, "flag"

    if feature_slug:
        feature_dir = repo_root / "kitty-specs" / feature_slug
        if feature_dir.exists():
            return get_feature_target_branch(repo_root, feature_slug), "meta.json"

    from specify_cli.core.git_ops import resolve_primary_branch

    return resolve_primary_branch(repo_root), "primary_branch"


def _validate_target_branch(
    repo_root: Path,
    feature_slug: str | None,
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

    if target_source == "meta.json" and feature_slug:
        error_msg = (
            f"Target branch '{target_branch}' (from meta.json) does not exist locally "
            f"or on origin. Check kitty-specs/{feature_slug}/meta.json."
        )
    elif target_source == "primary_branch" and feature_slug:
        error_msg = (
            f"Target branch '{target_branch}' (resolved as primary branch) does not exist "
            f"locally or on origin. Check kitty-specs/{feature_slug}/meta.json."
        )
    else:
        error_msg = (
            f"Target branch '{target_branch}' does not exist locally or on origin."
        )

    if json_output:
        print(json.dumps({"spec_kitty_version": SPEC_KITTY_VERSION, "error": error_msg}))
    else:
        console.print(f"[red]Error:[/red] {error_msg}")
    raise typer.Exit(1)


def _run_lane_based_merge(
    repo_root: Path,
    feature_slug: str,
    *,
    push: bool,
    delete_branch: bool,
    remove_worktree: bool,
    target_override: str | None = None,
) -> None:
    """Execute the lane-only merge flow."""
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.merge import merge_lane_to_mission, merge_mission_to_target
    from specify_cli.policy.config import load_policy_config
    from specify_cli.policy.merge_gates import evaluate_merge_gates

    main_repo = get_main_repo_root(repo_root)
    feature_dir = main_repo / "kitty-specs" / feature_slug
    lanes_manifest = require_lanes_json(feature_dir)
    if target_override:
        lanes_manifest.target_branch = target_override

    console.print(f"[bold]Lane-based merge for {feature_slug}[/bold]")
    console.print(f"  Mission branch: {lanes_manifest.mission_branch}")
    console.print(f"  Lanes: {', '.join(l.lane_id for l in lanes_manifest.lanes)}")

    policy = load_policy_config(main_repo)
    all_wp_ids = [wp for lane in lanes_manifest.lanes for wp in lane.wp_ids]
    gate_eval = evaluate_merge_gates(
        feature_dir,
        feature_slug,
        all_wp_ids,
        policy.merge_gates,
        main_repo,
    )
    for gate in gate_eval.gates:
        icon = (
            "[green]✓[/green]"
            if gate.verdict == "pass"
            else "[yellow]⚠[/yellow]"
            if not gate.blocking
            else "[red]✗[/red]"
        )
        console.print(f"  {icon} Gate {gate.gate_name}: {gate.details}")
    if not gate_eval.overall_pass:
        console.print("\n[red]Error:[/red] Merge gates failed.")
        raise typer.Exit(1)

    for lane in lanes_manifest.lanes:
        lane_result = merge_lane_to_mission(main_repo, feature_slug, lane.lane_id, lanes_manifest)
        if lane_result.success:
            console.print(f"  [green]✓[/green] {lane.lane_id} → {lanes_manifest.mission_branch}")
        else:
            for error in lane_result.errors:
                console.print(f"  [red]✗[/red] {lane.lane_id}: {error}")
            raise typer.Exit(1)

    mission_result = merge_mission_to_target(main_repo, feature_slug, lanes_manifest)
    if not mission_result.success:
        for error in mission_result.errors:
            console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1)

    console.print(f"\n[green]✓[/green] {lanes_manifest.mission_branch} → {lanes_manifest.target_branch}")
    if mission_result.commit:
        console.print(f"  Commit: {mission_result.commit[:7]}")

    for lane in lanes_manifest.lanes:
        for wp_id in lane.wp_ids:
            _mark_wp_merged_done(main_repo, feature_slug, wp_id, lanes_manifest.target_branch)

    if push and has_remote(main_repo):
        run_command(["git", "push", "origin", lanes_manifest.target_branch], cwd=main_repo)
        console.print(f"[green]✓[/green] Pushed {lanes_manifest.target_branch} to origin")

    if remove_worktree:
        for lane in lanes_manifest.lanes:
            wt_path = main_repo / ".worktrees" / f"{feature_slug}-{lane.lane_id}"
            if wt_path.exists():
                run_command(
                    ["git", "worktree", "remove", str(wt_path), "--force"],
                    cwd=main_repo,
                    check_return=False,
                )
                console.print(f"  Removed worktree: {wt_path.name}")

    if delete_branch:
        for lane in lanes_manifest.lanes:
            run_command(
                ["git", "branch", "-D", lane_branch_name(feature_slug, lane.lane_id)],
                cwd=main_repo,
                check_return=False,
            )
        run_command(
            ["git", "branch", "-D", lanes_manifest.mission_branch],
            cwd=main_repo,
            check_return=False,
        )
        console.print(f"  Cleaned up {len(lanes_manifest.lanes)} lane branch(es) + mission branch")


@require_main_repo
def merge(
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
    delete_branch: bool = typer.Option(True, "--delete-branch/--keep-branch", help="Delete lane branches after merge"),
    remove_worktree: bool = typer.Option(True, "--remove-worktree/--keep-worktree", help="Remove lane worktrees after merge"),
    push: bool = typer.Option(False, "--push", help="Push to origin after merge"),
    target_branch: str = typer.Option(None, "--target", help="Target branch to merge into (auto-detected)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
    json_output: bool = typer.Option(False, "--json", help="Output deterministic JSON (dry-run mode)"),
    mission: str = typer.Option(None, "--mission", help="Mission slug when merging from main branch"),
    feature: str = typer.Option(None, "--feature", help="Mission slug when merging from main branch (legacy flag name)"),
    resume: bool = typer.Option(False, "--resume", help="Resume is no longer supported"),
    abort: bool = typer.Option(False, "--abort", help="Abort is no longer supported"),
    context_token: str = typer.Option(None, "--context", help="Unused compatibility flag"),
    keep_workspace: bool = typer.Option(False, "--keep-workspace", help="Unused compatibility flag"),
) -> None:
    """Merge a lane-based feature into its target branch."""
    del context_token, keep_workspace, strategy

    if not json_output:
        show_banner()

    if resume or abort:
        console.print("[red]Error:[/red] Resume/abort merge flows were removed with the legacy merge engine.")
        raise typer.Exit(1)

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    _enforce_git_preflight(repo_root, json_output=json_output)

    mission_slug = (mission or feature or "").strip() or None
    resolved_feature = _resolve_feature_slug(repo_root, mission_slug)
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
            error_msg = "Feature slug could not be resolved. Use --feature <slug>."
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
            raise typer.Exit(1)

        payload: dict[str, object] = {
            "spec_kitty_version": SPEC_KITTY_VERSION,
            "feature_slug": resolved_feature,
            "target_branch": resolved_target_branch,
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
        console.print("[red]Error:[/red] Feature slug could not be resolved. Use --feature <slug>.")
        raise typer.Exit(1)

    try:
        _run_lane_based_merge(
            repo_root=repo_root,
            feature_slug=resolved_feature,
            push=push,
            delete_branch=delete_branch,
            remove_worktree=remove_worktree,
            target_override=resolved_target_branch,
        )
    except (MissingLanesError, CorruptLanesError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


__all__ = ["_mark_wp_merged_done", "merge"]
