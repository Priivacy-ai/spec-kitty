"""WP01 architecture census for the per-project sync-store boundary.

This is a shrink-only census of the pre-migration tree.  It deliberately records
the legacy/live debt without blessing it: growth fails, shrinkage warns, and the
strict final-state predicate is reusable by WP11 when the migration is complete.
"""

from __future__ import annotations

import ast
import warnings
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
_SYNC_ROOTS = (
    _SRC / "specify_cli" / "event_journal",
    _SRC / "specify_cli" / "delivery",
    _SRC / "specify_cli" / "sync",
    _SRC / "specify_cli" / "cli" / "commands" / "sync.py",
)


class SiteKind(StrEnum):
    SQLITE_CONNECT = "sqlite_connect"
    COMMIT = "commit"
    TRANSACTION_CONTEXT = "transaction_context"


class SiteCategory(StrEnum):
    LIVE_PAYLOAD_CONTROL = "live-payload-or-control"
    LEGACY_READ_ONLY = "strictly-read-only-legacy-snapshot"
    LEGACY_MIGRATION = "legacy-migration"
    TEST_OR_UNRELATED = "test-or-unrelated"
    DEAD_CODE = "dead-code"


@dataclass(frozen=True, order=True)
class StoreSite:
    relpath: str
    qualname: str
    kind: SiteKind
    lineno: int

    @property
    def key(self) -> str:
        return f"{self.relpath}::{self.qualname}::{self.kind.value}"


class _StoreVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.scope: list[str] = []
        self.sites: list[StoreSite] = []

    def _qualname(self) -> str:
        return ".".join(self.scope) or "<module>"

    def _record(self, node: ast.AST, kind: SiteKind) -> None:
        self.sites.append(
            StoreSite(
                self.path.relative_to(_SRC).as_posix(),
                self._qualname(),
                kind,
                node.lineno,
            )
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "sqlite3" and func.attr == "connect":
            self._record(node, SiteKind.SQLITE_CONNECT)
        elif isinstance(func, ast.Name) and func.id == "connect":
            # The hosted-store modules currently import ``sqlite3`` rather than
            # ``connect`` directly.  Keeping this branch makes the census fail on
            # that import-style evasion instead of silently losing coverage.
            self._record(node, SiteKind.SQLITE_CONNECT)
        if isinstance(func, ast.Attribute) and func.attr == "commit":
            self._record(node, SiteKind.COMMIT)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:  # noqa: N802
        for item in node.items:
            expr = item.context_expr
            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute) and expr.func.attr == "transaction":
                self._record(expr, SiteKind.TRANSACTION_CONTEXT)
        self.generic_visit(node)


def scan_store_sites(roots: tuple[Path, ...] = _SYNC_ROOTS) -> tuple[StoreSite, ...]:
    """Return every direct sqlite open, component commit, and tx context."""
    paths: list[Path] = []
    for root in roots:
        paths.extend(root.rglob("*.py") if root.is_dir() else [root])
    found: list[StoreSite] = []
    for path in sorted(set(paths)):
        visitor = _StoreVisitor(path)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        found.extend(visitor.sites)
    return tuple(sorted(found))


_READ_ONLY_LEGACY_SYMBOLS = frozenset(
    {
        "specify_cli/cli/commands/sync.py::_count_legacy_body_uploads_for_mission",
        "specify_cli/cli/commands/sync.py::_emit_status_check_json",
        "specify_cli/cli/commands/sync.py::_purge_journal_census",
        "specify_cli/cli/commands/sync.py::_purge_journal_ids",
        "specify_cli/cli/commands/sync.py::_purge_ledger_census",
        "specify_cli/cli/commands/sync.py::_purge_ledger_ghost_count",
        "specify_cli/cli/commands/sync.py::status",
        "specify_cli/sync/migrate_journal.py::_read_queued_rows",
        "specify_cli/sync/queue.py::_queue_db_has_content",
        "specify_cli/sync/queue.py::detect_legacy_rows_for_scope",
    }
)


def classify_store_site(site: StoreSite) -> SiteCategory:
    """Classify every current site using the WP01 four-way census vocabulary."""
    symbol = f"{site.relpath}::{site.qualname}"
    if symbol in _READ_ONLY_LEGACY_SYMBOLS and site.kind is SiteKind.SQLITE_CONNECT:
        return SiteCategory.LEGACY_READ_ONLY
    if site.relpath == "specify_cli/sync/migrate_journal.py":
        return SiteCategory.LEGACY_MIGRATION
    if site.relpath == "specify_cli/sync/queue.py" and any(
        marker in site.qualname
        for marker in (
            "_migrate_body_queue_column_rename",
            "_migrate_legacy_queue_to_scope",
        )
    ):
        return SiteCategory.LEGACY_MIGRATION
    if site.relpath.startswith("specify_cli/"):
        return SiteCategory.LIVE_PAYLOAD_CONTROL
    return SiteCategory.TEST_OR_UNRELATED


