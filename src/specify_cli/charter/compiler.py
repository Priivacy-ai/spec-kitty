"""Charter compiler: interview answers + doctrine assets -> charter bundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from io import StringIO
from pathlib import Path
import re

from ruamel.yaml import YAML

from specify_cli.charter.catalog import DoctrineCatalog, load_doctrine_catalog, resolve_doctrine_root
from specify_cli.charter.interview import CharterInterview
from specify_cli.charter.resolver import DEFAULT_TOOL_REGISTRY


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
    repo_root: Path | None = None,
) -> CompiledCharter:
    """Compile charter markdown, references manifest, and library docs.

    Per D-3 of the ``excise-doctrine-curation-and-inline-references-01KP54J6``
    mission this function is the twin of :func:`charter.compiler.compile_charter`
    and now also accepts *repo_root* for project-overlay DRG discovery.
    """
    catalog = doctrine_catalog or load_doctrine_catalog()
    diagnostics: list[str] = []

    template = _resolve_template_set(mission=mission, requested_template_set=template_set, catalog=catalog)
    selected_paradigms = _sanitize_catalog_selection(
        values=interview.selected_paradigms,
        allowed=set(catalog.paradigms),
        label="selected_paradigms",
        diagnostics=diagnostics,
    )
    selected_directives = _sanitize_catalog_selection(
        values=interview.selected_directives,
        allowed=set(catalog.directives),
        label="selected_directives",
        diagnostics=diagnostics,
    )
    available_tools = _sanitize_catalog_selection(
        values=interview.available_tools,
        allowed=set(DEFAULT_TOOL_REGISTRY),
        label="available_tools",
        diagnostics=diagnostics,
    )

    references = _build_references(
        mission=mission,
        template_set=template,
        interview=interview,
        paradigms=selected_paradigms,
        directives=selected_directives,
        repo_root=repo_root,
    )
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
    """Write charter bundle artifacts to output_dir."""
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

    library_dir = output_dir / "library"
    library_dir.mkdir(parents=True, exist_ok=True)

    expected_library_files: set[str] = set()
    for reference in compiled.references:
        target = output_dir / reference.local_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(reference.content, encoding="utf-8")
        relative = str(target.relative_to(output_dir))
        files_written.append(relative)
        expected_library_files.add(relative)

    # Remove stale generated library markdown files for deterministic output.
    for stale in sorted(library_dir.glob("*.md")):
        rel = str(stale.relative_to(output_dir))
        if rel not in expected_library_files:
            stale.unlink()

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

    return []


def _build_references(
    *,
    mission: str,
    template_set: str,
    interview: CharterInterview,
    paradigms: list[str],
    directives: list[str],
    repo_root: Path | None = None,
) -> list[CharterReference]:
    """Load references via the DRG (shipped + optional project overlay).

    Per C-001 of the
    ``excise-doctrine-curation-and-inline-references-01KP54J6`` mission this
    path has no YAML-scanning fallback: transitive reference resolution is
    always graph-driven.
    """
    from doctrine.drg.loader import load_graph, merge_layers
    from doctrine.drg.models import Relation
    from doctrine.drg.query import ResolveTransitiveRefsResult, resolve_transitive_refs
    from doctrine.drg.validator import assert_valid
    from doctrine.service import DoctrineService
    from specify_cli.charter._drg_helpers import load_validated_graph

    doctrine_root = resolve_doctrine_root()

    references: list[CharterReference] = []
    references.append(_user_profile_reference(interview))

    # Paradigms: loaded via the typed catalog (no typed paradigm DRG edges).
    paradigm_sources = _index_yaml_assets(doctrine_root / "paradigms", "*.paradigm.yaml")
    for paradigm in paradigms:
        references.append(
            _doctrine_yaml_reference(
                kind="paradigm",
                raw_id=paradigm,
                source=paradigm_sources.get(paradigm.casefold()),
            )
        )

    # Build a DoctrineService so typed repository lookups for directive /
    # tactic / styleguide / toolguide / procedure titles are possible.
    project_root: Path | None = None
    if repo_root is not None:
        candidates = [repo_root / "src" / "doctrine", repo_root / "doctrine"]
        project_root = next((path for path in candidates if path.is_dir()), None)
    service = DoctrineService(shipped_root=doctrine_root, project_root=project_root)

    if directives:
        if repo_root is not None:
            try:
                merged = load_validated_graph(repo_root)
            except FileNotFoundError:
                merged = None
        else:
            graph_path = doctrine_root / "graph.yaml"
            if graph_path.exists():
                shipped = load_graph(graph_path)
                merged = merge_layers(shipped, None)
                assert_valid(merged)
            else:
                merged = None

        if merged is not None:
            start_urns = {f"directive:{d}" for d in directives}
            graph = resolve_transitive_refs(
                merged,
                start_urns=start_urns,
                relations={Relation.REQUIRES, Relation.SUGGESTS},
            )
        else:
            graph = ResolveTransitiveRefsResult(directives=sorted(directives))
    else:
        graph = ResolveTransitiveRefsResult()

    directive_sources = _index_yaml_assets(doctrine_root / "directives", "*.directive.yaml")
    for directive_id in graph.directives:
        directive = service.directives.get(directive_id)
        if directive is not None:
            references.append(
                _doctrine_yaml_reference(
                    kind="directive",
                    raw_id=directive.id,
                    source=directive_sources.get(directive.id.casefold()),
                )
            )
        else:
            references.append(
                _doctrine_yaml_reference(
                    kind="directive",
                    raw_id=directive_id,
                    source=directive_sources.get(directive_id.casefold()),
                )
            )

    tactic_sources = _index_yaml_assets(doctrine_root / "tactics", "*.tactic.yaml")
    for tactic_id in graph.tactics:
        references.append(
            _doctrine_yaml_reference(
                kind="tactic",
                raw_id=tactic_id,
                source=tactic_sources.get(tactic_id.casefold()),
            )
        )

    styleguide_sources = _index_yaml_assets(doctrine_root / "styleguides", "*.styleguide.yaml")
    for sg_id in graph.styleguides:
        references.append(
            _doctrine_yaml_reference(
                kind="styleguide",
                raw_id=sg_id,
                source=styleguide_sources.get(sg_id.casefold()),
            )
        )

    toolguide_sources = _index_yaml_assets(doctrine_root / "toolguides", "*.toolguide.yaml")
    for tg_id in graph.toolguides:
        references.append(
            _doctrine_yaml_reference(
                kind="toolguide",
                raw_id=tg_id,
                source=toolguide_sources.get(tg_id.casefold()),
            )
        )

    procedure_sources = _index_yaml_assets(doctrine_root / "procedures", "*.procedure.yaml")
    for proc_id in graph.procedures:
        references.append(
            _doctrine_yaml_reference(
                kind="procedure",
                raw_id=proc_id,
                source=procedure_sources.get(proc_id.casefold()),
            )
        )

    references.append(_template_reference(doctrine_root=doctrine_root, mission=mission, template_set=template_set))

    return references


def _index_yaml_assets(directory: Path, pattern: str) -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = {}
    if not directory.is_dir():
        return index

    # Doctrine artifacts live under a ``shipped/`` subdirectory; fall back to
    # the directory itself for tests or flat layouts.
    shipped = directory / "shipped"
    scan_root = shipped if shipped.is_dir() else directory

    for path in sorted(scan_root.rglob(pattern)):
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
    local_path = f"library/{kind}-{local_slug}.md"

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
    mission_path = doctrine_root / "missions" / mission / "mission.yaml"
    source: dict[str, object] = _load_yaml_asset(mission_path) if mission_path.exists() else {"name": mission}

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
        local_path=f"library/template-set-{_slugify(template_set)}.md",
        content=content,
    )


def _user_profile_reference(interview: CharterInterview) -> CharterReference:
    lines: list[str] = ["# User Project Profile", ""]
    lines.append(f"- Mission: `{interview.mission}`")
    lines.append(f"- Interview profile: `{interview.profile}`")
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
        local_path="library/user-project-profile.md",
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

    numbered_directives = _render_directives(interview, selected_directives)

    reference_rows = ["| Reference ID | Kind | Summary | Local Doc |", "|---|---|---|---|"]
    for reference in references:
        reference_rows.append(
            f"| `{reference.id}` | {reference.kind} | {reference.summary} | `{reference.local_path}` |"
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
        "```yaml\n"
        f"mission: {mission}\n"
        f"selected_paradigms: {_yaml_inline_list(selected_paradigms)}\n"
        f"selected_directives: {_yaml_inline_list(selected_directives)}\n"
        f"available_tools: {_yaml_inline_list(available_tools)}\n"
        f"template_set: {template_set}\n"
        "```\n\n"
        "## Policy Summary\n\n" + "\n".join(policy_summary_lines) + "\n\n"
        "## Project Directives\n\n" + numbered_directives + "\n\n"
        "## Reference Index\n\n" + "\n".join(reference_rows) + "\n\n"
        "## Amendment Process\n\n"
        f"{interview.answers.get('amendment_process', 'Amendments are proposed by PR and reviewed before adoption.')}\n\n"  # noqa: E501
        "## Exception Policy\n\n"
        f"{interview.answers.get('exception_policy', 'Exceptions must include rationale and expiration criteria.')}\n"
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
    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mission": compiled.mission,
        "template_set": compiled.template_set,
        "references": [
            {
                "id": reference.id,
                "kind": reference.kind,
                "title": reference.title,
                "summary": reference.summary,
                "source_path": reference.source_path,
                "local_path": reference.local_path,
            }
            for reference in compiled.references
        ],
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
