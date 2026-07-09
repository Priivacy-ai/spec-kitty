"""Architectural surface test for the ``mission_runtime`` umbrella (FR-005).

``mission_runtime`` is the canonical execution-state surface. Consumers import
**only** from the package root (``from mission_runtime import ...``); the
internal submodules ``mission_runtime.context`` and ``mission_runtime.resolution``
are import-forbidden from outside the package. This keeps the public surface lean
and prevents the internal-leakage that let the old ``core/execution_context``
resolver sprawl.

Rules enforced:
* **MR-1** (pytestarch): No module outside ``mission_runtime`` imports any
  ``mission_runtime.*`` submodule directly.
* **MR-2** (AST scan): Same rule for lazy / function-scoped imports that
  pytestarch's import-graph analysis may miss, scanned across the whole source
  tree (the umbrella's surface must be enforced repo-wide, not scoped).
* **MR-3** (injection proof): The AST scanner is not a no-op — it actively
  catches an injected violation.

See also:
  - ``tests/architectural/test_status_module_boundary.py`` — template / pattern
  - ADR ``docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md``
  - Contract ``kitty-specs/execution-state-canonical-surface-01KTG6P9/contracts/mission_runtime_api.md``
"""
from __future__ import annotations

import ast
import contextlib
import pathlib
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from pytestarch import EvaluableArchitecture, Rule
from pytestarch.eval_structure.exceptions import ImpossibleMatch

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_PACKAGE_DIR = _SRC / "mission_runtime"
# WP03 (execution-context-unification-01KTPKST) grows the surface with the
# doc-09 fragment / op-composite value objects that the conversion WPs
# (WP04/05/06/07) consume via the package root. ``__all__`` is sorted, so the
# expected surface is sorted too.
_PUBLIC_SURFACE = sorted(
    [
        "ActionContextError",
        "ArtifactPlacementFragment",
        "BranchRefFragment",
        "CommitTarget",
        "ExecutionMode",
        "IdentityFragment",
        "MissionArtifactContext",
        "MissionArtifactHome",
        "MissionArtifactKind",
        "MissionContext",
        "MissionExecutionContext",
        # mission-resolver-port-01KX1C05 WP02 (FR-001): the handle -> mission
        # identity Protocol, defined here (not in specify_cli.context) so the
        # shell references a local type with no new mission_runtime ->
        # specify_cli.context ledger edge (D-Q2). See
        # mission_runtime/mission_resolver_port.py for the full rationale.
        "MissionResolver",
        "MissionTopology",
        # coord-primary-partition-lock WP01 (T001): the kind-aware placement seam
        # — the public face of resolve_action_context's derivation root (C-001) —
        # exposed as one authority object + its constructor, out-of-map edit
        # (this surface list is not a WP01 owned file, but every new
        # mission_runtime public symbol must be pinned here).
        "PlacementSeam",
        "StatusSurfaceFragment",
        "WorkspaceFragment",
        "artifact_home_for",
        "classify_topology",
        "is_coordination_artifact_residue_path",
        "is_primary_artifact_kind",
        # gate-read-surface-completion WP05 (FR-003): the self-bookkeeping allowlist
        # predicate is a package-root public symbol consumed by the record-analysis
        # dirty-tree preflight (DISJOINT from the coord-residue partition, G-5).
        "is_self_bookkeeping_path",
        "kind_for_mission_file",
        "mission_context_for",
        "placement_seam",
        "resolve_action_context",
        "resolve_placement_only",
        "resolve_topology",
        "routes_through_coordination",
    ]
)


# ---------------------------------------------------------------------------
# MR-1 -- pytestarch rule
# ---------------------------------------------------------------------------


