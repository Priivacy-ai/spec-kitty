"""Fixture: a lazy ``doctrine`` import inside a nested function body.

The lazy-import ratchet MUST flag this file. A function-body (or deeper) direct
``from charter.offering…`` import is exactly the reach-through the sibling ratchet
exists to catch: invisible to the module-level ratchet, yet a real runtime
dependency the moment the enclosing function runs. This file is parsed via
``ast.parse``; it is never imported, so the lazy import never resolves.
"""

from __future__ import annotations


def outer() -> object:
    def inner() -> object:
        # Depth-2 (function inside function) — the descent must still flag it.
        from charter.offering.drg.models import ReferenceGraph

        return ReferenceGraph

    return inner()
