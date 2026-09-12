"""The COLLECTED gate: the verdict, the 806-state oracle, and the keys checked against this tree.

Binding sources: ``spec.md`` §0.9, ``data-model.md`` §``Verdict`` / §Banding, WP02/T008.

**This module is the gate that blocks every package.** It is a *collected*, ``architectural``-marked,
top-level test module — not "WP-a's first task", which gates only whichever package happens to be
sequenced first and which any concurrent package can skip.

Seven limbs, each independently falsifiable
--------------------------------------------
(a) reds when the verdict artefact is **absent**; (b) reds when it reads ``halt``; (c) passes only
for ``proceed`` / ``proceed-degraded``; (d) **recomputes** the band from the published operands and
asserts it equals the published label; (e) asserts internal consistency **as sets** and requires the
``start_sha_crosscheck`` to be present; (f) runs the full 806-state oracle as a **mapping**
comparison against thresholds transcribed inline from §0.9; (g) recomputes the surviving
``sites_at_end`` keys from this working tree against a published non-zero floor.

Why (b) and (d) exist at all
-----------------------------
A test asserting ``"verdict" in artefact`` passes for ``halt``. **(b)** kills that. A band that is
*published* rather than *recomputed* hides ``verdict: proceed`` written above ``r = 0.6``; **(d)**
kills that, and nothing else in the criterion set can.

No git, no subprocess in this module
-------------------------------------
C-003's containment: the window measurement, the extraction and the walk live in
``_home_pin_gate.py``. This module reads a committed artefact and this working tree. Measured cost
of limb (g): **0.19 s for 40 keys**.

What this cannot see
--------------------
The **start-SHA operands**, which name content that is not in this tree. Limb (g) raises the forgery
cost from *"consistent numbers"* to *"consistent numbers that are also real token lines at real line
numbers in this repository"*, but only for the end half. The start half remains unprovable without
git, and it is anchored instead by the ``start_sha_crosscheck`` the artefact publishes — which
(e) requires to be there rather than leaving it verified by nobody.
"""

from __future__ import annotations

import textwrap
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml

from specify_cli.contracts.anchoring import (
    code_tokens_by_line,
    composite_key_from_file,
    enclosing_qualname,
)
from tests.architectural import _home_pin_gate as gate
from tests.architectural._home_pin_scan import (
    TOMBSTONE_MANIFEST_PATH,
    load_tombstone_keys,
)

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"

#: §0.9's literal end SHA. It **never** moves; only the start SHA does, and only under the
#: pre-committed widening schedule.
END_SHA = "5d49d31ed6505627d98d8f95d8502c9bf6a2f5ac"
#: The VOID result the schedule starts from. Its presence in ``attempted_windows`` is required:
#: an artefact that omits it is publishing a chosen window rather than every attempted one.
VOID_START_SHA = "709a59534a1b8aac7e55a1cf6f5d2106a32c31ea"

#: **The published floor for limb (g)** — over the keys that actually *recompute* live, never over
#: mere file-presence. Originally 30, when all **40** end-SHA member files were byte-identical to
#: END_SHA and all 40 keys recomputed. Re-pinned to **20** on 2026-08-16 for #3121 R1b (PR #3510):
#: the provable-class convergence adjudicated **14** of the 40 members away (converged onto
#: ``canonical_home``, recorded in the tombstone manifest), so their sites were removed from the
#: tree on purpose and **26** members recomputed live.
#:
#: Re-pinned to **0** at issue-5-delete-sync-transport (2026-08-25): issue #5 deleted the whole
#: sync transport, and with it every remaining member file -- all 40 anchor keys are now
#: tombstoned (real removals, each recorded in the manifest with that cause) and zero recompute
#: live. The floor's anti-buy-off role ("the gate cannot be tombstoned away") is discharged for as
#: long as the population is empty: there is nothing left to excuse, and any NEW home pin in
#: ``tests/`` reds t023's discovered-class equality directly, because a fresh key is not in the
#: frozen anchor whatever the manifest says. If home pins are ever re-introduced, re-raise this
#: floor with the regeneration that admits them.
KEYS_CHECKED_FLOOR = 0

