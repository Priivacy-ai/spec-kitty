"""The R1a guard: the eight SC-006 transitions, SC-004, SC-013, and the ``E`` mechanism (WP04).

Everything here runs over **materialised** trees and **materialised** census/baseline artefacts, so
this package is green on its own branch without WP03 and without WP05. The real-tree
``discovered == census u E`` assertion is deliberately **not** here — it is WP05's, and that is
what buys the parallelism (FR-009).

The verdict itself lives in ``_home_pin_verdict.py``
-----------------------------------------------------
This module holds the **trees, the artefact doctoring and the assertions**; the comparison it
asserts over — :func:`~tests.architectural._home_pin_verdict.evaluate` and the census/hash/tombstone
semantics — is a shared primitive with three consumers (WP04 proves it, WP05 applies it to the real
tree, R1b drives its tombstone path) and lives in its own seam. Keeping it here would have left a
peer package importing a leaf ``test_*.py`` to reach a non-test function, which is a **DIR-001**
boundary violation and a dependency inversion. **Moving it must not move the teeth**: every mutation
in WP04's red-first campaign is re-run against the extracted seam and reds the same named assertion.

The guard is TWO limbs, and both are load-bearing
--------------------------------------------------
``discovered == census u E`` alone does **not** close SC-006. Transition (7) — a 41st member
**accompanied by a new census row** — satisfies the equality by construction: the absorption path
walks straight through it. What refuses the addition is the second limb, the **key-set hash pinned
in the baseline**, which no census edit can restore. So ``evaluate`` returns both, and (7) is red on
the hash while the equality is clean. Six of the eight transitions are equality reds, (7) is a hash
red, and (2) is the green.

Why the hash is over the KEY SET and not the file bytes
--------------------------------------------------------
``sha256(path.read_bytes())`` passes any "a hash exists" review and fails on day thirty: it moves
under an ``owed_to`` re-point and under a comment edit, neither of which touches the key set the
ratchet compares. T018(ii) therefore requires **all four** cases — the two legitimate edits must
**PASS** as firmly as the two illegitimate ones must red. A blanket "touching both reds" rule would
satisfy the reds and **forbid R1b's entire job**.

And the tombstone path is asymmetric, on purpose
-------------------------------------------------
A census row removed **with** a matching tombstone passes (that is R1b adjudicating a member away);
the same removal **without** one reds. ``E`` gets **no tombstone path at all** — any delta to ``E``
or its hash reds unconditionally, because ``E`` never legitimately changes in R1a or R1b.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.architectural import _home_pin_scan as scan
from tests.architectural import _home_pin_synthetic as synthetic
from tests.architectural._home_pin_verdict import (
    add_row,
    census_keys,
    drop_row,
    edit_header,
    evaluate,
    with_rows,
    with_tombstones,
)

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]

#: ``E`` at its shipped arity. ``scan.ExemptSet`` also admits ``tuple[()]`` — the empty alternative
#: WP01 needs to demonstrate ``--exempt-module`` absent — so indexing an ``ExemptSet`` is a
#: ``mypy --strict`` error. Naming the pair separately is what lets the co-edit limbs below take
#: ``exempt[0]`` and ``exempt[1]`` without a suppression, and it is the same fixed-arity discipline
#: the mypy limb (T018(i)) exists to enforce on the real ``E``.
ExemptPair = tuple[scan.Exempt, scan.Exempt]

#: A materialised tree with its matching census, baseline and ``E``.
FrozenTree = tuple[Path, str, str, ExemptPair]

#: The census header's ``frozen_at_sha``. A synthetic tree has no commit, and the value is a header
#: scalar the key-set hash never covers — which is exactly what T018(ii)'s header-edit case proves.
SYNTHETIC_SHA = "0" * 40

#: ``render_census`` refuses anything that is not ``^#[0-9]+$``.
OWED_TO = "#3121"

#: The two members of the base tree that model ``E``: the canonical owner's own pin and FR-011's
#: retained-pin probe. Holding them OUT of the census is what makes ``census u E`` load-bearing —
#: an ``E`` that never participates in the union is decoration, and every transition would still
#: pass with the union deleted.
EXEMPT_SITES: frozenset[tuple[str, str]] = frozenset(
    {
        ("pkg/test_exempt_probes.py", "owner_pins_its_own_home"),
        ("pkg/test_exempt_probes.py", "retained_pin_probe"),
    }
)


def freeze_census(root: Path, *, owed_to: str = OWED_TO) -> str:
    """The census as it would be frozen for ``root``, minus the rows ``E`` carries."""
    rows = [m for m in scan.discover(root) if (m.relpath, m.key[1]) not in EXEMPT_SITES]
    return scan.render_census(rows, sha=SYNTHETIC_SHA, owed_to=owed_to)


def freeze_baseline(root: Path, exempt: scan.ExemptSet) -> str:
    """The baseline pinning the census key set and ``E``'s key set for ``root``."""
    rows = [m for m in scan.discover(root) if (m.relpath, m.key[1]) not in EXEMPT_SITES]
    return scan.render_baseline(rows, exempt=exempt)


