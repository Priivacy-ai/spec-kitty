"""Charter-centric governance resolver.

Resolves active governance from charter selections and validates
selected references against available profile/tool catalogs.

Exports ``DoctrineService`` — an activation-aware wrapper around
:class:`doctrine.service.DoctrineService`.  The wrapper applies per-kind
activation filters from :class:`~charter.pack_context.PackContext` to the
``paradigms``, ``procedures``, and ``agent_profiles`` properties.  All other
properties delegate to the inner doctrine service transparently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from charter.catalog import DoctrineCatalog, load_doctrine_catalog
from charter.reference_resolver import resolve_references_transitively
from charter.schemas import DirectivesConfig, DoctrineSelectionConfig
from charter.sync import (
    load_directives_config,
    load_governance_config,
)

__all__ = [
    "DEFAULT_TOOL_REGISTRY",
    "DoctrineService",
    "GovernanceResolution",
    "GovernanceResolutionError",
    "collect_governance_diagnostics",
    "resolve_governance_for_profile",
    "resolve_mission_steps",
    "resolve_project_governance",
]


if TYPE_CHECKING:
    from doctrine.agent_profiles.profile import AgentProfile
    from doctrine.drg.models import DRGGraph
    from doctrine.paradigms.models import Paradigm
    from doctrine.procedures.models import Procedure
    import doctrine.service as _doctrine_service_module
    from charter.interview import CharterInterview
    from charter.pack_context import PackContext

DEFAULT_TEMPLATE_SET = "software-dev-default"
DEFAULT_TOOL_REGISTRY: frozenset[str] = frozenset({"spec-kitty", "git"})


# ---------------------------------------------------------------------------
# Activation-aware DoctrineService wrapper (Pattern B + C wiring)
# ---------------------------------------------------------------------------


class DoctrineService:
    """Activation-aware wrapper around :class:`doctrine.service.DoctrineService`.

    Applies per-kind activation filters from
    :class:`~charter.pack_context.PackContext` when accessing ``paradigms``,
    ``procedures``, and ``agent_profiles``.  All other attributes delegate
    transparently to the underlying doctrine service.

    Layer rule
    ----------
    This class lives in ``charter.*`` so it can import ``PackContext``
    without violating the ``doctrine ← charter`` dependency direction.
    Callers in ``specify_cli.*`` pass a real :class:`PackContext`; callers
    in ``charter.*`` may pass ``pack_context=None`` for unfiltered access.

    Three-state filtering semantics
    --------------------------------
    * ``pack_context is None`` → no filtering; return all artifacts.
    * ``pack_context.activated_<kind> is None`` → key absent from config;
      return all artifacts (backward-compat / new-project default).
    * ``pack_context.activated_<kind> == frozenset()`` → key present but
      empty; return empty dict (explicit opt-out).
    * ``pack_context.activated_<kind> = {ids}`` → return only those IDs.
    """

    def __init__(
        self,
        _inner: _doctrine_service_module.DoctrineService,
        pack_context: PackContext | None = None,
    ) -> None:
        # Use object.__setattr__ to bypass any potential descriptor magic.
        object.__setattr__(self, "_inner", _inner)
        object.__setattr__(self, "_pack_context", pack_context)

    # ------------------------------------------------------------------
    # Pattern B: flat catalog activation filter (paradigms, procedures)
    # ------------------------------------------------------------------

    @property
    def paradigms(self) -> dict[str, Paradigm]:
        """Return paradigms dict, filtered by ``activated_paradigms`` when set."""
        all_paradigms: dict[str, Paradigm] = {
            item.id: item for item in self._inner.paradigms.list_all()
        }
        pack_ctx: PackContext | None = object.__getattribute__(self, "_pack_context")
        if pack_ctx is not None and pack_ctx.activated_paradigms is not None:
            return {k: v for k, v in all_paradigms.items() if k in pack_ctx.activated_paradigms}
        return all_paradigms

    @property
    def procedures(self) -> dict[str, Procedure]:
        """Return procedures dict, filtered by ``activated_procedures`` when set."""
        all_procedures: dict[str, Procedure] = {
            item.id: item for item in self._inner.procedures.list_all()
        }
        pack_ctx: PackContext | None = object.__getattribute__(self, "_pack_context")
        if pack_ctx is not None and pack_ctx.activated_procedures is not None:
            return {k: v for k, v in all_procedures.items() if k in pack_ctx.activated_procedures}
        return all_procedures

    # ------------------------------------------------------------------
    # Pattern C: direct repository activation filter (agent_profiles)
    # ------------------------------------------------------------------

    @property
    def agent_profiles(self) -> dict[str, AgentProfile]:
        """Return agent profiles dict, filtered by ``activated_agent_profiles`` when set."""
        all_profiles: dict[str, AgentProfile] = {
            p.profile_id: p for p in self._inner.agent_profiles.list_all()
        }
        pack_ctx: PackContext | None = object.__getattribute__(self, "_pack_context")
        if pack_ctx is not None and pack_ctx.activated_agent_profiles is not None:
            return {k: v for k, v in all_profiles.items() if k in pack_ctx.activated_agent_profiles}
        return all_profiles

    # ------------------------------------------------------------------
    # Delegation: all other attributes forwarded to the inner service
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attribute access to the inner doctrine service."""
        inner = object.__getattribute__(self, "_inner")
        return getattr(inner, name)


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
    """Raise GovernanceResolutionError if any selected paradigm is not in the built-in catalog."""
    if not selected_paradigms or "paradigms" not in doctrine_catalog.domains_present:
        return
    missing = sorted(p for p in selected_paradigms if p not in doctrine_catalog.paradigms)
    if missing:
        raise GovernanceResolutionError(
            [
                "Charter selected unavailable paradigm(s): " + ", ".join(missing),
                "Available built-in paradigms: "
                + (", ".join(sorted(doctrine_catalog.paradigms)) or "(none)"),
                "Update charter selected_paradigms to values present in doctrine/paradigms/built-in/.",
            ]
        )


