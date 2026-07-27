"""Zero-producer lint — a declared slot that nothing populates must fail a test.

WP01 of mission ``doctrine-silence-guards-01KYFV7Q`` (FR-001, NFR-001, SC-001).

Why this exists
---------------
The precedent this guards against is measured, not theoretical: **three schema slots
have shipped inert in this repository, one of them green for 162 days behind passing
tests.** A field is added, a schema property is added to match, nothing ever writes
it, and every test stays green because nothing asserts that a declared thing is a
used thing. This module makes that a red test.

It is the first work package of its mission for a reason — it is what proves the
gates the later packages add are not themselves inert. Missions B1 and B2 add
``impacts``, ``is_symmetric`` and ``aliases``; C-009 requires each to arrive with a
producer *and* a coverage gate in the same commit, and this lint is the mechanism
that makes that requirement checkable rather than aspirational.

The definition (T001)
---------------------
An earlier definition was **self-annihilating** and is recorded here so it is not
reinvented. It read: *"a slot is both a model field and a JSON-Schema property; a
producer is any writer under src/ or the generated schemas."* Slots were a subset of
schema properties and producers included the generated schemas, so **every slot had a
producer by construction** — the lint would return the empty set on any tree and pass
its own zero-entry allowlist vacuously. The gate meant to prevent a fourth inert
register would have been the fourth inert register.

The adopted definition:

**Slot** — a declared, populatable field:

* a Pydantic model field declared under ``src/doctrine/**/models.py``, or
* a JSON-Schema *property* under ``src/doctrine/schemas/*.schema.yaml``.

  A schema ``definitions/`` entry is **not** a slot. It is a ``$ref`` target — a type,
  not a place data goes. The slot is the property that *uses* it. Getting this wrong
  is what would flag ``point_in_time_marker`` (see the anchors below).

**Producer** — anything that actually puts a value in the slot:

* a shipped doctrine artefact under ``src/doctrine/**`` carrying the key, **or**
* code **under ``src/doctrine/``** that assigns it.

  Scoped to the doctrine tree, not all of ``src/``, and the scope is load-bearing.
  Matching is by bare name (see the under-count section), so a wider producer scan
  means any unrelated local variable anywhere in the CLI masks a doctrine slot.
  Harvesting all of ``src/`` produced 12,742 names against 807 here — and among the
  11,935 it added were ``aliases`` and ``overrides``. That is not a rounding error:
  ``aliases`` is one of the three fields SC-001 names, so the whole-``src`` version
  of this gate **did not guard the thing it was written to guard**.

**The generated schemas are explicitly NOT producers.** They are the thing being
checked. Admitting them is precisely what made the earlier definition vacuous.

Note the asymmetry, because it is the whole point: a *reader* is not a producer. Code
that consumes a slot proves the slot is wired at the consumption end and says nothing
about whether anything fills it. But an **authored artefact** carrying the key *is* a
producer — in a doctrine layer most slots are filled by YAML authors, not by
assignment statements.

Calibration anchors
-------------------
Both were expected to be inert specimens and **both turn out not to be**, which makes
them the two most useful cases in the tree: they are the nearest-miss false positives,
and each defeats a different naive rule.

``structural_lint_config``
    Declared at ``styleguides/models.py:92``; its only code contact is a *reader*
    (``assets/built-in/docs_structural_lint.py``). A naive "producer = code that
    writes it" rule flags it. It is **not** inert: ``common-docs.styleguide.yaml``
    populates it. Mission A's WP05 is simultaneously defending this field as valid, so
    a lint that flags it would put two work packages in direct contradiction.

``point_in_time_marker``
    Declared in **no** model, present at ``schemas/styleguide.schema.yaml:14``. A naive
    "slot = model field ∩ schema property" rule cannot see it; a naive "slot = any
    schema key" rule flags it. Neither is right: it is a ``definitions/`` entry, i.e. a
    ``$ref`` target rather than a slot, and the *property* that uses it
    (``point_in_time_markers``) is both populated by ``common-docs.styleguide.yaml``
    and read by the asset.

The historical inert set is **derived, not cited**. An earlier draft referred to
"three known-inert cases" that no artefact names — a calibration set that does not
exist cannot falsify anything, and invites picking three cases that flatter the
definition. Whatever this lint reports on the shipped tree *is* the finding.

Known under-counts — and what they cost
---------------------------------------
Two of them. Both make the lint **under**-report, never over-report, so the true
debt is ``>= 59``. State the forward consequence, not just the arithmetic: an
under-count does not merely hide debt, it can silently retire one of this gate's
named duties.

**1. Bare-name matching.** Slots are matched to producers by name with no
namespacing, so a slot is masked whenever an unrelated same-named producer exists
anywhere in the scanned tree. This one already cost a guard duty once: while
producers were harvested from all of ``src/``, ``aliases`` was masked by unrelated
CLI code, so **mission B2 could have shipped ``aliases`` inert with this gate
green** — SC-001's central promise, quietly void. ``overrides`` was masked the same
way, hiding half the FR-028 pair. Scoping producers to ``src/doctrine/`` recovered
both. The residual risk is a collision *inside* the doctrine tree; per-kind
namespacing would close it and is a change to the definition, not this work
package's to make.

**2. ``_model_slots`` globs only ``models.py``.** Roughly 99 Pydantic fields are
invisible to the slot side: ``agent_profiles/profile.py`` (68),
``missions/step_contracts.py`` (23), ``drg/org_pack_config.py`` (8), plus
``base.py``, ``drg/merge.py`` and ``drg/org_pack_loader.py``. Concretely, the
agent-profile findings below are schema-side only — their Python twins
(``avatar_image``, ``toolguide_references``, …) are simply not seen. Widening the
glob is deferred, not solved.

The baseline is not an allowlist (operator ruling)
--------------------------------------------------
SC-001 asked for a zero-entry allowlist. The lint's first run on the shipped tree
returned 41 findings whose owners run **after** this work package (WP05) or in a
later mission (Mission D / I9): the dependency is inverted, and the criterion was
written against a tree that turned out not to be clean. The operator's ruling is a
frozen shrink-only baseline at ``_inert_slots_baseline.yaml``.

The distinction the next reader will otherwise collapse:

``ALLOWLIST``
    permanently excused. Stays ``frozenset()``, and ``test_allowlist_is_empty``
    keeps it there.
the baseline
    **debt**, not an excuse. Every entry carries a named ``owner``, one of exactly
    three structural ``disposition`` values (none of which is "accept"), and
    ``test_a_baseline_entry_does_not_survive_its_owner`` fails the moment that owner
    completes with the entry still present. Clearing the entry is a precondition of
    the owner being done — which is the whole reason this is a baseline and not an
    ``xfail``.

Growth above the baseline FAILS; shrinkage WARNS (charter Burn-down Policy §a), and
the file's size is registered with the charter-named ratchet in ``_baselines.yaml``
so nothing about it is pinned only by this module.

``unassigned`` is the hole in that claim, and it is capped
------------------------------------------------------------
``owner_is_complete`` returns ``False`` unconditionally for ``unassigned``, so the
anti-weasel test is *structurally incapable* of firing for those entries — the
"fails the moment that owner completes" promise is simply false for them. Combined
with the growth rule (a new finding must enter the baseline to pass), an
``unassigned`` row is a legal way to satisfy the gate without doing any work: it
never fires, never expires, never requires adjudication. Two things hold the line:

* ``MAX_UNASSIGNED_ENTRIES`` — a shrink-only cap, so the hatch cannot widen while
  the current set is adjudicated.
* ``test_every_named_owner_resolves`` — every non-``unassigned`` owner must name a
  real WP or mission in the event log, so ``WP42``, ``wp05`` and ``mission:typo``
  cannot masquerade as owned work. (They would read as "never complete", which is
  indistinguishable from live debt.)

Concrete floor (charter §5)
---------------------------
Every shipped-tree assertion here is an **absence** assertion — ``new == []``,
``offenders == {}``, ``name not in flagged`` — and all of them pass on a scan that
found nothing at all. The ``tmp_path`` self-mutation tests cannot cover this: they
build their own tree, so the shipped-tree path stays unpinned. Relocate
``src/doctrine``, rename the ``models.py`` convention, or land any refactor that
empties either walk, and this whole module goes inert behind green tests.
``test_the_scan_actually_sees_the_shipped_tree`` is the floor that pins it.

**Floored per walk, and that revision was earned.** The first floor pinned the
*union* of the two walks, which caught total collapse and missed partial collapse:
renaming the ``models.py`` convention kills the model walk — 145 distinct names, 23
baseline entries — while the surviving schema side (186 / 36) cleared a union floor
of 180/35, the entry half by exactly one. Review demonstrated it with a four-line
mutation: **25 passed** with half the gate dead. This docstring asserted the
opposite at the time, which is the part that mattered — a false coverage claim in
the gate whose whole job is to stop mechanisms going quietly inert. Both walks are
now floored independently, and both mutations go red.

**Entries-still-found floors are proportional, not absolute (WP05, FR-005).** The
name floors (``MINIMUM_SCHEMA_SLOT_NAMES`` / ``MINIMUM_MODEL_SLOT_NAMES``) stay
hardcoded — they pin the walk against wholesale collapse and have no relationship
to the baseline file's size. The *entries-still-found* floors were hardcoded too
(30 / 18) until WP05's FR-028 excision legitimately shrank the schema baseline
36 -> 28 (the ``enhances``/``overrides`` pair, four schemas each), which would have
tripped an absolute 30-floor on a change that did nothing wrong — and "lower the
floor" is indistinguishable at review time from quietly hiding a regression, which
is the same failure class this section already tells that story about once. WP05
converted both to ``len(BASELINE_SLOTS filtered by walk)`` — see
``_inert_slots.py`` — so they move automatically when a baseline entry is deleted
(the correct response to cleared debt) and still catch the 0-producer collapse
this floor exists for: ``0 >= 28`` fails exactly as hard as ``0 >= 30`` did.

The code-producer path was a silence guard, and it is now recorded
------------------------------------------------------------------
Everything above rests on one claim: **the baseline is the only way to make a finding
go away.** It was not. A slot leaves the findings list the moment *any* code under
``src/doctrine/`` names it, and review proved that costs one dead line. Plant a
producerless property, append ``_UNUSED = {"zzzprobeslot": None}`` to
``artifact_kinds.py``, and the module goes 1-failed → 26-passed with no ``ALLOWLIST``
entry, no baseline entry, and nothing visible in review. Confirming it turned up two
more shapes that work identically: a bare binding (``zzzprobeslot = None``) and a
keyword argument.

That third data point decided the fix. Every rule of the form "which AST node counts
as a write" is satisfiable by writing that node, so tightening
``_iter_code_producer_names`` narrows the hole and never closes it. **The producer
rule is therefore unchanged.** What changes is that the route is no longer silent:
``find_code_only_suppressions`` computes the slots that leave the findings list on a
code producer alone, and ``test_the_code_only_suppressions_match_the_frozen_record``
requires that set to equal the ``code_only_suppressions`` block of
``_inert_slots_baseline.yaml`` — both directions failing, so a collapsed walk cannot
satisfy it by finding nothing.

Visibility alone would only make the fake *conspicuous*; the cap is what makes it
expensive. Each row carries one of three verdicts, and the two that concede the slot
is really inert (``name-collision``, ``reader-not-producer``) are capped shrink-only
at their current population by ``MAX_MASKING_SUPPRESSIONS``. So a **new** code-only
suppression can only enter as ``genuine-producer`` — a positive claim, in a diff,
beside the code it claims, re-derived from the AST by ``code_producer_writes``.

The measurement behind leaving the rule permissive, because it should not have to be
re-derived: of the 15 code-only suppressions on the shipped tree, **one** is a real
production (``payload["action_sequence"] = …``). The other fourteen are same-named
locals (``lines = text.splitlines()``, ``field_path = ".".join(…)`` in six validation
modules), ``ArtifactKind`` tokens in ``_PLURALS``/``_PATTERNS``, and a loader's
read-map. Two of them invert this module's own reader/writer asymmetry outright:
``RoutingCandidate(effort=profile.effort)`` is a *read* of ``effort`` that the kwarg
rule scores as a write. In a doctrine layer the load-bearing producer is the authored
artefact, and that ratio is pinned by
``test_the_code_producer_path_is_mostly_coincidence`` so a future change that inverts
it has to re-argue the case rather than inherit it.

What this deliberately does **not** do: it does not enrol those fourteen as baseline
findings. That is the honest end state and the operator should get there, but it
needs an ``owner`` and a ``disposition`` per row — the owner's call, not the
implementer's, which ``_parse_entry`` enforces — and the ``unassigned`` hatch is at
its cap (23/23) with no headroom by design. The record holds the evidence for that
adjudication instead of performing it.

Non-vacuity (NFR-001)
---------------------
``test_planted_producerless_slot_is_flagged`` plants a real violation and asserts RED.
Critically it calls **the same** :func:`find_inert_slots` as the shipped-tree
assertion, differing only in the tree it is pointed at. A self-mutation test that
reimplements the check inline is green forever while the production checker rots.

The anti-weasel check needs the same treatment, and for a sharper reason: today no
owner has completed, so it passes **vacuously**.
``test_the_anti_weasel_check_fires_when_an_owner_completes`` plants a synthetic
mission whose owner is ``done`` and asserts the check reports it — otherwise this
mission would have shipped a guard against inert mechanisms that was itself inert.
"""

