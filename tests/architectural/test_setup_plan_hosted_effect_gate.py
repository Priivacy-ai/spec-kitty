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
AUTHORIZED_HOSTED_IMPORTS = frozenset(
    {
        ("specify_cli.status.lifecycle_events", "fanout_lifecycle_event_hosted"),
        (
            "specify_cli.sync.dossier_pipeline",
            "trigger_feature_dossier_sync_if_enabled",
        ),
    }
)
REFLECTION_SELECTORS = frozenset(
    {
        "eval",
        "exec",
        "getattr",
        "globals",
        "import_module",
        "locals",
        "vars",
        "__import__",
        "__dict__",
        "getitem",
    }
)


@dataclass(frozen=True)
class _Edge:
    kind: str
    value: str
    lineno: int


@dataclass(frozen=True)
class _SinkUse:
    """One selection or escape of a physical hosted callable."""

    sink: str
    kind: str
    function: str | None
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
            edges.extend(_Edge("import", f"{node.module}.{item.name}", node.lineno) for item in node.names if item.name in HOSTED_NAMES or item.name == "*")
        elif isinstance(node, ast.Import):
            edges.extend(_Edge("import", item.name, node.lineno) for item in node.names if item.name in HOSTED_MODULES)
        elif isinstance(node, ast.Name) and node.id in HOSTED_NAMES:
            edges.append(_Edge("name", node.id, node.lineno))
        elif isinstance(node, ast.Attribute) and node.attr in HOSTED_NAMES:
            edges.append(_Edge("name", node.attr, node.lineno))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in HOSTED_MODULES:
            edges.append(_Edge("dynamic-import", node.value, node.lineno))
    return sorted(set(edges), key=lambda item: (item.lineno, item.kind, item.value))


def _setup_plan_production_files() -> tuple[Path, ...]:
    return tuple(sorted(AGENT_COMMANDS.glob("*setup_plan*.py")))


