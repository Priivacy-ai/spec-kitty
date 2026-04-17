"""Regression tests for software-dev action index doctrine wiring."""

import pytest

from doctrine.missions import MissionTemplateRepository

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

def test_review_action_index_includes_living_documentation_sync() -> None:
    repo = MissionTemplateRepository.default()
    index = repo.get_action_index("software-dev", "review")

    assert index is not None
    assert "037-examples-are-source-of-truth" in index.parsed["directives"]
    assert index.parsed["tactics"][0] == "living-documentation-sync"
