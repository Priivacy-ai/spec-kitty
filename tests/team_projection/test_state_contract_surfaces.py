"""D1-T1 state-surface registration (§3.5): the five new team_projection
paths are registered in ``state/contract.py`` as DERIVED/IGNORED, mirroring
the ``derived_mission_views`` pattern already used for status/board-summary.
"""

from __future__ import annotations

import pytest

from specify_cli.state.contract import (
    STATE_SURFACES,
    AuthorityClass,
    GitClass,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_EXPECTED_PATH_PATTERNS = frozenset(
    {
        ".kittify/derived/<mission_slug>/team-snapshot.json",
        ".kittify/derived/team-index.json",
        ".kittify/derived/<mission_slug>/public/mission.json",
        ".kittify/derived/public/index.json",
        ".kittify/derived/attestation-manifest.json",
    }
)


def test_all_five_team_projection_surfaces_registered():
    patterns = {s.path_pattern for s in STATE_SURFACES}
    missing = _EXPECTED_PATH_PATTERNS - patterns
    assert not missing, f"missing team_projection state surfaces: {missing}"


def test_team_projection_surfaces_are_derived_and_ignored():
    surfaces = [s for s in STATE_SURFACES if s.path_pattern in _EXPECTED_PATH_PATTERNS]
    assert len(surfaces) == len(_EXPECTED_PATH_PATTERNS)
    for surface in surfaces:
        assert surface.authority == AuthorityClass.DERIVED
        assert surface.git_class == GitClass.IGNORED
        assert surface.owner_module == "team_projection"
        assert surface.creation_trigger == "spec-kitty team-projection publish"
