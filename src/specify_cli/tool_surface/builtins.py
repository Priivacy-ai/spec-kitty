"""Built-in surface definitions for all supported tools.

This module is a stub. WP03-WP09 populate the per-kind definitions; for now it
only establishes the structure and exposes the canonical set of supported tool
keys (imported from ``specify_cli.core.config``, never hardcoded here).
"""

from __future__ import annotations

from specify_cli.core.config import AI_CHOICES

from .registry import ToolSurfaceRegistry


def supported_tool_keys() -> tuple[str, ...]:
    """Return the canonical set of supported tool keys.

    Sourced from :data:`specify_cli.core.config.AI_CHOICES` so the tool surface
    contract stays in lock-step with the rest of the CLI rather than drifting
    from a hardcoded copy.
    """
    return tuple(AI_CHOICES.keys())


def register_builtin_definitions(registry: ToolSurfaceRegistry) -> None:
    """Register built-in surface definitions for all supported tools.

    Populated incrementally by later work packages:

    - Command skills -- registered in WP03
    - Session presence -- registered in WP04
    - Doctrine skills -- registered in WP05
    - Agent profiles -- registered in WP06
    - Plugin bundles -- registered in WP09

    This is currently a stub; providers register their own definitions on init
    in the work packages above. The ``registry`` parameter is accepted now so
    the call site contract is stable for those later work packages.
    """
    _ = registry  # stub: definitions registered by later work packages
