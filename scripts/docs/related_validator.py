"""``related:`` frontmatter graph validator (IC-03 / FR-005).

Walks every ``docs/**/*.md`` page, reads its YAML frontmatter ``related:``
list, and resolves each entry — a repo-relative path — against the
repository root. A ``related:`` entry that does not resolve to an existing
file is a **dangling edge**.

Per ADR ``2026-06-27-1-common-docs-reconciliation`` the canonical ``related:``
form is a list of resolvable repo-relative ``.md`` paths. This validator is
**report-only** (exit ``0``; C-002): it prints what it finds and records a
baseline, but it does not fail CI. Mission B turns the wired ``--strict`` flag
on to flip the exit semantics to blocking.

The validator never mutates the docs tree (C-006) and depends only on the
standard library plus ``ruamel.yaml`` (already a project dependency).

Output shape (per the rulers contract)::

    { "checked_count": int, "dangling_edges": [ {"from": path, "to": path} ] }

where ``checked_count`` is the number of ``related:`` edges examined — so a
"0 dangling" result can never silently mean "0 checked".
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from scripts.docs._inventory import parse_frontmatter

__all__ = [
    "DEFAULT_DOCS_ROOT",
    "DanglingEdge",
    "RelatedReport",
    "build_parser",
    "main",
    "validate_related",
]

DEFAULT_DOCS_ROOT: Final[str] = "docs"


@dataclass(slots=True, frozen=True)
class DanglingEdge:
    """A ``related:`` edge whose target does not resolve to an existing file."""

    from_path: str
    to_path: str

    def as_dict(self) -> dict[str, str]:
        """Serialize to the contract's ``{from, to}`` shape."""
        return {"from": self.from_path, "to": self.to_path}


@dataclass(slots=True, frozen=True)
class RelatedReport:
    """Result of a ``related:`` graph walk."""

    checked_count: int = 0
    dangling_edges: list[DanglingEdge] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        """Serialize to the contract's JSON shape."""
        return {
            "checked_count": self.checked_count,
            "dangling_edges": [edge.as_dict() for edge in self.dangling_edges],
        }


def validate_related(*, docs_root: Path, repo_root: Path) -> RelatedReport:
    """Walk ``docs_root`` and resolve every ``related:`` edge against ``repo_root``.

    Parameters
    ----------
    docs_root:
        Directory whose ``*.md`` files are scanned for frontmatter.
    repo_root:
        Base against which each repo-relative ``related:`` entry is resolved.

    Returns
    -------
    RelatedReport
        ``checked_count`` (total edges examined) and the dangling edges, in
        deterministic ``(from, to)`` order.
    """
    checked_count = 0
    dangling: list[DanglingEdge] = []

    if not docs_root.exists() or not docs_root.is_dir():
        return RelatedReport(checked_count=0, dangling_edges=[])

    for md_path in sorted(docs_root.rglob("*.md")):
        related = _read_related(md_path)
        if not related:
            continue
        from_rel = _repo_relative(md_path, repo_root)
        for entry in related:
            checked_count += 1
            if not _resolves(entry, repo_root):
                dangling.append(DanglingEdge(from_path=from_rel, to_path=entry))

    dangling.sort(key=lambda edge: (edge.from_path, edge.to_path))
    return RelatedReport(checked_count=checked_count, dangling_edges=dangling)


def _read_related(md_path: Path) -> list[str]:
    """Return the ``related:`` list from a page's frontmatter (``[]`` if none)."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return []

    frontmatter = parse_frontmatter(text)
    raw = frontmatter.get("related")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, str) and item.strip()]


def _resolves(entry: str, repo_root: Path) -> bool:
    """An entry resolves when its repo-relative path exists as a file."""
    candidate = (repo_root / entry).resolve()
    return candidate.is_file()


def _repo_relative(path: Path, repo_root: Path) -> str:
    """Render ``path`` as a POSIX repo-relative string (best-effort)."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def build_parser() -> argparse.ArgumentParser:
    """Build the validator CLI parser."""
    parser = argparse.ArgumentParser(
        prog="related_validator",
        description=(
            "Validate docs/ frontmatter 'related:' edges. Report-only "
            "(exit 0) unless --strict is passed."
        ),
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=Path(DEFAULT_DOCS_ROOT),
        help=f"Docs tree to scan (default: {DEFAULT_DOCS_ROOT}).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Base for resolving repo-relative 'related:' entries (default: cwd).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON instead of a human summary.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit non-zero when dangling edges are found. Wired but OFF by "
            "default in Mission A (report-only, C-002); Mission B turns it on."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    args = build_parser().parse_args(argv)
    report = validate_related(docs_root=args.docs_root, repo_root=args.repo_root)
    _emit(report, as_json=args.json)
    if args.strict and report.dangling_edges:
        return 1
    return 0


def _emit(report: RelatedReport, *, as_json: bool) -> None:
    """Print the report — JSON payload or a human-readable summary."""
    if as_json:
        sys.stdout.write(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n")
        return

    sys.stdout.write(
        f"related_validator: checked {report.checked_count} edge(s); "
        f"{len(report.dangling_edges)} dangling.\n"
    )
    for edge in report.dangling_edges:
        sys.stdout.write(f"  DANGLING {edge.from_path} -> {edge.to_path}\n")


if __name__ == "__main__":  # pragma: no cover - module-level CLI guard
    raise SystemExit(main())
