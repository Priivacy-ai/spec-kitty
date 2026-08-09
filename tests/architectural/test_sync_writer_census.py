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
_CONSENT_FILES = (
    _SRC / "specify_cli" / "sync" / "config.py",
    _SRC / "specify_cli" / "sync" / "consent.py",
    _SRC / "specify_cli" / "sync" / "routing.py",
    _SRC / "specify_cli" / "cli" / "commands" / "sync.py",
)
_GRANT_FIELDS = frozenset({"enabled", "granted", "effective_sync_enabled"})


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
    qualname: str
    short_name: str
    node: ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class _CallEdge:
    caller: str
    callee: str
    node: ast.Call
    returned: bool


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, relpath: str, records: list[_FunctionRecord]) -> None:
        self.relpath = relpath
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


def _semantic_sites(record: _FunctionRecord) -> list[GrantSite]:
    """Discover grant/refusal shapes without relying on the function's name."""
    sites: list[GrantSite] = []
    owner = "WP03" if record.relpath.endswith("routing.py") else "WP02"
    for node in ast.walk(record.node):
        if isinstance(node, ast.Call):
            callee = _call_tail(node.func) or ast.unparse(node.func)
            for keyword in node.keywords:
                if keyword.arg not in _GRANT_FIELDS:
                    continue
                sites.append(
                    GrantSite(
                        record.relpath,
                        record.qualname,
                        GrantKind.DECISION_RETURN,
                        _expr_effect(keyword.value),
                        f"keyword:{callee}.{keyword.arg}",
                        owner,
                        node.lineno,
                    )
                )
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value in _GRANT_FIELDS and value is not None:
                    sites.append(
                        GrantSite(
                            record.relpath,
                            record.qualname,
                            GrantKind.PERSISTENCE,
                            _expr_effect(value),
                            f"mapping:{key.value}",
                            owner,
                            node.lineno,
                        )
                    )
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            if isinstance(node, ast.Assign):
                targets = node.targets
                value = node.value
            else:
                targets = [node.target]
                if node.value is None:
                    continue
                value = node.value
            for target in targets:
                if isinstance(target, ast.Subscript) and _subscript_key(target) in _GRANT_FIELDS:
                    sites.append(
                        GrantSite(
                            record.relpath,
                            record.qualname,
                            GrantKind.PERSISTENCE,
                            _expr_effect(value),
                            f"subscript:{_subscript_key(target)}",
                            owner,
                            node.lineno,
                        )
                    )
        if isinstance(node, ast.Return) and node.value is not None:
            names = {item.id for item in ast.walk(node.value) if isinstance(item, ast.Name)} | {
                item.attr for item in ast.walk(node.value) if isinstance(item, ast.Attribute)
            }
            if names & _GRANT_FIELDS:
                sites.append(
                    GrantSite(
                        record.relpath,
                        record.qualname,
                        GrantKind.DECISION_RETURN,
                        _expr_effect(node.value),
                        "return:grant-field",
                        owner,
                        node.lineno,
                    )
                )
    return sites


def _functions(paths: tuple[Path, ...], source_root: Path) -> list[_FunctionRecord]:
    records: list[_FunctionRecord] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relpath = path.relative_to(source_root).as_posix()
        _FunctionCollector(relpath, records).visit(tree)
    return records


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


def _call_targets(
    record: _FunctionRecord,
    call: ast.Call,
    *,
    by_short: dict[str, list[_FunctionRecord]],
    by_qualname: dict[str, list[_FunctionRecord]],
) -> list[_FunctionRecord]:
    func = call.func
    if isinstance(func, ast.Name):
        return by_short.get(func.id, [])
    if not isinstance(func, ast.Attribute):
        return []
    if isinstance(func.value, ast.Name) and func.value.id == "self" and "." in record.qualname:
        owner = record.qualname.rsplit(".", 1)[0]
        return by_qualname.get(f"{owner}.{func.attr}", [])
    if isinstance(func.value, ast.Call):
        constructor_owner = _call_tail(func.value.func)
        if constructor_owner is not None:
            qualified = by_qualname.get(f"{constructor_owner}.{func.attr}")
            if qualified:
                return qualified
    return by_short.get(func.attr, [])


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


def scan_grant_paths(
    paths: tuple[Path, ...] = _CONSENT_FILES,
    *,
    source_root: Path = _SRC,
) -> tuple[GrantSite, ...]:
    """Discover direct semantic sites, then every transitive source caller."""
    records = _functions(paths, source_root)
    by_short: dict[str, list[_FunctionRecord]] = defaultdict(list)
    by_qualname: dict[str, list[_FunctionRecord]] = defaultdict(list)
    by_identity: dict[str, _FunctionRecord] = {}
    direct: list[GrantSite] = []
    for record in records:
        identity = f"{record.relpath}::{record.qualname}"
        by_identity[identity] = record
        by_short[record.short_name].append(record)
        by_qualname[record.qualname].append(record)
        direct.extend(_semantic_sites(record))
    edges: list[_CallEdge] = []
    for record in records:
        caller_id = f"{record.relpath}::{record.qualname}"
        for node in ast.walk(record.node):
            if isinstance(node, ast.Call):
                for callee in _call_targets(
                    record,
                    node,
                    by_short=by_short,
                    by_qualname=by_qualname,
                ):
                    edges.append(
                        _CallEdge(
                            caller_id,
                            f"{callee.relpath}::{callee.qualname}",
                            node,
                            _is_returned(record.node, node),
                        )
                    )

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
    source = tmp_path / "specify_cli" / "sync" / "mutant.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def decide_anything():\n"
        "    return ConsentDecision(granted=True)\n"
        "def remember_anything(record, answer):\n"
        "    record['enabled'] = bool(answer)\n"
        "def renamed_entry(record):\n"
        "    remember_anything(record, decide_anything())\n",
        encoding="utf-8",
    )
    sites = scan_grant_paths((source,), source_root=tmp_path)
    identities = {(site.qualname, site.kind) for site in sites}
    assert ("decide_anything", GrantKind.DECISION_RETURN) in identities
    assert ("remember_anything", GrantKind.PERSISTENCE) in identities
    assert ("renamed_entry", GrantKind.CALL_PATH) in identities
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
