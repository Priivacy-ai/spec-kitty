"""Merge command implementation.

Merges completed mission work packages into the target branch with VCS
abstraction support.
"""

from __future__ import annotations

import json
import re
import subprocess
import warnings
from pathlib import Path

import typer

from specify_cli import __version__ as SPEC_KITTY_VERSION
from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import check_version_compatibility, console, show_banner
from specify_cli.core.git_preflight import (
    build_git_preflight_failure_payload,
    run_git_preflight,
)
from specify_cli.core.paths import get_main_repo_root, get_feature_target_branch
from specify_cli.core.git_ops import has_remote, has_tracking_branch, run_command
from specify_cli.core.vcs import VCSBackend, get_vcs
from specify_cli.core.context_validation import require_main_repo
from specify_cli.merge.ordering import MergeOrderError, get_merge_order
from specify_cli.merge.preflight import (
    display_preflight_result,
    run_preflight,
)
from specify_cli.merge.state import (
    MergeState,
    abort_git_merge,
    clear_state,
    detect_git_merge_state,
    get_state_path,
    load_state,
)
from specify_cli.tasks_support import TaskCliError, find_repo_root
from specify_cli.frontmatter import read_frontmatter
from specify_cli.status.emit import emit_status_transition, TransitionError
from specify_cli.status.history_parser import extract_done_evidence
from specify_cli.status.models import DoneEvidence, ReviewApproval
from specify_cli.status.transitions import resolve_lane_alias


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
    lane = resolve_lane_alias(get_wp_lane(feature_dir, wp_id))
    if lane == "done":
        return

    evidence = extract_done_evidence(frontmatter, wp_id)
    if evidence is None:
        if lane == "approved":
            # WP was approved via move-task (no legacy review_status/reviewed_by).
            # The approved lane itself is sufficient evidence for merge→done.
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

    payload = build_git_preflight_failure_payload(
        preflight,
        command_name="spec-kitty merge",
    )
    if json_output:
        enriched = dict(payload)
        enriched["spec_kitty_version"] = SPEC_KITTY_VERSION
        print(json.dumps(enriched))
    else:
        console.print(f"[red]Error:[/red] {payload['error']}")
        for cmd in payload.get("remediation", []):
            console.print(f"  - Run: {cmd}")
    raise typer.Exit(1)


def _wp_sort_key(wp_id: str) -> tuple[int, str]:
    """Stable sort key for WP IDs."""
    match = re.match(r"^WP(\d+)$", wp_id)
    if match:
        return (int(match.group(1)), wp_id)
    return (9999, wp_id)


def _list_wp_branches(repo_root: Path, feature_slug: str) -> list[tuple[str, str]]:
    """List existing local WP branches for a feature as (wp_id, branch_name)."""
    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", f"refs/heads/{feature_slug}-WP*"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return []

    rows: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        branch = line.strip()
        if not branch:
            continue
        match = re.search(r"-(WP\d{2})$", branch)
        if not match:
            continue
        rows.append((match.group(1), branch))

    return sorted(rows, key=lambda row: _wp_sort_key(row[0]))


