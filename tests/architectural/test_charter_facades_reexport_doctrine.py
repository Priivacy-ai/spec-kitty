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
import pathlib

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
        # Tabled during the #3321 landing squad (inverse-containment hardening,
        # below): advertised in ``__all__`` but previously identity-unchecked.
        ("SkippedProfile", "doctrine.agent_profiles.diagnostics"),
    ],
    "charter.mission_steps": [
        # MissionStep retired from the facade contract 2026-06-11: the last src/
        # consumer was correctly retyped to MissionStepContractStep (executor.py);
        # the symbol remains an explicit PEP 484 re-export for direct importers.
        # See contracts/charter-facade-modules.md addendum.
        #
        # MissionStepRepository retired from this facade's contract 2026-08-14:
        # WP02 of mission ``up-mission-type-seam-01KZY1JB`` deleted
        # ``resolve_mission_steps`` (src/charter/resolver.py), which was the
        # only src/ importer reached through *this* facade; the symbol remains
        # an explicit PEP 484 re-export for direct importers and is still
        # identity-checked (with a live src/ importer) via the
        # ``charter.missions`` facade table entry below.
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
        # Added alongside ``resolve_org_roots`` above: closes the direct
        # ``specify_cli``/``runtime`` -> ``doctrine`` reach-through that
        # ``tests/architectural/test_runtime_charter_doctrine_boundary.py``
        # forbids. Same source module, same identity-reexport shape.
        ("resolve_org_dirs", "doctrine.drg.org_pack_config"),
        # Added by the #3520 chain fold (#3525): the multi-org-pack DRG merge
        # gave `specify_cli`/`runtime` runtime callers (executor, gate_bindings)
        # a top-level need for the org-root-chain resolver and the graph loader.
        # Re-exported here — same identity-reexport shape — so those callers reach
        # doctrine through this facade rather than a lazy `doctrine.*` import that
        # `test_runtime_charter_doctrine_boundary.py` forbids.
        ("resolve_existing_org_roots", "doctrine.drg.org_pack_config"),
        ("load_graph_or_dir", "doctrine.drg.loader"),
        # ``doctrine.base`` census-drift door (WP01 FACADE-ONLY): the
        # layer-collision warning belongs on the layer-merge facade beside
        # ``merge_layers`` / ``merge_three_layers``. Consumer is WP05-owned.
        ("DoctrineLayerCollisionWarning", "doctrine.base"),
        # Tabled during the #3321 landing squad (inverse-containment hardening,
        # below). These 10 were advertised in ``charter.drg.__all__`` yet absent
        # from this table, so they were public but identity-unchecked — a
        # wrapper/shim could have replaced any of them with the gate staying
        # green. All FACADE-ONLY; identity verified live at add time.
        ("OrgDRGConflictError", "doctrine.drg.merge"),
        ("OrgDRGFragment", "doctrine.drg.org_pack_loader"),
        ("OrgPackEnvVarUnsetError", "doctrine.drg.org_pack_config"),
        ("OrgPackMissingError", "doctrine.drg.org_pack_loader"),
        # Added by mission ``doctrine-drg-silent-drop-boundary`` (#3530 landing):
        # the executor's org-pack error handling + loader now reach doctrine
        # only through ``charter.drg``, so these three doctrine re-exports join
        # the identity contract. All FACADE-ONLY; identity verified live.
        ("OrgPackParseError", "doctrine.drg.org_pack_loader"),
        ("OrgPackSchemaError", "doctrine.drg.org_pack_loader"),
        ("load_org_pack", "doctrine.drg.org_pack_loader"),
        ("OrgPackSubdirEscapeError", "doctrine.drg.org_pack_config"),
        ("UnknownRelationError", "doctrine.drg.merge"),
        ("graph_document_to_dict", "doctrine.drg.migration.extractor"),
        ("load_built_in_graph", "doctrine.drg.loader"),
        ("merge_three_layers", "doctrine.drg.merge"),
        ("model_to_graph_dict", "doctrine.drg.migration.extractor"),
        # Promoted from a private doctrine helper during the #3321 landing (the
        # post-fold squad flagged charter surfacing ``doctrine.drg.merge``'s
        # private ``_bridge_org_edge_to_drg_edge``). It is now a public symbol in
        # ``doctrine.drg.merge.__all__`` with a live runtime consumer
        # (``specify_cli.drg_writers.registry``), so it is a plain re-export.
        ("bridge_org_edge_to_drg_edge", "doctrine.drg.merge"),
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
        # Added by mission ``rc3-charter-gate-predicate-inversion-01M0GGT1`` (M3,
        # #3599): the artifact-filename seam relocated the expected-artifact
        # manifest into doctrine (C-001) and specify_cli reaches it through this
        # facade (runtime -> charter -> doctrine, test_runtime_charter_doctrine_boundary).
        ("ArtifactClassEnum", "doctrine.missions.expected_artifact_manifest"),
        ("ExpectedArtifactManifest", "doctrine.missions.expected_artifact_manifest"),
        ("ExpectedArtifactSpec", "doctrine.missions.expected_artifact_manifest"),
        ("project_artifact_name_set", "doctrine.missions.step_projection"),
        # Added by mission ``up-mission-type-seam-01KZY1JB`` WP07 (FR-006):
        # the CLI layer (``specify_cli.cli.commands.charter.mission_type``)
        # needs direct reach to the FR-001 layered factory to report a real
        # per-id ``source_layer``, not just an activation-scoped action
        # sequence -- ``specify_cli`` may only reach a FACADE-ONLY doctrine
        # module (``tests/architectural/test_doctrine_census.py``'s
        # disposition for ``doctrine.missions.mission_type_repository``)
        # through a charter door, so this door is widened rather than a new
        # direct ``doctrine.*`` import added to a CLI command file.
        ("resolve_layered_mission_types", "doctrine.missions.mission_type_repository"),
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
    # Added by mission ``operator-config-ergonomics`` (portable provenance):
    # the runtime provenance-normalizer reach-through routes through this
    # facade exactly like ``charter.pack_paths`` above, closing the direct
    # ``specify_cli``/``runtime`` -> ``doctrine.provenance`` import that
    # ``test_runtime_charter_doctrine_boundary.py`` forbids. Same source
    # module, same identity-reexport shape. FACADE-ONLY.
    "charter.provenance": [
        ("is_built_in_pack_path", "doctrine.provenance"),
        ("to_portable_source_path", "doctrine.provenance"),
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
        # Tabled during the #3321 landing squad (inverse-containment hardening):
        # advertised in ``__all__`` but previously identity-unchecked.
        ("repair_v2_synthesis_manifest_defaults", "doctrine.versioning"),
    ],
    # Not a pure "facade" (it carries local ``from_operator_token`` /
    # ``resolve_artifact_urn`` logic), but it DOES re-export two doctrine symbols
    # in ``__all__``. Tabled during the #3321 post-fold squad: the self-discovery
    # inverse gate below found these public but identity-unchecked (they escaped
    # the earlier key-scoped gate because this module was absent from the table).
    "charter.kind_vocabulary": [
        ("ArtifactKind", "doctrine.artifact_kinds"),
        ("MissionTypeNotAnArtifactKind", "doctrine.artifact_kinds"),
    ],
}

