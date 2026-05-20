"""Shared DRG graph-load helpers for charter resolver and compiler.

Introduced in WP03 of the
``excise-doctrine-curation-and-inline-references-01KP54J6`` mission so that
``src/charter/resolver.py`` and ``src/charter/compiler.py`` no longer
duplicate the shipped+project merge/validate sequence.

Updated in WP03 of ``layered-doctrine-org-layer-01KRNPEE`` to add
``_resolve_org_root()`` and perform three-layer (shipped → org → project)
DRG merging in ``load_validated_graph()``.

Architectural note
------------------
``charter`` sits below ``specify_cli`` in the dependency hierarchy::

    kernel (root) <- doctrine <- charter <- specify_cli

``_resolve_org_root()`` therefore cannot import ``specify_cli`` directly.  The
charter-layer implementation always returns ``None`` (no-config fallback).
Callers in ``specify_cli`` that need config-aware org-root resolution should
resolve the path themselves and pass it explicitly as the *org_root* argument
to :func:`load_validated_graph`.
"""

from __future__ import annotations

from pathlib import Path

from charter.catalog import resolve_doctrine_root
from doctrine.drg.loader import has_graph_files, load_graph_or_dir, merge_layers
from doctrine.drg.models import DRGGraph
from doctrine.drg.validator import assert_valid


def _resolve_org_root(_repo_root: Path) -> Path | None:
    """Return the configured org doctrine snapshot path, or ``None`` if absent.

    The charter-layer implementation is intentionally inert — it always returns
    ``None``.  The ``repo_root`` parameter is accepted for API compatibility;
    callers in ``specify_cli`` are expected to resolve the org root themselves
    (e.g. via ``specify_cli.doctrine.config``) and supply it explicitly to
    :func:`load_validated_graph`.

    This design keeps the ``charter`` package free of ``specify_cli`` imports,
    satisfying the architectural boundary enforced by
    ``tests/architectural/test_layer_rules.py``.
    """
    return None


def load_validated_graph(repo_root: Path, org_root: Path | None = None) -> DRGGraph:
    """Load the shipped + org + project DRG overlay and validate the result.

    Performs a three-layer merge:

    1. **shipped** — built-in graph bundled with the ``doctrine`` package.
    2. **org** — optional organisation-level snapshot supplied via *org_root*.
       When *org_root* is ``None``, :func:`_resolve_org_root` is called; the
       charter-layer implementation returns ``None`` (no-op).  Callers in
       ``specify_cli`` that need config-aware resolution should resolve the org
       root and pass it explicitly.
    3. **project** — optional per-project overlay at
       ``<repo_root>/.kittify/doctrine``.

    Args:
        repo_root: Project root; used to locate the project overlay at
            ``<repo_root>/.kittify/doctrine``.
        org_root: Explicit org doctrine root.  Pass the path returned by the
            ``specify_cli``-layer org-root resolver when calling from higher
            layers.  Defaults to ``None`` (two-layer shipped+project merge).

    Returns:
        A validated :class:`DRGGraph`.

    Raises:
        ValueError: If :func:`assert_valid` rejects the merged graph
            (dangling edges, duplicate edges, or ``requires`` cycles).
    """
    doctrine_root = resolve_doctrine_root()
    if org_root is None:
        org_root = _resolve_org_root(repo_root)

    shipped = load_graph_or_dir(doctrine_root)
    org = load_graph_or_dir(org_root) if org_root and org_root.exists() else None
    project_dir = repo_root / ".kittify" / "doctrine"
    project = (
        load_graph_or_dir(project_dir)
        if has_graph_files(project_dir)
        else None
    )

    merged = merge_layers(merge_layers(shipped, org), project)
    assert_valid(merged)
    return merged


__all__ = [
    "load_validated_graph",
]
