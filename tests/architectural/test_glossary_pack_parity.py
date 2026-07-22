"""T016 (WP03, NFR-002): standing pack<->seed full-key parity + synonyms round-trip.

Squad F2 (post-tasks anti-laziness lens) is the load-bearing constraint here:
the assertion MUST be **seed-driven**, not pack-driven. For every one of the
104 seed terms, for **every key actually present on that seed term**
(including the sparse optionals -- ``see_also`` on 1 term,
``introduced_in_mission`` on 2, ``synonyms_to_avoid`` on 3), the migrated pack
must carry the identical value. A pack-side comparison that only checks
fields present on the pack (treating ``None == absent``) would let a dropped
sparse field pass green -- that is the exact vacuity trap this test is
written to avoid.

This is a **standing** invariant (not a one-shot migration snapshot): it
stays green only as long as the built-in pack and the seed agree on every
field, for every term, and will go red the moment either side drifts --
until Mission C retires the seed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from doctrine.glossary_packs.repository import GlossaryPackRepository

pytestmark = [pytest.mark.architectural, pytest.mark.doctrine]


def _repo_root() -> Path:
    """Resolve the repository root by walking up to a ``.kittify/`` marker."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


_SEED_PATH: Path = _repo_root() / ".kittify" / "glossaries" / "spec_kitty_core.yaml"
_BUILT_IN_DIR: Path = _repo_root() / "src" / "doctrine" / "glossary_packs" / "built-in"
_PACK_ID = "spec-kitty-core"

#: The optional keys the seed carries beyond the four obvious fields
#: (surface/definition/confidence/status). Populated on a small, known subset
#: of the 104 terms -- exactly what makes a pack-side-only check vacuous
#: (squad F2): a dropped field on the ONE ``see_also`` term or the TWO
#: ``introduced_in_mission`` terms would be invisible to a check that only
#: iterates the pack's own populated fields.
_OPTIONAL_SEED_KEYS: tuple[str, ...] = (
    "see_also",
    "introduced_in_mission",
    "synonyms_to_avoid",
)

#: Expected occurrence counts in the seed, pinned so a future seed edit that
#: silently drops or adds a sparse-field occurrence is itself caught (not just
#: whether the pack mirrors whatever the seed happens to have right now).
_EXPECTED_OPTIONAL_KEY_COUNTS: dict[str, int] = {
    "see_also": 1,
    "introduced_in_mission": 2,
    "synonyms_to_avoid": 3,
}


def _load_seed_terms() -> list[dict[str, Any]]:
    yaml = YAML(typ="safe")
    with _SEED_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.load(fh)
    return list(data["terms"])


def _stringify_see_also_entry(entry: Any) -> str:
    """Deterministically flatten one seed ``see_also`` entry to a string.

    Mirrors the migration transform exactly (the ratified ``GlossaryTerm``
    schema types ``see_also`` as ``list[str] | None``; the seed's one real
    occurrence is a list of small heterogeneous dicts, e.g.
    ``{tactic: ..., path: ...}`` / ``{fr: ..., description: ...}``). Plain
    string entries pass through unchanged. Recomputed independently here (not
    imported from the migration tooling) so this test proves the *shipped
    pack file* actually carries the transformed value, not merely that the
    migration script once produced it.
    """
    if isinstance(entry, str):
        return entry
    return ", ".join(f"{key}: {value}" for key, value in entry.items())


def _expected_see_also(seed_value: list[Any]) -> list[str]:
    return [_stringify_see_also_entry(entry) for entry in seed_value]


@pytest.fixture(scope="module")
def seed_terms() -> list[dict[str, Any]]:
    return _load_seed_terms()


@pytest.fixture(scope="module")
def pack_terms_by_surface() -> dict[str, Any]:
    repo = GlossaryPackRepository(built_in_dir=_BUILT_IN_DIR)
    pack = repo.get(_PACK_ID)
    assert pack is not None, f"built-in pack {_PACK_ID!r} failed to load from {_BUILT_IN_DIR}"
    return {term.surface: term for term in pack.terms}


# ---------------------------------------------------------------------------
# Bulk shape parity
# ---------------------------------------------------------------------------


def test_term_count_parity(seed_terms: list[dict[str, Any]], pack_terms_by_surface: dict[str, Any]) -> None:
    assert len(seed_terms) == 104, "seed term count drifted from the migrated assumption"  # golden-count: cardinality-is-contract
    assert len(pack_terms_by_surface) == len(seed_terms)


def test_surface_set_parity(seed_terms: list[dict[str, Any]], pack_terms_by_surface: dict[str, Any]) -> None:
    """No term is missing from the pack and no extra term was invented."""
    seed_surfaces = {t["surface"] for t in seed_terms}
    assert set(pack_terms_by_surface.keys()) == seed_surfaces


# ---------------------------------------------------------------------------
# T016 core: seed-driven, full-key-set parity (squad F2)
# ---------------------------------------------------------------------------