def exempt_set_for(root: Path) -> ExemptPair:
    """``E`` for a materialised tree: the two designated members, typed ``tuple[Exempt, Exempt]``.

    The arity is the type's, not this function's — see the mypy limb (T018(i)), which is the only
    thing standing between SC-005 and nothing at all, because CI type-checks no part of ``tests/``.
    """
    by_site = {(m.relpath, m.key[1]): m for m in scan.discover(root)}
    owner = by_site[("pkg/test_exempt_probes.py", "owner_pins_its_own_home")]
    probe = by_site[("pkg/test_exempt_probes.py", "retained_pin_probe")]
    return (
        scan.Exempt(key=owner.key, why="the canonical home owner's own pin (FR-005)"),
        scan.Exempt(key=probe.key, why="FR-011's retained-pin probe, which must keep its setenv"),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def frozen(tmp_path: Path) -> FrozenTree:
    """The census-frozen base tree with its matching census, baseline and ``E``.

    Every tree gets its **own** root: ``_home_pin_scan._corpus`` is ``lru_cache``d on the root PATH
    and not on its contents, so a re-materialisation under a reused root would be handed the first
    parse back.
    """
    root = tmp_path / "frozen"
    synthetic.census_frozen_tree(root)
    exempt = exempt_set_for(root)
    return root, freeze_census(root), freeze_baseline(root, exempt), exempt


# ---------------------------------------------------------------------------
# T016 — the EIGHT SC-006 transitions. Count them: there are eight.
# ---------------------------------------------------------------------------


def test_transition_2_the_census_frozen_tree_greens(
    frozen: FrozenTree,
) -> None:
    """(2) The frozen tree GREENS — attesting **FREEZING**, and asserting nothing about desert.

    Placed first because it is the control every other transition is differential against: without
    a demonstrated green, "the guard reds on X" is satisfied by a guard that reds on everything.
    """
    root, census, baseline, exempt = frozen
    verdict = evaluate(root, census, baseline, exempt)
    assert verdict.ok, f"the frozen tree must green, got {verdict}"


def test_transition_1_an_empty_census_reds(
    frozen: FrozenTree,
) -> None:
    """(1) An empty census REDS — every non-exempt member becomes unexpected."""
    root, census, baseline, exempt = frozen
    emptied = with_rows(census, [])
    verdict = evaluate(root, emptied, baseline, exempt)
    assert not verdict.ok
    assert verdict.unexpected == census_keys(census), (
        "an empty census must surface every censused member as unexpected"
    )


def test_transition_3_a_41st_member_anywhere_reds(tmp_path: Path) -> None:
    """(3) A 41st member ANYWHERE reds — here appended to a file the census already knows.

    The file is not new and the name is not novel, so nothing but the member itself has changed.
    """
    frozen_root = tmp_path / "frozen"
    synthetic.census_frozen_tree(frozen_root)
    exempt = exempt_set_for(frozen_root)
    census, baseline = freeze_census(frozen_root), freeze_baseline(frozen_root, exempt)

    grown = tmp_path / "grown"
    tree = synthetic.extra_member_in_an_existing_file(grown)
    verdict = evaluate(tree.root, census, baseline, _rebased(exempt, tree.root))
    assert not verdict.ok
    assert {key[1] for key in verdict.unexpected} == {"test_beta_pins_a_second_home"}


def test_transition_4_a_41st_under_a_name_used_nowhere_else_reds(tmp_path: Path) -> None:
    """(4) A 41st under a name used NOWHERE ELSE reds, in a file the census has never seen.

    Distinct from (3): a guard that absorbed by filename, or that keyed on a name it already knew,
    could pass (3) and miss this.
    """
    frozen_root = tmp_path / "frozen"
    synthetic.census_frozen_tree(frozen_root)
    exempt = exempt_set_for(frozen_root)
    census, baseline = freeze_census(frozen_root), freeze_baseline(frozen_root, exempt)

    grown = tmp_path / "grown"
    tree = synthetic.extra_member_under_a_novel_name(grown)
    verdict = evaluate(tree.root, census, baseline, _rebased(exempt, tree.root))
    assert not verdict.ok
    assert {key[1] for key in verdict.unexpected} == {"unshared_pin_name_qhbxk"}


def test_transition_5_a_removed_row_with_the_definition_still_present_reds(
    frozen: FrozenTree,
) -> None:
    """(5) A row removed while its DEFINITION REMAINS reds — on both limbs, and that is the point.

    The equality catches it because the member is still discovered; the hash catches it because no
    tombstone was filed. Deleting the row is the cheapest way to make a census green, and it is the
    edit this transition exists to refuse.
    """
    root, census, baseline, exempt = frozen
    victim = sorted(census_keys(census))[0]
    verdict = evaluate(root, drop_row(census, victim), baseline, exempt)
    assert not verdict.ok
    assert verdict.unexpected == {victim}
    assert not verdict.census_hash_ok, "a row removed without a tombstone must red the hash limb"


def test_transition_6_a_41st_requesting_the_owner_and_restating_the_pin_reds(
    monkeypatch: pytest.MonkeyPatch,
    canonical_home: Path,
) -> None:
    """(6) A 41st that ALSO REQUESTS THE OWNER **and RESTATES THE PIN** reds (FR-010).

    **This witness is declared ``(monkeypatch, canonical_home)`` with NO ``tmp_path``** — modelled
    on the live population-1 ``runtime_home`` shape, never on the ``None``-returning canonical
    owner, which could not be written from. A witness that gratuitously re-declared ``tmp_path``
    would test nothing FR-010 is for: the member under test fails the naive predicate on **two**
    limbs at once (no ``tmp_path`` in the silhouette, no ``tmp_path`` in the value) and is caught
    only because ``OWNER_PARAM_NAMES`` counts the owner parameter as ``tmp_path`` for both.

    ``monkeypatch`` is **load-bearing here, not decorative**. The verdict is re-taken with the
    ambient pin removed from the environment, asserting the classifier reads FILES and never the
    process environment — so a future implementation that consulted ``os.environ`` to decide
    membership reds here. An unused ``monkeypatch`` parameter is exactly the fragility C-012(5)
    records at ``:1165``, held in the class by a parameter ``ruff``'s relaxed ``ARG`` for
    ``tests/**`` will not defend.
    """
    frozen_root = canonical_home / "frozen"
    synthetic.census_frozen_tree(frozen_root)
    exempt = exempt_set_for(frozen_root)
    census, baseline = freeze_census(frozen_root), freeze_baseline(frozen_root, exempt)

    grown = canonical_home / "grown"
    tree = synthetic.owner_requesting_witness_tree(grown)
    rebased = _rebased(exempt, tree.root)
    verdict = evaluate(tree.root, census, baseline, rebased)
    assert not verdict.ok
    assert {key[1] for key in verdict.unexpected} == {"owner_restates_the_pin"}

    intruder = next(m for m in scan.discover(tree.root) if m.key[1] == "owner_restates_the_pin")
    assert "tmp_path" not in _declared_params(tree.root, intruder), (
        "the 41st must declare NO tmp_path of its own — it is caught only because the owner "
        "parameter is normalised to tmp_path, which is the escape FR-010 exists to close"
    )

    monkeypatch.delenv(scan.NEEDLE, raising=False)
    assert evaluate(tree.root, census, baseline, rebased) == verdict, (
        "the verdict moved when the ambient pin was removed — the classifier must read FILES, "
        "never the process environment"
    )


def test_transition_7_a_41st_accompanied_by_a_new_census_row_still_reds(tmp_path: Path) -> None:
    """(7) A 41st **ACCOMPANIED BY a new census row** STILL reds — the absorption path.

    None of the first six touches this. The equality limb is **clean** here by construction: the
    row was added precisely so that ``discovered == census u E`` holds. What refuses it is the
    pinned key-set hash, and no census edit can restore that — additions are **structurally
    impossible**, not merely discouraged.
    """
    frozen_root = tmp_path / "frozen"
    synthetic.census_frozen_tree(frozen_root)
    exempt = exempt_set_for(frozen_root)
    census, baseline = freeze_census(frozen_root), freeze_baseline(frozen_root, exempt)

    grown = tmp_path / "grown"
    tree = synthetic.extra_member_in_an_existing_file(grown)
    rebased = _rebased(exempt, tree.root)
    intruder = next(
        m.key for m in scan.discover(tree.root) if m.key[1] == "test_beta_pins_a_second_home"
    )
    absorbed = add_row(census, intruder)

    verdict = evaluate(tree.root, absorbed, baseline, rebased)
    assert verdict.unexpected == frozenset(), "the row was added so the equality would be clean"
    assert verdict.stale == frozenset()
    assert not verdict.census_hash_ok, (
        "absorbing a new member by adding a census row must still red — on the hash limb"
    )
    assert not verdict.ok


def test_transition_8_removing_one_of_a_colliding_pair_reds(tmp_path: Path) -> None:
    """(8) Removing one of a COLLIDING PAIR reds — two members, DIFFERENT files, one bare key.

    **The single cheapest test that catches the 19-key collapse, and the only one that keeps it
    caught.** Without it the C-012 interpretation is unpinned and can be reverted with the other
    seven still green.

    The first assertion is the instrument check: it proves the pair really does collide on the bare
    2-tuple. A tree that quietly stopped colliding would make the rest of this test green for the
    wrong reason.
    """
    root = tmp_path / "colliding"
    synthetic.colliding_pair_tree(root)
    members = sorted(scan.discover(root), key=lambda m: m.key)
    bare = {key[1:] for key in (m.key for m in members)}
    assert bare == {("pinned_home", 'monkeypatch . setenv ( , str ( tmp_path / ) )')}, (
        f"the pair no longer collides on the BARE composite_key — got {sorted(bare)}. "
        f"Transition (8) tests nothing unless the collision is real."
    )
    assert members[0].key != members[1].key, "the 3-tuple must still separate them by relpath"
    assert members[0].key[0] != members[1].key[0], "and it separates them on the RELPATH component"

    census = scan.render_census(members, sha=SYNTHETIC_SHA, owed_to=OWED_TO)
    baseline = scan.render_baseline(members, exempt=())
    assert evaluate(root, census, baseline, ()).ok, "the colliding pair must green while intact"

    verdict = evaluate(root, drop_row(census, members[0].key), baseline, ())
    assert not verdict.ok
    assert verdict.unexpected == {members[0].key}, (
        "under a BARE 2-tuple key the two members collapse to one, the census still 'contains' the "
        "survivor, and this removal greens — which is the 19-key collapse"
    )


@pytest.fixture
def canonical_home(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """A fixture that **YIELDS a home root** — the FR-010 owner shape, in this module's own idiom.

    Transition (6)'s witness requests ``(monkeypatch, canonical_home)`` and declares **no
    ``tmp_path``**, which is the shape SC-006(6) names. Modelled on the live population-1
    ``runtime_home`` fixture, **not** on the ``None``-returning canonical owner — a witness
    requesting that could not restate the pin from its value, because there is no value.

    The name is deliberate: ``canonical_home`` is in ``OWNER_PARAM_NAMES``, so the witness's own
    parameter union normalises to ``{monkeypatch, tmp_path}``. The witness is nonetheless **not** a
    member of the real tree — it writes no literal ``"SPEC_KITTY_HOME"`` pin — and that separation
    is what keeps this module out of WP05's ``discovered == census u E``.
    """
    yield tmp_path_factory.mktemp("canonical_home")


def _declared_params(root: Path, member: scan.Member) -> frozenset[str]:
    """The member's def chain's parameter union **as written**, before FR-010 normalisation.

    ``Member.params`` is already normalised, so it cannot answer "did this member declare
    ``tmp_path`` itself?" — which is exactly the question transition (6) turns on.
    """
    tree = scan.parse_module(root / member.relpath)
    chain = scan.def_chain(tree, member.lineno)
    return frozenset().union(*(scan.def_params(node) for node in chain))


def _rebased(exempt: ExemptPair, root: Path) -> ExemptPair:
    """``E`` re-resolved against another materialisation of the same base tree.

    The two exempt members carry identical keys in every tree built from ``census_frozen_tree``
    (the key is content-addressed — relpath, qualname, normalised token line — and none of the
    three moves), so this is an identity in practice. It is spelled out rather than assumed so a
    builder change that DID move them reds here instead of silently emptying ``E``.
    """
    resolved = exempt_set_for(root)
    assert {e.key for e in resolved} == {e.key for e in exempt}, (
        "E's keys moved between materialisations of the same base tree — the transitions below "
        "would be comparing against an E that no longer names the same members"
    )
    return resolved


# ---------------------------------------------------------------------------
# T017 — SC-004, SC-013, and the SYNTHETIC outermost-versus-innermost witness
# ---------------------------------------------------------------------------


def test_sc004_the_guard_reds_on_a_stale_census_row(
    frozen: FrozenTree,
) -> None:
    """SC-004, as a PERMANENT test: a row is stale while every member is present, and the guard
    reds **ON THE ROW**.

    Not a red-first demonstration that leaves no artefact — the tree and the assertion ship.
    """
    root, census, baseline, exempt = frozen
    ghost: scan.MemberKey = ("pkg/test_vanished.py", "vanished_home", "monkeypatch . setenv ( )")
    haunted = add_row(census, ghost)
    verdict = evaluate(root, haunted, baseline, exempt)
    assert not verdict.ok
    assert verdict.stale == {ghost}, f"the guard must red ON THE ROW, got {verdict}"
    assert verdict.unexpected == frozenset(), "every real member is still present"


def test_the_comparison_is_set_equality_and_not_containment(tmp_path: Path) -> None:
    """SC-004's second half: a tree where ``discovered`` is a STRICT SUBSET of the census reds.

    The first assertion is the whole argument — it proves a **subset-only ratchet would GREEN
    here**. That ratchet is what §0.4 spends a page refusing, and it is the cheapest repair
    available to an implementer who cannot otherwise make SC-004 demonstrable.
    """
    frozen_root = tmp_path / "frozen"
    synthetic.census_frozen_tree(frozen_root)
    exempt = exempt_set_for(frozen_root)
    census, baseline = freeze_census(frozen_root), freeze_baseline(frozen_root, exempt)

    shrunk = tmp_path / "shrunk"
    synthetic.census_frozen_tree(shrunk)
    (shrunk / "pkg" / "test_gamma.py").write_text("VALUE = 1\n", encoding="utf-8")

    discovered = {m.key for m in scan.discover(shrunk)}
    known = census_keys(census) | {e.key for e in exempt}
    assert discovered < known, (
        "this tree must be a STRICT SUBSET of the frozen class, or it does not discriminate "
        "set equality from containment"
    )

    verdict = evaluate(shrunk, census, baseline, _rebased(exempt, shrunk))
    assert not verdict.ok, "a subset-only ratchet greens here; set equality must not"
    assert verdict.stale == known - discovered


def test_sc013_the_guard_reds_on_a_deliberate_syntax_error(tmp_path: Path) -> None:
    """SC-013, behaviourally: the ``SyntaxError`` propagates out of the guard's call path.

    ``except SyntaxError: continue`` narrows the walk with nothing firing and buys budget
    headroom — NFR-001's defeat wearing an exception handler.
    """
    root = tmp_path / "broken"
    synthetic.syntax_error_tree(root)
    empty_census = scan.render_census([], sha=SYNTHETIC_SHA, owed_to=OWED_TO)
    empty_baseline = scan.render_baseline([], exempt=())
    with pytest.raises(SyntaxError):
        evaluate(root, empty_census, empty_baseline, ())


def test_sc013_no_syntax_error_handler_exists_on_the_guard_call_path() -> None:
    """SC-013, by AST: neither the seam nor this module catches ``SyntaxError`` anywhere.

    Behavioural evidence alone would still pass if a handler were added *around* a different call;
    this asserts the construct is absent from both modules on the path.
    """
    for module in (scan.__file__, __file__, synthetic.__file__):
        tree = scan.parse_module(Path(module))
        handlers = scan.find_except_handlers(tree, exception="SyntaxError")
        assert handlers == set(), f"{Path(module).name} catches SyntaxError at line(s) {sorted(handlers)}"


def test_sc013_the_handler_matcher_bites_on_a_module_that_does_catch(tmp_path: Path) -> None:
    """The positive control for the assertion above — an empty set otherwise proves nothing."""
    planted = tmp_path / "catcher.py"
    planted.write_text(
        textwrap.dedent(
            '''
            def scan_them(paths):
                for path in paths:
                    try:
                        parse(path)
                    except SyntaxError:
                        continue
            '''
        ).lstrip(),
        encoding="utf-8",
    )
    handlers = scan.find_except_handlers(scan.parse_module(planted), exception="SyntaxError")
    assert handlers != set(), "the matcher must see a handler that is really there"


def test_c004_synthetic_outermost_versus_innermost_witness(tmp_path: Path) -> None:
    """C-012(5): a materialised member whose KEYED def and INNERMOST def differ.

    Both of C-004's discriminators otherwise rest on **one real-tree site** — ``:1165`` — held in
    the class by an unused ``monkeypatch`` parameter that ``ruff``'s relaxed ``ARG`` for
    ``tests/**`` will not defend, so a routine cleanup silently disarms the mechanisation. This
    tree takes C-004 off that single row.

    The discriminator is the ``kind`` DISTRIBUTION, not the key set (C-012(4)).
    """
    root = tmp_path / "layered"
    synthetic.outermost_versus_innermost_tree(root)
    (member,) = scan.discover(root)

    assert member.key[1] == "layered_home._apply", (
        "IDENTITY is taken at the INNERMOST def — keying at the attributed def is what gives the "
        "real tree a symmetric difference of 2 against the C-011 anchor, both at :1165"
    )
    assert member.kind == "fixture", "SHAPE is read at the KEYED (outermost satisfying) def"

    keyed = scan.kind_distribution(root, at="keyed")
    innermost = scan.kind_distribution(root, at="innermost")
    assert keyed != innermost, (
        "the witness does not discriminate: keyed and innermost readings agree, so an implementer "
        "who attributed to the innermost def would still green"
    )
    assert keyed == {"fixture": 1, "test-body": 0, "helper": 0}
    assert innermost == {"fixture": 0, "test-body": 0, "helper": 1}


# ---------------------------------------------------------------------------
# T018 — the E mechanism: arity, hash placement, and the co-edit asymmetry
# ---------------------------------------------------------------------------

_ARITY_PROBE = '''
from __future__ import annotations

from tests.architectural._home_pin_scan import Exempt

E: tuple[Exempt, Exempt] = (
{entries}
)
'''

_ARITY_ENTRY = '    Exempt(key=("f{n}.py", "q{n}", "t{n}"), why="entry {n}"),'


def _run_mypy(tmp_path: Path, entries: int) -> subprocess.CompletedProcess[str]:
    """Invoke mypy as ``[sys.executable, '-m', 'mypy']`` — **never a bare ``mypy`` from PATH**.

    CI runs under ``uv run``, where PATH resolution is not the venv's, so a bare ``mypy`` would
    either miss or check under a different interpreter. The probe **imports the REAL ``Exempt``**;
    re-declaring it locally would test mypy rather than the type.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    probe = tmp_path / "arity_probe.py"
    body = "\n".join(_ARITY_ENTRY.format(n=i) for i in range(entries))
    probe.write_text(textwrap.dedent(_ARITY_PROBE).format(entries=body), encoding="utf-8")
    env = dict(os.environ)
    env["MYPYPATH"] = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "src")])
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--no-incremental",
            "--cache-dir",
            str(tmp_path / "mypy_cache"),
            str(probe),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
    )


def test_e_is_fixed_arity_a_third_entry_is_a_type_error(tmp_path: Path) -> None:
    """T018(i): a THREE-element tuple assigned to ``tuple[Exempt, Exempt]`` fails mypy.

    **This limb is not insurance — it is the only enforcement that exists.** ``ci-quality.yml``'s
    mypy step is ``continue-on-error: true`` and covers only ``src/specify_cli src/charter
    src/doctrine``; ``tests/`` has **no** mypy gate, so SC-005's "a third entry is a type error"
    would otherwise be enforced by nothing.

    It proves the MECHANISM over a materialised probe. **WP05 runs mypy over the REAL
    ``_home_pin_exempt.py``**, which is what SC-005 itself needs; this does not duplicate it.
    """
    result = _run_mypy(tmp_path / "three", 3)
    assert result.returncode != 0, (
        f"a third E entry must be a type error, mypy exited 0. stdout:\n{result.stdout}"
    )
    assert "tuple[Exempt, Exempt]" in result.stdout, (
        f"the diagnostic must name the tuple type, got:\n{result.stdout}"
    )


def test_the_arity_harness_passes_on_two_entries(tmp_path: Path) -> None:
    """T018(i)'s POSITIVE CONTROL: the same harness exits **zero** for a two-element tuple.

    Without it, a harness that reds for any reason at all — a broken ``MYPYPATH``, an unresolvable
    import — would satisfy the assertion above while proving nothing about arity.
    """
    result = _run_mypy(tmp_path / "two", 2)
    assert result.returncode == 0, (
        f"the two-entry control must pass; the arity red above is only meaningful against it. "
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_mypy_is_available_and_its_absence_fails_rather_than_skips() -> None:
    """T018(i): **if mypy is unavailable the test FAILS. A skip is a fake green.**

    **STATED COST**: this reds the always-on ``arch-adversarial`` pole on any machine without mypy.
    That is deliberate — ``E``'s fixed arity has no CI backstop, so a skip here would silently
    retire SC-005's only enforcement — and under DIR-013 such a red is **reported, not absorbed**.
    """
    probe = subprocess.run(
        [sys.executable, "-m", "mypy", "--version"], capture_output=True, text=True, check=False
    )
    assert probe.returncode == 0, (
        "mypy is not importable under this interpreter. This is a FAILURE, not a skip: E's fixed "
        "arity is enforced by nothing else. Install mypy or report the red per DIR-013."
    )


def test_hash_placement_an_owed_to_repoint_passes(
    frozen: FrozenTree,
) -> None:
    """T018(ii)a: re-pointing ``owed_to`` **PASSES** — it is a header scalar, not a key.

    A ``sha256(path.read_bytes())`` baseline reds here, which is how that design passes review and
    fails on day thirty.
    """
    root, census, baseline, exempt = frozen
    repointed = edit_header(census, owed_to="#9999")
    assert census_keys(repointed) == census_keys(census), "the key set must be untouched"
    assert evaluate(root, repointed, baseline, exempt).ok


def test_hash_placement_a_header_edit_passes(
    frozen: FrozenTree,
) -> None:
    """T018(ii)b: editing the fragility note / regeneration command **PASSES**, same reason."""
    root, census, baseline, exempt = frozen
    edited = edit_header(census, fragility_note="reworded for clarity; the key set is unchanged")
    assert evaluate(root, edited, baseline, exempt).ok


def test_hash_placement_a_row_removal_without_a_tombstone_reds(
    frozen: FrozenTree,
) -> None:
    """T018(ii)c: a row removed with **no** tombstone REDS on the hash limb."""
    root, census, baseline, exempt = frozen
    victim = sorted(census_keys(census))[0]
    verdict = evaluate(root, drop_row(census, victim), baseline, exempt)
    assert not verdict.census_hash_ok


def test_hash_placement_a_row_removal_with_a_matching_tombstone_passes(
    frozen: FrozenTree,
) -> None:
    """T018(ii)d: the same removal **WITH** a matching tombstone **PASSES** — R1b's whole job.

    A blanket "touching both reds" rule would satisfy (c) and **forbid this**, which is why the
    legitimate case is asserted as firmly as the illegitimate one.
    """
    root, census, baseline, exempt = frozen
    victim = sorted(census_keys(census))[0]
    tombstoned = with_tombstones(baseline, frozenset({victim}))
    verdict = evaluate(root, drop_row(census, victim), tombstoned, exempt)
    assert verdict.census_hash_ok, "an adjudicated removal with a tombstone must pass the hash limb"
    assert verdict.stale == frozenset(), "the row is gone and so is nothing else"
    assert verdict.unexpected == {victim}, (
        "the DEFINITION is still in the tree, so the equality limb still reds — a tombstone "
        "records an adjudication, it does not delete a member"
    )


def test_e_co_edit_any_delta_to_the_exempt_set_reds_unconditionally(
    frozen: FrozenTree,
) -> None:
    """T018(iii): **any** delta to ``E`` reds, with **no tombstone path**.

    ``E`` never legitimately changes in R1a or R1b, so unlike the census there is nothing to
    adjudicate and nothing to record. This is the asymmetry T018 names.
    """
    root, census, baseline, exempt = frozen
    swapped = (exempt[0], scan.Exempt(key=("other.py", "other_home", "x"), why="a quiet swap"))
    verdict = evaluate(root, census, baseline, swapped)
    assert not verdict.exempt_hash_ok, "E's hash must red on any delta"


def test_e_co_edit_has_no_tombstone_escape(
    frozen: FrozenTree,
) -> None:
    """T018(iii), the asymmetry made explicit: a tombstone rescues a census row and NOT ``E``.

    Same edit, same tombstone, two different answers — which is what "no tombstone path" means
    operationally rather than as prose.
    """
    root, census, baseline, exempt = frozen
    swapped = (exempt[0], scan.Exempt(key=("other.py", "other_home", "x"), why="a quiet swap"))
    excused = with_tombstones(baseline, frozenset({exempt[1].key, swapped[1].key}))
    assert not evaluate(root, census, excused, swapped).exempt_hash_ok, (
        "a tombstone must NOT excuse an E delta — that path exists for the census only"
    )


def test_e_is_typed_as_a_fixed_pair_at_the_alias(
    frozen: FrozenTree,
) -> None:
    """The runtime companion to the mypy limb: ``E`` really is the two designated members.

    The type is what forbids a third entry; this asserts the two present ones are the intended
    ones, so a silently emptied ``E`` cannot make ``census u E`` green by degenerating.
    """
    root, _census, _baseline, exempt = frozen
    by_key = {member.key: member for member in scan.discover(root)}
    assert {entry.key for entry in exempt} == {
        key for key, member in by_key.items() if (member.relpath, key[1]) in EXEMPT_SITES
    }
    assert all(entry.why for entry in exempt), "every E entry states why; prose entitles nothing"


def test_this_module_never_parses_outside_the_seam() -> None:
    """WP02's anti-drift rule: zero ``ast.parse`` calls and zero ``NodeVisitor`` subclasses here.

    Materialised sources are parsed **only** through ``_home_pin_scan.parse_module``. The rule
    reaches the positive controls too, and the cheapest repair for a control that broke it would be
    to exempt the control — which reopens the seam.
    """
    tree = scan.parse_module(Path(__file__))
    parses = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "parse"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "ast"
    ]
    visitors = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(
            isinstance(base, ast.Attribute) and base.attr in {"NodeVisitor", "NodeTransformer"}
            for base in node.bases
        )
    ]
    assert parses == [] and visitors == []
