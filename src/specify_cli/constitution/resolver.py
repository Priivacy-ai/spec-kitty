"""Constitution-centric governance resolver.

Resolves active governance from constitution selections and validates
selected references against available profile/tool catalogs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.constitution.catalog import load_doctrine_catalog
from specify_cli.constitution.sync import (
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
    tools: list[str]
    template_set: str
    metadata: dict[str, str]
    diagnostics: list[str] = field(default_factory=list)


def resolve_governance(
    repo_root: Path,
    *,
    tool_registry: set[str] | None = None,
    fallback_template_set: str = DEFAULT_TEMPLATE_SET,
) -> GovernanceResolution:
    """Resolve active governance from constitution-first selection data."""
    governance = load_governance_config(repo_root)
    directives_cfg = load_directives_config(repo_root)
    doctrine_catalog = load_doctrine_catalog()
    doctrine = governance.doctrine
    diagnostics: list[str] = []

    selected_paradigms = list(doctrine.selected_paradigms)
    if selected_paradigms and doctrine_catalog.paradigms:
        missing_paradigms = sorted(p for p in selected_paradigms if p not in doctrine_catalog.paradigms)
        if missing_paradigms:
            raise GovernanceResolutionError(
                [
                    "Constitution selected unavailable paradigms: " + ", ".join(missing_paradigms),
                    "Update constitution selected_paradigms to values present in doctrine/paradigms.",
                ]
            )

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

    directive_catalog_ids = {directive.id for directive in directives_cfg.directives}
    if doctrine_catalog.directives:
        directive_catalog_ids.update(doctrine_catalog.directives)

    if doctrine.selected_directives:
        missing_directives = sorted(
            directive for directive in doctrine.selected_directives if directive not in directive_catalog_ids
        )
        if missing_directives:
            raise GovernanceResolutionError(
                [
                    "Constitution selected unavailable directives: " + ", ".join(missing_directives),
                    "Update constitution selected_directives to values present in directives.yaml or doctrine/directives.",
                ]
            )
        resolved_directives = list(doctrine.selected_directives)
        directives_source = "constitution"
    else:
        if directives_cfg.directives:
            resolved_directives = [directive.id for directive in directives_cfg.directives]
        else:
            resolved_directives = sorted(doctrine_catalog.directives)
        directives_source = "catalog_fallback"

    if doctrine.template_set:
        if doctrine_catalog.template_sets and doctrine.template_set not in doctrine_catalog.template_sets:
            raise GovernanceResolutionError(
                [
                    f"Constitution selected unavailable template_set: {doctrine.template_set}",
                    "Update constitution template_set to values available in doctrine missions.",
                ]
            )
        template_set = doctrine.template_set
        template_set_source = "constitution"
    else:
        template_set = fallback_template_set
        template_set_source = "fallback"
        diagnostics.append(f"Template set not selected in constitution; fallback '{template_set}' applied.")

    return GovernanceResolution(
        paradigms=selected_paradigms,
        directives=resolved_directives,
        tools=resolved_tools,
        template_set=template_set,
        metadata={
            "tools_source": tools_source,
            "directives_source": directives_source,
            "template_set_source": template_set_source,
        },
        diagnostics=diagnostics,
    )


def collect_governance_diagnostics(
    repo_root: Path,
    *,
    tool_registry: set[str] | None = None,
    fallback_template_set: str = DEFAULT_TEMPLATE_SET,
) -> list[str]:
    """Collect diagnostics for planning/runtime checks."""
    try:
        resolution = resolve_governance(
            repo_root,
            tool_registry=tool_registry,
            fallback_template_set=fallback_template_set,
        )
    except GovernanceResolutionError as exc:
        return exc.issues
    return resolution.diagnostics
