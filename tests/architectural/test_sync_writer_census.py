"""Semantic census of grant-producing and grant-persisting source paths.

Unlike a callee-name allowlist, this collector starts from syntax that can create
or persist an ``enabled``/``granted`` value, then walks the source call graph back
to every callable entry.  A differently named constructor or writer is therefore
new census growth.  Explicit literal refusal calls are retained as a distinct
effect and may never be promoted by the final boundary.
"""

from __future__ import annotations

import ast
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pytest

from specify_cli.sync.consent import resolve_project_consent

pytestmark = [pytest.mark.architectural]

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
_CONSENT_ROOTS = (
    _SRC / "specify_cli" / "sync",
    _SRC / "specify_cli" / "cli" / "commands" / "sync.py",
)
_GRANT_FIELDS = frozenset({"enabled", "granted", "effective_sync_enabled"})
_ENABLED_MODELS = frozenset(
    {
        "CheckoutSyncRouting",
        "ProjectConsentRead",
        "UnresolvedConsentEntry",
    }
)
_ENABLED_WRITERS = frozenset(
    {
        "SyncConfig.set_checkout_sync_enabled",
        "SyncConfig.set_project_consent_bulk",
        "SyncConfig.set_repository_sync_enabled",
    }
)


class GrantKind(StrEnum):
    DECISION_RETURN = "decision-return"
    PERSISTENCE = "persistence"
    CALL_PATH = "call-path"


class GrantEffect(StrEnum):
    MAY_GRANT = "may-grant"
    REFUSAL_ONLY = "refusal-only"


@dataclass(frozen=True, order=True)
class GrantSite:
    relpath: str
    qualname: str
    kind: GrantKind
    effect: GrantEffect
    evidence: str
    owner_wp: str
    lineno: int

    @property
    def key(self) -> str:
        return f"{self.relpath}::{self.qualname}::{self.kind.value}::{self.effect.value}::{self.evidence}"


@dataclass(frozen=True)
class _FunctionRecord:
    relpath: str
    module: str
    qualname: str
    short_name: str
    node: ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class _CallEdge:
    caller: str
    callee: str
    node: ast.Call
    returned: bool


