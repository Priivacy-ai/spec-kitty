"""Backward-compatible re-exports from ``doctrine.resolver``.

The canonical implementation of the 5-tier asset resolution chain was
moved to ``doctrine.resolver`` so that the ``constitution`` layer can
use it without violating the 2.x architectural dependency direction:

    kernel (root) <- doctrine <- constitution <- specify_cli

Public symbols are re-exported here so that existing
``from specify_cli.runtime.resolver import …`` statements continue to
work without modification.

Test-only helpers (``_reset_migrate_nudge``, ``_is_global_runtime_configured``)
should be imported from ``doctrine.resolver`` directly.
"""

from __future__ import annotations

from doctrine.resolver import (
    ResolutionResult,
    ResolutionTier,
    resolve_command,
    resolve_mission,
    resolve_template,
)

__all__ = [
    "ResolutionResult",
    "ResolutionTier",
    "resolve_command",
    "resolve_mission",
    "resolve_template",
]
