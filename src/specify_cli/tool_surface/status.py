"""Status collection for the tool surface contract bounded context.

:class:`SurfaceStatusService` probes every instance in one or more
:class:`~specify_cli.tool_surface.model.SurfacePlan` objects and assembles a
:class:`SurfaceReport` containing per-surface statuses, flattened findings, and
aggregate summary counts. The report serializes to the JSON shape frozen by
``contracts/doctor-tool-surfaces-output.schema.json``.

This module is owned by WP03. Later work packages (WP04-WP09) extend it to add
new surface kinds; the public ``collect`` contract stays stable.

Plugin-manifest surfaces (WP09) flow through the same generic path: the
:class:`~specify_cli.tool_surface.providers.plugin_bundle.PluginBundleProvider`
owns the kind-specific verdicts -- an incomplete bundle yields a
``bundle-component-missing`` finding at ``error`` severity (state ``missing``),
and an unknown distribution target yields a ``plugin-manifest-stale-path``
finding at ``warning`` severity (state ``stale``). Stale surfaces are tallied by
:meth:`_Accumulator.add` purely through their finding severity, so no new
summary counter is required.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .findings import SurfaceFinding
from .model import SurfaceInstance, SurfacePlan
from .providers.protocol import ReportingSurfaceProvider

# Surface states (stable JSON wire strings, see schema enum).
STATE_PRESENT = "present"
STATE_MISSING = "missing"
STATE_DRIFTED = "drifted"
STATE_STALE = "stale"
STATE_ORPHANED = "orphaned"
STATE_UNSAFE = "unsafe"
STATE_UNSUPPORTED = "unsupported"
STATE_NOT_APPLICABLE = "not_applicable"

_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SurfaceStatus:
    """Result of probing one :class:`SurfaceInstance` against disk state."""

    instance: SurfaceInstance
    state: str
    findings: tuple[SurfaceFinding, ...] = ()

    def to_json(self) -> dict[str, object]:
        """Serialize to a ``SurfaceStatusEntry`` per the output schema."""
        inst = self.instance
        definition = inst.definition
        repair_command = next(
            (f.repair_command for f in self.findings if f.repair_command),
            None,
        )
        return {
            "id": _surface_id(inst),
            "tool": inst.owner,
            "kind": str(definition.kind),
            "provider": definition.provider_key,
            "path": str(inst.path),
            "state": self.state,
            "source_kind": str(definition.source_kind),
            "manifest": None,
            "repair_command": repair_command,
        }


@dataclass(frozen=True)
class SurfaceSummary:
    """Aggregate counts across all probed surfaces."""

    surfaces: int
    present: int
    missing: int
    drifted: int
    warnings: int
    errors: int

    def to_json(self) -> dict[str, int]:
        """Serialize to a ``SurfaceSummary`` per the output schema."""
        return {
            "surfaces": self.surfaces,
            "present": self.present,
            "missing": self.missing,
            "drifted": self.drifted,
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class SurfaceReport:
    """Full output of :meth:`SurfaceStatusService.collect`."""

    ok: bool
    project_root: str
    configured_tools: tuple[str, ...]
    summary: SurfaceSummary
    surfaces: tuple[SurfaceStatus, ...]
    findings: tuple[SurfaceFinding, ...]
    schema_version: int = _SCHEMA_VERSION

    def to_json(self) -> dict[str, object]:
        """Serialize to the full ``doctor tool-surfaces --json`` shape."""
        return {
            "ok": self.ok,
            "schema_version": self.schema_version,
            "project_root": self.project_root,
            "configured_tools": list(self.configured_tools),
            "summary": self.summary.to_json(),
            "surfaces": [s.to_json() for s in self.surfaces],
            "findings": [f.to_json() for f in self.findings],
        }


@dataclass
class _Accumulator:
    """Mutable tally used while folding statuses into a report."""

    statuses: list[SurfaceStatus] = field(default_factory=list)
    findings: list[SurfaceFinding] = field(default_factory=list)
    present: int = 0
    missing: int = 0
    drifted: int = 0
    warnings: int = 0
    errors: int = 0

    def add(self, status: SurfaceStatus) -> None:
        self.statuses.append(status)
        if status.state == STATE_PRESENT:
            self.present += 1
        elif status.state == STATE_MISSING:
            self.missing += 1
        elif status.state == STATE_DRIFTED:
            self.drifted += 1
        for finding in status.findings:
            self.findings.append(finding)
            if finding.severity == "error":
                self.errors += 1
            elif finding.severity == "warning":
                self.warnings += 1


def _surface_id(instance: SurfaceInstance) -> str:
    """Derive a stable surface id from the instance owner and kind/path."""
    if instance.surface_id is not None:
        return instance.surface_id
    suffix = (
        f"{instance.path.parent.name}.SKILL.md"
        if instance.path.name == "SKILL.md" and instance.path.parent.name
        else instance.path.name
    )
    return f"{instance.owner}.{instance.definition.kind}.{suffix}"


class SurfaceStatusService:
    """Probe surface plans and assemble a :class:`SurfaceReport`."""

    def __init__(self, providers: Sequence[ReportingSurfaceProvider]) -> None:
        self._providers = list(providers)

    def _provider_for(
        self, instance: SurfaceInstance
    ) -> ReportingSurfaceProvider | None:
        for provider in self._providers:
            if provider.can_handle(instance.definition):
                return provider
        return None

    def collect(
        self,
        project_root: Path,
        plans: Sequence[SurfacePlan],
        *,
        configured_tools: Sequence[str] | None = None,
    ) -> SurfaceReport:
        """Probe every instance in ``plans`` and return a report."""
        acc = _Accumulator()
        for plan in plans:
            for instance in plan.instances:
                acc.add(self._probe_one(instance))
        tools = (
            tuple(configured_tools)
            if configured_tools is not None
            else tuple(plan.tool_key for plan in plans)
        )
        summary = SurfaceSummary(
            surfaces=len(acc.statuses),
            present=acc.present,
            missing=acc.missing,
            drifted=acc.drifted,
            warnings=acc.warnings,
            errors=acc.errors,
        )
        return SurfaceReport(
            ok=acc.errors == 0,
            project_root=str(project_root),
            configured_tools=tools,
            summary=summary,
            surfaces=tuple(acc.statuses),
            findings=tuple(acc.findings),
        )

    def _probe_one(self, instance: SurfaceInstance) -> SurfaceStatus:
        provider = self._provider_for(instance)
        if provider is None:
            return SurfaceStatus(instance=instance, state=STATE_UNSUPPORTED)
        return provider.probe(instance)
