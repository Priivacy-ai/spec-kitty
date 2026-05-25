"""Cross-field validation tests for `Styleguide.overrides` / `Styleguide.enhances`.

WP05 of mission `charter-ux-and-org-pack-vocabulary-01KSAF14`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from doctrine.styleguides.models import Styleguide

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


def _build(**overrides: object) -> Styleguide:
    base: dict[str, object] = {
        "schema_version": "1.0",
        "id": "test-style",
        "title": "Test Styleguide",
        "scope": "code",
        "principles": ["Write clear code"],
    }
    base.update(overrides)
    return Styleguide(**base)  # type: ignore[arg-type]


class TestStyleguideAugmentationFields:
    def test_neither_set_loads(self) -> None:
        sg = _build()
        assert sg.overrides is None
        assert sg.enhances is None

    def test_enhances_only_loads(self) -> None:
        sg = _build(enhances="builtin-style-id")
        assert sg.enhances == "builtin-style-id"
        assert sg.overrides is None

    def test_overrides_only_loads(self) -> None:
        sg = _build(overrides="builtin-style-id")
        assert sg.overrides == "builtin-style-id"
        assert sg.enhances is None

    def test_both_set_raises_mutually_exclusive(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _build(overrides="foo", enhances="bar")
        assert "mutually exclusive" in str(exc_info.value)
        assert "test-style" in str(exc_info.value)
