"""The anti-drift teeth over a **discovered** consumer set (WP02, T007, R1a).

Binding contract: ``kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/contracts/home-pin-scan-seam.md``,
§"Anti-drift mechanism (the teeth)". **The seam is not the import; it is the test that makes the
import the only option.**

This repository has the failure on record as a live incident, not as a hypothetical:
``tests/architectural/_sole_door_scan.py:13-27`` documents Gates 4 and 5 each rolling an
independent, drifting copy of the same primitives. Prose did not prevent it there.

Why the consumer set is DISCOVERED and never hard-coded
-------------------------------------------------------
A hard-coded list of consumer filenames greens the day a consumer is renamed — the guard then
enforces nothing while still reporting green. So the set is computed by AST at run time, and two
independent properties are asserted about it:

* it is **non-empty** (a matcher that sees nothing is indistinguishable from a matcher that
  passes), and
* it **contains** ``_home_pin_gate.py`` and this module itself — named members whose absence is a
  red rather than a silent hole.

WP03/WP04/WP05 modules are therefore covered **without editing this file**.

Why this module never calls ``ast.parse``
------------------------------------------
This module imports the seam, so it is a member of the very set it polices. Every parse routes
through :func:`_home_pin_scan.parse_module`; a positive control calling ``ast.parse`` directly
would red the guard it exists to serve, and the cheapest repair for that red is to exempt the
control — which reopens the seam. The contract states this explicitly because three separate
subtasks ship such controls.

Pre-filter, and why it is not the C-003 text search
----------------------------------------------------
File **selection** uses a raw-bytes containment test for ``b"_home_pin_scan"``. That is C-003
form (i): a pre-filter that over-selects by construction (any mention in any context, including a
comment or a string) and whose output is then decided **by AST**. No population this module
publishes is produced by text search.

What this cannot see
--------------------
A second copy of the predicate written **without importing ``_home_pin_scan`` at all**. That hole
is stated rather than papered over; closing it needs a similarity oracle, not an import graph.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from tests.architectural import _home_pin_scan as scan

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"

#: The seam's module name, and the bytes the (over-selecting) pre-filter looks for.
SEAM_MODULE = "_home_pin_scan"
SEAM_BYTES = SEAM_MODULE.encode("utf-8")
SEAM_PATH = Path(__file__).resolve().with_name(f"{SEAM_MODULE}.py")

#: Named members of the discovered set. Their **absence** is a red; the set itself is never
#: enumerated from these.
GATE_RELPATH = "architectural/_home_pin_gate.py"
GUARD_RELPATH = Path(__file__).resolve().relative_to(TESTS_ROOT).as_posix()

#: The banned constructs, by the attribute/class name they present at the AST.
PARSE_NAME = "parse"
#: ``NodeTransformer`` is a **subclass of** ``NodeVisitor``, so a class deriving from it *is* a
#: ``NodeVisitor`` subclass — the contract's words cover it, and matching only the literal
#: ``NodeVisitor`` would leave the one-word rename as an open hole.
VISITOR_NAMES = frozenset({"NodeVisitor", "NodeTransformer"})

#: ``subprocess`` and every git surface. The contract puts the whole window measurement in
#: ``_home_pin_gate.py`` precisely so this stays empty: collected tests import the seam under a
#: six-second budget on every PR (NFR-001).
GIT_SURFACES = frozenset({"subprocess", "git", "pygit2", "dulwich"})


def _materialise(root: Path, relpath: str, source: str) -> Path:
    """Write ``source`` (dedented) to ``root/relpath``, creating parents. Returns the path."""
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Discovery — the consumer set, by AST
# ---------------------------------------------------------------------------


def imports_seam(tree: ast.Module) -> bool:
    """``True`` when ``tree`` imports :mod:`_home_pin_scan` in any of its three spellings.

    ``import tests.architectural._home_pin_scan``,
    ``from tests.architectural import _home_pin_scan`` and
    ``from tests.architectural._home_pin_scan import discover`` all count — the guard is about the
    dependency, not about the spelling a consumer happened to pick.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(SEAM_MODULE in alias.name.split(".") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and SEAM_MODULE in node.module.split("."):
                return True
            if any(alias.name == SEAM_MODULE for alias in node.names):
                return True
    return False


def seam_consumers(root: Path) -> frozenset[str]:
    """POSIX relpaths, relative to ``root``, of every module importing the seam.

    Root-parameterised for the same reason :func:`_home_pin_scan.discover` is (FR-009): the
    positive controls run the **production discovery function** over a synthetic tree, never a
    second copy of it written for the test.
    """
    return frozenset(
        path.relative_to(root).as_posix()
        for path in scan.enumerate_py_files(root)
        if SEAM_BYTES in path.read_bytes() and imports_seam(scan.parse_module(path))
    )


# ---------------------------------------------------------------------------
# The banned-construct matchers
# ---------------------------------------------------------------------------


def _ast_aliases(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    """``(module aliases bound to ``ast``, names imported directly out of ``ast``)``.

    Resolving the binding is what keeps the matcher from firing on an unrelated ``parse(...)``
    from some other library, and from missing ``import ast as a`` / ``from ast import parse``.
    """
    modules: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.asname or alias.name for alias in node.names if alias.name == "ast"}
        elif isinstance(node, ast.ImportFrom) and node.module == "ast":
            names |= {alias.asname or alias.name for alias in node.names}
    return frozenset(modules), frozenset(names)


def banned_constructs(tree: ast.Module) -> frozenset[tuple[str, int]]:
    """``(construct, lineno)`` for every ``ast.parse`` call and ``NodeVisitor`` subclass.

    One matcher, run over the real consumer set (where it must return the empty set) and over a
    materialised module that **does** carry both constructs (where it must not). An empty-set
    assertion without that second run is its own proof — C-003 form (ii)'s named failure.
    """
    modules, names = _ast_aliases(tree)
    hits: set[tuple[str, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_ast_member(node.func, PARSE_NAME, modules, names):
            hits.add(("ast.parse", node.lineno))
        elif isinstance(node, ast.ClassDef):
            hits |= {
                ("ast.NodeVisitor", node.lineno)
                for base in node.bases
                if any(_is_ast_member(base, name, modules, names) for name in VISITOR_NAMES)
            }
    return frozenset(hits)


def _is_ast_member(
    node: ast.expr, member: str, modules: frozenset[str], names: frozenset[str]
) -> bool:
    """``True`` when ``node`` denotes ``ast.<member>`` under this module's own import bindings."""
    if isinstance(node, ast.Attribute):
        return node.attr == member and isinstance(node.value, ast.Name) and node.value.id in modules
    return isinstance(node, ast.Name) and node.id == member and node.id in names


def _offenders(root: Path, consumers: frozenset[str]) -> dict[str, list[tuple[str, int]]]:
    """``relpath -> sorted banned constructs`` for every consumer carrying at least one."""
    found: dict[str, list[tuple[str, int]]] = {}
    for relpath in sorted(consumers):
        hits = banned_constructs(scan.parse_module(root / relpath))
        if hits:
            found[relpath] = sorted(hits)
    return found


# ---------------------------------------------------------------------------
# Limb 1 — the discovered consumer set and the ban over it
# ---------------------------------------------------------------------------


def test_consumer_set_is_discovered_non_empty_and_names_the_gate() -> None:
    """The set is computed, not listed — and its two known members are present.

    ``_home_pin_gate.py`` is named because T006 authors it **before** this subtask: the previous
    revision put this guard in a package where its own named consumer did not yet exist, and it
    was red at its own completion.
    """
    consumers = seam_consumers(TESTS_ROOT)
    assert consumers, (
        "the seam consumer set is EMPTY — a hard-coded list would have greened here, which is "
        "why the set is discovered and its non-emptiness asserted separately"
    )
    missing = {GATE_RELPATH, GUARD_RELPATH} - consumers
    assert missing == set(), (
        f"named consumers absent from the discovered set: {sorted(missing)}; "
        f"discovered {sorted(consumers)}"
    )


def test_no_consumer_reimplements_the_predicate() -> None:
    """Every module importing the seam holds zero ``ast.parse`` calls and zero visitors."""
    consumers = seam_consumers(TESTS_ROOT)
    assert _offenders(TESTS_ROOT, consumers) == {}, (
        "a seam consumer carries a banned construct — route the parse through "
        "`_home_pin_scan.parse_module` rather than exempting the module"
    )


def test_banned_construct_matchers_bite_on_a_materialised_second_copy(tmp_path: Path) -> None:
    """The positive control: a module that DOES carry both constructs is discovered and reported.

    Without this run, ``_offenders(...) == {}`` above is indistinguishable from a matcher that
    matches nothing at all.
    """
    _materialise(
        tmp_path,
        "second_copy.py",
        '''
        import ast

        from tests.architectural._home_pin_scan import discover


        class Visitor(ast.NodeVisitor):
            """A second copy of the predicate, written the way drift actually arrives."""


        def scan_again(text: str) -> object:
            return ast.parse(text), discover
        ''',
    )
    _materialise(tmp_path, "innocent.py", "VALUE = 1\n")

    consumers = seam_consumers(tmp_path)
    assert consumers == frozenset({"second_copy.py"}), (
        "discovery must select exactly the importing module and leave the non-importer alone"
    )
    offenders = _offenders(tmp_path, consumers)
    assert set(offenders) == {"second_copy.py"}
    assert {construct for construct, _ in offenders["second_copy.py"]} == {
        "ast.parse",
        "ast.NodeVisitor",
    }


def test_matchers_do_not_fire_on_an_unrelated_parse(tmp_path: Path) -> None:
    """A ``parse`` from some other library is not ``ast.parse`` — the binding is resolved.

    A name-only matcher would report this file, and the cheapest repair for a false red is to
    weaken the matcher, which is how a guard stops biting.
    """
    _materialise(
        tmp_path,
        "other_parse.py",
        """
        from tests.architectural._home_pin_scan import parse_module
        from urllib.parse import urlparse as parse


        def go(text: str) -> object:
            return parse(text), parse_module
        """,
    )
    consumers = seam_consumers(tmp_path)
    assert consumers == frozenset({"other_parse.py"})
    assert _offenders(tmp_path, consumers) == {}


# ---------------------------------------------------------------------------
# Limb 2 — the seam module holds no subprocess and no git surface
# ---------------------------------------------------------------------------


def test_seam_module_holds_no_subprocess_and_no_git_surface() -> None:
    """``_home_pin_scan.py`` stays importable under a six-second budget on every PR.

    The whole window measurement — git-archive extraction, the walk, verdict emission — lives in
    ``_home_pin_gate.py``, which is a *consumer* and owns no predicate, so the no-second-copy
    property is preserved while ``subprocess`` stays out of the collected import path.
    """
    hits = scan.find_module_references(scan.parse_module(SEAM_PATH), names=GIT_SURFACES)
    assert {name for name, _ in hits} == set(), f"seam module reaches a barred surface: {hits}"


def test_git_surface_matcher_bites(tmp_path: Path) -> None:
    """The positive control for limb 2, over a module that DOES reach the barred surface."""
    path = _materialise(
        tmp_path,
        "with_surface.py",
        """
        import subprocess


        def run() -> object:
            return subprocess.run(["git", "archive"], check=True)
        """,
    )
    hits = scan.find_module_references(scan.parse_module(path), names=GIT_SURFACES)
    assert {name for name, _ in hits} == {"subprocess"}
