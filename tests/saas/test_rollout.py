"""Unit tests for specify_cli.saas.rollout.

Covers the truthy/falsy env-var table, byte-wise stable disabled message, and
BC shim identity (each shim must re-export the exact same callable object as
the canonical module, not a copy of it).

The autouse fixture in ``tests/conftest.py`` sets SPEC_KITTY_ENABLE_SAAS_SYNC=1
globally.  Every test here uses ``monkeypatch`` to override that value so the
results are deterministic regardless of fixture ordering.
"""

from __future__ import annotations

import pytest

from specify_cli.saas.rollout import is_saas_sync_enabled, saas_sync_disabled_message

_ENV_VAR = "SPEC_KITTY_ENABLE_SAAS_SYNC"

# ---------------------------------------------------------------------------
# Parametrised truthy / falsy tests
# ---------------------------------------------------------------------------

_TRUTHY_CASES = [
    "1",
    "true",
    "TRUE",
    "True",
    "yes",
    "YES",
    "Yes",
    "on",
    "ON",
    "On",
]

_FALSY_CASES = [
    "",
    "0",
    "false",
    "FALSE",
    "no",
    "NO",
    "off",
    "OFF",
    "banana",
    "2",
    " ",
    "enabled",
]


@pytest.mark.parametrize("value", _TRUTHY_CASES)
def test_is_saas_sync_enabled_truthy(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Truthy env-var values must return True."""
    monkeypatch.setenv(_ENV_VAR, value)
    assert is_saas_sync_enabled() is True


@pytest.mark.parametrize("value", _FALSY_CASES)
def test_is_saas_sync_enabled_falsy(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Falsy env-var values (including empty string) must return False."""
    monkeypatch.setenv(_ENV_VAR, value)
    assert is_saas_sync_enabled() is False


def test_is_saas_sync_enabled_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset env var must return False."""
    monkeypatch.delenv(_ENV_VAR, raising=False)
    assert is_saas_sync_enabled() is False


def test_is_saas_sync_enabled_strips_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leading/trailing whitespace around a truthy value must still return True."""
    monkeypatch.setenv(_ENV_VAR, "  1  ")
    assert is_saas_sync_enabled() is True


# ---------------------------------------------------------------------------
# Stable disabled-message wording (byte-wise assertion per contract)
# ---------------------------------------------------------------------------

_EXPECTED_MESSAGE = (
    "Hosted SaaS sync is not enabled on this machine. "
    "Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in."
)


def test_saas_sync_disabled_message_wording() -> None:
    """Disabled message must be byte-for-byte identical to the contract wording."""
    assert saas_sync_disabled_message() == _EXPECTED_MESSAGE


# ---------------------------------------------------------------------------
# BC shim identity tests
# ---------------------------------------------------------------------------


def test_tracker_shim_identity() -> None:
    """tracker.feature_flags must re-export the exact same callable as saas.rollout."""
    from specify_cli.tracker.feature_flags import (
        is_saas_sync_enabled as tr_fn,
    )

    assert tr_fn is is_saas_sync_enabled, (
        "specify_cli.tracker.feature_flags.is_saas_sync_enabled must be the "
        "identical object as specify_cli.saas.rollout.is_saas_sync_enabled"
    )


def test_sync_shim_identity() -> None:
    """sync.feature_flags must re-export the exact same callable as saas.rollout."""
    from specify_cli.sync.feature_flags import (
        is_saas_sync_enabled as sync_fn,
    )

    assert sync_fn is is_saas_sync_enabled, (
        "specify_cli.sync.feature_flags.is_saas_sync_enabled must be the "
        "identical object as specify_cli.saas.rollout.is_saas_sync_enabled"
    )


def test_tracker_shim_disabled_message_identity() -> None:
    """tracker shim's saas_sync_disabled_message must be the canonical callable."""
    from specify_cli.tracker.feature_flags import (
        saas_sync_disabled_message as tr_msg,
    )

    assert tr_msg is saas_sync_disabled_message


def test_sync_shim_disabled_message_identity() -> None:
    """sync shim's saas_sync_disabled_message must be the canonical callable."""
    from specify_cli.sync.feature_flags import (
        saas_sync_disabled_message as sync_msg,
    )

    assert sync_msg is saas_sync_disabled_message
