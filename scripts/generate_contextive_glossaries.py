#!/usr/bin/env python3
"""
Generate Contextive-compatible YAML glossary files from canonical glossary markdown.

Reads glossary/contexts/*.md and a traceability map to produce:
  - src/specify_cli/.contextive/<slug>.yml  (one per referenced context)
  - <scope-path>/.contextive.yml            (imports relevant contexts)

Usage:
    python scripts/generate_contextive_glossaries.py generate
    python scripts/generate_contextive_glossaries.py check

The 'check' mode exits with code 1 if any generated file is missing or stale.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_CONTEXTS_DIR = REPO_ROOT / "glossary" / "contexts"
MAP_FILE = REPO_ROOT / ".kittify" / "traceability" / "contextive-map.yaml"

GENERATED_HEADER_LINES = [
    "# GENERATED FILE — do not edit manually.",
    "# Run: python scripts/generate_contextive_glossaries.py generate",
    "#",
]

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class GlossaryTerm:
    name: str
    definition: str
    status: str = "candidate"
    aliases: list[str] = field(default_factory=list)


@dataclass
class GlossaryContext:
    slug: str
    name: str
    description: str
    terms: list[GlossaryTerm]
    source_file: Path


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------


def _strip_md_links(text: str) -> str:
    """Replace [text](url) with text, keeping readable content."""
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)


def _clean_cell(text: str) -> str:
    """Strip inline code backticks and normalise whitespace from a table cell."""
    text = text.strip()
    # Remove bold markers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return _strip_md_links(text).strip()


def parse_context_file(md_file: Path) -> GlossaryContext:
    """Parse a glossary context markdown file into structured data."""
    text = md_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    context_name: str = md_file.stem
    context_desc: str = ""

    # Locate the ## Context: heading
    for i, line in enumerate(lines):
        m = re.match(r"^##\s+Context:\s+(.+)$", line)
        if m:
            context_name = m.group(1).strip()
            # First non-empty, non-heading paragraph after heading = description
            for j in range(i + 1, len(lines)):
                stripped = lines[j].strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("|"):
                    context_desc = stripped
                    break
            break

    # Extract terms
    terms: list[GlossaryTerm] = []
    i = 0
    while i < len(lines):
        m = re.match(r"^###\s+(.+)$", lines[i])
        if m:
            term_name = m.group(1).strip()
            definition = ""
            status = "candidate"
            aliases: list[str] = []

            j = i + 1
            while j < len(lines):
                line = lines[j]
                # Stop at next heading
                if re.match(r"^#{1,3}\s", line):
                    break

                # Definition row
                dm = re.match(r"\|\s*\*\*Definition\*\*\s*\|\s*(.+?)\s*\|?\s*$", line)
                if dm:
                    definition = _clean_cell(dm.group(1))

                # Status row
                sm = re.match(r"\|\s*\*\*Status\*\*\s*\|\s*(.+?)\s*\|?\s*$", line)
                if sm:
                    status = _clean_cell(sm.group(1))

                j += 1

            terms.append(GlossaryTerm(
                name=term_name,
                definition=definition,
                status=status,
                aliases=aliases,
            ))
            i = j
        else:
            i += 1

    # Sort terms alphabetically for deterministic output
    terms.sort(key=lambda t: t.name.lower())

    return GlossaryContext(
        slug=md_file.stem,
        name=context_name,
        description=context_desc,
        terms=terms,
        source_file=md_file,
    )


# ---------------------------------------------------------------------------
# YAML rendering
# ---------------------------------------------------------------------------


def _yaml_quote(text: str) -> str:
    """Return text as a YAML double-quoted scalar, escaping special chars."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_context_yaml(ctx: GlossaryContext, repo_root: Path | None = None) -> str:
    """Render a GlossaryContext as a Contextive YAML string."""
    _root = repo_root or REPO_ROOT
    try:
        source_rel = ctx.source_file.relative_to(_root).as_posix()
    except ValueError:
        source_rel = ctx.source_file.name

    out: list[str] = [*GENERATED_HEADER_LINES, f"# Source: {source_rel}", ""]
    out.append("contexts:")
    out.append(f"  - name: {_yaml_quote(ctx.name)}")

    if ctx.description:
        out.append(f"    domainVisionStatement: {_yaml_quote(ctx.description)}")

    out.append("    terms:")

    for term in ctx.terms:
        out.append(f"      - name: {_yaml_quote(term.name)}")
        if term.definition:
            out.append(f"        definition: {_yaml_quote(term.definition)}")
        if term.aliases:
            out.append("        aliases:")
            for alias in term.aliases:
                out.append(f"          - {_yaml_quote(alias)}")

    return "\n".join(out) + "\n"


