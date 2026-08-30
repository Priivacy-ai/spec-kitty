"""T052 (WP11): cross-platform physical isolation of per-project sync stores.

NFR-001 demands *observed* isolation, not inferred isolation: store-open
instrumentation must record zero cross-project file opens across a full
operation matrix. NFR-005 demands that the same canonical UUID resolves to one
deterministic, ASCII-safe store path regardless of how a platform spells it —
Windows registry braces, uppercase hex, bare 32-hex — and regardless of what
Unicode display name, symlinked checkout root, or worktree the project lives in.

This file does not need to *run* on Windows to cover Windows-shaped inputs: the
platform differences that matter here are **identity spellings** (``{...}`` /
uppercase / undashed UUID text) and **path aliases** (case-variant tokens,
symlinks, multiple checkout roots), all of which are constructed portably and
pushed through the real resolver (``CanonicalProjectUUID`` /
``ProjectStorePaths`` / ``ProjectSyncStore``).

Instrumentation follows the pattern proven by
``tests/delivery/test_nfr003_predicate_cost_3030.py::measure``: patch
``sqlite3.connect`` process-wide (recording every database argument and tracing
every statement) plus ``builtins.open`` / ``io.open`` / ``os.open`` for
non-SQLite filesystem opens. The census is then checked against project B's
store root. Because each project store is its own database file, a project-B
*table* is only reachable through project-B's *file* (or an ``ATTACH`` naming
it), so "no B database file opened and no executed statement mentions B" is the
complete table-level claim.

Per the NFR-004 mutant-control idiom
(``tests/architectural/test_unfiltered_journal_read_boundary.py::TestGuardBites``),
a guard never observed to fail is decoration: ``TestSharedResolverMutantControl``
forces ``ProjectStorePaths.for_project`` to resolve every UUID onto one shared
path and asserts the isolation assertion FAILS, proving the census measures
real opens rather than vacuously passing.
"""

from __future__ import annotations

import builtins
import io
import json
import os
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from specify_cli.delivery.consent_gate import ConsentedBatch
from specify_cli.delivery.dispatcher import DispatchSummary, dispatch
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import (
    DeliveryEffectCertainty,
    DeliveryOutcome,
    DeliveryResult,
    ReceiverGate,
    StubReceiver,
)
from specify_cli.delivery.retention import purge_project_events
from specify_cli.delivery.status_report import build_per_project_store_report
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.identity.project import (
    ProjectIdentity,
    atomic_write_config,
    load_identity,
)
from specify_cli.paths import get_runtime_root
from specify_cli.sync.consent import (
    ConsentAuthorityStatus,
    read_project_consent_decision,
    record_project_opt_in,
    record_project_opt_out,
)
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_identity import CanonicalProjectUUID, ProjectStorePaths
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.project_store_migration import LegacyProjectStoreMigration

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "aaaaaaaa-1111-1111-1111-111111111111"
UUID_B = "bbbbbbbb-2222-2222-2222-222222222222"
#: A third identity the mutant collapses everything onto — deliberately neither
#: A nor B so the shared store initializes cleanly instead of tripping the
#: store's own owner-mismatch guard (which would mask what the mutant proves).
UUID_SHARED_MUTANT = "cccccccc-3333-3333-3333-333333333333"

_ACTOR = "t052-cross-platform-test"

#: Platform spellings of the SAME canonical identity. Windows tooling emits
#: registry-braced and uppercase forms; undashed 32-hex appears in URL-safe
#: contexts. All must resolve to one lowercase hyphenated ASCII store token.
PLATFORM_UUID_SPELLINGS = (
    pytest.param(UUID_A.upper(), id="windows-uppercase"),
    pytest.param("{" + UUID_A + "}", id="windows-registry-braced"),
    pytest.param("{" + UUID_A.upper() + "}", id="windows-registry-braced-uppercase"),
    pytest.param(UUID_A.replace("-", ""), id="undashed-32-hex"),
    pytest.param("AaAaAaAa-1111-1111-1111-111111111111", id="mixed-case"),
)


