"""Unit tests for Toolguide model."""

import pytest
from pydantic import ValidationError

from doctrine.toolguides.models import Toolguide

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


class TestToolguide:
    def test_minimal_construction(self, sample_toolguide_data: dict) -> None:
        toolguide = Toolguide.model_validate(sample_toolguide_data)
        assert toolguide.id == "test-toolguide"
        assert toolguide.schema_version == "1.0"
        assert toolguide.commands == []

    def test_enriched_construction(self, enriched_toolguide_data: dict) -> None:
        toolguide = Toolguide.model_validate(enriched_toolguide_data)
        assert toolguide.tool == "git"
        assert len(toolguide.commands) == 2

    def test_frozen_model(self, sample_toolguide_data: dict) -> None:
        toolguide = Toolguide.model_validate(sample_toolguide_data)
        with pytest.raises(ValidationError):
            toolguide.title = "changed"  # type: ignore[misc]

    def test_invalid_guide_path_pattern_raises(self, sample_toolguide_data: dict) -> None:
        sample_toolguide_data["guide_path"] = "docs/guide.md"
        with pytest.raises(ValidationError):
            Toolguide.model_validate(sample_toolguide_data)

    def test_invalid_schema_version_raises(self, sample_toolguide_data: dict) -> None:
        sample_toolguide_data["schema_version"] = "2.0"
        with pytest.raises(ValidationError):
            Toolguide.model_validate(sample_toolguide_data)
