"""Limb tests for the shared ``SPEC_KITTY_HOME`` scanning seam (WP01, R1a).

Every population in this module is an **AST set**, never a text search (C-003), and every
synthetic source is materialised into ``tmp_path`` at test time — **no synthetic tree is checked
in** (FR-009), because a checked-in tree would sit inside the classifier's own walk.

**This module never calls ``ast.parse`` and never subclasses ``ast.NodeVisitor``.** Every parse
routes through :func:`_home_pin_scan.parse_module`; a control that parsed directly would red the
anti-drift guard it exists to serve (contract §"Anti-drift mechanism").
"""

from __future__ import annotations

import hashlib
import importlib
import re
import shlex
import textwrap
from pathlib import Path
from typing import get_args, get_origin

import pytest
import yaml

from tests.architectural import _home_pin_scan as scan

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"

NEEDLE = scan.NEEDLE  # never rebind the literal here: SC-002b's population is 0 and stays 0


def _materialise(root: Path, relpath: str, source: str) -> Path:
    """Write ``source`` (dedented) to ``root/relpath``, creating parents. Returns the path."""
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


def _lineno_of(path: Path, fragment: str) -> int:
    """The 1-based line carrying ``fragment``, asserted UNIQUE.

    Line numbers in this module are always *derived from content at run time*, never written as
    int literals: ``test_ratchet_positional_anchor_ban.py`` bans an int literal reaching
    ``composite_key_from_file(path, N)``'s second positional argument, and content-derived
    linenos are what the whole key design is for. The uniqueness assertion doubles as a positive
    control that the fragment naming the site is not silently matching nothing.
    """
    source = path.read_text(encoding="utf-8")
    matches = [n for n, line in enumerate(source.splitlines(), start=1) if fragment in line]
    assert len(matches) == 1, f"{fragment!r} must name exactly one line, matched {matches}"
    return matches[0]


# ---------------------------------------------------------------------------
# T001 — the walk, the byte pre-filter, the parser that raises, the vocabulary
# ---------------------------------------------------------------------------


def test_module_exports_the_shared_vocabulary() -> None:
    """`MemberKey`, `Member`, `Exempt` and `INERT_LIMBS` are the seam three packages bind to."""
    assert get_origin(scan.MemberKey) is tuple
    assert get_args(scan.MemberKey) == (str, str, str)
    assert isinstance(scan.Exempt, type)
    assert isinstance(scan.Member, type)
    assert isinstance(scan.INERT_LIMBS, frozenset)
    assert scan.INERT_LIMBS, "the inert sub-form registry may never be empty"


def test_enumerate_py_files_equals_an_inline_rglob_over_the_real_tree() -> None:
    """SC-007: set equality against an rglob written INLINE here, never taken from the module."""
    expected = set(Path(TESTS_ROOT).rglob("*.py"))
    actual = set(scan.enumerate_py_files(TESTS_ROOT))
    assert actual == expected
    # C-002 / SC-007: the count is REPORTED, never asserted.
    print(f"[reported, not asserted] .py files under tests/: {len(expected)}")


def test_enumerate_py_files_is_never_narrowed_under_a_materialised_root(tmp_path: Path) -> None:
    """FR-009's root parameter over a tree whose every shape a narrowed walk would drop."""
    underscored = _materialise(tmp_path, "_private/hidden_module.py", "X = 1\n")
    conftest = _materialise(tmp_path, "conftest.py", "import pytest\n")
    _materialise(tmp_path, "pkg/__init__.py", "")
    nested = _materialise(tmp_path, "pkg/nested/deep_module.py", "Y = 2\n")
    _materialise(tmp_path, "notes.txt", "not python at all\n")

    expected = set(Path(tmp_path).rglob("*.py"))
    # Positive control on the fixture itself: the shapes a narrowed walk drops are really here.
    assert {underscored, conftest, nested} <= expected
    assert set(scan.enumerate_py_files(tmp_path)) == expected
    print(f"[reported, not asserted] .py files under the materialised root: {len(expected)}")


def test_byte_prefilter_returns_exactly_the_needle_files(tmp_path: Path) -> None:
    """FR-002: mandatory, and asserted by SET EQUALITY naming both the included and the excluded."""
    hits = {
        _materialise(tmp_path, "hit_setenv.py", f'M.setenv("{NEEDLE}", "/x")\n'),
        _materialise(tmp_path, "hit_comment.py", f"# mentions {NEEDLE} in a comment only\n"),
        _materialise(tmp_path, "hit_docstring.py", f'"""{NEEDLE} in a docstring."""\n'),
    }
    misses = {
        _materialise(tmp_path, "miss_other_key.py", 'M.setenv("SPEC_KITTY_ROOT", "/x")\n'),
        _materialise(tmp_path, "miss_home.py", 'M.setenv("HOME", "/x")\n'),
        _materialise(tmp_path, "miss_empty.py", ""),
    }
    assert misses, "the excluded arm must be non-empty or the set equality is vacuous"

    selected = set(scan.byte_prefilter(sorted(hits | misses)))
    assert selected == hits


def test_parse_module_propagates_syntax_error(tmp_path: Path) -> None:
    """SC-013: `except SyntaxError: continue` is NFR-001's defeat wearing an exception handler."""
    broken = _materialise(tmp_path, "broken.py", "def f(:\n    pass\n")
    with pytest.raises(SyntaxError):
        scan.parse_module(broken)


def test_scan_module_declares_no_except_syntaxerror_handler(tmp_path: Path) -> None:
    """SC-013, asserted over the module's own source — with a control proving the matcher bites."""
    own = scan.parse_module(Path(scan.__file__))
    assert scan.find_except_handlers(own, exception="SyntaxError") == set()

    control_path = _materialise(
        tmp_path,
        "control_except_syntaxerror.py",
        """
        import ast


        def parse(source):
            try:
                return ast.parse(source)
            except SyntaxError:  # the-shape
                return None
        """,
    )
    control_hits = scan.find_except_handlers(
        scan.parse_module(control_path), exception="SyntaxError"
    )
    assert control_hits == {_lineno_of(control_path, "# the-shape")}, (
        "a control returning set() proves nothing"
    )


def test_scan_module_carries_no_subprocess_and_no_git_surface(tmp_path: Path) -> None:
    """Contract §"The gate driver is NOT in this module" — with a control per banned module."""
    banned = frozenset({"subprocess", "git", "pygit2", "sh"})
    own = scan.parse_module(Path(scan.__file__))
    assert scan.find_module_references(own, names=banned) == set()

    control = scan.parse_module(
        _materialise(
            tmp_path,
            "control_subprocess.py",
            """
            import subprocess


            def run():
                return subprocess.run(["git", "status"], check=False)
            """,
        )
    )
    control_hits = scan.find_module_references(control, names=banned)
    assert {name for name, _ in control_hits} == {"subprocess"}


