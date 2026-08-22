"""Unit tests for the shared runtime mission-type reader ``read_mission_type``.

rc3 M5 / FR-001 / FR-002 / FR-003: ``read_mission_type(meta)`` is the one
dict-in reader every in-scope mission-type reader delegates to. It reads only
the canonical ``mission_type`` field (legacy ``mission`` is retired), routes the
value through :func:`canonical_mission_type_key`, and returns ``None`` for a
typeless value — never a ``software-dev`` default.
"""

from __future__ import annotations

from typing import Any

import pytest

from charter.mission_type_key import read_mission_type

pytestmark = [pytest.mark.unit]


class TestReadMissionType:
    """Canonical-field-only, no legacy fallback, no default."""

    @pytest.mark.parametrize(
        ("meta", "expected"),
        [
            ({"mission_type": "software-dev"}, "software-dev"),
            ({"mission_type": "research"}, "research"),
            ({"mission_type": "  documentation  "}, "documentation"),  # stripped
            ({"mission_type": "a-project-specific-type"}, "a-project-specific-type"),
        ],
    )
    def test_canonical_field_resolves(self, meta: dict[str, Any], expected: str) -> None:
        assert read_mission_type(meta) == expected

    @pytest.mark.parametrize(
        "meta",
        [
            {},  # absent
            {"mission_type": ""},  # blank
            {"mission_type": "   "},  # whitespace-only
            {"mission_type": None},  # explicit null
            {"mission_type": 123},  # non-string
            {"mission_type": ["research"]},  # non-string container
        ],
    )
    def test_typeless_or_malformed_degrades_to_none(self, meta: dict[str, Any]) -> None:
        result = read_mission_type(meta)
        assert result is None
        assert result != "software-dev"

    @pytest.mark.parametrize(
        "meta",
        [
            {"mission": "software-dev"},  # legacy-only
            {"mission": "research"},  # legacy-only
        ],
    )
    def test_legacy_mission_field_is_retired(self, meta: dict[str, Any]) -> None:
        """FR-002: a legacy ``{"mission": …}``-only mission no longer resolves.

        It must be backfilled (``spec-kitty migrate backfill-mission-type``)
        before it resolves again — the deliberate M5 behavior change.
        """
        assert read_mission_type(meta) is None

    def test_canonical_field_wins_when_both_present(self) -> None:
        """A mission carrying both fields resolves the canonical one only."""
        assert read_mission_type({"mission_type": "research", "mission": "software-dev"}) == "research"
