#!/usr/bin/env python3
"""Compile the markdown glossary into Contextive glossary YAML files.

This script reads glossary context markdown files from `glossary/contexts/` and
writes Contextive-compatible `.glossary.yml` files to `.kittify/memory/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re
import sys

try:
    from ruamel.yaml import YAML
except ImportError:  # pragma: no cover - runtime environment detail
    print(
        "Error: ruamel.yaml is required. Activate the project venv and install dependencies.",
        file=sys.stderr,
    )
    raise


REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_CONTEXTS_DIR = REPO_ROOT / "glossary" / "contexts"
OUTPUT_ROOT = REPO_ROOT / ".kittify" / "memory"
OUTPUT_CONTEXTS_DIR = OUTPUT_ROOT / "contexts"
OUTPUT_INDEX = OUTPUT_ROOT / "spec-kitty.glossary.yml"
PROJECT_GLOSSARY = REPO_ROOT / "project.glossary.yml"
DOCTRINE_ROOT = REPO_ROOT / "src" / "doctrine"


def _slugify(text: str) -> str:
    """Convert free text to a lowercase file-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug


def _strip_markdown_links(text: str) -> str:
    """Strip markdown link syntax while preserving display text."""
    return re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)


def _split_list_values(raw_value: str) -> list[str]:
    """Split comma-separated values into a clean string list."""
    normalized = _strip_markdown_links(raw_value).replace(";", ",")
    items = [part.strip() for part in normalized.split(",") if part.strip()]
    return items


