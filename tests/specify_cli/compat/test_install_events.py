"""Unit tests for UvToolInstallationVerified and VerificationConfidence (WP01 T005).

Covers:
- Construction with all 4 fields
- VerificationConfidence enum membership and string values
- Frozen constraint (FrozenInstanceError on field assignment)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.compat.install_events import (
    UvToolInstallationVerified,
    VerificationConfidence,
)


pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# VerificationConfidence enum
# ---------------------------------------------------------------------------


class TestVerificationConfidence:
    def test_has_low_medium_high_members(self) -> None:
        names = {m.name for m in VerificationConfidence}
        assert names == {"LOW", "MEDIUM", "HIGH"}

    @pytest.mark.parametrize(
        "member,expected_value",
        [
            (VerificationConfidence.LOW, "low"),
            (VerificationConfidence.MEDIUM, "medium"),
            (VerificationConfidence.HIGH, "high"),
        ],
    )
    def test_string_values(self, member: VerificationConfidence, expected_value: str) -> None:
        assert str(member) == expected_value
        assert member.value == expected_value


# ---------------------------------------------------------------------------
# UvToolInstallationVerified dataclass
# ---------------------------------------------------------------------------


class TestUvToolInstallationVerified:
    def test_construct_with_all_fields(self) -> None:
        receipt = Path("/home/user/.local/share/uv/tools/spec-kitty-cli/uv-receipt.toml")
        event = UvToolInstallationVerified(
            receipt_path=receipt,
            entrypoint_match=True,
            package_binding="spec-kitty-cli==3.2.0",
            confidence=VerificationConfidence.HIGH,
        )
        assert event.receipt_path == receipt
        assert event.entrypoint_match is True
        assert event.package_binding == "spec-kitty-cli==3.2.0"
        assert event.confidence == VerificationConfidence.HIGH

    def test_construct_with_receipt_path_none(self) -> None:
        event = UvToolInstallationVerified(
            receipt_path=None,
            entrypoint_match=False,
            package_binding="unknown",
            confidence=VerificationConfidence.LOW,
        )
        assert event.receipt_path is None
        assert event.entrypoint_match is False
        assert event.confidence == VerificationConfidence.LOW

    def test_confidence_medium(self) -> None:
        event = UvToolInstallationVerified(
            receipt_path=None,
            entrypoint_match=False,
            package_binding="spec-kitty-cli==3.2.0",
            confidence=VerificationConfidence.MEDIUM,
        )
        assert event.confidence == VerificationConfidence.MEDIUM

    def test_frozen_constraint(self) -> None:
        event = UvToolInstallationVerified(
            receipt_path=None,
            entrypoint_match=True,
            package_binding="spec-kitty-cli==3.2.0",
            confidence=VerificationConfidence.HIGH,
        )
        with pytest.raises((AttributeError, TypeError)):
            event.entrypoint_match = False  # type: ignore[misc]
