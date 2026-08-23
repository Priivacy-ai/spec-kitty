"""Non-vacuous AST recurrence gate for setup-plan hosted effects.

The gate deliberately reasons about the small amount of Python indirection used
on this command surface: import aliases, local callable aliases, ``getattr``,
and module-local wrappers. It is not a general Python call-graph engine. The
closed sink census keeps the analysis bounded and makes additions explicit.
"""

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
DECISION_VALIDATOR = "is_canonical_hosted_sync_decision"

# Final symbol/attribute names are intentional: this catches direct imports,
# module-qualified calls, queue instances, and the supported getattr shape.
HOSTED_SINKS = frozenset(
    {
        DOSSIER_ADAPTER,
        "fanout_lifecycle_event_hosted",
        "trigger_feature_dossier_sync_if_enabled",
        "OfflineQueue",
        "OfflineBodyUploadQueue",
        "queue_event",
        "enqueue",
        "queue_body_upload",
        "_request_dashboard_sync",
        "_publish_event_via_sync_daemon",
        "get_client",
        "get_async_client",
    }
)


@dataclass(frozen=True)
class _Finding:
    owner: str
    sink: str
    lineno: int


def _attribute_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ):
        return node.args[1].value
    return None


class _FunctionBodyVisitor(ast.NodeVisitor):
    """Collect nodes without attributing nested callable bodies to their owner."""

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


def _body_nodes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.AST]:
    visitor = _FunctionBodyVisitor(function)
    visitor.visit(function)
    return visitor.nodes


