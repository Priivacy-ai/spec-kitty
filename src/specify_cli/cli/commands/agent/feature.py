"""Feature lifecycle commands for AI agents."""

from __future__ import annotations

import json
import os
import re
import shutil
from importlib.resources import files
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.core.paths import locate_project_root, is_worktree_context
from specify_cli.core.worktree import (
    get_next_feature_number,
    validate_feature_structure,
    setup_feature_directory,
)
from specify_cli.core.git_ops import run_command, is_git_repo, get_current_branch
from specify_cli.core.dependency_graph import (
    parse_wp_dependencies,
    detect_cycles,
    validate_dependencies,
)
from specify_cli.frontmatter import read_frontmatter, write_frontmatter

app = typer.Typer(
    name="feature",
    help="Feature lifecycle commands for AI agents",
    no_args_is_help=True
)

console = Console()


def _commit_to_main(
    file_path: Path,
    feature_slug: str,
    artifact_type: str,
    repo_root: Path,
    json_output: bool = False
) -> None:
    """Commit planning artifact to main branch.

    Args:
        file_path: Path to file being committed
        feature_slug: Feature slug (e.g., "001-my-feature")
        artifact_type: Type of artifact ("spec", "plan", "tasks")
        repo_root: Repository root path (ensures commits go to main repo, not worktree)
        json_output: If True, suppress Rich console output

    Raises:
        subprocess.CalledProcessError: If commit fails unexpectedly
        typer.Exit: If not on main/master branch
    """
    try:
        # Verify we're on main branch (check from repo root)
        current_branch = get_current_branch(repo_root)
        if current_branch not in ["main", "master"]:
            error_msg = f"Planning artifacts must be committed to main branch (currently on: {current_branch})"
            if not json_output:
                console.print(f"[red]Error:[/red] {error_msg}")
                console.print("[yellow]Switch to main branch:[/yellow] cd {repo_root} && git checkout main")
            raise RuntimeError(error_msg)

        # Add file to staging (run from repo root to ensure main repo, not worktree)
        run_command(["git", "add", str(file_path)], check_return=True, capture=True, cwd=repo_root)

        # Commit with descriptive message
        commit_msg = f"Add {artifact_type} for feature {feature_slug}"
        run_command(
            ["git", "commit", "-m", commit_msg],
            check_return=True,
            capture=True,
            cwd=repo_root
        )

        if not json_output:
            console.print(f"[green]✓[/green] {artifact_type.capitalize()} committed to main")

    except subprocess.CalledProcessError as e:
        # Check if it's just "nothing to commit" (benign)
        stderr = e.stderr if hasattr(e, 'stderr') and e.stderr else ""
        if "nothing to commit" in stderr or "nothing added to commit" in stderr:
            # Benign - file unchanged
            if not json_output:
                console.print(f"[dim]{artifact_type.capitalize()} unchanged, no commit needed[/dim]")
        else:
            # Actual error
            if not json_output:
                console.print(f"[yellow]Warning:[/yellow] Failed to commit {artifact_type}: {e}")
                console.print(f"[yellow]You may need to commit manually:[/yellow] git add {file_path} && git commit")
            raise


