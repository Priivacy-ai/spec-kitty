"""Doctrine reach-through census gate (mission doctrine-public-api-surface, WP01).

This module is the **authoritative, machine-readable disposition manifest** for the
doctrine public-API-surface mission. It is deliberately self-contained: WP02's
INTERNAL-negative test and WP04's lazy-import ratchet baseline import the constants
below directly rather than re-deriving a classification (or re-reading prose from
``data-model.md`` that can silently drift from what the tests enforce)::

    from tests.architectural.test_doctrine_census import (
        DISPOSITION,
        EXEMPT_MANAGEMENT_SURFACE,
        TICKETED_BASELINE,
        reached_doctrine_paths,
    )

The census is **re-run against the live tree** on every invocation (an AST sweep of
``src/specify_cli/`` excluding the exempt ``src/specify_cli/doctrine/`` management
subpackage) — the disposition table is not trusted from a stale snapshot. A newly
reach-through-ed, undoored doctrine path therefore fails CI (FR-002 / SC-002).

Census numbers, re-measured on this tip (post WP05–WP07 migration) via
``reached_doctrine_paths()`` — the same live scan the gate runs on every invocation:

* module-level direct ``from charter.offering …`` imports (``ImportFrom.level == 0``): **0**
* lazy (function-body) direct doctrine imports: **4 files / 5 reaches**
* ``if TYPE_CHECKING:`` doctrine imports (excluded from the reach-through set): 11 files
* distinct doctrine module-paths reached (non-TYPE_CHECKING): **4**

(Earlier snapshots recorded 29 files / 54 lines / 23 paths before the WP05–WP07
migration, and 34 files / 70 lines / 26 paths at planning time — both superseded.
The gate re-censuses the live tree every run, so it, not this prose, is the
authority; reproduce the numbers above with ``reached_doctrine_paths()``.)

See ``kitty-specs/doctrine-public-api-surface-01KZPDSR/data-model.md`` for the finalized
per-symbol disposition table and the management-surface / C-007-mission notes.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.architectural]


# ---------------------------------------------------------------------------
# Repository anchors
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_ROOT = _REPO_ROOT / "src" / "specify_cli"
_MISSION_TASKS = (
    _REPO_ROOT
    / "kitty-specs"
    / "doctrine-public-api-surface-01KZPDSR"
    / "tasks"
)

# ---------------------------------------------------------------------------
# Manifest — the machine-readable disposition surface (imported by WP02 / WP04)
# ---------------------------------------------------------------------------

#: The inbound-only *management surface*: the only runtime location permitted to
#: import ``doctrine.*`` directly. WP01 is the SOLE owner of this enumeration — no
#: later WP may reclassify a module into the exempt surface, so it is pinned as a
#: frozen set and any growth must be a deliberate, reviewed diff (test below).
EXEMPT_MANAGEMENT_SURFACE: frozenset[str] = frozenset({"src/specify_cli/doctrine"})

#: The full disposition taxonomy (data-model.md "Taxonomy (value set)" + the two
#: census-only tags: TICKETED-BASELINE for doorless management internals, and
#: INTERNAL-METADATA for ``import charter.offering`` path/metadata introspection).
TAXONOMY: frozenset[str] = frozenset(
    {
        "PUBLIC",
        "FACADE-ONLY",
        "MANAGEMENT",
        "TICKETED-BASELINE",
        "INTERNAL",
        "CONSTRUCTION-ROUTED",
        "INTERNAL-METADATA",
    }
)

#: Doctrine module-paths that have **no clean charter door** and are doctrine-
#: *management* internals. Per WP01 T004 they resolve to a documented, tracker-
#: referenced permanent ratchet allowlist entry (TICKETED-BASELINE) rather than
#: MANAGEMENT — MANAGEMENT would widen the exempt surface, the opposite of this
#: mission's intent. WP03 owes no door for these; WP05 keeps them allowlisted.
TICKETED_BASELINE: dict[str, str] = {
    "charter.offering.drg.override_policy": (
        "Doctrine-management internal consumed by _doctrine_collect.py "
        "(override-audit paths); no clean charter door. Ratchet allowlist, #3179."
    ),
    "charter.offering.drg.migration.hand_authored_overlay": (
        "write_reference_graph_with_overlay is a DRG-regeneration internal "
        "consumed by cli/commands/doctrine.py; no clean charter door. "
        "Ratchet allowlist, #3179."
    ),
}

#: The finalized per-path disposition table (keyed by doctrine module-path). This
#: is a **superset** of the currently-reached set: it also classifies paths reached
#: only under ``TYPE_CHECKING`` today (drg.merge, glossary_packs, assets.models) so
#: WP02/WP03 have a stable target even as call sites migrate. Every reached path
#: MUST appear here (test_every_reached_doctrine_path_has_disposition).
DISPOSITION: dict[str, str] = {
    # agent_profiles cluster → charter.profiles (existing door)
    "charter.offering.agent_profiles.profile": "FACADE-ONLY",
    "charter.offering.agent_profiles.repository": "FACADE-ONLY",
    "charter.offering.agent_profiles.capabilities": "FACADE-ONLY",
    "charter.offering.agent_profiles.diagnostics": "FACADE-ONLY",
    # artifact kinds — PUBLIC (already enumerated in charter.offering.api / charter.drg)
    "charter.offering.artifact_kinds": "PUBLIC",
    # DRG cluster → charter.drg (existing/widened door)
    "charter.offering.drg.models": "FACADE-ONLY",
    "charter.offering.drg.loader": "FACADE-ONLY",
    "charter.offering.drg.merge": "FACADE-ONLY",
    "charter.offering.drg.org_pack_config": "FACADE-ONLY",
    "charter.offering.drg.validator": "FACADE-ONLY",
    "charter.offering.drg.override_policy": "TICKETED-BASELINE",
    "charter.offering.drg.migration.hand_authored_overlay": "TICKETED-BASELINE",
    # charter.offering.base — DoctrineLayerCollisionWarning (census-drift: absent from the
    # snapshot table). Doorable → FACADE-ONLY (prefer a clean door over widening
    # the exempt surface). Consumer _doctrine_collect.py is WP05-owned.
    "charter.offering.base": "FACADE-ONLY",
    # missions cluster → new charter.missions door
    "charter.offering.missions.step_contracts": "FACADE-ONLY",
    "charter.offering.missions.repository": "FACADE-ONLY",
    "charter.offering.missions.mission_type_repository": "FACADE-ONLY",
    # The two former "decide IC-01" rows: FACADE-ONLY (a clean charter.missions
    # door exists) — NOT MANAGEMENT, which would widen exemptions.
    "charter.offering.missions.step_projection": "FACADE-ONLY",
    "charter.offering.missions.mission_step_repository": "FACADE-ONLY",
    # model/task routing → new charter.model_routing (symbol-level PUBLIC)
    "charter.offering.model_task_routing": "PUBLIC",
    # assets → new charter.assets (PUBLIC)
    "charter.offering.assets.repository": "PUBLIC",
    "charter.offering.assets.models": "PUBLIC",
    # narrow doors
    "charter.offering.glossary_packs": "FACADE-ONLY",
    "charter.offering.spdd_reasons": "FACADE-ONLY",
    "charter.offering.template_catalog": "FACADE-ONLY",
    "charter.offering.pack_paths": "FACADE-ONLY",
    # sole-door service construction (routed through charter builder, IC-05)
    "charter.offering.service": "CONSTRUCTION-ROUTED",
    # bare ``import charter.offering`` — path/metadata introspection (charter.offering.__file__)
    # in tool_surface/bundles/codex.py. Not a symbol import; FR-006 exempt.
    "doctrine": "INTERNAL-METADATA",
}

#: Consumer files that reach doctrine (lazy import) but are **not** claimed by any
#: migration WP's ``owned_files`` — surfaced by the re-run census, not the snapshot.
#: Documented, ticket-referenced exceptions so the orphan is loud and reviewed
#: rather than silently passing the catch-all owner check. A NEW orphan (reached,
#: unowned, not listed here) fails test_no_reached_file_is_orphaned.
#:
#: ``charter/interview.py`` was the sole orphan: it reached ``charter.offering.artifact_kinds``
#: (ArtifactKind) directly while being owned by no migration WP. Mission
#: ``doctrine-public-api-surface-01KZPDSR`` WP07 folded it in (out-of-map, justified):
#: its ArtifactKind import now routes through ``charter.drg`` and its
#: ``specify_cli.charter.offering.org_charter`` usage is a first-party call into the exempt
#: management surface (not a laundered doctrine symbol). The set is now empty; any NEW
#: orphan (reached, unowned, not listed here) fails ``test_no_reached_file_is_orphaned``.
#: Tracker: #3179.
ORPHAN_REACHED_EXCEPTIONS: frozenset[str] = frozenset()

#: Migration WPs whose union of ``owned_files`` must cover the reach-through census.
_MIGRATION_WP_FILES: tuple[str, ...] = (
    "WP05-conduit-closure-sole-door.md",
    "WP06-runtime-migration-profiles-routing.md",
    "WP07-runtime-migration-missions-bundles.md",
)


# ---------------------------------------------------------------------------
# AST census — parent-tracking descent (skips TYPE_CHECKING, tracks nesting)
# ---------------------------------------------------------------------------


def _is_type_checking(test: ast.expr) -> bool:
    """True for ``if TYPE_CHECKING:`` / ``if typing.TYPE_CHECKING:`` guards."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _doctrine_path(node: ast.AST) -> str | None:
    """Return the reached ``doctrine[.…]`` module-path for a level-0 import, else None."""
    if isinstance(node, ast.ImportFrom):
        if node.level != 0:
            return None
        module = node.module or ""
        if module == "doctrine" or module.startswith("doctrine."):
            return module
        return None
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name == "doctrine" or alias.name.startswith("doctrine."):
                return alias.name
    return None


