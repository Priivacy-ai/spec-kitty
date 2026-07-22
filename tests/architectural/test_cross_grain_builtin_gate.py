"""FR-013 built-in cross-grain structural gate (#2666, WP05).

``charter.action_grain.scan_builtin_cross_grain_duplicates`` is the single
IC-11 dup-scan authority (C-002): for every shipped mission type it unions
the type grain (``governance-profile.yaml``) with the action grain
(``actions/*/index.yaml``) and raises
``charter.mission_type_profiles.CrossGrainDoubleDeclarationError`` the moment
one artifact URN is declared in both.

``tests/doctrine/drg/test_cross_grain_integrity.py`` (owned elsewhere, not
touched by this WP) is the finer-grained structural home for that gate plus
its non-vacuity twin. This module is a **dedicated, independent** CI
structural gate on the same scan (WP05 T023): it runs
``scan_builtin_cross_grain_duplicates()`` against the shipped tree and pins
that the scan actually covers the full built-in roster (returns every
shipped mission type, disjoint), so a regression in this gate does not
silently hide behind the doctrine-suite's broader run.
"""

from __future__ import annotations

import pytest

from charter.action_grain import scan_builtin_cross_grain_duplicates
from doctrine.missions.mission_type_repository import builtin_mission_type_id_set

pytestmark = [pytest.mark.architectural]


def test_shipped_tree_is_cross_grain_disjoint_and_covers_every_type() -> None:
    """Every shipped mission type is scanned and confirmed disjoint (FR-013)."""
    scanned = scan_builtin_cross_grain_duplicates()

    # Disjoint: a collision would have raised CrossGrainDoubleDeclarationError
    # rather than returning, so a returned value at all is already a partial
    # proof; the roster equality below closes the remaining gap (no shipped
    # type silently skipped).
    assert set(scanned) == builtin_mission_type_id_set()
    # No duplicate scan entries -- one pass per shipped type.
    assert len(scanned) == len(set(scanned))
