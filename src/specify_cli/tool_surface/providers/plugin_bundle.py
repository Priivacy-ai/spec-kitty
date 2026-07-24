"""Plugin bundle surface provider.

Wires the plugin bundle projectors (Claude Code, Copilot CLI, VS Code) into a
reporting-layer provider for :data:`ToolSurfaceKind.PLUGIN_MANIFEST`. The provider
*delegates* all projection to the projectors and only translates their results
into surface-contract types -- it never reimplements bundle layout logic.

**Scope guard (FR-016, C-006):** this provider projects bundles into a staging
``output_dir`` and validates them. It performs no auto-install, no plugin
registration, and no marketplace publication. The ``repair`` path re-projects
staging files only; it does not enable or ship anything.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..bundles.claude import ClaudeCodeBundleProjector
from ..bundles.copilot import CopilotBundleProjector
from ..bundles.model import BundleValidationResult, PluginBundle
from ..bundles.vscode import VsCodeBundleProjector
from ..enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    ToolSurfaceKind,
)
from ..findings import (
    BUNDLE_COMPONENT_MISSING,
    PLUGIN_MANIFEST_STALE_PATH,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SurfaceFinding,
    make_finding,
)
from ..model import SurfaceDefinition, SurfaceInstance, SurfacePlan
from ..repair import RepairResult
from ..status import (
    STATE_MISSING,
    STATE_PRESENT,
    STATE_STALE,
    SurfaceStatus,
    _surface_id,
)
from ._registry import SurfaceProviderRegistry, SurfaceRegistration

PROVIDER_KEY = "plugin_bundle"
# Synthetic registry key under which the (tool-agnostic) plugin-manifest surface
# is registered. Plugin bundles aggregate surfaces across all tools, so the
# manifest is not a per-tool surface; ``expand`` only fires for this key.
PLUGIN_BUNDLE_TOOL_KEY = "plugin_bundle"
# Staging output root for projected bundles. Per the WP09 task spec this must be
# a release/staging artifact and never live under ``.kittify/`` or any
# project-managed directory.
_OUTPUT_SUBDIR = "dist/spec-kitty-plugins"
# Definition-level path pattern (root manifest) used only for the registry's
# ``SurfaceDefinition``; the *probed* per-target manifest path is computed from
# each projector's ``manifest_relative_path`` so the Claude Code
# ``.claude-plugin/`` layout is honoured.
_PATH_PATTERN = "dist/spec-kitty-plugins/{target}/plugin.json"
_REPAIR_HINT = "spec-kitty doctor tool-surfaces --kind plugin-manifest --fix"


@runtime_checkable
class BundleProjector(Protocol):
    """Structural type for the bundle projectors this provider drives."""

    distribution_target: str
    manifest_relative_path: str

    def project(
        self,
        plan: Sequence[SurfacePlan],
        project_root: Path,
        output_dir: Path,
    ) -> PluginBundle: ...

    def validate(
        self,
        bundle: PluginBundle,
        required_surface_kinds: set[ToolSurfaceKind] | None = None,
    ) -> BundleValidationResult: ...


def plugin_manifest_definition() -> SurfaceDefinition:
    """Return the built-in plugin-manifest :class:`SurfaceDefinition`."""
    return SurfaceDefinition(
        kind=ToolSurfaceKind.PLUGIN_MANIFEST,
        source_kind=SourceKind.GENERATED,
        install_scope=InstallScope.PLUGIN_BUNDLE,
        path_pattern=_PATH_PATTERN,
        required_policy=RequiredPolicy.OPTIONAL,
        activation_mode=ActivationMode.DISABLED,
        provider_key=PROVIDER_KEY,
        repair_hint=_REPAIR_HINT,
    )


def default_projectors() -> list[BundleProjector]:
    """Return the standard set of staging-only bundle projectors."""
    return [
        ClaudeCodeBundleProjector(),
        CopilotBundleProjector(),
        VsCodeBundleProjector(),
    ]


class PluginBundleProvider:
    """Provider for plugin-manifest (plugin bundle) surfaces."""

    provider_key = PROVIDER_KEY

    def __init__(
        self,
        projectors: Sequence[BundleProjector] | None = None,
        output_subdir: str = _OUTPUT_SUBDIR,
    ) -> None:
        self._projectors = list(projectors) if projectors is not None else (
            default_projectors()
        )
        self._output_subdir = output_subdir

    def can_handle(self, definition: SurfaceDefinition) -> bool:
        return definition.kind == ToolSurfaceKind.PLUGIN_MANIFEST

    def _output_dir(self, project_root: Path, target: str) -> Path:
        return project_root / self._output_subdir / target

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]:
        """Expand into one manifest instance per distribution target.

        Bundles aggregate across all tools, so this only fires for the synthetic
        :data:`PLUGIN_BUNDLE_TOOL_KEY`; any other ``tool_key`` yields nothing,
        preventing a duplicate manifest per configured tool.
        """
        if tool_key != PLUGIN_BUNDLE_TOOL_KEY:
            return []
        instances: list[SurfaceInstance] = []
        for projector in self._projectors:
            manifest_path = (
                self._output_dir(project_root, projector.distribution_target)
                / projector.manifest_relative_path
            )
            instances.append(
                SurfaceInstance(
                    definition=definition,
                    path=manifest_path,
                    exists=manifest_path.exists(),
                    file_hash=None,
                    owner=projector.distribution_target,
                )
            )
        return instances

    def _projector_for(self, target: str) -> BundleProjector | None:
        for projector in self._projectors:
            if projector.distribution_target == target:
                return projector
        return None

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus:
        """Probe the staged bundle manifest and its required components."""
        target = instance.owner
        projector = self._projector_for(target)
        if projector is None:
            return self._stale_status(instance)
        if not instance.path.exists():
            return SurfaceStatus(instance=instance, state=STATE_MISSING)
        bundle = self._reproject(instance, projector)
        result = projector.validate(bundle)
        if not result.passed:
            return self._incomplete_status(instance, result.missing_surfaces)
        return SurfaceStatus(instance=instance, state=STATE_PRESENT)

    def _reproject(
        self, instance: SurfaceInstance, projector: BundleProjector
    ) -> PluginBundle:
        """Re-derive the bundle descriptor for validation without re-writing."""
        # The staged output dir is the manifest's parent (or grandparent for the
        # Claude Code ``.claude-plugin/`` layout). We rebuild the descriptor from
        # the staged tree by listing it; projection is delegated, never inlined.
        output_dir = self._staged_output_dir(instance.path)
        return _descriptor_from_staged(output_dir, projector.distribution_target)

    @staticmethod
    def _staged_output_dir(manifest_path: Path) -> Path:
        # Claude Code: ``<output>/.claude-plugin/plugin.json``.
        if manifest_path.parent.name == ".claude-plugin":
            return manifest_path.parent.parent
        return manifest_path.parent

    @staticmethod
    def _incomplete_status(
        instance: SurfaceInstance,
        missing: Sequence[SurfaceFinding],
    ) -> SurfaceStatus:
        findings = tuple(
            make_finding(
                BUNDLE_COMPONENT_MISSING,
                SEVERITY_ERROR,
                finding.message,
                tool_key=instance.owner,
                surface_id=_surface_id(instance),
                path=instance.path,
                repair_command=_REPAIR_HINT,
            )
            for finding in missing
        )
        return SurfaceStatus(
            instance=instance, state=STATE_MISSING, findings=findings
        )

    @staticmethod
    def _stale_status(instance: SurfaceInstance) -> SurfaceStatus:
        return SurfaceStatus(
            instance=instance,
            state=STATE_STALE,
            findings=(
                make_finding(
                    PLUGIN_MANIFEST_STALE_PATH,
                    SEVERITY_WARNING,
                    (
                        "Plugin manifest references an unknown distribution "
                        f"target: {instance.owner}"
                    ),
                    tool_key=instance.owner,
                    surface_id=_surface_id(instance),
                    path=instance.path,
                ),
            ),
        )

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult:
        """Re-project staging bundles for missing/stale statuses."""
        actionable = [
            s for s in statuses if s.state in (STATE_MISSING, STATE_STALE)
        ]
        if not actionable:
            return RepairResult(dry_run=dry_run)
        if dry_run:
            return RepairResult(
                repaired=tuple(_surface_id(s.instance) for s in actionable),
                dry_run=True,
            )
        return self._project_all(project_root, actionable)

    def _project_all(
        self,
        project_root: Path,
        actionable: Sequence[SurfaceStatus],
    ) -> RepairResult:
        repaired: list[str] = []
        failed: list[str] = []
        plans = self._plans_for_projection(project_root)
        for status in actionable:
            self._project_one(project_root, plans, status, repaired, failed)
        return RepairResult(
            repaired=tuple(repaired), failed=tuple(failed), dry_run=False
        )

    def _project_one(
        self,
        project_root: Path,
        plans: Sequence[SurfacePlan],
        status: SurfaceStatus,
        repaired: list[str],
        failed: list[str],
    ) -> None:
        surface_id = _surface_id(status.instance)
        projector = self._projector_for(status.instance.owner)
        if projector is None:
            failed.append(f"{surface_id}: unknown target {status.instance.owner}")
            return
        output_dir = self._output_dir(project_root, projector.distribution_target)
        try:
            projector.project(plans, project_root, output_dir)
        except OSError as exc:  # surfaced as a failure, never swallowed
            failed.append(f"{surface_id}: {exc}")
            return
        repaired.append(surface_id)

    @staticmethod
    def _plans_for_projection(project_root: Path) -> list[SurfacePlan]:
        """Build the surface plans the projectors consume during repair.

        Imported lazily to avoid a provider <-> service import cycle.
        """
        from ..service import build_plans_for_bundles

        return build_plans_for_bundles(project_root)


def _descriptor_from_staged(output_dir: Path, target: str) -> PluginBundle:
    """Reconstruct a :class:`PluginBundle` descriptor from a staged tree.

    Reads only the staged directory layout to decide which surface kinds are
    present; performs no projection or mutation.
    """
    from ..bundles.model import BundleEntry

    entries: list[BundleEntry] = []
    skills_dir = output_dir / "skills"
    if skills_dir.is_dir() and any(skills_dir.rglob("SKILL.md")):
        for skill in sorted(skills_dir.rglob("SKILL.md")):
            entries.append(
                BundleEntry(
                    surface_kind=ToolSurfaceKind.COMMAND_SKILL,
                    source_path=skill,
                    bundle_relative_path=str(skill.relative_to(output_dir)),
                )
            )
        # Treat staged skills as covering the doctrine-skill kind too: both land
        # under ``skills/`` in every supported layout.
        entries.append(
            BundleEntry(
                surface_kind=ToolSurfaceKind.DOCTRINE_SKILL,
                source_path=skills_dir,
                bundle_relative_path="skills",
            )
        )
    agents_dir = output_dir / "agents"
    if agents_dir.is_dir() and any(agents_dir.iterdir()):
        entries.append(
            BundleEntry(
                surface_kind=ToolSurfaceKind.AGENT_PROFILE,
                source_path=agents_dir,
                bundle_relative_path="agents",
            )
        )
    manifest_path = _staged_manifest_path(output_dir)
    return PluginBundle(
        distribution_target=target,
        entries=tuple(entries),
        manifest_path=manifest_path if manifest_path.exists() else None,
    )


def _staged_manifest_path(output_dir: Path) -> Path:
    claude_manifest = output_dir / ".claude-plugin" / "plugin.json"
    if claude_manifest.exists():
        return claude_manifest
    return output_dir / "plugin.json"


# ---------------------------------------------------------------------------
# Self-registration (fires at import time via providers._discovery)
# ---------------------------------------------------------------------------
SurfaceProviderRegistry.register(
    SurfaceRegistration(
        provider_class=PluginBundleProvider,
        definitions=(plugin_manifest_definition(),),
        kind_tokens={
            "plugin-manifest": ToolSurfaceKind.PLUGIN_MANIFEST,
            "plugin_manifest": ToolSurfaceKind.PLUGIN_MANIFEST,
        },
        synthetic_key=PLUGIN_BUNDLE_TOOL_KEY,
        order=60,
    )
)
