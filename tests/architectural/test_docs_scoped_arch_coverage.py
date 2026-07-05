"""Completeness guard: docs-scanning arch/adversarial tests carry ``docs_scoped``.

Convention (mission ci-topology-shrink — docs-only arch pole)
------------------------------------------------------------
The always-on ``arch-adversarial`` CI job (``.github/workflows/ci-quality.yml``)
trims to ``-m 'docs_scoped and not windows_ci'`` on a **docs-only** PR (every
changed path under ``docs/``) instead of running the full ~14-min suite. That
trim is only invariant-safe if EVERY arch/adversarial test whose result depends
on repo ``docs/`` content — i.e. a docs change could newly-red it — carries
``@pytest.mark.docs_scoped``. A docs-scanning test that forgets the marker would
be silently skipped on a docs-only PR, so the pole could go green while the full
suite would red: a false-green hole.

This guard closes that drift by construction (DIR-043):

* **(a) Pinned known scanners** — the four modules known to read real ``docs/``
  content are asserted to carry the module-level marker. If one loses the marker
  (or the arch pole's docs-only trim would stop selecting it) this reds.

* **(b) Best-effort static detector** — every ``.py`` under ``tests/architectural``
  and ``tests/adversarial`` is AST-scanned for a *docs-read signal*:
  a ``_SCAN_ROOTS``-style tuple/list literal containing ``"docs"`` (alongside
  ``"src"``/``"tests"``), or a repo-rooted ``... / "docs"`` :class:`pathlib.Path`
  division chain (``tmp_path``-rooted chains are excluded — those stage a
  fixture, they do not read the real tree). Any file with a signal MUST carry
  ``docs_scoped``. A NEW docs-scanning arch test that forgets the marker reds
  here.

The detector is deliberately conservative: it may over-flag (harmless — the
extra fast test just runs on the trim), but the pinned set (a) guarantees the
two canonical prose scanners are covered even if the heuristic misses a novel
scan idiom. Fault-injection tests below exercise both a positive
(SCAN_ROOTS / Path-``docs``) and a negative (``tmp_path`` / unrelated ``"docs"``
literal) so the detector's teeth are proven, not assumed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCAN_DIRS: tuple[Path, ...] = (
    _REPO_ROOT / "tests" / "architectural",
    _REPO_ROOT / "tests" / "adversarial",
)

# The docs marker's canonical name (single source: pytest.ini registry).
_DOCS_MARKER = "docs_scoped"

# Path-chain roots that denote a *fixture-staged* docs tree (not the real repo
# ``docs/``); a ``"docs"`` segment under one of these is NOT a docs-read signal.
_FIXTURE_ROOTS: frozenset[str] = frozenset({"tmp_path", "tmpdir", "tmp"})

# Sibling roots that, appearing beside ``"docs"`` in a tuple/list literal, mark it
# as a source-scan-root set (the ``_SCAN_ROOTS`` idiom) rather than an incidental
# literal (e.g. an extras-name set like ``{"dev", "docs"}``).
_SCAN_ROOT_SIBLINGS: frozenset[str] = frozenset({"src", "tests"})

# Known docs-content scanners (pinned so a heuristic miss can never silently
# drop the canonical prose scanners). Kept in sync with the marked modules.
_KNOWN_DOCS_SCANNERS: tuple[str, ...] = (
    "test_no_legacy_terminology.py",
    "test_docs_cli_reference_parity.py",
    "test_unregistered_shim_scanner.py",
    "test_shim_registry_schema.py",
)


# ---------------------------------------------------------------------------
# Pure detectors (unit-testable without touching the filesystem).
# ---------------------------------------------------------------------------


def _leftmost_name(node: ast.expr) -> str | None:
    """The base identifier of a left-associative ``a / b / c`` division chain."""
    while isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        node = node.left
    return node.id if isinstance(node, ast.Name) else None


def _is_docs_constant(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value == "docs"


def _has_scan_roots_docs(tree: ast.AST) -> bool:
    """A tuple/list literal holding ``"docs"`` alongside ``"src"``/``"tests"``.

    Catches the ``_SCAN_ROOTS = ("src", "tests", "docs")`` idiom while ignoring
    unrelated ``"docs"`` literals (e.g. an extras-name set that never pairs with
    a source root).
    """
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Tuple, ast.List)):
            continue
        literals = {
            elt.value
            for elt in node.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        }
        if "docs" in literals and literals & _SCAN_ROOT_SIBLINGS:
            return True
    return False


def _has_repo_docs_path(tree: ast.AST) -> bool:
    """A ``<root> / "docs"`` Path division whose root is not a tmp fixture.

    Catches ``_REPO_ROOT / "docs" / "reference" / ...`` (real-tree read) while
    excluding ``tmp_path / "docs" / ...`` (fixture staging).
    """
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            continue
        if not (_is_docs_constant(node.left) or _is_docs_constant(node.right)):
            continue
        base = _leftmost_name(node)
        if base is not None and base not in _FIXTURE_ROOTS:
            return True
    return False


def reads_repo_docs(source: str) -> bool:
    """True iff ``source`` statically reads real repo ``docs/`` content.

    Best-effort AST heuristic backing the drift guard: a source-scan-root tuple
    containing ``"docs"``, or a non-fixture repo-rooted ``.../docs`` Path chain.
    """
    tree = ast.parse(source)
    return _has_scan_roots_docs(tree) or _has_repo_docs_path(tree)


def module_marks_docs_scoped(source: str) -> bool:
    """True iff the module's ``pytestmark`` references ``pytest.mark.docs_scoped``.

    Robust to the list (``[architectural, docs_scoped]``) and single-marker
    forms: it inspects the top-level ``pytestmark`` assignment(s) for any
    ``.docs_scoped`` marker attribute, so a stray mention in a comment/docstring
    (absent from the AST) never counts.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
        ):
            continue
        for sub in ast.walk(node.value):
            if isinstance(sub, ast.Attribute) and sub.attr == _DOCS_MARKER:
                return True
    return False


