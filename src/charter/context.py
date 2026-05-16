"""Charter context bootstrap for prompt generation."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from charter._doctrine_paths import resolve_project_root
from charter.context_renderers import (
    BUDGET_DEFAULT,
    RenderedSection,
    render_authority_paths,
    render_critical_section_bodies,
)
from charter.context_renderers.fetch_stanza import (
    fetch_stanza_lines as _shared_fetch_stanza_lines,
)
from charter.language_scope import infer_repo_languages
from charter.schemas import DoctrineSelectionConfig
from doctrine.agent_profiles import AgentProfile, AgentProfileRepository
from doctrine.spdd_reasons import append_spdd_reasons_guidance, is_spdd_reasons_active
from kernel.atomic import atomic_write

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


def build_charter_context(
    repo_root: Path,
    *,
    profile: str | None = None,
    action: str,
    mark_loaded: bool = True,
    depth: int | None = None,
    org_root: Path | None = None,
) -> CharterContextResult:
    """Build charter context by querying the Doctrine Reference Graph.

    Parameters
    ----------
    org_root:
        Optional path to the configured org doctrine snapshot.  When provided,
        the three-layer (shipped + org + project) DRG overlay is used and the
        ``DoctrineService`` is constructed with the org layer included.
        Charter-layer callers leave this as ``None``; ``specify_cli`` callers
        resolve the value via :func:`specify_cli.doctrine.config.resolve_org_roots`
        and pass it explicitly (preserving the kernel <- doctrine <- charter <-
        specify_cli dependency direction).
    """
    profile_record = _load_agent_profile(profile) if profile else None

    from charter.sync import ensure_charter_bundle_fresh

    sync_result = ensure_charter_bundle_fresh(repo_root)
    canonical_root = sync_result.canonical_root if sync_result and sync_result.canonical_root else repo_root

    normalized = action.strip().lower()
    charter_path = canonical_root / KITTIFY_DIRNAME / "charter" / "charter.md"
    references_path = canonical_root / KITTIFY_DIRNAME / "charter" / "references.yaml"

    if normalized not in BOOTSTRAP_ACTIONS:
        effective_depth = depth if depth is not None else 1
        return CharterContextResult(
            action=normalized,
            mode="compact",
            first_load=False,
            text=_render_compact_governance(repo_root, profile=profile_record, action=normalized),
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
            text=text,
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
            text=_render_compact_governance(repo_root, profile=profile_record, action=normalized),
            references_count=0,
            depth=state_bundle.effective_depth,
        )

    doctrine_bundle = _load_action_doctrine_bundle(
        repo_root=repo_root,
        action=normalized,
        effective_depth=state_bundle.effective_depth,
        org_root=org_root,
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
        text=text,
        references_count=len(references),
        depth=state_bundle.effective_depth,
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
    merged: object,
    project_directives: set[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Partition resolved artifact URNs into doctrine-type buckets."""
    from doctrine.drg.models import NodeKind

    directive_ids: list[str] = []
    tactic_ids: list[str] = []
    styleguide_ids: list[str] = []
    toolguide_ids: list[str] = []
    for urn in sorted(artifact_urns):
        node = merged.get_node(urn)  # type: ignore[attr-defined]
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


def _load_doctrine_selection(repo_root: Path) -> DoctrineSelectionConfig:
    """Return the charter's :class:`DoctrineSelectionConfig` for *repo_root*.

    Best-effort lookup: any failure (missing governance.yaml, parse
    error, unexpected exception) collapses to a default-constructed
    :class:`DoctrineSelectionConfig`.  This keeps the resolver hot path
    resilient (NFR-005) so a malformed governance file never crashes
    prompt rendering — the authority-paths block will simply lack
    charter-declared entries.
    """

    from charter.sync import load_governance_config

    try:
        governance = load_governance_config(repo_root)
    except Exception:  # noqa: BLE001 — best-effort governance load
        return DoctrineSelectionConfig()
    return governance.doctrine


