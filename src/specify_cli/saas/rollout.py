"""Backward-compat re-export shim. Canonical home: specify_cli.core.saas_sync_config.

Stability contract: ``contracts/saas_rollout.md``.

Re-exports the same function objects so ``is``-identity holds across every shim
(``tracker.feature_flags``, ``sync.feature_flags``) and existing importers of
``specify_cli.saas.rollout`` keep working unchanged.
"""

from __future__ import annotations

from specify_cli.core.saas_sync_config import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)

__all__ = ["SAAS_SYNC_ENV_VAR", "is_saas_sync_enabled", "saas_sync_disabled_message"]
