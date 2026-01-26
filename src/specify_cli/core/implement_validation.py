"""Shared dependency validation utilities for implement command.

This module provides validation logic for work package dependencies,
ensuring that workspaces are created with correct base branches.

Used by both:
- Top-level `spec-kitty implement` command
- Agent `spec-kitty agent workflow implement` command
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from specify_cli.core.dependency_graph import parse_wp_dependencies

console = Console()


def validate_and_resolve_base(
    wp_id: str,
    wp_file: Path,
    base: str | None,
    feature_slug: str,
    repo_root: Path
) -> tuple[str | None, bool]:
    """Validate dependencies and resolve base workspace.

    This function implements the core dependency validation logic:
    - Multi-parent: Returns (None, True) to trigger auto-merge mode
    - Single parent: Errors if --base not provided, validates if provided
    - No dependencies: Accepts provided base or None (branches from main)

    Args:
        wp_id: Work package ID (e.g., "WP01")
        wp_file: Path to WP markdown file
        base: Base WP ID from --base flag (may be None)
        feature_slug: Feature slug (e.g., "010-my-feature")
        repo_root: Repository root path

    Returns:
        Tuple of (base_to_use, auto_merge_mode):
        - base_to_use: The base WP ID to use, or None for main/auto-merge
        - auto_merge_mode: True if should create multi-parent merge base

    Raises:
        typer.Exit: If validation fails (missing --base, invalid base, etc.)
    """
    # Parse dependencies from WP frontmatter
    declared_deps = parse_wp_dependencies(wp_file)

    # Multi-parent dependency handling
    if len(declared_deps) > 1:
        if base is None:
            # Auto-merge mode: Create merge commit combining all dependencies
            console.print(f"\n[cyan]Multi-parent dependency detected:[/cyan]")
            console.print(f"  {wp_id} depends on: {', '.join(declared_deps)}")
            console.print(f"  Auto-creating merge base combining all dependencies...")
            return (None, True)  # Auto-merge mode
        else:
            # User provided explicit base - validate it's in dependencies
            if base not in declared_deps:
                console.print(
                    f"[yellow]Warning:[/yellow] {wp_id} doesn't declare {base} "
                    f"as dependency"
                )
                console.print(f"Declared dependencies: {declared_deps}")
                # Allow but warn (user might know better than parser)
            return (base, False)  # Use provided base, no auto-merge

    # Single dependency handling
    elif len(declared_deps) == 1:
        if base is None:
            # ERROR: Must provide --base for single dependency
            console.print(f"\n[red]Error:[/red] {wp_id} depends on {declared_deps[0]}")
            console.print(f"\nSpecify base workspace:")
            console.print(f"  spec-kitty implement {wp_id} --base {declared_deps[0]}")
            console.print(f"\n[dim]Or for agent commands:[/dim]")
            console.print(
                f"  spec-kitty agent workflow implement {wp_id} "
                f"--base {declared_deps[0]} --agent <name>"
            )
            raise typer.Exit(1)

        # Validate provided base matches dependency
        if base not in declared_deps:
            console.print(
                f"[yellow]Warning:[/yellow] {wp_id} does not declare dependency "
                f"on {base}"
            )
            console.print(f"Declared dependencies: {declared_deps}")
            # Allow but warn (user might know better than parser)

        return (base, False)  # Use provided base

    # No dependencies
    else:
        # Accept any provided base (or None for main)
        return (base, False)


def validate_base_workspace_exists(
    base: str,
    feature_slug: str,
    repo_root: Path
) -> None:
    """Validate that a base workspace exists and is valid.

    Args:
        base: Base WP ID (e.g., "WP01")
        feature_slug: Feature slug
        repo_root: Repository root path

    Raises:
        typer.Exit: If base workspace doesn't exist or is invalid
    """
    import subprocess

    base_workspace = repo_root / ".worktrees" / f"{feature_slug}-{base}"

    if not base_workspace.exists():
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
        console.print(
            f"[red]Error:[/red] {base_workspace} exists but is not a valid worktree"
        )
        console.print("This directory may be corrupted. Remove it and re-create:")
        console.print(f"  rm -rf {base_workspace}")
        console.print(f"  spec-kitty implement {base}")
        raise typer.Exit(1)


__all__ = [
    "validate_and_resolve_base",
    "validate_base_workspace_exists",
]