def _load_action_doctrine_bundle(
    *,
    repo_root: Path,
    action: str,
    effective_depth: int,
    org_root: Path | None = None,
) -> _ActionDoctrineBundle:
    """Load DRG-backed action doctrine artifacts for bootstrap rendering."""
    from charter._drg_helpers import load_validated_graph
    from charter.sync import load_governance_config
    from doctrine.drg.query import resolve_context

    # WP07 T034: route the DRG load through the shared helper so the shipped +
    # org + project three-layer overlay is honoured.  Callers in ``specify_cli``
    # supply *org_root* explicitly; charter-internal callers pass ``None`` and
    # get the two-layer (shipped + project) merge.
    merged = load_validated_graph(repo_root, org_root=org_root)

    governance = load_governance_config(repo_root)
    mission = (governance.doctrine.template_set or "software-dev-default").removesuffix("-default")
    project_directives = {_normalize_directive_id(d) for d in governance.doctrine.selected_directives}
    action_urn = f"action:{mission}/{action}"
    resolved = resolve_context(merged, action_urn, depth=effective_depth)

    directive_ids, tactic_ids, styleguide_ids, toolguide_ids = _classify_artifact_urns(
        resolved.artifact_urns, merged, project_directives
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

    lines.append("")
    lines.append(f"Action Doctrine ({action}):")
    _extend_named_artifact_lines(lines, "Directives", doctrine_bundle.directive_ids, service.directives, "title", "intent")  # type: ignore[attr-defined]
    _extend_named_artifact_lines(lines, "Tactics", doctrine_bundle.tactic_ids, service.tactics, "name", "purpose")  # type: ignore[attr-defined]

    if effective_depth >= _EXTENDED_CONTEXT_DEPTH:
        _extend_named_artifact_lines(lines, "Styleguides", doctrine_bundle.styleguide_ids, service.styleguides, "title", None)  # type: ignore[attr-defined]
        _extend_named_artifact_lines(lines, "Toolguides", doctrine_bundle.toolguide_ids, service.toolguides, "title", None)  # type: ignore[attr-defined]

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
        if len(current_text) <= budget:
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
) -> None:
    """Append formatted artifact lines when the bucket is non-empty."""
    if not artifact_ids:
        return

    formatted: list[str] = []
    for artifact_id in artifact_ids:
        artifact = repository.get(artifact_id)  # type: ignore[attr-defined]
        if artifact is None:
            formatted.append(f"    - {artifact_id}")
            continue
        title = getattr(artifact, title_attr)
        summary = getattr(artifact, summary_attr) if summary_attr else None
        if isinstance(summary, str) and summary:
            formatted.append(f"    - {artifact_id}: {title} — {summary}")
        else:
            formatted.append(f"    - {artifact_id}: {title}")

    lines.append(f"  {heading}:")
    lines.extend(formatted)


def _build_doctrine_service(repo_root: Path, *, org_roots: list[Path] | None = None) -> object:
    """Build a DoctrineService for the given repo root.

    The project-root candidate list (in priority order):
    1. ``.kittify/doctrine/``  — Phase 3 synthesis target (FR-009 / T025).
    2. ``src/doctrine/``       — code-local shipped-layer path.
    3. ``doctrine/``           — flat fallback.

    Discovery is conditional on directory presence so legacy (pre-synthesis)
    projects see byte-identical behaviour (R-2 mitigation).

    Cross-reference: ``compiler._default_doctrine_service`` uses the same
    ``resolve_project_root`` helper from ``charter._doctrine_paths``.

    WP07: callers in ``specify_cli`` may supply explicit *org_roots* (a list
    of org doctrine snapshot paths) so the resulting service includes the
    configured org layer in provenance tracking.  Charter-internal callers
    omit the argument and get the shipped-plus-project baseline.
    """
    from doctrine.service import DoctrineService
    from charter.catalog import resolve_doctrine_root

    doctrine_root = resolve_doctrine_root()
    project_root = resolve_project_root(repo_root)
    kwargs: dict[str, object] = {
        "shipped_root": doctrine_root,
        "project_root": project_root,
        "active_languages": infer_repo_languages(repo_root),
    }
    # Only pass ``org_roots`` when it carries paths so charter-internal
    # callers see byte-identical kwargs (preserves existing test stubs and
    # downstream constructors that may not declare the parameter).
    if org_roots:
        kwargs["org_roots"] = org_roots
    return DoctrineService(**kwargs)


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
    from charter.sync import load_governance_config

    try:
        repo = MissionTemplateRepository.default()
        governance = load_governance_config(repo_root)
        template_set = governance.doctrine.template_set or "software-dev-default"
        mission = template_set.removesuffix("-default")
        action_index = load_action_index(repo._missions_root, mission, action)
        project_directives: set[str] = {_normalize_directive_id(d) for d in governance.doctrine.selected_directives}
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


