"""Unit tests for specify_cli.saas.rollout.

Hosted SaaS sync is release-enabled.  The historical env var remains exported
for compatibility, but its value no longer controls the upload path.
"""

from __future__ import annotations

import pytest

from specify_cli.saas.rollout import is_saas_sync_enabled, saas_sync_disabled_message

_ENV_VAR = "SPEC_KITTY_ENABLE_SAAS_SYNC"

_ENV_VALUES = [
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


@pytest.mark.parametrize("value", _ENV_VALUES)
def test_is_saas_sync_enabled_ignores_env_value(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """All env-var values leave SaaS sync enabled in the release channel."""
    monkeypatch.setenv(_ENV_VAR, value)
    assert is_saas_sync_enabled() is True


def test_is_saas_sync_enabled_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset env var still returns True."""
    monkeypatch.delenv(_ENV_VAR, raising=False)
    assert is_saas_sync_enabled() is True


# ---------------------------------------------------------------------------
# Stable disabled-message wording (byte-wise assertion per contract)
# ---------------------------------------------------------------------------

_EXPECTED_MESSAGE = (
    "Hosted SaaS sync is enabled by default. "
    "Use `spec-kitty sync opt-out` to disable uploads for this checkout."
)


def test_saas_sync_disabled_message_wording() -> None:
    """Compatibility disabled message points to supported opt-out."""
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