def _functions(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(source)
    return {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _enclosing_function(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current
        current = parents.get(current)
    return None


def _outer_attribute(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST:
    current = node
    while isinstance(parents.get(current), ast.Attribute):
        current = parents[current]
    return current


def _hosted_import_census(
    tree: ast.AST,
) -> tuple[dict[str, str], dict[str, str], list[_Edge]]:
    """Enforce the boundary's two exact, unaliased physical imports."""
    sink_bindings: dict[str, str] = {}
    module_bindings: dict[str, str] = {}
    violations: list[_Edge] = []
    authorized_import_counts = dict.fromkeys(AUTHORIZED_HOSTED_IMPORTS, 0)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in HOSTED_MODULES:
            for item in node.names:
                qualified = (node.module, item.name)
                if qualified not in AUTHORIZED_HOSTED_IMPORTS:
                    violations.append(
                        _Edge(
                            "unauthorized-hosted-import",
                            f"{node.module}.{item.name}",
                            node.lineno,
                        )
                    )
                elif item.asname is not None:
                    violations.append(
                        _Edge(
                            "aliased-hosted-import",
                            f"{node.module}.{item.name} as {item.asname}",
                            node.lineno,
                        )
                    )
                else:
                    authorized_import_counts[qualified] += 1
                    sink_bindings[item.name] = item.name
        elif isinstance(node, ast.Import):
            for item in node.names:
                if item.name in HOSTED_MODULES:
                    violations.append(_Edge("hosted-module-import", item.name, node.lineno))
                    module_bindings[item.asname or item.name.split(".", 1)[0]] = item.name
        elif (
            isinstance(node, ast.Call)
            and _qualified_name(node.func) in {"__import__", "importlib.import_module"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in HOSTED_MODULES
        ):
            violations.append(_Edge("dynamic-import", str(node.args[0].value), node.lineno))

    for qualified, count in authorized_import_counts.items():
        if count != 1:
            violations.append(
                _Edge(
                    "authorized-import-count",
                    f"{qualified[0]}.{qualified[1]}={count}",
                    0,
                )
            )
    return sink_bindings, module_bindings, violations


def _physical_sink_census(source: str) -> tuple[list[_SinkUse], list[_Edge]]:
    """Census every hosted binding selection, including pre-call escapes.

    This deliberately does not try to predict every eventual Python call shape.
    Instead it follows the capability: a physical sink binding may only be
    selected as the immediate callee.  Assignment, return, containers,
    ``partial``, and reflection all first *load* or dynamically import that
    capability and are rejected before alias propagation becomes relevant.
    """
    tree = ast.parse(source)
    parents = _parent_map(tree)
    sink_bindings, module_bindings, violations = _hosted_import_census(tree)

    uses: list[_SinkUse] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
            continue
        function = _enclosing_function(node, parents)
        function_name = function.name if function is not None else None
        parent = parents.get(node)

        if node.id in sink_bindings:
            immediate_call = isinstance(parent, ast.Call) and parent.func is node
            uses.append(
                _SinkUse(
                    sink=sink_bindings[node.id],
                    kind="direct-call" if immediate_call else "escape",
                    function=function_name,
                    lineno=node.lineno,
                )
            )
            continue

        if node.id not in module_bindings:
            continue
        outer = _outer_attribute(node, parents)
        outer_parent = parents.get(outer)
        sink = outer.attr if isinstance(outer, ast.Attribute) else module_bindings[node.id]
        immediate_call = isinstance(outer, ast.Attribute) and sink in HOSTED_NAMES and isinstance(outer_parent, ast.Call) and outer_parent.func is outer
        uses.append(
            _SinkUse(
                sink=sink,
                kind="direct-call" if immediate_call else "escape",
                function=function_name,
                lineno=node.lineno,
            )
        )

    return (
        sorted(uses, key=lambda item: (item.lineno, item.sink, item.kind)),
        sorted(set(violations), key=lambda item: (item.lineno, item.kind, item.value)),
    )


def _reflection_edges(source: str) -> list[_Edge]:
    """Reject dynamic namespace selectors from the deliberately closed boundary."""
    tree = ast.parse(source)
    edges: list[_Edge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in REFLECTION_SELECTORS:
            edges.append(_Edge("boundary-reflection", node.id, node.lineno))
        elif isinstance(node, ast.Attribute) and (node.attr in REFLECTION_SELECTORS or _qualified_name(node) == "sys.modules"):
            edges.append(
                _Edge(
                    "boundary-reflection",
                    _qualified_name(node) or node.attr,
                    node.lineno,
                )
            )
        elif isinstance(node, ast.ImportFrom) and node.module in {
            "builtins",
            "operator",
            "importlib",
        }:
            edges.extend(
                _Edge(
                    "boundary-reflection-import",
                    f"{node.module}.{item.name}",
                    node.lineno,
                )
                for item in node.names
                if item.name in REFLECTION_SELECTORS
            )
    return sorted(set(edges), key=lambda item: (item.lineno, item.kind, item.value))


def _first_executable_statement(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.stmt:
    statements = function.body
    if statements and isinstance(statements[0], ast.Expr) and isinstance(statements[0].value, ast.Constant) and isinstance(statements[0].value.value, str):
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


def _boundary_violations(source: str) -> list[_Edge]:
    """Return unguarded selections and all sink capability escapes."""
    functions = _functions(source)
    uses, violations = _physical_sink_census(source)
    violations.extend(_reflection_edges(source))
    for use in uses:
        if use.kind != "direct-call":
            violations.append(_Edge("sink-escape", use.sink, use.lineno))
            continue
        function = functions.get(use.function or "")
        if function is None or not _has_terminal_identity_guard(function):
            violations.append(_Edge("unguarded-sink", use.sink, use.lineno))
    return sorted(set(violations), key=lambda item: (item.lineno, item.kind, item.value))


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
    imports = [item.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == BOUNDARY_MODULE for item in node.names]
    assert imports == [EXECUTOR]

    functions = _functions(CALLER.read_text(encoding="utf-8"))
    finalizer = functions["_finalize_setup_plan_outcome"]
    executor_calls = [
        node for node in ast.walk(finalizer) if isinstance(node, ast.Call) and (_qualified_name(node.func) or "").rsplit(".", 1)[-1] in {EXECUTOR, f"_{EXECUTOR}"}
    ]
    assert len(executor_calls) == 1


def test_every_physical_sink_is_locally_dominated_by_identity_guard() -> None:
    source = BOUNDARY.read_text(encoding="utf-8")
    uses, census_violations = _physical_sink_census(source)
    sink_owners: dict[str, set[str]] = {}
    for use in uses:
        if use.function is not None:
            sink_owners.setdefault(use.function, set()).add(use.sink)
    assert census_violations == []
    assert sink_owners == {
        "_trigger_dossier_sync": {"trigger_feature_dossier_sync_if_enabled"},
        EXECUTOR: {"fanout_lifecycle_event_hosted"},
    }
    assert _boundary_violations(source) == []


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
    missing = ast.parse("def execute(decision):\n    fanout_lifecycle_event_hosted({})\n").body[0]
    late = ast.parse(
        "def execute(decision):\n    fanout_lifecycle_event_hosted({})\n    if not is_canonical_hosted_sync_decision(decision):\n        return\n"
    ).body[0]
    assert isinstance(missing, ast.FunctionDef)
    assert isinstance(late, ast.FunctionDef)
    assert not _has_terminal_identity_guard(missing)
    assert not _has_terminal_identity_guard(late)


@pytest.mark.parametrize(
    ("expected_kind", "mutation"),
    [
        (
            "unguarded-sink",
            "\ndef hostile(decision):\n    fanout_lifecycle_event_hosted({})\n",
        ),
        (
            "sink-escape",
            "\ndef hostile(decision):\n"
            "    if not is_canonical_hosted_sync_decision(decision):\n        return\n"
            "    emit = fanout_lifecycle_event_hosted\n    emit({})\n",
        ),
        (
            "sink-escape",
            "\ndef hostile(decision):\n"
            "    if not is_canonical_hosted_sync_decision(decision):\n        return\n"
            "    handlers = [fanout_lifecycle_event_hosted]\n    handlers[0]({})\n",
        ),
        (
            "sink-escape",
            "\nfrom functools import partial\n"
            "def hostile(decision):\n"
            "    if not is_canonical_hosted_sync_decision(decision):\n        return\n"
            "    emit = partial(fanout_lifecycle_event_hosted, {})\n    emit()\n",
        ),
        (
            "sink-escape",
            "\ndef hostile(decision):\n    if not is_canonical_hosted_sync_decision(decision):\n        return\n    return fanout_lifecycle_event_hosted\n",
        ),
        (
            "dynamic-import",
            "\ndef hostile(decision, name):\n"
            "    if not is_canonical_hosted_sync_decision(decision):\n        return\n"
            "    module = __import__('specify_cli.sync.events', fromlist=['*'])\n"
            "    getattr(module, name)({})\n",
        ),
        (
            "sink-escape",
            "\nimport specify_cli.auth.transport as hostile_transport\n"
            "def hostile(decision, name):\n"
            "    if not is_canonical_hosted_sync_decision(decision):\n        return\n"
            "    vars(hostile_transport).get(name)()\n",
        ),
        (
            "boundary-reflection",
            "\ndef hostile(decision):\n"
            "    if not is_canonical_hosted_sync_decision(decision):\n        return\n"
            '    globals()["fanout_lifecycle_event_hosted"]({})\n',
        ),
        (
            "boundary-reflection",
            "\nimport sys\n"
            "def hostile(decision):\n"
            "    if not is_canonical_hosted_sync_decision(decision):\n        return\n"
            "    getattr(sys.modules[__name__], "
            '"fanout_lifecycle_event_hosted")({})\n',
        ),
        (
            "aliased-hosted-import",
            "\nfrom specify_cli.status.lifecycle_events import fanout_lifecycle_event_hosted as emit\n",
        ),
        (
            "unauthorized-hosted-import",
            "\nfrom specify_cli.auth.transport import get_client\n",
        ),
    ],
)
def test_boundary_census_rejects_hostile_internal_mutations(
    expected_kind: str,
    mutation: str,
) -> None:
    source = BOUNDARY.read_text(encoding="utf-8") + mutation
    assert expected_kind in {finding.kind for finding in _boundary_violations(source)}