def _default_agent_profile_repository() -> AgentProfileRepository:
    """Return a process-wide cached :class:`AgentProfileRepository`.

    The repository is constructed lazily on first call and reused for the
    lifetime of the interpreter. Tests that need a clean repository can
    reset the cache via :func:`_reset_agent_profile_cache`.
    """
    global _DEFAULT_AGENT_PROFILE_REPO
    if _DEFAULT_AGENT_PROFILE_REPO is None:
        _DEFAULT_AGENT_PROFILE_REPO = AgentProfileRepository()
    return _DEFAULT_AGENT_PROFILE_REPO


def _reset_agent_profile_cache() -> None:
    """Clear the cached default :class:`AgentProfileRepository` (test hook)."""
    global _DEFAULT_AGENT_PROFILE_REPO
    _DEFAULT_AGENT_PROFILE_REPO = None


def _load_agent_profile(profile_id: str) -> AgentProfile | None:
    """Resolve *profile_id* via the doctrine layer. Returns ``None`` on miss.

    Errors are intentionally swallowed: this helper is on the prompt-build
    hot path and must never raise into the resolver. A diagnostic is logged
    at WARNING level so operators can audit unknown profile IDs without the
    prompt collapsing.
    """
    try:
        record = _default_agent_profile_repository().get(profile_id)
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
    return _shared_fetch_stanza_lines(selector, when_clause, indent="    ")


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
            lines.append("    (catalog entry not found; verify profile references)")
            _LOGGER.warning(
                "Profile '%s' cites directive '%s' but the catalog does not "
                "carry it; rendered as fetch-only.",
                profile.profile_id,
                code,
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
            lines.append("    (catalog entry not found; verify profile references)")
            _LOGGER.warning(
                "Profile '%s' cites tactic '%s' but the catalog does not "
                "carry it; rendered as fetch-only.",
                profile.profile_id,
                tactic_id,
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

    if action:
        charter_path = repo_root / KITTIFY_DIRNAME / "charter" / "charter.md"
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
        charter_path = repo_root / KITTIFY_DIRNAME / "charter" / "charter.md"
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
    assume shipped").
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
    * ``directives`` / ``tactics`` / ``styleguides`` / ``toolguides`` — typed
      artifact arrays, each entry carrying a ``"source"`` provenance field
      (``"builtin"`` | ``"org"`` | ``"project"``).
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
        "org_charter": (
            dict(org_charter_block) if org_charter_block is not None else dict(_EMPTY_ORG_CHARTER)
        ),
    }

    if normalized not in BOOTSTRAP_ACTIONS:
        payload["mode"] = "compact"
        return payload

    state_bundle = _prepare_context_state(repo_root, normalized, depth)
    payload["mode"] = "bootstrap"
    if state_bundle.effective_depth < _MIN_EFFECTIVE_DEPTH:
        return payload

    bundle = _load_action_doctrine_bundle(
        repo_root=repo_root,
        action=normalized,
        effective_depth=state_bundle.effective_depth,
        org_root=org_root,
    )
    service = bundle.service
    payload["directives"] = _collect_typed_artifacts(service.directives, bundle.directive_ids)  # type: ignore[attr-defined]
    payload["tactics"] = _collect_typed_artifacts(service.tactics, bundle.tactic_ids)  # type: ignore[attr-defined]
    payload["styleguides"] = _collect_typed_artifacts(service.styleguides, bundle.styleguide_ids)  # type: ignore[attr-defined]
    payload["toolguides"] = _collect_typed_artifacts(service.toolguides, bundle.toolguide_ids)  # type: ignore[attr-defined]
    return payload
