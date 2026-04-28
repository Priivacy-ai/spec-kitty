"""Shared DoctrineService project-root candidate resolution.

Both ``src/charter/compiler.py::_default_doctrine_service`` and
``src/charter/context.py::_build_doctrine_service`` use the same candidate-list
ordering.  This module is the **single source of truth** for that ordering so
the two call-sites cannot drift apart.

Candidate ordering (FR-009 / T024 / T025):

1. ``.kittify/doctrine/``   — Phase 3 synthesis target; present only after a
                              successful ``spec-kitty charter synthesize`` run.
2. ``src/doctrine/``        — code-local shipped-layer path (legacy 3.x default).
3. ``doctrine/``            — flat shipped-layer fallback.

Discovery is **conditional on directory presence**: if ``.kittify/doctrine/``
does not exist the resolver returns the next matching candidate, preserving
byte-identical behaviour for legacy (pre-synthesis) projects (R-2 mitigation).
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Candidate list (ordered: synthesis-aware first, shipped-layer fallbacks after)
# ---------------------------------------------------------------------------

_PROJECT_ROOT_CANDIDATES: tuple[str, ...] = (
    ".kittify/doctrine",  # NEW — Phase 3 synthesis target (FR-009)
    "src/doctrine",  # existing — code-local shipped-layer path
    "doctrine",  # existing — flat shipped-layer fallback
)


def resolve_project_root(repo_root: Path) -> Path | None:
    """Return the first existing project-doctrine directory for *repo_root*.

    Returns ``None`` when none of the candidates exist on disk, which means
    ``DoctrineService`` will be constructed with ``project_root=None`` (shipped
    layer only — identical to the pre-Phase-3 default).

    The function is intentionally a thin directory-presence check: it does
    **not** inspect the directory's contents.  An empty ``.kittify/doctrine/``
    directory is still a valid candidate (the ``DoctrineService`` will simply
    surface an empty project layer with no shipped-layer impact).

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        The first matching :class:`~pathlib.Path` or ``None``.
    """
    for candidate in _PROJECT_ROOT_CANDIDATES:
        path = repo_root / candidate
        if path.is_dir():
            return path
    return None


__all__ = ["resolve_project_root", "_PROJECT_ROOT_CANDIDATES"]
