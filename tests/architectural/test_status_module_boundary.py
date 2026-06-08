"""Architectural boundary tests for the ``specify_cli.status`` facade.

These tests enforce that no module *outside* ``specify_cli.status`` imports
any ``specify_cli.status.*`` submodule directly.  External consumers must go
through the curated public API surface defined by ``specify_cli.status.__all__``.

Rules enforced:
* **SR-1** (pytestarch): No module outside ``specify_cli.status`` in
  ``src/specify_cli`` imports any ``specify_cli.status.*`` submodule, except
  the explicitly exempted coordination plumbing files.
* **SR-2** (AST scan): Same rule for lazy / function-scoped imports that
  pytestarch's import-graph analysis may miss, covering all of ``src/specify_cli``
  and ``src/runtime``.
* **SR-3** (injection proof): The AST scanner is not a no-op — it actively
  catches violations.

WP09 widens the scope from the 6 WP03-owned directories to ALL of
``src/specify_cli`` and ``src/runtime``, locking in the WP08 migration.

Exemptions (C-004 plumbing — permanent):
  - ``coordination/status_transition.py``: internal Mission Management plumbing;
    it IS part of the transactional commit pipeline, not an external caller.
  - ``coordination/transaction.py``: BookkeepingTransaction plumbing.

Residual allow-list (post-WP10):
  WP10 routed every prior ROUTE-deferred file onto the ``status`` facade by
  promoting the relevant symbols into ``status/__init__.__all__``
  (lifecycle_events, work_package_lifecycle, reducer.materialize_snapshot,
  doctor.run_doctor, aggregate.InvalidMissionSlug) and refactoring the sync
  SaaS fan-out handler onto facade helpers. The only remaining entry is the
  permanent import-time cycle-breaker:
  - ``workspace/context.py`` — ``status.wp_metadata``
    (cycle-breaker: status/__init__ → .emit → workspace → .context; facade
    is not yet initialized when workspace.context loads at import time —
    permanent).

See also:
  - ``tests/architectural/test_shared_package_boundary.py`` — template / pattern
  - ADR ``architecture/3.x/adr/2026-06-03-1-execution-state-domain-model.md``
  - Contract: ``kitty-specs/execution-state-canonical-surface-01KTG6P9/contracts/status_boundary.md``
"""
from __future__ import annotations

import ast
import contextlib
import pathlib
import textwrap
import time
from pathlib import Path

import pytest
from pytestarch import EvaluableArchitecture, Rule
from pytestarch.eval_structure.exceptions import ImpossibleMatch

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"

# ---------------------------------------------------------------------------
# Exemption documentation (C-004 — permanent plumbing exemptions)
# ---------------------------------------------------------------------------

# coordination/status_transition.py is exempt: it is internal Mission Management
# domain plumbing that coordinates transactional status transitions. It directly
# coordinates with status.emit, status.reducer, and status.locking as low-level
# building blocks of the transactional commit pipeline. This exemption is
# intentional and documented in the contract.
#
# coordination/transaction.py is exempt: BookkeepingTransaction plumbing that
# coordinates transactional JSONL writes; also a legitimate internal consumer
# of status internals per C-004.
_EXEMPT_FILES: frozenset[Path] = frozenset(
    {
        _SRC / "specify_cli" / "coordination" / "status_transition.py",
        _SRC / "specify_cli" / "coordination" / "transaction.py",
    }
)

# ---------------------------------------------------------------------------
# ROUTE-deferred-to-WP10 allow-list (shrinking ledger)
#
# These files contain deep status imports for symbols NOT yet exposed on the
# facade.  WP10 will add each symbol to `status/__init__.__all__` and migrate
# each callsite to `from specify_cli.status import <symbol>`, then remove the
# entry from this allow-list.
#
# Format: (relative_path_under_src/specify_cli/, imported_submodule)
# ---------------------------------------------------------------------------
#
# WP10 routed every prior ROUTE-deferred file: the lifecycle_events,
# work_package_lifecycle, reducer.materialize_snapshot, doctor.run_doctor, and
# aggregate.InvalidMissionSlug symbols were promoted onto the ``status`` facade
# (``status/__init__.__all__``), and the sync SaaS fan-out handler now consumes
# ``build_saas_lifecycle_queue_event`` / ``repo_root_for_lifecycle_log`` from the
# facade instead of reaching into ``status.lifecycle_events`` internals. The only
# remaining entry is the permanent import-time cycle-breaker.
_WP10_DEFERRED_FILES: frozenset[Path] = frozenset(
    {
        # cycle-breaker (permanent): status/__init__ → .emit → workspace →
        # .context; the facade isn't initialized when workspace.context loads at
        # import time, so it must import status.wp_metadata directly. Cannot be
        # routed through the facade without an import cycle.
        _SRC / "specify_cli" / "workspace" / "context.py",
    }
)

# Combined exemptions for the AST scanner: permanent C-004 plumbing + WP10-deferred
_ALL_EXEMPT_FILES: frozenset[Path] = _EXEMPT_FILES | _WP10_DEFERRED_FILES


