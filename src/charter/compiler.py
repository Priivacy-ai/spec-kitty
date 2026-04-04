"""Charter compiler: interview answers + doctrine assets -> charter bundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from io import StringIO
from pathlib import Path
import re
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from constitution.catalog import DoctrineCatalog, load_doctrine_catalog, resolve_doctrine_root
from constitution.interview import (
    CharterInterview,
    LocalSupportDeclaration,
    validate_local_support_declarations,
)
from constitution.resolver import DEFAULT_TOOL_REGISTRY

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
) -> CompiledCharter:
    """Compile charter markdown, references manifest, and library docs.

    When *doctrine_service* is provided, artifact loading and transitive reference
    resolution use the typed repository API (profile-aware path). When it is None
    the compiler falls back to direct YAML scanning and emits a diagnostic warning.
    """
    catalog = doctrine_catalog or load_doctrine_catalog()
    diagnostics: list[str] = []

    if doctrine_service is None:
        diagnostics.append(
            "DoctrineService unavailable; using YAML scanning fallback. "
            "Profile-aware compilation requires DoctrineService."
        )

    template = _resolve_template_set(mission=mission, requested_template_set=template_set, catalog=catalog)
    selected_paradigms = _sanitize_catalog_selection(
        values=interview.selected_paradigms,
        allowed=set(catalog.paradigms),
        default=sorted(catalog.paradigms),
        label="selected_paradigms",
        diagnostics=diagnostics,
    )
    selected_directives = _sanitize_catalog_selection(
        values=interview.selected_directives,
        allowed=set(catalog.directives),
        default=sorted(catalog.directives),
        label="selected_directives",
        diagnostics=diagnostics,
    )
    available_tools = _sanitize_catalog_selection(
        values=interview.available_tools,
        allowed=set(DEFAULT_TOOL_REGISTRY),
        default=sorted(DEFAULT_TOOL_REGISTRY),
        label="available_tools",
        diagnostics=diagnostics,
    )

    # Validate and normalize local support file declarations.
    valid_local, local_errors = validate_local_support_declarations(
        list(interview.local_supporting_files)
    )
    diagnostics.extend(local_errors)

    references = _build_references(
        mission=mission,
        template_set=template,
        interview=interview,
        paradigms=selected_paradigms,
        directives=selected_directives,
        doctrine_service=doctrine_service,
        diagnostics=diagnostics,
    )

    # Build additive local support references.
    shipped_ids = _build_shipped_concept_ids(references)
    local_references = _build_local_support_references(
        valid_local,
        shipped_ids=shipped_ids,
        diagnostics=diagnostics,
    )
    references = references + local_references

    markdown = _render_charter_markdown(
        mission=mission,
        template_set=template,
        interview=interview,
        selected_paradigms=selected_paradigms,
        selected_directives=selected_directives,
        available_tools=available_tools,
        references=references,
    )

    return CompiledCharter(
        mission=mission,
        template_set=template,
        selected_paradigms=selected_paradigms,
        selected_directives=selected_directives,
        available_tools=available_tools,
        markdown=markdown,
        references=references,
        diagnostics=diagnostics,
    )


def write_compiled_charter(
    output_dir: Path,
    compiled: CompiledCharter,
    *,
    force: bool = False,
) -> WriteBundleResult:
    """Write charter bundle artifacts to output_dir.

    Only charter.md and references.yaml are written; _LIBRARY/ materialization
    has been removed — doctrine content is fetched at context-retrieval time via
    references.yaml.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    charter_path = output_dir / "charter.md"

    if charter_path.exists() and not force:
        raise FileExistsError(f"Charter already exists at {charter_path}. Use --force to overwrite.")

    files_written: list[str] = []

    charter_path.write_text(compiled.markdown, encoding="utf-8")
    files_written.append("charter.md")

    references_path = output_dir / "references.yaml"
    _write_references_yaml(references_path, compiled)
    files_written.append("references.yaml")

    return WriteBundleResult(files_written=files_written)


