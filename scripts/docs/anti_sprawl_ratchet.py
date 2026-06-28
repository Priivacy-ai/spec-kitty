"""Common Docs anti-sprawl structure ratchet (Mission A WP05 — ruler 3).

This is the third and final *ruler* of the Common Docs consolidation: a
**report-only** structural guard that detects the four sprawl regressions the
reconciliation ADR (``docs/adr/3.x/2026-06-27-1-common-docs-reconciliation.md``)
and ``DIRECTIVE_042`` are meant to cure. Mission B flips it to **blocking**
against the cleaned tree (paired with a full-gate dry-run per C-004); here it
only *reports* — it always exits ``0`` unless ``--strict`` is passed.

Four detectors (C-002 / FR-007)
-------------------------------
1. **second_doc_root** — a second documentation root: any top-level directory
   other than the single ``docs/`` root that itself carries an ``index.md``
   (the Common Docs root marker), i.e. a competing root claiming to be docs.
2. **section_missing_index** — any ``docs/*/`` section directory missing its
   own ``index.md`` (every Common Docs section directory must carry one).
3. **adr_missing_frontmatter** — an Architecture Decision Record (a ``*.md``
   file under any ``adr/`` directory) that does not open with a YAML
   frontmatter block carrying the required ADR schema keys.
4. **version_shadow_tree** — a re-introduced ``docs/<version>x`` shadow tree
   (``docs/1x/``, ``docs/2.x/`` …), the per-version duplicate the ADR retires.

Content-anchored floor (C-002 / T022)
-------------------------------------
The ratchet compares against a **concrete enumerated baseline** — the 13
canonical Common Docs section names (:data:`CANONICAL_SECTIONS`) and "exactly
one docs root" (:data:`EXPECTED_DOC_ROOTS`) — not an empty set that would pass
everything. This mirrors the ``tests/architectural/`` concrete-floor idiom.

Directive binding (C-003 / T023)
--------------------------------
The report references the governing directive id via the **single shared
constant** :data:`doctrine.directives.common_docs.COMMON_DOCS_DIRECTIVE_ID`
(WP02's source of truth) — never a hard-coded string. The binding is a
*resolvable contract*: :func:`directive_node_present` confirms the id resolves
to a loaded node in ``src/doctrine/graph.yaml``, so a typo or placeholder fails
rather than silently passing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

import yaml

# ---------------------------------------------------------------------------
# Self-locating import of the shared directive constant (T023 binding).
#
# The constant lives at ``<repo>/src/doctrine/directives/common_docs.py``. In a
# parallel lane worktree the installed ``doctrine`` package may resolve to a
# sibling checkout that predates WP02, so we anchor sys.path to *this* tree's
# ``src`` (computed from __file__) before importing — the binding must resolve
# against the co-located source of truth, not a stale editable install.
# ---------------------------------------------------------------------------
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_SRC_DIR: Final[Path] = _REPO_ROOT / "src"
if _SRC_DIR.is_dir() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
# Also anchor the repo root so ``scripts.docs._inventory`` (the shared
# frontmatter extractor) imports cleanly when this ratchet runs as a standalone
# script (``python scripts/docs/anti_sprawl_ratchet.py``), where ``sys.path[0]``
# is the script directory rather than the repo root.
if _REPO_ROOT.is_dir() and str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from doctrine.directives.common_docs import (  # noqa: E402  (sys.path bootstrap above)
    COMMON_DOCS_DIRECTIVE_ID,
)
from scripts.docs._inventory import (  # noqa: E402  (sys.path bootstrap above)
    parse_frontmatter,
)

# Explicit public surface (C-007). ``COMMON_DOCS_DIRECTIVE_ID`` is re-exported on
# purpose: the ratchet's binding to WP02's directive id is part of its public
# contract, and the self-test reads it via this module to prove the binding.
__all__ = [
    "ADR_FRONTMATTER_REQUIRED_KEYS",
    "CANONICAL_SECTIONS",
    "COMMON_DOCS_DIRECTIVE_ID",
    "COND_ADR_NO_FRONTMATTER",
    "COND_MISSING_INDEX",
    "COND_SECOND_ROOT",
    "COND_VERSION_SHADOW",
    "EXPECTED_DOC_ROOTS",
    "Violation",
    "build_parser",
    "build_report",
    "collect_violations",
    "detect_adr_missing_frontmatter",
    "detect_missing_section_index",
    "detect_second_doc_root",
    "detect_version_shadow_tree",
    "directive_node_present",
    "floor_baseline",
    "main",
]

# ---------------------------------------------------------------------------
# Content-anchored floor (T022) — the real enumerated baseline, never empty.
# ---------------------------------------------------------------------------
#: The 13 canonical Common Docs sections (ADR D3 / DIRECTIVE_042 procedures).
#: ``index`` is the root ``index.md``; the remaining 12 are section directories.
CANONICAL_SECTIONS: Final[tuple[str, ...]] = (
    "index",
    "context",
    "architecture",
    "adr",
    "plans",
    "api",
    "configuration",
    "integrations",
    "security",
    "guides",
    "operations",
    "migrations",
    "changelog",
)

#: Exactly one documentation root is permitted (ADR D3 integrity rule).
EXPECTED_DOC_ROOTS: Final[int] = 1

#: Required frontmatter keys for an ADR. The ADR schema (ADR D3 / D6) mandates a
#: YAML frontmatter block; these keys are the content-anchored schema the
#: ratchet checks. ``status`` here is the ADR *decision* status
#: (Accepted/Proposed/Superseded) carried in the ADR body today — distinct from
#: the prohibited bare doc-lifecycle ``status`` key (which is ``doc_status``).
ADR_FRONTMATTER_REQUIRED_KEYS: Final[tuple[str, ...]] = ("title", "status", "date")

#: The canonical single documentation root directory name.
DOCS_ROOT_NAME: Final[str] = "docs"

#: Common Docs root marker: a directory carrying this file at its top is a root.
ROOT_MARKER: Final[str] = "index.md"

#: Navigational files that are *not* decision records and so are excluded from
#: the ADR-frontmatter detector — the section/era landing pages. ``index.md`` is
#: the Common Docs section index; ``README.md`` is the era landing page. Both are
#: governed by the missing-section-index detector, not the ADR schema check.
_ADR_NON_RECORD_NAMES: Final[frozenset[str]] = frozenset({ROOT_MARKER, "README.md"})

#: A re-introduced per-version shadow tree under ``docs/`` (``1x``, ``2.x`` …).
_VERSION_SHADOW_RE: Final[re.Pattern[str]] = re.compile(r"^\d+\.?x$")

# Condition identifiers (stable strings used in the structured report).
COND_SECOND_ROOT: Final[str] = "second_doc_root"
COND_MISSING_INDEX: Final[str] = "section_missing_index"
COND_ADR_NO_FRONTMATTER: Final[str] = "adr_missing_frontmatter"
COND_VERSION_SHADOW: Final[str] = "version_shadow_tree"


@dataclass(frozen=True)
class Violation:
    """A single detected sprawl regression."""

    condition: str
    path: str


# ---------------------------------------------------------------------------
# Detectors (FR-007).
# ---------------------------------------------------------------------------
def _immediate_subdirs(directory: Path) -> list[Path]:
    """Return sorted immediate child directories of ``directory`` (or empty)."""
    if not directory.is_dir():
        return []
    return sorted(child for child in directory.iterdir() if child.is_dir())


def detect_second_doc_root(root: Path) -> list[Violation]:
    """Detect a competing documentation root (condition 1).

    Any top-level directory other than ``docs/`` that itself carries an
    ``index.md`` is treated as a second Common Docs root.
    """
    violations: list[Violation] = []
    for child in _immediate_subdirs(root):
        if child.name == DOCS_ROOT_NAME:
            continue
        if (child / ROOT_MARKER).is_file():
            violations.append(
                Violation(COND_SECOND_ROOT, child.relative_to(root).as_posix())
            )
    return violations


def detect_missing_section_index(root: Path) -> list[Violation]:
    """Detect ``docs/*/`` section directories missing ``index.md`` (condition 2)."""
    docs_root = root / DOCS_ROOT_NAME
    violations: list[Violation] = []
    for section in _immediate_subdirs(docs_root):
        if not (section / ROOT_MARKER).is_file():
            violations.append(
                Violation(COND_MISSING_INDEX, section.relative_to(root).as_posix())
            )
    return violations


def _has_adr_frontmatter(text: str) -> bool:
    """Return True iff ``text`` opens with a YAML frontmatter block carrying the
    required ADR schema keys.

    Uses the shared :func:`scripts.docs._inventory.parse_frontmatter` extractor
    (``ruamel``-based) so every docs ruler agrees on what a frontmatter block is
    — an empty mapping (no/malformed frontmatter) yields ``False`` because the
    required keys cannot all be present.
    """
    parsed = parse_frontmatter(text)
    return all(key in parsed for key in ADR_FRONTMATTER_REQUIRED_KEYS)


def _iter_adr_files(root: Path) -> list[Path]:
    """Return sorted ``*.md`` decision records living under any ``adr/`` directory.

    Navigational landing pages (``index.md`` section index, ``README.md`` era
    landing) are *not* decision records — they are covered by the missing-index
    detector — so they are excluded from the ADR frontmatter check.

    Hidden directories (``.worktrees``, ``.git``, ``.venv`` …) are skipped: they
    are never part of the published docs tree and, in a developer checkout with
    sibling lane worktrees under ``.worktrees/``, would otherwise pull thousands
    of unrelated ADR copies into the scan (and are absent in CI's clean
    checkout anyway).
    """
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.name not in _ADR_NON_RECORD_NAMES
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
        and "adr" in {part.lower() for part in path.parent.parts}
    )


def detect_adr_missing_frontmatter(root: Path) -> list[Violation]:
    """Detect ADRs lacking the required YAML frontmatter schema (condition 3)."""
    violations: list[Violation] = []
    for adr in _iter_adr_files(root):
        try:
            text = adr.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if not _has_adr_frontmatter(text):
            violations.append(
                Violation(COND_ADR_NO_FRONTMATTER, adr.relative_to(root).as_posix())
            )
    return violations


def detect_version_shadow_tree(root: Path) -> list[Violation]:
    """Detect re-introduced ``docs/<version>x`` shadow trees (condition 4)."""
    docs_root = root / DOCS_ROOT_NAME
    violations: list[Violation] = []
    for section in _immediate_subdirs(docs_root):
        if _VERSION_SHADOW_RE.match(section.name):
            violations.append(
                Violation(COND_VERSION_SHADOW, section.relative_to(root).as_posix())
            )
    return violations


# ---------------------------------------------------------------------------
# Floor + report assembly (T022 / T021).
# ---------------------------------------------------------------------------
def floor_baseline() -> dict[str, Any]:
    """Return the concrete content-anchored floor (never empty)."""
    return {
        "sections": list(CANONICAL_SECTIONS),
        "doc_roots": EXPECTED_DOC_ROOTS,
    }


def collect_violations(root: Path) -> list[Violation]:
    """Run all four detectors against ``root`` and return the combined list."""
    return [
        *detect_second_doc_root(root),
        *detect_missing_section_index(root),
        *detect_adr_missing_frontmatter(root),
        *detect_version_shadow_tree(root),
    ]


def build_report(root: Path) -> dict[str, Any]:
    """Assemble the structured anti-sprawl report for ``root``."""
    violations = collect_violations(root)
    return {
        "violations": [asdict(v) for v in violations],
        "baseline_count": len(violations),
        "directive_ref": COMMON_DOCS_DIRECTIVE_ID,
        "floor": floor_baseline(),
    }


# ---------------------------------------------------------------------------
# Directive binding resolution (T023 — the binding must resolve, C-003).
# ---------------------------------------------------------------------------
def _default_graph_path(root: Path) -> Path:
    return root / "src" / "doctrine" / "graph.yaml"


def directive_node_present(
    directive_id: str, *, graph_path: Path | None = None, root: Path | None = None
) -> bool:
    """Return True iff ``directive:<directive_id>`` is a loaded directive node.

    Confirms the binding constant resolves to a real node in the doctrine
    relationship graph (``src/doctrine/graph.yaml``) — not merely that the
    string appears in a message somewhere.
    """
    path = graph_path or _default_graph_path(root or _REPO_ROOT)
    if not path.is_file():
        return False
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return False
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return False
    target_urn = f"directive:{directive_id}"
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("urn") == target_urn and node.get("kind") == "directive":
            return True
    return False


# ---------------------------------------------------------------------------
# CLI (T021 report-only exit 0; T024 --strict wired but off; T025 baseline).
# ---------------------------------------------------------------------------
def _render_human(report: dict[str, Any]) -> str:
    lines = [
        "Common Docs anti-sprawl ratchet (report-only ruler 3)",
        f"governed by directive {report['directive_ref']}",
        f"floor: {EXPECTED_DOC_ROOTS} docs root, "
        f"{len(CANONICAL_SECTIONS)} canonical sections",
        f"baseline violations: {report['baseline_count']}",
    ]
    by_condition: dict[str, int] = {}
    for violation in report["violations"]:
        by_condition[violation["condition"]] = (
            by_condition.get(violation["condition"], 0) + 1
        )
    for condition in (
        COND_SECOND_ROOT,
        COND_MISSING_INDEX,
        COND_ADR_NO_FRONTMATTER,
        COND_VERSION_SHADOW,
    ):
        lines.append(f"  {condition}: {by_condition.get(condition, 0)}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anti_sprawl_ratchet",
        description=(
            "Report-only Common Docs anti-sprawl structure ratchet "
            f"(governed by {COMMON_DOCS_DIRECTIVE_ID})."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root containing the docs/ tree (default: this repo).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the structured JSON report instead of the human summary.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Wired-but-off: exit non-zero when violations exist. Mission B "
            "flips the default to blocking; here the ratchet is report-only."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root: Path = args.root.resolve()
    report = build_report(root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_render_human(report))
    if args.strict and report["baseline_count"] > 0:
        return 1
    return 0  # report-only (C-002): the default ruler never blocks.


if __name__ == "__main__":
    raise SystemExit(main())
