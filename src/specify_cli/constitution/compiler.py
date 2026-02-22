"""Constitution compiler: interview answers + doctrine assets -> constitution bundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
import re

from ruamel.yaml import YAML

from specify_cli.constitution.catalog import DoctrineCatalog, load_doctrine_catalog, resolve_doctrine_root
from specify_cli.constitution.interview import ConstitutionInterview
from specify_cli.constitution.resolver import DEFAULT_TOOL_REGISTRY


@dataclass(frozen=True)
class ConstitutionReference:
    """One reference item used by constitution context."""

    id: str
    kind: str
    title: str
    summary: str
    source_path: str
    local_path: str
    content: str


@dataclass(frozen=True)
class CompiledConstitution:
    """Compiled constitution bundle."""

    mission: str
    template_set: str
    selected_paradigms: list[str]
    selected_directives: list[str]
    available_tools: list[str]
    markdown: str
    references: list[ConstitutionReference]
    diagnostics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WriteBundleResult:
    """Filesystem write result for compiled constitution bundle."""

    files_written: list[str]


def compile_constitution(
    *,
    mission: str,
    interview: ConstitutionInterview,
    template_set: str | None = None,
    doctrine_catalog: DoctrineCatalog | None = None,
) -> CompiledConstitution:
    """Compile constitution markdown, references manifest, and library docs."""
    catalog = doctrine_catalog or load_doctrine_catalog()
    diagnostics: list[str] = []

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

    references = _build_references(
        mission=mission,
        template_set=template,
        interview=interview,
        paradigms=selected_paradigms,
        directives=selected_directives,
    )
    markdown = _render_constitution_markdown(
        mission=mission,
        template_set=template,
        interview=interview,
        selected_paradigms=selected_paradigms,
        selected_directives=selected_directives,
        available_tools=available_tools,
        references=references,
    )

    return CompiledConstitution(
        mission=mission,
        template_set=template,
        selected_paradigms=selected_paradigms,
        selected_directives=selected_directives,
        available_tools=available_tools,
        markdown=markdown,
        references=references,
        diagnostics=diagnostics,
    )


def write_compiled_constitution(
    output_dir: Path,
    compiled: CompiledConstitution,
    *,
    force: bool = False,
) -> WriteBundleResult:
    """Write constitution bundle artifacts to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    constitution_path = output_dir / "constitution.md"

    if constitution_path.exists() and not force:
        raise FileExistsError(f"Constitution already exists at {constitution_path}. Use --force to overwrite.")

    files_written: list[str] = []

    constitution_path.write_text(compiled.markdown, encoding="utf-8")
    files_written.append("constitution.md")

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
            raise ValueError(
                f"Unknown template set '{requested_template_set}'. Available template sets: {options}"
            )
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
    interview: ConstitutionInterview,
    paradigms: list[str],
    directives: list[str],
) -> list[ConstitutionReference]:
    doctrine_root = resolve_doctrine_root()

    references: list[ConstitutionReference] = []
    references.append(_user_profile_reference(interview))

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


def _index_yaml_assets(directory: Path, pattern: str) -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = {}
    if not directory.is_dir():
        return index

    for path in sorted(directory.glob(pattern)):
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
) -> ConstitutionReference:
    source = source or {"id": raw_id, "title": raw_id, "summary": "Definition unavailable in bundled doctrine."}

    source_path = str(source.get("_source_path", ""))
    display_path = _trim_source_path(source_path)
    title = str(source.get("title") or source.get("name") or raw_id)
    summary = str(
        source.get("summary")
        or source.get("intent")
        or "No summary provided."
    )

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

    return ConstitutionReference(
        id=f"{kind.upper()}:{raw_id}",
        kind=kind,
        title=title,
        summary=summary,
        source_path=display_path or source_path,
        local_path=local_path,
        content=content,
    )


def _template_reference(*, doctrine_root: Path, mission: str, template_set: str) -> ConstitutionReference:
    mission_path = doctrine_root / "missions" / mission / "mission.yaml"
    source = _load_yaml_asset(mission_path) if mission_path.exists() else {"name": mission}

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

    return ConstitutionReference(
        id=f"TEMPLATE_SET:{template_set}",
        kind="template_set",
        title=template_set,
        summary=summary,
        source_path=_trim_source_path(str(mission_path)),
        local_path=f"library/template-set-{_slugify(template_set)}.md",
        content=content,
    )


def _user_profile_reference(interview: ConstitutionInterview) -> ConstitutionReference:
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

    return ConstitutionReference(
        id="USER:PROJECT_PROFILE",
        kind="user_profile",
        title="User Project Profile",
        summary="Project-specific interview answers captured for constitution compilation.",
        source_path=".kittify/constitution/interview/answers.yaml",
        local_path="library/user-project-profile.md",
        content="\n".join(lines) + "\n",
    )


def _render_constitution_markdown(
    *,
    mission: str,
    template_set: str,
    interview: ConstitutionInterview,
    selected_paradigms: list[str],
    selected_directives: list[str],
    available_tools: list[str],
    references: list[ConstitutionReference],
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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

    return (
        "# Project Constitution\n\n"
        "<!-- Generated by `spec-kitty constitution generate` -->\n\n"
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
        "## Policy Summary\n\n"
        + "\n".join(policy_summary_lines)
        + "\n\n"
        "## Project Directives\n\n"
        + numbered_directives
        + "\n\n"
        "## Reference Index\n\n"
        + "\n".join(reference_rows)
        + "\n\n"
        "## Amendment Process\n\n"
        f"{interview.answers.get('amendment_process', 'Amendments are proposed by PR and reviewed before adoption.')}\n\n"
        "## Exception Policy\n\n"
        f"{interview.answers.get('exception_policy', 'Exceptions must include rationale and expiration criteria.')}\n"
    )


def _render_directives(interview: ConstitutionInterview, selected_directives: list[str]) -> str:
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


def _write_references_yaml(path: Path, compiled: CompiledConstitution) -> None:
    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        return source_path[source_path.index(marker):]
    return source_path


def _yaml_inline_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(values) + "]"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"
