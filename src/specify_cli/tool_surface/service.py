"""High-level assembly for the ``doctor tool-surfaces`` command path.

This module wires the registry, providers, plan builder, status service, and
repair service together so the CLI layer stays thin (C-001: no business logic in
``doctor.py``). The CLI calls :func:`run_tool_surfaces` with parsed flags and
renders the returned :class:`SurfaceReport` / :class:`RepairResult`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .docs import DocsLinter, DocsLintFinding
from .enums import SurfaceKind
from .plan import SurfacePlanBuilder
from .providers.agent_profiles import (
    AgentProfilesProvider,
    agent_profile_definition,
)
from .providers.command_skills import (
    CommandSkillsProvider,
    command_skill_definition,
)
from .providers.managed_skills import (
    ManagedSkillsProvider,
    managed_skill_definition,
)
from .providers.native_config import (
    NativeConfigProvider,
    native_config_definition,
)
from .providers.plugin_bundle import (
    PLUGIN_BUNDLE_TOOL_KEY,
    PluginBundleProvider,
    plugin_manifest_definition,
)
from .providers.protocol import ReportingSurfaceProvider
from .providers.session_presence import (
    SessionPresenceProvider,
    context_file_definition,
    hook_definition,
    rule_definition,
)
from .providers.slash_commands import (
    SlashCommandsProvider,
    slash_command_definition,
)
from .model import SurfacePlan
from .registry import ToolSurfaceRegistry
from .repair import RepairResult, SurfaceRepairService
from .status import SurfaceReport, SurfaceStatusService

# Operator-facing ``--kind`` tokens are kebab-case; map them to SurfaceKind.
# Session-presence kinds also accept the underscore wire value so operators can
# pass ``--kind context_file`` (matching the JSON ``surface_kind``) directly.
_KIND_TOKENS: dict[str, SurfaceKind] = {
    "command-skill": SurfaceKind.COMMAND_SKILL,
    "command-file": SurfaceKind.COMMAND_FILE,
    "context-file": SurfaceKind.CONTEXT_FILE,
    "context_file": SurfaceKind.CONTEXT_FILE,
    "hook": SurfaceKind.HOOK,
    "rule": SurfaceKind.RULE,
    "native-config": SurfaceKind.NATIVE_CONFIG,
    "native_config": SurfaceKind.NATIVE_CONFIG,
    "doctrine-skill": SurfaceKind.DOCTRINE_SKILL,
    "agent-profile": SurfaceKind.AGENT_PROFILE,
    "plugin-manifest": SurfaceKind.PLUGIN_MANIFEST,
    "plugin_manifest": SurfaceKind.PLUGIN_MANIFEST,
}

# Representative tool keys whose surfaces feed bundle projection: skills-invocable
# agents supply command + doctrine skills, ``claude`` supplies native agent
# profiles, and ``vibe`` supplies native config / hooks. Used only to build the
# projection plans during ``--fix`` repair of plugin bundles.
_BUNDLE_SOURCE_TOOL_KEYS: tuple[str, ...] = (
    "codex",
    "claude",
    "copilot",
    "vibe",
)


# Synthetic tool key used to register every built-in path pattern into a single
# registry for docs-contract linting (FR-017). The docs linter validates path
# *shapes* against the contract, independent of which tools are configured.
_DOCS_INDEX_TOOL_KEY = "__docs_contract__"


class UnknownSurfaceKind(ValueError):
    """Raised when an operator passes an unrecognized ``--kind`` token."""


def surface_kind_from_token(token: str) -> SurfaceKind:
    """Map a kebab-case ``--kind`` token to a :class:`SurfaceKind`."""
    try:
        return _KIND_TOKENS[token]
    except KeyError as exc:
        known = ", ".join(sorted(_KIND_TOKENS))
        raise UnknownSurfaceKind(
            f"Unknown surface kind '{token}'. Known kinds: {known}."
        ) from exc


@dataclass(frozen=True)
class ToolSurfaceOutcome:
    """Bundle of the probe report and (optional) repair result."""

    report: SurfaceReport
    repair: RepairResult | None = None

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = self.report.to_json()
        if self.repair is not None:
            payload["repair"] = self.repair.to_json()
        return payload


def build_providers() -> list[ReportingSurfaceProvider]:
    """Return all providers available at this work package."""
    return [
        CommandSkillsProvider(),
        SlashCommandsProvider(),
        SessionPresenceProvider(),
        NativeConfigProvider(),
        ManagedSkillsProvider(),
        AgentProfilesProvider(),
        PluginBundleProvider(),
    ]


def build_registry(tool_keys: Sequence[str]) -> ToolSurfaceRegistry:
    """Register the built-in definitions for each configured tool key."""
    registry = ToolSurfaceRegistry()
    definitions = (
        command_skill_definition(),
        slash_command_definition(),
        context_file_definition(),
        rule_definition(),
        hook_definition(),
        native_config_definition(),
        managed_skill_definition(),
        agent_profile_definition(),
    )
    for tool_key in tool_keys:
        for definition in definitions:
            registry.register_definition(tool_key, definition)
    # Plugin manifests aggregate across all tools; register the definition once
    # under the synthetic bundle key so its provider emits one manifest instance
    # per distribution target (not one per configured tool).
    registry.register_definition(
        PLUGIN_BUNDLE_TOOL_KEY, plugin_manifest_definition()
    )
    return registry


def build_plans_for_bundles(project_root: Path) -> list[SurfacePlan]:
    """Build the canonical surface plans consumed by plugin bundle projection.

    Used by :class:`PluginBundleProvider` during ``--fix`` repair. Excludes the
    plugin-manifest kind itself (a bundle never contains another bundle) and the
    session-presence kinds (project-install surfaces, not bundle components).
    """
    providers = build_providers()
    registry = build_registry(_BUNDLE_SOURCE_TOOL_KEYS)
    builder = SurfacePlanBuilder(registry, providers)
    return builder.build(_BUNDLE_SOURCE_TOOL_KEYS, project_root)


def build_docs_linter() -> DocsLinter:
    """Build a :class:`DocsLinter` backed by every built-in path pattern.

    The linter validates documented path *shapes* against the contract and is
    independent of which tools are configured, so all definitions are registered
    under a single synthetic key (:data:`_DOCS_INDEX_TOOL_KEY`).
    """
    return DocsLinter(build_registry((_DOCS_INDEX_TOOL_KEY,)))


def lint_docs_directory(
    docs_dir: Path, patterns: list[str] | None = None
) -> list[DocsLintFinding]:
    """Lint a docs directory against the tool surface contract (FR-017)."""
    return build_docs_linter().lint_directory(docs_dir, patterns)


def run_tool_surfaces(
    project_root: Path,
    configured_tools: Sequence[str],
    *,
    tool_filter: str | None = None,
    kinds: Sequence[SurfaceKind] | None = None,
    fix: bool = False,
) -> ToolSurfaceOutcome:
    """Build a plan, collect status, and optionally repair."""
    tools = _selected_tools(configured_tools, tool_filter)
    providers = build_providers()
    registry = build_registry(tools)
    builder = SurfacePlanBuilder(registry, providers)
    kind_set = set(kinds) if kinds else None
    # The plugin-manifest surface is registered under a synthetic key (it is not
    # owned by any single configured tool). Add that key to the *plan* tool list
    # so the bundle manifests are probed, but never to ``configured_tools`` so
    # the operator-facing tool roster stays accurate. Skip it when a ``--tool``
    # filter is active (the operator asked for one specific tool) or when no
    # tools are configured (a bundle has nothing to aggregate).
    plan_tools = (
        [*tools, PLUGIN_BUNDLE_TOOL_KEY]
        if tools and tool_filter is None
        else list(tools)
    )
    plans = builder.build(plan_tools, project_root)
    if kind_set is not None:
        plans = _filter_plans_by_kinds(plans, kind_set)
    report = SurfaceStatusService(providers).collect(
        project_root, plans, configured_tools=tools
    )
    if not fix:
        return ToolSurfaceOutcome(report=report)
    repair = SurfaceRepairService(providers).repair(
        project_root, report.surfaces, kinds=kind_set
    )
    refreshed = SurfaceStatusService(providers).collect(
        project_root, plans, configured_tools=tools
    )
    return ToolSurfaceOutcome(report=refreshed, repair=repair)


def _selected_tools(
    configured_tools: Sequence[str], tool_filter: str | None
) -> list[str]:
    if tool_filter is None:
        return list(configured_tools)
    return [t for t in configured_tools if t == tool_filter]


def _filter_plans_by_kinds(
    plans: Sequence[SurfacePlan], kind_set: set[SurfaceKind]
) -> list[SurfacePlan]:
    filtered: list[SurfacePlan] = []
    for plan in plans:
        instances = tuple(
            inst for inst in plan.instances if inst.definition.kind in kind_set
        )
        filtered.append(
            SurfacePlan(
                tool_key=plan.tool_key,
                instances=instances,
                computed_at=plan.computed_at,
            )
        )
    return filtered
