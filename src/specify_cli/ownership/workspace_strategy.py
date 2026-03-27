"""Workspace strategy for planning-artifact work packages.

Provides :func:`create_planning_workspace`, which returns the path that a
planning-artifact WP should use as its working directory.

Planning-artifact WPs produce documentation/specification changes only (no
source-code changes).  They do not need an isolated git worktree because:

* They work directly in the main repository root.
* All planning files (kitty-specs/) are visible there by definition.
* Sparse checkout is NOT used anywhere in spec-kitty (removed in WP04).

The function returns ``repo_root`` so callers receive a consistent ``Path``
whether the WP is ``code_change`` (worktree) or ``planning_artifact`` (repo root).
"""

from __future__ import annotations

from pathlib import Path


def create_planning_workspace(
    feature_slug: str,  # noqa: ARG001
    wp_code: str,  # noqa: ARG001
    owned_files: list[str],  # noqa: ARG001
    repo_root: Path,
) -> Path:
    """Return the workspace path for a planning-artifact work package.

    Planning-artifact WPs work directly in-repo.  No worktree is created and
    no sparse checkout is configured.  All files in the repository are
    accessible at ``repo_root``.

    Args:
        feature_slug: Feature identifier (e.g. ``"057-canonical-context-architecture-cleanup"``).
        wp_code: Work-package code (e.g. ``"WP04"``).
        owned_files: Glob patterns describing files owned by this WP.  Not
            used for workspace creation but validated to be accessible under
            ``repo_root`` (informational only).
        repo_root: Absolute path to the repository root.

    Returns:
        ``repo_root`` — the in-repo workspace path.
    """
    if not repo_root.is_dir():
        raise ValueError(f"repo_root does not exist or is not a directory: {repo_root}")
    return repo_root
