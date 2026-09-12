"""AST support for the live coord-read authority gate.

This module deliberately owns no tests.  The production-corpus gate lives in
``test_coord_read_residuals_closeout.py``; keeping synthetic self-tests here
duplicated its detector rather than protecting another behavior.
"""

from __future__ import annotations

import ast

from mission_runtime import MissionArtifactKind, is_primary_artifact_kind

_TOPOLOGY_ROUTED_READ_RESOLVERS = frozenset(
    {
        "_find_feature_directory",
        "resolve_handle_to_read_path",
        "resolve_feature_dir_for_mission",
        "resolve_feature_dir_for_slug",
        "candidate_feature_dir_for_mission",
    }
)
_COORD_AWARE_CALLSHAPE_RESOLVERS = _TOPOLOGY_ROUTED_READ_RESOLVERS | frozenset(
    {"_resolve_setup_plan_feature_dir"}
)
_PRIMARY_FOLD_CALLSHAPE_FUNCS = frozenset(
    {
        "_canonicalize_primary_read_handle",
        "primary_feature_dir_for_mission",
        "resolve_planning_read_dir",
    }
)
_IDENTITY_READ_FUNCS = frozenset(
    {"resolve_mission_identity", "get_mission_type"}
)
_LANES_READ_FUNCS = frozenset({"read_lanes_json", "require_lanes_json"})
_SANCTIONED_PRIMARY_ATTRS = frozenset({"target_feature_dir"})
_READ_FIRST_ARG_KEYWORDS = frozenset({"feature_dir"})


def _call_func_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _read_dir_kind_arg(call: ast.Call) -> ast.expr | None:
    if _call_func_name(call) != "read_dir":
        return None
    if call.args:
        return call.args[0]
    return next((kw.value for kw in call.keywords if kw.arg == "kind"), None)


def _kind_expr_member(kind_expr: ast.expr) -> MissionArtifactKind | None:
    if isinstance(kind_expr, ast.Attribute):
        name = kind_expr.attr
    elif isinstance(kind_expr, ast.Name):
        name = kind_expr.id
    else:
        return None
    member = getattr(MissionArtifactKind, name, None)
    return member if isinstance(member, MissionArtifactKind) else None


def _is_primary_partition_read_dir_call(call: ast.Call) -> bool:
    kind_expr = _read_dir_kind_arg(call)
    if kind_expr is None or (member := _kind_expr_member(kind_expr)) is None:
        return False
    return is_primary_artifact_kind(member)


def _names_bound_from_primary_read_dir(func: ast.AST) -> set[str]:
    bound: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value.value if isinstance(node.value, ast.Attribute) else node.value
        if not isinstance(value, ast.Call) or not _is_primary_partition_read_dir_call(
            value
        ):
            continue
        bound.update(
            target.id for target in node.targets if isinstance(target, ast.Name)
        )
    return bound


def _find_function(
    tree: ast.AST, name: str
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    return next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == name
        ),
        None,
    )


def _names_bound_from(func: ast.AST, callees: frozenset[str]) -> set[str]:
    bound: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value.value if isinstance(node.value, ast.Attribute) else node.value
        if not isinstance(value, ast.Call) or _call_func_name(value) not in callees:
            continue
        bound.update(
            target.id for target in node.targets if isinstance(target, ast.Name)
        )
    return bound


def _attr_repr(node: ast.Attribute) -> str:
    if isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    return node.attr


def _param_position(
    func: ast.FunctionDef | ast.AsyncFunctionDef, name: str
) -> int | None:
    return next(
        (
            index
            for index, arg in enumerate([*func.args.posonlyargs, *func.args.args])
            if arg.arg == name
        ),
        None,
    )