class _ReachVisitor(ast.NodeVisitor):
    """Collect non-TYPE_CHECKING ``doctrine.*`` imports (module-level or lazy)."""

    def __init__(self) -> None:
        self.paths: set[str] = set()
        self._type_checking_depth = 0

    def _record(self, node: ast.AST) -> None:
        if self._type_checking_depth:
            return
        path = _doctrine_path(node)
        if path is not None:
            self.paths.add(path)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self._record(node)

    def visit_Import(self, node: ast.Import) -> None:
        self._record(node)

    def visit_If(self, node: ast.If) -> None:
        guarded = _is_type_checking(node.test)
        if guarded:
            self._type_checking_depth += 1
        for child in node.body:
            self.visit(child)
        if guarded:
            self._type_checking_depth -= 1
        for child in node.orelse:
            self.visit(child)


def _is_exempt(path: Path) -> bool:
    """True when ``path`` lives inside the exempt management subpackage."""
    exempt_root = _RUNTIME_ROOT / "doctrine"
    try:
        path.relative_to(exempt_root)
    except ValueError:
        return False
    return True


def reached_doctrine_paths() -> dict[str, set[str]]:
    """Map each non-exempt runtime file → the set of doctrine module-paths it reaches.

    Reach = a direct ``from charter.offering…`` / ``import charter.offering`` with
    ``ImportFrom.level == 0``, at module level *or* inside a function body,
    excluding ``if TYPE_CHECKING:`` blocks. Files that reach nothing are omitted.
    Public so WP04's ratchet baseline can consume the identical census.
    """
    result: dict[str, set[str]] = {}
    for path in sorted(_RUNTIME_ROOT.rglob("*.py")):
        if _is_exempt(path):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        visitor = _ReachVisitor()
        for child in tree.body:
            visitor.visit(child)
        if visitor.paths:
            result[str(path.relative_to(_REPO_ROOT))] = visitor.paths
    return result


