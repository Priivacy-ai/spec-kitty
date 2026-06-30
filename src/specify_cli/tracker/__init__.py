"""Tracker integration surface for Spec Kitty CLI."""

from specify_cli.tracker.config import (
    ALL_SUPPORTED_PROVIDERS,
    LOCAL_PROVIDERS,
    REMOVED_PROVIDERS,
    SAAS_PROVIDERS,
)
from specify_cli.tracker.feature_flags import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)

__all__ = [
    "ALL_SUPPORTED_PROVIDERS",
    "LOCAL_PROVIDERS",
    "REMOVED_PROVIDERS",
    "SAAS_PROVIDERS",
    "SAAS_SYNC_ENV_VAR",
    "is_saas_sync_enabled",
    "saas_sync_disabled_message",
]

# ---------------------------------------------------------------------------
# Pending-origin consumer registration (FR-006, WP03)
#
# Registers ``consume_pending_origin_impl`` with ``core.adapters`` so that
# ``core/mission_creation.py`` can invoke tracker's pending-origin binding
# without a direct CORE→INTEGRATION import.
#
# This runs once at tracker package startup.  Registration is idempotent
# (the registry de-duplicates by qualified name) so re-importing the
# tracker package in test processes is safe.
#
# Startup ordering: the ``mission_create`` CLI command body imports
# ``specify_cli.tracker`` (inside ``create_mission()``, immediately before the
# core phase) so this registration happens before ``create_mission_core`` is
# first called. That in-function import is load-bearing — do NOT remove it as
# "redundant": it is the sole trigger that registers the pending-origin consumer
# for the CLI path.
# ---------------------------------------------------------------------------
from specify_cli.core.adapters import register_pending_origin_consumer
from specify_cli.tracker.origin_consumer import consume_pending_origin_impl

register_pending_origin_consumer(consume_pending_origin_impl)