from __future__ import annotations

import json
import warnings
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from tests.architectural._inert_slots import (
    ALLOWLIST,
    BASELINE_SLOTS,
    CODE_ONLY_SUPPRESSIONS,
    CODE_ONLY_VERDICTS,
    DISPOSITIONS,
    MAX_MASKING_SUPPRESSIONS,
    MAX_UNASSIGNED_ENTRIES,
    MINIMUM_MODEL_BASELINE_ENTRIES_STILL_FOUND,
    MINIMUM_MODEL_SLOT_NAMES,
    MINIMUM_SCHEMA_BASELINE_ENTRIES_STILL_FOUND,
    MINIMUM_SCHEMA_SLOT_NAMES,
    is_schema_declared,
    UNASSIGNED_OWNER,
    Baseline,
    BaselineEntry,
    BaselineError,
    InertSlot,
    code_only_drift,
    code_producer_writes,
    find_code_only_suppressions,
    find_inert_slots,
    load_baseline,
    load_code_only_record,
    owner_exists,
    owner_is_complete,
    ratchet,
    scanned_slots,
    unresolved_by_completed_owners,
)

# CI's arch pole ANDs two clauses:
#   -m '<shard> and not windows_ci and (git_repo or integration or architectural) and not timing'
# The conftest hook auto-applies ``arch_shard_N`` to everything under the arch
# roots, so the shard half is satisfied automatically — but the second clause is
# not, and an unmarked file is deselected despite having its shard. Without this
# marker every test in this module collected ZERO in all three shards: the gate
# that exists to prove other gates are not inert was itself inert in CI.
# ``test_arch_shard_marker_completeness.py`` does not catch it — it checks the
# shard half of the partition only, never the clause CI ANDs on.
pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _shipped() -> tuple[InertSlot, ...]:
    """Memoised shipped-tree scan — it walks the whole of ``src/`` each call."""
    return tuple(find_inert_slots(_REPO_ROOT))


