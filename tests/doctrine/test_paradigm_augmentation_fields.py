"""Cross-field validation tests for `Paradigm.overrides` / `Paradigm.enhances`.

WP05 of mission `charter-ux-and-org-pack-vocabulary-01KSAF14`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from doctrine.paradigms.models import Paradigm

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


def _build(**overrides: object) -> Paradigm:
    base: dict[str, object] = {
        "schema_version": "1.0",
        "id": "test-paradigm",
        "name": "Test Paradigm",
        "summary": "A test paradigm.",
    }
    base.update(overrides)
    return Paradigm(**base)  # type: ignore[arg-type]


class TestParadigmAugmentationFields:
    def test_neither_set_loads(self) -> None:
        p = _build()
        assert p.overrides is None
        assert p.enhances is None

    def test_enhances_only_loads(self) -> None:
        p = _build(enhances="builtin-paradigm-id")
        assert p.enhances == "builtin-paradigm-id"
        assert p.overrides is None

    def test_overrides_only_loads(self) -> None:
        p = _build(overrides="builtin-paradigm-id")
        assert p.overrides == "builtin-paradigm-id"
        assert p.enhances is None

    def test_both_set_raises_mutually_exclusive(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _build(overrides="foo", enhances="bar")
        assert "mutually exclusive" in str(exc_info.value)
        assert "test-paradigm" in str(exc_info.value)
