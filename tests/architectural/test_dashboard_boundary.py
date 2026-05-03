"""Boundary test: src/dashboard/ must not import from src/specify_cli/dashboard/.

This prevents the circular dependency between the service layer and its own
CLI adapter. See research.md §4 for the staged-boundary rationale.

Uses stdlib ``ast`` to walk ALL import shapes (module-level, TYPE_CHECKING
blocks, lazy function-body imports) — consistent with test_dossier_sync_boundary.py.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
DASHBOARD_SRC = SRC / "dashboard"
FORBIDDEN_PREFIX = "specify_cli.dashboard"

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


class TestDashboardServiceBoundary:
    """src/dashboard/ must not import from src/specify_cli/dashboard/."""

    def test_dashboard_has_no_imports_from_specify_cli_dashboard(self) -> None:
        """No module in src/dashboard/ may import from specify_cli.dashboard.*.

        Catches all import shapes (module-level, TYPE_CHECKING, lazy
        function-body). Zero exceptions are allowed.
        """
        edges = _collect_imports(DASHBOARD_SRC)
        violations = [
            f"  {src}: imports '{mod}'"
            for src, mod in edges
            if mod == FORBIDDEN_PREFIX or mod.startswith(FORBIDDEN_PREFIX + ".")
        ]
        assert not violations, (
            "src/dashboard/ imports from src/specify_cli/dashboard/ (circular dependency).\n"
            "Violations found (including lazy and TYPE_CHECKING imports):\n"
            + "\n".join(violations)
            + "\n\nFix: import from specify_cli.scanner, specify_cli.mission, "
            "specify_cli.sync, etc. (not from specify_cli.dashboard.*)."
        )

    def test_dashboard_package_exists(self) -> None:
        """Sanity: src/dashboard/ must exist so the boundary test is non-vacuous."""
        assert DASHBOARD_SRC.is_dir(), (
            f"src/dashboard/ not found at {DASHBOARD_SRC}. "
            "Update SRC or DASHBOARD_SRC if the package moved."
        )

    def test_boundary_would_catch_forbidden_import(self) -> None:
        """Meta-test: verify the AST scan detects a forbidden import in synthetic source."""
        forbidden_src = "from specify_cli.dashboard.scanner import scan_all_features\n"
        tree = ast.parse(forbidden_src)
        modules = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        assert any(m.startswith(FORBIDDEN_PREFIX) for m in modules), (
            "Meta-test failed: AST scan did not detect the injected forbidden import"
        )

    def test_dashboard_api_can_import_dashboard_services(self) -> None:
        """Positive test: ``src/dashboard/api/`` may import sibling dashboard packages.

        The FR-010 boundary forbids imports *from* ``specify_cli.dashboard.*``
        but explicitly allows the new FastAPI subpackage to import sibling
        modules inside ``src/dashboard/`` itself: ``dashboard.services.*``,
        ``dashboard.api.models``, ``dashboard.api_types``, and
        ``dashboard.file_reader``. This test confirms those imports actually
        resolve at runtime so the architectural rule cannot regress
        accidentally (e.g., via a circular re-export).
        """
        # If any of these imports raise, pytest reports a clear failure
        # naming the offending module.
        import dashboard.api  # noqa: F401
        import dashboard.api.models  # noqa: F401
        import dashboard.api_types  # noqa: F401
        import dashboard.file_reader  # noqa: F401
        import dashboard.services.mission_scan  # noqa: F401
        import dashboard.services.project_state  # noqa: F401
        import dashboard.services.sync  # noqa: F401

        # Sanity: the public ``create_app`` symbol must round-trip through
        # ``dashboard.api`` so the WP02 scaffold contract still holds.
        from dashboard.api import create_app

        assert callable(create_app), "dashboard.api.create_app must be callable"