def _find_feature_directory(repo_root: Path, cwd: Path) -> Path:
    """Find the current feature directory.

    Handles three contexts:
    1. Worktree root (cwd contains kitty-specs/)
    2. Inside feature directory (walk up to find kitty-specs/)
    3. Main repo (find latest feature in kitty-specs/)

    Args:
        repo_root: Repository root path
        cwd: Current working directory

    Returns:
        Path to feature directory

    Raises:
        ValueError: If feature directory cannot be determined
    """
    # Check if we're in a worktree
    if is_worktree_context(cwd):
        # Get the current git branch name to match feature directory
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            branch_name = result.stdout.strip()
        except subprocess.CalledProcessError:
            branch_name = None

        # Strategy 1: Check if cwd contains kitty-specs/ (we're at worktree root)
        kitty_specs_candidate = cwd / "kitty-specs"
        if kitty_specs_candidate.exists() and kitty_specs_candidate.is_dir():
            kitty_specs = kitty_specs_candidate
        else:
            # Strategy 2: Walk up to find kitty-specs directory
            kitty_specs = cwd
            while kitty_specs != kitty_specs.parent:
                if kitty_specs.name == "kitty-specs":
                    break
                kitty_specs = kitty_specs.parent

            if kitty_specs.name != "kitty-specs":
                raise ValueError("Could not locate kitty-specs directory in worktree")

        # Find the ###-* feature directory that matches the branch name
        if branch_name:
            # First try exact match with branch name
            branch_feature_dir = kitty_specs / branch_name
            if branch_feature_dir.exists() and branch_feature_dir.is_dir():
                return branch_feature_dir

        # Fallback: Find any ###-* feature directory (for older worktrees)
        for item in kitty_specs.iterdir():
            if item.is_dir() and len(item.name) >= 3 and item.name[:3].isdigit():
                return item

        raise ValueError("Could not find feature directory in worktree")
    else:
        # We're in main repo - find latest feature
        specs_dir = repo_root / "kitty-specs"
        if not specs_dir.exists():
            raise ValueError("No kitty-specs directory found in repository")

        # Find the highest numbered feature
        max_num = 0
        feature_dir = None
        for item in specs_dir.iterdir():
            if item.is_dir() and len(item.name) >= 3 and item.name[:3].isdigit():
                try:
                    num = int(item.name[:3])
                    if num > max_num:
                        max_num = num
                        feature_dir = item
                except ValueError:
                    continue

        if feature_dir is None:
            raise ValueError("No feature directories found in kitty-specs/")

        return feature_dir