def render_scope_yaml(scope_path: Path, context_base_dir: Path, context_slugs: list[str]) -> str:
    """Render a scope .contextive.yml using imports to avoid duplication."""
    rel = os.path.relpath(context_base_dir, scope_path)

    out: list[str] = [
        *GENERATED_HEADER_LINES,
        "# Imports context glossaries relevant to this package.",
        "# See .kittify/traceability/contextive-map.yaml for the scope mapping.",
        "",
        "imports:",
    ]
    for slug in sorted(context_slugs):
        import_path = Path(rel) / f"{slug}.yml"
        # Always use forward slashes (Contextive cross-platform)
        out.append(f'  - "{import_path.as_posix()}"')

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Map loading & validation
# ---------------------------------------------------------------------------


@dataclass
class ScopeEntry:
    path: str           # relative to repo root, e.g. "src/specify_cli/glossary"
    contexts: list[str]
    description: str = ""


@dataclass
class TraceabilityMap:
    context_base_dir: str
    scopes: list[ScopeEntry]


def load_map(map_file: Path) -> TraceabilityMap:
    """Load and parse the traceability map YAML."""
    with map_file.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    context_base_dir = data.get("context_base_dir", "src/specify_cli/.contextive")
    scopes = [
        ScopeEntry(
            path=s["path"],
            contexts=s.get("contexts", []),
            description=s.get("description", ""),
        )
        for s in data.get("scopes", [])
    ]
    return TraceabilityMap(context_base_dir=context_base_dir, scopes=scopes)


def validate_map(tmap: TraceabilityMap) -> list[str]:
    """Return a list of validation error strings (empty if valid)."""
    errors: list[str] = []
    for scope in tmap.scopes:
        for ctx_slug in scope.contexts:
            md_file = GLOSSARY_CONTEXTS_DIR / f"{ctx_slug}.md"
            if not md_file.exists():
                errors.append(
                    f"Scope '{scope.path}' references context '{ctx_slug}' "
                    f"but '{md_file}' does not exist."
                )
    return errors


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------


def collect_all_context_slugs(tmap: TraceabilityMap) -> set[str]:
    slugs: set[str] = set()
    for scope in tmap.scopes:
        slugs.update(scope.contexts)
    return slugs


def generate(repo_root: Path, tmap: TraceabilityMap) -> dict[Path, str]:
    """
    Return a mapping of {output_path: file_content} for all files to be written.
    Does NOT write anything to disk.
    """
    context_base_dir = repo_root / tmap.context_base_dir
    output: dict[Path, str] = {}

    # Parse and render each referenced context
    all_slugs = collect_all_context_slugs(tmap)
    parsed_contexts: dict[str, GlossaryContext] = {}
    for slug in all_slugs:
        md_file = GLOSSARY_CONTEXTS_DIR / f"{slug}.md"
        ctx = parse_context_file(md_file)
        parsed_contexts[slug] = ctx
        out_path = context_base_dir / f"{slug}.yml"
        output[out_path] = render_context_yaml(ctx, repo_root)

    # Render scope files (with imports)
    for scope in tmap.scopes:
        scope_path = repo_root / scope.path
        out_path = scope_path / ".contextive.yml"
        output[out_path] = render_scope_yaml(scope_path, context_base_dir, scope.contexts)

    return output


# ---------------------------------------------------------------------------
# Write / Check
# ---------------------------------------------------------------------------


def cmd_generate(repo_root: Path, tmap: TraceabilityMap) -> int:
    """Write all generated files to disk. Returns exit code."""
    output = generate(repo_root, tmap)
    for path, content in sorted(output.items()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        rel = path.relative_to(repo_root).as_posix()
        print(f"  wrote  {rel}")
    print(f"\nGenerated {len(output)} file(s).")
    return 0


def cmd_check(repo_root: Path, tmap: TraceabilityMap) -> int:
    """Check that all generated files are up-to-date. Returns exit code."""
    output = generate(repo_root, tmap)
    stale: list[str] = []
    missing: list[str] = []

    for path, expected_content in sorted(output.items()):
        rel = path.relative_to(repo_root).as_posix()
        if not path.exists():
            missing.append(rel)
        elif path.read_text(encoding="utf-8") != expected_content:
            stale.append(rel)

    if missing:
        print("Missing generated files (run `generate` to create them):")
        for p in missing:
            print(f"  missing  {p}")
    if stale:
        print("Stale generated files (run `generate` to update them):")
        for p in stale:
            print(f"  stale    {p}")

    if missing or stale:
        print("\nRun: python scripts/generate_contextive_glossaries.py generate")
        return 1

    print(f"All {len(output)} generated file(s) are up-to-date.")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    if not argv or argv[0] not in ("generate", "check"):
        print(f"Usage: {Path(sys.argv[0]).name} <generate|check>")
        return 2

    cmd = argv[0]

    # Validate map exists
    if not MAP_FILE.exists():
        print(f"Error: traceability map not found: {MAP_FILE}")
        return 1

    tmap = load_map(MAP_FILE)
    errors = validate_map(tmap)
    if errors:
        print("Traceability map validation errors:")
        for e in errors:
            print(f"  {e}")
        return 1

    if cmd == "generate":
        return cmd_generate(REPO_ROOT, tmap)
    else:
        return cmd_check(REPO_ROOT, tmap)


if __name__ == "__main__":
    sys.exit(main())
