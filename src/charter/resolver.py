"""Charter-centric governance resolver.

Resolves active governance from charter selections and validates
selected references against available profile/tool catalogs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from charter.catalog import DoctrineCatalog, load_doctrine_catalog
from charter.reference_resolver import resolve_references_transitively
from charter.schemas import DirectivesConfig, DoctrineSelectionConfig
from charter.sync import (
    load_directives_config,
    load_governance_config,
)

if TYPE_CHECKING:
    from doctrine.service import DoctrineService
    from charter.interview import CharterInterview

DEFAULT_TEMPLATE_SET = "software-dev-default"
DEFAULT_TOOL_REGISTRY: frozenset[str] = frozenset({"spec-kitty", "git"})


class GovernanceResolutionError(ValueError):
    """Raised when charter selections reference unavailable entities."""

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
    tactics: list[str] = field(default_factory=list)
    styleguides: list[str] = field(default_factory=list)
    toolguides: list[str] = field(default_factory=list)
    procedures: list[str] = field(default_factory=list)
    profile_id: str | None = None
    role: str | None = None
    diagnostics: list[str] = field(default_factory=list)


def _validate_paradigm_selection(
    selected_paradigms: list[str],
    doctrine_catalog: DoctrineCatalog,
) -> None:
    """Raise GovernanceResolutionError if any selected paradigm is not in the shipped catalog."""
    if not selected_paradigms or "paradigms" not in doctrine_catalog.domains_present:
        return
    missing = sorted(p for p in selected_paradigms if p not in doctrine_catalog.paradigms)
    if missing:
        raise GovernanceResolutionError(
            [
                "Charter selected unavailable paradigm(s): " + ", ".join(missing),
                "Available shipped paradigms: "
                + (", ".join(sorted(doctrine_catalog.paradigms)) or "(none)"),
                "Update charter selected_paradigms to values present in doctrine/paradigms/shipped/.",
            ]
        )


def _resolve_tools_selection(
    doctrine: DoctrineSelectionConfig,
    available_tools: set[str],
    diagnostics: list[str],
) -> tuple[list[str], str]:
    """Resolve tool list from charter selection or registry fallback."""
    selected_tools = doctrine.available_tools
    if selected_tools:
        missing_tools = sorted(tool for tool in selected_tools if tool not in available_tools)
        if missing_tools:
            raise GovernanceResolutionError(
                [
                    "Charter selected unavailable tool(s): " + ", ".join(missing_tools),
                    "Update charter available_tools or register those tools in the runtime tool registry.",
                ]
            )
        return list(selected_tools), "charter"

    diagnostics.append("No available_tools selection provided; using runtime tool registry fallback.")
    return sorted(available_tools), "registry_fallback"


def _resolve_directives_selection(
    doctrine: DoctrineSelectionConfig,
    directives_cfg: DirectivesConfig,
    doctrine_catalog: DoctrineCatalog,
) -> tuple[list[str], str]:
    """Resolve directive list from charter selection, local declarations, or catalog fallback."""
    local_ids = {d.id for d in directives_cfg.directives}
    valid_ids = set(local_ids)
    if doctrine_catalog.directives:
        valid_ids.update(doctrine_catalog.directives)

    if doctrine.selected_directives:
        missing = sorted(d for d in doctrine.selected_directives if d not in valid_ids)
        if missing:
            raise GovernanceResolutionError(
                [
                    "Charter selected unavailable directive(s): " + ", ".join(missing),
                    "Declare these IDs in directives.yaml or add them to doctrine/directives/shipped/.",
                ]
            )
        return list(doctrine.selected_directives), "charter"

    fallback = (
        [d.id for d in directives_cfg.directives]
        if directives_cfg.directives
        else sorted(doctrine_catalog.directives)
    )
    return fallback, "catalog_fallback"


def _resolve_template_set_selection(
    doctrine: DoctrineSelectionConfig,
    doctrine_catalog: DoctrineCatalog,
    fallback_template_set: str,
    diagnostics: list[str],
) -> tuple[str, str]:
    """Resolve template set from charter selection or fallback."""
    if doctrine.template_set:
        if (
            "template_sets" in doctrine_catalog.domains_present
            and doctrine.template_set not in doctrine_catalog.template_sets
        ):
            raise GovernanceResolutionError(
                [
                    f"Charter selected unavailable template_set: '{doctrine.template_set}'",
                    "Available template sets: "
                    + (", ".join(sorted(doctrine_catalog.template_sets)) or "(none)"),
                    "Update charter template_set to a value available in doctrine missions.",
                ]
            )
        return doctrine.template_set, "charter"

    diagnostics.append(f"Template set not selected in charter; fallback '{fallback_template_set}' applied.")
    return fallback_template_set, "fallback"


def resolve_governance(
    repo_root: Path,
    *,
    tool_registry: set[str] | None = None,
    fallback_template_set: str = DEFAULT_TEMPLATE_SET,
) -> GovernanceResolution:
    """Resolve active governance from charter-first selection data."""
    governance = load_governance_config(repo_root)
    directives_cfg = load_directives_config(repo_root)
    doctrine_catalog = load_doctrine_catalog()
    doctrine = governance.doctrine
    diagnostics: list[str] = []

    selected_paradigms = list(doctrine.selected_paradigms)
    _validate_paradigm_selection(selected_paradigms, doctrine_catalog)

    available_tools = tool_registry or set(DEFAULT_TOOL_REGISTRY)
    resolved_tools, tools_source = _resolve_tools_selection(doctrine, available_tools, diagnostics)
    resolved_directives, directives_source = _resolve_directives_selection(doctrine, directives_cfg, doctrine_catalog)
    template_set, template_set_source = _resolve_template_set_selection(
        doctrine, doctrine_catalog, fallback_template_set, diagnostics
    )

    return GovernanceResolution(
        paradigms=selected_paradigms,
        directives=resolved_directives,
        tactics=[],
        styleguides=[],
        toolguides=[],
        procedures=[],
        tools=resolved_tools,
        template_set=template_set,
        metadata={
            "tools_source": tools_source,
            "directives_source": directives_source,
            "template_set_source": template_set_source,
        },
        diagnostics=diagnostics,
    )


def resolve_governance_for_profile(
    profile_id: str,
    role: str | None,
    doctrine_service: DoctrineService,
    interview: CharterInterview,
) -> GovernanceResolution:
    """Resolve governance selections for a specific agent profile."""
    normalized_profile_id = profile_id.strip()
    if not normalized_profile_id:
        raise ValueError("Profile ID is required for profile-aware governance resolution.")

    try:
        profile = doctrine_service.agent_profiles.resolve_profile(normalized_profile_id)
    except KeyError as exc:
        raise ValueError(f"Agent profile '{normalized_profile_id}' not found.") from exc

    profile_directives = [ref.code.strip() for ref in profile.directive_references if ref.code.strip()]
    merged_directives = _merge_unique(profile_directives, interview.selected_directives)
    graph = resolve_references_transitively(merged_directives, doctrine_service)
    diagnostics = [
        f"Unresolved reference: {artifact_type}/{artifact_id}" for artifact_type, artifact_id in graph.unresolved
    ]

    return GovernanceResolution(
        paradigms=list(interview.selected_paradigms),
        directives=merged_directives,
        tactics=list(graph.tactics),
        styleguides=list(graph.styleguides),
        toolguides=list(graph.toolguides),
        procedures=list(graph.procedures),
        tools=list(interview.available_tools),
        template_set=DEFAULT_TEMPLATE_SET,
        metadata={
            "directives_source": "profile+interview",
            "profile_directives_count": str(len(profile_directives)),
            "interview_directives_count": str(len(interview.selected_directives)),
        },
        profile_id=profile.profile_id,
        role=role.strip() if role and role.strip() else None,
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


def _merge_unique(primary: list[str], secondary: list[str]) -> list[str]:
    merged: list[str] = []
    for value in [*primary, *secondary]:
        item = str(value).strip()
        if item and item not in merged:
            merged.append(item)
    return merged
