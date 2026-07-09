"""Plan builder for the tool surface contract bounded context.

:class:`SurfacePlanBuilder` turns the configured tool keys plus the policy
registry into a concrete :class:`SurfacePlan` per tool: it looks up each tool's
:class:`SurfaceDefinition` objects, finds the provider that can handle each, and
expands them into :class:`SurfaceInstance` objects on disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from specify_cli.core.time_utils import now_utc_iso

from .enums import SurfaceKind
from .model import SurfaceDefinition, SurfaceInstance, SurfacePlan
from .providers.protocol import ReportingSurfaceProvider
from .registry import ToolSurfaceRegistry


class SurfacePlanBuilder:
    """Compute :class:`SurfacePlan` objects from registry + providers."""

    def __init__(
        self,
        registry: ToolSurfaceRegistry,
        providers: Sequence[ReportingSurfaceProvider],
    ) -> None:
        self._registry = registry
        self._providers = list(providers)

    def build(
        self,
        configured_tool_keys: Sequence[str],
        project_root: Path,
        surface_kind_filter: SurfaceKind | None = None,
    ) -> list[SurfacePlan]:
        """Build one :class:`SurfacePlan` for each configured tool key."""
        computed_at = now_utc_iso()
        return [
            self._build_one(tool_key, project_root, surface_kind_filter, computed_at)
            for tool_key in configured_tool_keys
        ]

    def _build_one(
        self,
        tool_key: str,
        project_root: Path,
        surface_kind_filter: SurfaceKind | None,
        computed_at: str,
    ) -> SurfacePlan:
        instances: list[SurfaceInstance] = []
        for definition in self._registry.get_definitions(tool_key):
            if surface_kind_filter is not None and definition.kind != surface_kind_filter:
                continue
            provider = self._provider_for(definition)
            if provider is None:
                continue
            instances.extend(provider.expand(definition, tool_key, project_root))
        return SurfacePlan(
            tool_key=tool_key,
            instances=tuple(instances),
            computed_at=computed_at,
        )

    def _provider_for(
        self, definition: SurfaceDefinition
    ) -> ReportingSurfaceProvider | None:
        for provider in self._providers:
            if provider.can_handle(definition):
                return provider
        return None
