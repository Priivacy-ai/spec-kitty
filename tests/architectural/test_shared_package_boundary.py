"""Negative import-boundary contracts for retired shared-package surfaces."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_PRODUCTION_ROOTS = tuple(_SRC / name for name in ("specify_cli", "runtime", "charter", "doctrine", "kernel"))
_TRACKER_PUBLIC_SURFACE = frozenset({"FieldOwner", "OwnershipMode", "OwnershipPolicy", "SyncEngine", "ExternalRef"})


def _forbidden_imports(roots: tuple[Path, ...], prefix: str) -> list[str]:
    offenders: list[str] = []
    for root in roots:
        paths = [root] if root.is_file() else root.rglob("*.py")
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    if name == prefix or name.startswith(prefix + "."):
                        offenders.append(f"{path}:{node.lineno}:{name}")
    return offenders


def _assert_live_negative_import_guard(
    tmp_path: Path,
    forbidden_prefix: str,
) -> None:
    assert sum(1 for root in _PRODUCTION_ROOTS for _ in root.rglob("*.py")) > 0
    assert _forbidden_imports(_PRODUCTION_ROOTS, forbidden_prefix) == []

    planted = tmp_path / "planted.py"
    planted.write_text(f"from {forbidden_prefix}.removed import symbol\n", encoding="utf-8")
    assert _forbidden_imports((planted,), forbidden_prefix)

    clean = tmp_path / "clean.py"
    clean.write_text("from spec_kitty_events import Event\n", encoding="utf-8")
    assert _forbidden_imports((clean,), forbidden_prefix) == []


def test_production_never_imports_retired_runtime_package(tmp_path: Path) -> None:
    _assert_live_negative_import_guard(tmp_path, "spec_kitty_runtime")


def test_production_never_imports_retired_vendored_events(tmp_path: Path) -> None:
    _assert_live_negative_import_guard(tmp_path, "specify_cli.spec_kitty_events")


def _tracker_reexports(
    cli_namespace: dict[str, object],
    upstream_namespace: dict[str, object],
    names: frozenset[str],
) -> set[str]:
    raw_declared = cli_namespace.get("__all__", ())
    declared = {str(name) for name in raw_declared} if isinstance(raw_declared, (list, tuple, set, frozenset)) else set()
    return {
        name for name in names if name in declared or (name in cli_namespace and name in upstream_namespace and cli_namespace[name] is upstream_namespace[name])
    }


def test_cli_tracker_does_not_reexport_public_sdk() -> None:
    cli_tracker = importlib.import_module("specify_cli.tracker")
    upstream = importlib.import_module("spec_kitty_tracker")
    assert _TRACKER_PUBLIC_SURFACE
    assert _tracker_reexports(vars(cli_tracker), vars(upstream), _TRACKER_PUBLIC_SURFACE) == set()

    victim = next(name for name in _TRACKER_PUBLIC_SURFACE if hasattr(upstream, name))
    incompatible = dict(vars(cli_tracker))
    incompatible[victim] = getattr(upstream, victim)
    assert _tracker_reexports(incompatible, vars(upstream), _TRACKER_PUBLIC_SURFACE) == {victim}
