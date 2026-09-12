"""The R1a synthetic-tree MATERIALISER (WP04/T015). **Never collected, and it asserts nothing.**

What this module is
-------------------
A file writer. It turns source **strings** into a real directory under a caller-supplied
``tmp_path`` root and returns a :class:`SyntheticTree` describing what it was built to contain.
Every guard behaviour in ``test_spec_kitty_home_pin_guard.py`` is exercised against one of these
trees through ``_home_pin_scan.discover(root=…)`` — FR-009's root parameter is what makes that
possible without editing a real test module.

Why nothing here is checked in under ``tests/``
-----------------------------------------------
Two independent reasons, either of which alone is decisive (FR-009):

1. ``enumerate_py_files`` is bound to **every** ``.py`` under the root and is **never narrowed**
   (C-003), and the real-tree pass roots at ``tests/``. These trees exist precisely to contain
   **41st members**, so a checked-in tree lands its deliberate extras in ``discovered`` and
   ``discovered == census u E`` can **never** green. Every cheap repair is separately barred:
   directory exclusion by C-003/NFR-001, a census row by C-007, a third ``E`` entry by ``E``'s
   fixed arity. *"Not collected" is a* **pytest** *property and says nothing about the
   classifier's walk.*
2. The deliberate ``SyntaxError`` tree (SC-013) would red ``ruff check`` with **``invalid-syntax``**,
   which is **not a rule code** — ``pyproject.toml``'s ``per-file-ignores`` cannot reach it and no
   ``exclude`` covers ``_``-prefixed directories.

Why this module holds NO assertions
------------------------------------
``pytest.ini`` sets ``testpaths = tests`` with **no ``python_files`` override**, so a module named
``_home_pin_synthetic.py`` is **never collected** and any assertion placed here would never run.
The materialiser's own correctness is proven in the collected module
``test_home_pin_synthetic_trees.py`` (T015), where a tree that silently fails to write a file reds
**there** instead of greening a transition downstream.

Why there is no ``ENV = "SPEC_KITTY_HOME"`` convenience constant
----------------------------------------------------------------
That would be an **assignment-bound string constant valued** ``"SPEC_KITTY_HOME"`` — the exact
population **SC-002b asserts is 0** across ``src/`` u ``tests/`` — and this module lives in
``tests/``. The pin appears here only **inside** the source strings below, where it is a fragment
of a larger literal and not the value of any binding, so ``_assignment_bound_key_hits`` does not
see it (T015(7)).
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "SyntheticTree",
    "materialise",
    "census_frozen_tree",
    "extra_member_in_an_existing_file",
    "extra_member_under_a_novel_name",
    "owner_requesting_witness_tree",
    "colliding_pair_tree",
    "syntax_error_tree",
    "outermost_versus_innermost_tree",
    "member_under_a_fixture_root_tree",
]


@dataclass(frozen=True)
class SyntheticTree:
    """A materialised tree plus the **hand-enumerated** description of what it should contain.

    ``files`` and ``sites`` are authored by a human beside the source strings, never derived from
    the classifier. That is the whole point: they are the independent side of T015's equality, so
    a builder that silently fails to write a file, or a source string that silently stops
    producing a member, reds in ``test_home_pin_synthetic_trees.py``.
    """

    #: The materialised root. Every tree gets its **own** root — ``_home_pin_scan._corpus`` is
    #: ``lru_cache``d on the root PATH and not on its contents, so reusing a root across two
    #: materialisations would hand the second scan the first parse.
    root: Path
    #: Every ``.py`` relpath the tree was built to write, memberless files included.
    files: frozenset[str]
    #: ``(relpath, innermost enclosing qualname)`` for every member the tree was built to contain.
    #: The third key component (the normalised token line) is mechanical and is pinned where it
    #: is load-bearing instead: the colliding-pair tree asserts it byte-identical across two files.
    sites: frozenset[tuple[str, str]]


# ---------------------------------------------------------------------------
# Source strings. Every pin below is written out in full: the classifier matches a
# STRING LITERAL first argument, so a tree assembled by concatenation would not be a member.
# ---------------------------------------------------------------------------

#: A pin-bearing fixture: the ``(tmp_path, monkeypatch)`` silhouette on one def, value
#: ``<tmp_path>/home``. The canonical member shape.
_PINNING_FIXTURE = '''
import pytest


@pytest.fixture
def {name}(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    return tmp_path / "home"
'''

#: A pin-bearing test body — the same silhouette, a different ``kind``.
_PINNING_TEST_BODY = '''
def {name}(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    assert (tmp_path / "home").parent == tmp_path
'''

#: **Not** a member, and deliberately so: the silhouette is unsatisfied (no ``monkeypatch``) and
#: the value never resolves to ``<tmp_path>/home``. It keeps the base tree from being one in
#: which everything is a member, so ``sites`` equality is discriminating rather than trivially met.
_NON_MEMBER_HELPER = '''
from pathlib import Path


def build_a_home(tmp_path):
    """No `monkeypatch`, no pin — the predicate must refuse this."""
    return Path(tmp_path) / "home"
'''

#: A file holding no environment write at all. It exists so that ``files`` equality catches a
#: builder that silently fails to write a file **even when that file holds no member**.
_MEMBERLESS_MODULE = '''
"""Walked, parsed by the unfiltered pass, and a member of nothing."""

VALUE = 3
'''

#: T016(6) / FR-010. ``canonical_home`` **yields a home root** — modelled on the live
#: population-1 ``runtime_home`` shape, **never** on the ``None``-returning canonical owner, which
#: could not be written from. The witness declares ``(monkeypatch, canonical_home)`` and
#: **no ``tmp_path``**, and restates the pin from the owner's value: it fails the naive predicate
#: on two limbs at once and is a member only because ``OWNER_PARAM_NAMES`` counts the owner
#: parameter as ``tmp_path`` for **both** the silhouette and value resolution.
_OWNER_REQUESTING_WITNESS = '''
import pytest


@pytest.fixture
def canonical_home(tmp_path):
    """Yields a private home root. A witness that re-declared `tmp_path` would test nothing."""
    yield tmp_path


@pytest.fixture
def {name}(monkeypatch, canonical_home):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(canonical_home / "home"))
    return canonical_home / "home"
'''

#: T017 / C-012(5). The **keyed** def and the **innermost** def differ. The outer def carries the
#: silhouette and is a ``fixture``; the inner def carries the write and is a ``helper``. Identity
#: is taken at the innermost (``{name}._apply``), ``kind`` at the keyed (outermost satisfying) def.
_OUTERMOST_VERSUS_INNERMOST = '''
import pytest


@pytest.fixture
def {name}(tmp_path, monkeypatch):
    def _apply():
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))

    _apply()
    return tmp_path / "home"
'''

#: SC-013. A deliberate ``SyntaxError``: the ``def`` has no colon. ``parse_module`` propagates and
#: nothing on the guard's call path catches it. Never checked in — ``ruff check`` would report
#: ``invalid-syntax``, which is not a rule code and cannot be per-file-ignored.
_DELIBERATE_SYNTAX_ERROR = '''
def this_line_has_no_colon(tmp_path, monkeypatch)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
'''


#: The two members that model ``E`` (FR-004): the canonical owner's own pin (FR-005) and FR-011's
#: retained-pin probe, which must keep its own ``setenv`` to prove the owner never wins. They are
#: ordinary members — ``E`` exempts them from the CENSUS, never from the WALK — so holding them out
#: of the census is what makes ``discovered == census u E`` a union that does work.
_EXEMPT_PROBES = '''
import pytest


@pytest.fixture
def owner_pins_its_own_home(tmp_path, monkeypatch):
    """Models the canonical owner's own pin — exempt by name, not by shape."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