class TestMissionRuntimeSurface:
    """MR-1: external modules must not import mission_runtime.* submodules."""

    def test_package_root_cold_imports(self) -> None:
        """Package-root import must not require prior status/core initialization."""
        result = subprocess.run(
            [sys.executable, "-c", "import mission_runtime; print(mission_runtime.__all__)"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    def test_public_surface_matches_contract(self) -> None:
        """The public API stays lean; compatibility attrs are not in __all__."""
        import mission_runtime

        assert mission_runtime.__all__ == _PUBLIC_SURFACE

    def test_no_external_submodule_imports(self, evaluable: EvaluableArchitecture) -> None:
        """pytestarch rule: nothing imports mission_runtime internals directly.

        Modules *inside* ``mission_runtime`` may import their siblings (the
        ``__init__`` re-exports from ``context``/``resolution``); everything
        else must go through the package root.

        pytestarch raises ``ImpossibleMatch`` when no module imports a
        ``mission_runtime`` submodule at all — that is the rule passing
        vacuously while the umbrella is empty-but-registered (WP02).

        The ``evaluable`` fixture roots the graph at ``src/`` so module names
        carry the ``src.`` prefix; both the bare and prefixed package names are
        listed as the self-import exception.
        """
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of(["mission_runtime", "src.mission_runtime"])
            .should_not()
            .be_imported_by_modules_except_modules_that()
            .are_sub_modules_of(["mission_runtime", "src.mission_runtime"])
        )
        with contextlib.suppress(ImpossibleMatch):
            rule.assert_applies(evaluable)


# ---------------------------------------------------------------------------
# MR-2 -- AST scan (catches lazy / function-scoped imports)
# ---------------------------------------------------------------------------


def _is_internal_submodule_import(module_name: str) -> bool:
    """Return True if ``module_name`` reaches into a mission_runtime submodule.

    ``mission_runtime`` (the package root) is allowed; ``mission_runtime.context``
    and ``mission_runtime.resolution`` (and any future internal submodule) are
    bypass imports when referenced from outside the package.
    """
    return (
        module_name.startswith("mission_runtime.")
        and module_name != "mission_runtime"
    )


def _collect_type_checking_linenos(tree: ast.AST) -> set[int]:
    """Collect line numbers of all nodes inside ``if TYPE_CHECKING:`` blocks."""
    linenos: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        is_type_checking = (
            (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING")
            or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")
        )
        if is_type_checking:
            for child in ast.walk(node):
                if hasattr(child, "lineno"):
                    linenos.add(child.lineno)
    return linenos


def scan_for_internal_imports(files: list[pathlib.Path]) -> list[str]:
    """Scan ``files`` for direct imports of ``mission_runtime.*`` submodules.

    Returns violation strings in the form ``"<path>:<lineno>: <module>"``.

    Walks the full AST so both module-level and function-scoped (lazy) imports
    are caught. ``TYPE_CHECKING``-guarded imports are excluded since they create
    no runtime coupling.
    """
    violations: list[str] = []
    for py_file in files:
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue
        type_checking_linenos = _collect_type_checking_linenos(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            node_lineno = getattr(node, "lineno", None)
            if node_lineno in type_checking_linenos:
                continue
            if isinstance(node, ast.ImportFrom) and node.module:
                if _is_internal_submodule_import(node.module):
                    violations.append(f"{py_file}:{node_lineno}: {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_internal_submodule_import(alias.name):
                        violations.append(f"{py_file}:{node_lineno}: {alias.name}")
    return violations


def _collect_external_source_files() -> list[pathlib.Path]:
    """All ``src/`` .py files *outside* the mission_runtime package."""
    files: list[pathlib.Path] = []
    for py_file in _SRC.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        if _PACKAGE_DIR in py_file.parents or py_file == _PACKAGE_DIR / "__init__.py":
            continue
        files.append(py_file)
    return files


def test_ast_scan_no_external_internal_imports() -> None:
    """AST scan: no module outside mission_runtime imports its submodules.

    Doubles up on the pytestarch rule (MR-1) to catch lazy imports (e.g. inside
    functions) that import-graph analysis may miss. Scoped to all of ``src/``
    except the package itself, so the umbrella's surface is enforced repo-wide.
    """
    files = _collect_external_source_files()
    violations = scan_for_internal_imports(files)
    assert not violations, (
        f"Direct mission_runtime submodule imports found outside the package "
        f"({len(violations)} violations):\n"
        + "\n".join(f"  {v}" for v in violations[:30])
        + (f"\n  ... and {len(violations) - 30} more" if len(violations) > 30 else "")
        + "\n\nImport from the package root instead: `from mission_runtime import X`."
    )


# ---------------------------------------------------------------------------
# MR-3 -- Injection proof (scanner is not a no-op)
# ---------------------------------------------------------------------------


def test_ast_scan_catches_injected_violation(tmp_path: pathlib.Path) -> None:
    """Injection proof: the scanner detects a synthetic bypass import.

    Proves the enforcement is not vacuous. If the scanner failed to catch this,
    the whole MR-2 rule would have no teeth.
    """
    bad_file = tmp_path / "bad_module.py"
    bad_file.write_text(
        textwrap.dedent(
            """
            # Synthetic MR-2 violator -- proves the scanner has teeth.
            from mission_runtime.resolution import resolve_action_context  # noqa: F401
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    violations = scan_for_internal_imports([bad_file])
    assert len(violations) == 1, (
        f"Expected exactly 1 violation, got {len(violations)}: {violations}"
    )
    assert "mission_runtime.resolution" in violations[0], (
        f"Expected 'mission_runtime.resolution' in violation, got: {violations[0]}"
    )


def test_ast_scan_allows_package_root_import(tmp_path: pathlib.Path) -> None:
    """The package root import is the sanctioned surface and must not flag."""
    good_file = tmp_path / "good_module.py"
    good_file.write_text(
        textwrap.dedent(
            """
            from mission_runtime import resolve_action_context  # noqa: F401
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    violations = scan_for_internal_imports([good_file])
    assert not violations, (
        f"Package-root import should not be flagged, got: {violations}"
    )


def test_ast_scan_ignores_type_checking_imports(tmp_path: pathlib.Path) -> None:
    """``TYPE_CHECKING``-guarded internal imports create no runtime coupling."""
    safe_file = tmp_path / "type_safe_module.py"
    safe_file.write_text(
        textwrap.dedent(
            """
            from __future__ import annotations
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from mission_runtime.context import ExecutionContext  # type-only

            def f(x: ExecutionContext) -> None:
                pass
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    violations = scan_for_internal_imports([safe_file])
    assert not violations, (
        f"TYPE_CHECKING imports should not be flagged, got: {violations}"
    )