# ---------------------------------------------------------------------------
# T002 — the receiver-agnostic, key-parameterised write-site finder
# ---------------------------------------------------------------------------

_ALL_WRITE_FORMS = """
import os
from os import environ

import pytest


@pytest.fixture
def every_write_form(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # attribute-receiver setenv
    setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # BARE-NAME setenv, no receiver at all
    os.environ["SPEC_KITTY_HOME"] = str(tmp_path / "home")  # dotted environ assignment
    environ["SPEC_KITTY_HOME"] = str(tmp_path / "home")  # bare environ assignment
    os.environ.setdefault("SPEC_KITTY_HOME", str(tmp_path / "home"))  # setdefault
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # withitem-bound receiver
"""


def test_find_write_sites_is_receiver_agnostic_over_every_write_form(tmp_path: Path) -> None:
    """The discriminator is receiver-agnosticism ON THE CALL — the bare-name case catches it.

    A receiver-*qualified* matcher is what drops `:1165` and biases `r` toward *proceed*.
    """
    path = _materialise(tmp_path, "mod_every_write_form.py", _ALL_WRITE_FORMS)
    expected = {
        (_lineno_of(path, "# attribute-receiver setenv"), "setenv"),
        (_lineno_of(path, "# BARE-NAME setenv"), "setenv"),
        (_lineno_of(path, "# dotted environ assignment"), "environ-assign"),
        (_lineno_of(path, "# bare environ assignment"), "environ-assign"),
        (_lineno_of(path, "# setdefault"), "setdefault"),
        (_lineno_of(path, "# withitem-bound receiver"), "setenv"),
    }
    tree = scan.parse_module(path)
    found = {(site.lineno, site.form) for site in scan.find_write_sites(tree, key=NEEDLE)}
    assert found == expected


_BOTH_KEYS = """
import os

import pytest


@pytest.fixture
def writes_both(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # skh setenv
    monkeypatch.setenv("HOME", str(tmp_path / "home"))  # home setenv
    os.environ["HOME"] = str(tmp_path / "user-home")  # home environ
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))  # unrelated key
"""


def test_find_write_sites_is_one_implementation_parameterised_by_key(tmp_path: Path) -> None:
    """One implementation, two keys, PROVEN BY THE SECOND CALL — never a second finder."""
    path = _materialise(tmp_path, "mod_both_keys.py", _BOTH_KEYS)
    tree = scan.parse_module(path)

    skh_expected = {(_lineno_of(path, "# skh setenv"), "setenv")}
    home_expected = {
        (_lineno_of(path, "# home setenv"), "setenv"),
        (_lineno_of(path, "# home environ"), "environ-assign"),
    }
    assert {(s.lineno, s.form) for s in scan.find_write_sites(tree, key=NEEDLE)} == skh_expected
    assert {(s.lineno, s.form) for s in scan.find_write_sites(tree, key="HOME")} == home_expected


_EIGHT_VALUE_FORMS = '''
import os
from pathlib import Path


def probe(tmp_path, monkeypatch, dynamic_key):
    v_str = str(tmp_path / "home")
    v_path = Path(tmp_path, "home")
    v_fspath = os.fspath(tmp_path / "home")
    v_joinpath = tmp_path.joinpath("home")
    v_fstring = f"{tmp_path}/home"
    v_ospathjoin = os.path.join(str(tmp_path), "home")
    v_percent = "%s/home" % str(tmp_path)
    v_format = "{}/home".format(str(tmp_path))
    v_concat = str(tmp_path) + "/home"
    v_name_keyed = dynamic_key
    v_dynamic = compute_home_somehow()
'''


@pytest.mark.parametrize(
    "binding",
    [
        "v_str",
        "v_path",
        "v_fspath",
        "v_joinpath",
        "v_fstring",
        "v_ospathjoin",
        "v_percent",
        "v_format",
        "v_concat",
    ],
)
def test_resolve_value_resolves_each_of_the_eight_value_forms(tmp_path: Path, binding: str) -> None:
    """FR-001's widening: eight forms, ENUMERATED SEPARATELY so a missing one reds on its own."""
    path = _materialise(tmp_path, "mod_value_forms.py", _EIGHT_VALUE_FORMS)
    tree = scan.parse_module(path)
    bindings = scan.collect_bindings(tree)
    assert binding in bindings, f"{binding} must be a collected single-assignment local binding"
    assert scan.resolve_value(bindings[binding], bindings) == scan.TMP_PATH_HOME


@pytest.mark.parametrize("binding", ["v_name_keyed", "v_dynamic"])
def test_resolve_value_returns_none_and_none_matches_nothing(tmp_path: Path, binding: str) -> None:
    """`None` is unresolvable and NEVER matches anything — asserted, not assumed."""
    path = _materialise(tmp_path, "mod_value_forms.py", _EIGHT_VALUE_FORMS)
    tree = scan.parse_module(path)
    bindings = scan.collect_bindings(tree)
    resolved = scan.resolve_value(bindings[binding], bindings)
    assert resolved is None
    assert resolved != scan.TMP_PATH_HOME
    assert resolved != scan.TMP_PATH_USER_HOME
    assert resolved != scan.TMP_PATH


# ---------------------------------------------------------------------------
# T003 — the keyer, discover(), and the identity/attribution separation
# ---------------------------------------------------------------------------

_MEMBER_TREE = '''
import os

import pytest


@pytest.fixture
def plain_member(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # M1 plain fixture


@pytest.fixture
def closure_holder(tmp_path, monkeypatch):
    def inner_writer(flag, label):
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # M2 nested closure

    return inner_writer


@pytest.fixture
def chain_union_outer(tmp_path):
    def chain_union_inner(monkeypatch):
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # M3 chain union only

    return chain_union_inner


@pytest.fixture
def owner_param_member(monkeypatch, canonical_home):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(canonical_home / "home"))  # M4 FR-010 owner param


@pytest.fixture
def non_member_other_value(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "other"))  # N1 wrong value


@pytest.fixture
def non_member_unresolvable(tmp_path, monkeypatch, opaque):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(opaque.resolve_home()))  # N2 unresolvable


def test_outermost_attribution_wins(tmp_path, monkeypatch):
    def _run_once():
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # M5 the :1165 shape

    _run_once()
'''