def _display_path(path: Path) -> str:
    """Return repository-relative path when possible, else absolute path."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


@dataclass(frozen=True)
class ParsedTerm:
    """Represents one parsed glossary term from markdown."""

    name: str
    definition: str
    aliases: list[str]
    examples: list[str]
    meta: dict[str, str]


@dataclass(frozen=True)
class ParsedContext:
    """Represents one parsed context file from markdown."""

    name: str
    vision_statement: str
    terms: list[ParsedTerm]
    source_file: str


@dataclass(frozen=True)
class DoctrineArtifactTerm:
    """Represents one doctrine artifact mapped into a glossary term."""

    artifact_id: str
    name: str
    description: str
    artifact_type: str
    source_file: str


TERM_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
ROW_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*$")
BULLET_RE = re.compile(r"^-\s+`?([^`\s]+(?:\s+[^`\s]+)*)`?\s*[—-]\s*(.+)$")
BLOCK_HEADING_RE = re.compile(r"^\*\*(.+?)\*\*:\s*$")


def _parse_context_header(content: str) -> tuple[str, str]:
    """Extract context name and subtitle from the top-level header."""
    first_line = content.splitlines()[0].strip()
    if not first_line.startswith("## Context:"):
        msg = "Expected first line to start with '## Context:'"
        raise ValueError(msg)

    header_value = first_line.replace("## Context:", "", 1).strip()
    if "(" in header_value and header_value.endswith(")"):
        base_name, paren = header_value.rsplit("(", 1)
        context_name = base_name.strip()
        subtitle = paren[:-1].strip()
    else:
        context_name = header_value
        subtitle = ""

    vision_statement = (
        f"Terms for {context_name.lower()} context."
        if not subtitle
        else f"Terms describing {subtitle}."
    )
    return context_name, vision_statement


def _extract_term_sections(content: str) -> list[tuple[str, str]]:
    """Split context content into (term_name, section_body) pairs."""
    matches = list(TERM_HEADING_RE.finditer(content))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        name = match.group(1).strip()
        body = content[start:end].strip()
        sections.append((name, body))
    return sections


def _extract_table_data(section: str) -> dict[str, str]:
    """Extract key-value pairs from the markdown term table."""
    data: dict[str, str] = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        row_match = ROW_RE.match(line)
        if row_match is None:
            continue
        key = row_match.group(1).strip()
        value = row_match.group(2).strip()
        if key and value:
            data[key] = _strip_markdown_links(value)
    return data


def _extract_bulleted_block(section: str) -> dict[str, list[str]]:
    """Extract structured bullet blocks such as Fields and Values."""
    result: dict[str, list[str]] = {}
    lines = section.splitlines()
    current_key = ""

    for raw_line in lines:
        line = raw_line.strip()
        heading_match = BLOCK_HEADING_RE.match(line)
        if heading_match is not None:
            current_key = heading_match.group(1).strip()
            result.setdefault(current_key, [])
            continue

        if not current_key or not line.startswith("-"):
            continue

        if line == "---":
            continue

        bullet = line[1:].strip()
        if bullet in {"--", "---"}:
            continue
        bullet_match = BULLET_RE.match(line)
        if bullet_match is not None:
            field_name = bullet_match.group(1).strip()
            field_desc = bullet_match.group(2).strip()
            result[current_key].append(f"{field_name}: {field_desc}")
            continue

        result[current_key].append(_strip_markdown_links(bullet))

    return result


def _build_term(term_name: str, section: str) -> ParsedTerm:
    """Build a ParsedTerm from a markdown section."""
    table_data = _extract_table_data(section)
    blocks = _extract_bulleted_block(section)

    definition = table_data.get("Definition", "").strip()
    if not definition:
        msg = f"Term '{term_name}' is missing a Definition"
        raise ValueError(msg)

    aliases: list[str] = []
    for key in ("Legacy alias", "Legacy name", "Synonym", "Synonyms"):
        if key in table_data:
            aliases.extend(_split_list_values(table_data[key]))

    examples: list[str] = []
    if "Examples" in table_data:
        examples.extend(_split_list_values(table_data["Examples"]))
    if "Example" in table_data:
        examples.append(table_data["Example"])

    meta: dict[str, str] = {}
    for key, value in table_data.items():
        if key in {
            "Definition",
            "Examples",
            "Example",
            "Legacy alias",
            "Legacy name",
            "Synonym",
            "Synonyms",
        }:
            continue

        if key == "Related terms":
            meta[key] = ", ".join(_split_list_values(value))
            continue

        meta[key] = value

    for block_name, items in blocks.items():
        if items:
            meta[block_name] = "; ".join(items)

    return ParsedTerm(
        name=term_name,
        definition=definition,
        aliases=aliases,
        examples=examples,
        meta=meta,
    )


def parse_context_file(path: Path) -> ParsedContext:
    """Parse a single markdown context glossary file."""
    content = path.read_text(encoding="utf-8")
    context_name, vision_statement = _parse_context_header(content)

    terms = [
        _build_term(term_name, section)
        for term_name, section in _extract_term_sections(content)
    ]

    return ParsedContext(
        name=context_name,
        vision_statement=vision_statement,
        terms=terms,
        source_file=_display_path(path),
    )


def _safe_load_yaml_mapping(path: Path) -> dict[str, object]:
    """Load a YAML document and return mapping root or empty mapping."""
    loader = YAML(typ="safe")
    data = loader.load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    return {}


def _first_non_empty(data: dict[str, object], keys: tuple[str, ...]) -> str:
    """Return the first non-empty string value for keys in priority order."""
    for key in keys:
        value = data.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return ""


def _extract_doctrine_terms(doctrine_root: Path) -> list[DoctrineArtifactTerm]:
    """Extract doctrine tactic/directive artifacts as glossary terms."""
    targets: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
        ("tactics", ("name", "title"), ("description", "purpose", "intent")),
        ("directives", ("title", "name"), ("description", "intent", "purpose")),
    )
    terms: list[DoctrineArtifactTerm] = []

    for directory, name_keys, description_keys in targets:
        artifact_dir = doctrine_root / directory
        if not artifact_dir.exists():
            continue

        for path in sorted(artifact_dir.glob("*.yaml")):
            data = _safe_load_yaml_mapping(path)
            artifact_id = _first_non_empty(data, ("id",))
            name = _first_non_empty(data, name_keys)
            description = _first_non_empty(data, description_keys)

            if not artifact_id or not name or not description:
                continue

            terms.append(
                DoctrineArtifactTerm(
                    artifact_id=artifact_id,
                    name=name,
                    description=description,
                    artifact_type=directory[:-1],
                    source_file=_display_path(path),
                )
            )

    return sorted(terms, key=lambda term: (term.artifact_type, term.name.lower()))


def build_doctrine_context(doctrine_root: Path) -> ParsedContext | None:
    """Build a generated doctrine artifact context from repository doctrine files."""
    terms = _extract_doctrine_terms(doctrine_root)
    if not terms:
        return None

    parsed_terms: list[ParsedTerm] = []
    for term in terms:
        parsed_terms.append(
            ParsedTerm(
                name=term.name,
                definition=term.description,
                aliases=[],
                examples=[],
                meta={
                    "id": term.artifact_id,
                    "description": term.description,
                    "artifact_type": term.artifact_type,
                    "source": term.source_file,
                },
            )
        )

    return ParsedContext(
        name="Doctrine Artifacts",
        vision_statement="Terms extracted from doctrine directives and tactics.",
        terms=parsed_terms,
        source_file="src/doctrine/**/*",
    )


def write_contextive_file(context: ParsedContext, out_path: Path, yaml: YAML) -> None:
    """Write one contextive glossary YAML file for a parsed context."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    context_doc: dict[str, object] = {
        "contexts": [
            {
                "name": context.name,
                "domainVisionStatement": context.vision_statement,
                "meta": {
                    "Generated from": context.source_file,
                },
                "terms": [],
            }
        ]
    }

    terms = context_doc["contexts"][0]["terms"]  # type: ignore[index]
    for term in context.terms:
        term_doc: dict[str, object] = {
            "name": term.name,
            "definition": term.definition,
        }
        if term.aliases:
            term_doc["aliases"] = term.aliases
        if term.examples:
            term_doc["examples"] = term.examples
        if term.meta:
            term_doc["meta"] = term.meta

        terms.append(term_doc)

    with out_path.open("w", encoding="utf-8") as handle:
        yaml.dump(context_doc, handle)


