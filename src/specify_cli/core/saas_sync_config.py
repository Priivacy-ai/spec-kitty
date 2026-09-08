"""Canonical rollout gate for hosted SaaS sync.

Stability contract: ``contracts/saas_rollout.md`` (version 3).

This CORE module is the single source of truth for the
``SPEC_KITTY_ENABLE_SAAS_SYNC`` environment-variable check. The former
re-export shims (``saas.rollout``, ``sync.feature_flags``) died with their
packages when the sync transport was deleted (issue #5);
``tracker.feature_flags`` re-exports from here.

Imports are stdlib-only (``os``) so this module introduces no import cycle and
is safe for CORE-set consumers (C-001).

#3980 (Team Kitty launch defaults) flipped the default: hosted sync is ON
unless explicitly opted out — ``SPEC_KITTY_ENABLE_SAAS_SYNC=0`` is the
opt-out; an unset or empty variable means enabled.
"""

from __future__ import annotations

import os

from specify_cli.core.env import is_truthy, sync_kill_switch_active

SAAS_SYNC_ENV_VAR = "SPEC_KITTY_ENABLE_SAAS_SYNC"

_DISABLED_MESSAGE = (
    "Hosted SaaS sync is disabled on this machine. "
    "Unset `SPEC_KITTY_ENABLE_SAAS_SYNC` (or set it to `1`) to re-enable it."
)

__all__ = [
    "SAAS_SYNC_ENV_VAR",
    "is_saas_sync_enabled",
    "saas_sync_disabled_message",
    "sync_active",
]


def is_saas_sync_enabled() -> bool:
    """Return True unless SaaS sync is explicitly opted out via the environment.

    Launch default (#3980): the variable is **opt-out-only**. Unset or empty
    means enabled. A truthy value (case-insensitive, after strip: ``1``,
    ``true``, ``yes``, ``y``, ``on`` — the canonical grammar in
    :mod:`specify_cli.core.env`) redundantly confirms enabled. Any other
    non-empty value — ``0``, ``false``, ``off``, ... — opts out.
    """
    value = os.environ.get(SAAS_SYNC_ENV_VAR)
    if value is None or not value.strip():
        return True
    return is_truthy(value)


def sync_active() -> bool:
    """Return whether hosted sync is armed after the global disable override.

    The kill switch is ``SPEC_KITTY_SYNC_DISABLE`` alone (#3980 launch
    table): ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` no longer disarms sync — it is
    a deprecated alias of the moment-handler import gate
    (:func:`specify_cli.core.env.moment_handlers_disabled_reason`).
    """
    return is_saas_sync_enabled() and not sync_kill_switch_active()


def saas_sync_disabled_message() -> str:
    """Return the stable, byte-wise-frozen message shown when SaaS sync is off.

    Wording is asserted byte-for-byte by tests; do not change without updating
    ``contracts/saas_rollout.md`` and bumping the contract version.
    """
    return _DISABLED_MESSAGE
