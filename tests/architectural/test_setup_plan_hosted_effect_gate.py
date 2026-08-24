"""Provenance-aware AST recurrence gate for setup-plan hosted effects."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

ROOT = Path(__file__).resolve().parents[2]
SETUP_PLAN = ROOT / "src/specify_cli/cli/commands/agent/mission_setup_plan.py"
EXECUTOR = "_execute_setup_plan_hosted_effects"
DOSSIER_ADAPTER = "_trigger_dossier_sync"
VALIDATOR = "is_canonical_hosted_sync_decision"
VALIDATOR_IDENTITY = (
    "specify_cli.cli.commands.agent.setup_plan_hosted."
    "is_canonical_hosted_sync_decision"
)

EXACT_SINKS = frozenset(
    {
        DOSSIER_ADAPTER,
        "specify_cli.status.lifecycle_events.fanout_lifecycle_event_hosted",
        "specify_cli.sync.dossier_pipeline.trigger_feature_dossier_sync_if_enabled",
        "specify_cli.sync.queue.OfflineQueue",
        "specify_cli.sync.body_queue.OfflineBodyUploadQueue",
        "specify_cli.sync.events._request_dashboard_sync",
        "specify_cli.sync.events._publish_event_via_sync_daemon",
        "specify_cli.auth.transport.get_client",
        "specify_cli.auth.transport.get_async_client",
    }
)
HOSTED_OBJECT_PREFIXES = (
    "specify_cli.sync.queue.OfflineQueue",
    "specify_cli.sync.body_queue.OfflineBodyUploadQueue",
    "specify_cli.status.lifecycle_events",
    "specify_cli.sync.dossier_pipeline",
    "specify_cli.sync.events",
    "specify_cli.auth.transport",
)
HOSTED_METHODS = frozenset(
    {"queue_event", "enqueue", "queue_body_upload", "get_client", "get_async_client"}
)


@dataclass(frozen=True)
class _Scope:
    owner: str
    node: ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class _Finding:
    owner: str
    sink: str
    lineno: int


class _ScopeCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.scopes: list[_Scope] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        owner = ".<locals>.".join((*self.stack, node.name))
        self.scopes.append(_Scope(owner, node))
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function


class _OwnBodyCollector(ast.NodeVisitor):
    def __init__(self, root: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.root = root
        self.nodes: list[ast.AST] = []

    def generic_visit(self, node: ast.AST) -> None:
        self.nodes.append(node)
        super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node is self.root:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node is self.root:
            self.generic_visit(node)


def _own_nodes(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.AST]:
    collector = _OwnBodyCollector(node)
    collector.visit(node)
    return collector.nodes


def _scopes(tree: ast.Module) -> list[_Scope]:
    collector = _ScopeCollector()
    collector.visit(tree)
    return collector.scopes


def _import_aliases(nodes: list[ast.AST]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in nodes:
        if isinstance(node, ast.ImportFrom) and node.module:
            for item in node.names:
                aliases[item.asname or item.name] = f"{node.module}.{item.name}"
        elif isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = item.name
    return aliases


def _identity(  # noqa: C901 - closed AST expression grammar is clearer together
    expression: ast.AST,
    aliases: dict[str, str],
) -> str | None:
    if isinstance(expression, ast.Name):
        return aliases.get(expression.id, expression.id)
    if isinstance(expression, ast.Attribute):
        base = _identity(expression.value, aliases)
        return f"{base}.{expression.attr}" if base else None
    if isinstance(expression, ast.Subscript):
        base_name = expression.value.id if isinstance(expression.value, ast.Name) else None
        try:
            key = ast.literal_eval(expression.slice)
        except (ValueError, TypeError):
            key = None
        if base_name is not None and key is not None:
            selected = aliases.get(f"{base_name}[{key!r}]")
            if selected:
                return selected
        if base_name is not None and key is None:
            hosted_member = aliases.get(f"{base_name}[*]")
            if hosted_member:
                return hosted_member
        base = _identity(expression.value, aliases)
        if base and base.startswith(HOSTED_OBJECT_PREFIXES):
            return f"{base}.<dynamic>"
        return None
    if isinstance(expression, ast.Call):
        if (
            isinstance(expression.func, ast.Name)
            and expression.func.id == "getattr"
            and len(expression.args) >= 2
        ):
            base = _identity(expression.args[0], aliases)
            attribute = expression.args[1]
            if base and isinstance(attribute, ast.Constant) and isinstance(attribute.value, str):
                return f"{base}.{attribute.value}"
            if base and base.startswith(HOSTED_OBJECT_PREFIXES):
                return f"{base}.<dynamic>"
            return None
        callable_identity = _identity(expression.func, aliases)
        if callable_identity == "functools.partial" and expression.args:
            return _identity(expression.args[0], aliases)
        if callable_identity == "vars" and expression.args:
            reflected = _identity(expression.args[0], aliases)
            if reflected and reflected.startswith(HOSTED_OBJECT_PREFIXES):
                return f"{reflected}.<dynamic>"
        return callable_identity
    return None


def _bind(  # noqa: C901 - closed destructuring/container grammar is one operation
    target: ast.AST,
    value: ast.AST,
    aliases: dict[str, str],
) -> None:
    if isinstance(target, ast.Name):
        if isinstance(value, (ast.List, ast.Tuple)):
            hosted_member: str | None = None
            for index, element in enumerate(value.elts):
                resolved_element = _identity(element, aliases)
                if resolved_element:
                    aliases[f"{target.id}[{index!r}]"] = resolved_element
                    if hosted_member is None and _is_sink(resolved_element):
                        hosted_member = resolved_element
            if hosted_member is not None:
                aliases[f"{target.id}[*]"] = hosted_member
            return
        if isinstance(value, ast.Dict):
            hosted_member = None
            for key_node, value_node in zip(value.keys, value.values, strict=False):
                if key_node is None:
                    continue
                try:
                    key = ast.literal_eval(key_node)
                except (ValueError, TypeError):
                    continue
                resolved_value = _identity(value_node, aliases)
                if resolved_value:
                    aliases[f"{target.id}[{key!r}]"] = resolved_value
                    if hosted_member is None and _is_sink(resolved_value):
                        hosted_member = resolved_value
            if hosted_member is not None:
                aliases[f"{target.id}[*]"] = hosted_member
            return
        resolved = _identity(value, aliases)
        if resolved:
            aliases[target.id] = resolved
        return
    if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)):
        for target_item, value_item in zip(target.elts, value.elts, strict=False):
            _bind(target_item, value_item, aliases)


def _aliases(scope: _Scope, module_aliases: dict[str, str]) -> dict[str, str]:
    nodes = _own_nodes(scope.node)
    aliases = {**module_aliases, **_import_aliases(nodes)}
    for node in sorted(nodes, key=lambda item: getattr(item, "lineno", 0)):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                _bind(target, node.value, aliases)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            _bind(node.target, node.value, aliases)
    return aliases


def _is_sink(identity: str | None) -> bool:
    if identity is None:
        return False
    if identity in EXACT_SINKS:
        return True
    if identity.endswith(".<dynamic>") and identity.startswith(HOSTED_OBJECT_PREFIXES):
        return True
    return identity.startswith(HOSTED_OBJECT_PREFIXES) and identity.rsplit(".", 1)[-1] in (
        HOSTED_METHODS
    )


def _calls(scope: _Scope, module_aliases: dict[str, str]) -> list[tuple[ast.Call, str]]:
    aliases = _aliases(scope, module_aliases)
    result: list[tuple[ast.Call, str]] = []
    for node in _own_nodes(scope.node):
        if isinstance(node, ast.Call):
            identity = _identity(node.func, aliases)
            if identity:
                result.append((node, identity))
    return result


def _sinkful_wrappers(scopes: list[_Scope], module_aliases: dict[str, str]) -> set[str]:
    targets = {
        scope.owner: {identity for _call, identity in _calls(scope, module_aliases)}
        for scope in scopes
    }
    sinkful = {DOSSIER_ADAPTER}
    changed = True
    while changed:
        changed = False
        for owner, identities in targets.items():
            local_name = owner.rsplit(".<locals>.", 1)[-1]
            if local_name == EXECUTOR or owner in sinkful:
                continue
            if any(_is_sink(identity) or identity in sinkful for identity in identities):
                sinkful.update({owner, local_name})
                changed = True
    return sinkful


def _hosted_effect_bypasses(source: str) -> list[_Finding]:
    tree = ast.parse(source)
    scopes = _scopes(tree)
    module_aliases = _import_aliases(list(tree.body))
    sinkful = _sinkful_wrappers(scopes, module_aliases)
    findings: list[_Finding] = []
    for scope in scopes:
        local_owner = scope.owner.rsplit(".<locals>.", 1)[-1]
        for call, identity in _calls(scope, module_aliases):
            dossier_leaf = local_owner == DOSSIER_ADAPTER and identity == (
                "specify_cli.sync.dossier_pipeline.trigger_feature_dossier_sync_if_enabled"
            )
            if (
                local_owner != EXECUTOR
                and not dossier_leaf
                and (_is_sink(identity) or identity in sinkful)
            ):
                findings.append(_Finding(scope.owner, identity, call.lineno))
    return sorted(findings, key=lambda item: (item.lineno, item.owner, item.sink))


def _terminates(statements: list[ast.stmt]) -> bool:
    return bool(statements) and isinstance(statements[-1], (ast.Return, ast.Raise))


def _executor_unguarded_sinks(source: str) -> list[_Finding]:
    tree = ast.parse(source)
    scopes = _scopes(tree)
    module_aliases = _import_aliases(list(tree.body))
    executor = next(scope for scope in scopes if scope.owner == EXECUTOR)
    aliases = _aliases(executor, module_aliases)
    sinkful = _sinkful_wrappers(scopes, module_aliases)
    decision_name = executor.node.args.args[0].arg
    guarded = False
    findings: list[_Finding] = []
    for statement in executor.node.body:
        if isinstance(statement, ast.If) and isinstance(statement.test, ast.UnaryOp):
            call = statement.test.operand
            identity = _identity(call.func, aliases) if isinstance(call, ast.Call) else None
            if (
                isinstance(statement.test.op, ast.Not)
                and identity in {VALIDATOR, VALIDATOR_IDENTITY}
                and isinstance(call, ast.Call)
                and len(call.args) == 1
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id == decision_name
                and _terminates(statement.body)
            ):
                guarded = True
                continue
        for node in ast.walk(statement):
            if isinstance(node, ast.Call):
                identity = _identity(node.func, aliases)
                if (_is_sink(identity) or identity in sinkful) and not guarded:
                    findings.append(_Finding(EXECUTOR, identity or "<unknown>", node.lineno))
    return findings


def test_production_has_one_dominated_hosted_authority() -> None:
    source = SETUP_PLAN.read_text(encoding="utf-8")
    assert _hosted_effect_bypasses(source) == []
    assert _executor_unguarded_sinks(source) == []


@pytest.mark.parametrize(
    "body",
    [
        "from specify_cli.status.lifecycle_events import fanout_lifecycle_event_hosted as emit\nemit({})",
        "_trigger_dossier_sync(None, 'm', None)",
        "import specify_cli.auth.transport as transport\ngetattr(transport, name)()",
        "from specify_cli.sync.queue import OfflineQueue\nqueue = OfflineQueue()\nqueue.queue_event({})",
        "import specify_cli.auth.transport as transport\nclient, spare = transport.get_client, object\nclient()",
    ],
)
def test_gate_rejects_provenance_preserving_indirection(body: str) -> None:
    source = "def bypass():\n" + "\n".join(f"    {line}" for line in body.splitlines())
    assert _hosted_effect_bypasses(source)


@pytest.mark.parametrize(
    "body",
    [
        (
            "from specify_cli.auth.transport import get_client\n"
            "handlers = [get_client]\nhandlers[0]()"
        ),
        (
            "from specify_cli.sync.dossier_pipeline import "
            "trigger_feature_dossier_sync_if_enabled as sync\n"
            "handlers = {'dossier': sync}\nhandlers['dossier']()"
        ),
        (
            "from functools import partial\n"
            "from specify_cli.status.lifecycle_events import "
            "fanout_lifecycle_event_hosted\n"
            "publish = partial(fanout_lifecycle_event_hosted, {})\npublish()"
        ),
    ],
)
def test_gate_rejects_container_and_partial_hosted_indirection(body: str) -> None:
    source = "def bypass():\n" + "\n".join(f"    {line}" for line in body.splitlines())
    assert _hosted_effect_bypasses(source)


def test_gate_rejects_nested_local_callable_with_qualified_owner() -> None:
    source = """
