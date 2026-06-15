from __future__ import annotations

import ast
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path


_BANNED_CALLS = {
    ("datetime", "now"): "datetime.now()",
    ("datetime", "utcnow"): "datetime.utcnow()",
    ("datetime", "today"): "datetime.today()",
    ("datetime", "datetime", "now"): "datetime.datetime.now()",
    ("datetime", "datetime", "utcnow"): "datetime.datetime.utcnow()",
    ("datetime", "datetime", "today"): "datetime.datetime.today()",
    ("date", "today"): "date.today()",
    ("datetime", "date", "today"): "datetime.date.today()",
    ("time", "time"): "time.time()",
}

_ALIASABLE_CLOCK_PATHS = set(_BANNED_CALLS) | {
    ("datetime",),
    ("datetime", "datetime"),
    ("date",),
    ("datetime", "date"),
    ("time",),
}

_AliasMap = dict[tuple[str, ...], tuple[str, ...] | None]
_SHADOWED_PATH = ("<shadowed>",)
_SETUP_METHOD_NAMES = {"setup", "setup_method", "setup_class", "setUp", "setUpClass"}
_MODULE_SETUP_NAMES = {"setup_module", "setup_function", "setUpModule"}


@dataclass(frozen=True, order=True)
class WallClockAssertionViolation:
    path: Path
    line: int
    call: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.call}"


def find_wall_clock_assertion_violations(paths: Iterable[Path]) -> list[WallClockAssertionViolation]:
    """Find direct wall-clock reads inside pytest assert expressions."""
    violations: list[WallClockAssertionViolation] = []
    python_paths = sorted({Path(p) for p in paths if Path(p).suffix == ".py"})
    import_aliases = _collect_import_aliases(python_paths)
    conftest_fixture_aliases = _collect_conftest_fixture_aliases(python_paths, import_aliases)
    for path in python_paths:
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _WallClockAssertionVisitor(path, import_aliases, conftest_fixture_aliases.get(path, {}))
        visitor.visit(tree)
        violations.extend(visitor.violations)
    return sorted(violations)


def find_test_python_paths(root: Path) -> list[Path]:
    """Return every Python file under the test tree, including helper modules."""
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _collect_import_aliases(paths: list[Path]) -> dict[str, _AliasMap]:
    if not paths:
        return {}
    root = Path(os.path.commonpath([str(path.parent) for path in paths]))
    module_names = {path: _module_names(path, root) for path in paths}
    import_aliases: dict[str, _AliasMap] = {}

    for _ in range(4):
        next_aliases: dict[str, _AliasMap] = {}
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            visitor = _WallClockAssertionVisitor(path, import_aliases)
            visitor.visit(tree)
            exports = _module_exports(visitor.scopes[0])
            for module_name in module_names[path]:
                next_aliases[module_name] = exports
        if next_aliases == import_aliases:
            break
        import_aliases = next_aliases
    return import_aliases


def _module_names(path: Path, root: Path) -> set[str]:
    try:
        relative = path.with_suffix("").relative_to(root)
    except ValueError:
        return set()
    parts = relative.parent.parts if relative.name == "__init__" else relative.parts
    if not parts:
        return set()
    names = {".".join(parts)}
    if root.name:
        names.add(".".join((root.name, *parts)))
    return names


def _module_exports(scope: _AliasMap) -> _AliasMap:
    return {
        path: source
        for path, source in scope.items()
        if source in _ALIASABLE_CLOCK_PATHS or source in _BANNED_CALLS
    }


def _collect_conftest_fixture_aliases(
    paths: list[Path],
    import_aliases: dict[str, _AliasMap],
) -> dict[Path, _AliasMap]:
    conftest_aliases: dict[Path, _AliasMap] = {}
    for path in paths:
        if path.name != "conftest.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _WallClockAssertionVisitor(path, import_aliases)
        visitor.visit(tree)
        conftest_aliases[path] = visitor.fixture_return_aliases()

    aliases_by_path: dict[Path, _AliasMap] = {}
    for path in paths:
        aliases: _AliasMap = {}
        for conftest_path, fixture_aliases in conftest_aliases.items():
            if conftest_path.parent == path.parent or conftest_path.parent in path.parent.parents:
                aliases.update(fixture_aliases)
        if aliases:
            aliases_by_path[path] = aliases
    return aliases_by_path


def format_wall_clock_assertion_violations(
    violations: Iterable[WallClockAssertionViolation],
) -> str:
    rendered = "\n".join(f"  - {violation.render()}" for violation in violations)
    return (
        "Wall-clock reads are not allowed inside test assertions.\n"
        "Inject a stable `now=`/clock into production code and assert against that fixed value.\n"
        "For genuine freshness-window checks, capture bounds before/after the action and keep the wall-clock calls out of the assert expression.\n"
        f"{rendered}"
    )


def _wall_clock_calls(
    assert_node: ast.Assert,
    scopes: list[_AliasMap],
) -> list[tuple[ast.Call, str]]:
    visitor = _AssertCallVisitor(scopes)
    visitor.visit(assert_node.test)
    if assert_node.msg is not None:
        visitor.visit(assert_node.msg)
    return visitor.calls


