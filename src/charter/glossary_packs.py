"""Charter facade for the glossary-pack domain model.

This module is the charter-layer proxy for runtime callers that need the
``GlossaryPack`` domain entity. The runtime → charter → doctrine boundary
(ADR 2026-03-27-1, re-affirmed by mission
``doctrine-public-api-surface-01KZPDSR``) requires runtime modules under
``src/specify_cli/`` to reach doctrine artifacts only through charter facades.

``doctrine.glossary_packs`` is dispositioned ``FACADE-ONLY`` in the WP01 census
(fronted by a clean charter door but not part of the wheel's public contract),
so ``GlossaryPack`` is re-exported from the ``doctrine.glossary_packs`` package
surface (not from ``doctrine.api``).

This file is a **pure re-export** module — no behaviour, no wrappers, no type
aliases. Object identity is preserved (``charter.glossary_packs.GlossaryPack is
doctrine.glossary_packs.GlossaryPack``), enforced by
``tests/architectural/test_charter_facades_reexport_doctrine.py``.
"""

from doctrine.glossary_packs import GlossaryPack

__all__ = [
    "GlossaryPack",
]
