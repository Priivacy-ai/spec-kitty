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


def _target_names(targets: list[ast.expr]) -> set[str]:
    return {target.id for target in targets if isinstance(target, ast.Name)}


def _function_local_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    names = {
        argument.arg
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
    }
    if node.args.vararg is not None:
        names.add(node.args.vararg.arg)
    if node.args.kwarg is not None:
        names.add(node.args.kwarg.arg)

    class LocalBindings(ast.NodeVisitor):
        def visit_FunctionDef(self, child: ast.FunctionDef) -> None:  # noqa: N802
            names.add(child.name)

        def visit_AsyncFunctionDef(  # noqa: N802
            self, child: ast.AsyncFunctionDef
        ) -> None:
            names.add(child.name)

        def visit_ClassDef(self, child: ast.ClassDef) -> None:  # noqa: N802
            names.add(child.name)

        def visit_Import(self, child: ast.Import) -> None:  # noqa: N802
            names.update(alias.asname or alias.name.split(".")[0] for alias in child.names)

        def visit_ImportFrom(self, child: ast.ImportFrom) -> None:  # noqa: N802
            names.update(alias.asname or alias.name for alias in child.names)

        def visit_Assign(self, child: ast.Assign) -> None:  # noqa: N802
            names.update(_target_names(child.targets))
            self.generic_visit(child.value)

        def visit_AnnAssign(self, child: ast.AnnAssign) -> None:  # noqa: N802
            names.update(_target_names([child.target]))
            if child.value is not None:
                self.generic_visit(child.value)

    visitor = LocalBindings()
    for statement in node.body:
        visitor.visit(statement)
    return names


def _update_store_binding(
    modules: set[str],
    constructors: set[str],
    targets: list[ast.expr],
    value: ast.expr,
) -> None:
    names = _target_names(targets)
    module_alias = isinstance(value, ast.Name) and value.id in modules
    constructor_alias = (
        isinstance(value, ast.Name)
        and value.id in constructors
        or isinstance(value, ast.Attribute)
        and isinstance(value.value, ast.Name)
        and value.value.id in modules
        and value.attr in {"connect", "Connection"}
    )
    modules.difference_update(names)
    constructors.difference_update(names)
    if module_alias:
        modules.update(names)
    if constructor_alias:
        constructors.update(names)


def _final_module_store_bindings(tree: ast.Module) -> tuple[set[str], set[str]]:
    modules: set[str] = set()
    constructors: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            bound = {alias.asname or alias.name.split(".")[0] for alias in statement.names}
            modules.difference_update(bound)
            constructors.difference_update(bound)
            modules.update(alias.asname or alias.name for alias in statement.names if alias.name == "sqlite3")
        elif isinstance(statement, ast.ImportFrom):
            bound = {alias.asname or alias.name for alias in statement.names}
            modules.difference_update(bound)
            constructors.difference_update(bound)
            if statement.module == "sqlite3":
                constructors.update(alias.asname or alias.name for alias in statement.names if alias.name in {"connect", "Connection"})
        elif isinstance(statement, ast.Assign):
            _update_store_binding(
                modules,
                constructors,
                statement.targets,
                statement.value,
            )
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            _update_store_binding(
                modules,
                constructors,
                [statement.target],
                statement.value,
            )
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            modules.discard(statement.name)
            constructors.discard(statement.name)
    return modules, constructors


