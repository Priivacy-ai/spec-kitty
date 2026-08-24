"""Structural boundary gate for setup-plan hosted effects.

The primary proof is a package-wide physical import inventory: every hosted
sink import in ``cli.commands.agent`` has an explicit owning module, and only
``setup_plan_hosted_effects.py`` is authorized for setup-plan. This prevents a
differently named helper from hiding outside a filename glob. The command
module receives inert local intents and calls one narrow executor. Within the
boundary, every sink-owning function has a terminal exact-identity guard before
its first sink.
"""

from __future__ import annotations

import ast
from collections import Counter
from collections.abc import Mapping
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
# Physical hosted imports outside setup-plan predate this mission and remain
# explicit exceptions. A new agent-command helper gets no authority merely by
# choosing a filename that omits ``setup_plan``.
PACKAGE_HOSTED_IMPORT_ALLOWLIST: Mapping[str, frozenset[tuple[str, str]]] = {
    "setup_plan_hosted_effects.py": AUTHORIZED_HOSTED_IMPORTS,
    "mission_finalize.py": frozenset(
        {
            (
                "specify_cli.sync.dossier_pipeline",
                "trigger_feature_dossier_sync_if_enabled",
            )
        }
    ),
    "mission_record_analysis.py": frozenset(
        {
            (
                "specify_cli.sync.dossier_pipeline",
                "trigger_feature_dossier_sync_if_enabled",
            )
        }
    ),
    "tasks_mark_status.py": frozenset(
        {
            (
                "specify_cli.sync.dossier_pipeline",
                "trigger_feature_dossier_sync_if_enabled",
            )
        }
    ),
    "workflow_executor.py": frozenset(
        {
            (
                "specify_cli.sync.dossier_pipeline",
                "trigger_feature_dossier_sync_if_enabled",
            )
        }
    ),
}
SINK_OWNERS = frozenset({"_trigger_dossier_sync", EXECUTOR})
PROTOCOL_METHODS = {
    "_LifecycleEventIntent": frozenset({"envelope", "log_path"}),
    "_DossierSyncIntent": frozenset({"feature_dir", "mission_slug", "repo_root"}),
}


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
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            edges.extend(_Edge("import", f"{node.module}.{item.name}", node.lineno) for item in node.names if f"{node.module}.{item.name}" in HOSTED_MODULES)
        elif isinstance(node, ast.Name) and node.id in HOSTED_NAMES:
            edges.append(_Edge("name", node.id, node.lineno))
        elif isinstance(node, ast.Attribute) and node.attr in HOSTED_NAMES:
            edges.append(_Edge("name", node.attr, node.lineno))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in HOSTED_MODULES:
            edges.append(_Edge("dynamic-import", node.value, node.lineno))
    return sorted(set(edges), key=lambda item: (item.lineno, item.kind, item.value))


