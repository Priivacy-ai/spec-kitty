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

Non-vacuity (NFR-001)
---------------------
``test_planted_producerless_slot_is_flagged`` plants a real violation and asserts RED.
Critically it calls **the same** :func:`find_inert_slots` as the shipped-tree
assertion, differing only in the tree it is pointed at. A self-mutation test that
reimplements the check inline is green forever while the production checker rots.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architectural._inert_slots import ALLOWLIST, InertSlot, find_inert_slots

_REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_shipped_tree_has_no_inert_slots() -> None:
    """The gate itself. Any finding here is real — do not add it to the allowlist."""
    found = find_inert_slots(_REPO_ROOT)

    assert found == [], (
        "declared slots that nothing populates:\n"
        + "\n".join(f"  - {s.name} declared at {s.declared_at}" for s in found)
        + "\n\nEach is either a producer that was never wired, or a declaration that "
        "should be deleted. Adding it to the allowlist is not one of the options."
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
