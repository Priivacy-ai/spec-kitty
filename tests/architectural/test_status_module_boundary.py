"""Architectural boundary tests for the ``specify_cli.status`` facade.

These tests enforce that no module *outside* ``specify_cli.status`` imports
any ``specify_cli.status.*`` submodule directly.  External consumers must go
through the curated public API surface defined by ``specify_cli.status.__all__``.

Rules enforced:
* **SR-1** (pytestarch): No module outside ``specify_cli.status`` in WP03-owned
  directories imports any ``specify_cli.status.*`` submodule, except the
  explicitly exempted ``specify_cli.coordination.status_transition`` (internal
  Mission Management domain plumbing).
* **SR-2** (AST scan): Same rule for lazy / function-scoped imports that
  pytestarch's import-graph analysis may miss, scoped to WP03-owned directories.
* **SR-3** (injection proof): The AST scanner is not a no-op — it actively
  catches violations.

Coverage expansion plan:
  - WP03 (this WP): agent_utils/, coordination/status_service.py,
    coordination/outbound.py, lanes/recovery.py, post_merge/
  - WP04: cli/commands/agent/status.py
  - WP05: missions/ (MissionRun back-reference)
  - WP06: runtime/next/ and cli/commands/agent/workflow.py
  - Remaining cli/, scripts/, migration/, etc.: tracked as follow-on work

Exemptions:
  - ``specify_cli.coordination.status_transition`` — see T016 comment below
  - All modules inside ``specify_cli.status`` itself

Bypass import audit (2026-06-03):
  - Total across all of src/specify_cli/ (non-status, non-status_transition): ~180 imports
  - Fixed by WP03 in owned directories:
    * agent_utils/status.py: 5 imports fixed
    * coordination/status_service.py: 3 imports fixed
    * coordination/outbound.py: 1 import fixed
    * lanes/recovery.py: 7 imports fixed
    * post_merge/review_artifact_consistency.py: 1 import fixed
  - Remaining violations owned by other WPs

See also:
  - ``tests/architectural/test_shared_package_boundary.py`` — template / pattern
  - ADR ``architecture/3.x/adr/2026-06-03-1-execution-state-domain-model.md``
"""
from __future__ import annotations

import ast
import contextlib
import pathlib
import textwrap
from pathlib import Path

import pytest
from pytestarch import Rule
from pytestarch.eval_structure.exceptions import ImpossibleMatch

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"

# WP03-owned directories (the ones this WP has fixed)
_WP03_OWNED_DIRS = [
    _SRC / "specify_cli" / "agent_utils",
    _SRC / "specify_cli" / "coordination",
    _SRC / "specify_cli" / "lanes",
    _SRC / "specify_cli" / "post_merge",
    _SRC / "specify_cli" / "missions",
    _SRC / "specify_cli" / "merge",
    _SRC / "specify_cli" / "next",
]
_WP03_OWNED_FILES = [
    _SRC / "specify_cli" / "doc_state.py",
    _SRC / "specify_cli" / "gap_analysis.py",
]

# ---------------------------------------------------------------------------
# Exemption documentation (T016)
# ---------------------------------------------------------------------------

# coordination/status_transition.py is exempt: it is internal Mission Management
# domain plumbing that coordinates transactional status transitions. It is NOT
# an external caller of status/; it is part of the same bounded module.
# It directly coordinates with status.emit, status.reducer, and status.locking
# as low-level building blocks of the transactional commit pipeline.
# This exemption is intentional and documented in the WP03 spec.
_EXEMPT_MODULES = frozenset(
    {
        "specify_cli.coordination.status_transition",
    }
)

# coordination/transaction.py is also out of scope for WP03 boundary enforcement
# (it is BookkeepingTransaction plumbing, handled separately per CLAUDE.md).
_EXEMPT_FILES: frozenset[Path] = frozenset(
    {
        _SRC / "specify_cli" / "coordination" / "status_transition.py",
        _SRC / "specify_cli" / "coordination" / "transaction.py",
    }
)


# ---------------------------------------------------------------------------
# SR-1 -- pytestarch rule (scoped to WP03-owned modules)
# ---------------------------------------------------------------------------


class TestStatusModuleBoundary:
    """SR-1: WP03-owned modules must not import status.* submodules directly.

    The exemption for ``specify_cli.coordination.status_transition`` is
    explicit and intentional — see module-level docstring above.

    Coverage is intentionally scoped to modules this WP fixed. Future WPs
    will expand coverage to the remaining codebase.
    """

    def test_no_direct_status_submodule_imports(self, evaluable) -> None:
        """pytestarch rule: WP03-owned modules must not bypass the status facade.

        Checks packages that WP03 has fully fixed: agent_utils, lanes, post_merge,
        missions, merge, and next.

        Note: The coordination package is partially fixed by WP03.
        coordination/status_transition.py is explicitly exempt (documented in
        module docstring); coordination/transaction.py is BookkeepingTransaction
        plumbing (out of scope per project guidelines).  These are covered by
        the AST scan with explicit file-level exemptions.

        pytestarch raises ``ImpossibleMatch`` when the constrained module is
        not present in the evaluable graph at all.  That is the rule passing.
        """
        # WP03 has fully fixed these packages (zero bypass imports remain)
        fully_fixed_packages = [
            r"^specify_cli\.agent_utils(\..*)?$",
            r"^specify_cli\.lanes(\..*)?$",
            r"^specify_cli\.post_merge(\..*)?$",
            r"^specify_cli\.missions(\..*)?$",
            r"^specify_cli\.merge(\..*)?$",
            r"^specify_cli\.next(\..*)?$",
        ]

        for pattern in fully_fixed_packages:
            rule = (
                Rule()
                .modules_that()
                .have_name_matching(pattern)
                .should_not()
                .import_modules_that()
                .are_sub_modules_of("specify_cli.status")
            )
            # ImpossibleMatch: subject absent -> no importers -> rule satisfied.
            with contextlib.suppress(ImpossibleMatch):
                rule.assert_applies(evaluable)