def _physical_hosted_import_edges(source: str) -> list[_Edge]:
    """Return imports that grant access to a physical hosted sink.

    Importing other symbols from a mixed module such as ``sync.events`` or
    ``lifecycle_events`` is intentionally not a finding. Importing an entire
    hosted module, a star, an alias, or a dynamic module is never allowlisted.
    """
    tree = ast.parse(source)
    edges: list[_Edge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in HOSTED_MODULES:
            for item in node.names:
                if item.name not in HOSTED_NAMES and item.name != "*":
                    continue
                value = f"{node.module}.{item.name}"
                if item.asname is not None:
                    value = f"{value} as {item.asname}"
                edges.append(_Edge("from-import", value, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            for item in node.names:
                qualified = f"{node.module}.{item.name}"
                if qualified not in HOSTED_MODULES:
                    continue
                value = f"{qualified}.*"
                if item.asname is not None:
                    value = f"{value} as {item.asname}"
                edges.append(_Edge("module-import", value, node.lineno))
        elif isinstance(node, ast.Import):
            for item in node.names:
                if item.name in HOSTED_MODULES:
                    value = f"{item.name}.*"
                    if item.asname is not None:
                        value = f"{value} as {item.asname}"
                    edges.append(_Edge("module-import", value, node.lineno))
        elif (
            isinstance(node, ast.Call)
            and _qualified_name(node.func) in {"__import__", "importlib.import_module"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in HOSTED_MODULES
        ):
            edges.append(_Edge("dynamic-import", str(node.args[0].value), node.lineno))
    return sorted(edges, key=lambda item: (item.lineno, item.kind, item.value))


def _agent_production_sources() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(AGENT_COMMANDS.glob("*.py"))}


def _package_hosted_import_findings(
    sources: Mapping[str, str],
) -> dict[str, list[_Edge]]:
    """Compare every agent-command module with the exact import allowlist."""
    findings: dict[str, list[_Edge]] = {}
    for filename, source in sources.items():
        edges = _physical_hosted_import_edges(source)
        actual = Counter((edge.kind, edge.value) for edge in edges)
        expected = Counter(("from-import", f"{module}.{name}") for module, name in PACKAGE_HOSTED_IMPORT_ALLOWLIST.get(filename, frozenset()))
        if actual != expected:
            findings[filename] = edges
    return findings


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


def _body_without_docstring(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.stmt]:
    body = function.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def _statement_shape(statements: list[ast.stmt]) -> str:
    return ast.dump(ast.Module(body=statements, type_ignores=[]), include_attributes=False)


EXPECTED_SINK_OWNER_BODIES = {
    "_trigger_dossier_sync": _statement_shape(
        ast.parse(
            "if not is_canonical_hosted_sync_decision(decision):\n"
            "    return\n"
            "trigger_feature_dossier_sync_if_enabled(\n"
            "    intent.feature_dir, intent.mission_slug, intent.repo_root\n"
            ")\n"
        ).body
    ),
    EXECUTOR: _statement_shape(
        ast.parse(
            "if not is_canonical_hosted_sync_decision(decision):\n"
            "    return\n"
            "for intent in lifecycle_intents:\n"
            "    fanout_lifecycle_event_hosted(\n"
            "        intent.envelope, log_path=intent.log_path\n"
            "    )\n"
            "if dossier_intent is not None:\n"
            "    _trigger_dossier_sync(decision, dossier_intent)\n"
        ).body
    ),
}


def _definition_preamble_has_call(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Detect decorators/defaults/annotations evaluated before a function guard."""
    expressions: list[ast.AST] = [*function.decorator_list, *function.args.defaults]
    expressions.extend(default for default in function.args.kw_defaults if default is not None)
    expressions.extend(
        annotation
        for annotation in (
            function.returns,
            *(argument.annotation for argument in function.args.posonlyargs),
            *(argument.annotation for argument in function.args.args),
            *(argument.annotation for argument in function.args.kwonlyargs),
        )
        if annotation is not None
    )
    return any(isinstance(node, ast.Call) for expression in expressions for node in ast.walk(expression))


def _closed_boundary_shape_edges(source: str) -> list[_Edge]:
    """Enforce the boundary's complete declaration and execution shape."""
    tree = ast.parse(source)
    parents = _parent_map(tree)
    edges: list[_Edge] = []
    functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if set(functions) != SINK_OWNERS:
        edges.append(
            _Edge(
                "top-level-function-shape",
                ",".join(sorted(functions)),
                0,
            )
        )
    for name, expected in EXPECTED_SINK_OWNER_BODIES.items():
        function = functions.get(name)
        if function is None or _statement_shape(_body_without_docstring(function)) != expected:
            edges.append(_Edge("sink-owner-body-shape", name, getattr(function, "lineno", 0)))

    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    if set(classes) != set(PROTOCOL_METHODS):
        edges.append(_Edge("protocol-class-shape", ",".join(sorted(classes)), 0))
    for class_name, expected_methods in PROTOCOL_METHODS.items():
        class_node = classes.get(class_name)
        if class_node is None:
            continue
        methods = {node.name: node for node in class_node.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if set(methods) != expected_methods:
            edges.append(_Edge("protocol-method-shape", class_name, class_node.lineno))
        for method in methods.values():
            inert_property = (
                len(method.decorator_list) == 1  # golden-count: cardinality-is-contract
                and _qualified_name(method.decorator_list[0]) == "property"
                and len(method.body) == 1  # golden-count: cardinality-is-contract
                and isinstance(method.body[0], ast.Expr)
                and isinstance(method.body[0].value, ast.Constant)
                and method.body[0].value.value is Ellipsis
                and not method.args.defaults
                and not any(method.args.kw_defaults)
            )
            if not inert_property:
                edges.append(_Edge("protocol-method-execution", method.name, method.lineno))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _enclosing_function(node, parents) is None:
            edges.append(_Edge("module-or-class-call", _qualified_name(node.func) or "call", node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _definition_preamble_has_call(node):
            edges.append(_Edge("definition-preamble-call", node.name, node.lineno))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            edges.append(_Edge("module-assignment", type(node).__name__, node.lineno))
    return sorted(set(edges), key=lambda item: (item.lineno, item.kind, item.value))


def _first_executable_statement(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.stmt:
    statements = _body_without_docstring(function)
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
        and len(statement.body) == 1  # golden-count: cardinality-is-contract
        and isinstance(statement.body[0], ast.Return)
        and statement.body[0].value is None
        and not statement.orelse
    )


def _boundary_violations(source: str) -> list[_Edge]:
    """Return unguarded selections and all sink capability escapes."""
    functions = _functions(source)
    uses, violations = _physical_sink_census(source)
    violations.extend(_closed_boundary_shape_edges(source))
    for use in uses:
        if use.kind != "direct-call":
            violations.append(_Edge("sink-escape", use.sink, use.lineno))
            continue
        function = functions.get(use.function or "")
        if function is None or not _has_terminal_identity_guard(function):
            violations.append(_Edge("unguarded-sink", use.sink, use.lineno))
    return sorted(set(violations), key=lambda item: (item.lineno, item.kind, item.value))


def test_agent_command_hosted_sink_imports_match_exact_package_allowlist() -> None:
    assert _package_hosted_import_findings(_agent_production_sources()) == {}


def test_differently_named_reachable_helper_cannot_hide_hosted_sink_import() -> None:
    sources = _agent_production_sources()
    sources[CALLER.name] += "\nfrom specify_cli.cli.commands.agent.delivery_bridge import deliver\n"
    sources["delivery_bridge.py"] = "from specify_cli.auth.transport import get_client\n\ndef deliver():\n    return get_client()\n"

    findings = _package_hosted_import_findings(sources)

    assert set(findings) == {"delivery_bridge.py"}
    assert findings["delivery_bridge.py"] == [
        _Edge(
            "from-import",
            "specify_cli.auth.transport.get_client",
            1,
        )
    ]


def test_package_import_policy_allows_unrelated_local_name_collision() -> None:
    sources = _agent_production_sources()
    sources["local_client_helpers.py"] = "def get_client():\n    return None\n\ndef use_local_client():\n    return get_client()\n"

    assert _package_hosted_import_findings(sources) == {}


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


@pytest.mark.parametrize(
    "statement",
    [
        'globals()["fanout_lifecycle_event_hosted"]({})',
        'getattr(sys.modules[__name__], "fanout_lifecycle_event_hosted")({})',
        '__builtins__["globals"]()["fanout_lifecycle_event_hosted"]({})',
        '__builtins__["getattr"](__builtins__, "globals")()["fanout_lifecycle_event_hosted"]({})',
    ],
)
def test_closed_sink_owner_body_rejects_namespace_lookup_bypasses(
    statement: str,
) -> None:
    source = BOUNDARY.read_text(encoding="utf-8")
    marker = "    for intent in lifecycle_intents:\n"
    assert source.count(marker) == 1
    mutated = source.replace(marker, f"    {statement}\n{marker}", 1)
    assert "sink-owner-body-shape" in {finding.kind for finding in _boundary_violations(mutated)}


@pytest.mark.parametrize(
    ("mutation", "expected_kind"),
    [
        ("\nfactory()\n", "module-or-class-call"),
        ("\nVALUE = factory()\n", "module-assignment"),
        ("\n@factory()\ndef extra():\n    pass\n", "definition-preamble-call"),
        ("\ndef extra(value=factory()):\n    pass\n", "definition-preamble-call"),
        ("\ndef extra(value: factory()):\n    pass\n", "definition-preamble-call"),
    ],
)
def test_closed_boundary_rejects_pre_guard_execution_surfaces(
    mutation: str,
    expected_kind: str,
) -> None:
    source = BOUNDARY.read_text(encoding="utf-8") + mutation
    assert expected_kind in {finding.kind for finding in _boundary_violations(source)}
