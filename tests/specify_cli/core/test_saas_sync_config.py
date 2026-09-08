"""Tests for the canonical rollout gate (:mod:`specify_cli.core.saas_sync_config`).

Contract: ``kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/
saas_rollout.md`` (version 3). #3980 flipped the default from opt-in to
opt-out-only: unset means hosted sync is ON.
"""

from __future__ import annotations

import pytest

from specify_cli.core.saas_sync_config import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
    sync_active,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.mark.parametrize(
    "value",
    [None, "", "   "],
)
def test_unset_or_blank_means_enabled(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(SAAS_SYNC_ENV_VAR, value)
    assert is_saas_sync_enabled() is True


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "True", "yes", "on", " ON "])
def test_truthy_redundantly_confirms_enabled(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, value)
    assert is_saas_sync_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "2", "banana"])
def test_explicit_opt_out_disables(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, value)
    assert is_saas_sync_enabled() is False


def test_kill_switch_disarms_sync_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "1")
    assert is_saas_sync_enabled() is True
    assert sync_active() is False


def test_deprecated_alias_no_longer_disarms_sync_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#3980 launch table: ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` gates only the
    moment-handler registration — it must not disarm hosted sync."""
    monkeypatch.setenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", "1")
    assert is_saas_sync_enabled() is True
    assert sync_active() is True


def test_sync_active_when_enabled_and_no_kill_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    assert sync_active() is True


def test_disabled_message_wording_is_byte_stable() -> None:
    assert saas_sync_disabled_message() == ("Hosted SaaS sync is disabled on this machine. Unset `SPEC_KITTY_ENABLE_SAAS_SYNC` (or set it to `1`) to re-enable it.")