def _plant(root: Path, *, schema: str, model: str | None = None) -> None:
    """Write a minimal doctrine tree under *root* carrying the given declarations."""
    schemas = root / "src" / "doctrine" / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    (schemas / "planted.schema.yaml").write_text(schema, encoding="utf-8")
    if model is not None:
        pkg = root / "src" / "doctrine" / "planted"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "models.py").write_text(model, encoding="utf-8")


def test_planted_producerless_slot_is_flagged(tmp_path: Path) -> None:
    """NFR-001: the lint must reject a real violation shape, not just pass on green.

    Same callable as :func:`test_shipped_tree_has_no_inert_slots`; only the tree differs.
    """
    _plant(
        tmp_path,
        schema=(
            "type: object\n"
            "properties:\n"
            "  a_slot_nothing_fills:\n"
            "    type: string\n"
        ),
    )

    found = find_inert_slots(tmp_path)

    assert [s.name for s in found] == ["a_slot_nothing_fills"], (
        "the lint did not flag a schema property that no artefact populates and no "
        f"code assigns; got {found!r}"
    )


def test_planted_slot_with_an_authored_producer_is_not_flagged(tmp_path: Path) -> None:
    """An artefact carrying the key is a producer — most doctrine slots are filled this way."""
    _plant(
        tmp_path,
        schema="type: object\nproperties:\n  filled_by_an_artefact:\n    type: string\n",
    )
    artefact = tmp_path / "src" / "doctrine" / "styleguides" / "built-in"
    artefact.mkdir(parents=True, exist_ok=True)
    (artefact / "x.styleguide.yaml").write_text(
        "id: x\nfilled_by_an_artefact: a value\n", encoding="utf-8"
    )

    assert find_inert_slots(tmp_path) == []


