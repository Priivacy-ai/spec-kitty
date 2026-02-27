"""Feature flags for tracker integration."""

from __future__ import annotations

import os

SAAS_SYNC_ENV_VAR = "SPEC_KITTY_ENABLE_SAAS_SYNC"
_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def is_saas_sync_enabled() -> bool:
    """Return True when SaaS connectivity is explicitly enabled."""
    raw_value = os.getenv(SAAS_SYNC_ENV_VAR, "")
    return raw_value.strip().lower() in _TRUTHY_VALUES


def saas_sync_disabled_message() -> str:
    """Return a consistent operator-facing message for disabled SaaS sync."""
    return (
        "SaaS sync is disabled by feature flag. "
        f"Set {SAAS_SYNC_ENV_VAR}=1 to enable."
    )
