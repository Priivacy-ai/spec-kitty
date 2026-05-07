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
        ``dashboard.api.models``, and ``dashboard.file_reader``. This test
        confirms those imports actually resolve at runtime so the architectural
        rule cannot regress accidentally (e.g., via a circular re-export).

        Note: ``dashboard.api_types`` was deleted as part of the FastAPI
        transport migration (WP07). All TypedDicts now live in their canonical
        packages (``kernel.api_types``, ``specify_cli.missions.api_types``,
        ``dashboard.api.presentation_types``, etc.).
        """
        # If any of these imports raise, pytest reports a clear failure
        # naming the offending module.
        import dashboard.api  # noqa: F401
        import dashboard.api.models  # noqa: F401
        import dashboard.file_reader  # noqa: F401
        import dashboard.services.mission_scan  # noqa: F401
        import dashboard.services.project_state  # noqa: F401
        import dashboard.services.sync  # noqa: F401

        # Sanity: the public ``create_app`` symbol must round-trip through
        # ``dashboard.api`` so the WP02 scaffold contract still holds.
        from dashboard.api import create_app

        assert callable(create_app), "dashboard.api.create_app must be callable"


def test_no_upstream_dashboard_imports() -> None:
    """Enforce C-009: specify_cli and kernel must not import from dashboard.

    The dashboard package is a presentation/adapter layer. Core packages
    (specify_cli, kernel) must never depend on it — doing so would invert
    the dependency arrow and create a circular coupling.

    Intentional exceptions (explicit allow-list, narrowed in WP04 of
    ``dashboard-services-domain-migration-01KR151P``):
    - ``specify_cli/dashboard/server.py`` — bootstraps the FastAPI app via a
      lazy ``from dashboard.api import create_app`` to keep the legacy
      ``BaseHTTPRequestHandler`` path import-free.
    - ``specify_cli/dashboard/api_types.py`` — re-exports presentation
      TypedDicts from ``dashboard.api.presentation_types`` for legacy
      consumers; this module is the canonical bridge.
    - ``specify_cli/dashboard/handlers/features.py`` — uses a lazy
      ``from dashboard.file_reader import DashboardFileReader`` to read
      kanban artifacts on demand. Cannot be inverted without restructuring
      the legacy adapter; tracked for future cleanup.

    NOTE: the previous broad skip-everything-under ``specify_cli/dashboard/``
    rule and the ``specify_cli/cli/commands/dashboard.py`` exemption were
    BOTH removed in WP04 (mission ``dashboard-services-domain-migration-01KR151P``)
    so that newly added files in those locations cannot regress C-009 silently.
    """
    import ast
    from pathlib import Path

    src_root = Path(__file__).resolve().parents[2] / "src"

    # Boundary modules intentionally allowed to cross the specify_cli ↔ dashboard line.
    # Tightened in WP04: every entry is a specific file with a known, justified
    # bridge import. New violations elsewhere will fail the test.
    _ALLOWED_BOUNDARY_FILES = frozenset({
        src_root / "specify_cli" / "dashboard" / "server.py",
        src_root / "specify_cli" / "dashboard" / "api_types.py",
        src_root / "specify_cli" / "dashboard" / "handlers" / "features.py",
    })

    violations: list[str] = []

    for pkg in ("specify_cli", "kernel"):
        pkg_root = src_root / pkg
        if not pkg_root.exists():
            continue
        for py_file in sorted(pkg_root.rglob("*.py")):
            if py_file in _ALLOWED_BOUNDARY_FILES:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    # Skip relative imports (level > 0): a `from ..dashboard.foo`
                    # inside specify_cli/something/ resolves to a sibling under
                    # specify_cli/, not to the top-level `dashboard` package.
                    if node.level and node.level > 0:
                        continue
                    if node.module == "dashboard" or node.module.startswith("dashboard."):
                        rel = py_file.relative_to(src_root)
                        violations.append(
                            f"  {rel}:{node.lineno}: imports from '{node.module}'"
                        )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "dashboard" or alias.name.startswith("dashboard."):
                            rel = py_file.relative_to(src_root)
                            violations.append(
                                f"  {rel}:{node.lineno}: imports '{alias.name}'"
                            )

    assert not violations, (
        "C-009 violation: specify_cli/* and kernel/* must not import from dashboard/*.\n"
        "Fix: move shared types to kernel.api_types, specify_cli.missions.api_types,\n"
        "or another canonical package that dashboard can depend on.\n"
        "Violations:\n" + "\n".join(violations)
    )


def test_boundary_check_catches_dashboard_import(tmp_path: Path) -> None:
    """Synthetic-violation fixture: the C-009 boundary checker must detect
    a planted ``from dashboard.*`` import in a file outside the allow-list.

    This is the regression guard for WP04 of mission
    ``dashboard-services-domain-migration-01KR151P``: it proves the AST scan
    used by ``test_no_upstream_dashboard_imports`` will fire when (not if)
    a future change reintroduces an inverted-dependency import.
    """
    fake_file = tmp_path / "fake_domain_module.py"
    fake_file.write_text("from dashboard.services.registry import MissionRegistry\n")
    violations: list[str] = []
    tree = ast.parse(fake_file.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "dashboard" or node.module.startswith("dashboard."):
                violations.append(f"{fake_file}:{node.lineno}: {node.module}")
    assert violations, "Boundary checker failed to detect synthetic violation"