class _AssertCallVisitor(ast.NodeVisitor):
    def __init__(self, scopes: list[_AliasMap]) -> None:
        self.scopes = [*scopes, {}]
        self.calls: list[tuple[ast.Call, str]] = []

    @property
    def scope(self) -> _AliasMap:
        return self.scopes[-1]

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.NamedExpr):
            self.visit(node.func.value)
            self._add_assignment_aliases([node.func.target], node.func.value)
            raw_path = _attribute_path(node.func.target)
        else:
            raw_path = _attribute_path(node.func)
            self.visit(node.func)

        if raw_path and _normalize_alias(raw_path, self.scopes) in _BANNED_CALLS:
            self.calls.append((node, f"{'.'.join(raw_path)}()"))

        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            self.visit(keyword.value)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self._add_assignment_aliases([node.target], node.value)

    def visit_If(self, node: ast.If) -> None:
        if _is_static_false(node.test) or _is_type_checking_name(node.test, self.scopes):
            for statement in node.orelse:
                self.visit(statement)
            return
        if _is_static_true(node.test):
            for statement in node.body:
                self.visit(statement)
            return
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in (*node.args.defaults, *(default for default in node.args.kw_defaults if default is not None)):
            self.visit(default)
        local_scope: _AliasMap = {(name,): None for name in _argument_names(node.args)}
        local_scope.update(_arguments_default_aliases(node.args, self.scopes))
        self.scopes.append(local_scope)
        try:
            self.visit(node.body)
        finally:
            self.scopes.pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension([node.key, node.value], node.generators)

    def _add_assignment_aliases(self, targets: list[ast.expr], value: ast.expr) -> None:
        _add_assignment_aliases(self.scopes, lambda _: self.scope, targets, value)

    def _visit_comprehension(
        self,
        result_nodes: list[ast.expr],
        generators: list[ast.comprehension],
    ) -> None:
        local_scope: _AliasMap = {}
        self.scopes.append(local_scope)
        for generator in generators:
            self.visit(generator.iter)
            for target_path in _assignment_target_paths(generator.target):
                _set_shadow(local_scope, target_path)
            for condition in generator.ifs:
                self.visit(condition)
        for result_node in result_nodes:
            self.visit(result_node)
        self.scopes.pop()


