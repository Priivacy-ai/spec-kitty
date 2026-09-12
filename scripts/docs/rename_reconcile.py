"""Rename / deletion reconciliation gate (IC-03a / NFR-005, FR-023).

A bulk-move mission must not silently drop or relocate a page outside the
declared spine. Two set-containment checks enforce that:

* ``rename_reconcile`` (reverse direction) — every rename/deletion the git diff
  reports under ``docs/`` (and the retired root directories the occurrence map
  names) MUST be covered by an ``occurrence_map.yaml`` ``moves:`` entry. A
  rename or deletion with no corresponding ``from:`` prefix is off-spine and
  reported.
* ``occurrence_subset_redirect`` (forward cross-check) — every concrete ``.md``
  file move whose destination is not ``RETIRE`` must have its published old-URL
  present as a key in ``redirect_map.yaml`` (the derived redirect spine), so a
  moved page keeps a working redirect.

**Path-configurable / spine-not-in-lane safe (C-010).** The occurrence-map spine
is authored on the planning branch and may not be materialized in an execution
lane. Both the occurrence-map and redirect-map paths are parameters (defaulting
to their canonical repo-relative locations); the gate logic is exercised by
fixtures and never depends on the live spine being checked out. When the
occurrence map is absent the gate is a no-op with an examined count of ``0``
(reported), never a crash.

**Advisory** at this stage (IC-03a): report-only exit ``0`` unless ``--strict``
is passed, which flips the exit code to ``1`` on any finding. WP13 turns the
reconcile blocking once the terminal spine is regenerated.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

__all__ = [
    "DEFAULT_OCCURRENCE_MAP",
    "DEFAULT_REDIRECT_MAP",
    "ReconcileReport",
    "Violation",
    "build_parser",
    "check_occurrence_subset_redirect",
    "check_renames_covered",
    "load_moves",
    "main",
    "renames_and_deletions",
    "run_reconcile",
]

DEFAULT_OCCURRENCE_MAP: Final[str] = (
    "kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml"
)
DEFAULT_REDIRECT_MAP: Final[str] = "scripts/docs/redirect_map.yaml"

_RETIRE: Final[str] = "RETIRE"
_DOCS_PREFIX: Final[str] = "docs/"


@dataclass(slots=True, frozen=True)
class Violation:
    """One reconciliation finding: ``{rule_id, path, message}``."""

    rule_id: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Serialize to the ``{rule_id, path, message}`` shape."""
        return {"rule_id": self.rule_id, "path": self.path, "message": self.message}


@dataclass(slots=True, frozen=True)
class Move:
    """One occurrence-map ``moves:`` entry: source path(s) -> destination."""

    from_paths: tuple[str, ...]
    to: str


@dataclass(slots=True, frozen=True)
class ReconcileReport:
    """Aggregate result of a reconciliation run."""

    renames_examined: int = 0
    moves_examined: int = 0
    violations: list[Violation] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        """Serialize to the report JSON shape."""
        return {
            "renames_examined": self.renames_examined,
            "moves_examined": self.moves_examined,
            "violations": [v.as_dict() for v in self.violations],
        }


# --- Spine loading ------------------------------------------------------------


def load_moves(occurrence_map_path: Path) -> list[Move]:
    """Load the ``moves:`` list from an occurrence map (``[]`` when absent)."""
    if not occurrence_map_path.is_file():
        return []
    yaml = YAML(typ="safe")
    try:
        with occurrence_map_path.open("r", encoding="utf-8") as handle:
            raw: Any = yaml.load(handle)
    except (OSError, YAMLError) as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"cannot read occurrence map {occurrence_map_path}: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        return []
    moves_raw = raw.get("moves")
    if not isinstance(moves_raw, list):
        return []
    moves: list[Move] = []
    for entry in moves_raw:
        if not isinstance(entry, dict):
            continue
        from_raw = entry.get("from")
        to_raw = entry.get("to")
        if isinstance(from_raw, str):
            from_list = [from_raw]
        elif isinstance(from_raw, list):
            from_list = [str(item) for item in from_raw if isinstance(item, str)]
        else:
            continue
        if not from_list or not isinstance(to_raw, str):
            continue
        moves.append(Move(from_paths=tuple(from_list), to=to_raw))
    return moves


