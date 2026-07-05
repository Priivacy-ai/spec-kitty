"""Unit tests for the shared pydantic wire-shaping primitive (#2407).

Extracted from the duplicate exclude_none/keep-none dance that used to live
independently in ``core/mission_payload.py`` and ``sync/emitter.py``'s
``_build_payload_via_model``.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from specify_cli.core.payload_shaping import apply_keep_none_fields

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class _Sample(BaseModel):
    required: str
    optional_dropped: str | None = None
    optional_kept: int | None = None
    set_value: str | None = None


def test_none_valued_optionals_are_dropped_by_default() -> None:
    model = _Sample(required="x")
    payload = apply_keep_none_fields(model)

    assert payload == {"required": "x"}
    assert "optional_dropped" not in payload
    assert "optional_kept" not in payload


def test_named_keep_none_field_survives_as_explicit_null() -> None:
    model = _Sample(required="x")
    payload = apply_keep_none_fields(model, keep_none_fields=("optional_kept",))

    assert payload == {"required": "x", "optional_kept": None}
    assert "optional_dropped" not in payload


def test_keep_none_field_with_a_real_value_is_unaffected() -> None:
    model = _Sample(required="x", optional_kept=3)
    payload = apply_keep_none_fields(model, keep_none_fields=("optional_kept",))

    assert payload == {"required": "x", "optional_kept": 3}


def test_set_optional_survives_regardless_of_keep_none_fields() -> None:
    model = _Sample(required="x", set_value="present")
    payload = apply_keep_none_fields(model)

    assert payload["set_value"] == "present"


def test_keep_none_fields_naming_an_absent_field_is_a_no_op() -> None:
    """A typo'd or model-mismatched field name in keep_none_fields must not raise."""
    model = _Sample(required="x")
    payload = apply_keep_none_fields(model, keep_none_fields=("does_not_exist",))

    assert payload == {"required": "x"}
