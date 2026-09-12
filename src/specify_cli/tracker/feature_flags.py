"""Backwards-compatibility shim; canonical home is specify_cli.core.saas_sync_config."""

from specify_cli.core.saas_sync_config import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)

__all__ = ["SAAS_SYNC_ENV_VAR", "is_saas_sync_enabled", "saas_sync_disabled_message"]
