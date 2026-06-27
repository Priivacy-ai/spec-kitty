"""Self-tests for the Common Docs anti-sprawl ratchet (Mission A WP05).

Four injection fixtures (one per detector) each assert the seeded sprawl
regression is detected and reds under ``--strict``; a clean fixture passes; the
floor is asserted to be the concrete enumerated 13-section list (never empty).

The squad-hardened binding test asserts that
:data:`COMMON_DOCS_DIRECTIVE_ID` **resolves to a loaded directive node** in
``src/doctrine/graph.yaml`` — not merely that the string appears in a message.
A typo or placeholder id must fail that test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ``conftest.py`` puts the repo root on sys.path so ``scripts.docs`` imports.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# The script anchors ``<repo>/src`` itself, but pre-seed it so the shared
# directive constant resolves to *this* tree even in a parallel lane worktree.
_SRC_DIR = _REPO_ROOT / "src"
if _SRC_DIR.is_dir() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from scripts.docs import anti_sprawl_ratchet as ratchet  # noqa: E402

pytestmark = pytest.mark.architectural


# ---------------------------------------------------------------------------
# Clean-tree builder: a minimal, Common-Docs-correct tree (zero violations).
# ---------------------------------------------------------------------------
_GOOD_ADR = (
    "---\n"
    "title: Example Decision\n"
    "status: Accepted\n"
    "date: 2026-06-27\n"
    "---\n\n"
    "# Example Decision\n\nBody.\n"
)


def _write(path: Path, text: str = "# stub\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_clean_tree(root: Path) -> Path:
    """Materialise a clean single-root 13-section Common Docs tree."""
    docs = root / "docs"
    _write(docs / "index.md")
    for section in ratchet.CANONICAL_SECTIONS:
        if section == "index":
            continue
        _write(docs / section / "index.md")
    # A correctly frontmattered ADR under adr/<era>/ keeps detector 3 quiet.
    _write(docs / "adr" / "3.x" / "2026-06-27-1-example.md", _GOOD_ADR)
    return root


@pytest.fixture()
def clean_root(tmp_path: Path) -> Path:
    return _build_clean_tree(tmp_path / "repo")


# ---------------------------------------------------------------------------
# Clean fixture: zero violations, report-only AND --strict both exit 0.
# ---------------------------------------------------------------------------
def test_clean_tree_has_no_violations(clean_root: Path) -> None:
    assert ratchet.collect_violations(clean_root) == []


def test_clean_tree_passes_under_strict(clean_root: Path) -> None:
    assert ratchet.main(["--root", str(clean_root), "--strict"]) == 0


# ---------------------------------------------------------------------------
# Four injection self-tests — one per condition. Each asserts detection AND a
# red under --strict, while the report-only default still exits 0.
# ---------------------------------------------------------------------------
def _conditions(violations: list[ratchet.Violation]) -> set[str]:
    return {v.condition for v in violations}


def test_injection_second_doc_root(clean_root: Path) -> None:
    _write(clean_root / "handbook" / "index.md")  # competing root marker
    violations = ratchet.collect_violations(clean_root)
    assert ratchet.COND_SECOND_ROOT in _conditions(violations)
    assert any(
        v.condition == ratchet.COND_SECOND_ROOT and v.path == "handbook"
        for v in violations
    )
    assert ratchet.main(["--root", str(clean_root), "--strict"]) == 1
    assert ratchet.main(["--root", str(clean_root)]) == 0  # report-only


def test_injection_section_missing_index(clean_root: Path) -> None:
    (clean_root / "docs" / "orphaned").mkdir()  # section dir, no index.md
    violations = ratchet.collect_violations(clean_root)
    assert ratchet.COND_MISSING_INDEX in _conditions(violations)
    assert any(
        v.condition == ratchet.COND_MISSING_INDEX and v.path == "docs/orphaned"
        for v in violations
    )
    assert ratchet.main(["--root", str(clean_root), "--strict"]) == 1
    assert ratchet.main(["--root", str(clean_root)]) == 0


def test_injection_adr_missing_frontmatter(clean_root: Path) -> None:
    _write(clean_root / "docs" / "adr" / "3.x" / "bad.md", "# No frontmatter ADR\n")
    violations = ratchet.collect_violations(clean_root)
    assert ratchet.COND_ADR_NO_FRONTMATTER in _conditions(violations)
    assert any(
        v.condition == ratchet.COND_ADR_NO_FRONTMATTER
        and v.path == "docs/adr/3.x/bad.md"
        for v in violations
    )
    assert ratchet.main(["--root", str(clean_root), "--strict"]) == 1
    assert ratchet.main(["--root", str(clean_root)]) == 0


def test_injection_version_shadow_tree(clean_root: Path) -> None:
    _write(clean_root / "docs" / "2x" / "index.md")  # shadow tree re-introduced
    violations = ratchet.collect_violations(clean_root)
    assert ratchet.COND_VERSION_SHADOW in _conditions(violations)
    assert any(
        v.condition == ratchet.COND_VERSION_SHADOW and v.path == "docs/2x"
        for v in violations
    )
    assert ratchet.main(["--root", str(clean_root), "--strict"]) == 1
    assert ratchet.main(["--root", str(clean_root)]) == 0


# ---------------------------------------------------------------------------
# Concrete content-anchored floor (T022): the real enumerated 13-section list.
# ---------------------------------------------------------------------------
_EXPECTED_SECTIONS = [
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
]


def test_floor_is_the_enumerated_thirteen_sections() -> None:
    floor = ratchet.floor_baseline()
    assert floor["sections"] == _EXPECTED_SECTIONS
    assert len(floor["sections"]) == 13
    assert floor["sections"]  # never empty — would pass everything otherwise
    assert floor["doc_roots"] == 1


def test_report_carries_directive_ref_and_floor(clean_root: Path) -> None:
    report = ratchet.build_report(clean_root)
    assert report["directive_ref"] == ratchet.COMMON_DOCS_DIRECTIVE_ID
    assert report["floor"]["sections"] == _EXPECTED_SECTIONS
    assert report["baseline_count"] == 0


# ---------------------------------------------------------------------------
# CRITICAL binding self-test (C-003): the constant must resolve to a LOADED
# directive node in graph.yaml — not merely appear as a string.
# ---------------------------------------------------------------------------
def test_directive_constant_resolves_to_loaded_node() -> None:
    assert ratchet.COMMON_DOCS_DIRECTIVE_ID  # non-empty
    assert ratchet.directive_node_present(
        ratchet.COMMON_DOCS_DIRECTIVE_ID, root=_REPO_ROOT
    ), (
        f"directive:{ratchet.COMMON_DOCS_DIRECTIVE_ID} must resolve to a loaded "
        "node in src/doctrine/graph.yaml"
    )


def test_bogus_directive_id_does_not_resolve() -> None:
    assert not ratchet.directive_node_present(
        "DIRECTIVE_999_DOES_NOT_EXIST", root=_REPO_ROOT
    )


def test_directive_ref_in_report_is_the_resolvable_constant(clean_root: Path) -> None:
    """The id printed in the report is the SAME id that resolves in graph.yaml."""
    report = ratchet.build_report(clean_root)
    assert ratchet.directive_node_present(report["directive_ref"], root=_REPO_ROOT)
