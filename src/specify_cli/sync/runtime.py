"""SyncRuntime: Lazy singleton managing WebSocket and background sync.

Provides a single entry point for background sync lifecycle management.
The runtime starts on first get_runtime() call (lazy initialization) and
stops cleanly on process exit via atexit handler.

Usage:
    from specify_cli.sync.runtime import get_runtime

    # Runtime auto-starts on first access
    runtime = get_runtime()

    # Attach emitter for WebSocket wiring
    runtime.attach_emitter(emitter)

    # Explicit shutdown (also happens via atexit)
    runtime.stop()
"""

from __future__ import annotations

import atexit
import asyncio
import contextlib
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from specify_cli.core.paths import locate_project_root
from specify_cli.diagnostics import invocation_succeeded

from .feature_flags import is_saas_sync_enabled, saas_sync_disabled_message
from .routing import is_sync_enabled_for_checkout

if TYPE_CHECKING:
    from .background import BackgroundSyncService
    from .body_queue import OfflineBodyUploadQueue
    from .client import WebSocketClient
    from .emitter import EventEmitter
    from .target_authority import ResolvedSyncTarget

logger = logging.getLogger(__name__)


def _safe_queue_size(queue_obj: object) -> int:
    """Best-effort queue size lookup that tolerates mocked test doubles."""
    try:
        raw = queue_obj.size()
    except Exception:
        return 0

    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _auto_start_enabled() -> bool:
    """Check if sync auto-start is enabled via config.

    Local checkout overrides win. If none is present, the remembered
    repository default from ``~/.spec-kitty/config.toml`` is used.

    Both unknowns deny (#3030 T028). This gate decides whether the daemon starts
    draining a project's events off the machine, so FR-003's rule applies to it as
    much as to the routing gate it consults: inability to determine consent is not
    consent. Previously **both** failure paths returned ``True`` — no locatable
    project root, and any exception resolving routing — which auto-started sync for
    a checkout whose consent nobody could establish. An explicit project-local
    ``sync.auto_start`` still wins; only the unknowns changed.

    Every denial is reported **here**, at a level the operator will actually see and
    naming the cause that actually fired (WP12 MINOR-3). The caller receives only a
    boolean, so it cannot know why, and the cause it used to guess — "disabled via
    config" — sent operators on a checkout with an unresolvable project root to edit
    a ``sync.auto_start`` key that was never consulted. Reporting the wrong cause is
    its own defect class: the operator's next action is decided by the explanation,
    not by the boolean.
    """
    cwd = Path.cwd()
    project_root = locate_project_root(cwd)
    if project_root is None:
        # No project root means no project identity, and consent is per project.
        logger.warning(
            "Sync auto-start denied: no spec-kitty project root is resolvable from %s. "
            "Consent is per project, so an unidentifiable project cannot consent. "
            "This is not a config setting — editing sync.auto_start will not change it.",
            cwd,
        )
        return False

    project_setting = _read_project_auto_start(project_root)
    if project_setting is not None:
        if not project_setting:
            logger.info(
                "Sync auto-start disabled by sync.auto_start in %s",
                project_root / ".kittify" / "config.yaml",
            )
        return project_setting

    # #3167 / C-001, operator decision D-M5a-1 = a: this Chain-B routing consult STAYS.
    # It answers "should the daemon start itself?", which is not an egress decision --
    # starting the runtime transmits nothing. ``sync.auto_start`` must never be unified
    # with ``sync.enabled``; see ``_read_project_auto_start``'s docstring just below and
    # ``consent.PROJECT_CONFIG_ENABLED_KEY`` for why that separation is binding rather
    # than incidental.
    #
    # Do NOT read this line -- or ``event_project_consents_to_publish`` further down --
    # as a gate that covers every path a started runtime can take. Neither does, and
    # the counter-example is already in the tree: a started runtime answers server pings
    # with a ``pong`` carrying a ``build_id`` (``client.py:_handle_ping``), a frame
    # ``event_project_consents_to_publish`` never sees. It is allowed deliberately, as
    # the ``E14`` ``TRANSPORT_ONLY`` entry in
    # ``tests/architectural/test_egress_consent_boundary.py``'s ``_EGRESS_ALLOWLIST``.
    #
    # Egress is enumerated PER SENDER, not by any single predicate: that allowlist names
    # every module that can reach the network and the seam each one carries, and E14's
    # own note records why the pong needs none (the callers that send project data --
    # emitter E11, local_commit E12, runtime E7 -- are each allowlisted with their own
    # seam). Audit coverage by reading that table, not by reading this function.
    #
    # The defence-in-depth options this decision declined -- D-M5a-1 (b) a consent
    # consult here, (c) removing this consult entirely -- are filed as
    # Priivacy-ai/spec-kitty#3199, so the residual has an owner.
    try:
        routing_enabled = is_sync_enabled_for_checkout(project_root)
    except Exception as e:
        logger.warning("Could not resolve sync routing config; denying auto-start: %s", e)
        return False

    if not routing_enabled:
        logger.info(
            "Sync auto-start denied: hosted sync is not enabled for checkout %s",
            project_root,
        )
    return routing_enabled


