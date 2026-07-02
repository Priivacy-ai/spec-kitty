"""Architectural convention: every test file MUST declare a pytest marker.

Rationale
---------
This project's CI quality gates and developer-loop test profiles
(``uv run pytest -m fast``, ``uv run pytest -m "not slow"``,
``uv run pytest -m architectural``, ``uv run pytest -m contract``, etc.)
are **marker-based**. A test file with no marker is invisible to those
profiles: it either runs in every profile (wasteful for slow tests) or
falls through every filter (silent gap in CI coverage).

This convention pins the rule:

    Every ``test_*.py`` file under ``tests/`` that defines test
    functions or test classes MUST declare a module-level
    ``pytestmark`` assignment carrying at least one
    ``pytest.mark.<name>`` entry. The marker propagates to every
    test in the file (pytest's built-in inheritance), so the rule
    is satisfied per-file rather than per-test.

Human-exploratory carve-out
---------------------------
Tests intended only for human-driven exploration (not CI) satisfy this
convention by declaring an explicit ``pytestmark = [pytest.mark.exploratory]``
(or equivalent), and CI workflows opt them out via
``-m "not exploratory"``. The rule is presence of *some* marker, not
membership of a specific allow-list — the failure mode this convention
prevents is the silent "no category" gap.

Allowed exemptions
------------------
- ``conftest.py`` (pytest fixture / hook module, not collected as tests).
- ``__init__.py`` (package marker).
- This file itself (cycle).
- Files that define no test functions or test classes (support modules
  living next to tests; pytest collects them as files but produces zero
  test items).

Failure mode
------------
On violation the assertion message lists every offending file relative
to the repo root, plus a hint pointing at how to fix it (add a module-
level ``pytestmark`` line near the top imports).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]


_TESTS_ROOT = Path(__file__).resolve().parents[1]
_SELF = Path(__file__).resolve()


def _iter_candidate_test_files() -> list[Path]:
    """Return every ``test_*.py`` file under ``tests/`` except known exemptions.

    Exemptions:
    - this checker file itself;
    - hidden / cache dirs (``.pytest_cache``, ``__pycache__``);
    - anything under a ``_support`` directory — the test-support/helper tree
      (leading underscore = not a normal collected suite; these modules are
      shared fixtures/utilities, not CI-profiled test suites), so they are not
      required to carry a marker.
    """
    paths: list[Path] = []
    for path in _TESTS_ROOT.rglob("test_*.py"):
        if path.resolve() == _SELF:
            continue
        # Only the parts *below* the tests root matter — the absolute prefix may
        # legitimately contain dot-dirs (e.g. a ``.worktrees/`` checkout), which
        # must NOT exempt every file and blind the gate. Skip files inside
        # __pycache__/.pytest_cache and similar under tests/.
        rel_parts = path.relative_to(_TESTS_ROOT).parts
        if any(part.startswith((".", "__")) for part in rel_parts):
            continue
        # Skip the test-support/helper tree (tests/_support/**).
        if "_support" in rel_parts:
            continue
        paths.append(path)
    return sorted(paths)


def _module_has_pytestmark(tree: ast.Module) -> bool:
    """Return True iff the module declares a non-empty ``pytestmark`` at top level.

    Accepts both forms:

        pytestmark = [pytest.mark.foo]                # list form (common)
        pytestmark = [pytest.mark.foo, pytest.mark.bar]
        pytestmark = pytest.mark.foo                  # singleton form (legal)

    Rejects:

        pytestmark = []                               # empty list
        pytestmark = None                             # no marker
    """
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not (isinstance(target, ast.Name) and target.id == "pytestmark"):
                continue
            value = node.value
            if isinstance(value, ast.List):
                return len(value.elts) > 0
            if isinstance(value, ast.Tuple):
                return len(value.elts) > 0
            # Singleton form (e.g. `pytestmark = pytest.mark.foo`).
            # Treat any non-None, non-empty-container expression as valid.
            return not (isinstance(value, ast.Constant) and value.value is None)
    return False


def _module_defines_tests(tree: ast.Module) -> bool:
    """Return True iff the module defines at least one ``test_*`` function or ``Test*`` class.

    Helper modules under ``tests/`` (e.g. ``tests/lane_test_utils.py``)
    don't define collected tests; they should not need a marker.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            return True
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("test_"):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            return True
    return False


def _format_violation_hint(repo_root: Path, violators: list[Path]) -> str:
    rel = [str(p.relative_to(repo_root)) for p in violators]
    bullet_list = "\n  - ".join(rel)
    return (
        "Pytest marker convention violation. The following test files declare\n"
        "test functions or test classes but do NOT carry a module-level\n"
        "`pytestmark = [pytest.mark.<name>]` assignment, which makes them\n"
        "invisible to this project's marker-based CI profiles\n"
        "(`uv run pytest -m fast`, `-m architectural`, `-m contract`, ...):\n"
        f"  - {bullet_list}\n"
        "\n"
        "Fix: add a module-level `pytestmark` near the imports, e.g.:\n"
        "    import pytest\n"
        "    pytestmark = [pytest.mark.architectural]\n"
        "\n"
        "Available markers are declared in pytest.ini under `[pytest] markers`.\n"
        "For human-exploratory tests that should NOT run in CI, declare\n"
        "`pytestmark = [pytest.mark.exploratory]` and rely on the CI workflow\n"
        "to opt out with `-m \"not exploratory\"`."
    )


def test_every_test_file_declares_a_pytestmark_marker() -> None:
    """Every ``test_*.py`` that defines tests MUST declare a module-level pytestmark."""
    repo_root = _TESTS_ROOT.parent
    violators: list[Path] = []

    for path in _iter_candidate_test_files():
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            # Unreadable file — flag as a violation so it surfaces in CI.
            violators.append(path)
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            # Syntax errors fail their own collection elsewhere; don't double-report.
            continue
        if not _module_defines_tests(tree):
            continue
        if not _module_has_pytestmark(tree):
            violators.append(path)

    assert not violators, _format_violation_hint(repo_root, violators)


def test_support_helper_tree_is_exempt_from_marker_convention() -> None:
    """``tests/_support/**`` (the helper tree) is excluded from the candidate set.

    Support modules are shared fixtures/utilities (and meta-tests of those
    utilities), not CI-profiled suites, so they are not required to carry a
    marker. Guards the ``"_support" in path.parts`` exemption.
    """
    candidates = _iter_candidate_test_files()
    assert candidates, "expected the checker to find at least one candidate file"
    assert not any("_support" in p.parts for p in candidates), (
        "tests/_support/** must be exempt from the marker convention; found: "
        + ", ".join(str(p) for p in candidates if "_support" in p.parts)
    )