@pytest.fixture
def retained_pin_probe(tmp_path, monkeypatch):
    """Models FR-011's probe: it KEEPS its setenv, to prove the owner never wins."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    return tmp_path
'''


def materialise(root: Path, sources: dict[str, str], sites: frozenset[tuple[str, str]]) -> SyntheticTree:
    """Write ``sources`` under ``root`` and describe the result.

    ``sources`` maps a POSIX relpath to a source string; parent directories are created. The
    returned :class:`SyntheticTree` carries the caller's **hand-enumerated** expectations
    unchanged — this function never inspects what it wrote.
    """
    _write(root, sources)
    return SyntheticTree(root=root, files=frozenset(sources), sites=sites)


def _write(root: Path, sources: dict[str, str]) -> None:
    """Write every ``relpath -> source`` pair under ``root``, creating parents."""
    root.mkdir(parents=True, exist_ok=True)
    for relpath, source in sources.items():
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")


def _extend(
    tree: SyntheticTree, sources: dict[str, str], sites: frozenset[tuple[str, str]]
) -> SyntheticTree:
    """Add files to an already-materialised tree, unioning both hand-enumerated descriptions."""
    _write(tree.root, sources)
    return SyntheticTree(
        root=tree.root,
        files=tree.files | frozenset(sources),
        sites=tree.sites | sites,
    )


def census_frozen_tree(root: Path) -> SyntheticTree:
    """The base tree: three members over three files, plus two files holding none.

    This is the tree the census is frozen against, so transitions (1), (2), (5) and (7) and the
    whole of T018 read against a fixed, hand-known member set.
    """
    return materialise(
        root,
        {
            "test_alpha.py": _PINNING_FIXTURE.format(name="pinned_home"),
            "pkg/test_beta.py": _PINNING_TEST_BODY.format(name="test_beta_pins_the_home"),
            "pkg/test_gamma.py": _PINNING_FIXTURE.format(name="gamma_home"),
            "pkg/test_exempt_probes.py": _EXEMPT_PROBES,
            "pkg/helpers.py": _NON_MEMBER_HELPER,
            "quiet.py": _MEMBERLESS_MODULE,
        },
        frozenset(
            {
                ("test_alpha.py", "pinned_home"),
                ("pkg/test_beta.py", "test_beta_pins_the_home"),
                ("pkg/test_gamma.py", "gamma_home"),
                ("pkg/test_exempt_probes.py", "owner_pins_its_own_home"),
                ("pkg/test_exempt_probes.py", "retained_pin_probe"),
            }
        ),
    )


def extra_member_in_an_existing_file(root: Path) -> SyntheticTree:
    """SC-006(3): a 41st member **anywhere** — here appended to a file the census already knows."""
    tree = census_frozen_tree(root)
    extra = root / "pkg" / "test_beta.py"
    extra.write_text(
        extra.read_text(encoding="utf-8")
        + textwrap.dedent(_PINNING_TEST_BODY.format(name="test_beta_pins_a_second_home")).lstrip(),
        encoding="utf-8",
    )
    return SyntheticTree(
        root=tree.root,
        files=tree.files,
        sites=tree.sites | {("pkg/test_beta.py", "test_beta_pins_a_second_home")},
    )


def extra_member_under_a_novel_name(root: Path) -> SyntheticTree:
    """SC-006(4): a 41st under a name used nowhere else, in a file the census has never seen.

    The name matters. A guard keyed on a name it already knows could absorb (3) and still miss
    this; the novel name is what separates "the count changed" from "this row is new".
    """
    return _extend(
        census_frozen_tree(root),
        {"pkg/test_delta.py": _PINNING_FIXTURE.format(name="unshared_pin_name_qhbxk")},
        frozenset({("pkg/test_delta.py", "unshared_pin_name_qhbxk")}),
    )


def owner_requesting_witness_tree(root: Path) -> SyntheticTree:
    """SC-006(6): a 41st that **also requests the owner AND restates the pin**, with no ``tmp_path``."""
    return _extend(
        census_frozen_tree(root),
        {"pkg/test_owner_witness.py": _OWNER_REQUESTING_WITNESS.format(name="owner_restates_the_pin")},
        frozenset({("pkg/test_owner_witness.py", "owner_restates_the_pin")}),
    )


def colliding_pair_tree(root: Path) -> SyntheticTree:
    """SC-006(8): two members in **DIFFERENT files** whose **bare** ``composite_key`` is identical.

    Same fixture name, byte-identical pin line: ``enclosing_qualname`` agrees and
    ``normalized_token_line`` agrees because ``code_tokens_by_line`` strips the string literals.
    Only the ``relpath`` component separates them — which is precisely the C-012 interpretation
    transition (8) exists to keep pinned. Nobody produces this shape by accident.
    """
    return materialise(
        root,
        {
            "one/test_collide.py": _PINNING_FIXTURE.format(name="pinned_home"),
            "two/test_collide.py": _PINNING_FIXTURE.format(name="pinned_home"),
        },
        frozenset({("one/test_collide.py", "pinned_home"), ("two/test_collide.py", "pinned_home")}),
    )


def syntax_error_tree(root: Path) -> SyntheticTree:
    """SC-013: the base tree plus one module that cannot be parsed.

    ``sites`` is empty because the pass never completes — it raises. The field is not "the members
    you would find"; it is "what the tree was built to contain", and this tree was built to
    contain a raise.
    """
    return _extend(census_frozen_tree(root), {"pkg/test_broken.py": _DELIBERATE_SYNTAX_ERROR}, frozenset())


def outermost_versus_innermost_tree(root: Path) -> SyntheticTree:
    """C-012(5)'s SYNTHETIC witness: keyed def and innermost def differ, on purpose.

    Without this tree both of C-004's discriminators rest on a single real-tree site (``:1165``),
    held in the class by an unused ``monkeypatch`` parameter that ``ruff``'s relaxed ``ARG`` for
    ``tests/**`` will not defend — so a routine cleanup silently disarms the mechanisation.
    """
    return materialise(
        root,
        {"test_layered.py": _OUTERMOST_VERSUS_INNERMOST.format(name="layered_home")},
        frozenset({("test_layered.py", "layered_home._apply")}),
    )


def member_under_a_fixture_root_tree(root: Path) -> SyntheticTree:
    """T015(4)'s POSITIVE CONTROL: a member that **does** live under a test-owned fixture root.

    The counterpart assertion — "no member of the real tree lives under a fixture root" — is a
    population-0 claim, and a matcher that sees nothing satisfies it forever. This tree is what
    proves the matcher can see.
    """
    return materialise(
        root,
        {"fixtures/test_planted.py": _PINNING_FIXTURE.format(name="planted_home")},
        frozenset({("fixtures/test_planted.py", "planted_home")}),
    )