def undoored_paths(reached: set[str], disposition: dict[str, str]) -> set[str]:
    """Pure helper: reached doctrine paths that carry no disposition (an undoored gap)."""
    return {path for path in reached if path not in disposition}


def _owned_files(task_filename: str) -> list[str]:
    """Read the ``owned_files`` list from a WP task file's YAML frontmatter."""
    text = (_MISSION_TASKS / task_filename).read_text(encoding="utf-8")
    parts = text.split("---", 2)
    frontmatter = yaml.safe_load(parts[1]) if len(parts) >= 3 else {}
    return list(frontmatter.get("owned_files", []) or [])


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


def test_every_reached_doctrine_path_has_disposition() -> None:
    """FR-002 / SC-002: every reached, non-exempt doctrine path is classified.

    A newly reach-through-ed doctrine module-path that lacks a disposition entry
    fails here — the machine-checkable "no undoored reach-through" guard.
    """
    reached: set[str] = set().union(*reached_doctrine_paths().values())
    undoored = undoored_paths(reached, DISPOSITION)
    assert not undoored, (
        "Undoored doctrine reach-through — the following doctrine module-paths are "
        "reached by non-exempt runtime code but carry no disposition in DISPOSITION:\n"
        + "\n".join(f"  - {path}" for path in sorted(undoored))
        + "\n\nClassify each (PUBLIC / FACADE-ONLY / TICKETED-BASELINE / …) in "
        "tests/architectural/test_doctrine_census.py::DISPOSITION and record the "
        "target door in data-model.md."
    )


