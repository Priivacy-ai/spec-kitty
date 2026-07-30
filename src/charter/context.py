"""Charter context bootstrap for prompt generation."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol

if TYPE_CHECKING:
    from charter.pack_context import PackContext
    from charter.repository_protocol import ArtifactRepository
    from charter.scope import CharterScope
    from doctrine.drg.models import DRGGraph
    import doctrine.service as _doctrine_service_module

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from charter._catalog_miss import (
    CatalogMissDiagnosis,
    classify_catalog_miss,
    classify_scope_filtered_miss,
    emit_catalog_miss_warning,
    format_catalog_miss_stanza,
)
from charter._doctrine_paths import resolve_project_root
from charter.activations import ActivationEntry, _activation_identity_key
from charter.bundle import CHARTER_MD, CHARTER_YAML
from charter.context_renderers import (
    BUDGET_DEFAULT,
    RenderedSection,
    budget_without_warning_line,
    render_authority_paths,
    render_critical_section_bodies,
    render_critical_section_include,
)
from charter.context_renderers.delivery_table import (
    _ACTION_BUNDLE_DELIVERY_BY_KIND as _ACTION_BUNDLE_DELIVERY_BY_KIND,
    _Gate as _Gate,
    _KindDelivery as _KindDelivery,
    _classify_artifact_urns as _classify_artifact_urns,
    _kind_delivery as _kind_delivery,
    action_bundle_bucket as action_bundle_bucket,
    action_bundle_gate as action_bundle_gate,
)
from charter.context_renderers.fetch_stanza import (
    fetch_stanza_lines as _shared_fetch_stanza_lines,
)
from charter.context_renderers.profile_sections import (
    format_inline_named_body as _format_inline_named_body,
    render_profile_procedures as _render_profile_procedures,
    render_profile_selector_refs as _render_profile_selector_refs,
    render_profile_styleguides as _render_profile_styleguides,
    render_profile_suggested_doctrine as _render_profile_suggested_doctrine,
    render_profile_toolguides as _render_profile_toolguides,
)
from charter.context_renderers.reference_pointers import (
    _REFERENCE_POINTER_FLOOR as _REFERENCE_POINTER_FLOOR,
    _REFERENCE_POINTER_LIMIT as _REFERENCE_POINTER_LIMIT,
    _select_reference_pointers,
)
from charter import progressive_disclosure as _pd
from charter.governance_references import (
    collect_governance_reference_status,
    render_governance_references,
)
from charter.language_scope import infer_repo_languages
from charter.schemas import DirectivesConfig, DoctrineSelectionConfig
from doctrine.agent_profiles import AgentProfile, AgentProfileRepository
from doctrine.spdd_reasons import append_spdd_reasons_guidance, is_spdd_reasons_active
from kernel.atomic import atomic_write

__all__ = [
    "BOOTSTRAP_ACTIONS",
    "CharterContextResult",
    "build_charter_context",
    "build_charter_context_include",
    "build_charter_context_json",
]


_LOGGER = logging.getLogger(__name__)


BOOTSTRAP_ACTIONS: frozenset[str] = frozenset({"specify", "plan", "implement", "review"})
BOOTSTRAP_HEADER = "Charter Context (Bootstrap):"
FIRST_LOAD_GUIDANCE = (
    "  - This is the first load for this action. Use the summary and follow references as needed."
)
POLICY_SUMMARY_HEADER = "Policy Summary:"
NO_POLICY_SUMMARY_MESSAGE = "  - No explicit policy summary section found in charter.md."
REFERENCE_DOCS_HEADER = "Reference Docs:"
NONE_LABEL = "(none)"
KITTIFY_DIRNAME = ".kittify"
#: WP05 (IC-05, display prose-consumer re-point): the display call-sites below
#: consume the shared ``charter.bundle.CHARTER_MD`` constant rather than
#: re-declaring the ``"charter.md"`` filename locally (Sonar S1192 pre-emption
#: the earlier local ``CHARTER_FILENAME = "charter.md"`` duplicate is retired).
MISSING_REFERENCES_MESSAGE = "  - No references manifest found."

_MIN_EFFECTIVE_DEPTH = 2   # minimum depth for bootstrap context (full summary + references)
# WP11 (T059) retired ``_EXTENDED_CONTEXT_DEPTH``: ``depth`` is now purely the
# DRG suggests-hop cap, not also a render-verbosity tier (which gated
# styleguides/toolguides out at every delivered depth).


@dataclass(frozen=True)
class CharterContextResult:
    """Rendered charter context payload."""

    action: str
    mode: str
    first_load: bool
    text: str
    references_count: int
    depth: int


@dataclass(frozen=True)
class _ContextStateBundle:
    """First-load state bundle used while rendering charter context."""

    state_path: Path
    state: dict[str, object]
    first_load: bool
    effective_depth: int


@dataclass(frozen=True)
class _ActionDoctrineBundle:
    """Resolved action doctrine artifacts for bootstrap rendering.

    ``procedure_ids``/``asset_ids`` are WP10 additions (FR-009/FR-011); ``mission``
    and ``service`` are kept though the contract sketch omits them.
    """

    mission: str
    directive_ids: list[str]
    tactic_ids: list[str]
    styleguide_ids: list[str]
    toolguide_ids: list[str]
    procedure_ids: list[str]
    asset_ids: list[str]
    service: _doctrine_service_module.DoctrineService
    # WP15 (progressive disclosure, out-of-map): the resolved DRG and the
    # traversal roots, carried so the JSON entrypoint can render each artefact's
    # ``references[]`` and split the requires-eager / suggests-linked cadence
    # without re-loading and re-filtering the graph.
    merged: DRGGraph | None = None
    roots: tuple[str, ...] = ()
    # WP15/D2a: every URN actually visited while resolving the action node
    # (``resolve_context``'s raw ``artifact_urns``, before the NodeKind
    # delivery table drops never-delivered kinds like ``paradigm``). Carried
    # separately from ``roots`` so progressive disclosure can use excluded-kind
    # pass-through hops as reference sources without widening the
    # requires-eager/inline set (see ``progressive_disclosure.link_references``
    # ``bridge_urns``).
    bridge_urns: tuple[str, ...] = ()


class _DirectiveLike(Protocol):
    """Minimal directive shape used by project directive helpers."""

    id: str


class _DirectivesConfigLike(Protocol):
    """Minimal directives config contract returned by charter.sync."""

    directives: Sequence[_DirectiveLike]


def _resolve_action_bundle(
    repo_root: Path,
    *,
    action: str,
    effective_depth: int,
    org_root: Path | None,
    mission_type: str | None,
    feature_dir: Path | None,
) -> _ActionDoctrineBundle:
    """Resolve the action doctrine bundle with the WP06 org-root fallback
    (extracted WP11/T060 so every-load delivery computes it once, before the
    depth-tier branch, without growing ``build_charter_context``)."""
    effective_org_root = org_root
    if effective_org_root is None:
        for _name, candidate in _enumerate_org_pack_paths(repo_root):
            if candidate.exists():
                effective_org_root = candidate
                break

    from charter.pack_context import PackContext as _PackContext  # noqa: PLC0415

    return _load_action_doctrine_bundle(
        repo_root=repo_root,
        action=action,
        effective_depth=effective_depth,
        org_root=effective_org_root,
        pack_context=_PackContext.from_config(repo_root),
        mission_type=mission_type,
        feature_dir=feature_dir,
    )


def _render_compact_from_bundle(
    repo_root: Path,
    *,
    action: str,
    profile: AgentProfile | None,
    bundle: _ActionDoctrineBundle,
) -> str:
    """Render the widened compact rail (T061): the steady-state render carries
    every delivered kind's ids (FR-010), collapsing only the long-form prose."""
    return _render_compact_governance(
        repo_root,
        directive_ids=list(bundle.directive_ids),
        tactic_ids=list(bundle.tactic_ids),
        styleguide_ids=list(bundle.styleguide_ids),
        toolguide_ids=list(bundle.toolguide_ids),
        procedure_ids=list(bundle.procedure_ids),
        asset_ids=list(bundle.asset_ids),
        profile=profile,
        action=action,
    )


def build_charter_context(
    repo_root: Path,
    *,
    profile: str | None = None,
    action: str,
    mark_loaded: bool = True,
    depth: int | None = None,
    org_root: Path | None = None,
    scope: CharterScope | None = None,
    mission_type: str | None = None,
    feature_dir: Path | None = None,
) -> CharterContextResult:
    """Build charter context by querying the Doctrine Reference Graph.

    Parameters
    ----------
    mission_type:
        Explicit canonical mission type (e.g. ``documentation``) for the action
        doctrine grain.  Takes precedence over ``feature_dir``.  When both are
        ``None`` the action grain is typeless and resolves to an empty bundle —
        never software-dev (FR-003a).  This replaces the retired
        ``template_set``-as-mission-type inference (#883 / FR-002).
    feature_dir:
        The mission's ``kitty-specs/<mission-slug>/`` directory; its
        ``meta.json`` ``mission_type`` field keys the action doctrine grain when
        ``mission_type`` is not given.
    org_root:
        Optional path to the configured org doctrine snapshot.  When provided,
        the three-layer (built-in + org + project) DRG overlay is used and the
        ``DoctrineService`` is constructed with the org layer included.
        Charter-layer callers leave this as ``None``; ``specify_cli`` callers
        resolve the value via :func:`doctrine.drg.org_pack_config.resolve_org_roots`
        and pass it explicitly (preserving the kernel <- doctrine <- charter <-
        specify_cli dependency direction).
    scope:
        Optional :class:`charter.scope.CharterScope` produced by
        :func:`charter.scope_router.build_with_scope`.  When provided, the
        effective ``repo_root`` for this call is ``scope.root`` so the
        nearest-enclosing charter is used instead of the repository root.
        This satisfies FR-010 spec wording: callers MAY pass a pre-resolved
        scope or rely on the :func:`build_with_scope` convenience wrapper.
        When ``scope`` is ``None`` the argument is ignored and *repo_root* is
        used as-is (backward-compatible with all existing callers).

        MEDIUM-2 (post-merge remediation cycle 1): added as a keyword-only
        pass-through so the FR-010 spec contract "SHALL accept an optional
        scope parameter" is honoured without breaking the WP07 call-site
        signature.
    """
    # MEDIUM-2: honour the scope kwarg by overriding repo_root when provided.
    if scope is not None:
        repo_root = scope.root
    profile_record = _load_agent_profile(profile, repo_root) if profile else None

    # WP06 / FR-015 — surface a loud diagnostic when the consumer's
    # config references an org pack whose snapshot is missing on disk.
    # We render the diagnostic into the bootstrap text (rather than
    # raising) so the prompt body carries the actionable error to the
    # operator even when the caller does not catch the exception.
    missing_pack_diagnostic = _missing_pack_diagnostic(repo_root)

    from charter.sync import ensure_charter_bundle_fresh

    sync_result = ensure_charter_bundle_fresh(repo_root)
    canonical_root = sync_result.canonical_root if sync_result and sync_result.canonical_root else repo_root

    normalized = action.strip().lower()
    charter_path = canonical_root / CHARTER_MD

    def _augment(text: str) -> str:
        if missing_pack_diagnostic:
            return missing_pack_diagnostic + "\n\n" + text
        return text

    if normalized not in BOOTSTRAP_ACTIONS:
        effective_depth = depth if depth is not None else 1
        return CharterContextResult(
            action=normalized,
            mode="compact",
            first_load=False,
            text=_augment(
                _render_compact_governance(repo_root, profile=profile_record, action=normalized)
            ),
            references_count=0,
            depth=effective_depth,
        )

    state_bundle = _prepare_context_state(repo_root, normalized, depth)

    if not charter_path.exists():
        text = (
            "Charter Context:\n"
            "  - Charter file not found at `.kittify/charter/charter.md`.\n"
            "  - Run `spec-kitty charter interview` then `spec-kitty charter generate`."
        )
        return CharterContextResult(
            action=normalized,
            mode="missing",
            first_load=state_bundle.first_load,
            text=_augment(text),
            references_count=0,
            depth=state_bundle.effective_depth,
        )

    # WP11 (T060/B-3) — compute the bundle BEFORE the depth-tier branch so it
    # is delivered on EVERY load; the old order returned compact before it existed.
    doctrine_bundle = _resolve_action_bundle(
        repo_root,
        action=normalized,
        effective_depth=state_bundle.effective_depth,
        org_root=org_root,
        mission_type=mission_type,
        feature_dir=feature_dir,
    )

    if state_bundle.effective_depth < _MIN_EFFECTIVE_DEPTH:
        # Steady-state load: deliver via the widened compact rail (T061/FR-010).
        if mark_loaded and state_bundle.first_load:
            _mark_action_loaded(state_bundle.state, state_bundle.state_path, normalized)
        return CharterContextResult(
            action=normalized,
            mode="compact",
            first_load=state_bundle.first_load,
            text=_augment(
                _render_compact_from_bundle(
                    repo_root,
                    action=normalized,
                    profile=profile_record,
                    bundle=doctrine_bundle,
                )
            ),
            references_count=0,
            depth=state_bundle.effective_depth,
        )

    charter_content = charter_path.read_text(encoding="utf-8")
    summary = _extract_policy_summary(charter_content)
    references = _load_references(canonical_root)
    doctrine_selection = _load_doctrine_selection(repo_root)
    text = _render_bootstrap_text(
        charter_path=charter_path,
        action=normalized,
        summary=summary,
        doctrine_bundle=doctrine_bundle,
        references=references,
        profile=profile_record,
        repo_root=repo_root,
        doctrine_selection=doctrine_selection,
        charter_content=charter_content,
    )

    if mark_loaded and state_bundle.first_load:
        _mark_action_loaded(state_bundle.state, state_bundle.state_path, normalized)

    return CharterContextResult(
        action=normalized,
        mode="bootstrap",
        first_load=state_bundle.first_load,
        text=_augment(text),
        references_count=len(references),
        depth=state_bundle.effective_depth,
    )


