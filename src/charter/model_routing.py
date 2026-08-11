"""Charter facade for the model→task-type routing surface (symbol-level).

This module is the charter-layer proxy for runtime callers that need the
deterministic model/task routing evaluator + loader. The runtime → charter →
doctrine boundary (ADR 2026-03-27-1, re-affirmed by mission
``doctrine-public-api-surface-01KZPDSR``) requires runtime modules under
``src/specify_cli/`` to reach doctrine artifacts only through charter facades.

**Symbol-level, not whole-module.** This door re-exports the leaf callables and
result types (``load``, ``evaluate``, ``RoutingRecommendation``,
``CatalogLoadResult``) — never the ``doctrine.model_task_routing.loader`` /
``.evaluator`` submodules. A whole-module re-export would pass the identity gate
but defeat curation (FR-003, NFR-002, contract C2 "symbol-level rule").

These symbols are dispositioned ``PUBLIC`` in the WP01 census
(``doctrine.model_task_routing``), so they are re-exported from the curated
public surface ``doctrine.api`` (not the origin submodules directly). This gives
the PUBLIC wheel symbols a live in-repo caller — the from-``doctrine.api`` wiring
the no-dead-symbol gate and the strict T007 live-caller assertion depend on.
Object identity is unchanged: ``charter.model_routing.load is doctrine.api.load
is doctrine.model_task_routing.loader.load``.

There is no import cycle: ``doctrine.model_task_routing`` and ``doctrine.api``
depend only on ``doctrine`` / ``kernel``, never on ``charter`` or
``specify_cli``.

This file is a **pure re-export** module — no behaviour, no wrappers, no type
aliases. Enforced by
``tests/architectural/test_charter_facades_reexport_doctrine.py``.
"""

from doctrine.api import (
    CatalogLoadResult,
    RoutingRecommendation,
    evaluate,
    load,
)

__all__ = [
    "CatalogLoadResult",
    "RoutingRecommendation",
    "evaluate",
    "load",
]
