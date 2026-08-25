"""Architectural guard: no dashboard → sync import edges.

Enforces the boundary created by the E4 re-homing (planning epic #4,
spec-kitty issue #2): after the re-homing, ``dashboard/`` owns its loopback
JSON probe and takes process liveness from ``core/process_liveness`` — it
borrows nothing from ``specify_cli.sync``. This gate is the revert detector
for that boundary: the first squad pass on PR [#2] showed every other guard
in the tree still passed with the pre-re-homing
``from specify_cli.sync.daemon import _fetch_health_payload`` restored in
``dashboard/lifecycle.py``.

Uses stdlib ``ast`` to walk ALL imports in every .py file under
src/specify_cli/dashboard/, including:
- Module-level imports
- Imports inside ``if TYPE_CHECKING:`` blocks
- Lazy function-body imports
- Relative imports (resolved against the importing module's package)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
DASHBOARD_PATH = SRC / "specify_cli" / "dashboard"

pytestmark = pytest.mark.architectural


def _import_base_package(relative_path: Path) -> tuple[str, ...]:
    """Dotted package an import statement in *relative_path* resolves against.

    ``dashboard/lifecycle.py`` → ``("specify_cli", "dashboard")``;
    ``dashboard/__init__.py`` → ``("specify_cli",)`` (a package's own
    ``__init__`` resolves level-1 relatives against its parent).
    """
    parts = relative_path.with_suffix("").parts
    if parts[-1] == "__init__":
        return parts[:-2]
    return parts[:-1]


def _resolve_import_target(module: str | None, level: int, relative_path: Path) -> str | None:
    """Absolute dotted name of an ``ImportFrom`` node, relatives included."""
    if level == 0:
        return module
    base = _import_base_package(relative_path)
    up = level - 1
    if up > len(base):
        return None
    stem = base[: len(base) - up] if up else base
    if module:
        return ".".join((*stem, module))
    return ".".join(stem) or None


def _collect_imports(package_path: Path, *, source_root: Path = SRC) -> list[tuple[str, str]]:
    """Return (source_file, imported_module) for all imports in a package.

    Walks the full AST including function bodies and TYPE_CHECKING blocks.
    """
    edges: list[tuple[str, str]] = []
    for py_file in sorted(package_path.rglob("*.py")):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        relative_path = py_file.relative_to(source_root)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                target = _resolve_import_target(node.module, node.level, relative_path)
                if target:
                    edges.append((str(relative_path), target))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append((str(relative_path), alias.name))
    return edges


def _sync_import_violations(package_path: Path, *, source_root: Path = SRC) -> list[str]:
    """Run the live dashboard-to-sync boundary oracle for one source corpus."""
    return [
        f"  {source}: imports '{module}'"
        for source, module in _collect_imports(package_path, source_root=source_root)
        if module == "specify_cli.sync" or module.startswith("specify_cli.sync.")
    ]


class TestDashboardSyncBoundary:
    """specify_cli.dashboard must not import specify_cli.sync."""

    def test_dashboard_does_not_import_sync(self) -> None:
        """No dashboard module may import from specify_cli.sync (any sub-module).

        Catches all import shapes (module-level, TYPE_CHECKING, lazy
        function-body, relative). Zero exceptions are allowed.
        """
        edges = _collect_imports(DASHBOARD_PATH)
        assert edges, "dashboard import scan reached no live source edges"
        scanned_sources = {source for source, _ in edges}
        assert any(source.endswith("dashboard/lifecycle.py") for source in scanned_sources), (
            "scan missed dashboard/lifecycle.py — the file whose sync imports were re-homed"
        )
        violations = _sync_import_violations(DASHBOARD_PATH)
        assert not violations, (
            "specify_cli.dashboard must not import specify_cli.sync.\n"
            "Violations found (including lazy, relative, and TYPE_CHECKING "
            "imports):\n" + "\n".join(violations) + "\n\nFix: dashboard owns its probes outright — import from "
            "specify_cli.core.process_liveness (or another core module), or "
            "re-home the needed code into dashboard/."
        )

    def test_boundary_oracle_bites_on_every_import_shape(self, tmp_path: Path) -> None:
        """The oracle flags absolute, relative, lazy, and TYPE_CHECKING edges."""
        package = tmp_path / "specify_cli" / "dashboard"
        (package / "handlers").mkdir(parents=True)
        for init in (package / "__init__.py", package / "handlers" / "__init__.py"):
            init.write_text("", encoding="utf-8")

        lifecycle = package / "lifecycle.py"
        lifecycle.write_text(
            "from specify_cli.core.atomic import atomic_write\n",
            encoding="utf-8",
        )
        api = package / "handlers" / "api.py"
        api.write_text(
            "from __future__ import annotations\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\n",
            encoding="utf-8",
        )

        assert _sync_import_violations(package, source_root=tmp_path) == []

        # The exact revert the squad demonstrated on PR [#2].
        lifecycle.write_text(
            "from specify_cli.sync.daemon import (\n    _fetch_health_payload as _fetch_localhost_json_payload,\n)\nfrom ..sync import daemon as _sync_daemon\n",
            encoding="utf-8",
        )
        # Lazy and TYPE_CHECKING shapes must bite identically.
        api.write_text(
            "from __future__ import annotations\n"
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from specify_cli.sync.events import SyncEvent\n"
            "\n"
            "\n"
            "def boot() -> None:\n"
            "    import specify_cli.sync.daemon\n",
            encoding="utf-8",
        )

        # File order follows path sort; only the violation set is contractual.
        assert set(_sync_import_violations(package, source_root=tmp_path)) == {
            "  specify_cli/dashboard/lifecycle.py: imports 'specify_cli.sync.daemon'",
            "  specify_cli/dashboard/lifecycle.py: imports 'specify_cli.sync'",
            "  specify_cli/dashboard/handlers/api.py: imports 'specify_cli.sync.events'",
            "  specify_cli/dashboard/handlers/api.py: imports 'specify_cli.sync.daemon'",
        }
