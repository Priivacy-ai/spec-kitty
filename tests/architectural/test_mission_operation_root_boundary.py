"""Repo-wide census for the caller-owned Mission operation boundary."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pytest


pytestmark = pytest.mark.architectural

_ROOT = Path(__file__).resolve().parents[2]
_RESOLVER = "resolve_mission_operation_context_cli"
_RAW_LOOKUPS = {
    "_find_mission_slug",
    "_resolve_mission_slug",
    "find_repo_root",
    "get_main_repo_root",
    "locate_project_root",
    "resolve_mission_handle",
}
_RAW_PATH_JOIN = "raw-path-join"
_KITTY_SPECS_NAMES = {
    "KITTY_SPECS_DIR",
    "_KITTY_SPECS_DIR",
    "kitty_specs_dir",
}
_MISSION_SELECTOR_NAMES = {
    "feature_slug",
    "handle",
    "mission_slug",
    "mission_slug_formatted",
    "raw_handle",
    "slug",
}


@dataclass(frozen=True, order=True)
class _CallSite:
    path: str
    function: str
    call: str


_EXPECTED_CONTEXT_BOUNDARIES = {
    _CallSite("src/specify_cli/cli/commands/agent/context.py", "resolve_context", _RESOLVER),
    _CallSite("src/specify_cli/cli/commands/agent/status.py", "_resolve_status_operation", _RESOLVER),
    _CallSite("src/specify_cli/cli/commands/agent/mission_setup_plan.py", "_resolve_setup_plan_operation", _RESOLVER),
    _CallSite("src/specify_cli/cli/commands/agent/tasks_shared.py", "_find_mission_slug", _RESOLVER),
    _CallSite("src/specify_cli/cli/commands/agent/tasks_status_cmd.py", "_st_resolve_dirs", _RESOLVER),
    _CallSite("src/specify_cli/cli/commands/agent/workflow.py", "implement", _RESOLVER),
    _CallSite("src/specify_cli/cli/commands/agent/workflow.py", "review", _RESOLVER),
    _CallSite("src/specify_cli/cli/commands/next_cmd.py", "next_step", _RESOLVER),
    _CallSite("src/specify_cli/cli/commands/accept.py", "accept", _RESOLVER),
}

# Shrink-only baseline: removing one of these legacy fallbacks is allowed, but
# adding another raw root/selector authority anywhere in the lifecycle census
# fails. Counts matter, so duplicating an already-allowed call also fails.
_ALLOWLIST_PATH = (
    Path(__file__).parent / "fixtures" / "mission_root_authority_allowlist.tsv"
)


def _load_foundation_lookup_allowlist() -> Counter[_CallSite]:
    """Load the static shrink-only baseline for the repo-wide census."""
    allowed: Counter[_CallSite] = Counter()
    for line in _ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        count_text, path, function, call = line.split("\t")
        allowed[_CallSite(path, function, call)] = int(count_text)
    return allowed


_FOUNDATION_LOOKUP_ALLOWLIST = _load_foundation_lookup_allowlist()


def _call_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _names_in(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _contains_kitty_specs(node: ast.AST) -> bool:
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
        return False
    if _names_in(node.right) & _KITTY_SPECS_NAMES:
        return True
    if isinstance(node.right, ast.Constant) and node.right.value == "kitty-specs":
        return True
    return _contains_kitty_specs(node.left)


def _raw_path_join_selector(node: ast.BinOp) -> str | None:
    if not isinstance(node.op, ast.Div):
        return None
    if isinstance(node.right, ast.Name) and node.right.id in _MISSION_SELECTOR_NAMES:
        return node.right.id
    if (
        isinstance(node.right, ast.Attribute)
        and node.right.attr in _MISSION_SELECTOR_NAMES
    ):
        return node.right.attr
    return None


def _enclosing_function(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> str:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
    return "<module>"


def _census(sources: dict[str, str]) -> Counter[_CallSite]:
    found: Counter[_CallSite] = Counter()
    for path, source in sources.items():
        tree = ast.parse(source, filename=path)
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                selector = _raw_path_join_selector(node)
                if selector is not None and _contains_kitty_specs(node.left):
                    found[
                        _CallSite(
                            path,
                            _enclosing_function(node, parents),
                            _RAW_PATH_JOIN,
                        )
                    ] += 1
                continue
            if not isinstance(node, ast.Call):
                continue
            call = _call_name(node)
            if call not in _RAW_LOOKUPS | {_RESOLVER}:
                continue
            found[_CallSite(path, _enclosing_function(node, parents), call)] += 1
    return found


def _production_sources() -> dict[str, str]:
    return {
        path.relative_to(_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((_ROOT / "src").rglob("*.py"))
    }


def test_context_boundary_census_covers_every_lifecycle_family() -> None:
    census = _census(_production_sources())
    actual = {site for site in census if site.call == _RESOLVER}

    assert actual == _EXPECTED_CONTEXT_BOUNDARIES


def test_raw_root_authorities_only_shrink_from_foundation_allowlist() -> None:
    census = _census(_production_sources())
    actual = Counter(
        {
            site: count
            for site, count in census.items()
            if site.call in _RAW_LOOKUPS | {_RAW_PATH_JOIN}
        }
    )

    assert actual - _FOUNDATION_LOOKUP_ALLOWLIST == Counter()


def test_census_detects_second_root_authority_mutation() -> None:
    sources = _production_sources()
    path = "src/specify_cli/cli/commands/agent/mission_branch_context.py"
    needle = "main_repo_root = _mission.get_main_repo_root(repo_root)"
    assert needle in sources[path]
    sources[path] = sources[path].replace(
        needle,
        needle + "\n    get_main_repo_root(repo_root)",
        1,
    )

    census = _census(sources)
    actual = Counter(
        {site: count for site, count in census.items() if site.call in _RAW_LOOKUPS}
    )

    assert actual - _FOUNDATION_LOOKUP_ALLOWLIST == Counter(
        {
            _CallSite(
                path,
                "_show_branch_context",
                "get_main_repo_root",
            ): 1
        }
    )


def test_census_detects_raw_path_join_mutation() -> None:
    sources = _production_sources()
    path = "src/specify_cli/cli/commands/agent/mission_branch_context.py"
    needle = "main_repo_root = _mission.get_main_repo_root(repo_root)"
    assert needle in sources[path]
    sources[path] = sources[path].replace(
        needle,
        needle + "\n    repo_root / KITTY_SPECS_DIR / mission_slug",
        1,
    )

    census = _census(sources)
    actual = Counter(
        {
            site: count
            for site, count in census.items()
            if site.call in _RAW_LOOKUPS | {_RAW_PATH_JOIN}
        }
    )

    assert actual - _FOUNDATION_LOOKUP_ALLOWLIST == Counter(
        {
            _CallSite(
                path,
                "_show_branch_context",
                _RAW_PATH_JOIN,
            ): 1
        }
    )
