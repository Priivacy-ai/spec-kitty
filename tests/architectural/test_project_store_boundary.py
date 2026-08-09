"""Source-derived WP01 census for the per-project sync-store boundary.

The baseline is a shrink-only debt register, not an allowlist.  Collection is
alias-aware, counts repeated sites inside one qualified symbol, validates each
connection's own read-only arguments, and records reachability plus the later WP
that owns the occurrence.  WP11 can reuse :func:`final_project_store_violations`
to activate the strict end-state gate.
"""

from __future__ import annotations

import ast
import warnings
from collections import Counter
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
    callee: str
    read_only: bool = False

    @property
    def key(self) -> str:
        """Line-independent ratchet identity; multiplicity is counted separately."""
        return f"{self.relpath}::{self.qualname}::{self.kind.value}"


@dataclass(frozen=True)
class SiteDisposition:
    category: SiteCategory
    owner_wp: str
    reachability: str


def _callee_text(func: ast.expr) -> str:
    return ast.unparse(func)


def _literal_true(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _connection_is_read_only(node: ast.Call) -> bool:
    """Validate read-only mode on this connect call, never elsewhere in its file."""
    if not node.args:
        return False
    target = ast.unparse(node.args[0]).lower()
    uri_true = any(keyword.arg == "uri" and _literal_true(keyword.value) for keyword in node.keywords)
    return uri_true and ("mode=ro" in target or "immutable=1" in target)


class _StoreVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, source_root: Path) -> None:
        self.path = path
        self.source_root = source_root
        self.scope: list[str] = []
        self.sites: list[StoreSite] = []
        self.sqlite_modules: set[str] = {"sqlite3"}
        self.sqlite_constructors: set[str] = set()

    def _qualname(self) -> str:
        return ".".join(self.scope) or "<module>"

    def _record(
        self,
        node: ast.AST,
        kind: SiteKind,
        *,
        callee: str,
        read_only: bool = False,
    ) -> None:
        self.sites.append(
            StoreSite(
                self.path.relative_to(self.source_root).as_posix(),
                self._qualname(),
                kind,
                getattr(node, "lineno", 0),
                callee,
                read_only,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            if alias.name == "sqlite3":
                self.sqlite_modules.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if node.module == "sqlite3":
            for alias in node.names:
                if alias.name in {"connect", "Connection"}:
                    self.sqlite_constructors.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        if isinstance(node.value, ast.Name) and node.value.id in self.sqlite_modules:
            self.sqlite_modules.update(target.id for target in node.targets if isinstance(target, ast.Name))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        is_module_constructor = (
            isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in self.sqlite_modules and func.attr in {"connect", "Connection"}
        )
        is_direct_constructor = isinstance(func, ast.Name) and func.id in self.sqlite_constructors
        if is_module_constructor or is_direct_constructor:
            self._record(
                node,
                SiteKind.SQLITE_CONNECT,
                callee=_callee_text(func),
                read_only=_connection_is_read_only(node),
            )
        if isinstance(func, ast.Attribute) and func.attr == "commit":
            self._record(node, SiteKind.COMMIT, callee=_callee_text(func))
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:  # noqa: N802
        for item in node.items:
            expr = item.context_expr
            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute) and expr.func.attr == "transaction":
                self._record(
                    expr,
                    SiteKind.TRANSACTION_CONTEXT,
                    callee=_callee_text(expr.func),
                )
        self.generic_visit(node)


def _paths_from_roots(roots: tuple[Path, ...]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for root in roots:
        paths.extend(root.rglob("*.py") if root.is_dir() else [root])
    return tuple(sorted(set(paths)))


def scan_store_sites(
    roots: tuple[Path, ...] = _SYNC_ROOTS,
    *,
    source_root: Path = _SRC,
) -> tuple[StoreSite, ...]:
    """Discover direct SQLite opens, component commits, and owned tx contexts."""
    found: list[StoreSite] = []
    for path in _paths_from_roots(roots):
        visitor = _StoreVisitor(path, source_root)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        found.extend(visitor.sites)
    return tuple(sorted(found))


def _source_call_counts(source_root: Path = _SRC) -> Counter[str]:
    """Approximate source reachability by callable/class tail, excluding tests."""
    counts: Counter[str] = Counter()
    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                counts[node.func.id] += 1
            elif isinstance(node.func, ast.Attribute):
                counts[node.func.attr] += 1
    return counts


_SOURCE_CALL_COUNTS = _source_call_counts()


def _reference_name(site: StoreSite) -> str:
    parts = site.qualname.split(".")
    return parts[-2] if parts[-1] == "__init__" and len(parts) > 1 else parts[-1]


def _owner_for(site: StoreSite) -> str:
    if site.relpath.startswith("specify_cli/delivery/dispatcher.py"):
        return "WP07"
    if site.relpath.startswith("specify_cli/delivery/targets.py"):
        return "WP05"
    if site.relpath.startswith("specify_cli/cli/") or site.relpath.endswith("migrate_journal.py"):
        return "WP10"
    return "WP04"


def classify_store_site(site: StoreSite) -> SiteDisposition:
    """Classify a discovered site with measured source reachability and owner."""
    reference = _reference_name(site)
    references = _SOURCE_CALL_COUNTS[reference]
    decorated_command = site.relpath.startswith("specify_cli/cli/") and site.qualname in {
        "status",
        "purge",
        "migrate",
    }
    reachability = "Typer command entry point" if decorated_command else f"{references} source call(s) to {reference}"
    if site.kind is SiteKind.SQLITE_CONNECT and site.read_only:
        return SiteDisposition(SiteCategory.LEGACY_READ_ONLY, "WP10", reachability)
    if site.relpath == "specify_cli/sync/migrate_journal.py" or (site.relpath == "specify_cli/sync/queue.py" and "_migrate_" in site.qualname):
        return SiteDisposition(SiteCategory.LEGACY_MIGRATION, "WP10", reachability)
    if references == 0 and not decorated_command:
        return SiteDisposition(SiteCategory.DEAD_CODE, "WP10", reachability)
    if site.relpath.startswith("specify_cli/"):
        return SiteDisposition(
            SiteCategory.LIVE_PAYLOAD_CONTROL,
            _owner_for(site),
            reachability,
        )
    return SiteDisposition(SiteCategory.TEST_OR_UNRELATED, "excluded", reachability)


# Measured planning-base baseline by qualified symbol.  Counter comparison makes
# a second call inside an already-known symbol growth rather than collapsing it.
_KNOWN_SITE_COUNTS: Counter[str] = Counter(
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
specify_cli/sync/migrate_journal.py::_import_source::commit
specify_cli/sync/migrate_journal.py::_import_source::transaction_context
specify_cli/sync/migrate_journal.py::_read_queued_rows::sqlite_connect
specify_cli/sync/migrate_journal.py::resolve_conflicts_keep_journal::commit
specify_cli/sync/migrate_journal.py::resolve_conflicts_keep_journal::commit
specify_cli/sync/queue.py::OfflineQueue._init_db::commit
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
specify_cli/sync/queue.py::_migrate_legacy_queue_to_scope::commit
specify_cli/sync/queue.py::_migrate_legacy_queue_to_scope::sqlite_connect
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


def final_project_store_violations(
    sites: tuple[StoreSite, ...],
) -> tuple[StoreSite, ...]:
    """Allow only the exact live unit-of-work and per-site read-only migration."""
    violations: list[StoreSite] = []
    for site in sites:
        exact_uow = site.relpath == "specify_cli/sync/project_store.py" and site.qualname == "ProjectSyncStore.unit_of_work"
        exact_read_only_migration = site.relpath == "specify_cli/sync/project_store_migration.py" and site.kind is SiteKind.SQLITE_CONNECT and site.read_only
        if not (exact_uow or exact_read_only_migration):
            violations.append(site)
    return tuple(violations)


def test_current_store_census_cannot_grow_and_every_site_has_evidence() -> None:
    sites = scan_store_sites()
    observed = Counter(site.key for site in sites)
    growth = observed - _KNOWN_SITE_COUNTS
    assert not growth, "new direct store ownership sites:\n" + "\n".join(f"{key} (+{count})" for key, count in sorted(growth.items()))
    assert set(observed) >= _KNOWN_LIVE_FLOOR
    dispositions = [classify_store_site(site) for site in sites]
    assert all(item.owner_wp and item.reachability for item in dispositions)
    assert SiteCategory.DEAD_CODE in {item.category for item in dispositions}
    shrink = _KNOWN_SITE_COUNTS - observed
    if shrink:
        warnings.warn(
            "project-store census shrank; keep the ratchet baseline unchanged: " + ", ".join(f"{key} (-{count})" for key, count in sorted(shrink.items())),
            stacklevel=1,
        )


def test_alias_and_duplicate_mutations_flow_through_real_collector(tmp_path: Path) -> None:
    source = tmp_path / "specify_cli" / "sync" / "mutant.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import sqlite3 as _db\ndef write(path):\n    one = _db.connect(path)\n    two = _db.connect(path)\n    one.commit()\n    return two\n",
        encoding="utf-8",
    )
    sites = scan_store_sites((source,), source_root=tmp_path)
    observed = Counter(site.key for site in sites)
    assert observed["specify_cli/sync/mutant.py::write::sqlite_connect"] == 2
    assert observed["specify_cli/sync/mutant.py::write::commit"] == 1


def test_final_boundary_is_exact_and_read_only_is_validated_per_site(
    tmp_path: Path,
) -> None:
    store = tmp_path / "specify_cli" / "sync" / "project_store.py"
    migration = tmp_path / "specify_cli" / "sync" / "project_store_migration.py"
    store.parent.mkdir(parents=True)
    store.write_text(
        "import sqlite3\n"
        "class ProjectSyncStore:\n"
        "    def unit_of_work(self, path):\n"
        "        return sqlite3.connect(path)\n"
        "    def unit_of_work_helper(self, path):\n"
        "        return sqlite3.connect(path)\n",
        encoding="utf-8",
    )
    migration.write_text(
        "import sqlite3\n"
        "def snapshot(path):\n"
        "    ro = sqlite3.connect(f'file:{path}?mode=ro', uri=True)\n"
        "    writable = sqlite3.connect(path)\n"
        "    return ro, writable\n",
        encoding="utf-8",
    )
    sites = scan_store_sites((store, migration), source_root=tmp_path)
    violations = final_project_store_violations(sites)
    assert {(site.qualname, site.read_only) for site in violations} == {
        ("ProjectSyncStore.unit_of_work_helper", False),
        ("snapshot", False),
    }


def test_project_store_adr_records_the_incident_and_boundary() -> None:
    adr = _ROOT / "docs" / "adr" / "3.x" / "2026-08-09-1-project-sync-store-boundary.md"
    text = adr.read_text(encoding="utf-8")
    for required in (
        "projects/<lowercase-hyphenated-uuid>/sync/sync.db",
        "sibling `egress.lock`",
        "ProjectSyncStore.unit_of_work()",
        "supersedes #3030's final consent-gated capture decision",
        "final transmit recheck",
        "no dual-read",
        "Human-in-Charge",
        "1,322",
    ):
        assert required in text
