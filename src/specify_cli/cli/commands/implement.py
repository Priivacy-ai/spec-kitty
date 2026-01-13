"""Implement command - create workspace for work package implementation."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from specify_cli.cli import StepTracker
from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    get_dependents,
    parse_wp_dependencies,
)
from specify_cli.frontmatter import read_frontmatter
from specify_cli.tasks_support import TaskCliError, find_repo_root

console = Console()


def detect_feature_context(feature_flag: str | None = None) -> tuple[str, str]:
    """Detect feature number and slug from current context.

    Args:
        feature_flag: Explicit feature slug from --feature flag (optional)

    Returns:
        Tuple of (feature_number, feature_slug)
        Example: ("010", "010-workspace-per-wp")

    Raises:
        typer.Exit: If feature context cannot be detected
    """
    # Priority 1: Explicit --feature flag
    if feature_flag:
        match = re.match(r'^(\d{3})-(.+)$', feature_flag)
        if match:
            number = match.group(1)
            return number, feature_flag
        else:
            console.print(f"[red]Error:[/red] Invalid feature format: {feature_flag}")
            console.print("Expected format: ###-feature-name (e.g., 001-my-feature)")
            raise typer.Exit(1)

    # Priority 2: Try git branch
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode == 0:
        branch = result.stdout.strip()

        # Pattern 1: WP branch (###-feature-name-WP##)
        # Check this FIRST - more specific pattern
        # Extract feature slug by removing -WP## suffix
        match = re.match(r'^((\d{3})-.+)-WP\d{2}$', branch)
        if match:
            slug = match.group(1)
            number = match.group(2)
            return number, slug

        # Pattern 2: Feature branch (###-feature-name)
        match = re.match(r'^(\d{3})-(.+)$', branch)
        if match:
            number = match.group(1)
            slug = branch
            return number, slug

    # Try current directory
    cwd = Path.cwd()
    # Look for kitty-specs/###-feature-name/ in path
    for part in cwd.parts:
        match = re.match(r'^(\d{3})-(.+)$', part)
        if match:
            number = match.group(1)
            slug = part
            return number, slug

    # Try scanning kitty-specs/ for features (v0.11.0 workflow)
    try:
        repo_root = find_repo_root()
        kitty_specs = repo_root / "kitty-specs"
        if kitty_specs.exists():
            # Find all feature directories
            features = [
                d.name for d in kitty_specs.iterdir()
                if d.is_dir() and re.match(r'^\d{3}-', d.name)
            ]

            if len(features) == 1:
                # Only one feature - use it automatically
                match = re.match(r'^(\d{3})-(.+)$', features[0])
                if match:
                    number = match.group(1)
                    slug = features[0]
                    return number, slug
            elif len(features) > 1:
                # Multiple features - fall back to latest feature by number
                def _feature_num(name: str) -> int:
                    try:
                        return int(name.split("-", 1)[0])
                    except (ValueError, IndexError):
                        return -1
                latest = max(features, key=_feature_num)
                match = re.match(r'^(\d{3})-(.+)$', latest)
                if match:
                    number = match.group(1)
                    slug = latest
                    return number, slug
    except TaskCliError:
        # Not in a git repo, continue to generic error
        pass

    # Cannot detect
    console.print("[red]Error:[/red] Cannot detect feature context")
    console.print("Run this command from a feature branch or feature directory")
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
    """Check if any WPs depend on this WP and warn if in progress.

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

    # Check if any dependents are in progress (lane: doing)
    in_progress_deps = []
    for dep_id in dependents:
        try:
            dep_file = find_wp_file(repo_root, feature_slug, dep_id)
            frontmatter, _ = read_frontmatter(dep_file)
            lane = frontmatter.get("lane", "planned")

            if lane == "doing":
                in_progress_deps.append(dep_id)
        except (FileNotFoundError, Exception):
            # If we can't read the dependent's metadata, skip it
            continue

    if in_progress_deps:
        console.print(f"\n[yellow]⚠️  Dependency Alert:[/yellow]")
        console.print(f"{', '.join(in_progress_deps)} depend on {wp_id}")
        console.print("If you modify this WP, dependent WPs will need manual rebase:")
        for dep_id in in_progress_deps:
            dep_workspace = f".worktrees/{feature_slug}-{dep_id}"
            console.print(f"  cd {dep_workspace} && git rebase {feature_slug}-{wp_id}")
        console.print()