def build_charter_context_include(
    repo_root: Path,
    selector: str,
    *,
    action: str | None = None,
    org_root: Path | None = None,
) -> str:
    """Render one fetch-deferred governance selector.

    The selector kind is routed through the canonical
    :meth:`~doctrine.artifact_kinds.ArtifactKind.from_operator_token` resolver
    (WP01), so hyphenated operator tokens such as ``agent-profile`` and
    ``mission-step-contract`` resolve to their canonical underscore kinds
    without a per-surface kind table (R-009 / CC-4). The two non-artifact
    selectors — ``section`` (a charter heading) and ``artifact`` (the
    best-effort activation selector) — are handled before the canonical
    resolver. ``template:<mission>/<name>`` resolves through WP18's
    :func:`doctrine.template_catalog.resolve_template_by_id` (FR-034).

    Unknown selector kinds fail closed with the canonical vocabulary error
    raised by :meth:`ArtifactKind.from_operator_token` (no silent fallback).
    """
    from doctrine.artifact_kinds import (
        ArtifactKind,
        MissionTypeNotAnArtifactKind,
    )

    kind, separator, identifier = selector.partition(":")
    kind = kind.strip().lower()
    identifier = identifier.strip()
    if not separator or not kind or not identifier:
        raise ValueError("Expected --include selector in '<kind>:<id>' form.")

    if kind == "section":
        canonical_root = _bundle_root_for_json(repo_root)
        charter_path = canonical_root / CHARTER_MD
        if not charter_path.exists():
            raise ValueError("No charter.md found for section selector.")
        charter_content = charter_path.read_text(encoding="utf-8")
        section = render_critical_section_include(
            charter_content,
            identifier,
            action=action.strip().lower() if action else None,
        )
        if section is None:
            raise ValueError(f"No charter section found for selector '{selector}'.")
        return str(section)

    org_roots = [org_root] if org_root is not None else None

    if kind == "artifact":
        service = _build_doctrine_service(repo_root, org_roots=org_roots)
        return _render_generic_artifact_include(service, identifier)

    # Route every other kind through the canonical operator-token resolver so
    # hyphenated tokens (``agent-profile``) and canonical underscore tokens
    # (``agent_profile``) both resolve, and unknown tokens fail closed with the
    # shared vocabulary error (no second kind enumeration here — CC-4).
    try:
        resolved_kind = ArtifactKind.from_operator_token(kind)
    except MissionTypeNotAnArtifactKind as exc:
        raise ValueError(
            f"--include does not support the 'mission-type' selector "
            f"(selector {selector!r}); mission types are not addressable "
            "governance artifacts."
        ) from exc

    if resolved_kind is ArtifactKind.TEMPLATE:
        return _render_template_include(repo_root, identifier, selector)

    canonical_kind = resolved_kind.value
    if canonical_kind == ArtifactKind.AGENT_PROFILE.value:
        # FR-016: the agent-profile fetch path must inherit the charter
        # activation gate, so it (and only it) uses the activation-aware
        # service. Every other include kind stays on the unwrapped service.
        gated_service = _build_activation_aware_doctrine_service(
            repo_root, org_roots=org_roots
        )
        # For a kind with a registered renderer (agent_profile has one),
        # _render_doctrine_artifact_include renders the activated profile or
        # raises ("No agent_profile found ...") for a gated/missing one — it
        # never returns None here, so a direct return is sufficient (no dead
        # fall-through branch to guard).
        artifact_result = _render_doctrine_artifact_include(
            gated_service, canonical_kind, identifier
        )
        if artifact_result is None:
            raise ValueError(f"No {canonical_kind} found for selector '{selector}'.")
        return artifact_result

    service = _build_doctrine_service(repo_root, org_roots=org_roots)
    if canonical_kind == ArtifactKind.DIRECTIVE.value:
        return _render_directive_include(service.directives, identifier, selector)
    if canonical_kind == ArtifactKind.TACTIC.value:
        return _render_tactic_include(service.tactics, identifier, selector)
    artifact = _render_doctrine_artifact_include(service, canonical_kind, identifier)
    if artifact is not None:
        return artifact

    raise ValueError(f"Unsupported --include selector kind '{kind}'.")


def _render_template_include(
    repo_root: Path,
    identifier: str,
    selector: str,
) -> str:
    """Render a ``template:<mission>/<name>`` selector via WP18 (FR-034).

    Resolves the mission-qualified template ID through the doctrine
    5-tier chain (:func:`doctrine.template_catalog.resolve_template_by_id`)
    and renders the resolved template file's content. The project root
    (the directory containing ``.kittify/``) is supplied as data so the
    project-scoped override/legacy tiers participate in resolution.

    Fails closed on malformed pack configuration: a
    :class:`charter.pack_context.CharterPackConfigError` raised while
    resolving the project root is re-raised rather than swallowed, matching
    WP12's fail-closed contract for the context entry point.
    """
    from doctrine.resolver import ResolutionTier
    from doctrine.template_catalog import TierRoot, resolve_template_by_id

    project_root = resolve_project_root(repo_root)

    tier_roots = [
        TierRoot(
            tier=ResolutionTier.PACKAGE_DEFAULT,
            missions_root=_default_missions_root(),
            project_dir=project_root,
        )
    ]
    try:
        result = resolve_template_by_id(identifier, tier_roots=tier_roots)
    except FileNotFoundError as exc:
        raise ValueError(
            f"No template found for selector '{selector}'."
        ) from exc
    except ValueError as exc:
        raise ValueError(
            f"Malformed template selector '{selector}': {exc}"
        ) from exc

    try:
        content = result.path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"Template for selector '{selector}' could not be read: {exc}"
        ) from exc

    return "\n".join(
        [
            f"Template {identifier} (tier: {result.tier.value}):",
            content.rstrip("\n"),
        ]
    )


def _default_missions_root() -> Path:
    """Return the doctrine-bundled missions root (PACKAGE_DEFAULT tier)."""
    from doctrine.missions import MissionTemplateRepository

    return MissionTemplateRepository.default_missions_root()


def _render_directive_include(directives: ArtifactRepository[Any], identifier: str, selector: str) -> str:
    """Render a directive selector for ``--include``.

    Takes the ``directives`` repository directly (not the whole service) —
    that is the only attribute this renderer needs (WP04 typing pass).
    """

    directive_id = _format_profile_directive_code(identifier)
    directive = directives.get(directive_id)
    if directive is None:
        raise ValueError(f"No directive found for selector '{selector}'.")
    title = getattr(directive, "title", directive_id)
    return "\n".join(
        [
            f"Directive {directive_id}: {title}",
            *_format_inline_directive_body(directive),
            *_format_full_artifact_payload_body(directive),
        ]
    )


def _render_tactic_include(tactics: ArtifactRepository[Any], identifier: str, selector: str) -> str:
    """Render a tactic selector for ``--include``.

    Takes the ``tactics`` repository directly (not the whole service) — that
    is the only attribute this renderer needs (WP04 typing pass).
    """

    tactic = tactics.get(identifier)
    if tactic is None:
        raise ValueError(f"No tactic found for selector '{selector}'.")
    name = getattr(tactic, "name", identifier)
    return "\n".join(
        [
            f"Tactic {identifier}: {name}",
            *_format_inline_tactic_body(tactic),
            *_format_full_artifact_payload_body(tactic),
        ]
    )


def _render_generic_artifact_include(
    service: _doctrine_service_module.DoctrineService, identifier: str
) -> str:
    """Resolve a best-effort ``artifact:<id>`` selector emitted by activations."""

    from doctrine.artifact_kinds import _NON_AUGMENTATION_ELIGIBLE_KINDS, ArtifactKind

    # Derive the candidate kinds from the canonical ArtifactKind set rather
    # than re-declaring a parallel tuple (R-009 / CC-4). Members of the
    # canonical ``_NON_AUGMENTATION_ELIGIBLE_KINDS`` set are excluded: both
    # ``TEMPLATE`` (mission-qualified ``<mission>/<name>`` IDs) and ``ASSET``
    # (loose-contract kind, FR-005/FR-011) are not addressable by a bare
    # ``artifact:<id>`` probe. This is the single canonical exclusion set
    # (WP06) — no private single-member ``is not TEMPLATE`` check may be
    # re-declared here or elsewhere in the charter cascade.
    matches: list[tuple[str, str]] = []
    for candidate_kind in (
        member.value
        for member in ArtifactKind
        if member not in _NON_AUGMENTATION_ELIGIBLE_KINDS
    ):
        selector = f"{candidate_kind}:{identifier}"
        try:
            rendered: str | None
            if candidate_kind == "directive":
                rendered = _render_directive_include(service.directives, identifier, selector)
            elif candidate_kind == "tactic":
                rendered = _render_tactic_include(service.tactics, identifier, selector)
            else:
                rendered = _render_doctrine_artifact_include(
                    service, candidate_kind, identifier
                )
        except ValueError:
            continue
        if rendered is not None:
            matches.append((candidate_kind, rendered))

    if not matches:
        raise ValueError(f"No artifact found for selector 'artifact:{identifier}'.")
    if len(matches) > 1:
        kinds = ", ".join(kind for kind, _text in matches)
        raise ValueError(
            f"Ambiguous artifact selector 'artifact:{identifier}' matched kinds: {kinds}."
        )
    return matches[0][1]


def _render_doctrine_artifact_include(
    service: object,
    kind: str,
    identifier: str,
) -> str | None:
    """Render non-directive/tactic doctrine artifacts addressed by ``--include``."""

    renderers = {
        "paradigm": (
            "paradigms",
            "Paradigm",
            "name",
            _format_inline_paradigm_body,
        ),
        "styleguide": (
            "styleguides",
            "Styleguide",
            "title",
            _format_inline_styleguide_body,
        ),
        "toolguide": (
            "toolguides",
            "Toolguide",
            "title",
            _format_inline_toolguide_body,
        ),
        "procedure": (
            "procedures",
            "Procedure",
            "name",
            _format_inline_procedure_body,
        ),
        "agent_profile": (
            "agent_profiles",
            "Agent profile",
            "name",
            _format_inline_agent_profile_body,
        ),
        "mission_step_contract": (
            "mission_step_contracts",
            "Mission step contract",
            "action",
            _format_inline_step_contract_body,
        ),
    }
    renderer = renderers.get(kind)
    if renderer is None:
        return None

    repo_attr, label, title_attr, body_formatter = renderer
    repo = getattr(service, repo_attr, None)
    artifact = repo.get(identifier) if repo is not None else None
    if artifact is None:
        raise ValueError(f"No {kind} found for selector '{kind}:{identifier}'.")
    title = getattr(artifact, title_attr, identifier)
    return "\n".join(
        [
            f"{label} {identifier}: {title}",
            *body_formatter(artifact),
            *_format_full_artifact_payload_body(artifact),
        ]
    )


def _prepare_context_state(
    repo_root: Path,
    action: str,
    depth: int | None,
) -> _ContextStateBundle:
    """Resolve first-load state and effective context depth."""
    state_path = repo_root / KITTIFY_DIRNAME / "charter" / "context-state.json"
    state = _load_state(state_path)
    actions_val = state.get("actions", {})
    first_load = action not in actions_val if isinstance(actions_val, dict) else True
    if depth is not None:
        effective_depth = depth
    elif first_load:
        effective_depth = _MIN_EFFECTIVE_DEPTH
    else:
        effective_depth = 1
    return _ContextStateBundle(
        state_path=state_path,
        state=state,
        first_load=first_load,
        effective_depth=effective_depth,
    )


# ---------------------------------------------------------------------------
# NodeKind delivery table (B-1) — relocated verbatim to
# ``context_renderers/delivery_table.py`` (WP04, single-owner, no-net-growth
# for this file). ``_Gate``, ``_KindDelivery``, ``_ACTION_BUNDLE_DELIVERY_BY_KIND``,
# ``_kind_delivery``, ``action_bundle_bucket``, ``action_bundle_gate`` and
# ``_classify_artifact_urns`` are imported below so they stay resolvable as
# ``charter.context`` attributes for the three external test importers
# (``tests/charter/test_action_bundle_delivery.py``,
# ``tests/charter/test_context_display_charter_md.py``,
# ``tests/doctrine/drg/test_unknown_kind_fails_loudly.py``).
# ---------------------------------------------------------------------------


#: Artifact-kind suffixes for which an org pack may declare a
#: ``required_<kind>`` list (mirrors
#: :data:`specify_cli.doctrine.org_charter.REQUIRED_KIND_FIELDS`).  Kept
#: as a local constant inside the charter layer so we can do the
#: cross-pack union without importing ``specify_cli`` (preserves the
#: kernel <- doctrine <- charter <- specify_cli dependency direction).
_REQUIRED_KIND_FIELDS: tuple[str, ...] = (
    "directives",
    "tactics",
    "paradigms",
    "styleguides",
    "toolguides",
    "procedures",
    "agent_profiles",
    "mission_step_contracts",
)


def _enumerate_org_pack_paths(repo_root: Path) -> list[tuple[str, Path]]:
    """Return configured ``(pack_name, local_path)`` pairs.

    The shared parser lives in ``doctrine.drg.org_pack_config`` so charter,
    DRG composition, and specify_cli registry paths consume one config
    contract.
    """
    try:
        from doctrine.drg.org_pack_config import load_pack_registry  # noqa: PLC0415
    except ImportError:
        return []
    try:
        registry = load_pack_registry(repo_root)
    except Exception:  # noqa: BLE001 - context rendering stays best-effort
        _LOGGER.debug(
            "load_pack_registry raised while enumerating org pack paths for %s; "
            "treating as no configured packs.",
            repo_root,
            exc_info=True,
        )
        return []
    return [(pack.name, pack.effective_root(repo_root)) for pack in registry.packs]


def _missing_pack_diagnostic(repo_root: Path) -> str | None:
    """Return a human-readable diagnostic when an org pack is missing on disk.

    Per FR-015 (Mission B WP06), a consumer whose ``.kittify/config.yaml``
    references a pack whose ``local_path`` does not exist on disk MUST
    surface a loud diagnostic at context-resolution time.  Returns ``None``
    when every configured pack exists (or no packs are configured).

    The diagnostic is rendered into the bootstrap text by
    :func:`build_charter_context` so the operator sees the error in the
    prompt body — exactly what ``test_case_2_consumer_without_fetched_pack_fails_loudly``
    pins.
    """
    missing: list[tuple[str, Path]] = []
    for name, local_path in _enumerate_org_pack_paths(repo_root):
        if not local_path.exists():
            missing.append((name, local_path))
    if not missing:
        return None
    lines = [
        "Charter Context Error:",
        "  - Doctrine pack(s) referenced in .kittify/config.yaml do NOT exist on disk:",
    ]
    for name, local_path in missing:
        lines.append(f"    - pack `{name}`: local_path `{local_path}` does not exist")
    lines.append(
        "  - Run `spec-kitty doctrine fetch --pack <name>` to populate the pack, "
        "or remove the entry from .kittify/config.yaml."
    )
    return "\n".join(lines)