def _load_redirect_keys(redirect_map_path: Path) -> set[str]:
    """Return the key set of a redirect map (``set()`` when absent)."""
    if not redirect_map_path.is_file():
        return set()
    yaml = YAML(typ="safe")
    try:
        with redirect_map_path.open("r", encoding="utf-8") as handle:
            raw: Any = yaml.load(handle)
    except (OSError, YAMLError) as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"cannot read redirect map {redirect_map_path}: {exc}"
        ) from exc
    return {str(key) for key in raw} if isinstance(raw, dict) else set()


# --- Git rename / deletion extraction ----------------------------------------


def renames_and_deletions(base: str, repo_root: Path) -> list[str]:
    """Return source paths of every rename/deletion vs ``base`` (rename-aware).

    Uses ``git diff --find-renames --name-status`` so a moved page surfaces as
    its ORIGINAL path (the thing the spine must account for), and a plain delete
    surfaces as its path. Additions and in-place edits are ignored.
    """
    result = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--find-renames", "--name-status", base],
        capture_output=True,
        text=True,
        check=True,
    )
    sources: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            sources.append(parts[1])  # original path of a rename
        elif status.startswith("D") and len(parts) >= 2:
            sources.append(parts[1])  # deleted path
    return sorted(sources)


# --- Coverage helpers ---------------------------------------------------------


def _from_prefixes(moves: list[Move]) -> tuple[str, ...]:
    prefixes: list[str] = []
    for move in moves:
        prefixes.extend(move.from_paths)
    return tuple(prefixes)


def _covers(prefix: str, path: str) -> bool:
    """True when ``prefix`` (a file path or a trailing-slash dir) covers ``path``."""
    if prefix.endswith("/"):
        return path == prefix.rstrip("/") or path.startswith(prefix)
    return path == prefix


def _non_docs_scope_prefixes(prefixes: tuple[str, ...]) -> tuple[str, ...]:
    """Retired-root scope: the map's own non-``docs/`` source prefixes."""
    return tuple(p for p in prefixes if not p.startswith(_DOCS_PREFIX))


def _in_scope(path: str, non_docs_scope: tuple[str, ...]) -> bool:
    if path.startswith(_DOCS_PREFIX):
        return True
    return any(_covers(prefix, path) for prefix in non_docs_scope)


# --- Gate 1: rename/deletion reconciliation (reverse) ------------------------


def check_renames_covered(sources: list[str], moves: list[Move]) -> list[Violation]:
    """Flag in-scope rename/deletion sources with no covering ``moves:`` entry."""
    prefixes = _from_prefixes(moves)
    non_docs_scope = _non_docs_scope_prefixes(prefixes)
    violations: list[Violation] = []
    for source in sources:
        if not _in_scope(source, non_docs_scope):
            continue
        if any(_covers(prefix, source) for prefix in prefixes):
            continue
        violations.append(
            Violation(
                rule_id="rename_reconcile",
                path=source,
                message=(
                    f"{source} was renamed/deleted but is not covered by any "
                    "occurrence_map.yaml moves: entry (off-spine)"
                ),
            )
        )
    return violations


# --- Gate 2: occurrence-map subset of redirect-map (forward) -----------------


def _published_old_url(docs_path: str) -> str | None:
    """Derive a moved page's published old URL (``docs/x/y.md`` -> ``x/y.html``)."""
    if not docs_path.startswith(_DOCS_PREFIX) or not docs_path.endswith(".md"):
        return None
    return docs_path[len(_DOCS_PREFIX) : -len(".md")] + ".html"