@pytest.fixture(autouse=True)
def home(canonical_home: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated runtime root; arming env set (arming is NOT consent — #3030)."""
    del canonical_home  # the ONE SPEC_KITTY_HOME owner (R1a #3121) pins the home
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    return tmp_path / "home"


# --------------------------------------------------------------------------- #
# Instrumentation (pattern: tests/delivery/test_nfr003_predicate_cost_3030.py) #
# --------------------------------------------------------------------------- #


@dataclass
class OpenCensus:
    """Every SQLite connect, filesystem open, and executed statement observed."""

    sqlite_databases: list[str] = field(default_factory=list)
    file_opens: list[str] = field(default_factory=list)
    statements: list[str] = field(default_factory=list)


def _normalize_sqlite_database(raw: str) -> str:
    """Strip the ``file:`` URI wrapper (read-only opens) down to a plain path."""
    if raw.startswith("file:"):
        return raw[len("file:") :].split("?", maxsplit=1)[0]
    return raw


@contextmanager
def measure() -> Iterator[OpenCensus]:
    """Record every ``sqlite3.connect`` target, statement, and filesystem open.

    ``sqlite3.connect`` is patched process-wide with a wrapper that records the
    database argument and attaches a trace callback to the returned connection,
    so *every* statement executed anywhere during the block is captured.
    ``builtins.open`` / ``io.open`` (one function, two lookup sites — ``pathlib``
    resolves ``io.open`` at call time) and ``os.open`` cover non-SQLite opens
    such as lock files and atomic writes. All originals are restored on exit
    even if the body raises.
    """
    census = OpenCensus()
    real_connect = sqlite3.connect
    real_open = builtins.open
    real_os_open = os.open

    def _connect(
        database: str | bytes | os.PathLike[str] | os.PathLike[bytes] = ":memory:",
        *args: Any,
        **kwargs: Any,
    ) -> sqlite3.Connection:
        census.sqlite_databases.append(os.fsdecode(database))
        conn = cast("sqlite3.Connection", real_connect(database, *args, **kwargs))

        def _trace(statement: str | None) -> None:
            census.statements.append(statement or "")

        conn.set_trace_callback(_trace)
        return conn

    def _open(file: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, (str, bytes, os.PathLike)):
            census.file_opens.append(os.fsdecode(file))
        return real_open(file, *args, **kwargs)

    def _os_open(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        if isinstance(path, (str, bytes, os.PathLike)):
            census.file_opens.append(os.fsdecode(path))
        return real_os_open(path, flags, mode, dir_fd=dir_fd)

    with (
        patch.object(sqlite3, "connect", _connect),
        patch.object(builtins, "open", _open),
        patch.object(io, "open", _open),
        patch.object(os, "open", _os_open),
    ):
        yield census


def _project_root(project_uuid: str) -> Path:
    """The whole ``projects/<token>`` directory a UUID resolves to right now.

    Deliberately routed through ``ProjectStorePaths.for_project`` — the same
    resolver production uses — so the mutant control below exercises the exact
    assertion the real test relies on.
    """
    return ProjectStorePaths.for_project(project_uuid).sync_directory.parent


def _is_under(raw: str, root: Path) -> bool:
    candidate = Path(raw)
    if candidate.is_relative_to(root):
        return True
    try:
        return candidate.resolve().is_relative_to(root.resolve())
    except OSError:  # unresolvable pseudo-paths like ":memory:" stay outside
        return False


def _paths_touched_under(census: OpenCensus, root: Path) -> list[str]:
    recorded = [_normalize_sqlite_database(raw) for raw in census.sqlite_databases]
    recorded.extend(census.file_opens)
    return [raw for raw in recorded if _is_under(raw, root)]


def _assert_no_project_b_resources_opened(census: OpenCensus, foreign_uuid: str) -> None:
    """The single NFR-001 isolation assertion (shared with the mutant control).

    File level: no recorded SQLite connect or filesystem open lies under the
    foreign project's store root. Table level: each store is its own database
    file, so a foreign table is only reachable through that file or an
    ``ATTACH`` naming it — and no executed statement may mention the foreign
    token at all.
    """
    foreign_root = _project_root(foreign_uuid)
    offenders = sorted(set(_paths_touched_under(census, foreign_root)))
    assert not offenders, f"project A operations opened project-B resources under {foreign_root}: {offenders}"
    token = CanonicalProjectUUID.parse(foreign_uuid).storage_token
    foreign_sql = [statement for statement in census.statements if token in statement.lower()]
    assert not foreign_sql, f"project A operations executed SQL naming project B ({token}): {foreign_sql}"


# --------------------------------------------------------------------------- #
# Store seeding and the full operation set                                     #
# --------------------------------------------------------------------------- #


def _event(event_id: str, uuid: str, created_at: str) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id, "project_uuid": uuid}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
    )


def _admit(store: ProjectSyncStore) -> None:
    """Project-only layout, explicit opt-in, and an admitted target binding."""
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover(_ACTOR)
        authority.publish_project_only(_ACTOR, verify_exact=lambda: True)
    record_project_opt_in(str(store.project_uuid), actor=_ACTOR)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
            "'admitted', '1', 'private-teamspace:team')",
            (str(store.project_uuid),),
        )