@app.command(name="create-feature")
def create_feature(
    feature_slug: Annotated[str, typer.Argument(help="Feature slug (e.g., 'user-auth')")],
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Create new feature directory structure in main repository.

    This command is designed for AI agents to call programmatically.
    Creates feature directory in kitty-specs/ and commits to main branch.

    Examples:
        spec-kitty agent create-feature "new-dashboard" --json
    """
    try:
        # GUARD: Refuse to run from inside a worktree (must be on main branch in main repo)
        cwd = Path.cwd().resolve()
        if is_worktree_context(cwd):
            error_msg = "Cannot create features from inside a worktree. Must be on main branch in main repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[bold red]Error:[/bold red] {error_msg}")
                # Find and suggest the main repo path
                for i, part in enumerate(cwd.parts):
                    if part == ".worktrees":
                        main_repo = Path(*cwd.parts[:i])
                        console.print(f"\n[cyan]Run from the main repository instead:[/cyan]")
                        console.print(f"  cd {main_repo}")
                        console.print(f"  spec-kitty agent create-feature {feature_slug}")
                        break
            raise typer.Exit(1)

        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Verify we're in a git repository
        if not is_git_repo(repo_root):
            error_msg = "Not in a git repository. Feature creation requires git."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Verify we're on main branch (or acceptable branch)
        current_branch = get_current_branch(repo_root)
        if current_branch not in ["main", "master"]:
            error_msg = f"Must be on main branch to create features (currently on: {current_branch})"
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Get next feature number
        feature_number = get_next_feature_number(repo_root)
        feature_slug_formatted = f"{feature_number:03d}-{feature_slug}"

        # Create feature directory in main repo
        feature_dir = repo_root / "kitty-specs" / feature_slug_formatted
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (feature_dir / "checklists").mkdir(exist_ok=True)
        (feature_dir / "research").mkdir(exist_ok=True)
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        # Create tasks/.gitkeep and README.md
        (tasks_dir / ".gitkeep").touch()

        # Create tasks/README.md (using same content from setup_feature_directory)
        tasks_readme_content = '''# Tasks Directory

This directory contains work package (WP) prompt files with lane status in frontmatter.

## Directory Structure (v0.9.0+)

```
tasks/
├── WP01-setup-infrastructure.md
├── WP02-user-authentication.md
├── WP03-api-endpoints.md
└── README.md
```

All WP files are stored flat in `tasks/`. The lane (planned, doing, for_review, done) is stored in the YAML frontmatter `lane:` field.

## Work Package File Format

Each WP file **MUST** use YAML frontmatter:

```yaml
---
work_package_id: "WP01"
title: "Work Package Title"
lane: "planned"
subtasks:
  - "T001"
  - "T002"
phase: "Phase 1 - Setup"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-01-01T00:00:00Z"
    lane: "planned"
    agent: "system"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Work Package Title

[Content follows...]
```

## Valid Lane Values

- `planned` - Ready for implementation
- `doing` - Currently being worked on
- `for_review` - Awaiting review
- `done` - Completed

## Moving Between Lanes

Use the CLI (updates frontmatter only, no file movement):
```bash
spec-kitty agent tasks move-task <WPID> --to <lane>
```

Example:
```bash
spec-kitty agent tasks move-task WP01 --to doing
```

## File Naming

- Format: `WP01-kebab-case-slug.md`
- Examples: `WP01-setup-infrastructure.md`, `WP02-user-auth.md`
'''
        (tasks_dir / "README.md").write_text(tasks_readme_content)

        # Copy spec template if it exists
        spec_file = feature_dir / "spec.md"
        if not spec_file.exists():
            spec_template_candidates = [
                repo_root / ".kittify" / "templates" / "spec-template.md",
                repo_root / "templates" / "spec-template.md",
            ]

            for template in spec_template_candidates:
                if template.exists():
                    shutil.copy2(template, spec_file)
                    break
            else:
                # No template found, create empty spec.md
                spec_file.touch()

        # Commit spec.md to main
        _commit_to_main(spec_file, feature_slug_formatted, "spec", repo_root, json_output)

        if json_output:
            print(json.dumps({
                "result": "success",
                "feature": feature_slug_formatted,
                "feature_dir": str(feature_dir)
            }))
        else:
            console.print(f"[green]✓[/green] Feature created: {feature_slug_formatted}")
            console.print(f"   Directory: {feature_dir}")
            console.print(f"   Spec committed to main")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="check-prerequisites")
def check_prerequisites(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    paths_only: Annotated[bool, typer.Option("--paths-only", help="Only output path variables")] = False,
    include_tasks: Annotated[bool, typer.Option("--include-tasks", help="Include tasks.md in validation")] = False,
) -> None:
    """Validate feature structure and prerequisites.

    This command is designed for AI agents to call programmatically.

    Examples:
        spec-kitty agent check-prerequisites --json
        spec-kitty agent check-prerequisites --paths-only --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Determine feature directory (main repo or worktree)
        cwd = Path.cwd().resolve()
        feature_dir = _find_feature_directory(repo_root, cwd)

        validation_result = validate_feature_structure(feature_dir, check_tasks=include_tasks)

        if json_output:
            if paths_only:
                print(json.dumps(validation_result["paths"]))
            else:
                print(json.dumps(validation_result))
        else:
            if validation_result["valid"]:
                console.print("[green]✓[/green] Prerequisites check passed")
                console.print(f"   Feature: {feature_dir.name}")
            else:
                console.print("[red]✗[/red] Prerequisites check failed")
                for error in validation_result["errors"]:
                    console.print(f"   • {error}")

            if validation_result["warnings"]:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in validation_result["warnings"]:
                    console.print(f"   • {warning}")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="setup-plan")
