"""Shared, canonical stdlib-``ast`` analysis primitives.

Small, pure helpers for reasoning about Python modules at the AST level
(imports, re-exports, ``__all__`` declarations). These are the single
canonical home for predicates that were previously hand-rolled — and
subtly diverged — across the architectural dead-code gates and the
post-merge stale-assertion analyzer.

No ``__all__`` is declared here on purpose: several primitives are
consumed only by ``tests/architectural/`` gates (never by another ``src/``
module), so declaring them in ``__all__`` would trip the symbol-level
dead-code gate. Import the functions by name instead.
"""
