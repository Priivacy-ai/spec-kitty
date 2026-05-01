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
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                edges.append((str(py_file.relative_to(SRC)), node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append((str(py_file.relative_to(SRC)), alias.name))
    return edges


class TestStatusSyncBoundary:
    """specify_cli.status must not import specify_cli.sync."""

    def test_status_does_not_import_sync(self) -> None:
        """No status module may import from specify_cli.sync (any sub-module)."""
        edges = _collect_imports(STATUS_PATH)
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

    def test_status_path_exists(self) -> None:
        """Sanity check: status package must exist so the boundary test is non-vacuous."""
        assert STATUS_PATH.is_dir(), (
            f"specify_cli.status not found at {STATUS_PATH}. "
            "Update SRC or STATUS_PATH if the package moved."
        )