def _read_project_auto_start(project_root: Path) -> bool | None:
    """Read the legacy project-local ``sync.auto_start`` flag when present.

    ``sync.auto_start`` is NOT consent and must never be unified with
    ``sync.enabled`` (``sync/consent.py``'s ``PROJECT_CONFIG_ENABLED_KEY``). It
    answers "should the daemon start itself?" — a runtime convenience. ``sync.enabled``
    answers "may this project's data leave the machine?". Collapsing the two would let
    an autostart preference grant hosted-sync consent, which is the class of mistake
    #3030 exists to close. They live in the same YAML section only for historical
    reasons.
    """
    config_path = project_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return None

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Could not read project sync config from %s: %s", config_path, exc)
        return None

    if not isinstance(raw, dict):
        return None

    sync_section = raw.get("sync")
    if not isinstance(sync_section, dict):
        return None

    auto_start = sync_section.get("auto_start")
    return auto_start if isinstance(auto_start, bool) else None


def _offered_consent_roots() -> list[Path]:
    """The checkout available to offer ``sync/consent.py`` for its level-1 read.

    Offering the working directory is **narrowing-only**, not the cwd shortcut this
    module's gate exists to remove: ``consent._project_local_votes`` ignores any root
    whose ``.kittify/config.yaml`` declares a *different* ``project_uuid``, so a root
    can only ever answer for its own project. Without offering it, a project's own
    committed refusal would silently not be honoured on the one publish where the
    daemon does stand in that checkout.

    This is not a second copy of the precedence chain — it decides nothing. It only
    hands the resolver the file it is allowed to read.
    """
    try:
        root = locate_project_root(Path.cwd().resolve())
    except Exception:  # noqa: BLE001 - an unreadable cwd is absence, not a decision
        return []
    return [root] if root is not None else []


#: Projects already reported as refused, so the machine-global daemon does not warn
#: once per event for the lifetime of the process. Log-level state only: it can never
#: affect a decision, and a leaked entry only downgrades a message.
_reported_publish_refusals: set[str] = set()


def _report_publish_refusal(project_uuid: str | None, detail: str) -> None:
    """Report a refused publish once per project, at a level the operator will see.

    The first refusal for a project warns — an armed machine with a healthy daemon
    silently withholding a project's events is a misconfiguration the operator has to
    be told about, and this mission has already found that reporting the wrong cause
    (or none) decides the operator's next action. Every later refusal for the same
    project drops to debug: the daemon is long-lived and would otherwise bury its own
    log under one line per event forever.
    """
    key = project_uuid or "<unidentified>"
    template = "Real-time publish refused for project %s (#3030 FR-026): %s"
    if key in _reported_publish_refusals:
        logger.debug(template, key, detail)
        return
    _reported_publish_refusals.add(key)
    logger.warning(template, key, detail)


