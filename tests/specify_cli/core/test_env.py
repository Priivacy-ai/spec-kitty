"""Tests for the canonical env truthy parser (:mod:`specify_cli.core.env`)."""

from __future__ import annotations

import pytest

from specify_cli.core.env import (
    _TRUTHY_VALUES,
    SYNC_DISABLE_ENV_VARS,
    first_set_sync_disable_env,
    is_truthy,
)

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


def test_sync_disable_env_vars_is_the_canonical_pair() -> None:
    assert SYNC_DISABLE_ENV_VARS == (
        "SPEC_KITTY_SYNC_DISABLE",
        "SPEC_KITTY_SYNC_MINIMAL_IMPORT",
    )


def test_first_set_returns_none_when_no_disable_env_set() -> None:
    assert first_set_sync_disable_env({}) is None


def test_first_set_returns_none_for_falsy_values() -> None:
    env = {"SPEC_KITTY_SYNC_DISABLE": "0", "SPEC_KITTY_SYNC_MINIMAL_IMPORT": "false"}
    assert first_set_sync_disable_env(env) is None


@pytest.mark.parametrize("value", ["1", "true", "yes", "on"])
def test_first_set_returns_disable_when_truthy(value: str) -> None:
    assert (
        first_set_sync_disable_env({"SPEC_KITTY_SYNC_DISABLE": value})
        == "SPEC_KITTY_SYNC_DISABLE"
    )


def test_first_set_returns_minimal_import_when_only_it_is_set() -> None:
    assert (
        first_set_sync_disable_env({"SPEC_KITTY_SYNC_MINIMAL_IMPORT": "1"})
        == "SPEC_KITTY_SYNC_MINIMAL_IMPORT"
    )


def test_first_set_honors_tuple_precedence_when_both_set() -> None:
    env = {"SPEC_KITTY_SYNC_DISABLE": "1", "SPEC_KITTY_SYNC_MINIMAL_IMPORT": "1"}
    assert first_set_sync_disable_env(env) == SYNC_DISABLE_ENV_VARS[0]


def test_first_set_defaults_to_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SYNC_DISABLE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", "yes")
    assert first_set_sync_disable_env() == "SPEC_KITTY_SYNC_MINIMAL_IMPORT"
