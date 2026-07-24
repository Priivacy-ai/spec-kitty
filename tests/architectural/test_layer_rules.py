"""2.x package boundary invariants.

These tests enforce the dependency direction documented in
docs/architecture/00_landscape/README.md:

    kernel (root) <- doctrine <- charter <- glossary/runtime <- specify_cli

A violation here means a package imports from a package it should not.
See ADR 2026-03-27-1 for rationale.

---

FR-012 audit verdict (#2548 ratio=1.00 audit, WP01 of mission
content-address-ratchet-allowlists-01KX8M4D — see research.md D-context and
the post-spec adversarial squad classification referenced there):

The post-spec squad classified all thirteen ratio=1.00 architectural tests.
Two of the thirteen (``test_unified_model_resolves_at_new_location`` and
``test_legacy_contract_types_resolve_at_new_location``, both below) were
positive-literal ``__module__ == "..."`` re-pins and were converted to
behavioural assertions by this WP (FR-011). The remaining **ten** were
audited and validated as legitimate KEEP — behavioural, negative, or
import-layer invariants that do not re-pin a literal path — and were left
UNCHANGED:

    test_no_raw_mission_spec_paths
    test_safe_commit_import_boundary
    test_pytest_marker_convention
    test_auth_transport_singleton
    test_status_module_boundary
    test_tid251_enforcement
    test_guard_capability_call_sites
    test_pytest_marker_correctness
    test_charter_facades_reexport_doctrine
    (plus the shared architectural ``conftest`` infra)

This closes the #2548 audit obligation. Do NOT re-open or re-classify these
ten without a fresh audit — see spec.md WS3 (FR-010/FR-011/FR-012).
"""
from __future__ import annotations

import ast
import importlib.util
from collections.abc import Iterable
from pathlib import Path

import pytest
from pytestarch import LayerRule

pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# Layer coverage guards (issue #395)
# ---------------------------------------------------------------------------

# Top-level src/ packages intentionally excluded from layer enforcement.
# Add entries here only for transitional / deprecated packages that will be
# removed once migration is complete.  Entries MUST include a comment
# explaining WHY they are excluded and when they can be removed.
_EXCLUDED_FROM_LAYER_ENFORCEMENT: frozenset[str] = frozenset(
    [
        # `constitution` is the pre-3.x predecessor of `charter`.  It is kept
        # for backward-compatibility shims until all 2.x consumers migrate.
        # Remove once mission 063 (rename-constitution-to-charter) is complete
        # and the compatibility layer is dropped.
        "constitution",
    ]
)

_SRC = Path(__file__).resolve().parents[2] / "src"

# Layer names as defined in the `landscape` fixture in conftest.py.
# Keep this in sync with that fixture; both lists must agree.
_DEFINED_LAYERS: frozenset[str] = frozenset(
    ["kernel", "doctrine", "charter", "glossary", "runtime", "mission_runtime", "specify_cli"]
)

# ---------------------------------------------------------------------------
# WP08 / FR-009 (#2327, WS1): mission_runtime -> specify_cli outbound ledger
# ---------------------------------------------------------------------------
#
# The landscape places ``mission_runtime`` BELOW ``specify_cli``
# (kernel <- ... <- mission_runtime <- specify_cli), so the clean invariant is
# "mission_runtime must NOT import specify_cli". Today ``resolution.py`` (plus a
# single edge in ``artifacts.py``) carry real *lazy, in-function* upward imports
# into the ``specify_cli.*`` subpackages named below.
#
# PRE-DECIDED (research D6, renata-reviewed): these edges are a DOCUMENTED
# allowed-exception set with recorded rationale — they are NOT violations. The
# clean rule ``mission_runtime should_not access specify_cli`` would red on
# existing, working code; converting the edges to hard errors is a carved-out
# FUTURE mission (invert the dependency behind a port — infra/logic separation
# epic #2173). This ledger is therefore bound as an outbound guard, not a purge.
#
# The ledger is SHRINK-ONLY by construction:
#   * ADDING a new ``specify_cli.<sub>`` edge outside this set MUST red the rule
#     (loud additions — proven by ``test_rule_rejects_out_of_ledger_import``),
#   * REMOVING an edge (future port work) must delete its entry here; a stale
#     entry with no matching live import reds ``test_ledger_has_no_stale_entries``.
#
# Each entry is a first-level ``specify_cli.<subpackage>`` name, derived from a
# live AST scan of ``src/mission_runtime/`` (do NOT hand-copy from the plan).
_MISSION_RUNTIME_ROOT = _SRC / "mission_runtime"

