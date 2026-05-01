"""Canonical rollout gate for hosted SaaS sync.

Stability contract: ``contracts/saas_rollout.md``.

This module is the single source of truth for the ``SPEC_KITTY_ENABLE_SAAS_SYNC``
environment-variable check.  Both ``specify_cli.tracker.feature_flags`` and
``specify_cli.sync.feature_flags`` are thin re-export shims that delegate here.
"""

from __future__ import annotations

import os

SAAS_SYNC_ENV_VAR = "SPEC_KITTY_ENABLE_SAAS_SYNC"
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})

_DISABLED_MESSAGE = "Hosted SaaS sync is not enabled on this machine. Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in."


def is_saas_sync_enabled() -> bool:
    """Return True iff SaaS sync is explicitly enabled via the environment.

    Truthy values (case-insensitive, after strip): ``1``, ``true``, ``yes``, ``on``.
    Everything else — including an unset or empty variable — returns ``False``.
    """
    raw = os.environ.get(SAAS_SYNC_ENV_VAR, "")
    return raw.strip().casefold() in _TRUTHY_VALUES


def saas_sync_disabled_message() -> str:
    """Return the stable, byte-wise-frozen message shown when SaaS sync is off.

    Wording is asserted byte-for-byte by tests; do not change without updating
    ``contracts/saas_rollout.md`` and bumping the contract version.
    """
    return _DISABLED_MESSAGE