@dataclass(frozen=True)
class _ImportBindings:
    modules: dict[str, str]
    symbols: dict[str, str]


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, relpath: str, module: str, records: list[_FunctionRecord]) -> None:
        self.relpath = relpath
        self.module = module
        self.records = records
        self.classes: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def _record(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.records.append(
            _FunctionRecord(
                self.relpath,
                self.module,
                ".".join((*self.classes, node.name)),
                node.name,
                node,
            )
        )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._record(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._record(node)


def _expr_effect(node: ast.expr) -> GrantEffect:
    if isinstance(node, ast.Constant) and node.value is False:
        return GrantEffect.REFUSAL_ONLY
    return GrantEffect.MAY_GRANT


def _subscript_key(node: ast.Subscript) -> str | None:
    value = node.slice
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def _call_tail(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _domain_field(field: str, *context: str) -> bool:
    if field in {"granted", "effective_sync_enabled"}:
        return True
    return any(value in _ENABLED_MODELS or value in _ENABLED_WRITERS for value in context)


def _target_field(target: ast.expr) -> tuple[str | None, str]:
    if isinstance(target, ast.Subscript):
        return _subscript_key(target), ast.unparse(target.value)
    if isinstance(target, ast.Attribute):
        return target.attr, ast.unparse(target.value)
    return None, ""


def _grant_site(
    record: _FunctionRecord,
    node: ast.AST,
    kind: GrantKind,
    value: ast.expr,
    evidence: str,
) -> GrantSite:
    return GrantSite(
        record.relpath,
        record.qualname,
        kind,
        _expr_effect(value),
        evidence,
        "WP03" if record.relpath.endswith("routing.py") else "WP02",
        getattr(node, "lineno", 0),
    )


def _keyword_sites(record: _FunctionRecord, node: ast.Call) -> list[GrantSite]:
    callee = _call_tail(node.func) or ast.unparse(node.func)
    return [
        _grant_site(
            record,
            node,
            GrantKind.DECISION_RETURN,
            keyword.value,
            f"keyword:{callee}.{keyword.arg}",
        )
        for keyword in node.keywords
        if keyword.arg in _GRANT_FIELDS and _domain_field(keyword.arg, callee, record.qualname)
    ]


def _mapping_sites(record: _FunctionRecord, node: ast.Dict) -> list[GrantSite]:
    sites: list[GrantSite] = []
    for key, value in zip(node.keys, node.values, strict=True):
        if not (
            isinstance(key, ast.Constant)
            and isinstance(key.value, str)
            and key.value in _GRANT_FIELDS
            and value is not None
            and _domain_field(key.value, record.qualname)
        ):
            continue
        sites.append(
            _grant_site(
                record,
                node,
                GrantKind.PERSISTENCE,
                value,
                f"mapping:{key.value}",
            )
        )
    return sites


def _assignment_sites(
    record: _FunctionRecord,
    node: ast.Assign | ast.AnnAssign,
) -> list[GrantSite]:
    if isinstance(node, ast.Assign):
        targets, value = node.targets, node.value
    elif node.value is not None:
        targets, value = [node.target], node.value
    else:
        return []
    sites: list[GrantSite] = []
    for target in targets:
        field, base = _target_field(target)
        if field not in _GRANT_FIELDS or not _domain_field(
            field,
            base,
            record.qualname,
        ):
            continue
        prefix = "attribute" if isinstance(target, ast.Attribute) else "subscript"
        sites.append(
            _grant_site(
                record,
                node,
                GrantKind.PERSISTENCE,
                value,
                f"{prefix}:{field}",
            )
        )
    return sites


def _update_sites(record: _FunctionRecord, node: ast.Call) -> list[GrantSite]:
    if not isinstance(node.func, ast.Attribute) or node.func.attr not in {
        "update",
        "setdefault",
    }:
        return []
    base = ast.unparse(node.func.value)
    sites = [
        _grant_site(
            record,
            node,
            GrantKind.PERSISTENCE,
            keyword.value,
            f"update:{keyword.arg}",
        )
        for keyword in node.keywords
        if keyword.arg in _GRANT_FIELDS and _domain_field(keyword.arg, base, record.qualname)
    ]
    for mapping in (arg for arg in node.args if isinstance(arg, ast.Dict)):
        for site in _mapping_sites(record, mapping):
            sites.append(
                _grant_site(
                    record,
                    node,
                    GrantKind.PERSISTENCE,
                    next(
                        value
                        for key, value in zip(
                            mapping.keys,
                            mapping.values,
                            strict=True,
                        )
                        if isinstance(key, ast.Constant) and key.value == site.evidence.removeprefix("mapping:") and value is not None
                    ),
                    site.evidence.replace("mapping:", "update:"),
                )
            )
    return sites


def _setattr_sites(record: _FunctionRecord, node: ast.Call) -> list[GrantSite]:
    if _call_tail(node.func) != "setattr" or len(node.args) < 3:
        return []
    receiver, field_node, value = node.args[:3]
    if not (
        isinstance(field_node, ast.Constant)
        and isinstance(field_node.value, str)
        and field_node.value in _GRANT_FIELDS
        and _domain_field(
            field_node.value,
            ast.unparse(receiver),
            record.qualname,
        )
    ):
        return []
    return [
        _grant_site(
            record,
            node,
            GrantKind.PERSISTENCE,
            value,
            f"setattr:{field_node.value}",
        )
    ]


def _return_sites(record: _FunctionRecord, node: ast.Return) -> list[GrantSite]:
    if node.value is None:
        return []
    names = {item.id for item in ast.walk(node.value) if isinstance(item, ast.Name)} | {
        item.attr for item in ast.walk(node.value) if isinstance(item, ast.Attribute)
    }
    if not names & _GRANT_FIELDS:
        return []
    return [
        _grant_site(
            record,
            node,
            GrantKind.DECISION_RETURN,
            node.value,
            "return:grant-field",
        )
    ]


def _semantic_sites(record: _FunctionRecord) -> list[GrantSite]:
    """Discover grant/refusal shapes without relying on the function's name."""
    sites: list[GrantSite] = []
    for node in ast.walk(record.node):
        if isinstance(node, ast.Call):
            sites.extend(_keyword_sites(record, node))
            sites.extend(_update_sites(record, node))
            sites.extend(_setattr_sites(record, node))
        elif isinstance(node, ast.Dict):
            sites.extend(_mapping_sites(record, node))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            sites.extend(_assignment_sites(record, node))
        elif isinstance(node, ast.Return):
            sites.extend(_return_sites(record, node))
    return sites


def _module_name(path: Path, source_root: Path) -> str:
    parts = list(path.relative_to(source_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _functions(paths: tuple[Path, ...], source_root: Path) -> list[_FunctionRecord]:
    records: list[_FunctionRecord] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relpath = path.relative_to(source_root).as_posix()
        _FunctionCollector(relpath, _module_name(path, source_root), records).visit(tree)
    return records


def _import_bindings(path: Path, source_root: Path) -> _ImportBindings:
    module = _module_name(path, source_root)
    package = module.split(".")[:-1]
    modules: dict[str, str] = {}
    symbols: dict[str, str] = {}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                modules.pop(bound, None)
                symbols.pop(bound, None)
                modules[bound] = alias.name if alias.asname else bound
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                prefix = package[: len(package) - node.level + 1]
                imported_module = ".".join((*prefix, *(node.module or "").split(".")))
            else:
                imported_module = node.module or ""
            for alias in node.names:
                bound = alias.asname or alias.name
                modules.pop(bound, None)
                symbols[bound] = f"{imported_module}.{alias.name}"
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    modules.pop(target.id, None)
                    symbols.pop(target.id, None)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            modules.pop(node.target.id, None)
            symbols.pop(node.target.id, None)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            modules.pop(node.name, None)
            symbols.pop(node.name, None)
    return _ImportBindings(modules, symbols)


def _relative_import_module(record: _FunctionRecord, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    package = record.module.split(".")[:-1]
    prefix = package[: len(package) - node.level + 1]
    return ".".join((*prefix, *((node.module or "").split("."))))


def _local_names(record: _FunctionRecord) -> set[str]:
    node = record.node
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
    for item in ast.walk(node):
        if isinstance(item, (ast.Assign, ast.AnnAssign)):
            targets = item.targets if isinstance(item, ast.Assign) else [item.target]
            names.update(target.id for target in targets if isinstance(target, ast.Name))
        elif isinstance(item, ast.Import):
            names.update(alias.asname or alias.name.split(".")[0] for alias in item.names)
        elif isinstance(item, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in item.names)
    return names


def _bindings_before_call(
    record: _FunctionRecord,
    call: ast.Call,
    module_bindings: _ImportBindings,
) -> _ImportBindings:
    modules = module_bindings.modules.copy()
    symbols = module_bindings.symbols.copy()
    for name in _local_names(record):
        modules.pop(name, None)
        symbols.pop(name, None)
    preceding = sorted(
        (
            item
            for item in ast.walk(record.node)
            if isinstance(item, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)) and getattr(item, "lineno", 0) < call.lineno
        ),
        key=lambda item: (item.lineno, item.col_offset),
    )
    for item in preceding:
        if isinstance(item, ast.Import):
            for alias in item.names:
                bound = alias.asname or alias.name.split(".")[0]
                modules.pop(bound, None)
                symbols.pop(bound, None)
                modules[bound] = alias.name if alias.asname else bound
        elif isinstance(item, ast.ImportFrom):
            imported_module = _relative_import_module(record, item)
            for alias in item.names:
                bound = alias.asname or alias.name
                modules.pop(bound, None)
                symbols[bound] = f"{imported_module}.{alias.name}"
        else:
            targets = item.targets if isinstance(item, ast.Assign) else [item.target]
            alias_symbol = symbols.get(item.value.id) if item.value is not None and isinstance(item.value, ast.Name) else None
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                modules.pop(target.id, None)
                symbols.pop(target.id, None)
                if alias_symbol is not None:
                    symbols[target.id] = alias_symbol
    return _ImportBindings(modules, symbols)


def _is_returned(function: ast.FunctionDef | ast.AsyncFunctionDef, call: ast.Call) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value = node.value
        if value is call:
            return True
        if isinstance(value, ast.Subscript) and value.value is call:
            return True
        if isinstance(value, ast.Await) and value.value is call:
            return True
    return False


def _receiver_types(
    record: _FunctionRecord,
    bindings: _ImportBindings,
    *,
    before_lineno: int,
) -> dict[str, str]:
    receiver_types: dict[str, str] = {}
    for assignment in ast.walk(record.node):
        if (
            not isinstance(assignment, ast.Assign)
            or not isinstance(
                assignment.value,
                ast.Call,
            )
            or assignment.lineno >= before_lineno
        ):
            continue
        constructor = assignment.value.func
        if isinstance(constructor, ast.Name):
            constructor_symbol = bindings.symbols.get(
                constructor.id,
                f"{record.module}.{constructor.id}",
            )
        elif isinstance(constructor, ast.Attribute) and isinstance(
            constructor.value,
            ast.Name,
        ):
            root = constructor.value.id
            prefix = bindings.modules.get(root, bindings.symbols.get(root))
            constructor_symbol = f"{prefix}.{constructor.attr}" if prefix else f"{record.module}.{root}.{constructor.attr}"
        else:
            continue
        for target_node in assignment.targets:
            if isinstance(target_node, ast.Name):
                receiver_types[target_node.id] = constructor_symbol
    return receiver_types


def _call_targets(
    record: _FunctionRecord,
    call: ast.Call,
    *,
    by_symbol: dict[str, _FunctionRecord],
    bindings: _ImportBindings,
) -> list[_FunctionRecord]:
    bindings = _bindings_before_call(record, call, bindings)
    receiver_types = _receiver_types(record, bindings, before_lineno=call.lineno)

    func = call.func
    if isinstance(func, ast.Name):
        symbol = bindings.symbols.get(func.id, f"{record.module}.{func.id}")
        target = by_symbol.get(symbol)
        return [target] if target else []
    if not isinstance(func, ast.Attribute):
        return []
    if isinstance(func.value, ast.Name) and func.value.id in {"self", "cls"} and "." in record.qualname:
        owner = record.qualname.rsplit(".", 1)[0]
        target = by_symbol.get(f"{record.module}.{owner}.{func.attr}")
        return [target] if target else []
    if isinstance(func.value, ast.Name):
        root = func.value.id
        if root in receiver_types:
            symbol = f"{receiver_types[root]}.{func.attr}"
        elif root in bindings.modules:
            symbol = f"{bindings.modules[root]}.{func.attr}"
        elif root in bindings.symbols:
            symbol = f"{bindings.symbols[root]}.{func.attr}"
        else:
            symbol = f"{record.module}.{root}.{func.attr}"
        target = by_symbol.get(symbol)
        return [target] if target else []
    if isinstance(func.value, ast.Call):
        constructor_owner = _call_tail(func.value.func)
        if constructor_owner is not None:
            owner_symbol = bindings.symbols.get(
                constructor_owner,
                f"{record.module}.{constructor_owner}",
            )
            target = by_symbol.get(f"{owner_symbol}.{func.attr}")
            return [target] if target else []
    return []


def _edge_effect(
    callee: _FunctionRecord,
    call: ast.Call,
    fallback: GrantEffect,
) -> GrantEffect:
    args = [*callee.node.args.posonlyargs, *callee.node.args.args]
    if args and args[0].arg in {"self", "cls"}:
        args = args[1:]
    for index, argument in enumerate(args):
        if argument.arg not in _GRANT_FIELDS:
            continue
        value: ast.expr | None = call.args[index] if index < len(call.args) else None
        for keyword in call.keywords:
            if keyword.arg == argument.arg:
                value = keyword.value
        if value is not None:
            return _expr_effect(value)
    return fallback


def _grant_paths(paths: tuple[Path, ...] | None, source_root: Path) -> tuple[Path, ...]:
    if paths is None:
        discovered: list[Path] = []
        for root in _CONSENT_ROOTS if source_root == _SRC else (source_root,):
            discovered.extend(root.rglob("*.py") if root.is_dir() else [root])
        return tuple(sorted(set(discovered)))
    return paths


def _grant_index(
    records: list[_FunctionRecord],
) -> tuple[dict[str, _FunctionRecord], dict[str, _FunctionRecord], list[GrantSite]]:
    by_symbol: dict[str, _FunctionRecord] = {}
    by_identity: dict[str, _FunctionRecord] = {}
    direct: list[GrantSite] = []
    for record in records:
        identity = f"{record.relpath}::{record.qualname}"
        by_identity[identity] = record
        by_symbol[f"{record.module}.{record.qualname}"] = record
        direct.extend(_semantic_sites(record))
    return by_symbol, by_identity, direct


def _grant_edges(
    records: list[_FunctionRecord],
    by_symbol: dict[str, _FunctionRecord],
    bindings_by_relpath: dict[str, _ImportBindings],
) -> list[_CallEdge]:
    edges: list[_CallEdge] = []
    for record in records:
        caller_id = f"{record.relpath}::{record.qualname}"
        for node in ast.walk(record.node):
            if isinstance(node, ast.Call):
                for callee in _call_targets(
                    record,
                    node,
                    by_symbol=by_symbol,
                    bindings=bindings_by_relpath[record.relpath],
                ):
                    edges.append(
                        _CallEdge(
                            caller_id,
                            f"{callee.relpath}::{callee.qualname}",
                            node,
                            _is_returned(record.node, node),
                        )
                    )
    return edges


def _grant_capabilities(
    direct: list[GrantSite],
    edges: list[_CallEdge],
    by_identity: dict[str, _FunctionRecord],
) -> dict[str, dict[GrantKind, GrantEffect]]:
    capabilities: dict[str, dict[GrantKind, GrantEffect]] = defaultdict(dict)
    for site in direct:
        identity = f"{site.relpath}::{site.qualname}"
        old = capabilities[identity].get(site.kind)
        capabilities[identity][site.kind] = GrantEffect.MAY_GRANT if GrantEffect.MAY_GRANT in {old, site.effect} else GrantEffect.REFUSAL_ONLY

    changed = True
    while changed:
        changed = False
        for edge in edges:
            callee = by_identity[edge.callee]
            for kind, effect in tuple(capabilities.get(edge.callee, {}).items()):
                if kind is GrantKind.DECISION_RETURN and not edge.returned:
                    continue
                propagated = _edge_effect(callee, edge.node, effect)
                old = capabilities[edge.caller].get(kind)
                new = GrantEffect.MAY_GRANT if GrantEffect.MAY_GRANT in {old, propagated} else GrantEffect.REFUSAL_ONLY
                if old != new:
                    capabilities[edge.caller][kind] = new
                    changed = True
    return capabilities


def _grant_call_sites(
    edges: list[_CallEdge],
    by_identity: dict[str, _FunctionRecord],
    capabilities: dict[str, dict[GrantKind, GrantEffect]],
) -> list[GrantSite]:
    call_sites: list[GrantSite] = []
    for edge in edges:
        caller_record = by_identity[edge.caller]
        callee_record = by_identity[edge.callee]
        for kind, effect in capabilities.get(edge.callee, {}).items():
            if kind is GrantKind.DECISION_RETURN and not edge.returned:
                continue
            call_sites.append(
                GrantSite(
                    caller_record.relpath,
                    caller_record.qualname,
                    GrantKind.CALL_PATH,
                    _edge_effect(callee_record, edge.node, effect),
                    f"calls:{callee_record.short_name}:{kind.value}",
                    "WP03" if caller_record.relpath.endswith("routing.py") else "WP02",
                    edge.node.lineno,
                )
            )
    return call_sites


def scan_grant_paths(
    paths: tuple[Path, ...] | None = None,
    *,
    source_root: Path = _SRC,
) -> tuple[GrantSite, ...]:
    """Discover direct semantic sites, then every transitive source caller."""
    paths = _grant_paths(paths, source_root)
    records = _functions(paths, source_root)
    by_symbol, by_identity, direct = _grant_index(records)
    bindings_by_relpath = {path.relative_to(source_root).as_posix(): _import_bindings(path, source_root) for path in paths}
    edges = _grant_edges(records, by_symbol, bindings_by_relpath)
    capabilities = _grant_capabilities(direct, edges, by_identity)
    call_sites = _grant_call_sites(edges, by_identity, capabilities)
    return tuple(sorted({*direct, *call_sites}))


# Populated from the source-derived collector and frozen by qualified symbol,
# semantic shape, effect, and multiplicity.  It is intentionally not a list of
# callable names the collector should search for.
_KNOWN_GRANT_SITE_COUNTS: Counter[str] = Counter(
    line.strip()
    for line in """
specify_cli/cli/commands/sync.py::_run_consent_index_backfill::call-path::may-grant::calls:backfill_uuid_consent_index:persistence
specify_cli/cli/commands/sync.py::migrate::call-path::may-grant::calls:_run_consent_index_backfill:persistence
specify_cli/cli/commands/sync.py::opt_in::call-path::may-grant::calls:enable_checkout_sync:persistence
specify_cli/cli/commands/sync.py::opt_out::call-path::refusal-only::calls:disable_checkout_sync:persistence
specify_cli/sync/background.py::_consenting_body_project_uuids::call-path::may-grant::calls:consented_project_uuids:decision-return
specify_cli/sync/body_upload.py::project_consents_to_hosted_sync::decision-return::may-grant::return:grant-field
specify_cli/sync/config.py::SyncConfig.get_checkout_sync_enabled::decision-return::may-grant::return:grant-field
specify_cli/sync/config.py::SyncConfig.get_project_consent::call-path::may-grant::calls:_project_consent_entry:decision-return
specify_cli/sync/config.py::SyncConfig.get_repository_sync_enabled::decision-return::may-grant::return:grant-field
specify_cli/sync/config.py::SyncConfig.read_project_consent::decision-return::may-grant::keyword:ProjectConsentRead.enabled
specify_cli/sync/config.py::SyncConfig.read_project_consent::decision-return::may-grant::keyword:ProjectConsentRead.enabled
specify_cli/sync/config.py::SyncConfig.read_project_consent::decision-return::may-grant::keyword:ProjectConsentRead.enabled
specify_cli/sync/config.py::SyncConfig.read_project_consent::decision-return::may-grant::return:grant-field
specify_cli/sync/config.py::SyncConfig.set_checkout_sync_enabled::persistence::may-grant::mapping:enabled
specify_cli/sync/config.py::SyncConfig.set_project_consent::call-path::may-grant::calls:set_project_consent_bulk:persistence
specify_cli/sync/config.py::SyncConfig.set_project_consent_bulk::persistence::may-grant::mapping:enabled
specify_cli/sync/config.py::SyncConfig.set_repository_sync_enabled::persistence::may-grant::mapping:enabled
specify_cli/sync/config.py::_project_consent_entry::decision-return::may-grant::return:grant-field
specify_cli/sync/config.py::_project_consent_entry::decision-return::may-grant::return:grant-field
specify_cli/sync/consent.py::_answer_machine_index::decision-return::may-grant::keyword:ConsentDecision.granted
specify_cli/sync/consent.py::_answer_machine_index::decision-return::may-grant::return:grant-field
specify_cli/sync/consent.py::_answer_machine_index::decision-return::refusal-only::keyword:ConsentDecision.granted
specify_cli/sync/consent.py::_answer_project_local::call-path::may-grant::calls:_reconcile_index:persistence
specify_cli/sync/consent.py::_answer_project_local::call-path::refusal-only::calls:_reconcile_index:persistence
specify_cli/sync/consent.py::_answer_project_local::decision-return::may-grant::keyword:ConsentDecision.granted
specify_cli/sync/consent.py::_answer_project_local::decision-return::may-grant::return:grant-field
specify_cli/sync/consent.py::_answer_project_local::decision-return::refusal-only::keyword:ConsentDecision.granted
specify_cli/sync/consent.py::_answer_project_local::decision-return::refusal-only::keyword:ConsentDecision.granted
specify_cli/sync/consent.py::_reconcile_index::call-path::may-grant::calls:set_project_consent:persistence
specify_cli/sync/consent.py::backfill_uuid_consent_index::call-path::may-grant::calls:set_project_consent_bulk:persistence
specify_cli/sync/consent.py::backfill_uuid_consent_index::decision-return::may-grant::keyword:UnresolvedConsentEntry.enabled
specify_cli/sync/consent.py::consented_project_uuids::decision-return::may-grant::return:grant-field
specify_cli/sync/consent.py::get_project_consent::call-path::may-grant::calls:get_project_consent:decision-return
specify_cli/sync/consent.py::resolve_project_consent::decision-return::refusal-only::keyword:ConsentDecision.granted
specify_cli/sync/consent.py::resolve_project_consent::decision-return::refusal-only::keyword:ConsentDecision.granted
specify_cli/sync/consent.py::set_project_consent::call-path::may-grant::calls:set_project_consent:persistence
specify_cli/sync/local_commit.py::_frame_project_consents::decision-return::may-grant::return:grant-field
specify_cli/sync/routing.py::_build_checkout_sync_routing::call-path::refusal-only::calls:_deny_routing_for_project_local_fault:decision-return
specify_cli/sync/routing.py::_build_checkout_sync_routing::decision-return::may-grant::keyword:CheckoutSyncRouting.effective_sync_enabled
specify_cli/sync/routing.py::_build_checkout_sync_routing::decision-return::may-grant::return:grant-field
specify_cli/sync/routing.py::_deny_routing_for_project_local_fault::decision-return::refusal-only::keyword:CheckoutSyncRouting.effective_sync_enabled
specify_cli/sync/routing.py::_routing_for_unreadable_project_config::call-path::refusal-only::calls:_deny_routing_for_project_local_fault:decision-return
specify_cli/sync/routing.py::disable_checkout_sync::call-path::refusal-only::calls:set_project_consent:persistence
specify_cli/sync/routing.py::disable_checkout_sync::call-path::refusal-only::calls:set_repository_sync_enabled:persistence
specify_cli/sync/routing.py::disable_checkout_sync::call-path::refusal-only::calls:write_local_sync_enabled:persistence
specify_cli/sync/routing.py::enable_checkout_sync::call-path::may-grant::calls:set_project_consent:persistence
specify_cli/sync/routing.py::enable_checkout_sync::call-path::may-grant::calls:set_repository_sync_enabled:persistence
specify_cli/sync/routing.py::enable_checkout_sync::call-path::may-grant::calls:write_local_sync_enabled:persistence
specify_cli/sync/routing.py::is_sync_enabled_for_checkout::decision-return::may-grant::return:grant-field
specify_cli/sync/routing.py::read_local_sync_enabled::call-path::may-grant::calls:get_checkout_sync_enabled:decision-return
specify_cli/sync/routing.py::resolve_checkout_sync_routing::call-path::may-grant::calls:_build_checkout_sync_routing:decision-return
specify_cli/sync/routing.py::resolve_checkout_sync_routing_readonly::call-path::may-grant::calls:_build_checkout_sync_routing:decision-return
specify_cli/sync/routing.py::write_local_sync_enabled::call-path::may-grant::calls:set_checkout_sync_enabled:persistence
specify_cli/sync/runtime.py::event_project_consents_to_publish::decision-return::may-grant::return:grant-field
""".splitlines()
    if line.strip()
)


def final_grant_writer_violations(
    sites: tuple[GrantSite, ...],
) -> tuple[GrantSite, ...]:
    """Only the exact store decision writer may create/persist a grant."""
    return tuple(
        site
        for site in sites
        if site.effect is GrantEffect.MAY_GRANT
        and not (site.relpath == "specify_cli/sync/project_store.py" and site.qualname == "ProjectSyncStore.set_consent_decision")
    )


def test_source_discovered_grant_census_cannot_grow() -> None:
    sites = scan_grant_paths()
    observed = Counter(site.key for site in sites)
    growth = observed - _KNOWN_GRANT_SITE_COUNTS
    assert not growth, "new grant-producing/persisting paths:\n" + "\n".join(f"{key} (+{count})" for key, count in sorted(growth.items()))
    assert any(site.kind is GrantKind.PERSISTENCE for site in sites)
    assert any(site.kind is GrantKind.DECISION_RETURN for site in sites)
    assert any(site.kind is GrantKind.CALL_PATH for site in sites)
    assert any(site.effect is GrantEffect.REFUSAL_ONLY for site in sites)
    assert all(site.owner_wp for site in sites)
    shrink = _KNOWN_GRANT_SITE_COUNTS - observed
    if shrink:
        warnings.warn(
            "grant census shrank; keep the ratchet baseline unchanged: " + ", ".join(f"{key} (-{count})" for key, count in sorted(shrink.items())),
            stacklevel=1,
        )


def test_differently_named_grant_and_persistence_mutants_use_real_collector(
    tmp_path: Path,
) -> None:
    sync_root = tmp_path / "specify_cli" / "sync"
    source = sync_root / "previously_unseen.py"
    noise = sync_root / "same_name_noise.py"
    caller = sync_root / "caller.py"
    rebound = sync_root / "rebound_import.py"
    writer = sync_root / "writer.py"
    sync_root.mkdir(parents=True)
    source.write_text(
        "def decide_anything():\n"
        "    return ConsentDecision(granted=True)\n"
        "def remember_anything(record, answer):\n"
        "    record.granted = answer\n"
        "    record.update({'granted': answer})\n"
        "    setattr(record, 'granted', answer)\n"
        "def renamed_entry(record):\n"
        "    remember_anything(record, decide_anything())\n",
        encoding="utf-8",
    )
    noise.write_text(
        "def remember_anything(widget):\n"
        "    return widget.configure(enabled=True)\n"
        "def configure_project_sync_widget(widget):\n"
        "    return widget.configure(enabled=True)\n",
        encoding="utf-8",
    )
    caller.write_text(
        "from specify_cli.sync.previously_unseen import remember_anything\ndef external_entry(record, answer):\n    remember_anything(record, answer)\n",
        encoding="utf-8",
    )
    writer.write_text(
        "def persist(record, answer):\n    setattr(record, 'granted', answer)\n",
        encoding="utf-8",
    )
    rebound.write_text(
        "from specify_cli.sync.writer import persist\n"
        "def safe(record, answer):\n"
        "    return answer\n"
        "persist = safe\n"
        "def rebound_entry(record, answer):\n"
        "    return persist(record, answer)\n",
        encoding="utf-8",
    )
    sites = scan_grant_paths(source_root=tmp_path)
    identities = {(site.qualname, site.kind) for site in sites}
    assert ("decide_anything", GrantKind.DECISION_RETURN) in identities
    assert ("remember_anything", GrantKind.PERSISTENCE) in identities
    assert any(site.evidence == "setattr:granted" for site in sites)
    assert ("renamed_entry", GrantKind.CALL_PATH) in identities
    assert ("external_entry", GrantKind.CALL_PATH) in identities
    assert ("rebound_entry", GrantKind.CALL_PATH) not in identities
    assert not any(site.relpath.endswith("same_name_noise.py") for site in sites), "unrelated enabled fields and same-named functions are not grant authority"
    assert final_grant_writer_violations(sites)


def test_absence_denies_all_ambient_non_grant_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "isolated-home"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://app.spec-kitty.ai")
    monkeypatch.setenv("SPEC_KITTY_TEAM", "logged-in-team")
    # Path, discovery, alias, target/host, login, store presence, and truthy env
    # are deliberately present.  None records the UUID's explicit decision.
    root = tmp_path / "same-slug-does-not-vouch"
    (root / ".kittify").mkdir(parents=True)
    (tmp_path / "isolated-home" / "projects" / "present-store").mkdir(parents=True)
    decision = resolve_project_consent(
        "aaaaaaaa-0000-0000-0000-000000000001",
        repo_root=root,
    )
    assert decision.granted is False


def test_explicit_legacy_refusal_is_distinct_from_grant() -> None:
    refusal = GrantSite(
        "specify_cli/sync/project_store_migration.py",
        "import_refusal",
        GrantKind.PERSISTENCE,
        GrantEffect.REFUSAL_ONLY,
        "mapping:granted",
        "WP10",
        1,
    )
    grant = GrantSite(
        "specify_cli/sync/legacy.py",
        "promote",
        GrantKind.PERSISTENCE,
        GrantEffect.MAY_GRANT,
        "mapping:granted",
        "WP10",
        1,
    )
    assert final_grant_writer_violations((refusal,)) == ()
    assert final_grant_writer_violations((grant,)) == (grant,)
