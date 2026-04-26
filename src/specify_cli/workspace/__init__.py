"""Workspace utilities for spec-kitty.

This package owns the canonical helpers that resolve "where on disk does
the mission live?" from any cwd, including cwds inside a git worktree.

WP07 (mission ``stability-and-hygiene-hardening-2026-04-01KQ4ARB``) owns
``assert_initialized.py`` and is intentionally not re-exported here.
"""

from __future__ import annotations

from .root_resolver import (
    WorkspaceRootNotFound,
    canonicalize_feature_dir,
    resolve_canonical_root,
)

__all__ = [
    "WorkspaceRootNotFound",
    "canonicalize_feature_dir",
    "resolve_canonical_root",
]