#: The three dead-write shapes that silence a finding. The first is the one review
#: demonstrated; the other two were found while confirming it, and their existence
#: is the reason this is not fixed by enumerating AST shapes (see below).
_DEAD_WRITES = {
    "dict-literal-key": '_UNUSED = {"zzzprobeslot": None}\n',
    "bare-binding": "zzzprobeslot = None\n",
    "keyword-argument": "def _f() -> None:\n    _g(zzzprobeslot=1)\n",
}


@pytest.mark.parametrize("shape", sorted(_DEAD_WRITES))
def test_a_dead_code_write_cannot_silence_a_new_finding(
    tmp_path: Path, shape: str
) -> None:
    """The inverse self-mutation test — the one whose absence left the gate fakeable.

    ``test_planted_slot_with_an_authored_producer_is_not_flagged`` exercises the
    *artefact* producer path. The **code** producer path — the fakeable one — had no
    test in either direction, so NFR-001's easy question ("does the gate fire?") was
    answered and the hard one ("can it be silenced without ceremony?") was not.

    Review demonstrated the gap on the shipped tree: plant a producerless property,
    then append ``_UNUSED = {"zzzprobeslot": None}`` to ``artifact_kinds.py``, and the
    module goes 1-failed → 26-passed. No ``ALLOWLIST`` entry (``test_allowlist_is_empty``
    forbids it), no baseline entry (that needs an ``owner`` and a ``disposition``, and
    the anti-weasel check stands behind it) — **nothing visible in review at all.**

    Confirming it turned up two more shapes, and that is the load-bearing detail: a
    bare binding and a keyword argument silence it just as well. Any rule of the form
    "which AST node counts as a write" is satisfiable by writing the node, so
    enumerating shapes narrows the hole and never closes it. What closes it is
    removing the *silence*: a slot kept out of the findings list by code alone is
    recorded in ``_inert_slots_baseline.yaml``, and the recorded set must match the
    computed one exactly. The producer rule is deliberately unchanged; what changes
    is that using it now costs a reviewable row.
    """
    _plant(tmp_path, schema="type: object\nproperties:\n  zzzprobeslot:\n    type: string\n")
    assert [s.name for s in find_inert_slots(tmp_path)] == ["zzzprobeslot"]

    (tmp_path / "src" / "doctrine" / "dead.py").write_text(
        _DEAD_WRITES[shape], encoding="utf-8"
    )

    assert find_inert_slots(tmp_path) == [], (
        "the producer rule is intentionally untouched by this fix — if this went red, "
        "the rule was tightened and the corroboration record below may now be "
        "double-counting. Re-measure before deleting either."
    )
    assert [s.name for s in find_code_only_suppressions(tmp_path)] == ["zzzprobeslot"], (
        f"a {shape} that nothing reads silenced a finding and left no trace; the "
        "shipped-tree gate would have gone green on it"
    )


def test_a_schema_definitions_entry_is_not_a_slot(tmp_path: Path) -> None:
    """``definitions/`` entries are ``$ref`` targets, not places data goes.

    This is the rule that keeps ``point_in_time_marker`` out of the report.
    """
    _plant(
        tmp_path,
        schema=(
            "type: object\n"
            "definitions:\n"
            "  some_ref_target:\n"
            "    type: object\n"
            "properties: {}\n"
        ),
    )

    assert find_inert_slots(tmp_path) == []


def test_shipped_tree_has_no_inert_slots_beyond_the_frozen_baseline() -> None:
    """The gate itself: growth above the baseline FAILS, shrinkage WARNS.

    Any finding not already frozen is real. It is either a producer that was never
    wired or a declaration that should be deleted; adding it to ``ALLOWLIST`` is not
    one of the options, and neither is adding it here without an owner and a
    disposition.
    """
    found = list(_shipped())
    new, cleared = ratchet(found, load_baseline())

    if cleared:
        warnings.warn(
            "baseline entries are no longer found — delete them from "
            "_inert_slots_baseline.yaml:\n"
            + "\n".join(f"  - {e.name} at {e.declared_at} ({e.owner})" for e in cleared),
            stacklevel=1,
        )

    assert new == [], (
        "declared slots that nothing populates, and that are NOT in the frozen "
        "baseline:\n"
        + "\n".join(f"  - {s.name} declared at {s.declared_at}" for s in new)
        + "\n\nEach is either a producer that was never wired, or a declaration that "
        "should be deleted. If it is genuinely scheduled debt, add it to "
        "_inert_slots_baseline.yaml with a named owner and one of "
        f"{sorted(DISPOSITIONS)} — never to ALLOWLIST."
    )


@lru_cache(maxsize=1)
def _shipped_code_only() -> tuple[InertSlot, ...]:
    """Memoised shipped-tree scan of the code-only suppression route."""
    return tuple(find_code_only_suppressions(_REPO_ROOT))


