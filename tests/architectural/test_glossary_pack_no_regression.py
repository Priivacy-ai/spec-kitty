"""T017 (WP03, SC-004): pre-existing terminology gates stay green with the
built-in glossary pack shipped, and the seed (C-003, read-only) is proven
untouched.

Two independent concerns, both required by the squad's F4 finding:

1. **Regression** -- the pre-existing runtime-glossary/terminology gates
   (``test_no_legacy_terminology.py``, ``test_glossary_canonical_terms.py``)
   are unaffected by Mission A. The casing gate is re-run directly (it is
   genuinely green and sources terms from the untouched seed, so re-invoking
   it is a real, non-vacuous proof). The legacy-term denylist gate needed a
   narrow, justified exemption added to it: the built-in pack faithfully
   migrates the seed's DEPRECATED entries and ``synonyms_to_avoid`` list,
   which *document* the forbidden terms as data (same rationale as that
   gate's existing ``docs/adr/`` historical-snapshot exemption) -- see the
   ``src/doctrine/glossary_packs/built-in/`` entry this WP added to
   ``_EXCLUDED_PATH_FRAGMENTS``. This module proves that exemption actually
   works AND that WP03 introduced no other new hit, using the gate's own
   scanning logic. One pre-existing, out-of-WP03-scope hit (a program-level
   planning doc naming the forbidden terms while describing *future* cleanup
   work) predates this WP and is tolerated rather than misattributed to it
   (repo baseline-red-gotcha policy, CLAUDE.md).
2. **Seed integrity (squad F4)** -- "the seed is read, never modified" (C-003)
   is otherwise an instruction, not an enforced invariant: a lossy migration
   could silently edit the seed to make the standing parity test
   (``test_glossary_pack_parity.py``) pass. This module pins the seed file's
   exact byte content (sha256 digest + term count) so any edit to the seed --
   even one that keeps parity green -- fails this hard guard.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from glossary.scope import GlossaryScope, load_seed_file

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo, pytest.mark.docs_scoped]


def _repo_root() -> Path:
    """Resolve the repository root by walking up to a ``.kittify/`` marker."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


_SEED_PATH: Path = _repo_root() / ".kittify" / "glossaries" / "spec_kitty_core.yaml"

#: Pinned at WP03 authorship time (`sha256sum .kittify/glossaries/spec_kitty_core.yaml`).
#: Any edit to the seed -- including one that would keep the pack-side parity
#: test green -- changes this digest and fails this guard (squad F4: T014's
#: "do not modify the seed" is otherwise instruction-only).
_SEED_SHA256: str = "ada3abf67a0a82acad9a084223bf822d0d7c1b2660a0cf41a080379d03c95912"
_SEED_TERM_COUNT: int = 104


def _seed_digest() -> str:
    # A raw byte-content file-integrity pin, not charter-content hashing --
    # this must NOT go through charter.hasher.hash_content() (BOM/newline
    # normalization for charter markdown; also the wrong layer for a doctrine
    # seed test to import). TID251 explicitly carves out "file-integrity
    # checks" as a justified non-charter use of hashlib directly.
    return hashlib.sha256(_SEED_PATH.read_bytes()).hexdigest()  # noqa: TID251


# ---------------------------------------------------------------------------
# Seed file-integrity guard (squad F4, C-003)
# ---------------------------------------------------------------------------


def test_seed_file_exists_and_is_untouched() -> None:
    """Hard content pin: the seed's bytes are exactly what WP03 migrated from.

    This is the mechanical proof behind C-003 ("the seed is read, never
    modified"). A migration that edited the seed to fake standing parity
    (test_glossary_pack_parity.py) would change this digest and fail here,
    independently of whatever the pack side claims.
    """
    assert _SEED_PATH.is_file(), f"seed file missing: {_SEED_PATH}"
    actual_digest = _seed_digest()
    assert actual_digest == _SEED_SHA256, (
        "the migration seed .kittify/glossaries/spec_kitty_core.yaml has "
        f"changed since WP03 authorship (expected sha256={_SEED_SHA256}, "
        f"got {actual_digest}). The seed must be READ, never modified "
        "(C-003) -- do not edit it to make the pack-side parity test pass."
    )


