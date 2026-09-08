"""Tests for the canonical env truthy parser (:mod:`specify_cli.core.env`)."""

from __future__ import annotations

import warnings

import pytest

from specify_cli.core.env import (
    _TRUTHY_VALUES,
    MOMENT_HANDLER_DISABLE_ENV_VARS,
    PRE_REVIEW_GATE_SKIP_ENV_VAR,
    SYNC_KILL_SWITCH_ENV_VAR,
    is_truthy,
    moment_handlers_disabled_reason,
    pre_review_gate_skip_reason,
    sync_kill_switch_active,
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


# ---------------------------------------------------------------------------
# #3980 launch names: kill switch, moment-handler gate, pre-review gate
# ---------------------------------------------------------------------------


def test_kill_switch_env_var_name_is_the_single_switch() -> None:
    assert SYNC_KILL_SWITCH_ENV_VAR == "SPEC_KITTY_SYNC_DISABLE"


def test_moment_handler_disable_vocabulary_is_canonical() -> None:
    assert MOMENT_HANDLER_DISABLE_ENV_VARS == (
        "SPEC_KITTY_NO_MOMENT_HANDLERS",
        "SPEC_KITTY_SYNC_DISABLE",
        "SPEC_KITTY_SYNC_MINIMAL_IMPORT",
    )


def test_kill_switch_inactive_when_unset_or_falsy() -> None:
    assert sync_kill_switch_active({}) is False
    assert sync_kill_switch_active({"SPEC_KITTY_SYNC_DISABLE": "0"}) is False
    assert sync_kill_switch_active({"SPEC_KITTY_SYNC_DISABLE": "banana"}) is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on"])
def test_kill_switch_active_when_truthy(value: str) -> None:
    assert sync_kill_switch_active({"SPEC_KITTY_SYNC_DISABLE": value}) is True


def test_kill_switch_defaults_to_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "yes")
    assert sync_kill_switch_active() is True


def test_pre_review_gate_skip_reason_none_when_unset_or_falsy() -> None:
    assert pre_review_gate_skip_reason({}) is None
    assert pre_review_gate_skip_reason({PRE_REVIEW_GATE_SKIP_ENV_VAR: "0"}) is None


def test_pre_review_gate_skip_reason_names_its_own_var_when_set() -> None:
    assert (
        pre_review_gate_skip_reason({PRE_REVIEW_GATE_SKIP_ENV_VAR: "1"})
        == "SPEC_KITTY_SKIP_PRE_REVIEW_GATE is set"
    )


def test_pre_review_gate_no_longer_reads_sync_disable_vocabulary() -> None:
    """#3980: disarming sync must not silently skip a review gate."""
    env = {
        "SPEC_KITTY_SYNC_DISABLE": "1",
        "SPEC_KITTY_SYNC_MINIMAL_IMPORT": "1",
    }
    assert pre_review_gate_skip_reason(env) is None


def test_moment_handlers_disabled_reason_none_when_nothing_set() -> None:
    assert moment_handlers_disabled_reason({}) is None


def test_moment_handlers_disabled_reason_for_own_name() -> None:
    assert (
        moment_handlers_disabled_reason({"SPEC_KITTY_NO_MOMENT_HANDLERS": "on"})
        == "SPEC_KITTY_NO_MOMENT_HANDLERS is set"
    )


def test_moment_handlers_disabled_reason_folds_in_kill_switch() -> None:
    assert (
        moment_handlers_disabled_reason({"SPEC_KITTY_SYNC_DISABLE": "1"})
        == "SPEC_KITTY_SYNC_DISABLE is set"
    )


def test_moment_handlers_disabled_reason_honors_deprecated_alias(
    monkeypatch: pytest.MonkeyPatch,
    recwarn: pytest.WarningsRecorder,
) -> None:
    """``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` is honored, with a once-per-process warning."""
    monkeypatch.setattr("specify_cli.core.env._deprecation_warned", set())
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        reason = moment_handlers_disabled_reason({"SPEC_KITTY_SYNC_MINIMAL_IMPORT": "1"})
    assert reason == "SPEC_KITTY_SYNC_MINIMAL_IMPORT is set"
    assert any(
        issubclass(w.category, DeprecationWarning)
        and "SPEC_KITTY_NO_MOMENT_HANDLERS" in str(w.message)
        for w in recwarn.list
    )


def test_deprecated_alias_warns_once_per_process(
    monkeypatch: pytest.MonkeyPatch,
    recwarn: pytest.WarningsRecorder,
) -> None:
    monkeypatch.setattr("specify_cli.core.env._deprecation_warned", set())
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        moment_handlers_disabled_reason({"SPEC_KITTY_SYNC_MINIMAL_IMPORT": "1"})
        # A second read in the same process must not warn again.
        moment_handlers_disabled_reason({"SPEC_KITTY_SYNC_MINIMAL_IMPORT": "1"})
    deprecations = [
        w for w in recwarn.list if issubclass(w.category, DeprecationWarning)
    ]
    assert len(deprecations) == 1


def test_moment_handler_gate_own_name_wins_over_deprecated_alias(
    monkeypatch: pytest.MonkeyPatch,
    recwarn: pytest.WarningsRecorder,
) -> None:
    """Precedence: ``SPEC_KITTY_NO_MOMENT_HANDLERS`` wins, and the alias's
    deprecation warning does not fire because the alias is never reached."""
    monkeypatch.setattr("specify_cli.core.env._deprecation_warned", set())
    env = {"SPEC_KITTY_NO_MOMENT_HANDLERS": "1", "SPEC_KITTY_SYNC_MINIMAL_IMPORT": "1"}
    assert (
        moment_handlers_disabled_reason(env)
        == "SPEC_KITTY_NO_MOMENT_HANDLERS is set"
    )
    assert not [
        w for w in recwarn.list if issubclass(w.category, DeprecationWarning)
    ]


def test_moment_handlers_disabled_reason_defaults_to_os_environ(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("specify_cli.core.env._deprecation_warned", set())
    monkeypatch.setenv("SPEC_KITTY_NO_MOMENT_HANDLERS", "yes")
    assert moment_handlers_disabled_reason() == "SPEC_KITTY_NO_MOMENT_HANDLERS is set"
