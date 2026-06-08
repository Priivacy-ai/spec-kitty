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
symbols + layer-guard registration); WP03 relocated the hardened resolver here.
The transitional re-export shim at ``specify_cli.core.execution_context`` imports
exclusively from this package root, so the historical symbol set
(``ActionContext`` / ``ActionName`` / ``ACTION_NAMES`` / ``_resolve_mission_slug``)
is re-exported here too — there is exactly one implementation behind these names.

See ADR ``architecture/3.x/adr/2026-06-07-1-execution-state-canonical-surface.md``.
"""
from __future__ import annotations

from mission_runtime.context import ActionContext, ExecutionContext, ExecutionMode
from mission_runtime.resolution import (
    ACTION_NAMES,
    ActionContextError,
    ActionName,
    _resolve_mission_slug,
    resolve_action_context,
)

__all__ = [
    "ExecutionContext",
    "ExecutionMode",
    "resolve_action_context",
    "ActionContextError",
    # Historical surface re-exported for the transitional shim at the old path.
    "ActionContext",
    "ActionName",
    "ACTION_NAMES",
    "_resolve_mission_slug",
]
