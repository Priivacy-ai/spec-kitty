"""Plan builder for the tool surface contract bounded context.

:class:`SurfacePlanBuilder` turns the configured tool keys plus the policy
registry into a concrete :class:`SurfacePlan` per tool: it looks up each tool's
:class:`SurfaceDefinition` objects, finds the provider that can handle each, and
expands them into :class:`SurfaceInstance` objects on disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from kernel.clock import now_utc_iso

from .enums import ActivationMode, RequiredPolicy, ToolSurfaceKind
from .model import SurfaceDefinition, SurfaceInstance, SurfacePlan
from .operations import AssessmentInputs, Diagnostic, OwnerAssessment
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
        surface_kind_filter: ToolSurfaceKind | None = None,
    ) -> list[SurfacePlan]:
        """Build one :class:`SurfacePlan` for each configured tool key."""
        computed_at = now_utc_iso()
        return [self._build_one(tool_key, project_root, surface_kind_filter, computed_at) for tool_key in configured_tool_keys]

    def _build_one(
        self,
        tool_key: str,
        project_root: Path,
        surface_kind_filter: ToolSurfaceKind | None,
        computed_at: str,
    ) -> SurfacePlan:
        instances: list[SurfaceInstance] = []
        definitions: list[SurfaceDefinition] = []
        diagnostics: list[Diagnostic] = []
        for definition in self._registry.get_definitions(tool_key):
            if surface_kind_filter is not None and definition.kind != surface_kind_filter:
                continue
            definitions.append(definition)
            provider = self._provider_for(definition)
            if provider is None:
                if (
                    definition.required_policy in {RequiredPolicy.REQUIRED, RequiredPolicy.REPAIRABLE_REQUIRED}
                    and definition.activation_mode != ActivationMode.DISABLED
                ):
                    diagnostics.append(
                        Diagnostic(
                            "missing_provider",
                            definition.provider_key,
                            "error",
                            f"Required {tool_key}/{definition.kind} has no reporting owner",
                        )
                    )
                continue
            instances.extend(provider.expand(definition, tool_key, project_root))
        return SurfacePlan(
            tool_key=tool_key,
            instances=tuple(instances),
            computed_at=computed_at,
            definitions=tuple(definitions),
            diagnostics=tuple(diagnostics),
        )

    def assess(
        self,
        configured_tool_keys: Sequence[str],
        inputs: AssessmentInputs,
        surface_kind_filter: ToolSurfaceKind | None = None,
    ) -> tuple[OwnerAssessment, ...]:
        """Assess selected definitions, retaining missing owners and original statuses.

        Concrete providers migrate separately. Unsupported required owners are
        incomplete here; ordinary reporting/repair continues using its old seam.
        """
        from .repair import SurfaceRepairService
        from .status import SurfaceStatusService

        try:
            plans = self.build(configured_tool_keys, inputs.root.path, surface_kind_filter)
            report = SurfaceStatusService(self._providers).collect(
                inputs.root.path,
                plans,
                configured_tools=configured_tool_keys,
            )
        except (OSError, ValueError) as exc:
            return (OwnerAssessment("inventory", inputs.root, complete=False, diagnostics=(Diagnostic("inventory_unreadable", "inventory", "error", str(exc)),)),)
        return SurfaceRepairService(self._providers).assess(inputs, report.surfaces, plans=plans)

    def _provider_for(self, definition: SurfaceDefinition) -> ReportingSurfaceProvider | None:
        for provider in self._providers:
            if provider.can_handle(definition):
                return provider
        return None