_ADMISSIBLE_VERDICTS = frozenset({"proceed", "proceed-degraded"})


# ---------------------------------------------------------------------------
# Loading and the falsifiable assertions, root-parameterised so limbs can be demonstrated
# ---------------------------------------------------------------------------


def load_verdict(root: Path) -> dict[str, Any]:
    """Read the verdict artefact under ``root``. **Raises ``AssertionError`` when absent.**"""
    path = root / gate.VERDICT_RELPATH
    assert path.is_file(), (
        f"the verdict artefact is absent at {gate.VERDICT_RELPATH} — WP-0b's measurement has not "
        "been published, and every downstream package is gated on it"
    )
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), f"{gate.VERDICT_RELPATH} must be a mapping"
    return document


def assert_verdict_admits(document: dict[str, Any]) -> None:
    """Pass only for ``proceed`` / ``proceed-degraded``. **``halt`` is a red.**"""
    verdict = document.get("verdict")
    assert verdict in _ADMISSIBLE_VERDICTS, (
        f"verdict is {verdict!r} — the Mission does not proceed. On `halt`, WP-0b stays at "
        "`for_review`, WP03..WP06 move to `blocked` via `move-task`, and the OPERATOR signs off; "
        "the implementer may not proceed on their own authority."
    )


def assert_band_recomputed(document: dict[str, Any]) -> None:
    """Recompute the band from the published operands and compare with the published label."""
    caught, arrivals = len(document["R_f"]), len(document["R"])
    recomputed = gate.window_label(caught, arrivals)
    assert recomputed == document["verdict"], (
        f"published verdict {document['verdict']!r} != band recomputed from the published "
        f"operands |R_f|={caught} |R|={arrivals} (r={caught / arrivals if arrivals else 0}) "
        f"-> {recomputed!r}"
    )


def _keys(rows: list[dict[str, Any]]) -> set[tuple[str, ...]]:
    """The published key triples of a site-row list, as a SET — never compared as a count."""
    return {tuple(str(part) for part in row["key"]) for row in rows}


def _key_list(rows: list[list[str]]) -> set[tuple[str, ...]]:
    """The published key triples of an ``R`` / ``R_f`` list, as a SET."""
    return {tuple(str(part) for part in key) for key in rows}


def _materialise_verdict(root: Path, document: dict[str, Any]) -> Path:
    """Write a synthetic verdict artefact into ``root`` at the real relative path."""
    path = root / gate.VERDICT_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# (a) absent artefact  (b) halt  (c) admissible
# ---------------------------------------------------------------------------


def test_a_absent_artefact_reds(tmp_path: Path) -> None:
    """Demonstrated against an empty tree: no artefact, no green."""
    with pytest.raises(AssertionError, match="verdict artefact is absent"):
        load_verdict(tmp_path)


def test_b_halt_verdict_reds(tmp_path: Path) -> None:
    """Demonstrated over a materialised artefact reading ``halt``.

    Without this limb, ``"verdict" in artefact`` passes for a halting Mission.
    """
    _materialise_verdict(tmp_path, {"verdict": "halt", "R": [], "R_f": []})
    with pytest.raises(AssertionError, match="does not proceed"):
        assert_verdict_admits(load_verdict(tmp_path))


def test_c_published_verdict_is_admissible() -> None:
    """The live gate. Reds until the published verdict reads ``proceed``/``proceed-degraded``."""
    assert_verdict_admits(load_verdict(REPO_ROOT))


# ---------------------------------------------------------------------------
# (d) the band is RECOMPUTED, never trusted
# ---------------------------------------------------------------------------


