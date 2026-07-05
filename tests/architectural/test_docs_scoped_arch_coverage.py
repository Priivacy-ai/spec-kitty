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

* **(b) Best-effort static detector** — every ``.py`` under the pole's live
  ``matrix.paths`` roots (derived from the workflow, today ``tests/adversarial``,
  ``tests/architectural``, ``tests/architecture`` (singular), ``tests/lint``) is
  AST-scanned for a *docs-read signal*:
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
import yaml

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]

# The docs marker's canonical name (single source: pytest.ini registry).
_DOCS_MARKER = "docs_scoped"

# The pole whose docs-only trim this guard protects, and the workflow that owns
# it. ``_SCAN_DIRS`` is DERIVED from the pole's ``matrix.paths`` (not hardcoded)
# so the guard can never again go blind to a root the pole actually runs.
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"
_ARCH_POLE_JOB = "arch-adversarial"


def _pole_matrix_path_roots() -> tuple[Path, ...]:
    """The ``arch-adversarial`` pole's ``matrix.paths`` roots, as repo paths.

    Parsed live from ``ci-quality.yml`` so the scan set the guard walks is
    exactly the set of directories the pole selects tests from (today
    ``tests/adversarial tests/architectural tests/architecture tests/lint``). A
    root added to / removed from the pole flows through here automatically, and
    :func:`test_scan_dirs_equal_pole_matrix_paths` reds if the two ever diverge.

    Mission ci-health-charter-path-and-arch-shard-01KWRTB2 (#2397) split the
    pole into a 3-shard matrix (``arch_shard_1/2/3``) with ``paths`` kept
    IDENTICAL across every leg by construction — the ``arch_shard_N`` pytest
    marker, not ``paths``, does the partitioning (see T008). This no longer
    hardcodes a single shard label (the old ``architectural`` name is retired);
    it reads the first matrix leg's ``paths`` as representative, and
    :func:`test_scan_dirs_equal_pole_matrix_paths` additionally asserts every
    leg's ``paths`` is identical, so a future leg that drifts from the others
    reds here instead of silently narrowing/widening the guard's scan set.
    """
    data = yaml.safe_load(_CI_WORKFLOW.read_text(encoding="utf-8"))
    job = data["jobs"][_ARCH_POLE_JOB]
    include = job["strategy"]["matrix"]["include"]
    if not include:
        raise ValueError(f"{_ARCH_POLE_JOB!r} matrix has no legs to derive scan roots from")
    return tuple(_REPO_ROOT / token for token in str(include[0]["paths"]).split())


_SCAN_DIRS: tuple[Path, ...] = _pole_matrix_path_roots()

# Path-chain roots that denote a *fixture-staged* docs tree (not the real repo
# ``docs/``); a ``"docs"`` segment under one of these is NOT a docs-read signal.
_FIXTURE_ROOTS: frozenset[str] = frozenset({"tmp_path", "tmpdir", "tmp"})

# Sibling roots that, appearing beside ``"docs"`` in a tuple/list literal, mark it
# as a source-scan-root set (the ``_SCAN_ROOTS`` idiom) rather than an incidental
# literal (e.g. an extras-name set like ``{"dev", "docs"}``).
_SCAN_ROOT_SIBLINGS: frozenset[str] = frozenset({"src", "tests"})

