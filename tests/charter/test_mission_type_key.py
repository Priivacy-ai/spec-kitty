"""Unit tests for the single boundary-safe mission-type canonicalizer.

Covers WP02 / FR-012 / FR-001 / FR-003a: the one canonicalizer that both the
``charter`` and ``specify_cli`` layers consume. It normalizes a raw mission-type
string to its canonical key and returns ``None`` for a typeless value — it never
bakes in a ``software-dev`` default.
"""

from __future__ import annotations

import pytest

from charter.activation.mission_type_key import canonical_mission_type_key

pytestmark = [pytest.mark.unit]


class TestCanonicalMissionTypeKey:
    """The canonicalizer is a pure whitespace-normalizer with no default."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("software-dev", "software-dev"),
            ("research", "research"),
            ("documentation", "documentation"),
            ("  research  ", "research"),  # surrounding whitespace stripped
            ("a-project-specific-type", "a-project-specific-type"),
        ],
    )
    def test_recognised_and_arbitrary_keys_normalize_to_stripped_value(self, raw: str, expected: str) -> None:
        assert canonical_mission_type_key(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "   ", "\t\n"])
    def test_typeless_input_degrades_to_none_never_software_dev(self, raw: str | None) -> None:
        """FR-003a: absence maps to ``None`` — never a ``software-dev`` load."""
        result = canonical_mission_type_key(raw)
        assert result is None
        assert result != "software-dev"