def _member_tree(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "synthetic_tests"
    path = _materialise(root, "test_member_tree.py", _MEMBER_TREE)
    return root, path


def test_discover_returns_the_enumerated_member_key_set(tmp_path: Path) -> None:
    """Each admitted and each refused shape is NAMED, so a wrong limb reds on the named row."""
    root, path = _member_tree(tmp_path)
    relpath = path.relative_to(root).as_posix()
    source = path.read_text(encoding="utf-8")

    expected = {
        scan.member_key(relpath, source, _lineno_of(path, "# M1 plain fixture")),
        scan.member_key(relpath, source, _lineno_of(path, "# M2 nested closure")),
        scan.member_key(relpath, source, _lineno_of(path, "# M3 chain union only")),
        scan.member_key(relpath, source, _lineno_of(path, "# M4 FR-010 owner param")),
        scan.member_key(relpath, source, _lineno_of(path, "# M5 the :1165 shape")),
    }
    discovered = scan.discover(root)
    assert {member.key for member in discovered} == expected

    refused_linenos = {
        _lineno_of(path, "# N1 wrong value"),
        _lineno_of(path, "# N2 unresolvable"),
    }
    assert {member.lineno for member in discovered} & refused_linenos == set()


def test_member_key_is_the_write_site_innermost_qualname_not_the_attributed_def(
    tmp_path: Path,
) -> None:
    """C-012(1)/(2): identity at the INNERMOST write-site qualname; the keyed def is NOT in it."""
    root, path = _member_tree(tmp_path)
    discovered = {member.lineno: member for member in scan.discover(root)}

    nested = discovered[_lineno_of(path, "# M2 nested closure")]
    assert nested.key[1] == "closure_holder.inner_writer"
    # ... while ATTRIBUTION is read at the outermost satisfying def, which is the fixture.
    assert nested.kind == "fixture"

    union = discovered[_lineno_of(path, "# M3 chain union only")]
    assert union.key[1] == "chain_union_outer.chain_union_inner"
    assert union.params >= {"tmp_path", "monkeypatch"}


def test_member_key_composition_is_explicit_because_the_types_differ(tmp_path: Path) -> None:
    """C-012(0a): `MemberKey = (relpath_posix, *composite_key_from_file(path, lineno))`."""
    from tests.architectural._ratchet_keys import composite_key_from_file

    root, path = _member_tree(tmp_path)
    member = next(m for m in scan.discover(root) if m.lineno == _lineno_of(path, "# M1 plain fixture"))
    primitive = composite_key_from_file(path, member.lineno)
    # The primitive is the trailing PAIR; the key is the path-qualified TRIPLE. Comparing the
    # two directly is a `mypy --strict` type error, which is why the composition is spelled out.
    assert primitive == member.key[1:]
    assert member.key == (member.relpath, *primitive)


def test_kind_distribution_mechanises_c004_at_the_keyed_def(tmp_path: Path) -> None:
    """C-012(4): C-004 is mechanised by the `kind` DISTRIBUTION, never by the key set."""
    root, path = _member_tree(tmp_path)
    keyed = scan.kind_distribution(root, at="keyed")
    innermost = scan.kind_distribution(root, at="innermost")
    # M5 mirrors `:1165`: `test-body` at the keyed def, `helper` at the innermost. That single
    # cell is the whole of C-004's mechanisation, and it reds HERE rather than in WP05.
    assert keyed == {"fixture": 3, "test-body": 1, "helper": 1}
    assert innermost == {"fixture": 2, "test-body": 0, "helper": 3}
    assert keyed != innermost, "the synthetic tree must be able to tell the two readings apart"
    assert path.exists()


def test_kind_distribution_over_the_real_tree_mechanises_c004() -> None:
    """C-012(4), asserted as the DISCRIMINATION between the two readings — never as the counts.

    **Why not the counts.** This test previously pinned `{30, 10, 0}` against `{30, 9, 1}`. Those
    are census-sized figures, and `discovered == census u E` means the discovered population
    legitimately GROWS: WP03's canonical owner and its retained-pin probe are class members by
    construction and belong to `E`, so `discover(Path("tests"))` is 40 in this lane and 42 once
    WP03 lands. Absolute counts are not what mechanises C-004 and they red on a change the spec
    mandates.

    **What actually mechanises C-004 is the shape of the disagreement**: attributing at the keyed
    (outermost satisfying) def versus at the innermost moves members from `test-body` to `helper`
    ONE FOR ONE and never touches `fixture`. Every arm below is invariant under `E` growing —
    a new top-level fixture member adds equally to both readings — and under R1b shrinking the
    census.

    **The magnitude of the transfer is REPORTED, not asserted.** Pinning it at 1 would rebuild
    exactly the brittleness this test is being repaired for: it is an absolute population figure,
    and it moves the day a second `:1165`-shaped member lands or the day R1b adjudicates the one
    away. The directional arm is what keeps the assertion non-vacuous.
    """
    keyed = scan.kind_distribution(TESTS_ROOT, at="keyed")
    innermost = scan.kind_distribution(TESTS_ROOT, at="innermost")

    # Same population under both readings — only the attribution depth differs.
    assert sum(keyed.values()) == sum(innermost.values())
    # Attribution depth NEVER reclassifies a fixture.
    assert keyed["fixture"] == innermost["fixture"]
    # Everything that moves, moves `test-body` (keyed) -> `helper` (innermost), one for one.
    assert keyed["test-body"] - innermost["test-body"] == innermost["helper"] - keyed["helper"]

    # NON-VACUITY used to be directional over the real tree (`keyed["test-body"] >
    # innermost["test-body"]`). Issue-5-delete-sync-transport removed every member that the two
    # readings could disagree about -- the surviving population is exactly E, all fixtures -- so
    # the real tree can no longer exercise the transfer and this arm lives entirely in
    # test_kind_distribution_mechanises_c004_at_the_keyed_def above, whose synthetic M5-shaped
    # tree still forces `keyed != innermost`.

    print(
        "[reported, not asserted] keyed-vs-innermost transfer: "
        f"{keyed['test-body'] - innermost['test-body']}; keyed={keyed}; innermost={innermost}"
    )


# `test_home_partition_over_the_real_tree_matches_the_published_distribution` was REMOVED here and
# relocated to WP05/T023 — see `_home_pin_scan._home_partition`'s docstring for why. It was not
# dropped: A=27/B1=11/B2=2 is a CENSUS claim, and only WP05 can see both `discover()` and `E`.


_PARTITION_TREE = '''
import os

import pytest


@pytest.fixture
def partition_a(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # P-A no HOME re-pin


@pytest.fixture
def partition_b1(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # P-B1 member site
    monkeypatch.setenv("HOME", str(tmp_path / "home"))


@pytest.fixture
def partition_b2(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # P-B2 member site
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))


@pytest.fixture
def partition_other(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # P-other member site
    monkeypatch.setenv("HOME", str(tmp_path / "elsewhere"))
'''


def test_home_partition_is_produced_for_every_member_with_one_example_each(
    tmp_path: Path,
) -> None:
    """FR-003's effect axis. `other` has real-tree population 0, so THIS example IS its control."""
    root = tmp_path / "partition_tree"
    path = _materialise(root, "test_partition_tree.py", _PARTITION_TREE)
    by_line = {member.lineno: member for member in scan.discover(root)}
    assert set(by_line) == {
        _lineno_of(path, "# P-A no HOME re-pin"),
        _lineno_of(path, "# P-B1 member site"),
        _lineno_of(path, "# P-B2 member site"),
        _lineno_of(path, "# P-other member site"),
    }
    assert by_line[_lineno_of(path, "# P-A no HOME re-pin")].home_partition == "A"
    assert by_line[_lineno_of(path, "# P-B1 member site")].home_partition == "B1"
    assert by_line[_lineno_of(path, "# P-B2 member site")].home_partition == "B2"
    assert by_line[_lineno_of(path, "# P-other member site")].home_partition == "other"


_COLLIDING_TREE = '''
import pytest


@pytest.fixture
def twin_sites(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
'''


def test_discover_raises_on_two_members_sharing_a_byte_identical_triple(tmp_path: Path) -> None:
    """C-012(5): the 3-tuple is non-injective and the counterexample is LIVE — so this RAISES."""
    root = tmp_path / "colliding_tree"
    _materialise(root, "test_colliding.py", _COLLIDING_TREE)
    with pytest.raises(scan.DuplicateMemberKeyError):
        scan.discover(root)


def test_discover_over_the_real_tests_tree_does_not_raise() -> None:
    """The exactly-one assertion must hold on the real tree, or the guard cannot ship."""
    members = scan.discover(TESTS_ROOT)
    assert members
    print(f"[reported, not asserted] members discovered under tests/: {len(members)}")


# ---------------------------------------------------------------------------
# T004 — the inert SUB-FORM registry, its controls, and the QUADRUPLE
# ---------------------------------------------------------------------------

SPEC_PATH = REPO_ROOT / "kitty-specs" / "isolated-home-pin-guard-r1a-01KZNMA3" / "spec.md"
SRC_ROOT = REPO_ROOT / "src"

#: **Enumerated literally HERE and never imported from the module under test.** Comparing
#: `INERT_LIMBS` only against a set derived from `_home_pin_scan.py` proves "every id I remembered
#: to register has a control" and can be shrunk to zero and stay green — the same circularity
#: C-011 diagnoses for the census, relocated into the registry built to prove the census's proofs
#: were complete. **This literal is what reds when a sub-form is removed from production.**
INLINE_EXPECTED: frozenset[str] = frozenset(
    {
        "SKH-SETDEFAULT",
        "SKH-BARE-SETENV",
        "SKH-VAL-OSPATHJOIN",
        "SKH-VAL-PERCENT",
        "SKH-VAL-FORMAT",
        "SKH-VAL-CONCAT",
        "HOME-SETDEFAULT",
        "HOME-VAL-OSPATHJOIN",
        "HOME-VAL-PERCENT",
        "HOME-VAL-FORMAT",
        "HOME-VAL-CONCAT",
        "SCOPE-EXPLICIT",
        "PARTITION-OTHER",
        "WITHITEM-VALUE-REF",
        "SC-002b",
    }
)

#: Every control marks its shape line with ``# the-shape``, so the control asserts WHICH site the
#: production matcher found rather than how many — a count would still pass if the matcher landed
#: on the wrong line.
SHAPE_MARKER = "# the-shape"

_SKH_VALUE_CONTROL = '''
import os

import pytest


@pytest.fixture
def pinned(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", {expression})  # the-shape
'''

_HOME_VALUE_CONTROL = '''
import os

import pytest


@pytest.fixture
def pinned(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", {expression})  # the-shape
'''

#: ``id -> synthetic source containing exactly one instance of the shape``. **The set of shipped
#: controls is the QUADRUPLE's fourth operand**, so it is derived from this mapping and never
#: written twice.
_CONTROLS: dict[str, str] = {
    "SKH-SETDEFAULT": '''
        import os


        def probe(tmp_path, monkeypatch):
            os.environ.setdefault("SPEC_KITTY_HOME", str(tmp_path / "home"))  # the-shape
    ''',
    "SKH-BARE-SETENV": '''
        def probe(tmp_path, monkeypatch):
            setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # the-shape
    ''',
    "SKH-VAL-OSPATHJOIN": _SKH_VALUE_CONTROL.format(
        expression='os.path.join(str(tmp_path), "home")'
    ),
    "SKH-VAL-PERCENT": _SKH_VALUE_CONTROL.format(expression='"%s/home" % str(tmp_path)'),
    "SKH-VAL-FORMAT": _SKH_VALUE_CONTROL.format(expression='"{}/home".format(str(tmp_path))'),
    "SKH-VAL-CONCAT": _SKH_VALUE_CONTROL.format(expression='str(tmp_path) + "/home"'),
    "HOME-SETDEFAULT": '''
        import os


        def probe(tmp_path, monkeypatch):
            os.environ.setdefault("HOME", str(tmp_path / "home"))  # the-shape
    ''',
    "HOME-VAL-OSPATHJOIN": _HOME_VALUE_CONTROL.format(
        expression='os.path.join(str(tmp_path), "home")'
    ),
    "HOME-VAL-PERCENT": _HOME_VALUE_CONTROL.format(expression='"%s/home" % str(tmp_path)'),
    "HOME-VAL-FORMAT": _HOME_VALUE_CONTROL.format(expression='"{}/home".format(str(tmp_path))'),
    "HOME-VAL-CONCAT": _HOME_VALUE_CONTROL.format(expression='str(tmp_path) + "/home"'),
    "SCOPE-EXPLICIT": '''
        import pytest


        @pytest.fixture(scope="session")
        def pinned(tmp_path, monkeypatch):  # the-shape
            monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    ''',
    "PARTITION-OTHER": '''
        import pytest


        @pytest.fixture
        def pinned(tmp_path, monkeypatch):
            monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # the-shape
            monkeypatch.setenv("HOME", str(tmp_path / "elsewhere"))
    ''',
    "WITHITEM-VALUE-REF": '''
        import pytest


        def probe(tmp_path, monkeypatch):
            with open_home_root(tmp_path) as bound_home:
                monkeypatch.setenv("SPEC_KITTY_HOME", str(bound_home))  # the-shape
    ''',
    "SC-002b": '''
        RUNTIME_HOME_ENV = "SPEC_KITTY_HOME"  # the-shape
    ''',
}

#: The fourth operand: the ids of the controls this module actually ships.
CONTROL_IDS: frozenset[str] = frozenset(_CONTROLS)


def _fr007_table_ids(text: str) -> list[str]:
    """Parse FR-007's inert sub-form table out of `spec.md`, by its explicit `id` column.

    One sub-form per row, no four-way cells, no anaphoric rows — a table whose sub-forms are
    packed into one cell cannot be parsed into ids without the parser inventing them, and a
    parser written to emit the author's own set is the circularity the fourth operand exists to
    close, relocated one level out.
    """
    ids: list[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if not in_table:
            in_table = stripped.startswith("| id |") and "Inert sub-form" in stripped
            continue
        if not stripped.startswith("|"):
            break
        first = [cell.strip() for cell in stripped.strip("|").split("|")][0]
        if set(first) <= set("-: "):
            continue
        assert first.startswith("`") and first.endswith("`"), f"row id must be backticked: {first!r}"
        ids.append(first.strip("`"))
    return ids


def test_inert_registry_completeness_is_a_quadruple() -> None:
    """`spec_table_ids u {SC-002b} == inline_expected == INERT_LIMBS == {ids of shipped controls}`.

    Four operands, not three. Without the fourth the three code artefacts stay internally
    consistent and green while DIVERGING FROM THE SPEC THAT DEFINES THE POPULATION — and a
    spec/code divergence is exactly the defect that produced the `HOME`-limb registration, so a
    mechanism that only watches code-versus-code guards the wrong axis of its own motivating
    failure.
    """
    spec_ids = _fr007_table_ids(SPEC_PATH.read_text(encoding="utf-8"))
    # Prove the instrument can see before trusting what it does not find.
    assert spec_ids, "the FR-007 table parser returned nothing — it is not reading the table"
    assert len(spec_ids) == len(set(spec_ids)), f"the id column is not a key: {spec_ids}"
    # C-002: the ROW COUNT is REPORTED, never asserted — the table legitimately grows, and the
    # set delta below already reds when it grows and the registry does not follow.
    print(f"[reported, not asserted] FR-007 inert sub-form table rows: {len(spec_ids)}")

    spec_table_ids = frozenset(spec_ids)
    assert spec_table_ids - INLINE_EXPECTED == set()
    assert spec_table_ids | {"SC-002b"} == INLINE_EXPECTED
    assert INLINE_EXPECTED == scan.INERT_LIMBS
    assert INLINE_EXPECTED == CONTROL_IDS


def test_the_home_enumeration_limb_is_not_registered_as_inert() -> None:
    """Measured, it is the most heavily populated LIMB in the classifier — the opposite of inert.

    Registering it would mandate a FALSE empty-set assertion whose cheapest repairs are both
    catastrophic: narrow the `HOME` matcher until it returns `set()`, collapsing B1/B2 into A and
    surfacing only in a different WP; or delete the id, keeping the equality green.
    """
    assert not {limb for limb in scan.INERT_LIMBS if limb == "HOME-ENUMERATION"}
    unfiltered = scan.enumerate_py_files(TESTS_ROOT)
    sites = {
        (path.relative_to(TESTS_ROOT).as_posix(), site.lineno)
        for path in unfiltered
        for site in scan.find_write_sites(scan.parse_module(path), key=scan.HOME_KEY)
    }
    assert sites, "a limb registered inert must be measured, not assumed"
    print(
        f"[reported, not asserted] unfiltered HOME write sites: {len(sites)} "
        f"in {len({relpath for relpath, _ in sites})} files"
    )
    # The B1/B2 "repinner" members used to be asserted non-empty over the real tree. Every such
    # member's file was deleted with the sync transport (issue #5), so the real-tree set measures
    # EMPTY and the surviving members are exactly E, partition A. The classifier's non-A arms stay
    # exercised on the synthetic trees in this package (`_MEMBER_TREE`, `_PARTITION_TREE`); a
    # future real B1/B2 member reds t023's discovered-class equality until the artefacts catch up.
    repinners = {m.key for m in scan.discover(TESTS_ROOT) if m.home_partition != "A"}
    assert repinners == set(), (
        "a non-A member appeared without its census/tombstone paperwork -- regenerate the home-pin "
        f"artefacts: {sorted(repinners)}"
    )


def test_fr010_runtime_home_alias_is_measured_inert_and_refused_on_both_limbs() -> None:
    """`runtime_home` matches nothing, and this is where that is measured rather than assumed.

    FR-007's rule — a limb matching nothing must be known to match nothing or it reads as
    enforcement — is applied above to fifteen ids; `OWNER_PARAM_NAMES` was the entry presented as
    live while matching nothing. **Its two names have since diverged and the docstring in
    `_home_pin_scan` tracks both**: `canonical_home` is now LIVE (WP03 landed the owner, and
    WP03/T012 binds the name to the contract), while `runtime_home` — the shape FR-010 cites as
    "the live population-1 shape" — remains population 0. It is live as a SHAPE and 0 as a
    member, because it is refused on **both** limbs at once, which is exactly the pair of
    failures FR-010 says such a definition suffers.

    This assertion is invariant across the WP03 boundary: `_capture_nudge` declares
    `runtime_home`, never the owner, so it is refused in this lane and in the merged tree alike.

    The positive control for the limb as a whole is the `# M4 FR-010 owner param` member in
    `_MEMBER_TREE`: the alias does admit a member when silhouette and value both cooperate.
    """
    probe = TESTS_ROOT / "audit" / "test_no_legacy_path_literals.py"
    tree = scan.parse_module(probe)
    module_bindings = scan.module_level_bindings(tree)
    sites = scan.find_write_sites(tree, key=NEEDLE)
    assert sites, "the cited anchor no longer carries a pin — this control has gone vacuous"

    for site in sites:
        chain = scan.def_chain(tree, site.lineno)
        union: frozenset[str] = frozenset()
        for node in chain:
            union |= scan.normalise_params(scan.def_params(node))
        # Limb 1 — the SILHOUETTE: `monkeypatch` is absent even with the alias applied.
        assert not union >= scan.SILHOUETTE
        # Limb 2 — VALUE RESOLUTION: the alias resolves, but never to `tmp_path/"home"`.
        bindings = scan.bindings_for_site(tree, site, module_bindings)
        assert scan.resolve_value(site.value, bindings) != scan.TMP_PATH_HOME
        assert scan.key_member(site, chain) is None

    assert not [m for m in scan.discover(TESTS_ROOT) if m.relpath == "audit/test_no_legacy_path_literals.py"]


def _real_roots(limb_id: str) -> tuple[Path, ...]:
    """SC-002b is stated over `src/` u `tests/`; every other id over the walked tree."""
    return (SRC_ROOT, TESTS_ROOT) if limb_id == "SC-002b" else (TESTS_ROOT,)


@pytest.mark.parametrize("limb_id", sorted(INLINE_EXPECTED))
def test_every_inert_sub_form_has_population_zero_over_the_real_tree(limb_id: str) -> None:
    """(i) of the pair. Any entry with a NON-ZERO population is a REGISTRY defect, not a matcher one."""
    hits: set[tuple[str, int]] = set()
    for root in _real_roots(limb_id):
        hits |= scan.inert_hits(limb_id, root)
    assert hits == set()


@pytest.mark.parametrize("limb_id", sorted(INLINE_EXPECTED))
def test_every_inert_sub_form_ships_a_positive_control(tmp_path: Path, limb_id: str) -> None:
    """(ii) of the pair: the SAME production matcher over a module containing the shape.

    **Any control returning `set()` fails the module** — an over-narrow matcher greens forever
    and still greens the day someone writes the shape for real.

    ``limb_id`` is folded into the root, not just ``tmp_path``: every parametrization of
    this test shares one 30-char-truncated node-name prefix (`_pytest.tmpdir._mk_tmp`'s
    ``MAXVAL``), so under ``tmp_path_retention_policy = failed`` pytest's numbered-dir
    allocator can hand two different ``limb_id``s the *same* physical directory once an
    earlier one is rmtree'd at its own teardown. `_home_pin_scan.py::_corpus` caches by
    root path alone, so a bare ``tmp_path`` here would let one limb's parse poison the
    next's cache entry.
    """
    root = tmp_path / "control_root" / limb_id
    control = _materialise(root, "test_control_module.py", _CONTROLS[limb_id])
    expected = {(control.relative_to(root).as_posix(), _lineno_of(control, SHAPE_MARKER))}
    hits = scan.inert_hits(limb_id, root)
    assert hits == expected, f"control for {limb_id} returned {hits!r} — a control returning set() proves nothing"


def test_sc002b_publishes_its_denominator() -> None:
    """0 assignment-bound against 229 literal occurrences in 98 files. The 229 makes the 0 mean something."""
    occurrences: set[tuple[str, int]] = set()
    for root in (SRC_ROOT, TESTS_ROOT):
        occurrences |= scan.literal_key_occurrences(root)
    files = {relpath for relpath, _ in occurrences}
    assert occurrences, "a population of 0 with no denominator cannot be audited"
    print(
        f"[reported, not asserted] literal 'SPEC_KITTY_HOME' constants: {len(occurrences)} "
        f"in {len(files)} files"
    )


def test_this_module_never_parses_outside_the_seam() -> None:
    """DoD 3: zero `ast.parse` calls and zero `ast.NodeVisitor` subclasses in THIS module."""
    own = scan.parse_module(Path(__file__))
    assert scan.find_module_references(own, names=frozenset({"ast"})) == set()


# ---------------------------------------------------------------------------
# T005 — render_census / render_baseline and the one regeneration entry
# ---------------------------------------------------------------------------

_THREE_MEMBERS = '''
import pytest


@pytest.fixture
def first(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # C1
    monkeypatch.setenv("HOME", str(tmp_path / "home"))


@pytest.fixture
def second(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(Path(tmp_path, "home")))  # C2


def test_third(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", f"{tmp_path}/home")  # C3
'''

FROZEN_SHA = "5d49d31ed6505627d98d8f95d8502c9bf6a2f5ac"


def _three_members(tmp_path: Path) -> set[scan.Member]:
    root = tmp_path / "census_tree"
    path = _materialise(root, "test_three_members.py", _THREE_MEMBERS)
    relpath, source = path.relative_to(root).as_posix(), path.read_text(encoding="utf-8")
    members = scan.discover(root)
    assert {member.key for member in members} == {
        scan.member_key(relpath, source, _lineno_of(path, marker))
        for marker in ("# C1", "# C2", "# C3")
    }
    return members


def test_render_census_rows_and_header_are_both_asserted_by_set_equality(tmp_path: Path) -> None:
    """FR-003: a per-row constant is a header scalar wearing row clothing, and the symmetric
    failure — a `reason` IN THE HEADER — is why the header is asserted the same way the rows are."""
    members = _three_members(tmp_path)
    document = yaml.safe_load(scan.render_census(members, sha=FROZEN_SHA, owed_to="#3121"))

    assert set(document["header"]) == {
        "generated_by",
        "regeneration_command",
        "frozen_at_sha",
        "owed_to",
        "fragility_note",
    }
    assert document["header"]["frozen_at_sha"] == FROZEN_SHA
    assert re.match(r"^#[0-9]+$", document["header"]["owed_to"])

    rows = document["rows"]
    assert {tuple(row["key"]) for row in rows} == {member.key for member in members}
    assert {name for row in rows for name in row} == {"key", "lineno", "kind", "home_partition"}


def test_render_census_refuses_an_owed_to_that_is_a_reason_column_in_kebab_case(
    tmp_path: Path,
) -> None:
    """`owed_to` matches `^#[0-9]+$` and nothing else — `SK-12-also-pins-home` is prose."""
    members = _three_members(tmp_path)
    with pytest.raises(ValueError, match=r"\^#\[0-9\]\+\$"):
        scan.render_census(members, sha=FROZEN_SHA, owed_to="SK-12-also-pins-home")


def _census_key_set_sha(document: str) -> str:
    return str(yaml.safe_load(document)["census_key_set_sha256"])


def test_render_baseline_hashes_the_key_set_and_not_the_file(tmp_path: Path) -> None:
    """The only triple the construction satisfies: INVARIANT / INVARIANT / CHANGES.

    `sha256(path.read_bytes())` passes any "a hash exists" check and fails the first two arms —
    plan §5's day-thirty failure.
    """
    members = _three_members(tmp_path)
    baseline = scan.render_baseline(members, exempt=())
    digest = _census_key_set_sha(baseline)

    # CONSTRUCTED, not read: the digest is rebuilt here from the KEY SET alone. This single
    # assertion is what `sha256(path.read_bytes())` cannot satisfy at all — the three arms below
    # are the behavioural statement of the same property.
    payload = "\n".join("\t".join(member.key) for member in sorted(members, key=lambda m: m.key))
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()  # noqa: TID251 — reconstructing the census key-set checksum, not the charter hash
    assert digest == expected

    # Positive controls: the two edits below really do change the census artefact's bytes.
    census_a = scan.render_census(members, sha=FROZEN_SHA, owed_to="#3121")
    census_b = scan.render_census(members, sha=FROZEN_SHA, owed_to="#9999")
    census_c = census_a + "\n# a hand-added trailing comment\n"
    assert census_a != census_b and census_a != census_c

    # 1. INVARIANT under an `owed_to` re-point.
    assert _census_key_set_sha(scan.render_baseline(members, exempt=())) == digest
    # 2. INVARIANT under a header / comment edit — the baseline never reads the census file.
    assert scan.render_baseline(members, exempt=()) == baseline
    # 3. CHANGES when one member key is removed.
    shrunk = set(sorted(members, key=lambda member: member.key)[1:])
    assert _census_key_set_sha(scan.render_baseline(shrunk, exempt=())) != digest


def test_render_baseline_header_is_the_tombstone_lists_named_home(tmp_path: Path) -> None:
    """FR-004(1) is "paths, named, not described"; the census header's key set has no room."""
    members = _three_members(tmp_path)
    document = yaml.safe_load(scan.render_baseline(members, exempt=()))
    assert set(document) == {
        "generated_by",
        "regeneration_command",
        "census_key_set_sha256",
        "exempt_set_sha256",
        "tombstones",
    }
    assert document["tombstones"] == []


def test_both_generators_are_byte_identical_on_a_second_run(tmp_path: Path) -> None:
    members = _three_members(tmp_path)
    # Two independent invocations, bound to distinct names, so the determinism
    # check compares separate render results rather than a self-identical
    # expression (SonarCloud python:S5863).
    census_first = scan.render_census(members, sha=FROZEN_SHA, owed_to="#3121")
    census_second = scan.render_census(members, sha=FROZEN_SHA, owed_to="#3121")
    assert census_first == census_second
    baseline_first = scan.render_baseline(members, exempt=())
    baseline_second = scan.render_baseline(members, exempt=())
    assert baseline_first == baseline_second


def test_main_demonstrates_the_exempt_module_absent(tmp_path: Path) -> None:
    """`--exempt-module` defaults to None and is imported INSIDE `main()`, so `E` is empty here.

    WP01 therefore never depends on WP03; WP05/T022 is what passes the flag.
    """
    root = tmp_path / "census_tree"
    _materialise(root, "test_three_members.py", _THREE_MEMBERS)
    census_out = tmp_path / "out" / "census.yaml"
    baseline_out = tmp_path / "out" / "baseline.yaml"
    exit_code = scan.main(
        [
            "--root",
            str(root),
            "--frozen-at-sha",
            FROZEN_SHA,
            "--census-out",
            str(census_out),
            "--baseline-out",
            str(baseline_out),
        ]
    )
    assert exit_code == 0
    rows = yaml.safe_load(census_out.read_text(encoding="utf-8"))["rows"]
    assert {tuple(row["key"]) for row in rows} == {member.key for member in scan.discover(root)}
    baseline = yaml.safe_load(baseline_out.read_text(encoding="utf-8"))
    # E absent means the empty payload, reconstructed here rather than read off the module.
    empty = hashlib.sha256(b"").hexdigest()  # noqa: TID251 — reconstructing the empty exempt-set checksum, not the charter hash
    assert baseline["exempt_set_sha256"] == empty
    # A second run is byte-identical.
    before = (census_out.read_bytes(), baseline_out.read_bytes())
    scan.main(
        [
            "--root",
            str(root),
            "--frozen-at-sha",
            FROZEN_SHA,
            "--census-out",
            str(census_out),
            "--baseline-out",
            str(baseline_out),
        ]
    )
    assert (census_out.read_bytes(), baseline_out.read_bytes()) == before


# ---------------------------------------------------------------------------
# T005 (reopened) — E is subtracted from the census, and the shipped command says so
# ---------------------------------------------------------------------------

#: A synthetic `E`, shaped exactly like WP03's: **fixed arity by type**, so a third entry is a
#: `mypy --strict` error. It derives its keys by calling `discover()` on the same root rather
#: than embedding literals, so the control works at 3 members, at 40 and at 42 alike.
_EXEMPT_MODULE_TEMPLATE = '''
from pathlib import Path

from tests.architectural._home_pin_scan import Exempt, discover

_ROOT = Path({root!r})
_MEMBERS = sorted(discover(_ROOT), key=lambda member: member.key)

E: tuple[Exempt, Exempt] = (
    Exempt(_MEMBERS[0].key, "synthetic canonical owner"),
    Exempt(_MEMBERS[1].key, "synthetic retained-pin probe"),
)
'''


def _census_keys(path: Path) -> set[scan.MemberKey]:
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))["rows"]
    return {(row["key"][0], row["key"][1], row["key"][2]) for row in rows}


