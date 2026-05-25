"""Cross-field validation tests for `AgentProfile.overrides` / `AgentProfile.enhances`.

WP05 of mission `charter-ux-and-org-pack-vocabulary-01KSAF14`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from doctrine.agent_profiles.profile import AgentProfile, Specialization

pytestmark = [pytest.mark.doctrine]


def _build(**overrides: object) -> AgentProfile:
    base: dict[str, object] = {
        "profile_id": "test-profile",
        "name": "Test Profile",
        "purpose": "Validate augmentation field semantics.",
        "specialization": Specialization(primary_focus="Testing"),
        "roles": ["implementer"],
    }
    base.update(overrides)
    return AgentProfile(**base)  # type: ignore[arg-type]


class TestAgentProfileAugmentationFields:
    def test_neither_set_loads(self) -> None:
        profile = _build()
        assert profile.overrides is None
        assert profile.enhances is None

    def test_enhances_only_loads(self) -> None:
        profile = _build(enhances="implementer-ivan")
        assert profile.enhances == "implementer-ivan"
        assert profile.overrides is None

    def test_overrides_only_loads(self) -> None:
        profile = _build(overrides="implementer-ivan")
        assert profile.overrides == "implementer-ivan"
        assert profile.enhances is None

    def test_both_set_raises_mutually_exclusive(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _build(overrides="foo", enhances="bar")
        assert "mutually exclusive" in str(exc_info.value)
        assert "test-profile" in str(exc_info.value)