def test_d_band_recomputed_equals_published_label() -> None:
    """SC-000(vi). Without it, ``proceed`` written above ``r = 0.6`` is undetectable."""
    assert_band_recomputed(load_verdict(REPO_ROOT))


def test_d_control_mislabelled_band_reds(tmp_path: Path) -> None:
    """The positive control: ``proceed`` published over operands that band ``proceed-degraded``.

    Twelve of twenty caught is ``r = 0.6``. A limb that trusted the published label greens here.
    """
    caught = [[f"f{i}.py", "q", "t"] for i in range(12)]
    arrivals = caught + [[f"g{i}.py", "q", "t"] for i in range(8)]
    _materialise_verdict(tmp_path, {"verdict": "proceed", "R": arrivals, "R_f": caught})
    with pytest.raises(AssertionError, match="!= band recomputed"):
        assert_band_recomputed(load_verdict(tmp_path))


# ---------------------------------------------------------------------------
# (e) internal consistency, AS SETS, plus the start-SHA cross-check
# ---------------------------------------------------------------------------


def test_e_operands_are_internally_consistent_as_sets() -> None:
    """``R_f ⊆ R ⊆ arrivals``, both operand sets non-empty, the floor met, the end SHA fixed."""
    document = load_verdict(REPO_ROOT)
    start_sites, end_sites = _keys(document["sites_at_start"]), _keys(document["sites_at_end"])
    arrivals, caught = _key_list(document["R"]), _key_list(document["R_f"])

    assert start_sites, "sites_at_start is empty — the difference is not recomputable"
    assert end_sites, "sites_at_end is empty — the difference is not recomputable"
    assert caught <= arrivals, f"R_f ⊄ R: {sorted(caught - arrivals)}"
    assert arrivals <= end_sites, f"R ⊄ sites_at_end: {sorted(arrivals - end_sites)}"
    assert arrivals & start_sites == set(), (
        f"R intersects sites_at_start — an arrival cannot be present at the start SHA: "
        f"{sorted(arrivals & start_sites)}"
    )
    assert len(arrivals) >= gate.FLOOR, (
        f"|R| = {len(arrivals)} is below the visibility floor of {gate.FLOOR}; VOID is a "
        "precondition and lowering the floor to fit a window is refused"
    )
    assert document["end_sha"] == END_SHA, "the end SHA never moves"


def test_e_start_sha_is_the_window_the_schedule_selected() -> None:
    """``start_sha`` is asserted against the published schedule, **never against a literal**.

    The window WILL move, so a literal here would have to be edited every time the schedule ran —
    which is the same thing as not asserting it. Every attempted window is published, beginning
    with the VOID result at ``709a59534``.
    """
    document = load_verdict(REPO_ROOT)
    attempts = document["attempted_windows"]
    assert attempts, "attempted_windows is empty — every attempt is published, including discards"
    assert document["start_sha"] == attempts[-1]["start_sha"], (
        "start_sha must be the window the walk stopped at, not a window chosen afterwards"
    )
    assert attempts[0]["start_sha"] == VOID_START_SHA, (
        "the first attempted window must be §0.9's stated one, whose VOID result the schedule "
        "starts from"
    )
    assert attempts[0]["band"] == "VOID", "the stated window measured |R| = 3 against a floor of 10"
    discarded = {attempt["band"] for attempt in attempts[:-1]}
    assert discarded <= {"VOID", "INADMISSIBLE", "UNMEASURABLE"}, (
        f"a window carrying a real band was discarded: {sorted(discarded)} — the stopping rule "
        "reads |R| and stability only, so a banded window is never passed over"
    )