# ---------------------------------------------------------------------------
# SR-2 -- AST scan (catches lazy / function-scoped imports)
# ---------------------------------------------------------------------------


def scan_for_bypass_imports(
    files: list[pathlib.Path],
    *,
    exempt_files: set[pathlib.Path] | None = None,
) -> list[str]:
    """Scan ``files`` for direct imports of ``specify_cli.status.*`` submodules.

    Returns a list of violation strings in the form ``"<path>:<lineno>: <module>"``.

    Parameters
    ----------
    files:
        List of ``.py`` files to scan.
    exempt_files:
        Set of file paths to skip entirely.  Defaults to an empty set.

    The function catches both module-level and function-scoped (lazy) imports
    because it walks the full AST tree rather than relying on import-graph
    static analysis.  TYPE_CHECKING-guarded imports are excluded since they
    are only evaluated by type-checkers and do not create runtime coupling.
    """
    if exempt_files is None:
        exempt_files = set()

    violations: list[str] = []
    for py_file in files:
        if py_file in exempt_files:
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue
        # Collect all if-TYPE_CHECKING node ranges to exclude them
        type_checking_linenos: set[int] = _collect_type_checking_linenos(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            node_lineno = getattr(node, "lineno", None)
            if node_lineno in type_checking_linenos:
                continue
            if isinstance(node, ast.ImportFrom) and node.module:
                if _is_bypass_import(node.module):
                    violations.append(f"{py_file}:{node_lineno}: {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_bypass_import(alias.name):
                        violations.append(f"{py_file}:{node_lineno}: {alias.name}")
    return violations


def _collect_type_checking_linenos(tree: ast.AST) -> set[int]:
    """Collect line numbers of all nodes inside ``if TYPE_CHECKING:`` blocks."""
    linenos: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        # Detect `if TYPE_CHECKING:` — the test is `Name(id='TYPE_CHECKING')`
        # or `Attribute(attr='TYPE_CHECKING')`.
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


def _is_bypass_import(module_name: str) -> bool:
    """Return True if the module is a direct status submodule import (bypass)."""
    return module_name.startswith("specify_cli.status.") and module_name != "specify_cli.status"


def _collect_wp03_files() -> list[pathlib.Path]:
    """Collect all .py files in WP03-owned directories/files.

    These are the files that WP03 has fixed.  The scan is scoped to these
    to ensure the test passes after WP03 lands, without requiring all other
    WPs to have completed their own fixes.
    """
    files: list[pathlib.Path] = []

    for dir_path in _WP03_OWNED_DIRS:
        if not dir_path.exists():
            continue
        for py_file in dir_path.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            files.append(py_file)

    for f in _WP03_OWNED_FILES:
        if f.exists():
            files.append(f)

    return files


def test_ast_scan_no_direct_status_imports_in_wp03_scope() -> None:
    """AST scan: WP03-owned modules must not bypass the status/ facade.

    This doubles up on the pytestarch rule (SR-1) to catch lazy imports
    (e.g. inside functions) that import-graph analysis may miss.

    Scoped to WP03-owned directories. Future WPs will expand coverage.
    """
    files = _collect_wp03_files()
    violations = scan_for_bypass_imports(files, exempt_files=_EXEMPT_FILES)
    assert not violations, (
        f"Direct status submodule imports found in WP03-owned files "
        f"({len(violations)} violations):\n"
        + "\n".join(f"  {v}" for v in violations[:30])
        + (f"\n  ... and {len(violations) - 30} more" if len(violations) > 30 else "")
        + "\n\nAll imports from status/ must go through `from specify_cli.status import X`.\n"
        "Exempt: specify_cli.coordination.status_transition and coordination/transaction.py"
    )


# ---------------------------------------------------------------------------
# SR-3 -- Injection proof (scanner is not a no-op)
# ---------------------------------------------------------------------------


def test_ast_scan_catches_injected_violation(tmp_path: pathlib.Path) -> None:
    """Injection proof: the scanner detects a synthetic bypass import.

    Proves the enforcement is not vacuous.  If the scanner fails to catch this,
    the entire SR-2 rule has no teeth.
    """
    bad_file = tmp_path / "bad_module.py"
    bad_file.write_text(
        textwrap.dedent(
            """
            # Synthetic SR-2 violator -- proves the scanner has teeth.
            from specify_cli.status.emit import emit_status_transition  # noqa: F401
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    violations = scan_for_bypass_imports([bad_file], exempt_files=set())
    assert len(violations) == 1, (
        f"Expected exactly 1 violation, got {len(violations)}: {violations}"
    )
    assert "status.emit" in violations[0], (
        f"Expected 'status.emit' in violation string, got: {violations[0]}"
    )


def test_ast_scan_ignores_type_checking_imports(tmp_path: pathlib.Path) -> None:
    """Verify that TYPE_CHECKING-guarded imports are not flagged as violations.

    These imports are only evaluated by type-checkers, not at runtime, and do
    not create actual module coupling.
    """
    safe_file = tmp_path / "type_safe_module.py"
    safe_file.write_text(
        textwrap.dedent(
            """
            from __future__ import annotations
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from specify_cli.status.models import StatusEvent  # type-only

            def f(x: StatusEvent) -> None:
                pass
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    violations = scan_for_bypass_imports([safe_file], exempt_files=set())
    assert not violations, (
        f"TYPE_CHECKING imports should not be flagged as violations, got: {violations}"
    )