def _resolve_tools_selection(
    doctrine: DoctrineSelectionConfig,
    available_tools: set[str],
    diagnostics: list[str],
) -> tuple[list[str], str]:
    """Resolve tool list as the union of registry baseline and charter selection.

    The runtime tool registry is the *baseline* (tools the framework guarantees
    are present, e.g. ``git``, ``spec-kitty``). The charter's
    ``available_tools`` list is a *declaration* of additional tools the project
    has adopted (e.g. ``pytest``, ``mypy``, ``ruff``). The effective resolved
    set is therefore the **union** of the two sets, not the intersection — a
    charter that declares ``mypy`` does not need the runtime registry to
    pre-register ``mypy`` for the declaration to take effect.

    Returns ``(sorted_tools, source)`` where ``source`` is one of:
      - ``"charter+registry"`` — charter declared one or more tools; the
        resolved set unions them with the registry baseline.
      - ``"registry_only"`` — charter did not declare any tools; the resolved
        set falls back to the registry baseline alone.

    A diagnostic is emitted only when the charter is silent, mirroring the
    pre-union behaviour so operators continue to see the "fallback applied"
    cue when their charter omits the declaration.
    """
    selected_tools = doctrine.available_tools
    if selected_tools:
        unioned = sorted(set(selected_tools) | available_tools)
        added_from_charter = sorted(set(selected_tools) - available_tools)
        if added_from_charter:
            diagnostics.append(
                "Charter declared additional tool(s) beyond the runtime registry: "
                + ", ".join(added_from_charter)
                + "."
            )
        return unioned, "charter+registry"

    diagnostics.append("No available_tools selection provided; using runtime tool registry fallback.")
    return sorted(available_tools), "registry_only"


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
                    "Declare these IDs in directives.yaml or add them to doctrine/directives/built-in/.",
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