def test_e_start_sha_crosscheck_is_published_and_explained() -> None:
    """C-011's second external anchor, verified by **something** rather than by nobody.

    ``symmetric_difference`` must be present whether empty or not; a non-empty difference must
    carry a non-empty ``explanation`` sibling, because a difference is explained, never tuned away.
    """
    document = load_verdict(REPO_ROOT)
    assert set(document) == gate.VERDICT_FIELDS, (
        f"the emitted top-level key set must equal data-model.md's Verdict field list; "
        f"missing {sorted(gate.VERDICT_FIELDS - set(document))}, "
        f"extra {sorted(set(document) - gate.VERDICT_FIELDS)}"
    )
    crosscheck = document["start_sha_crosscheck"]
    assert {"instrument", "start_sha", "symmetric_difference", "explanation"} <= set(crosscheck)
    assert crosscheck["start_sha"] == document["start_sha"], (
        "the cross-check must anchor the SELECTED start SHA, not some other one"
    )
    if crosscheck["symmetric_difference"]:
        assert crosscheck["explanation"].strip(), (
            f"non-empty symmetric difference {crosscheck['symmetric_difference']} carries no "
            "explanation — a difference is explained, never tuned away"
        )


def test_e_effect_class_fallback_is_asserted_inert_at_both_ends() -> None:
    """The gate's own inert limb, asserted inert rather than presented as live (FR-007's rule).

    ``_home_pin_gate.Site`` reads the rename signature at the **keyed def** for a member and falls
    back to the **outermost enclosing def** for an effect-class site the FR-001 predicate does not
    catch. §0.9 measures that near-miss shape — ``tmp_path`` present, ``monkeypatch`` absent — at
    population **0**, so the fallback is never exercised at either published end.

    This limb is the executable form of that claim. If it ever reds, the fallback has gone live
    and the rename signature's "at the KEYED def" rule needs re-reading before the pairing is
    trusted — which is exactly the notice a silent fallback would not give.
    """
    document = load_verdict(REPO_ROOT)
    membership = {
        bool(row["is_member"])
        for key in ("sites_at_start", "sites_at_end")
        for row in document[key]
    }
    assert membership == {True}, (
        "an effect-class site is not a member at a published end — the rename-signature fallback "
        "to the outermost def is live, and §0.9's population-0 near-miss claim no longer holds"
    )


def test_h_record_names_the_section_0_3_disposition_and_the_leak() -> None:
    """§0.9 requires two statements **in so many words**; prose alone is what keeps failing here.

    The artefact must name §0.3's ``28 -> 30`` disposition with the literal word **RE-DERIVED** or
    **SUPERSEDED** — not "addressed" — and must record that the measurement **LEAKED**. Both are
    obligations on the record, and an obligation on a record that nothing reads is the failure
    mode this Mission keeps recording. So something reads it.
    """
    text = (REPO_ROOT / gate.VERDICT_RELPATH).read_text(encoding="utf-8")
    assert {"28 -> 30"} <= set(_phrases(text)), "the artefact does not name §0.3's figure at all"
    disposition = {"RE-DERIVED", "SUPERSEDED"} & set(_phrases(text))
    assert disposition, (
        "the record must use the literal word RE-DERIVED or SUPERSEDED for §0.3's 28 -> 30 "
        "figure — 'addressed' is explicitly refused"
    )
    assert {"LEAKED", "r = 100%"} <= set(_phrases(text)), (
        "the record must state that the measurement leaked; the gate confirms a known answer "
        "rather than discovering one, and only the stopping rule's independence is protected"
    )


def _phrases(text: str) -> set[str]:
    """The required phrases present in ``text``. A membership test over a fixed vocabulary."""
    required = {"28 -> 30", "RE-DERIVED", "SUPERSEDED", "LEAKED", "r = 100%"}
    return {phrase for phrase in required if phrase in text}


def test_h_control_a_silent_record_reds(tmp_path: Path) -> None:
    """The positive control: an artefact carrying neither statement is reported, not passed."""
    _materialise_verdict(tmp_path, {"verdict": "proceed"})
    text = (tmp_path / gate.VERDICT_RELPATH).read_text(encoding="utf-8")
    assert _phrases(text) == set()


