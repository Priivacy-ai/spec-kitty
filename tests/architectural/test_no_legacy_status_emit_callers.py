"""Architectural guardrail for transactional status emits.

Production status writes must route through
``coordination.status_transition`` so outbound fanout is deferred until
``BookkeepingTransaction`` commits successfully.  The legacy
``status.emit.emit_status_transition`` functions remain as compatibility
wrappers, but new production call sites must not use them directly.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src" / "specify_cli"
_LEGACY_NAMES = {"emit_status_transition", "emit_status_transition_batch"}
_ALLOWED = {
    _SRC_ROOT / "coordination" / "status_transition.py",
    _SRC_ROOT / "status" / "emit.py",
    _SRC_ROOT / "status" / "__init__.py",
}


def _legacy_status_emit_uses(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    imported_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "specify_cli.status.emit":
            for alias in node.names:
                if alias.name in _LEGACY_NAMES:
                    imported_aliases.add(alias.asname or alias.name)
                    hits.append(f"{path}:{node.lineno} imports {alias.name}")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in imported_aliases:
            hits.append(f"{path}:{node.lineno} calls {func.id}")
        elif isinstance(func, ast.Attribute) and func.attr in _LEGACY_NAMES:
            hits.append(f"{path}:{node.lineno} calls .{func.attr}")
    return hits


def test_production_code_has_no_legacy_status_emit_callers() -> None:
    offenders: list[str] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        if path in _ALLOWED:
            continue
        offenders.extend(_legacy_status_emit_uses(path))

    assert not offenders, (
        "Production status transitions must use "
        "coordination.status_transition + BookkeepingTransaction.append_event:\n"
        + "\n".join(offenders)
    )