def test_every_seed_term_every_present_key_round_trips_identically(
    seed_terms: list[dict[str, Any]],
    pack_terms_by_surface: dict[str, Any],
) -> None:
    """The seed-driven parity assertion (squad F2 -- non-negotiable shape).

    Iterates EVERY seed term and, for that term, EVERY key present in the
    seed dict (not the pack's dict) -- so a field present on the seed but
    dropped from the pack shows up as a missing key on the *seed* side of the
    comparison, which this loop always visits, rather than being silently
    skipped by a pack-side-only iteration.
    """
    mismatches: list[str] = []

    for seed_term in seed_terms:
        surface = seed_term["surface"]
        pack_term = pack_terms_by_surface.get(surface)
        if pack_term is None:
            mismatches.append(f"{surface!r}: missing from pack entirely")
            continue

        for key, seed_value in seed_term.items():
            if key == "surface":
                continue  # the join key itself, not a field to compare

            if key == "confidence":
                # confidence compares as float (contract explicit carve-out).
                if pack_term.confidence != float(seed_value):
                    mismatches.append(
                        f"{surface!r}.confidence: seed={seed_value!r} "
                        f"pack={pack_term.confidence!r}"
                    )
                continue

            if key == "see_also":
                expected = _expected_see_also(seed_value)
                if pack_term.see_also != expected:
                    mismatches.append(
                        f"{surface!r}.see_also: expected={expected!r} "
                        f"pack={pack_term.see_also!r}"
                    )
                continue

            # definition, status, introduced_in_mission, synonyms_to_avoid:
            # direct identity comparison (synonyms_to_avoid is already
            # list[str] shaped in the seed -- no transform needed).
            pack_value = getattr(pack_term, key, "<MISSING ATTRIBUTE>")
            if pack_value != seed_value:
                mismatches.append(
                    f"{surface!r}.{key}: seed={seed_value!r} pack={pack_value!r}"
                )

    assert not mismatches, (
        "seed<->pack parity broke for the following seed-present field(s) "
        "(NFR-002 standing invariant):\n  " + "\n  ".join(mismatches)
    )


def test_terms_with_no_optional_seed_fields_have_none_on_pack_side(
    seed_terms: list[dict[str, Any]],
    pack_terms_by_surface: dict[str, Any],
) -> None:
    """A seed term that carries NO optional key must load with None defaults.

    Complements the seed-driven loop above: proves the migration did not
    invent values for terms the seed never populated (the other direction of
    zero-loss -- zero-invention).
    """
    violations: list[str] = []
    for seed_term in seed_terms:
        surface = seed_term["surface"]
        pack_term = pack_terms_by_surface[surface]
        for key in _OPTIONAL_SEED_KEYS:
            if key in seed_term:
                continue
            if getattr(pack_term, key) is not None:
                violations.append(
                    f"{surface!r}.{key}: seed has no value but pack has "
                    f"{getattr(pack_term, key)!r}"
                )

    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# Explicit sparse-field occurrence counts + round-trip (US3 / squad F2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", sorted(_EXPECTED_OPTIONAL_KEY_COUNTS))
def test_sparse_optional_key_occurrence_count_pinned(
    key: str, seed_terms: list[dict[str, Any]]
) -> None:
    """Pin the exact occurrence count for each sparse optional seed key.

    Guards the guard: if the seed's sparse-field distribution ever changes,
    this fails loudly rather than the parity test silently covering fewer
    cases than the squad intended.
    """
    count = sum(1 for t in seed_terms if key in t)
    assert count == _EXPECTED_OPTIONAL_KEY_COUNTS[key], (
        f"expected {_EXPECTED_OPTIONAL_KEY_COUNTS[key]} seed term(s) with "
        f"{key!r}, found {count}"
    )


def test_synonyms_to_avoid_round_trips_for_all_three_real_terms(
    seed_terms: list[dict[str, Any]],
    pack_terms_by_surface: dict[str, Any],
) -> None:
    """US3: the 3 real ``synonyms_to_avoid`` seed terms round-trip exactly."""
    seed_terms_with_synonyms = [t for t in seed_terms if "synonyms_to_avoid" in t]
    assert len(seed_terms_with_synonyms) == 3  # golden-count: cardinality-is-contract

    for seed_term in seed_terms_with_synonyms:
        surface = seed_term["surface"]
        pack_term = pack_terms_by_surface[surface]
        assert pack_term.synonyms_to_avoid == seed_term["synonyms_to_avoid"], (
            f"{surface!r}: synonyms_to_avoid did not round-trip "
            f"(seed={seed_term['synonyms_to_avoid']!r}, "
            f"pack={pack_term.synonyms_to_avoid!r})"
        )


def test_see_also_round_trips_for_the_one_real_term(
    seed_terms: list[dict[str, Any]],
    pack_terms_by_surface: dict[str, Any],
) -> None:
    """The 1 real ``see_also`` seed term round-trips via the documented
    dict-to-string flattening (see :func:`_stringify_see_also_entry`).
    """
    seed_terms_with_see_also = [t for t in seed_terms if "see_also" in t]
    assert len(seed_terms_with_see_also) == 1  # golden-count: cardinality-is-contract

    seed_term = seed_terms_with_see_also[0]
    surface = seed_term["surface"]
    pack_term = pack_terms_by_surface[surface]
    expected = _expected_see_also(seed_term["see_also"])
    assert pack_term.see_also == expected


def test_introduced_in_mission_round_trips_for_both_real_terms(
    seed_terms: list[dict[str, Any]],
    pack_terms_by_surface: dict[str, Any],
) -> None:
    seed_terms_with_intro = [t for t in seed_terms if "introduced_in_mission" in t]
    assert len(seed_terms_with_intro) == 2  # golden-count: cardinality-is-contract

    for seed_term in seed_terms_with_intro:
        surface = seed_term["surface"]
        pack_term = pack_terms_by_surface[surface]
        assert pack_term.introduced_in_mission == seed_term["introduced_in_mission"]