def event_project_consents_to_publish(event: object) -> bool:
    """May *this envelope's* project be published off the machine? (#3030 FR-026)

    The one predicate behind both daemon publish seams: :meth:`SyncRuntime.publish_event`
    (which the daemon's ``POST /api/sync/publish`` endpoint calls) and
    ``events._publish_event_via_sync_daemon`` (which the eleven ``emit_*`` wrappers and
    the ``MissionCreated`` lifecycle fan-out call). Both reach ``sync/consent.py``'s
    single chain through ``consented_project_uuids`` — the same seam the capture gate,
    the drain, the body upload and the LocalCommit flush use, so no second
    representation of consent is created (C-003).

    Resolved from **the event's own identity** via ``resolve_event_project_uuid``
    (T011's single chain, the same resolution the journal's stored column uses), and
    never from:

    * the working directory — cwd is whichever project the process happens to stand
      in, and the ``SyncRuntime``/daemon singleton outlives any ``os.chdir``;
    * the daemon's scope or the caller's ``repo_root`` — that is *scope*, not consent,
      and a scope grant authorising another project's publish is exactly the M1-1
      finding one level up;
    * ``is_saas_sync_enabled()`` — machine-global arming is never a grant, and it is
      the 2026-07-27 incident's own mechanism.

    An unresolvable uuid **denies** (FR-003, NFR-001): a missing, blank or nil-sentinel
    identity cannot be shown to belong to a consenting project. Fails **closed** on
    any error, departing from this module's best-effort habit — here that instinct
    would turn an unanswerable consent question into egress.

    Membership in the returned subset is checked for *this* uuid rather than the
    subset being non-empty. Equivalent only while exactly one candidate is passed; the
    day anyone batches envelopes through here, one consenting project would otherwise
    authorize every other project in the batch.
    """
    project_uuid: str | None = None
    try:
        from .consent import consented_project_uuids
        from .project_identity import resolve_event_project_uuid

        project_uuid = resolve_event_project_uuid(event if isinstance(event, dict) else None)
        if not project_uuid:
            _report_publish_refusal(
                None,
                "the event carries no resolvable project_uuid, so it cannot be shown "
                "to belong to a consenting project",
            )
            return False
        granted = project_uuid in consented_project_uuids(
            [project_uuid], checkout_roots=_offered_consent_roots()
        )
    except Exception as exc:  # noqa: BLE001 - inability to determine is not consent
        _report_publish_refusal(
            project_uuid, f"hosted-sync consent could not be resolved: {exc}"
        )
        return False

    if not granted:
        _report_publish_refusal(
            project_uuid,
            "the project has not consented to hosted sync. Arming the machine "
            "(SPEC_KITTY_ENABLE_SAAS_SYNC) is not consent — run `spec-kitty sync "
            "opt-in` inside that project's own checkout",
        )
    return granted