def outer():
    def publish():
        from specify_cli.auth.transport import get_client
        get_client()
"""
    assert _hosted_effect_bypasses(source) == [
        _Finding("outer.<locals>.publish", "specify_cli.auth.transport.get_client", 5)
    ]


def test_gate_rejects_transitive_wrapper_and_pre_guard_sink() -> None:
    wrapper = """
def wrapper():
    from specify_cli.status.lifecycle_events import fanout_lifecycle_event_hosted
    fanout_lifecycle_event_hosted({})
def bypass():
    wrapper()
"""
    assert any(item.owner == "bypass" for item in _hosted_effect_bypasses(wrapper))

    dominance = f"""
def {DOSSIER_ADAPTER}():
    from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
    trigger_feature_dossier_sync_if_enabled()
def {EXECUTOR}(decision):
    {DOSSIER_ADAPTER}()
    if not {VALIDATOR}(decision):
        return
"""
    assert _executor_unguarded_sinks(dominance)


def test_gate_avoids_unrelated_name_false_positives() -> None:
    source = """
def get_client():
    return None
def harmless(queue):
    enqueue = queue.enqueue
    get_client()
    enqueue({})
    getattr(queue, dynamic_name)()
"""
    assert _hosted_effect_bypasses(source) == []


def test_gate_avoids_unrelated_container_and_partial_false_positives() -> None:
    source = """