def resolve_project_governance(
    repo_root: Path,
    *,
    tool_registry: set[str] | None = None,
    fallback_template_set: str = DEFAULT_TEMPLATE_SET,
) -> GovernanceResolution:
    """Resolve active governance from project + org charter selection data.

    This resolver consumes the charter-mediated **project + org** doctrine
    selections at ``.kittify/charter/governance.yaml`` and
    ``.kittify/charter/directives.yaml``.  It is intentionally *narrow* to
    that surface: it does NOT read ``meta.json`` or per-mission overrides.

    The companion resolver
    :func:`charter.mission_type_profiles.resolve_mission_type_governance`
    handles **mission-type** scoped governance (``meta.json mission_type``
    → built-in governance profile).  The two resolvers compose at the
    prompt-builder layer: the mission-type resolver runs first to fill
    documentation / research / plan defaults, then this resolver fills
    project + org selections on top.  Keeping them as two named functions
    (rather than one umbrella) preserves the FR-011 hard-fail contract on
    the mission-type side and the rich :class:`GovernanceResolution`
    dataclass on the project + org side.

    """
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
    *,
    graph: DRGGraph | None = None,
    repo_root: Path | None = None,
) -> GovernanceResolution:
    """Resolve governance selections for a specific agent profile."""
    normalized_profile_id = profile_id.strip()
    if not normalized_profile_id:
        raise ValueError("Profile ID is required for profile-aware governance resolution.")

    # Pattern C: agent_profiles may be a filtered dict (DoctrineService wrapper)
    # or a repository (raw doctrine.service.DoctrineService / MagicMock in tests).
    agent_profiles_attr = doctrine_service.agent_profiles
    if isinstance(agent_profiles_attr, dict):
        profile = agent_profiles_attr.get(normalized_profile_id)
        if profile is None:
            raise ValueError(f"Agent profile '{normalized_profile_id}' not found.")
    else:
        try:
            profile = agent_profiles_attr.resolve_profile(normalized_profile_id)
        except KeyError as exc:
            raise ValueError(f"Agent profile '{normalized_profile_id}' not found.") from exc

    profile_directives = [ref.code.strip() for ref in profile.directive_references if ref.code.strip()]
    merged_directives = _merge_unique(profile_directives, interview.selected_directives)
    resolution_graph = resolve_references_transitively(
        merged_directives,
        doctrine_service,
        graph=graph,
        repo_root=repo_root,
    )
    diagnostics = [
        f"Unresolved reference: {artifact_type}/{artifact_id}" for artifact_type, artifact_id in resolution_graph.unresolved
    ]

    return GovernanceResolution(
        paradigms=list(interview.selected_paradigms),
        directives=merged_directives,
        tactics=list(resolution_graph.tactics),
        styleguides=list(resolution_graph.styleguides),
        toolguides=list(resolution_graph.toolguides),
        procedures=list(resolution_graph.procedures),
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
        resolution = resolve_project_governance(
            repo_root,
            tool_registry=tool_registry,
            fallback_template_set=fallback_template_set,
        )
    except GovernanceResolutionError as exc:
        return exc.issues
    return resolution.diagnostics


def resolve_mission_steps(
    mission_type_id: str,
    pack_context: PackContext | None = None,
) -> dict[str, Any]:
    """Resolve all mission steps for ``mission_type_id`` with org/project shadowing.

    Uses :class:`charter.mission_steps.MissionStepRepository` (the charter-layer
    facade for FR-037 step resolution) to load the layered step catalog:
    built-in → org packs → project overrides.

    Parameters
    ----------
    mission_type_id:
        The mission type identifier (e.g. ``"software-dev"``).
    pack_context:
        Optional :class:`~charter.pack_context.PackContext` for org and project
        layer resolution.  When ``None``, only the built-in layer is queried.

    Returns
    -------
    dict[str, MissionStep]
        Mapping of ``step_id → MissionStep`` with layered shadowing applied.
        Returns an empty dict when no steps exist for the given mission type.
    """
    from charter.mission_steps import MissionStepRepository  # noqa: PLC0415

    return MissionStepRepository.default().resolve_all_for_mission_type(
        mission_type_id,
        pack_context=pack_context,
    )


def _merge_unique(primary: list[str], secondary: list[str]) -> list[str]:
    merged: list[str] = []
    for value in [*primary, *secondary]:
        item = str(value).strip()
        if item and item not in merged:
            merged.append(item)
    return merged

