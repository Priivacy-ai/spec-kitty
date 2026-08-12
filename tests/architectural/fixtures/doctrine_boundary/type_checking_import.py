"""Fixture: ``doctrine`` imports that live ONLY under ``if TYPE_CHECKING:``.

The lazy-import ratchet MUST NOT flag this file. A ``TYPE_CHECKING`` import is
erased at runtime (it exists only for the type checker), so it is not a real
runtime reach-through into doctrine.

Two guards are present so the fixture proves the ``TYPE_CHECKING`` skip is what
saves it — not merely the module-level rule:

* a conventional module-level ``if TYPE_CHECKING:`` (nesting depth 0), and
* a ``TYPE_CHECKING`` guard **inside a function body** (nesting depth 1) — here
  only the ``TYPE_CHECKING`` bookkeeping keeps it unflagged; a descent that
  skipped the guard would (wrongly) treat it as a lazy import.

This file is parsed by the ratchet via ``ast.parse``; it is never imported, so
the guarded imports never resolve.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from doctrine.drg.models import ReferenceGraph  # noqa: F401


def build_graph() -> object:  # pragma: no cover - never executed
    if TYPE_CHECKING:
        from doctrine.drg.loader import load_reference_graph  # noqa: F401
    raise NotImplementedError