class _StoreVisitor(ast.NodeVisitor):
    def __init__(
        self,
        path: Path,
        source_root: Path,
        module_bindings: tuple[set[str], set[str]],
    ) -> None:
        self.path = path
        self.source_root = source_root
        self.scope: list[str] = []
        self.sites: list[StoreSite] = []
        self.module_sqlite_modules, self.module_sqlite_constructors = (binding.copy() for binding in module_bindings)
        self.sqlite_modules: set[str] = set()
        self.sqlite_constructors: set[str] = set()
        self.function_depth = 0

    def _bind_assignment(self, targets: list[ast.expr], value: ast.expr) -> None:
        _update_store_binding(
            self.sqlite_modules,
            self.sqlite_constructors,
            targets,
            value,
        )

    def _visit_function_scope(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        saved_modules = self.sqlite_modules.copy()
        saved_constructors = self.sqlite_constructors.copy()
        if self.function_depth == 0:
            self.sqlite_modules = self.module_sqlite_modules.copy()
            self.sqlite_constructors = self.module_sqlite_constructors.copy()
        locals_ = _function_local_names(node)
        self.sqlite_modules.difference_update(locals_)
        self.sqlite_constructors.difference_update(locals_)
        self.scope.append(node.name)
        self.function_depth += 1
        for statement in node.body:
            self.visit(statement)
        self.function_depth -= 1
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
        bound = {alias.asname or alias.name.split(".")[0] for alias in node.names}
        self.sqlite_modules.difference_update(bound)
        self.sqlite_constructors.difference_update(bound)
        for alias in node.names:
            if alias.name == "sqlite3":
                self.sqlite_modules.add(alias.asname or alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        bound = {alias.asname or alias.name for alias in node.names}
        self.sqlite_modules.difference_update(bound)
        self.sqlite_constructors.difference_update(bound)
        if node.module == "sqlite3":
            for alias in node.names:
                if alias.name in {"connect", "Connection"}:
                    self.sqlite_constructors.add(alias.asname or alias.name)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        self._bind_assignment(node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if node.value is not None:
            self._bind_assignment([node.target], node.value)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        for statement in node.body:
            self.visit(statement)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function_scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function_scope(node)

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
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _StoreVisitor(
            path,
            source_root,
            _final_module_store_bindings(tree),
        )
        visitor.visit(tree)
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
                modules.pop(bound, None)
                symbols.pop(bound, None)
                modules[bound] = alias.name if alias.asname else bound
        elif isinstance(statement, ast.ImportFrom):
            if statement.level:
                prefix = package[: len(package) - statement.level + 1]
                imported_module = ".".join((*prefix, *(statement.module or "").split(".")))
            else:
                imported_module = statement.module or ""
            for alias in statement.names:
                bound = alias.asname or alias.name
                modules.pop(bound, None)
                symbols[bound] = f"{imported_module}.{alias.name}"
        elif isinstance(statement, ast.Assign):
            for name in _target_names(statement.targets):
                modules.pop(name, None)
                symbols.pop(name, None)
        elif isinstance(statement, ast.AnnAssign):
            for name in _target_names([statement.target]):
                modules.pop(name, None)
                symbols.pop(name, None)
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            modules.pop(statement.name, None)
            symbols.pop(statement.name, None)
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


class _QualifiedCallVisitor(ast.NodeVisitor):
    def __init__(
        self,
        tree: ast.Module,
        module: str,
        symbols: dict[str, str],
        counts: Counter[str],
    ) -> None:
        self.module = module
        self.symbol_index = symbols
        self.counts = counts
        self.module_bindings, self.symbol_bindings = _module_aliases(tree, module)
        self.modules = self.module_bindings.copy()
        self.symbols = self.symbol_bindings.copy()
        self.local_classes = {statement.name for statement in tree.body if isinstance(statement, ast.ClassDef)}
        self.function_depth = 0

    def _imported_module(self, node: ast.ImportFrom) -> str:
        if not node.level:
            return node.module or ""
        package = self.module.split(".")[:-1]
        prefix = package[: len(package) - node.level + 1]
        return ".".join((*prefix, *((node.module or "").split("."))))

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            bound = alias.asname or alias.name.split(".")[0]
            self.modules.pop(bound, None)
            self.symbols.pop(bound, None)
            self.modules[bound] = alias.name if alias.asname else bound

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        imported_module = self._imported_module(node)
        for alias in node.names:
            bound = alias.asname or alias.name
            self.modules.pop(bound, None)
            self.symbols[bound] = f"{imported_module}.{alias.name}"

    def _discard_targets(self, targets: list[ast.expr]) -> None:
        for name in _target_names(targets):
            self.modules.pop(name, None)
            self.symbols.pop(name, None)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        self.visit(node.value)
        self._discard_targets(node.targets)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if node.value is not None:
            self.visit(node.value)
        self._discard_targets([node.target])

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        saved_modules = self.modules
        saved_symbols = self.symbols
        if self.function_depth == 0:
            self.modules = self.module_bindings.copy()
            self.symbols = self.symbol_bindings.copy()
        else:
            self.modules = self.modules.copy()
            self.symbols = self.symbols.copy()
        for name in _function_local_names(node):
            self.modules.pop(name, None)
            self.symbols.pop(name, None)
        self.function_depth += 1
        for statement in node.body:
            self.visit(statement)
        self.function_depth -= 1
        self.modules = saved_modules
        self.symbols = saved_symbols

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        raw = _dotted_name(node.func)
        if raw is not None:
            parts = raw.split(".")
            resolved = _resolved_symbol(
                raw,
                self.module,
                self.modules,
                self.symbols,
            )
            target = self.symbol_index.get(resolved)
            if target:
                self.counts[target] += 1
            constructor = f"{resolved}.__init__"
            if parts[-1] in self.local_classes:
                constructor = f"{self.module}.{parts[-1]}.__init__"
            constructor_target = self.symbol_index.get(constructor)
            if constructor_target:
                self.counts[constructor_target] += 1
        self.generic_visit(node)


@cache
def _qualified_call_counts(source_root: Path = _SRC) -> Counter[str]:
    """Resolve qualified edges with runtime-global and local-import bindings."""
    trees, symbols = _symbol_index(tuple(sorted(source_root.rglob("*.py"))), source_root)
    counts: Counter[str] = Counter()
    for path, tree in trees.items():
        module = _module_name(path, source_root)
        _QualifiedCallVisitor(tree, module, symbols, counts).visit(tree)
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
        "specify_cli/sync/queue.py::detect_legacy_rows_for_scope::sqlite_connect",
        "specify_cli/delivery/dispatcher.py::_record::transaction_context",
    }
)

_KNOWN_DEAD_FLOOR = frozenset({"specify_cli/sync/queue.py::_queue_db_has_content::sqlite_connect"})


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
    detect_symbol = "specify_cli/sync/queue.py::detect_legacy_rows_for_scope"
    assert _qualified_call_counts()[detect_symbol] == 3
    dead_evidence = {
        site.key: disposition.reachability for site, disposition in zip(sites, dispositions, strict=True) if disposition.category is SiteCategory.DEAD_CODE
    }
    assert set(dead_evidence) == _KNOWN_DEAD_FLOOR
    assert all(evidence.startswith("0 qualified") for evidence in dead_evidence.values())
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


def test_constructor_alias_rebinding_uses_runtime_global_binding(tmp_path: Path) -> None:
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
    assert sites == ()


def test_local_import_reachability_and_python_binding_controls(tmp_path: Path) -> None:
    sync_root = tmp_path / "specify_cli" / "sync"
    cli_root = tmp_path / "specify_cli" / "cli"
    queue = sync_root / "queue.py"
    callers = (
        sync_root / "preflight.py",
        sync_root / "background.py",
        cli_root / "status.py",
    )
    binding_controls = sync_root / "binding_controls.py"
    cli_root.mkdir(parents=True)
    sync_root.mkdir(parents=True, exist_ok=True)
    queue.write_text(
        "import sqlite3\ndef detect_legacy_rows_for_scope(scope):\n    return sqlite3.connect(scope)\n",
        encoding="utf-8",
    )
    callers[0].write_text(
        "def preflight(scope):\n    from specify_cli.sync.queue import detect_legacy_rows_for_scope\n    return detect_legacy_rows_for_scope(scope)\n",
        encoding="utf-8",
    )
    callers[1].write_text(
        "def background(scope):\n    from .queue import detect_legacy_rows_for_scope\n    return detect_legacy_rows_for_scope(scope)\n",
        encoding="utf-8",
    )
    callers[2].write_text(
        "def status(scope):\n    from specify_cli.sync.queue import detect_legacy_rows_for_scope\n    return detect_legacy_rows_for_scope(scope)\n",
        encoding="utf-8",
    )
    binding_controls.write_text(
        "import sqlite3\n"
        "def safe(path):\n"
        "    return path\n"
        "open_sync = sqlite3.connect\n"
        "def runtime_safe(path):\n"
        "    return open_sync(path)\n"
        "open_sync = safe\n"
        "def parameter_safe(sqlite3, path):\n"
        "    return sqlite3.connect(path)\n"
        "def local_owner(path):\n"
        "    import sqlite3 as local_sqlite\n"
        "    return local_sqlite.connect(path)\n",
        encoding="utf-8",
    )

    symbol = "specify_cli/sync/queue.py::detect_legacy_rows_for_scope"
    assert _qualified_call_counts(tmp_path)[symbol] == 3
    disposition = classify_store_site(
        next(site for site in scan_store_sites(source_root=tmp_path) if site.qualname == "detect_legacy_rows_for_scope"),
        source_root=tmp_path,
    )
    assert disposition.category is SiteCategory.LIVE_PAYLOAD_CONTROL
    control_sites = [site.qualname for site in scan_store_sites(source_root=tmp_path) if site.relpath.endswith("binding_controls.py")]
    assert control_sites == ["local_owner"]


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
