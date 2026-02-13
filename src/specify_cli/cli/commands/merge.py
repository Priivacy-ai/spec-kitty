"""Merge command implementation.

Merges completed work packages into target branch with VCS abstraction support.
Supports both git and jujutsu backends through the VCS abstraction layer.
"""

from __future__ import annotations

import os
import re
import subprocess
import warnings
from pathlib import Path

import typer

from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import check_version_compatibility, console, show_banner
from specify_cli.core.git_ops import run_command
from specify_cli.core.vcs import VCSBackend, get_vcs
from specify_cli.core.context_validation import require_main_repo
from specify_cli.merge.executor import execute_legacy_merge, execute_merge
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


def get_main_repo_root(repo_root: Path) -> Path:
    """Get the main repository root, even if called from a worktree.

    If repo_root is a worktree, find its main repository.
    Otherwise, return repo_root as-is.
    """
    git_dir = repo_root / ".git"

    # If .git is a directory, we're in the main repo
    if git_dir.is_dir():
        return repo_root

    # If .git is a file, we're in a worktree - read it to find main repo
    if git_dir.is_file():
        git_file_content = git_dir.read_text().strip()
        # Format: "gitdir: /path/to/main/repo/.git/worktrees/feature-name"
        if git_file_content.startswith("gitdir: "):
            gitdir_path = Path(git_file_content[8:])  # Remove "gitdir: " prefix
            # Go up from .git/worktrees/feature-name to main repo root
            # gitdir_path points to: /main/repo/.git/worktrees/feature-name
            # We want: /main/repo
            if "worktrees" in gitdir_path.parts:
                # Find the .git parent
                main_git_dir = gitdir_path
                while main_git_dir.name != ".git":
                    main_git_dir = main_git_dir.parent
                    if main_git_dir == main_git_dir.parent:
                        # Reached root without finding .git
                        break
                return main_git_dir.parent

    # Fallback: return as-is
    return repo_root