def _branch_is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    """Return True when `ancestor` tip is reachable from `descendant`."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _order_wp_workspaces(
    repo_root: Path,
    feature_slug: str,
    wp_workspaces: list[tuple[Path, str, str]],
) -> list[tuple[Path, str, str]]:
    """Prefer dependency/topological order, then deterministic WP sorting."""
    feature_dir = repo_root / "kitty-specs" / feature_slug
    if feature_dir.exists():
        try:
            return get_merge_order(wp_workspaces, feature_dir)
        except MergeOrderError:
            pass

    return sorted(wp_workspaces, key=lambda row: _wp_sort_key(row[1]))


def _build_workspace_per_wp_merge_plan(
    repo_root: Path,
    feature_slug: str,
    target_branch: str,
    wp_workspaces: list[tuple[Path, str, str]],
) -> dict[str, object]:
    """Build deterministic effective merge set using branch ancestry."""
    ordered = _order_wp_workspaces(repo_root, feature_slug, wp_workspaces)

    skipped_already_in_target: list[dict[str, str]] = []
    candidates: list[tuple[Path, str, str]] = []
    for wt_path, wp_id, branch in ordered:
        if _branch_is_ancestor(repo_root, branch, target_branch):
            skipped_already_in_target.append({"wp_id": wp_id, "branch": branch})
            continue
        candidates.append((wt_path, wp_id, branch))

    skipped_ancestor_of: dict[str, list[str]] = {}
    effective: list[tuple[Path, str, str]] = []
    for wt_path, wp_id, branch in candidates:
        superseding = [
            other_branch
            for _, _, other_branch in candidates
            if other_branch != branch and _branch_is_ancestor(repo_root, branch, other_branch)
        ]
        if superseding:
            skipped_ancestor_of[branch] = sorted(set(superseding))
            continue
        effective.append((wt_path, wp_id, branch))

    reason_summary: list[str] = []
    if skipped_already_in_target:
        reason_summary.append(
            f"Skipped {len(skipped_already_in_target)} branch(es) already integrated into {target_branch}."
        )
    if skipped_ancestor_of:
        reason_summary.append(
            f"Skipped {len(skipped_ancestor_of)} branch(es) that are ancestors of another candidate tip."
        )
    if not effective:
        reason_summary.append("No effective branches remain; feature appears already integrated.")
    elif len(effective) == 1 and len(ordered) > 1:
        reason_summary.append("Single effective tip contains all remaining work-package commits.")

    return {
        "all_wp_workspaces": ordered,
        "effective_wp_workspaces": effective,
        "skipped_already_in_target": skipped_already_in_target,
        "skipped_ancestor_of": skipped_ancestor_of,
        "reason_summary": reason_summary,
    }


def detect_worktree_structure(repo_root: Path, feature_slug: str) -> str:
    """Detect if feature uses lane-based, workspace-per-WP, or legacy model.

    Returns: "lane-based", "legacy", "workspace-per-wp", or "none"

    IMPORTANT: This function must work correctly when called from within a worktree.
    repo_root may be a worktree directory, so we need to find the main repo first.
    """
    # Get the main repository root (handles case where repo_root is a worktree)
    main_repo = get_main_repo_root(repo_root)

    # Check for lanes.json FIRST — lane-based takes precedence.
    feature_dir = main_repo / "kitty-specs" / feature_slug
    lanes_file = feature_dir / "lanes.json"
    if lanes_file.exists():
        return "lane-based"

    worktrees_dir = main_repo / ".worktrees"

    if not worktrees_dir.exists():
        return "none"

    # Look for workspace-per-WP pattern (takes precedence over legacy)
    # Pattern: .worktrees/###-feature-WP##/
    wp_pattern = list(worktrees_dir.glob(f"{feature_slug}-WP*"))
    if wp_pattern:
        return "workspace-per-wp"

    # Worktree directories may be missing while branches still exist.
    if _list_wp_branches(main_repo, feature_slug):
        return "workspace-per-wp"

    # Look for legacy pattern: .worktrees/###-feature/
    legacy_pattern = worktrees_dir / feature_slug
    if legacy_pattern.exists() and legacy_pattern.is_dir():
        return "legacy"

    return "none"


def extract_wp_id(worktree_path: Path) -> str | None:
    """Extract WP ID from worktree directory name.

    Example: .worktrees/010-feature-WP01/ → WP01
    """
    name = worktree_path.name
    match = re.search(r'-(WP\d{2})$', name)
    if match:
        return match.group(1)
    return None


def find_wp_worktrees(repo_root: Path, feature_slug: str) -> list[tuple[Path, str, str]]:
    """Find all WP worktrees for a feature.

    Returns: List of (worktree_path, wp_id, branch_name) tuples, sorted by WP ID.

    IMPORTANT: This function must work correctly when called from within a worktree.
    """
    # Get the main repository root (handles case where repo_root is a worktree)
    main_repo = get_main_repo_root(repo_root)
    worktrees_dir = main_repo / ".worktrees"
    pattern = f"{feature_slug}-WP*"

    wp_worktrees = sorted(worktrees_dir.glob(pattern))
    workspace_map: dict[str, tuple[Path, str, str]] = {}

    for wt_path in wp_worktrees:
        wp_id = extract_wp_id(wt_path)
        if wp_id:
            branch_name = wt_path.name  # Directory name = branch name
            workspace_map[wp_id] = (wt_path, wp_id, branch_name)

    # Branch fallback: merge should still work even when worktree dirs were pruned.
    for wp_id, branch_name in _list_wp_branches(main_repo, feature_slug):
        if wp_id in workspace_map:
            continue
        expected_path = worktrees_dir / branch_name
        workspace_map[wp_id] = (expected_path, wp_id, branch_name)

    return sorted(workspace_map.values(), key=lambda item: _wp_sort_key(item[1]))


def extract_feature_slug(branch_name: str) -> str:
    """Extract feature slug from a WP branch name.

    Example: 010-workspace-per-wp-WP01 → 010-workspace-per-wp
    """
    match = re.match(r'(.*?)-WP\d{2}$', branch_name)
    if match:
        return match.group(1)
    return branch_name  # Return as-is for legacy branches


def validate_wp_ready_for_merge(repo_root: Path, worktree_path: Path, branch_name: str) -> tuple[bool, str]:
    """Validate WP workspace is ready to merge."""
    # Check 1: Branch exists in git (check from repo root)
    result = subprocess.run(
        ["git", "rev-parse", "--verify", branch_name],
        cwd=str(repo_root),
        capture_output=True,
        check=False
    )
    if result.returncode != 0:
        return False, f"Branch {branch_name} does not exist"

    # Check 2: No uncommitted changes in worktree (if path still exists)
    if not worktree_path.exists():
        return True, ""

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if result.stdout.strip():
        return False, f"Worktree {worktree_path.name} has uncommitted changes"

    return True, ""


def branch_already_merged(repo_root: Path, target_branch: str, branch_name: str) -> bool:
    """Return True when branch tip is already reachable from target branch."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", branch_name, target_branch],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def merge_workspace_per_wp(
    repo_root: Path,
    merge_root: Path,
    feature_slug: str,
    current_branch: str,
    target_branch: str,
    strategy: str,
    delete_branch: bool,
    remove_worktree: bool,
    push: bool,
    dry_run: bool,
    json_output: bool,
    tracker: StepTracker,
    resume_state: MergeState | None = None,
) -> None:
    """Handle merge for workspace-per-WP features.

    IMPORTANT: repo_root may be a worktree directory. All worktree detection
    and operations use get_main_repo_root() to find the actual main repository.
    """
    # Get the main repository root (handles case where repo_root is a worktree)
    main_repo = get_main_repo_root(repo_root)

    # Find all WP worktrees (this function also uses get_main_repo_root internally)
    wp_workspaces = find_wp_worktrees(repo_root, feature_slug)

    # Evaluate merge gates before proceeding.
    from specify_cli.policy.config import load_policy_config as _load_pol
    from specify_cli.policy.merge_gates import evaluate_merge_gates as _eval_gates

    _pol = _load_pol(main_repo)
    _wp_ids = [wp_id for _, wp_id, _ in wp_workspaces]
    _feature_dir = main_repo / "kitty-specs" / feature_slug
    _gate_eval = _eval_gates(_feature_dir, feature_slug, _wp_ids, _pol.merge_gates, main_repo)
    for _g in _gate_eval.gates:
        _icon = "✓" if _g.verdict == "pass" else "⚠" if not _g.blocking else "✗"
        console.print(f"  {_icon} Gate {_g.gate_name}: {_g.details}")
    if not _gate_eval.overall_pass:
        console.print("\n[red]Error:[/red] Merge gates failed. Use --force to override.")
        raise typer.Exit(1)

    # Filter out already-completed WPs if resuming
    if resume_state and resume_state.completed_wps:
        completed_set = set(resume_state.completed_wps)
        wp_workspaces = [
            (wt_path, wp_id, branch)
            for wt_path, wp_id, branch in wp_workspaces
            if wp_id not in completed_set
        ]
        console.print(f"[cyan]Resuming merge:[/cyan] {len(resume_state.completed_wps)} WPs already merged")

    if not wp_workspaces:
        if json_output and dry_run:
            print(json.dumps({
                "feature_slug": feature_slug,
                "target_branch": target_branch,
                "all_wp_branches": [],
                "effective_wp_branches": [],
                "skipped_already_in_target": [],
                "skipped_ancestor_of": {},
                "planned_steps": [],
                "reason_summary": [
                    f"No WP branches/worktrees found for feature {feature_slug}."
                ],
            }))
            return
        console.print(tracker.render())
        console.print(f"\n[yellow]Warning:[/yellow] No WP worktrees found for feature {feature_slug}")
        console.print("Feature may already be merged or not yet implemented")
        raise typer.Exit(1)

    console.print(f"\n[cyan]Workspace-per-WP feature detected:[/cyan] {len(wp_workspaces)} work packages")
    for wt_path, wp_id, branch in wp_workspaces:
        console.print(f"  - {wp_id}: {branch}")

    # Validate all WP workspaces are ready
    console.print(f"\n[cyan]Validating all WP workspaces...[/cyan]")
    errors = []
    for wt_path, wp_id, branch in wp_workspaces:
        is_valid, error_msg = validate_wp_ready_for_merge(main_repo, wt_path, branch)
        if not is_valid:
            errors.append(f"  - {wp_id}: {error_msg}")

    if errors:
        tracker.error("verify", "WP workspaces not ready")
        console.print(tracker.render())
        console.print(f"\n[red]Cannot merge:[/red] WP workspaces not ready")
        for err in errors:
            console.print(err)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] All WP workspaces validated")

    merge_plan = _build_workspace_per_wp_merge_plan(
        main_repo,
        feature_slug,
        target_branch,
        wp_workspaces,
    )
    effective_workspaces = merge_plan["effective_wp_workspaces"]  # type: ignore[assignment]

    # Dry run: show what would be done
    if dry_run:
        steps = [
            f"git checkout {target_branch}",
            "git pull --ff-only",
        ]
        for wt_path, wp_id, branch in effective_workspaces:
            if strategy == "squash":
                steps.extend([
                    f"git merge --squash {branch}",
                    f"git commit -m 'Merge {wp_id} from {feature_slug}'",
                ])
            else:
                steps.append(f"git merge --no-ff {branch} -m 'Merge {wp_id} from {feature_slug}'")

        if push:
            steps.append(f"git push origin {target_branch}")

        if remove_worktree:
            for wt_path, wp_id, branch in wp_workspaces:
                if wt_path.exists():
                    steps.append(f"git worktree remove {wt_path}")
                else:
                    steps.append(f"# skip worktree removal for {wp_id} (path not present)")

        if delete_branch:
            for wt_path, wp_id, branch in wp_workspaces:
                steps.append(f"git branch -d {branch}")

        if json_output:
            payload = {
                "feature_slug": feature_slug,
                "target_branch": target_branch,
                "all_wp_branches": [branch for _, _, branch in merge_plan["all_wp_workspaces"]],  # type: ignore[index]
                "effective_wp_branches": [branch for _, _, branch in effective_workspaces],
                "skipped_already_in_target": merge_plan["skipped_already_in_target"],
                "skipped_ancestor_of": merge_plan["skipped_ancestor_of"],
                "planned_steps": steps,
                "reason_summary": merge_plan["reason_summary"],
            }
            print(json.dumps(payload))
            return

        console.print(tracker.render())
        console.print("\n[cyan]Dry run - would execute:[/cyan]")
        for idx, step in enumerate(steps, start=1):
            console.print(f"  {idx}. {step}")
        if merge_plan["reason_summary"]:
            console.print("\n[dim]Planning summary:[/dim]")
            for line in merge_plan["reason_summary"]:  # type: ignore[index]
                console.print(f"[dim]  - {line}[/dim]")
        return

    if not effective_workspaces:
        tracker.complete("merge", f"{feature_slug} already integrated into {target_branch}")
        console.print(
            f"\n[yellow]Nothing to merge:[/yellow] Feature '{feature_slug}' already appears integrated into {target_branch}."
        )
        console.print("[cyan]Cleaning up worktrees and branches...[/cyan]")
    else:
        # Checkout and update target branch
        tracker.start("checkout")
        try:
            console.print(f"[cyan]Operating from {merge_root}[/cyan]")
            _, target_status, _ = run_command(
                ["git", "status", "--porcelain"],
                capture=True,
                cwd=merge_root,
            )
            if target_status.strip():
                raise RuntimeError(f"Target repository at {merge_root} has uncommitted changes.")
            run_command(["git", "checkout", target_branch], cwd=merge_root)
            tracker.complete("checkout", f"using {merge_root}")
        except Exception as exc:
            tracker.error("checkout", str(exc))
            console.print(tracker.render())
            raise typer.Exit(1)

        tracker.start("pull")
        try:
            if not has_remote(merge_root):
                tracker.skip("pull", "no remote configured")
                console.print("[dim]Skipping pull (no remote)[/dim]")
            elif not has_tracking_branch(merge_root):
                tracker.skip("pull", "no upstream tracking")
                console.print("[dim]Skipping pull (main branch not tracking remote)[/dim]")
            else:
                run_command(["git", "pull", "--ff-only"], cwd=merge_root)
                tracker.complete("pull")
        except Exception as exc:
            tracker.error("pull", str(exc))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Could not fast-forward {target_branch}.")
            console.print("You may need to resolve conflicts manually.")
            raise typer.Exit(1)

        # Merge all WP branches
        tracker.start("merge")
        try:
            merged_count = 0
            skipped_count = 0
            skipped_count += len(merge_plan["skipped_already_in_target"]) + len(merge_plan["skipped_ancestor_of"])  # type: ignore[arg-type,index]
            for wt_path, wp_id, branch in effective_workspaces:
                console.print(f"[cyan]Merging {wp_id} ({branch})...[/cyan]")

                if strategy == "squash":
                    run_command(["git", "merge", "--squash", branch], cwd=merge_root)
                    run_command(
                        ["git", "commit", "-m", f"Merge {wp_id} from {feature_slug}"],
                        cwd=merge_root,
                    )
                elif strategy == "rebase":
                    console.print("\n[yellow]Note:[/yellow] Rebase strategy not supported for workspace-per-WP.")
                    console.print("Use 'merge' or 'squash' strategy instead.")
                    tracker.skip("merge", "rebase not supported for workspace-per-WP")
                    console.print(tracker.render())
                    raise typer.Exit(1)
                else:  # merge (default)
                    run_command(
                        ["git", "merge", "--no-ff", branch, "-m", f"Merge {wp_id} from {feature_slug}"],
                        cwd=merge_root,
                    )

                console.print(f"[green]✓[/green] {wp_id} merged")
                _mark_wp_merged_done(merge_root, feature_slug, wp_id, target_branch)
                merged_count += 1

            # Reconcile: mark ALL approved WPs as done (including skipped ancestors)
            all_wp_branches = merge_plan.get("all_wp_branches", [])
            for branch_name in all_wp_branches:
                # Extract WP ID from branch name (e.g., "026-feature-WP03" → "WP03")
                import re as _re_merge
                _wp_match = _re_merge.search(r"(WP\d+)$", branch_name, _re_merge.IGNORECASE)
                if not _wp_match:
                    continue
                _recon_wp_id = _wp_match.group(1).upper()
                # Skip WPs already marked done in this merge
                _already_done = any(
                    wp_id == _recon_wp_id for _, wp_id, _ in effective_workspaces
                )
                if _already_done:
                    continue
                # Mark remaining approved WPs as done (their code is merged via ancestor tips)
                _mark_wp_merged_done(merge_root, feature_slug, _recon_wp_id, target_branch)

            summary = f"merged {merged_count} work packages"
            if skipped_count:
                summary += f", skipped {skipped_count} redundant/already-integrated (all marked done)"
            tracker.complete("merge", summary)
        except Exception as exc:
            tracker.error("merge", str(exc))
            console.print(tracker.render())
            console.print(f"\n[red]Merge failed.[/red] Resolve conflicts and try again.")
            raise typer.Exit(1)

        # Push if requested
        if push:
            tracker.start("push")
            try:
                run_command(["git", "push", "origin", target_branch], cwd=merge_root)
                tracker.complete("push")
            except Exception as exc:
                tracker.error("push", str(exc))
                console.print(tracker.render())
                console.print(f"\n[yellow]Warning:[/yellow] Merge succeeded but push failed.")
                console.print(f"Run manually: git push origin {target_branch}")

    # Remove worktrees (always run — cleanup is needed even when all branches are already integrated)
    if remove_worktree:
        tracker.start("worktree")
        failed_removals = []
        for wt_path, wp_id, branch in wp_workspaces:
            try:
                run_command(
                    ["git", "worktree", "remove", str(wt_path), "--force"],
                    cwd=merge_root,
                )
                console.print(f"[green]✓[/green] Removed worktree: {wp_id}")
            except Exception as exc:
                failed_removals.append((wp_id, wt_path))

        if failed_removals:
            tracker.error("worktree", f"could not remove {len(failed_removals)} worktrees")
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Could not remove some worktrees:")
            for wp_id, wt_path in failed_removals:
                console.print(f"  {wp_id}: git worktree remove {wt_path}")
        else:
            tracker.complete("worktree", f"removed {len(wp_workspaces)} worktrees")

    # Delete branches
    if delete_branch:
        tracker.start("branch")
        failed_deletions = []
        for wt_path, wp_id, branch in wp_workspaces:
            try:
                run_command(["git", "branch", "-d", branch], cwd=merge_root)
                console.print(f"[green]✓[/green] Deleted branch: {branch}")
            except Exception:
                # Try force delete
                try:
                    run_command(["git", "branch", "-D", branch], cwd=merge_root)
                    console.print(f"[green]✓[/green] Force deleted branch: {branch}")
                except Exception:
                    failed_deletions.append((wp_id, branch))

        if failed_deletions:
            tracker.error("branch", f"could not delete {len(failed_deletions)} branches")
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Could not delete some branches:")
            for wp_id, branch in failed_deletions:
                console.print(f"  {wp_id}: git branch -D {branch}")
        else:
            tracker.complete("branch", f"deleted {len(wp_workspaces)} branches")

    console.print(tracker.render())
    if effective_workspaces:
        console.print(
            f"\n[bold green]✓ Feature {feature_slug} ({len(effective_workspaces)}/{len(wp_workspaces)} effective WPs) successfully merged into {target_branch}[/bold green]"
        )
    else:
        console.print(
            f"\n[bold green]✓ Feature {feature_slug} was already integrated into {target_branch}. Cleanup complete.[/bold green]"
        )