#: Top-level packages whose re-exports through a charter ``__all__`` MUST carry an
#: identity contract: ``doctrine`` (the migrated surface) plus the external
#: shared-contract packages (per the Shared Package Boundary). A charter-local
#: definition (``__module__`` under ``charter``) is not a re-export; a stdlib
#: value instance such as a ``pathlib.Path`` constant is not one either — both are
#: correctly excluded by keying on these origins rather than on "not charter".
_IDENTITY_REQUIRED_ORIGINS = frozenset(
    {"doctrine", "spec_kitty_events", "spec_kitty_tracker"}
)

_CHARTER_SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "charter"


def _charter_modules() -> list[str]:
    """Self-discover every top-level ``charter.*`` module from ``src/charter/``.

    The inverse-containment gate iterates THIS, not ``_FACADE_TABLE.keys()``, so a
    re-export module simply never added to the table (e.g. ``charter.kind_vocabulary``,
    caught by the #3321 post-fold squad) cannot hide from the check.
    """
    return [
        f"charter.{path.stem}"
        for path in sorted(_CHARTER_SRC.glob("*.py"))
        if path.stem != "__init__"
    ]


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


@pytest.mark.parametrize("facade_module", _charter_modules())
def test_facade_all_reexports_are_tabled(facade_module: str) -> None:
    """Reverse of :func:`test_facade_all_lists_every_reexport`, enforced repo-wide:
    every symbol a charter module advertises in ``__all__`` whose object ORIGINATES
    from doctrine (or an external shared-contract package) MUST carry an identity
    contract — an entry in ``_FACADE_TABLE``.

    Without this the identity gate is one-directional: a re-export placed in
    ``__all__`` but omitted from the table is public yet identity-UNCHECKED, so a
    later PR could replace it with a wrapper/shim and every gate stays green.

    Two scoping choices make the guard complete rather than manually curated:
    it is parametrized over **every** ``charter.*`` module self-discovered from
    ``src/charter/`` (not just ``_FACADE_TABLE.keys()``), so a re-export module
    absent from the table cannot hide (the ``charter.kind_vocabulary`` escape the
    #3321 post-fold squad found); and it keys on
    :data:`_IDENTITY_REQUIRED_ORIGINS`, which includes doctrine-origin re-exports
    while excluding both charter-local definitions and stdlib value instances
    (e.g. a ``pathlib.Path`` module-level constant).
    """
    facade = importlib.import_module(facade_module)
    covered = {symbol for symbol, _ in _FACADE_TABLE.get(facade_module, [])}
    untabled: list[tuple[str, str]] = []
    for name in getattr(facade, "__all__", None) or []:
        origin = getattr(getattr(facade, name, None), "__module__", None)
        if origin and origin.split(".")[0] in _IDENTITY_REQUIRED_ORIGINS and name not in covered:
            untabled.append((name, origin))
    assert not untabled, (
        f"{facade_module}.__all__ advertises re-exported symbols with no "
        f"identity contract (public but UNCHECKED): {sorted(untabled)}. Add each "
        f"to _FACADE_TABLE (promote a private doctrine symbol to a public name "
        f"before re-exporting it, rather than aliasing a private symbol)."
    )