# Qualified symbols, never line numbers.  This is the measured 2026-08-09
# baseline.  Later WPs may remove entries without editing this file; additions
# are architecture regressions and fail immediately.
_KNOWN_SITE_KEYS = frozenset(
    line.strip()
    for line in """
specify_cli/cli/commands/sync.py::_count_legacy_body_uploads_for_mission::sqlite_connect
specify_cli/cli/commands/sync.py::_emit_status_check_json::sqlite_connect
specify_cli/cli/commands/sync.py::_purge_journal_census::sqlite_connect
specify_cli/cli/commands/sync.py::_purge_journal_ids::sqlite_connect
specify_cli/cli/commands/sync.py::_purge_ledger_census::sqlite_connect
specify_cli/cli/commands/sync.py::_purge_ledger_ghost_count::sqlite_connect
specify_cli/cli/commands/sync.py::status::sqlite_connect
specify_cli/delivery/dispatcher.py::_record::transaction_context
specify_cli/delivery/ledger.py::SqliteDeliveryLedger.__init__::sqlite_connect
specify_cli/delivery/ledger.py::SqliteDeliveryLedger._record::commit
specify_cli/delivery/ledger.py::SqliteDeliveryLedger.transaction::commit
specify_cli/delivery/ledger.py::init_ledger::commit
specify_cli/delivery/retention.py::_all_event_ids::sqlite_connect
specify_cli/delivery/retention.py::_purge_all_body_rows::commit
specify_cli/delivery/retention.py::_purge_all_body_rows::sqlite_connect
specify_cli/delivery/retention.py::_purge_journal_rows::commit
specify_cli/delivery/retention.py::_purge_journal_rows::sqlite_connect
specify_cli/delivery/retention.py::_purge_ledger_rows::transaction_context
specify_cli/delivery/targets.py::SqliteDeliveryTargetRegistry.__init__::commit
specify_cli/delivery/targets.py::SqliteDeliveryTargetRegistry.__init__::sqlite_connect
specify_cli/delivery/targets.py::SqliteDeliveryTargetRegistry._insert::commit
specify_cli/delivery/targets.py::SqliteDeliveryTargetRegistry._update_provenance::commit
specify_cli/event_journal/coalesce.py::_collapse_into::commit
specify_cli/event_journal/coalesce.py::_connect::commit
specify_cli/event_journal/coalesce.py::_connect::sqlite_connect
specify_cli/event_journal/coalesce.py::_record_supersede::commit
specify_cli/event_journal/journal.py::EventJournal._connect::sqlite_connect
specify_cli/event_journal/journal.py::EventJournal._ensure_schema::commit
specify_cli/event_journal/journal.py::EventJournal._migrate_add_identity_columns::commit
specify_cli/event_journal/journal.py::EventJournal.append::commit
specify_cli/event_journal/journal.py::EventJournal.mark_archived::commit
specify_cli/event_journal/journal.py::EventJournal.set_project_identity::commit
specify_cli/event_journal/journal.py::JournalTransaction.commit::commit
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.__init__::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.count_by_project::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.drain::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.enqueue::commit
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.enqueue::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.failure_count::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.get_recent_failures::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.get_stats::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_already_exists::commit
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_already_exists::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_failed_permanent::commit
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_failed_permanent::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_failed_retryable::commit
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_failed_retryable::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_uploaded::commit
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_uploaded::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.record_permanent_failure::commit
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.record_permanent_failure::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.remove_project_tasks::commit
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.remove_project_tasks::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.remove_stale::commit
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.remove_stale::sqlite_connect
specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.size::sqlite_connect
specify_cli/sync/migrate_journal.py::MigrationAudit.__init__::commit
specify_cli/sync/migrate_journal.py::MigrationAudit.__init__::sqlite_connect
specify_cli/sync/migrate_journal.py::MigrationAudit.commit::commit
specify_cli/sync/migrate_journal.py::_import_source::commit
specify_cli/sync/migrate_journal.py::_import_source::transaction_context
specify_cli/sync/migrate_journal.py::_read_queued_rows::sqlite_connect
specify_cli/sync/migrate_journal.py::resolve_conflicts_keep_journal::commit
specify_cli/sync/queue.py::OfflineQueue._init_db::commit
specify_cli/sync/queue.py::OfflineQueue._init_db::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue._load_row_count::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue._migrate_add_coalesce_key::commit
specify_cli/sync/queue.py::OfflineQueue._size_from_disk::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue._try_coalesce::commit
specify_cli/sync/queue.py::OfflineQueue._try_coalesce::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.append::commit
specify_cli/sync/queue.py::OfflineQueue.append::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.clear::commit
specify_cli/sync/queue.py::OfflineQueue.clear::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.drain_queue::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.drain_to_file::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.get_drain_blocked_counts::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.get_events_by_retry_count::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.get_queue_stats::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.increment_retry::commit
specify_cli/sync/queue.py::OfflineQueue.increment_retry::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.mark_synced::commit
specify_cli/sync/queue.py::OfflineQueue.mark_synced::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.process_batch_results::commit
specify_cli/sync/queue.py::OfflineQueue.process_batch_results::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.queue_event::commit
specify_cli/sync/queue.py::OfflineQueue.queue_event::sqlite_connect
specify_cli/sync/queue.py::OfflineQueue.remove_events::commit
specify_cli/sync/queue.py::OfflineQueue.remove_events::sqlite_connect
specify_cli/sync/queue.py::_migrate_body_queue_column_rename::commit
specify_cli/sync/queue.py::_migrate_legacy_queue_to_scope::commit
specify_cli/sync/queue.py::_migrate_legacy_queue_to_scope::sqlite_connect
specify_cli/sync/queue.py::_queue_db_has_content::sqlite_connect
specify_cli/sync/queue.py::detect_legacy_rows_for_scope::sqlite_connect
""".splitlines()
    if line.strip()
)

