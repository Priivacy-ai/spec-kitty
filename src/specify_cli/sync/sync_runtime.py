"""Runtime-open / lifecycle + config-I/O adapters for the ``spec-kitty sync``
command surface (WP05).

The Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``)
relocates the runtime-open / lifecycle openers and the event-sync config
readers/writers off the single ``cli/commands/sync.py`` host into this cohesive
seam module (one adapter per port, ``DIRECTIVE_044`` — the shared port home is
:mod:`specify_cli.agent_tasks_ports`). This is a **pure move** (INV-1): every
opener body, authority call, and config token is byte-identical to the inline
form it replaces. The WP02 golden + the ~60 patch-tests are the guard.

**The read-vs-dispatch authority split (architect A-2 / plan IC-03) is
preserved.** :func:`_open_event_sync_runtime` is the READ-authority open (no
auth, no network, no delivery-target resolution);
:func:`_open_project_dispatch_runtime` is the DISPATCH-authority open bound to a
delivery target. They are **two distinct functions** — deliberately not
de-duplicated. ``_open_project_dispatch_runtime`` irreducibly mixes read+write
authority at the flow level and is **frozen verbatim (C-007)**: its authority
calls are relocated in the same order, with the same arguments, never purified
or merged. (#3620: one negotiated-admission step —
``admission_negotiation.maybe_admit_locally`` — is inserted before
``store.create_context()`` / the delivery-target lookup; this is an addition
to the sequence, not a reordering or removal of the frozen calls above.)

**Late-bound host access (INV-4 / WP03 convention).** A relocated opener that
must call a monkeypatched ``sync`` seam callee — or reach a host helper that
deliberately still lives on the host (``_current_event_sync_scope`` and, until
WP07 relocates them, ``_assert_event_sync_runtime_authority`` /
``_assert_delivery_target_matches_context``) — reaches it by ATTRIBUTE ACCESS on
the host module object (``sync_module.<name>``), never by an early-bound
``from ...cli.commands.sync import <name>``. The ``import ... as sync_module`` is
kept FUNCTION-LOCAL so this module has no import-time dependency on the host (the
host imports THIS module from its husk re-export block, so a module-level
back-import would be circular). ``tests/architectural/test_sync_no_early_bind.py``
is the AST guard that fails any early-bind of a seam name.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import typer

from specify_cli.cli.console import console

if TYPE_CHECKING:
    from specify_cli.delivery.config import EventSyncConfig, Mode
    from specify_cli.identity.project import ProjectIdentity
    from specify_cli.sync.target_authority import ResolvedSyncTarget

_LOG = logging.getLogger(__name__)

# Operator event-sync mode is persisted under a dedicated config.toml table so
# it never collides with the [sync] target-authority keys (FR-016 / C-007).
_EVENT_SYNC_TABLE = "event_sync"
_EVENT_SYNC_MODE_KEY = "mode"
_EVENT_SYNC_ENDPOINT_KEY = "external_endpoint"


@dataclass
class _EventSyncRuntime:
    """The already-resolved domain handles the thin CLI hands to the dispatcher
    / status-report / retention modules. The CLI never derives scope or URLs
    itself — it only opens these and passes them through (contract §1)."""

    target: ResolvedSyncTarget | None
    store: Any
    context: Any
    delivery_target: Any | None
    checkout_identity: ProjectIdentity | None = None

    def close(self) -> None:
        return None


@dataclass(frozen=True)
class _ProjectDispatchRuntime:
    """ProjectSyncStore-backed handles for canonical live dispatcher sends only."""

    target: ResolvedSyncTarget
    store: Any
    context: Any
    delivery_target: Any | None

    def close(self) -> None:
        return None


def _open_event_sync_runtime(*, include_target: bool = True) -> _EventSyncRuntime:
    """Open local project state for status/retention without auth or network."""
    import specify_cli.cli.commands.sync as sync_module
    from specify_cli.identity.project import ProjectIdentity
    from specify_cli.sync.layout_generation import LayoutMode
    from specify_cli.sync.project_store import ProjectSyncStore
    from specify_cli.sync.routing import resolve_checkout_sync_routing_readonly
    from specify_cli.sync.target_authority import resolve_sync_target

    routing = resolve_checkout_sync_routing_readonly()
    if routing is None or routing.project_uuid is None:
        raise FileNotFoundError("event-sync project store unavailable: active checkout has no project_uuid")
    store = ProjectSyncStore(routing.project_uuid)
    layout = store.layout_generation().peek_state()
    if layout.mode is not LayoutMode.PROJECT_ONLY:
        raise RuntimeError(
            f"event-sync project store migration required before status or retention (layout={layout.mode.value}); run `spec-kitty sync project-store-migrate`"
        )
    if not store.database_path.exists():
        raise FileNotFoundError(f"event-sync project store DB absent: {store.database_path}")
    scope = sync_module._current_event_sync_scope() if include_target else None
    return _EventSyncRuntime(
        target=(resolve_sync_target(user_id=scope.user_id, team_slug=scope.team_slug) if scope is not None else None),
        store=store,
        context=None,
        delivery_target=None,
        checkout_identity=ProjectIdentity(
            project_uuid=(UUID(str(routing.project_uuid)) if routing.project_uuid is not None else None),
            project_slug=routing.project_slug,
            repo_slug=routing.repo_slug,
            build_id=routing.build_id,
        ),
    )


def _open_project_dispatch_runtime(
    *,
    create: bool = True,
    require_project_only: bool = False,
) -> _ProjectDispatchRuntime:
    """Resolve ProjectSyncStore-backed authority for canonical live dispatch only."""
    import specify_cli.cli.commands.sync as sync_module
    from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
    from specify_cli.sync.project_store import ProjectSyncStore
    from specify_cli.sync.routing import resolve_checkout_sync_routing, resolve_checkout_sync_routing_readonly
    from specify_cli.sync.target_authority import resolve_sync_target

    scope = sync_module._current_event_sync_scope()
    target = resolve_sync_target(user_id=scope.user_id, team_slug=scope.team_slug)
    routing = resolve_checkout_sync_routing() if create else resolve_checkout_sync_routing_readonly()
    if routing is None or routing.project_uuid is None:
        raise FileNotFoundError("event-sync project store unavailable: active checkout has no project_uuid")
    store = ProjectSyncStore(routing.project_uuid)
    if require_project_only:
        from specify_cli.sync.layout_generation import LayoutMode

        layout = store.layout_generation().peek_state()
        if layout.mode is not LayoutMode.PROJECT_ONLY:
            raise RuntimeError(
                f"event-sync project store migration required before status or retention (layout={layout.mode.value}); run `spec-kitty sync project-store-migrate`"
            )
    if not create and not store.database_path.exists():
        raise FileNotFoundError(f"event-sync project store DB absent: {store.database_path}")
    from specify_cli.sync.admission_negotiation import maybe_admit_locally

    # #3620: negotiated admission. A no-op unless the project is consented,
    # authenticated, not already admitted, and the resolved server has not
    # advertised strict admission (dormant until SaaS #795 ships) — see the
    # module docstring above and admission_negotiation.py for the full guard
    # matrix. Must run BEFORE create_context()/get_current below so a fresh
    # local self-admission is visible to both.
    maybe_admit_locally(store, target=target, routing_project_uuid=str(routing.project_uuid))
    context = store.create_context()
    delivery_target = None
    with store.unit_of_work() as unit:
        registry = ProjectDeliveryTargetRegistry(store)
        delivery_target = registry.get_current(unit)
    if delivery_target is not None:
        sync_module._assert_event_sync_runtime_authority(
            target=target,
            delivery_target=delivery_target,
            routing_project_uuid=str(routing.project_uuid),
        )
        sync_module._assert_delivery_target_matches_context(
            delivery_target=delivery_target,
            context=context,
        )
    return _ProjectDispatchRuntime(
        target=target,
        context=context,
        store=store,
        delivery_target=delivery_target,
    )


def _open_event_sync_runtime_readonly() -> _EventSyncRuntime:
    """Open runtime handles only when DBs already exist."""
    import specify_cli.cli.commands.sync as sync_module

    runtime: _EventSyncRuntime = sync_module._open_event_sync_runtime()
    return runtime


def _open_retention_runtime_or_exit() -> _EventSyncRuntime:
    """Open canonical local retention state with user-facing migration guidance."""
    import specify_cli.cli.commands.sync as sync_module

    try:
        runtime: _EventSyncRuntime = sync_module._open_event_sync_runtime(include_target=False)
        return runtime
    except (FileNotFoundError, RuntimeError) as exc:
        console.print(f"[red]Retention unavailable:[/red] {exc}")
        raise typer.Exit(1) from exc


def _event_sync_config_path() -> Path:
    from specify_cli.sync.config import SyncConfig

    return Path(SyncConfig().config_file)


def _read_event_sync_table() -> dict[str, Any]:
    """Best-effort read of the ``[event_sync]`` config table (empty when absent)."""
    import toml

    path = _event_sync_config_path()
    if not path.exists():
        return {}
    try:
        data = toml.load(path)
    except (toml.TomlDecodeError, OSError):
        return {}
    table = data.get(_EVENT_SYNC_TABLE)
    return table if isinstance(table, dict) else {}


def _load_event_sync_config() -> EventSyncConfig:
    """Reconstruct the persisted :class:`EventSyncConfig` (defaults to TEAMSPACE).

    Mode semantics are owned by WP09 — the CLI only stores/reads the token and
    rebuilds the config through ``EventSyncConfig.from_mode``.
    """
    from specify_cli.delivery.config import EventSyncConfig, EventSyncConfigError, Mode

    table = _read_event_sync_table()
    token = table.get(_EVENT_SYNC_MODE_KEY)
    if not token:
        return EventSyncConfig.from_mode(Mode.TEAMSPACE)
    endpoint = table.get(_EVENT_SYNC_ENDPOINT_KEY)
    try:
        return EventSyncConfig.from_mode(
            Mode.from_token(str(token)),
            external_endpoint=str(endpoint) if endpoint else None,
        )
    except EventSyncConfigError as exc:
        # A corrupt persisted token must not break read paths (status/now).
        _LOG.debug("event-sync mode %r unusable, defaulting to TEAMSPACE: %s", token, exc)
        return EventSyncConfig.from_mode(Mode.TEAMSPACE)


def _write_event_sync_config(mode: Mode, external_endpoint: str | None) -> None:
    """Persist the operator's event-sync mode token (and optional endpoint)."""
    import toml

    from specify_cli.core.atomic import atomic_write

    path = _event_sync_config_path()
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = toml.load(path)
        except (toml.TomlDecodeError, OSError):
            data = {}
    table = data.get(_EVENT_SYNC_TABLE)
    if not isinstance(table, dict):
        table = {}
        data[_EVENT_SYNC_TABLE] = table
    table[_EVENT_SYNC_MODE_KEY] = mode.value
    if external_endpoint:
        table[_EVENT_SYNC_ENDPOINT_KEY] = external_endpoint
    else:
        table.pop(_EVENT_SYNC_ENDPOINT_KEY, None)
    atomic_write(path, toml.dumps(data), mkdir=True)


