"""Architectural guard: no dashboard → sync import edges.

Enforces the boundary created by the E4 re-homing (planning epic #4,
spec-kitty issue #2): after the re-homing, ``dashboard/`` owns its loopback
JSON probe and takes process liveness from ``core/process_liveness`` — it
borrows nothing from ``specify_cli.sync``. This gate is the revert detector
for that boundary: the first squad pass on PR [#2] showed every other guard
in the tree still passed with the pre-re-homing
``from specify_cli.sync.daemon import _fetch_health_payload`` restored in
``dashboard/lifecycle.py``.

Uses stdlib ``ast`` to walk ALL static import statements in every .py file under
src/specify_cli/dashboard/, including:
- Module-level imports
- Imports inside ``if TYPE_CHECKING:`` blocks
- Lazy function-body imports
- Relative imports (resolved against the importing module's package)
- Package-binding forms — ``from specify_cli import sync``, ``from .. import
  sync``, and their ``as``-aliased variants resolve to the *parent* package
  while binding the child through the alias, so aliases on root-package targets
  are completed onto them before matching

Out of scope (not statically visible to an Import/ImportFrom AST walk):
dynamic imports via ``importlib.import_module()`` / ``__import__()``.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
DASHBOARD_PATH = SRC / "specify_cli" / "dashboard"

pytestmark = pytest.mark.architectural

ROOT_PACKAGE = "specify_cli"
BOUNDARY_PACKAGE = f"{ROOT_PACKAGE}.sync"


def _alias_completions(target: str, node: ast.ImportFrom) -> Iterator[str]:
    """Dotted names an ``ImportFrom`` may bind through a root-package alias.

    ``from specify_cli import sync [as _s]`` resolves to target
    ``specify_cli`` while binding ``specify_cli.sync`` through the alias, and
    ``from .. import sync`` does the same via a relative edge — the shapes that
    escaped the first cut of this gate. ``specify_cli`` is the only resolved
    target from which an alias can compose the boundary path, so only those are
    completed; submodule-qualified targets (``from specify_cli.sync.events
    import X``) already carry their own violating edge.
    """
    if target != ROOT_PACKAGE:
        return ()
    return (f"{target}.{alias.name}" for alias in node.names)


def _import_base_package(relative_path: Path) -> tuple[str, ...]:
    """Dotted module an import statement in *relative_path* resolves against.

    Uniform rule: drop only the file component. A package's own
    ``__init__.py`` has the package's dotted name as its module name, so its
    level-1 relatives resolve against the package *itself* — ``from . import x``
    in ``dashboard/__init__.py`` binds ``specify_cli.dashboard.x``, exactly as
    for a regular module's parent-package resolution:

    - ``dashboard/lifecycle.py`` → ``("specify_cli", "dashboard")``
    - ``dashboard/__init__.py`` → ``("specify_cli", "dashboard")``
    - ``dashboard/handlers/__init__.py`` → ``("specify_cli", "dashboard",
      "handlers")``

    (An earlier special case stripped one extra part under ``__init__`` files,
    which mis-resolved every relative edge inside them and let two violating
    shapes escape — see ``test_boundary_oracle_bites_on_every_import_shape``.)
    """
    parts = relative_path.with_suffix("").parts
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
                    source = str(relative_path)
                    edges.append((source, target))
                    for completed in _alias_completions(target, node):
                        edges.append((source, completed))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append((str(relative_path), alias.name))
    return edges


def _sync_import_violations(package_path: Path, *, source_root: Path = SRC) -> list[str]:
    """Run the live dashboard-to-sync boundary oracle for one source corpus."""
    return [
        f"  {source}: imports '{module}'"
        for source, module in _collect_imports(package_path, source_root=source_root)
        if module == BOUNDARY_PACKAGE or module.startswith(f"{BOUNDARY_PACKAGE}.")
    ]


class TestDashboardSyncBoundary:
    """specify_cli.dashboard must not import specify_cli.sync."""

    def test_dashboard_does_not_import_sync(self) -> None:
        """No dashboard module may import from specify_cli.sync (any sub-module).

        Catches all static import shapes (module-level, TYPE_CHECKING, lazy
        function-body, relative, package-binding). Zero exceptions are allowed.
        Dynamic imports (``importlib.import_module``/``__import__``) are out of
        scope for an AST walk.
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
        """The oracle flags absolute, relative, lazy, TYPE_CHECKING, and
        package-binding edges — and stays quiet on benign root-package imports."""
        package = tmp_path / "specify_cli" / "dashboard"
        (package / "handlers").mkdir(parents=True)
        for init in (package / "__init__.py", package / "handlers" / "__init__.py"):
            init.write_text("", encoding="utf-8")

        lifecycle = package / "lifecycle.py"
        # Benign shapes that must NOT bite, including package bindings whose
        # completions stay outside specify_cli.sync (precision guard: the
        # alias-completion rule may not flag every root-package import).
        lifecycle.write_text(
            "from specify_cli.core.atomic import atomic_write\nfrom specify_cli import core\nfrom . import server\n",
            encoding="utf-8",
        )
        api = package / "handlers" / "api.py"
        api.write_text(
            "from __future__ import annotations\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\n",
            encoding="utf-8",
        )

        assert _sync_import_violations(package, source_root=tmp_path) == []

        # The exact revert the squad demonstrated on PR [#2], plus the
        # package-binding shapes that escaped it (controller-qa second-pass
        # MAJOR): each resolves to a *parent* package while an alias completes
        # the path into specify_cli.sync.
        lifecycle.write_text(
            "from specify_cli.sync.daemon import (\n"
            "    _fetch_health_payload as _fetch_localhost_json_payload,\n"
            ")\n"
            "from ..sync import daemon as _sync_daemon\n"
            "from specify_cli import sync\n"
            "from specify_cli import sync as _sync_pkg\n"
            "from .. import sync as _rel_sync\n",
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

        # Package-binding shapes must bite on their own — isolated so the
        # assertion cannot be satisfied by the sibling ``..sync`` edge above.
        lifecycle.write_text(
            "from specify_cli import sync\nfrom specify_cli import sync as _sync_pkg\nfrom .. import sync as _rel_sync\n",
            encoding="utf-8",
        )
        api.write_text(
            "from __future__ import annotations\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\n",
            encoding="utf-8",
        )
        assert set(_sync_import_violations(package, source_root=tmp_path)) == {
            "  specify_cli/dashboard/lifecycle.py: imports 'specify_cli.sync'",
        }

        # Relative edges inside the package's own ``__init__.py`` must bite in
        # isolation too (squad third-pass MAJOR): a package's relatives resolve
        # against the package itself, and the mis-resolved base produced edge
        # target bare 'sync' for the level-2 from-import and *no edge at all*
        # for the level-2 package binding — both escaped every guard. Sibling
        # modules are reset to benign stubs and each attack line stands alone,
        # so neither shape can ride on another source's edge.
        lifecycle.write_text("", encoding="utf-8")
        (package / "__init__.py").write_text("from ..sync import daemon as _d\n", encoding="utf-8")
        assert _sync_import_violations(package, source_root=tmp_path) == [
            "  specify_cli/dashboard/__init__.py: imports 'specify_cli.sync'",
        ]
        (package / "__init__.py").write_text("from .. import sync as _rel_init_sync\n", encoding="utf-8")
        assert _sync_import_violations(package, source_root=tmp_path) == [
            "  specify_cli/dashboard/__init__.py: imports 'specify_cli.sync'",
        ]