# ---------------------------------------------------------------------------
# (f) the 806-state oracle, compared as a FULL MAPPING
# ---------------------------------------------------------------------------

_FLOOR = 10
_THRESHOLD = 0.5


def _inline_band(caught: int, arrivals: int) -> str:
    """§0.9's three rows, transcribed here rather than imported from the module under test."""
    ratio = caught / arrivals
    if ratio >= 1.0:
        return "proceed"
    return "proceed-degraded" if ratio >= _THRESHOLD else "halt"


def _inline_consequence(label: str) -> str:
    return "halt" if label == "halt" else "go"


def _inline_perturbations(caught: int, arrivals: int) -> list[tuple[int, int]]:
    """§0.9's ±1 neighbourhood in both axes, with the clamp spelled out."""
    neighbours: list[tuple[int, int]] = []
    if caught > 0:
        neighbours.append((caught - 1, arrivals))
    if caught < arrivals:
        neighbours.append((caught + 1, arrivals))
    neighbours.append((caught, arrivals + 1))
    if arrivals > caught and arrivals - 1 >= _FLOOR:
        neighbours.append((caught, arrivals - 1))
    return neighbours


def _inline_class(caught: int, arrivals: int, *, over_labels: bool) -> str:
    """One enumerated state's class, over CONSEQUENCES or — the fifteenth defect — over labels."""
    base = _inline_band(caught, arrivals)
    if over_labels:
        moved = any(_inline_band(f, n) != base for f, n in _inline_perturbations(caught, arrivals))
        return "inadmissible" if moved else base
    base_consequence = _inline_consequence(base)
    moved = any(
        _inline_consequence(_inline_band(f, n)) != base_consequence
        for f, n in _inline_perturbations(caught, arrivals)
    )
    return "inadmissible" if moved else base_consequence


def _enumerate(*, over_labels: bool) -> dict[tuple[int, int], str]:
    return {
        (arrivals, caught): _inline_class(caught, arrivals, over_labels=over_labels)
        for arrivals in range(_FLOOR, 41)
        for caught in range(0, arrivals + 1)
    }


def test_f_oracle_full_mapping_over_consequences() -> None:
    """The module's classifier equals an inline transcription of §0.9, state for state."""
    expected = _enumerate(over_labels=False)
    measured = {
        (arrivals, caught): gate.consequence_class(caught, arrivals)
        for arrivals, caught in expected
    }
    assert measured == expected


def test_f_oracle_reproduces_the_published_consequence_distribution() -> None:
    """§0.9's independently published ``380 go / 364 halt / 62 inadmissible``.

    ``sum`` over the distribution reproduces the **806**-state total, which is the figure the
    first pass got wrong (it wrote 682 — the admissible subset of the *label* enumeration, a
    wrong-denominator error in miniature).
    """
    distribution = Counter(_enumerate(over_labels=False).values())
    assert dict(distribution) == {"go": 380, "halt": 364, "inadmissible": 62}
    assert sum(distribution.values()) == 806


def test_f_over_labels_the_success_state_is_unreachable() -> None:
    """The fifteenth defect, mechanised: ``proceed`` in **exactly 0** of 806 states over labels.

    This is why the ±1 rule is evaluated over consequence classes. Evaluated over labels the
    halting instrument is a guaranteed no-verdict, and widening cannot rescue it — a moved window
    measuring 100% is inadmissible again.
    """
    distribution = Counter(_enumerate(over_labels=True).values())
    assert dict(distribution) == {"proceed-degraded": 318, "halt": 364, "inadmissible": 124}
    assert "proceed" not in distribution


def test_f_void_is_a_precondition_and_not_a_band() -> None:
    """Below the floor there is no band to return — asked for one, the module refuses."""
    with pytest.raises(gate.VoidWindowError):
        gate.band(_FLOOR - 1, _FLOOR - 1)
    assert gate.window_label(9, 9) == "VOID"


