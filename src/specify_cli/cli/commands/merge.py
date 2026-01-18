"""Merge command implementation.

Merges completed work packages into target branch with VCS abstraction support.
Supports both git and jujutsu backends through the VCS abstraction layer.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer

from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import check_version_compatibility, console, show_banner
from specify_cli.core.git_ops import run_command
from specify_cli.core.vcs import VCSBackend, get_vcs
from specify_cli.merge.executor import execute_legacy_merge, execute_merge
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


def validate_wp_ready_for_merge(
    repo_root: Path, worktree_path: Path, branch_name: str
) -> tuple[bool, str]:
    """Validate WP workspace is ready to merge.

    This is a public wrapper for backward compatibility with tests.
    The actual validation is performed by executor._validate_wp_ready().

    Args:
        repo_root: Repository root path
        worktree_path: Path to the worktree
        branch_name: Branch name to verify

    Returns:
        Tuple of (is_valid, error_message)
    """
    from specify_cli.merge.executor import _validate_wp_ready

    return _validate_wp_ready(repo_root, worktree_path, branch_name)


def merge(
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
    delete_branch: bool = typer.Option(True, "--delete-branch/--keep-branch", help="Delete feature branch after merge"),
    remove_worktree: bool = typer.Option(True, "--remove-worktree/--keep-worktree", help="Remove feature worktree after merge"),
    push: bool = typer.Option(False, "--push", help="Push to origin after merge"),
    target_branch: str = typer.Option("main", "--target", help="Target branch to merge into"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
    feature: str = typer.Option(None, "--feature", help="Feature slug when merging from main branch"),
) -> None:
    """Merge a completed feature branch into the target branch and clean up resources.

    For workspace-per-WP features (0.11.0+), merges all WP branches
    (010-feature-WP01, 010-feature-WP02, etc.) to main in sequence.

    For legacy features (0.10.x), merges single feature branch.
    """
    show_banner()

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

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    check_version_compatibility(repo_root, "merge")

    # Detect VCS backend
    try:
        vcs = get_vcs(repo_root)
        vcs_backend = vcs.backend
    except Exception:
        # Fall back to git if VCS detection fails
        vcs_backend = VCSBackend.GIT

    # Show VCS backend info
    backend_label = "jj" if vcs_backend == VCSBackend.JUJUTSU else "git"
    console.print(f"[dim]VCS Backend: {backend_label}[/dim]")

    # jj-specific merge workflow note
    if vcs_backend == VCSBackend.JUJUTSU:
        console.print("[dim]Note: Using git commands for merge (jj colocated mode)[/dim]")

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

                # Get WP workspaces for merge execution
                wp_workspaces = find_wp_worktrees(repo_root, feature_slug)

                # Proceed directly to workspace-per-wp merge via executor
                tracker.skip("verify", "handled in preflight")
                merge_result = execute_merge(
                    wp_workspaces=wp_workspaces,
                    feature_slug=feature_slug,
                    feature_dir=main_repo / "kitty-specs" / feature_slug,
                    target_branch=target_branch,
                    strategy=strategy,
                    repo_root=main_repo,
                    merge_root=merge_root,
                    tracker=tracker,
                    delete_branch=delete_branch,
                    remove_worktree=remove_worktree,
                    push=push,
                    dry_run=dry_run,
                )
                if not merge_result.success:
                    console.print(tracker.render())
                    if merge_result.error:
                        console.print(f"\n[red]Error:[/red] {merge_result.error}")
                    raise typer.Exit(1)
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
        # Get main repo for merge execution
        main_repo = get_main_repo_root(repo_root)
        wp_workspaces = find_wp_worktrees(repo_root, feature_slug)

        merge_result = execute_merge(
            wp_workspaces=wp_workspaces,
            feature_slug=feature_slug,
            feature_dir=main_repo / "kitty-specs" / feature_slug,
            target_branch=target_branch,
            strategy=strategy,
            repo_root=main_repo,
            merge_root=merge_root,
            tracker=tracker,
            delete_branch=delete_branch,
            remove_worktree=remove_worktree,
            push=push,
            dry_run=dry_run,
        )
        if not merge_result.success:
            console.print(tracker.render())
            if merge_result.error:
                console.print(f"\n[red]Error:[/red] {merge_result.error}")
            raise typer.Exit(1)
        return

    # Continue with legacy merge logic for single worktree
    # Skip preflight for legacy merges (single worktree validation is done above in verify step)
    tracker.skip("preflight", "legacy single-worktree merge")

    legacy_result = execute_legacy_merge(
        current_branch=current_branch,
        target_branch=target_branch,
        strategy=strategy,
        merge_root=merge_root.resolve(),
        feature_worktree_path=feature_worktree_path.resolve(),
        tracker=tracker,
        push=push,
        remove_worktree=remove_worktree,
        delete_branch=delete_branch,
        dry_run=dry_run,
        in_worktree=in_worktree,
    )
    if not legacy_result.success:
        console.print(tracker.render())
        if legacy_result.error:
            console.print(f"\n[red]Error:[/red] {legacy_result.error}")
        raise typer.Exit(1)
__all__ = ["merge"]