def test_disposition_values_are_within_taxonomy() -> None:
    """Every disposition value is a member of the sanctioned taxonomy."""
    invalid = {v for v in DISPOSITION.values() if v not in TAXONOMY}
    assert not invalid, f"Disposition values outside the taxonomy: {sorted(invalid)}"


def test_no_reached_path_tagged_management() -> None:
    """MANAGEMENT (per-path) stays empty — the mission tightens, never widens.

    Choosing MANAGEMENT for a reached path widens the exempt surface, the opposite
    of this mission's goal. The four former "decide IC-01" rows resolved to
    FACADE-ONLY or TICKETED-BASELINE; none to MANAGEMENT.
    """
    management = {path for path, disp in DISPOSITION.items() if disp == "MANAGEMENT"}
    assert not management, (
        "A doctrine path was tagged MANAGEMENT, widening the exempt surface. Prefer "
        f"FACADE-ONLY (clean door) or TICKETED-BASELINE (doorless internal): {sorted(management)}"
    )


def test_management_surface_is_frozen() -> None:
    """Pin the inbound-only management surface as a frozen, reviewed constant.

    WP01 is the sole owner of this enumeration; any growth must be a deliberate diff
    to this literal, not a silent per-path judgment in a later WP.
    """
    expected = frozenset({"src/specify_cli/doctrine"})
    assert expected == EXEMPT_MANAGEMENT_SURFACE
    exempt_dir = _REPO_ROOT / "src" / "specify_cli" / "doctrine"
    assert exempt_dir.is_dir(), "exempt management subpackage missing from the tree"


def test_ticketed_baseline_paths_are_classified() -> None:
    """The two doorless management internals are TICKETED-BASELINE, not MANAGEMENT."""
    for path in TICKETED_BASELINE:
        assert DISPOSITION.get(path) == "TICKETED-BASELINE", (
            f"{path} must be TICKETED-BASELINE in DISPOSITION (see WP01 T004)"
        )


def test_no_reached_file_is_orphaned() -> None:
    """SC-001 catch-all owner check: every reached file has a named migration owner.

    The union of WP05/WP06/WP07 ``owned_files`` must cover the re-run lazy-import
    census set; any remainder must be a documented ORPHAN_REACHED_EXCEPTIONS entry
    (else the reached file is orphaned and this fails).
    """
    census_files = set(reached_doctrine_paths())
    owned: set[str] = set()
    for task_filename in _MIGRATION_WP_FILES:
        owned.update(_owned_files(task_filename))
    orphans = census_files - owned - ORPHAN_REACHED_EXCEPTIONS
    assert not orphans, (
        "Orphaned doctrine reach-through — the following files reach doctrine but are "
        "claimed by no migration WP (WP05/06/07) and are not a documented exception:\n"
        + "\n".join(f"  - {path}" for path in sorted(orphans))
        + "\n\nAssign each to a migration WP's owned_files, or record a ticketed "
        "ORPHAN_REACHED_EXCEPTIONS entry."
    )


def test_orphan_exceptions_are_actually_reached() -> None:
    """An ORPHAN_REACHED_EXCEPTIONS entry that no longer reaches doctrine is stale."""
    census_files = set(reached_doctrine_paths())
    stale = ORPHAN_REACHED_EXCEPTIONS - census_files
    assert not stale, (
        "Stale ORPHAN_REACHED_EXCEPTIONS entries (no longer reach doctrine — a "
        f"migration likely landed): {sorted(stale)}. Remove them."
    )


def test_injected_undoored_path_is_flagged() -> None:
    """The undoored detector flags a synthetic newly-reached path (gate efficacy).

    Proves the census gate would fail on a real regression without mutating the tree.
    """
    reached = {"charter.offering.artifact_kinds", "charter.offering.brand_new_undoored_module"}
    flagged = undoored_paths(reached, DISPOSITION)
    assert flagged == {"charter.offering.brand_new_undoored_module"}
    # And the real, fully-classified reached set must flag nothing.
    real = set().union(*reached_doctrine_paths().values())
    assert undoored_paths(real, DISPOSITION) == set()