# ---------------------------------------------------------------------------
# Live guards over the real tree.
# ---------------------------------------------------------------------------


def _iter_test_files() -> list[Path]:
    files: list[Path] = []
    for root in _SCAN_DIRS:
        if not root.is_dir():
            continue
        files.extend(
            p
            for p in sorted(root.rglob("test_*.py"))
            if "__pycache__" not in p.parts
        )
    return files


def test_known_docs_scanners_are_docs_scoped() -> None:
    """(a) Every pinned known docs-content scanner carries the module marker."""
    missing: list[str] = []
    for name in _KNOWN_DOCS_SCANNERS:
        path = _REPO_ROOT / "tests" / "architectural" / name
        assert path.is_file(), (
            f"pinned docs scanner {name!r} moved/renamed — update "
            "_KNOWN_DOCS_SCANNERS so the arch pole's docs-only trim still runs it"
        )
        if not module_marks_docs_scoped(path.read_text(encoding="utf-8")):
            missing.append(name)
    assert not missing, (
        "known docs-content scanners missing @pytest.mark.docs_scoped (the "
        "arch-adversarial docs-only trim would silently skip them): "
        f"{missing}"
    )


def test_every_docs_reading_arch_test_is_docs_scoped() -> None:
    """(b) Best-effort: any docs-reading arch/adversarial test carries the marker.

    A NEW test that scans real ``docs/`` content but forgets ``docs_scoped``
    reds here — closing the false-green hole by construction (DIR-043). See the
    module docstring for the marking convention.
    """
    unmarked: list[str] = []
    for path in _iter_test_files():
        if path.name == Path(__file__).name:
            continue
        source = path.read_text(encoding="utf-8")
        if reads_repo_docs(source) and not module_marks_docs_scoped(source):
            unmarked.append(str(path.relative_to(_REPO_ROOT)))
    assert not unmarked, (
        "these arch/adversarial tests statically read repo docs/ content but do "
        "not carry @pytest.mark.docs_scoped, so the arch-adversarial docs-only "
        "trim (`-m 'docs_scoped and not windows_ci'`) would silently skip them "
        "on a docs-only PR — a false-green hole. Add the marker (module-level "
        "pytestmark):\n  " + "\n  ".join(unmarked)
    )


# ---------------------------------------------------------------------------
# MANDATORY fault-injection — the detector's teeth are proven, not assumed.
# ---------------------------------------------------------------------------


def test_detector_flags_scan_roots_docs() -> None:
    assert reads_repo_docs('_SCAN_ROOTS = ("src", "tests", "docs")') is True


def test_detector_flags_repo_rooted_docs_path() -> None:
    assert reads_repo_docs('P = _REPO_ROOT / "docs" / "reference" / "x.md"') is True


def test_detector_ignores_tmp_path_docs() -> None:
    assert reads_repo_docs('(tmp_path / "docs" / "context").mkdir()') is False


def test_detector_ignores_unrelated_docs_literal() -> None:
    # An extras-name set (no source-root sibling) and a bare string are NOT
    # docs-read signals.
    assert reads_repo_docs('_GROUPS = frozenset({"dev", "lint", "docs"})') is False
    assert reads_repo_docs('assert "docs" not in refs') is False


def test_marker_detector_reads_list_and_single_forms() -> None:
    assert module_marks_docs_scoped(
        "pytestmark = [pytest.mark.architectural, pytest.mark.docs_scoped]"
    )
    assert module_marks_docs_scoped("pytestmark = pytest.mark.docs_scoped")
    assert not module_marks_docs_scoped("pytestmark = pytest.mark.architectural")
    # A comment mention must not count (AST-only).
    assert not module_marks_docs_scoped(
        "pytestmark = pytest.mark.architectural  # not docs_scoped here"
    )