def implement(
    wp_id: str = typer.Argument(..., help="Work package ID (e.g., WP01)"),
    base: str = typer.Option(None, "--base", help="Base WP to branch from (e.g., WP01)"),
    feature: str = typer.Option(None, "--feature", help="Feature slug (e.g., 001-my-feature)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
) -> None:
    """Create workspace for work package implementation.

    Creates a git worktree for the specified work package, branching from
    main (for WPs with no dependencies) or from a base WP's branch.

    Examples:
        # Create workspace for WP01 (no dependencies)
        spec-kitty implement WP01

        # Create workspace for WP02, branching from WP01
        spec-kitty implement WP02 --base WP01

        # Explicit feature specification
        spec-kitty implement WP01 --feature 001-my-feature

        # JSON output for scripting
        spec-kitty implement WP01 --json
    """
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
    try:
        # Find WP file to read dependencies
        wp_file = find_wp_file(repo_root, feature_slug, wp_id)
        declared_deps = parse_wp_dependencies(wp_file)

        # Check if WP has dependencies but --base not provided
        if declared_deps and base is None:
            tracker.error("validate", "missing --base flag")
            console.print(tracker.render())
            console.print(f"\n[red]Error:[/red] {wp_id} has dependencies: {declared_deps}")
            console.print(f"Use: spec-kitty implement {wp_id} --base {declared_deps[0]}")
            raise typer.Exit(1)

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
            primary_branch = resolve_primary_branch(repo_root)

            # Check current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False
            )
            current_branch = result.stdout.strip() if result.returncode == 0 else ""

            # Find planning artifacts for this feature
            feature_dir = repo_root / "kitty-specs" / feature_slug
            if not feature_dir.exists():
                console.print(f"\n[red]Error:[/red] Feature directory not found: {feature_dir}")
                console.print(f"Run /spec-kitty.specify first")
                raise typer.Exit(1)

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
                            status = line[:2]
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
                    result = subprocess.run(
                        ["git", "add", str(feature_dir)],
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

        # Check if workspace already exists
        if validate_workspace_path(workspace_path, wp_id):
            # Workspace exists and is valid, reuse it
            tracker.complete("create", f"Reused: {workspace_path}")
            console.print(tracker.render())

            # Check if base branch has changed since workspace was created (T080)
            if base:
                base_branch = f"{feature_slug}-{base}"
                if check_base_branch_changed(workspace_path, base_branch):
                    display_rebase_warning(workspace_path, wp_id, base_branch, feature_slug)

            # Check for dependent WPs (T079)
            check_for_dependents(repo_root, feature_slug, wp_id)

            return

        # Determine base branch
        if base is None:
            # No dependencies - branch from primary branch
            base_branch = resolve_primary_branch(repo_root)
            cmd = [
                "git",
                "worktree",
                "add",
                str(workspace_path),
                "-b",
                branch_name,
                base_branch,
            ]
        else:
            # Has dependencies - branch from base WP's branch
            base_branch = f"{feature_slug}-{base}"

            # Validate base branch exists in git
            result = subprocess.run(
                ["git", "rev-parse", "--verify", base_branch],
                capture_output=True,
                check=False
            )
            if result.returncode != 0:
                tracker.error("create", f"base branch {base_branch} not found")
                console.print(tracker.render())
                console.print(f"[red]Error:[/red] Base branch {base_branch} does not exist")
                raise typer.Exit(1)

            cmd = ["git", "worktree", "add", str(workspace_path), "-b", branch_name, base_branch]

        # Execute git command
        result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            tracker.error("create", "git worktree creation failed")
            console.print(tracker.render())
            console.print(f"\n[red]Error:[/red] Git worktree creation failed")
            console.print(f"Command: {' '.join(cmd)}")
            console.print(f"Error: {result.stderr}")
            raise typer.Exit(1)

        tracker.complete("create", f"Workspace: {workspace_path.relative_to(repo_root)}")

    except typer.Exit:
        console.print(tracker.render())
        raise

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

        console.print(f"\nTo start working:")
        console.print(f"  cd {workspace_path}")
        console.print(f"  git status")


__all__ = ["implement"]