def test_the_code_only_suppressions_match_the_frozen_record() -> None:
    """The second half of the gate: the silent suppression route, made loud.

    ``test_shipped_tree_has_no_inert_slots_beyond_the_frozen_baseline`` above is
    load-bearing only if the findings list cannot be shortened without ceremony. It
    could: a slot leaves that list the moment any code under ``src/doctrine/`` names
    it, and review proved a single dead line is enough. This assertion is what makes
    that route cost something.

    Both directions fail. An unrecorded suppression is the hole itself. A recorded
    row that is no longer computed is either cleared debt whose row belongs in the
    same diff, or a collapsed walk — and the walk case matters, because every other
    assertion about this route is an absence assertion that a collapsed walk would
    satisfy. This one is an equality, so it cannot be satisfied by finding nothing.
    """
    new, stale = code_only_drift(list(_shipped_code_only()), CODE_ONLY_SUPPRESSIONS)

    assert (new, stale) == ([], []), "\n".join(
        [
            *(
                [
                    "slots that left the findings list because code names them, with "
                    "nothing recorded for them:",
                    *(f"  - {s.name} declared at {s.declared_at}" for s in new),
                    "",
                    "This is the shape review used to silence a planted finding with "
                    "one dead line. If the producer is real, add a row to "
                    "_inert_slots_baseline.yaml under 'code_only_suppressions' with "
                    f"verdict: genuine-producer (legal: {sorted(CODE_ONLY_VERDICTS)}) "
                    "and the file that writes it. If it is not real, the slot is a "
                    "finding: give it a baseline entry with an owner instead.",
                ]
                if new
                else []
            ),
            *(
                [
                    "recorded code-only suppressions that are no longer computed:",
                    *(f"  - {r.name} declared at {r.declared_at}" for r in stale),
                    "",
                    "Either the slot gained a real artefact producer or lost its "
                    "declaration — delete the row in this same change — or a walk "
                    "collapsed, in which case repair the walk and change nothing here.",
                ]
                if stale
                else []
            ),
        ]
    )


def test_every_recorded_code_producer_actually_writes_the_slot() -> None:
    """A cited producer that writes nothing reads exactly like one that does.

    Same failure ``test_every_named_owner_resolves`` closes for baseline owners: an
    unverifiable value in the record is indistinguishable from a legitimate one, so
    a row could name any path at all and still look adjudicated.
    """
    unverified = sorted(
        f"{row.name} -> {row.producer}"
        for row in CODE_ONLY_SUPPRESSIONS
        if not code_producer_writes(_REPO_ROOT, row.name, row.producer)
    )

    assert unverified == [], (
        f"recorded producers that do not write the slot they are cited for: "
        f"{unverified}. The path is re-parsed from the AST; a stale citation means "
        "the row's verdict was reasoned about code that has since moved or changed."
    )


def test_the_masking_verdicts_are_capped_and_shrink_only() -> None:
    """The cap is what turns a visible route into a closed one.

    Making the suppression route visible stops it being silent. The cap is what
    stops it being *cheap*: with masking rows at their current population, a new
    code-only suppression can only enter as ``genuine-producer`` — a positive claim
    someone signs, next to the code, re-derived from the AST. Raising this number is
    the single move that re-opens the hole, so it may only ever go down.
    """
    masking = [row for row in CODE_ONLY_SUPPRESSIONS if row.masks_a_finding]

    assert len(masking) <= MAX_MASKING_SUPPRESSIONS, (
        f"{len(masking)} rows carry a masking verdict, above the shrink-only cap of "
        f"{MAX_MASKING_SUPPRESSIONS}. A new code-only suppression must be a genuine "
        "producer, or the slot is a finding and belongs in the baseline with an owner."
    )
    if len(masking) < MAX_MASKING_SUPPRESSIONS:
        warnings.warn(
            f"masking code-only suppressions are down to {len(masking)}; lower "
            f"MAX_MASKING_SUPPRESSIONS to lock it in.",
            stacklevel=1,
        )


def test_the_code_producer_path_is_mostly_coincidence() -> None:
    """The measurement that justifies the record's shape, pinned so it cannot rot.

    In a doctrine layer, slots are filled by YAML authors — the module docstring says
    so, and this is the number behind it: of the code-only suppressions on the
    shipped tree, exactly one is a real production and the rest are same-named
    locals, ArtifactKind tokens, and loader read-maps. A future change that inverts
    this ratio means the code-producer rule has become load-bearing after all, and
    the case for keeping it permissive should be re-argued rather than inherited.
    """
    genuine = [row for row in CODE_ONLY_SUPPRESSIONS if not row.masks_a_finding]

    assert [row.name for row in genuine] == ["action_sequence"], (
        "the set of code-only suppressions claimed as real producers changed: "
        f"{sorted(row.name for row in genuine)}. Re-read the record's header — the "
        "one-in-fifteen ratio is the evidence the producer rule was left permissive."
    )


def test_an_illegal_code_only_verdict_is_rejected_at_load_time(tmp_path: Path) -> None:
    """No ``accepted``, for the same reason the disposition vocabulary has none."""
    path = tmp_path / "b.yaml"
    path.write_text(
        "mission: m\nentries: []\ncode_only_suppressions:\n"
        "  - name: x\n    declared_at: a.yaml\n    producer: b.py\n"
        "    verdict: accepted\n    note: n\n",
        encoding="utf-8",
    )

    with pytest.raises(BaselineError, match="illegal verdict"):
        load_code_only_record(path)


def test_a_missing_code_only_block_is_malformed_not_empty(tmp_path: Path) -> None:
    """Deleting the record must not read as "there are no suppressions".

    A block that defaults to empty when absent is a gate you disable by deletion,
    and the deletion looks like tidying.
    """
    path = tmp_path / "b.yaml"
    path.write_text("mission: m\nentries: []\n", encoding="utf-8")

    with pytest.raises(BaselineError, match="must be a list"):
        load_code_only_record(path)