@pytest.mark.parametrize("case", ["synthetic-tree", "real-tree"])
def test_main_with_an_exempt_module_keeps_e_out_of_the_census(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """**The positive control that was missing, and its absence is why the defect shipped.**

    The only `main()` test ran with `--exempt-module` ABSENT, so the flag's effect on the census
    was exercised by nothing — the population-0-without-a-control shape this mission has been
    closing everywhere else, in the one place nobody pointed it at.

    With `E ⊆ census`, `census u E` is a NO-OP UNION and `discovered == census u E` degenerates
    to `discovered == census`: the accounting reports that it works while doing nothing, and the
    canonical owner becomes a census row owed an adjudication under C-007's monotonic
    non-increase. Every arm below is a set relation, so it is meaningful at 3 members, at 40
    without WP03's owner, and at 42 with it.
    """
    if case == "synthetic-tree":
        root = tmp_path / "census_tree"
        _materialise(root, "test_three_members.py", _THREE_MEMBERS)
    else:
        root = TESTS_ROOT

    module_name = f"_synthetic_exempt_{case.replace('-', '_')}"
    _materialise(tmp_path, f"{module_name}.py", _EXEMPT_MODULE_TEMPLATE.format(root=str(root)))
    monkeypatch.syspath_prepend(str(tmp_path))

    census_out = tmp_path / "out" / f"census_{case}.yaml"
    baseline_out = tmp_path / "out" / f"baseline_{case}.yaml"
    argv = [
        "--root", str(root),
        "--frozen-at-sha", FROZEN_SHA,
        "--census-out", str(census_out),
        "--baseline-out", str(baseline_out),
    ]

    assert scan.main([*argv, "--exempt-module", module_name]) == 0
    with_exempt = _census_keys(census_out)

    exempt_keys: set[scan.MemberKey] = {
        entry.key for entry in importlib.import_module(module_name).E
    }
    discovered = {member.key for member in scan.discover(root)}
    assert exempt_keys <= discovered, "the control is vacuous unless E is drawn from real members"

    # The Not-Done-If, mechanised: `E` and the census may never share a key.
    assert with_exempt & exempt_keys == set()
    # ... and the subtraction is EXACT, so `census u E` reconstructs the discovered class.
    assert with_exempt | exempt_keys == discovered

    # POSITIVE CONTROL: the flag must actually MOVE the census. Byte-identical output with and
    # without `--exempt-module` is precisely the silent green this test exists to catch.
    assert scan.main(argv) == 0
    assert _census_keys(census_out) - with_exempt == exempt_keys


def _parses(argv: list[str]) -> bool:
    try:
        scan.build_parser().parse_args(argv)
    except SystemExit:
        return False
    return True


def test_the_shipped_regeneration_command_names_every_flag_it_needs() -> None:
    """FR-004(2): the header must name the command that actually reproduces the artefact.

    Omitting `--exempt-module` sends a maintainer following the shipped header down exactly the
    path T022 names as a failure — a census with `E` still in it. Naming a flag that does not
    exist (`--regenerate`, `--sha`) sends them nowhere at all. Both are caught here by PARSING
    the shipped string rather than eyeballing it.
    """
    flags = {token for token in shlex.split(scan.REGENERATION_COMMAND) if token.startswith("--")}
    assert flags, "the parser check is vacuous unless the shipped command carries flags"
    assert "--exempt-module" in flags

    argv = ["--frozen-at-sha", FROZEN_SHA]
    for flag in sorted(flags - {"--frozen-at-sha"}):
        argv += [flag, "placeholder"]
    assert _parses(argv)
    # Positive control: the same mechanism REJECTS a flag argparse does not define, so a header
    # naming `--regenerate` or `--sha` could never pass the arm above.
    assert not _parses([*argv, "--regenerate", "placeholder"])


# ---------------------------------------------------------------------------
# T026(1) — the fragility register, and the census note derived FROM it
# ---------------------------------------------------------------------------

_FRAGILE_TREE = '''
import pytest


def test_fragile_member(tmp_path, monkeypatch):
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # F1 held by an unused monkeypatch


@pytest.fixture
def sturdy_member(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))  # F2 both params referenced
'''


def test_fragility_register_names_only_members_held_by_an_unused_silhouette_parameter(
    tmp_path: Path,
) -> None:
    """C-012(5)/§0.1b's named residual, constructed: `ruff`'s relaxed `ARG` for `tests/**` will
    not defend a declared-but-never-referenced `monkeypatch`, so such a member is one routine
    cleanup away from leaving the class silently."""
    root = tmp_path / "fragile_tree"
    path = _materialise(root, "test_fragile_tree.py", _FRAGILE_TREE)
    relpath, source = path.relative_to(root).as_posix(), path.read_text(encoding="utf-8")

    register = scan.fragility_register(root)
    assert {row.key for row in register} == {
        scan.member_key(relpath, source, _lineno_of(path, "# F1 held by an unused monkeypatch"))
    }
    # The sturdy member IS discovered and is NOT registered, or the register is a no-op.
    assert {member.key for member in scan.discover(root)} > {row.key for row in register}


def test_fragility_register_over_the_real_tree_is_a_subset_of_the_class() -> None:
    """Every arm is a set relation, so it survives `E` growing the discovered population.

    The real-tree register measured exactly one row (the `:1165` shape) until
    issue-5-delete-sync-transport deleted that file with the sync transport; it measures EMPTY
    now, so the non-empty arm was dropped and the matcher's bite lives in
    test_fragility_register_names_only_members_held_by_an_unused_silhouette_parameter above. An
    empty register here is therefore a measured fact, not a blind matcher -- but if one appears,
    t025's equality reds until the artefacts are regenerated.
    """
    register = scan.fragility_register(TESTS_ROOT)
    keys = {row.key for row in register}
    assert keys <= {member.key for member in scan.discover(TESTS_ROOT)}
    for row in register:
        assert scan.normalise_params(row.unused_silhouette_params) & scan.SILHOUETTE
    print(
        "[reported, not asserted] fragility register: "
        + repr(sorted((r.relpath, r.lineno, sorted(r.unused_silhouette_params)) for r in register))
    )


def test_the_census_fragility_note_names_the_fragile_rows_via_the_generator(tmp_path: Path) -> None:
    """T026(1): the census header names the known-fragile row **via the generator**.

    Derived from the register rather than hard-coded, which changes a VALUE and never a key — so
    the header's asserted key set is untouched and no key was added to carry it.
    """
    root = tmp_path / "fragile_tree"
    path = _materialise(root, "test_fragile_tree.py", _FRAGILE_TREE)
    register = scan.fragility_register(root)
    members = scan.discover(root)

    document = yaml.safe_load(
        scan.render_census(members, sha=FROZEN_SHA, owed_to="#3121", fragility=register)
    )
    note = document["header"]["fragility_note"]
    assert register, "a note derived from an empty register would assert nothing"
    for row in register:
        assert f"{row.relpath}:{row.lineno}" in note
    assert str(_lineno_of(path, "# F2 both params referenced")) not in note

    # The header KEY SET is unchanged — a value moved, never a key.
    assert set(document["header"]) == {
        "generated_by",
        "regeneration_command",
        "frozen_at_sha",
        "owed_to",
        "fragility_note",
    }
    # Positive control: without the register the note does NOT claim a population of fragile rows.
    plain = yaml.safe_load(scan.render_census(members, sha=FROZEN_SHA, owed_to="#3121"))
    assert plain["header"]["fragility_note"] != note
