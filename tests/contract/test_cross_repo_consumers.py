"""Cross-repo consumer smoke tests for pinned spec-kitty-events compatibility."""

from __future__ import annotations

import json
from importlib import resources


def test_spec_kitty_events_fixture_shape_matches_scope_b_contract() -> None:
    """Pinned downstream fixtures must retain canonical mission identity names."""
    import spec_kitty_events

    assert spec_kitty_events.__version__ == "3.0.0"

    fixture_dir = resources.files("spec_kitty_events") / "conformance" / "fixtures" / "events" / "valid"
    for fixture_name in ("mission_created.json", "mission_closed.json"):
        payload = json.loads((fixture_dir / fixture_name).read_text(encoding="utf-8"))
        assert payload["mission_slug"] == "mission-001"
        assert payload["mission_number"] == 1
        assert payload["mission_type"] == "software-dev"
        assert "feature_slug" not in payload
        assert "feature_number" not in payload
        assert "feature_type" not in payload
