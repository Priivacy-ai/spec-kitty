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
* code under ``src/`` that assigns it.

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

A known under-count: bare-name matching
---------------------------------------
Slots are matched to producers **by name, with no namespacing**, so a slot is masked
whenever an unrelated same-named producer exists anywhere under ``src/``. The live
example is ``overrides``: the exact twin of the four ``enhances`` findings, retired
by the same FR-028 cutover, and absent from the report only because
``cli/commands/agent/tasks_status_cmd.py`` and ``review/arbiter.py`` use ``overrides``
as a local name. The error direction is always **false-negative**, never false
positive — the lint under-reports, so the real debt is ``>= 41``. Per-kind
namespacing is a change to the definition, not to the implementation; it is not this
work package's to make.

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

Growth above the baseline FAILS; shrinkage WARNS (charter Burn-down Policy §a).

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

from tests.architectural._inert_slots import (
    ALLOWLIST,
    DISPOSITIONS,
    UNASSIGNED_OWNER,
    Baseline,
    BaselineEntry,
    BaselineError,
    InertSlot,
    find_inert_slots,
    load_baseline,
    owner_is_complete,
    ratchet,
    unresolved_by_completed_owners,
)

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
    flagged = {s.name for s in find_inert_slots(_REPO_ROOT)}

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