def _event_sync_access_token() -> str:
    """Best-effort Bearer token for the Teamspace receiver (empty when absent).

    The dispatcher never POSTs an empty selection, so an absent token degrades
    safely to no delivery rather than an error.
    """
    import asyncio

    from specify_cli.auth import get_token_manager

    try:
        token_manager = get_token_manager()
        if not token_manager.is_authenticated:
            return ""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            token = loop.run_until_complete(token_manager.get_access_token())
        finally:
            with contextlib.suppress(Exception):
                asyncio.set_event_loop(None)
            loop.close()
        return token or ""
    except Exception as exc:  # best-effort credential read; never block a drain
        _LOG.debug("event-sync access token unavailable: %s", exc)
        return ""


def _open_active_body_queue(
    runtime: _EventSyncRuntime,
    unit: Any,
    *,
    max_queue_size: int,
) -> Any:
    """Open the body-upload queue for the WP11 ``body_upload_compatibility``
    section, or ``None`` when it cannot be read (the section then reports zeros)."""
    try:
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue

        return OfflineBodyUploadQueue(
            unit,
            runtime.store.layout_generation(),
            max_queue_size=max_queue_size,
        )
    except Exception as exc:  # read-only diagnostic; never fail status on it
        _LOG.debug("body-upload queue unavailable for status report: %s", exc)
        return None


