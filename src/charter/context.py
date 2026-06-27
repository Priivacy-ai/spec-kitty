"""Charter context bootstrap for prompt generation."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from charter.activations import ActivationEntry
    from charter.pack_context import PackContext
    from charter.scope import CharterScope
    from doctrine.drg.models import DRGGraph
    import doctrine.service as _doctrine_service_module

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
from charter.context_renderers import (
    BUDGET_DEFAULT,
    RenderedSection,
    budget_without_warning_line,
    render_authority_paths,
    render_critical_section_bodies,
    render_critical_section_include,
)
from charter.context_renderers.fetch_stanza import (
    fetch_stanza_lines as _shared_fetch_stanza_lines,
)
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
CHARTER_FILENAME = "charter.md"
MISSING_REFERENCES_MESSAGE = "  - No references manifest found."

_MIN_EFFECTIVE_DEPTH = 2   # minimum depth for bootstrap context (full summary + references)
_EXTENDED_CONTEXT_DEPTH = 3  # depth that includes extended styleguide/toolguide lines


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
    """Resolved action doctrine artifacts for bootstrap rendering."""

    mission: str
    directive_ids: list[str]
    tactic_ids: list[str]
    styleguide_ids: list[str]
    toolguide_ids: list[str]
    service: object


class _DirectiveLike(Protocol):
    """Minimal directive shape used by project directive helpers."""

    id: str


class _DirectivesConfigLike(Protocol):
    """Minimal directives config contract returned by charter.sync."""

    directives: Sequence[_DirectiveLike]


def build_charter_context(
    repo_root: Path,
    *,
    profile: str | None = None,
    action: str,
    mark_loaded: bool = True,
    depth: int | None = None,
    org_root: Path | None = None,
    scope: CharterScope | None = None,
) -> CharterContextResult:
    """Build charter context by querying the Doctrine Reference Graph.

    Parameters
    ----------
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
    charter_path = canonical_root / KITTIFY_DIRNAME / "charter" / CHARTER_FILENAME
    references_path = canonical_root / KITTIFY_DIRNAME / "charter" / "references.yaml"

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

    if state_bundle.effective_depth < _MIN_EFFECTIVE_DEPTH:
        if mark_loaded and state_bundle.first_load:
            _mark_action_loaded(state_bundle.state, state_bundle.state_path, normalized)
        return CharterContextResult(
            action=normalized,
            mode="compact",
            first_load=state_bundle.first_load,
            text=_augment(
                _render_compact_governance(repo_root, profile=profile_record, action=normalized)
            ),
            references_count=0,
            depth=state_bundle.effective_depth,
        )

    # WP06 — when the caller did not supply an explicit ``org_root``,
    # fall back to the first existing pack path discovered via the
    # charter-layer enumeration of ``.kittify/config.yaml``.  This keeps
    # callers that go through ``build_charter_context`` directly (e.g.
    # ATDD tests) on the same three-layer (built-in + org + project)
    # service shape that the ``specify_cli``-wrapped callers get.
    effective_org_root = org_root
    if effective_org_root is None:
        for _name, candidate in _enumerate_org_pack_paths(repo_root):
            if candidate.exists():
                effective_org_root = candidate
                break

    from charter.pack_context import PackContext as _PackContext  # noqa: PLC0415

    _pack_ctx = _PackContext.from_config(repo_root)
    doctrine_bundle = _load_action_doctrine_bundle(
        repo_root=repo_root,
        action=normalized,
        effective_depth=state_bundle.effective_depth,
        org_root=effective_org_root,
        pack_context=_pack_ctx,
    )
    charter_content = charter_path.read_text(encoding="utf-8")
    summary = _extract_policy_summary(charter_content)
    references = _load_references(references_path)
    doctrine_selection = _load_doctrine_selection(repo_root)
    text = _render_bootstrap_text(
        charter_path=charter_path,
        action=normalized,
        summary=summary,
        doctrine_bundle=doctrine_bundle,
        references=references,
        effective_depth=state_bundle.effective_depth,
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
        charter_path = canonical_root / KITTIFY_DIRNAME / "charter" / CHARTER_FILENAME
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
        return _render_directive_include(service, identifier, selector)
    if canonical_kind == ArtifactKind.TACTIC.value:
        return _render_tactic_include(service, identifier, selector)
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


def _render_directive_include(service: object, identifier: str, selector: str) -> str:
    """Render a directive selector for ``--include``."""

    directive_id = _format_profile_directive_code(identifier)
    directive = service.directives.get(directive_id)  # type: ignore[attr-defined]
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


def _render_tactic_include(service: object, identifier: str, selector: str) -> str:
    """Render a tactic selector for ``--include``."""

    tactic = service.tactics.get(identifier)  # type: ignore[attr-defined]
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


def _render_generic_artifact_include(service: object, identifier: str) -> str:
    """Resolve a best-effort ``artifact:<id>`` selector emitted by activations."""

    from doctrine.artifact_kinds import ArtifactKind

    # Derive the candidate kinds from the canonical ArtifactKind set rather
    # than re-declaring a parallel tuple (R-009 / CC-4). ``TEMPLATE`` is
    # excluded: templates are mission-qualified (``<mission>/<name>``) and are
    # not addressable by a bare ``artifact:<id>`` probe.
    matches: list[tuple[str, str]] = []
    for candidate_kind in (
        member.value
        for member in ArtifactKind
        if member is not ArtifactKind.TEMPLATE
    ):
        selector = f"{candidate_kind}:{identifier}"
        try:
            rendered: str | None
            if candidate_kind == "directive":
                rendered = _render_directive_include(service, identifier, selector)
            elif candidate_kind == "tactic":
                rendered = _render_tactic_include(service, identifier, selector)
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


def _classify_artifact_urns(
    artifact_urns: frozenset[str] | set[str],
    merged: DRGGraph,
    project_directives: set[str],
    selected_tactics: set[str] | None = None,
    selected_paradigms: set[str] | None = None,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Partition resolved artifact URNs into doctrine-type buckets."""
    from doctrine.drg.models import NodeKind, Relation
    from doctrine.drg.query import resolve_transitive_refs

    selected_tactics = selected_tactics or set()
    selected_paradigms = selected_paradigms or set()
    start_urns = {f"directive:{directive_id}" for directive_id in project_directives}
    start_urns.update(f"tactic:{tactic_id}" for tactic_id in selected_tactics)
    start_urns.update(f"paradigm:{paradigm_id}" for paradigm_id in selected_paradigms)
    selected_closure = resolve_transitive_refs(
        merged,
        start_urns=start_urns,
        relations={Relation.REQUIRES, Relation.SUGGESTS},
    )
    artifact_urns = set(artifact_urns)
    artifact_urns.update(f"directive:{directive_id}" for directive_id in selected_closure.directives)
    artifact_urns.update(f"tactic:{tactic_id}" for tactic_id in selected_closure.tactics)
    artifact_urns.update(f"styleguide:{styleguide_id}" for styleguide_id in selected_closure.styleguides)
    artifact_urns.update(f"toolguide:{toolguide_id}" for toolguide_id in selected_closure.toolguides)

    directive_ids: list[str] = []
    tactic_ids: list[str] = []
    styleguide_ids: list[str] = []
    toolguide_ids: list[str] = []
    for urn in sorted(artifact_urns):
        node = merged.get_node(urn)
        if node is None:
            continue
        artifact_id = urn.split(":", 1)[1] if ":" in urn else urn
        if node.kind == NodeKind.DIRECTIVE:
            if project_directives and artifact_id not in project_directives:
                continue
            directive_ids.append(artifact_id)
        elif node.kind == NodeKind.TACTIC:
            tactic_ids.append(artifact_id)
        elif node.kind == NodeKind.STYLEGUIDE:
            styleguide_ids.append(artifact_id)
        elif node.kind == NodeKind.TOOLGUIDE:
            toolguide_ids.append(artifact_id)
    return directive_ids, tactic_ids, styleguide_ids, toolguide_ids


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


def _read_org_required_selections(repo_root: Path) -> dict[str, list[str]]:
    """Union every org pack's ``required_<kind>`` across packs.

    Reads each configured pack's ``org-charter.yaml`` directly and
    returns a ``{kind: [ids...]}`` map covering the 8 kinds listed in
    :data:`_REQUIRED_KIND_FIELDS`.  Union preserves first-seen order
    across packs (declaration-order precedence, matching the merge
    semantics of :func:`specify_cli.doctrine.org_charter.load_org_charter_policies`).

    Packs whose ``local_path`` is missing are silently skipped here —
    the loud diagnostic for that case is produced by
    :func:`_missing_pack_diagnostic` upstream.
    """
    yaml = YAML(typ="safe")
    out: dict[str, list[str]] = {kind: [] for kind in _REQUIRED_KIND_FIELDS}
    for _name, pack_path in _enumerate_org_pack_paths(repo_root):
        charter_path = pack_path / "org-charter.yaml"
        if not charter_path.exists():
            continue
        try:
            raw = yaml.load(charter_path.read_text(encoding="utf-8"))
        except (OSError, YAMLError, ValueError):
            continue
        if not isinstance(raw, dict):
            continue
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
) -> _ActionDoctrineBundle:
    """Load DRG-backed action doctrine artifacts for bootstrap rendering."""
    from charter._drg_helpers import load_validated_graph
    from charter.drg import filter_graph_by_activation
    from doctrine.drg.loader import DRGLoadError
    from doctrine.drg.query import resolve_context

    doctrine_selection = _load_doctrine_selection(repo_root)
    mission = (doctrine_selection.template_set or "software-dev-default").removesuffix("-default")
    project_directives = {_normalize_directive_id(d) for d in doctrine_selection.selected_directives}
    selected_tactics = {t for t in doctrine_selection.selected_tactics if t}
    selected_paradigms = {p for p in doctrine_selection.selected_paradigms if p}

    # WP07 T034: route the DRG load through the shared helper so the built-in +
    # org + project three-layer overlay is honoured.  Callers in ``specify_cli``
    # supply *org_root* explicitly; charter-internal callers pass ``None`` and
    # get the two-layer (built-in + project) merge.
    #
    # WP04 (charter-mediated-doctrine-selection): a project that authors a
    # user doctrine artifact (e.g. ``.kittify/doctrine/styleguide/foo.yaml``)
    # without a sibling ``*.graph.yaml`` fragment causes ``load_graph_or_dir``
    # to raise ``DRGLoadError``. The DRG-action resolution is orthogonal to
    # charter-level global selection rendering, so we collapse the failure to
    # an empty action bundle and let the selection-renderer path continue
    # surfacing charter-authored ``selected_<kind>`` lists.  A WARNING is
    # logged so operators can audit the missing graph fragment.
    directive_ids: list[str] = []
    tactic_ids: list[str] = []
    styleguide_ids: list[str] = []
    toolguide_ids: list[str] = []
    try:
        merged = load_validated_graph(repo_root, org_root=org_root)
        # FR-032, FR-035 (WP08): apply activation filter before resolving context.
        if pack_context is not None:
            merged = filter_graph_by_activation(merged, pack_context)
        action_urn = f"action:{mission}/{action}"
        resolved = resolve_context(merged, action_urn, depth=effective_depth)
        directive_ids, tactic_ids, styleguide_ids, toolguide_ids = _classify_artifact_urns(
            resolved.artifact_urns,
            merged,
            project_directives,
            selected_tactics,
            selected_paradigms,
        )
    except DRGLoadError as exc:
        _LOGGER.warning(
            "DRG action resolution skipped for %s/%s: %s. "
            "Charter-level selections still render.",
            mission,
            action,
            exc,
        )

    return _ActionDoctrineBundle(
        mission=mission,
        directive_ids=directive_ids,
        tactic_ids=tactic_ids,
        styleguide_ids=styleguide_ids,
        toolguide_ids=toolguide_ids,
        service=_build_doctrine_service(repo_root, org_roots=[org_root] if org_root else None),
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


def _render_bootstrap_text(
    *,
    charter_path: Path,
    action: str,
    summary: list[str],
    doctrine_bundle: _ActionDoctrineBundle,
    references: list[dict[str, str]],
    effective_depth: int,
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

    # WP04 (FR-003) — authority paths block, sliced between Policy Summary
    # and the action-critical bodies so the resolved-context anchor order
    # documented in data-model.md §3 holds.
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

    # WP04 (FR-001) — action-critical charter section bodies.  When a
    # heading is absent from the charter the renderer emits a fetch
    # stanza, so the executing agent has a recovery path either way.
    section_block = render_critical_section_bodies(charter_content, action)
    if section_block:
        lines.append("")
        lines.append(section_block)

    profile_block = _render_profile_sections(profile, service)
    if profile_block:
        lines.append("")
        lines.append(profile_block)

    # WP04 (FR-005) — charter-level global selection rendering.  The
    # combined 5-kind block surfaces every artifact named in
    # ``DoctrineSelectionConfig.selected_<kind>`` (with provenance
    # disclosure for org-distributed entries).
    selection_block = _render_selection_block(
        doctrine_selection, service, repo_root=repo_root
    )
    if selection_block:
        lines.append("")
        lines.append(selection_block)

    # WP04 T023 — activation-registry hook (FR-007).  The renderer body
    # is WP05's surface (``charter._activation_render``); WP04 only
    # ships the call site so the wire is exercised end-to-end as soon
    # as WP05 lands.  Until then the stub returns ``""``.
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

    # WP07 T035/T036 (FR-001, Option B) — compute org-layer provenance map ONCE
    # and pass it to each _extend_named_artifact_lines call so org-contributed
    # artifacts carry a ``(source: org:<pack>)`` suffix.  Returns {} when no org
    # packs are configured → NFR-001 byte-stability preserved (23 fixtures unchanged).
    _all_action_ids = (
        doctrine_bundle.directive_ids
        + doctrine_bundle.tactic_ids
        + doctrine_bundle.styleguide_ids
        + doctrine_bundle.toolguide_ids
    )
    _action_org_source_map = (
        _build_action_org_source_map(repo_root, _all_action_ids)
        if repo_root is not None and _all_action_ids
        else {}
    )

    _extend_named_artifact_lines(lines, "Directives", doctrine_bundle.directive_ids, service.directives, "title", "intent", org_source_map=_action_org_source_map)  # type: ignore[attr-defined]
    _extend_named_artifact_lines(lines, "Tactics", doctrine_bundle.tactic_ids, service.tactics, "name", "purpose", org_source_map=_action_org_source_map)  # type: ignore[attr-defined]

    if effective_depth >= _EXTENDED_CONTEXT_DEPTH:
        _service_any: Any = service
        _extend_named_artifact_lines(
            lines, "Styleguides", doctrine_bundle.styleguide_ids,
            _service_any.styleguides, "title", None, org_source_map=_action_org_source_map,
        )
        _extend_named_artifact_lines(
            lines, "Toolguides", doctrine_bundle.toolguide_ids,
            _service_any.toolguides, "title", None, org_source_map=_action_org_source_map,
        )

    _append_guidelines_lines(lines, doctrine_bundle.mission, action)

    if is_spdd_reasons_active(charter_path.parent.parent.parent):
        append_spdd_reasons_guidance(lines, doctrine_bundle.mission, action)

    lines.append("")
    lines.append(REFERENCE_DOCS_HEADER)
    filtered_references = _filter_references_for_action(references, action)
    if filtered_references:
        for reference in filtered_references[:10]:
            ref_id = reference.get("id", "unknown")
            title = reference.get("title", "")
            local_path = reference.get("local_path", "")
            lines.append(f"  - {ref_id}: {title} ({local_path})")
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


def _extend_named_artifact_lines(
    lines: list[str],
    heading: str,
    artifact_ids: list[str],
    repository: object,
    title_attr: str,
    summary_attr: str | None,
    org_source_map: dict[str, str] | None = None,
) -> None:
    """Append formatted artifact lines when the bucket is non-empty.

    When *org_source_map* is provided, each artifact contributed by an org
    pack receives a ``(source: org:<pack>)`` suffix (Option B — additive only
    when an org pack is present, preserving NFR-001 byte-stability when no
    org packs are configured).
    """
    if not artifact_ids:
        return

    formatted: list[str] = []
    for artifact_id in artifact_ids:
        suffix = _provenance_suffix(artifact_id, org_source_map)
        artifact = repository.get(artifact_id)  # type: ignore[attr-defined]
        if artifact is None:
            formatted.append(f"    - {artifact_id}{suffix}")
            continue
        title = getattr(artifact, title_attr)
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


def _build_directive_lines(
    action_index: object,
    project_directives: set[str],
    doctrine_service: object,
) -> list[str]:
    """Build formatted directive lines for the action doctrine section."""
    directive_lines: list[str] = []
    for raw_id in action_index.directives:  # type: ignore[attr-defined]
        norm_id = _normalize_directive_id(raw_id)
        if project_directives and norm_id not in project_directives:
            continue
        try:
            directive = doctrine_service.directives.get(norm_id)  # type: ignore[attr-defined]
            if directive is not None:
                directive_lines.append(f"    - {norm_id}: {directive.title} — {directive.intent}")
            else:
                directive_lines.append(f"    - {norm_id}")
        except (AttributeError, KeyError):
            directive_lines.append(f"    - {norm_id}")
    return directive_lines


def _build_tactic_lines(action_index: object, doctrine_service: object) -> list[str]:
    """Build formatted tactic lines for the action doctrine section."""
    tactic_lines: list[str] = []
    for tactic_id in action_index.tactics:  # type: ignore[attr-defined]
        try:
            tactic = doctrine_service.tactics.get(tactic_id)  # type: ignore[attr-defined]
            if tactic is not None:
                desc = tactic.description or ""
                tactic_lines.append(f"    - {tactic_id}: {tactic.title} — {desc}".rstrip(" —"))
            else:
                tactic_lines.append(f"    - {tactic_id}")
        except (AttributeError, KeyError):
            tactic_lines.append(f"    - {tactic_id}")
    return tactic_lines


def _build_extended_lines(action_index: object, doctrine_service: object) -> list[str]:
    """Build styleguide + toolguide lines for depth-3 extended context."""
    extended: list[str] = []

    styleguide_lines: list[str] = []
    for sg_id in action_index.styleguides:  # type: ignore[attr-defined]
        try:
            sg = doctrine_service.styleguides.get(sg_id)  # type: ignore[attr-defined]
            styleguide_lines.append(f"    - {sg_id}: {sg.title}" if sg else f"    - {sg_id}")
        except (AttributeError, KeyError):
            styleguide_lines.append(f"    - {sg_id}")

    if styleguide_lines:
        extended.append("  Styleguides:")
        extended.extend(styleguide_lines)

    toolguide_lines: list[str] = []
    for tg_id in action_index.toolguides:  # type: ignore[attr-defined]
        try:
            tg = doctrine_service.toolguides.get(tg_id)  # type: ignore[attr-defined]
            toolguide_lines.append(f"    - {tg_id}: {tg.title}" if tg else f"    - {tg_id}")
        except (AttributeError, KeyError):
            toolguide_lines.append(f"    - {tg_id}")

    if toolguide_lines:
        extended.append("  Toolguides:")
        extended.extend(toolguide_lines)

    return extended


def _append_action_doctrine_lines(
    lines: list[str],
    repo_root: Path,
    action: str,
    *,
    include_extended: bool,
) -> None:
    """Append action doctrine content to lines list. Degrades gracefully on error."""
    from doctrine.missions import MissionTemplateRepository
    from doctrine.missions.action_index import load_action_index

    try:
        repo = MissionTemplateRepository.default()
        doctrine_selection = _load_doctrine_selection(repo_root)
        template_set = doctrine_selection.template_set or "software-dev-default"
        mission = template_set.removesuffix("-default")
        action_index = load_action_index(repo._missions_root, mission, action)
        project_directives: set[str] = {_normalize_directive_id(d) for d in doctrine_selection.selected_directives}
        doctrine_service = _build_doctrine_service(repo_root)

        lines.append(f"Action Doctrine ({action}):")

        directive_lines = _build_directive_lines(action_index, project_directives, doctrine_service)
        if directive_lines:
            lines.append("  Directives:")
            lines.extend(directive_lines)

        tactic_lines = _build_tactic_lines(action_index, doctrine_service)
        if tactic_lines:
            lines.append("  Tactics:")
            lines.extend(tactic_lines)

        if include_extended:
            lines.extend(_build_extended_lines(action_index, doctrine_service))

        # Action guidelines
        guidelines_result = repo.get_action_guidelines(mission, action)
        if guidelines_result is not None:
            guidelines_content = guidelines_result.content.strip()
            if guidelines_content:
                lines.append("  Guidelines:")
                for gl_line in guidelines_content.splitlines():
                    lines.append(f"    {gl_line}")

    except Exception:  # noqa: BLE001, S110
        # Degrade gracefully - skip action doctrine section on any error
        pass


def _render_action_scoped(
    repo_root: Path,
    action: str,
    charter_path: Path,
    summary: list[str],
    references: list[dict[str, str]],
    *,
    include_extended: bool = False,
) -> str:
    """Render action-scoped bootstrap context (depth >= 2).

    Loads the action index, intersects project directives, fetches doctrine
    content, and renders a structured context block.
    """
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

    lines.append("")

    _append_action_doctrine_lines(lines, repo_root, action, include_extended=include_extended)

    lines.append("")

    # --- Reference Docs section ---
    lines.append(REFERENCE_DOCS_HEADER)

    filtered_references = _filter_references_for_action(references, action)

    if filtered_references:
        for reference in filtered_references[:10]:
            ref_id = reference.get("id", "unknown")
            title = reference.get("title", "")
            local_path = reference.get("local_path", "")
            lines.append(f"  - {ref_id}: {title} ({local_path})")
    else:
        lines.append(MISSING_REFERENCES_MESSAGE)

    return "\n".join(lines)


def _filter_references_for_action(references: list[dict[str, str]], action: str) -> list[dict[str, str]]:
    """Filter references for a specific action.

    Non-local_support references are always included.
    For local_support references:
      - If the summary contains "(action: XXX)", include only if XXX matches the requested action.
      - If no "(action: ...)" appears in the summary, include (global).
    """
    filtered: list[dict[str, str]] = []
    for ref in references:
        kind = ref.get("kind", "")
        if kind != "local_support":
            filtered.append(ref)
            continue

        # local_support: check summary for action scope
        summary = ref.get("summary", ref.get("title", ""))
        action_match = re.search(r"\(action:\s*(\w+)\)", summary)
        if action_match:
            ref_action = action_match.group(1).strip().lower()
            if ref_action == action.lower():
                filtered.append(ref)
        else:
            # No action scope in summary → include globally
            filtered.append(ref)

    return filtered


def _render_bootstrap(charter_path: Path, summary: list[str], references: list[dict[str, str]]) -> str:
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

    lines.append("")
    lines.append(REFERENCE_DOCS_HEADER)
    if references:
        for reference in references[:10]:
            ref_id = reference.get("id", "unknown")
            title = reference.get("title", "")
            local_path = reference.get("local_path", "")
            lines.append(f"  - {ref_id}: {title} ({local_path})")
    else:
        lines.append(MISSING_REFERENCES_MESSAGE)

    return "\n".join(lines)


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

    header = _PROFILE_TACTICS_HEADER_TPL.format(profile_id=profile.profile_id)
    lines: list[str] = [header]
    repo = getattr(service, "tactics", None)

    for ref in refs:
        tactic_id = str(getattr(ref, "id", "")).strip()
        rationale = getattr(ref, "rationale", "") or ""
        header_line = f"  - {tactic_id}"
        if rationale:
            header_line = f"{header_line}: {rationale}"
        lines.append(header_line)

        tactic = None
        if repo is not None:
            try:
                tactic = repo.get(tactic_id)
            except Exception:  # noqa: BLE001 — best-effort catalog lookup
                tactic = None

        if tactic is None:
            # RISK-3 (Mission B post-merge): structured catalog-miss
            # stanza + warning instead of the generic placeholder.
            # FR-013: _diagnose_catalog_miss checks scope_filtered_ids
            # first so a scope-filtered tactic surfaces SCOPE_FILTERED
            # rather than MISSING_ARTIFACT.
            diagnosis = _diagnose_catalog_miss(tactic_id, repo)
            lines.extend(
                format_catalog_miss_stanza(
                    selector_kind="tactic",
                    artifact_id=tactic_id,
                    diagnosis=diagnosis,
                    indent="    ",
                )
            )
            emit_catalog_miss_warning(
                selector_kind="tactic",
                artifact_id=tactic_id,
                diagnosis=diagnosis,
                context=f"profile:{profile.profile_id}",
            )
            continue

        body_lines: list[str] = []
        name = getattr(tactic, "name", None)
        if isinstance(name, str) and name:
            body_lines.append(f"    Name: {name}")
        purpose = getattr(tactic, "purpose", None)
        if isinstance(purpose, str) and purpose.strip():
            body_lines.append(f"    Purpose: {purpose.strip()}")
        steps = getattr(tactic, "steps", None)
        if isinstance(steps, list) and steps:
            body_lines.append("    Steps:")
            for step in steps:
                step_title = getattr(step, "title", str(step))
                body_lines.append(f"      - {step_title}")

        if body_lines and _budget_estimate(body_lines) <= _PROFILE_INLINE_BODY_LIMIT_CHARS:
            lines.extend(body_lines)
        else:
            lines.extend(
                _render_fetch_stanza(
                    selector=f"tactic:{tactic_id}",
                    when_clause="are about to apply a code change",
                )
            )

    return lines


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
    repository: object | None,
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
                artifact = repository.get(artifact_id)  # type: ignore[attr-defined]
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
    repository: object,
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
            source = repository.get_provenance(artifact_id)  # type: ignore[attr-defined]
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

    Returns ``""`` when the activation list is empty, when the WP05
    renderer is still a stub, or when any error is raised by the
    renderer (defensive — the prompt build hot path must not crash).
    """
    if repo_root is None:
        return ""
    activations = _load_governance_activations(repo_root)
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
    """Render the combined profile-cited directive + tactic sections.

    Returns an empty string when *profile* is ``None`` or when neither
    section has any entries — callers can then skip the leading blank
    line without emitting a stray section header.
    """
    if profile is None:
        return ""
    directive_lines = _render_profile_directives(profile, service)
    tactic_lines = _render_profile_tactics(profile, service)
    blocks: list[str] = []
    if directive_lines:
        blocks.append("\n".join(directive_lines))
    if tactic_lines:
        blocks.append("\n".join(tactic_lines))
    return "\n\n".join(blocks)


def _render_compact_governance(
    repo_root: Path,
    *,
    directive_ids: list[str] | None = None,
    tactic_ids: list[str] | None = None,
    profile: AgentProfile | None = None,
    action: str | None = None,
) -> str:
    """Render the compact governance block (FR-034).

    Compact mode preserves every directive ID, tactic ID, and section
    anchor that bootstrap mode would emit; only the long-form prose
    body is collapsed. ``directive_ids`` / ``tactic_ids`` are optional
    bootstrap-side lists that the caller has already resolved; when
    omitted the compact view falls back to the resolver's directive
    canon.

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

    if action:
        charter_path = repo_root / KITTIFY_DIRNAME / "charter" / CHARTER_FILENAME
        if charter_path.exists():
            try:
                charter_content = charter_path.read_text(encoding="utf-8")
            except OSError:
                charter_content = ""
            section_block = render_critical_section_bodies(charter_content, action)
            if section_block:
                augmented_blocks.append(section_block)

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
    section_block_str = ""
    if action:
        charter_path = repo_root / KITTIFY_DIRNAME / "charter" / CHARTER_FILENAME
        if charter_path.exists():
            try:
                charter_content = charter_path.read_text(encoding="utf-8")
            except OSError:
                charter_content = ""
            section_block_str = render_critical_section_bodies(charter_content, action or "")
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


def _load_references(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    yaml = YAML(typ="safe")
    try:
        data = yaml.load(path.read_text(encoding="utf-8")) or {}
    except (YAMLError, UnicodeDecodeError, OSError):
        return []

    raw_references = data.get("references") if isinstance(data, dict) else []
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


def _artifact_to_dict(artifact: object, source: str) -> dict[str, object]:
    """Render a single doctrine artifact for the JSON ``charter context`` output.

    The returned mapping always carries an ``id`` and a ``source`` field;
    additional fields are extracted on a best-effort basis.  Unknown layer
    sources fall back to ``"builtin"`` (the safest default — "we don't know,
    assume "built-in"").
    """
    item_id = getattr(artifact, "id", None)
    title = getattr(artifact, "title", None) or getattr(artifact, "name", None)
    summary = getattr(artifact, "intent", None) or getattr(artifact, "purpose", None)
    out: dict[str, object] = {
        "id": item_id if isinstance(item_id, str) else "",
        "source": source if source in {"builtin", "org", "project"} else "builtin",
    }
    if isinstance(title, str) and title:
        out["title"] = title
    if isinstance(summary, str) and summary:
        out["summary"] = summary
    return out


def _collect_typed_artifacts(
    repository: object,
    artifact_ids: list[str],
) -> list[dict[str, object]]:
    """Look up artifacts in *repository* and emit JSON entries tagged with provenance."""
    entries: list[dict[str, object]] = []
    for artifact_id in artifact_ids:
        try:
            artifact = repository.get(artifact_id)  # type: ignore[attr-defined]
            source = repository.get_provenance(artifact_id) or "builtin"  # type: ignore[attr-defined]
        except (AttributeError, KeyError):
            artifact, source = None, "builtin"
        if artifact is None:
            entries.append({"id": artifact_id, "source": source})
            continue
        entries.append(_artifact_to_dict(artifact, source))
    return entries


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
    charter_path = charter_dir / CHARTER_FILENAME
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
        entries.extend(_collect_typed_artifacts(service.directives, [directive_id]))  # type: ignore[attr-defined]
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


def _maybe_build_doctrine_service(repo_root: Path) -> object | None:
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
        payload["mode"] = "compact"
        return payload

    state_bundle = _prepare_context_state(repo_root, normalized, depth)
    payload["mode"] = "bootstrap"
    if state_bundle.effective_depth < _MIN_EFFECTIVE_DEPTH:
        return payload

    from charter.pack_context import PackContext as _PackContext  # noqa: PLC0415

    _pack_ctx_json = _PackContext.from_config(repo_root)
    bundle = _load_action_doctrine_bundle(
        repo_root=repo_root,
        action=normalized,
        effective_depth=state_bundle.effective_depth,
        org_root=org_root,
        pack_context=_pack_ctx_json,
    )
    service = bundle.service
    payload["directives"] = _collect_typed_artifacts(service.directives, bundle.directive_ids)  # type: ignore[attr-defined]
    payload["tactics"] = _collect_typed_artifacts(service.tactics, bundle.tactic_ids)  # type: ignore[attr-defined]
    payload["styleguides"] = _collect_typed_artifacts(service.styleguides, bundle.styleguide_ids)  # type: ignore[attr-defined]
    payload["toolguides"] = _collect_typed_artifacts(service.toolguides, bundle.toolguide_ids)  # type: ignore[attr-defined]
    return payload