def _iter_org_charter_docs(repo_root: Path) -> list[tuple[str, dict[str, Any]]]:
    """Return ``(pack_name, raw_dict)`` for every pack's parsed ``org-charter.yaml``.

    Single shared raw-rescan reader (FR-006) consumed by BOTH
    :func:`_read_org_required_selections` (``required_<kind>``, the
    established precedent) and :func:`_read_org_activations`
    (``activations:``, WP01) so the fix does not leave a third
    hand-rolled rescan copy — the exact duplication class that caused
    #2365.

    Packs whose ``org-charter.yaml`` is absent, unreadable, or does not
    parse to a YAML mapping are silently skipped here — the loud
    diagnostic for a missing *pack directory* is produced by
    :func:`_missing_pack_diagnostic` upstream. This reader only decides
    "can I hand the caller a parsed document"; whether individual
    entries within that document are then valid is each caller's own
    concern (e.g. :func:`_read_org_activations` raises on a malformed
    ``activations:`` entry per FR-004 — a different failure class than
    "the YAML file itself didn't parse").
    """
    yaml = YAML(typ="safe")
    docs: list[tuple[str, dict[str, Any]]] = []
    for name, pack_path in _enumerate_org_pack_paths(repo_root):
        charter_path = pack_path / "org-charter.yaml"
        if not charter_path.exists():
            continue
        try:
            raw = yaml.load(charter_path.read_text(encoding="utf-8"))
        except (OSError, YAMLError, ValueError):
            continue
        if not isinstance(raw, dict):
            continue
        docs.append((name, raw))
    return docs


def _read_org_required_selections(repo_root: Path) -> dict[str, list[str]]:
    """Union every org pack's ``required_<kind>`` across packs.

    Reads each configured pack's parsed ``org-charter.yaml`` (via the
    shared :func:`_iter_org_charter_docs` reader) and returns a
    ``{kind: [ids...]}`` map covering the 8 kinds listed in
    :data:`_REQUIRED_KIND_FIELDS`.  Union preserves first-seen order
    across packs (declaration-order precedence, matching the merge
    semantics of :func:`specify_cli.doctrine.org_charter.load_org_charter_policies`).
    """
    out: dict[str, list[str]] = {kind: [] for kind in _REQUIRED_KIND_FIELDS}
    for _name, raw in _iter_org_charter_docs(repo_root):
        for kind in _REQUIRED_KIND_FIELDS:
            value = raw.get(f"required_{kind}")
            if not isinstance(value, list):
                continue
            for item in value:
                token = str(item).strip()
                if token and token not in out[kind]:
                    out[kind].append(token)
    return out


def _load_doctrine_selection(repo_root: Path) -> DoctrineSelectionConfig:
    """Return the charter's :class:`DoctrineSelectionConfig` for *repo_root*.

    Best-effort lookup: any failure (missing governance.yaml, parse
    error, unexpected exception) collapses to a default-constructed
    :class:`DoctrineSelectionConfig`.  This keeps the resolver hot path
    resilient (NFR-005) so a malformed governance file never crashes
    prompt rendering — the authority-paths block will simply lack
    charter-declared entries.

    Mission B WP06: after loading the charter-level selection, this
    helper UNIONs every org pack's ``required_<kind>`` into the matching
    ``selected_<kind>`` field.  Org-required artifacts therefore reach
    the prompt without the operator having to mirror them in the
    project's own ``governance.yaml`` (FR-003 / FR-008).  The union is
    non-destructive: project-selected ids are preserved and org-required
    additions append in first-seen order across packs.
    """

    from charter.sync import load_governance_config

    try:
        governance = load_governance_config(repo_root)
        selection = governance.doctrine
    except Exception:  # noqa: BLE001 — best-effort governance load
        selection = DoctrineSelectionConfig()

    org_required = _read_org_required_selections(repo_root)
    if not any(org_required.values()):
        return selection

    # Merge per-kind, preserving project-selected order and appending new
    # org-required ids.  Pydantic models default to mutable list fields
    # so in-place ``extend`` is fine; we still rebuild the model via
    # ``model_copy`` to keep the original instance immutable for callers
    # that hold a reference.
    updates: dict[str, list[str]] = {}
    for kind in _REQUIRED_KIND_FIELDS:
        field_name = f"selected_{kind}"
        current = list(getattr(selection, field_name, []) or [])
        additions = [token for token in org_required[kind] if token not in current]
        if additions:
            updates[field_name] = current + additions
    if not updates:
        return selection
    return selection.model_copy(update=updates)


def _load_action_doctrine_bundle(
    *,
    repo_root: Path,
    action: str,
    effective_depth: int,
    org_root: Path | None = None,
    pack_context: PackContext | None = None,
    mission_type: str | None = None,
    feature_dir: Path | None = None,
) -> _ActionDoctrineBundle:
    """Load DRG-backed action doctrine artifacts for bootstrap rendering.

    The mission type keying off which the ``action:<mission_type>/<action>``
    node is resolved comes from ``meta.json`` (via ``feature_dir``) or an
    explicit ``mission_type`` argument — NEVER from the project-level
    ``template_set`` (the #883 leak, WP04 / FR-002).  ``template_set`` is
    retained solely for template-file selection (C-004) and no longer proxies
    the mission type on this governance path.

    A typeless mission (no ``mission_type`` and no ``meta.json`` type — the
    genuinely mission-less callers) degrades to an EMPTY action bundle; it is
    never resolved as software-dev (FR-003a).
    """
    from charter._drg_helpers import load_validated_graph
    from charter.drg import filter_graph_by_activation
    from charter.mission_type_profiles import resolve_mission_type_key
    from doctrine.drg.loader import DRGLoadError
    from doctrine.drg.query import resolve_context

    doctrine_selection = _load_doctrine_selection(repo_root)
    resolved_type = resolve_mission_type_key(
        mission_type=mission_type, feature_dir=feature_dir
    )
    project_directives = {_normalize_directive_id(d) for d in doctrine_selection.selected_directives}
    selected_tactics = {t for t in doctrine_selection.selected_tactics if t}
    selected_paradigms = {p for p in doctrine_selection.selected_paradigms if p}

    # The DRG load honours the built-in + org + project three-layer overlay
    # (WP07 T034; charter-internal callers pass org_root=None for two layers).
    # A project authoring a doctrine artifact without a sibling ``*.graph.yaml``
    # raises ``DRGLoadError``; that is orthogonal to charter-level selection
    # rendering, so we collapse it to an empty bundle and log a WARNING (WP04).
    ids_by_slot: Mapping[str, tuple[str, ...]] = {}
    merged_graph: DRGGraph | None = None
    roots: tuple[str, ...] = ()
    bridge_urns: tuple[str, ...] = ()
    # A typeless mission has no action:<type>/<action> node to resolve; skip the
    # DRG action resolution entirely so no doctrine is inferred (FR-003a).
    if resolved_type is not None:
        try:
            merged = load_validated_graph(repo_root, org_root=org_root)
            # FR-032, FR-035 (WP08): apply activation filter before resolving context.
            if pack_context is not None:
                merged = filter_graph_by_activation(merged, pack_context)
            action_urn = f"action:{resolved_type}/{action}"
            resolved = resolve_context(merged, action_urn, depth=effective_depth)
            ids_by_slot = _classify_artifact_urns(
                resolved.artifact_urns,
                merged,
                project_directives,
                selected_tactics,
                selected_paradigms,
            )
            # WP15: carry the graph + traversal roots for progressive disclosure.
            # Roots mirror ``_classify_artifact_urns``: the action node plus the
            # project/selected start URNs whose requires-closure is delivered eager.
            merged_graph = merged
            roots = (
                action_urn,
                *(f"directive:{d}" for d in project_directives),
                *(f"tactic:{t}" for t in selected_tactics),
                *(f"paradigm:{p}" for p in selected_paradigms),
            )
            # D2a: ``resolve_context``'s raw ``artifact_urns`` can reach a
            # delivered (slotted) artefact only through a node of an
            # excluded kind (e.g. ``paradigm:brownfield-onboarding``
            # ``suggests``-> ``tactic:test-to-system-reconstruction``, with no
            # paradigm selected). ``_classify_artifact_urns`` correctly never
            # delivers the paradigm itself, but that leaves it out of both
            # ``roots`` and ``delivered`` — so ``link_references`` can never
            # walk its outbound edge and the tactic ends up delivered yet
            # neither inlined nor named, silently. Carrying the raw resolved
            # set as bridge URNs restores it as a reference source without
            # making it delivered or inline.
            bridge_urns = tuple(resolved.artifact_urns)
        except DRGLoadError as exc:
            _LOGGER.warning(
                "DRG action resolution skipped for %s/%s: %s. "
                "Charter-level selections still render.",
                resolved_type,
                action,
                exc,
            )

    return _ActionDoctrineBundle(
        mission=resolved_type or "",
        directive_ids=list(ids_by_slot.get("directives", ())),
        tactic_ids=list(ids_by_slot.get("tactics", ())),
        styleguide_ids=list(ids_by_slot.get("styleguides", ())),
        toolguide_ids=list(ids_by_slot.get("toolguides", ())),
        procedure_ids=list(ids_by_slot.get("procedures", ())),
        asset_ids=list(ids_by_slot.get("assets", ())),
        service=_build_doctrine_service(repo_root, org_roots=[org_root] if org_root else None),
        merged=merged_graph,
        roots=roots,
        bridge_urns=bridge_urns,
    )


def _append_guidelines_lines(lines: list[str], mission: str, action: str) -> None:
    """Append action guidelines to lines, silently skipping on any error."""
    from doctrine.missions import MissionTemplateRepository

    try:
        repo = MissionTemplateRepository.default()
        result = repo.get_action_guidelines(mission, action)
        if result is not None:
            content = result.content.strip()
            if content:
                lines.append("  Guidelines:")
                for guideline_line in content.splitlines():
                    lines.append(f"    {guideline_line}")
    except Exception:  # noqa: BLE001, S110
        pass


class _ActionRenderRow(NamedTuple):
    """One Action Doctrine render row."""

    heading: str
    ids_attr: str  # attribute on _ActionDoctrineBundle
    service_attr: str  # repository/dict on the service (absent for assets here)
    title_attr: str
    summary_attr: str | None
    # D2c: the progressive-disclosure kind prefix (matches
    # ``progressive_disclosure``'s URN kind, e.g. "directive"/"tactic") for the
    # four kinds WP15's JSON payload already disclosure-cadences. ``None`` for
    # procedure/asset, which stay always-inline here (unchanged, pre-D2c
    # behaviour) — they are not part of the WP15 disclosure-cadenced kind set.
    progressive_kind: str | None = None


#: The Action Doctrine render order. Iterating it (not hand-written per-kind
#: calls) makes "the render emits every kind the bundle carries" one statement
#: (FR-009/B-2): a kind flipped into a slot renders as soon as it has a row.
#: WP11 (T059) retired the ``extended`` depth gate — every row renders on the
#: bootstrap load; the compact rail carries the same kinds as ids (T061).
_ACTION_RENDER_ROWS: tuple[_ActionRenderRow, ...] = (
    _ActionRenderRow("Directives", "directive_ids", "directives", "title", "intent", "directive"),
    _ActionRenderRow("Tactics", "tactic_ids", "tactics", "name", "purpose", "tactic"),
    _ActionRenderRow("Styleguides", "styleguide_ids", "styleguides", "title", None, "styleguide"),
    _ActionRenderRow("Toolguides", "toolguide_ids", "toolguides", "title", None, "toolguide"),
    _ActionRenderRow("Procedures", "procedure_ids", "procedures", "name", "purpose"),
    _ActionRenderRow("Assets", "asset_ids", "assets", "title", None),
)


def _render_action_doctrine_lines(
    lines: list[str],
    doctrine_bundle: _ActionDoctrineBundle,
    *,
    repo_root: Path | None,
) -> None:
    """Emit every kind the bundle resolves under the Action Doctrine heading.

    Assets have no repository on this lane, so ``getattr(service, "assets",
    None)`` is ``None`` and :func:`_extend_named_artifact_lines` emits bare ids.

    D2c: directive/tactic/styleguide/toolguide entries follow the same
    requires-eager / suggests-linked cadence WP15 already applies to the
    ``--json`` payload (:func:`progressive_disclosure.requires_closure`) —
    an entry outside the roots' requires-closure renders as a fetch +
    when-doing stanza instead of its full verbatim body. Before this, every
    resolved id always rendered its full body regardless of cadence, so a
    grain reached mostly through ``suggests`` (the norm — see WP15's own
    ADR) produced an Action Doctrine block large enough to blow the NFR-001
    token budget on its own; the (smaller, but budget-substitutable)
    profile-citation and charter-section blocks paid for it by being swapped
    away first, silently dropping profile-cited directives like DIRECTIVE_032
    even though swapping them never actually closed the budget gap.
    """
    service = doctrine_bundle.service
    all_action_ids: list[str] = [
        artifact_id
        for row in _ACTION_RENDER_ROWS
        for artifact_id in getattr(doctrine_bundle, row.ids_attr)
    ]
    org_source_map = (
        _build_action_org_source_map(repo_root, all_action_ids)
        if repo_root is not None and all_action_ids
        else {}
    )
    inline_urns: frozenset[str] = (
        frozenset(_pd.requires_closure(doctrine_bundle.merged, doctrine_bundle.roots))
        if doctrine_bundle.merged is not None
        else frozenset()
    )
    for row in _ACTION_RENDER_ROWS:
        _extend_named_artifact_lines(
            lines,
            row.heading,
            getattr(doctrine_bundle, row.ids_attr),
            getattr(service, row.service_attr, None),
            row.title_attr,
            row.summary_attr,
            org_source_map=org_source_map,
            progressive_kind=row.progressive_kind,
            inline_urns=inline_urns,
        )


