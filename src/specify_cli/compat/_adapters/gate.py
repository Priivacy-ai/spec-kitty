"""Adapter wrapping specify_cli.migration.gate (WP05).

WP07 will replace migration.gate with a thin shim that delegates to
compat.planner. Until WP07 lands, this adapter exposes today's behavior.
"""

# adapter:no-logic

from __future__ import annotations

from specify_cli.migration.gate import (
    _EXEMPT_COMMANDS,
    check_schema_version,
)

__all__ = [
    "_EXEMPT_COMMANDS",
    "check_schema_version",
]
