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
from functools import cache
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

    def _is_constructor(self, value: ast.expr) -> bool:
        if isinstance(value, ast.Name):
            return value.id in self.sqlite_constructors
        return (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id in self.sqlite_modules
            and value.attr in {"connect", "Connection"}
        )

    def _bind_assignment(self, targets: list[ast.expr], value: ast.expr) -> None:
        names = {target.id for target in targets if isinstance(target, ast.Name)}
        module_alias = isinstance(value, ast.Name) and value.id in self.sqlite_modules
        constructor_alias = self._is_constructor(value)
        self.sqlite_modules.difference_update(names)
        self.sqlite_constructors.difference_update(names)
        if module_alias:
            self.sqlite_modules.update(names)
        if constructor_alias:
            self.sqlite_constructors.update(names)

    def _visit_nested_scope(self, node: ast.AST, name: str) -> None:
        saved_modules = self.sqlite_modules.copy()
        saved_constructors = self.sqlite_constructors.copy()
        self.scope.append(name)
        self.generic_visit(node)
        self.scope.pop()
        self.sqlite_modules = saved_modules
        self.sqlite_constructors = saved_constructors

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
        self._bind_assignment(node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if node.value is not None:
            self._bind_assignment([node.target], node.value)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._visit_nested_scope(node, node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_nested_scope(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_nested_scope(node, node.name)

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
    roots: tuple[Path, ...] | None = None,
    *,
    source_root: Path = _SRC,
) -> tuple[StoreSite, ...]:
    """Discover direct SQLite opens, component commits, and owned tx contexts."""
    if roots is None:
        roots = _SYNC_ROOTS if source_root == _SRC else (source_root,)
    found: list[StoreSite] = []
    for path in _paths_from_roots(roots):
        visitor = _StoreVisitor(path, source_root)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        found.extend(visitor.sites)
    return tuple(sorted(found))


def _module_name(path: Path, source_root: Path) -> str:
    parts = list(path.relative_to(source_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _dotted_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


def _symbol_index(
    paths: tuple[Path, ...],
    source_root: Path,
) -> tuple[dict[Path, ast.Module], dict[str, str]]:
    symbols: dict[str, str] = {}
    trees: dict[Path, ast.Module] = {}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        trees[path] = tree
        module = _module_name(path, source_root)
        relpath = path.relative_to(source_root).as_posix()
        for statement in tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols[f"{module}.{statement.name}"] = f"{relpath}::{statement.name}"
            elif isinstance(statement, ast.ClassDef):
                for child in statement.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols[f"{module}.{statement.name}.{child.name}"] = f"{relpath}::{statement.name}.{child.name}"
    return trees, symbols


def _module_aliases(
    tree: ast.Module,
    module: str,
) -> tuple[dict[str, str], dict[str, str]]:
    modules: dict[str, str] = {}
    symbols: dict[str, str] = {}
    package = module.split(".")[:-1]
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                bound = alias.asname or alias.name.split(".")[0]
                modules[bound] = alias.name if alias.asname else bound
        elif isinstance(statement, ast.ImportFrom):
            if statement.level:
                prefix = package[: len(package) - statement.level + 1]
                imported_module = ".".join((*prefix, *(statement.module or "").split(".")))
            else:
                imported_module = statement.module or ""
            for alias in statement.names:
                symbols[alias.asname or alias.name] = f"{imported_module}.{alias.name}"
    return modules, symbols


def _resolved_symbol(
    raw: str,
    module: str,
    module_aliases: dict[str, str],
    symbol_aliases: dict[str, str],
) -> str:
    parts = raw.split(".")
    if parts[0] in symbol_aliases:
        return ".".join((symbol_aliases[parts[0]], *parts[1:]))
    if parts[0] in module_aliases:
        return ".".join((module_aliases[parts[0]], *parts[1:]))
    return f"{module}.{raw}"


@cache
def _qualified_call_counts(source_root: Path = _SRC) -> Counter[str]:
    """Resolve only module/class-qualified source edges, never tail-name guesses."""
    trees, symbols = _symbol_index(tuple(sorted(source_root.rglob("*.py"))), source_root)

    counts: Counter[str] = Counter()
    for path, tree in trees.items():
        module = _module_name(path, source_root)
        module_aliases, symbol_aliases = _module_aliases(tree, module)
        local_classes = {statement.name for statement in tree.body if isinstance(statement, ast.ClassDef)}
        for item in ast.walk(tree):
            if not isinstance(item, ast.Call):
                continue
            raw = _dotted_name(item.func)
            if raw is None:
                continue
            parts = raw.split(".")
            resolved = _resolved_symbol(raw, module, module_aliases, symbol_aliases)
            target = symbols.get(resolved)
            if target:
                counts[target] += 1
            constructor = f"{resolved}.__init__"
            if parts[-1] in local_classes:
                constructor = f"{module}.{parts[-1]}.__init__"
            constructor_target = symbols.get(constructor)
            if constructor_target:
                counts[constructor_target] += 1
    return counts


def _owner_for(site: StoreSite) -> str:
    if site.relpath.startswith("specify_cli/delivery/dispatcher.py"):
        return "WP07"
    if site.relpath.startswith("specify_cli/delivery/targets.py"):
        return "WP05"
    if site.relpath.startswith("specify_cli/cli/") or site.relpath.endswith("migrate_journal.py"):
        return "WP10"
    return "WP04"


_LIVE_CLASS_CONTROLS: dict[tuple[str, str], str] = {
    ("specify_cli/event_journal/journal.py", "EventJournal"): ("EventJournal constructor/append public entry; exercised by WP01 live control"),
    ("specify_cli/event_journal/journal.py", "JournalTransaction"): ("EventJournal.transaction public entry"),
    ("specify_cli/delivery/ledger.py", "SqliteDeliveryLedger"): ("record_success/transaction public entries; exercised by WP01 live control"),
    ("specify_cli/delivery/targets.py", "SqliteDeliveryTargetRegistry"): ("delivery target registry constructor/register public entries"),
    ("specify_cli/sync/queue.py", "OfflineQueue"): ("offline event queue constructor/queue_event public entries"),
    ("specify_cli/sync/body_queue.py", "OfflineBodyUploadQueue"): ("offline body queue constructor/enqueue/result public entries"),
}


def _live_control(site: StoreSite) -> str | None:
    class_name = site.qualname.split(".", 1)[0]
    return _LIVE_CLASS_CONTROLS.get((site.relpath, class_name))


def classify_store_site(
    site: StoreSite,
    *,
    source_root: Path = _SRC,
) -> SiteDisposition:
    """Classify a discovered site with measured source reachability and owner."""
    symbol = f"{site.relpath}::{site.qualname}"
    references = _qualified_call_counts(source_root)[symbol]
    decorated_command = site.relpath.startswith("specify_cli/cli/") and site.qualname in {
        "status",
        "purge",
        "migrate",
    }
    reachability = "Typer command entry point" if decorated_command else f"{references} qualified source call(s) to {symbol}"
    if site.kind is SiteKind.SQLITE_CONNECT and site.read_only:
        return SiteDisposition(SiteCategory.LEGACY_READ_ONLY, "WP10", reachability)
    if site.relpath == "specify_cli/sync/migrate_journal.py" or (site.relpath == "specify_cli/sync/queue.py" and "_migrate_" in site.qualname):
        return SiteDisposition(SiteCategory.LEGACY_MIGRATION, "WP10", reachability)
    control = _live_control(site)
    if control is not None:
        return SiteDisposition(
            SiteCategory.LIVE_PAYLOAD_CONTROL,
            _owner_for(site),
            control,
        )
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
        "specify_cli/delivery/ledger.py::SqliteDeliveryLedger._record::commit",
        "specify_cli/delivery/ledger.py::SqliteDeliveryLedger.transaction::commit",
        "specify_cli/delivery/targets.py::SqliteDeliveryTargetRegistry.__init__::sqlite_connect",
        "specify_cli/delivery/targets.py::SqliteDeliveryTargetRegistry._insert::commit",
        "specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.__init__::sqlite_connect",
        "specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.enqueue::commit",
        "specify_cli/sync/body_queue.py::OfflineBodyUploadQueue.mark_uploaded::commit",
        "specify_cli/sync/queue.py::OfflineQueue._init_db::sqlite_connect",
        "specify_cli/sync/queue.py::OfflineQueue.append::commit",
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
    by_key = {site.key: classify_store_site(site).category for site in sites if site.key in _KNOWN_LIVE_FLOOR}
    assert by_key == dict.fromkeys(
        _KNOWN_LIVE_FLOOR,
        SiteCategory.LIVE_PAYLOAD_CONTROL,
    )
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
        "import sqlite3\n"
        "open_sync = sqlite3.connect\n"
        "open_again = open_sync\n"
        "def write(path):\n"
        "    one = open_sync(path)\n"
        "    two = open_again(path)\n"
        "    one.commit()\n"
        "    return two\n",
        encoding="utf-8",
    )
    sites = scan_store_sites(source_root=tmp_path)
    observed = Counter(site.key for site in sites)
    assert observed["specify_cli/sync/mutant.py::write::sqlite_connect"] == 2
    assert observed["specify_cli/sync/mutant.py::write::commit"] == 1


def test_constructor_alias_rebinding_is_order_and_scope_sensitive(tmp_path: Path) -> None:
    source = tmp_path / "specify_cli" / "sync" / "rebound.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import sqlite3\n"
        "def safe(path):\n"
        "    return path\n"
        "open_sync = sqlite3.connect\n"
        "def before_rebind(path):\n"
        "    return open_sync(path)\n"
        "open_sync = safe\n"
        "def inspect(path):\n"
        "    return open_sync(path)\n",
        encoding="utf-8",
    )
    sites = scan_store_sites(source_root=tmp_path)
    assert [site.qualname for site in sites] == ["before_rebind"]


def test_reachability_is_qualified_not_a_common_tail_name(tmp_path: Path) -> None:
    source = tmp_path / "specify_cli" / "sync" / "mutant.py"
    caller = tmp_path / "specify_cli" / "sync" / "caller.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import sqlite3\ndef append(path):\n    return sqlite3.connect(path)\ndef live(path):\n    return sqlite3.connect(path)\n",
        encoding="utf-8",
    )
    caller.write_text(
        "from .mutant import live\ndef entry(path):\n    return live(path)\n",
        encoding="utf-8",
    )
    sites = scan_store_sites(source_root=tmp_path)
    dispositions = {site.qualname: classify_store_site(site, source_root=tmp_path) for site in sites}
    assert dispositions["append"].category is SiteCategory.DEAD_CODE
    assert dispositions["append"].reachability.startswith("0 qualified")
    assert dispositions["live"].category is SiteCategory.LIVE_PAYLOAD_CONTROL
    assert dispositions["live"].reachability.startswith("1 qualified")


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