def test_an_artefact_producer_is_not_a_code_only_suppression(tmp_path: Path) -> None:
    """The record covers the code route only — an authored key is the honest way out.

    Without this the new check would grow a row every time a slot is legitimately
    populated by doctrine YAML, i.e. it would tax the correct behaviour.
    """
    _plant(tmp_path, schema="type: object\nproperties:\n  authored:\n    type: string\n")
    artefact = tmp_path / "src" / "doctrine" / "styleguides" / "built-in"
    artefact.mkdir(parents=True, exist_ok=True)
    (artefact / "x.styleguide.yaml").write_text(
        "id: x\nauthored: a value\n", encoding="utf-8"
    )
    (tmp_path / "src" / "doctrine" / "also.py").write_text(
        'd["authored"] = 1\n', encoding="utf-8"
    )

    assert find_inert_slots(tmp_path) == []
    assert find_code_only_suppressions(tmp_path) == []


def test_a_cited_producer_that_does_not_write_the_slot_is_rejected(tmp_path: Path) -> None:
    """Non-vacuity for :func:`code_producer_writes` — it must answer ``False`` sometimes."""
    doctrine = tmp_path / "src" / "doctrine"
    doctrine.mkdir(parents=True)
    (doctrine / "writes.py").write_text('d["real"] = 1\n', encoding="utf-8")
    (doctrine / "reads.py").write_text('x = d["real"]\n', encoding="utf-8")

    assert code_producer_writes(tmp_path, "real", Path("src/doctrine/writes.py"))
    assert not code_producer_writes(tmp_path, "real", Path("src/doctrine/reads.py"))
    assert not code_producer_writes(tmp_path, "real", Path("src/doctrine/gone.py"))


def test_baseline_entries_are_well_formed() -> None:
    """Every entry needs an owner and a legal disposition.

    ``unassigned`` is legal but is visible pressure, not a resting place — and an
    un-adjudicated disposition must say so via ``provisional`` rather than passing
    itself off as a decision someone made. An entry with a named owner may not be
    provisional: that owner's disposition is theirs to decide and record. (The
    converse does not hold — the occurrence-map entry is un-owned but its
    disposition was adjudicated by the operator.)
    """
    baseline = load_baseline()

    assert baseline.entries, "the baseline exists to hold entries; an empty one is a bug"
    for entry in baseline.entries:
        assert entry.owner, f"{entry.name} has no owner"
        assert entry.disposition in DISPOSITIONS, (
            f"{entry.name} carries illegal disposition {entry.disposition!r}"
        )
        assert not (entry.provisional and entry.owner != UNASSIGNED_OWNER), (
            f"{entry.name}: owner {entry.owner!r} is named, so its disposition is "
            "that owner's call to make and record — it cannot stay provisional"
        )


def test_an_illegal_disposition_is_rejected_at_load_time(tmp_path: Path) -> None:
    """There is no ``accepted``. A fourth value is how a baseline becomes an allowlist."""
    path = tmp_path / "b.yaml"
    path.write_text(
        "mission: m\nentries:\n"
        "  - name: x\n    declared_at: a.yaml\n    owner: WP01\n"
        "    disposition: accepted\n    note: n\n",
        encoding="utf-8",
    )

    with pytest.raises(BaselineError, match="illegal disposition"):
        load_baseline(path)


def test_a_baseline_entry_does_not_survive_its_owner() -> None:
    """The anti-weasel gate: an owner cannot complete and leave its debt behind.

    Non-vacuity for this test lives in
    :func:`test_the_anti_weasel_check_fires_when_an_owner_completes` — as of today
    no owner has completed, so this assertion passes without exercising anything.
    """
    offenders = unresolved_by_completed_owners(
        list(_shipped()), load_baseline(), root=_REPO_ROOT
    )

    assert offenders == {}, "\n".join(
        [
            "these owners completed with baseline entries still unresolved:",
            *(
                f"  {owner}: " + ", ".join(f"{e.name} at {e.declared_at}" for e in items)
                for owner, items in sorted(offenders.items())
            ),
            "",
            "Clearing them is a precondition of the owner being done. Resolve each "
            "per its disposition; do not re-home the entry to another owner.",
        ]
    )


def _plant_mission(root: Path, slug: str, wp_id: str, lane: str) -> None:
    """Write a mission whose *wp_id* sits in *lane*, readable by the status reducer."""
    mission_dir = root / "kitty-specs" / slug
    mission_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "actor": "test",
        "at": "2026-07-26T00:00:00+00:00",
        "event_id": "01KYFZE2V36SSDADX84PDVB6B4",
        "evidence": None,
        "execution_mode": "worktree",
        "force": False,
        "from_lane": "genesis",
        "mission_slug": slug,
        "policy_metadata": None,
        "reason": "planted",
        "review_ref": None,
        "to_lane": lane,
        "wp_id": wp_id,
    }
    (mission_dir / "status.events.jsonl").write_text(
        json.dumps(event) + "\n", encoding="utf-8"
    )


def _entry(owner: str) -> BaselineEntry:
    return BaselineEntry(
        name="planted",
        declared_at=Path("planted.schema.yaml"),
        owner=owner,
        disposition="delete-the-declaration",
        note="planted",
        provisional=False,
    )


@pytest.mark.parametrize("lane", ["approved", "done"])
def test_the_anti_weasel_check_fires_when_an_owner_completes(
    tmp_path: Path, lane: str
) -> None:
    """NFR-001 for the anti-weasel gate itself.

    Without this, the guard is green forever simply because nobody has finished yet
    — a gate against inert mechanisms that is itself inert, which is precisely the
    defect class this mission exists to close.
    """
    _plant_mission(tmp_path, "planted-mission", "WP99", lane)
    entry = _entry("WP99")
    baseline = Baseline(mission="planted-mission", entries=(entry,))

    offenders = unresolved_by_completed_owners(
        [entry.slot], baseline, root=tmp_path
    )

    assert offenders == {"WP99": [entry]}