_KNOWN_LIVE_FLOOR = frozenset(
    {
        "specify_cli/event_journal/journal.py::EventJournal._connect::sqlite_connect",
        "specify_cli/event_journal/journal.py::EventJournal.append::commit",
        "specify_cli/delivery/ledger.py::SqliteDeliveryLedger.__init__::sqlite_connect",
        "specify_cli/delivery/targets.py::SqliteDeliveryTargetRegistry.__init__::sqlite_connect",
        "specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.__init__::sqlite_connect",
        "specify_cli/sync/queue.py::OfflineQueue.queue_event::sqlite_connect",
        "specify_cli/delivery/dispatcher.py::_record::transaction_context",
    }
)


def final_project_store_violations(sites: tuple[StoreSite, ...]) -> tuple[StoreSite, ...]:
    """Return sites forbidden once WP11 activates the one-store boundary.

    Live ``sync.db`` access belongs only to ``ProjectSyncStore``.  The migration
    module may open an immutable/read-only legacy snapshot, but may never commit.
    """
    violations: list[StoreSite] = []
    for site in sites:
        if site.relpath == "specify_cli/sync/project_store.py" and site.qualname.startswith("ProjectSyncStore"):
            continue
        if site.relpath == "specify_cli/sync/project_store_migration.py" and site.kind is SiteKind.SQLITE_CONNECT:
            source = (_SRC / site.relpath).read_text(encoding="utf-8")
            if "mode=ro" in source or "immutable=1" in source:
                continue
        violations.append(site)
    return tuple(violations)


def test_current_store_census_cannot_grow_and_every_site_is_classified() -> None:
    sites = scan_store_sites()
    keys = {site.key for site in sites}
    growth = keys - _KNOWN_SITE_KEYS
    assert not growth, "new direct store ownership sites:\n" + "\n".join(sorted(growth))
    assert keys >= _KNOWN_LIVE_FLOOR
    assert all(classify_store_site(site) is not SiteCategory.DEAD_CODE for site in sites)
    shrink = _KNOWN_SITE_KEYS - keys
    if shrink:
        warnings.warn(
            "project-store census shrank; keep the ratchet baseline unchanged: " + ", ".join(sorted(shrink)),
            stacklevel=1,
        )


def test_final_boundary_accepts_only_store_uow_and_read_only_migration() -> None:
    store = StoreSite(
        "specify_cli/sync/project_store.py",
        "ProjectSyncStore.transaction",
        SiteKind.COMMIT,
        20,
    )
    assert final_project_store_violations((store,)) == ()

    bypass = StoreSite(
        "specify_cli/sync/body_queue.py",
        "OfflineBodyUploadQueue.enqueue",
        SiteKind.COMMIT,
        99,
    )
    assert final_project_store_violations((bypass,)) == (bypass,)


def test_project_store_adr_records_the_incident_and_boundary() -> None:
    adr = _ROOT / "docs" / "adr" / "3.x" / "2026-08-09-1-project-sync-store-boundary.md"
    assert adr.exists(), "WP01 red: the project-store boundary ADR has not been authored"
    text = adr.read_text(encoding="utf-8")
    for required in (
        "one UUID",
        "ProjectSyncStore",
        "#3030",
        "final transmit recheck",
        "no dual-read",
        "1,322",
    ):
        assert required in text