def _import_aliases(nodes: list[ast.AST]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in nodes:
        if isinstance(node, ast.ImportFrom):
            for imported in node.names:
                aliases[imported.asname or imported.name] = imported.name
        elif isinstance(node, ast.Import):
            for imported in node.names:
                aliases[imported.asname or imported.name.split(".")[0]] = (
                    imported.name.split(".")[-1]
                )
    return aliases


def _aliases(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    module_aliases: dict[str, str],
) -> dict[str, str]:
    """Resolve the supported simple callable-alias forms in one function."""
    nodes = _body_nodes(function)
    raw = {**module_aliases, **_import_aliases(nodes)}
    for node in sorted(nodes, key=lambda item: getattr(item, "lineno", 0)):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if value is None:
            continue
        name = _attribute_name(value)
        if name is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                raw[target.id] = name

    def resolve(name: str) -> str:
        seen: set[str] = set()
        while name in raw and name not in seen:
            seen.add(name)
            candidate = raw[name]
            if candidate == name:
                break
            name = candidate
        return name

    return {name: resolve(name) for name in raw}


def _call_target(call: ast.Call, aliases: dict[str, str]) -> str | None:
    name = _attribute_name(call.func)
    if name is None:
        return None
    return aliases.get(name, name)


def _function_calls(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    module_aliases: dict[str, str],
) -> list[tuple[ast.Call, str]]:
    aliases = _aliases(function, module_aliases)
    calls: list[tuple[ast.Call, str]] = []
    for node in _body_nodes(function):
        if isinstance(node, ast.Call):
            target = _call_target(node, aliases)
            if target is not None:
                calls.append((node, target))
    return calls


def _module_functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _sinkful_functions(
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    module_aliases: dict[str, str],
) -> set[str]:
    """Close module-local wrappers transitively over the sink census."""
    sinkful: set[str] = {DOSSIER_ADAPTER}
    targets_by_function = {
        name: {
            target
            for _call, target in _function_calls(function, module_aliases)
            if target != EXECUTOR
        }
        for name, function in functions.items()
    }
    changed = True
    while changed:
        changed = False
        for name in functions:
            if name == EXECUTOR or name in sinkful:
                continue
            targets = targets_by_function[name]
            if targets & (HOSTED_SINKS | sinkful):
                sinkful.add(name)
                changed = True
    return sinkful


def _hosted_effect_bypasses(source: str) -> list[_Finding]:
    """Return hosted calls reachable outside the one executor."""
    tree = ast.parse(source)
    functions = _module_functions(tree)
    module_aliases = _import_aliases(list(tree.body))
    sinkful = _sinkful_functions(functions, module_aliases)
    bypasses: list[_Finding] = []
    for owner, function in functions.items():
        for call, target in _function_calls(function, module_aliases):
            is_sink = target in HOSTED_SINKS or target in sinkful
            dossier_leaf = owner == DOSSIER_ADAPTER and target == (
                "trigger_feature_dossier_sync_if_enabled"
            )
            if is_sink and owner != EXECUTOR and not dossier_leaf:
                bypasses.append(_Finding(owner, target, call.lineno))
    return sorted(bypasses, key=lambda finding: (finding.lineno, finding.owner, finding.sink))


def _terminates(statements: list[ast.stmt]) -> bool:
    return bool(statements) and isinstance(statements[-1], (ast.Return, ast.Raise))


def _is_rejecting_identity_guard(test: ast.AST, decision_name: str, aliases: dict[str, str]) -> bool:
    if not isinstance(test, ast.UnaryOp) or not isinstance(test.op, ast.Not):
        return False
    call = test.operand
    if not isinstance(call, ast.Call) or _call_target(call, aliases) != DECISION_VALIDATOR:
        return False
    return (
        len(call.args) == 1
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == decision_name
    )


def _executor_unguarded_sinks(source: str) -> list[_Finding]:
    """Conservatively prove a fail-closed identity guard dominates each sink."""
    tree = ast.parse(source)
    functions = _module_functions(tree)
    module_aliases = _import_aliases(list(tree.body))
    executor = functions[EXECUTOR]
    aliases = _aliases(executor, module_aliases)
    sinkful = _sinkful_functions(functions, module_aliases)
    decision_name = executor.args.args[0].arg
    findings: list[_Finding] = []

    def visit_statements(statements: list[ast.stmt], guarded: bool) -> bool:
        current_guarded = guarded
        for statement in statements:
            if (
                isinstance(statement, ast.If)
                and _is_rejecting_identity_guard(statement.test, decision_name, aliases)
                and _terminates(statement.body)
            ):
                visit_statements(statement.body, current_guarded)
                visit_statements(statement.orelse, current_guarded)
                current_guarded = True
                continue

            for node in ast.walk(statement):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not isinstance(node, ast.Call):
                    continue
                target = _call_target(node, aliases)
                if (target in HOSTED_SINKS or target in sinkful) and not current_guarded:
                    findings.append(_Finding(EXECUTOR, target or "<unknown>", node.lineno))
        return current_guarded

    visit_statements(executor.body, False)
    return sorted(findings, key=lambda finding: (finding.lineno, finding.sink))


def test_setup_plan_hosted_effects_have_one_dominated_authority() -> None:
    source = SETUP_PLAN.read_text(encoding="utf-8")
    assert _hosted_effect_bypasses(source) == []
    assert _executor_unguarded_sinks(source) == []


@pytest.mark.parametrize(
    ("body", "expected_sink"),
    [
        ("fan = fanout_lifecycle_event_hosted\nfan({})", "fanout_lifecycle_event_hosted"),
        ("_trigger_dossier_sync(None, 'm', None)", DOSSIER_ADAPTER),
        (
            "getattr(events, 'fanout_lifecycle_event_hosted')({})",
            "fanout_lifecycle_event_hosted",
        ),
        ("queue_type = OfflineQueue\nqueue = queue_type()\nqueue.queue_event({})", "OfflineQueue"),
        ("client_factory = transport.get_client\nclient_factory()", "get_client"),
    ],
)
def test_gate_rejects_alias_adapter_queue_and_transport_bypasses(
    body: str,
    expected_sink: str,
) -> None:
    source = "def bypass():\n" + "\n".join(f"    {line}" for line in body.splitlines())
    findings = _hosted_effect_bypasses(source)
    assert any(finding.owner == "bypass" and finding.sink == expected_sink for finding in findings)


def test_gate_rejects_renamed_direct_import() -> None:
    source = """
from specify_cli.status.lifecycle_events import fanout_lifecycle_event_hosted as publish

def bypass():
    publish({})
"""
    assert _hosted_effect_bypasses(source) == [
        _Finding("bypass", "fanout_lifecycle_event_hosted", 5)
    ]


def test_gate_rejects_transitive_wrapper_bypass() -> None:
    source = """
def wrapper():
    fanout_lifecycle_event_hosted({})

def bypass():
    relay = wrapper
    relay()
"""
    findings = _hosted_effect_bypasses(source)
    assert any(finding.owner == "bypass" and finding.sink == "wrapper" for finding in findings)


def test_gate_rejects_sink_moved_before_identity_guard() -> None:
    source = f"""
def {DOSSIER_ADAPTER}():
    trigger_feature_dossier_sync_if_enabled()

def {EXECUTOR}(decision):
    {DOSSIER_ADAPTER}()
    if not {DECISION_VALIDATOR}(decision):
        return
"""
    assert _executor_unguarded_sinks(source) == [
        _Finding(EXECUTOR, DOSSIER_ADAPTER, 6)
    ]


def test_gate_accepts_sink_after_terminal_identity_guard() -> None:
    source = f"""
def {DOSSIER_ADAPTER}():
    trigger_feature_dossier_sync_if_enabled()

def {EXECUTOR}(decision):
    if not {DECISION_VALIDATOR}(decision):
        return
    {DOSSIER_ADAPTER}()
"""
    assert _executor_unguarded_sinks(source) == []
