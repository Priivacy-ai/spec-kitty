"""Architectural guard: no status -> sync import edges.

Enforces the boundary fixed in GitHub issue #862 (P1.3). This test must
remain in CI permanently to prevent regression. Uses stdlib ``ast`` to
walk ALL imports in every .py file under src/specify_cli/status/,
including:
- Module-level imports
- Imports inside ``if TYPE_CHECKING:`` blocks
- Lazy function-body imports

After P1.3 the status package routes side-effects through
``specify_cli.status.adapters.fire_*``. The sync package registers
handlers at startup; status never depends on sync.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
STATUS_PATH = SRC / "specify_cli" / "status"

pytestmark = pytest.mark.architectural


def _collect_imports(package_path: Path) -> list[tuple[str, str]]:
    """Return (source_file, imported_module) for all imports in a package."""
    edges: list[tuple[str, str]] = []
    for py_file in sorted(package_path.rglob("*.py")):
        try:
            source_file = str(py_file.relative_to(SRC))
        except ValueError:
            source_file = str(py_file)
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                edges.append((source_file, node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append((source_file, alias.name))
    return edges


class TestStatusSyncBoundary:
    """specify_cli.status must not import specify_cli.sync."""

    def test_status_does_not_import_sync(self, tmp_path: Path) -> None:
        """Scan the live package and prove the oracle rejects a planted edge."""
        edges = _collect_imports(STATUS_PATH)
        assert edges, "status import corpus must be non-empty"
        violations = [
            f"  {src}: imports '{mod}'"
            for src, mod in edges
            if mod == "specify_cli.sync" or mod.startswith("specify_cli.sync.")
        ]
        assert not violations, (
            "specify_cli.status must not import specify_cli.sync.\n"
            "Violations found (including lazy and TYPE_CHECKING imports):\n"
            + "\n".join(violations)
            + "\n\nFix: route through specify_cli.status.adapters.fire_* instead."
        )

        control = tmp_path / "control"
        control.mkdir()
        (control / "module.py").write_text(
            "from specify_cli.status import adapters\n", encoding="utf-8"
        )
        assert not [mod for _, mod in _collect_imports(control) if mod.startswith("specify_cli.sync")]

        fault = tmp_path / "fault"
        fault.mkdir()
        (fault / "module.py").write_text(
            "from specify_cli.sync import emit\n", encoding="utf-8"
        )
        assert [mod for _, mod in _collect_imports(fault) if mod.startswith("specify_cli.sync")] == [
            "specify_cli.sync"
        ]
