from __future__ import annotations

import ast
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
    for path in sorted({Path(p) for p in paths}):
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _WallClockAssertionVisitor(path)
        visitor.visit(tree)
        violations.extend(visitor.violations)
    return sorted(violations)


def find_test_python_paths(root: Path) -> list[Path]:
    """Return every Python file under the test tree, including helper modules."""
    return sorted(path for path in root.rglob("*.py") if path.is_file())


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
        if _is_static_false(node.test) or _is_type_checking_name(node.test):
            for statement in node.orelse:
                self.visit(statement)
            return
        if _is_static_true(node.test):
            for statement in node.body:
                self.visit(statement)
            return
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.scopes.append({(name,): None for name in _argument_names(node.args)})
        self.visit(node.body)
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
    def __init__(self, path: Path) -> None:
        self.path = path
        self.violations: list[WallClockAssertionViolation] = []
        self.scopes: list[_AliasMap] = [{}]
        self.global_names_stack: list[set[str]] = []
        self.propagate_global_stack: list[bool] = []

    @property
    def scope(self) -> _AliasMap:
        return self.scopes[-1]

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
            if parts and parts[0] in {"datetime", "time"}:
                self._set_alias((alias.asname or parts[0],), parts)
            else:
                self._set_shadow((alias.asname or parts[0],))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
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

    def visit_Assign(self, node: ast.Assign) -> None:
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
        if _is_static_false(node.test) or _is_type_checking_name(node.test):
            for statement in node.orelse:
                self.visit(statement)
            return
        if _is_static_true(node.test):
            for statement in node.body:
                self.visit(statement)
            return
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_scope(node, bind_name=True)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_scope(node, bind_name=True)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._set_shadow((node.name,))
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
        for method in deferred_methods:
            if method.name in _SETUP_METHOD_NAMES:
                class_aliases.update(_method_instance_aliases(method, self.scopes, class_aliases))
        for method in deferred_methods:
            self._visit_function_scope(
                method,
                bind_name=False,
                class_aliases=class_aliases,
            )

    def _visit_function_scope(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        bind_name: bool,
        class_aliases: dict[tuple[str, ...], tuple[str, ...]] | None = None,
    ) -> None:
        if bind_name:
            self._set_shadow((node.name,))
        local_shadows: _AliasMap = {(name,): None for name in _function_bound_names(node)}
        local_shadows.update(_function_default_aliases(node, self.scopes))
        if class_aliases:
            for self_name in _method_self_names(node):
                for path, source in class_aliases.items():
                    local_shadows[(self_name, *path)] = source
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


def _add_star_import_aliases(
    aliases: _AliasMap,
    module: str | None,
) -> None:
    if module == "time":
        aliases[("time",)] = ("time", "time")
    elif module == "datetime":
        aliases[("datetime",)] = ("datetime", "datetime")
        aliases[("date",)] = ("datetime", "date")


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


def _is_type_checking_name(node: ast.AST) -> bool:
    return _attribute_path(node) in {("TYPE_CHECKING",), ("typing", "TYPE_CHECKING")}


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
    aliases: _AliasMap = {}
    positional_args = (*node.args.posonlyargs, *node.args.args)
    default_offset = len(positional_args) - len(node.args.defaults)
    for arg, default in zip(positional_args[default_offset:], node.args.defaults, strict=False):
        source = _alias_source(default, scopes)
        if source in _ALIASABLE_CLOCK_PATHS:
            aliases[(arg.arg,)] = source

    for arg, kw_default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True):
        if kw_default is None:
            continue
        source = _alias_source(kw_default, scopes)
        if source in _ALIASABLE_CLOCK_PATHS:
            aliases[(arg.arg,)] = source
    return aliases


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
) -> dict[tuple[str, ...], tuple[str, ...]]:
    self_names = _method_self_names(node)
    aliases: dict[tuple[str, ...], tuple[str, ...]] = {}
    if not self_names:
        return aliases

    collector = _MethodInstanceAliasCollector(scopes, class_aliases, self_names, node)
    for statement in node.body:
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
        local_scope: _AliasMap = {(name,): None for name in _function_bound_names(node)}
        for self_name in self_names:
            for path, source in class_aliases.items():
                local_scope[(self_name, *path)] = source
        self.scopes = [*scopes, local_scope]

    @property
    def scope(self) -> _AliasMap:
        return self.scopes[-1]

    def visit_Assign(self, node: ast.Assign) -> None:
        self._record_instance_aliases(node.targets, node.value)
        _add_assignment_aliases(self.scopes, lambda _: self.scope, node.targets, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is None:
            return
        self._record_instance_aliases([node.target], node.value)
        _add_assignment_aliases(self.scopes, lambda _: self.scope, [node.target], node.value)

    def visit_If(self, node: ast.If) -> None:
        if _is_static_false(node.test) or _is_type_checking_name(node.test):
            for statement in node.orelse:
                self.visit(statement)
            return
        if _is_static_true(node.test):
            for statement in node.body:
                self.visit(statement)
            return
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        del node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        del node

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        del node

    def visit_Lambda(self, node: ast.Lambda) -> None:
        del node

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