def write_index_file(import_paths: list[str], out_path: Path, yaml: YAML) -> None:
    """Write the root Contextive index file with imports."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    index_doc = {"imports": import_paths}
    with out_path.open("w", encoding="utf-8") as handle:
        yaml.dump(index_doc, handle)


def write_project_glossary(index_path: Path, out_path: Path, yaml: YAML) -> None:
    """Write project-level Contextive entrypoint that imports memory index."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    relative_to_project = index_path.relative_to(out_path.parent)
    project_doc = {"imports": [f"./{relative_to_project.as_posix()}"]}
    with out_path.open("w", encoding="utf-8") as handle:
        yaml.dump(project_doc, handle)


def compile_glossary(
    input_dir: Path,
    output_dir: Path,
    index_path: Path,
    project_glossary_path: Path | None = PROJECT_GLOSSARY,
    doctrine_root: Path | None = DOCTRINE_ROOT,
) -> None:
    """Compile markdown glossary contexts into Contextive YAML files."""
    if not input_dir.exists():
        msg = f"Input directory does not exist: {input_dir}"
        raise FileNotFoundError(msg)

    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 100

    context_files = sorted(input_dir.glob("*.md"))
    parsed_contexts = [parse_context_file(path) for path in context_files]
    if doctrine_root is not None:
        doctrine_context = build_doctrine_context(doctrine_root)
        if doctrine_context is not None:
            parsed_contexts.append(doctrine_context)

    import_paths: list[str] = []
    for context in parsed_contexts:
        file_name = f"{_slugify(context.name)}.glossary.yml"
        out_path = output_dir / file_name
        write_contextive_file(context, out_path, yaml)
        relative_to_index = out_path.relative_to(index_path.parent)
        import_paths.append(f"./{relative_to_index.as_posix()}")

    write_index_file(import_paths, index_path, yaml)
    if project_glossary_path is not None:
        write_project_glossary(index_path, project_glossary_path, yaml)


def build_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Compile markdown glossary contexts into Contextive glossary YAML files.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_CONTEXTS_DIR,
        help="Directory containing source markdown context files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_CONTEXTS_DIR,
        help="Directory where generated .glossary.yml context files are written.",
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=OUTPUT_INDEX,
        help="Path for the generated root Contextive glossary imports file.",
    )
    parser.add_argument(
        "--project-glossary",
        type=Path,
        default=PROJECT_GLOSSARY,
        help="Path for generated project-level glossary entrypoint.",
    )
    parser.add_argument(
        "--doctrine-root",
        type=Path,
        default=DOCTRINE_ROOT,
        help="Doctrine root directory used to extract doctrine artifact glossary terms.",
    )
    return parser


def main() -> int:
    """Run glossary compilation from CLI arguments."""
    parser = build_parser()
    args = parser.parse_args()

    compile_glossary(
        args.input,
        args.output,
        args.index,
        args.project_glossary,
        args.doctrine_root,
    )
    print(f"Compiled Contextive glossary index: {args.index}")
    print(f"Compiled context files in: {args.output}")
    print(f"Updated project glossary entrypoint: {args.project_glossary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
