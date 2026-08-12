"""Keep mission discovery on the resolver boundary.

Authority: ``docs/adr/3.x/2026-07-08-1-mission-resolver-port.md``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
_SANCTIONED_RESOLVER_MODULE = "src/specify_cli/context/mission_resolver.py"
_LEGACY_WALKER_ALLOWLIST = frozenset(
    {
        "src/specify_cli/status/identity_audit.py",
        "src/specify_cli/merge/ordering.py",
        "src/specify_cli/core/paths.py",
        "src/specify_cli/charter_activate.py",
        "src/specify_cli/cli/commands/materialize.py",
        "src/specify_cli/cli/commands/_coordination_doctor.py",
        "src/specify_cli/cli/commands/_review_cycle_reconcile_doctor.py",
        "src/specify_cli/cli/commands/_identity_audit.py",
        "src/specify_cli/cli/commands/agent/mission_feature_resolution.py",
        "src/specify_cli/git/sparse_checkout.py",
        "src/specify_cli/release/changelog.py",
        "src/specify_cli/missions/_read_path_resolver.py",
        "src/specify_cli/manifest.py",
        "src/specify_cli/dashboard/scanner.py",
        "src/specify_cli/audit/engine.py",
        "src/specify_cli/cli/commands/validate_tasks.py",
        "src/specify_cli/cli/commands/validate_encoding.py",
        "src/specify_cli/cli/commands/mission_type.py",
        "src/specify_cli/cli/commands/migrate/charter_encoding.py",
        "src/specify_cli/cli/commands/migrate/backfill_provenance.py",
        "src/specify_cli/retrospective/generator.py",
        "src/specify_cli/tasks/issue_matrix_migration.py",
    }
)
_MIGRATION_WALKER_DIR_PREFIXES = (
    "src/specify_cli/upgrade/migrations/",
    "src/specify_cli/migration/",
)
_ENUMERATION_METHODS = frozenset({"iterdir", "glob", "scandir"})
_SPECS_NAME_VOCABULARY = frozenset(
    {
        "specs_dir",
        "mission_specs_dir",
        "mission_specs",
        "specs_root",
        "kitty_specs_dir",
        "kitty_specs",
        "wt_specs",
        "root_specs",
        "scan_specs",
        "main_specs",
        "scan_root",
    }
)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _is_allowlisted(rel: str) -> bool:
    return (
        rel == _SANCTIONED_RESOLVER_MODULE
        or rel in _LEGACY_WALKER_ALLOWLIST
        or any(rel.startswith(prefix) for prefix in _MIGRATION_WALKER_DIR_PREFIXES)
    )


def _references_kitty_specs(node: ast.AST) -> bool:
    return any(
        (isinstance(item, ast.Name) and item.id == "KITTY_SPECS_DIR")
        or (isinstance(item, ast.Constant) and item.value == "kitty-specs")
        for item in ast.walk(node)
    )


def _tainted_names_in_file(tree: ast.AST) -> set[str]:
    tainted: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            tainted.update(arg.arg for arg in args if arg.arg in _SPECS_NAME_VOCABULARY)
        elif isinstance(node, ast.Assign) and _references_kitty_specs(node.value):
            tainted.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and isinstance(node.target, ast.Name)
            and _references_kitty_specs(node.value)
        ):
            tainted.add(node.target.id)
    return tainted


def _find_raw_walker_calls(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tainted = _tainted_names_in_file(tree)
    return [
        (node.lineno, node.func.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _ENUMERATION_METHODS
        and (
            (isinstance(node.func.value, ast.Name) and node.func.value.id in tainted)
            or _references_kitty_specs(node.func.value)
        )
    ]


def _scan_tree_for_violations(src_root: Path) -> dict[str, list[tuple[int, str]]]:
    violations: dict[str, list[tuple[int, str]]] = {}
    for path in sorted(src_root.rglob("*.py")):
        rel = _rel(path)
        if not _is_allowlisted(rel) and (hits := _find_raw_walker_calls(path)):
            violations[rel] = hits
    return violations


def test_no_unsanctioned_raw_kitty_specs_enumeration_in_src() -> None:
    """Reject a new raw mission-directory walk outside reviewed boundaries."""
    scanned = list(_SRC_ROOT.rglob("*.py"))
    assert scanned, "src/ corpus is empty; the architectural gate did not execute"
    violations = _scan_tree_for_violations(_SRC_ROOT)
    assert not violations, (
        "Raw kitty-specs enumeration bypasses MissionResolver; route the read "
        f"through the resolver or document a distinct corpus walk: {violations}"
    )