def check_occurrence_subset_redirect(
    moves: list[Move], redirect_keys: set[str]
) -> list[Violation]:
    """Flag concrete file moves whose published old URL has no redirect entry."""
    violations: list[Violation] = []
    for move in moves:
        if move.to == _RETIRE:
            continue
        for source in move.from_paths:
            url = _published_old_url(source)
            if url is None:
                continue  # directory / non-docs move — covered by the reverse gate
            if url not in redirect_keys:
                violations.append(
                    Violation(
                        rule_id="occurrence_subset_redirect",
                        path=source,
                        message=(
                            f"{source} moves to '{move.to}' but its published URL "
                            f"'{url}' is absent from the redirect map (broken "
                            "redirect)"
                        ),
                    )
                )
    return violations


# --- Aggregation + CLI --------------------------------------------------------


def run_reconcile(
    *,
    base: str,
    repo_root: Path,
    occurrence_map_path: Path | None = None,
    redirect_map_path: Path | None = None,
    cross_check: bool = True,
) -> ReconcileReport:
    """Run the rename-reconcile gate and (optionally) the redirect cross-check."""
    occ_path = occurrence_map_path or repo_root / DEFAULT_OCCURRENCE_MAP
    red_path = redirect_map_path or repo_root / DEFAULT_REDIRECT_MAP
    moves = load_moves(occ_path)
    sources = renames_and_deletions(base, repo_root)

    violations = check_renames_covered(sources, moves)
    if cross_check:
        redirect_keys = _load_redirect_keys(red_path)
        violations.extend(check_occurrence_subset_redirect(moves, redirect_keys))
    violations.sort(key=lambda v: (v.rule_id, v.path))
    return ReconcileReport(
        renames_examined=len(sources),
        moves_examined=len(moves),
        violations=violations,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the rename-reconcile CLI parser."""
    parser = argparse.ArgumentParser(
        prog="rename_reconcile",
        description=(
            "Assert every rename/deletion is accounted for by the "
            "occurrence_map.yaml spine, and every file move has a redirect. "
            "Report-only (exit 0) unless --strict is passed."
        ),
    )
    parser.add_argument(
        "--base",
        required=True,
        help="Git ref the diff is computed against (e.g. origin/main).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: cwd).",
    )
    parser.add_argument(
        "--occurrence-map",
        type=Path,
        default=None,
        help=f"Occurrence map path (default: <repo-root>/{DEFAULT_OCCURRENCE_MAP}).",
    )
    parser.add_argument(
        "--redirect-map",
        type=Path,
        default=None,
        help=f"Redirect map path (default: <repo-root>/{DEFAULT_REDIRECT_MAP}).",
    )
    parser.add_argument(
        "--no-cross-check",
        action="store_true",
        help="Skip the occurrence-map ⊆ redirect-map cross-check.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON instead of a human summary.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any finding exists (blocking). Advisory off.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    args = build_parser().parse_args(argv)
    report = run_reconcile(
        base=args.base,
        repo_root=args.repo_root,
        occurrence_map_path=args.occurrence_map,
        redirect_map_path=args.redirect_map,
        cross_check=not args.no_cross_check,
    )
    _emit(report, as_json=args.json)
    if args.strict and report.violations:
        return 1
    return 0


def _emit(report: ReconcileReport, *, as_json: bool) -> None:
    """Print the report — JSON payload or a human-readable summary."""
    if as_json:
        sys.stdout.write(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n")
        return
    sys.stdout.write(
        f"rename_reconcile: examined {report.renames_examined} rename/deletion(s) "
        f"against {report.moves_examined} move(s); "
        f"{len(report.violations)} finding(s).\n"
    )
    for violation in report.violations:
        sys.stdout.write(
            f"  [{violation.rule_id}] {violation.path}: {violation.message}\n"
        )


if __name__ == "__main__":  # pragma: no cover - module-level CLI guard
    raise SystemExit(main())