def _capture(store: ProjectSyncStore, event_ids: Sequence[str]) -> None:
    # Live payload writes require the project_only layout (WP10 cutover);
    # publish it idempotently so capture-only scenarios need no consent row.
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover(_ACTOR)
        authority.publish_project_only(_ACTOR, verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        for index, event_id in enumerate(event_ids):
            journal.append(_event(event_id, str(store.project_uuid), f"2026-08-01T00:00:{index:02d}Z"))


def _drain(
    store: ProjectSyncStore,
    receiver: StubReceiver | _TransientReceiver,
    *,
    recovery_event_ids: frozenset[str] = frozenset(),
) -> DispatchSummary:
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None, "the seeded admission row must resolve to an active target"
    return dispatch(
        store=store,
        receiver=receiver,
        target=target,
        context=store.create_context(),
        recovery_event_ids=recovery_event_ids,
    )


class _TransientReceiver:
    """A §4-conformant receiver whose first answer is a KNOWN_NO_EFFECT refusal.

    Deliberately NOT a bare 503: a 5xx after transmit has uncertain remote
    effect, so WP06 parks the durable attempt for operator review with no
    automatic resend — the safe behavior, but not a *retry*. A refusal whose
    lack of effect is proven (the shape ``_KnownNoEffectOnceStub`` pins in
    tests/delivery/test_dispatcher.py) is the protocol's retryable case: the
    ledger records ``retryable_no_effect`` and the next drain reselects the
    same attempt with its native identity.
    """

    def __init__(self) -> None:
        self.calls = 0

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__t052-transient-stub__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[ReceiverGate, ...]:
        return ()

    def deliver(self, batch: ConsentedBatch) -> Sequence[DeliveryResult]:
        self.calls += 1
        return [
            DeliveryResult(
                event_id=event.event_id,
                outcome=DeliveryOutcome.REJECTED,
                http_status=400,
                error="known no effect",
                effect_certainty=DeliveryEffectCertainty.KNOWN_NO_EFFECT,
            )
            for event in batch
        ]


def _seed_project_b() -> ProjectSyncStore:
    """A fully-populated bystander store: consent, admission, journal, ledger."""
    store = ProjectSyncStore(UUID_B)
    _admit(store)
    _capture(store, ["evt-b-000", "evt-b-001"])
    summary = _drain(store, StubReceiver())
    assert summary.selected == 2, "project B must hold real delivered rows worth protecting"
    return store


def _seed_legacy_source(path: Path, project_uuid: str) -> None:
    """One explicit legacy source holding only *project_uuid*'s rows."""
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE event_journal ("
            "event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, payload BLOB NOT NULL, "
            "occurred_at TEXT NOT NULL, created_at TEXT NOT NULL, project_uuid TEXT)"
        )
        connection.execute(
            "INSERT INTO event_journal VALUES (?, 'mission.changed', ?, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z', ?)",
            (
                f"legacy-{project_uuid[:8]}",
                json.dumps({"event_id": f"legacy-{project_uuid[:8]}", "project_uuid": project_uuid}),
                project_uuid,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _run_project_a_full_operation_set(uuid_a: str, *, legacy_source: Path, migration_id: str) -> None:
    """capture, select, send (stub), result, retry, migrate, diagnose, purge, opt-out.

    Every step asserts it actually did its work, so an operation that silently
    no-ops cannot launder an empty census into an isolation claim. Rows are
    keyed on ``store.project_uuid`` (not the caller's literal) so the mutant
    control can push the identical operation set through a mutated resolver.
    """
    store = ProjectSyncStore(uuid_a)
    _admit(store)
    owner = str(store.project_uuid)

    # capture
    _capture(store, ["evt-a-000", "evt-a-001", "evt-a-002"])

    # select + send (stub receiver) + result
    stub = StubReceiver()
    summary = _drain(store, stub)
    assert summary.selected == 3, f"the drain must select the captured batch: {summary}"
    assert set(stub.received_event_ids()) == {"evt-a-000", "evt-a-001", "evt-a-002"}

    # retry: a proven-no-effect refusal now, a real ledger-driven retry after
    _capture(store, ["evt-a-retry"])
    refused = _drain(store, _TransientReceiver())
    assert refused.selected == 1 and refused.rejected == 1, f"the refusal drain must record a retryable_no_effect attempt: {refused}"
    retried = _drain(store, stub)
    assert retried.selected == 1 and retried.delivered == 1, f"the follow-up drain must retry the no-effect row: {retried}"
    assert "evt-a-retry" in stub.received_event_ids()

    # migrate: preview of one explicit legacy source (project A rows only)
    manifest = LegacyProjectStoreMigration(get_runtime_root().base, (legacy_source,)).preview(migration_id)
    assert manifest.migration_id == migration_id

    # diagnose: read-only store verification + the per-project store report
    identity = store.verify_existing_readonly()
    assert identity.database_path == store.database_path
    with store.unit_of_work() as unit:
        report = build_per_project_store_report(EventJournal(unit, store.layout_generation()))
    assert report.reconciles and report.retained_event_count == 4

    # purge
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        purge = purge_project_events(owner, journal=journal, ledger=ledger, dry_run=False)
    assert purge.purged_count == 4, f"the purge must remove the four captured rows: {purge}"

    # opt-out
    record_project_opt_out(owner, actor=_ACTOR)
    assert read_project_consent_decision(owner).status is ConsentAuthorityStatus.REFUSED


# --------------------------------------------------------------------------- #
# NFR-001: the full operation set opens zero project-B resources               #
# --------------------------------------------------------------------------- #


def test_project_a_full_operation_set_opens_no_project_b_resources(tmp_path: Path) -> None:
    """Project A's complete operation matrix never touches project B's store.

    B is seeded *first* with real consent, admission, journal and delivered
    ledger rows, so B's resources exist on disk and would be one resolver bug
    away from being opened. Then every A operation runs under the census.
    """
    _seed_project_b()
    legacy_source = tmp_path / "legacy-a.db"
    _seed_legacy_source(legacy_source, UUID_A)

    with measure() as census:
        _run_project_a_full_operation_set(UUID_A, legacy_source=legacy_source, migration_id="t052-isolation")

    # The census must have observed reality before its absence claim means anything:
    # A's own database was opened through the instrumented connect, and statements ran.
    a_database = str(ProjectStorePaths.for_project(UUID_A).database)
    assert any(_normalize_sqlite_database(raw) == a_database for raw in census.sqlite_databases), (
        "instrumentation observed no connect to project A's own store — the census is not measuring"
    )
    assert census.statements, "instrumentation captured no SQL statements — the trace callback is not attached"

    _assert_no_project_b_resources_opened(census, UUID_B)


@pytest.mark.parametrize("spelling", PLATFORM_UUID_SPELLINGS)
def test_platform_uuid_spellings_resolve_to_one_store_and_stay_isolated(spelling: str) -> None:
    """Every platform spelling of A's UUID lands in ONE ASCII store, never B's.

    A case-variant or braced spelling that minted a second directory would be a
    silent split-brain on case-sensitive filesystems and a collision on
    case-insensitive ones; one that leaked into B's token would be the incident.
    """
    _seed_project_b()
    canonical = ProjectStorePaths.for_project(UUID_A)
    variant = ProjectStorePaths.for_project(spelling)
    assert variant.database == canonical.database, f"{spelling!r} resolved to a different store than the canonical spelling"
    assert variant.project_uuid.storage_token == UUID_A
    assert str(variant.database).isascii(), "store paths must be ASCII-safe on every platform"

    store = ProjectSyncStore(spelling)
    _admit(store)
    with measure() as census:
        _capture(store, [f"evt-variant-{abs(hash(spelling)) % 1000:03d}"])

    _assert_no_project_b_resources_opened(census, UUID_B)
    projects_dir = canonical.runtime_root / "projects"
    tokens = {entry.name for entry in projects_dir.iterdir() if entry.is_dir() and not entry.name.startswith(".")}
    assert tokens == {UUID_A, UUID_B}, f"a UUID spelling minted an extra store directory: {tokens}"


# --------------------------------------------------------------------------- #
# NFR-005: display names, symlinks, slug collisions, worktrees                 #
# --------------------------------------------------------------------------- #


def _write_identity(checkout: Path, project_uuid: UUID, slug: str) -> Path:
    """Persist a real ``.kittify/config.yaml`` identity and return its path."""
    config_path = checkout / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_config(
        config_path,
        ProjectIdentity(
            project_uuid=project_uuid,
            project_slug=slug,
            node_id="abcdef012345",
            build_id="11111111-2222-3333-4444-555555555555",
        ),
    )
    return config_path


def test_unicode_display_names_never_reach_the_store_path(tmp_path: Path, home: Path) -> None:
    """Accented and non-ASCII display names must not shape the store location.

    The store path is derived from the UUID alone, so a rename from
    ``café-app`` to ``кот`` can never orphan or split a store, and the path
    stays byte-identical across platform filename encodings (NFR-005).
    """
    display_names = ("Ünïcode-Projëct", "プロジェクト-kitty", "café-app")
    stores: list[ProjectSyncStore] = []
    for name in display_names:
        checkout = tmp_path / "checkouts" / name
        config_path = _write_identity(checkout, uuid5(NAMESPACE_URL, f"t052:{name}"), name)
        loaded = load_identity(config_path)
        assert loaded.project_uuid is not None
        store = ProjectSyncStore(str(loaded.project_uuid))
        _capture(store, [f"evt-unicode-{len(stores)}"])
        relative = store.database_path.relative_to(home)
        assert str(relative).isascii(), f"store path for {name!r} is not ASCII-safe: {relative}"
        assert name not in str(store.database_path)
        stores.append(store)

    # The first project's operations open none of its Unicode-named siblings' stores.
    with measure() as census:
        _capture(stores[0], ["evt-unicode-again"])
    for sibling in stores[1:]:
        _assert_no_project_b_resources_opened(census, str(sibling.project_uuid))


@pytest.mark.requires_symlinks
def test_symlinked_checkout_roots_resolve_to_one_store(tmp_path: Path, home: Path) -> None:
    """A symlinked checkout root is the same project, not a second store."""
    real = tmp_path / "real-checkout"
    project_uuid = uuid5(NAMESPACE_URL, "t052:symlinked")
    _write_identity(real, project_uuid, "kitty-app")
    link = tmp_path / "linked-checkout"
    link.symlink_to(real, target_is_directory=True)

    via_real = load_identity(real / ".kittify" / "config.yaml")
    via_link = load_identity(link / ".kittify" / "config.yaml")
    assert via_link.project_uuid == via_real.project_uuid == project_uuid

    store_real = ProjectSyncStore(str(via_real.project_uuid))
    store_link = ProjectSyncStore(str(via_link.project_uuid))
    assert store_link.database_path == store_real.database_path

    _capture(store_link, ["evt-via-symlink"])
    with store_real.unit_of_work() as unit:
        rows = EventJournal(unit, store_real.layout_generation()).read_all()
    assert [event.event_id for event in rows] == ["evt-via-symlink"], "the symlinked root must write into the same single store"

    projects_dir = home / "projects"
    tokens = {entry.name for entry in projects_dir.iterdir() if entry.is_dir() and not entry.name.startswith(".")}
    assert tokens == {str(project_uuid)}, f"a symlinked checkout minted an extra store: {tokens}"


def test_same_slug_different_uuids_stay_physically_apart(tmp_path: Path) -> None:
    """Two projects both named ``kitty-app`` are two stores; slug is not identity."""
    uuid_one = uuid5(NAMESPACE_URL, "t052:teamspace-one/kitty-app")
    uuid_two = uuid5(NAMESPACE_URL, "t052:teamspace-two/kitty-app")
    _write_identity(tmp_path / "teamspace-one" / "kitty-app", uuid_one, "kitty-app")
    _write_identity(tmp_path / "teamspace-two" / "kitty-app", uuid_two, "kitty-app")

    store_one = ProjectSyncStore(str(uuid_one))
    store_two = ProjectSyncStore(str(uuid_two))
    assert store_one.database_path != store_two.database_path, "a shared slug must never share a store"

    _capture(store_two, ["evt-two-000"])
    with measure() as census:
        _capture(store_one, ["evt-one-000"])

    _assert_no_project_b_resources_opened(census, str(uuid_two))
    with store_two.unit_of_work() as unit:
        rows = EventJournal(unit, store_two.layout_generation()).read_all()
    assert [event.event_id for event in rows] == ["evt-two-000"], "the slug-twin's store must be untouched"


def test_same_uuid_across_multiple_worktrees_shares_exactly_one_store(tmp_path: Path, home: Path) -> None:
    """Worktrees of one repository share one UUID and therefore ONE store."""
    project_uuid = uuid5(NAMESPACE_URL, "t052:worktrees")
    for worktree in ("main-checkout", ".worktrees/mission-lane-1"):
        _write_identity(tmp_path / worktree, project_uuid, "kitty-app")

    identities = [load_identity(tmp_path / worktree / ".kittify" / "config.yaml") for worktree in ("main-checkout", ".worktrees/mission-lane-1")]
    assert identities[0].project_uuid == identities[1].project_uuid == project_uuid

    store_main = ProjectSyncStore(str(identities[0].project_uuid))
    store_lane = ProjectSyncStore(str(identities[1].project_uuid))
    assert store_main.database_path == store_lane.database_path

    _capture(store_main, ["evt-from-main"])
    _capture(store_lane, ["evt-from-lane"])
    with store_main.unit_of_work() as unit:
        rows = EventJournal(unit, store_main.layout_generation()).read_all()
    assert {event.event_id for event in rows} == {"evt-from-main", "evt-from-lane"}, "both worktrees must capture into the one shared store"

    projects_dir = home / "projects"
    tokens = {entry.name for entry in projects_dir.iterdir() if entry.is_dir() and not entry.name.startswith(".")}
    assert tokens == {str(project_uuid)}, f"a worktree minted a second store for one UUID: {tokens}"


# --------------------------------------------------------------------------- #
# NFR-004 mutant control: the assertion must be observed to fail               #
# --------------------------------------------------------------------------- #


class TestSharedResolverMutantControl:
    """Negative control. A guard never observed to fail is decoration.

    Idiom follows ``tests/architectural/test_unfiltered_journal_read_boundary.py::
    TestGuardBites``: run the REAL collection path under the mutant and assert
    the failure fires with text naming the offense — not a boolean.
    """

    def test_shared_resolver_mutant_makes_the_isolation_assertion_fail(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Collapse the resolver to one shared path; the census must object.

        ``ProjectStorePaths.for_project`` is the seam every store, consent
        writer, and context read resolves through. The mutant makes it return
        one fixed location for *every* UUID — the pre-#3262 shared-store shape.
        The identical full operation set then runs, and the identical assertion
        that passes in the real test above must FAIL, proving the census
        measures actual opens rather than agreeing with itself.
        """
        _seed_project_b()
        legacy_source = tmp_path / "legacy-a.db"
        _seed_legacy_source(legacy_source, UUID_A)

        def _shared_resolver(
            _cls: type[ProjectStorePaths],
            _project_uuid: CanonicalProjectUUID | UUID | str,
        ) -> ProjectStorePaths:
            return ProjectStorePaths(
                project_uuid=CanonicalProjectUUID.parse(UUID_SHARED_MUTANT),
                runtime_root=get_runtime_root().base,
            )

        monkeypatch.setattr(ProjectStorePaths, "for_project", classmethod(_shared_resolver))

        with measure() as census:
            _run_project_a_full_operation_set(UUID_A, legacy_source=legacy_source, migration_id="t052-mutant")

        shared_root = _project_root(UUID_SHARED_MUTANT)
        assert _paths_touched_under(census, shared_root), "the mutant run must actually have used the shared path, or this control proves nothing"

        with pytest.raises(AssertionError) as failure:
            _assert_no_project_b_resources_opened(census, UUID_B)
        message = str(failure.value)
        assert "project-B resources" in message, f"the isolation failure must name the offense: {message}"
        assert str(shared_root) in message, f"the isolation failure must name the shared path it caught: {message}"