from functools import partial

def local_callback():
    return None

def harmless():
    callbacks = [local_callback]
    mapping = {"local": local_callback}
    callbacks[0]()
    mapping["local"]()
    partial(local_callback)()
"""
    assert _hosted_effect_bypasses(source) == []


def test_gate_rejects_dynamic_subscript_on_container_with_hosted_member() -> None:
    source = """
from specify_cli.auth.transport import get_client

def bypass(key):
    handlers = {"hosted": get_client}
    handlers[key]()
"""
    assert _hosted_effect_bypasses(source)


def test_gate_allows_dynamic_subscript_on_unrelated_container() -> None:
    source = """
def local_callback():
    return None

def harmless(key):
    handlers = {"local": local_callback}
    handlers[key]()
"""
    assert _hosted_effect_bypasses(source) == []


def test_gate_rejects_vars_reflection_on_hosted_module() -> None:
    source = """
import specify_cli.auth.transport as hosted_module

def bypass(key):
    vars(hosted_module)[key]()
"""
    assert _hosted_effect_bypasses(source)


def test_gate_allows_vars_reflection_on_unrelated_object() -> None:
    source = """
class LocalCallbacks:
    pass

def harmless(callbacks, key):
    vars(callbacks)[key]()
"""
    assert _hosted_effect_bypasses(source) == []


def test_production_finalizer_routes_through_executor_without_becoming_a_sink() -> None:
    source = SETUP_PLAN.read_text(encoding="utf-8")
    tree = ast.parse(source)
    scopes = _scopes(tree)
    module_aliases = _import_aliases(list(tree.body))
    finalizer = next(scope for scope in scopes if scope.owner == "_finalize_setup_plan_outcome")
    assert [identity for _call, identity in _calls(finalizer, module_aliases)].count(EXECUTOR) == 1
    assert not [
        finding
        for finding in _hosted_effect_bypasses(source)
        if finding.owner == "_finalize_setup_plan_outcome"
    ]


def test_gate_accepts_sink_after_terminal_identity_guard() -> None:
    source = f"""
def {DOSSIER_ADAPTER}():
    from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
    trigger_feature_dossier_sync_if_enabled()
def {EXECUTOR}(decision):
    if not {VALIDATOR}(decision):
        return
    {DOSSIER_ADAPTER}()
"""
    assert _executor_unguarded_sinks(source) == []