@dataclass
class SyncRuntime:
    """Background sync runtime managing WebSocket and queue.

    The runtime coordinates:
    - BackgroundSyncService: Periodic queue flush
    - WebSocketClient: Real-time event streaming (if authenticated)
    - EventEmitter wiring: Connects WS client to emitter when available

    Thread-safe and idempotent: start() can be called multiple times.
    """

    background_service: BackgroundSyncService | None = field(default=None, repr=False)
    ws_client: WebSocketClient | None = field(default=None, repr=False)
    emitter: EventEmitter | None = field(default=None, repr=False)
    body_queue: OfflineBodyUploadQueue | None = field(default=None, repr=False)
    # Target authority (WP02, contract §1): the one resolved sync target this
    # runtime keys off, populated before the WebSocket connect. WebSocket,
    # tracker, queue scope and status all trace back to this single target.
    resolved_target: ResolvedSyncTarget | None = field(default=None, repr=False)
    _async_loop: asyncio.AbstractEventLoop | None = field(default=None, repr=False)
    _async_loop_thread: threading.Thread | None = field(default=None, repr=False)
    _build_registered: bool = False
    started: bool = False

    def start(self) -> None:
        """Start background services (idempotent).

        - Starts BackgroundSyncService for queue processing
        - Connects WebSocket if authenticated
        - Safe to call multiple times
        """
        if self.started:
            return

        if not is_saas_sync_enabled():
            logger.info("%s SyncRuntime not started.", saas_sync_disabled_message())
            return

        # Check the auto-start gate. It has already reported *why* it denied, at a
        # level the operator sees; restating a cause here would be a guess, and the
        # guess this line used to make ("via config") was wrong for every denial
        # except the config one (WP12 MINOR-3).
        if not _auto_start_enabled():
            logger.debug("Sync auto-start gate denied; SyncRuntime not started.")
            return

        # Start background service (use existing singleton)
        from .background import get_sync_service
        self.background_service = get_sync_service()

        # Create body queue sharing same DB as event queue (C-001)
        from .body_queue import OfflineBodyUploadQueue
        self.body_queue = OfflineBodyUploadQueue(
            db_path=self.background_service.queue.db_path,
        )
        self.background_service._body_queue = self.body_queue
        if _safe_queue_size(self.background_service.queue) > 0 or _safe_queue_size(self.body_queue) > 0:
            self.background_service.wake()

        self._ensure_async_loop()

        # Connect WebSocket if authenticated
        self._connect_websocket_if_authenticated()

        self.started = True
        logger.debug("SyncRuntime started")

    def _connect_websocket_if_authenticated(self) -> None:
        """Attempt WebSocket connection if user is authenticated."""
        from specify_cli.auth import get_token_manager

        tm = get_token_manager()

        if tm.is_authenticated:
            try:
                from .client import WebSocketClient

                project_identity = self._attached_project_identity()
                # Target authority (WP02, contract §1): resolve the one canonical
                # target ONCE before opening the WebSocket so every surface keys
                # off the same ``resolved_server_url`` (and the split-brain guard
                # runs before any network call). The WebSocket transport reads
                # the same env/config the resolver consumed.
                self.resolved_target = self._resolve_runtime_target()
                if self.resolved_target is not None:
                    logger.debug(
                        "Sync runtime target resolved: %s (override_mode=%s)",
                        self.resolved_target.resolved_server_url,
                        self.resolved_target.override_mode.value,
                    )
                self.ws_client = WebSocketClient(project_identity=project_identity)
                self._ensure_async_loop()
                if self._async_loop is None:
                    logger.info("Async loop unavailable; events will be queued for batch sync")
                    return
                future = asyncio.run_coroutine_threadsafe(self.ws_client.connect(), self._async_loop)
                future.add_done_callback(self._log_async_future_error)

                # Wire WebSocket to emitter if already attached
                if self.emitter is not None:
                    self.emitter.ws_client = self.ws_client
                    if project_identity is not None:
                        self.ws_client._project_identity = project_identity
                logger.debug("WebSocket connect scheduled")
            except Exception as e:
                logger.warning(f"WebSocket connection failed: {e}")
                logger.info("Events will be queued for batch sync")
        else:
            logger.info("Not authenticated; events queued locally")
            logger.info("Run 'spec-kitty auth login' to enable real-time sync")

    def _attached_project_identity(self) -> object | None:
        """Return the attached emitter's project identity when it is usable."""
        if self.emitter is None:
            return None

        try:
            identity = self.emitter._get_identity()
        except Exception as exc:
            logger.debug("Could not resolve project identity from emitter: %s", exc)
            return None

        build_id = getattr(identity, "build_id", None)
        if not isinstance(build_id, str) or not build_id:
            return None
        return identity

    def _resolve_runtime_target(self) -> ResolvedSyncTarget | None:
        """Resolve the canonical sync target via the config-backed resolver.

        Target authority (WP02, contract §1): the runtime obtains its one
        ``ResolvedSyncTarget`` through :meth:`SyncConfig.resolve_runtime_target`
        (the resolver-backed entry point) rather than reading config/env
        directly. Resolution is purely descriptive and must never break the
        runtime, so any failure degrades to ``None`` (the WebSocket transport
        still resolves its own URL from the same env/config).
        """
        try:
            from .config import SyncConfig

            return SyncConfig().resolve_runtime_target()
        except Exception as exc:
            logger.debug("Could not resolve canonical sync target: %s", exc)
            return None

    def _attached_repo_slug(self) -> str | None:
        """Return the repo slug from the attached emitter, if available."""
        if self.emitter is None:
            return None
        try:
            git_meta = self.emitter._get_git_metadata()
        except Exception as exc:
            logger.debug("Could not resolve git metadata from emitter: %s", exc)
            return None
        repo_slug = getattr(git_meta, "repo_slug", None)
        return repo_slug if isinstance(repo_slug, str) and repo_slug else None

    def _ensure_async_loop(self) -> None:
        """Create a dedicated asyncio loop for daemon-owned WebSocket transport."""
        if self._async_loop is not None and self._async_loop_thread is not None and self._async_loop_thread.is_alive():
            return

        loop = asyncio.new_event_loop()

        def _run_loop() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(
            target=_run_loop,
            name="spec-kitty-sync-async-loop",
            daemon=True,
        )
        thread.start()
        self._async_loop = loop
        self._async_loop_thread = thread

    def _log_async_future_error(self, future: object) -> None:
        """Log exceptions from asyncio.run_coroutine_threadsafe futures."""
        try:
            future.result()
        except Exception as exc:
            logger.debug("Async sync task failed: %s", exc)

    def get_websocket_status(self) -> str:
        """Expose current WebSocket connection status."""
        if self.ws_client is None:
            return "Offline"
        return self.ws_client.get_status()

    def publish_event(self, event: dict[str, object]) -> bool:
        """Best-effort real-time event publish via the daemon-owned WebSocket.

        **This is an egress point, so it owns its own refusal (#3030 FR-026).** The
        consent decision is made here, from the envelope's own ``project_uuid``, and is
        not inherited from anything the caller computed: the daemon is machine-global
        and auto-starts for whichever project ``cwd`` belonged to, so its scope, its
        arming flag and its caller's ``repo_root`` all describe a *different* project
        than the envelope may. M1-1 was exactly the failure of resting this boundary on
        a value computed elsewhere.

        The refusal precedes every side effect, ``start()`` included: a non-consenting
        project's envelope must not be the thing that brings the transport up, and
        placing the gate first keeps the refusal independent of auth, arming and the
        auto-start gate.

        Refusal is **transmission-only** — the callers' durable outbox write already
        happened and is deliberately not consent-gated (see the recorded ``queue_event``
        judgement above ``emitter._route_event``), so nothing is dropped here that
        would otherwise have been kept.
        """
        if not event_project_consents_to_publish(event):
            return False

        if not self.started:
            self.start()

        if self.ws_client is None or self._async_loop is None:
            self._connect_websocket_if_authenticated()
            return False

        if not self.ws_client.connected:
            self._connect_websocket_if_authenticated()
            return False

        try:
            future = asyncio.run_coroutine_threadsafe(self.ws_client.send_event(event), self._async_loop)
            future.result(timeout=2.0)
            return True
        except Exception as exc:
            logger.debug("WebSocket publish failed: %s", exc)
            return False

    def attach_emitter(self, emitter: EventEmitter) -> None:
        """Attach emitter so WS client can be injected.

        Called by get_emitter() after creating the EventEmitter instance.
        If WebSocket is already connected, wires it to the emitter.

        Auto-emits ``BuildRegistered`` for the active checkout when the
        project identity is complete. ``repo_slug`` is intentionally not
        a precondition (issue #1074): fresh / local-only / detached
        projects without a git remote still get a build-level
        registration event, so SaaS can materialize the project even
        before a remote is configured.
        """
        self.emitter = emitter
        identity = self._attached_project_identity()
        if self.ws_client is not None:
            self.emitter.ws_client = self.ws_client
            if identity is not None:
                self.ws_client._project_identity = identity

        if (
            not self._build_registered
            and identity is not None
            and getattr(identity, "is_complete", False) is True
        ):
            event = emitter.emit_build_registered()
            if event is not None:
                self._build_registered = True
                if self.background_service is not None:
                    self.background_service.wake()

    def stop(self) -> None:
        """Stop background services gracefully.

        Disconnects WebSocket and stops background sync service.
        Safe to call multiple times or if not started.

        FR-008: When ``invocation_succeeded()`` returns True, WebSocket
        teardown warnings should be downgraded so they don't paint red
        over a clean stdout JSON payload (#735). Final sync failures are
        reported by ``BackgroundSyncService.stop`` as structured non-fatal
        diagnostics on stderr.
        """
        if not self.started:
            return

        succeeded = invocation_succeeded()

        if self.ws_client:
            try:
                if self._async_loop is not None:
                    future = asyncio.run_coroutine_threadsafe(self.ws_client.disconnect(), self._async_loop)
                    future.result(timeout=5.0)
            except Exception as exc:
                if succeeded:
                    logger.debug(
                        "WebSocket disconnect failed during post-success shutdown: %s",
                        exc,
                    )
                else:
                    logger.debug("WebSocket disconnect failed during shutdown: %s", exc)
            self.ws_client = None

        if self.background_service:
            self.background_service.stop()
            self.background_service = None

        if self._async_loop is not None:
            with contextlib.suppress(Exception):
                self._async_loop.call_soon_threadsafe(self._async_loop.stop)
        if self._async_loop_thread is not None and self._async_loop_thread.is_alive():
            self._async_loop_thread.join(timeout=5.0)
        if self._async_loop is not None:
            with contextlib.suppress(Exception):
                self._async_loop.close()
        self._async_loop = None
        self._async_loop_thread = None
        self.body_queue = None
        self._build_registered = False
        self.started = False
        logger.debug("SyncRuntime stopped")


# ── Singleton accessor ────────────────────────────────────────────

_runtime: SyncRuntime | None = None
_runtime_lock = threading.Lock()


def get_runtime() -> SyncRuntime:
    """Get or create the singleton SyncRuntime instance.

    Thread-safe via double-checked locking pattern.
    Runtime starts on first access (lazy initialization).
    """
    global _runtime
    if _runtime is None:
        with _runtime_lock:
            if _runtime is None:
                runtime = SyncRuntime()
                # Publish only after a successful start (#3030 H8). start() can
                # raise — e.g. the T007 legacy-queue guard — and assigning first
                # cached an unstarted runtime that every later call returned
                # without ever retrying start().
                runtime.start()
                _runtime = runtime
    return _runtime


def reset_runtime() -> None:
    """Reset the singleton (for testing only)."""
    global _runtime
    with _runtime_lock:
        if _runtime is not None:
            _runtime.stop()
        _runtime = None


def _shutdown_runtime() -> None:
    """atexit handler for graceful shutdown."""
    global _runtime
    if _runtime is not None:
        _runtime.stop()


atexit.register(_shutdown_runtime)