def _render_bootstrap_text(
    *,
    charter_path: Path,
    action: str,
    summary: list[str],
    doctrine_bundle: _ActionDoctrineBundle,
    references: list[dict[str, str]],
    profile: AgentProfile | None = None,
    repo_root: Path | None = None,
    doctrine_selection: DoctrineSelectionConfig | None = None,
    charter_content: str = "",
) -> str:
    """Render the full bootstrap charter context text."""

    service = doctrine_bundle.service
    lines: list[str] = [
        BOOTSTRAP_HEADER,
        f"  - Source: {charter_path}",
        FIRST_LOAD_GUIDANCE,
        "",
        POLICY_SUMMARY_HEADER,
    ]
    if summary:
        for item in summary[:8]:
            lines.append(f"  - {item}")
    else:
        lines.append(NO_POLICY_SUMMARY_MESSAGE)

    # WP04 (FR-003) — authority paths block, between Policy Summary and the
    # action-critical bodies (resolved-context anchor order, data-model.md §3).
    authority_block = ""
    if repo_root is not None and doctrine_selection is not None:
        authority_block = render_authority_paths(repo_root, doctrine_selection)
    if authority_block:
        lines.append("")
        lines.append(authority_block)

    reference_block = ""
    if repo_root is not None and doctrine_selection is not None:
        reference_block = render_governance_references(
            repo_root,
            doctrine_selection.governance_references,
        )
    if reference_block:
        lines.append("")
        lines.append(reference_block)

    # WP04 (FR-001) — action-critical charter section bodies; an absent heading
    # emits a fetch stanza so the agent still has a recovery path.
    section_block = render_critical_section_bodies(charter_content, action)
    if section_block:
        lines.append("")
        lines.append(section_block)

    profile_block = _render_profile_sections(profile, service)
    if profile_block:
        lines.append("")
        lines.append(profile_block)

    # WP04 (FR-005) — charter-level global selection rendering: the 5-kind block
    # surfaces every ``DoctrineSelectionConfig.selected_<kind>`` (with org provenance).
    selection_block = _render_selection_block(
        doctrine_selection, service, repo_root=repo_root
    )
    if selection_block:
        lines.append("")
        lines.append(selection_block)

    # WP04 T023 — activation-registry hook (FR-007); renderer body is WP05's
    # surface (``charter._activation_render``), this only ships the call site.
    activation_block = _render_activation_block(
        doctrine_selection,
        repo_root,
        service,
        mission_type=doctrine_bundle.mission,
        action=action,
    )
    if activation_block:
        lines.append("")
        lines.append(activation_block)

    lines.append("")
    lines.append(f"Action Doctrine ({action}):")
    _render_action_doctrine_lines(lines, doctrine_bundle, repo_root=repo_root)

    _append_guidelines_lines(lines, doctrine_bundle.mission, action)

    if is_spdd_reasons_active(charter_path.parent.parent.parent):
        append_spdd_reasons_guidance(lines, doctrine_bundle.mission, action)

    lines.append("")
    lines.append(REFERENCE_DOCS_HEADER)
    from charter.catalog import resolve_doctrine_root  # noqa: PLC0415 — lazy, avoids import cycle

    selected_references = _select_reference_pointers(
        references, action, resolve_doctrine_root()
    )
    if selected_references:
        for reference, resolved_path in selected_references:
            ref_id = reference.get("id", "unknown")
            title = reference.get("title", "")
            lines.append(f"  - {ref_id}: {title} ({resolved_path})")
    else:
        lines.append(MISSING_REFERENCES_MESSAGE)
    text = "\n".join(lines)

    # WP05 (NFR-001) — token budget enforcement.  When the bootstrap
    # render fits inside the budget the text passes through unchanged;
    # otherwise the longest substitutable section bodies are swapped
    # for fetch + when-doing stanzas until the budget holds.  Authority
    # paths and core doctrine stay inline (substitutable=False).
    return _enforce_token_budget(
        text,
        action=action,
        profile_block=profile_block,
        section_block=section_block,
    )


def _enforce_token_budget(
    text: str,
    *,
    action: str,
    profile_block: str,
    section_block: str,
    budget: int = BUDGET_DEFAULT,
) -> str:
    """Apply the NFR-001 token budget to *text* (WP05).

    When ``len(text) <= budget`` the text is returned unchanged.  Over
    budget, the largest substitutable governance block is swapped for
    the canonical fetch + when-doing stanza, and the substitution loop
    iterates over the remaining blocks (longest first) until the budget
    holds or no swap candidates remain.

    Substitution preference (in order of preferred swap):
      1. action-critical section bodies (`section_block`) — largest
      2. profile-cited directives + tactics (`profile_block`)

    Authority paths and core action-doctrine sections stay inline (they
    are small + critical to the prompt's actionable surface, per
    WP05 NFR-001 spec).
    """

    if len(text) <= budget:
        return text

    # Decompose the rendered ``text`` into a fixed-section model and run
    # the substitution loop.  We do this by replacing whole blocks in
    # the original text rather than re-joining, so the surrounding
    # structure (Charter Context header, Policy Summary, Action
    # Doctrine, References) stays byte-identical.
    candidates: list[RenderedSection] = []
    if section_block:
        candidates.append(
            RenderedSection(
                section_id="action-critical-sections",
                header="",
                body=section_block,
                selector=f"section:critical-{action}",
                when_doing_clause=(
                    "need to consult the action-critical charter sections"
                ),
                substitutable=True,
                indent="  ",
            )
        )
    if profile_block:
        candidates.append(
            RenderedSection(
                section_id="profile-cited-sections",
                header="",
                body=profile_block,
                selector="section:profile-citations",
                when_doing_clause=(
                    "need to consult the profile-cited directives and tactics"
                ),
                substitutable=True,
                indent="  ",
            )
        )

    if not candidates:
        # Nothing safe to substitute — return the original text so we
        # don't silently drop content.  The caller (the WP prompt
        # builder) sees over-budget text rather than missing content;
        # operators will spot the regression via the measurement script.
        return text

    # Sort longest first, ties broken on section_id for determinism.
    candidates.sort(key=lambda sec: (-len(sec.body), sec.section_id))

    current_text = text
    swapped_ids: list[str] = []
    for section in candidates:
        if len(current_text) <= budget_without_warning_line(len(swapped_ids), budget):
            break
        stanza = "\n".join(
            _shared_fetch_stanza_lines(
                section.selector,
                section.when_doing_clause,
                indent=section.indent,
            )
        )
        # Replace only the first occurrence — the block is rendered
        # exactly once in the bootstrap text.
        new_text = current_text.replace(section.body, stanza, 1)
        if new_text == current_text:
            # Defensive: block not found (renderer drift).  Skip it.
            continue
        current_text = new_text
        swapped_ids.append(section.section_id)

    if swapped_ids:
        from charter.context_renderers.token_budget import warning_line

        current_text = f"{current_text}\n\n{warning_line(len(swapped_ids), budget)}"

    return current_text


#: When-doing clause for a linked (suggests-reached) Action Doctrine entry —
#: mirrors the profile-citation renderers' own clause (D2c,
#: ``_render_profile_directives`` / ``_render_profile_tactics``) so the two
#: surfaces read consistently.
_ACTION_DOCTRINE_LINK_WHEN = "are about to apply a code change"


def _extend_named_artifact_lines(
    lines: list[str],
    heading: str,
    artifact_ids: list[str],
    repository: ArtifactRepository[Any] | None,
    title_attr: str,
    summary_attr: str | None,
    org_source_map: dict[str, str] | None = None,
    progressive_kind: str | None = None,
    inline_urns: frozenset[str] = frozenset(),
) -> None:
    """Append formatted artifact lines when the bucket is non-empty.

    When *org_source_map* is provided, each artifact contributed by an org
    pack receives a ``(source: org:<pack>)`` suffix (Option B — additive only
    when an org pack is present, preserving NFR-001 byte-stability when no
    org packs are configured).

    *repository* may be ``None`` when a delivered kind has no repository wired
    on this layer (e.g. assets on the WP10 base): every id then renders in the
    bare-id form, so the ids still reach the output (FR-009/B-2).

    D2c: when *progressive_kind* is set (directive/tactic/styleguide/
    toolguide), an entry outside *inline_urns* (WP15's requires-closure —
    the eager set) renders its id + title header line plus a fetch +
    when-doing stanza in place of the verbatim summary/body, matching the
    cadence WP15 already applies to the ``--json`` payload. *progressive_kind*
    ``None`` (procedure/asset) always renders the full verbatim line,
    unchanged from pre-D2c behaviour.
    """
    if not artifact_ids:
        return

    formatted: list[str] = []
    for artifact_id in artifact_ids:
        suffix = _provenance_suffix(artifact_id, org_source_map)
        artifact = repository.get(artifact_id) if repository is not None else None
        if artifact is None:
            formatted.append(f"    - {artifact_id}{suffix}")
            continue
        title = getattr(artifact, title_attr)
        is_linked = (
            progressive_kind is not None
            and f"{progressive_kind}:{artifact_id}" not in inline_urns
        )
        if is_linked:
            formatted.append(f"    - {artifact_id}: {title}{suffix}")
            formatted.extend(
                _render_fetch_stanza(
                    selector=f"{progressive_kind}:{artifact_id}",
                    when_clause=_ACTION_DOCTRINE_LINK_WHEN,
                )
            )
            continue
        summary = getattr(artifact, summary_attr) if summary_attr else None
        if isinstance(summary, str) and summary:
            formatted.append(f"    - {artifact_id}: {title} — {summary}{suffix}")
        else:
            formatted.append(f"    - {artifact_id}: {title}{suffix}")

    lines.append(f"  {heading}:")
    lines.extend(formatted)


def _build_action_org_source_map(
    repo_root: Path,
    artifact_ids: list[str],
) -> dict[str, str]:
    """Build an ``artifact_id → pack_name`` map for action-doctrine artifacts contributed by org packs.

    Uses :func:`charter.drg.load_org_drg` (WP06) to read the configured
    organisation-tier DRG fragments and maps each fragment node id to the
    pack name that contributed it.  The resulting map is consumed by
    :func:`_extend_named_artifact_lines` to append ``(source: org:<pack>)``
    suffixes.

    Returns ``{}`` when:
    * no org packs are configured (NFR-001 byte-stability — no diff to 23-fixture suite)
    * ``load_org_drg`` raises any exception (best-effort; action doctrine still renders)
    * no artifact IDs are provided

    Option B per T036: stanzas carry ``source:`` ONLY when an org pack
    contributes the artifact.  Shipped-only artifacts carry no suffix,
    preserving the existing plain-text rendering for all 23 governance-
    contract fixtures.

    Implementation note: we read provenance directly from the ``OrgDRGFragment``
    node list rather than calling ``merge_three_layers`` and inspecting the
    merged graph.  The merge monkey-patches a ``source`` sidecar attribute onto
    DRGEdge objects that already have a ``source`` field (the URN endpoint), which
    causes Pydantic validation failures when the returned DRGGraph is reconstructed
    with the real built-in graph (hundreds of edges).  Reading fragment nodes directly
    is simpler and sufficient for building the id → pack_name map.
    """
    if not artifact_ids:
        return {}

    try:
        from charter.drg import load_org_drg  # noqa: PLC0415 — lazy import keeps charter boundary clean
    except ImportError:
        return {}

    try:
        org_fragments = load_org_drg(repo_root)
    except Exception:  # noqa: BLE001 — best-effort; never crash action doctrine rendering
        return {}

    if not org_fragments:
        # No org packs → NFR-001 preserved (byte-identical output for 23 fixtures).
        return {}

    # Build the map directly from fragment node ids.
    # Each fragment node has an ``id`` (e.g. ``"sox-controls"``) and the fragment
    # has a ``pack_name`` (e.g. ``"example-org"``).
    artifact_id_set = set(artifact_ids)
    source_map: dict[str, str] = {}
    for fragment in org_fragments:
        pack_name = fragment.pack_name
        for node in fragment.nodes:
            if node.id in artifact_id_set and node.id not in source_map:
                source_map[node.id] = pack_name

    return source_map


def _build_doctrine_service(
    repo_root: Path,
    *,
    org_roots: list[Path] | None = None,
) -> _doctrine_service_module.DoctrineService:
    """Build a DoctrineService for the given repo root.

    The project-root candidate list (in priority order):
    1. ``.kittify/doctrine/``  — Phase 3 synthesis target (FR-009 / T025).
    2. ``src/doctrine/``       — code-local built-in-layer path.
    3. ``doctrine/``           — flat fallback.

    Discovery is conditional on directory presence so legacy (pre-synthesis)
    projects see byte-identical behaviour (R-2 mitigation).

    Cross-reference: ``compiler._default_doctrine_service`` uses the same
    ``resolve_project_root`` helper from ``charter._doctrine_paths``.

    WP07: callers in ``specify_cli`` may supply explicit *org_roots* (a list
    of org doctrine snapshot paths) so the resulting service includes the
    configured org layer in provenance tracking.  Charter-internal callers
    omit the argument and get the built-in-plus-project baseline.
    """
    from doctrine.service import DoctrineService
    from charter.catalog import resolve_doctrine_root

    doctrine_root = resolve_doctrine_root()
    project_root = resolve_project_root(repo_root)
    # Only pass ``org_roots`` when it carries paths so charter-internal
    # callers see byte-identical kwargs (preserves existing test stubs and
    # downstream constructors that may not declare the parameter).
    if org_roots:
        return DoctrineService(
            built_in_root=doctrine_root,
            project_root=project_root,
            active_languages=infer_repo_languages(repo_root),
            org_roots=org_roots,
        )
    return DoctrineService(
        built_in_root=doctrine_root,
        project_root=project_root,
        active_languages=infer_repo_languages(repo_root),
    )


def _build_activation_aware_doctrine_service(
    repo_root: Path, *, org_roots: list[Path] | None = None
) -> object:
    """Build an *activation-aware* doctrine service for ``--include`` fetches.

    FR-016: ``charter context --include agent-profile:<id>`` must inherit the
    charter activation gate so that a non-activated profile is treated as a
    structured miss rather than silently rendered. This is the **scoped**
    counterpart to :func:`_build_doctrine_service`: it builds the same inner
    service (identical kwargs) and wraps it with the activation-aware
    :class:`charter.resolver.DoctrineService`, supplying a freshly constructed
    :class:`~charter.pack_context.PackContext` for *repo_root*.

    Only the ``agent-profile`` include branch routes through this helper; the
    other five callers of :func:`_build_doctrine_service` are deliberately left
    on the unwrapped service so their return type and behaviour are unchanged.

    Single builder contract (R5): the service is ALWAYS wrapped, even when
    ``activated_agent_profiles is None``. The wrapper's three-state filter
    treats ``None`` as "admit all", so the unrestricted case stays byte-identical
    in *behaviour* to the legacy fetch path while giving both activation-service
    builders one contract — ``_inner`` is always valid and ``.agent_profiles``
    is always a gated ``dict``. This matches
    :func:`specify_cli.doctrine_service_factory.build_activation_aware_doctrine_service`,
    which also wraps unconditionally.
    """
    from charter.pack_context import PackContext
    from charter.resolver import DoctrineService as ActivationAwareDoctrineService

    inner = _build_doctrine_service(repo_root, org_roots=org_roots)
    pack_context = PackContext.from_config(repo_root)
    return ActivationAwareDoctrineService(inner, pack_context=pack_context)


