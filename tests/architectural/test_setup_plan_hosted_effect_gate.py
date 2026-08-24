"""Structural boundary gate for setup-plan hosted effects.

The primary proof is an import/name edge: among setup-plan production modules,
only ``setup_plan_hosted_effects.py`` may know a physical hosted sink. The
command module receives inert local intents and calls one narrow executor.
Within the boundary, every sink-owning function has a terminal exact-identity
guard before its first sink.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

ROOT = Path(__file__).resolve().parents[2]
AGENT_COMMANDS = ROOT / "src/specify_cli/cli/commands/agent"
CALLER = AGENT_COMMANDS / "mission_setup_plan.py"
BOUNDARY = AGENT_COMMANDS / "setup_plan_hosted_effects.py"
BOUNDARY_MODULE = "specify_cli.cli.commands.agent.setup_plan_hosted_effects"
EXECUTOR = "execute_setup_plan_hosted_effects"
VALIDATOR = "is_canonical_hosted_sync_decision"

HOSTED_MODULES = frozenset(
    {
        "specify_cli.status.lifecycle_events",
        "specify_cli.sync.dossier_pipeline",
        "specify_cli.sync.queue",
        "specify_cli.sync.body_queue",
        "specify_cli.sync.events",
        "specify_cli.auth.transport",
    }
)
HOSTED_NAMES = frozenset(
    {
        "fanout_lifecycle_event_hosted",
        "trigger_feature_dossier_sync_if_enabled",
        "OfflineQueue",
        "OfflineBodyUploadQueue",
        "_request_dashboard_sync",
        "_publish_event_via_sync_daemon",
        "get_client",
        "get_async_client",
    }
)


@dataclass(frozen=True)
class _Edge:
    kind: str
    value: str
    lineno: int


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _qualified_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _forbidden_edges(source: str) -> list[_Edge]:
    """Return physical hosted import/name edges without tracing call shapes."""
    tree = ast.parse(source)
    edges: list[_Edge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in HOSTED_MODULES:
            edges.extend(
                _Edge("import", f"{node.module}.{item.name}", node.lineno)
                for item in node.names
                if item.name in HOSTED_NAMES or item.name == "*"
            )
        elif isinstance(node, ast.Import):
            edges.extend(
                _Edge("import", item.name, node.lineno)
                for item in node.names
                if item.name in HOSTED_MODULES
            )
        elif isinstance(node, ast.Name) and node.id in HOSTED_NAMES:
            edges.append(_Edge("name", node.id, node.lineno))
        elif isinstance(node, ast.Attribute) and node.attr in HOSTED_NAMES:
            edges.append(_Edge("name", node.attr, node.lineno))
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in HOSTED_MODULES
        ):
            edges.append(_Edge("dynamic-import", node.value, node.lineno))
    return sorted(set(edges), key=lambda item: (item.lineno, item.kind, item.value))


def _setup_plan_production_files() -> tuple[Path, ...]:
    return tuple(sorted(AGENT_COMMANDS.glob("*setup_plan*.py")))


def _functions(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(source)
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _first_executable_statement(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.stmt:
    statements = function.body
    if (
        statements
        and isinstance(statements[0], ast.Expr)
        and isinstance(statements[0].value, ast.Constant)
        and isinstance(statements[0].value.value, str)
    ):
        statements = statements[1:]
    assert statements, f"{function.name} has no executable body"
    return statements[0]


def _has_terminal_identity_guard(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    decision_names = {argument.arg for argument in function.args.args}
    statement = _first_executable_statement(function)
    if not isinstance(statement, ast.If) or not isinstance(statement.test, ast.UnaryOp):
        return False
    call = statement.test.operand
    return (
        isinstance(statement.test.op, ast.Not)
        and isinstance(call, ast.Call)
        and _qualified_name(call.func) == VALIDATOR
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id in decision_names
        and bool(statement.body)
        and isinstance(statement.body[-1], (ast.Return, ast.Raise))
    )


def _direct_sink_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {
        name
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and (name := (_qualified_name(node.func) or "").rsplit(".", 1)[-1])
        in HOSTED_NAMES
    }


def test_setup_plan_physical_sinks_are_isolated_to_one_module() -> None:
    files = _setup_plan_production_files()
    assert CALLER in files and BOUNDARY in files
    findings: dict[str, list[_Edge]] = {}
    for path in files:
        if path == BOUNDARY:
            continue
        edges = _forbidden_edges(path.read_text(encoding="utf-8"))
        if edges:
            findings[path.relative_to(ROOT).as_posix()] = edges
    assert findings == {}


def test_command_imports_only_the_narrow_executor_from_boundary() -> None:
    tree = ast.parse(CALLER.read_text(encoding="utf-8"))
    imports = [
        item.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == BOUNDARY_MODULE
        for item in node.names
    ]
    assert imports == [EXECUTOR]

    functions = _functions(CALLER.read_text(encoding="utf-8"))
    finalizer = functions["_finalize_setup_plan_outcome"]
    executor_calls = [
        node
        for node in ast.walk(finalizer)
        if isinstance(node, ast.Call)
        and (_qualified_name(node.func) or "").rsplit(".", 1)[-1]
        in {EXECUTOR, f"_{EXECUTOR}"}
    ]
    assert len(executor_calls) == 1


def test_every_physical_sink_is_locally_dominated_by_identity_guard() -> None:
    source = BOUNDARY.read_text(encoding="utf-8")
    functions = _functions(source)
    sink_owners = {
        name: sinks
        for name, function in functions.items()
        if (sinks := _direct_sink_names(function))
    }
    assert sink_owners == {
        "_trigger_dossier_sync": {"trigger_feature_dossier_sync_if_enabled"},
        EXECUTOR: {"fanout_lifecycle_event_hosted"},
    }
    assert all(_has_terminal_identity_guard(functions[name]) for name in sink_owners)


@pytest.mark.parametrize(
    "body",
    [
        "from specify_cli.status.lifecycle_events import fanout_lifecycle_event_hosted as emit\nemit({})",
        "import specify_cli.sync.dossier_pipeline as dossier\ndossier.trigger_feature_dossier_sync_if_enabled()",
        "from specify_cli.auth.transport import get_client\nhandlers = [get_client]\nhandlers[0]()",
        "from functools import partial\nfrom specify_cli.auth.transport import get_client\npublish = partial(get_client)\npublish()",
        "import specify_cli.auth.transport as hosted\nvars(hosted).get(name)()",
        "import operator\nimport specify_cli.auth.transport as hosted\noperator.getitem(vars(hosted), name)()",
        "def nested():\n    from specify_cli.sync.queue import OfflineQueue\n    return OfflineQueue()",
        "module = __import__('specify_cli.sync.events', fromlist=['*'])\ngetattr(module, name)()",
    ],
)
def test_forbidden_edge_rejects_common_indirection_mutations(body: str) -> None:
    assert _forbidden_edges(body)


def test_forbidden_edge_avoids_unrelated_call_shape_false_positives() -> None:
    source = """
from functools import partial
import operator

def local_callback():
    return None

def harmless(callbacks, key):
    handlers = {"local": local_callback}
    vars(callbacks).get(key)
    operator.getitem(handlers, "local")()
    partial(local_callback)()
"""
    assert _forbidden_edges(source) == []


def test_missing_or_late_identity_guard_fails_dominance_oracle() -> None:
    missing = ast.parse(
        "def execute(decision):\n"
        "    fanout_lifecycle_event_hosted({})\n"
    ).body[0]
    late = ast.parse(
        "def execute(decision):\n"
        "    fanout_lifecycle_event_hosted({})\n"
        "    if not is_canonical_hosted_sync_decision(decision):\n"
        "        return\n"
    ).body[0]
    assert isinstance(missing, ast.FunctionDef)
    assert isinstance(late, ast.FunctionDef)
    assert not _has_terminal_identity_guard(missing)
    assert not _has_terminal_identity_guard(late)
