"""Canonical rollout gate for hosted SaaS sync.

Stability contract: ``contracts/saas_rollout.md``.

This CORE module is the single source of truth for the
``SPEC_KITTY_ENABLE_SAAS_SYNC`` environment-variable check.  The INTEGRATION-set
``saas.rollout`` module is a thin re-export shim that delegates here, as are the
``tracker.feature_flags`` and ``sync.feature_flags`` shims.

Imports are stdlib-only (``os``) so this module introduces no import cycle and
is safe for CORE-set consumers (C-001).
"""

from __future__ import annotations

import os

from specify_cli.core.env import is_truthy

SAAS_SYNC_ENV_VAR = "SPEC_KITTY_ENABLE_SAAS_SYNC"

_DISABLED_MESSAGE = (
    "Hosted SaaS sync is not enabled on this machine. "
    "Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in."
)

_OPT_IN_RECORDED_BASE = "Local sync preference recorded for this checkout"

__all__ = [
    "SAAS_SYNC_ENV_VAR",
    "is_saas_sync_enabled",
    "saas_sync_disabled_message",
    "saas_sync_opt_in_recorded_message",
]


def is_saas_sync_enabled() -> bool:
    """Return True iff SaaS sync is explicitly enabled via the environment.

    Truthy values (case-insensitive, after strip): ``1``, ``true``, ``yes``,
    ``y``, ``on`` (the canonical grammar in :mod:`specify_cli.core.env`).
    Everything else — including an unset or empty variable — returns ``False``.
    """
    return is_truthy(os.environ.get(SAAS_SYNC_ENV_VAR))


def saas_sync_disabled_message() -> str:
    """Return the stable, byte-wise-frozen message shown when SaaS sync is off.

    Wording is asserted byte-for-byte by tests; do not change without updating
    ``contracts/saas_rollout.md`` and bumping the contract version.
    """
    return _DISABLED_MESSAGE


def saas_sync_opt_in_recorded_message(scope_label: str | None = None) -> str:
    """Return the honest confirmation for ``spec-kitty sync opt-in`` (#2264).

    ``opt-in`` writes LOCAL routing flags only — no auth, no remote round-trip,
    no history import. This message must therefore NOT imply remote
    materialization or history: it states only that a local preference was
    recorded. The prior wording ("Enabled SaaS sync for this checkout") was the
    false-green that escalated #2264 to P1. Wording is asserted by tests.
    """
    if scope_label:
        return f"{_OPT_IN_RECORDED_BASE} ({scope_label})."
    return f"{_OPT_IN_RECORDED_BASE}."