def _normalize_directive_id(raw: str) -> str:
    """Normalise a directive slug like '024-locality-of-change' -> 'DIRECTIVE_024'.

    If the raw value already looks like DIRECTIVE_NNN, return as-is.
    """
    if re.match(r"^DIRECTIVE_\d+$", raw):
        return raw
    match = re.match(r"^(\d+)", raw)
    if match:
        number = match.group(1).zfill(3)
        return f"DIRECTIVE_{number}"
    return raw.upper()


# ---------------------------------------------------------------------------
# WP13 (FR-013 / FR-014, SC-006) — reference-block distribution + resolution.
#
# WP04 (mission doctrine-delivery-activation): relocated verbatim to
# ``context_renderers/reference_pointers.py`` (single-owner, no-net-growth
# for this file). ``_select_reference_pointers`` is imported below for the
# call site in ``_render_bootstrap_text``; ``_REFERENCE_POINTER_FLOOR`` /
# ``_REFERENCE_POINTER_LIMIT`` are imported too so they stay resolvable as
# ``charter.context`` attributes for ``tests/charter/test_reference_block.py``.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Profile-driven rendering (WP03 — FR-002 / FR-004)
# ---------------------------------------------------------------------------


_PROFILE_DIRECTIVES_HEADER_TPL = "Profile-Cited Directives ({profile_id}):"
_PROFILE_TACTICS_HEADER_TPL = "Profile-Cited Tactics ({profile_id}):"
_PROFILE_INLINE_BODY_LIMIT_CHARS = 2_400


# Shared, repository-cached store. ``AgentProfileRepository()`` reads YAML
# at construction; we cache the default instance so per-call cost in the
# resolver is a dict lookup (NFR-002 budget).
_DEFAULT_AGENT_PROFILE_REPO: AgentProfileRepository | None = None
# Per-repo cache of the **charter-activation-aware** profile map (org + project
# + built-in, gated by ``activated_agent_profiles``). Populated only when the
# repo declares org packs, so the no-org-packs path stays byte-identical to the
# built-in-only fast path above (NFR-001). Keyed by resolved ``repo_root``.
_ACTIVATION_AWARE_PROFILE_MAPS: dict[Path, dict[str, AgentProfile]] = {}


def _default_agent_profile_repository() -> AgentProfileRepository:
    """Return a process-wide cached **built-in-only** :class:`AgentProfileRepository`.

    The repository is constructed lazily on first call and reused for the
    lifetime of the interpreter. Tests that need a clean repository can
    reset the cache via :func:`_reset_agent_profile_cache`. This is the
    no-org-packs fast path; org-aware resolution flows through
    :func:`_activation_aware_profile_map` instead.
    """
    global _DEFAULT_AGENT_PROFILE_REPO
    if _DEFAULT_AGENT_PROFILE_REPO is None:
        _DEFAULT_AGENT_PROFILE_REPO = AgentProfileRepository()
    return _DEFAULT_AGENT_PROFILE_REPO


def _reset_agent_profile_cache() -> None:
    """Clear the cached profile stores (test hook)."""
    global _DEFAULT_AGENT_PROFILE_REPO
    _DEFAULT_AGENT_PROFILE_REPO = None
    _ACTIVATION_AWARE_PROFILE_MAPS.clear()


def _existing_org_roots(repo_root: Path) -> list[Path]:
    """Return on-disk org-pack roots declared in ``.kittify/config.yaml``.

    Best-effort: a missing/corrupt config yields an empty list so the caller
    falls back to the built-in-only fast path. Imports stay charter→doctrine
    (never charter→specify_cli) so the layer rule holds.
    """
    try:
        from doctrine.drg.org_pack_config import resolve_org_roots  # noqa: PLC0415
    except ImportError:
        return []
    try:
        return [root for root in resolve_org_roots(repo_root) if root.exists()]
    except Exception:  # noqa: BLE001 — context rendering stays best-effort
        return []


def _profiles_dict_from_service(service: object) -> dict[str, AgentProfile]:
    """Return the activation-aware service's pre-gated ``{id: profile}`` map.

    Single builder contract (R5): every activation-service builder now ALWAYS
    wraps, so ``service.agent_profiles`` is the wrapper's already-gated ``dict``.
    The empty fallback defends against a service that exposes no mapping.
    """
    attr = getattr(service, "agent_profiles", None)
    return dict(attr) if isinstance(attr, dict) else {}


def _activation_aware_profile_map(
    repo_root: Path, org_roots: list[Path]
) -> dict[str, AgentProfile]:
    """Return (and cache) the activation-gated profile map for ``repo_root``.

    Reuses the in-module :func:`_build_activation_aware_doctrine_service`
    (the FR-016 precedent) so the ``activated_agent_profiles`` three-state
    gate is honoured — never re-implemented — and threads the discovered org
    roots in as **data** (no ``specify_cli`` import, preserving the layer
    rule).
    """
    cached = _ACTIVATION_AWARE_PROFILE_MAPS.get(repo_root)
    if cached is not None:
        return cached
    service = _build_activation_aware_doctrine_service(repo_root, org_roots=org_roots)
    profile_map = _profiles_dict_from_service(service)
    _ACTIVATION_AWARE_PROFILE_MAPS[repo_root] = profile_map
    return profile_map


def _resolve_agent_profile_record(
    profile_id: str, repo_root: Path | None
) -> AgentProfile | None:
    """Resolve *profile_id*, threading charter activation when org packs exist.

    ``repo_root is None`` (callers with no repo context) and "no org packs
    declared" both take the built-in-only fast path (byte-identical to the
    pre-mission behaviour, NFR-001). Org packs present → activation-aware map
    so a dispatched, **activated** org profile resolves (FR-005) while a
    de-activated one returns ``None`` (NFR-002).
    """
    if repo_root is None:
        return _default_agent_profile_repository().get(profile_id)
    org_roots = _existing_org_roots(repo_root)
    if not org_roots:
        return _default_agent_profile_repository().get(profile_id)
    return _activation_aware_profile_map(repo_root, org_roots).get(profile_id)


def _load_agent_profile(
    profile_id: str, repo_root: Path | None = None
) -> AgentProfile | None:
    """Resolve *profile_id* via the doctrine layer. Returns ``None`` on miss.

    Errors are intentionally swallowed: this helper is on the prompt-build
    hot path and must never raise into the resolver. A diagnostic is logged
    at WARNING level so operators can audit unknown profile IDs without the
    prompt collapsing.
    """
    try:
        record = _resolve_agent_profile_record(profile_id, repo_root)
    except Exception:  # noqa: BLE001 — best-effort lookup
        _LOGGER.warning(
            "Profile '%s' lookup failed; profile-cited sections will be omitted.",
            profile_id,
        )
        return None
    if record is None:
        _LOGGER.warning(
            "Profile '%s' not found; profile-cited sections omitted.",
            profile_id,
        )
    return record


def _format_profile_directive_code(raw: object) -> str:
    """Normalise a directive-ref code to the canonical ``DIRECTIVE_NNN`` form.

    Profile YAML stores codes as bare numerals (``"010"``) or already in
    ``DIRECTIVE_NNN`` form. The catalog lookup needs the canonical form.
    """
    text = str(raw).strip()
    if re.match(r"^DIRECTIVE_\d+$", text):
        return text
    match = re.match(r"^(\d+)$", text)
    if match:
        return f"DIRECTIVE_{match.group(1).zfill(3)}"
    return text


