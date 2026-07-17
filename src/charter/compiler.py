"""Charter compiler: interview answers + doctrine assets -> charter bundle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, UTC
from io import StringIO
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML

from charter._doctrine_paths import resolve_project_root
from charter._io import load_charter_file
from charter.catalog import DoctrineCatalog, load_doctrine_catalog, resolve_doctrine_root
from charter.interview import (
    CharterInterview,
    LocalSupportDeclaration,
    validate_local_support_declarations,
)
from charter.kind_vocabulary import ArtifactKind, resolve_artifact_urn
from charter.language_scope import extract_declared_languages
from charter.pack_context import PackContext
from charter.resolver import DEFAULT_TOOL_REGISTRY

__all__ = [
    "CharterReference",
    "CompiledCharter",
    "WriteBundleResult",
    "compile_charter",
    "resolve_config_activated_roots",
    "resolve_synthesis_graph_directives",
    "write_compiled_charter",
]
# NOTE: ``ConfigActivatedRoots`` is intentionally NOT public API -- it is the
# return type of ``resolve_config_activated_roots`` but every real caller
# (e.g. ``specify_cli.cli.commands.charter._synthesis``) consumes the
# returned instance by attribute access and never imports the class name
# itself; only its own test module imports it directly, which does not
# count as a caller under ``test_no_public_symbol_in_all_is_unimported``
# (WP05/T021b, mission unify-charter-activation-surfaces-01KX5SJ9).



@dataclass(frozen=True)
class _SelectionBundle:
    """Bundled paradigm + directive selections passed to service-based reference builders."""

    paradigms: list[str]
    directives: list[str]


@dataclass(frozen=True)
class ConfigActivatedRoots:
    """Config-sourced activation roots (FR-001/FR-002), resolved to bare DRG ids.

    Replaces the retired ``answers.selected_*`` derivation source (WP02,
    IC-01). Directives and paradigms feed the legacy pipelines unchanged
    (directive-closure seed; paradigm direct YAML load); tactics, styleguides,
    toolguides, procedures, and agent profiles are *additionally* seeded as
    direct roots (T026) so an artefact activated directly in
    ``config.activated_*`` resolves in the compiled set even when no selected
    directive's transitive closure reaches it.
    """

    directives: list[str]
    paradigms: list[str]
    tactics: list[str]
    styleguides: list[str]
    toolguides: list[str]
    procedures: list[str]
    agent_profiles: list[str]


def _resolve_config_activated_ids(
    kind: ArtifactKind,
    activated_stems: frozenset[str] | None,
    *,
    doctrine_root: Path,
    fallback_ids: frozenset[str],
    org_roots: list[Path] | None = None,
) -> list[str]:
    """Resolve ``config.activated_<kind>`` stems to bare canonical DRG ids.

    ``activated_stems is None`` mirrors the three-state semantics documented
    on :class:`charter.pack_context.PackContext`: the key is absent from
    ``.kittify/config.yaml`` (or no project config is available at all), so
    every built-in id for *kind* is available -- the same default already
    applied by ``charter.resolver`` when filtering paradigms/procedures/agent
    profiles.

    *org_roots* extends the artefact scan to org/project-overlay pack roots
    (:attr:`charter.pack_context.PackContext.pack_roots`, sans the built-in
    root at index 0) so a config-activated ORG artefact resolves instead of
    raising -- an activated stem that only exists in an org pack is not an
    unknown id (#2529).

    A stem that cannot be resolved to a canonical id (in *either* the
    built-in doctrine root or an org root) raises
    :class:`~charter.kind_vocabulary.UnknownArtifactIdError` (propagated from
    :func:`~charter.kind_vocabulary.resolve_artifact_urn`) rather than being
    silently dropped -- this closes the C-006 silent-drop vector that
    ``_sanitize_catalog_selection`` left open for the answers-sourced path.
    """
    if activated_stems is None:
        return sorted(fallback_ids)

    resolved = {
        resolve_artifact_urn(kind, stem, doctrine_root=doctrine_root, org_roots=org_roots).split(":", 1)[1]
        for stem in activated_stems
    }
    return sorted(resolved)


def _resolve_config_activated_roots(
    *,
    pack_context: PackContext | None,
    catalog: DoctrineCatalog,
    doctrine_root: Path,
) -> ConfigActivatedRoots:
    """Build the full config-sourced activation bundle for one compile."""

    def _stems(field_name: str) -> frozenset[str] | None:
        return getattr(pack_context, field_name) if pack_context is not None else None

    # ``pack_context.pack_roots`` is ``(builtin_root, *org_pack_roots)``
    # (``PackContext.from_config``); the built-in root is already threaded
    # separately as ``doctrine_root``, so only the org/project-overlay
    # entries need to be passed to the resolver. Empty for non-org projects
    # (no behavior change) -- see #2529.
    org_roots: list[Path] | None = list(pack_context.pack_roots[1:]) if pack_context is not None else None

    return ConfigActivatedRoots(
        directives=_resolve_config_activated_ids(
            ArtifactKind.DIRECTIVE,
            _stems("activated_directives"),
            doctrine_root=doctrine_root,
            fallback_ids=catalog.directives,
            org_roots=org_roots,
        ),
        paradigms=_resolve_config_activated_ids(
            ArtifactKind.PARADIGM,
            _stems("activated_paradigms"),
            doctrine_root=doctrine_root,
            fallback_ids=catalog.paradigms,
            org_roots=org_roots,
        ),
        tactics=_resolve_config_activated_ids(
            ArtifactKind.TACTIC,
            _stems("activated_tactics"),
            doctrine_root=doctrine_root,
            fallback_ids=catalog.tactics,
            org_roots=org_roots,
        ),
        styleguides=_resolve_config_activated_ids(
            ArtifactKind.STYLEGUIDE,
            _stems("activated_styleguides"),
            doctrine_root=doctrine_root,
            fallback_ids=catalog.styleguides,
            org_roots=org_roots,
        ),
        toolguides=_resolve_config_activated_ids(
            ArtifactKind.TOOLGUIDE,
            _stems("activated_toolguides"),
            doctrine_root=doctrine_root,
            fallback_ids=catalog.toolguides,
            org_roots=org_roots,
        ),
        procedures=_resolve_config_activated_ids(
            ArtifactKind.PROCEDURE,
            _stems("activated_procedures"),
            doctrine_root=doctrine_root,
            fallback_ids=catalog.procedures,
            org_roots=org_roots,
        ),
        agent_profiles=_resolve_config_activated_ids(
            ArtifactKind.AGENT_PROFILE,
            _stems("activated_agent_profiles"),
            doctrine_root=doctrine_root,
            fallback_ids=catalog.agent_profiles,
            org_roots=org_roots,
        ),
    )


def _direct_root_urns(config_roots: ConfigActivatedRoots) -> frozenset[str]:
    """Direct-activation root URNs (WP02 T026).

    These are the kinds that may be activated directly in
    ``config.activated_*`` with no directive edge reaching them (e.g. a
    styleguide or toolguide with only a ``suggests`` edge from an
    unreachable tactic). Directives seed the transitive closure separately
    (see :func:`_resolve_transitive_reference_graph`); paradigms are never
    DRG-reachable and are loaded directly from YAML, so neither appears here.
    """
    urns: set[str] = set()
    urns.update(f"{ArtifactKind.TACTIC.value}:{artifact_id}" for artifact_id in config_roots.tactics)
    urns.update(f"{ArtifactKind.STYLEGUIDE.value}:{artifact_id}" for artifact_id in config_roots.styleguides)
    urns.update(f"{ArtifactKind.TOOLGUIDE.value}:{artifact_id}" for artifact_id in config_roots.toolguides)
    urns.update(f"{ArtifactKind.PROCEDURE.value}:{artifact_id}" for artifact_id in config_roots.procedures)
    urns.update(f"{ArtifactKind.AGENT_PROFILE.value}:{artifact_id}" for artifact_id in config_roots.agent_profiles)
    return frozenset(urns)


def _bare_ids_for_kind(urns: frozenset[str], kind: ArtifactKind) -> list[str]:
    """Strip the ``"<kind>:"`` prefix from every URN in *urns* matching *kind*."""
    prefix = f"{kind.value}:"
    return [urn[len(prefix) :] for urn in urns if urn.startswith(prefix)]


def resolve_config_activated_roots(
    *,
    repo_root: Path,
    doctrine_catalog: DoctrineCatalog | None = None,
) -> ConfigActivatedRoots:
    """Resolve ``.kittify/config.yaml`` ``activated_*`` stems to bare canonical ids.

    Public entry point shared by both FR-002 derivation paths: this module's
    own :func:`compile_charter` (the ``references.yaml`` path) and
    ``specify_cli.cli.commands.charter._synthesis`` (the project-graph path,
    ``interview_snapshot``/``drg_snapshot``). Keeping the config-read + stem
    mapping logic here (rather than duplicating it in ``specify_cli``) is the
    charter/specify_cli layer rule for this mission: config-read and mapping
    logic live in ``charter``; ``specify_cli`` orchestrates.
    """
    catalog = doctrine_catalog or load_doctrine_catalog()
    pack_context = PackContext.from_config(repo_root)
    doctrine_root = resolve_doctrine_root()
    return _resolve_config_activated_roots(
        pack_context=pack_context,
        catalog=catalog,
        doctrine_root=doctrine_root,
    )


def resolve_synthesis_graph_directives(
    repo_root: Path, *, config_roots: ConfigActivatedRoots | None = None
) -> list[str]:
    """The resolved directive list the synthesizer feeds ``graph.yaml``.

    Single authority shared by ``specify_cli.cli.commands.charter._synthesis``
    (``interview_snapshot["selected_directives"]`` / ``drg_snapshot["nodes"]``)
    and ``charter.bundle``'s freshness hash input (WP02, FR-002/FR-004, C-004).

    Absent ``config.activated_directives`` -> ``[]`` (the #2577 fast-follow
    fix): unlike :func:`resolve_config_activated_roots`, which falls back to
    "every built-in directive" for the ``references.yaml`` consumer, this
    consumer must see zero directives on a fresh project with no explicit
    activation yet -- otherwise the DRG/companion-tactic expansion path
    demands companion tactics nobody asked for. See
    :func:`specify_cli.cli.commands.charter._synthesis._build_synthesis_request`
    for the full rationale (only the raw three-state signal, read directly
    from :class:`~charter.pack_context.PackContext`, distinguishes the
    absent-key case from an explicit, possibly-empty activation list).

    *config_roots* is an optional pre-resolved
    :class:`ConfigActivatedRoots`: a caller that already called
    :func:`resolve_config_activated_roots` (e.g. ``_build_synthesis_request``,
    which also needs ``config_roots.paradigms``) passes its instance in so this
    helper does not repeat the uncached ``load_doctrine_catalog()`` (~2s,
    354-file glob). When ``None`` the roots are resolved here, so a caller that
    only has ``repo_root`` (e.g. WP02's ``charter.bundle``) still gets a single
    resolve. The three-state directive signal is always read fresh from
    :class:`~charter.pack_context.PackContext` and is independent of the
    (possibly pre-resolved) roots' catalog fallback.
    """
    pack_context = PackContext.from_config(repo_root)
    if pack_context.activated_directives is None:
        # #2577: the graph consumer sees [] on the absent-key path regardless of
        # the resolved roots. Short-circuit BEFORE resolving so the freshness
        # read (WP02's charter.bundle caller) never pays the uncached
        # load_doctrine_catalog() (~2s, 354-file glob) for a project with no
        # activated directives -- keeps the read within NFR-001/NFR-002.
        return []
    if config_roots is None:
        config_roots = resolve_config_activated_roots(repo_root=repo_root)
    return config_roots.directives


if TYPE_CHECKING:
    from doctrine.service import DoctrineService


@dataclass(frozen=True)
class CharterReference:
    """One reference item used by charter context."""

    id: str
    kind: str
    title: str
    summary: str
    source_path: str
    local_path: str
    content: str


@dataclass(frozen=True)
class CompiledCharter:
    """Compiled charter bundle."""

    mission: str
    template_set: str
    selected_paradigms: list[str]
    selected_directives: list[str]
    available_tools: list[str]
    markdown: str
    references: list[CharterReference]
    diagnostics: list[str] = field(default_factory=list)
    selected_tactics: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    active_languages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WriteBundleResult:
    """Filesystem write result for compiled charter bundle."""

    files_written: list[str]


def compile_charter(
    *,
    mission: str,
    interview: CharterInterview,
    template_set: str | None = None,
    doctrine_catalog: DoctrineCatalog | None = None,
    doctrine_service: DoctrineService | None = None,
    repo_root: Path | None = None,
    pack_context: PackContext | None = None,
) -> CompiledCharter:
    """Compile charter markdown, references manifest, and library docs.

    Artifact loading and transitive reference resolution always prefer the
    typed repository API and DRG-backed path. When *doctrine_service* is not
    supplied, a default service rooted at built-in doctrine (and an optional
    project overlay under *repo_root*) is constructed automatically.

    The activated-doctrine selection (paradigms, directives, tactics,
    styleguides, toolguides, procedures, agent profiles) is sourced from
    ``config.activated_*`` (FR-001/FR-002), never from
    ``interview.selected_*`` -- ``answers.selected_*`` is retired as an
    activation source and is captured purely as an interview record (see
    ``_user_profile_reference``). When *pack_context* is not supplied, it is
    built from ``.kittify/config.yaml`` under *repo_root* (mirroring
    :func:`_default_doctrine_service`); when neither is available, every kind
    resolves to "all built-ins active" -- the same absent-key default
    :class:`~charter.pack_context.PackContext` already documents.

    *interview* is used as-is: doctrine-intent aliasing (e.g. the "Lynn
    Cole" free-text shorthand -> ``DIRECTIVE_039`` + ``deep-module-design``)
    happens at interview *construction* time (``charter.interview``'s
    ``default_interview``/``from_dict``/``apply_answer_overrides``, all of
    which return an already-aliased :class:`CharterInterview`) and, for the
    interactive CLI flow, is promoted into ``config.activated_*`` before
    compilation ever runs (``specify_cli.cli.commands.charter.interview.
    _promote_interview_selections``). Re-aliasing here was a no-op for that
    path and had zero effect on the config-sourced activation set for any
    path (#2530) -- removed rather than re-applied a second time.
    """
    active_languages = extract_declared_languages("\n".join(str(value) for value in interview.answers.values()))
    catalog = doctrine_catalog or load_doctrine_catalog(active_languages=active_languages)
    diagnostics: list[str] = []

    if doctrine_service is None:
        doctrine_service = _default_doctrine_service(repo_root)

    if pack_context is None and repo_root is not None:
        pack_context = PackContext.from_config(repo_root)

    doctrine_root = resolve_doctrine_root()
    config_roots = _resolve_config_activated_roots(
        pack_context=pack_context,
        catalog=catalog,
        doctrine_root=doctrine_root,
    )

    template = _resolve_template_set(mission=mission, requested_template_set=template_set, catalog=catalog)
    available_tools = _sanitize_catalog_selection(
        values=interview.available_tools,
        allowed=set(DEFAULT_TOOL_REGISTRY),
        label="available_tools",
        diagnostics=diagnostics,
    )

    # Validate and normalize local support file declarations.
    valid_local, local_errors = validate_local_support_declarations(
        list(interview.local_supporting_files or [])
    )
    diagnostics.extend(local_errors)

    references = _build_references(
        mission=mission,
        template_set=template,
        interview=interview,
        config_roots=config_roots,
        doctrine_service=doctrine_service,
        repo_root=repo_root,
        diagnostics=diagnostics,
    )

    # Build additive local support references.
    built_in_ids = _build_built_in_concept_ids(references)
    local_references = _build_local_support_references(
        valid_local,
        built_in_ids=built_in_ids,
        diagnostics=diagnostics,
    )
    references = references + local_references

    markdown = _render_charter_markdown(
        mission=mission,
        template_set=template,
        interview=interview,
        selected_paradigms=config_roots.paradigms,
        selected_directives=config_roots.directives,
        selected_tactics=config_roots.tactics,
        available_tools=available_tools,
        references=references,
        doctrine_service=doctrine_service,
    )

    return CompiledCharter(
        mission=mission,
        template_set=template,
        selected_paradigms=config_roots.paradigms,
        selected_directives=config_roots.directives,
        available_tools=available_tools,
        markdown=markdown,
        references=references,
        diagnostics=diagnostics,
        selected_tactics=config_roots.tactics,
        active_languages=active_languages,
    )


def write_compiled_charter(
    output_dir: Path,
    compiled: CompiledCharter,
    *,
    force: bool = False,
    repo_root: Path | None = None,
) -> WriteBundleResult:
    """Write charter bundle artifacts to output_dir.

    Only charter.md and references.yaml are written; _LIBRARY/ materialization
    has been removed — doctrine content is fetched at context-retrieval time via
    references.yaml.
    """
    _assert_safe_charter_output_dir(output_dir, repo_root=repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    _assert_safe_charter_output_dir(output_dir, repo_root=repo_root)
    charter_path = output_dir / "charter.md"

    if charter_path.is_symlink():
        raise FileExistsError(
            f"Refusing to overwrite symlinked charter at {charter_path}; it is a symlink. "
            "Remove the symlink or update the symlink target directly."
        )
    if charter_path.exists() and not force:
        raise FileExistsError(f"Charter already exists at {charter_path}. Use --force to overwrite.")

    files_written: list[str] = []

    charter_path.write_text(compiled.markdown, encoding="utf-8")
    files_written.append("charter.md")

    references_path = output_dir / "references.yaml"
    _write_references_yaml(references_path, compiled)
    files_written.append("references.yaml")

    return WriteBundleResult(files_written=files_written)


def _assert_safe_charter_output_dir(
    output_dir: Path,
    *,
    repo_root: Path | None,
) -> None:
    """Reject symlinked charter output dirs before generated writes."""
    if repo_root is None:
        if output_dir.is_symlink():
            raise FileExistsError(
                f"Charter output directory {output_dir} is a symlink. Replace it "
                "with a normal .kittify/charter directory before running charter generate."
            )
        return

    root = repo_root.resolve(strict=False)
    candidate = output_dir if output_dir.is_absolute() else root / output_dir
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise FileExistsError(
            f"Charter output directory {output_dir} is outside repository root {repo_root}."
        ) from exc

    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise FileExistsError(
                f"Charter output path {current} is a symlink. Replace it with a normal "
                ".kittify/charter directory before running charter generate."
            )

    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise FileExistsError(
            f"Charter output directory {output_dir} resolves outside repository root {repo_root}."
        ) from exc


def _resolve_template_set(
    *,
    mission: str,
    requested_template_set: str | None,
    catalog: DoctrineCatalog,
) -> str:
    # ``catalog`` resolves to ``Any`` under single-file mypy, so bind the
    # attribute to its declared element type; this lets mypy infer ``str`` for
    # ``min(...)`` instead of propagating ``Any`` (no-any-return).
    template_sets: frozenset[str] = catalog.template_sets

    if requested_template_set:
        if template_sets and requested_template_set not in template_sets:
            options = ", ".join(sorted(template_sets))
            raise ValueError(f"Unknown template set '{requested_template_set}'. Available template sets: {options}")
        return requested_template_set

    mission_default = f"{mission}-default"
    if mission_default in template_sets:
        return mission_default

    if template_sets:
        return min(template_sets)

    return mission_default


def _sanitize_catalog_selection(
    *,
    values: list[str],
    allowed: set[str],
    label: str,
    diagnostics: list[str],
) -> list[str]:
    seen: list[str] = []
    missing: list[str] = []

    allowed_casefold = {item.casefold(): item for item in allowed}

    for raw in values:
        key = str(raw).strip()
        if not key:
            continue
        canonical = allowed_casefold.get(key.casefold())
        if canonical is None:
            missing.append(key)
            continue
        if canonical not in seen:
            seen.append(canonical)

    if missing:
        diagnostics.append(f"Ignored unknown {label}: {', '.join(sorted(missing))}")

    if seen:
        return seen

    # Explicitly empty selections remain empty. We do not broaden charter
    # doctrine or tool choices just because the interview provided no built-in
    # match.
    return []


def _default_doctrine_service(repo_root: Path | None) -> DoctrineService:
    """Build a DoctrineService rooted at built-in doctrine plus optional project overlay.

    The project-root candidate list (in priority order):
    1. ``.kittify/doctrine/``  — Phase 3 synthesis target (FR-009 / T024).
    2. ``src/doctrine/``       — code-local built-in-layer path.
    3. ``doctrine/``           — flat fallback.

    Discovery is conditional on directory presence: legacy projects (pre-
    synthesis) that have none of these directories see ``project_root=None``
    and byte-identical behaviour to the pre-Phase-3 default (R-2 mitigation).
    """
    from doctrine.service import DoctrineService

    doctrine_root = resolve_doctrine_root()
    project_root: Path | None = None
    if repo_root is not None:
        project_root = resolve_project_root(repo_root)
    return DoctrineService(built_in_root=doctrine_root, project_root=project_root)


def _build_references(
    *,
    mission: str,
    template_set: str,
    interview: CharterInterview,
    config_roots: ConfigActivatedRoots,
    doctrine_service: DoctrineService,
    repo_root: Path | None = None,
    diagnostics: list[str] | None = None,
) -> list[CharterReference]:
    doctrine_root = resolve_doctrine_root()

    references: list[CharterReference] = []
    references.append(_user_profile_reference(interview))
    references.extend(
        _build_references_from_service(
            mission=mission,
            template_set=template_set,
            config_roots=config_roots,
            doctrine_root=doctrine_root,
            doctrine_service=doctrine_service,
            repo_root=repo_root,
            diagnostics=diagnostics if diagnostics is not None else [],
        )
    )
    return references


def _build_references_from_yaml(
    *,
    mission: str,
    template_set: str,
    interview: CharterInterview,
    paradigms: list[str],
    directives: list[str],
    doctrine_root: Path,
) -> list[CharterReference]:
    """Load references by scanning YAML files directly (fallback path)."""
    references: list[CharterReference] = []

    paradigm_sources = _index_yaml_assets(doctrine_root / "paradigms", "*.paradigm.yaml")
    directive_sources = _index_yaml_assets(doctrine_root / "directives", "*.directive.yaml")

    for paradigm in paradigms:
        references.append(
            _doctrine_yaml_reference(
                kind="paradigm",
                raw_id=paradigm,
                source=paradigm_sources.get(paradigm.casefold()),
            )
        )

    for directive in directives:
        references.append(
            _doctrine_yaml_reference(
                kind="directive",
                raw_id=directive,
                source=directive_sources.get(directive.casefold()),
            )
        )

    references.append(_template_reference(doctrine_root=doctrine_root, mission=mission, template_set=template_set))

    language_hints = interview.answers.get("languages_frameworks", "").lower()
    if "python" in language_hints:
        styleguide_path = doctrine_root / "styleguides" / "python-implementation.styleguide.yaml"
        if styleguide_path.exists():
            references.append(
                _doctrine_yaml_reference(
                    kind="styleguide",
                    raw_id="python-implementation",
                    source=_load_yaml_asset(styleguide_path),
                )
            )

    return references


def _render_kind_references(
    ids: list[str],
    *,
    kind: str,
    repository: Any,
    id_of: Callable[[Any], str],
    title_of: Callable[[Any], str],
    summary_of: Callable[[Any], str],
) -> list[CharterReference]:
    """Render one :class:`CharterReference` per id, via a typed repository lookup.

    Shared by every DRG-backed kind in :func:`_build_references_from_service`
    (directive, tactic, styleguide, toolguide, procedure, agent profile) so
    the five near-identical "look up, else fall back to a bare YAML
    reference" loops collapse to one call site per kind.
    """
    references: list[CharterReference] = []
    for raw_id in ids:
        model = repository.get(raw_id)
        if model is not None:
            references.append(
                _doctrine_model_reference(
                    kind=kind,
                    raw_id=id_of(model),
                    title=title_of(model),
                    summary=summary_of(model),
                )
            )
        else:
            references.append(_doctrine_yaml_reference(kind=kind, raw_id=raw_id, source=None))
    return references


def _build_references_from_service(
    *,
    mission: str,
    template_set: str,
    config_roots: ConfigActivatedRoots,
    doctrine_root: Path,
    doctrine_service: DoctrineService,
    repo_root: Path | None,
    diagnostics: list[str],
) -> list[CharterReference]:
    """Load references via typed repository queries and DRG-backed transitive resolution."""
    references: list[CharterReference] = []

    # Paradigms: still loaded via YAML scanning (no typed paradigm references in graph).
    # Selection-only per the mission decision -- never DRG-reachable.
    paradigm_sources = _index_yaml_assets(doctrine_root / "paradigms", "*.paradigm.yaml")
    for paradigm in config_roots.paradigms:
        references.append(
            _doctrine_yaml_reference(
                kind="paradigm",
                raw_id=paradigm,
                source=paradigm_sources.get(paradigm.casefold()),
            )
        )

    # T026: tactics/styleguides/toolguides/procedures/agent profiles activated
    # directly in config.activated_* seed the transitive walk as additional
    # roots, unioned with the directive-closure result -- so an artefact with
    # no directive edge (e.g. the #2524 baseline danglers `aggregate-design-
    # rules` / `contextive`) still resolves.
    graph = _resolve_transitive_reference_graph(
        doctrine_root=doctrine_root,
        directives=config_roots.directives,
        direct_root_urns=_direct_root_urns(config_roots),
        repo_root=repo_root,
    )

    references.extend(
        _render_kind_references(
            graph.directives,
            kind="directive",
            repository=doctrine_service.directives,
            id_of=lambda d: str(d.id),
            title_of=lambda d: str(d.title),
            summary_of=lambda d: str(d.intent),
        )
    )
    references.extend(
        _render_kind_references(
            graph.tactics,
            kind="tactic",
            repository=doctrine_service.tactics,
            id_of=lambda t: str(t.id),
            title_of=lambda t: str(t.name),
            summary_of=lambda t: str(t.purpose or f"Tactic: {t.name}"),
        )
    )
    references.extend(
        _render_kind_references(
            graph.styleguides,
            kind="styleguide",
            repository=doctrine_service.styleguides,
            id_of=lambda sg: str(sg.id),
            title_of=lambda sg: str(sg.title),
            summary_of=lambda sg: str(sg.principles[0] if sg.principles else f"Styleguide: {sg.title}"),
        )
    )
    references.extend(
        _render_kind_references(
            graph.toolguides,
            kind="toolguide",
            repository=doctrine_service.toolguides,
            id_of=lambda tg: str(tg.id),
            title_of=lambda tg: str(tg.title),
            summary_of=lambda tg: str(tg.summary),
        )
    )
    references.extend(
        _render_kind_references(
            graph.procedures,
            kind="procedure",
            repository=doctrine_service.procedures,
            id_of=lambda proc: str(proc.id),
            title_of=lambda proc: str(proc.name),
            summary_of=lambda proc: str(proc.purpose),
        )
    )
    references.extend(
        _render_kind_references(
            graph.agent_profiles,
            kind="agent_profile",
            repository=doctrine_service.agent_profiles,
            id_of=lambda ap: str(ap.profile_id),
            title_of=lambda ap: str(ap.name),
            summary_of=lambda ap: str(ap.description or f"Agent profile: {ap.name}"),
        )
    )

    # Record unresolved refs in diagnostics
    for artifact_type, artifact_id in graph.unresolved:
        diagnostics.append(f"Unresolved reference: {artifact_type}/{artifact_id}")

    references.append(_template_reference(doctrine_root=doctrine_root, mission=mission, template_set=template_set))

    return references


def _resolve_transitive_reference_graph(
    *,
    doctrine_root: Path,
    directives: list[str],
    repo_root: Path | None,
    direct_root_urns: frozenset[str] = frozenset(),
    pack_context: Any = None,
) -> Any:
    """Resolve the transitive closure from built-in/project DRG layers.

    *directives* seed the closure as before. *direct_root_urns* (WP02 T026)
    are additional non-directive roots -- e.g. ``"styleguide:aggregate-
    design-rules"`` -- for kinds activated directly in
    ``config.activated_*`` with no directive edge reaching them; they are
    unioned into the same BFS start set so they (and anything they in turn
    require/suggest) resolve alongside the directive closure.
    """
    from charter._drg_helpers import load_validated_graph
    from charter.drg import filter_graph_by_activation
    from doctrine.drg.loader import load_built_in_graph
    from doctrine.drg.models import Relation
    from doctrine.drg.query import ResolveTransitiveRefsResult, resolve_transitive_refs
    from doctrine.drg.validator import assert_valid

    start_urns = {f"directive:{directive_id}" for directive_id in directives} | set(direct_root_urns)
    if not start_urns:
        return ResolveTransitiveRefsResult()

    # Graph-load-failure fallback: no transitive resolution, but the direct
    # roots must still surface (bare ids, one bucket per kind) rather than
    # silently vanishing alongside the directive closure.
    fallback = ResolveTransitiveRefsResult(
        directives=sorted(directives),
        tactics=sorted(_bare_ids_for_kind(direct_root_urns, ArtifactKind.TACTIC)),
        styleguides=sorted(_bare_ids_for_kind(direct_root_urns, ArtifactKind.STYLEGUIDE)),
        toolguides=sorted(_bare_ids_for_kind(direct_root_urns, ArtifactKind.TOOLGUIDE)),
        procedures=sorted(_bare_ids_for_kind(direct_root_urns, ArtifactKind.PROCEDURE)),
        agent_profiles=sorted(_bare_ids_for_kind(direct_root_urns, ArtifactKind.AGENT_PROFILE)),
    )

    try:
        if repo_root is not None:
            merged = load_validated_graph(repo_root)
        else:
            if not doctrine_root.exists():
                return fallback
            merged = load_built_in_graph()
            assert_valid(merged)
    except Exception:
        return fallback

    # FR-032, FR-035 (WP08): apply activation filter after load, before resolution.
    if pack_context is not None:
        merged = filter_graph_by_activation(merged, pack_context)

    return resolve_transitive_refs(
        merged,
        start_urns=start_urns,
        relations={Relation.REQUIRES, Relation.SUGGESTS},
    )


def _build_built_in_concept_ids(references: list[CharterReference]) -> frozenset[str]:
    """Return a set of '<kind>:<id>' keys for built-in (non-local) references."""
    result: set[str] = set()
    for ref in references:
        if ref.kind != "local_support":
            result.add(ref.id.upper())
    return frozenset(result)


def _build_local_support_references(
    declarations: list[LocalSupportDeclaration],
    *,
    built_in_ids: frozenset[str],
    diagnostics: list[str],
) -> list[CharterReference]:
    """Build CharterReference entries for local support file declarations."""
    refs: list[CharterReference] = []
    for decl in declarations:
        warning: str | None = None
        if decl.target_kind and decl.target_id:
            overlap_key = f"{decl.target_kind.upper()}:{decl.target_id.upper()}"
            if overlap_key in {k.upper() for k in built_in_ids}:
                warning = (
                    f"Local support file overlaps built-in {decl.target_kind} "
                    f"{decl.target_id}; built-in content remains primary."
                )
                diagnostics.append(
                    f"local_supporting_files '{decl.path}': {warning}"
                )

        ref_id = f"LOCAL:{decl.path}"
        title = Path(decl.path).name
        summary_parts = ["Local support file"]
        if decl.target_kind and decl.target_id:
            summary_parts.append(f"supplements {decl.target_kind} {decl.target_id}")
        if decl.action:
            summary_parts.append(f"(action: {decl.action})")
        summary = "; ".join(summary_parts) + "."

        # Build a lightweight content block (no schema validation for free-form markdown)
        lines: list[str] = [f"# Local Support File: {title}", ""]
        lines.append(f"- Path: `{decl.path}`")
        if decl.action:
            lines.append(f"- Action scope: `{decl.action}`")
        if decl.target_kind:
            lines.append(f"- Target kind: `{decl.target_kind}`")
        if decl.target_id:
            lines.append(f"- Target ID: `{decl.target_id}`")
        lines.append("- Relationship: additive")
        if warning:
            lines.append(f"- Warning: {warning}")
        lines.append("")

        refs.append(
            CharterReference(
                id=ref_id,
                kind="local_support",
                title=title,
                summary=summary,
                source_path=decl.path,
                local_path=f"_LIBRARY/local-{_slugify(decl.path)}.md",
                content="\n".join(lines),
            )
        )
    return refs


def _index_yaml_assets(directory: Path, pattern: str) -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = {}
    if not directory.is_dir():
        return index

    # Doctrine artifacts live in a built-in/ subdirectory; fall back to the
    # directory itself for tests or custom flat layouts.
    built_in = directory / "built-in"
    scan_root = built_in if built_in.is_dir() else directory

    for path in sorted(scan_root.glob(pattern)):
        loaded = _load_yaml_asset(path)
        raw_id = str(loaded.get("id", "")).strip() if isinstance(loaded, dict) else ""
        if not raw_id:
            raw_id = path.stem.split(".")[0]

        if raw_id:
            index[raw_id.casefold()] = loaded
    return index


def _load_yaml_asset(path: Path, *, unsafe: bool = False) -> dict[str, object]:
    """Load a YAML asset through the charter encoding chokepoint.

    Propagates :class:`CharterEncodingError` (a
    :class:`kernel.errors.KittyInternalConsistencyError`) to callers so the
    operator sees the actual failure mode rather than a silent empty parse.
    Truly-unrelated YAML errors (malformed structure on a successfully-decoded
    file) still degrade to an empty dict — that is the pre-existing resilience
    contract and is exercised by the regression test.

    Args:
        path: filesystem path of the YAML asset.
        unsafe: forwarded to :func:`load_charter_file`; when True an ambiguous
            encoding is bypassed using the highest-confidence decode candidate
            and ``bypass_used=True`` is recorded in provenance.
    """
    yaml = YAML(typ="safe")
    text = load_charter_file(path, unsafe=unsafe).text
    try:
        data = yaml.load(text) or {}
    except Exception:  # noqa: BLE001 — YAML parse failures degrade to empty
        # Pre-existing resilience contract: a syntactically-broken YAML file
        # whose encoding decoded cleanly produces an empty asset rather than
        # halting the whole compile. Encoding errors are NOT caught here —
        # they raise above in load_charter_file().
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("_source_path", str(path))
    return data


def _doctrine_model_reference(
    *,
    kind: str,
    raw_id: str,
    title: str,
    summary: str,
) -> CharterReference:
    """Build a CharterReference from typed repository model data."""
    local_slug = _slugify(raw_id)
    local_path = f"_LIBRARY/{kind}-{local_slug}.md"
    content = f"# {kind.title()}: {title}\n\n- ID: `{raw_id}`\n- Summary: {summary}\n"
    return CharterReference(
        id=f"{kind.upper()}:{raw_id}",
        kind=kind,
        title=title,
        summary=summary,
        source_path="",
        local_path=local_path,
        content=content,
    )


def _doctrine_yaml_reference(
    *,
    kind: str,
    raw_id: str,
    source: dict[str, object] | None,
) -> CharterReference:
    source = source or {"id": raw_id, "title": raw_id, "summary": "Definition unavailable in bundled doctrine."}

    source_path = str(source.get("_source_path", ""))
    display_path = _trim_source_path(source_path)
    title = str(source.get("title") or source.get("name") or raw_id)
    summary = str(source.get("summary") or source.get("intent") or "No summary provided.")

    source_yaml = _dump_yaml(source)
    local_slug = _slugify(raw_id)
    local_path = f"_LIBRARY/{kind}-{local_slug}.md"

    content = (
        f"# {kind.title()}: {title}\n\n"
        f"- ID: `{raw_id}`\n"
        f"- Source: `{display_path or source_path or 'N/A'}`\n"
        f"- Summary: {summary}\n\n"
        "## Raw Definition\n\n"
        "```yaml\n"
        f"{source_yaml}```\n"
    )

    return CharterReference(
        id=f"{kind.upper()}:{raw_id}",
        kind=kind,
        title=title,
        summary=summary,
        source_path=display_path or source_path,
        local_path=local_path,
        content=content,
    )


def _template_reference(*, doctrine_root: Path, mission: str, template_set: str) -> CharterReference:
    from doctrine.missions import MissionTemplateRepository

    repo = MissionTemplateRepository.default()
    config = repo.get_mission_config(mission)
    mission_path = repo._mission_config_path(mission) or (doctrine_root / "missions" / mission / "mission.yaml")
    raw_parsed = config.parsed if config is not None else {"name": mission}
    source: dict[str, object] = (
        {str(key): value for key, value in raw_parsed.items()}
        if isinstance(raw_parsed, dict)
        else {"name": mission}
    )

    summary = str(source.get("description") or f"Mission template set for {mission}.")
    content = (
        f"# Template Set: {template_set}\n\n"
        f"- Mission: `{mission}`\n"
        f"- Source: `{_trim_source_path(str(mission_path))}`\n"
        f"- Summary: {summary}\n\n"
        "## Mission Definition\n\n"
        "```yaml\n"
        f"{_dump_yaml(source)}```\n"
    )

    return CharterReference(
        id=f"TEMPLATE_SET:{template_set}",
        kind="template_set",
        title=template_set,
        summary=summary,
        source_path=_trim_source_path(str(mission_path)),
        local_path=f"_LIBRARY/template-set-{_slugify(template_set)}.md",
        content=content,
    )


def _user_profile_reference(interview: CharterInterview) -> CharterReference:
    lines: list[str] = ["# User Project Profile", ""]
    lines.append(f"- Mission: `{interview.mission}`")
    lines.append(f"- Interview profile: `{interview.profile}`")
    if interview.agent_profile:
        lines.append(f"- Agent profile: `{interview.agent_profile}`")
    if interview.agent_role:
        lines.append(f"- Agent role: `{interview.agent_role}`")
    lines.append("")
    lines.append("## Interview Answers")
    lines.append("")

    for key, value in interview.answers.items():
        label = key.replace("_", " ").strip().title()
        lines.append(f"- **{label}**: {value}")

    lines.append("")
    lines.append("## Selected Doctrine")
    lines.append("")
    lines.append(f"- Paradigms: {', '.join(interview.selected_paradigms) or '(none)'}")
    lines.append(f"- Directives: {', '.join(interview.selected_directives) or '(none)'}")
    lines.append(f"- Tools: {', '.join(interview.available_tools) or '(none)'}")
    lines.append("")

    return CharterReference(
        id="USER:PROJECT_PROFILE",
        kind="user_profile",
        title="User Project Profile",
        summary="Project-specific interview answers captured for charter compilation.",
        source_path=".kittify/charter/interview/answers.yaml",
        local_path="_LIBRARY/user-project-profile.md",
        content="\n".join(lines) + "\n",
    )


def _render_charter_markdown(
    *,
    mission: str,
    template_set: str,
    interview: CharterInterview,
    selected_paradigms: list[str],
    selected_directives: list[str],
    available_tools: list[str],
    references: list[CharterReference],
    doctrine_service: DoctrineService,
    selected_tactics: list[str] | None = None,
) -> str:
    selected_tactics = selected_tactics or []
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    testing = interview.answers.get(
        "testing_requirements",
        "Use the project's declared testing approach, or mark it as NEEDS CLARIFICATION.",
    )
    quality = interview.answers.get("quality_gates", "Tests, lint, and type checks must pass before merge.")
    performance = interview.answers.get("performance_targets", "No explicit performance policy provided.")
    deployment = interview.answers.get("deployment_constraints", "No deployment constraints provided.")
    review_policy = interview.answers.get("review_policy", "At least one reviewer validates changes.")

    policy_summary_lines = [
        f"- Intent: {interview.answers.get('project_intent', 'Not specified.')}",
        f"- Languages/Frameworks: {interview.answers.get('languages_frameworks', 'Not specified.')}",
        f"- Testing: {testing}",
        f"- Quality Gates: {quality}",
        f"- Review Policy: {review_policy}",
        f"- Performance Targets: {performance}",
        f"- Deployment Constraints: {deployment}",
    ]

    numbered_directives = _render_directives(interview, selected_directives, doctrine_service)

    reference_rows = ["| Reference ID | Kind | Summary | Local Doc |", "|---|---|---|---|"]
    for reference in references:
        reference_rows.append(
            f"| `{reference.id}` | {reference.kind} | {reference.summary} | `{reference.local_path}` |"
        )

    activation_lines = [f"mission: {mission}"]
    if interview.agent_profile:
        activation_lines.append(f"agent_profile: {interview.agent_profile}")
    if interview.agent_role:
        activation_lines.append(f"agent_role: {interview.agent_role}")
    activation_lines.extend(
        [
            f"selected_paradigms: {_yaml_inline_list(selected_paradigms)}",
            f"selected_directives: {_yaml_inline_list(selected_directives)}",
            f"selected_tactics: {_yaml_inline_list(selected_tactics)}",
            f"available_tools: {_yaml_inline_list(available_tools)}",
            f"template_set: {template_set}",
        ]
    )

    amendment = interview.answers.get(
        "amendment_process", "Amendments are proposed by PR and reviewed before adoption."
    )
    exception_policy = interview.answers.get(
        "exception_policy", "Exceptions must include rationale and expiration criteria."
    )
    return (
        "# Project Charter\n\n"
        "<!-- Generated by `spec-kitty charter generate` -->\n\n"
        f"Generated: {now}\n\n"
        "## Testing Standards\n\n"
        f"- {testing}\n\n"
        "## Quality Gates\n\n"
        f"- {quality}\n\n"
        "## Performance Benchmarks\n\n"
        f"- {performance}\n\n"
        "## Branch Strategy\n\n"
        f"- {review_policy}\n"
        f"- Deployment constraints: {deployment}\n\n"
        "## Governance Activation\n\n"
        "```yaml\n" + "\n".join(activation_lines) + "\n"
        "```\n\n"
        "## Policy Summary\n\n" + "\n".join(policy_summary_lines) + "\n\n"
        "## Project Directives\n\n" + numbered_directives + "\n\n"
        "## Reference Index\n\n" + "\n".join(reference_rows) + "\n\n"
        "## Amendment Process\n\n"
        f"{amendment}\n\n"
        "## Exception Policy\n\n"
        f"{exception_policy}\n"
    )


def _render_directives(
    interview: CharterInterview,
    selected_directives: list[str],
    doctrine_service: DoctrineService,
) -> str:
    lines: list[str] = []
    index = 1

    for directive_id in selected_directives:
        directive = doctrine_service.directives.get(directive_id)
        if directive is None:
            lines.append(f"{index}. Apply doctrine directive `{directive_id}` to planning and implementation decisions.")
            index += 1
            continue

        lines.append(f"{index}. {directive.title} (`{directive.id}`): {directive.intent.strip()}")
        if directive.scope:
            lines.append(f"   - Scope: {directive.scope.strip()}")
        for procedure in directive.procedures:
            lines.append(f"   - Procedure: {procedure}")
        for rule in directive.integrity_rules:
            lines.append(f"   - Integrity rule: {rule}")
        for criterion in directive.validation_criteria:
            lines.append(f"   - Validation criterion: {criterion}")
        index += 1

    risk = interview.answers.get("risk_boundaries")
    if risk:
        lines.append(f"{index}. Respect risk boundaries: {risk}")
        index += 1

    docs = interview.answers.get("documentation_policy")
    if docs:
        lines.append(f"{index}. Keep documentation synchronized with workflow and behavior changes: {docs}")
        index += 1

    if not lines:
        lines.append("1. Keep specification, plan, tasks, implementation, and review artifacts consistent.")

    return "\n".join(lines)


def _write_references_yaml(path: Path, compiled: CompiledCharter) -> None:
    ref_entries: list[dict[str, object]] = []
    for reference in compiled.references:
        entry: dict[str, object] = {
            "id": reference.id,
            "kind": reference.kind,
            "title": reference.title,
            "summary": reference.summary,
            "source_path": reference.source_path,
            "local_path": reference.local_path,
        }
        # For local support references, include extra metadata from the content block.
        # The content is authoritative; we parse action/target from the id/summary.
        # Instead, enrich from the reference content heuristic or keep as-is.
        # Extra fields are stored on the reference id for traceability.
        if reference.kind == "local_support":
            entry["relationship"] = "additive"
        ref_entries.append(entry)

    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mission": compiled.mission,
        "template_set": compiled.template_set,
        # Structured, compile-time-canonical language set (DIRECTIVE_044
        # unification). Runtime resolution in charter.language_scope reads
        # this field first; the interview transcript is consulted only when
        # this field is absent (pre-existing charters compiled before this
        # field was introduced).
        "languages": list(compiled.active_languages),
        "references": ref_entries,
    }

    yaml = YAML()
    yaml.default_flow_style = False
    with path.open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def _dump_yaml(data: dict[str, object]) -> str:
    cleaned = {k: v for k, v in data.items() if k != "_source_path"}
    yaml = YAML()
    yaml.default_flow_style = False
    buffer = StringIO()
    yaml.dump(cleaned, buffer)
    return buffer.getvalue()


def _trim_source_path(source_path: str) -> str:
    if not source_path:
        return ""
    marker = "src/doctrine/"
    if marker in source_path:
        return source_path[source_path.index(marker) :]
    return source_path


def _yaml_inline_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(values) + "]"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"
