"""Plan builder for the tool surface contract bounded context.

:class:`SurfacePlanBuilder` turns the configured tool keys plus the policy
registry into a concrete :class:`SurfacePlan` per tool: it looks up each tool's
:class:`SurfaceDefinition` objects, finds the provider that can handle each, and
expands them into :class:`SurfaceInstance` objects on disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from kernel.clock import now_utc_iso

from .enums import ActivationMode, RequiredPolicy, ToolSurfaceKind
from .findings import SurfaceFinding
from .model import SurfaceDefinition, SurfaceInstance, SurfacePlan
from .operations import AssessmentInputs, Diagnostic, OwnerAssessment
from .providers.protocol import ReportingSurfaceProvider
from .registry import ToolSurfaceRegistry
from .status import SurfaceReport, SurfaceStatusService, SurfaceSummary


@dataclass(frozen=True)
class AssessedSurfaces:
    """One guarded inventory's report and immutable owner preparations."""

    report: SurfaceReport
    assessments: tuple[OwnerAssessment, ...]


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
        *,
        kinds: Sequence[ToolSurfaceKind] | None = None,
    ) -> list[SurfacePlan]:
        """Build one :class:`SurfacePlan` for each configured tool key."""
        computed_at = now_utc_iso()
        kind_set = set(kinds) if kinds else None
        if surface_kind_filter is not None:
            kind_set = {surface_kind_filter} if kind_set is None else kind_set & {surface_kind_filter}
        return [self._build_one(tool_key, project_root, kind_set, computed_at) for tool_key in configured_tool_keys]

    def _build_one(
        self,
        tool_key: str,
        project_root: Path,
        kinds: set[ToolSurfaceKind] | None,
        computed_at: str,
    ) -> SurfacePlan:
        instances: list[SurfaceInstance] = []
        definitions: list[SurfaceDefinition] = []
        diagnostics: list[Diagnostic] = []
        for definition in self._registry.get_definitions(tool_key):
            if kinds is not None and definition.kind not in kinds:
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
        *,
        kinds: Sequence[ToolSurfaceKind] | None = None,
        configured_tools: Sequence[str] | None = None,
    ) -> AssessedSurfaces:
        """Assess selected definitions, retaining missing owners and original statuses.

        Concrete providers migrate separately. Unsupported required owners are
        incomplete here; ordinary reporting/repair continues using its old seam.
        """
        from .repair import SurfaceRepairService

        tools = configured_tool_keys if configured_tools is None else configured_tools
        try:
            plans = self.build(configured_tool_keys, inputs.root.path, surface_kind_filter, kinds=kinds)
            report = SurfaceStatusService(self._providers).collect(
                inputs.root.path,
                plans,
                configured_tools=tools,
            )
        except (OSError, ValueError) as exc:
            # No complete inventory exists. Do not present an empty successful
            # report or guess which uncollected surfaces were present/missing.
            report = SurfaceReport(
                ok=False,
                project_root=str(inputs.root.path),
                configured_tools=tuple(tools),
                summary=SurfaceSummary(0, 0, 0, 0, 0, 1),
                surfaces=(),
                findings=(SurfaceFinding("inventory-unreadable", "error", str(exc)),),
            )
            assessment = OwnerAssessment(
                "inventory",
                inputs.root,
                complete=False,
                diagnostics=(Diagnostic("inventory_unreadable", "inventory", "error", str(exc)),),
            )
            return AssessedSurfaces(report, (assessment,))
        return AssessedSurfaces(report, SurfaceRepairService(self._providers).assess(inputs, report.surfaces, plans=plans))

    def _provider_for(self, definition: SurfaceDefinition) -> ReportingSurfaceProvider | None:
        for provider in self._providers:
            if provider.can_handle(definition):
                return provider
        return None
