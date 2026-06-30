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

Scan strategy: a single enforcement function, ``_scan_trees``, walks the FULL
AST of each candidate file — including module-level imports, ``if
TYPE_CHECKING:`` blocks, and lazy function-body imports — so no import form can
escape detection. The gate test feeds it the *cached, pre-parsed* CORE-set
trees from the session-scoped ``src_source_tree`` fixture (so this gate stops
re-walking and re-parsing ``src/`` independently of the five other boundary
gates that share that cache). The injection sanity-check feeds the SAME
function a real on-disk file, so it exercises the actual enforcement path
rather than a re-implementation of it.

Allowlist: at most one exemption is permitted (``readiness/coordinator.py`` →
``specify_cli.saas.rollout``), documented with rationale and planned resolution.
A count-ratchet test pins ``len(ALLOWLIST) <= 1`` so the exemption set can only
shrink (when the follow-up relocation lands) — never silently grow.

Tests:
  - ``test_core_package_dirs_exist``: C-008 sanity — all CORE dirs exist on disk
    so the boundary scan cannot pass vacuously if a package is renamed.
  - ``test_no_core_imports_integration``: main enforcement scan over the cached
    CORE-set trees.
  - ``test_allowlist_cannot_be_bypassed``: injection proof — a real on-disk CORE
    file with a non-allowlisted INTEGRATION import is driven through the same
    ``_scan_trees`` the gate uses and MUST be reported.
  - ``test_allowlist_count_ratchet``: pins ``len(ALLOWLIST) <= 1``.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest

from tests.architectural.conftest import SourceFile

pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SRC = Path(__file__).resolve().parents[2] / "src"
REPO_ROOT = SRC.parent

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
            # by follow-up issue #2252 (https://github.com/Priivacy-ai/spec-kitty/issues/2252).
            # Exempted until that relocation lands; the count-ratchet below holds the set at
            # <= 1 so this is the only crossing that can exist.
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
# Enforcement scanner (single source of truth — used by the gate AND the
# injection proof, so the proof exercises the real enforcement path)
# ---------------------------------------------------------------------------


def _imports_in_tree(tree: ast.AST) -> list[str]:
    """Return every imported module string in *tree*.

    Walks the full AST so it captures module-level ``import X`` /
    ``from X import ...``, imports inside ``if TYPE_CHECKING:`` blocks, and lazy
    function-body imports. Returns the left-hand side module strings, not
    individual names.
    """
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
    return modules


def _is_allowlisted(rel: str, mod: str) -> bool:
    """True if (rel, mod) is covered by an ALLOWLIST entry.

    The module match is dot-bounded (exact, or a true sub-module) so an entry for
    ``specify_cli.saas.rollout`` cannot silently exempt a sibling like a future
    ``specify_cli.saas.rollout_v2`` — mirrors the prefix match in :func:`_scan_trees`.
    """
    return any(
        rel == entry[0] and (mod == entry[1] or mod.startswith(entry[1] + "."))
        for entry in ALLOWLIST
    )


def _scan_trees(items: Iterable[tuple[str, ast.AST]]) -> list[str]:
    """Scan ``(repo_relative_path, parsed_tree)`` pairs for boundary violations.

    Each item is treated as a CORE-set file (the caller is responsible for
    restricting *items* to the CORE set). Returns a list of human-readable
    violation messages — each carrying ≥ 3 diagnostic fields (file / import /
    action) per NFR-002. An empty list means no violations.
    """
    violations: list[str] = []
    for rel, tree in items:
        for mod in _imports_in_tree(tree):
            for prefix in INTEGRATION_PREFIXES:
                if mod == prefix or mod.startswith(prefix + "."):
                    if not _is_allowlisted(rel, mod):
                        violations.append(
                            "CORE→INTEGRATION boundary violation:\n"
                            f"  file:   {rel}\n"
                            f"  import: {mod}\n"
                            f"  action: {_CORRECTIVE_ACTION}"
                        )
                    break  # matched a prefix — no need to check others
    return violations