def test_an_unfinished_owner_is_not_an_offender(tmp_path: Path) -> None:
    """The other half of the contract: debt is allowed to exist while it is owned."""
    _plant_mission(tmp_path, "planted-mission", "WP99", "in_progress")
    entry = _entry("WP99")
    baseline = Baseline(mission="planted-mission", entries=(entry,))

    assert unresolved_by_completed_owners([entry.slot], baseline, root=tmp_path) == {}


def test_unassigned_is_never_complete(tmp_path: Path) -> None:
    """``unassigned`` must not read as "nobody owns it, so nobody has to clear it"."""
    assert not owner_is_complete(
        UNASSIGNED_OWNER, root=tmp_path, mission="planted-mission"
    )


def test_a_mission_owner_completes_only_when_all_its_wps_do(tmp_path: Path) -> None:
    """``mission:`` owners are the Mission D case — granularity is the whole mission."""
    _plant_mission(tmp_path, "band", "WP01", "done")
    owner = "mission:band"

    assert owner_is_complete(owner, root=tmp_path, mission="irrelevant")

    _plant_mission(tmp_path, "band", "WP01", "in_progress")

    assert not owner_is_complete(owner, root=tmp_path, mission="irrelevant")


def test_a_missing_mission_is_not_complete(tmp_path: Path) -> None:
    """An owner whose mission does not exist yet has certainly not finished it."""
    assert not owner_is_complete("mission:nope", root=tmp_path, mission="nope")


def test_a_specified_but_unplanned_mission_resolves_yet_is_not_complete(
    tmp_path: Path,
) -> None:
    """"Not yet decomposed into WPs" is not "no such mission".

    This is Mission D's live state, and conflating the two is a bug this module
    shipped until ``test_every_named_owner_resolves`` caught it: existence must be
    the mission directory, completion must be its work packages.
    """
    mission_dir = tmp_path / "kitty-specs" / "specified-only"
    mission_dir.mkdir(parents=True)
    (mission_dir / "status.events.jsonl").write_text("", encoding="utf-8")
    owner = "mission:specified-only"

    assert owner_exists(owner, root=tmp_path, mission="irrelevant")
    assert not owner_is_complete(owner, root=tmp_path, mission="irrelevant")


def test_a_typo_owner_does_not_resolve(tmp_path: Path) -> None:
    """The failure this guards: a misspelt owner reads exactly like unfinished work."""
    _plant_mission(tmp_path, "planted-mission", "WP99", "done")

    assert owner_exists("WP99", root=tmp_path, mission="planted-mission")
    assert not owner_exists("wp99", root=tmp_path, mission="planted-mission")
    assert not owner_exists("WP42", root=tmp_path, mission="planted-mission")
    assert not owner_exists("mission:typo", root=tmp_path, mission="planted-mission")


def test_the_scan_actually_sees_the_shipped_tree() -> None:
    """The concrete floor — pinned **per walk**, not on their union.

    ``new == []`` is green when the tree is clean **and** when the walk found
    nothing, and nothing else in this module can tell those apart.

    The union floor this replaces caught total collapse and missed *partial*
    collapse. Renaming the ``models.py`` convention kills the model walk — 145
    distinct names and 23 baseline entries go dark — while the surviving schema
    side (186 / 36) cleared a union floor of 180/35, the entry half **by a single
    entry**. Both this module's docstring and the old assertion message claimed
    that case was caught. It was not. Two walks, two floors.
    """
    scanned = list(scanned_slots(_REPO_ROOT))
    schema_names = {slot.name for slot in scanned if is_schema_declared(slot)}
    model_names = {slot.name for slot in scanned if not is_schema_declared(slot)}

    assert len(schema_names) >= MINIMUM_SCHEMA_SLOT_NAMES, (
        f"the schema walk found only {len(schema_names)} distinct names; the floor "
        f"is {MINIMUM_SCHEMA_SLOT_NAMES}. The doctrine schemas moved or the walk is "
        "broken — repair it, do not relax the floor."
    )
    assert len(model_names) >= MINIMUM_MODEL_SLOT_NAMES, (
        f"the model walk found only {len(model_names)} distinct names; the floor is "
        f"{MINIMUM_MODEL_SLOT_NAMES}. The `models.py` convention was renamed or the "
        "walk is broken. This half can die silently while the schema half keeps the "
        "suite green, which is exactly why the floors are split."
    )

    still_found = set(_shipped()) & load_baseline().slots
    schema_entries = {slot for slot in still_found if is_schema_declared(slot)}
    model_entries = still_found - schema_entries

    assert len(schema_entries) >= MINIMUM_SCHEMA_BASELINE_ENTRIES_STILL_FOUND, (
        f"only {len(schema_entries)} schema-declared baseline entries are still "
        f"detected; the floor is {MINIMUM_SCHEMA_BASELINE_ENTRIES_STILL_FOUND} — "
        "derived from _inert_slots_baseline.yaml itself (see _inert_slots.py), so "
        "this is not a stale hardcoded number. If a baseline entry was cleared "
        "for real, delete its row from the file — the floor drops with it — and "
        "update `_baselines.yaml`'s `baseline_entries` in the same change, which "
        "the registration gate requires. Do not lower a floor constant."
    )
    assert len(model_entries) >= MINIMUM_MODEL_BASELINE_ENTRIES_STILL_FOUND, (
        f"only {len(model_entries)} model-declared baseline entries are still "
        f"detected; the floor is {MINIMUM_MODEL_BASELINE_ENTRIES_STILL_FOUND} — "
        "derived from _inert_slots_baseline.yaml itself. Delete the cleared row, "
        "do not edit a floor constant."
    )

