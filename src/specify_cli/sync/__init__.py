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
from pathlib import Path

from specify_cli.core.env import is_truthy
from specify_cli.core.saas_sync_config import sync_active

_EVENTS_MODULE = ".events"
_FEATURE_FLAGS_MODULE = ".feature_flags"
_LOCAL_COMMIT_MODULE = ".local_commit"
_BATCH_MODULE = ".batch"
_BACKGROUND_MODULE = ".background"
_RUNTIME_MODULE = ".runtime"
_DAEMON_MODULE = ".daemon"

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
    "ProjectOutboxTask": (".queue", "ProjectOutboxTask"),
    "OfflineBodyUploadQueue": (".body_queue", "OfflineBodyUploadQueue"),
    "ProjectSyncStore": (".project_store", "ProjectSyncStore"),
    "ProjectUnitOfWork": (".project_store", "ProjectUnitOfWork"),
    "LayoutGenerationAuthority": (".layout_generation", "LayoutGenerationAuthority"),
    "LayoutWritePermit": (".layout_generation", "LayoutWritePermit"),
    "LayoutTestHooks": (".layout_generation", "LayoutTestHooks"),
    "SAAS_SYNC_ENV_VAR": (_FEATURE_FLAGS_MODULE, "SAAS_SYNC_ENV_VAR"),
    "is_saas_sync_enabled": (_FEATURE_FLAGS_MODULE, "is_saas_sync_enabled"),
    "saas_sync_disabled_message": (_FEATURE_FLAGS_MODULE, "saas_sync_disabled_message"),
    # Lazy-loaded names that require heavier optional/runtime dependencies.
    "BatchEventResult": (_BATCH_MODULE, "BatchEventResult"),
    "BatchSyncResult": (_BATCH_MODULE, "BatchSyncResult"),
    # NOTE (#3030 FR-012): ``batch_sync`` and ``sync_all_queued_events`` are
    # deliberately absent. They are the retired queue-backed event drain, which
    # carries no per-project consent; the journal dispatcher
    # (``delivery/dispatcher.py``) is the sole event drain. Re-exporting them
    # reinstates the cross-project leak — guarded by
    # ``tests/sync/test_no_queue_drain_constructed_3030.py``.
    "categorize_error": (_BATCH_MODULE, "categorize_error"),
    "format_sync_summary": (_BATCH_MODULE, "format_sync_summary"),
    "generate_failure_report": (_BATCH_MODULE, "generate_failure_report"),
    "write_failure_report": (_BATCH_MODULE, "write_failure_report"),
    "WebSocketClient": (".client", "WebSocketClient"),
    "SyncConfig": (".config", "SyncConfig"),
    "BackgroundSyncService": (_BACKGROUND_MODULE, "BackgroundSyncService"),
    "get_sync_service": (_BACKGROUND_MODULE, "get_sync_service"),
    "reset_sync_service": (_BACKGROUND_MODULE, "reset_sync_service"),
    "SyncRuntime": (_RUNTIME_MODULE, "SyncRuntime"),
    "get_runtime": (_RUNTIME_MODULE, "get_runtime"),
    "reset_runtime": (_RUNTIME_MODULE, "reset_runtime"),
    "SyncDaemonStatus": (_DAEMON_MODULE, "SyncDaemonStatus"),
    "ensure_sync_daemon_running": (_DAEMON_MODULE, "ensure_sync_daemon_running"),
    "get_sync_daemon_status": (_DAEMON_MODULE, "get_sync_daemon_status"),
    "stop_sync_daemon": (_DAEMON_MODULE, "stop_sync_daemon"),
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
    "ProjectOutboxTask",
    "OfflineBodyUploadQueue",
    "ProjectSyncStore",
    "ProjectUnitOfWork",
    "LayoutGenerationAuthority",
    "LayoutWritePermit",
    "LayoutTestHooks",
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
    from specify_cli.identity.project import resolve_identity
    from specify_cli.status import (
        build_saas_lifecycle_queue_event,
        repo_root_for_lifecycle_log,
    )
    from specify_cli.sync.clock import LamportClock
    from specify_cli.sync.feature_flags import is_saas_sync_enabled
    from specify_cli.sync.queue import (
        OfflineQueue,
        read_queue_scope_from_session,
    )
    from specify_cli.sync.project_store import ProjectSyncStore

    if not is_saas_sync_enabled():
        return
    # Direct sync ingress is fail-closed to the Private Teamspace. Do NOT fall
    # back to the credentials file's team_slug: it stores whatever team was last
    # written (often a shared/primary team, e.g. `stijn`, not `stijn-private`),
    # so when the session read transiently returns None (a token refresh in
    # flight, a rehydrate miss) the old `session() or credentials()` silently
    # rerouted ingress to that team. That forks the producer-scoped journal
    # (`journal-<scope>.db`) and materializes the project under the wrong team on
    # the server, so the private->shared share can never find it (#738/#911).
    # `read_queue_scope_from_session` already fails closed (returns None rather
    # than a shared team, per `require_private_team_id`); honour that here and
    # skip queueing when the Private Teamspace can't be resolved, rather than
    # attribute the event to the wrong scope.
    scope = read_queue_scope_from_session()
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
    if not isinstance(event_type, str) or not isinstance(payload, Mapping) or not isinstance(aggregate_type, str):
        return

    repo_root = repo_root_for_lifecycle_log(log_path)
    if repo_root is None:
        return

    # Background SaaS fan-out: resolve identity WITHOUT persisting (#2263,
    # FR-001/FR-003) so the lifecycle handler never dirties .kittify/config.yaml.
    identity = resolve_identity(repo_root)
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
    store = ProjectSyncStore(str(identity.project_uuid))
    with store.unit_of_work() as unit:
        OfflineQueue(unit, store.layout_generation()).queue_event(event)

    # -----------------------------------------------------------------------
    # Daemon/WebSocket push for MissionCreated envelopes (FR-005, WP03)
    #
    # Before WP02, ``core/mission_creation.py`` called
    # ``sync.events.emit_mission_created`` directly, which also invoked
    # ``_publish_event_via_sync_daemon`` and ``_request_dashboard_sync``.
    # That direct CORE→INTEGRATION call was removed (Leak #1 fix). To
    # preserve the daemon/WebSocket behaviour for MissionCreated events,
    # we extend this observer to fire those calls here — inside the
    # registered observer only, zero new CORE imports needed.
    # -----------------------------------------------------------------------
    if event_type == "MissionCreated":
        from specify_cli.sync.events import (
            _publish_event_via_sync_daemon,
            _request_dashboard_sync,
        )

        _publish_event_via_sync_daemon(event, repo_root)
        _request_dashboard_sync(repo_root)


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

    Machine-arming gate (WP02 / FR-003, C-006): the SaaS **fan-out** handlers
    (dossier / saas / lifecycle) register only when ``sync_active()`` is armed;
    on the inactive path this function registers zero fan-out handlers and the
    daemon / capture / store-lock surfaces stay silent. The guard sits in the
    body (not at import-time and not a conditional definition) so the function
    stays unconditionally callable and re-reads the environment on every call —
    preserving the late-bind seam that lets co-gate tests re-invoke it after
    toggling ``SPEC_KITTY_ENABLE_SAAS_SYNC``.

    The per-project egress **consent resolver**, by contrast, registers
    UNCONDITIONALLY — machine arming is strictly upstream of, and never a
    replacement for, the consent gate (C-007). Registration is pure (no I/O, no
    spawn); the resolver only answers when an egress is actually attempted, and
    every egress site is itself arming-gated, so populating the CORE consent slot
    on the inactive path reintroduces none of the daemon / capture / store-lock
    noise WP02 removed. This restores the pre-#3799 invariant that importing this
    package always populates the slot, which ``egress.py::_egress_decision``
    relies on to answer ``NOT_CONSENTABLE`` / ``GRANTED`` for a real project
    instead of degrading every send to ``NO_RESOLVER`` on the default path.
    """
    with _contextlib.suppress(ImportError):
        from specify_cli.invocation.adapters import EgressConsent, register_egress_consent_resolver

        def _egress_consent_resolver(path: Path) -> EgressConsent:
            """Does the PROJECT that owns *path* consent to hosted sync, and why not? (#3030 FR-025)

            This slot used to answer ``routing.effective_sync_enabled`` — "is sync
            configured for this checkout" — and returned ``None`` for a path that is
            not a project root, which the propagator read as permission to send. Two
            corrections, in the two halves of the answer:

            **Which project is asking** comes from the checkout's resolved identity,
            via the read-only routing resolver. That is the mission's single
            derivation of checkout → project, and it already carries the FR-022 /
            FR-023 hardening: an unreadable or non-mapping ``.kittify/config.yaml``
            yields ``project_uuid=None`` instead of raising, and an unidentifiable
            project is never consentable (NFR-001), so it denies here.

            **Whether that project consents** comes from one call to
            ``consent.resolve_project_consent`` — the same authority used by the drain
            and emitter, walking the one declared precedence chain. Deliberately NOT
            ``effective_sync_enabled``: that chain also honours the repo-slug-keyed
            ``[sync.repo_defaults]`` record, which FR-019 condemns precisely because
            it is keyed on a mutable git remote and cannot speak for a project. One
            authority and one split mapping preserve the current main contract.

            Returns an ``EgressConsent`` member, never a bare bool. The registry seam
            maps a raise to ``UNANSWERABLE``; this resolver classifies ordinary
            absence, refusal, grant, and non-consentable paths explicitly.

            Imports at call time (not closure) so that test patches on
            ``specify_cli.sync.routing`` / ``specify_cli.sync.consent`` are respected.
            """
            from specify_cli.sync.consent import ConsentLevel, resolve_project_consent
            from specify_cli.sync.routing import resolve_checkout_sync_routing_readonly

            routing = resolve_checkout_sync_routing_readonly(path)
            if routing is None or not routing.project_uuid:
                return EgressConsent.NOT_CONSENTABLE
            uuid = str(routing.project_uuid)
            decision = resolve_project_consent(uuid, checkout_roots=[routing.repo_root])
            if decision.granted:
                return EgressConsent.GRANTED
            if decision.level is ConsentLevel.ABSENT:
                return EgressConsent.NO_RECORD
            return EgressConsent.RECORDED_REFUSAL

        register_egress_consent_resolver(_egress_consent_resolver)

    if not sync_active():
        return
    with _contextlib.suppress(ImportError):
        from specify_cli.status import register_dossier_sync_handler, register_lifecycle_saas_fanout_handler, register_saas_fanout_handler

        register_dossier_sync_handler(_dossier_sync_handler)
        register_saas_fanout_handler(_saas_fanout_handler)
        register_lifecycle_saas_fanout_handler(_lifecycle_saas_fanout_handler)

    # ------------------------------------------------------------------
    # No SaaS-client factory is registered here, and that is deliberate
    # (#3030 FR-032).
    #
    # A ``_saas_client_factory`` used to be registered at this point. Its whole
    # body was a lookup of ``getattr(token_manager, "_ws_client", None)`` — an
    # attribute **nothing in ``src/`` has ever assigned**: no ``=``, no
    # ``setattr``, and ``specify_cli/auth/`` does not declare it. Only tests
    # injected it. The live WebSocket client is a different attribute on a
    # different owner (``SyncRuntime.ws_client``, built in ``sync/runtime.py``
    # and handed to the emitter), so this factory returned ``None`` on every
    # production call and ``invocation/propagator.py``'s send has never executed
    # outside tests.
    #
    # Deleting it rather than leaving it removes a real hazard: a one-line
    # ``token_manager._ws_client = ...`` — the obvious-looking "fix" for "the
    # propagator never sends" — used to turn three egress paths live at once,
    # during a P0 confidentiality incident. It now turns on none of them.
    #
    # ``invocation/adapters.get_saas_client`` therefore answers ``None`` for
    # every production caller, which is the documented safe-degrade for that
    # seam ("no transport, so nothing can leave"). The propagator keeps its
    # FR-025 consent gate: the gate is checked *before* the client lookup and
    # protects the path whatever transport is registered later. Wiring this
    # slot to ``SyncRuntime.ws_client`` was considered and explicitly rejected;
    # anyone re-registering a factory here is opening a new egress path and
    # owns proving the gate above it holds.
    # ------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # Surviving MissionCreated SaaS fan-out path (FR-005 collapse, WP03):
    #
    #   emit_mission_created_local(feature_dir, ...)        ← status/lifecycle_events.py
    #       └── append_lifecycle_event(log_path, ...)
    #             └── fanout_lifecycle_event_hosted(...)
    #                   └── fire_lifecycle_saas_fanout(...)   ← status/adapters.py
    #                         └── _lifecycle_saas_fanout_handler()  ← this module
    #                               ├── OfflineQueue().queue_event(event)
    #                               └── [MissionCreated only]
    #                                   ├── _publish_event_via_sync_daemon(event, repo_root)
    #                                   └── _request_dashboard_sync(repo_root)
    #
    # The ``emit_mission_created`` module-level function in ``sync/events.py``
    # and the ``EventEmitter.emit_mission_created`` method in ``sync/emitter.py``
    # are NOT deleted — they remain as valid INTEGRATION-internal API (used by
    # tests and future sync-internal callers).  Neither is imported from any
    # CORE module after WP02.
    # -----------------------------------------------------------------------


# Initial registration at import time. Subsequent code (production or
# tests) can call ``register_default_handlers()`` again to repair the
# registry after a wipe.
if not is_truthy(os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT")):
    register_default_handlers()

if not is_truthy(os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT")):
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
            project_context: object,
            project_unit: object,
            project_layout: object,
        ) -> dict[str, object]:
            from specify_cli.sync.layout_generation import LayoutGenerationAuthority
            from specify_cli.sync.project_context import (
                ProjectSyncContext,
                validate_project_sync_context_authority,
            )
            from specify_cli.sync.project_store import ProjectUnitOfWork
            from specify_cli.sync.events import get_emitter

            if not isinstance(project_context, ProjectSyncContext):
                raise TypeError("dossier emission requires a store-minted ProjectSyncContext")
            if not isinstance(project_unit, ProjectUnitOfWork):
                raise TypeError("dossier emission requires the active project unit of work")
            if not isinstance(project_layout, LayoutGenerationAuthority):
                raise TypeError("dossier emission requires the project layout authority")
            validate_project_sync_context_authority(project_context)
            if project_unit.store_identity is not project_context.store_identity:
                raise ValueError("dossier project unit does not match the explicit project context")
            # Forward the sealed authority object to the explicit local-capture
            # seam. That seam never falls back to cwd/cached identity or direct
            # remote routing.
            result = get_emitter()._emit(
                event_type=event_type,
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                payload=payload,
                project_context=project_context,
                project_unit=project_unit,
                project_layout=project_layout,
            )
            return result if result is not None else {}

        register_dossier_emitter(_dossier_emit_via_sync)