def detect_worktree_structure(repo_root: Path, feature_slug: str) -> str:
    """Detect if feature uses legacy or workspace-per-WP model.

    Returns: "legacy", "workspace-per-wp", or "none"

    IMPORTANT: This function must work correctly when called from within a worktree.
    repo_root may be a worktree directory, so we need to find the main repo first.
    """
    # Get the main repository root (handles case where repo_root is a worktree)
    main_repo = get_main_repo_root(repo_root)
    worktrees_dir = main_repo / ".worktrees"

    if not worktrees_dir.exists():
        return "none"

    # Look for workspace-per-WP pattern FIRST (takes precedence per spec)
    # Pattern: .worktrees/###-feature-WP##/
    wp_pattern = list(worktrees_dir.glob(f"{feature_slug}-WP*"))
    if wp_pattern:
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

    wp_workspaces = []
    for wt_path in wp_worktrees:
        wp_id = extract_wp_id(wt_path)
        if wp_id:
            branch_name = wt_path.name  # Directory name = branch name
            wp_workspaces.append((wt_path, wp_id, branch_name))

    return wp_workspaces


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

    # Check 2: No uncommitted changes in worktree
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.stdout.strip():
        return False, f"Worktree {worktree_path.name} has uncommitted changes"

    return True, ""


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

    # Dry run: show what would be done
    if dry_run:
        console.print(tracker.render())
        console.print("\n[cyan]Dry run - would execute:[/cyan]")
        steps = [
            f"git checkout {target_branch}",
            "git pull --ff-only",
        ]
        for wt_path, wp_id, branch in wp_workspaces:
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
                steps.append(f"git worktree remove {wt_path}")

        if delete_branch:
            for wt_path, wp_id, branch in wp_workspaces:
                steps.append(f"git branch -d {branch}")

        for idx, step in enumerate(steps, start=1):
            console.print(f"  {idx}. {step}")
        return

    # Checkout and update target branch
    tracker.start("checkout")
    try:
        console.print(f"[cyan]Operating from {merge_root}[/cyan]")
        os.chdir(merge_root)
        _, target_status, _ = run_command(["git", "status", "--porcelain"], capture=True)
        if target_status.strip():
            raise RuntimeError(f"Target repository at {merge_root} has uncommitted changes.")
        run_command(["git", "checkout", target_branch])
        tracker.complete("checkout", f"using {merge_root}")
    except Exception as exc:
        tracker.error("checkout", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    tracker.start("pull")
    try:
        run_command(["git", "pull", "--ff-only"])
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
        for wt_path, wp_id, branch in wp_workspaces:
            console.print(f"[cyan]Merging {wp_id} ({branch})...[/cyan]")

            if strategy == "squash":
                run_command(["git", "merge", "--squash", branch])
                run_command(["git", "commit", "-m", f"Merge {wp_id} from {feature_slug}"])
            elif strategy == "rebase":
                console.print("\n[yellow]Note:[/yellow] Rebase strategy not supported for workspace-per-WP.")
                console.print("Use 'merge' or 'squash' strategy instead.")
                tracker.skip("merge", "rebase not supported for workspace-per-WP")
                console.print(tracker.render())
                raise typer.Exit(1)
            else:  # merge (default)
                run_command(["git", "merge", "--no-ff", branch, "-m", f"Merge {wp_id} from {feature_slug}"])

            console.print(f"[green]✓[/green] {wp_id} merged")

        tracker.complete("merge", f"merged {len(wp_workspaces)} work packages")
    except Exception as exc:
        tracker.error("merge", str(exc))
        console.print(tracker.render())
        console.print(f"\n[red]Merge failed.[/red] Resolve conflicts and try again.")
        raise typer.Exit(1)

    # Push if requested
    if push:
        tracker.start("push")
        try:
            run_command(["git", "push", "origin", target_branch])
            tracker.complete("push")
        except Exception as exc:
            tracker.error("push", str(exc))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Merge succeeded but push failed.")
            console.print(f"Run manually: git push origin {target_branch}")

    # Remove worktrees
    if remove_worktree:
        tracker.start("worktree")
        failed_removals = []
        for wt_path, wp_id, branch in wp_workspaces:
            try:
                run_command(["git", "worktree", "remove", str(wt_path), "--force"])
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
                run_command(["git", "branch", "-d", branch])
                console.print(f"[green]✓[/green] Deleted branch: {branch}")
            except Exception:
                # Try force delete
                try:
                    run_command(["git", "branch", "-D", branch])
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
    console.print(f"\n[bold green]✓ Feature {feature_slug} ({len(wp_workspaces)} WPs) successfully merged into {target_branch}[/bold green]")


@require_main_repo
def merge(
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
    delete_branch: bool = typer.Option(True, "--delete-branch/--keep-branch", help="Delete feature branch after merge"),
    remove_worktree: bool = typer.Option(True, "--remove-worktree/--keep-worktree", help="Remove feature worktree after merge"),
    push: bool = typer.Option(False, "--push", help="Push to origin after merge"),
    target_branch: str = typer.Option(None, "--target", help="Target branch to merge into (auto-detected)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
    feature: str = typer.Option(None, "--feature", help="Feature slug when merging from main branch"),
    resume: bool = typer.Option(False, "--resume", help="Resume an interrupted merge from saved state"),
    abort: bool = typer.Option(False, "--abort", help="Abort and clear merge state"),
) -> None:
    """Merge a completed feature branch into the target branch and clean up resources.

    For workspace-per-WP features (0.11.0+), merges all WP branches
    (010-feature-WP01, 010-feature-WP02, etc.) to main in sequence.

    For legacy features (0.10.x), merges single feature branch.

    Use --resume to continue an interrupted merge from saved state.
    Use --abort to clear merge state and abort any in-progress git merge.
    """
    show_banner()

    # Handle --abort flag early (before any other processing)
    if abort:
        try:
            repo_root = find_repo_root()
        except TaskCliError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)

        main_repo = get_main_repo_root(repo_root)
        state = load_state(main_repo)

        if state is None:
            console.print("[yellow]No merge state to abort[/yellow]")
        else:
            clear_state(main_repo)
            console.print(f"[green]✓[/green] Merge state cleared for {state.feature_slug}")
            console.print(f"  Progress was: {len(state.completed_wps)}/{len(state.wp_order)} WPs complete")

        # Also abort git merge if in progress
        if abort_git_merge(main_repo):
            console.print("[green]✓[/green] Git merge aborted")

        raise typer.Exit(0)

    # Handle --resume flag
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

        # Check for pending git merge
        if detect_git_merge_state(main_repo):
            console.print("[yellow]⚠ Git merge in progress - resolve conflicts first[/yellow]")
            console.print("Then run 'spec-kitty merge --resume' again.")
            raise typer.Exit(1)

        # Set feature from state and override options
        feature = resume_state.feature_slug
        target_branch = resume_state.target_branch
        strategy = resume_state.strategy

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    # Resolve target branch dynamically if not specified
    if target_branch is None:
        from specify_cli.core.git_ops import resolve_primary_branch
        target_branch = resolve_primary_branch(repo_root)

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
                # Validate feature exists by checking for worktrees
                main_repo = get_main_repo_root(repo_root)
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

                # Get WP workspaces for preflight and merge
                wp_workspaces = find_wp_worktrees(repo_root, feature_slug)

                # Run preflight checks
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

                # Proceed directly to workspace-per-wp merge
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
                    tracker=tracker,
                    resume_state=resume_state,
                )
                return
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
    feature_slug = extract_feature_slug(current_branch)
    structure = detect_worktree_structure(repo_root, feature_slug)

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
        os.chdir(merge_root)
        _, target_status, _ = run_command(["git", "status", "--porcelain"], capture=True)
        if target_status.strip():
            raise RuntimeError(f"Target repository at {merge_root} has uncommitted changes.")
        run_command(["git", "checkout", target_branch])
        tracker.complete("checkout", f"using {merge_root}")
    except Exception as exc:
        tracker.error("checkout", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    tracker.start("pull")
    try:
        run_command(["git", "pull", "--ff-only"])
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
            run_command(["git", "merge", "--squash", current_branch])
            run_command(["git", "commit", "-m", f"Merge feature {current_branch}"])
            tracker.complete("merge", "squashed")
        elif strategy == "rebase":
            console.print("\n[yellow]Note:[/yellow] Rebase strategy requires manual intervention.")
            console.print(f"Please run: git checkout {current_branch} && git rebase {target_branch}")
            tracker.skip("merge", "requires manual rebase")
            console.print(tracker.render())
            raise typer.Exit(0)
        else:
            run_command(["git", "merge", "--no-ff", current_branch, "-m", f"Merge feature {current_branch}"])
            tracker.complete("merge", "merged with merge commit")
    except Exception as exc:
        tracker.error("merge", str(exc))
        console.print(tracker.render())
        console.print(f"\n[red]Merge failed.[/red] You may need to resolve conflicts.")
        raise typer.Exit(1)

    if push:
        tracker.start("push")
        try:
            run_command(["git", "push", "origin", target_branch])
            tracker.complete("push")
        except Exception as exc:
            tracker.error("push", str(exc))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Merge succeeded but push failed.")
            console.print(f"Run manually: git push origin {target_branch}")

    if in_worktree and remove_worktree:
        tracker.start("worktree")
        try:
            run_command(["git", "worktree", "remove", str(feature_worktree_path), "--force"])
            tracker.complete("worktree", f"removed {feature_worktree_path}")
        except Exception as exc:
            tracker.error("worktree", str(exc))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Could not remove worktree.")
            console.print(f"Run manually: git worktree remove {feature_worktree_path}")

    if delete_branch:
        tracker.start("branch")
        try:
            run_command(["git", "branch", "-d", current_branch])
            tracker.complete("branch", f"deleted {current_branch}")
        except Exception as exc:
            try:
                run_command(["git", "branch", "-D", current_branch])
                tracker.complete("branch", f"force deleted {current_branch}")
            except Exception:
                tracker.error("branch", str(exc))
                console.print(tracker.render())
                console.print(f"\n[yellow]Warning:[/yellow] Could not delete branch {current_branch}.")
                console.print(f"Run manually: git branch -d {current_branch}")

    console.print(tracker.render())
    console.print(f"\n[bold green]✓ Feature {current_branch} successfully merged into {target_branch}[/bold green]")
__all__ = ["merge"]
