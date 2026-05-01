"""Architectural guard: no dossier → sync import edges.

Enforces the boundary fixed in GitHub issue #862 (P1.2).
This test must remain in CI permanently to prevent regression.

Uses stdlib ``ast`` to walk ALL imports in every .py file under
src/specify_cli/dossier/, including:
- Module-level imports
- Imports inside ``if TYPE_CHECKING:`` blocks
- Lazy function-body imports

After P1.2 the dossier package emits events via
``specify_cli.dossier.emitter_adapter.fire_dossier_event``. The sync
package registers an emitter callable at startup; dossier never imports
sync directly.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
DOSSIER_PATH = SRC / "specify_cli" / "dossier"

pytestmark = pytest.mark.architectural


def _collect_imports(package_path: Path) -> list[tuple[str, str]]:
    """Return (source_file, imported_module) for all imports in a package.

    Walks the full AST including function bodies and TYPE_CHECKING blocks.
    """
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


class TestDossierSyncBoundary:
    """specify_cli.dossier must not import specify_cli.sync."""

    def test_dossier_does_not_import_sync(self) -> None:
        """No dossier module may import from specify_cli.sync (any sub-module).

        Catches all import shapes (module-level, TYPE_CHECKING, lazy
        function-body). Zero exceptions are allowed.
        """
        edges = _collect_imports(DOSSIER_PATH)
        violations = [
            f"  {src}: imports '{mod}'"
            for src, mod in edges
            if mod == "specify_cli.sync" or mod.startswith("specify_cli.sync.")
        ]
        assert not violations, (
            "specify_cli.dossier must not import specify_cli.sync.\n"
            "Violations found (including lazy and TYPE_CHECKING imports):\n"
            + "\n".join(violations)
            + "\n\nFix: route through specify_cli.dossier.emitter_adapter "
            "(or import from specify_cli.identity.project for ProjectIdentity)."
        )

    def test_dossier_path_exists(self) -> None:
        """Sanity check: dossier package must exist so the boundary test is non-vacuous."""
        assert DOSSIER_PATH.is_dir(), (
            f"specify_cli.dossier not found at {DOSSIER_PATH}. "
            "Update SRC or DOSSIER_PATH if the package moved."
        )