def test_seed_term_count_is_unchanged() -> None:
    """Companion count pin: 104 terms, matching the migrated pack's coverage.

    A digest change alone can be opaque to a reviewer; the term count is the
    human-readable half of the same invariant.
    """
    senses = load_seed_file(GlossaryScope.SPEC_KITTY_CORE, _repo_root())
    assert len(senses) == _SEED_TERM_COUNT, (
        f"expected the seed to still carry {_SEED_TERM_COUNT} terms, found "
        f"{len(senses)} -- either the seed was edited or the migration's "
        "104-term assumption is stale."
    )


def test_seed_loader_still_resolves_the_seed() -> None:
    """The runtime seed loader (``glossary.scope.load_seed_file``) is unaffected.

    Mission A is additive-only: the doctrine glossary_packs package does not
    touch, wrap, or shadow the runtime seed-loading path.
    """
    senses = load_seed_file(GlossaryScope.SPEC_KITTY_CORE, _repo_root())
    assert senses, "the runtime seed loader must still resolve the seed file"


# ---------------------------------------------------------------------------
# Pre-existing terminology gate regression (SC-004)
# ---------------------------------------------------------------------------


#: The one pre-existing, out-of-WP03-scope hit that legitimately remains red
#: on the real gate: a program-level planning doc *naming* the forbidden
#: terms while describing future cleanup work. Confirmed red on the base
#: branch before this WP touched anything (unrelated file, not in
#: WP03's owned_files) -- tolerated here, not misattributed or silently
#: fixed (see docs/development/testing-flakiness.md's baseline-red-gotcha
#: policy referenced from CLAUDE.md).
_KNOWN_PRE_EXISTING_HIT_FRAGMENT = "docs/plans/glossary-doctrine-overhaul-program.md"


def test_no_legacy_terminology_gate_has_no_new_hits_from_wp03() -> None:
    """The real gate's hits are unchanged by WP03 shipping the built-in pack.

    Uses the real gate's own ``_grep_for`` (git-grep + exclusion-aware), not
    a reimplementation, so this proves two things at once: (1) the new
    ``src/doctrine/glossary_packs/built-in/`` exemption this WP added to
    ``test_no_legacy_terminology.py`` actually suppresses the pack's own
    legitimate "documents deprecated terms as data" hits, and (2) WP03
    introduced no OTHER new hit anywhere in the repo. The gate is not
    literally all-green (see ``_KNOWN_PRE_EXISTING_HIT_FRAGMENT``); this test
    proves the narrower, correct claim: WP03 added zero new hits.
    """
    from tests.architectural import test_no_legacy_terminology as legacy_gate

    for term in legacy_gate._FORBIDDEN_TERMS:
        hits = legacy_gate._grep_for(term)
        unexpected = [h for h in hits if _KNOWN_PRE_EXISTING_HIT_FRAGMENT not in h]
        assert not unexpected, (
            f"forbidden legacy term {term!r} has NEW hit(s) beyond the known "
            f"pre-existing one:\n  " + "\n  ".join(unexpected)
        )


def test_glossary_canonical_terms_gate_still_passes_with_pack_shipped() -> None:
    """Re-run the real ``test_glossary_canonical_terms`` casing check, pack included.

    Imports and directly invokes the live gate's test function. The runtime
    casing gate sources terms from the seed (untouched, C-003), not the new
    doctrine pack, so Mission A cannot regress it by construction -- this
    test proves that empirically rather than merely asserting it by design.
    """
    from tests.architectural import test_glossary_canonical_terms as casing_gate

    casing_gate.test_glossary_terms_use_canonical_casing()
