"""
Sync module for spec-kitty CLI.

Provides real-time synchronization with spec-kitty-saas server via:
- WebSocket client for event streaming
- Offline queue for resilience
- OAuth authentication via ``specify_cli.auth.get_token_manager``
- Batch sync for offline queue replay
- Event emission with Lamport clock ordering

Heavy dependencies (requests, websockets) are lazily imported via __getattr__
so that lightweight imports like ``from specify_cli.sync.events import ...``
do not pull in optional packages.

SaaS connectivity is feature-flagged and disabled by default. Set
``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` to enable auth/network sync flows.

As of mission 080 (browser-mediated OAuth) the legacy
``specify_cli.sync.auth`` module has been removed entirely. All callers
must fetch bearer tokens via
``from specify_cli.auth import get_token_manager`` (WP08 rewire, WP10
deletion).
"""

from .clock import LamportClock, generate_node_id
from .diagnose import emit_diagnostic
from .events import (
    get_emitter,
    reset_emitter,
    emit_wp_status_changed,
    emit_wp_created,
    emit_wp_assigned,
    emit_mission_created,
    emit_mission_closed,
    emit_history_added,
    emit_error_logged,
    emit_dependency_resolved,
    emit_token_usage_recorded,
    emit_diff_summary_recorded,
)
from .queue import OfflineQueue
from .feature_flags import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)

# Lazy-loaded names (require 'requests' or 'websockets' at runtime)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BatchEventResult": (".batch", "BatchEventResult"),
    "BatchSyncResult": (".batch", "BatchSyncResult"),
    "batch_sync": (".batch", "batch_sync"),
    "categorize_error": (".batch", "categorize_error"),
    "format_sync_summary": (".batch", "format_sync_summary"),
    "generate_failure_report": (".batch", "generate_failure_report"),
    "write_failure_report": (".batch", "write_failure_report"),
    "sync_all_queued_events": (".batch", "sync_all_queued_events"),
    "WebSocketClient": (".client", "WebSocketClient"),
    "SyncConfig": (".config", "SyncConfig"),
    "BackgroundSyncService": (".background", "BackgroundSyncService"),
    "get_sync_service": (".background", "get_sync_service"),
    "reset_sync_service": (".background", "reset_sync_service"),
    "SyncRuntime": (".runtime", "SyncRuntime"),
    "get_runtime": (".runtime", "get_runtime"),
    "reset_runtime": (".runtime", "reset_runtime"),
    "SyncDaemonStatus": (".daemon", "SyncDaemonStatus"),
    "ensure_sync_daemon_running": (".daemon", "ensure_sync_daemon_running"),
    "get_sync_daemon_status": (".daemon", "get_sync_daemon_status"),
    "stop_sync_daemon": (".daemon", "stop_sync_daemon"),
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        import importlib

        mod = importlib.import_module(module_path, __name__)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "WebSocketClient",
    "SyncConfig",
    "OfflineQueue",
    "batch_sync",
    "sync_all_queued_events",
    "BatchEventResult",
    "BatchSyncResult",
    "categorize_error",
    "format_sync_summary",
    "generate_failure_report",
    "write_failure_report",
    "LamportClock",
    "generate_node_id",
    "get_emitter",
    "reset_emitter",
    "emit_wp_status_changed",
    "emit_wp_created",
    "emit_wp_assigned",
    "emit_mission_created",
    "emit_mission_closed",
    "emit_history_added",
    "emit_error_logged",
    "emit_dependency_resolved",
    "emit_token_usage_recorded",
    "emit_diff_summary_recorded",
    "BackgroundSyncService",
    "get_sync_service",
    "reset_sync_service",
    "SyncRuntime",
    "get_runtime",
    "reset_runtime",
    "SyncDaemonStatus",
    "ensure_sync_daemon_running",
    "get_sync_daemon_status",
    "stop_sync_daemon",
    "SAAS_SYNC_ENV_VAR",
    "is_saas_sync_enabled",
    "saas_sync_disabled_message",
    "emit_diagnostic",
]


# ─── Adapter registration (run at import time) ─────────────────────────
# Register handlers so that canonical status events trigger SaaS sync
# and dossier-sync side effects, and dossier event emission routes
# through the existing sync emitter, without status/emit.py or
# dossier/events.py depending on the sync package.
#
# This block must remain at the BOTTOM of the file (after all imports
# and __all__). We narrow contextlib.suppress to ImportError only so
# that real bugs (SyntaxError, AttributeError, broken APIs) surface
# during sync package init rather than producing a silent no-op
# fan-out. ImportError covers the legitimate compatibility case where
# optional sync sub-modules are absent (0.1x environments / test
# stubs); anything else is a defect.
import contextlib as _contextlib  # noqa: E402

with _contextlib.suppress(ImportError):
    from specify_cli.status.adapters import (
        register_dossier_sync_handler,
        register_saas_fanout_handler,
    )

    # Late-binding wrappers: look up sync targets at call time so that
    # tests which patch the underlying module attributes (e.g.
    # ``patch("specify_cli.sync.events.emit_wp_status_changed")``)
    # observe the patch on every invocation. Registering the targets
    # directly would capture the original function reference and bypass
    # such patches.
    def _dossier_sync_handler(feature_dir, mission_slug, repo_root):  # type: ignore[no-untyped-def]
        from specify_cli.sync.dossier_pipeline import (
            trigger_feature_dossier_sync_if_enabled,
        )

        trigger_feature_dossier_sync_if_enabled(feature_dir, mission_slug, repo_root)

    def _saas_fanout_handler(**kwargs):  # type: ignore[no-untyped-def]
        from specify_cli.sync.events import emit_wp_status_changed

        emit_wp_status_changed(**kwargs)

    register_dossier_sync_handler(_dossier_sync_handler)
    register_saas_fanout_handler(_saas_fanout_handler)

with _contextlib.suppress(ImportError):
    # Register dossier emitter (WP01 inversion). The wrapper routes
    # through get_emitter() lazily so the late-binding behavior of the
    # emitter singleton is preserved across resets.
    from specify_cli.dossier.emitter_adapter import register_dossier_emitter

    def _dossier_emit_via_sync(
        *,
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        payload: dict,
    ) -> dict:
        from specify_cli.sync.events import get_emitter

        return get_emitter()._emit(
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            payload=payload,
        )

    register_dossier_emitter(_dossier_emit_via_sync)
