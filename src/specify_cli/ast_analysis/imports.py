"""Canonical ``ast`` primitives for imports, re-exports, and ``__all__``.

This module is the single source of truth for a family of low-level
predicates that were previously hand-rolled as three independent copies:

* ``tests/architectural/test_no_dead_symbols.py`` — ``_resolve_import_from``
  and ``_extract_all_literal``.
* ``tests/architectural/test_no_dead_modules.py`` — ``_resolve_import_from``.
* ``src/specify_cli/post_merge/stale_assertions.py`` — the module-head
  re-export detector (``_import_binds_name`` / ``_dunder_all_contains_name``).

The three copies had **deliberately different semantics** for their
respective jobs. This module preserves each behavior exactly rather than
"unifying" them into one lossy predicate — the divergences are documented
inline so a future reader sees they are intentional, not accidental:

* ``module_of_import_from`` — byte-identical resolver shared by both
  architectural gates (dead-symbols and dead-modules).
* ``extract_static_all`` — the dead-symbols gate's whole-module ``__all__``
  reader: returns the full static set, distinguishes *dynamic* (``None``)
  from *absent-value* (empty ``frozenset``), is ``AnnAssign``-aware, and
  accepts only list/tuple literals.
* ``import_binds_name`` / ``assignment_lists_dunder_all`` — the
  stale-assertion analyzer's per-node membership predicates: they answer
  "does *this* statement bind/export *this* name?", accept ``__all__``
  expressed as a set literal too, and are **not** ``AnnAssign``-aware.

The last two ``__all__`` helpers intentionally differ from
``extract_static_all`` (set-literal handling, ``AnnAssign`` handling); they
answer a different question and must not be collapsed together.
"""

from __future__ import annotations

import ast

# ---------------------------------------------------------------------------
# ImportFrom module resolution (shared by both architectural gates)
# ---------------------------------------------------------------------------


def module_of_import_from(node: ast.ImportFrom, containing_pkg: str) -> str:
    """Resolve a ``from X import ...`` node to its absolute dotted module.

    Handles absolute imports (``level == 0``) and relative imports
    (``level >= 1``) by trimming ``level - 1`` trailing segments from the
    importer's containing package. ``level == 1`` means "from this
    package", ``level == 2`` means "from the parent package", and so on.

    This is byte-for-byte the logic that the ``test_no_dead_symbols`` and
    ``test_no_dead_modules`` gates each carried independently, so both keep
    identical resolution after adopting this shared primitive.
    """
    level = node.level or 0
    mod = node.module or ""
    if level == 0:
        return mod
    pkg_parts = containing_pkg.split(".") if containing_pkg else []
    base_parts = pkg_parts[: len(pkg_parts) - (level - 1)] if level > 1 else pkg_parts[:]
    if mod:
        base_parts = base_parts + mod.split(".")
    return ".".join(base_parts)


# ---------------------------------------------------------------------------
# Whole-module static ``__all__`` reader (dead-symbols gate semantics)
# ---------------------------------------------------------------------------


def extract_static_all(tree: ast.Module) -> frozenset[str] | None:
    """Return the names listed in the module's ``__all__`` if static.

    Returns ``None`` if the module does not declare ``__all__`` OR
    declares it dynamically (e.g. ``__all__ = sorted(...)``). Dynamic
    declarations are legal but cannot be statically introspected for
    membership and are therefore skipped by callers that walk membership.

    Accepts both ``ast.Assign`` and ``ast.AnnAssign`` — typed
    declarations like ``__all__: list[str] = []`` are equivalent for the
    purposes of this walker. Only list/tuple literals are accepted as a
    static value; anything else (including a set literal) yields ``None``.

    An ``AnnAssign`` without a value (``__all__: list[str]``) is treated as
    dynamic/absent membership and returns an empty ``frozenset`` — distinct
    from ``None``, which means "not statically introspectable".

    NOTE: this deliberately differs from ``assignment_lists_dunder_all``,
    which is a per-node membership predicate accepting set literals and
    ignoring ``AnnAssign``. The two answer different questions; do not
    collapse them.
    """
    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            tgt = node.target
            if isinstance(tgt, ast.Name) and tgt.id == "__all__":
                value = node.value
            else:
                continue  # non-__all__ AnnAssign; skip rather than fall-through
        else:
            continue
        if value is None:
            # AnnAssign without value (``__all__: list[str]``): treat as
            # dynamic / absent membership.
            return frozenset()
        if not isinstance(value, (ast.List, ast.Tuple)):
            return None
        names: list[str] = []
        for elt in value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                names.append(elt.value)
            else:
                return None
        return frozenset(names)
    return None


# ---------------------------------------------------------------------------
# Per-node module-head binding / re-export predicates
# (stale-assertion analyzer semantics)
# ---------------------------------------------------------------------------


def import_binds_name(node: ast.Import | ast.ImportFrom, name: str) -> bool:
    """Return True when an import statement binds/re-exports *name*.

    ``ast.ImportFrom`` matches on the imported symbol's ORIGINAL name
    (``alias.name``) as well as its local bound name (``alias.asname or
    alias.name``) — this covers both a direct re-export (``from mod import
    X``) and a shim that renames on import in either direction (``from mod
    import X as _X`` or ``from mod import other as X``).

    ``ast.Import`` is different: a bare import only ever binds its TOP-LEVEL
    local name (``import mod`` binds ``mod``; ``import mod as X`` binds
    ``X``; ``import pkg.sub`` binds ``pkg`` — never ``sub`` and never the
    dotted path). Matching on ``alias.name`` there (as ImportFrom does)
    would be wrong in both directions: ``import mod as X`` does NOT leave
    ``mod`` importable (only ``X`` is bound), and ``import pkg.sub`` DOES
    leave ``pkg`` importable even though ``alias.name`` is the dotted
    ``"pkg.sub"``.
    """
    if isinstance(node, ast.Import):
        return any(
            (alias.asname or alias.name.split(".")[0]) == name for alias in node.names
        )
    return any(alias.name == name or alias.asname == name for alias in node.names)


def _targets_dunder_all(node: ast.Assign) -> bool:
    """Return True when *node* assigns to a module-level ``__all__`` name."""
    return any(
        isinstance(target, ast.Name) and target.id == "__all__"
        for target in node.targets
    )


def assignment_lists_dunder_all(node: ast.Assign, name: str) -> bool:
    """Return True when an ``__all__ = [...]`` assignment lists *name*.

    Membership predicate for a single ``ast.Assign`` node. Accepts
    ``__all__`` expressed as a list, tuple, OR set literal, and looks for a
    string ``Constant`` equal to *name* among its elements.

    NOTE: unlike ``extract_static_all`` this deliberately does NOT handle
    ``AnnAssign`` (typed ``__all__: list[str] = [...]``): the stale-assertion
    analyzer scans ``ast.Assign`` head statements only, and preserving that
    exact scope is required to keep its observable behavior unchanged.
    """
    if not _targets_dunder_all(node):
        return False
    if not isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
        return False
    return any(
        isinstance(elt, ast.Constant) and elt.value == name for elt in node.value.elts
    )