def _resolve_template_set(
    *,
    mission: str,
    requested_template_set: str | None,
    catalog: DoctrineCatalog,
) -> str:
    if requested_template_set:
        if catalog.template_sets and requested_template_set not in catalog.template_sets:
            options = ", ".join(sorted(catalog.template_sets))
            raise ValueError(f"Unknown template set '{requested_template_set}'. Available template sets: {options}")
        return requested_template_set

    mission_default = f"{mission}-default"
    if mission_default in catalog.template_sets:
        return mission_default

    if catalog.template_sets:
        return sorted(catalog.template_sets)[0]

    return mission_default


def _sanitize_catalog_selection(
    *,
    values: list[str],
    allowed: set[str],
    default: list[str],
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

    return list(default)


def _build_references(
    *,
    mission: str,
    template_set: str,
    interview: CharterInterview,
    paradigms: list[str],
    directives: list[str],
    doctrine_service: DoctrineService | None = None,
    diagnostics: list[str] | None = None,
) -> list[CharterReference]:
    doctrine_root = resolve_doctrine_root()

    references: list[CharterReference] = []
    references.append(_user_profile_reference(interview))

    if doctrine_service is not None:
        references.extend(
            _build_references_from_service(
                mission=mission,
                template_set=template_set,
                paradigms=paradigms,
                directives=directives,
                doctrine_root=doctrine_root,
                doctrine_service=doctrine_service,
                diagnostics=diagnostics if diagnostics is not None else [],
            )
        )
    else:
        references.extend(
            _build_references_from_yaml(
                mission=mission,
                template_set=template_set,
                interview=interview,
                paradigms=paradigms,
                directives=directives,
                doctrine_root=doctrine_root,
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


def _build_references_from_service(
    *,
    mission: str,
    template_set: str,
    paradigms: list[str],
    directives: list[str],
    doctrine_root: Path,
    doctrine_service: DoctrineService,
    diagnostics: list[str],
) -> list[CharterReference]:
    """Load references via typed repository queries and transitive resolution."""
    from constitution.reference_resolver import resolve_references_transitively

    references: list[CharterReference] = []

    # Paradigms: still loaded via YAML scanning (no typed paradigm references in graph)
    paradigm_sources = _index_yaml_assets(doctrine_root / "paradigms", "*.paradigm.yaml")
    for paradigm in paradigms:
        references.append(
            _doctrine_yaml_reference(
                kind="paradigm",
                raw_id=paradigm,
                source=paradigm_sources.get(paradigm.casefold()),
            )
        )

    # Resolve directives + transitive artifacts via DoctrineService
    graph = resolve_references_transitively(directives, doctrine_service)

    for directive_id in graph.directives:
        directive = doctrine_service.directives.get(directive_id)
        if directive is not None:
            references.append(
                _doctrine_model_reference(
                    kind="directive",
                    raw_id=directive.id,
                    title=directive.title,
                    summary=directive.intent,
                )
            )
        else:
            references.append(_doctrine_yaml_reference(kind="directive", raw_id=directive_id, source=None))

    for tactic_id in graph.tactics:
        tactic = doctrine_service.tactics.get(tactic_id)
        if tactic is not None:
            references.append(
                _doctrine_model_reference(
                    kind="tactic",
                    raw_id=tactic.id,
                    title=tactic.name,
                    summary=tactic.purpose or f"Tactic: {tactic.name}",
                )
            )
        else:
            references.append(_doctrine_yaml_reference(kind="tactic", raw_id=tactic_id, source=None))

    for sg_id in graph.styleguides:
        sg = doctrine_service.styleguides.get(sg_id)
        if sg is not None:
            references.append(
                _doctrine_model_reference(
                    kind="styleguide",
                    raw_id=sg.id,
                    title=sg.title,
                    summary=sg.principles[0] if sg.principles else f"Styleguide: {sg.title}",
                )
            )
        else:
            references.append(_doctrine_yaml_reference(kind="styleguide", raw_id=sg_id, source=None))

    for tg_id in graph.toolguides:
        tg = doctrine_service.toolguides.get(tg_id)
        if tg is not None:
            references.append(
                _doctrine_model_reference(
                    kind="toolguide",
                    raw_id=tg.id,
                    title=tg.title,
                    summary=tg.summary,
                )
            )
        else:
            references.append(_doctrine_yaml_reference(kind="toolguide", raw_id=tg_id, source=None))

    for proc_id in graph.procedures:
        proc = doctrine_service.procedures.get(proc_id)
        if proc is not None:
            references.append(
                _doctrine_model_reference(
                    kind="procedure",
                    raw_id=proc.id,
                    title=proc.name,
                    summary=proc.purpose,
                )
            )
        else:
            references.append(_doctrine_yaml_reference(kind="procedure", raw_id=proc_id, source=None))

    # Record unresolved refs in diagnostics
    for artifact_type, artifact_id in graph.unresolved:
        diagnostics.append(f"Unresolved reference: {artifact_type}/{artifact_id}")

    references.append(_template_reference(doctrine_root=doctrine_root, mission=mission, template_set=template_set))

    return references


def _build_shipped_concept_ids(references: list[CharterReference]) -> frozenset[str]:
    """Return a set of '<kind>:<id>' keys for shipped (non-local) references."""
    result: set[str] = set()
    for ref in references:
        if ref.kind != "local_support":
            result.add(ref.id.upper())
    return frozenset(result)


def _build_local_support_references(
    declarations: list[LocalSupportDeclaration],
    *,
    shipped_ids: frozenset[str],
    diagnostics: list[str],
) -> list[CharterReference]:
    """Build CharterReference entries for local support file declarations."""
    refs: list[CharterReference] = []
    for decl in declarations:
        warning: str | None = None
        if decl.target_kind and decl.target_id:
            overlap_key = f"{decl.target_kind.upper()}:{decl.target_id.upper()}"
            if overlap_key in {k.upper() for k in shipped_ids}:
                warning = (
                    f"Local support file overlaps shipped {decl.target_kind} "
                    f"{decl.target_id}; shipped content remains primary."
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

    # Doctrine artifacts live in a shipped/ subdirectory; fall back to the
    # directory itself for tests or custom flat layouts.
    shipped = directory / "shipped"
    scan_root = shipped if shipped.is_dir() else directory

    for path in sorted(scan_root.glob(pattern)):
        loaded = _load_yaml_asset(path)
        raw_id = str(loaded.get("id", "")).strip() if isinstance(loaded, dict) else ""
        if not raw_id:
            raw_id = path.stem.split(".")[0]

        if raw_id:
            index[raw_id.casefold()] = loaded
    return index


def _load_yaml_asset(path: Path) -> dict[str, object]:
    yaml = YAML(typ="safe")
    try:
        data = yaml.load(path.read_text(encoding="utf-8")) or {}
    except Exception:
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
    source = config.parsed if config is not None else {"name": mission}

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
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    testing = interview.answers.get("testing_requirements", "Use pytest with measurable coverage goals.")
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

    numbered_directives = _render_directives(interview, selected_directives)

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


def _render_directives(interview: CharterInterview, selected_directives: list[str]) -> str:
    lines: list[str] = []
    index = 1

    for directive in selected_directives:
        lines.append(f"{index}. Apply doctrine directive `{directive}` to planning and implementation decisions.")
        index += 1

    risk = interview.answers.get("risk_boundaries")
    if risk:
        lines.append(f"{index}. Respect risk boundaries: {risk}")
        index += 1

    docs = interview.answers.get("documentation_policy")
    if docs:
        lines.append(f"{index}. Keep documentation synchronized with workflow and behavior changes.")
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
