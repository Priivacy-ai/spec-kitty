"""Charter context bootstrap for prompt generation (``specify_cli`` twin).

As of WP03 of the
``excise-doctrine-curation-and-inline-references-01KP54J6`` mission this
module is a thin re-export of :func:`charter.context.build_charter_context`
so the ``specify_cli`` surface and the canonical ``charter`` surface share
a single context builder. The pre-WP03 parallel implementation (legacy
compact/bootstrap renderer) has been deleted to avoid drift between the
two packages -- see plan D-3 "twin-package lockstep".
"""

from __future__ import annotations

from charter.context import (
    BOOTSTRAP_ACTIONS,
    CharterContextResult,
    build_charter_context,
)

__all__ = [
    "BOOTSTRAP_ACTIONS",
    "CharterContextResult",
    "build_charter_context",
]
