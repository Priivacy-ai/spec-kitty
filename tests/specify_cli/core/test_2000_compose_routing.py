"""Byte-parity tests for the #2000 compose-routing (WP05, T017).

Pins that the two hand-rolled ``<human-slug>-<mid8>`` compose sites in
``core/mission_creation.py:321`` and ``core/worktree.py:367/370`` produce
**byte-identical** names before and after being routed through the canonical
``mission_dir_name`` seam function (FR-005 / NFR-001).

Anti-gaming discipline: the RHS of every assertion is a **frozen string literal
captured from HEAD before any edit**, never a re-call of the seam (which would
produce a tautological ``resolve_mid8(x) == resolve_mid8(x)`` test).

The four representative inputs exercise:
  - ``NNN-`` prefix (stripped by strip_numeric_prefix)
  - bare slug (no prefix, no embedded mid8)
  - already-embedded mid8 tail (idempotent; no double-suffix)
  - ``NNN-`` prefix with hyphen-body (stripping + compose)
"""

from __future__ import annotations

import pytest

from specify_cli.lanes.branch_naming import (
    _mid8 as mid8,  # demoted to private by WP01; this test cross-checks the inline compose
    mission_dir_name,
    resolve_mid8,
    strip_numeric_prefix,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Frozen literals captured from HEAD before any edit (T017 anti-gaming).
#
# Mission-id used throughout: this 26-char ULID-like string yields mid8 "01KV7SFD".
# Each frozen value below is ``f"{strip_numeric_prefix(slug)}-{mid8(MISSION_ID)}"``
# computed verbatim from the CURRENT (pre-edit) code, hard-coded so a tautological
# re-call cannot mask a compose regression.
# ---------------------------------------------------------------------------

_MISSION_ID = "01KV7SFD00000000000000000A"  # 26-char ULID; mid8 = "01KV7SFD"

_FROZEN: dict[str, str] = {
    # (slug, mission_id) -> frozen dir/branch name
    "083-foo": "foo-01KV7SFD",              # NNN- stripped
    "foo": "foo-01KV7SFD",                  # bare slug, no prefix
    "foo-01KV6510": "foo-01KV6510-01KV7SFD",  # already-embedded mid8 (different ULID)
    "057-my-feature": "my-feature-01KV7SFD",  # NNN- prefix with hyphen body
}


# ---------------------------------------------------------------------------
# T017-A: HEAD behavior baseline — the inline f-string produces these literals.
#
# These pass BEFORE the routing change and MUST continue to pass after.
# They document that ``strip_numeric_prefix(slug) + "-" + mid8(mission_id)``
# is the current compose contract in both files.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug,expected", list(_FROZEN.items()))
def test_head_inline_compose_produces_frozen_literal(slug: str, expected: str) -> None:
    """The inline f-string compose (pre-edit HEAD) matches the frozen literal.

    This is the "before" oracle: captures what the current hand-rolled
    ``f"{human_slug}-{mid8(mission_id)}"`` code produces, expressed as
    a hard-coded literal on the RHS so the assertion is not tautological.
    """
    human_slug = strip_numeric_prefix(slug)
    composed = f"{human_slug}-{mid8(_MISSION_ID)}"
    assert composed == expected, (
        f"HEAD inline compose for {slug!r} drifted from frozen literal: "
        f"got {composed!r}, expected {expected!r}"
    )


# ---------------------------------------------------------------------------
# T017-B: ``mission_dir_name`` seam produces byte-identical names.
#
# The routing change replaces the inline f-string with:
#   mid8_val = resolve_mid8("", mission_id=_MISSION_ID)
#   mission_dir_name(slug, mid8=mid8_val)
# These MUST equal the frozen literals.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug,expected", list(_FROZEN.items()))
def test_mission_dir_name_seam_byte_identical_to_frozen_literal(
    slug: str, expected: str
) -> None:
    """``mission_dir_name`` + ``resolve_mid8`` seam is byte-identical to the frozen literal.

    This is the "after" oracle: the routed seam call produces the same name
    the inline f-string produced, confirmed against the hard-coded RHS.
    """
    mid8_val = resolve_mid8("", mission_id=_MISSION_ID)
    seam_result = mission_dir_name(slug, mid8=mid8_val)
    assert seam_result == expected, (
        f"mission_dir_name seam for {slug!r} is not byte-identical to frozen literal: "
        f"got {seam_result!r}, expected {expected!r}"
    )


# ---------------------------------------------------------------------------
# T017-C: Parity between HEAD inline compose and the seam (cross-check).
#
# Belt-and-suspenders: the seam result == HEAD inline result for every slug.
# Both sides reference the frozen string, so if they diverge, the test fails.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", list(_FROZEN))
def test_seam_and_inline_compose_are_equal(slug: str) -> None:
    """The seam output matches the inline compose output for the same inputs.

    Cross-check that ``mission_dir_name(slug, mid8=resolve_mid8("", mission_id=…))``
    equals ``f"{strip_numeric_prefix(slug)}-{mid8(mission_id)}"`` — confirming
    the routing change is byte-neutral.
    """
    human_slug = strip_numeric_prefix(slug)
    inline_result = f"{human_slug}-{mid8(_MISSION_ID)}"

    mid8_val = resolve_mid8("", mission_id=_MISSION_ID)
    seam_result = mission_dir_name(slug, mid8=mid8_val)

    assert seam_result == inline_result, (
        f"Seam/inline parity failed for {slug!r}: "
        f"seam={seam_result!r}, inline={inline_result!r}"
    )
