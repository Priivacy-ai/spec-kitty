"""Unit tests for the single boundary-safe mission-type canonicalizer.

Covers WP02 / FR-012 / FR-001 / FR-003a: the one canonicalizer that both the
``charter`` and ``specify_cli`` layers consume. It normalizes a raw mission-type
string to its canonical key and returns ``None`` for a typeless value — it never
bakes in a ``software-dev`` default.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from charter.mission_type_key import canonical_mission_type_key

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
    def test_recognised_and_arbitrary_keys_normalize_to_stripped_value(
        self, raw: str, expected: str
    ) -> None:
        assert canonical_mission_type_key(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "   ", "\t\n"])
    def test_typeless_input_degrades_to_none_never_software_dev(
        self, raw: str | None
    ) -> None:
        """FR-003a: absence maps to ``None`` — never a ``software-dev`` load."""
        result = canonical_mission_type_key(raw)
        assert result is None
        assert result != "software-dev"

    def test_does_not_lowercase_or_otherwise_rewrite_the_key(self) -> None:
        """Canonicalization is strip-only; it must not alter case (NFR-001)."""
        assert canonical_mission_type_key("Research") == "Research"


class TestCanonicalizerBoundarySafety:
    """C-001: the canonicalizer must not import ``specify_cli`` at module level."""

    def test_module_has_no_module_level_specify_cli_import(self) -> None:
        module_path = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "charter"
            / "mission_type_key.py"
        )
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module is None or not node.module.startswith(
                    "specify_cli"
                ), f"forbidden specify_cli import: {node.module}"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(
                        "specify_cli"
                    ), f"forbidden specify_cli import: {alias.name}"