def setup_plan(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Scaffold implementation plan template in main repository.

    This command is designed for AI agents to call programmatically.
    Creates plan.md and commits to main branch.

    Examples:
        spec-kitty agent setup-plan --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Determine feature directory (main repo or worktree)
        cwd = Path.cwd().resolve()
        feature_dir = _find_feature_directory(repo_root, cwd)

        plan_file = feature_dir / "plan.md"

        # Find plan template
        plan_template_candidates = [
            repo_root / ".kittify" / "templates" / "plan-template.md",
            repo_root / "src" / "specify_cli" / "templates" / "plan-template.md",
            repo_root / "templates" / "plan-template.md",
        ]

        plan_template = None
        for candidate in plan_template_candidates:
            if candidate.exists():
                plan_template = candidate
                break

        if plan_template is not None:
            shutil.copy2(plan_template, plan_file)
        else:
            package_template = files("specify_cli").joinpath("templates", "plan-template.md")
            if not package_template.exists():
                raise FileNotFoundError("Plan template not found in repository or package")
            with package_template.open("rb") as src, open(plan_file, "wb") as dst:
                shutil.copyfileobj(src, dst)

        # Commit plan.md to main
        feature_slug = feature_dir.name
        _commit_to_main(plan_file, feature_slug, "plan", repo_root, json_output)

        if json_output:
            print(json.dumps({
                "result": "success",
                "plan_file": str(plan_file),
                "feature_dir": str(feature_dir)
            }))
        else:
            console.print(f"[green]✓[/green] Plan scaffolded: {plan_file}")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

def _find_latest_feature_worktree(repo_root: Path) -> Optional[Path]:
    """Find the latest feature worktree by number.

    Migrated from find_latest_feature_worktree() in common.sh

    Args:
        repo_root: Repository root directory

    Returns:
        Path to latest worktree, or None if no worktrees exist
    """
    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.exists():
        return None

    latest_num = 0
    latest_worktree = None

    for worktree_dir in worktrees_dir.iterdir():
        if not worktree_dir.is_dir():
            continue

        # Match pattern: 001-feature-name
        match = re.match(r"^(\d{3})-", worktree_dir.name)
        if match:
            num = int(match.group(1))
            if num > latest_num:
                latest_num = num
                latest_worktree = worktree_dir

    return latest_worktree


def _get_current_branch(repo_root: Path) -> str:
    """Get current git branch name.

    Args:
        repo_root: Repository root directory

    Returns:
        Current branch name, or 'main' if not in a git repo
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "main"


@app.command(name="accept")
def accept_feature(
    feature: Annotated[
        Optional[str],
        typer.Option(
            "--feature",
            help="Feature directory slug (auto-detected if not specified)"
        )
    ] = None,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Acceptance mode: auto, pr, local, checklist"
        )
    ] = "auto",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON for agent parsing"
        )
    ] = False,
    lenient: Annotated[
        bool,
        typer.Option(
            "--lenient",
            help="Skip strict metadata validation"
        )
    ] = False,
    no_commit: Annotated[
        bool,
        typer.Option(
            "--no-commit",
            help="Skip auto-commit (report only)"
        )
    ] = False,
) -> None:
    """Perform feature acceptance workflow.

    This command:
    1. Validates all tasks are in 'done' lane
    2. Runs acceptance checks from checklist files
    3. Creates acceptance report
    4. Marks feature as ready for merge

    Delegates to existing tasks_cli.py accept implementation.

    Examples:
        # Run acceptance workflow
        spec-kitty agent feature accept

        # With JSON output for agents
        spec-kitty agent feature accept --json

        # Lenient mode (skip strict validation)
        spec-kitty agent feature accept --lenient --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error = "Could not locate project root"
            if json_output:
                print(json.dumps({"error": error, "success": False}))
            else:
                console.print(f"[red]Error:[/red] {error}")
            sys.exit(1)

        # Build command to call tasks_cli.py
        tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
        if not tasks_cli.exists():
            error = f"tasks_cli.py not found: {tasks_cli}"
            if json_output:
                print(json.dumps({"error": error, "success": False}))
            else:
                console.print(f"[red]Error:[/red] {error}")
            sys.exit(1)

        cmd = ["python3", str(tasks_cli), "accept"]
        if feature:
            cmd.extend(["--feature", feature])
        cmd.extend(["--mode", mode])
        if json_output:
            cmd.append("--json")
        if lenient:
            cmd.append("--lenient")
        if no_commit:
            cmd.append("--no-commit")

        # Execute accept command
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        # Pass through output
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr and not json_output:
            print(result.stderr, end="", file=sys.stderr)

        sys.exit(result.returncode)

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e), "success": False}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command(name="merge")
def merge_feature(
    feature: Annotated[
        Optional[str],
        typer.Option(
            "--feature",
            help="Feature directory slug (auto-detected if not specified)"
        )
    ] = None,
    target: Annotated[
        str,
        typer.Option(
            "--target",
            help="Target branch to merge into"
        )
    ] = "main",
    strategy: Annotated[
        str,
        typer.Option(
            "--strategy",
            help="Merge strategy: merge, squash, rebase"
        )
    ] = "merge",
    push: Annotated[
        bool,
        typer.Option(
            "--push",
            help="Push to origin after merging"
        )
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show actions without executing"
        )
    ] = False,
    keep_branch: Annotated[
        bool,
        typer.Option(
            "--keep-branch",
            help="Keep feature branch after merge (default: delete)"
        )
    ] = False,
    keep_worktree: Annotated[
        bool,
        typer.Option(
            "--keep-worktree",
            help="Keep worktree after merge (default: remove)"
        )
    ] = False,
    auto_retry: Annotated[
        bool,
        typer.Option(
            "--auto-retry/--no-auto-retry",
            help="Auto-navigate to latest worktree if in wrong location"
        )
    ] = True,
) -> None:
    """Merge feature branch into target branch.

    This command:
    1. Validates feature is accepted
    2. Merges feature branch into target (usually 'main')
    3. Cleans up worktree
    4. Deletes feature branch

    Auto-retry logic (from merge-feature.sh):
    If current branch doesn't match feature pattern (XXX-name) and auto-retry is enabled,
    automatically finds and navigates to latest worktree.

    Delegates to existing tasks_cli.py merge implementation.

    Examples:
        # Merge into main branch
        spec-kitty agent feature merge

        # Merge into specific branch with push
        spec-kitty agent feature merge --target develop --push

        # Dry-run mode
        spec-kitty agent feature merge --dry-run

        # Keep worktree and branch after merge
        spec-kitty agent feature merge --keep-worktree --keep-branch
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error = "Could not locate project root"
            print(json.dumps({"error": error, "success": False}))
            sys.exit(1)

        # Auto-retry logic: Check if we're on a feature branch
        if auto_retry and not os.environ.get("SPEC_KITTY_AUTORETRY"):
            current_branch = _get_current_branch(repo_root)
            is_feature_branch = re.match(r"^\d{3}-", current_branch)

            if not is_feature_branch:
                # Try to find latest worktree and retry there
                latest_worktree = _find_latest_feature_worktree(repo_root)
                if latest_worktree:
                    console.print(
                        f"[yellow]Auto-retry:[/yellow] Not on feature branch ({current_branch}). "
                        f"Running merge in {latest_worktree.name}"
                    )

                    # Set env var to prevent infinite recursion
                    env = os.environ.copy()
                    env["SPEC_KITTY_AUTORETRY"] = "1"

                    # Re-run command in worktree
                    retry_cmd = ["spec-kitty", "agent", "feature", "merge"]
                    if feature:
                        retry_cmd.extend(["--feature", feature])
                    retry_cmd.extend(["--target", target, "--strategy", strategy])
                    if push:
                        retry_cmd.append("--push")
                    if dry_run:
                        retry_cmd.append("--dry-run")
                    if keep_branch:
                        retry_cmd.append("--keep-branch")
                    if keep_worktree:
                        retry_cmd.append("--keep-worktree")
                    retry_cmd.append("--no-auto-retry")

                    result = subprocess.run(
                        retry_cmd,
                        cwd=latest_worktree,
                        env=env,
                    )
                    sys.exit(result.returncode)

        # Build command to call tasks_cli.py
        tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
        if not tasks_cli.exists():
            error = f"tasks_cli.py not found: {tasks_cli}"
            print(json.dumps({"error": error, "success": False}))
            sys.exit(1)

        cmd = ["python3", str(tasks_cli), "merge"]
        if feature:
            cmd.extend(["--feature", feature])
        cmd.extend(["--target", target, "--strategy", strategy])
        if push:
            cmd.append("--push")
        if dry_run:
            cmd.append("--dry-run")
        if keep_branch:
            cmd.append("--keep-branch")
        else:
            cmd.append("--delete-branch")
        if keep_worktree:
            cmd.append("--keep-worktree")
        else:
            cmd.append("--remove-worktree")

        # Execute merge command
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        # Pass through output
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        sys.exit(result.returncode)

    except Exception as e:
        print(json.dumps({"error": str(e), "success": False}))
        sys.exit(1)


@app.command(name="finalize-tasks")
def finalize_tasks(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Parse dependencies from tasks.md and update WP frontmatter, then commit to main.

    This command is designed to be called after LLM generates WP files via /spec-kitty.tasks.
    It post-processes the generated files to add dependency information and commits everything.

    Examples:
        spec-kitty agent feature finalize-tasks --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root"
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Determine feature directory
        cwd = Path.cwd().resolve()
        feature_dir = _find_feature_directory(repo_root, cwd)

        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.exists():
            error_msg = f"Tasks directory not found: {tasks_dir}"
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Parse dependencies from tasks.md (if it exists)
        tasks_md = feature_dir / "tasks.md"
        wp_dependencies = {}
        if tasks_md.exists():
            # Read tasks.md and parse dependencies
            tasks_content = tasks_md.read_text(encoding="utf-8")
            wp_dependencies = _parse_dependencies_from_tasks_md(tasks_content)

        # Validate dependencies (detect cycles, invalid references)
        if wp_dependencies:
            # Check for circular dependencies
            cycles = detect_cycles(wp_dependencies)
            if cycles:
                error_msg = f"Circular dependencies detected: {cycles}"
                if json_output:
                    print(json.dumps({"error": error_msg, "cycles": cycles}))
                else:
                    console.print(f"[red]Error:[/red] Circular dependencies detected:")
                    for cycle in cycles:
                        console.print(f"  {' → '.join(cycle)}")
                raise typer.Exit(1)

            # Validate each WP's dependencies
            for wp_id, deps in wp_dependencies.items():
                is_valid, errors = validate_dependencies(wp_id, deps, wp_dependencies)
                if not is_valid:
                    error_msg = f"Invalid dependencies for {wp_id}: {errors}"
                    if json_output:
                        print(json.dumps({"error": error_msg, "wp_id": wp_id, "errors": errors}))
                    else:
                        console.print(f"[red]Error:[/red] Invalid dependencies for {wp_id}:")
                        for err in errors:
                            console.print(f"  - {err}")
                    raise typer.Exit(1)

        # Update each WP file's frontmatter with dependencies
        wp_files = list(tasks_dir.glob("WP*.md"))
        updated_count = 0

        for wp_file in wp_files:
            # Extract WP ID from filename
            wp_id_match = re.match(r"(WP\d{2})", wp_file.name)
            if not wp_id_match:
                continue

            wp_id = wp_id_match.group(1)

            # Detect whether dependencies field exists in raw frontmatter
            raw_content = wp_file.read_text(encoding="utf-8")
            has_dependencies_line = False
            if raw_content.startswith("---"):
                parts = raw_content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_text = parts[1]
                    has_dependencies_line = re.search(
                        r"^\s*dependencies\s*:", frontmatter_text, re.MULTILINE
                    ) is not None

            # Read current frontmatter
            try:
                frontmatter, body = read_frontmatter(wp_file)
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Could not read {wp_file.name}: {e}")
                continue

            # Get dependencies for this WP (default to empty list)
            deps = wp_dependencies.get(wp_id, [])

            # Update frontmatter with dependencies
            if not has_dependencies_line or frontmatter.get("dependencies") != deps:
                frontmatter["dependencies"] = deps

                # Write updated frontmatter
                write_frontmatter(wp_file, frontmatter, body)
                updated_count += 1

        # Commit tasks.md and WP files to main
        feature_slug = feature_dir.name
        try:
            # Add tasks.md (if present) and all WP files
            if tasks_md.exists():
                run_command(
                    ["git", "add", str(tasks_md)],
                    check_return=True,
                    capture=True,
                    cwd=repo_root
                )
            run_command(
                ["git", "add", str(tasks_dir)],
                check_return=True,
                capture=True,
                cwd=repo_root
            )

            # Commit with descriptive message
            commit_msg = f"Add tasks for feature {feature_slug}"
            run_command(
                ["git", "commit", "-m", commit_msg],
                check_return=True,
                capture=True,
                cwd=repo_root
            )

            if not json_output:
                console.print(f"[green]✓[/green] Tasks committed to main")
                console.print(f"[dim]Updated {updated_count} WP files with dependencies[/dim]")

        except subprocess.CalledProcessError as e:
            # Check if it's just "nothing to commit"
            stderr = e.stderr if hasattr(e, 'stderr') and e.stderr else ""
            if "nothing to commit" in stderr or "nothing added to commit" in stderr:
                if not json_output:
                    console.print(f"[dim]Tasks unchanged, no commit needed[/dim]")
            else:
                raise

        if json_output:
            print(json.dumps({
                "result": "success",
                "updated_wp_count": updated_count,
                "tasks_dir": str(tasks_dir)
            }))

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _parse_dependencies_from_tasks_md(tasks_content: str) -> dict[str, list[str]]:
    """Parse WP dependencies from tasks.md content.

    Parsing strategy (priority order):
    1. Explicit dependency markers ("Depends on WP01", "Dependencies: WP01, WP02")
    2. Phase grouping (Phase 2 WPs depend on Phase 1 WPs)
    3. Default to empty list if ambiguous

    Returns:
        Dict mapping WP ID to list of dependencies
        Example: {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01", "WP02"]}
    """
    dependencies = {}

    # Split into WP sections
    wp_sections = re.split(r'##\s+Work Package (WP\d{2})', tasks_content)

    # Process sections (they come in pairs: WP ID, then content)
    for i in range(1, len(wp_sections), 2):
        if i + 1 >= len(wp_sections):
            break

        wp_id = wp_sections[i]
        section_content = wp_sections[i + 1]

        # Method 1: Explicit "Depends on" or "Dependencies:"
        explicit_deps = []

        # Pattern: "Depends on WP01" or "Depends on WP01, WP02"
        depends_matches = re.findall(r'Depends?\s+on\s+(WP\d{2}(?:\s*,\s*WP\d{2})*)', section_content, re.IGNORECASE)
        for match in depends_matches:
            explicit_deps.extend(re.findall(r'WP\d{2}', match))

        # Pattern: "Dependencies: WP01, WP02"
        deps_line = re.search(r'Dependencies:\s*(.+)', section_content)
        if deps_line:
            explicit_deps.extend(re.findall(r'WP\d{2}', deps_line.group(1)))

        if explicit_deps:
            # Remove duplicates and sort
            dependencies[wp_id] = sorted(list(set(explicit_deps)))
        else:
            # Default to empty
            dependencies[wp_id] = []

    return dependencies
