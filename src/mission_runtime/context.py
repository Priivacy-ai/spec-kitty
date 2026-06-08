"""Execution-state context objects (canonical surface, internal module).

This is an **internal** submodule of the :mod:`mission_runtime` umbrella. It is
import-forbidden from outside the package — consumers use the symbols re-exported
from :mod:`mission_runtime` only (see ADR 2026-06-07-1 and
``tests/architectural/test_mission_runtime_surface.py``).

WP02 stands up these names as **stubs** so the package imports cleanly and the
public ``__all__`` is satisfiable. WP03 relocates the hardened
``ExecutionContext`` from ``specify_cli.core.execution_context`` into this module
under the Strangler migration; the placeholders below are replaced then.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass


class ExecutionMode(enum.Enum):
    """How an action's execution context is resolved.

    Stub vocabulary for WP02; the authoritative member set is wired in WP03 when
    the resolver is relocated. ``WORKTREE`` resolves against a lane worktree;
    ``CODE_CHANGE`` resolves against an in-place checkout.
    """

    WORKTREE = "worktree"
    CODE_CHANGE = "code_change"


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable, fully-resolved context for a single action.

    The canonical surface is expressed over **this object**, never over path
    fragments: consumers receive a resolved context and never reconstruct
    ``main_repo_root / "kitty-specs" / mission_slug`` themselves (FR-009).

    WP02 ships the minimal shape (mission identity + resolution mode) so the
    public API is type-checkable. WP03 relocates the complete field set
    (read/write/dest dirs, target branch, WP identity, prompt) from
    ``specify_cli.core.execution_context`` here, preserving behaviour (NFR-001).
    """

    mission_slug: str
    mode: ExecutionMode
