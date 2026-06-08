"""``mission_runtime`` — the canonical execution-state surface.

This umbrella package is the single, screaming home for execution-state
resolution: given a mission (and optional work package), it produces a fully
resolved, CWD-invariant :class:`ExecutionContext`. Consumers import **only** from
this package root; internal submodules (``context``, ``resolution``) are
import-forbidden from outside the package and enforced by
``tests/architectural/test_mission_runtime_surface.py`` (FR-005).

The public API is expressed over context objects, never over path fragments —
callers receive a resolved context and never reconstruct
``main_repo_root / "kitty-specs" / mission_slug`` themselves (FR-009).

WP02 stands up the package empty-but-registered (lean ``__all__`` over stub
symbols + layer-guard registration); WP03 relocates the hardened resolver here.

See ADR ``architecture/3.x/adr/2026-06-07-1-execution-state-canonical-surface.md``.
"""
from __future__ import annotations

from mission_runtime.context import ExecutionContext, ExecutionMode
from mission_runtime.resolution import ActionContextError, resolve_action_context

__all__ = ["ExecutionContext", "ExecutionMode", "resolve_action_context", "ActionContextError"]
