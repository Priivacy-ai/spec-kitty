"""Tests for the canonical env truthy parser (:mod:`specify_cli.core.env`)."""

from __future__ import annotations

import pytest

from specify_cli.core.env import _TRUTHY_VALUES, is_truthy

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.mark.parametrize(
    "value",
    ["1", "true", "TRUE", " TRUE ", "Yes", "yes", "y", "Y", "on", "ON", " on "],
)
def test_truthy_tokens_return_true(value: str) -> None:
    assert is_truthy(value) is True


@pytest.mark.parametrize(
    "value",
    [None, "", " ", "0", "false", "no", "n", "off", "2", "banana", "enabled"],
)
def test_falsy_values_return_false(value: str | None) -> None:
    assert is_truthy(value) is False


def test_truthy_values_frozenset_is_the_union_grammar() -> None:
    assert frozenset({"1", "true", "yes", "y", "on"}) == _TRUTHY_VALUES
