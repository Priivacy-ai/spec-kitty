"""Cross-field validation tests for `Tactic.overrides` / `Tactic.enhances`.

WP05 of mission `charter-ux-and-org-pack-vocabulary-01KSAF14` adds two
optional declarative fields (`overrides`, `enhances`) plus a
`_augmentation_intent_is_exclusive` validator that rejects both-set.
Tests cover the four reachable shapes: neither, enhances-only,
overrides-only, both-set (the validator path).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from doctrine.tactics.models import Tactic, TacticStep

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


def _build(**overrides: object) -> Tactic:
    base: dict[str, object] = {
        "schema_version": "1.0",
        "id": "test-tactic",
        "name": "Test Tactic",
        "steps": [TacticStep(title="Step One")],
    }
    base.update(overrides)
    return Tactic(**base)  # type: ignore[arg-type]


class TestTacticAugmentationFields:
    """Four-case matrix from WP05."""

    def test_neither_set_loads(self) -> None:
        """Backward compatibility (NFR-004): existing fixtures keep loading."""
        tactic = _build()
        assert tactic.overrides is None
        assert tactic.enhances is None

    def test_enhances_only_loads(self) -> None:
        tactic = _build(enhances="builtin-tactic-id")
        assert tactic.enhances == "builtin-tactic-id"
        assert tactic.overrides is None

    def test_overrides_only_loads(self) -> None:
        tactic = _build(overrides="builtin-tactic-id")
        assert tactic.overrides == "builtin-tactic-id"
        assert tactic.enhances is None

    def test_both_set_raises_mutually_exclusive(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _build(overrides="foo", enhances="bar")
        # Error message must include the canonical wording for operator clarity.
        assert "mutually exclusive" in str(exc_info.value)
        # And must include the artifact ID so the operator knows which YAML to fix.
        assert "test-tactic" in str(exc_info.value)
