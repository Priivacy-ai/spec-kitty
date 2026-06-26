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

import os

_EVENTS_MODULE = ".events"
_FEATURE_FLAGS_MODULE = ".feature_flags"
_LOCAL_COMMIT_MODULE = ".local_commit"

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Keep package init cheap. Importing a sync submodule such as
    # ``runtime_event_emitter`` still initializes this package first, so
    # every common export must stay lazy to avoid pulling in auth/queue/
    # daemon machinery on unrelated startup paths like ``spec-kitty next``.
    "LamportClock": (".clock", "LamportClock"),
    "generate_node_id": (".clock", "generate_node_id"),
    "emit_diagnostic": (".diagnose", "emit_diagnostic"),
    "get_emitter": (_EVENTS_MODULE, "get_emitter"),
    "reset_emitter": (_EVENTS_MODULE, "reset_emitter"),
    "emit_wp_status_changed": (_EVENTS_MODULE, "emit_wp_status_changed"),
    "emit_wp_created": (_EVENTS_MODULE, "emit_wp_created"),
    "emit_wp_assigned": (_EVENTS_MODULE, "emit_wp_assigned"),
    "emit_mission_created": (_EVENTS_MODULE, "emit_mission_created"),
    "emit_mission_closed": (_EVENTS_MODULE, "emit_mission_closed"),
    "emit_history_added": (_EVENTS_MODULE, "emit_history_added"),
    "emit_error_logged": (_EVENTS_MODULE, "emit_error_logged"),
    "emit_dependency_resolved": (_EVENTS_MODULE, "emit_dependency_resolved"),
    "emit_token_usage_recorded": (_EVENTS_MODULE, "emit_token_usage_recorded"),
    "emit_diff_summary_recorded": (_EVENTS_MODULE, "emit_diff_summary_recorded"),
    "emit_proof_event": (_EVENTS_MODULE, "emit_proof_event"),
    "OfflineQueue": (".queue", "OfflineQueue"),
    "SAAS_SYNC_ENV_VAR": (_FEATURE_FLAGS_MODULE, "SAAS_SYNC_ENV_VAR"),
    "is_saas_sync_enabled": (_FEATURE_FLAGS_MODULE, "is_saas_sync_enabled"),
    "saas_sync_disabled_message": (_FEATURE_FLAGS_MODULE, "saas_sync_disabled_message"),
    # Lazy-loaded names that require heavier optional/runtime dependencies.
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
    # LocalCommit core (WP05): SyncState and frame lifecycle.
    "SyncState": (_LOCAL_COMMIT_MODULE, "SyncState"),
    "load_sync_state": (_LOCAL_COMMIT_MODULE, "load_sync_state"),
    "save_sync_state": (_LOCAL_COMMIT_MODULE, "save_sync_state"),
    "emit_local_commit": (_LOCAL_COMMIT_MODULE, "emit_local_commit"),
    "flush_pending_local_commits": (_LOCAL_COMMIT_MODULE, "flush_pending_local_commits"),
    "record_local_commit_ack": (_LOCAL_COMMIT_MODULE, "record_local_commit_ack"),
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
    "emit_proof_event",
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
    # register_default_handlers: demoted — no cross-module src/ callers; used
    # only by tests to restore handler state (WP01 harden-dead-symbol-gate).
    # Remains callable as an unexported internal.
    # LocalCommit core (WP05)
    "SyncState",
    "load_sync_state",
    "save_sync_state",
    "emit_local_commit",
    "flush_pending_local_commits",
    "record_local_commit_ack",
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


# Module-level handler functions so they can be re-registered after a
# test-only ``adapters.reset_handlers()`` call. Defining them at the
# top level (instead of nested inside the original ``with`` block)
# means ``register_default_handlers()`` can be called from anywhere
# in the test suite to restore the registry after a wipe — fixing the
# order-dependent test pollution where ``reset_handlers()`` in one test
# left subsequent lifecycle-fan-out tests with an empty registry
# (issues Priivacy-ai/spec-kitty#1198 / #1200).
def _dossier_sync_handler(feature_dir, mission_slug, repo_root):  # type: ignore[no-untyped-def]
    """Default dossier-sync handler, registered by ``register_default_handlers``.

    Late-binding wrapper: looks up the sync target at call time so that
    tests which patch the underlying module attribute observe the patch
    on every invocation. Registering the target directly would capture
    the original function reference and bypass such patches.
    """
    from specify_cli.sync.dossier_pipeline import (
        trigger_feature_dossier_sync_if_enabled,
    )

    trigger_feature_dossier_sync_if_enabled(feature_dir, mission_slug, repo_root)


