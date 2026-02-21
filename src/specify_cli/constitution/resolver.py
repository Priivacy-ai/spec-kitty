"""Constitution-centric governance resolver.

Resolves active governance from constitution selections and validates
selected references against available profile/tool catalogs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.constitution.schemas import AgentProfile
from specify_cli.constitution.sync import (
    load_agents_config,
    load_directives_config,
    load_governance_config,
)

DEFAULT_TEMPLATE_SET = "software-dev-default"
DEFAULT_TOOL_REGISTRY: frozenset[str] = frozenset({"spec-kitty", "git", "python", "pytest", "ruff", "mypy", "poetry"})


class GovernanceResolutionError(ValueError):
    """Raised when constitution selections reference unavailable entities."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        message = "Governance resolution failed:\n- " + "\n- ".join(issues)
        super().__init__(message)


@dataclass(frozen=True)
class GovernanceResolution:
    """Resolved governance activation result."""

    paradigms: list[str]
    directives: list[str]
    agent_profiles: list[AgentProfile]
    tools: list[str]
    template_set: str
    metadata: dict[str, str]
    diagnostics: list[str] = field(default_factory=list)


def resolve_governance(
    repo_root: Path,
    *,
    profile_catalog: dict[str, AgentProfile] | None = None,
    tool_registry: set[str] | None = None,
    fallback_template_set: str = DEFAULT_TEMPLATE_SET,
) -> GovernanceResolution:
    """Resolve active governance from constitution-first selection data."""
    governance = load_governance_config(repo_root)
    agents = load_agents_config(repo_root)
    directives_cfg = load_directives_config(repo_root)
    doctrine = governance.doctrine

    catalog = profile_catalog or {p.agent_key: p for p in agents.profiles}
    selected_profiles = doctrine.selected_agent_profiles
    diagnostics: list[str] = []

    if selected_profiles:
        missing_profiles = sorted(profile for profile in selected_profiles if profile not in catalog)
        if missing_profiles:
            raise GovernanceResolutionError(
                [
                    "Selected agent profiles are not available: " + ", ".join(missing_profiles),
                    "Update constitution selected_agent_profiles or add matching profiles to agents.yaml.",
                ]
            )
        resolved_profiles = [catalog[profile] for profile in selected_profiles]
        profile_source = "constitution"
    else:
        resolved_profiles = list(catalog.values())
        profile_source = "catalog_fallback"
        diagnostics.append("No selected_agent_profiles provided; using full profile catalog fallback.")

    available_tools = tool_registry or set(DEFAULT_TOOL_REGISTRY)
    selected_tools = doctrine.available_tools
    if selected_tools:
        missing_tools = sorted(tool for tool in selected_tools if tool not in available_tools)
        if missing_tools:
            raise GovernanceResolutionError(
                [
                    "Constitution selected unavailable tools: " + ", ".join(missing_tools),
                    "Update constitution available_tools or register those tools in the runtime tool registry.",
                ]
            )
        resolved_tools = list(selected_tools)
        tools_source = "constitution"
    else:
        resolved_tools = sorted(available_tools)
        tools_source = "registry_fallback"
        diagnostics.append("No available_tools selection provided; using runtime tool registry fallback.")

    if doctrine.selected_directives:
        resolved_directives = list(doctrine.selected_directives)
        directives_source = "constitution"
    else:
        resolved_directives = [directive.id for directive in directives_cfg.directives]
        directives_source = "catalog_fallback"

    if doctrine.template_set:
        template_set = doctrine.template_set
        template_set_source = "constitution"
    else:
        template_set = fallback_template_set
        template_set_source = "fallback"
        diagnostics.append(f"Template set not selected in constitution; fallback '{template_set}' applied.")

    return GovernanceResolution(
        paradigms=list(doctrine.selected_paradigms),
        directives=resolved_directives,
        agent_profiles=resolved_profiles,
        tools=resolved_tools,
        template_set=template_set,
        metadata={
            "profile_source": profile_source,
            "tools_source": tools_source,
            "directives_source": directives_source,
            "template_set_source": template_set_source,
        },
        diagnostics=diagnostics,
    )


def collect_governance_diagnostics(
    repo_root: Path,
    *,
    profile_catalog: dict[str, AgentProfile] | None = None,
    tool_registry: set[str] | None = None,
    fallback_template_set: str = DEFAULT_TEMPLATE_SET,
) -> list[str]:
    """Collect diagnostics for planning/runtime checks."""
    try:
        resolution = resolve_governance(
            repo_root,
            profile_catalog=profile_catalog,
            tool_registry=tool_registry,
            fallback_template_set=fallback_template_set,
        )
    except GovernanceResolutionError as exc:
        return exc.issues
    return resolution.diagnostics