# Known docs-content scanners (pinned so a heuristic miss can never silently
# drop the canonical prose scanners). Repo-relative paths — these span more than
# one pole root (``tests/architectural`` AND ``tests/architecture`` singular).
_KNOWN_DOCS_SCANNERS: tuple[str, ...] = (
    "tests/architectural/test_no_legacy_terminology.py",
    "tests/architectural/test_docs_cli_reference_parity.py",
    "tests/architectural/test_unregistered_shim_scanner.py",
    "tests/architectural/test_shim_registry_schema.py",
    "tests/architecture/test_ownership_manifest_schema.py",
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

    Catches both ``_REPO_ROOT / "docs" / "reference" / ...`` (Name root) and
    ``Path(__file__).parents[2] / "docs" / ...`` (non-Name root — an expression
    with no leading identifier) — real-tree reads. Excludes only
    ``tmp_path / "docs" / ...`` (fixture staging): a chain whose leftmost
    identifier is a known tmp fixture. A non-Name root (``_leftmost_name`` ->
    ``None``) is NOT a fixture root, so it is flagged (the ownership-manifest
    scanner's ``Path(__file__).parents[2]`` idiom).
    """
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            continue
        if not (_is_docs_constant(node.left) or _is_docs_constant(node.right)):
            continue
        if _leftmost_name(node) not in _FIXTURE_ROOTS:
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


def test_scan_dirs_equal_pole_matrix_paths() -> None:
    """The guard's scan set EQUALS the pole's live ``matrix.paths`` roots.

    Closes the drift class that this guard was rejected for: if the guard walked
    fewer roots than the pole runs, a docs-scanning test under an unwatched root
    could go unmarked and be silently trimmed away. Deriving ``_SCAN_DIRS`` from
    the pole plus this equality assertion means adding/removing a pole root reds
    here instead of silently narrowing the guard's coverage.
    """
    scan = {p.relative_to(_REPO_ROOT).as_posix() for p in _SCAN_DIRS}
    pole = {p.relative_to(_REPO_ROOT).as_posix() for p in _pole_matrix_path_roots()}
    assert scan == pole, (
        f"guard scan roots {sorted(scan)} != pole matrix.paths {sorted(pole)} — "
        "the guard would be blind to a root the pole actually runs"
    )
    # And every pole root must exist on disk (a typo'd root would silently drop).
    for root in _SCAN_DIRS:
        assert root.is_dir(), f"pole matrix.paths root {root} is not a directory"


def test_all_arch_shard_legs_share_identical_paths() -> None:
    """Every ``arch-adversarial`` matrix leg's ``paths`` must be identical.

    ``_pole_matrix_path_roots()`` reads only the FIRST matrix leg's ``paths``
    as representative of the whole pole (mission
    ci-health-charter-path-and-arch-shard-01KWRTB2 / #2397 — the
    ``arch_shard_N`` marker, not ``paths``, does the partitioning across the 3
    legs). If a future edit ever narrows one leg's ``paths`` while leaving the
    others untouched, this guard's scan set would silently diverge from what a
    specific shard actually runs — this reds that drift immediately instead of
    relying on the representative-leg assumption silently.
    """
    data = yaml.safe_load(_CI_WORKFLOW.read_text(encoding="utf-8"))
    include = data["jobs"][_ARCH_POLE_JOB]["strategy"]["matrix"]["include"]
    assert include, f"{_ARCH_POLE_JOB!r} matrix has no legs"
    path_sets = {frozenset(str(entry["paths"]).split()) for entry in include}
    assert len(path_sets) == 1, (
        "arch-adversarial matrix legs have diverging 'paths' "
        f"({path_sets}) — the representative-leg assumption in "
        "_pole_matrix_path_roots() no longer holds"
    )


def test_known_docs_scanners_are_docs_scoped() -> None:
    """(a) Every pinned known docs-content scanner carries the module marker."""
    missing: list[str] = []
    for relpath in _KNOWN_DOCS_SCANNERS:
        path = _REPO_ROOT / relpath
        assert path.is_file(), (
            f"pinned docs scanner {relpath!r} moved/renamed — update "
            "_KNOWN_DOCS_SCANNERS so the arch pole's docs-only trim still runs it"
        )
        if not module_marks_docs_scoped(path.read_text(encoding="utf-8")):
            missing.append(relpath)
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


def test_detector_flags_dunder_file_rooted_docs_path() -> None:
    # The ownership-manifest scanner's idiom: a non-Name root (Path(__file__)…).
    assert reads_repo_docs(
        'M = Path(__file__).parents[2] / "docs" / "architecture" / "x.yaml"'
    ) is True


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
