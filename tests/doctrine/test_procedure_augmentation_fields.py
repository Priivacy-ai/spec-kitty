"""Cross-field validation tests for `Procedure.overrides` / `Procedure.enhances`.

WP05 of mission `charter-ux-and-org-pack-vocabulary-01KSAF14`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from doctrine.procedures.models import Procedure, ProcedureStep

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


def _build(**overrides: object) -> Procedure:
    base: dict[str, object] = {
        "schema_version": "1.0",
        "id": "test-procedure",
        "name": "Test Procedure",
        "purpose": "Test mutually-exclusive augmentation fields.",
        "entry_condition": "Test entry.",
        "exit_condition": "Test exit.",
        "steps": [ProcedureStep(title="Step One")],
    }
    base.update(overrides)
    return Procedure(**base)  # type: ignore[arg-type]


class TestProcedureAugmentationFields:
    def test_neither_set_loads(self) -> None:
        p = _build()
        assert p.overrides is None
        assert p.enhances is None

    def test_enhances_only_loads(self) -> None:
        p = _build(enhances="builtin-procedure-id")
        assert p.enhances == "builtin-procedure-id"
        assert p.overrides is None

    def test_overrides_only_loads(self) -> None:
        p = _build(overrides="builtin-procedure-id")
        assert p.overrides == "builtin-procedure-id"
        assert p.enhances is None

    def test_both_set_raises_mutually_exclusive(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _build(overrides="foo", enhances="bar")
        assert "mutually exclusive" in str(exc_info.value)
        assert "test-procedure" in str(exc_info.value)
