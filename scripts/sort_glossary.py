#!/usr/bin/env python3
"""Sort a spec-kitty glossary seed YAML file alphabetically by surface term.

Canonical sort logic lives in specify_cli.glossary.scope.save_seed_file, which
is called automatically whenever a seed file is updated through the Python API.

This script is the escape hatch for files edited outside that API (manual edits,
git merges, direct agent writes). It uses the same sort logic but operates on raw
YAML dicts so it works without the package installed.

Usage:
    python3 scripts/sort_glossary.py .kittify/glossaries/spec_kitty_core.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path


def _needs_quotes(value: str) -> bool:
    return ": " in value or "'" in value


def _render_scalar(value: str) -> str:
    if _needs_quotes(value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _confidence_str(conf: float) -> str:
    return f"{conf:.1f}" if conf == int(conf) else str(round(conf, 4))


def sort_glossary_file(path: Path) -> bool:
    """Sort terms alphabetically by surface in place. Returns True if changed."""
    import yaml

    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or "terms" not in data:
        return False

    terms = data["terms"] or []
    sorted_terms = sorted(terms, key=lambda t: t["surface"].lower())

    if [t["surface"] for t in sorted_terms] == [t["surface"] for t in terms]:
        return False

    header: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped == "":
            header.append(line)
        else:
            break

    out: list[str] = list(header)
    if not sorted_terms:
        out.append("terms: []")
    else:
        out.append("terms:")
    for term in sorted_terms:
        out.append("")
        out.append(f"  - surface: {_render_scalar(term['surface'])}")
        out.append(f"    definition: {_render_scalar(term['definition'])}")
        out.append(f"    confidence: {_confidence_str(term['confidence'])}")
        out.append(f"    status: {term['status']}")
    out.append("")

    path.write_text("\n".join(out), encoding="utf-8")
    return True


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        print("usage: sort_glossary.py <glossary.yaml> [...]", file=sys.stderr)
        sys.exit(1)

    for path in paths:
        if not path.exists():
            print(f"skip (not found): {path}", file=sys.stderr)
            continue
        if sort_glossary_file(path):
            print(f"sorted: {path}")


if __name__ == "__main__":
    main()