def _saas_fanout_handler(**kwargs):  # type: ignore[no-untyped-def]
    """Default WPStatusChanged SaaS fan-out handler."""
    from specify_cli.sync.events import emit_wp_status_changed

    emit_wp_status_changed(**kwargs)


def _lifecycle_saas_fanout_handler(**kwargs):  # type: ignore[no-untyped-def]
    """Default lifecycle SaaS fan-out handler.

    Constructs the SaaS wire envelope from the local lifecycle event and
    queues it into the offline outbox when sync is enabled and a valid
    Teamspace scope is available. Strict canonical-payload validation
    runs here (see ``_validate_lifecycle_payload``) so schema-drift
    becomes an emit-time error, not an RC-canary failure
    (issues Priivacy-ai/spec-kitty#1198 / #1200).
    """
    from collections.abc import Mapping

    from spec_kitty_events import Event as EventModel

    from specify_cli.core.contract_gate import validate_outbound_payload
    from specify_cli.identity.project import ensure_identity
    from specify_cli.status import (
        build_saas_lifecycle_queue_event,
        repo_root_for_lifecycle_log,
    )
    from specify_cli.sync.clock import LamportClock
    from specify_cli.sync.feature_flags import is_saas_sync_enabled
    from specify_cli.sync.queue import (
        OfflineQueue,
        read_queue_scope_from_credentials,
        read_queue_scope_from_session,
    )

    if not is_saas_sync_enabled():
        return
    scope = read_queue_scope_from_session() or read_queue_scope_from_credentials()
    if not scope:
        return

    envelope = kwargs.get("envelope")
    log_path = kwargs.get("log_path")
    if not isinstance(envelope, Mapping):
        return

    # Cheap queueability pre-check before any clock/identity work so a
    # non-lifecycle envelope never advances the Lamport clock (preserves the
    # original early-return ordering).
    event_type = envelope.get("event_type")
    payload = envelope.get("payload")
    aggregate_type = envelope.get("aggregate_type")
    if (
        not isinstance(event_type, str)
        or not isinstance(payload, Mapping)
        or not isinstance(aggregate_type, str)
    ):
        return

    repo_root = repo_root_for_lifecycle_log(log_path)
    if repo_root is None:
        return

    identity = ensure_identity(repo_root)
    if not identity.project_uuid or not identity.build_id:
        return

    clock = LamportClock.load()
    # Lifecycle-specific shaping (canonical payload, strict validation, envelope
    # assembly) lives behind the status facade; sync owns the identity/clock/queue
    # orchestration only. Returns None for non-queueable envelopes.
    event = build_saas_lifecycle_queue_event(
        envelope,
        build_id=identity.build_id,
        project_uuid=str(identity.project_uuid),
        project_slug=identity.project_slug,
        node_id=identity.node_id or clock.node_id,
        lamport_clock=clock.tick(),
    )
    if event is None:
        return

    validate_outbound_payload(event, "envelope")
    EventModel(**event)
    OfflineQueue().queue_event(event)


def register_default_handlers() -> None:
    """Register the default sync handlers into ``specify_cli.status.adapters``.

    Idempotent: ``adapters.register_*`` functions de-duplicate by qualified
    name, so calling this repeatedly is safe. Tests that wipe the registry
    via ``adapters.reset_handlers()`` should call this immediately after
    (or use the autouse fixture in ``tests/status/conftest.py``) so the
    next lifecycle event still has a fan-out target.

    See issues Priivacy-ai/spec-kitty#1198 / #1200 — without this hook,
    ``test_emit_backward_transition.py`` (which calls ``reset_handlers``
    in its teardown) poisoned subsequent ``test_lifecycle_events.py``
    tests that depend on the lifecycle SaaS fan-out being registered.
    """
    with _contextlib.suppress(ImportError):
        from specify_cli.status import register_dossier_sync_handler, register_lifecycle_saas_fanout_handler, register_saas_fanout_handler

        register_dossier_sync_handler(_dossier_sync_handler)
        register_saas_fanout_handler(_saas_fanout_handler)
        register_lifecycle_saas_fanout_handler(_lifecycle_saas_fanout_handler)


# Initial registration at import time. Subsequent code (production or
# tests) can call ``register_default_handlers()`` again to repair the
# registry after a wipe.
if os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT") != "1":
    register_default_handlers()

if os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT") != "1":
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
            payload: dict[str, object],
        ) -> dict[str, object]:
            from specify_cli.sync.events import get_emitter

            result = get_emitter()._emit(
                event_type=event_type,
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                payload=payload,
            )
            return result if result is not None else {}

        register_dossier_emitter(_dossier_emit_via_sync)
