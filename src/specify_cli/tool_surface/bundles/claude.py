"""Claude Code plugin bundle projection and validation.

Projects the canonical tool surfaces into Claude Code's plugin bundle layout
(``.claude-plugin/``) and validates the result before publication. The bundle
includes command skills, doctrine skills, agent profiles, hooks, and MCP config;
it deliberately **excludes** session-presence files (CLAUDE.md, AGENTS.md, rules
/ steering files), which are project-install surfaces, not bundle components.

**Scope guard (FR-016, C-006):** :meth:`ClaudeCodeBundleProjector.project`
writes only the staging files under the caller-supplied ``output_dir`` and
returns an inert :class:`PluginBundle` descriptor. It never installs, registers,
enables, or publishes the bundle to any marketplace.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..enums import SurfaceKind
from ..findings import (
    BUNDLE_COMPONENT_MISSING,
    SEVERITY_ERROR,
    SurfaceFinding,
    make_finding,
)
from ..model import SurfacePlan
from .model import (
    TARGET_CLAUDE_CODE,
    BundleValidationResult,
    PluginBundle,
)
from .projection import (
    BUNDLE_SURFACE_KINDS,
    bundle_entries_for_plans,
    plugin_manifest_payload,
    write_bundle,
)

# Claude Code plugin layout: manifest lives under ``.claude-plugin/``; hooks and
# MCP config use ``hooks/hooks.json`` and ``.mcp.json`` (NEVER ``settings.json``).
_MANIFEST_DIR = ".claude-plugin"
_MANIFEST_NAME = "plugin.json"

# Per-kind destination prefix inside the Claude Code bundle package.
_CLAUDE_LAYOUT: dict[SurfaceKind, str] = {
    SurfaceKind.COMMAND_SKILL: "skills",
    SurfaceKind.DOCTRINE_SKILL: "skills",
    SurfaceKind.AGENT_PROFILE: "agents",
    SurfaceKind.HOOK: "hooks",
    SurfaceKind.NATIVE_CONFIG: "",
}

# Required surface kinds a complete Claude Code bundle must carry.
_REQUIRED_KINDS: frozenset[SurfaceKind] = frozenset(
    {
        SurfaceKind.COMMAND_SKILL,
        SurfaceKind.DOCTRINE_SKILL,
        SurfaceKind.AGENT_PROFILE,
    }
)


def _agent_filename(profile_id: str) -> str:
    """Claude Code uses plain ``<profile-id>.md`` agent files."""
    return f"{profile_id}.md"


class ClaudeCodeBundleProjector:
    """Project + validate Claude Code plugin bundles (staging only)."""

    distribution_target = TARGET_CLAUDE_CODE
    # Manifest sits under ``.claude-plugin/`` for this target.
    manifest_relative_path = f"{_MANIFEST_DIR}/{_MANIFEST_NAME}"

    def project(
        self,
        plan: Sequence[SurfacePlan],
        project_root: Path,
        output_dir: Path,
    ) -> PluginBundle:
        """Project all bundleable surfaces into the Claude Code layout.

        Writes staging files under ``output_dir`` and returns an inert
        :class:`PluginBundle` descriptor. No install/publish side effect occurs.
        """
        entries = bundle_entries_for_plans(
            plan,
            project_root,
            layout=_CLAUDE_LAYOUT,
            agent_filename=_agent_filename,
            bundle_kinds=BUNDLE_SURFACE_KINDS,
        )
        manifest_rel = self.manifest_relative_path
        manifest = plugin_manifest_payload(self.distribution_target)
        write_bundle(output_dir, entries, manifest_rel, manifest)
        return PluginBundle(
            distribution_target=self.distribution_target,
            entries=entries,
            manifest_path=output_dir / manifest_rel,
        )

    def validate(
        self,
        bundle: PluginBundle,
        required_surface_kinds: set[SurfaceKind] | None = None,
    ) -> BundleValidationResult:
        """Validate that every required surface kind is present in ``bundle``."""
        required = (
            frozenset(required_surface_kinds)
            if required_surface_kinds is not None
            else _REQUIRED_KINDS
        )
        return _validate_bundle(bundle, required)


def _validate_bundle(
    bundle: PluginBundle,
    required: frozenset[SurfaceKind],
) -> BundleValidationResult:
    """Shared validation: report a finding for every missing required kind."""
    present = bundle.kinds()
    missing: list[SurfaceFinding] = []
    warnings: list[str] = []
    for kind in sorted(required - present, key=str):
        missing.append(
            make_finding(
                BUNDLE_COMPONENT_MISSING,
                SEVERITY_ERROR,
                (
                    f"Plugin bundle for {bundle.distribution_target} is missing "
                    f"required surface kind: {kind}"
                ),
                surface_id=f"{bundle.distribution_target}.{kind}",
                details={"distribution_target": bundle.distribution_target},
            )
        )
    if bundle.manifest_path is None:
        warnings.append(
            f"Bundle for {bundle.distribution_target} has no manifest path."
        )
    return BundleValidationResult(
        passed=not missing,
        missing_surfaces=tuple(missing),
        warnings=tuple(warnings),
        distribution_target=bundle.distribution_target,
    )


# Re-export so ``copilot``/``vscode`` projectors can share validation logic.
__all__ = [
    "ClaudeCodeBundleProjector",
    "_validate_bundle",
]