def _jsonable_artifact_value(value: object) -> object:
    """Return a deterministic JSON-safe representation of a doctrine object."""

    if value is None or isinstance(value, str | int | float | bool):
        return value

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump(by_alias=True, mode="json", exclude_none=True)
        except TypeError:
            dumped = model_dump()
        return _jsonable_artifact_value(dumped)

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str | int | float | bool):
        return enum_value

    if isinstance(value, dict):
        return {
            str(key): _jsonable_artifact_value(item)
            for key, item in value.items()
            if item is not None
        }

    if isinstance(value, set):
        normalized = [_jsonable_artifact_value(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(item, sort_keys=True),
        )

    if isinstance(value, list | tuple):
        return [_jsonable_artifact_value(item) for item in value]

    attrs = getattr(value, "__dict__", None)
    if isinstance(attrs, dict):
        return {
            key: _jsonable_artifact_value(item)
            for key, item in attrs.items()
            if not key.startswith("_") and item is not None
        }

    return str(value)


def _format_full_artifact_payload_body(artifact: object) -> list[str]:
    """Render the full doctrine payload for fetch-selector recovery."""

    payload = _jsonable_artifact_value(artifact)
    if not isinstance(payload, dict) or not payload:
        return []

    json_lines = json.dumps(payload, indent=2, sort_keys=True).splitlines()
    return ["    Full artifact:", *(f"      {line}" for line in json_lines)]


def _format_inline_directive_body(directive: object) -> list[str]:
    """Render the verbatim body of a directive as indented lines."""
    body_lines: list[str] = []
    intent = getattr(directive, "intent", None)
    if isinstance(intent, str) and intent.strip():
        body_lines.append(f"    Intent: {intent.strip()}")
    scope = getattr(directive, "scope", None)
    if isinstance(scope, str) and scope.strip():
        body_lines.append(f"    Scope: {scope.strip()}")
    for label, attr in (
        ("Procedures", "procedures"),
        ("Integrity rules", "integrity_rules"),
        ("Validation criteria", "validation_criteria"),
    ):
        items = getattr(directive, attr, None)
        if isinstance(items, list) and items:
            body_lines.append(f"    {label}:")
            for item in items:
                body_lines.append(f"      - {item}")
    return body_lines


def _budget_estimate(lines: list[str]) -> int:
    """Total character cost of *lines* including newlines."""
    return sum(len(line) + 1 for line in lines)


def _render_fetch_stanza(
    *,
    selector: str,
    when_clause: str,
) -> list[str]:
    """Render the canonical fetch + when-doing stanza for a single entry.

    WP05 T020: this is a thin wrapper around the shared
    :func:`charter.context_renderers.fetch_stanza.fetch_stanza_lines`
    helper so every renderer (WP03 profile-cited, WP04 section bodies,
    WP05 budget substitution) emits identical bytes.  The four-space
    indent is preserved here to match the existing profile-cited
    rendering shape.
    """
    return list(_shared_fetch_stanza_lines(selector, when_clause, indent="    "))


def _render_profile_directives(
    profile: AgentProfile,
    service: object,
) -> list[str]:
    """Render the ``Profile-Cited Directives (<profile-id>):`` section as a list of lines.

    Returns an empty list when the profile has no ``directive_references``
    so the caller can filter out the header. Each entry is either the
    verbatim body (when under the per-entry budget) OR the
    fetch + when-doing stanza pinned by the ATDD contract.
    """
    refs = list(profile.directive_references)
    if not refs:
        return []

    header = _PROFILE_DIRECTIVES_HEADER_TPL.format(profile_id=profile.profile_id)
    lines: list[str] = [header]
    repo = getattr(service, "directives", None)

    for ref in refs:
        code = _format_profile_directive_code(getattr(ref, "code", ""))
        title = getattr(ref, "name", "") or ""
        rationale = getattr(ref, "rationale", "") or ""
        header_line = f"  - {code}: {title}"
        if rationale:
            header_line = f"{header_line} — {rationale}"
        lines.append(header_line)

        directive = None
        if repo is not None:
            try:
                directive = repo.get(code)
            except Exception:  # noqa: BLE001 — best-effort catalog lookup
                directive = None

        if directive is None:
            # RISK-3 (Mission B post-merge): structured catalog-miss
            # stanza + warning instead of the generic placeholder.
            # FR-013: _diagnose_catalog_miss checks scope_filtered_ids
            # first so a scope-filtered directive surfaces SCOPE_FILTERED
            # rather than MISSING_ARTIFACT.
            diagnosis = _diagnose_catalog_miss(code, repo)
            lines.extend(
                format_catalog_miss_stanza(
                    selector_kind="directive",
                    artifact_id=code,
                    diagnosis=diagnosis,
                    indent="    ",
                )
            )
            emit_catalog_miss_warning(
                selector_kind="directive",
                artifact_id=code,
                diagnosis=diagnosis,
                context=f"profile:{profile.profile_id}",
            )
            continue

        body_lines = _format_inline_directive_body(directive)
        if body_lines and _budget_estimate(body_lines) <= _PROFILE_INLINE_BODY_LIMIT_CHARS:
            lines.extend(body_lines)
        else:
            lines.extend(
                _render_fetch_stanza(
                    selector=f"directive:{code}",
                    when_clause="are about to apply a code change",
                )
            )

    return lines


def _render_profile_tactics(
    profile: AgentProfile,
    service: object,
) -> list[str]:
    """Render the ``Profile-Cited Tactics (<profile-id>):`` section as a list of lines.

    Returns an empty list when the profile has no ``tactic_references``.
    The fetch stanza uses ``--include tactic:<id>``. Tactics do not carry
    a ``when:`` field today; the conditional falls back to "apply a code
    change" so the prompt remains actionable.
    """
    refs = list(profile.tactic_references)
    if not refs:
        return []
    # WP12/T067: shares the profile-section renderer with the styleguide /
    # toolguide / procedure paths (extracted to context_renderers.profile_sections
    # so context.py does not grow). Byte-identical to the prior inline body.
    return _render_profile_selector_refs(
        header=_PROFILE_TACTICS_HEADER_TPL.format(profile_id=profile.profile_id),
        entries=[
            (getattr(ref, "id", ""), getattr(ref, "rationale", "") or "")
            for ref in refs
        ],
        repo=getattr(service, "tactics", None),
        selector_kind="tactic",
        profile_id=profile.profile_id,
        when_clause="are about to apply a code change",
        body_fn=_format_inline_named_body,
    )


# ---------------------------------------------------------------------------
# Charter-level global selection rendering (WP04 — FR-005)
# ---------------------------------------------------------------------------


_SELECTED_PARADIGMS_HEADER = "Selected paradigms:"
_SELECTED_DIRECTIVES_HEADER = "Selected directives:"
_SELECTED_TACTICS_HEADER = "Selected tactics:"
_SELECTED_STYLEGUIDES_HEADER = "Selected styleguides:"
_SELECTED_TOOLGUIDES_HEADER = "Selected toolguides:"
_SELECTED_PROCEDURES_HEADER = "Selected procedures:"
_SELECTED_AGENT_PROFILES_HEADER = "Selected agent profiles:"
_SELECTED_MISSION_STEP_CONTRACTS_HEADER = "Selected mission step contracts:"


def _provenance_suffix(
    artifact_id: str,
    org_source_map: dict[str, str] | None,
) -> str:
    """Return ``" (source: org, pack: <name>)"`` for org-sourced artifacts.

    Per the WP04 contract (selection-schema.md §"Resolver-level"):

    * built-in / project artifacts → no suffix (matches today's convention).
    * org-distributed artifacts → ``(source: org, pack: <name>)`` so the
      operator can audit which pack contributed the rule.

    ``org_source_map`` maps ``artifact_id → pack_name``. When the pack name
    is not known (legacy callers pass an empty string), the suffix
    collapses to ``(source: org)`` so the provenance signal survives even
    without per-pack attribution.
    """
    if not org_source_map or artifact_id not in org_source_map:
        return ""
    pack = (org_source_map.get(artifact_id) or "").strip()
    if pack:
        return f" (source: org, pack: {pack})"
    return " (source: org)"


def _format_inline_styleguide_body(styleguide: object) -> list[str]:
    """Render the verbatim body of a styleguide as indented lines."""
    body_lines: list[str] = []
    title = getattr(styleguide, "title", None)
    if isinstance(title, str) and title.strip():
        body_lines.append(f"    Title: {title.strip()}")
    scope = getattr(styleguide, "scope", None)
    if scope is not None:
        scope_str = scope.value if hasattr(scope, "value") else str(scope)
        if scope_str:
            body_lines.append(f"    Scope: {scope_str}")
    principles = getattr(styleguide, "principles", None)
    if isinstance(principles, list) and principles:
        body_lines.append("    Principles:")
        for principle in principles:
            body_lines.append(f"      - {principle}")
    return body_lines


def _format_inline_paradigm_body(paradigm: object) -> list[str]:
    """Render the verbatim body of a paradigm as indented lines."""
    body_lines: list[str] = []
    name = getattr(paradigm, "name", None)
    if isinstance(name, str) and name.strip():
        body_lines.append(f"    Name: {name.strip()}")
    summary = getattr(paradigm, "summary", None)
    if isinstance(summary, str) and summary.strip():
        body_lines.append(f"    Summary: {summary.strip()}")
    return body_lines


def _format_inline_tactic_body(tactic: object) -> list[str]:
    """Render the verbatim body of a tactic as indented lines."""
    body_lines: list[str] = []
    name = getattr(tactic, "name", None)
    if isinstance(name, str) and name.strip():
        body_lines.append(f"    Name: {name.strip()}")
    purpose = getattr(tactic, "purpose", None)
    if isinstance(purpose, str) and purpose.strip():
        body_lines.append(f"    Purpose: {purpose.strip()}")
    steps = getattr(tactic, "steps", None)
    if isinstance(steps, list) and steps:
        body_lines.append("    Steps:")
        for step in steps:
            step_title = getattr(step, "title", str(step))
            body_lines.append(f"      - {step_title}")
    return body_lines


def _format_inline_toolguide_body(toolguide: object) -> list[str]:
    """Render the verbatim body of a toolguide as indented lines."""
    body_lines: list[str] = []
    title = getattr(toolguide, "title", None)
    if isinstance(title, str) and title.strip():
        body_lines.append(f"    Title: {title.strip()}")
    tool = getattr(toolguide, "tool", None)
    if isinstance(tool, str) and tool.strip():
        body_lines.append(f"    Tool: {tool.strip()}")
    summary = getattr(toolguide, "summary", None)
    if isinstance(summary, str) and summary.strip():
        body_lines.append(f"    Summary: {summary.strip()}")
    return body_lines


def _format_inline_procedure_body(procedure: object) -> list[str]:
    """Render the verbatim body of a procedure as indented lines."""
    body_lines: list[str] = []
    name = getattr(procedure, "name", None)
    if isinstance(name, str) and name.strip():
        body_lines.append(f"    Name: {name.strip()}")
    purpose = getattr(procedure, "purpose", None)
    if isinstance(purpose, str) and purpose.strip():
        body_lines.append(f"    Purpose: {purpose.strip()}")
    entry = getattr(procedure, "entry_condition", None)
    if isinstance(entry, str) and entry.strip():
        body_lines.append(f"    Entry condition: {entry.strip()}")
    exit_ = getattr(procedure, "exit_condition", None)
    if isinstance(exit_, str) and exit_.strip():
        body_lines.append(f"    Exit condition: {exit_.strip()}")
    steps = getattr(procedure, "steps", None)
    if isinstance(steps, list) and steps:
        body_lines.append("    Steps:")
        for step in steps:
            step_title = getattr(step, "title", str(step))
            body_lines.append(f"      - {step_title}")
    return body_lines


def _format_inline_agent_profile_body(profile_obj: object) -> list[str]:
    """Render the verbatim body of an agent profile as indented lines."""
    body_lines: list[str] = []
    name = getattr(profile_obj, "name", None)
    if isinstance(name, str) and name.strip():
        body_lines.append(f"    Name: {name.strip()}")
    purpose = getattr(profile_obj, "purpose", None)
    if isinstance(purpose, str) and purpose.strip():
        body_lines.append(f"    Purpose: {purpose.strip()}")
    roles = getattr(profile_obj, "roles", None)
    if isinstance(roles, list) and roles:
        role_names = [
            role.value if hasattr(role, "value") else str(role) for role in roles
        ]
        body_lines.append(f"    Roles: {', '.join(role_names)}")
    return body_lines


def _format_inline_step_contract_body(contract: object) -> list[str]:
    """Render the verbatim body of a mission step contract as indented lines."""
    body_lines: list[str] = []
    action = getattr(contract, "action", None)
    if isinstance(action, str) and action.strip():
        body_lines.append(f"    Action: {action.strip()}")
    mission = getattr(contract, "mission", None)
    if isinstance(mission, str) and mission.strip():
        body_lines.append(f"    Mission: {mission.strip()}")
    steps = getattr(contract, "steps", None)
    if isinstance(steps, list) and steps:
        body_lines.append("    Steps:")
        for step in steps:
            step_id = getattr(step, "id", None)
            step_desc = getattr(step, "description", "")
            if step_id:
                body_lines.append(f"      - {step_id}: {step_desc}")
            else:
                body_lines.append(f"      - {step_desc}")
    return body_lines


def _diagnose_catalog_miss(
    missing_id: str,
    repository: object | None,
) -> CatalogMissDiagnosis:
    """Return the best-fit :class:`CatalogMissDiagnosis` for *missing_id*.

    Checks whether the repository recorded *missing_id* as scope-filtered
    (present on disk but excluded by the active language scope) before
    falling back to the fuzzy-match :func:`classify_catalog_miss`.  This
    is the single gate that implements FR-013 end-to-end: any call site
    that previously called ``classify_catalog_miss`` directly now calls
    this helper instead, so scope-filtered misses are never surfaced as
    ``MISSING_ARTIFACT``.

    Active-language context is read directly from the repository's own
    ``_active_languages`` attribute (the value already stored at
    construction time), avoiding the need to thread ``repo_root`` through
    every renderer.
    """
    scope_filtered: frozenset[str] | set[str] = getattr(
        repository, "scope_filtered_ids", frozenset()
    )
    if isinstance(scope_filtered, (set, frozenset)) and missing_id in scope_filtered:
        active_languages: list[str] | None = getattr(
            repository, "_active_languages", None
        )
        return classify_scope_filtered_miss(missing_id, active_languages)
    return classify_catalog_miss(missing_id, _available_catalog_ids(repository))


def _available_catalog_ids(repository: object | None) -> list[str]:
    """Return the IDs the repository carries, for fuzzy-match suggestions.

    Used by the catalog-miss diagnosis path (RISK-3 from the Mission B
    post-merge review).  Defensive against stub repositories used in
    tests that may not implement ``list_all`` / ``all``; returns an
    empty list when no listing API is available.
    """
    if repository is None:
        return []
    for attr in ("list_all", "all"):
        lister = getattr(repository, attr, None)
        if callable(lister):
            try:
                items = lister()
            except Exception as exc:  # noqa: BLE001 — best-effort introspection
                _LOGGER.debug(
                    "Catalog listing via %s() raised %r; falling back.",
                    attr,
                    exc,
                )
                continue
            ids: list[str] = []
            for item in items or []:
                ident = getattr(item, "id", None)
                if isinstance(ident, str) and ident:
                    ids.append(ident)
            if ids:
                return ids
    # Fall back to introspecting the stub's internal ``_items`` dict
    # (used by the test doubles in ``tests/charter/`` so we can suggest
    # close matches without forcing every stub to grow a ``list_all``).
    items = getattr(repository, "_items", None)
    if isinstance(items, dict):
        return [k for k in items if isinstance(k, str)]
    return []


def _render_selected_artifacts(
    selected_ids: list[str],
    repository: ArtifactRepository[Any] | None,
    *,
    header: str,
    selector_kind: str,
    when_clause: str,
    body_formatter: Callable[[object], list[str]],
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Shared implementation for the 8 ``_render_selected_<kind>`` helpers.

    Each helper is a thin wrapper that picks the right repository
    (``service.styleguides`` / ``service.toolguides`` / ...) and inline
    body formatter, then defers to this routine for the budget /
    fetch-stanza / provenance logic.

    Returns an empty list when ``selected_ids`` is empty so the caller
    can filter out the header — preserving the "no leading header,
    no trailing section" guarantee from the WP04 reviewer checklist.
    """
    if not selected_ids:
        return []

    lines: list[str] = [header]
    seen: set[str] = set()
    for artifact_id in selected_ids:
        # Deduplicate while preserving authoring order (R-4 mitigation).
        if artifact_id in seen:
            continue
        seen.add(artifact_id)

        suffix = _provenance_suffix(artifact_id, org_source_map)
        header_line = f"  - {artifact_id}{suffix}"
        lines.append(header_line)

        artifact = None
        if repository is not None:
            try:
                artifact = repository.get(artifact_id)
            except Exception:  # noqa: BLE001 — best-effort catalog lookup
                artifact = None

        if artifact is None:
            # RISK-3 (Mission B post-merge): replace the generic
            # placeholder with a structured stanza that classifies the
            # miss (typo vs. missing vs. schema-validation drop) and
            # routes a warning through both ``warnings.warn`` and the
            # module logger so the failure is never silent.
            # FR-013: _diagnose_catalog_miss checks scope_filtered_ids
            # first so a scope-filtered artifact surfaces SCOPE_FILTERED
            # rather than MISSING_ARTIFACT.
            diagnosis = _diagnose_catalog_miss(artifact_id, repository)
            lines.extend(
                format_catalog_miss_stanza(
                    selector_kind=selector_kind,
                    artifact_id=artifact_id,
                    diagnosis=diagnosis,
                    indent="    ",
                )
            )
            emit_catalog_miss_warning(
                selector_kind=selector_kind,
                artifact_id=artifact_id,
                diagnosis=diagnosis,
            )
            lines.extend(
                _shared_fetch_stanza_lines(
                    f"{selector_kind}:{artifact_id}",
                    when_clause,
                    indent="    ",
                )
            )
            continue

        body_lines = body_formatter(artifact)
        if body_lines and _budget_estimate(body_lines) <= _PROFILE_INLINE_BODY_LIMIT_CHARS:
            lines.extend(body_lines)
        else:
            lines.extend(
                _shared_fetch_stanza_lines(
                    f"{selector_kind}:{artifact_id}",
                    when_clause,
                    indent="    ",
                )
            )

    return lines


def _render_selected_paradigms(
    selected_ids: list[str],
    service: object,
    *,
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Render globally-selected paradigms into prompt lines."""
    repo = getattr(service, "paradigms", None)
    return _render_selected_artifacts(
        selected_ids,
        repo,
        header=_SELECTED_PARADIGMS_HEADER,
        selector_kind="paradigm",
        when_clause="are about to choose a reasoning frame",
        body_formatter=_format_inline_paradigm_body,
        org_source_map=org_source_map,
    )


def _render_selected_directives(
    selected_ids: list[str],
    service: object,
    *,
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Render globally-selected directives into prompt lines."""
    repo = getattr(service, "directives", None)
    return _render_selected_artifacts(
        selected_ids,
        repo,
        header=_SELECTED_DIRECTIVES_HEADER,
        selector_kind="directive",
        when_clause="are about to apply a code change",
        body_formatter=_format_inline_directive_body,
        org_source_map=org_source_map,
    )


def _render_selected_tactics(
    selected_ids: list[str],
    service: object,
    *,
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Render globally-selected tactics into prompt lines."""
    repo = getattr(service, "tactics", None)
    return _render_selected_artifacts(
        selected_ids,
        repo,
        header=_SELECTED_TACTICS_HEADER,
        selector_kind="tactic",
        when_clause="are about to apply a code change",
        body_formatter=_format_inline_tactic_body,
        org_source_map=org_source_map,
    )


def _render_selected_styleguides(
    selected_ids: list[str],
    service: object,
    *,
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Render globally-selected styleguides into prompt lines (T017).

    Returns inline body lines when budget allows; fetch + when-doing
    stanzas when overflow triggers.  Provenance is appended as
    ``(source: org, pack: <name>)`` after each org-sourced artifact ID.
    """
    repo = getattr(service, "styleguides", None)
    return _render_selected_artifacts(
        selected_ids,
        repo,
        header=_SELECTED_STYLEGUIDES_HEADER,
        selector_kind="styleguide",
        when_clause="are about to write a code comment or styled output",
        body_formatter=_format_inline_styleguide_body,
        org_source_map=org_source_map,
    )


def _render_selected_toolguides(
    selected_ids: list[str],
    service: object,
    *,
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Render globally-selected toolguides into prompt lines (T018)."""
    repo = getattr(service, "toolguides", None)
    return _render_selected_artifacts(
        selected_ids,
        repo,
        header=_SELECTED_TOOLGUIDES_HEADER,
        selector_kind="toolguide",
        when_clause="are about to invoke a project tool",
        body_formatter=_format_inline_toolguide_body,
        org_source_map=org_source_map,
    )


def _render_selected_procedures(
    selected_ids: list[str],
    service: object,
    *,
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Render globally-selected procedures into prompt lines (T018)."""
    repo = getattr(service, "procedures", None)
    return _render_selected_artifacts(
        selected_ids,
        repo,
        header=_SELECTED_PROCEDURES_HEADER,
        selector_kind="procedure",
        when_clause="are about to follow a multi-step workflow",
        body_formatter=_format_inline_procedure_body,
        org_source_map=org_source_map,
    )


def _render_selected_agent_profiles(
    selected_ids: list[str],
    service: object,
    *,
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Render globally-selected agent profiles into prompt lines (T018)."""
    repo = getattr(service, "agent_profiles", None)
    return _render_selected_artifacts(
        selected_ids,
        repo,
        header=_SELECTED_AGENT_PROFILES_HEADER,
        selector_kind="agent_profile",
        when_clause="are about to apply a code change",
        body_formatter=_format_inline_agent_profile_body,
        org_source_map=org_source_map,
    )


def _render_selected_mission_step_contracts(
    selected_ids: list[str],
    service: object,
    *,
    org_source_map: dict[str, str] | None = None,
) -> list[str]:
    """Render globally-selected mission step contracts (T018)."""
    repo = getattr(service, "mission_step_contracts", None)
    return _render_selected_artifacts(
        selected_ids,
        repo,
        header=_SELECTED_MISSION_STEP_CONTRACTS_HEADER,
        selector_kind="mission_step_contract",
        when_clause="are about to step a mission action",
        body_formatter=_format_inline_step_contract_body,
        org_source_map=org_source_map,
    )


def _collect_org_source_map(
    repository: ArtifactRepository[Any] | None,
    artifact_ids: list[str],
) -> dict[str, str]:
    """Map ``artifact_id → "org"`` (placeholder pack name) for org-sourced IDs.

    Computed once per ``build_charter_context`` call so each renderer
    can call :func:`_provenance_suffix` without a repository walk
    (R-3 mitigation: ``Provenance source map computed N times per build``).

    The repository tracks provenance as one of ``"builtin"`` / ``"org"`` /
    ``"project"`` (see :meth:`doctrine.base.BaseDoctrineRepository.get_provenance`);
    today there is no per-pack attribution at the repository layer.  When
    that lands, the value here will gain pack-name semantics — for now
    we use an empty-string sentinel so the suffix collapses to
    ``(source: org)`` per :func:`_provenance_suffix`.
    """
    if repository is None or not artifact_ids:
        return {}

    org_map: dict[str, str] = {}
    for artifact_id in artifact_ids:
        try:
            source = repository.get_provenance(artifact_id)
        except (AttributeError, KeyError):
            source = None
        if source == "org":
            org_map[artifact_id] = ""
    return org_map


def _render_selection_block(
    doctrine_selection: DoctrineSelectionConfig | None,
    service: object,
    *,
    repo_root: Path | None = None,
) -> str:
    """Render the combined 8-kind selection section block.

    Concatenates the 8 ``_render_selected_<kind>`` outputs with blank
    lines between non-empty blocks so the prompt body remains readable.
    Returns ``""`` when no selections exist on the charter — the caller
    can then skip the leading blank line without emitting a stray
    section header.

    Mission B WP06: the provenance map now ALSO carries org-pack-required
    ids (read straight from each pack's ``org-charter.yaml``) so that
    artifacts declared by an org pack but absent from the catalog (e.g.
    a styleguide whose YAML failed schema validation) still surface their
    org provenance in the prompt.  The catalog-derived map wins when
    both are present — that path retains the per-artifact provenance the
    DoctrineService computed.
    """
    if doctrine_selection is None or service is None:
        return ""

    # WP04 T020: compute the provenance source map ONCE per build, then
    # pass it down to each renderer — avoids the N×repo-walk regression
    # called out in the WP04 risk table.
    org_required: dict[str, list[str]] = (
        _read_org_required_selections(repo_root) if repo_root is not None else {}
    )

    def _merge(
        catalog_map: dict[str, str],
        kind: str,
        selected_ids: list[str],
    ) -> dict[str, str]:
        merged = dict(catalog_map)
        for sid in selected_ids:
            if sid in merged:
                continue
            if sid in (org_required.get(kind) or []):
                # Sentinel value matches ``_collect_org_source_map``: empty
                # string collapses to a bare ``(source: org)`` suffix per
                # :func:`_provenance_suffix`.
                merged[sid] = ""
        return merged

    paradigm_org = _merge(
        _collect_org_source_map(
            getattr(service, "paradigms", None), doctrine_selection.selected_paradigms
        ),
        "paradigms",
        doctrine_selection.selected_paradigms,
    )
    directive_org = _merge(
        _collect_org_source_map(
            getattr(service, "directives", None), doctrine_selection.selected_directives
        ),
        "directives",
        doctrine_selection.selected_directives,
    )
    tactic_org = _merge(
        _collect_org_source_map(
            getattr(service, "tactics", None), doctrine_selection.selected_tactics
        ),
        "tactics",
        doctrine_selection.selected_tactics,
    )
    styleguide_org = _merge(
        _collect_org_source_map(
            getattr(service, "styleguides", None), doctrine_selection.selected_styleguides
        ),
        "styleguides",
        doctrine_selection.selected_styleguides,
    )
    toolguide_org = _merge(
        _collect_org_source_map(
            getattr(service, "toolguides", None), doctrine_selection.selected_toolguides
        ),
        "toolguides",
        doctrine_selection.selected_toolguides,
    )
    procedure_org = _merge(
        _collect_org_source_map(
            getattr(service, "procedures", None), doctrine_selection.selected_procedures
        ),
        "procedures",
        doctrine_selection.selected_procedures,
    )
    agent_profile_org = _merge(
        _collect_org_source_map(
            getattr(service, "agent_profiles", None),
            doctrine_selection.selected_agent_profiles,
        ),
        "agent_profiles",
        doctrine_selection.selected_agent_profiles,
    )
    step_contract_org = _merge(
        _collect_org_source_map(
            getattr(service, "mission_step_contracts", None),
            doctrine_selection.selected_mission_step_contracts,
        ),
        "mission_step_contracts",
        doctrine_selection.selected_mission_step_contracts,
    )

    blocks: list[str] = []
    sections = (
        _render_selected_paradigms(
            doctrine_selection.selected_paradigms, service, org_source_map=paradigm_org
        ),
        _render_selected_directives(
            doctrine_selection.selected_directives, service, org_source_map=directive_org
        ),
        _render_selected_tactics(
            doctrine_selection.selected_tactics, service, org_source_map=tactic_org
        ),
        _render_selected_styleguides(
            doctrine_selection.selected_styleguides, service, org_source_map=styleguide_org
        ),
        _render_selected_toolguides(
            doctrine_selection.selected_toolguides, service, org_source_map=toolguide_org
        ),
        _render_selected_procedures(
            doctrine_selection.selected_procedures, service, org_source_map=procedure_org
        ),
        _render_selected_agent_profiles(
            doctrine_selection.selected_agent_profiles,
            service,
            org_source_map=agent_profile_org,
        ),
        _render_selected_mission_step_contracts(
            doctrine_selection.selected_mission_step_contracts,
            service,
            org_source_map=step_contract_org,
        ),
    )
    for section_lines in sections:
        if section_lines:
            blocks.append("\n".join(section_lines))
    return "\n\n".join(blocks)


def _load_governance_activations(repo_root: Path) -> list[ActivationEntry]:
    """Best-effort load of ``GovernanceConfig.activations`` for *repo_root*.

    The activation registry is a top-level governance field (per
    :mod:`charter.activations`).  We isolate the load here so the call
    site in :func:`_render_bootstrap_text` stays small and any parse
    failure collapses to an empty list (mirrors
    :func:`_load_doctrine_selection`'s resilience pattern).
    """
    from charter.sync import load_governance_config

    try:
        governance = load_governance_config(repo_root)
    except Exception:  # noqa: BLE001 — best-effort governance load
        return []
    return list(governance.activations)


def _read_org_activations(repo_root: Path) -> list[ActivationEntry]:
    """Union every org pack's ``activations:`` entries (FR-001/002/004).

    Mirrors :func:`_read_org_required_selections`'s union/order shape
    (first-seen across packs in config order, via the shared
    :func:`_iter_org_charter_docs` reader) but deliberately does NOT
    mirror its silent-skip error handling (C-002 override): a
    structurally malformed entry in a *present* pack's ``activations:``
    list RAISES via ``ActivationEntry.model_validate`` (FR-004), naming
    the offending pack so the operator can locate it (SC-003). A pack
    whose ``org-charter.yaml`` is missing or unreadable is skipped by
    :func:`_iter_org_charter_docs` upstream — that is a different,
    non-raising failure class (the pack was never a parseable document
    to begin with).

    Deduplication across packs (and against the project-local list) is
    NOT performed here — :func:`_union_activations` owns identity-key
    dedup for the merged project+org list (SC-002).
    """
    entries: list[ActivationEntry] = []
    for name, raw in _iter_org_charter_docs(repo_root):
        value = raw.get("activations")
        if not isinstance(value, list):
            continue
        for item in value:
            try:
                entries.append(ActivationEntry.model_validate(item))
            except ValidationError as exc:
                raise ValueError(
                    f"org pack `{name}` declares a malformed activations entry "
                    f"{item!r}: {exc}"
                ) from exc
    return entries


def _union_activations(
    project_activations: list[ActivationEntry],
    org_activations: list[ActivationEntry],
) -> list[ActivationEntry]:
    """Union *project_activations* and *org_activations*, deduped by identity.

    Mirrors :func:`_read_org_required_selections`'s union/order
    semantics: first-seen wins on the shared 4-tuple identity key
    (:func:`charter.activations._activation_identity_key`), project
    entries are processed first so project first-seen order is
    preserved, and org entries are appended in their own first-seen
    order for anything not already present (SC-002). This is NOT
    ``_fold_policies``'s extends-chain last-wins semantics.
    """
    seen: set[tuple[str, str, str, str]] = set()
    merged: list[ActivationEntry] = []
    for entry in (*project_activations, *org_activations):
        key = _activation_identity_key(entry)
        if key in seen:
            continue
        seen.add(key)
        merged.append(entry)
    return merged


def _render_activation_block(
    doctrine_selection: DoctrineSelectionConfig | None,  # noqa: ARG001
    repo_root: Path | None,
    service: object,
    *,
    mission_type: str,
    action: str,
) -> str:
    """Call the WP05 activation-stanza renderer with the runtime context.

    WP04 owns the wire; WP05 owns the body.  This helper centralises the
    boilerplate (governance load + safe-call) so the call site in
    :func:`_render_bootstrap_text` is a single line.

    WP01 (#2365) adds the org∪project resolve-time union: the org read
    (:func:`_read_org_activations`) is a SEPARATE call from the project
    load, not folded inside :func:`_load_governance_activations` (that
    function has its own best-effort ``except: return []`` which would
    swallow the FR-004 validation raise). Both calls — and the union —
    happen BEFORE the ``if not activations`` short-circuit below (so an
    org-only match still renders, SC-001) and before the ``try`` around
    the renderer call (so the FR-004 raise escapes to
    :func:`build_charter_context` instead of being caught by the
    defensive ``except Exception`` a few lines down).

    Returns ``""`` when the activation list is empty, when the WP05
    renderer is still a stub, or when any error is raised by the
    renderer (defensive — the prompt build hot path must not crash).
    """
    if repo_root is None:
        return ""
    project_activations = _load_governance_activations(repo_root)
    org_activations = _read_org_activations(repo_root)
    activations = _union_activations(project_activations, org_activations)
    if not activations:
        return ""

    from charter._activation_render import render_activation_stanza

    try:
        return str(render_activation_stanza(
            activations,
            service,
            mission_type=mission_type,
            action=action,
        ))
    except Exception:  # noqa: BLE001 — defensive: never crash the prompt build
        _LOGGER.warning(
            "Activation stanza renderer raised; surface omitted for action %s.",
            action,
        )
        return ""


# ---------------------------------------------------------------------------
# Profile-driven rendering helpers (continued)
# ---------------------------------------------------------------------------


def _render_profile_sections(
    profile: AgentProfile | None,
    service: object,
) -> str:
    """Render every profile-channel section the profile attests.

    Returns an empty string when *profile* is ``None`` (T069 — an absent
    profile renders nothing, never a fail-open whole-graph fallback) or when
    no section has entries. WP12/T067 widens this beyond directives/tactics to
    the schema-attested styleguide/toolguide kinds and the channel-resolved
    procedure kind (T068). Unattested kinds (asset/anti-pattern/paradigm) are
    C-007 deferrals and contribute no section.
    """
    if profile is None:
        return ""
    section_renderers = (
        _render_profile_directives,
        _render_profile_tactics,
        _render_profile_styleguides,
        _render_profile_toolguides,
        _render_profile_procedures,
        # WP01 (doctrine-delivery-activation-01KYQVQK): the channel-resolved
        # ``suggests``-delivery section — the profile channel now follows
        # ``suggests``, delivering the #3063 A–E families (paradigm/tactic/…) as
        # ``when``-labelled links. Distinct from the C-007 deferral of
        # schema-attested INLINE citation of asset/anti-pattern/paradigm kinds:
        # this delivers what the CHANNEL reaches, as ``render_profile_procedures``
        # already does. Renderer body lives in ``context_renderers/profile_sections``
        # (owned by WP01); this is the one documented out-of-map ``context.py``
        # tuple registration (WP04 owns this module for IC-08 extraction).
        _render_profile_suggested_doctrine,
    )
    blocks = [
        "\n".join(lines)
        for renderer in section_renderers
        if (lines := renderer(profile, service))
    ]
    return "\n\n".join(blocks)


def _compact_section_block(repo_root: Path, action: str | None) -> str:
    """Render the compact-mode action-critical section block (DISPLAY-only).

    Reads the companion ``charter.md`` for the given *action* and delegates
    to :func:`render_critical_section_bodies`. The companion file is an
    optional display surface (a project's governance authority lives in
    ``charter.yaml``), so a missing or unreadable ``charter.md`` degrades to
    the empty string rather than raising (NFR-005).
    """
    if not action:
        return ""
    charter_path = repo_root / CHARTER_MD
    if not charter_path.exists():
        return ""
    try:
        charter_content = charter_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return str(render_critical_section_bodies(charter_content, action))


def _render_compact_governance(
    repo_root: Path,
    *,
    directive_ids: list[str] | None = None,
    tactic_ids: list[str] | None = None,
    styleguide_ids: list[str] | None = None,
    toolguide_ids: list[str] | None = None,
    procedure_ids: list[str] | None = None,
    asset_ids: list[str] | None = None,
    profile: AgentProfile | None = None,
    action: str | None = None,
) -> str:
    """Render the compact governance block (FR-034, WP11/T061).

    Compact mode preserves every directive ID, tactic ID, and section
    anchor that bootstrap mode would emit; only the long-form prose
    body is collapsed. ``directive_ids`` / ``tactic_ids`` are optional
    bootstrap-side lists that the caller has already resolved; when
    omitted the compact view falls back to the resolver's directive
    canon.

    WP11 (T061) widens this to the full delivered kind set (styleguide/
    toolguide/procedure/asset ids) — the render an agent receives on every load
    after the first (FR-010).

    When *profile* is provided (an :class:`AgentProfile` already resolved
    via :func:`_load_agent_profile`), the profile's
    ``directive_references`` and ``tactic_references`` are appended to
    the compact block as two additional sections (``Profile-Cited
    Directives`` / ``Profile-Cited Tactics``) so the WP06 wiring path
    can drive prompt-time governance even in compact mode.
    """
    from charter.compact import render_compact_view

    view = render_compact_view(
        repo_root,
        directive_ids=directive_ids or (),
        tactic_ids=tactic_ids or (),
        styleguide_ids=styleguide_ids or (),
        toolguide_ids=toolguide_ids or (),
        procedure_ids=procedure_ids or (),
        asset_ids=asset_ids or (),
    )
    text: str = str(view.text)

    # WP04 — the compact render path must carry the same authority-paths
    # and action-critical-section blocks as the bootstrap path so the
    # prompt-governance contract holds in both modes (R-3 mitigation).
    augmented_blocks: list[str] = []
    doctrine_selection = _load_doctrine_selection(repo_root)
    authority_block = render_authority_paths(repo_root, doctrine_selection)
    if authority_block:
        augmented_blocks.append(authority_block)
    reference_block = render_governance_references(
        repo_root,
        doctrine_selection.governance_references,
    )
    if reference_block:
        augmented_blocks.append(reference_block)

    # WP05 (IC-05) — the companion `charter.md` prose is DISPLAY-only and
    # optional: a project may have no `charter.md` on disk (e.g. governance
    # authority already lives in `charter.yaml`). ``_compact_section_block``
    # degrades gracefully to the empty string in that case (no crash, no
    # section block) rather than raising. The block is computed once and
    # reused for both the appended section and the NFR-001 budget input
    # below, instead of re-reading the companion file a second time.
    section_block_str = _compact_section_block(repo_root, action)
    if section_block_str:
        augmented_blocks.append(section_block_str)

    profile_block_str = ""
    if profile is not None:
        # Build a lightweight DoctrineService for the compact path. The
        # service constructor is cheap (catalog directories are mmaped
        # lazily) and the resulting sections compose with the compact
        # block without altering the existing ID/anchor surface.
        service = _build_doctrine_service(repo_root)
        profile_block_str = _render_profile_sections(profile, service)
        if profile_block_str:
            augmented_blocks.append(profile_block_str)

    if not augmented_blocks:
        return text
    combined = text + "\n\n" + "\n\n".join(augmented_blocks)

    # WP05 (NFR-001) — compact view shares the budget cap with the
    # bootstrap path so prompts driven through the compact rail (e.g.
    # via the WP06 wiring) honour the same NFR-001 contract.
    return _enforce_token_budget(
        combined,
        action=action or "",
        profile_block=profile_block_str,
        section_block=section_block_str,
    )


def _extract_policy_summary(content: str) -> list[str]:
    lines = content.splitlines()
    start = _find_section_start(lines, "## Policy Summary")

    if start is None:
        # Fallback: return the first meaningful bullet points in the document.
        fallback = [line.strip().lstrip("- ").strip() for line in lines if line.strip().startswith("-")]
        return [item for item in fallback if item][:8]

    summary: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("-"):
            summary.append(stripped.lstrip("- ").strip())
    return summary


def _find_section_start(lines: list[str], heading: str) -> int | None:
    for index, line in enumerate(lines):
        if line.strip() == heading:
            return index
    return None


def _load_references(canonical_root: Path) -> list[dict[str, str]]:
    """Load the doctrine reference catalog from charter.yaml's ``catalog.references``.

    consolidate-charter-bundle (#2773): the retired ``references.yaml`` body is now
    the DERIVED ``catalog`` projection inside the authoritative ``charter.yaml``
    (``charter.schemas.CharterCatalog`` — item shape mirrors the old file verbatim).
    Reading it here keeps the injected "Reference Docs" bootstrap block sourced from
    the authoritative charter, not the file the fold migration deletes. Returns
    ``[]`` when charter.yaml or its ``catalog`` section is absent.
    """
    from charter.charter_yaml_io import load_charter_yaml  # noqa: PLC0415 — same-layer, lazy to avoid import cycles

    charter_yaml_path = canonical_root / CHARTER_YAML
    if not charter_yaml_path.exists():
        return []

    try:
        document = load_charter_yaml(charter_yaml_path)
    except (YAMLError, UnicodeDecodeError, OSError):
        return []

    catalog = document.get("catalog") if isinstance(document, dict) else None
    raw_references = catalog.get("references") if isinstance(catalog, dict) else []
    if not isinstance(raw_references, list):
        return []

    refs: list[dict[str, str]] = []
    for item in raw_references:
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                "id": str(item.get("id", "")),
                "title": str(item.get("title", "")),
                "local_path": str(item.get("local_path", "")),
                "kind": str(item.get("kind", "")),
                "summary": str(item.get("summary", "")),
            }
        )
    return refs


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"schema_version": "1.0.0", "actions": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {"schema_version": "1.0.0", "actions": {}}

    if not isinstance(data, dict):
        return {"schema_version": "1.0.0", "actions": {}}

    actions = data.get("actions")
    if not isinstance(actions, dict):
        data["actions"] = {}

    return data


def _write_state(path: Path, state: dict[str, object]) -> None:
    atomic_write(path, json.dumps(state, indent=2, sort_keys=True), mkdir=True)


def _mark_action_loaded(state: dict[str, object], state_path: Path, action: str) -> None:
    """Persist first-load timestamp for *action* into context-state.json."""
    actions_obj = state.setdefault("actions", {})
    if not isinstance(actions_obj, dict):
        actions_obj = {}
        state["actions"] = actions_obj
    actions_obj[action] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_state(state_path, state)


# ---------------------------------------------------------------------------
# WP07: JSON structured data export (provenance + org charter)
# ---------------------------------------------------------------------------


def _bundle_root_for_json(repo_root: Path) -> Path:
    """Return the canonical charter bundle root, falling back to *repo_root*."""
    try:
        from charter.sync import ensure_charter_bundle_fresh

        refresh_result = ensure_charter_bundle_fresh(repo_root)
    except Exception:  # noqa: BLE001 - JSON metadata is best-effort
        return repo_root
    if refresh_result is not None and refresh_result.canonical_root is not None:
        return Path(refresh_result.canonical_root)
    return repo_root


def _relative_json_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _project_charter_json_block(repo_root: Path) -> dict[str, object]:
    """Describe the project-local charter loaded by the context renderer."""
    bundle_root = _bundle_root_for_json(repo_root)
    charter_dir = bundle_root / KITTIFY_DIRNAME / "charter"
    charter_path = bundle_root / CHARTER_MD
    metadata_path = charter_dir / "metadata.yaml"

    block: dict[str, object] = {
        "present": charter_path.exists(),
        "path": _relative_json_path(charter_path, bundle_root),
    }
    if not charter_path.exists():
        return block

    block["bytes"] = charter_path.stat().st_size
    if not metadata_path.exists():
        return block

    try:
        data = YAML(typ="safe").load(metadata_path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError, ValueError):
        return block
    if not isinstance(data, dict):
        return block

    charter_hash = data.get("charter_hash")
    if isinstance(charter_hash, str) and charter_hash:
        block["hash"] = charter_hash
    source_path = data.get("source_path")
    if isinstance(source_path, str) and source_path:
        block["source_path"] = source_path
    bundle_schema_version = data.get("bundle_schema_version")
    if isinstance(bundle_schema_version, int):
        block["bundle_schema_version"] = bundle_schema_version
    schema_version = data.get("schema_version")
    if isinstance(schema_version, str) and schema_version:
        block["schema_version"] = schema_version
    return block


def _project_directive_entries(repo_root: Path) -> list[dict[str, object]]:
    """Return every directive ID that the project-governance resolver exposes."""
    from charter.sync import load_directives_config

    local_by_id, directive_ids = _load_project_directives(repo_root, load_directives_config)
    service = _maybe_build_doctrine_service(repo_root)
    entries: list[dict[str, object]] = []
    for directive_id in directive_ids:
        local = local_by_id.get(directive_id)
        if local is not None:
            entries.append(_local_directive_entry(directive_id, local))
            continue
        if service is None:
            entries.append({"id": directive_id, "source": "builtin"})
            continue
        entries.extend(_pd.collect_typed_artifacts(service.directives, [directive_id], kind="directive"))
    return entries


def _load_project_directives(
    repo_root: Path,
    load_directives_config: Callable[[Path], DirectivesConfig],
) -> tuple[dict[str, object], list[str]]:
    try:
        directives_cfg = load_directives_config(repo_root)
    except Exception:  # noqa: BLE001 - fall through to resolver/catalog path
        local_by_id: dict[str, object] = {}
        directive_ids: list[str] = []
    else:
        local_by_id = {directive.id: directive for directive in directives_cfg.directives}
        directive_ids = [directive.id for directive in directives_cfg.directives]

    try:
        from charter.resolver import resolve_project_governance

        resolution = resolve_project_governance(repo_root)
    except Exception:  # noqa: BLE001 - keep any directly-loaded directive IDs
        return local_by_id, list(dict.fromkeys(directive_ids))
    return local_by_id, list(dict.fromkeys(list(resolution.directives) + directive_ids))


def _maybe_build_doctrine_service(repo_root: Path) -> _doctrine_service_module.DoctrineService | None:
    try:
        return _build_doctrine_service(repo_root)
    except Exception:  # noqa: BLE001 - local directive IDs are still useful
        return None


def _local_directive_entry(directive_id: str, local: object) -> dict[str, object]:
    entry: dict[str, object] = {"id": directive_id, "source": "project"}
    title = getattr(local, "title", None)
    description = getattr(local, "description", None)
    if isinstance(title, str) and title:
        entry["title"] = title
    if isinstance(description, str) and description:
        entry["summary"] = description
    return entry


_EMPTY_ORG_CHARTER: dict[str, object] = {"present": False, "packs": []}


def build_charter_context_json(
    repo_root: Path,
    *,
    action: str,
    org_root: Path | None = None,
    depth: int | None = None,
    org_charter_block: dict[str, object] | None = None,
    mission_type: str | None = None,
    feature_dir: Path | None = None,
    include_all: bool = False,
) -> dict[str, object]:
    """Return the structured JSON payload for ``charter context --json``.

    The payload contains:

    * ``action`` / ``mode`` — same surface as :class:`CharterContextResult`.
    * ``directives`` / ``tactics`` / ``styleguides`` / ``toolguides`` —
      action-scoped typed artifact arrays, each entry carrying a ``"source"``
      provenance field (``"builtin"`` | ``"org"`` | ``"project"``).
    * ``all_directives`` — every directive ID exposed by the project
      governance resolver, including directives extracted from the
      project-local charter even when the action-scoped ``directives`` array
      is empty.
    * ``project_charter`` — the loaded project-local charter, when present.
    * ``org_charter`` — additive block describing org-layer governance
      policies (empty when no org pack ships an ``org-charter.yaml``).

    The *org_charter_block* is supplied by the caller as pre-loaded data —
    the charter layer must not import from ``specify_cli`` (ADR 2026-03-27-1),
    so any org-charter policy loading happens in the higher layer and is
    passed in here as a plain mapping.  Defaults to ``{"present": false,
    "packs": []}`` when omitted.

    Returns an empty-shell payload when the action is not a bootstrap action
    (the textual ``charter context`` surface is still authoritative for
    non-bootstrap actions).
    """
    normalized = action.strip().lower()
    payload: dict[str, object] = {
        "action": normalized,
        "directives": [],
        "tactics": [],
        "styleguides": [],
        "toolguides": [],
        "all_directives": _project_directive_entries(repo_root),
        "references": [],
        "project_charter": _project_charter_json_block(repo_root),
        "org_charter": (
            dict(org_charter_block) if org_charter_block is not None else dict(_EMPTY_ORG_CHARTER)
        ),
        "governance_references": [],
    }
    selection = _load_doctrine_selection(repo_root)
    payload["governance_references"] = [
        status.to_dict()
        for status in collect_governance_reference_status(
            repo_root,
            selection.governance_references,
        )
    ]

    if normalized not in BOOTSTRAP_ACTIONS:
        # WP11 (B-6) — non-bootstrap actions carry no action grain; ruled OUT
        # explicitly (empty typed arrays), not an early-return before a bundle.
        payload["mode"] = "compact"
        return payload

    state_bundle = _prepare_context_state(repo_root, normalized, depth)
    payload["mode"] = "bootstrap"
    # WP11 (T060/B-3) — no depth<minimum early return: the ``--json`` half of
    # every-load delivery (where SC-001/002 are measured) delivers at every depth.

    from charter.pack_context import PackContext as _PackContext  # noqa: PLC0415

    _pack_ctx_json = _PackContext.from_config(repo_root)
    bundle = _load_action_doctrine_bundle(
        repo_root=repo_root,
        action=normalized,
        effective_depth=state_bundle.effective_depth,
        org_root=org_root,
        pack_context=_pack_ctx_json,
        mission_type=mission_type,
        feature_dir=feature_dir,
    )
    service = bundle.service
    # WP15 progressive disclosure (default cadence): DTOs carry ``references[]``
    # (T081); ``requires``-reachable is inline/eager, ``suggests``-reached is
    # link/lazy (T082); ``include_all`` inlines the whole closure — a strict
    # superset (T083); the link set names every delivered artefact so the union
    # of inlined + referenced ids equals the delivered set, no cap (T084).
    payload.update(
        _pd.build_disclosure_payload(
            repos_by_kind={
                "directive": (service.directives, bundle.directive_ids),
                "tactic": (service.tactics, bundle.tactic_ids),
                "styleguide": (service.styleguides, bundle.styleguide_ids),
                "toolguide": (service.toolguides, bundle.toolguide_ids),
            },
            extra_delivered={"procedure": bundle.procedure_ids, "asset": bundle.asset_ids},
            merged=bundle.merged,
            roots=bundle.roots,
            include_all=include_all,
            body_of=_jsonable_artifact_value,
            bridge_urns=bundle.bridge_urns,
        )
    )
    return payload
