"""Execution-state resolution entry point (canonical surface, internal module).

This is an **internal** submodule of the :mod:`mission_runtime` umbrella. It is
import-forbidden from outside the package — consumers use the symbols re-exported
from :mod:`mission_runtime` only (see ADR 2026-06-07-1 and
``tests/architectural/test_mission_runtime_surface.py``).

WP02 stands up :func:`resolve_action_context` and :class:`ActionContextError` as
**stubs** so the public ``__all__`` is satisfiable. WP03 relocates the hardened
``resolve_action_context`` from ``specify_cli.core.execution_context`` here under
the Strangler migration, delegating to today's resolver to preserve behaviour
(NFR-001).
"""
from __future__ import annotations

from pathlib import Path

from mission_runtime.context import ExecutionContext, ExecutionMode


class ActionContextError(RuntimeError):
    """Raised when canonical action context cannot be resolved.

    The single error type consumers catch. The resolver raises this on
    unresolvable context — there is never a silent fallback (see the contract).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def resolve_action_context(
    repo_root: Path,
    mission: str,
    wp_id: str | None = None,
    *,
    mode: ExecutionMode | None = None,
) -> ExecutionContext:
    """Resolve the canonical :class:`ExecutionContext` for an action.

    CWD-invariant, topology-aware, mode-correct. Raises
    :class:`ActionContextError` on unresolvable context (no silent fallback).

    WP02 stub: the real resolution logic is relocated from
    ``specify_cli.core.execution_context`` in WP03. Until then this raises so no
    caller can mistake the stub for working behaviour. The requested inputs are
    echoed into the error so a premature caller sees exactly what it asked for.
    """
    requested = f"repo_root={repo_root}, mission={mission!r}, wp_id={wp_id!r}, mode={mode}"
    raise ActionContextError(
        "not_implemented",
        "mission_runtime.resolve_action_context is wired in WP03; "
        f"the WP02 umbrella ships the surface only (requested: {requested}).",
    )
