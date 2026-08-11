"""Charter facade for the SPDD (REASONS) template-block application surface.

This module is the charter-layer proxy for runtime callers that apply SPDD
REASONS blocks into a project's templates. The runtime → charter → doctrine
boundary (ADR 2026-03-27-1, re-affirmed by mission
``doctrine-public-api-surface-01KZPDSR``) requires runtime modules under
``src/specify_cli/`` to reach doctrine artifacts only through charter facades.

``doctrine.spdd_reasons`` is dispositioned ``FACADE-ONLY`` in the WP01 census
(fronted by a clean charter door but not part of the wheel's public contract),
so ``apply_spdd_blocks_for_project`` is re-exported from the
``doctrine.spdd_reasons`` package surface (not from ``doctrine.api``).

This file is a **pure re-export** module — no behaviour, no wrappers, no type
aliases. Object identity is preserved
(``charter.spdd_reasons.apply_spdd_blocks_for_project is
doctrine.spdd_reasons.apply_spdd_blocks_for_project``), enforced by
``tests/architectural/test_charter_facades_reexport_doctrine.py``.
"""

from doctrine.spdd_reasons import apply_spdd_blocks_for_project

__all__ = [
    "apply_spdd_blocks_for_project",
]