def _is_parameter(func: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    return any(
        arg.arg == name
        for arg in (*func.args.posonlyargs, *func.args.args, *func.args.kwonlyargs)
    )


def _iter_module_functions(
    module: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in ast.walk(module)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def _caller_binds_arg_coord_aware(
    caller: ast.FunctionDef | ast.AsyncFunctionDef,
    callee_name: str,
    pos: int | None,
    param_name: str,
) -> bool:
    coord = _names_bound_from(caller, _COORD_AWARE_CALLSHAPE_RESOLVERS)
    primary = _names_bound_from(caller, _PRIMARY_FOLD_CALLSHAPE_FUNCS) | (
        _names_bound_from_primary_read_dir(caller)
    )
    for node in ast.walk(caller):
        if not isinstance(node, ast.Call) or _call_func_name(node) != callee_name:
            continue
        candidates: list[ast.expr] = []
        if pos is not None and pos < len(node.args):
            candidates.append(node.args[pos])
        candidates.extend(kw.value for kw in node.keywords if kw.arg == param_name)
        if any(
            isinstance(arg, ast.Name)
            and arg.id in coord
            and arg.id not in primary
            for arg in candidates
        ):
            return True
    return False


def _one_hop_caller_is_coord_aware(
    callee_func: ast.AST, param_name: str, module: ast.Module
) -> bool:
    if not isinstance(callee_func, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    if not _is_parameter(callee_func, param_name):
        return False
    pos = _param_position(callee_func, param_name)
    return any(
        caller is not callee_func
        and _caller_binds_arg_coord_aware(
            caller, callee_func.name, pos, param_name
        )
        for caller in _iter_module_functions(module)
    )


def _flag_name_arg(
    callee: str,
    name: str,
    *,
    func: ast.AST,
    coord_bound: set[str],
    primary_bound: set[str],
    module: ast.Module | None,
) -> str | None:
    if name in coord_bound and name not in primary_bound:
        return f"{callee}({name})"
    if module is not None and _one_hop_caller_is_coord_aware(func, name, module):
        return f"{callee}({name})"
    return None


def _flagged_first_arg(
    callee: str,
    first: ast.expr,
    *,
    func: ast.AST,
    coord_bound: set[str],
    primary_bound: set[str],
    module: ast.Module | None,
) -> str | None:
    if isinstance(first, ast.Name):
        return _flag_name_arg(
            callee,
            first.id,
            func=func,
            coord_bound=coord_bound,
            primary_bound=primary_bound,
            module=module,
        )
    if isinstance(first, ast.Call):
        inner = _call_func_name(first)
        if inner in _COORD_AWARE_CALLSHAPE_RESOLVERS:
            return f"{callee}({inner}(...))"
    elif (
        isinstance(first, ast.Attribute)
        and first.attr not in _SANCTIONED_PRIMARY_ATTRS
    ):
        return f"{callee}({_attr_repr(first)})"
    return None


def _read_call_first_arg(node: ast.Call) -> ast.expr | None:
    if node.args:
        return node.args[0]
    return next(
        (kw.value for kw in node.keywords if kw.arg in _READ_FIRST_ARG_KEYWORDS),
        None,
    )


def callshape_violations(
    func: ast.AST,
    *,
    read_funcs: frozenset[str],
    module: ast.Module | None = None,
) -> list[str]:
    """Return coord-aware identity/lanes reads lacking a primary fold."""
    coord_bound = _names_bound_from(func, _COORD_AWARE_CALLSHAPE_RESOLVERS)
    primary_bound = _names_bound_from(func, _PRIMARY_FOLD_CALLSHAPE_FUNCS) | (
        _names_bound_from_primary_read_dir(func)
    )
    violations: list[str] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call) or _call_func_name(node) not in read_funcs:
            continue
        first = _read_call_first_arg(node)
        if first is None:
            continue
        descriptor = _flagged_first_arg(
            _call_func_name(node) or "",
            first,
            func=func,
            coord_bound=coord_bound,
            primary_bound=primary_bound,
            module=module,
        )
        if descriptor is not None:
            violations.append(descriptor)
    return violations