class _WallClockAssertionVisitor(ast.NodeVisitor):
    def __init__(
        self,
        path: Path,
        import_aliases: dict[str, _AliasMap] | None = None,
        external_fixture_aliases: _AliasMap | None = None,
    ) -> None:
        self.path = path
        self.import_aliases = import_aliases or {}
        self.external_fixture_aliases = external_fixture_aliases or {}
        self.violations: list[WallClockAssertionViolation] = []
        self.scopes: list[_AliasMap] = [{}]
        self.global_names_stack: list[set[str]] = []
        self.propagate_global_stack: list[bool] = []
        self.defer_function_scans = True
        self.deferred_functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        self.deferred_classes: list[tuple[str, list[ast.FunctionDef | ast.AsyncFunctionDef], set[str]]] = []
        self.autouse_fixtures: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        self.fixtures: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.module_usefixtures: set[str] = set()

    def fixture_return_aliases(self) -> _AliasMap:
        aliases: _AliasMap = {}
        for fixture_name in self.fixtures:
            aliases.update(self._fixture_return_aliases(fixture_name, set()))
        return aliases

    @property
    def scope(self) -> _AliasMap:
        return self.scopes[-1]

    def visit_Module(self, node: ast.Module) -> None:
        for statement in node.body:
            self.visit(statement)
        self._scan_deferred_functions()

    def visit_Assert(self, node: ast.Assert) -> None:
        for call, call_name in _wall_clock_calls(node, self.scopes):
            self.violations.append(
                WallClockAssertionViolation(
                    path=self.path,
                    line=getattr(call, "lineno", node.lineno),
                    call=call_name,
                )
            )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            parts = tuple(alias.name.split("."))
            module_name = ".".join(parts)
            if module_name in self.import_aliases:
                target_path = (alias.asname,) if alias.asname else parts
                self._add_module_import_aliases(target_path, self.import_aliases[module_name])
            elif parts and parts[0] in {"datetime", "time", "typing", "pytest"}:
                self._set_alias((alias.asname or parts[0],), parts)
            else:
                self._set_shadow((alias.asname or parts[0],))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "typing":
            for alias in node.names:
                if alias.name == "TYPE_CHECKING":
                    self._set_alias((alias.asname or alias.name,), ("typing", "TYPE_CHECKING"))
                elif alias.name != "*":
                    self._set_shadow((alias.asname or alias.name,))
            return
        if node.module == "pytest":
            for alias in node.names:
                if alias.name in {"fixture", "mark"}:
                    self._set_alias((alias.asname or alias.name,), ("pytest", alias.name))
                elif alias.name != "*":
                    self._set_shadow((alias.asname or alias.name,))
            return
        if node.module and self._has_from_import_aliases(node.module, node.names):
            self._add_from_import_aliases(node.module, node.names)
            return
        if node.module not in {"datetime", "time"}:
            for alias in node.names:
                if alias.name == "*":
                    self._set_shadow(("datetime",))
                    self._set_shadow(("date",))
                    self._set_shadow(("time",))
                else:
                    self._set_shadow((alias.asname or alias.name,))
            return
        for alias in node.names:
            if alias.name == "*":
                _add_star_import_aliases(self.scope, node.module)
                continue
            self._set_alias((alias.asname or alias.name,), (node.module, alias.name))

    def _add_module_import_aliases(self, target_path: tuple[str, ...], exports: _AliasMap) -> None:
        for export_path, source in exports.items():
            if source is not None:
                self._set_alias((*target_path, *export_path), source)

    def _add_from_import_aliases(self, module_name: str, aliases: list[ast.alias]) -> None:
        exports = self.import_aliases.get(module_name, {})
        for alias in aliases:
            if alias.name == "*":
                for export_path, source in exports.items():
                    if source is not None:
                        self._set_alias(export_path, source)
                continue
            target_name = alias.asname or alias.name
            source = exports.get((alias.name,))
            if source is not None:
                self._set_alias((target_name,), source)
                continue
            descendant_exports = {
                export_path[1:]: export_source
                for export_path, export_source in exports.items()
                if len(export_path) > 1 and export_path[0] == alias.name and export_source is not None
            }
            if descendant_exports:
                for export_path, export_source in descendant_exports.items():
                    self._set_alias((target_name, *export_path), export_source)
                continue
            imported_module = self.import_aliases.get(f"{module_name}.{alias.name}")
            if imported_module is not None:
                self._add_module_import_aliases((target_name,), imported_module)
                continue
            self._set_shadow((target_name,))

    def _has_from_import_aliases(self, module_name: str, aliases: list[ast.alias]) -> bool:
        return module_name in self.import_aliases or any(
            alias.name != "*" and f"{module_name}.{alias.name}" in self.import_aliases for alias in aliases
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if _attribute_path(target) == ("pytestmark",):
                self.module_usefixtures.update(_pytestmark_usefixture_names(node.value, self.scopes))
        self._add_assignment_aliases(node.targets, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is None:
            self._shadow_targets([node.target])
            return
        self._add_assignment_aliases([node.target], node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._shadow_targets([node.target])

    def visit_For(self, node: ast.For) -> None:
        self._visit_for(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_for(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_with(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_with(node)

    def _visit_for(self, node: ast.For | ast.AsyncFor) -> None:
        self.visit(node.iter)
        self._shadow_targets([node.target])
        for statement in node.body:
            self.visit(statement)
        for statement in node.orelse:
            self.visit(statement)

    def _visit_with(self, node: ast.With | ast.AsyncWith) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self._shadow_targets([item.optional_vars])
        for statement in node.body:
            self.visit(statement)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._add_assignment_aliases([node.target], node.value)

    def visit_If(self, node: ast.If) -> None:
        if _is_static_false(node.test) or _is_type_checking_name(node.test, self.scopes):
            for statement in node.orelse:
                self.visit(statement)
            return
        if _is_static_true(node.test):
            for statement in node.body:
                self.visit(statement)
            return
        self.visit(node.test)
        self._visit_unknown_branch(node.body)
        self._visit_unknown_branch(node.orelse)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self.defer_function_scans:
            self._set_shadow((node.name,))
            self._record_function_return_alias(node)
            if node.name in _MODULE_SETUP_NAMES:
                _propagate_module_setup_aliases(node, self.scopes)
            self._record_fixture(node)
            if _is_autouse_fixture(node, self.scopes):
                self.autouse_fixtures.append(node)
            self.deferred_functions.append(node)
            return
        self._set_shadow((node.name,))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self.defer_function_scans:
            self._set_shadow((node.name,))
            self._record_function_return_alias(node)
            if node.name in _MODULE_SETUP_NAMES:
                _propagate_module_setup_aliases(node, self.scopes)
            self._record_fixture(node)
            if _is_autouse_fixture(node, self.scopes):
                self.autouse_fixtures.append(node)
            self.deferred_functions.append(node)
            return
        self._set_shadow((node.name,))

    def _scan_function_def(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        fixture_aliases: _AliasMap = {}
        if _is_test_function(node):
            fixture_aliases = self._fixture_aliases_for_function(node, set())
        self._visit_function_scope(node, bind_name=True, local_aliases=fixture_aliases)
        if not _is_test_function(node):
            self._record_function_return_alias(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if not self.defer_function_scans:
            self._set_shadow((node.name,))
            return

        self._set_shadow((node.name,))
        class_usefixtures = _usefixture_names(node.decorator_list, self.scopes)
        deferred_methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

        self.scopes.append({})
        for statement in node.body:
            if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
                self._set_shadow((statement.name,))
                deferred_methods.append(statement)
                continue
            self.visit(statement)
        class_aliases = {path: source for path, source in self.scope.items() if source is not None}
        self.scopes.pop()

        for path, source in class_aliases.items():
            self._set_alias((node.name, *path), source)
        self.deferred_classes.append((node.name, deferred_methods, class_usefixtures))

    def _scan_deferred_functions(self) -> None:
        self.defer_function_scans = False
        for fixture in self.autouse_fixtures:
            self._propagate_fixture_node_aliases(fixture, set())
        for function in self.deferred_functions:
            self._scan_function_def(function)
        for class_name, methods, class_usefixtures in self.deferred_classes:
            base_class_aliases = _module_class_aliases(self.scopes[0], class_name)
            for method in methods:
                if method.name in _SETUP_METHOD_NAMES:
                    base_class_aliases.update(_method_instance_aliases(method, self.scopes, base_class_aliases))
            class_fixture_methods = _class_fixture_methods(methods, self.scopes)
            autouse_fixture_methods = [
                method for method in methods if _is_autouse_fixture(method, self.scopes)
            ]
            for method in methods:
                class_aliases = base_class_aliases.copy()
                fixture_aliases: _AliasMap = {}
                if _is_test_function(method):
                    requested_fixtures = class_usefixtures | _usefixture_names(method.decorator_list, self.scopes)
                    for fixture_method in autouse_fixture_methods:
                        class_aliases.update(
                            _method_instance_aliases(
                                fixture_method,
                                self.scopes,
                                class_aliases,
                                stop_at_yield=True,
                            )
                        )
                    for fixture_name in requested_fixtures:
                        requested_fixture_method = class_fixture_methods.get(fixture_name)
                        if requested_fixture_method is not None:
                            class_aliases.update(
                                _method_instance_aliases(
                                    requested_fixture_method,
                                    self.scopes,
                                    class_aliases,
                                    stop_at_yield=True,
                                )
                            )
                    fixture_aliases = self._fixture_aliases_for_function(method, class_usefixtures)
                self._visit_function_scope(
                    method,
                    bind_name=False,
                    class_aliases=class_aliases,
                    local_aliases=fixture_aliases,
                )
        self.defer_function_scans = True

    def _visit_function_scope(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        bind_name: bool,
        class_aliases: dict[tuple[str, ...], tuple[str, ...]] | None = None,
        local_aliases: _AliasMap | None = None,
    ) -> None:
        if bind_name:
            self._set_shadow((node.name,))
        local_shadows: _AliasMap = {(name,): None for name in _function_bound_names(node)}
        local_shadows.update(_function_default_aliases(node, self.scopes))
        if class_aliases:
            for self_name in _method_self_names(node):
                for path, source in class_aliases.items():
                    local_shadows[(self_name, *path)] = source
        if local_aliases:
            local_shadows.update(local_aliases)
        self.scopes.append(local_shadows)
        self.global_names_stack.append(_function_global_names(node))
        self.propagate_global_stack.append(bind_name and node.name in _MODULE_SETUP_NAMES)
        for statement in node.body:
            self.visit(statement)
        self.propagate_global_stack.pop()
        self.global_names_stack.pop()
        self.scopes.pop()

    def _add_assignment_aliases(self, targets: list[ast.expr], value: ast.expr) -> None:
        _add_assignment_aliases(self.scopes, self._scope_for_target, targets, value)

    def _record_function_return_alias(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        source = _function_return_alias(node, self.scopes)
        if source is not None:
            self._set_alias((node.name,), source)

    def _record_fixture(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for fixture_name in _fixture_names(node, self.scopes):
            self.fixtures[fixture_name] = node

    def _fixture_aliases_for_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        extra_fixture_names: set[str],
    ) -> _AliasMap:
        fixture_argument_names = _argument_names(node.args)
        fixture_names = (
            fixture_argument_names
            | _usefixture_names(node.decorator_list, self.scopes)
            | self.module_usefixtures
            | extra_fixture_names
        )
        for fixture_name in sorted(fixture_names):
            self._propagate_fixture_aliases(fixture_name, set())

        aliases: _AliasMap = {}
        for fixture_name in sorted(fixture_argument_names):
            aliases.update(self._fixture_return_aliases(fixture_name, set()))
        return aliases

    def _propagate_fixture_aliases(self, fixture_name: str, active_fixtures: set[int]) -> None:
        fixture = self.fixtures.get(fixture_name)
        if fixture is not None:
            self._propagate_fixture_node_aliases(fixture, active_fixtures)

    def _propagate_fixture_node_aliases(
        self,
        fixture: ast.FunctionDef | ast.AsyncFunctionDef,
        active_fixtures: set[int],
    ) -> None:
        fixture_id = id(fixture)
        if fixture_id in active_fixtures:
            return
        active_fixtures.add(fixture_id)
        for dependency_name in _argument_names(fixture.args):
            self._propagate_fixture_aliases(dependency_name, active_fixtures)
        _propagate_module_setup_aliases(
            fixture,
            self.scopes,
            self._fixture_argument_aliases(fixture, active_fixtures),
            stop_at_yield=True,
        )
        active_fixtures.remove(fixture_id)

    def _fixture_argument_aliases(
        self,
        fixture: ast.FunctionDef | ast.AsyncFunctionDef,
        active_fixtures: set[int],
    ) -> _AliasMap:
        aliases: _AliasMap = {}
        for dependency_name in _argument_names(fixture.args):
            aliases.update(self._fixture_return_aliases(dependency_name, active_fixtures))
        return aliases

    def _fixture_return_aliases(self, fixture_name: str, active_fixtures: set[int]) -> _AliasMap:
        fixture = self.fixtures.get(fixture_name)
        if fixture is None:
            return {
                path: source
                for path, source in self.external_fixture_aliases.items()
                if path[:1] == (fixture_name,) and source is not None
            }
        fixture_id = id(fixture)
        if fixture_id in active_fixtures:
            return {}
        active_fixtures.add(fixture_id)
        local_aliases = _function_default_aliases(fixture, self.scopes)
        local_aliases.update(self._fixture_argument_aliases(fixture, active_fixtures))
        aliases = _function_result_aliases(
            fixture,
            self.scopes,
            (fixture_name,),
            include_yields=True,
            initial_aliases=local_aliases,
        )
        active_fixtures.remove(fixture_id)
        return aliases

    def _shadow_targets(self, targets: list[ast.expr]) -> None:
        for target in targets:
            for target_path in _assignment_target_paths(target):
                self._set_shadow(target_path)

    def _set_alias(self, target_path: tuple[str, ...], source: tuple[str, ...]) -> None:
        _set_alias(self.scope, target_path, source)

    def _set_shadow(self, target_path: tuple[str, ...]) -> None:
        _set_shadow(self.scope, target_path)

    def _scope_for_target(self, target_path: tuple[str, ...]) -> _AliasMap:
        if (
            self.global_names_stack
            and self.propagate_global_stack
            and self.propagate_global_stack[-1]
            and len(target_path) == 1
            and target_path[0] in self.global_names_stack[-1]
        ):
            return self.scopes[0]
        return self.scope

    def _visit_unknown_branch(self, statements: list[ast.stmt]) -> None:
        branch_scope: _AliasMap = {}
        self.scopes.append(branch_scope)
        for statement in statements:
            self.visit(statement)
        self.scopes.pop()
        _merge_clock_aliases(self.scope, branch_scope)


def _add_star_import_aliases(
    aliases: _AliasMap,
    module: str | None,
) -> None:
    if module == "time":
        aliases[("time",)] = ("time", "time")
    elif module == "datetime":
        aliases[("datetime",)] = ("datetime", "datetime")
        aliases[("date",)] = ("datetime", "date")


def _module_class_aliases(
    module_scope: _AliasMap,
    class_name: str,
) -> dict[tuple[str, ...], tuple[str, ...]]:
    return {
        alias_path[1:]: source
        for alias_path, source in module_scope.items()
        if len(alias_path) > 1 and alias_path[0] == class_name and source is not None
    }


def _class_fixture_methods(
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
    scopes: list[_AliasMap],
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    fixtures: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for method in methods:
        for fixture_name in _fixture_names(method, scopes):
            fixtures[fixture_name] = method
    return fixtures


def _merge_clock_aliases(target: _AliasMap, source: _AliasMap) -> None:
    for path, alias_source in source.items():
        if alias_source is not None:
            _set_alias(target, path, alias_source)


def _fixture_names(node: ast.FunctionDef | ast.AsyncFunctionDef, scopes: list[_AliasMap]) -> set[str]:
    names: set[str] = set()
    for decorator in node.decorator_list:
        if not _is_fixture_decorator(decorator, scopes):
            continue
        names.add(_fixture_decorator_name(decorator) or node.name)
    return names


def _is_autouse_fixture(node: ast.FunctionDef | ast.AsyncFunctionDef, scopes: list[_AliasMap]) -> bool:
    for decorator in node.decorator_list:
        if not _is_fixture_decorator(decorator, scopes):
            continue
        if not isinstance(decorator, ast.Call):
            continue
        for keyword in decorator.keywords:
            if keyword.arg == "autouse" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                return True
    return False


def _is_fixture_decorator(decorator: ast.expr, scopes: list[_AliasMap]) -> bool:
    path = _attribute_path(decorator.func) if isinstance(decorator, ast.Call) else _attribute_path(decorator)
    return _normalize_alias(path, scopes) in {("fixture",), ("pytest", "fixture")}


def _fixture_decorator_name(decorator: ast.expr) -> str | None:
    if not isinstance(decorator, ast.Call):
        return None
    for keyword in decorator.keywords:
        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def _usefixture_names(decorators: list[ast.expr], scopes: list[_AliasMap]) -> set[str]:
    names: set[str] = set()
    for decorator in decorators:
        if not isinstance(decorator, ast.Call):
            continue
        if _normalize_alias(_attribute_path(decorator.func), scopes) != ("pytest", "mark", "usefixtures"):
            continue
        for arg in decorator.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                names.add(arg.value)
    return names


def _pytestmark_usefixture_names(node: ast.expr, scopes: list[_AliasMap]) -> set[str]:
    if isinstance(node, ast.Call):
        return _usefixture_names([node], scopes)
    if isinstance(node, ast.Tuple | ast.List):
        names: set[str] = set()
        for element in node.elts:
            names.update(_pytestmark_usefixture_names(element, scopes))
        return names
    return set()


def _propagate_module_setup_aliases(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    scopes: list[_AliasMap],
    local_aliases: _AliasMap | None = None,
    *,
    stop_at_yield: bool = False,
) -> None:
    global_names = _function_global_names(node)
    collector = _ModuleSetupAliasCollector(scopes, global_names, local_aliases)
    for statement in (_setup_phase_body(node.body) if stop_at_yield else node.body):
        collector.visit(statement)


def _setup_phase_body(statements: list[ast.stmt]) -> list[ast.stmt]:
    setup_statements: list[ast.stmt] = []
    for statement in statements:
        if any(isinstance(node, ast.Yield | ast.YieldFrom) for node in ast.walk(statement)):
            break
        setup_statements.append(statement)
    return setup_statements


class _ModuleSetupAliasCollector(ast.NodeVisitor):
    def __init__(self, scopes: list[_AliasMap], global_names: set[str], local_aliases: _AliasMap | None = None) -> None:
        self.global_names = global_names
        self.scopes = [*scopes, local_aliases.copy() if local_aliases else {}]
        self.local_helpers: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.local_helper_aliases: dict[str, str] = {}
        self.active_helpers: set[str] = set()

    @property
    def scope(self) -> _AliasMap:
        return self.scopes[-1]

    def visit_Assign(self, node: ast.Assign) -> None:
        self._record_helper_aliases(node.targets, node.value)
        _add_assignment_aliases(self.scopes, self._scope_for_target, node.targets, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            _add_assignment_aliases(self.scopes, self._scope_for_target, [node.target], node.value)

    def visit_If(self, node: ast.If) -> None:
        if _is_static_false(node.test) or _is_type_checking_name(node.test, self.scopes):
            for statement in node.orelse:
                self.visit(statement)
            return
        if _is_static_true(node.test):
            for statement in node.body:
                self.visit(statement)
            return
        self.visit(node.test)
        self._visit_unknown_branch(node.body)
        self._visit_unknown_branch(node.orelse)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.local_helpers[node.name] = node
        _set_alias(self.scope, (node.name,), (node.name,))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.local_helpers[node.name] = node
        _set_alias(self.scope, (node.name,), (node.name,))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        del node

    def visit_Call(self, node: ast.Call) -> None:
        helper_name = self._local_helper_alias_name(_raw_called_name(node))
        if helper_name is None:
            helper_name = self._local_helper_name(_called_name(node, self.scopes))
        if helper_name is None or helper_name not in self.local_helpers or helper_name in self.active_helpers:
            self.generic_visit(node)
            return
        helper = self.local_helpers[helper_name]
        bindings = _call_argument_bindings(helper, node)
        if bindings is None:
            self.generic_visit(node)
            return
        call_scope = _function_call_scope(helper, bindings, self.scopes)
        self.active_helpers.add(helper_name)
        original_global_names = self.global_names
        self.global_names = self.global_names | _function_global_names(helper)
        self.scopes.append(call_scope)
        try:
            for statement in helper.body:
                self.visit(statement)
        finally:
            self.scopes.pop()
            self.global_names = original_global_names
            self.active_helpers.remove(helper_name)

    def _scope_for_target(self, target_path: tuple[str, ...]) -> _AliasMap:
        if len(target_path) == 1 and target_path[0] in self.global_names:
            return self.scopes[0]
        return self.scope

    def _record_helper_aliases(self, targets: list[ast.expr], value: ast.expr) -> None:
        source = _attribute_path(value)
        helper_name = source[0] if len(source) == 1 and source[0] in self.local_helpers else None
        for target in targets:
            target_path = _attribute_path(target)
            if len(target_path) == 1:
                if helper_name is None:
                    self.local_helper_aliases.pop(target_path[0], None)
                else:
                    self.local_helper_aliases[target_path[0]] = helper_name

    def _local_helper_name(self, name: str | None) -> str | None:
        if name is None:
            return None
        return self.local_helper_aliases.get(name, name)

    def _local_helper_alias_name(self, name: str | None) -> str | None:
        if name is None:
            return None
        return self.local_helper_aliases.get(name)

    def _visit_unknown_branch(self, statements: list[ast.stmt]) -> None:
        branch_scope: _AliasMap = {}
        self.scopes.append(branch_scope)
        for statement in statements:
            self.visit(statement)
        self.scopes.pop()
        _merge_clock_aliases(self.scope, branch_scope)

def _add_assignment_aliases(
    scopes: list[_AliasMap],
    scope_for_target: Callable[[tuple[str, ...]], _AliasMap],
    targets: list[ast.expr],
    value: ast.expr,
) -> None:
    if len(targets) == 1 and isinstance(targets[0], ast.Tuple | ast.List) and isinstance(value, ast.Tuple | ast.List):
        for target, element in zip(targets[0].elts, value.elts, strict=False):
            _add_assignment_aliases(scopes, scope_for_target, [target], element)
        return

    source = _alias_source(value, scopes)
    if source not in _ALIASABLE_CLOCK_PATHS:
        for target in targets:
            for target_path in _assignment_target_paths(target):
                _set_shadow(scope_for_target(target_path), target_path)
        return
    for target in targets:
        target_path = _attribute_path(target)
        if target_path:
            _set_alias(scope_for_target(target_path), target_path, source)


def _set_alias(scope: _AliasMap, target_path: tuple[str, ...], source: tuple[str, ...]) -> None:
    scope[target_path] = source


def _set_shadow(scope: _AliasMap, target_path: tuple[str, ...]) -> None:
    for alias_path in list(scope):
        if len(alias_path) > len(target_path) and alias_path[: len(target_path)] == target_path:
            del scope[alias_path]
    scope[target_path] = None


def _normalize_alias(
    path: tuple[str, ...],
    scopes: list[_AliasMap],
) -> tuple[str, ...]:
    for scope in reversed(scopes):
        for index in range(len(path), 0, -1):
            prefix = path[:index]
            if prefix not in scope:
                continue
            replacement = scope[prefix]
            if replacement is None:
                return _SHADOWED_PATH
            return replacement + path[index:]
    return path


def _alias_source(node: ast.expr, scopes: list[_AliasMap]) -> tuple[str, ...]:
    if (
        isinstance(node, ast.Call)
        and _attribute_path(node.func) in {("staticmethod",), ("classmethod",)}
        and len(node.args) == 1
    ):
        return _normalize_alias(_attribute_path(node.args[0]), scopes)
    return _normalize_alias(_attribute_path(node), scopes)


def _is_static_false(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _is_static_true(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _is_type_checking_name(node: ast.AST, scopes: list[_AliasMap]) -> bool:
    return _normalize_alias(_attribute_path(node), scopes) == ("typing", "TYPE_CHECKING")


def _is_test_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return node.name.startswith("test_")


def _function_bound_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names = _argument_names(node.args)
    visitor = _FunctionBindingVisitor()
    for statement in node.body:
        visitor.visit(statement)
    names.update(visitor.names - visitor.global_names - visitor.nonlocal_names)
    return names


def _function_global_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    visitor = _FunctionBindingVisitor()
    for statement in node.body:
        visitor.visit(statement)
    return visitor.global_names


def _function_default_aliases(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    scopes: list[_AliasMap],
) -> _AliasMap:
    return _arguments_default_aliases(node.args, scopes)


def _arguments_default_aliases(
    arguments: ast.arguments,
    scopes: list[_AliasMap],
) -> _AliasMap:
    aliases: _AliasMap = {}
    positional_args = (*arguments.posonlyargs, *arguments.args)
    default_offset = len(positional_args) - len(arguments.defaults)
    for arg, default in zip(positional_args[default_offset:], arguments.defaults, strict=False):
        source = _alias_source(default, scopes)
        if source in _ALIASABLE_CLOCK_PATHS:
            aliases[(arg.arg,)] = source

    for arg, kw_default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True):
        if kw_default is None:
            continue
        source = _alias_source(kw_default, scopes)
        if source in _ALIASABLE_CLOCK_PATHS:
            aliases[(arg.arg,)] = source
    return aliases


def _function_return_alias(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    scopes: list[_AliasMap],
    *,
    include_yields: bool = False,
) -> tuple[str, ...] | None:
    visitor = _FunctionReturnAliasVisitor(scopes, node, include_yields=include_yields)
    for statement in node.body:
        visitor.visit(statement)
    return visitor.source


def _function_result_aliases(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    scopes: list[_AliasMap],
    target_prefix: tuple[str, ...],
    *,
    include_yields: bool,
    initial_aliases: _AliasMap | None = None,
) -> _AliasMap:
    visitor = _FunctionReturnAliasVisitor(
        scopes,
        node,
        include_yields=include_yields,
        initial_aliases=initial_aliases,
    )
    for statement in node.body:
        visitor.visit(statement)

    aliases: _AliasMap = {}
    if visitor.source in _ALIASABLE_CLOCK_PATHS or visitor.source in _BANNED_CALLS:
        aliases[target_prefix] = visitor.source
    if visitor.result_path:
        for scope in visitor.scopes:
            for alias_path, source in scope.items():
                if (
                    source is not None
                    and (source in _ALIASABLE_CLOCK_PATHS or source in _BANNED_CALLS)
                    and len(alias_path) > len(visitor.result_path)
                    and alias_path[: len(visitor.result_path)] == visitor.result_path
                ):
                    aliases[(*target_prefix, *alias_path[len(visitor.result_path) :])] = source
    return aliases


class _FunctionReturnAliasVisitor(ast.NodeVisitor):
    def __init__(
        self,
        scopes: list[_AliasMap],
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        include_yields: bool,
        initial_aliases: _AliasMap | None = None,
    ) -> None:
        local_scope: _AliasMap = {(name,): None for name in _function_bound_names(node)}
        local_scope.update(_function_default_aliases(node, scopes))
        if initial_aliases:
            local_scope.update(initial_aliases)
        self.scopes = [*scopes, local_scope]
        self.include_yields = include_yields
        self.source: tuple[str, ...] | None = None
        self.result_path: tuple[str, ...] | None = None

    @property
    def scope(self) -> _AliasMap:
        return self.scopes[-1]

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is None:
            return
        self._record_result(node.value)

    def visit_Yield(self, node: ast.Yield) -> None:
        if not self.include_yields or node.value is None:
            return
        self._record_result(node.value)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        if self.include_yields:
            self._record_result(node.value)

    def _record_result(self, node: ast.expr) -> None:
        if isinstance(node, ast.Call):
            source = _normalize_alias(_attribute_path(node.func), self.scopes)
            if source in _BANNED_CALLS:
                self.source = source
                return
        source = _alias_source(node, self.scopes)
        if source in _ALIASABLE_CLOCK_PATHS:
            self.source = source
        raw_path = _attribute_path(node)
        path = _normalize_alias(raw_path, self.scopes)
        if path and path != _SHADOWED_PATH:
            self.result_path = path
        elif raw_path:
            self.result_path = raw_path

    def visit_Assign(self, node: ast.Assign) -> None:
        _add_assignment_aliases(self.scopes, lambda _: self.scope, node.targets, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            _add_assignment_aliases(self.scopes, lambda _: self.scope, [node.target], node.value)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        _add_assignment_aliases(self.scopes, lambda _: self.scope, [node.target], node.value)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        del node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        del node

    def visit_Lambda(self, node: ast.Lambda) -> None:
        del node

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        _set_shadow(self.scope, (node.name,))
        self.scopes.append({})
        for statement in node.body:
            if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            self.visit(statement)
        class_aliases = {path: source for path, source in self.scope.items() if source is not None}
        self.scopes.pop()
        for path, source in class_aliases.items():
            _set_alias(self.scope, (node.name, *path), source)


def _call_argument_bindings(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    call: ast.Call,
) -> dict[str, ast.expr] | None:
    positional_params = (*function.args.posonlyargs, *function.args.args)
    if len(call.args) > len(positional_params):
        return None

    bindings = {param.arg: arg for param, arg in zip(positional_params, call.args, strict=False)}
    keyword_param_names = {param.arg for param in (*function.args.args, *function.args.kwonlyargs)}
    for keyword in call.keywords:
        if keyword.arg is None or keyword.arg not in keyword_param_names or keyword.arg in bindings:
            return None
        bindings[keyword.arg] = keyword.value
    return bindings


def _function_call_scope(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    bindings: dict[str, ast.expr],
    scopes: list[_AliasMap],
) -> _AliasMap:
    call_scope: _AliasMap = {(name,): None for name in _function_bound_names(function)}
    call_scope.update(_function_default_aliases(function, scopes))
    for name, value in bindings.items():
        source = _alias_source(value, scopes)
        if source in _ALIASABLE_CLOCK_PATHS:
            _set_alias(call_scope, (name,), source)
        else:
            _set_shadow(call_scope, (name,))
    return call_scope


def _method_self_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    positional_args = (*node.args.posonlyargs, *node.args.args)
    if positional_args:
        names.add(positional_args[0].arg)
    if node.args.vararg is not None:
        names.add(node.args.vararg.arg)
    return names


def _method_instance_aliases(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    scopes: list[_AliasMap],
    class_aliases: dict[tuple[str, ...], tuple[str, ...]],
    *,
    stop_at_yield: bool = False,
) -> dict[tuple[str, ...], tuple[str, ...]]:
    self_names = _method_self_names(node)
    aliases: dict[tuple[str, ...], tuple[str, ...]] = {}
    if not self_names:
        return aliases

    collector = _MethodInstanceAliasCollector(scopes, class_aliases, self_names, node)
    for statement in (_setup_phase_body(node.body) if stop_at_yield else node.body):
        collector.visit(statement)
    return collector.aliases


class _MethodInstanceAliasCollector(ast.NodeVisitor):
    def __init__(
        self,
        scopes: list[_AliasMap],
        class_aliases: dict[tuple[str, ...], tuple[str, ...]],
        self_names: set[str],
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self.self_names = self_names
        self.aliases: dict[tuple[str, ...], tuple[str, ...]] = {}
        self.local_helpers: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.local_helper_aliases: dict[str, str] = {}
        self.active_helpers: set[str] = set()
        local_scope: _AliasMap = {(name,): None for name in _function_bound_names(node)}
        for self_name in self_names:
            for path, source in class_aliases.items():
                local_scope[(self_name, *path)] = source
        self.scopes = [*scopes, local_scope]

    @property
    def scope(self) -> _AliasMap:
        return self.scopes[-1]

    def visit_Assign(self, node: ast.Assign) -> None:
        self._record_helper_aliases(node.targets, node.value)
        self._record_instance_aliases(node.targets, node.value)
        _add_assignment_aliases(self.scopes, lambda _: self.scope, node.targets, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is None:
            return
        self._record_instance_aliases([node.target], node.value)
        _add_assignment_aliases(self.scopes, lambda _: self.scope, [node.target], node.value)

    def visit_If(self, node: ast.If) -> None:
        if _is_static_false(node.test) or _is_type_checking_name(node.test, self.scopes):
            for statement in node.orelse:
                self.visit(statement)
            return
        if _is_static_true(node.test):
            for statement in node.body:
                self.visit(statement)
            return
        self.visit(node.test)
        self._visit_unknown_branch(node.body)
        self._visit_unknown_branch(node.orelse)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.local_helpers[node.name] = node
        _set_alias(self.scope, (node.name,), (node.name,))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.local_helpers[node.name] = node
        _set_alias(self.scope, (node.name,), (node.name,))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        del node

    def visit_Lambda(self, node: ast.Lambda) -> None:
        del node

    def visit_Call(self, node: ast.Call) -> None:
        helper_name = self._local_helper_alias_name(_raw_called_name(node))
        if helper_name is None:
            helper_name = self._local_helper_name(_called_name(node, self.scopes))
        if helper_name is None or helper_name not in self.local_helpers or helper_name in self.active_helpers:
            self.generic_visit(node)
            return
        helper = self.local_helpers[helper_name]
        bindings = _call_argument_bindings(helper, node)
        if bindings is None:
            self.generic_visit(node)
            return
        call_scope = _function_call_scope(helper, bindings, self.scopes)
        helper_self_names = self._helper_self_names(bindings)
        self.active_helpers.add(helper_name)
        original_self_names = self.self_names
        self.self_names = self.self_names | helper_self_names
        self.scopes.append(call_scope)
        try:
            for statement in helper.body:
                self.visit(statement)
        finally:
            self.scopes.pop()
            self.self_names = original_self_names
            self.active_helpers.remove(helper_name)

    def _record_instance_aliases(self, targets: list[ast.expr], value: ast.expr) -> None:
        if len(targets) == 1 and isinstance(targets[0], ast.Tuple | ast.List) and isinstance(value, ast.Tuple | ast.List):
            for target, element in zip(targets[0].elts, value.elts, strict=False):
                self._record_instance_aliases([target], element)
            return

        source = _alias_source(value, self.scopes)
        for target in targets:
            target_path = _attribute_path(target)
            if len(target_path) <= 1 or target_path[0] not in self.self_names:
                continue
            instance_path = target_path[1:]
            if source in _ALIASABLE_CLOCK_PATHS:
                self.aliases[instance_path] = source
            else:
                self.aliases.pop(instance_path, None)

    def _record_helper_aliases(self, targets: list[ast.expr], value: ast.expr) -> None:
        source = _attribute_path(value)
        helper_name = source[0] if len(source) == 1 and source[0] in self.local_helpers else None
        for target in targets:
            target_path = _attribute_path(target)
            if len(target_path) == 1:
                if helper_name is None:
                    self.local_helper_aliases.pop(target_path[0], None)
                else:
                    self.local_helper_aliases[target_path[0]] = helper_name

    def _local_helper_name(self, name: str | None) -> str | None:
        if name is None:
            return None
        return self.local_helper_aliases.get(name, name)

    def _local_helper_alias_name(self, name: str | None) -> str | None:
        if name is None:
            return None
        return self.local_helper_aliases.get(name)

    def _visit_unknown_branch(self, statements: list[ast.stmt]) -> None:
        branch_scope: _AliasMap = {}
        self.scopes.append(branch_scope)
        for statement in statements:
            self.visit(statement)
        self.scopes.pop()
        _merge_clock_aliases(self.scope, branch_scope)

    def _helper_self_names(
        self,
        bindings: dict[str, ast.expr],
    ) -> set[str]:
        helper_self_names: set[str] = set()
        self_paths = {(name,) for name in self.self_names}
        for helper_arg, call_arg in bindings.items():
            if _attribute_path(call_arg) in self_paths:
                helper_self_names.add(helper_arg)
        return helper_self_names


class _FunctionBindingVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()
        self.global_names: set[str] = set()
        self.nonlocal_names: set[str] = set()

    def visit_Global(self, node: ast.Global) -> None:
        self.global_names.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocal_names.update(node.names)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.names.add(alias.asname or alias.name.split(".", 1)[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != "*":
                self.names.add(alias.asname or alias.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        del node

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            _add_bound_target_names(target, self.names)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        _add_bound_target_names(node.target, self.names)
        if node.value is not None:
            self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        _add_bound_target_names(node.target, self.names)
        self.visit(node.value)

    def visit_For(self, node: ast.For) -> None:
        self._visit_for(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_for(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_with(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_with(node)

    def _visit_for(self, node: ast.For | ast.AsyncFor) -> None:
        _add_bound_target_names(node.target, self.names)
        self.visit(node.iter)
        for statement in node.body:
            self.visit(statement)
        for statement in node.orelse:
            self.visit(statement)

    def _visit_with(self, node: ast.With | ast.AsyncWith) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                _add_bound_target_names(item.optional_vars, self.names)
        for statement in node.body:
            self.visit(statement)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        _add_bound_target_names(node.target, self.names)
        self.visit(node.value)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name is not None:
            self.names.add(node.name)
        for statement in node.body:
            self.visit(statement)


def _argument_names(arguments: ast.arguments) -> set[str]:
    names = {
        arg.arg
        for arg in (
            *arguments.posonlyargs,
            *arguments.args,
            *arguments.kwonlyargs,
        )
    }
    if arguments.vararg is not None:
        names.add(arguments.vararg.arg)
    if arguments.kwarg is not None:
        names.add(arguments.kwarg.arg)
    return names


def _add_bound_target_names(target: ast.expr, names: set[str]) -> None:
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, ast.Tuple | ast.List):
        for element in target.elts:
            _add_bound_target_names(element, names)


def _assignment_target_paths(target: ast.expr) -> list[tuple[str, ...]]:
    if isinstance(target, ast.Tuple | ast.List):
        paths: list[tuple[str, ...]] = []
        for element in target.elts:
            paths.extend(_assignment_target_paths(element))
        return paths
    target_path = _attribute_path(target)
    if target_path:
        return [target_path]
    return []


def _called_name(node: ast.Call, scopes: list[_AliasMap]) -> str | None:
    path = _normalize_alias(_attribute_path(node.func), scopes)
    if len(path) == 1:
        return path[0]
    return None


def _raw_called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _attribute_path(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.NamedExpr):
        target_path = _attribute_path(current.target)
        if target_path:
            return target_path + tuple(reversed(parts))
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return tuple(reversed(parts))