# ---------------------------------------------------------------------------
# SR-1 -- pytestarch rule (widened to all of src/specify_cli, WP09)
# ---------------------------------------------------------------------------


class TestStatusModuleBoundary:
    """SR-1: All modules in src/specify_cli must not import status.* submodules directly.

    The exemptions for ``specify_cli.coordination.status_transition`` and
    ``specify_cli.coordination.transaction`` are explicit C-004 plumbing
    exemptions — see module-level docstring.

    WP09 widens coverage from WP03's 6-directory scope to ALL of
    ``src/specify_cli``.  The pytestarch rule covers module-level (static)
    imports; the AST scan (SR-2) covers lazy/function-scoped imports as well.

    The WP03 packages (agent_utils, lanes, post_merge, missions, merge, next)
    are fully fixed and NOT in the allow-list; their absence from the
    allow-list is what makes the rule bite for those packages.
    """

    def test_no_direct_status_submodule_imports(self, evaluable: EvaluableArchitecture) -> None:
        """pytestarch rule: all specify_cli modules must not bypass the status facade.

        Covers the full specify_cli package. Exempted: coordination.status_transition
        and coordination.transaction (C-004 plumbing).

        pytestarch raises ``ImpossibleMatch`` when the constrained module is not
        present in the evaluable graph at all; that is the rule passing (vacuously,
        no such module found → no violations).
        """
        # WP03 fully-fixed packages: already clean, no violations allowed.
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
# SR-2 -- AST scan (repo-wide; catches lazy / function-scoped imports)
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
    return (
        module_name.startswith("specify_cli.status.")
        and module_name != "specify_cli.status"
    )


def _collect_all_src_files() -> list[pathlib.Path]:
    """Collect all .py files under src/specify_cli and src/runtime.

    WP09 widens from WP03's 6-directory scope to the full source tree.
    ``src/specify_cli/status/`` itself is excluded (it is the boundary owner,
    not a consumer).  ``src/runtime/`` is included to catch any future
    imports that might be introduced there.
    """
    files: list[pathlib.Path] = []

    search_roots = [
        _SRC / "specify_cli",
        _SRC / "runtime",
    ]

    for root in search_roots:
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            # Skip the status package itself — it is the owner of the boundary,
            # not a consumer that the rule constrains.
            if py_file.is_relative_to(_SRC / "specify_cli" / "status"):
                continue
            files.append(py_file)

    return files


def test_ast_scan_no_direct_status_imports_repo_wide() -> None:
    """AST scan: all modules in src/specify_cli + src/runtime must not bypass the status/ facade.

    WP09 widens the scan from WP03-owned directories to the full source tree.
    The allow-list (_ALL_EXEMPT_FILES) documents:
      1. C-004 permanent plumbing exemptions (coordination/status_transition.py,
         coordination/transaction.py).
      2. ROUTE-deferred-to-WP10 files where facade symbols are not yet available.

    WP10 shrinks the allow-list by adding each deferred symbol to
    ``status/__init__.__all__`` and migrating each callsite.

    This test proves the scan covers the full src/ tree and catches any NEW
    non-allow-listed deep imports introduced after WP09.

    Also asserts that the scan completes within 15 seconds (NFR-005).
    """
    start = time.monotonic()

    files = _collect_all_src_files()
    violations = scan_for_bypass_imports(files, exempt_files=set(_ALL_EXEMPT_FILES))

    elapsed = time.monotonic() - start
    assert elapsed < 15.0, (  # noqa: PLR2004 — NFR-005 numeric literal is the spec
        f"AST scan took {elapsed:.1f}s, exceeds NFR-005 15s budget"
    )

    assert not violations, (
        f"Direct status submodule imports found outside the allow-list "
        f"({len(violations)} violations):\n"
        + "\n".join(f"  {v}" for v in violations[:30])
        + (f"\n  ... and {len(violations) - 30} more" if len(violations) > 30 else "")
        + "\n\n"
        "All imports from status/ must go through `from specify_cli.status import X`.\n"
        "To add a temporary exemption: add the file path to _WP10_DEFERRED_FILES "
        "with a comment explaining WHY and which WP will fix it.\n"
        "Permanent exemptions (C-004 plumbing): coordination/status_transition.py, "
        "coordination/transaction.py."
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


def test_ast_scan_allow_list_covers_known_residuals() -> None:
    """Verify that every file in _WP10_DEFERRED_FILES actually exists on disk.

    Guards against allow-list rot: if WP10 removes a violation and forgets to
    remove it from the allow-list, this test will fail (the file still exists
    but no longer has a deep import — the file-exists check alone is not
    sufficient, but it catches deleted files being left in the allow-list).
    """
    missing = [p for p in _WP10_DEFERRED_FILES if not p.exists()]
    assert not missing, (
        f"Files in _WP10_DEFERRED_FILES no longer exist on disk "
        f"({len(missing)} entries):\n"
        + "\n".join(f"  {p}" for p in sorted(missing))
        + "\n\nRemove stale entries from _WP10_DEFERRED_FILES."
    )
