"""Execution-state context objects (canonical surface, internal module).

This is an **internal** submodule of the :mod:`mission_runtime` umbrella. It is
import-forbidden from outside the package — consumers use the symbols re-exported
from :mod:`mission_runtime` only (see ADR 2026-06-07-1 and
``tests/architectural/test_mission_runtime_surface.py``).

WP03 relocates the hardened context value object from
``specify_cli.core.execution_context`` (the historical ``ActionContext``) into
this module under the Strangler migration, preserving the public field/API shape
(NFR-001). The canonical name is :class:`ExecutionContext`; ``ActionContext`` is
retained as a re-exported alias so callers using the historical name keep
resolving (the old ``core/execution_context`` module itself was removed).
"""
from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from typing import Any


class ExecutionMode(enum.Enum):
    """How an action's execution context is resolved.

    ``WORKTREE`` resolves against a lane worktree; ``CODE_CHANGE`` resolves
    against an in-place checkout. The resolved string mode is surfaced on
    :attr:`ExecutionContext.execution_mode` (which carries the raw workspace
    string), so this enum is the typed vocabulary callers may compare against.
    """

    WORKTREE = "worktree"
    CODE_CHANGE = "code_change"


@dataclass
class ExecutionContext:
    """Immutable, fully-resolved context for a single action.

    The canonical surface is expressed over **this object**, never over path
    fragments: consumers receive a resolved context and never reconstruct the
    mission-spec directory from ``main_repo_root`` + the specs dir name +
    ``mission_slug`` themselves (FR-009).

    Relocated verbatim from ``specify_cli.core.execution_context.ActionContext``
    (WP03, Stage C) — the field set and :meth:`to_dict` shape are preserved so
    every existing consumer continues to read the same attributes (NFR-001).
    """

    action: str
    mission_slug: str
    feature_dir: str
    target_branch: str
    detection_method: str
    wp_id: str | None = None
    wp_file: str | None = None
    lane: str | None = None
    lane_id: str | None = None
    branch_name: str | None = None
    execution_mode: str | None = None
    resolution_kind: str | None = None
    dependencies: list[str] = field(default_factory=list)
    resolved_base: str | None = None
    auto_merge: bool = False
    workspace_path: str | None = None
    commands: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Transitional alias: the historical name used by ``core/execution_context`` and
# its consumers. Kept so the Stage-C shim re-exports a single relocated type
# rather than introducing a parallel implementation (NFR-002).
ActionContext = ExecutionContext