# ---------------------------------------------------------------------------
# (g) the published end-SHA keys, recomputed from THIS working tree
# ---------------------------------------------------------------------------


def _key_still_present(
    path: Path, published: tuple[str, ...], *, tests_root: Path = TESTS_ROOT
) -> bool:
    """True when ``published``'s ``(qualname, token_line)`` pair occurs anywhere in ``path``.

    Searched rather than indexed by line number, and that distinction is the whole point.
    ``composite_key``'s components are content-addressed, but its *lookup* is
    ``tokens.get(lineno, "")`` — so content inserted **above** a site moves the site and the
    recomputed key changes, while the docstring's promise of stability under comment insertion
    holds only for insertions below. Upstream inserted five lines above the site published as
    ``cli/commands/test_sync_doctor_tracker_egress_3108.py:124``; line 124 became a comment,
    whose token line is ``''``, and a key that had not changed at all was reported as forged.

    Searching for the key restores what this limb is actually asserting — that the site the
    verdict named still exists in this tree — and keeps the anti-forgery property intact, because
    a fabricated ``(qualname, token_line)`` pair occurs at no line of the real file.
    """
    source = path.read_text(encoding="utf-8")
    if published[0] != path.relative_to(tests_root).as_posix():
        return False
    return any(
        enclosing_qualname(source, lineno) == published[1]
        for lineno, token_line in code_tokens_by_line(source).items()
        if token_line == published[2]
    )


def _recompute_report(
    sites_at_end: list[dict[str, Any]],
    tombstoned: frozenset[tuple[str, ...]],
    *,
    tests_root: Path = TESTS_ROOT,
) -> tuple[set[tuple[str, ...]], dict[str, tuple[str, ...]]]:
    """Split the published end-SHA keys into ``(recomputed, mismatches)`` against ``tests_root``.

    A key **recomputes** when its ``(qualname, token_line)`` pair is still found in its file
    (:func:`_key_still_present`). A key that no longer recomputes is a **mismatch** — *unless* it is
    **tombstoned**: an R1b (#3121) member the census has adjudicated away, whose pin was removed
    from the tree on purpose and recorded in the tombstone manifest. A tombstoned key's absence is
    expected, so it is neither a recompute nor a mismatch. Keys whose file is missing entirely are
    skipped; the live-recompute floor in :func:`test_g_published_end_sha_keys_recompute_in_this_tree`
    guards against that eroding the check to a vacuous green.

    The anti-forgery property is preserved and sharpened: a fabricated ``(qualname, token_line)``
    pair occurs at no line of a real file, so it lands in ``mismatches`` unless it is tombstoned —
    and tombstoning is itself guarded (the census fails closed if a tombstoned key is still a live
    pin, and cannot exceed the removals the manifest records) while the floor bounds how far the
    live set may shrink. Tombstoning to dodge this limb therefore costs a real, recorded removal.
    """
    recomputed: set[tuple[str, ...]] = set()
    mismatches: dict[str, tuple[str, ...]] = {}
    for row in sites_at_end:
        path = tests_root / str(row["relpath"])
        if not path.is_file():
            continue
        published = tuple(str(part) for part in row["key"])
        if _key_still_present(path, published, tests_root=tests_root):
            recomputed.add(published)
        elif published not in tombstoned:
            mismatches[f"{row['relpath']}:{row['lineno']}"] = (
                path.relative_to(tests_root).as_posix(),
                *composite_key_from_file(path, row["lineno"]),
            )
    return recomputed, mismatches