_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI: frozenset[str] = frozenset(
    {
        "coordination",      # resolution.py: CoordinationWorkspace, surface_resolver
        "core",              # artifacts.py + resolution.py: constants, paths, dependency_graph
        # coord-trust-2841: the "lanes" allow-row (resolution.py's coord-state
        # branch resolving the mid8 disambiguator via
        # ``lanes.branch_naming.resolve_mid8``, GEC-3 / contract C3) is CLOSED.
        # ``resolve_mid8`` (and its heuristic sibling ``mid8_from_slug``) was
        # pure and is now relocated to ``mission_runtime.identity``;
        # ``specify_cli.lanes.branch_naming`` re-exports both verbatim so
        # existing importers are unaffected. resolution.py imports the
        # resolver directly from its new in-layer home — no specify_cli.lanes
        # crossing remains.
        "migration",         # resolution.py: backfill_topology.read_topology
        "mission",           # resolution.py: get_mission_type
        "mission_metadata",  # resolution.py: load_meta
        "missions",          # resolution.py: _read_path_resolver
        # coord-primary-partition-lock WP01 (H-1, binding): the placement seam's
        # RETROSPECTIVE read leg MUST delegate to the SINGLE home authority
        # ``retrospective.writer.resolve_retrospective_home`` (#2119) — computing
        # a second RETROSPECTIVE home in mission_runtime would duplicate that
        # authority and fail its own single-authority guard. This is a sanctioned
        # upward edge, same class as the ``missions`` read-path delegation above.
        "retrospective",     # resolution.py: PlacementSeam.read_dir -> resolve_retrospective_home
        "status",            # resolution.py: Lane, get_wp_lane, read_events, ...
        "task_utils",        # resolution.py: locate_work_package, split_frontmatter
        "workspace",         # resolution.py: resolve_workspace_for_wp
    }
)


def _is_specify_cli_module(module: str) -> bool:
    """True when ``module`` is ``specify_cli`` itself or one of its subpackages."""
    return module == "specify_cli" or module.startswith("specify_cli.")


def _specify_cli_subpackage(module: str) -> str:
    """First-level subpackage of a ``specify_cli`` import.

    ``specify_cli.core.paths`` -> ``"core"``; bare ``specify_cli`` -> ``""``.
    """
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else ""