def _run_lane_based_merge(
    repo_root: Path,
    feature_slug: str,
    *,
    push: bool = False,
    delete_branch: bool = True,
    remove_worktree: bool = True,
) -> None:
    """Execute lane-based two-tier merge: lanes → mission → target.

    Merges all lane branches into the mission integration branch, then
    merges the mission branch into the target. Cleans up worktrees and
    branches afterward based on flags. Raises typer.Exit on failure.
    """
    from specify_cli.lanes.branch_naming import lane_branch_name as _lane_br
    from specify_cli.lanes.merge import merge_lane_to_mission, merge_mission_to_target
    from specify_cli.lanes.persistence import read_lanes_json

    main_repo = get_main_repo_root(repo_root)
    feature_dir = main_repo / "kitty-specs" / feature_slug
    lanes_manifest = read_lanes_json(feature_dir)

    if lanes_manifest is None:
        console.print("[red]Error:[/red] lanes.json missing or corrupt")
        raise typer.Exit(1)

    console.print(f"[bold]Lane-based merge for {feature_slug}[/bold]")
    console.print(f"  Mission branch: {lanes_manifest.mission_branch}")
    console.print(f"  Lanes: {', '.join(l.lane_id for l in lanes_manifest.lanes)}")

    # Evaluate merge gates before proceeding.
    from specify_cli.policy.config import load_policy_config
    from specify_cli.policy.merge_gates import evaluate_merge_gates

    _policy = load_policy_config(main_repo)
    all_wp_ids = [wp for lane in lanes_manifest.lanes for wp in lane.wp_ids]
    gate_eval = evaluate_merge_gates(
        feature_dir, feature_slug, all_wp_ids, _policy.merge_gates, main_repo,
    )
    for g in gate_eval.gates:
        icon = "[green]✓[/green]" if g.verdict == "pass" else "[yellow]⚠[/yellow]" if not g.blocking else "[red]✗[/red]"
        console.print(f"  {icon} Gate {g.gate_name}: {g.details}")
    if not gate_eval.overall_pass:
        console.print("\n[red]Error:[/red] Merge gates failed. Use --force to override.")
        raise typer.Exit(1)
    for w in gate_eval.warnings:
        console.print(f"  [yellow]Warning:[/yellow] {w}")

    # Step 1: Merge all lane branches into mission branch.
    all_lanes_ok = True
    for lane in lanes_manifest.lanes:
        lane_result = merge_lane_to_mission(
            main_repo, feature_slug, lane.lane_id, lanes_manifest,
        )
        if lane_result.success:
            console.print(f"  [green]✓[/green] {lane.lane_id} → {lanes_manifest.mission_branch}")
        else:
            all_lanes_ok = False
            for err in lane_result.errors:
                console.print(f"  [red]✗[/red] {lane.lane_id}: {err}")

    if not all_lanes_ok:
        console.print("\n[red]Error:[/red] Not all lanes merged. Fix issues above and retry.")
        raise typer.Exit(1)

    # Step 2: Merge mission branch into target.
    mission_result = merge_mission_to_target(main_repo, feature_slug, lanes_manifest)
    if mission_result.success:
        console.print(f"\n[green]✓[/green] {lanes_manifest.mission_branch} → {lanes_manifest.target_branch}")
        if mission_result.commit:
            console.print(f"  Commit: {mission_result.commit[:7]}")
    else:
        for err in mission_result.errors:
            console.print(f"[red]Error:[/red] {err}")
        raise typer.Exit(1)

    # Push.
    if push and has_remote(main_repo):
        run_command(["git", "push", "origin", lanes_manifest.target_branch], cwd=main_repo)
        console.print(f"[green]✓[/green] Pushed {lanes_manifest.target_branch} to origin")

    # Cleanup lane worktrees.
    if remove_worktree:
        for lane in lanes_manifest.lanes:
            wt_path = main_repo / ".worktrees" / f"{feature_slug}-{lane.lane_id}"
            if wt_path.exists():
                run_command(
                    ["git", "worktree", "remove", str(wt_path), "--force"],
                    cwd=main_repo,
                )
                console.print(f"  Removed worktree: {wt_path.name}")

    # Cleanup lane and mission branches.
    if delete_branch:
        for lane in lanes_manifest.lanes:
            branch = _lane_br(feature_slug, lane.lane_id)
            run_command(["git", "branch", "-D", branch], cwd=main_repo, check_return=False)
        run_command(
            ["git", "branch", "-D", lanes_manifest.mission_branch],
            cwd=main_repo, check_return=False,
        )
        console.print(f"  Cleaned up {len(lanes_manifest.lanes)} lane branch(es) + mission branch")