def test_every_named_owner_resolves() -> None:
    """An owner that does not exist reads exactly like an owner that is not done.

    Without this, ``WP42`` / ``wp05`` / ``mission:typo`` sit in the baseline looking
    like live, owned debt while being unreachable by the anti-weasel gate forever.
    """
    baseline = load_baseline()
    unresolvable = sorted(
        {
            entry.owner
            for entry in baseline.entries
            if not owner_exists(entry.owner, root=_REPO_ROOT, mission=baseline.mission)
        }
    )

    assert unresolvable == [], (
        f"baseline owners that name no real WP or mission: {unresolvable}. "
        f"WP owners resolve against mission {baseline.mission!r}; 'mission:<slug>' "
        "owners resolve against kitty-specs/<slug>."
    )


def test_the_unassigned_hatch_is_capped_and_shrink_only() -> None:
    """``unassigned`` can never fire the anti-weasel gate, so it must not widen.

    This is the one number in the file that is a policy, not an observation: it may
    go down as entries are adjudicated and must never go up.
    """
    unassigned = [e for e in load_baseline().entries if e.owner == UNASSIGNED_OWNER]

    assert len(unassigned) <= MAX_UNASSIGNED_ENTRIES, (
        f"{len(unassigned)} entries are owned by {UNASSIGNED_OWNER!r}, above the "
        f"shrink-only cap of {MAX_UNASSIGNED_ENTRIES}. A new finding needs a real "
        "owner; the hatch does not widen to accommodate it."
    )
    if len(unassigned) < MAX_UNASSIGNED_ENTRIES:
        warnings.warn(
            f"{UNASSIGNED_OWNER} entries are down to {len(unassigned)}; lower "
            f"MAX_UNASSIGNED_ENTRIES to lock it in.",
            stacklevel=1,
        )


def test_an_owned_entry_may_not_be_provisional_at_load_time(tmp_path: Path) -> None:
    """Same class of rule as the disposition vocabulary, so same enforcement point."""
    path = tmp_path / "b.yaml"
    path.write_text(
        "mission: m\nentries:\n"
        "  - name: x\n    declared_at: a.yaml\n    owner: WP01\n"
        "    disposition: wire-the-producer\n    note: n\n    provisional: true\n",
        encoding="utf-8",
    )

    with pytest.raises(BaselineError, match="cannot stay provisional"):
        load_baseline(path)


def test_the_unassigned_cap_is_registered_with_the_charter_ratchet() -> None:
    """The escape hatch's cap is a ratchet, so it lives where ratchets are governed.

    Without this the cap is a bare module constant: a future PR widens it 23 → 30 on
    one line with nothing to answer to, while the baseline *total* it guards sits
    under the charter file's `# justification:` policy. The asymmetry was arbitrary.
    """
    recorded = yaml.safe_load(
        (_REPO_ROOT / "tests" / "architectural" / "_baselines.yaml").read_text(
            encoding="utf-8"
        )
    )["test_no_inert_schema_slots"]["unassigned_entries"]

    assert recorded == MAX_UNASSIGNED_ENTRIES, (
        f"_baselines.yaml records unassigned_entries={recorded} but the module caps "
        f"at {MAX_UNASSIGNED_ENTRIES}. Change both, and growing either needs a "
        "`# justification:` comment per the charter file's own policy."
    )


def test_the_baseline_size_is_registered_with_the_charter_ratchet() -> None:
    """Burn-down Policy §a: the size lives in ``_baselines.yaml``, not only here.

    Pinned from this side too, so the registration cannot drift into being a number
    nobody compares against anything.
    """
    recorded = yaml.safe_load(
        (_REPO_ROOT / "tests" / "architectural" / "_baselines.yaml").read_text(
            encoding="utf-8"
        )
    )["test_no_inert_schema_slots"]["baseline_entries"]

    assert recorded == len(BASELINE_SLOTS), (
        f"_baselines.yaml records {recorded} baseline entries but the file holds "
        f"{len(BASELINE_SLOTS)}. Update both in the same change."
    )


def test_allowlist_is_empty() -> None:
    """NFR-001: a gate with a populated allowlist is a gate with exceptions.

    Mirrors ``test_doctrine_artefact_layout.py``'s own zero-entry rule.
    """
    assert frozenset() == ALLOWLIST


@pytest.mark.parametrize(
    "slot_name",
    ["structural_lint_config", "point_in_time_marker", "point_in_time_markers"],
)
def test_calibration_anchors_are_not_flagged(slot_name: str) -> None:
    """The two nearest-miss false positives, each defeating a different naive rule.

    See the module docstring. If a future definition change flags either of these, it
    is the definition that is wrong — ``structural_lint_config`` in particular is a
    field mission A's own WP05 is defending.
    """
    flagged = {s.name for s in _shipped()}

    assert slot_name not in flagged, (
        f"{slot_name!r} was flagged as inert. It is not: see the calibration-anchor "
        "section of this module's docstring for which naive rule this indicates."
    )


def test_inert_slot_reports_where_the_slot_is_declared(tmp_path: Path) -> None:
    """A finding a maintainer cannot locate is a finding they will ignore."""
    _plant(tmp_path, schema="type: object\nproperties:\n  orphan:\n    type: string\n")

    (slot,) = find_inert_slots(tmp_path)

    assert isinstance(slot, InertSlot)
    assert slot.name == "orphan"
    assert "planted.schema.yaml" in str(slot.declared_at)
