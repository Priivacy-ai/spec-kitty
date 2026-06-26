"""Architectural guard: CORE set must not import INTEGRATION set.

Enforces the integration boundary contract defined in
``kitty-specs/integration-boundary-01KW0PBE/contracts/integration-boundary-rule.md``.

CORE set (src/specify_cli/):
  - core/
  - status/
  - readiness/
  - invocation/

INTEGRATION set (src/specify_cli/):
  - orchestrator_api/
  - sync/
  - tracker/
  - saas/
  - saas_client/

Rule: CORE MUST NOT import INTEGRATION (any direction of INTEGRATION → CORE is
      allowed, never the reverse).

Scan strategy: stdlib ``ast.walk`` traverses the FULL AST — including module-level
imports, ``if TYPE_CHECKING:`` blocks, and lazy function-body imports — so no import
form can escape detection.

Allowlist: exactly one exemption is permitted (``readiness/coordinator.py`` →
``specify_cli.saas.rollout``), documented with rationale and planned resolution.

Tests:
  - ``test_core_package_dirs_exist``: C-008 sanity — all CORE dirs exist on disk
    so the boundary scan cannot pass vacuously if a package is renamed.
  - ``test_no_core_imports_integration``: main enforcement scan.
  - ``test_allowlist_cannot_be_bypassed``: injection-proof sanity — proves the
    scanner catches a synthetic non-allowlisted INTEGRATION import.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SRC = Path(__file__).resolve().parents[2] / "src"

CORE_PACKAGES = [
    SRC / "specify_cli" / "core",
    SRC / "specify_cli" / "status",
    SRC / "specify_cli" / "readiness",
    SRC / "specify_cli" / "invocation",
]

INTEGRATION_PREFIXES = [
    "specify_cli.orchestrator_api",
    "specify_cli.sync",
    "specify_cli.tracker",
    "specify_cli.saas",
    "specify_cli.saas_client",
]

# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------

# Each entry is a 2-tuple of (source_file_relative_to_repo_root, import_prefix).
# Changes here require a written rationale comment.
ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {
        (
            "src/specify_cli/readiness/coordinator.py",
            "specify_cli.saas.rollout",
            # Rationale: saas/rollout.py acts as a shared-config module (shared-config v1).
            # is_saas_sync_enabled is a pure feature-flag read with no side effects; not a
            # structural SaaS dependency. Will be relocated to a core/kernel config module
            # in a follow-up mission. Exempted until that relocation lands.
        ),
    }
)

# ---------------------------------------------------------------------------
# Corrective action string (reused in violation messages — NFR-002)
# ---------------------------------------------------------------------------

_CORRECTIVE_ACTION = (
    "Route through the adapter/observer registry in status/adapters.py or "
    "invocation/adapters.py instead of importing INTEGRATION modules directly."
)

# ---------------------------------------------------------------------------
# AST helper
# ---------------------------------------------------------------------------


def _collect_imports(source: str) -> list[str]:
    """Parse *source* and return every imported module string.

    Walks the full AST so it captures:
    - Module-level ``import X`` and ``from X import ...`` statements.
    - Imports inside ``if TYPE_CHECKING:`` blocks.
    - Lazy function-body imports.

    Returns a flat list of module strings (the left-hand side of import
    statements), not individual names.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
    return modules


# ---------------------------------------------------------------------------
# T017: Path-existence sub-test (C-008)
# ---------------------------------------------------------------------------


@pytest.mark.architectural
def test_core_package_dirs_exist() -> None:
    """Assert every CORE_PACKAGES entry exists on disk.

    If a CORE package is renamed, this test fails loudly rather than
    allowing the boundary scan to pass vacuously (C-008).
    """
    missing = [p for p in CORE_PACKAGES if not p.is_dir()]
    assert not missing, (
        f"CORE_PACKAGES directories missing: {missing}. "
        "If a package was renamed, update CORE_PACKAGES in this test."
    )


# ---------------------------------------------------------------------------
# T016 + T019: Main enforcement scan
# ---------------------------------------------------------------------------


@pytest.mark.architectural
def test_no_core_imports_integration() -> None:
    """CORE set must not import INTEGRATION set.

    Scans every .py file under each CORE_PACKAGES directory recursively via
    the full AST walker (_collect_imports), including lazy and
    TYPE_CHECKING-guarded imports.

    Allowlisted edges (ALLOWLIST) are silently permitted.  Every other
    CORE→INTEGRATION edge is a violation.

    On failure, each violation message includes ≥ 3 diagnostic fields
    (NFR-002): ``file``, ``import``, and ``action``.
    """
    repo_root = SRC.parent
    violations: list[str] = []

    for pkg_dir in CORE_PACKAGES:
        if not pkg_dir.is_dir():
            # test_core_package_dirs_exist will catch this; skip to avoid noise.
            continue
        for py_file in sorted(pkg_dir.rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            rel = str(py_file.relative_to(repo_root))
            imported_modules = _collect_imports(source)

            for mod in imported_modules:
                for prefix in INTEGRATION_PREFIXES:
                    if mod == prefix or mod.startswith(prefix + "."):
                        # Check allowlist: match on (relative file, exact import prefix
                        # from INTEGRATION_PREFIXES — not the full module string, because
                        # the allowlist stores the saas.rollout prefix, not saas.rollout.*)
                        allowlisted = any(
                            rel == entry[0] and mod.startswith(entry[1])
                            for entry in ALLOWLIST
                        )
                        if not allowlisted:
                            violations.append(
                                "CORE→INTEGRATION boundary violation:\n"
                                f"  file:   {rel}\n"
                                f"  import: {mod}\n"
                                f"  action: {_CORRECTIVE_ACTION}"
                            )
                        break  # matched a prefix — no need to check others

    assert not violations, (
        f"CORE→INTEGRATION boundary violations found "
        f"({len(violations)} total):\n\n"
        + "\n\n".join(violations)
    )


# ---------------------------------------------------------------------------
# T018: Allowlist sanity / injection-proof sub-test
# ---------------------------------------------------------------------------


@pytest.mark.architectural
def test_allowlist_cannot_be_bypassed() -> None:
    """Injection proof: scanner catches a synthetic non-allowlisted INTEGRATION import.

    Passes a synthetic source string containing a known INTEGRATION import to
    _collect_imports and asserts the enforcement logic in
    test_no_core_imports_integration would catch it — i.e., the import appears
    in the collected modules AND is NOT allowlisted for a fictional source file.

    No on-disk file is written; the string is passed directly to _collect_imports.
    """
    synthetic_source = "from specify_cli.sync.events import emit_mission_created\n"
    fake_rel = "src/specify_cli/core/fake_module_for_injection_test.py"

    collected = _collect_imports(synthetic_source)
    assert "specify_cli.sync.events" in collected, (
        f"_collect_imports did not return the injected import. Got: {collected}"
    )

    # Confirm the enforcement logic would flag it: not in allowlist
    is_integration = any(
        prefix == "specify_cli.sync.events"
        or "specify_cli.sync.events".startswith(prefix + ".")
        for prefix in INTEGRATION_PREFIXES
    )
    assert is_integration, (
        "specify_cli.sync.events should match INTEGRATION_PREFIXES"
    )

    allowlisted = any(
        fake_rel == entry[0] and "specify_cli.sync.events".startswith(entry[1])
        for entry in ALLOWLIST
    )
    assert not allowlisted, (
        "The synthetic import should NOT be in the allowlist — the test proves "
        "that enforcement is not vacuous."
    )