@require_main_repo
def merge(
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
    delete_branch: bool = typer.Option(True, "--delete-branch/--keep-branch", help="Delete feature branch after merge"),
    remove_worktree: bool = typer.Option(True, "--remove-worktree/--keep-worktree", help="Remove feature worktree after merge"),
    push: bool = typer.Option(False, "--push", help="Push to origin after merge"),
    target_branch: str = typer.Option(None, "--target", help="Target branch to merge into (auto-detected)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
    json_output: bool = typer.Option(False, "--json", help="Output deterministic JSON (dry-run mode)"),
    feature: str = typer.Option(None, "--feature", help="Mission slug when merging from main branch (legacy flag name)"),
    resume: bool = typer.Option(False, "--resume", help="Resume an interrupted merge from saved state"),
    abort: bool = typer.Option(False, "--abort", help="Abort and clear merge state"),
    context_token: str = typer.Option(None, "--context", help="MissionContext token for engine-v2 merge"),
    keep_workspace: bool = typer.Option(False, "--keep-workspace", help="Keep merge workspace after completion (for debugging)"),
) -> None:
    """Merge a completed feature branch into the target branch and clean up resources.

    For workspace-per-WP features (0.11.0+), computes an effective branch tip set
    using ancestry pruning, then merges only non-redundant tips.

    For legacy features (0.10.x), merges single feature branch.

    Use --resume to continue an interrupted merge from saved state.
    Use --abort to clear merge state and abort any in-progress git merge.
    Use --keep-workspace to preserve the merge workspace for debugging.
    """
    if not json_output:
        show_banner()

    # Handle --abort flag early (before any other processing)
    if abort:
        try:
            repo_root = find_repo_root()
        except TaskCliError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)

        main_repo = get_main_repo_root(repo_root)

        # Use engine v2 abort (handles workspace cleanup + lock release)
        from specify_cli.merge.engine import abort_merge as engine_abort_merge

        state = load_state(main_repo)
        if state is None:
            console.print("[yellow]No merge state to abort[/yellow]")
        else:
            console.print(f"[cyan]Aborting merge of {state.feature_slug}...[/cyan]")
            console.print(f"  Progress was: {len(state.completed_wps)}/{len(state.wp_order)} WPs complete")

        engine_abort_merge(main_repo)
        console.print(f"[green]✓[/green] Merge aborted and state cleared")

        raise typer.Exit(0)

    # Handle --resume flag (engine v2 path)
    resume_state: MergeState | None = None
    if resume:
        try:
            repo_root = find_repo_root()
        except TaskCliError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)

        main_repo = get_main_repo_root(repo_root)
        resume_state = load_state(main_repo)

        if resume_state is None:
            state_path = get_state_path(main_repo)
            if state_path.exists():
                clear_state(main_repo)
                console.print("[yellow]⚠ Invalid merge state file cleared[/yellow]")
            console.print("[red]Error:[/red] No merge state to resume")
            console.print("Run 'spec-kitty merge --feature <slug>' to start a new merge.")
            raise typer.Exit(1)

        console.print(f"[cyan]Resuming merge of {resume_state.feature_slug}[/cyan]")
        console.print(f"  Progress: {len(resume_state.completed_wps)}/{len(resume_state.wp_order)} WPs")
        console.print(f"  Remaining: {', '.join(resume_state.remaining_wps)}")

        # Check for pending git merge in workspace or main repo
        workspace_path_str = resume_state.workspace_path
        check_root = Path(workspace_path_str) if workspace_path_str else main_repo
        if detect_git_merge_state(check_root):
            console.print("[yellow]⚠ Git merge in progress - resolve conflicts first[/yellow]")
            console.print("Then run 'spec-kitty merge --resume' again.")
            raise typer.Exit(1)

        # Use engine v2 resume
        from specify_cli.merge.engine import resume_merge as engine_resume_merge

        eng_result = engine_resume_merge(main_repo, keep_workspace=keep_workspace)
        if eng_result.success:
            console.print(f"[bold green]✓ Merge resumed and completed successfully.[/bold green]")
            if eng_result.merged_wps:
                console.print(f"  Merged: {', '.join(eng_result.merged_wps)}")
            if eng_result.skipped_wps:
                console.print(f"  Skipped (already done): {', '.join(eng_result.skipped_wps)}")
        else:
            if eng_result.conflicts:
                console.print(f"[yellow]Merge paused — unresolved conflicts:[/yellow]")
                for f in eng_result.conflicts:
                    console.print(f"  {f}")
                console.print("Resolve conflicts, then run 'spec-kitty merge --resume'.")
            else:
                console.print(f"[red]Merge failed:[/red]")
                for err in eng_result.errors:
                    console.print(f"  {err}")
            raise typer.Exit(1)
        raise typer.Exit(0)

        # Set feature from state and override options (kept for legacy paths below)
        feature = resume_state.feature_slug
        target_branch = resume_state.target_branch
        strategy = resume_state.strategy

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    _enforce_git_preflight(repo_root, json_output=json_output)

    resolved_feature = feature

    # Track where the target branch value came from for error messages.
    # Possible values: "flag" (--target), "meta.json", "primary_branch"
    target_source: str | None = "flag" if target_branch is not None else None

    # Resolve target branch dynamically if not specified
    if target_branch is None:
        if resolved_feature:
            target_branch = get_feature_target_branch(repo_root, resolved_feature)
            target_source = "meta.json"
        else:
            # Attempt to derive feature slug from current branch before falling
            # back to resolve_primary_branch().  This handles the case where the
            # user is on a feature/WP branch and omits --feature.
            _, _current_branch, _ = run_command(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True
            )
            _inferred_slug = extract_feature_slug(_current_branch)
            _feature_dir = repo_root / "kitty-specs" / _inferred_slug
            if re.match(r"^\d{3}-.+$", _inferred_slug) and (_feature_dir / "meta.json").exists():
                resolved_feature = _inferred_slug
                target_branch = get_feature_target_branch(repo_root, resolved_feature)
                target_source = "meta.json"
            else:
                from specify_cli.core.git_ops import resolve_primary_branch
                target_branch = resolve_primary_branch(repo_root)
                target_source = "primary_branch"

    # Validate resolved target branch exists (FR-006: hard error, no silent fallback)
    if resolved_feature and target_branch:
        ret_local, _, _ = run_command(
            ["git", "rev-parse", "--verify", f"refs/heads/{target_branch}"],
            capture=True,
            check_return=False,
            cwd=repo_root,
        )
        if ret_local != 0:
            ret_remote, _, _ = run_command(
                ["git", "rev-parse", "--verify", f"refs/remotes/origin/{target_branch}"],
                capture=True,
                check_return=False,
                cwd=repo_root,
            )
            if ret_remote != 0:
                if target_source == "meta.json":
                    error_msg = (
                        f"Target branch '{target_branch}' (from meta.json) does not exist "
                        f"locally or on origin. Check kitty-specs/{resolved_feature}/meta.json."
                    )
                elif target_source == "primary_branch":
                    error_msg = (
                        f"Target branch '{target_branch}' (resolved as primary branch) does not exist "
                        f"locally or on origin. Check kitty-specs/{resolved_feature}/meta.json."
                    )
                else:
                    error_msg = (
                        f"Target branch '{target_branch}' does not exist "
                        f"locally or on origin. Check kitty-specs/{resolved_feature}/meta.json."
                    )
                if json_output:
                    print(json.dumps({
                        "spec_kitty_version": SPEC_KITTY_VERSION,
                        "error": error_msg,
                    }))
                else:
                    console.print(f"[red]Error:[/red] {error_msg}")
                raise typer.Exit(1)

    if json_output and not dry_run:
        print(json.dumps({
            "spec_kitty_version": SPEC_KITTY_VERSION,
            "error": "--json is currently supported with --dry-run only.",
        }))
        raise typer.Exit(1)

    if json_output and dry_run:
        _, current_branch, _ = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
        if current_branch == target_branch and not feature:
            print(json.dumps({
                "spec_kitty_version": SPEC_KITTY_VERSION,
                "error": f"Already on {target_branch}; pass --feature <slug> for workspace-per-WP planning.",
            }))
            raise typer.Exit(1)

        feature_slug = resolved_feature or extract_feature_slug(current_branch)
        structure = detect_worktree_structure(repo_root, feature_slug)
        main_repo = get_main_repo_root(repo_root)

        if structure == "lane-based":
            from specify_cli.lanes.persistence import read_lanes_json
            lanes_manifest = read_lanes_json(main_repo / "kitty-specs" / feature_slug)
            print(json.dumps({
                "spec_kitty_version": SPEC_KITTY_VERSION,
                "feature_slug": feature_slug,
                "structure": "lane-based",
                "mission_branch": lanes_manifest.mission_branch if lanes_manifest else None,
                "lanes": [l.to_dict() for l in lanes_manifest.lanes] if lanes_manifest else [],
                "dry_run": True,
            }))
            raise typer.Exit(0)

        if structure == "workspace-per-wp":
            wp_workspaces = find_wp_worktrees(repo_root, feature_slug)
            merge_plan = _build_workspace_per_wp_merge_plan(
                main_repo,
                feature_slug,
                target_branch,
                wp_workspaces,
            )
            effective_workspaces = merge_plan["effective_wp_workspaces"]  # type: ignore[assignment]
            steps = [
                f"git checkout {target_branch}",
                "git pull --ff-only",
            ]
            for _, wp_id, branch in effective_workspaces:
                if strategy == "squash":
                    steps.extend([
                        f"git merge --squash {branch}",
                        f"git commit -m 'Merge {wp_id} from {feature_slug}'",
                    ])
                else:
                    steps.append(f"git merge --no-ff {branch} -m 'Merge {wp_id} from {feature_slug}'")
            if push:
                steps.append(f"git push origin {target_branch}")
            if remove_worktree:
                for wt_path, wp_id, _ in wp_workspaces:
                    if wt_path.exists():
                        steps.append(f"git worktree remove {wt_path}")
                    else:
                        steps.append(f"# skip worktree removal for {wp_id} (path not present)")
            if delete_branch:
                for _, _, branch in wp_workspaces:
                    steps.append(f"git branch -d {branch}")

            print(json.dumps({
                "spec_kitty_version": SPEC_KITTY_VERSION,
                "feature_slug": feature_slug,
                "target_branch": target_branch,
                "all_wp_branches": [branch for _, _, branch in merge_plan["all_wp_workspaces"]],  # type: ignore[index]
                "effective_wp_branches": [branch for _, _, branch in effective_workspaces],
                "skipped_already_in_target": merge_plan["skipped_already_in_target"],
                "skipped_ancestor_of": merge_plan["skipped_ancestor_of"],
                "planned_steps": steps,
                "reason_summary": merge_plan["reason_summary"],
            }))
            return

        planned_steps = [
            f"git checkout {target_branch}",
            "git pull --ff-only",
        ]
        if strategy == "squash":
            planned_steps.extend([
                f"git merge --squash {feature_slug}",
                f"git commit -m 'Merge feature {feature_slug}'",
            ])
        elif strategy == "rebase":
            planned_steps.append(f"git merge --ff-only {feature_slug} (after rebase)")
        else:
            planned_steps.append(f"git merge --no-ff {feature_slug}")
        if push:
            planned_steps.append(f"git push origin {target_branch}")
        if delete_branch:
            planned_steps.append(f"git branch -d {feature_slug}")

        print(json.dumps({
            "spec_kitty_version": SPEC_KITTY_VERSION,
            "feature_slug": feature_slug,
            "target_branch": target_branch,
            "all_wp_branches": [],
            "effective_wp_branches": [],
            "skipped_already_in_target": [],
            "skipped_ancestor_of": {},
            "planned_steps": planned_steps,
            "reason_summary": ["Legacy/single-branch merge plan generated."],
        }))
        return

    tracker = StepTracker("Feature Merge")
    tracker.add("detect", "Detect current feature and branch")
    tracker.add("preflight", "Pre-flight validation")
    tracker.add("verify", "Verify merge readiness")
    tracker.add("checkout", f"Switch to {target_branch}")
    tracker.add("pull", f"Update {target_branch}")
    tracker.add("merge", "Merge feature branch")
    if push: tracker.add("push", "Push to origin")
    if remove_worktree: tracker.add("worktree", "Remove feature worktree")
    if delete_branch: tracker.add("branch", "Delete feature branch")
    console.print()

    check_version_compatibility(repo_root, "merge")

    # Detect VCS backend
    try:
        vcs = get_vcs(repo_root)
        vcs_backend = vcs.backend
    except Exception:
        # Fall back to git if VCS detection fails
        vcs_backend = VCSBackend.GIT

    # Show VCS backend info
    console.print(f"[dim]VCS Backend: git[/dim]")

    feature_worktree_path = merge_root = repo_root
    tracker.start("detect")
    try:
        _, current_branch, _ = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
        if current_branch == target_branch:
            # Check if --feature flag was provided
            if feature:
                main_repo = get_main_repo_root(repo_root)

                # Check for lane-based structure first
                structure = detect_worktree_structure(main_repo, feature)
                if structure == "lane-based":
                    # Dispatch to lane merge flow (handled below after detect block)
                    resolved_feature = feature
                    feature_slug = feature
                    in_worktree = False
                    merge_root = main_repo
                    tracker.complete("detect", f"lane-based feature {feature}")
                    # Fall through to the lane-based dispatch below
                else:
                    # Validate feature exists by checking for WP worktrees
                    worktrees_dir = main_repo / ".worktrees"
                    wp_pattern = list(worktrees_dir.glob(f"{feature}-WP*")) if worktrees_dir.exists() else []

                    if not wp_pattern:
                        tracker.error("detect", f"no WP worktrees found for {feature}")
                        console.print(tracker.render())
                        console.print(f"\n[red]Error:[/red] No WP worktrees found for feature '{feature}'.")
                        console.print("Check the feature slug or create workspaces first.")
                        raise typer.Exit(1)

                    # Use the provided feature slug and continue
                    feature_slug = feature
                    tracker.complete("detect", f"using --feature {feature_slug}")

                if structure != "lane-based":
                    # WP-per-worktree path: preflight + merge + return
                    wp_workspaces = find_wp_worktrees(repo_root, feature_slug)

                    tracker.skip("verify", "handled in preflight")
                    tracker.start("preflight")
                    preflight_result = run_preflight(
                        feature_slug=feature_slug,
                        target_branch=target_branch,
                        repo_root=main_repo,
                        wp_workspaces=wp_workspaces,
                    )
                    display_preflight_result(preflight_result, console)

                    if not preflight_result.passed:
                        tracker.error("preflight", "validation failed")
                        console.print(tracker.render())
                        raise typer.Exit(1)
                    tracker.complete("preflight", "all checks passed")

                    merge_workspace_per_wp(
                        repo_root=repo_root,
                        merge_root=merge_root,
                        feature_slug=feature_slug,
                        current_branch=current_branch,
                        target_branch=target_branch,
                        strategy=strategy,
                        delete_branch=delete_branch,
                        remove_worktree=remove_worktree,
                        push=push,
                        dry_run=dry_run,
                        json_output=json_output,
                        tracker=tracker,
                        resume_state=resume_state,
                    )
                    return
                # Lane-based: fall through to lane dispatch below
            else:
                tracker.error("detect", f"already on {target_branch}")
                console.print(tracker.render())
                console.print(f"\n[red]Error:[/red] Already on {target_branch} branch.")
                console.print("Use --feature <slug> to specify the feature to merge.")
                raise typer.Exit(1)

        _, git_dir_output, _ = run_command(["git", "rev-parse", "--git-dir"], capture=True)
        git_dir_path = Path(git_dir_output).resolve()
        in_worktree = "worktrees" in git_dir_path.parts
        if in_worktree:
            merge_root = git_dir_path.parents[2]
            if not merge_root.exists():
                raise RuntimeError(f"Primary repository path not found: {merge_root}")
        tracker.complete(
            "detect",
            f"on {current_branch}" + (f" (worktree → operating from {merge_root})" if in_worktree else ""),
        )
    except Exception as exc:
        tracker.error("detect", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    # Detect workspace structure and extract feature slug
    feature_slug = resolved_feature or extract_feature_slug(current_branch)
    structure = detect_worktree_structure(repo_root, feature_slug)

    # Lane-based merge: two-tier flow (lane→mission, then mission→target)
    if structure == "lane-based":
        _run_lane_based_merge(
            repo_root, feature_slug, push=push,
            delete_branch=delete_branch, remove_worktree=remove_worktree,
        )

        return

    # Branch to workspace-per-WP merge if detected
    if structure == "workspace-per-wp":
        tracker.skip("verify", "handled in preflight")
        # Get main repo for preflight
        main_repo = get_main_repo_root(repo_root)
        wp_workspaces = find_wp_worktrees(repo_root, feature_slug)

        # Run preflight checks
        tracker.start("preflight")
        preflight_result = run_preflight(
            feature_slug=feature_slug,
            target_branch=target_branch,
            repo_root=main_repo,
            wp_workspaces=wp_workspaces,
        )
        display_preflight_result(preflight_result, console)

        if not preflight_result.passed:
            tracker.error("preflight", "validation failed")
            console.print(tracker.render())
            raise typer.Exit(1)
        tracker.complete("preflight", "all checks passed")

        merge_workspace_per_wp(
            repo_root=repo_root,
            merge_root=merge_root,
            feature_slug=feature_slug,
            current_branch=current_branch,
            target_branch=target_branch,
            strategy=strategy,
            delete_branch=delete_branch,
            remove_worktree=remove_worktree,
            push=push,
            dry_run=dry_run,
            json_output=json_output,
            tracker=tracker,
            resume_state=resume_state,
        )
        return

    # Continue with legacy merge logic for single worktree
    # Skip preflight for legacy merges (single worktree validation is done above in verify step)
    tracker.skip("preflight", "legacy single-worktree merge")
    tracker.start("verify")
    try:
        _, status_output, _ = run_command(["git", "status", "--porcelain"], capture=True)
        if status_output.strip():
            tracker.error("verify", "uncommitted changes")
            console.print(tracker.render())
            console.print(f"\n[red]Error:[/red] Working directory has uncommitted changes.")
            console.print("Commit or stash your changes before merging.")
            raise typer.Exit(1)
        tracker.complete("verify", "clean working directory")
    except Exception as exc:
        tracker.error("verify", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    merge_root, feature_worktree_path = merge_root.resolve(), feature_worktree_path.resolve()
    if dry_run:
        console.print(tracker.render())
        console.print("\n[cyan]Dry run - would execute:[/cyan]")
        checkout_prefix = f"(from {merge_root}) " if in_worktree else ""
        steps = [
            f"{checkout_prefix}git checkout {target_branch}",
            "git pull --ff-only",
        ]
        if strategy == "squash":
            steps.extend([
                f"git merge --squash {current_branch}",
                f"git commit -m 'Merge feature {current_branch}'",
            ])
        elif strategy == "rebase":
            steps.append(f"git merge --ff-only {current_branch} (after rebase)")
        else:
            steps.append(f"git merge --no-ff {current_branch}")
        if push:
            steps.append(f"git push origin {target_branch}")
        if in_worktree and remove_worktree:
            steps.append(f"git worktree remove {feature_worktree_path}")
        if delete_branch:
            steps.append(f"git branch -d {current_branch}")
        for idx, step in enumerate(steps, start=1):
            console.print(f"  {idx}. {step}")
        return

    tracker.start("checkout")
    try:
        if in_worktree:
            console.print(f"[cyan]Detected worktree. Merge operations will run from {merge_root}[/cyan]")
        _, target_status, _ = run_command(
            ["git", "status", "--porcelain"],
            capture=True,
            cwd=merge_root,
        )
        if target_status.strip():
            raise RuntimeError(f"Target repository at {merge_root} has uncommitted changes.")
        run_command(["git", "checkout", target_branch], cwd=merge_root)
        tracker.complete("checkout", f"using {merge_root}")
    except Exception as exc:
        tracker.error("checkout", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    tracker.start("pull")
    try:
        if not has_remote(merge_root):
            tracker.skip("pull", "no remote configured")
            console.print("[dim]Skipping pull (no remote)[/dim]")
        elif not has_tracking_branch(merge_root):
            tracker.skip("pull", "no upstream tracking")
            console.print("[dim]Skipping pull (main branch not tracking remote)[/dim]")
        else:
            run_command(["git", "pull", "--ff-only"], cwd=merge_root)
            tracker.complete("pull")
    except Exception as exc:
        tracker.error("pull", str(exc))
        console.print(tracker.render())
        console.print(f"\n[yellow]Warning:[/yellow] Could not fast-forward {target_branch}.")
        console.print("You may need to resolve conflicts manually.")
        raise typer.Exit(1)

    tracker.start("merge")
    try:
        if strategy == "squash":
            run_command(["git", "merge", "--squash", current_branch], cwd=merge_root)
            run_command(
                ["git", "commit", "-m", f"Merge feature {current_branch}"],
                cwd=merge_root,
            )
            tracker.complete("merge", "squashed")
        elif strategy == "rebase":
            console.print("\n[yellow]Note:[/yellow] Rebase strategy requires manual intervention.")
            console.print(f"Please run: git checkout {current_branch} && git rebase {target_branch}")
            tracker.skip("merge", "requires manual rebase")
            console.print(tracker.render())
            raise typer.Exit(0)
        else:
            run_command(
                ["git", "merge", "--no-ff", current_branch, "-m", f"Merge feature {current_branch}"],
                cwd=merge_root,
            )
            tracker.complete("merge", "merged with merge commit")
    except Exception as exc:
        tracker.error("merge", str(exc))
        console.print(tracker.render())
        console.print(f"\n[red]Merge failed.[/red] You may need to resolve conflicts.")
        raise typer.Exit(1)

    if push:
        tracker.start("push")
        try:
            run_command(["git", "push", "origin", target_branch], cwd=merge_root)
            tracker.complete("push")
        except Exception as exc:
            tracker.error("push", str(exc))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Merge succeeded but push failed.")
            console.print(f"Run manually: git push origin {target_branch}")

    if in_worktree and remove_worktree:
        tracker.start("worktree")
        try:
            run_command(
                ["git", "worktree", "remove", str(feature_worktree_path), "--force"],
                cwd=merge_root,
            )
            tracker.complete("worktree", f"removed {feature_worktree_path}")
        except Exception as exc:
            tracker.error("worktree", str(exc))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Could not remove worktree.")
            console.print(f"Run manually: git worktree remove {feature_worktree_path}")

    if delete_branch:
        tracker.start("branch")
        try:
            run_command(["git", "branch", "-d", current_branch], cwd=merge_root)
            tracker.complete("branch", f"deleted {current_branch}")
        except Exception as exc:
            try:
                run_command(["git", "branch", "-D", current_branch], cwd=merge_root)
                tracker.complete("branch", f"force deleted {current_branch}")
            except Exception:
                tracker.error("branch", str(exc))
                console.print(tracker.render())
                console.print(f"\n[yellow]Warning:[/yellow] Could not delete branch {current_branch}.")
                console.print(f"Run manually: git branch -d {current_branch}")

    console.print(tracker.render())
    console.print(f"\n[bold green]✓ Feature {current_branch} successfully merged into {target_branch}[/bold green]")
__all__ = ["merge"]
