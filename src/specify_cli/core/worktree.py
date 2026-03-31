"""Worktree management utilities for spec-kitty feature development.

This module provides functions for creating and managing workspaces (git worktrees)
for parallel feature development. Uses the VCS abstraction layer.

All functions are location-aware and work correctly whether called from main
repository or existing worktree/workspace.

Workspace routing by execution_mode (WP04):
- ``code_change`` WPs  → standard git worktree (full checkout, no sparse exclusions)
- ``planning_artifact`` WPs → in-repo workspace (``repo_root`` returned directly)
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import warnings
from pathlib import Path

from .constants import KITTIFY_DIR, KITTY_SPECS_DIR, WORKTREES_DIR
from .vcs import get_vcs
from specify_cli.ownership.models import ExecutionMode
from specify_cli.ownership.workspace_strategy import create_planning_workspace


def _exclude_from_git(worktree_path: Path, patterns: list[str]) -> None:
    """Add patterns to worktree's .git/info/exclude to prevent committing.

    This prevents symlinks created in worktrees from being committed and
    overwriting real files in main on merge (fixes issue #79).

    Args:
        worktree_path: Path to the worktree root
        patterns: List of patterns to exclude (e.g., [".kittify/memory"])
    """
    # In a worktree, .git is a file pointing to the real git dir
    git_path = worktree_path / ".git"
    if not git_path.exists():
        return

    # Find the actual git directory
    if git_path.is_file():
        # Worktree: .git file contains "gitdir: /path/to/real/.git/worktrees/name"
        try:
            content = git_path.read_text().strip()
            if content.startswith("gitdir:"):
                git_dir = Path(content[7:].strip())
                exclude_file = git_dir / "info" / "exclude"
            else:
                return
        except (OSError, ValueError):
            return
    else:
        # Regular repo or already resolved
        exclude_file = git_path / "info" / "exclude"

    # Ensure info directory exists
    exclude_file.parent.mkdir(parents=True, exist_ok=True)

    # Read existing exclusions
    existing = set()
    if exclude_file.exists():
        try:
            existing = set(exclude_file.read_text().splitlines())
        except OSError:
            pass

    # Add new patterns if not already present
    new_patterns = [p for p in patterns if p not in existing]
    if new_patterns:
        try:
            with exclude_file.open("a") as f:
                # Add comment if this is our first addition
                marker = "# Added by spec-kitty (worktree symlinks)"
                if marker not in existing:
                    f.write(f"\n{marker}\n")
                for pattern in new_patterns:
                    f.write(f"{pattern}\n")
        except OSError:
            # If we can't write, just skip - not critical
            pass


def create_wp_workspace(
    repo_root: Path,
    workspace_path: Path,
    workspace_name: str,
    wp_frontmatter: dict,
    base_branch: str | None = None,
    base_commit: str | None = None,
) -> Path:
    """Create a workspace for a work package, routing by execution_mode.

    Routes workspace creation based on the WP's ``execution_mode`` field
    from the ownership manifest embedded in its frontmatter:

    * ``code_change``        → creates a standard git worktree at ``workspace_path``
    * ``planning_artifact``  → returns ``repo_root`` (work directly in-repo, no
      worktree created, full repo visible)

    No sparse checkout is applied in either case.

    Args:
        repo_root: Absolute path to the repository root.
        workspace_path: Where a ``code_change`` worktree would be created.
        workspace_name: Branch name for a ``code_change`` worktree.
        wp_frontmatter: Parsed YAML frontmatter dict for the work package.
            Must contain ``execution_mode`` (defaults to ``code_change`` if absent).
        base_branch: Optional branch to base the worktree on.
        base_commit: Optional commit to base the worktree on.

    Returns:
        Path to the workspace.  For ``code_change`` this is ``workspace_path``
        (after creation); for ``planning_artifact`` this is ``repo_root``.

    Raises:
        RuntimeError: If worktree creation fails for a ``code_change`` WP.
        FileExistsError: If ``workspace_path`` already exists and is not a
            valid git worktree (``code_change`` only).
    """
    # Determine execution_mode from frontmatter; default to code_change when absent
    raw_mode = wp_frontmatter.get("execution_mode", ExecutionMode.CODE_CHANGE)
    try:
        mode = ExecutionMode(raw_mode)
    except ValueError:
        mode = ExecutionMode.CODE_CHANGE

    if mode == ExecutionMode.PLANNING_ARTIFACT:
        owned_files: list[str] = wp_frontmatter.get("owned_files") or []
        wp_code = wp_frontmatter.get("work_package_id", "")
        feature_slug = wp_frontmatter.get("feature_slug", "")
        return create_planning_workspace(
            feature_slug=feature_slug,
            wp_code=wp_code,
            owned_files=list(owned_files) if isinstance(owned_files, (list, tuple)) else [],
            repo_root=repo_root,
        )

    # code_change: create a standard git worktree (full checkout)
    workspace_path.parent.mkdir(parents=True, exist_ok=True)

    if workspace_path.exists():
        # Reuse if it is already a valid worktree
        git_marker = workspace_path / ".git"
        if git_marker.exists():
            return workspace_path
        raise FileExistsError(f"Workspace path already exists but is not a worktree: {workspace_path}")

    vcs = get_vcs(repo_root)
    result = vcs.create_workspace(
        workspace_path=workspace_path,
        workspace_name=workspace_name,
        base_branch=base_branch,
        base_commit=base_commit,
        repo_root=repo_root,
    )

    if not result.success:
        raise RuntimeError(f"Failed to create workspace: {result.error}")

    return workspace_path


def get_next_feature_number(repo_root: Path) -> int:
    """Determine next sequential feature number.

    Scans both kitty-specs/ and .worktrees/ directories for existing features
    (###-name format) and returns next number in sequence. This prevents number
    reuse when features exist only in worktrees.

    Args:
        repo_root: Repository root path

    Returns:
        Next feature number (e.g., 9 if highest existing is 008)

    Examples:
        >>> repo_root = Path("/path/to/repo")
        >>> next_num = get_next_feature_number(repo_root)
        >>> assert next_num > 0
    """
    max_number = 0

    # Scan kitty-specs/ for feature numbers
    specs_dir = repo_root / KITTY_SPECS_DIR
    if specs_dir.exists():
        for item in sorted(specs_dir.iterdir(), key=lambda p: p.name):
            if item.is_dir() and len(item.name) >= 3 and item.name[:3].isdigit():
                try:
                    number = int(item.name[:3])
                    max_number = max(max_number, number)
                except ValueError:
                    # Not a valid number, skip
                    continue

    # Also scan .worktrees/ for feature numbers
    worktrees_dir = repo_root / WORKTREES_DIR
    if worktrees_dir.exists():
        for item in sorted(worktrees_dir.iterdir(), key=lambda p: p.name):
            if item.is_dir() and len(item.name) >= 3 and item.name[:3].isdigit():
                try:
                    number = int(item.name[:3])
                    max_number = max(max_number, number)
                except ValueError:
                    # Not a valid number, skip
                    continue

    return max_number + 1


def create_feature_worktree(
    repo_root: Path,
    feature_slug: str,
    feature_number: int | None = None
) -> tuple[Path, Path]:
    """Create workspace (git worktree) for feature development.

    Creates a new workspace with a feature branch and sets up the
    feature directory structure. Uses VCS abstraction.

    Args:
        repo_root: Repository root path
        feature_slug: Feature identifier (e.g., "test-feature")
        feature_number: Optional feature number (auto-detected if None)

    Returns:
        Tuple of (worktree_path, feature_dir)

    Raises:
        RuntimeError: If workspace creation fails
        FileExistsError: If worktree path already exists

    Examples:
        >>> repo_root = Path("/path/to/repo")
        >>> worktree, feature_dir = create_feature_worktree(repo_root, "new-feature")
        >>> assert worktree.exists()
        >>> assert feature_dir.exists()
    """
    # Auto-detect feature number if not provided
    if feature_number is None:
        feature_number = get_next_feature_number(repo_root)

    # Format: 001-test-feature
    branch_name = f"{feature_number:03d}-{feature_slug}"

    # Create worktree at .worktrees/001-test-feature
    worktree_path = repo_root / WORKTREES_DIR / branch_name

    # Ensure .worktrees directory exists
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if worktree already exists
    if worktree_path.exists():
        # Check if it's a valid workspace using VCS abstraction
        is_valid_workspace = False
        try:
            vcs = get_vcs(worktree_path)
            is_valid_workspace = vcs.is_repo(worktree_path)
        except Exception:
            pass

        # If VCS says no (or failed), fall back to simple git check
        # A valid git worktree has .git as a file (pointing to main repo)
        # or as a directory (standalone repo)
        if not is_valid_workspace:
            git_marker = worktree_path / ".git"
            is_valid_workspace = git_marker.exists()

        if is_valid_workspace:
            feature_dir = worktree_path / KITTY_SPECS_DIR / branch_name
            return (worktree_path, feature_dir)

        raise FileExistsError(f"Worktree path already exists: {worktree_path}")

    # Get VCS implementation and create workspace (full checkout, no sparse exclusions)
    try:
        vcs = get_vcs(repo_root)
        result = vcs.create_workspace(
            workspace_path=worktree_path,
            workspace_name=branch_name,
            repo_root=repo_root,
        )

        if not result.success:
            raise RuntimeError(f"Failed to create workspace: {result.error}")

    except Exception as e:
        deterministic_preflight_markers = (
            "Git repository check failed:",
            "Git rejected repository ownership trust",
            "Git worktree discovery failed:",
        )
        if any(marker in str(e) for marker in deterministic_preflight_markers):
            raise

        # If VCS abstraction fails, fall back to direct git command with warning
        warnings.warn(
            f"VCS abstraction failed ({type(e).__name__}: {e}); "
            "falling back to direct git commands. "
            "See: VCS abstraction layer documentation",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), "-b", branch_name],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
        except subprocess.CalledProcessError as git_error:
            raise RuntimeError(
                f"Failed to create workspace: {git_error.stderr}"
            ) from git_error

    # Create feature directory structure
    feature_dir = worktree_path / KITTY_SPECS_DIR / branch_name
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Setup feature directory (symlinks, subdirectories, etc.)
    setup_feature_directory(feature_dir, worktree_path, repo_root)

    return (worktree_path, feature_dir)


def setup_feature_directory(
    feature_dir: Path,
    worktree_path: Path,
    repo_root: Path,
    create_symlinks: bool = True
) -> None:
    """Setup standard feature directory structure.

    Creates:
    - kitty-specs/###-name/ directory
    - Subdirectories: checklists/, research/, tasks/
    - Symlinks to .kittify/memory/ (or file copies on Windows)
    - spec.md from template
    - tasks/README.md

    Args:
        feature_dir: Feature directory path
        worktree_path: Worktree root path
        repo_root: Main repository root path
        create_symlinks: If True, create symlinks; else copy files (Windows)

    Examples:
        >>> feature_dir = Path("/path/to/.worktrees/001-feature/kitty-specs/001-feature")
        >>> setup_feature_directory(feature_dir, feature_dir.parent.parent, repo_root)
        >>> assert (feature_dir / "checklists").exists()
    """
    # Ensure feature directory exists
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (feature_dir / "checklists").mkdir(exist_ok=True)
    (feature_dir / "research").mkdir(exist_ok=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    # Create tasks/.gitkeep and README.md
    (tasks_dir / ".gitkeep").touch()

    # Create tasks/README.md with frontmatter format reference
    tasks_readme_content = '''# Tasks Directory

This directory contains work package (WP) prompt files.

## Directory Structure (v0.9.0+)

```
tasks/
├── WP01-setup-infrastructure.md
├── WP02-user-authentication.md
├── WP03-api-endpoints.md
└── README.md
```

All WP files are stored flat in `tasks/`.

## Status Tracking

Status is tracked in `status.events.jsonl`, not in WP frontmatter.
Use `spec-kitty agent tasks move-task` to change WP status.

## Work Package File Format

Each WP file **MUST** use YAML frontmatter:

```yaml
---
work_package_id: "WP01"
title: "Work Package Title"
subtasks:
  - "T001"
  - "T002"
phase: "Phase 1 - Setup"
assignee: ""
agent: ""
shell_pid: ""
history:
  - at: "2025-01-01T00:00:00Z"
    actor: "system"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 -- Work Package Title

[Content follows...]
```

## Moving Between Lanes

Use the CLI to emit a status transition event:
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
    (tasks_dir / "README.md").write_text(tasks_readme_content, encoding='utf-8')

    # Create worktree .kittify directory if it doesn't exist
    worktree_kittify = worktree_path / KITTIFY_DIR
    worktree_kittify.mkdir(exist_ok=True)

    # Setup shared constitution and AGENTS.md via symlink (or copy on Windows)
    # Calculate relative path from worktree to main repo
    # Worktree: .worktrees/001-feature/.kittify/memory
    # Main:     .kittify/memory
    # Relative: ../../../.kittify/memory
    relative_memory_path = Path("../../../.kittify/memory")
    relative_agents_path = Path("../../../.kittify/AGENTS.md")

    worktree_memory = worktree_kittify / "memory"
    worktree_agents = worktree_kittify / "AGENTS.md"

    # Detect if we're on Windows or symlinks are not supported
    is_windows = platform.system() == "Windows"
    use_copy = is_windows or not create_symlinks

    # Setup memory/ symlink or copy
    if worktree_memory.is_symlink():
        # Remove existing symlink first (can't use rmtree on symlinks)
        worktree_memory.unlink()
    elif worktree_memory.exists() and worktree_memory.is_dir():
        # Remove existing directory (from git worktree add)
        shutil.rmtree(worktree_memory)

    if use_copy:
        # Copy memory directory
        main_memory = repo_root / KITTIFY_DIR / "memory"
        if main_memory.exists() and main_memory.is_dir():
            shutil.copytree(main_memory, worktree_memory)
    else:
        # Create relative symlink
        try:
            worktree_memory.symlink_to(relative_memory_path, target_is_directory=True)
        except (OSError, NotImplementedError):
            # Symlink failed, fall back to copy
            main_memory = repo_root / KITTIFY_DIR / "memory"
            if main_memory.exists() and main_memory.is_dir():
                shutil.copytree(main_memory, worktree_memory)

    # Setup AGENTS.md symlink or copy
    if worktree_agents.exists():
        worktree_agents.unlink()

    main_agents = repo_root / KITTIFY_DIR / "AGENTS.md"
    if main_agents.exists():
        if use_copy:
            shutil.copy2(main_agents, worktree_agents)
        else:
            try:
                worktree_agents.symlink_to(relative_agents_path)
            except (OSError, NotImplementedError):
                shutil.copy2(main_agents, worktree_agents)

    # Exclude symlinks from git to prevent them from being committed
    # This fixes issue #79: symlinks overwriting main repo files on merge
    _exclude_from_git(worktree_path, [".kittify/memory", ".kittify/AGENTS.md"])

    # Copy spec template if it exists
    spec_file = feature_dir / "spec.md"
    if not spec_file.exists():
        # Try to find spec template
        spec_template_candidates = [
            repo_root / KITTIFY_DIR / "templates" / "spec-template.md",
            repo_root / "templates" / "spec-template.md",
        ]

        for template in spec_template_candidates:
            if template.exists():
                shutil.copy2(template, spec_file)
                break
        else:
            # No template found, create empty spec.md
            spec_file.touch()


def validate_feature_structure(
    feature_dir: Path,
    check_tasks: bool = False
) -> dict:
    """Validate feature directory structure and required files.

    Checks for:
    - Required files: spec.md
    - Recommended directories: checklists/, research/, tasks/
    - Optional: tasks.md (if check_tasks=True)

    Args:
        feature_dir: Feature directory path
        check_tasks: If True, validate tasks.md and task files exist

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": [list of error messages],
            "warnings": [list of warning messages],
            "paths": {dict of important paths}
        }

    Examples:
        >>> feature_dir = Path("/path/to/kitty-specs/001-feature")
        >>> result = validate_feature_structure(feature_dir)
        >>> assert "valid" in result
        >>> assert "errors" in result
    """
    errors = []
    warnings = []
    paths: dict[str, str] = {}
    artifact_files: dict[str, str] = {}
    artifact_dirs: dict[str, str] = {}
    available_docs: list[str] = []

    # Check if feature directory exists
    if not feature_dir.exists():
        errors.append(f"Feature directory not found: {feature_dir}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "paths": paths,
            "artifact_files": artifact_files,
            "artifact_dirs": artifact_dirs,
            "available_docs": available_docs,
            "FEATURE_DIR": "",
            "AVAILABLE_DOCS": available_docs,
        }

    # Check required files exist
    spec_file = feature_dir / "spec.md"
    if not spec_file.exists():
        errors.append("Missing required file: spec.md")
    else:
        spec_file_str = str(spec_file)
        paths["spec_file"] = spec_file_str
        artifact_files["spec_file"] = spec_file_str
        available_docs.append("spec.md")

    plan_file = feature_dir / "plan.md"
    if plan_file.exists():
        plan_file_str = str(plan_file)
        paths["plan_file"] = plan_file_str
        artifact_files["plan_file"] = plan_file_str
        available_docs.append("plan.md")

    # Check directory structure
    recommended_dirs = ["checklists", "research", "tasks"]
    for dir_name in recommended_dirs:
        dir_path = feature_dir / dir_name
        if not dir_path.exists():
            warnings.append(f"Missing recommended directory: {dir_name}/")
        else:
            dir_path_str = str(dir_path)
            paths[f"{dir_name}_dir"] = dir_path_str
            artifact_dirs[f"{dir_name}_dir"] = dir_path_str

    # Check task files if requested
    if check_tasks:
        tasks_file = feature_dir / "tasks.md"
        if not tasks_file.exists():
            errors.append("Missing required file: tasks.md")
        else:
            tasks_file_str = str(tasks_file)
            paths["tasks_file"] = tasks_file_str
            artifact_files["tasks_file"] = tasks_file_str
            if "tasks.md" not in available_docs:
                available_docs.append("tasks.md")
    else:
        tasks_file = feature_dir / "tasks.md"
        if tasks_file.exists():
            tasks_file_str = str(tasks_file)
            paths["tasks_file"] = tasks_file_str
            artifact_files["tasks_file"] = tasks_file_str
            available_docs.append("tasks.md")

    # Always include feature_dir in paths
    feature_dir_str = str(feature_dir)
    paths["feature_dir"] = feature_dir_str
    artifact_dirs["feature_dir"] = feature_dir_str

    checklists_dir = feature_dir / "checklists"
    if checklists_dir.exists():
        checklists_dir_str = str(checklists_dir)
        artifact_dirs.setdefault("checklists_dir", checklists_dir_str)

    research_dir = feature_dir / "research"
    if research_dir.exists():
        research_dir_str = str(research_dir)
        artifact_dirs.setdefault("research_dir", research_dir_str)

    tasks_dir = feature_dir / "tasks"
    if tasks_dir.exists():
        tasks_dir_str = str(tasks_dir)
        artifact_dirs.setdefault("tasks_dir", tasks_dir_str)

    available_docs = sorted(set(available_docs))

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "paths": paths,
        "artifact_files": artifact_files,
        "artifact_dirs": artifact_dirs,
        "available_docs": available_docs,
        # Compatibility aliases for older templates/prompts
        "FEATURE_DIR": feature_dir_str,
        "AVAILABLE_DOCS": available_docs,
    }