class _ScopedStatusJournal:
    """Journal proxy that keeps its caller-owned read UoW active until closed."""

    def __init__(self, journal: Any, unit_context: Any) -> None:
        self._journal = journal
        self._unit_context = unit_context

    def __getattr__(self, name: str) -> Any:
        return getattr(self._journal, name)

    def close(self) -> None:
        self._unit_context.__exit__(None, None, None)


def _open_journal_readonly() -> Any:
    """Open the canonical project journal in one scoped read UoW (#3030 T021).

    Deliberately not ``_open_event_sync_runtime_readonly``, which also resolves the
    delivery target and opens the ledger and target registry. A "whose data is in
    here?" read needs none of those, and sharing that opener meant any
    target-resolution failure was reported as "the event journal could not be
    read" — the wrong diagnosis, naming the wrong store, in the one section whose
    job is to be trustworthy about which store it read.

    Raises ``FileNotFoundError`` when this scope has no journal file yet, which the
    caller renders as the benign absence it is.
    """
    from specify_cli.event_journal.journal import EventJournal

    runtime = _open_event_sync_runtime_readonly()
    unit_context = runtime.store.unit_of_work()
    unit = unit_context.__enter__()
    try:
        return _ScopedStatusJournal(
            EventJournal(unit, runtime.store.layout_generation()),
            unit_context,
        )
    except BaseException:
        unit_context.__exit__(None, None, None)
        raise