def _core_items(src_source_tree: Mapping[Path, SourceFile]) -> list[tuple[str, ast.AST]]:
    """Filter the shared source-tree cache down to CORE-set ``(rel, tree)`` pairs."""
    items: list[tuple[str, ast.AST]] = []
    for abs_path, entry in sorted(src_source_tree.items()):
        if any(abs_path.is_relative_to(pkg) for pkg in CORE_PACKAGES):
            items.append((str(abs_path.relative_to(REPO_ROOT)), entry.tree))
    return items


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
# T016 + T019: Main enforcement scan (over the shared, cached source tree)
# ---------------------------------------------------------------------------


@pytest.mark.architectural
def test_no_core_imports_integration(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """CORE set must not import INTEGRATION set.

    Consumes the session-scoped ``src_source_tree`` cache (read + AST parsed
    once for the whole suite), filters to the CORE set, and runs the shared
    ``_scan_trees`` enforcement function — the same one the injection proof
    exercises. Allowlisted edges are silently permitted; every other
    CORE→INTEGRATION edge is a violation with ≥ 3 diagnostic fields (NFR-002).
    """
    items = _core_items(src_source_tree)
    # Guard against a vacuous pass if filtering ever silently yields nothing
    # (e.g. a fixture/glob regression); paired with test_core_package_dirs_exist.
    assert items, "CORE-set scan collected zero files — fixture or path regression?"

    violations = _scan_trees(items)

    assert not violations, (
        f"CORE→INTEGRATION boundary violations found "
        f"({len(violations)} total):\n\n" + "\n\n".join(violations)
    )


# ---------------------------------------------------------------------------
# T018: Allowlist sanity / injection-proof sub-test
# ---------------------------------------------------------------------------


@pytest.mark.architectural
def test_allowlist_cannot_be_bypassed(tmp_path: Path) -> None:
    """Injection proof: the real scanner flags a real on-disk CORE violation.

    Writes an actual ``.py`` file to disk containing a non-allowlisted
    INTEGRATION import, reads + parses it back, and drives it through the SAME
    ``_scan_trees`` function the gate uses (labelled with a CORE-set relative
    path). A regression in the enforcement loop — not just in a re-implemented
    copy of it — would surface here.
    """
    injected = tmp_path / "injected_core_violation.py"
    injected.write_text(
        "from specify_cli.sync.events import emit_mission_created\n",
        encoding="utf-8",
    )
    # Read back from disk and parse through the real path.
    tree = ast.parse(injected.read_text(encoding="utf-8"))
    fake_rel = "src/specify_cli/core/injected_core_violation.py"

    violations = _scan_trees([(fake_rel, tree)])

    assert violations, (
        "Enforcement scan did NOT flag a non-allowlisted INTEGRATION import in a "
        "CORE-set file — the gate would pass vacuously."
    )
    assert "specify_cli.sync.events" in violations[0]
    assert fake_rel in violations[0]

    # Positive control: the allowlisted edge is NOT reported, proving the
    # exemption path is what suppresses it (not a broken scanner).
    allow_src = "from specify_cli.saas.rollout import is_saas_sync_enabled\n"
    allow_tree = ast.parse(allow_src)
    allow_rel = "src/specify_cli/readiness/coordinator.py"
    assert not _scan_trees([(allow_rel, allow_tree)]), (
        "The allowlisted readiness/coordinator.py → saas.rollout edge must be "
        "suppressed by the exemption, not reported."
    )


# ---------------------------------------------------------------------------
# Allowlist count-ratchet (Success Criterion 3 — exactly one exemption today)
# ---------------------------------------------------------------------------


@pytest.mark.architectural
def test_allowlist_count_ratchet() -> None:
    """``len(ALLOWLIST) <= 1`` — the exemption set may only shrink, never grow.

    Exactly one exemption exists today (``readiness/coordinator.py`` →
    ``specify_cli.saas.rollout``). The ``<= 1`` ceiling lets the planned
    follow-up relocation drop it to zero without editing this ratchet, while
    forbidding any new crossing from being silently allowlisted in.
    """
    assert len(ALLOWLIST) <= 1, (
        f"ALLOWLIST grew to {len(ALLOWLIST)} entries: {sorted(ALLOWLIST)}. "
        "New CORE→INTEGRATION exemptions are not permitted — invert the "
        "dependency via the adapter registry instead."
    )