def test_g_published_end_sha_keys_recompute_in_this_tree() -> None:
    """``MemberKey`` is content-addressed, so every surviving key must recompute here.

    Recomputation is a **search** for the published key, not a lookup at the published line —
    see :func:`_key_still_present` for the upstream edit that proved the difference. The line
    number is retained solely to report *what* sits there when a key does go missing.

    Since #3121 R1b (PR #3510) the population can legitimately *shrink*: a member converged onto
    ``canonical_home`` has its pin removed and is recorded in the tombstone manifest, so its
    published key no longer recomputes **by design**. Limb (g) excuses exactly the tombstoned keys
    (:func:`_recompute_report`) and holds the floor over the keys that still recompute live — so a
    fabricated end-SHA operand still costs a real ``(qualname, token_line)`` pair in a real file,
    and tombstoning the population away to dodge the check reds the floor instead.
    """
    document = load_verdict(REPO_ROOT)
    tombstoned = load_tombstone_keys(REPO_ROOT / TOMBSTONE_MANIFEST_PATH)
    recomputed, mismatches = _recompute_report(document["sites_at_end"], tombstoned)
    assert mismatches == {}, f"published keys that do not recompute from this tree: {mismatches}"
    assert len(recomputed) >= KEYS_CHECKED_FLOOR, (
        f"only {len(recomputed)} of the published end-SHA keys recompute live against this tree, "
        f"below the floor of {KEYS_CHECKED_FLOOR} — the limb has degraded toward the vacuous green "
        "it exists to prevent (a tombstone excuses an absent key, so the floor is what keeps the "
        "live population from being tombstoned away to nothing)"
    )


def test_g_control_a_forged_key_is_caught(tmp_path: Path) -> None:
    """The positive control: a key that does **not** match its site is reported.

    Without this run, the mismatch set being empty above is indistinguishable from a comparison
    that never happened.
    """
    module = tmp_path / "forged.py"
    module.write_text(
        textwrap.dedent(
            '''
            def anchor(tmp_path, monkeypatch):
                """A real def with a real line to key against."""
                monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
            '''
        ).lstrip(),
        encoding="utf-8",
    )
    lineno = next(
        n
        for n, line in enumerate(module.read_text(encoding="utf-8").splitlines(), start=1)
        if "setenv" in line
    )
    recomputed = (module.name, *composite_key_from_file(module, lineno))
    assert recomputed != (module.name, "anchor", "a forged token line")
    assert recomputed[0] == module.name
    assert recomputed[1].endswith("anchor")


def _absent_site(tmp_path: Path) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """A real file plus one published key that does **not** recompute against it.

    The file exists (so the missing-file skip does not apply), but the published token line sits at
    no line of it — the exact shape of a member whose home pin was converged away.
    """
    module = tmp_path / "converged.py"
    module.write_text("def anchor():\n    return None\n", encoding="utf-8")
    key = ("converged.py", "anchor", "monkeypatch . setenv ( , str ( tmp_path / ) )")
    row = [{"relpath": "converged.py", "lineno": 1, "key": list(key)}]
    return row, key


def test_g_control_a_tombstoned_absent_key_is_excused(tmp_path: Path) -> None:
    """The R1b path: an absent key that **is** tombstoned is expected, not a forgery.

    Without this excuse, converging a member (removing its pin) would red limb (g) forever — the
    very failure PR #3510 folds. The excused key is neither a mismatch nor a live recompute.
    """
    rows, key = _absent_site(tmp_path)
    recomputed, mismatches = _recompute_report(rows, frozenset({key}), tests_root=tmp_path)
    assert mismatches == {}, f"a tombstoned absent key must be excused, got {mismatches}"
    assert recomputed == set(), "a tombstoned absent key does not count toward the live floor"


def test_g_control_a_non_tombstoned_absent_key_still_reds(tmp_path: Path) -> None:
    """The anti-abuse teeth: the excuse is scoped to the manifest, nothing wider.

    The same absent site, with an **empty** tombstone set, is reported as a mismatch. A forged or
    genuinely-missing key cannot dodge the check unless it is a recorded tombstone.
    """
    rows, _key = _absent_site(tmp_path)
    recomputed, mismatches = _recompute_report(rows, frozenset(), tests_root=tmp_path)
    assert mismatches, "an absent key that is not tombstoned must still be reported"
    assert recomputed == set()
