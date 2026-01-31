"""Implement command - create workspace for work package implementation."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console

from specify_cli.cli import StepTracker
from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    get_dependents,
    parse_wp_dependencies,
)
from specify_cli.core.vcs import (
    get_vcs,
    VCSBackend,
    VCSLockError,
)
from specify_cli.frontmatter import read_frontmatter, update_fields
from specify_cli.tasks_support import (
    TaskCliError,
    find_repo_root,
    locate_work_package,
    set_scalar,
    build_document,
)
from specify_cli.workspace_context import WorkspaceContext, save_context
from specify_cli.core.multi_parent_merge import create_multi_parent_base
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.feature_detection import (
    detect_feature,
    FeatureDetectionError,
)

console = Console()


def detect_feature_context(feature_flag: str | None = None) -> tuple[str, str]:
    """Detect feature number and slug from current context using centralized detection.

    This function now uses the centralized feature detection module
    to provide deterministic, consistent behavior across all commands.

    Args:
        feature_flag: Explicit feature slug from --feature flag (optional)

    Returns:
        Tuple of (feature_number, feature_slug)
        Example: ("010", "010-workspace-per-wp")

    Raises:
        typer.Exit: If feature context cannot be detected
    """
    try:
        repo_root = find_repo_root()
        ctx = detect_feature(
            repo_root,
            explicit_feature=feature_flag,
            cwd=Path.cwd(),
            mode="strict"
        )
        return ctx.number, ctx.slug
    except TaskCliError:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)
    except FeatureDetectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def find_wp_file(repo_root: Path, feature_slug: str, wp_id: str) -> Path:
    """Find WP file in kitty-specs/###-feature/tasks/ directory.

    Args:
        repo_root: Repository root path
        feature_slug: Feature slug (e.g., "010-workspace-per-wp")
        wp_id: Work package ID (e.g., "WP01")

    Returns:
        Path to WP file

    Raises:
        FileNotFoundError: If WP file not found
    """
    tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"
    if not tasks_dir.exists():
        raise FileNotFoundError(f"Tasks directory not found: {tasks_dir}")

    # Search for WP##-*.md pattern
    wp_files = list(tasks_dir.glob(f"{wp_id}-*.md"))
    if not wp_files:
        raise FileNotFoundError(f"WP file not found for {wp_id} in {tasks_dir}")

    return wp_files[0]


def validate_workspace_path(workspace_path: Path, wp_id: str) -> bool:
    """Ensure workspace path is available or reusable.

    Args:
        workspace_path: Path to workspace directory
        wp_id: Work package ID

    Returns:
        True if workspace already exists and is valid (reusable)
        False if workspace doesn't exist (should create)

    Raises:
        typer.Exit: If directory exists but is not a valid worktree
    """
    if not workspace_path.exists():
        return False  # Good - doesn't exist, should create

    # Check if it's a valid git worktree
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=workspace_path,
        capture_output=True,
        check=False
    )

    if result.returncode == 0:
        # Valid worktree exists
        console.print(f"[cyan]Workspace for {wp_id} already exists[/cyan]")
        console.print(f"Reusing: {workspace_path}")

        # SECURITY CHECK: Detect symlinks to kitty-specs/ (bypass attempt)
        kitty_specs_path = workspace_path / "kitty-specs"
        if kitty_specs_path.is_symlink():
            console.print()
            console.print("[bold red]⚠️  SECURITY WARNING: kitty-specs/ is a symlink![/bold red]")
            console.print(f"   Target: {kitty_specs_path.resolve()}")
            console.print("   This bypasses sparse-checkout isolation and can corrupt main repo state.")
            console.print(f"   Remove with: rm {kitty_specs_path}")
            console.print()
            raise typer.Exit(1)

        return True  # Reuse existing

    # Directory exists but not a worktree
    console.print(f"[red]Error:[/red] Directory exists but is not a valid worktree")
    console.print(f"Path: {workspace_path}")
    console.print(f"Remove manually: rm -rf {workspace_path}")
    raise typer.Exit(1)


def check_base_branch_changed(workspace_path: Path, base_branch: str) -> bool:
    """Check if base branch has commits not in current workspace.

    Args:
        workspace_path: Path to workspace directory
        base_branch: Base branch name (e.g., "010-workspace-per-wp-WP01")

    Returns:
        True if base branch has new commits not in workspace
    """
    try:
        # Get merge-base (common ancestor between workspace and base)
        result = subprocess.run(
            ["git", "merge-base", "HEAD", base_branch],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            # Cannot determine merge-base (branches diverged too much or other issue)
            return False

        merge_base = result.stdout.strip()

        # Get base branch tip
        result = subprocess.run(
            ["git", "rev-parse", base_branch],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False

        base_tip = result.stdout.strip()

        # If merge-base != base tip, base has new commits
        return merge_base != base_tip

    except Exception:
        # If git commands fail, assume no changes
        return False


def resolve_primary_branch(repo_root: Path) -> str:
    """Resolve the primary branch name (main or master).

    Returns:
        "main" if it exists, otherwise "master" if it exists.

    Raises:
        typer.Exit: If neither branch exists.
    """
    for candidate in ("main", "master"):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", candidate],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return candidate

    console.print("[red]Error:[/red] Neither 'main' nor 'master' branch exists.")
    raise typer.Exit(1)


def display_rebase_warning(
    workspace_path: Path,
    wp_id: str,
    base_branch: str,
    feature_slug: str
) -> None:
    """Display warning about needing to rebase on changed base.

    Args:
        workspace_path: Path to workspace directory
        wp_id: Work package ID (e.g., "WP02")
        base_branch: Base branch name (e.g., "010-workspace-per-wp-WP01")
        feature_slug: Feature slug (e.g., "010-workspace-per-wp")
    """
    console.print(f"\n[bold yellow]⚠️  Base branch {base_branch} has changed[/bold yellow]")
    console.print(f"Your {wp_id} workspace may have outdated code from base\n")

    console.print("[cyan]Recommended action:[/cyan]")
    console.print(f"  cd {workspace_path}")
    console.print(f"  git rebase {base_branch}")
    console.print("  # Resolve any conflicts")
    console.print("  git add .")
    console.print("  git rebase --continue\n")

    console.print("[yellow]This is a git limitation.[/yellow]")
    console.print("Future jj integration will auto-rebase dependent workspaces.\n")


def check_for_dependents(
    repo_root: Path,
    feature_slug: str,
    wp_id: str
) -> None:
    """Check if any WPs depend on this WP and warn if not yet done.

    Args:
        repo_root: Repository root path
        feature_slug: Feature slug (e.g., "010-workspace-per-wp")
        wp_id: Work package ID (e.g., "WP01")
    """
    feature_dir = repo_root / "kitty-specs" / feature_slug

    # Build dependency graph
    graph = build_dependency_graph(feature_dir)

    # Get dependents
    dependents = get_dependents(wp_id, graph)
    if not dependents:
        return  # No dependents, no warnings needed

    # Check if any dependents are incomplete (any lane except done)
    incomplete_deps = []
    for dep_id in dependents:
        try:
            dep_file = find_wp_file(repo_root, feature_slug, dep_id)
            frontmatter, _ = read_frontmatter(dep_file)
            lane = frontmatter.get("lane", "planned")

            if lane in ["planned", "doing", "for_review"]:
                incomplete_deps.append(dep_id)
        except (FileNotFoundError, Exception):
            # If we can't read the dependent's metadata, skip it
            continue

    if incomplete_deps:
        console.print(f"\n[yellow]⚠️  Dependency Alert:[/yellow]")
        console.print(f"{', '.join(incomplete_deps)} depend on {wp_id} (not yet done)")
        console.print("If you modify this WP, dependent WPs will need manual rebase:")
        for dep_id in incomplete_deps:
            dep_workspace = f".worktrees/{feature_slug}-{dep_id}"
            console.print(f"  cd {dep_workspace} && git rebase {feature_slug}-{wp_id}")
        console.print()


def _ensure_planning_artifacts_committed_git(
    repo_root: Path,
    feature_dir: Path,
    feature_slug: str,
    wp_id: str,
    primary_branch: str,
) -> None:
    """Ensure planning artifacts are committed using git commands.

    For git repos, checks that:
    1. We're on the primary branch (main/master)
    2. No uncommitted files exist in kitty-specs/$feature/

    If uncommitted files exist and we're on the primary branch, auto-commits them.

    Args:
        repo_root: Repository root path
        feature_dir: Path to feature directory (kitty-specs/###-feature/)
        feature_slug: Feature slug (e.g., "001-my-feature")
        wp_id: Work package ID (e.g., "WP01")
        primary_branch: Primary branch name (main/master)

    Raises:
        typer.Exit: If not on primary branch or commit fails
    """
    # Check current branch
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False
    )
    current_branch = result.stdout.strip() if result.returncode == 0 else ""

    # Check git status for untracked/modified files in feature directory
    result = subprocess.run(
        ["git", "status", "--porcelain", str(feature_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode == 0 and result.stdout.strip():
        # Parse git status output - any file showing up needs to be committed
        # Porcelain format: XY filename (X=staged, Y=working tree)
        # Examples: ??(untracked), M (staged modified), MM(staged+modified), etc.
        files_to_commit = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                # Get status code (first 2 chars) and filepath (rest after space)
                if len(line) >= 3:
                    filepath = line[3:].strip()
                    # Any file with status means it's untracked, modified, or staged
                    # All of these should be included in the commit
                    files_to_commit.append(filepath)

        if files_to_commit:
            console.print(f"\n[cyan]Planning artifacts not committed:[/cyan]")
            for f in files_to_commit:
                console.print(f"  {f}")

            if current_branch != primary_branch:
                console.print(
                    f"\n[red]Error:[/red] Planning artifacts must be committed on {primary_branch}."
                )
                console.print(f"Current branch: {current_branch}")
                console.print(f"Run: git checkout {primary_branch}")
                raise typer.Exit(1)

            console.print(f"\n[cyan]Auto-committing to {primary_branch}...[/cyan]")

            # Stage all files in feature directory
            # Use -f to force-add files in kitty-specs/ which is in .gitignore
            result = subprocess.run(
                ["git", "add", "-f", str(feature_dir)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                console.print(f"[red]Error:[/red] Failed to stage files")
                console.print(result.stderr)
                raise typer.Exit(1)

            # Commit with descriptive message
            commit_msg = f"chore: Planning artifacts for {feature_slug}\n\nAuto-committed by spec-kitty before creating workspace for {wp_id}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                console.print(f"[red]Error:[/red] Failed to commit")
                console.print(result.stderr)
                raise typer.Exit(1)

            console.print(f"[green]✓[/green] Planning artifacts committed to {primary_branch}")


def _ensure_planning_artifacts_committed_jj(
    repo_root: Path,
    feature_dir: Path,
    feature_slug: str,
    wp_id: str,
    primary_branch: str,
) -> None:
    """Verify planning artifacts exist for jj repos.

    For jj repos, the working copy IS always a commit - there's no "uncommitted"
    state like in git. We just need to verify the feature directory exists.

    The user can run orchestration from any bookmark - we don't enforce being
    on main. The planning artifacts just need to exist in the current revision.

    Args:
        repo_root: Repository root path
        feature_dir: Path to feature directory (kitty-specs/###-feature/)
        feature_slug: Feature slug (e.g., "001-my-feature")
        wp_id: Work package ID (e.g., "WP01")
        primary_branch: Primary branch name (main/master) - not enforced

    Raises:
        typer.Exit: If feature directory doesn't exist
    """
    # In jj, working copy IS a commit - no "uncommitted" state
    # Just verify the feature directory exists
    if not feature_dir.exists():
        console.print(
            f"\n[red]Error:[/red] Feature directory not found: {feature_dir}"
        )
        console.print("Run planning commands first (specify, plan, tasks)")
        raise typer.Exit(1)

    # Get current bookmark for display
    result = subprocess.run(
        ["jj", "log", "-r", "@", "--no-graph", "-T", "bookmarks"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False
    )
    current_bookmark = result.stdout.strip() if result.returncode == 0 else "unknown"
    console.print(f"[green]✓[/green] Planning artifacts ready (on {current_bookmark or '@'})")


def _ensure_vcs_in_meta(feature_dir: Path, repo_root: Path) -> VCSBackend:
    """Ensure VCS is selected and locked in meta.json.

    Always locks to git (jj support removed due to sparse checkout incompatibility).

    If a feature was created with jj, it will be automatically converted to git
    with a warning message.

    Args:
        feature_dir: Path to the feature directory (kitty-specs/###-feature/)
        repo_root: Repository root path (not used, but kept for compatibility)

    Returns:
        VCSBackend.GIT (always)

    Raises:
        typer.Exit: If meta.json is missing or malformed
    """
    meta_path = feature_dir / "meta.json"

    if not meta_path.exists():
        console.print(f"[red]Error:[/red] meta.json not found in {feature_dir}")
        console.print("Run /spec-kitty.specify first to create feature structure")
        raise typer.Exit(1)

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON in meta.json: {e}")
        raise typer.Exit(1)

    # Check if VCS is already locked
    if "vcs" in meta:
        backend_str = meta["vcs"]
        if backend_str == "jj":
            console.print("[yellow]Warning:[/yellow] Feature was created with jj, but jj is no longer supported.")
            console.print("[yellow]Converting to git...[/yellow]")
            # Override to git
            meta["vcs"] = "git"
            meta["vcs_locked_at"] = datetime.now(timezone.utc).isoformat()
            meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
            return VCSBackend.GIT
        # Already git
        return VCSBackend.GIT

    # VCS not yet locked - lock to git (only supported VCS)
    meta["vcs"] = "git"
    meta["vcs_locked_at"] = datetime.now(timezone.utc).isoformat()

    # Write updated meta.json
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    console.print("[cyan]→ VCS locked to git in meta.json[/cyan]")
    return VCSBackend.GIT


@require_main_repo
def implement(
    wp_id: str = typer.Argument(..., help="Work package ID (e.g., WP01)"),
    base: str = typer.Option(None, "--base", help="Base WP to branch from (e.g., WP01)"),
    feature: str = typer.Option(None, "--feature", help="Feature slug (e.g., 001-my-feature)"),
    force: bool = typer.Option(False, "--force", help="Force auto-merge even when dependencies are done"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
) -> None:
    """Create workspace for work package implementation.

    Creates a git worktree for the specified work package, branching from
    the feature's target branch (for WPs with no dependencies) or from a base WP's branch.

    Examples:
        # Create workspace for WP01 (no dependencies)
        spec-kitty implement WP01

        # Create workspace for WP02, branching from WP01
        spec-kitty implement WP02 --base WP01

        # Force auto-merge when all multi-parent dependencies are done
        spec-kitty implement WP06 --force

        # Explicit feature specification
        spec-kitty implement WP01 --feature 001-my-feature

        # JSON output for scripting
        spec-kitty implement WP01 --json
    """
    # Context validation handled by @require_main_repo decorator
    tracker = StepTracker(f"Implement {wp_id}")
    tracker.add("detect", "Detect feature context")
    tracker.add("validate", "Validate dependencies")
    tracker.add("create", "Create workspace")
    console.print()

    # Step 1: Detect feature context
    tracker.start("detect")
    try:
        repo_root = find_repo_root()
        feature_number, feature_slug = detect_feature_context(feature)
        tracker.complete("detect", f"Feature: {feature_slug}")
    except (TaskCliError, typer.Exit) as exc:
        tracker.error("detect", str(exc) if isinstance(exc, TaskCliError) else "failed")
        console.print(tracker.render())
        raise typer.Exit(1)

    # Step 2: Validate dependencies
    tracker.start("validate")
    auto_merge_base = False  # Track if we're using auto-merge
    try:
        # Find WP file to read dependencies
        wp_file = find_wp_file(repo_root, feature_slug, wp_id)
        declared_deps = parse_wp_dependencies(wp_file)

        # Multi-parent dependency handling
        if len(declared_deps) > 1 and base is None:
            # Check if all dependencies are done - suggest merge-first workflow
            from specify_cli.core.dependency_resolver import check_dependency_status

            feature_dir = repo_root / "kitty-specs" / feature_slug
            dep_status = check_dependency_status(feature_dir, wp_id, declared_deps)

            if dep_status.should_suggest_merge_first and not force:
                # All dependencies done - suggest merging to main first
                tracker.error("validate", "dependencies should be merged first")
                console.print(tracker.render())
                console.print(f"\n[yellow]Suggestion:[/yellow] {dep_status.get_recommendation()}")
                raise typer.Exit(1)

            # Auto-merge mode: Create merge commit combining all dependencies
            console.print(f"\n[cyan]Multi-parent dependency detected:[/cyan]")
            console.print(f"  {wp_id} depends on: {', '.join(declared_deps)}")

            if dep_status.all_done:
                console.print(f"  [yellow]Warning:[/yellow] All dependencies done - merge conflicts likely")
                console.print(f"  Attempting auto-merge (use merge command for safer workflow)...")
            else:
                console.print(f"  Auto-creating merge base combining all dependencies...")

            auto_merge_base = True
            # Will create merge base after validation completes

        # Single dependency handling - auto-detect base
        elif len(declared_deps) == 1 and base is None:
            # Auto-use the single dependency as base (no need to make user specify it!)
            base = declared_deps[0]
            console.print(f"\n[cyan]Auto-detected:[/cyan] {wp_id} depends on {base}")
            console.print(f"Using --base {base} automatically")

        # If --base provided, validate it matches declared dependencies
        if base:
            if base not in declared_deps and declared_deps:
                console.print(f"[yellow]Warning:[/yellow] {wp_id} does not declare dependency on {base}")
                console.print(f"Declared dependencies: {declared_deps}")
                # Allow but warn (user might know better than parser)

            # Validate base workspace exists
            base_workspace = repo_root / ".worktrees" / f"{feature_slug}-{base}"
            if not base_workspace.exists():
                tracker.error("validate", f"base workspace {base} not found")
                console.print(tracker.render())
                console.print(f"\n[red]Error:[/red] Base workspace {base} does not exist")
                console.print(f"Implement {base} first: spec-kitty implement {base}")
                raise typer.Exit(1)

            # Verify it's a valid worktree
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=base_workspace,
                capture_output=True,
                check=False
            )
            if result.returncode != 0:
                tracker.error("validate", f"base workspace {base} invalid")
                console.print(tracker.render())
                console.print(f"[red]Error:[/red] {base_workspace} exists but is not a valid worktree")
                raise typer.Exit(1)

        tracker.complete("validate", f"Base: {base or 'main'}")
    except (FileNotFoundError, typer.Exit) as exc:
        if not isinstance(exc, typer.Exit):
            tracker.error("validate", str(exc))
            console.print(tracker.render())
        raise typer.Exit(1)

    # Step 2.5: Ensure planning artifacts are committed (v0.11.0 requirement)
    # All planning must happen in primary branch and be committed BEFORE worktree creation
    if base is None:  # Only for first WP in feature (branches from main)
        try:
            # Detect VCS backend early to use appropriate commands
            feature_dir = repo_root / "kitty-specs" / feature_slug
            if not feature_dir.exists():
                console.print(f"\n[red]Error:[/red] Feature directory not found: {feature_dir}")
                console.print(f"Run /spec-kitty.specify first")
                raise typer.Exit(1)

            # Get VCS backend (auto-detect or from meta.json)
            vcs = get_vcs(repo_root)
            vcs_backend = vcs.backend

            primary_branch = resolve_primary_branch(repo_root)

            if vcs_backend == VCSBackend.GIT:
                # Git path: check branch and status using git commands
                _ensure_planning_artifacts_committed_git(
                    repo_root, feature_dir, feature_slug, wp_id, primary_branch
                )
            else:
                # jj path: check status and commit using jj commands
                _ensure_planning_artifacts_committed_jj(
                    repo_root, feature_dir, feature_slug, wp_id, primary_branch
                )

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"\n[red]Error:[/red] Failed to validate planning artifacts: {e}")
            raise typer.Exit(1)

    # Step 3: Create workspace
    tracker.start("create")
    try:
        # Determine workspace path and branch name
        workspace_name = f"{feature_slug}-{wp_id}"
        workspace_path = repo_root / ".worktrees" / workspace_name
        branch_name = workspace_name  # Same as workspace dir name

        # Ensure VCS is locked in meta.json and get the backend to use
        # (do this early so we can use VCS for all operations)
        feature_dir = repo_root / "kitty-specs" / feature_slug
        vcs_backend = _ensure_vcs_in_meta(feature_dir, repo_root)

        # Get VCS implementation
        vcs = get_vcs(repo_root, backend=vcs_backend)

        # Check if workspace already exists using VCS abstraction
        workspace_info = vcs.get_workspace_info(workspace_path)
        if workspace_info is not None:
            # Workspace exists and is valid, reuse it
            tracker.complete("create", f"Reused: {workspace_path}")
            console.print(tracker.render())

            # Use VCS abstraction for stale detection
            if workspace_info.is_stale:
                if base:
                    base_branch = f"{feature_slug}-{base}"
                    display_rebase_warning(workspace_path, wp_id, base_branch, feature_slug)
                else:
                    # No explicit base, but workspace is stale (base changed)
                    console.print(f"\n[yellow]⚠️  Workspace is stale (base has changed)[/yellow]")
                    if vcs_backend == VCSBackend.JUJUTSU:
                        console.print("Run [bold]jj workspace update-stale[/bold] to sync")
                    else:
                        console.print(f"Consider rebasing if needed")

            # Check for dependent WPs (T079)
            check_for_dependents(repo_root, feature_slug, wp_id)

            return

        # Validate workspace path doesn't exist as a non-workspace directory
        if workspace_path.exists():
            console.print(f"[red]Error:[/red] Directory exists but is not a valid workspace")
            console.print(f"Path: {workspace_path}")
            console.print(f"Remove manually: rm -rf {workspace_path}")
            raise typer.Exit(1)

        # Determine base branch
        if auto_merge_base:
            # Multi-parent: Create merge base combining all dependencies
            merge_result = create_multi_parent_base(
                feature_slug=feature_slug,
                wp_id=wp_id,
                dependencies=declared_deps,
                repo_root=repo_root,
            )

            if not merge_result.success:
                tracker.error("create", "merge base creation failed")
                console.print(tracker.render())
                console.print(f"\n[red]Error:[/red] Failed to create merge base")
                console.print(f"Reason: {merge_result.error}")

                if merge_result.conflicts:
                    console.print(f"\n[yellow]Conflicts in:[/yellow]")
                    for conflict_file in merge_result.conflicts:
                        console.print(f"  - {conflict_file}")
                    console.print(f"\n[dim]Resolve conflicts manually, then re-run implement[/dim]")

                raise typer.Exit(1)

            # Use merge base branch
            base_branch = merge_result.branch_name

        elif base is None:
            # No dependencies - branch from target branch (or primary if target not set)
            from specify_cli.core.feature_detection import get_feature_target_branch

            # Get target branch from feature metadata
            target_branch = get_feature_target_branch(repo_root, feature_slug)

            # Check if target branch exists
            branch_exists_result = subprocess.run(
                ["git", "rev-parse", "--verify", target_branch],
                cwd=repo_root,
                capture_output=True,
                check=False
            )

            if branch_exists_result.returncode != 0:
                # Target branch doesn't exist
                if target_branch != "main" and target_branch != "master":
                    # Auto-create target branch from primary branch (bootstrap)
                    primary_branch = resolve_primary_branch(repo_root)
                    console.print(f"\n[cyan]Target branch '{target_branch}' doesn't exist - creating from {primary_branch}[/cyan]")

                    create_result = subprocess.run(
                        ["git", "branch", target_branch, primary_branch],
                        cwd=repo_root,
                        capture_output=True,
                        text=True,
                        check=False
                    )

                    if create_result.returncode == 0:
                        # Branch created successfully from primary's current HEAD
                        # This means 3.x now includes all planning commits (feature files exist)
                        console.print(f"[green]✓[/green] Created target branch: {target_branch} from {primary_branch}")
                        base_branch = target_branch
                    else:
                        # Creation failed (conflict, permissions, etc.)
                        console.print(f"[yellow]Warning:[/yellow] Could not create {target_branch}: {create_result.stderr}")
                        console.print(f"[yellow]Falling back to {primary_branch}[/yellow]")
                        base_branch = primary_branch
                else:
                    # Target is main/master but doesn't exist - use primary
                    base_branch = resolve_primary_branch(repo_root)
            else:
                # Target branch exists - use it
                base_branch = target_branch
        else:
            # Has dependencies - branch from base WP's branch
            base_branch = f"{feature_slug}-{base}"

            # Validate base branch/workspace exists
            base_workspace_path = repo_root / ".worktrees" / f"{feature_slug}-{base}"
            base_workspace_info = vcs.get_workspace_info(base_workspace_path)
            if base_workspace_info is None:
                tracker.error("create", f"base workspace {base} not found")
                console.print(tracker.render())
                console.print(f"[red]Error:[/red] Base workspace {base} does not exist")
                console.print(f"Implement {base} first: spec-kitty implement {base}")
                raise typer.Exit(1)

            # Use the base workspace's current branch for git, or the revision for jj
            if vcs_backend == VCSBackend.GIT:
                if base_workspace_info.current_branch:
                    base_branch = base_workspace_info.current_branch
                # For git, verify the branch exists
                result = subprocess.run(
                    ["git", "rev-parse", "--verify", base_branch],
                    cwd=repo_root,
                    capture_output=True,
                    check=False
                )
                if result.returncode != 0:
                    tracker.error("create", f"base branch {base_branch} not found")
                    console.print(tracker.render())
                    console.print(f"[red]Error:[/red] Base branch {base_branch} does not exist")
                    raise typer.Exit(1)

        # Create workspace using VCS abstraction
        # For git: sparse_exclude excludes kitty-specs/ from worktree
        # For jj: no sparse-checkout needed (jj has different isolation model)
        if vcs_backend == VCSBackend.GIT:
            create_result = vcs.create_workspace(
                workspace_path=workspace_path,
                workspace_name=workspace_name,
                base_branch=base_branch,
                repo_root=repo_root,
                sparse_exclude=["kitty-specs/"],
            )
        else:
            # jj workspace creation
            create_result = vcs.create_workspace(
                workspace_path=workspace_path,
                workspace_name=workspace_name,
                base_branch=base_branch,
                repo_root=repo_root,
            )

        if not create_result.success:
            tracker.error("create", "workspace creation failed")
            console.print(tracker.render())
            console.print(f"\n[red]Error:[/red] Failed to create workspace")
            console.print(f"Error: {create_result.error}")
            raise typer.Exit(1)

        # For git, confirm sparse-checkout was applied
        if vcs_backend == VCSBackend.GIT:
            console.print("[cyan]→ Sparse-checkout configured (kitty-specs/ excluded, agents read from main)[/cyan]")

        # Step 3.5: Get base commit SHA for tracking
        result = subprocess.run(
            ["git", "rev-parse", base_branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False
        )
        base_commit_sha = result.stdout.strip() if result.returncode == 0 else "unknown"

        # Step 3.6: Update WP frontmatter with base tracking
        try:
            created_at = datetime.now(timezone.utc).isoformat()

            # Update frontmatter with base tracking fields
            update_fields(wp_file, {
                "base_branch": base_branch,
                "base_commit": base_commit_sha,
                "created_at": created_at,
            })

            console.print(f"[cyan]→ Base tracking: {base_branch} @ {base_commit_sha[:7]}[/cyan]")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not update base tracking in frontmatter: {e}")

        # Step 3.7: Create workspace context file
        try:
            # Note if this was created via multi-parent merge
            created_by = "implement-command"
            if auto_merge_base:
                created_by = "implement-command-multi-parent-merge"

            context = WorkspaceContext(
                wp_id=wp_id,
                feature_slug=feature_slug,
                worktree_path=str(workspace_path.relative_to(repo_root)),
                branch_name=branch_name,
                base_branch=base_branch,
                base_commit=base_commit_sha,
                dependencies=declared_deps,
                created_at=created_at,
                created_by=created_by,
                vcs_backend=vcs_backend.value,
            )

            context_path = save_context(repo_root, context)
            console.print(f"[cyan]→ Workspace context: {context_path.relative_to(repo_root)}[/cyan]")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not create workspace context: {e}")

        tracker.complete("create", f"Workspace: {workspace_path.relative_to(repo_root)}")

    except typer.Exit:
        console.print(tracker.render())
        raise

    # Step 4: Update WP lane to "doing" and auto-commit to main
    # This enables multi-agent synchronization - all agents see the claim immediately
    try:
        import os

        wp = locate_work_package(repo_root, feature_slug, wp_id)

        # Only update if currently planned (avoid overwriting existing doing/review state)
        current_lane = wp.lane or "planned"
        if current_lane == "planned":
            # Capture current shell PID for audit trail
            shell_pid = str(os.getppid())

            # Update lane and shell_pid in frontmatter
            updated_front = set_scalar(wp.frontmatter, "lane", "doing")
            updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

            # Build and write updated document
            updated_doc = build_document(updated_front, wp.body, wp.padding)
            wp.path.write_text(updated_doc, encoding="utf-8")

            # Auto-commit to target branch (respects two-branch strategy)
            commit_msg = f"chore: {wp_id} claimed for implementation"
            commit_result = subprocess.run(
                ["git", "commit", str(wp.path.resolve()), "-m", commit_msg],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False
            )

            if commit_result.returncode == 0:
                # Get target branch for accurate console message
                from specify_cli.core.feature_detection import get_feature_target_branch
                target_branch = get_feature_target_branch(repo_root, feature_slug)
                console.print(f"[cyan]→ {wp_id} moved to 'doing' (committed to {target_branch})[/cyan]")
            else:
                # Commit failed - file might be unchanged or other issue
                console.print(f"[yellow]Warning:[/yellow] Could not auto-commit lane change")
                if commit_result.stderr:
                    console.print(f"  {commit_result.stderr.strip()}")

    except Exception as e:
        # Non-fatal: workspace created but lane update failed
        console.print(f"[yellow]Warning:[/yellow] Could not update WP status: {e}")

    # Success
    if json_output:
        # JSON output for scripting
        import json
        print(json.dumps({
            "workspace_path": str(workspace_path.relative_to(repo_root)),
            "branch": branch_name,
            "feature": feature_slug,
            "wp_id": wp_id,
            "base": base or "main",
            "status": "created"
        }))
    else:
        # Human-readable output
        console.print(tracker.render())
        console.print(f"\n[bold green]✓ Workspace created successfully[/bold green]")

        # Check for dependent WPs after creation (T079)
        check_for_dependents(repo_root, feature_slug, wp_id)

        # CRITICAL: Explicit cd instruction to prevent writing to main
        console.print()
        console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
        console.print("[bold yellow]CRITICAL: Change to workspace directory before making any changes![/bold yellow]")
        console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
        console.print()
        console.print(f"  [bold]cd {workspace_path}[/bold]")
        console.print()
        console.print("[dim]All file edits, writes, and commits MUST happen in this directory.[/dim]")
        console.print("[dim]Writing to main repository instead of the workspace is a critical error.[/dim]")


__all__ = ["implement"]
