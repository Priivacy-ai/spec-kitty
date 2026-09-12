"""The owner never wins — the exempt member probe, and the control that makes the claim bite.

WP03/T013 + T014 (R1a). Binding contract:
``kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/contracts/canonical-home-owner.md`` §3a.

**SC-012 limb 2 AS SPECIFIED CANNOT FAIL, and that is recorded here as a spec finding rather than
silently repaired.** FR-005 forces the owner to pin ``str(tmp_path / "home")``; any member of the
behaviour class pins ``str(tmp_path / "home")``; ``tmp_path`` is function-scoped and **shared**
within a test. So inside one test those two strings are *the same string*, and the criterion's
*"fails if the owner's value is seen"* has nothing to distinguish. :func:`test_the_retained_pin_
probe_observes_its_own_value` is green **whether the owner won or lost**.

The repair is the second probe, and the pair is the point:

* **Probe (a)** — :func:`retained_pin_home`. Pins ``str(tmp_path / "home")``. It **is** a member of
  the behaviour class and therefore spends **one of ``E``'s two irrevocable, hash-pinned slots**.
  FR-011 mandates it, C-007 forbids widening the carve-out that pays for it, and that cost is this
  Mission's most irreversible decision. **Do not spend the second slot.**
* **Probe (b)** — :func:`probe_home_pin`. Pins ``str(tmp_path / "probe-home")``, **a value the
  owner can never produce**. It resolves to ``<tmp_path>/probe-home``, is therefore **not** a class
  member, costs **no slot**, and is **the only assertion in the pair that can be falsified**.
  Delete it and this module greens for an owner that overwrites every module's pin — the failure
  ``tests/conftest.py:272-286`` records having cost ~16 ``tests/sync`` cases.

Why the pin lives in a FIXTURE and not in a test body
------------------------------------------------------
Fixture setup completes **before** the test body runs, so a body-level ``monkeypatch.setenv`` wins
by ordering **unconditionally** and proves nothing about the *fixture-versus-fixture* precedence
decision at ``tests/conftest.py:272-286`` that this limb exists to demonstrate. Both probes
therefore declare their pin in a module-local fixture that **requests the owner as its first
parameter** — the required declaration order, asserted mechanically by
:func:`test_both_probes_request_the_owner_before_pinning`, not merely stated in this docstring.

``E`` is declared here-adjacent, in ``_home_pin_exempt.py``
------------------------------------------------------------
``E``'s two keys are determined by this WP's own two artefacts and nothing else: the canonical
owner (T011) and probe (a) above. WP04 tests the exemption **mechanism**; WP05 asserts the **real**
hash and runs mypy over the declaring module. No package edits another's.

No ``ast.parse`` and no ``NodeVisitor``: this module imports ``_home_pin_scan``, so WP02's seam
guard polices it, and every parse routes through :func:`_home_pin_scan.parse_module`.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from tests.architectural import _home_pin_exempt as exempt
from tests.architectural import _home_pin_scan as scan
from tests.architectural._ratchet_keys import composite_key_from_file

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"
SELF_RELPATH = Path(__file__).resolve().relative_to(TESTS_ROOT).as_posix()
CONFTEST_RELPATH = "conftest.py"

#: The owner's name, taken from the same contract T012 parses — never re-typed as a literal here.
OWNER_NAME = "canonical_home"

#: Probe (b)'s discriminating value: a leaf the owner is structurally incapable of producing,
#: because FR-005 pins the owner to ``home``.
PROBE_LEAF = "probe-home"


# ---------------------------------------------------------------------------
# T013(a) — THE E-SLOT MEMBER
# ---------------------------------------------------------------------------


@pytest.fixture
def retained_pin_home(canonical_home: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    """Probe (a): a module-local fixture keeping its OWN pin, declared after the owner.

    **This fixture is a member of the behaviour class and holds one of ``E``'s two slots.** It
    requests ``canonical_home`` first, so the owner's setup completes before this ``setenv`` runs —
    the fixture-versus-fixture ordering the precedence decision at ``tests/conftest.py:272-286`` is
    about. A body-level pin would win by ordering unconditionally and demonstrate nothing.
    """
    assert canonical_home is None
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    return str(home)


def test_the_retained_pin_probe_observes_its_own_value(
    retained_pin_home: str, tmp_path: Path
) -> None:
    """SC-012 limb 2, as literally specified — **and it cannot fail. See the module docstring.**

    The owner pins ``str(tmp_path / "home")`` and this probe pins ``str(tmp_path / "home")`` from
    the SAME function-scoped ``tmp_path``: within one test they are the same string, so this
    assertion is green whether the owner won or lost. It ships because FR-011 mandates the member
    probe and SC-012 states the limb; :func:`test_the_negative_control_probe_observes_its_own_
    differing_value` is what makes the claim bite.
    """
    assert os.environ[scan.NEEDLE] == retained_pin_home == str(tmp_path / "home")


# ---------------------------------------------------------------------------
# T013(b) — THE DISCRIMINATING NEGATIVE CONTROL
# ---------------------------------------------------------------------------


@pytest.fixture
def probe_home_pin(canonical_home: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    """Probe (b): the same shape, pinning a value the owner can never produce.

    **Not a class member** — it resolves to ``<tmp_path>/probe-home``, never
    ``<tmp_path>/home`` — so it costs no ``E`` slot while carrying the whole falsifiability of the
    pair.
    """
    assert canonical_home is None
    home = tmp_path / PROBE_LEAF
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    return str(home)


def test_the_negative_control_probe_observes_its_own_differing_value(
    probe_home_pin: str, tmp_path: Path
) -> None:
    """**The only assertion in the pair that can be falsified.**

    An owner that overwrote every requesting module's pin — the ``setattr(Path, "home", ...)``
    shape that silently won over ~16 ``tests/sync`` cases — reds exactly here and nowhere else in
    this module.
    """
    assert probe_home_pin == str(tmp_path / PROBE_LEAF)
    assert os.environ[scan.NEEDLE] == probe_home_pin
    assert os.environ[scan.NEEDLE] != str(tmp_path / "home"), (
        "the owner's value is being observed by a probe that kept its own pin — the owner is "
        "winning, which FR-006 forbids and `tests/conftest.py:272-286` records the cost of"
    )


def test_both_probes_request_the_owner_before_pinning() -> None:
    """The required declaration order, asserted over this module's own source.

    Stated in the module docstring AND checked, because the docstring is what a future edit moving
    a pin into a test body would leave untouched. Every fixture in this module that writes a
    ``SPEC_KITTY_HOME`` pin must name the owner as its **first** parameter.
    """
    tree = scan.parse_module(Path(__file__).resolve())
    pin_lines = {site.lineno for site in scan.find_write_sites(tree, key=scan.NEEDLE)}
    assert pin_lines, "this module has stopped pinning anything — both probes have gone vacuous"
    enclosing = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(node.lineno <= line <= (node.end_lineno or node.lineno) for line in pin_lines)
    }
    assert set(enclosing) == {"retained_pin_home", "probe_home_pin"}, (
        "a SPEC_KITTY_HOME pin appeared outside the two declared probe fixtures — a pin in a test "
        "BODY wins by ordering unconditionally and proves nothing about fixture-vs-fixture "
        "precedence, and any third pinning fixture is a third class member with no E slot to hold it"
    )
    first_params = {
        name: (node.args.args[0].arg if node.args.args else None)
        for name, node in enclosing.items()
    }
    assert first_params == {"retained_pin_home": OWNER_NAME, "probe_home_pin": OWNER_NAME}


# ---------------------------------------------------------------------------
# T013 accounting — which probe costs a slot, constructed rather than asserted
# ---------------------------------------------------------------------------


def test_only_probe_a_is_a_class_member_so_probe_b_costs_no_slot() -> None:
    """Probe (b)'s non-membership is CONSTRUCTED from the production classifier, not assumed.

    If probe (b) ever became a member, ``E`` would need a third entry — which fixed arity makes a
    ``mypy --strict`` error and C-007 forbids widening. This is where that reds, in the package
    that wrote it, rather than in WP05's ``discovered == census u E`` accounting.
    """
    mine = {
        member.resolved_value
        for member in scan.discover(TESTS_ROOT)
        if member.relpath == SELF_RELPATH
    }
    assert mine == {scan.TMP_PATH_HOME}, (
        "exactly one member is expected in this module — probe (a). Probe (b) resolves to "
        f"{scan.TMP_PATH}/{PROBE_LEAF} and must never be classified"
    )


# ---------------------------------------------------------------------------
# T014 — E, content-addressed, with its linenos taken from discover() AT RUNTIME
# ---------------------------------------------------------------------------


def _members_in(relpath: str) -> set[scan.Member]:
    return {member for member in scan.discover(TESTS_ROOT) if member.relpath == relpath}


def test_the_exempt_set_names_the_owner_and_the_retained_pin_probe() -> None:
    """``E``'s two entries are exactly this WP's own two artefacts, keyed by their relpaths."""
    assert {entry.key[0] for entry in exempt.E} == {CONFTEST_RELPATH, SELF_RELPATH}
    assert {entry.key[1] for entry in exempt.E} == {OWNER_NAME, "retained_pin_home"}
    assert all(entry.why for entry in exempt.E), "every entry carries its prose, which entitles nothing"


def test_every_exempt_key_is_recomputable_from_the_file_at_a_runtime_lineno() -> None:
    """T014(4): each key is content-addressed, and **the lineno comes from ``discover()``**.

    The entry's own key is deliberately **not** used to select the line. For each entry, every
    member ``discover()`` reports in that file contributes its **runtime** lineno; the key is
    recomputed from the file at each of those linenos, and the declared key must be among the
    results. A hand-typed key that no longer matches the source reds here — which is what makes
    this content-addressing rather than a literal restated twice.

    No line number is written down anywhere in ``_home_pin_exempt.py``; a module-level
    ``(rel, int, ...)`` seed is exactly the shape
    ``test_ratchet_positional_anchor_ban.py::test_no_int_line_sink_in_architectural_python_seeds``
    flags under its #2564 clause.
    """
    for entry in exempt.E:
        relpath = entry.key[0]
        path = TESTS_ROOT / relpath
        recomputed = {
            (member.relpath, *composite_key_from_file(path, member.lineno))
            for member in _members_in(relpath)
        }
        assert entry.key in recomputed, (
            f"exempt key {entry.key} is not recomputable from {relpath} at any lineno "
            f"discover() reports there; live keys: {sorted(recomputed)}"
        )


def test_the_recomputation_can_tell_a_wrong_key_apart() -> None:
    """Positive control for the check above — an empty or blind comparison would also 'pass'.

    A key with a mutated qualname must NOT be recomputable. Without this, the assertion above is
    indistinguishable from one comparing a set against itself.
    """
    entry = exempt.E[0]
    relpath = entry.key[0]
    path = TESTS_ROOT / relpath
    recomputed = {
        (member.relpath, *composite_key_from_file(path, member.lineno))
        for member in _members_in(relpath)
    }
    assert recomputed, "the recomputation produced nothing — it cannot see, so it cannot bite"
    forged = (entry.key[0], f"{entry.key[1]}_not_a_real_qualname", entry.key[2])
    assert forged not in recomputed


def test_the_exempt_set_is_a_subset_of_the_discovered_class() -> None:
    """T014(4): ``{e.key for e in E} subset {m.key for m in discover(tests)}``.

    An ``E`` entry naming a **phantom** definition would inflate ``census u E`` and be caught only
    in WP05. It is caught here, in the package that wrote it.
    """
    declared = {entry.key for entry in exempt.E}
    discovered = {member.key for member in scan.discover(TESTS_ROOT)}
    assert declared <= discovered, (
        f"exempt entries naming no discovered member: {sorted(declared - discovered)}"
    )


def test_the_owner_and_the_probe_are_the_only_members_of_their_two_files() -> None:
    """Exact accounting over the two files ``E`` covers — a set equality, never a count.

    A third member appearing in either file would need a third ``E`` entry, which fixed arity
    makes a type error and C-007 forbids carving out. This is that accounting at the point it can
    still be fixed cheaply.
    """
    declared = {entry.key for entry in exempt.E}
    live = {
        member.key
        for member in scan.discover(TESTS_ROOT)
        if member.relpath in {CONFTEST_RELPATH, SELF_RELPATH}
    }
    assert live == declared
