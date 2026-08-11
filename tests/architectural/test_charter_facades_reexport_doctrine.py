"""Architectural guard — charter facades re-export doctrine symbols by identity.

Each facade module under ``src/charter/`` that exists to proxy a doctrine
surface MUST re-export the exact doctrine object (object identity), not a
custom wrapper. This prevents a future PR from silently replacing a
re-export with a sneaky shim that drifts from doctrine.

Mission: ``charter-mediated-doctrine-selection-01KRTZCA``.
Contract: ``kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/contracts/charter-facade-modules.md``.

The table below mirrors the contract's "Symbol tables" section. When a
facade gains a new re-export, add the (symbol, doctrine-module) tuple here.
The parametrised test then asserts (a) the symbol exists on both modules
and (b) ``facade.SYMBOL is doctrine.SYMBOL`` (object identity).
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.architectural


# Mapping: charter facade module -> list of (symbol, doctrine source module).
# Keep in sync with contracts/charter-facade-modules.md "Symbol tables".
_FACADE_TABLE: dict[str, list[tuple[str, str]]] = {
    "charter.profiles": [
        ("AgentProfile", "doctrine.agent_profiles.profile"),
        ("Role", "doctrine.agent_profiles.profile"),
        ("AgentProfileRepository", "doctrine.agent_profiles.repository"),
        ("DEFAULT_ROLE_CAPABILITIES", "doctrine.agent_profiles.capabilities"),
    ],
    "charter.mission_steps": [
        # MissionStep retired from the facade contract 2026-06-11: the last src/
        # consumer was correctly retyped to MissionStepContractStep (executor.py);
        # the symbol remains an explicit PEP 484 re-export for direct importers.
        # See contracts/charter-facade-modules.md addendum.
        ("MissionStepContract", "doctrine.missions.step_contracts"),
        ("MissionStepInput", "doctrine.missions.step_contracts"),
        ("MissionStepContractRepository", "doctrine.missions.step_contracts"),
        ("MissionStepContractStep", "doctrine.missions.step_contracts"),
        # Widened by mission ``doctrine-public-api-surface-01KZPDSR`` WP03
        # (T011): the gate-binding model on a mission-step contract. FACADE-ONLY.
        ("GateBinding", "doctrine.missions.step_contracts"),
    ],
    "charter.drg": [
        # PUBLIC: re-exported from the curated public surface ``doctrine.api``
        # (WP03/T010) so the wheel symbol gains a live in-repo caller. Identity
        # holds: ``doctrine.api.ArtifactKind is doctrine.artifact_kinds.ArtifactKind``.
        ("ArtifactKind", "doctrine.api"),
        ("DRGEdge", "doctrine.drg.models"),
        ("DRGGraph", "doctrine.drg.models"),
        ("DRGNode", "doctrine.drg.models"),
        ("NodeKind", "doctrine.drg.models"),
        ("Relation", "doctrine.drg.models"),
        ("load_graph", "doctrine.drg"),
        ("merge_layers", "doctrine.drg"),
        ("resolve_context", "doctrine.drg.query"),
        ("ResolvedContext", "doctrine.drg.query"),
        # Added by mission ``doctrine-silence-guards-01KYFV7Q`` WP08. The
        # post-merge completeness check that every runtime caller merging the
        # COMPLETE graph must run; sourced from the ``doctrine.drg`` package
        # surface (not ``doctrine.drg.validator``) so the package's ``__all__``
        # entry has a real ``src/`` importer instead of being a dead export.
        ("validate_dangling_references", "doctrine.drg"),
        # Widened by mission ``doctrine-public-api-surface-01KZPDSR`` WP03
        # (T010): the DRG error hierarchy + org-root resolution + org-DRG
        # conflict absorb the ``drg.*`` reach-through cluster. All FACADE-ONLY.
        ("DRGLoadError", "doctrine.drg"),
        ("DRGValidationError", "doctrine.drg"),
        ("OrgDRGConflict", "doctrine.drg.merge"),
        ("resolve_org_roots", "doctrine.drg.org_pack_config"),
        # ``doctrine.base`` census-drift door (WP01 FACADE-ONLY): the
        # layer-collision warning belongs on the layer-merge facade beside
        # ``merge_layers`` / ``merge_three_layers``. Consumer is WP05-owned.
        ("DoctrineLayerCollisionWarning", "doctrine.base"),
    ],
    # New door (WP03/T012): mission-template / mission-type / mission-step
    # repository surfaces. All FACADE-ONLY per the WP01 census.
    "charter.missions": [
        ("MissionsRootNotFound", "doctrine.missions.repository"),
        ("MissionTemplateRepository", "doctrine.missions.repository"),
        ("MissionTypeRepository", "doctrine.missions.mission_type_repository"),
        ("builtin_mission_type_ids", "doctrine.missions.mission_type_repository"),
        ("project_template_set", "doctrine.missions.step_projection"),
        ("MissionStepRepository", "doctrine.missions.mission_step_repository"),
    ],
    # New door (WP03/T013): symbol-level model→task routing surface. PUBLIC —
    # re-exported from ``doctrine.api`` (leaf callables/types only, NOT the
    # ``.loader`` / ``.evaluator`` submodules). Identity holds transitively:
    # ``charter.model_routing.load is doctrine.api.load is
    # doctrine.model_task_routing.loader.load``.
    "charter.model_routing": [
        ("CatalogLoadResult", "doctrine.api"),
        ("RoutingRecommendation", "doctrine.api"),
        ("evaluate", "doctrine.api"),
        ("load", "doctrine.api"),
    ],
    # New door (WP03/T014): asset-resolution surface. PUBLIC — re-exported from
    # ``doctrine.api`` so the wheel symbols gain live in-repo callers.
    "charter.assets": [
        ("AssetManifest", "doctrine.api"),
        ("AssetNotFoundError", "doctrine.api"),
        ("AssetPathEscapeError", "doctrine.api"),
        ("AssetRepository", "doctrine.api"),
        ("AssetResolutionError", "doctrine.api"),
    ],
    # New narrow doors (WP03/T015). All FACADE-ONLY per the WP01 census.
    "charter.glossary_packs": [
        ("GlossaryPack", "doctrine.glossary_packs"),
    ],
    "charter.spdd_reasons": [
        ("apply_spdd_blocks_for_project", "doctrine.spdd_reasons"),
    ],
    "charter.pack_paths": [
        ("built_in_dir", "doctrine.pack_paths"),
        ("built_in_root", "doctrine.pack_paths"),
    ],
    # Widened by WP03/T015: ``resolve_template_by_id`` (WP01 found it missing;
    # ``runtime/resolver.py`` needs it in WP07/T036). FACADE-ONLY.
    "charter.template_catalog": [
        ("discover_templates", "doctrine.template_catalog"),
        ("TemplateRef", "doctrine.template_catalog"),
        ("TierRoot", "doctrine.template_catalog"),
        ("resolve_template_by_id", "doctrine.template_catalog"),
    ],
    "charter.primitives": [
        ("PrimitiveExecutionContext", "doctrine.missions"),
        ("execute_with_glossary", "doctrine.missions"),
    ],
    "charter.resolution": [
        ("ResolutionResult", "doctrine.resolver"),
        ("ResolutionTier", "doctrine.resolver"),
    ],
    "charter.versioning": [
        ("BundleCompatibilityStatus", "doctrine.versioning"),
        ("CURRENT_BUNDLE_SCHEMA_VERSION", "doctrine.versioning"),
        ("check_bundle_compatibility", "doctrine.versioning"),
        ("get_bundle_schema_version", "doctrine.versioning"),
        ("run_migration", "doctrine.versioning"),
    ],
}


def _flat_cases() -> list[tuple[str, str, str]]:
    """Flatten the facade table into a list of (facade, symbol, doctrine) tuples."""
    return [
        (facade, symbol, doctrine)
        for facade, items in _FACADE_TABLE.items()
        for symbol, doctrine in items
    ]


@pytest.mark.parametrize(
    ("facade_module", "symbol", "doctrine_module"),
    _flat_cases(),
    ids=[f"{facade}.{symbol}" for facade, symbol, _ in _flat_cases()],
)
def test_facade_reexports_doctrine_symbol_by_identity(
    facade_module: str, symbol: str, doctrine_module: str
) -> None:
    """Each facade symbol MUST be the same object as its doctrine source.

    Identity (``is``) — not equality (``==``) — is the invariant. A facade
    that wraps, aliases, or copies a doctrine symbol is a contract violation.
    """
    facade = importlib.import_module(facade_module)
    doctrine = importlib.import_module(doctrine_module)
    facade_obj = getattr(facade, symbol)
    doctrine_obj = getattr(doctrine, symbol)
    assert facade_obj is doctrine_obj, (
        f"{facade_module}.{symbol} must be the same object as "
        f"{doctrine_module}.{symbol}. Facade modules are pure re-exports — "
        "no wrappers, no aliases, no shims. "
        f"Got facade={facade_obj!r}, doctrine={doctrine_obj!r}."
    )


@pytest.mark.parametrize("facade_module", sorted(_FACADE_TABLE.keys()))
def test_facade_all_lists_every_reexport(facade_module: str) -> None:
    """Every contract symbol MUST appear in the facade's ``__all__``.

    This catches the case where a future edit imports a new doctrine symbol
    into a facade but forgets to advertise it in ``__all__``, which would
    silently break ``from charter.<facade> import *`` callers and leave the
    public surface ambiguous.
    """
    facade = importlib.import_module(facade_module)
    all_ = getattr(facade, "__all__", None)
    assert all_ is not None, f"{facade_module} must define __all__"
    expected_symbols = {symbol for symbol, _ in _FACADE_TABLE[facade_module]}
    missing = expected_symbols - set(all_)
    assert not missing, (
        f"{facade_module}.__all__ is missing contract symbols: {sorted(missing)}. "
        f"Add them to __all__ or update the contract table."
    )
