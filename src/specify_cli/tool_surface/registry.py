"""Policy registry for the tool surface contract bounded context.

The :class:`ToolSurfaceRegistry` is the authoritative answer to "what surfaces
should exist for a configured tool?". Registry is policy; manifests are state.

In this work package the registry is a stub: definitions can be registered and
read back, but provider dispatch is added in a later work package.
"""

from __future__ import annotations

from .model import SurfaceDefinition


class ToolSurfaceRegistry:
    """Authoritative registry for what tool surfaces should exist.

    Registry is policy; manifests are state. The registry holds, per tool key,
    the list of :class:`SurfaceDefinition` objects that describe the surfaces a
    configured tool should expose.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, list[SurfaceDefinition]] = {}

    def register_definition(
        self,
        tool_key: str,
        definition: SurfaceDefinition,
    ) -> None:
        """Register a surface definition for a tool key."""
        self._definitions.setdefault(tool_key, []).append(definition)

    def get_definitions(self, tool_key: str) -> list[SurfaceDefinition]:
        """Return the definitions for a tool key (empty list if none)."""
        return list(self._definitions.get(tool_key, []))

    def all_tool_keys(self) -> list[str]:
        """Return all tool keys that have at least one registered definition."""
        return list(self._definitions.keys())
