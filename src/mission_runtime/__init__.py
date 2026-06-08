"""``mission_runtime`` — the canonical execution-state surface.

This umbrella package is the single, screaming home for execution-state
resolution: given a mission (and optional work package), it produces a fully
resolved, CWD-invariant :class:`ExecutionContext`. Consumers import **only** from
this package root; internal submodules (``context``, ``resolution``) are
import-forbidden from outside the package and enforced by
``tests/architectural/test_mission_runtime_surface.py`` (FR-005).

The public API is expressed over context objects, never over path fragments —
callers receive a resolved context and never reconstruct the mission-spec
directory from ``main_repo_root`` + the specs dir name + ``mission_slug``
themselves (FR-009).

WP02 stood up the package empty-but-registered (lean ``__all__`` over stub
symbols + layer-guard registration); WP03 relocated the hardened resolver here
and removed the old ``specify_cli.core.execution_context`` module outright (all
callers were migrated to this package root). A few historical command-oriented
names remain as compatibility attributes for first-party callers, but they are
not part of the public ``__all__`` surface.

See ADR ``architecture/3.x/adr/2026-06-07-1-execution-state-canonical-surface.md``.
"""
from __future__ import annotations

from typing import Any

from mission_runtime.context import ExecutionContext, ExecutionMode
from mission_runtime.resolution import (
    ActionContextError,
    resolve_action_context,
)

__all__ = [
    "ExecutionContext",
    "ExecutionMode",
    "resolve_action_context",
    "ActionContextError",
]

_COMPAT_ATTRS = frozenset(
    {
        "ActionContext",
        "ActionName",
        "ACTION_NAMES",
        "_resolve_mission_slug",
    }
)


def __getattr__(name: str) -> Any:
    """Resolve historical first-party names without widening ``__all__``."""
    if name not in _COMPAT_ATTRS:
        raise AttributeError(name)
    if name == "ActionContext":
        from mission_runtime.context import ActionContext

        return ActionContext
    from mission_runtime import resolution

    return getattr(resolution, name)
