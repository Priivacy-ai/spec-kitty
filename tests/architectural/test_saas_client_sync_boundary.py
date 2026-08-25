"""Architectural guard: no hosted-client → sync import edges.

Enforces the boundary cut by GitHub issue #3: after the durable sync
transport was deleted, ``saas_client`` and ``tracker/saas_client.py`` talk
to the hosted SaaS through plain HTTP and the egress consent gate — they
never reach into ``specify_cli.sync`` again. This test must remain in CI
permanently to prevent regression.

Uses stdlib ``ast`` to walk ALL imports in every scanned .py file,
including module-level imports, ``if TYPE_CHECKING:`` blocks, and lazy
function-body imports.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
SAAS_CLIENT_PATH = SRC / "specify_cli" / "saas_client"
TRACKER_CLIENT_FILE = SRC / "specify_cli" / "tracker" / "saas_client.py"

# Issue #3 removed every sync.* dependency of the two hosted clients except
# this one: runtime-target resolution still comes from ``sync.config``, which
# lives inside the doomed tree. It is re-homed (or deleted with its caller)
# by epic issue #5; until then it is the single allowlisted edge, so nothing
# else can quietly join it.
ALLOWED_TRACKER_SYNC_IMPORTS: dict[str, set[str]] = {
    "specify_cli/tracker/saas_client.py": {"specify_cli.sync.config"},
}

pytestmark = pytest.mark.architectural


def _collect_imports(package_path: Path, *, source_root: Path = SRC) -> list[tuple[str, str]]:
    """Return (source_file, imported_module) for all imports below a path.

    Walks the full AST including function bodies and TYPE_CHECKING blocks.
    """
    edges: list[tuple[str, str]] = []
    for py_file in sorted(package_path.rglob("*.py")) if package_path.is_dir() else [package_path]:
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                edges.append((str(py_file.relative_to(source_root)), node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append((str(py_file.relative_to(source_root)), alias.name))
    return edges


def _sync_import_violations(
    scan_path: Path,
    *,
    allowed: dict[str, set[str]] | None = None,
    source_root: Path = SRC,
) -> list[str]:
    """Run the client-to-sync boundary oracle for one source corpus."""
    allowed = allowed or {}
    return [
        f"  {source}: imports '{module}'"
        for source, module in _collect_imports(scan_path, source_root=source_root)
        if (module == "specify_cli.sync" or module.startswith("specify_cli.sync.")) and module not in allowed.get(source, set())
    ]


class TestSaasClientSyncBoundary:
    """The hosted clients must not import specify_cli.sync."""

    def test_saas_client_package_does_not_import_sync(self) -> None:
        """No saas_client module may import from specify_cli.sync (any sub-module).

        Catches all import shapes (module-level, TYPE_CHECKING, lazy
        function-body). Zero exceptions are allowed.
        """
        edges = _collect_imports(SAAS_CLIENT_PATH)
        assert edges, "saas_client import scan reached no live source edges"
        violations = _sync_import_violations(SAAS_CLIENT_PATH)
        assert not violations, (
            "specify_cli.saas_client must not import specify_cli.sync.\n"
            "Violations found (including lazy and TYPE_CHECKING imports):\n"
            + "\n".join(violations)
            + "\n\nFix: issue #3 cut this boundary — resolve the dependency "
            "locally or re-home the helper instead of re-importing sync."
        )

    def test_tracker_client_does_not_reacquire_sync_edges(self) -> None:
        """tracker/saas_client.py stays at its single disclosed sync edge.

        The one allowlist entry is the ``sync.config`` runtime-target import
        that issue #5 removes with the rest of the doomed tree. Any edge
        beyond it fails here rather than re-growing silently.
        """
        assert TRACKER_CLIENT_FILE.exists(), "tracker/saas_client.py moved — repoint this guard"
        violations = _sync_import_violations(TRACKER_CLIENT_FILE, allowed=ALLOWED_TRACKER_SYNC_IMPORTS)
        assert not violations, (
            "specify_cli.tracker.saas_client must not import specify_cli.sync "
            f"beyond {sorted(ALLOWED_TRACKER_SYNC_IMPORTS.values())} "
            "(removed by issue #5).\n"
            "Violations found (including lazy and TYPE_CHECKING imports):\n" + "\n".join(violations)
        )

    def test_import_scanner_has_two_sided_fault_bite(self, tmp_path: Path) -> None:
        package = tmp_path / "saas_client"
        package.mkdir()
        source = package / "consumer.py"
        source.write_text("from specify_cli.egress import project_egress_refusal\n", encoding="utf-8")
        assert _sync_import_violations(package, source_root=tmp_path) == []

        source.write_text("from specify_cli.sync import consent\n", encoding="utf-8")
        assert _sync_import_violations(package, source_root=tmp_path) == ["  saas_client/consumer.py: imports 'specify_cli.sync'"]

    def test_allowlist_exception_is_exact(self, tmp_path: Path) -> None:
        source = tmp_path / "tracker_client.py"
        source.write_text("from specify_cli.sync.config import SyncConfig\n", encoding="utf-8")
        allowed = {"tracker_client.py": {"specify_cli.sync.config"}}
        assert _sync_import_violations(source, allowed=allowed, source_root=tmp_path) == []

        source.write_text("from specify_cli.sync.transport_lease import acquire_project_transport_lease\n", encoding="utf-8")
        assert _sync_import_violations(source, allowed=allowed, source_root=tmp_path) == ["  tracker_client.py: imports 'specify_cli.sync.transport_lease'"]
