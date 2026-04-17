"""Regression tests for software-dev action index doctrine wiring."""

import pytest

from doctrine.missions import MissionTemplateRepository

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


def test_specify_action_index_includes_example_mapping_assets() -> None:
    repo = MissionTemplateRepository.default()
    index = repo.get_action_index("software-dev", "specify")

    assert index is not None
    assert index.parsed["directives"] == [
        "010-specification-fidelity-requirement",
        "035-examples-are-source-of-truth",
        "003-decision-documentation-requirement",
    ]
    assert index.parsed["procedures"] == ["example-mapping-workshop"]


def test_review_action_index_includes_living_documentation_sync() -> None:
    repo = MissionTemplateRepository.default()
    index = repo.get_action_index("software-dev", "review")

    assert index is not None
    assert "035-examples-are-source-of-truth" in index.parsed["directives"]
    assert index.parsed["tactics"][0] == "living-documentation-sync"