def _collect_specify_cli_imports(root: Path) -> list[tuple[str, str]]:
    """Return ``(relative_path, imported_module)`` for every specify_cli import.

    Walks the full AST so *lazy, in-function* imports are included — the
    ``mission_runtime`` upward edges live inside functions, so a module-level
    scan would miss them and the rule would pass vacuously.
    """
    found: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = str(path.relative_to(_SRC))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and _is_specify_cli_module(node.module):
                    found.append((rel, node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_specify_cli_module(alias.name):
                        found.append((rel, alias.name))
    return found


def _out_of_ledger_specify_cli_imports(
    imports: Iterable[tuple[str, str]],
    allowed: frozenset[str],
) -> list[str]:
    """Rule matcher: ``"path imports module"`` for edges outside ``allowed``.

    Pure function of its inputs so the negative test can drive it with a
    synthetic out-of-set edge and prove non-vacuity without touching disk.
    """
    return [
        f"{rel} imports {module}"
        for rel, module in imports
        if _specify_cli_subpackage(module) not in allowed
    ]


class TestLayerCoverage:
    """Meta-tests that keep the landscape fixture honest."""

    def test_no_unregistered_src_packages(self) -> None:
        """Every top-level src/ package must have a layer definition.

        When a new package is added to src/ without a corresponding layer,
        architectural boundary rules pass vacuously for it — violations go
        undetected.  Add the package to `_DEFINED_LAYERS` in the landscape
        fixture *and* to this file's `_DEFINED_LAYERS` constant, or add it
        to `_EXCLUDED_FROM_LAYER_ENFORCEMENT` with a documented reason.
        """
        src_packages = {
            p.name
            for p in _SRC.iterdir()
            if p.is_dir()
            and not p.name.startswith("_")
            and (p / "__init__.py").exists()
        }
        unregistered = src_packages - _DEFINED_LAYERS - _EXCLUDED_FROM_LAYER_ENFORCEMENT
        assert not unregistered, (
            f"src/ packages with no architectural layer assignment: "
            f"{sorted(unregistered)!r}.  "
            "Add a layer to tests/architectural/conftest.py or add to "
            "_EXCLUDED_FROM_LAYER_ENFORCEMENT with a documented reason."
        )

    def test_all_defined_layers_match_at_least_one_module(self) -> None:
        """Every defined layer must match at least one importable module.

        If a package is renamed or removed, the layer definition becomes an
        empty set and all its rules pass vacuously.
        """
        empty: list[str] = []
        for layer in sorted(_DEFINED_LAYERS):
            installed = importlib.util.find_spec(layer) is not None
            on_disk = (_SRC / layer / "__init__.py").exists()
            if not installed and not on_disk:
                empty.append(layer)
        assert not empty, (
            f"Layers defined but no matching module found: {empty!r}.  "
            "The boundary rules for these layers would pass vacuously.  "
            "Remove the layer or restore the package."
        )


# --- Invariant 1: kernel is the true root (zero outgoing deps) ---


class TestKernelIsolation:
    """kernel must not import from any other landscape container."""

    def test_kernel_does_not_import_doctrine(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("kernel")
            .should_not()
            .access_layers_that()
            .are_named("doctrine")
        ).assert_applies(evaluable)

    def test_kernel_does_not_import_charter(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("kernel")
            .should_not()
            .access_layers_that()
            .are_named("charter")
        ).assert_applies(evaluable)

    def test_kernel_does_not_import_specify_cli(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("kernel")
            .should_not()
            .access_layers_that()
            .are_named("specify_cli")
        ).assert_applies(evaluable)


# --- Invariant 2: doctrine depends only on kernel ---


class TestDoctrineIsolation:
    """doctrine must not import from specify_cli or charter."""

    def test_doctrine_does_not_import_specify_cli(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("doctrine")
            .should_not()
            .access_layers_that()
            .are_named("specify_cli")
        ).assert_applies(evaluable)

    def test_doctrine_does_not_import_charter(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("doctrine")
            .should_not()
            .access_layers_that()
            .are_named("charter")
        ).assert_applies(evaluable)


# --- Invariant 3: charter boundary ---


class TestCharterBoundary:
    """charter may import doctrine + kernel only. No specify_cli imports."""

    def test_charter_does_not_import_specify_cli(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("charter")
            .should_not()
            .access_layers_that()
            .are_named("specify_cli")
        ).assert_applies(evaluable)


class TestGlossaryBoundary:
    """glossary may import lower layers, but not specify_cli adapters."""

    def test_glossary_does_not_import_specify_cli(self, evaluable, landscape):
        (
            LayerRule()
            .based_on(landscape)
            .layers_that()
            .are_named("glossary")
            .should_not()
            .access_layers_that()
            .are_named("specify_cli")
        ).assert_applies(evaluable)


class TestRuntimeBoundary:
    """runtime owns next-step decisions and must not import CLI presentation."""

    def test_runtime_does_not_import_cli_commands(self) -> None:
        offenders: list[str] = []
        runtime_root = _SRC / "runtime"
        forbidden_prefixes = ("specify_cli.cli", "specify_cli.next")
        for path in runtime_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith(forbidden_prefixes):
                            offenders.append(f"{path.relative_to(_SRC)} imports {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(forbidden_prefixes):
                    offenders.append(f"{path.relative_to(_SRC)} imports {node.module}")
        assert not offenders


# --- Invariant 4: WP01 — unified MissionStep model location ---


def _non_canonical_instances(objs: Iterable[object], canonical: type) -> list[str]:
    """Return a description for every ``obj`` that is not an instance of ``canonical``.

    Pure function of its inputs (FR-011/FR-013) so the plant-and-catch
    negative test can drive it with a synthetic wrong-wiring object and
    prove non-vacuity without touching disk or real resolver state. Used in
    place of literal ``__module__ == "..."`` comparisons: identity/usage
    is what matters, not which module a class happens to report.
    """
    return [
        f"{obj!r} is {type(obj).__module__}.{type(obj).__qualname__}, "
        f"not {canonical.__qualname__}"
        for obj in objs
        if not isinstance(obj, canonical)
    ]


class TestUnifiedMissionStepBoundary:
    """WP01 (mission charter-doctrine-mission-type-configuration-01KSWJVX).

    After the unification, the legacy ``doctrine.mission_step_contracts``
    subpackage is gone. The unified :class:`MissionStep` model lives at
    ``doctrine.missions.models``; the legacy step-contract types relocate
    to ``doctrine.missions.step_contracts``. Charter modules import from
    ``doctrine.*`` directly (allowed: charter sits above doctrine in the
    dependency stack); the runtime layer reaches doctrine artifacts
    through the charter facades whenever possible.
    """

    def test_legacy_subpackage_is_gone(self) -> None:
        """The legacy ``doctrine.mission_step_contracts`` import path must
        not resolve. WP01 retired this subpackage; any code importing it
        would silently shadow the unified model and reintroduce the
        fragmentation that this WP eliminated.

        We tolerate a leftover ``__pycache__`` directory (pytest may
        recreate the parent on import-error paths even after the source
        files are gone). The invariant the WP enforces is that none of
        the source ``__init__.py`` / ``models.py`` / ``repository.py``
        files exist; the package itself becomes unimportable as a
        consequence.

        Note: ``importlib.util.find_spec`` may return a non-None namespace
        ModuleSpec even when no source files are present (Python namespace
        package behaviour). We therefore rely solely on the source-file
        existence check as the authoritative gate.
        """
        legacy = Path(__file__).resolve().parents[2] / "src" / "doctrine" / "mission_step_contracts"
        forbidden_source_files = ("__init__.py", "models.py", "repository.py")
        present = [name for name in forbidden_source_files if (legacy / name).exists()]
        assert not present, (
            f"Legacy subpackage source files present after WP01: {present}. "
            "Use doctrine.missions.models.MissionStep (unified) or "
            "doctrine.missions.step_contracts (legacy contract types) instead."
        )

    def test_unified_model_resolves_at_new_location(self) -> None:
        """The unified :class:`MissionStep` is BOTH importable via its
        public surface AND the exact class the doctrine mission-step
        resolver actually instantiates when parsing on-disk ``step.yaml``
        definitions (FR-011) — not merely a same-named class that happens
        to report a pinned literal ``__module__`` string.

        Behavioural, not literal: this stays GREEN across a relocation that
        keeps the resolver correctly wired, and it REDS if the resolver
        were ever wired to a decoy/duplicate class (see
        ``test_plant_and_catch_wrong_mission_step_wiring`` below).
        """
        from doctrine.missions.mission_step_repository import MissionStepRepository
        from doctrine.missions.models import MissionStep

        resolved = MissionStepRepository.default().resolve_all_for_mission_type(
            "software-dev"
        )
        assert resolved, (
            "expected the shipped software-dev built-in mission-steps to "
            "resolve at least one step"
        )
        offenders = _non_canonical_instances(resolved.values(), MissionStep)
        assert not offenders, (
            "the mission-step resolver produced steps that are not "
            f"instances of the canonical MissionStep class: {offenders}"
        )

    def test_legacy_contract_types_resolve_at_new_location(self) -> None:
        """The relocated legacy step-contract types are BOTH importable at
        ``doctrine.missions.step_contracts`` AND the exact classes the
        shipped ``*.step-contract.yaml`` loader actually instantiates
        (FR-011) — not merely same-named classes at a pinned literal
        module path.
        """
        from doctrine.missions.step_contracts import (
            DelegatesTo,
            MissionStepContract,
            MissionStepContractRepository,
            MissionStepContractStep,
        )

        repo = MissionStepContractRepository()
        contract = repo.get("implement")
        assert contract is not None, (
            "expected the shipped 'implement' step contract to load"
        )
        assert isinstance(contract, MissionStepContract)

        offenders = _non_canonical_instances(contract.steps, MissionStepContractStep)
        assert not offenders, (
            f"loaded contract.steps produced non-canonical instances: {offenders}"
        )

        delegating_steps = [s for s in contract.steps if s.delegates_to is not None]
        assert delegating_steps, (
            "expected at least one shipped 'implement' step (e.g. 'workspace') "
            "to populate delegates_to — the fixture this test relies on has drifted"
        )
        offenders = _non_canonical_instances(
            (s.delegates_to for s in delegating_steps), DelegatesTo
        )
        assert not offenders, (
            f"loaded delegates_to values are not canonical DelegatesTo "
            f"instances: {offenders}"
        )

    def test_plant_and_catch_wrong_mission_step_wiring(self) -> None:
        """Non-vacuity guard for the two behavioural tests above (FR-013).

        Feeds :func:`_non_canonical_instances` a synthetic decoy object that
        is NOT an instance of the canonical class (simulating a resolver
        accidentally wired to a same-named-but-different class) and asserts
        it is flagged. Without this test, a resolver silently rewired to
        the wrong class could pass the behavioural tests above vacuously.
        """

        class _DecoyMissionStep:
            """Same-named decoy — proves identity/usage checks have teeth."""

        from doctrine.missions.models import MissionStep

        offenders = _non_canonical_instances([_DecoyMissionStep()], MissionStep)
        assert offenders, (
            "expected the decoy instance to be flagged as non-canonical — "
            "the wrong-wiring self-test has lost its teeth"
        )


# --- Invariant 5: WP08 — mission_runtime outbound boundary (FR-009, #2327) ---


class TestMissionRuntimeBoundary:
    """WP08 / FR-009 (#2327, WS1): bind the mission_runtime -> specify_cli edge.

    ``mission_runtime`` sits BELOW ``specify_cli`` in the landscape, so importing
    upward is a layer inversion. The clean ``should_not access specify_cli`` rule
    (as used by the sibling ``TestCharterBoundary`` / ``TestGlossaryBoundary``
    classes) would red on existing, working code, so — per research D6 — the real
    upward edges are pinned as a named allowed-exception ledger
    (:data:`_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI`). This class binds the
    previously missing outbound rule and proves it is non-vacuous.

    See :data:`_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI` for the full decision record
    and the future-mission carve-out.
    """

    def test_mission_runtime_specify_cli_imports_within_ledger(self) -> None:
        """Every mission_runtime -> specify_cli edge must be in the named ledger.

        Adding a NEW ``specify_cli.<sub>`` import outside the ledger reds here —
        the intended loud signal for the carved-out future dependency-inversion
        work. This is the outbound LayerRule the WP binds.
        """
        offenders = _out_of_ledger_specify_cli_imports(
            _collect_specify_cli_imports(_MISSION_RUNTIME_ROOT),
            _MISSION_RUNTIME_ALLOWED_SPECIFY_CLI,
        )
        assert not offenders, (
            "mission_runtime imports specify_cli subpackages outside the "
            "documented allowed-exception ledger "
            "(_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI):\n  "
            + "\n  ".join(offenders)
            + "\nInvert the dependency (preferred) or, if the edge is sanctioned, "
            "add the subpackage to the ledger with a rationale comment."
        )

    def test_rule_rejects_out_of_ledger_import(self) -> None:
        """Non-vacuity guard: the matcher MUST flag a synthetic out-of-set edge.

        A rule that silently allowed everything would pass the ledger test above
        vacuously. Here we drive the SAME matcher with a synthetic
        ``specify_cli.cli`` edge (deliberately absent from the ledger) and assert
        it is rejected — proving the rule has teeth. This is the committed,
        CI-selected negative test (module marker ``architectural``; NFR-005/#2034).
        """
        synthetic = [
            ("mission_runtime/resolution.py", "specify_cli.cli.commands.tasks"),
        ]
        offenders = _out_of_ledger_specify_cli_imports(
            synthetic, _MISSION_RUNTIME_ALLOWED_SPECIFY_CLI
        )
        assert offenders == [
            "mission_runtime/resolution.py imports specify_cli.cli.commands.tasks"
        ], "the outbound rule must reject a specify_cli subpackage outside the ledger"

    def test_ledger_has_no_stale_entries(self) -> None:
        """Shrink-only guard: every ledger entry must match a live source edge.

        When future port work removes an upward edge, its ledger entry must be
        deleted too. A stale entry (no matching import under
        ``src/mission_runtime/``) reds here, keeping the exception set honestly
        minimal so the debt can only shrink.
        """
        live_subpackages = {
            _specify_cli_subpackage(module)
            for _, module in _collect_specify_cli_imports(_MISSION_RUNTIME_ROOT)
        }
        stale = _MISSION_RUNTIME_ALLOWED_SPECIFY_CLI - live_subpackages
        assert not stale, (
            f"allowed-exception ledger has entries with no live edge: {sorted(stale)!r}. "
            "Remove them — the ledger is shrink-only."
        )
