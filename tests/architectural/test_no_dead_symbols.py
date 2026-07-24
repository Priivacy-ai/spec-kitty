"""Symbol-level dead-code gate (Slice F WP02 / FR-120).

Where ``test_no_dead_modules`` ensures every module has at least one
non-test caller, this gate ensures every NAME in a module's ``__all__``
declaration has at least one non-test caller too. A public class
declared in ``__all__`` with zero callers -- the failure mode that bit
Mission B WP08 cycle 1 -- fails here.

ATDD anchor: AC-8 (covers: FR-120, FR-122).

Mechanics
---------

* Walk every ``*.py`` file under ``src/`` and collect the modules that
  declare an ``__all__`` literal at module scope (``ast.Assign`` whose
  target is ``Name(id="__all__")`` with a list / tuple of string
  literals as value).
* Walk every ``*.py`` file under ``src/`` again and collect every
  ``from <module> import <name>`` site, resolving relative imports
  against the importer's containing package (same logic as
  ``test_no_dead_modules``).
* For each ``(module, name)`` in some ``__all__``, fail if no caller in
  ``src/`` (other than the declaring module itself) imports that name
  from that module OR re-exports it from its parent package.

Tests under ``tests/`` are deliberately NOT counted as callers -- a
symbol exercised only by its own unit tests is functionally dead in the
runtime sense this gate cares about (the WP08 cycle-1 case study).

Allowlist
---------

``_SYMBOL_ALLOWLIST`` carries documented exceptions, keyed onto the
relocation-tolerant ``SymbolKey`` from ``_symbol_key.py`` (mission
``relocation-hardened-dead-code-scanners-01KX958P`` WP02 -- FR-007) instead
of a positional ``module::Name`` string. Each entry is still commented with
its original qualified name for audit traceability. A ``SymbolKey`` is
either content-tier (``(bare_name, body_hash)``, relocation-proof) or, for a
bare_name that resolves to >=2 LIVE ``__all__`` locations sharing the same
body, escalated to the module_path tier (``(bare_name, module_path,
body_hash)`` -- relocation-forfeit for that entry only, D-1/FR-005). Tier
assignment is recomputed live every gate run against the current corpus
(:func:`tests.architectural._symbol_key.classify_collisions` +
:func:`tests.architectural._symbol_key.key_tier`), NOT frozen at authoring
time -- see the module docstring of ``_symbol_key.py`` for the full design
record. Some previously hand-curated entries are no longer listed here: they
are covered instead by the T013 structural auto-exempt categories
(``_is_registered_migration_class`` / ``_is_typer_subapp_definition`` /
``_is_reexport_shim_symbol``) -- see ``test_auto_exempt_disjoint_from_hand_allowlist``
for the disjointness proof. Future entries MUST cite a rationale and a
follow-up tracker ticket per FR-303.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

import pytest

from specify_cli.ast_analysis.imports import (
    extract_static_all as _extract_all_literal,
    module_of_import_from as _resolve_import_from,
)
from tests.architectural._symbol_key import (
    CorpusModule,
    Location,
    SymbolKey,
    bind_call_accessor_aliases,
    classify_collisions,
    definition_span,
    find_module_factory_functions,
    key_tier,
    record_call_chain_attr_edges,
    resolve_symbol_key,
)

pytestmark = [pytest.mark.architectural]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"


# Symbol-level allowlist for genuine exceptions, expressed as qualified
# ``module::Name`` strings. Split into per-category frozensets so the
# ratchet-baseline meta-test (``tests/architectural/test_ratchet_baselines.py``)
# can track each category independently and apply different burn-down
# policies per category.
#
# THIS ALLOWLIST IS A RATCHET. When an entry gains a real caller,
# remove it from this set -- the test enforces shrinkage. When a new
# orphan public symbol appears, do NOT add it here as a reflex:
# investigate first, then either wire it from runtime, remove the
# name from ``__all__``, delete the symbol entirely, or add it under
# the appropriate category with a one-line rationale and (for category B)
# a follow-up tracker ticket per FR-303.

# ---------- A. Slice F charter+kernel deferred ----------
# Pre-existing public symbols in ``src/charter/`` + ``src/kernel/`` whose
# ``__all__`` membership was inherited from before WP02 and whose lack of
# runtime callers reflects a "library written but never wired" situation
# carried over from earlier missions. A future mission MUST either wire each
# from a runtime caller, remove it from ``__all__``, or delete the symbol
# entirely. Target = 0 by Slice G.
# ``is_re2_active`` -- rescued by detector (a) -- add_typer/app.command
# patterns now capture module-attr accesses (WP01 harden-dead-symbol-gate).

_CATEGORY_A_SLICE_F_DEFERRED: frozenset[SymbolKey] = frozenset(
    {
        SymbolKey("CatalogMissCause", "77f08f1610245bbd1a390b4f8dd581bc92dace80d6fcc5feab4112884171dea5"),  # charter._catalog_miss::CatalogMissCause
        SymbolKey("CharterCatalogMissError", "f0f2057a37b2ac491094023a2059ce8904848d1ae6e6e63e84b627fc508ab1b8"),  # charter._catalog_miss::CharterCatalogMissError
        # charter._catalog_miss::CharterCatalogMissWarning
        SymbolKey("CharterCatalogMissWarning", "7e5a4824e4b5a66125cf3e5ac266279983bfd23e5a02f3abd661eefaa0f93be8"),
        # charter.activations::ALLOWED_MISSION_TYPES (body_hash refreshed WP03/#2669: derived from builtin_mission_type_id_set())
        SymbolKey("ALLOWED_MISSION_TYPES", "66f78adc4726573209f4e4eba6c766601762ead6492b8a86131ef45184ef69fd"),
        SymbolKey("REGISTERED_TRIGGERS", "4582c6fc202160e4708ef2cec5b63a041e7331f9dc704abd9020800abe042c0f"),  # charter.activations::REGISTERED_TRIGGERS
        SymbolKey("CompactView", "88c5804b596411b484f9a7d6ff3404a60d31a3c554ef77b96491aa4966b5aad2"),  # charter.compact::CompactView
        SymbolKey("extract_section_anchors", "98ff665e1c40a10a69f25707ce30f4be7366667f472fb3abb3f457b8370e6633"),  # charter.compact::extract_section_anchors
        SymbolKey("StagedArtifact", "e5cac178a00a1ab09ab3a43c31edee223c69f455e050f12dd172742c15e25f8b"),  # charter.synthesizer.write_pipeline::StagedArtifact
        SymbolKey("is_re2_active", "1f449ff66fa7793bd2911da921304f2668c6c449879c96292bf8c6a8a8b2efe9"),  # kernel._safe_re::is_re2_active
    }
)


# ---------- B. Grandfathered legacy (out of WP02 scope) ----------
# Pre-existing public symbols across ``src/doctrine/`` + ``src/specify_cli/``
# whose ``__all__`` membership predates the WP02 symbol-level gate. WP02 was
# scoped to ``src/charter/`` + ``src/kernel/`` per C-007/FR-121, so these
# entries were inherited as-is into the ratchet baseline. Per the Slice F
# ratchet policy (C-004), this category MAY only shrink: growth requires an
# entry in ``_baselines.yaml`` plus a ``# justification:`` comment and a
# follow-up tracker ticket (FR-303).
#
# relocation-hardened-dead-code-scanners-01KX958P WP02: re-keyed onto
# ``SymbolKey`` (FR-007). Two stale entries dropped (FR-006):
# ``charter_activate_app`` / ``charter_deactivate_app`` no longer exist.
# ``UnifiedBundleMigration`` / ``RefreshOrientationBlockMigration`` moved to
# the T013 structural auto-exempt (``@MigrationRegistry.register`` class
# detector) -- see ``_is_registered_migration_class`` below; a dead helper or
# constant elsewhere in the same ``m_*.py`` file is still caught (DoD e).

_CATEGORY_B_GRANDFATHERED_LEGACY: frozenset[SymbolKey] = frozenset(
    {
        # doctrine.directives::ArtifactKind (escalated: live collision)
        SymbolKey("ArtifactKind", "daf6b8e8a33ac97ab1bbd7e927cd20ca85bedb05de19ec852dc58cd6184763be", module_path="doctrine.directives"),
        SymbolKey("IDENTIFIER_PATTERN", "944bd183d9ba2c291aefb749f879af6cd98fc905083ec9c8c6d11b76ec488d12"),  # doctrine.missions.models::IDENTIFIER_PATTERN
        SymbolKey("Mission", "15e9ee0fa689f7a7e779b89907e036590786ec6594a8ab27bdb062e5f9fe8fa5"),  # doctrine.missions.models::Mission
        SymbolKey("MissionOrchestration", "07d36b401f8d499e95d93e93d61fc1a9c139798fe4f7f0bf9f66939257ef965d"),  # doctrine.missions.models::MissionOrchestration
        SymbolKey("MissionStateObject", "955954fbc29b36f5c463bc5e39a04a5b24410cc31f5c0e017e8221176efae587"),  # doctrine.missions.models::MissionStateObject
        SymbolKey("MissionTransition", "9fe929fc9914ddcb8ebc8c3872fe9f1d410a7f14ea6690c82165379d980dc973"),  # doctrine.missions.models::MissionTransition
        SymbolKey("MissionRepository", "87721dffc175e1e94aa69dc020df1effd47b986d66e538eef4c49df962d684f9"),  # doctrine.missions::MissionRepository
        # doctrine.procedures::ArtifactKind (escalated: live collision)
        SymbolKey("ArtifactKind", "daf6b8e8a33ac97ab1bbd7e927cd20ca85bedb05de19ec852dc58cd6184763be", module_path="doctrine.procedures"),
        # doctrine.shared::ConflictType (escalated: live collision)
        SymbolKey("ConflictType", "34ff96f6eabe70e229d72efc5674d6050bb7291c458ee30394ebc1d629bf566e", module_path="doctrine.shared"),
        # doctrine.shared::ExtractedTerm (escalated: live collision)
        SymbolKey("ExtractedTerm", "6a7ebe24a2cc047a13b893af65d33944f51293abbd976de963a6585ef032f0ce", module_path="doctrine.shared"),
        # doctrine.shared::GlossaryScope (escalated: live collision)
        SymbolKey("GlossaryScope", "e433a93e6f5df50065e49747d40c3be1bd0957989e424a8b47ed2d75a5da4ba7", module_path="doctrine.shared"),
        # doctrine.shared::ScopeRef (escalated: live collision)
        SymbolKey("ScopeRef", "6edbfc7de81b473814e0582739ad128906a23b95ee2fed75d471b6de77860e83", module_path="doctrine.shared"),
        # doctrine.shared::SemanticConflict (escalated: live collision)
        SymbolKey("SemanticConflict", "03a7b588ce09a403baa5d3c6130231131ed3e7eb824ec18448215061a85ccd00", module_path="doctrine.shared"),
        # doctrine.shared::SenseRef (escalated: live collision)
        SymbolKey("SenseRef", "80a18c5b75e03f2202466dbc52090000b2819302b89ae90048f98125d4b89b43", module_path="doctrine.shared"),
        # doctrine.shared::Severity (escalated: live collision)
        SymbolKey("Severity", "5e9f98120dbe568255ee059f39671686982b113d4e917b6d6faf149918c81709", module_path="doctrine.shared"),
        # doctrine.shared::Strictness (escalated: live collision)
        SymbolKey("Strictness", "bf6124f24491be137dec5c0a209e381046bc032dfeea16723b313a5014d2d6af", module_path="doctrine.shared"),
        # doctrine.shared::TermSurface (escalated: live collision)
        SymbolKey("TermSurface", "92ae59dd08020d0481eb46aac5aae4d296803b7647f1c97cfd63cb157da9ed81", module_path="doctrine.shared"),
        # doctrine.tactics::ArtifactKind (escalated: live collision)
        SymbolKey("ArtifactKind", "daf6b8e8a33ac97ab1bbd7e927cd20ca85bedb05de19ec852dc58cd6184763be", module_path="doctrine.tactics"),
        SymbolKey("SemanticConflictRecord", "a8ede16418bd45b1fefb48097ef7bfc5c27d9b90ba68906f3ee7124a3c1a11dd"),  # glossary.semantic_events::SemanticConflictRecord
        SymbolKey("JsonlEventLog", "34ec3df04b36a1751a8bc959f38bc68af652b974deaa35224cc3eb86822821db"),  # runtime.next._internal_runtime.events::JsonlEventLog
        SymbolKey("ClaimablePreview", "fb24f6e5c378dfe6485d21ca6f2a9167ec885d688bc34eb53f3e3dfe7a23683a"),  # runtime.next.discovery::ClaimablePreview
        SymbolKey("AcceptanceMode", "c5cd8f94fa6b672c333faeaf3cdc781f33fee2bb29a8bb465fd7562ec85582c2"),  # specify_cli.acceptance::AcceptanceMode
        # specify_cli.acceptance::WorkPackageState -- PRUNED (coord-authority-
        # trio-degod #2464/#2465/#2508): the class body relocated to
        # specify_cli.acceptance.summary_core, re-exported via
        # `from .summary_core import WorkPackageState` in __init__.py. That
        # bare single-name re-export now matches the T013
        # `_is_reexport_shim_symbol` structural auto-exempt category, so a
        # hand-curated entry here would violate the auto-exempt/hand-allowlist
        # disjointness invariant (test_auto_exempt_disjoint_from_hand_allowlist).
        SymbolKey("RefreshResult", "8d26dc6c2df664824ed8c070ed4f488088b80dd83ab10a87f2f0cc962f60f141"),  # specify_cli.auth.refresh_transaction::RefreshResult
        SymbolKey("DaemonSummary", "17ddc7a066a9d721be767b753f6c5ecdc4dcdeca46754c67a49ef0322c1b82ab"),  # specify_cli.cli.commands._auth_doctor::DaemonSummary
        SymbolKey("DoctorReport", "3083b579d7782d2eaf3940307c5813b06ee421abfbe971d9f50355a7bd19158b"),  # specify_cli.cli.commands._auth_doctor::DoctorReport
        SymbolKey("Finding", "d47a46e21c6dc7c48f4654c3c1e88ca76cc25ae2b81b9efaaaea90649e8b2065"),  # specify_cli.cli.commands._auth_doctor::Finding
        SymbolKey("LockSummary", "089ea89da3f5099cf79f24b80f0227a7768c5880944fdb62ede8051eaed13562"),  # specify_cli.cli.commands._auth_doctor::LockSummary
        # specify_cli.cli.commands._auth_doctor::ServerSessionStatus
        SymbolKey("ServerSessionStatus", "5814547ac903022d97fd3b3a685e3218971f8e6d2407cf99d1f505f2f964b25b"),
        SymbolKey("SessionSummary", "465b7c32684be07566e692b5ef249e2585ccb568f9b2ffe36fd88ba4ed872e74"),  # specify_cli.cli.commands._auth_doctor::SessionSummary
        SymbolKey("assemble_report", "fa4ee3f45be25cf02f8878bd8077bb8e2a86ae2aa6739133650cbc5e2a840c01"),  # specify_cli.cli.commands._auth_doctor::assemble_report
        # specify_cli.cli.commands._auth_doctor::compute_exit_code
        SymbolKey("compute_exit_code", "060144b6c7b405770cc41179f7c74273e8618e6271027c42794a87f567516179"),
        SymbolKey("render_report", "719c4b8b25a0a7b9e613e559e60abacbdef6ad4ab04788e9b956b7d788ad13fb"),  # specify_cli.cli.commands._auth_doctor::render_report
        # specify_cli.cli.commands._auth_doctor::render_report_json
        SymbolKey("render_report_json", "909a351e28d3aa72e41d2986c624b5ac2eb10476fa7010667fb4d1a76993cf8e"),
        # specify_cli.cli.commands._branch_strategy_gate::GateDecision
        SymbolKey("GateDecision", "e771518baeeaa1f5ff82b36c70e2f06dea0792f9d43cd16a4361f72a3aaf5899"),
        SymbolKey("GateOutcome", "a5a38bc5a569b83b9d227c1bd2c9000aa8c1a9d6b139032c562f7da23faeb563"),  # specify_cli.cli.commands._branch_strategy_gate::GateOutcome
        # specify_cli.cli.commands.implement::_ensure_vcs_in_meta
        SymbolKey("_ensure_vcs_in_meta", "7de334239ff2b3665e555c98740eb29e5b69449795940475b748f6de3c070c80"),
        # specify_cli.cli.commands.implement::detect_feature_context
        SymbolKey("detect_feature_context", "03ce3f732e5db8d5a02fbfdcae55ae3acdaf00bdbbd3370b400b37e57fb66b81"),
        SymbolKey("find_wp_file", "4b72782a4174a1e4ac3e0dc39023effb2e0e86fb49a8fd5f3509b84a12ab8ea7"),  # specify_cli.cli.commands.implement::find_wp_file
        SymbolKey("CurrentContext", "49c03fb8a6af76f87fbae0133fd35d4c9ee8a4c5a0b7e5b49a812409af871bc7"),  # specify_cli.core.context_validation::CurrentContext
        SymbolKey("ExecutionContext", "19c71b5bbf90ee7bd3aa32f2240f9495b9ff1354ceea059d4ec54824eb0d92a1"),  # specify_cli.core.context_validation::ExecutionContext
        # specify_cli.core.context_validation::detect_execution_context
        SymbolKey("detect_execution_context", "66c12833de0af4228946dec0b95a17b58daa610f60172a5c7867ca8dbae145f1"),
        # specify_cli.core.context_validation::get_context_env_vars
        SymbolKey("get_context_env_vars", "56bf48a63174f5c63921938c0a8dcda0d19f98c00ba638e8a702aae1074dce0d"),
        # specify_cli.core.context_validation::get_current_context
        SymbolKey("get_current_context", "530ede0c50e1cc62a22df394e5677aebc9c966a146bc0e67272e3f7617e26f50"),
        SymbolKey("require_either", "d0cef5401daa9ad655fdf70d43329ecd945a77062022719cbd2e3a16f8c43805"),  # specify_cli.core.context_validation::require_either
        SymbolKey("require_worktree", "1d54252d092035cbcd73ac4705bab7cd7fd668e041d5d4125a8e93b67eeffdda"),  # specify_cli.core.context_validation::require_worktree
        # specify_cli.core.context_validation::set_context_env_vars
        SymbolKey("set_context_env_vars", "b766e1ecbde17cc1bb179f2fd9f2587caa50d9a5f7fd68c27b8588ef02137b53"),
        SymbolKey("STALE_AFTER_S_DEFAULT", "4cc4fddf416cec3b9f30b60227a6ef49ccbb4e284b60157cbc63318f63c28452"),  # specify_cli.core.file_lock::STALE_AFTER_S_DEFAULT
        SymbolKey("BranchResolution", "8ff2750e1b6b4d57f15389814bd6a09313da7c83e1c97c832a08b599030251f5"),  # specify_cli.core.git_ops::BranchResolution
        SymbolKey("has_tracking_branch", "d56afa2a06af3ad5cf4510162cc98b1fa96c3dfccf116935d8fc14ef3a2c2533"),  # specify_cli.core.git_ops::has_tracking_branch
        SymbolKey("GitPreflightIssue", "0d7ef9d2b9dd1a727e7f312f0452d3454a00afdf70f96cd4a3a60918d0fdb996"),  # specify_cli.core.git_preflight::GitPreflightIssue
        SymbolKey("GitPreflightResult", "27bc17df44fcb02a7c958848286546deb067266d6e30fe1337bdd194e7f6cd0c"),  # specify_cli.core.git_preflight::GitPreflightResult
        SymbolKey("StatusReadUnsupported", "cb3fb8a540195e5a5d9e44f0c57aeafca8af3da21dd56ae454c8566085d8f6fa"),  # specify_cli.core.paths::StatusReadUnsupported
        # specify_cli.core.paths::assert_worktree_supported
        SymbolKey("assert_worktree_supported", "d09277b8bab529fa14813600e1e8b1c40eeaad52f8939c11664500ed93ac6723"),
        SymbolKey("check_broken_symlink", "da895533a84b6c40ff500a143b2f8e31c1f0f05f0ad70936d7dde5d3689c1054"),  # specify_cli.core.paths::check_broken_symlink
        SymbolKey("resolve_with_context", "ecd3546936aecdb7a52d035c1413d9e70abc5da973e64066bfcf51544da5f69c"),  # specify_cli.core.paths::resolve_with_context
        SymbolKey("DEFAULT_TIMEOUT_S", "06ad6f73f97f6fa8fb8842f61fea9ff0bc7e8c5a6aa3cd65369ee5f09f605e76"),  # specify_cli.core.upgrade_probe::DEFAULT_TIMEOUT_S
        SymbolKey("PYPI_JSON_URL", "34521508629be2d77f48e49b4908e2e7e8baedeb8eab95ac9005b0b66ace1b36"),  # specify_cli.core.upgrade_probe::PYPI_JSON_URL
        SymbolKey("FeatureTopology", "7eb983a309007bf528c914ade5ecf049191c487a1de7457dcc663f0b6fbad30e"),  # specify_cli.core.worktree_topology::FeatureTopology
        SymbolKey("WPTopologyEntry", "c141560334391715de4dfc82c956b81426a506c4d022fca2af3509b38aa57045"),  # specify_cli.core.worktree_topology::WPTopologyEntry
        # specify_cli.core.worktree_topology::render_topology_text
        SymbolKey("render_topology_text", "f2355bf1f11119024cdc83aa9f71dfc3723ce0c0f1055798038d064eecea5b68"),
        # specify_cli.dashboard.api_types::ArtifactDirectoryFile
        SymbolKey("ArtifactDirectoryFile", "6d6d39dfb5f96086c52c2fb376fa70e288617ba0d2ec0e1eb6f90129d9c6e07c"),
        SymbolKey("ArtifactInfo", "127f2331f4b95a36680cf52accbccbb500e7ddf70f4ed1394086adf0e3381e74"),  # specify_cli.dashboard.api_types::ArtifactInfo
        # specify_cli.dashboard.api_types::CurrentFeatureDetected
        SymbolKey("CurrentFeatureDetected", "5d71a01dbf0a518810700217652bf4cb6f835430f48dffef0fa46795c530a52b"),
        # specify_cli.dashboard.api_types::CurrentFeatureNotDetected
        SymbolKey("CurrentFeatureNotDetected", "16dcad41883317c0e21ebb04366be47c864fd845acb92bbd19f1bd0a6ea27236"),
        # specify_cli.dashboard.api_types::DashboardHealthInfo
        SymbolKey("DashboardHealthInfo", "54eb82892c4caf6d73e5fe3149d6b29e7525e657fcb17a72342102a5f9affa14"),
        # specify_cli.dashboard.api_types::DiagnosticsErrorResponse
        SymbolKey("DiagnosticsErrorResponse", "cc8eda5cbc21d10d229de1e419d51da1c76b8b413d934f6b11f87509b3355c19"),
        # specify_cli.dashboard.api_types::DiagnosticsFeatureStatus
        SymbolKey("DiagnosticsFeatureStatus", "a780d167c838d00cc894ece9d79172f216da99d4283eb22df6eb7c6249c20885"),
        # specify_cli.dashboard.api_types::DiagnosticsResponse
        SymbolKey("DiagnosticsResponse", "bbebc967757d09e195e0d7b7fd63cde903321cc4c0629a74095f51e4e6a90a93"),
        SymbolKey("ErrorResponse", "92ab9716988898729741ad5fd8289d669e00e1bd87a18c8d3469f0506f508742"),  # specify_cli.dashboard.api_types::ErrorResponse
        # specify_cli.dashboard.api_types::FeaturesListErrorResponse
        SymbolKey("FeaturesListErrorResponse", "f8650806ac140e69a4a06f1c0ed809ce90a70e190daa9f7817a5d2a8c45d8377"),
        SymbolKey("FileIntegrity", "5a2f8439ee99d8d6c314eaa5ea2ba90bdb65552269804016362b3fb48e3949a7"),  # specify_cli.dashboard.api_types::FileIntegrity
        SymbolKey("KanbanStats", "b294629da998209af14c759957f0ad2a6d6479ddf5b383ae7ae6aba4476a3797"),  # specify_cli.dashboard.api_types::KanbanStats
        SymbolKey("MissionRecord", "874182d4e297344cf91fa4944d015c4183a8aa7c7004187a98497ab7ca314403"),  # specify_cli.dashboard.api_types::MissionRecord
        SymbolKey("ResearchArtifact", "3bceb1df567e06b8b2e1923f5fab8412e4eba3fd49c3ab89d5a2187635ee4b35"),  # specify_cli.dashboard.api_types::ResearchArtifact
        SymbolKey("SyncInfo", "a9b32d4636c364815cab3b0810ccdfb1e51c9c328643fdee8b867f8ae2fafaf5"),  # specify_cli.dashboard.api_types::SyncInfo
        SymbolKey("SyncTriggerSuccess", "aced0b9a63cd5f3e7442bca40d354db1a176c41d42d6ece869c2c429ba5ad155"),  # specify_cli.dashboard.api_types::SyncTriggerSuccess
        SymbolKey("WorkflowStatus", "77fd5a6326798e778a0d9d16adc37b6d87a6c6a93923fc88feca4b74cb2a1030"),  # specify_cli.dashboard.api_types::WorkflowStatus
        SymbolKey("WorktreeInfo", "16f6ed6ff09cd073c6a18e5c720c74d1ed1fa0a69799a672643cdf7bbe7b1beb"),  # specify_cli.dashboard.api_types::WorktreeInfo
        # specify_cli.dashboard.lifecycle::_write_dashboard_file
        SymbolKey("_write_dashboard_file", "ef82e6e8e295ed1b746ebbc8983b3fee53ab6f31b6d4bd143be6bfcc4a82017e"),
        SymbolKey("get_dashboard_html", "99ab224c187cd9b6ac929157228cd64e5c53eca093745248f868dc8da6008cfa"),  # specify_cli.dashboard.templates::get_dashboard_html
        SymbolKey("GovernancePolicy", "46ddf246ad782f50222cdff721814f7880aa33c8d000a88110475e71b78a6f7c"),  # specify_cli.doctrine.org_charter::GovernancePolicy
        # specify_cli.doctrine.org_charter::REQUIRED_KIND_FIELDS
        # Hash refreshed for the WP04 glossary-pack tuple extension (added the
        # ``glossary_packs`` member); still grandfathered-dead (no external src/
        # importer -- only internal use + a private ``_REQUIRED_KIND_FIELDS`` copy
        # in ``src/charter/context.py``). Body-sensitive key => extending the
        # tuple changes its content hash (see ``_symbol_key.py`` Body-sensitivity).
        SymbolKey("REQUIRED_KIND_FIELDS", "5e079a10875db742f2fffd782afc057ba2898db8cfb2ded5847e77081edff122"),
        # specify_cli.doctrine.org_charter::apply_org_charter_pre_fill
        SymbolKey("apply_org_charter_pre_fill", "559da0a61fd4f6255212b449ad4de219cb758f57501e1c5adcc1f5e5f801385b"),
        SymbolKey("AssemblyResult", "3af243769584cf1b5e44b1a04238c6a9f879b3cd8c34e05414c046d2220202f0"),  # specify_cli.doctrine.pack_assembler::AssemblyResult
        SymbolKey("ConflictItem", "ba27993ebb52415cc1de33833e170bcaf33a09aed1db8ebf396d778466992f57"),  # specify_cli.doctrine.pack_assembler::ConflictItem
        SymbolKey("ArtifactDetailResponse", "6ab904af861ebc649ce5950673d6be8ef4b65f323addde067ea3bcf61bb03f49"),  # specify_cli.dossier.api::ArtifactDetailResponse
        SymbolKey("ArtifactListItem", "6f28fdc4337d4ebecb92fdc06a278ddbbc53d2acae8258cd31257e8ec7d7eebc"),  # specify_cli.dossier.api::ArtifactListItem
        SymbolKey("ArtifactListResponse", "4cdb7c9d4c499dff5f7554bbea3b107ff0ecd7cf192d5ce93015f247ccd02542"),  # specify_cli.dossier.api::ArtifactListResponse
        SymbolKey("DossierHandlerAdapter", "02cde998eec8166a25ef083d57f52df460389227a595fe92253b069949338f5a"),  # specify_cli.dossier.api::DossierHandlerAdapter
        # specify_cli.dossier.api::DossierOverviewResponse
        SymbolKey("DossierOverviewResponse", "c0eea0f2e556ff61a368cb4f3b41b870d439b890c082c04da5a1572b5f6a330f"),
        SymbolKey("SnapshotExportResponse", "91db1cf5fefd3a5b097d6eaa6273749184caa56906c0d30a45091f3db1d6e032"),  # specify_cli.dossier.api::SnapshotExportResponse
        # (WP10/T039) ``add_history_entry`` allowlist entry removed: WP07/T028
        # deleted the module fn + manager method + ``__all__`` export, so the
        # symbol no longer exists to be dead — keeping the entry masks the next
        # dead symbol. Confirmed gone from ``src/`` at closeout.
        SymbolKey("get_field", "3b2643bff1ddd668dc6bd85daeb01169fd44248d148357b2a87858349df7db9e"),  # specify_cli.frontmatter::get_field
        SymbolKey("validate_frontmatter", "83489690099bbb23896f190267e54965a3cfbddc23084e1c9698b74fe7a9a118"),  # specify_cli.frontmatter::validate_frontmatter
        SymbolKey("SparseCheckoutKind", "7628d183a1fdd02d956c9f1557061eb221dd5ea3ffb82aeabc1c54e80e4f7409"),  # specify_cli.git.sparse_checkout::SparseCheckoutKind
        # specify_cli.git.sparse_checkout::_reset_session_warning_state
        SymbolKey("_reset_session_warning_state", "41466d1d3efede301673da3d49ae625c027c20e4f3d7fc52bd96579a1999c9be"),
        SymbolKey("scan_path", "e70cf877ec6d932f793d197349a0d7e14053758ccc5f91045553d16d32c97d8f"),  # specify_cli.git.sparse_checkout::scan_path
        # specify_cli.git.sparse_checkout_remediation::STEP_REFRESH_WORKING_TREE
        SymbolKey("STEP_REFRESH_WORKING_TREE", "2581db715e744a22f2e17f63e6d402fca97cdc7339aa1c9f5b3efad8c2f8daac"),
        # specify_cli.git.sparse_checkout_remediation::STEP_REMOVE_PATTERN_FILE
        SymbolKey("STEP_REMOVE_PATTERN_FILE", "e69c1be0f4c5698c3da5aa7699eab32bfe4e0e1c9e1e48b9c56d11273e376a97"),
        # specify_cli.git.sparse_checkout_remediation::STEP_SPARSE_DISABLE
        SymbolKey("STEP_SPARSE_DISABLE", "fc8312c094ac81778428095d3be5dc066f206fcdaa61fbd7d35311bca6b9b1cc"),
        # specify_cli.git.sparse_checkout_remediation::STEP_UNSET_CONFIG
        SymbolKey("STEP_UNSET_CONFIG", "e7d1de2d22078e3d7b215ba0f0322fb83fe982b76bc42ee70a745f58537f551f"),
        # specify_cli.git.sparse_checkout_remediation::STEP_USER_DECLINED
        SymbolKey("STEP_USER_DECLINED", "43267cc6fc081fd9cc4d453c7e98f8fa04677b6553e65b34eb29bfc0e0b4d0c1"),
        # specify_cli.git.sparse_checkout_remediation::STEP_VERIFY_CLEAN
        SymbolKey("STEP_VERIFY_CLEAN", "8504fb56e041ae5dccf1de99792afcb7354173696ee242776b4a9b40916e8704"),
        # specify_cli.git.sparse_checkout_remediation::SparseCheckoutRemediationReport
        SymbolKey("SparseCheckoutRemediationReport", "20b509762a8f1e2e9302ab37b6d1bd4467aa88843c96005d7774bde676261859"),
        # specify_cli.intake.brief_writer::CrossFilesystemWriteError
        SymbolKey("CrossFilesystemWriteError", "acd6ef68ddf571b5d10e060705595ec6757064a9fc4fcb8999cb7e359b61dc7d"),
        SymbolKey("atomic_write_bytes", "299f9a2ce9d0680ea41a791fc5817f56818ace58c9e90d841230f2fed65d2db1"),  # specify_cli.intake.brief_writer::atomic_write_bytes
        SymbolKey("atomic_write_text", "4338782faca587ec7cc4c907a9680bcf0fb2f6f01d920dae26adb3497fd7c46a"),  # specify_cli.intake.brief_writer::atomic_write_text
        SymbolKey("POLICY_TABLE", "6b1740b1daf02057f8a6eb6e475fbec6dd706b69f41184b4e74067d2cfc169eb"),  # specify_cli.invocation.projection_policy::POLICY_TABLE
        SymbolKey("ProjectionRule", "3582715cd23856b1d0e2cf14293fef2a71b5b8a7b8b178b018f33b08638b3982"),  # specify_cli.invocation.projection_policy::ProjectionRule
        # specify_cli.lanes.lifecycle_sync::LANE_AUTO_REBASE_FAILED
        SymbolKey("LANE_AUTO_REBASE_FAILED", "ac422fb0845653d0bab1cb2449584a37ca13c9b89e1bdb6170893aa23a810630"),
        SymbolKey("ClassifierRule", "e4253249c186c97ce24d24d459a758fe02f4b3ebc7f94e62d0a000edf743755f"),  # specify_cli.merge.conflict_classifier::ClassifierRule
        SymbolKey("RULES", "f2fede76cafc6c35cc093acdc068080406066dc6e5f82bf7b13575fe24359c24"),  # specify_cli.merge.conflict_classifier::RULES
        SymbolKey("Resolution", "7bc793f726da67f4273d0f5ac82d13ed3141e7a53c9c2a42bbab390b64ff46b1"),  # specify_cli.merge.conflict_classifier::Resolution
        # specify_cli.merge.conflict_classifier::r_default_manual
        SymbolKey("r_default_manual", "729111cef2a3601de1948651817b84123bea90eed651a9cd3b458377486e6d18"),
        # specify_cli.merge.conflict_classifier::r_init_imports_union
        SymbolKey("r_init_imports_union", "d72fa8545eb4e8df7dc80288ea3bcd1994adfb4d4e5ab1d18144aec8f4a29de1"),
        # specify_cli.merge.conflict_classifier::r_pyproject_deps_union
        SymbolKey("r_pyproject_deps_union", "e3633e4ef609408e8a9d8433c080edad3cf595dac30db1ca7dba0a12cc852e64"),
        # specify_cli.merge.conflict_classifier::r_urls_list_union
        SymbolKey("r_urls_list_union", "483a7c2e4e5c7ec6829ed411b4f485ae141a40ff6aaaa2d07fa588c461463bfd"),
        # specify_cli.merge.conflict_classifier::r_uvlock_regenerate
        SymbolKey("r_uvlock_regenerate", "00c7c15c6ac3c4eebd8a6a071b3c6157953733f7dcdcdf0f8c9b29d11fbf4b94"),
        SymbolKey("display_merge_order", "305ac620b2ebbb6568c8aef92428d3c8326cbca533039995280ad367fd35dd67"),  # specify_cli.merge.ordering::display_merge_order
        # specify_cli.merge.state::MergeAmbiguousStateError
        SymbolKey("MergeAmbiguousStateError", "d69fb84bf96a1edbfa84500b1c49c6eaf6c30fce35ce95659504abff5221d7c5"),
        SymbolKey("detect_git_merge_state", "1ebb0846821cef8d19a05382e249a78a78e602af5c6568fcf47746664b27e1f6"),  # specify_cli.merge.state::detect_git_merge_state
        # specify_cli.mission_brief::IntakeFileMissingError (escalated: live collision)
        SymbolKey("IntakeFileMissingError", "10c5629ceb1c89d8fa16d2dfacaac2480549638e7ce8264138959a6e9be9155c", module_path="specify_cli.mission_brief"),
        # specify_cli.mission_brief::IntakeFileUnreadableError (escalated: live collision)
        SymbolKey("IntakeFileUnreadableError", "cbc27774574a9c61c998e746fa8749b06806674e67079e3ad9e932fd2ab147e9", module_path="specify_cli.mission_brief"),
        SymbolKey("clear_mission_brief", "52ef7df6a2e4e0e40032f1b4a785936d2a9e21d322b225fd80aa119a66d99b83"),  # specify_cli.mission_brief::clear_mission_brief
        SymbolKey("MissionProtocol", "c5521662618b6e3878d62d2cbda8f5b36e658221e7925fb4faf14153c6913bd1"),  # specify_cli.mission_v1::MissionProtocol
        SymbolKey("load_mission", "ff1a5a3dc0abab0af9244e16db29da088093f66a6ee1a6cd80477abdf731b6d9"),  # specify_cli.mission_v1::load_mission
        SymbolKey("load_mission_by_name", "489d0f9a1c2e1bce4062ba94ff015d79148f4b105c660813bd1156a139178d4a"),  # specify_cli.mission_v1::load_mission_by_name
        # specify_cli.missions::PrimitiveExecutionContext (escalated: live collision)
        SymbolKey("PrimitiveExecutionContext", "8d0ff32282080dcc0ee90b8fd3ba8ba5c9f41d4a20886979453df1db4ce64561", module_path="specify_cli.missions"),
        # specify_cli.missions::execute_with_glossary (escalated: live collision)
        SymbolKey("execute_with_glossary", "5942ba731fd9b815adc70427f1098602d157e8bdb6cbfb9c103c2939246ef368", module_path="specify_cli.missions"),
        SymbolKey("SRC_FALLBACK_GLOB", "98996636a6168fb393c855815769613ceeb84fd88ded2ea37b7ac2fe659048b1"),  # specify_cli.ownership.inference::SRC_FALLBACK_GLOB
        # specify_cli.ownership.inference::SRC_FALLBACK_WARNING
        SymbolKey("SRC_FALLBACK_WARNING", "bf26744e04d9f2a94ff9647ec65de398875b3bdbfcb74764ba9081379e54c223"),
        # specify_cli.ownership.validation::validate_authoritative_surface
        SymbolKey("validate_authoritative_surface", "987d09f98ff07d79a1de805e4e088add4719c804056cf500b37e843c201a9357"),
        # specify_cli.ownership.validation::validate_execution_mode_consistency
        SymbolKey("validate_execution_mode_consistency", "72de0a50923215a33589efddc79177f751fdf05c4a5b46a2c86616b9d7ceb96f"),
        # specify_cli.ownership.validation::validate_no_overlap
        SymbolKey("validate_no_overlap", "53fd8afa15dbb6f34b94541da3a2e4b183cf91a4c3170fbd0ed77223918cacd5"),
        SymbolKey("detect_unfilled_plan", "a939602c9997240b49616668817fffbab7af31432e65813252b4afccbff57424"),  # specify_cli.plan_validation::detect_unfilled_plan
        SymbolKey("_is_windows", "e45defef9fec1c1c49c25645cb3f12af0773098ea15f2c5c34a44e6995409704"),  # specify_cli.runtime.home::_is_windows
        # specify_cli.runtime.resolver::ResolutionResult (escalated: live collision)
        SymbolKey("ResolutionResult", "a49e0d4f6645139569e84bec5471e1f3cfa6ee507aa530454f76265290ddca58", module_path="specify_cli.runtime.resolver"),
        # specify_cli.runtime.resolver::ResolutionTier (escalated: live collision)
        SymbolKey("ResolutionTier", "5503356030b4f173a85df71b0ddd839476675f23c6f80a53bd381a0a1e8004cb", module_path="specify_cli.runtime.resolver"),
        SymbolKey("AssetDisposition", "80538ab23937dae2a0ae5057b94162ab6d3ee08ee7df23683f57a650eccd4580"),  # specify_cli.runtime::AssetDisposition
        SymbolKey("MigrationReport", "281c091735269501f17e11de13a8ea2e88a1ce97fe4e08034928d55be34e8a6f"),  # specify_cli.runtime::MigrationReport
        SymbolKey("OriginEntry", "1f789caf3d0bbf11391ca36704de0ab247e6693ea437be93b9598850463dbf29"),  # specify_cli.runtime::OriginEntry
        # specify_cli.runtime::ResolutionResult (escalated: live collision)
        SymbolKey("ResolutionResult", "a49e0d4f6645139569e84bec5471e1f3cfa6ee507aa530454f76265290ddca58", module_path="specify_cli.runtime"),
        # specify_cli.runtime::ResolutionTier (escalated: live collision)
        SymbolKey("ResolutionTier", "5503356030b4f173a85df71b0ddd839476675f23c6f80a53bd381a0a1e8004cb", module_path="specify_cli.runtime"),
        SymbolKey("classify_asset", "7d40a0db5e655cbd1457c6f28d6a5069a31642a0cde6c94149179003e86a7932"),  # specify_cli.runtime::classify_asset
        SymbolKey("SkillRegistry", "c01cd024b561b9115a36d3487195aac21d78bd7262a02d993702e4346c51c16b"),  # specify_cli.shims::SkillRegistry
        SymbolKey("SCHEMA_VERSION", "8fb29803d3d131301db2bbe72bbaab5314981664272c6a9d57f2a75684ae1811"),  # specify_cli.skills.manifest_store::SCHEMA_VERSION
        SymbolKey("load", "7689780b2e4a040cfc29e5b540406167217369b98795702cc6c496cb1c9a2b7c"),  # specify_cli.skills.manifest_store::load
        SymbolKey("save", "222fabd1e77c7d011d9fc0b583fd27d7c8a044cf0fe17fdce0a59c95583b1172"),  # specify_cli.skills.manifest_store::save
        SymbolKey("MISSION_CREATED", "cee8959200ec2e6304a1ff8d59dd8eb356bf76108ecdf4ba8210ff4522fbebdc"),  # specify_cli.status.lifecycle_events::MISSION_CREATED
        # specify_cli.status.lifecycle_events::MISSION_EVENTS_FILENAME
        SymbolKey("MISSION_EVENTS_FILENAME", "725b94e955667ce901d7080717a134b4f0b6da5c5efc829f5fc9e98353d9afc9"),
        # specify_cli.status.lifecycle_events::PROJECT_EVENTS_FILENAME
        SymbolKey("PROJECT_EVENTS_FILENAME", "27f95adf27cd2fb348df3cd92afb8f6bd3c015697e237d232da23bfa900f74fe"),
        # specify_cli.status.lifecycle_events::PROJECT_INITIALIZED
        SymbolKey("PROJECT_INITIALIZED", "ee097bd3221c588159762747beceb7db48856f2f323d8551524f02e238770723"),
        SymbolKey("WP_CREATED", "4f61af61cf1570deb1b34ef633f688e26483b680cc965d27f75415e188289732"),  # specify_cli.status.lifecycle_events::WP_CREATED
        # specify_cli.status.lifecycle_events::append_lifecycle_event
        SymbolKey("append_lifecycle_event", "44bbd8d10caea88cf4765a3952d39b9c790cb33de16111d5110aa3fb2d574659"),
        # specify_cli.status.lifecycle_events::has_lifecycle_event
        SymbolKey("has_lifecycle_event", "ded63398ebd799f9cbdb0519033bf4ed4cb4dee39e51837f7c1b1fe7d562e69d"),
        # specify_cli.status.lifecycle_events::project_event_log_path
        SymbolKey("project_event_log_path", "b865a8c81e88c0816fd94a24242e9bfff14f6504da477813fc99b160049f3f70"),
        # specify_cli.status.uninitialized_hint::find_wp_dependency_cycles
        SymbolKey("find_wp_dependency_cycles", "5b6258f4436930d9c732a9afc04d5261c137cd98c5b976a780e137d482e97135"),
        SymbolKey("SyncDiagnostic", "ea3c1a482cae9570db15cadcdf12eaefbe1ec3841d82c512dc67177c455f40b6"),  # specify_cli.sync.diagnostics::SyncDiagnostic
        SymbolKey("reset_emitted_codes", "52fe7de8627d0dc2f62a726e39459f8512f20d4ab8206445dd91dc23b8dd20fb"),  # specify_cli.sync.diagnostics::reset_emitted_codes
        SymbolKey("SweepReport", "7ea93e8eac2a372c62bf080a8b9af326064800e2c072fe7a8ef01111ba1c1c10"),  # specify_cli.sync.orphan_sweep::SweepReport
        # specify_cli.task_metadata_validation::TaskMetadataError
        SymbolKey("TaskMetadataError", "a5f4d63d6b2895e3143710b52553986e2c34ee1170b0a2c65909f19b8776aee7"),
        # specify_cli.task_metadata_validation::detect_lane_mismatch
        SymbolKey("detect_lane_mismatch", "4318eac514483a8a366cb66673d4a595fec81e0664b7fc0a6d27d945148b542a"),
        # specify_cli.task_metadata_validation::validate_task_metadata
        SymbolKey("validate_task_metadata", "204dce3e2bd29c165be77f41d8e43b39b81c0a424e5ab947800272e07e8e73c3"),
        # specify_cli.template.asset_generator::_convert_markdown_syntax_to_format
        SymbolKey("_convert_markdown_syntax_to_format", "e8bc1f720dcafc3536917329a9cd279c81e544c390050d4d651a33f96418709b"),
        SymbolKey("PROBLEMATIC_CHARS", "2c28f74e9e567401e971a4c8fb4d8d88e441d7ade49d950e0bd1208a3d514b41"),  # specify_cli.text_sanitization::PROBLEMATIC_CHARS
        # specify_cli.text_sanitization::sanitize_markdown_text
        SymbolKey("sanitize_markdown_text", "1531f4eece348d60d229144a81fc098028060a79d91d8ccd0fad3f8ec0ca2f34"),
        # specify_cli.tracker.origin::search_origin_candidates
        SymbolKey("search_origin_candidates", "b8ff826597fe523e0b2fa3297300ff1ffceff4f39c8bd0e9e061104aae7b019a"),
        # specify_cli.tracker.origin::start_mission_from_ticket
        SymbolKey("start_mission_from_ticket", "16f1e4cf5ba62e5e10c1d4622b62549922f9b149432897f11696e00e7e8cac8a"),
        # specify_cli.upgrade.migrations.m_3_2_0rc35_unified_bundle::MIGRATION_ID
        SymbolKey("MIGRATION_ID", "2141404f3e6b3f0f036403171fd8dd34a0f4ac8775a0c19082a55bf7d3d939ad"),
        # specify_cli.upgrade.migrations.m_3_2_0rc35_unified_bundle::TARGET_VERSION
        SymbolKey("TARGET_VERSION", "ea06e5f0a28dd3c9678a78930f7dab5d64ba2f054bfdbbd6e4b1052bd94d0b6b"),
        # specify_cli.upgrade.migrations::MigrationDiscoveryError
        SymbolKey("MigrationDiscoveryError", "541864310809d0a9f476f2963151b6468ced74b86082c66d0e0e3e420cbd133f"),
        # specify_cli.validators.csv_schema::CSVSchemaValidation
        SymbolKey("CSVSchemaValidation", "9492562d2a8ff78e95fe51a2eb532a7046b2c26e8a04281d800551d07ccb8b9c"),
        SymbolKey("PathValidationResult", "0c06a5f97dbf0bd590850ce8c7bb5067852f3edfbcbf7dc58dcec264b37e55da"),  # specify_cli.validators.paths::PathValidationResult
        # specify_cli.validators.paths::suggest_directory_creation
        SymbolKey("suggest_directory_creation", "43ab52fd99963aff65a61cac707bfa4e7460fb71e515f636c9e79960290f90f7"),
        SymbolKey("APA_PATTERN", "e225a418edd433afa959eaafb07895bb8ff165314b82c6a9bd13b5708fd3c3ce"),  # specify_cli.validators.research::APA_PATTERN
        SymbolKey("BIBTEX_PATTERN", "1f6ccd16b6d0e71a858aefb3f51f1bb54628c060140af6aec7148bb44a00f18a"),  # specify_cli.validators.research::BIBTEX_PATTERN
        SymbolKey("CitationFormat", "c9a89a89f61089daf873da3b26960c6ddea341d6bbe8707db968efb0f3e8aef7"),  # specify_cli.validators.research::CitationFormat
        SymbolKey("CitationIssue", "a2f57e836d2dc4705cd00e84c6a29b265dbde10052802f024f050d405ce5e0c4"),  # specify_cli.validators.research::CitationIssue
        # specify_cli.validators.research::CitationValidationResult
        SymbolKey("CitationValidationResult", "2f404bee806cbe15605248cad74d39dc91004b7411a6346c37d02e5da7da1426"),
        # specify_cli.validators.research::ResearchValidationError
        SymbolKey("ResearchValidationError", "8e0de7c1ce2abc09e2e26ef2b86891a533d23a5b62d3f58918fb08c5747a8284"),
        SymbolKey("SIMPLE_PATTERN", "a2435238e81b44f25766109d814ec803c148c3a29e2d85d47e30ab096042c7b9"),  # specify_cli.validators.research::SIMPLE_PATTERN
        # specify_cli.validators.research::VALID_CONFIDENCE_LEVELS
        SymbolKey("VALID_CONFIDENCE_LEVELS", "c160515f343ad25476a372943d437d1cf393ea028115d2a91855bc41645c7ddb"),
        # specify_cli.validators.research::VALID_RELEVANCE_LEVELS
        SymbolKey("VALID_RELEVANCE_LEVELS", "34722f8e96555350ed3f46a0f61ea69354855e42a78f72f88f54a1a04190d535"),
        # specify_cli.validators.research::VALID_SOURCE_STATUS
        SymbolKey("VALID_SOURCE_STATUS", "6b50ea350d414cf3e31225b4ee1c1116cf4eac86922853b8568fba9792e89771"),
        SymbolKey("VALID_SOURCE_TYPES", "ca324041c550e4de017a74c75c66dc5e74ae08a64dca757367f149b082209d5a"),  # specify_cli.validators.research::VALID_SOURCE_TYPES
        # specify_cli.validators.research::detect_citation_format
        SymbolKey("detect_citation_format", "77028d1d9914eae810073eb37c535a3ff246d8505abfeee0f3b362f93278ad7d"),
        SymbolKey("is_apa_format", "c93231c83488d6ec02f061ed0abb668970978ef80f41c46796dc3ff6d7553b19"),  # specify_cli.validators.research::is_apa_format
        SymbolKey("is_bibtex_format", "a405d08064337875f5131fc8ace8adbdc0166926571fb9e4bafe123d954383e3"),  # specify_cli.validators.research::is_bibtex_format
        SymbolKey("is_simple_format", "554f7f44d63e6bfb35c044e79f4cc227be18d10799e7d43ab117123fbbf72a47"),  # specify_cli.validators.research::is_simple_format
        SymbolKey("validate_citations", "c8f28b75658a499c19b3bea2a86ecd2460289cf32811fdb472279ffaac16d44b"),  # specify_cli.validators.research::validate_citations
        # specify_cli.validators.research::validate_source_register
        SymbolKey("validate_source_register", "c9828e462d4312022aabd276cfddac19d8839c37480d692a1f54fc874ceca9d9"),
        # specify_cli.widen.interview_helpers::render_widen_hint_if_present
        SymbolKey("render_widen_hint_if_present", "488672b20073c5fb098086f3a277c270b6bfada6f1efc571c7ea6d3030286011"),
    }
)


# ---------- C. WP-in-flight Slice F charter symbols ----------
# ``OperationalContext.require_active_profile`` / ``.require_active_role``
# entries dropped (relocation-hardened-dead-code-scanners-01KX958P WP02):
# these were never real ``__all__`` bare names (only module-level names are
# ever checked by ``_compute_offenders``) -- inert no-ops under the OLD
# string-keyed allowlist too, so dropping them changes no gate behaviour.

_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE: frozenset[SymbolKey] = frozenset(
    {
        # charter.consistency_check::ConsistencyReport entry pruned
        # (doctrine-tension-edges-01KY1WPC): removed from __all__ instead of
        # re-pinning the hash -- no external caller imports it by name (only
        # consumed via attribute access on run_consistency_check()'s return
        # value), matching this file's own CharterYamlCorruptError precedent.
        # charter.invocation_context::ContextPreconditionError
        SymbolKey("ContextPreconditionError", "ed270fe330c24f71db20d7c033d1246499b83b3bad558fc526fc4620bddd67af"),
    }
)


# ---------- C. WP-in-flight Slice F workflow registry symbols ----------
# WP11 removal trigger reached: all four symbols now have live src/ callers.

_CATEGORY_C_WP_IN_FLIGHT_WORKFLOW_REGISTRY: frozenset[SymbolKey] = frozenset()


# ---------- C. Charter command split legacy patch surface ----------
# Both entries rescued by detector (a) (module-attribute accesses).

_CATEGORY_C_CHARTER_SPLIT_LEGACY_PATCH_SURFACE: frozenset[SymbolKey] = frozenset()


# ---------- C. Mission #1348 coordination-branch atomic event log ----------
# Public helper symbols for missions/coordination-branch topology; each is
# exercised by integration + unit tests, with production wiring tracked
# under Priivacy-ai/spec-kitty#1355 / #1356.

_CATEGORY_C_WP_IN_FLIGHT_COORDINATION_BRANCH: frozenset[SymbolKey] = frozenset(
    {
        # specify_cli.missions._create::CoordinationBranchResult
        SymbolKey("CoordinationBranchResult", "dc567286f5c65649bf53e959fae163eda7bc545db28e0cd59828ba382728a790"),
        # specify_cli.missions._create::coordination_branch_name
        SymbolKey("coordination_branch_name", "8fa08bd97424675f219df65dde32de3212f4087b60ec407994190a9aad26e01b"),
        # specify_cli.missions._resolve_planning_branch::resolve_planning_branch_from_meta
        SymbolKey("resolve_planning_branch_from_meta", "ab0a19c05c45f58a95bb0a95e12757a2036e6a6a690238e3f19332e336c53582"),
    }
)


# ---------- C. WP-in-flight topology authority seam (mission 01KTYGTE) ----------
# ``ResolvedStatusSurface`` is the return type of the already-wired
# ``resolve_status_surface_with_anchor``; callers consume the value, not the
# name. No follow-up tracker -- lone remaining transitive-consumption entry.

_CATEGORY_C_WP_IN_FLIGHT_TOPOLOGY_AUTHORITY: frozenset[SymbolKey] = frozenset(
    {
        # specify_cli.coordination.surface_resolver::ResolvedStatusSurface
        SymbolKey("ResolvedStatusSurface", "9e509c1b3194a519661e3613738bfa2c69e145820701bba61c1c56cfe49ef501"),
    }
)


# ---------- C. WP-in-flight unified MissionStep model (mission 01KSWJVX) ----------
# Public surface for the unified ``MissionStep``/mission-type model, shipped
# ahead of production callers landing in later WPs of the same mission
# family. Follow-up tracker: mission-internal WP03/WP04/WP05.

_CATEGORY_C_WP_IN_FLIGHT_UNIFIED_MISSION_STEP: frozenset[SymbolKey] = frozenset(
    {
        SymbolKey("StepKey", "6b982c25b6d2735411195c4e785e71c6178eca1ce51e18c0b656f7f44bdd0edc"),  # doctrine.missions.mission_step_repository::StepKey
        SymbolKey("IDENTIFIER_PATTERN", "944bd183d9ba2c291aefb749f879af6cd98fc905083ec9c8c6d11b76ec488d12"),  # doctrine.missions.models::IDENTIFIER_PATTERN
        SymbolKey("Mission", "15e9ee0fa689f7a7e779b89907e036590786ec6594a8ab27bdb062e5f9fe8fa5"),  # doctrine.missions.models::Mission
        SymbolKey("MissionOrchestration", "07d36b401f8d499e95d93e93d61fc1a9c139798fe4f7f0bf9f66939257ef965d"),  # doctrine.missions.models::MissionOrchestration
        SymbolKey("MissionStateObject", "955954fbc29b36f5c463bc5e39a04a5b24410cc31f5c0e017e8221176efae587"),  # doctrine.missions.models::MissionStateObject
        SymbolKey("MissionTransition", "9fe929fc9914ddcb8ebc8c3872fe9f1d410a7f14ea6690c82165379d980dc973"),  # doctrine.missions.models::MissionTransition
        SymbolKey("DelegatesTo", "e43595becef9482b7caa76b2e901db98a5f48737237d6c1aac8b74b64c32b9ee"),  # doctrine.missions.step_contracts::DelegatesTo
    }
)


# ---------- C. WP-in-flight charter-pack activation layer (01KSYE4V) ----------
# New public symbols across charter/doctrine/specify_cli whose only callers
# today are the test suite or later WPs still in development. Follow-up
# tracker: mission-internal WP06/WP08 (CLI wiring).

_CATEGORY_C_WP_IN_FLIGHT_CHARTER_ACTIVATION: frozenset[SymbolKey] = frozenset(
    {
        SymbolKey("ActivationResult", "3caa63e1d20b223d5052be3797c81a938ab823a04087c3fe7a4ca6fa7d82aec7"),  # charter.pack_manager::ActivationResult
        SymbolKey("MergeResult", "cc0c8d09dc8bd0cc0152b7bee385aefdedb9f555cc1e6ac4593a009b38b25093"),  # charter.pack_manager::MergeResult
        SymbolKey("StepKey", "6b982c25b6d2735411195c4e785e71c6178eca1ce51e18c0b656f7f44bdd0edc"),  # doctrine.missions.mission_step_repository::StepKey
        SymbolKey("AffectedMission", "aca1c4d1ccf40c858667a7ca7fc09a28197e3b7ed559beffd1c72e4ed91f5a1f"),  # specify_cli.charter_activate::AffectedMission
        SymbolKey("StepRemovalWarning", "508dec1c957b44c16c889862c20780e4d64148a0918785d8edd5ff094aa66ccf"),  # specify_cli.charter_activate::StepRemovalWarning
        # specify_cli.doctrine.org_charter::OrgCharterCycleError
        SymbolKey("OrgCharterCycleError", "15ac7dc4906c07d6bbfeab8cd3051ed1872032f497dfe23b680eb118c0126740"),
        # specify_cli.doctrine.org_charter::OrgCharterExtensionError
        SymbolKey("OrgCharterExtensionError", "5351ebd8c29db6ce6682b7c0a92db5b9f433157d77f4c1985e030d0b8f7aae69"),
    }
)


# ---------- C. org-doctrine close-out (mission-authored public surface) ----------
# Public charter/doctrine API symbols awaiting production callers that ship
# in later WPs of the same mission family, or intentionally discoverable
# public surface that is only test-exercised today. Re-derived each cycle,
# not a standing tracker (the mission owns them).

_CATEGORY_C_ORG_DOCTRINE_CLOSEOUT: frozenset[SymbolKey] = frozenset(
    {
        SymbolKey("ActivationPlan", "49697a5e9d4ea41ac9531c0b4bb6605a8aa71bf116e0dfbf1af2eee33a935a53"),  # charter.activation_engine::ActivationPlan
        SymbolKey("DeactivationPlan", "527c491b7df6c1369bc3f4c7491626817a5a3a2ede574ffe4527168fde17bf43"),  # charter.cascade::DeactivationPlan
        SymbolKey("REFERENCE_RELATIONS", "923c7531fa07a59396d69e256ee38a05448b62f4d75cde08c9fbaa932376a8ca"),  # charter.cascade::REFERENCE_RELATIONS
        SymbolKey("ReferencedArtifact", "80d3c02ebae2c466ff75be630ecfd259036be62ea0a1394dbab6503f75414afc"),  # charter.cascade::ReferencedArtifact
        SymbolKey("SharedSkip", "5eaddd3d5d18e386fc96f4ad558b21289c0bf7955cc70cfadca308d234f3ff5b"),  # charter.cascade::SharedSkip
        # doctrine.drg.org_pack_loader::AUGMENTATION_RELATIONS
        SymbolKey("AUGMENTATION_RELATIONS", "724f4741d69125ccfd2bb664f8f05739fb4a2372220636958b84476741738af0"),
        SymbolKey("TOPOLOGY_KINDS", "eb1deec7b602719bb1ada5074ee99c1bf01b1df4faa1370845f9e8f65b341e9e"),  # doctrine.drg.org_pack_loader::TOPOLOGY_KINDS
        # doctrine.drg.org_pack_loader::merge_topology_artifact
        SymbolKey("merge_topology_artifact", "8b3946b11d7220f921e402afa6152d2d33907b8743465c34a56e681e676539e9"),
        # ``template_id_for`` and ``template_urn`` left the allowlist in
        # mission-step-creatability-01KXQA6R WP06 (S-C / #2724): the DRG
        # extractor's template-instantiation pass
        # (``doctrine.drg.migration.extractor.extract_template_instantiation_edges``)
        # is now their first live non-test caller, so the dead-symbol gate
        # (FR-008) requires them removed. ``template_node``/``template_nodes``
        # stay allowlisted -- still no live caller.
        SymbolKey("template_node", "dea39c9ec49890b233342ad15392800be8606946f3ad2964e995969792c9b0e0"),  # doctrine.template_catalog::template_node
        SymbolKey("template_nodes", "84573a47cbf040c8d00b413ada1f52225e2131371dd580393fbc88ac226404dd"),  # doctrine.template_catalog::template_nodes
        SymbolKey("PackHealth", "82268603b58f8a1449a0bf97456ddf08c217c11de4d66d85a41afc56819f7eee"),  # specify_cli.cli.commands._doctrine_health::PackHealth
    }
)


# ---------- C. Upstream session-presence public surface (pre-existing on main) ----------
# Two module-level constants used internally by ``UpgradeChecker`` but with
# no import-site caller in src/ yet. NOT this mission's code -- surfaced only
# because the mission's ``src/specify_cli/status/`` changes triggered the
# ``core_misc`` path filter. Follow-up: wire or prune when callers land.

_CATEGORY_C_UPSTREAM_SESSION_PRESENCE: frozenset[SymbolKey] = frozenset(
    {
        SymbolKey("CACHE_PATH", "65335e57687d24eac92dec11e6cd5d4099547d3a60bb633501912b789b5ddfa2"),  # specify_cli.session_presence.upgrade_check::CACHE_PATH
        SymbolKey("TTL_SECONDS", "12e366f07395dad9d3e750719e906194509f2ec6f0e16a5a9b180be893795962"),  # specify_cli.session_presence.upgrade_check::TTL_SECONDS
    }
)


# ---------- C. Quality-debt epic #1928 ----------
# ``PathValidationError`` is the public exception raised by
# ``validate_mission_paths(..., strict=True)``; the sole runtime caller
# invokes it non-strict. Deliberate public API. Tracked under #1928 (FR-303).

_CATEGORY_C_QUALITY_DEBT_1928: frozenset[SymbolKey] = frozenset(
    {
        SymbolKey("PathValidationError", "85f3d9bc44e166ee3f73f0bccfa146e43b23e3ac019402238fddda73f670e56f"),  # specify_cli.validators.paths::PathValidationError
    }
)


# ---------- C. Branch-naming legacy-failover seam ----------
# Both symbols are LIVE -- the gate only counts cross-file src/ ``__all__``
# importers, so a test-only hook and an intra-module env read are invisible
# to it (NOT dead). Manufacturing a fake src/ importer is the anti-pattern
# this gate warns against, so they are allow-listed instead.

_CATEGORY_C_BRANCH_NAMING_FAILOVER_SEAM: frozenset[SymbolKey] = frozenset(
    {
        # specify_cli.lanes.branch_naming::LEGACY_FAILOVER_SUPPRESS_ENV
        SymbolKey("LEGACY_FAILOVER_SUPPRESS_ENV", "957586eb65e3ce121ded2ef48b5d57a4a72909a7ae1a254d4929a39f8e6428b3"),
        # specify_cli.lanes.branch_naming::reset_legacy_failover_warning
        SymbolKey("reset_legacy_failover_warning", "7b006e531bb376166d109ca44ba745608b0e558e55f69565e21f83469c19c8c9"),
    }
)


# ---------- C. Test-facing agent.tasks re-export compatibility ----------
# relocation-hardened-dead-code-scanners-01KX958P WP02: all three remaining
# entries (_lane_targets_for_emit / _wp_lane_from_status_events /
# compute_incomplete_dependents) are pure re-export-shim symbols whose
# underlying definition has a live caller elsewhere -- now covered by the
# T013 structural auto-exempt (``_is_reexport_shim_symbol``); category
# emptied, kept defined for the burn-down record.

_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT: frozenset[SymbolKey] = frozenset()


# ---------- C. Merge god-module decomposition shim re-exports (mission #2057) ----------
# The ``cli/commands/merge.py`` god-module was decomposed into cohesive
# seams under ``specify_cli/merge/`` (behavior-preserving refactor). FR-006
# mandates the thin command shim re-export every relocated symbol so
# existing importers keep working with zero import edits.
#
# relocation-hardened-dead-code-scanners-01KX958P WP02: 59 of the 65
# pure re-export names (``specify_cli.cli.commands.merge::*``) are now
# covered by the T013 structural auto-exempt (``_is_reexport_shim_symbol``)
# -- each resolves via a single-alias ``ImportFrom`` whose origin definition
# has a live caller elsewhere. ``BaselineMergeCommitError`` stays hand-listed
# because its bare name is a LIVE COLLISION bare_name (escalated to the
# module_path tier by the FR-005 classifier) -- collision bare_names are
# never auto-exempt (T012's escalate-or-fail-close path must see them). The
# 13 seam-INTERNAL helpers stay hand-listed too: they are locally DEFINED
# (not re-exported) in their seam module, just lacking a cross-file src/
# caller after the decomposition moved the consuming call to a sibling seam
# -- a different shape than a re-export shim.

_CATEGORY_C_MERGE_DECOMP_SHIM_REEXPORT_2057: frozenset[SymbolKey] = frozenset(
    {
        # specify_cli.cli.commands.merge::BaselineMergeCommitError (escalated: live collision)
        SymbolKey("BaselineMergeCommitError", "f63bb04588cfd7df1144a1e646283b39e2bcc28ae152b07a0799b34f0f91c65b", module_path="specify_cli.cli.commands.merge"),
        # specify_cli.merge.bookkeeping_projection::_assert_status_surface_file_path_is_trusted
        SymbolKey("_assert_status_surface_file_path_is_trusted", "d0447f87156c6860ac0a96338fe409aeda51ea18cf317fdc4430fd32945778cd"),
        # specify_cli.merge.bookkeeping_projection::_read_optional_bytes
        SymbolKey("_read_optional_bytes", "ff9a424ce926fdeb80a67f95e6350ef8b4107a3fcf9a3192f57d6fed6db076a8"),
        # specify_cli.merge.bookkeeping_projection::_restore_optional_bytes
        SymbolKey("_restore_optional_bytes", "d34e2cf5f0c1325386d4747c6111cd696a89d476dde3ced2018182c0dfba6fdb"),
        SymbolKey("_already_baked", "42470ebca7e82026542624079c0cbafeaa3a5dc53ca3a653b2a4c196492bd93c"),  # specify_cli.merge.ordering::_already_baked
        # specify_cli.merge.ordering::_compute_next_mission_number_or_none
        SymbolKey("_compute_next_mission_number_or_none", "a1b9c06e3368d481c463b2c09a7a9055923219ddc4de8cd33d6d52bc5f73182d"),
        # specify_cli.merge.ordering::_is_assigned_mission_number
        SymbolKey("_is_assigned_mission_number", "4da9f3fde4e20df83693697787af0a7ef0e4399b21c99bd102b9b3a899e34fe1"),
        # specify_cli.merge.ordering::_mark_mission_number_baked
        SymbolKey("_mark_mission_number_baked", "aa2e64b018e1d7ecc47f73211c291d16934d659b8f4b07b472e200225d99e72b"),
        # specify_cli.merge.ordering::_write_mission_number_to_branch (body_hash
        # refreshed lifecycle-gate-execution-context: body edited, key is
        # content-tier and body-sensitive by design -- see _symbol_key.py
        # "Body-sensitivity" note; still a seam-internal helper, zero cross-file
        # src/ caller)
        SymbolKey("_write_mission_number_to_branch", "38e9704c5b132c12d81d3be921a257f0e340f58264fba5909703bb088b523fc2"),
        SymbolKey("check_push_safety", "893124ff3029dec30c538fd54577881f4afa05002067b4f1033ce550f52e0460"),  # specify_cli.merge.push_preflight::check_push_safety
        SymbolKey("_extract_mission_slug", "834a3e235860c64046504604c6f21d21f5a8c2e8443ef33b8c4ad6ad07c2e934"),  # specify_cli.merge.resolve::_extract_mission_slug
        # specify_cli.merge.resolve::_iter_merge_states_for_slug
        SymbolKey("_iter_merge_states_for_slug", "7685ecbbf713921090d3265d6df803e98839f0b4f2a75795f0903478009b10e7"),
        # specify_cli.merge.resolve::_merge_state_key_candidates
        SymbolKey("_merge_state_key_candidates", "19d7cf2fd2d776af5d5fbcbb8f51ad77ea23659a5533b4777176e1e8aa42d113"),
    }
)


# ---------- B. T001-unblinded symbols (WP01 harden-dead-symbol-gate) ----------
# The T001 bug in ``_extract_all_literal`` caused any module with a
# top-level ``ast.AnnAssign`` before ``__all__`` to be silently zeroed. WP01
# fixed the parser; these symbols surfaced as offenders for the first time.
# Grandfathered at the same "investigate + wire/prune/delete" policy as
# ``_CATEGORY_B_GRANDFATHERED_LEGACY``. Burns down when each symbol is
# wired, removed from ``__all__``, or deleted (FR-303).

_CATEGORY_B_T001_UNBLINDED: frozenset[SymbolKey] = frozenset(
    {
        # specify_cli.auth.transport::AsyncAuthenticatedClient
        SymbolKey("AsyncAuthenticatedClient", "f55c360aa798fa78dafc366bdb643c863d5d1a56aa2d130c276b808095516f0e"),
        SymbolKey("AuthRefreshFailed", "ceaa6c4e7772ec4cf012512c1fa9504f988aa3522df697264ecbb6025bc0367d"),  # specify_cli.auth.transport::AuthRefreshFailed
        SymbolKey("AuthenticatedClient", "fdca768debf63f3f84eb7a9119b9b1e219094c9210840fdd433cf2a5bd3d0fc9"),  # specify_cli.auth.transport::AuthenticatedClient
        SymbolKey("get_async_client", "784e28c299d00ac9210b69146d666fec3d77103b9475c9306bf9350d458a2f5a"),  # specify_cli.auth.transport::get_async_client
        SymbolKey("get_client", "c8a14f890fac446b89c410dc11a379b5b759c7e8c0e7e041a23413b06a00a313"),  # specify_cli.auth.transport::get_client
        SymbolKey("reset_clients", "3f0f27d532f29c06c5a85a9415ac60db6e5f5421ca4732d8e9a12bf69eb0e9b3"),  # specify_cli.auth.transport::reset_clients
    }
)


# ---------- C. event-sync retention/delivery mission public surface ----------
# Mission ``event-sync-retention-delivery-01KVYWRG`` (#2124) shipped two new
# domains plus a ``sync.migrate_journal`` migration. The names below are the
# remaining mission public surface: the locked per-WP test-contract plus the
# C-008 OPT_OUT discard-safety machinery, whose LIVE runtime enforcement is
# deferred to the legacy-queue retirement follow-up (mission-review-report
# DRIFT-1/RISK-1). Tracked in
# ``kitty-specs/event-sync-retention-delivery-01KVYWRG/issue-matrix.md``.

_CATEGORY_C_EVENT_SYNC_RETENTION_DELIVERY: frozenset[SymbolKey] = frozenset(
    {
        SymbolKey("AuditSink", "1db149c15d93c2e917fb6c942a5dcd9a9fb1b8309af911d0ad060d962544bdf9"),  # specify_cli.delivery.config::AuditSink
        SymbolKey("Delivery", "b6ae32688201dfdb4daf70060f1071b62a7ddc2ea123c32b4d0c65de5440ecce"),  # specify_cli.delivery.config::Delivery
        SymbolKey("DiscardAuditRecord", "dab90db7f8fa5c751b0379858c0a9877fe88ff8caf0b658291736ffeaeba32d9"),  # specify_cli.delivery.config::DiscardAuditRecord
        SymbolKey("DiscardDecision", "e7aa1c068489ec6ce9075c33bfc025a5ed1b3546309995989b7f9d01080f2c93"),  # specify_cli.delivery.config::DiscardDecision
        SymbolKey("DiscardDecisionKind", "d205655876907c0b0d9765caebcf188ef255e41cba21bfad0d85c09560e9736c"),  # specify_cli.delivery.config::DiscardDecisionKind
        SymbolKey("FamilyClassification", "7dce11f428dfaca1671eedfe1649ecf07d0803d5cf9bb2046e5b4c40b99f2f40"),  # specify_cli.delivery.config::FamilyClassification
        SymbolKey("JsonlAuditSink", "c5348817f0566cb012cd9be73c5e243c7a19b4d2e76a7f77f78b8a6ae345914f"),  # specify_cli.delivery.config::JsonlAuditSink
        # specify_cli.delivery.config::MissingExternalEndpointError
        SymbolKey("MissingExternalEndpointError", "b92bf3e32108adf605bb484a0427e057ed7f7318d1ba7554b5159a81603567e8"),
        # specify_cli.delivery.config::PolicyResolutionError
        SymbolKey("PolicyResolutionError", "937326d99123aab38978177224911a0de39b93c8143da4498727c870c23263f0"),
        SymbolKey("ReceiverFactory", "8bffbd5ba44ccbea82402e5cfeb6915399fb1ea6336abfe5dea1fed5d953b850"),  # specify_cli.delivery.config::ReceiverFactory
        SymbolKey("ResolvedPolicy", "b9143d0f72c90606233e8e85d20950068b660049e318009aea6c83557707f6d8"),  # specify_cli.delivery.config::ResolvedPolicy
        SymbolKey("ResolvedTarget", "249eb5ca981d52ddbba5fc8f8468dacd27c5262d5dce4e51abc3f8e25003d258"),  # specify_cli.delivery.config::ResolvedTarget
        SymbolKey("Retention", "e4346975f8569d23e351047f7b4a892c1b73f40d8e5579ddf6748d06819f2367"),  # specify_cli.delivery.config::Retention
        SymbolKey("UnknownModeError", "5065dd65ecc8c46ce95b5c762c83b139fd66c21fa6c6d3125a761034ac0033eb"),  # specify_cli.delivery.config::UnknownModeError
        SymbolKey("discard_decision", "e0c5fd8606d658c33140576b9ddeaace7e88ab9ea9030b536047a9d8e9988c40"),  # specify_cli.delivery.config::discard_decision
        SymbolKey("LEDGER_INDEX_NAME", "00ff2374543242c1a9bb343f02ce2a4119d806a11f317a6b569f631332aeebca"),  # specify_cli.delivery.ledger::LEDGER_INDEX_NAME
        SymbolKey("LedgerRow", "8120a15f278fab95a5e1eda3af4bc646b746555a8f4ac31e9bcf44559b0da3e3"),  # specify_cli.delivery.ledger::LedgerRow
        SymbolKey("TERMINAL_STATUSES", "39cfb0bb7ccf29fe7683659c8e5648022bc1fa98b30069fdee81822c103fe7bd"),  # specify_cli.delivery.ledger::TERMINAL_STATUSES
        SymbolKey("init_ledger", "95d75b9f2c0c5692072a02c2145128f9fe47e82e9a47120235d5c77bfae3f4ec"),  # specify_cli.delivery.ledger::init_ledger
        SymbolKey("BATCH_ENDPOINT_PATH", "ca95ace141f4fdf0e9b45beded0c05ad7eacbf89e4d6d3db6035fd7d17fcc644"),  # specify_cli.delivery.receivers::BATCH_ENDPOINT_PATH
        # specify_cli.delivery.receivers::BATCH_TIMEOUT_SECONDS
        SymbolKey("BATCH_TIMEOUT_SECONDS", "b369a7d782ba7ef5f063929fda2b130c0a53b2044621b8d19dd3afe495d3d226"),
        SymbolKey("GateDecision", "63e6f6d31d87a0baa8128896db70bcd1a281aef33f9cdc64dc7a4fc1f825dd99"),  # specify_cli.delivery.receivers::GateDecision
        SymbolKey("GateKind", "5b6ccac48cf9723e99c997a1f70c7af1f481e819abb62e251d9b3814fd71d05e"),  # specify_cli.delivery.receivers::GateKind
        SymbolKey("HttpResponse", "424e7dd151b9e7abdea1693be40b486e5755f23c7a23fef775d06f3864217935"),  # specify_cli.delivery.receivers::HttpResponse
        SymbolKey("ReceiverGate", "222316c26a75df8f8d97c3423fa0d49fdbd2f6326362a53fd1cb8de155f30298"),  # specify_cli.delivery.receivers::ReceiverGate
        SymbolKey("STUB_ENDPOINT_URL", "bf67c1a0cecca5dd72e30cc6a6a0e2b3cef8c69dd363929c13f96bcd5129079d"),  # specify_cli.delivery.receivers::STUB_ENDPOINT_URL
        SymbolKey("StubReceiver", "aeba7292204499407e90549f03b49684b4539e6baea89dab4158f58cf41bcbcc"),  # specify_cli.delivery.receivers::StubReceiver
        SymbolKey("map_batch_response", "608a6a0ba7eb0439166cd843f95d8fcbb2a1cd61f13e7b081e6daa596f4730d2"),  # specify_cli.delivery.receivers::map_batch_response
        # specify_cli.delivery.status_report::ADDITIVE_SECTION_KEYS
        SymbolKey("ADDITIVE_SECTION_KEYS", "45f0e694af41633f3bf4de2228ba6e52905e1c41a5d9cdbb8c1e67f5b256472a"),
        # specify_cli.delivery.status_report::BODY_UPLOAD_COMPAT_KEY
        SymbolKey("BODY_UPLOAD_COMPAT_KEY", "339aee253812a3490f03a4fc4e1e4e8492c0f62fc5813a55db35b3f22ca79a3e"),
        # specify_cli.delivery.status_report::DELIVERY_LEDGER_KEY
        SymbolKey("DELIVERY_LEDGER_KEY", "d3df6fb989f2687421cd363713117eda8a903ca2b7482791740e12a296cde217"),
        # specify_cli.delivery.status_report::DELIVERY_TARGETS_KEY
        SymbolKey("DELIVERY_TARGETS_KEY", "f44d437e6c09d172b81e68a322038fdf78712517331cbb0f9e4515be21d612c5"),
        SymbolKey("EVENT_JOURNAL_KEY", "4e41a05ccac292750359c3be4216534255f1a19bc0c2e70afb07a3b0d8930321"),  # specify_cli.delivery.status_report::EVENT_JOURNAL_KEY
        # specify_cli.delivery.status_report::GC_LARGE_JOURNAL_THRESHOLD_BYTES
        SymbolKey("GC_LARGE_JOURNAL_THRESHOLD_BYTES", "bae60652257ec6420577d1642eefcc61afc08fb6bec3facc14f60cc5ad4e5074"),
        # specify_cli.delivery.status_report::MIGRATION_CONFLICTS_KEY
        SymbolKey("MIGRATION_CONFLICTS_KEY", "2b593112d73a14ba353d22c5408b3fbdf6d3672e1f0aeac6f948aee093ee7827"),
        # specify_cli.delivery.status_report::TARGET_AUTHORITY_KEY
        SymbolKey("TARGET_AUTHORITY_KEY", "e07abf140b944fdac04293e228c927c0e3d47e6e3668a0efb02f889d22202d8f"),
        # specify_cli.delivery.status_report::TERMINAL_FAILURES_KEY
        SymbolKey("TERMINAL_FAILURES_KEY", "59fcb2d13859d17054c2b2ec3102d40e6e06a507128e071bca2079e3fa8a9640"),
        # specify_cli.delivery.status_report::evaluate_gc_suggestion
        SymbolKey("evaluate_gc_suggestion", "ec86dd1fd2dac37f7f480eb7e3d7b6f5454ba1b5231f574c5d3232894751e64a"),
        # specify_cli.event_journal.coalesce::CoalescingStrategy
        SymbolKey("CoalescingStrategy", "04e781848fa8cfb8dd5dbf2b31dac5d5a1a519a59861d405dde3d9c9dd03dbd4"),
        # specify_cli.event_journal.coalesce::DeliveredAnywhereQuery
        SymbolKey("DeliveredAnywhereQuery", "006197fe8e8930ae3340613069f631fd0478c9aed0b95416e3c951db65c9c70b"),
        SymbolKey("SUPERSEDED_TABLE", "0692924492f1bdbd44f223bb9f42c90fc80d9f5f5aa324dc6b291d597565d346"),  # specify_cli.event_journal.coalesce::SUPERSEDED_TABLE
        SymbolKey("SupersedeMarker", "28103221c51dc7ad13004841818581069756ef63456a93fd398760b0e9934968"),  # specify_cli.event_journal.coalesce::SupersedeMarker
        SymbolKey("install", "49e1cbe2531458103c6492184d179bc70a1707789487b439a4815b4e21ec58ef"),  # specify_cli.event_journal.coalesce::install
        # specify_cli.event_journal.coalesce::read_supersede_markers
        SymbolKey("read_supersede_markers", "5aef05a234dd7a63b420970cc73a1d2cdf3b2b2acf8aa65add08722b4a5d2905"),
        SymbolKey("JOURNAL_SUBDIR", "43ec497396ce60afcd8ef2916a2646172c1c3775c05813cb212642144d8e1d62"),  # specify_cli.event_journal.journal::JOURNAL_SUBDIR
        SymbolKey("ORDERED_COLUMNS", "37527823ca5422a7d0efeec9b8c3d4843e8ebff3a1da0714b53a483cf9f2e4ca"),  # specify_cli.event_journal.models::ORDERED_COLUMNS
        SymbolKey("KNOWN_PREFIX", "98ecae0739efcb4413e222ecc96031896d1c57e85b9bf934884cbbdb1b2bb838"),  # specify_cli.sync.migrate_journal::KNOWN_PREFIX
        SymbolKey("LEGACY_DIGEST", "170c1daeecd9635cf72713656060e38404f956d4305108275d591c11ecb86d29"),  # specify_cli.sync.migrate_journal::LEGACY_DIGEST
        SymbolKey("MIGRATION_NOTE", "5ed3a197746b627274ddde481632dffb952714f486217193e06475ec10ea466d"),  # specify_cli.sync.migrate_journal::MIGRATION_NOTE
        SymbolKey("MigrationConflict", "28bc71565ef0e26abdfd20e5a6ebb85e30bca5600c6ae1584371a75e2ebc62e9"),  # specify_cli.sync.migrate_journal::MigrationConflict
        SymbolKey("SourceDb", "359bad378deef3920559bea9d89645c9a7aa2d84ff0c14ae315047fb9e5a3e22"),  # specify_cli.sync.migrate_journal::SourceDb
        SymbolKey("SourceOutcome", "e5222067e3eba9771531b0a8364d898136c13fbfa5757cbd3b40a50cf8ce30a2"),  # specify_cli.sync.migrate_journal::SourceOutcome
        SymbolKey("UNKNOWN_PREFIX", "8f1aac4b29244ee6faa6b237b3fdbe471d1ea66cdd9afd0370727053535c2791"),  # specify_cli.sync.migrate_journal::UNKNOWN_PREFIX
        # specify_cli.sync.migrate_journal::discover_source_dbs
        SymbolKey("discover_source_dbs", "b62fbc49144c13965d68cc210612005523d6b3fdf2cb224737ab11bfb035197d"),
        # specify_cli.sync.migrate_journal::migration_target_token
        SymbolKey("migration_target_token", "bce7a50af7aefac52a1f1b1319dba5f0ba128f8d67ac449c16e9cf1986cbf6a0"),
    }
)


# sync-daemon-orphan-cleanup-01KWC2A3 (#2261): the ``ResetResult`` per-entry
# dataclasses are the public structured-reporting surface for
# ``auth doctor --reset`` (FR-005), constructed/asserted directly by the
# auth-doctor + orphan-sweep test suites but with no in-``src/`` importer
# because production code consumes them only through ``ResetResult``.

_CATEGORY_C_SYNC_RESET_RESULT_ENTRIES: frozenset[SymbolKey] = frozenset(
    {
        SymbolKey("FailedEntry", "0e1aa316dd07e92dedc924494897d393b9e8410bb718b8884698933da58900e9"),  # specify_cli.sync.orphan_sweep::FailedEntry
        SymbolKey("SkippedEntry", "d55962bfd4eb368c36e7204231f5dd79c7c677768ca27db70fc0c0d21950547f"),  # specify_cli.sync.orphan_sweep::SkippedEntry
        SymbolKey("SweptEntry", "e74ae7b75e826cf7e213e08728c1ef15d7ba42dad631136512d9ed2527f1304f"),  # specify_cli.sync.orphan_sweep::SweptEntry
    }
)


# ---------- C. runtime-bridge-degod-01KX8M1C (#2531) compat-surface entries ----------
# ``runtime_bridge``'s ``__all__`` is a deliberate, spec'd 8-name public surface
# (contracts/compat-surface.md: "Introduce __all__ for the 8 public names
# (sibling merge.py parity)"; mirrored by the FR-007 comment at the top of
# the ``__all__`` block in runtime_bridge.py itself). The 4 dynamically-
# accessed entries -- ``get_or_start_run``/``query_current_state``/
# ``answer_decision_via_runtime`` via ``cli.commands.next_cmd``'s
# ``_runtime_bridge_module()`` patchable lazy accessor (docstring: "Return
# the patched bridge when tests/consumers installed one") and
# ``mission_loader.command``'s ``from runtime.next import runtime_bridge``
# + attribute access; ``QueryModeValidationError`` is read off the same
# patched accessor in ``next_cmd._run_query_mode`` -- previously required a
# hand-curated allowlist row because the gate's static scanner could not
# see either shape: a function-return-bound module reference is invisible
# to any AST import walk, and an un-aliased ``from X import Y`` binding a
# submodule (``alias.asname is None``) is skipped by
# ``_build_alias_map_and_consts`` by design (T004 -- only ``as``-aliased or
# flat ``import module`` bindings populate the module-attr alias map).
# WP05 (FR-002) wires detector (e) -- first-party dynamic call-accessor
# access, ``_record_dynamic_call_accessor_edges`` -- into
# :func:`_imports_by_target` proper, so the gate now recognises these 4
# names as live via ``_runtime_bridge_module()``'s call-bound accessor
# pattern WITHOUT a permanent allowlist row; the 4 entries are removed
# here in the same commit. Converting the call sites to a direct
# ``from runtime.next.runtime_bridge import get_or_start_run`` was
# considered and rejected: it would defeat the very patchability the
# dynamic accessor exists for and breaks a live regression test
# (``tests/integration/test_identity_coord_read.py::
# test_answer_flow_get_mission_type_reads_primary_type``, which
# monkeypatches ``next_cmd._runtime_bridge_module`` and asserts the
# patched fake is actually invoked). The whole surface is independently
# guarded end-to-end by ``tests/runtime/test_bridge_compat_surface.py``
# (behavioral sentinel + static AST re-export guard covering these same
# three canonical entries). Tracker: #2531 (runtime-bridge-degod), #2559.

_CATEGORY_C_RUNTIME_BRIDGE_DEGOD_COMPAT_SURFACE: frozenset[SymbolKey] = frozenset()


# ---------- C. mission-type-drg-edges (#2677) charter.drg facade re-export ----------
# ``charter.drg`` is a contract-required FACADE module: the
# ``runtime-charter-doctrine-boundary`` plan (docs/plans/doctrine, ~L57) and the
# ``charter-facade-modules.md`` Symbol table mandate it re-export ``load_graph``
# so consumers reach the DRG loader through ``charter.drg.*`` -- an invariant
# independently enforced by ``test_charter_facades_reexport_doctrine``. WP03 of
# this mission rerouted the LAST in-``src/`` consumer of ``charter.drg.load_graph``
# to ``load_built_in_graph``, so the contract-required re-export now has no
# cross-file src/ caller (removing it would break the facade gate -- two-gate
# tension). ``load_graph`` is a LIVE COLLISION bare_name (3 live ``__all__``
# locations; ``charter.drg`` + ``doctrine.drg`` share a body_hash), so the
# FR-005 classifier escalates it to the module_path tier and it is deliberately
# NOT covered by ``_is_reexport_shim_symbol`` (escalated keys are hand-curated
# by design). Tracker: #2677 (FR-303).

_CATEGORY_C_MISSION_TYPE_DRG_EDGES_FACADE_REEXPORT: frozenset[SymbolKey] = frozenset(
    {
        # charter.drg::load_graph (escalated: live collision) -- contract-required
        # facade re-export (charter-facade-modules.md) with no internal caller
        # after WP03 rerouting -- same status as MissionStep.
        SymbolKey("load_graph", "ae679d7777f4e1d2ba6289c8aeef09d3f9f179ddf5d4f3501f631fcf2593a8aa", module_path="charter.drg"),
    }
)


# ---------- C. mission-step-creatability (01KXQA6R) WP07 URN resolution lane ----------
# ``resolve_template_by_urn`` / ``TemplateURNError`` are the by-URN
# compatibility-contract lane for template resolution (C-004,
# ``contracts/name-urn-resolution.md``). WP07's scope is FR-010-bound to
# "add the lane + a by-URN==by-name equivalence test only" -- wiring a real
# production consumer is explicitly out of scope for this WP. The real
# consumer (`charter context --include template:<id>`) lands in a later
# mission/WP, so these two names are exported but currently have zero
# production importers. Follow-up tracker: #2761.

_CATEGORY_C_URN_RESOLUTION_LANE: frozenset[SymbolKey] = frozenset(
    {
        # specify_cli.runtime.resolver::resolve_template_by_urn -- compatibility-contract
        # URN lane (C-004/FR-010); consumer wired in #2761
        SymbolKey("resolve_template_by_urn", "9bb6376d69e172430d4dbebb61800f0be7b11cd48522bb0201e6a4b2e8ad9b3d"),
        # specify_cli.runtime.resolver::TemplateURNError -- compatibility-contract
        # URN lane (C-004/FR-010); consumer wired in #2761
        SymbolKey("TemplateURNError", "226a29599f205cd275a02a6ccd97545c8af1bc82ace37003d4ab2017c5b3b813"),
    }
)


# ---------- C. consolidate-charter-bundle (01KXSYB9) WP04 extractor retirement ----------
# charter-deadcode-noop-campsite WP02: ``charter.extractor`` (the ``Extractor``
# class this category used to allowlist) is fully deleted -- the module has
# zero non-test src/ callers, and its test-only dependents were retired or
# reconstructed without it. Category fully drained (formerly gated here
# pending final class deletion; now closed).


# ---------- C. consolidate-charter-bundle WP01 shared write-helper vocabulary ----------
# ``charter.charter_yaml_io.update_charter_yaml_section`` (the INV-9 single
# writer all three charter.yaml mutators -- activation_engine.commit_plan,
# pack_manager.merge_defaults, compiler.write_compiled_charter -- route
# through) IS wired with a live src/ caller. ``OWNED_SECTIONS`` (the public
# vocabulary of section names callers may name) and
# ``UnknownCharterYamlSectionError`` (the typed error the helper raises for
# an unrecognised section) are the module's public *contract* surface for
# that call, but every current caller passes a literal section string
# rather than importing the vocabulary/exception to validate against --
# so neither symbol itself has a cross-file src/ importer yet. Library-
# primitive, test-exercised (tests/charter/test_charter_yaml_io.py
# validates both the accepted-section vocabulary and the raised-on-unknown
# contract). WP07 (consolidate-charter-bundle-01KXSYB9, #2773) declines to
# force an artificial caller (e.g. a defensive pre-check duplicating the
# helper's own validation) purely to satisfy this gate. Follow-up tracker:
# #2773 (wire a real caller, e.g. a CLI/validation surface that echoes
# ``OWNED_SECTIONS`` back to an operator, or fold the two symbols out of
# ``__all__`` in a dedicated follow-up).

_CATEGORY_C_WP_IN_FLIGHT_CHARTER_YAML_IO_WRITE_HELPER: frozenset[SymbolKey] = frozenset(
    {
        # charter.charter_yaml_io::OWNED_SECTIONS
        SymbolKey("OWNED_SECTIONS", "64c7a3f3de0c69de219050aed3e63d0f50a2ad8162997d0efa52be16deff81c3"),
        # charter.charter_yaml_io::UnknownCharterYamlSectionError
        SymbolKey("UnknownCharterYamlSectionError", "9671c9b4163dbb4c718cf85bc3850ed8643fbf1d92ea63c7e296040e7197328a"),
    }
)


# ---------- C. scopesource-gate-followup-01KY6S9P WP04 single-factory-construction hub ----------
# WP04 (this WP, epic #2535 half A follow-up, tracker #2873) landed the FR-014
# rewire: ``tasks_move_task._mt_resolve_scope_source`` now delegates to WP02's
# ``resolve_scope_source`` factory instead of hard-constructing
# ``GateCoverageScopeSource`` directly, and ``pre_review_gate.py`` no longer
# imports ``GateCoverageScopeSource`` at all (its former direct uses --
# ``_live_filter_groups``/``_live_composite_routing`` -- were retired
# alongside the census tier they backed, FR-001). Every concrete
# ``ScopeSource`` implementer below is genuinely alive at runtime --
# ``resolve_scope_source`` selects and constructs one of them on every
# ``for_review`` move -- but by DESIGN (the structural-Protocol port,
# ``ScopeSource``/``ScopeBreakdownSource``) callers outside this module never
# name the concrete class: they receive a value through the factory and use
# it polymorphically (``scope_source.test_command()``, ``.scope_breakdown()``,
# ``.file_to_scope()``), so this cross-module-import gate's heuristic never
# sees a wiring edge for the concrete classes themselves, no matter how
# thoroughly they are exercised. Proven live + correct end-to-end by ~40
# tests across ``tests/review/test_scope_source.py``,
# ``test_pre_review_gate_engine.py``, and ``test_baseline_lifecycle.py``.
_CATEGORY_C_SCOPE_SOURCE_FACTORY_CONSTRUCTED: frozenset[SymbolKey] = frozenset(
    {
        # specify_cli.review.scope_source::GateCoverageScopeSource -- constructed
        # exclusively via resolve_scope_source() (same-module) since WP04's FR-014
        # rewire; real caller confirmed via tasks_move_task._mt_resolve_scope_source
        # -> resolve_scope_source -> GateCoverageScopeSource(...).
        # Content-hash re-pin (landing fold #2892): parse_results now consumes
        # parse_mode's result in its branch condition (was a discarded call),
        # moving the class body hash b6749c1 -> 07f52ef. Still same-module-constructed.
        SymbolKey("GateCoverageScopeSource", "07f52ef5a1d46d26494964082ad14dbe83e7009c88987837e4096b3de4226be8"),
        # specify_cli.review.scope_source::DeclaredCommandScopeSource -- constructed
        # exclusively via resolve_scope_source() (same-module); consumed
        # cross-module only structurally, through the ScopeSource port (never
        # imported by concrete name outside scope_source.py by design).
        # Content-hash re-pin (landing fold, mission scopesource-gate-followup):
        # parse_mode/parse_results were stabilized to an outcome-invariant
        # strategy label (SOURCE_MISMATCH fail-open fix), moving the class body
        # hash 0ed7a0e -> fac6a9d. Symbol is still same-module-constructed only.
        SymbolKey("DeclaredCommandScopeSource", "fac6a9dffbf00049014f5397114a40ed36ebc4be66a09a23028dd7422400e6b9"),
        # specify_cli.review.scope_source::FileScopeBreakdown -- the return value
        # of GateCoverageScopeSource.scope_breakdown(); consumed structurally
        # (attribute access) by pre_review_gate._scope_result_from_breakdown,
        # never imported there by concrete type name.
        SymbolKey("FileScopeBreakdown", "870689c5e51f6e752f05b416fa7fc03111f98f07263f8d330cfb2383ef1193ae"),
        # specify_cli.review.scope_source::ScopeBreakdownMixin -- inherited only
        # by GateCoverageScopeSource, same-module; the mixin's file_to_scope
        # default projection (FR-006) is exercised by every narrowing-source
        # test but the mixin class itself is never imported cross-module.
        SymbolKey("ScopeBreakdownMixin", "c54d14c1c0c52cbd24231e9cc6bbf90ea9c988b830edce5628bb5d32da27fae4"),
    }
)


# ---------- C. lifecycle-gate-execution-context (#1834/#2885/#2795/#2882) forward seams ----------
# Mission ``lifecycle-gate-execution-context`` (FR-303 dead-symbol case, no new
# tracker ticket) landed some surfaces still awaiting a real cross-module caller:
#
# * ``acceptance/execution_context.py::SurfaceHeadResolver`` is a ``Callable[[Path],
#   str]`` type alias used ONLY as the annotation on
#   ``GateExecutionContext.assert_at_ref``'s ``head_of`` parameter -- the C5
#   ref-agreement gate (``gates_core._assert_ref_agreement``, wired into the
#   ACCEPT-phase acceptance-matrix gate) calls ``assert_at_ref()`` with the default
#   resolver and never needs to inject a substitute in production, so this alias is
#   exercised only by the direct unit tests that inject a fake ``head_of`` for
#   ``tests/acceptance/test_gate_execution_context.py``'s isolated-method cases. A
#   type alias consumed purely as a signature annotation is never a ``from ... import``
#   site by construction.
# * ``acceptance/execution_context.py::CannotEvaluateReason`` -- its
#   ``SURFACE_CANNOT_HOLD_FACT`` member is produced by ``surface_cannot_hold`` (wired
#   into the acceptance-matrix gate via ``gates_core._matrix_surface_cannot_hold``) and
#   its ``BELOW_MINIMUM_PHASE`` member by ``not_applicable_below`` (still genuinely
#   unwired -- no gate in this mission's scope declares a phase floor yet). Both
#   producing methods return the enum member as an attribute of the ``CannotEvaluate``
#   they build; ``gates_core.py`` reads ``cannot.reason.value`` structurally off that
#   instance (mirrored by the C5 path, which reads ``exc.error_code`` off the raised
#   ``GateSurfaceRefMismatch`` the same way) rather than importing the enum type by
#   name, so the type itself has no cross-module import site even though its members
#   are live.
# * ``acceptance/post_consolidation.py`` (``verify_deferred_invariants`` /
#   ``PostConsolidationResult`` / ``PostConsolidationViolation`` /
#   ``InvariantViolation``) is WP06/T031's Op, dispatched ad hoc via
#   ``spec-kitty dispatch`` -- by design "there is no new CLI verb and no
#   call-in from merge/executor.py" (module docstring; zero ``merge/``
#   coupling is a load-bearing contract constraint, C7) and
#   ``scripts/ci/check_dangling_deferrals.py`` is deliberately "zero-coupled to
#   src/specify_cli" (its own docstring) so it duplicates the wire value
#   instead of importing this module. A plain library function with a real,
#   documented caller (docs/guides/accept-and-merge.md
#   #deferred-invariants-and-the-post-consolidation-gate) that is never a
#   static ``src/`` import by design.
# * ``cli/commands/archive.py`` (``create`` / ``list_archives``) are Typer
#   command callbacks registered by the ``@app.command(...)`` decorator; the
#   real runtime caller is Typer's own dispatch against ``archive_module.app``
#   (wired in ``cli/commands/__init__.py``), never a ``from ... import create``
#   site.
_CATEGORY_C_LIFECYCLE_GATE_EXECUTION_CONTEXT_2841: frozenset[SymbolKey] = frozenset(
    {
        # specify_cli.acceptance.execution_context::CannotEvaluateReason
        SymbolKey("CannotEvaluateReason", "169f6e0b84cc22cc54ed339999b26191c66ce24fb4b8c4f4d9e87ba82852c55d"),
        # specify_cli.acceptance.execution_context::SurfaceHeadResolver
        SymbolKey("SurfaceHeadResolver", "1b5124eac062ce4ebeec680cbd3d867d602747896eab7ae166162f65427653a2"),
        # specify_cli.acceptance.post_consolidation::InvariantViolation
        SymbolKey("InvariantViolation", "2ef6e1e24afd16c2e6d0ea942a09f82189f61f7c4e081d33e2bb7f4fcb513f2d"),
        # specify_cli.acceptance.post_consolidation::PostConsolidationResult
        SymbolKey("PostConsolidationResult", "d657817ba43238e2bbae83261e6acb8eb65a28de60a15496087166021594fb30"),
        # specify_cli.acceptance.post_consolidation::PostConsolidationViolation
        SymbolKey("PostConsolidationViolation", "6e97a633cce0f4ed58dcbc805cbf9ceb4aed0884f4b137e7362cf52f4d6f99cb"),
        # specify_cli.acceptance.post_consolidation::verify_deferred_invariants
        SymbolKey("verify_deferred_invariants", "e1c30bf407aa9a48fe5dfe0870f00f47cb0fb61367f2ad8f292f608ca2661c9d"),
        # specify_cli.cli.commands.archive::create
        SymbolKey("create", "758e16e495dc35a5a9338583a8a906a46d7e6b9ffcddc04b9d0b49f7f39227ba"),
        # specify_cli.cli.commands.archive::list_archives
        SymbolKey("list_archives", "1d7216238f988bfdd9f3a29fd315d89a48d0092b8b22c9ebdaf5c23c2308a886"),
    }
)


# Aggregate. The gate consults this; the per-category frozensets are
# the surface introspected by the ratchet-baseline meta-test
# (``tests/architectural/test_ratchet_baselines.py``). Entries are
# ``SymbolKey`` objects (relocation-hardened-dead-code-scanners-01KX958P
# WP02 -- FR-007), not qualified ``module::Name`` strings.
_SYMBOL_ALLOWLIST: frozenset[SymbolKey] = (
    _CATEGORY_A_SLICE_F_DEFERRED
    | _CATEGORY_B_GRANDFATHERED_LEGACY
    | _CATEGORY_B_T001_UNBLINDED
    | _CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE
    | _CATEGORY_C_WP_IN_FLIGHT_WORKFLOW_REGISTRY
    | _CATEGORY_C_CHARTER_SPLIT_LEGACY_PATCH_SURFACE
    | _CATEGORY_C_WP_IN_FLIGHT_COORDINATION_BRANCH
    | _CATEGORY_C_WP_IN_FLIGHT_TOPOLOGY_AUTHORITY
    | _CATEGORY_C_WP_IN_FLIGHT_UNIFIED_MISSION_STEP
    | _CATEGORY_C_WP_IN_FLIGHT_CHARTER_ACTIVATION
    | _CATEGORY_C_ORG_DOCTRINE_CLOSEOUT
    | _CATEGORY_C_UPSTREAM_SESSION_PRESENCE
    | _CATEGORY_C_QUALITY_DEBT_1928
    | _CATEGORY_C_BRANCH_NAMING_FAILOVER_SEAM
    | _CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT
    | _CATEGORY_C_MERGE_DECOMP_SHIM_REEXPORT_2057
    | _CATEGORY_C_EVENT_SYNC_RETENTION_DELIVERY
    | _CATEGORY_C_SYNC_RESET_RESULT_ENTRIES
    | _CATEGORY_C_RUNTIME_BRIDGE_DEGOD_COMPAT_SURFACE
    | _CATEGORY_C_MISSION_TYPE_DRG_EDGES_FACADE_REEXPORT
    | _CATEGORY_C_URN_RESOLUTION_LANE
    | _CATEGORY_C_WP_IN_FLIGHT_CHARTER_YAML_IO_WRITE_HELPER
    | _CATEGORY_C_SCOPE_SOURCE_FACTORY_CONSTRUCTED
    | _CATEGORY_C_LIFECYCLE_GATE_EXECUTION_CONTEXT_2841
)


def _iter_src_python_files() -> list[Path]:
    """Yield every ``*.py`` file under ``src/`` (sorted, deterministic)."""
    return sorted(p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _module_dotted(path: Path) -> str:
    """Return the dotted module name for *path* relative to ``src/``.

    ``src/charter/mission_type_profiles.py`` -> ``charter.mission_type_profiles``.
    For ``__init__.py`` the package itself is returned (``charter``).
    """
    rel = path.relative_to(_SRC_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_of(path: Path) -> str:
    """Return the dotted package containing *path* (for relative imports).

    Mirrors the helper in ``test_no_dead_modules`` so resolution is
    identical.
    """
    rel = path.relative_to(_SRC_ROOT).with_suffix("")
    parts = list(rel.parts)
    return ".".join(parts[:-1])


def _extract_str_consts_from_body(tree: ast.Module) -> dict[str, str]:
    """Extract top-level ``NAME = "string"`` constants from a module body.

    Only top-level body nodes are inspected (not nested scopes) to avoid
    false matches from deeply nested string literals.

    Used by ``_build_alias_map_and_consts`` as a separate helper to keep
    ``_build_alias_map_and_consts`` within the McCabe complexity ceiling.
    """
    str_consts: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        str_consts[tgt.id] = node.value.value
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and isinstance(node.target, ast.Name)
        ):
            str_consts[node.target.id] = node.value.value
    return str_consts


def _build_alias_map_and_consts(
    tree: ast.Module,
    containing_pkg: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build per-file import alias map and top-level string constants.

    Returns ``(alias_map, str_consts)`` where:

    * ``alias_map`` maps a local Python name to the dotted module it
      resolves to.  Only explicit ``asname`` bindings are captured:

      - ``import a.b.c as x``  →  ``{"x": "a.b.c"}``
      - ``from X import Y as Z``  →  ``{"Z": "X.Y"}`` (absolute X)

      Plain ``import a.b.c`` (no alias) is skipped: the gate only needs
      to trace ``x.attr``-style attribute accesses where the module is
      bound to a single local name.

    * ``str_consts`` maps top-level ``NAME = "string"`` (or ``AnnAssign``)
      to the string value.  Used by ``_record_facade_edges`` to resolve
      symbolic module-path variables like ``_EVENTS_MODULE = ".events"``.
    """
    alias_map: dict[str, str] = {}
    # Walk ALL nodes for import aliases: late/local imports (inside functions
    # or try-blocks) are common in spec-kitty for cycle-safety, and the
    # module-attr detector must see them.  String-constant resolution is
    # limited to top-level body (see ``_extract_str_consts_from_body``).
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    alias_map[alias.asname] = alias.name
                elif "." not in alias.name:
                    # ``import flat_module`` — local name IS the module name.
                    # Dotted imports (``import a.b.c``) are skipped: the local
                    # binding is just ``a``, which would mismatch the full path.
                    alias_map[alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            target = _resolve_import_from(node, containing_pkg)
            for alias in node.names:
                if alias.name != "*" and alias.asname:
                    alias_map[alias.asname] = f"{target}.{alias.name}"
    return alias_map, _extract_str_consts_from_body(tree)


def _record_module_attr_edges(
    tree: ast.Module,
    alias_map: dict[str, str],
    per_symbol: dict[str, set[str]],
    known_modules: frozenset[str],
) -> None:
    """Record caller-edges from ``alias.attr`` attribute patterns (detector a).

    For every ``<alias>.<name>`` node where ``<alias>`` resolves to a
    *real module* (a key in ``known_modules``) via ``alias_map``, records
    ``per_symbol[resolved_module].add(name)``.

    This subsumes the previously-missing Typer ``app.command()`` and
    lifecycle-module attribute patterns (detector c in the research).

    The ``known_modules`` guard is load-bearing (T004 / no-false-negative):
    ``from M import SomeClass as C`` binds ``C`` to the *synthetic* path
    ``M.SomeClass`` (a symbol, not a module). A class-attribute access
    ``C.NAME`` must NOT record a module-edge on ``M`` — otherwise
    ``_submodule_index`` would index ``M.SomeClass`` under prefix ``M`` and
    rule 3 of ``_symbol_has_caller`` would falsely rescue a genuinely-dead
    ``M::NAME``, silently re-blinding the very gate this mission hardens.
    """
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in alias_map
        ):
            resolved = alias_map[node.value.id]
            if resolved in known_modules:
                per_symbol.setdefault(resolved, set()).add(node.attr)


def _record_getattr_str_edges(
    tree: ast.Module,
    alias_map: dict[str, str],
    per_symbol: dict[str, set[str]],
    known_modules: frozenset[str],
) -> None:
    """Record caller-edges from ``getattr(alias, 'name')`` patterns (detector d).

    For every ``getattr(<alias>, <str_literal>)`` call where ``<alias>``
    resolves to a *real module* (in ``known_modules``) via ``alias_map``,
    records ``per_symbol[resolved_module].add(str_literal)``. See
    ``_record_module_attr_edges`` for why the ``known_modules`` guard is
    required to avoid re-blinding the gate via a symbol-path collision.
    """
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
        ):
            continue
        obj, attr_arg = node.args[0], node.args[1]
        if not (isinstance(obj, ast.Name) and obj.id in alias_map):
            continue
        if not (isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str)):
            continue
        resolved = alias_map[obj.id]
        if resolved in known_modules:
            per_symbol.setdefault(resolved, set()).add(attr_arg.value)


def _find_facade_lazy_dict_name(tree: ast.Module) -> str | None:
    """Return the lazy-imports dict variable referenced in a ``__getattr__`` facade.

    Searches for ``def __getattr__(name): ... DICT[name] ...`` at module
    scope.  Returns the dict variable name, or ``None`` if not a facade.
    """
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name == "__getattr__"):
            continue
        if not node.args.args:
            continue
        arg_id = node.args.args[0].arg
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Subscript)
                and isinstance(child.value, ast.Name)
                and isinstance(child.slice, ast.Name)
                and child.slice.id == arg_id
            ):
                return child.value.id
    return None


def _resolve_relative_module(mod_path: str, containing_pkg: str) -> str:
    """Resolve a relative-or-absolute dotted module path to its absolute form.

    ``".clock"`` resolved from ``"specify_cli.sync"`` →
    ``"specify_cli.sync.clock"``.  Absolute paths are returned unchanged.
    """
    if not mod_path.startswith("."):
        return mod_path
    level = len(mod_path) - len(mod_path.lstrip("."))
    rel = mod_path.lstrip(".")
    pkg_parts = containing_pkg.split(".") if containing_pkg else []
    base_parts = pkg_parts[: len(pkg_parts) - (level - 1)] if level > 1 else list(pkg_parts)
    if rel:
        base_parts = base_parts + rel.split(".")
    return ".".join(base_parts)


def _record_facade_edges(
    tree: ast.Module,
    containing_pkg: str,
    str_consts: dict[str, str],
    per_symbol: dict[str, set[str]],
    known_modules: frozenset[str],
) -> None:
    """Record caller-edges from a ``__getattr__``-style lazy-import facade (detector b).

    Detects the pattern::

        _LAZY_IMPORTS = {
            "Foo": (".bar", "Foo"),           # literal relative module
            "Baz": (_EVENTS_MODULE, "Baz"),   # name resolved via str_consts
        }
        def __getattr__(name):
            module_path, attr = _LAZY_IMPORTS[name]
            ...

    For each resolvable dict entry, records
    ``per_symbol[resolved_submodule].add(attr_name)``.  The ``_LAZY_IMPORTS``
    dict may be typed (``ast.AnnAssign``) or untyped (``ast.Assign``).
    """
    dict_name = _find_facade_lazy_dict_name(tree)
    if dict_name is None:
        return
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
            value_node: ast.expr | None = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value_node = node.value
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == dict_name for t in targets):
            continue
        if not isinstance(value_node, ast.Dict):
            continue
        for val in value_node.values:
            if not isinstance(val, (ast.Tuple, ast.List)) or len(val.elts) != 2:
                continue
            mod_expr, attr_expr = val.elts
            if not (isinstance(attr_expr, ast.Constant) and isinstance(attr_expr.value, str)):
                continue
            attr_name: str = attr_expr.value
            mod_path: str | None = None
            if isinstance(mod_expr, ast.Constant) and isinstance(mod_expr.value, str):
                mod_path = mod_expr.value
            elif isinstance(mod_expr, ast.Name) and mod_expr.id in str_consts:
                mod_path = str_consts[mod_expr.id]
            if mod_path is None:
                continue
            resolved = _resolve_relative_module(mod_path, containing_pkg)
            if resolved in known_modules:
                per_symbol.setdefault(resolved, set()).add(attr_name)


def _walk_modules() -> tuple[
    dict[str, frozenset[str]],
    dict[Path, str],
    dict[Path, ast.Module],
    dict[str, CorpusModule],
]:
    """Walk src/, return (decls, path_to_dotted, path_to_tree, corpus).

    * ``decls`` maps module dotted name to the static ``__all__`` set.
    * ``path_to_dotted`` maps each ``*.py`` path to its dotted name.
    * ``path_to_tree`` caches parsed ASTs so the import walk does not
      re-read every file.
    * ``corpus`` maps dotted module name -> :class:`CorpusModule`
      (tree, source, containing_pkg) -- the source-bearing inversion T008
      (relocation-hardened-dead-code-scanners-01KX958P WP02) requires so
      :func:`tests.architectural._symbol_key.resolve_symbol_key` can hash a
      symbol's definition span: ``code_tokens_by_line`` needs the source
      STRING, not just the parsed tree. Not in the C-005 byte-frozen set --
      safe to extend.
    """
    decls: dict[str, frozenset[str]] = {}
    path_to_dotted: dict[Path, str] = {}
    path_to_tree: dict[Path, ast.Module] = {}
    corpus: dict[str, CorpusModule] = {}
    for path in _iter_src_python_files():
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:  # pragma: no cover - defensive
            continue
        dotted = _module_dotted(path)
        path_to_dotted[path] = dotted
        path_to_tree[path] = tree
        corpus[dotted] = CorpusModule(tree=tree, source=source, containing_pkg=_package_of(path))
        names = _extract_all_literal(tree)
        if names is not None:
            decls[dotted] = names
    return decls, path_to_dotted, path_to_tree, corpus


def _imports_by_target(
    path_to_dotted: dict[Path, str],
    path_to_tree: dict[Path, ast.Module],
) -> tuple[dict[str, set[str]], set[str]]:
    """Return (per-symbol imports, star-import targets).

    * ``per_symbol_imports`` maps target dotted module -> set of names
      that *some* ``src/`` file imports via ``from <target> import <name>``.
      Plain ``import X`` is intentionally NOT counted: it pins the
      module name itself, not any specific public name from ``__all__``
      (the module-level gate already covers module-level use).
    * ``star_targets`` is the set of modules wildcard-imported via
      ``from X import *`` somewhere in ``src/``. A wildcard import
      satisfies every name in the target's ``__all__``.

    Detector (e) -- first-party dynamic (call-bound) module access
    (:func:`_record_dynamic_call_accessor_edges`, IC-01 / FR-001 / FR-002 /
    #2559) is folded in here (WP05 / FR-002): the production
    offender/stale/dangling ratchet now sees ``factory().attr`` /
    ``bound = factory(); bound.attr`` dynamic-access edges, which is what
    lets the 4 ``runtime.next.runtime_bridge`` façade rows in
    ``_CATEGORY_C_RUNTIME_BRIDGE_DEGOD_COMPAT_SURFACE`` be recognised live
    WITHOUT a permanent allowlist entry (see the WP05 row removal + this
    wiring landing in the same commit, NFR-001 safety ordering).
    """
    per_symbol: dict[str, set[str]] = {}
    star_targets: set[str] = set()
    # The set of REAL src modules. Attribute/getattr/facade detectors only
    # record an edge when the alias resolves to a member of this set, so a
    # symbol-path collision (``from M import Cls as C; C.NAME``) cannot
    # re-blind the gate (T004 / no-false-negative). See
    # ``_record_module_attr_edges``.
    known_modules = frozenset(path_to_dotted.values())
    for path, tree in path_to_tree.items():
        containing = _package_of(path)
        alias_map, str_consts = _build_alias_map_and_consts(tree, containing)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                target = _resolve_import_from(node, containing)
                for alias in node.names:
                    if alias.name == "*":
                        star_targets.add(target)
                    else:
                        per_symbol.setdefault(target, set()).add(alias.name)
        _record_module_attr_edges(tree, alias_map, per_symbol, known_modules)
        _record_getattr_str_edges(tree, alias_map, per_symbol, known_modules)
        _record_facade_edges(tree, containing, str_consts, per_symbol, known_modules)
    _record_dynamic_call_accessor_edges(path_to_dotted, path_to_tree, per_symbol)
    return per_symbol, star_targets


def _record_dynamic_call_accessor_edges(
    path_to_dotted: dict[Path, str],
    path_to_tree: dict[Path, ast.Module],
    per_symbol: dict[str, set[str]],
) -> None:
    """Overlay detector (e) -- first-party dynamic (call-bound) module access
    (IC-01 / FR-001 / FR-002 / #2559) -- on top of an existing ``per_symbol``
    map.

    Folded into :func:`_imports_by_target` proper as of WP05 (FR-002): the
    4 ``runtime.next.runtime_bridge`` façade rows previously hand-carried in
    ``_CATEGORY_C_RUNTIME_BRIDGE_DEGOD_COMPAT_SURFACE`` are removed in the
    same commit that wires this call in, so the production
    offender/stale/dangling ratchet and the allowlist-row removal land
    atomically (NFR-001 safety ordering -- removing the rows without this
    wiring would red the offenders check; wiring this in without removing
    the rows would red the stale-allowlist check). Kept as a separate
    function (rather than inlined) because it is independently exercised by
    ``test_wp01_runtime_bridge_facade_symbols_recognised_live_without_allowlist``
    against the real live corpus.
    """
    known_modules = frozenset(path_to_dotted.values())
    for path, tree in path_to_tree.items():
        containing = _package_of(path)
        alias_map, str_consts = _build_alias_map_and_consts(tree, containing)
        factories = find_module_factory_functions(
            tree, alias_map, str_consts, containing, known_modules, _resolve_relative_module
        )
        if not factories:
            continue
        merged_alias_map = {**alias_map, **bind_call_accessor_aliases(tree, factories)}
        _record_module_attr_edges(tree, merged_alias_map, per_symbol, known_modules)
        record_call_chain_attr_edges(tree, factories, per_symbol)


def _symbol_has_caller(
    name: str,
    mod_dotted: str,
    per_symbol: dict[str, set[str]],
    submodule_prefixes: dict[str, list[str]],
) -> bool:
    """Return True iff *name* (declared in ``mod_dotted.__all__``) has a caller.

    A symbol is "called" if any ``from <X> import <name>`` site in ``src/``
    targets:

    * the declaring module itself (``X == mod_dotted``);
    * the declaring module's parent package (``X == parent(mod_dotted)``)
      -- the parent re-exports the name via its own ``__all__``;
    * any submodule of ``mod_dotted`` (``X.startswith(mod_dotted + ".")``)
      -- this covers package ``__init__.py`` re-exports: a name listed
      in ``charter.__all__`` and imported via ``charter.compiler``
      proves the symbol is live runtime code.

    The third rule is necessary because the WP08 anti-pattern we gate
    against is *symbol with zero callers anywhere*, not *symbol unused
    via this exact import path*. Re-export contracts are honoured by
    proof-of-life from any importer of the canonical implementation.
    """
    # Direct: from mod_dotted import name
    if name in per_symbol.get(mod_dotted, set()):
        return True
    # Re-export via parent package
    if "." in mod_dotted:
        parent = mod_dotted.rsplit(".", 1)[0]
        if name in per_symbol.get(parent, set()):
            return True
    # Re-export via any submodule (covers package __init__ re-exports
    # where the canonical home is a submodule that callers import from
    # directly).
    return any(name in per_symbol.get(sub, set()) for sub in submodule_prefixes.get(mod_dotted, ()))


def _submodule_index(per_symbol: dict[str, set[str]]) -> dict[str, list[str]]:
    """Build ``{prefix: [submodule, ...]}`` for fast submodule lookups.

    Used by ``_symbol_has_caller`` to honour re-export proof-of-life.
    """
    out: dict[str, list[str]] = {}
    for target in per_symbol:
        if "." not in target:
            continue
        parts = target.split(".")
        for i in range(1, len(parts)):
            prefix = ".".join(parts[:i])
            out.setdefault(prefix, []).append(target)
    return out


def _resolve_final_key(
    name: str,
    mod_dotted: str,
    module: CorpusModule | None,
    corpus: Mapping[str, CorpusModule],
    collision_index: Mapping[str, list[Location]],
) -> SymbolKey | None:
    """Resolve *name* (declared in ``mod_dotted``'s ``__all__``) to its FINAL
    (tier-assigned) :class:`SymbolKey` against the live corpus + collision
    index (relocation-hardened-dead-code-scanners-01KX958P WP02 T009/T012 --
    FR-005/FR-009).

    Returns ``None`` -- fail-closed (T006/FR-009) -- whenever the symbol is
    un-keyable OR its content key resolves to a live collision that
    ``module_path`` cannot disambiguate. A ``None`` result is NEVER treated
    as a silent exemption by callers; it always falls through to the
    caller-detection / offender path ([[no_legacy_resolver_paths]]).
    """
    if module is None:
        return None
    key = resolve_symbol_key(name, mod_dotted, module, corpus=corpus)
    return key_tier(key, mod_dotted, collision_index)


def _is_registered_migration_class(mod_dotted: str, name: str, tree: ast.Module) -> bool:
    """T013 auto-exempt: a class decorated with ``@MigrationRegistry.register``.

    Migration classes are loaded via runtime discovery (``MigrationRegistry``
    auto-discovery over ``upgrade/migrations/m_*.py``), never via a direct
    ``from module import Name`` -- a genuinely-wired migration class has zero
    direct-import callers BY DESIGN, not because it is dead. Scoped to the
    CLASS only (FR-010 / DoD e): a dead helper or constant elsewhere in the
    same ``m_*.py`` file is NOT covered by this check and stays caught.
    """
    if not mod_dotted.startswith("specify_cli.upgrade.migrations."):
        return False
    for node in tree.body:
        if not (isinstance(node, ast.ClassDef) and node.name == name):
            continue
        for dec in node.decorator_list:
            if isinstance(dec, ast.Attribute) and dec.attr == "register" and isinstance(dec.value, ast.Name) and dec.value.id == "MigrationRegistry":
                return True
    return False


def _is_typer_subapp_definition(name: str, tree: ast.Module) -> bool:
    """T013 auto-exempt: a module-level ``NAME = typer.Typer(...)`` definition.

    A Typer sub-app is normally consumed by its parent via
    ``parent_app.add_typer(mod.NAME)`` -- a module-attribute CALL pattern
    already rescued by detector (a) wherever a caller is present. This
    structural, definition-shape check covers the residual case where no
    detector (a) caller has (yet) been recorded.
    """
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            continue
        value = node.value
        return (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "Typer"
            and isinstance(value.func.value, ast.Name)
            and value.func.value.id == "typer"
        )
    return False


def _reexport_origin(tree: ast.Module, containing_pkg: str, name: str) -> tuple[str, str] | None:
    """Return ``(origin_module, origin_name)`` for a single-alias ``ImportFrom``
    binding *name*, or ``None`` if *name* is not a simple re-export.

    Used only by :func:`_is_reexport_shim_symbol` (T013) to trace a re-export
    to its origin so the origin's OWN caller graph can be consulted.
    """
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        target = _resolve_import_from(node, containing_pkg)
        for alias in node.names:
            if alias.name == "*":
                continue
            bound = alias.asname or alias.name
            if bound == name:
                return target, alias.name
    return None


def _is_reexport_shim_symbol(
    mod_dotted: str,
    name: str,
    module: CorpusModule,
    final_key: SymbolKey | None,
    per_symbol: dict[str, set[str]],
    submodule_index: dict[str, list[str]],
) -> bool:
    """T013 auto-exempt: a pure re-export whose UNDERLYING definition has a
    live caller elsewhere (just not via THIS shim's own import path).

    Requires ALL of:

    1. ``final_key`` is a plain CONTENT-tier key (``module_path is None``).
       A collision bare_name (escalated tier, or fail-closed ``None``) is
       NEVER auto-exempt -- it MUST be hand-curated so the FR-005 live
       classifier's escalate-or-fail-close path (T012) stays the only route
       to exempting a same-name collision. This is load-bearing: without
       it, a future GateDecision-collapse-style rogue same-name sibling
       could be silently swallowed by this structural check instead of
       being caught by the escalation logic (DoD i).
    2. ``name`` has no local definition in this module (it is imported, not
       defined -- ``definition_span`` returns ``None``).
    3. The single-alias ``ImportFrom`` resolves to an ORIGIN module/name
       that has a REAL caller elsewhere in the corpus (``_symbol_has_caller``
       on the origin, not this shim). This is what distinguishes "compat
       shim re-exporting something already proven live" from "genuinely
       dead symbol that also happens to be re-exported nowhere else" --
       the latter must stay caught (FR-013 (c)/(e)).
    """
    if final_key is None or final_key.module_path is not None:
        return False
    if definition_span(module.tree, name) is not None:
        return False
    origin = _reexport_origin(module.tree, module.containing_pkg, name)
    if origin is None:
        return False
    origin_module, origin_name = origin
    if origin_module == mod_dotted:
        return False
    return _symbol_has_caller(origin_name, origin_module, per_symbol, submodule_index)


def _is_auto_exempt(
    mod_dotted: str,
    name: str,
    module: CorpusModule | None,
    final_key: SymbolKey | None,
    per_symbol: dict[str, set[str]],
    submodule_index: dict[str, list[str]],
) -> bool:
    """T013 -- symbol-granular auto-derived exemptions (never per-module).

    Three structural categories (FR-010), checked in order: a registered
    ``@MigrationRegistry.register`` class, a Typer sub-app definition, or a
    re-export shim whose underlying symbol is proven live elsewhere. See
    ``test_auto_exempt_disjoint_from_hand_allowlist`` for the disjointness
    proof against ``_SYMBOL_ALLOWLIST`` (auto_exempt ∩ hand_allowlist = ∅).
    """
    if module is None:
        return False
    tree = module.tree
    if _is_registered_migration_class(mod_dotted, name, tree):
        return True
    if _is_typer_subapp_definition(name, tree):
        return True
    return _is_reexport_shim_symbol(mod_dotted, name, module, final_key, per_symbol, submodule_index)


def _compute_offenders(
    decls: dict[str, frozenset[str]],
    per_symbol: dict[str, set[str]],
    star_targets: set[str],
    allowlist: frozenset[SymbolKey],
    corpus: Mapping[str, CorpusModule],
    collision_index: Mapping[str, list[Location]],
) -> list[str]:
    """Return sorted ``module::Name`` offenders for the symbol-level gate.

    Extracted so the end-to-end "teeth" self-test
    (``test_gate_still_flags_a_truly_dead_symbol``) drives a constructed
    dead-symbol fixture through the *exact* aggregate path the real gate
    uses — proving the four additive caller-detectors did not turn the gate
    into a silent no-op (NFR-001 / gate-can't-self-validate).

    relocation-hardened-dead-code-scanners-01KX958P WP02 (T009/T012/T013):
    exemption is now checked THREE ways, in order -- (1) the symbol's LIVE
    tier-assigned ``SymbolKey`` (:func:`_resolve_final_key`, threading the
    FR-005 collision classifier so a bare_name resolving to >=2 live
    locations dynamically escalates or fail-closes, never silently staying
    single-tier -- this is what keeps the re-key from re-blinding T004) is a
    member of ``allowlist``; else (2) the symbol matches a T013 structural
    auto-exempt category (:func:`_is_auto_exempt`); else (3) the existing
    caller-detection path (unchanged).
    """
    submodule_index = _submodule_index(per_symbol)
    offenders: list[str] = []
    for mod_dotted, names in sorted(decls.items()):
        if mod_dotted in star_targets:
            # Star-imported elsewhere; ``__all__`` is consumed wholesale.
            continue
        module = corpus.get(mod_dotted)
        for name in sorted(names):
            qualified = f"{mod_dotted}::{name}"
            final_key = _resolve_final_key(name, mod_dotted, module, corpus, collision_index)
            if final_key is not None and final_key in allowlist:
                continue
            if _is_auto_exempt(mod_dotted, name, module, final_key, per_symbol, submodule_index):
                continue
            if _symbol_has_caller(name, mod_dotted, per_symbol, submodule_index):
                continue
            offenders.append(qualified)
    return offenders


def _compute_stale(
    decls: dict[str, frozenset[str]],
    star_targets: set[str],
    corpus: Mapping[str, CorpusModule],
    collision_index: Mapping[str, list[Location]],
    allowlist: frozenset[SymbolKey],
    per_symbol: dict[str, set[str]],
    submodule_index: dict[str, list[str]],
) -> list[str]:
    """Return sorted ``module::Name`` STALE allow-list hits -- ratchet direction 1
    (the pre-existing "gained a caller" shrink-only direction).

    Extracted (relocation-hardened-dead-code-scanners-01KX958P WP03/T015) so
    the bite battery can drive this SAME path -- never a standalone
    re-derivation (C-007) -- exactly like :func:`_compute_offenders`. An
    allow-listed symbol is stale when its LIVE tier-assigned key is STILL a
    member of ``allowlist`` (the entry has not itself moved or had its body
    edited -- see :func:`_compute_dangling` for that direction) but the
    symbol has GAINED a real caller: the exception no longer applies and the
    entry should be pruned. Body-independent: this fires identically for a
    content-tier or an escalated module_path-tier entry -- ``key_tier``
    already resolved the FINAL key before this function ever compares it
    against ``allowlist``.
    """
    stale: list[str] = []
    for mod_dotted, names in decls.items():
        if mod_dotted in star_targets:
            continue
        module = corpus.get(mod_dotted)
        for name in names:
            final_key = _resolve_final_key(name, mod_dotted, module, corpus, collision_index)
            if final_key is None or final_key not in allowlist:
                continue
            if _symbol_has_caller(name, mod_dotted, per_symbol, submodule_index):
                stale.append(f"{mod_dotted}::{name}")
    return stale


def _compute_dangling(
    allowlist: frozenset[SymbolKey],
    decls: dict[str, frozenset[str]],
    collision_index: Mapping[str, list[Location]],
    offenders: list[str],
) -> list[str]:
    """Third ratchet direction (relocation-hardened-dead-code-scanners-01KX958P
    WP03 T015 -- FR-008/D-4): flag allow-list entries whose key no longer
    resolves to ANY live ``__all__`` location. The pre-existing shrink-only
    ratchet (:func:`_compute_stale`) only fires on "gained a caller";
    relocation (or deletion) can silently ORPHAN an allow-list entry while
    the gate simultaneously false-reds at the symbol's new home under a
    different key -- with nothing pointing back at the stale entry. This is
    the missing third direction.

    Tier-specific (a module_path-tier dangling check is UNDEFINED for a
    location-free content-tier entry -- D-4, contracts/symbol-key-resolver.md):

    * **content-tier** entry (``module_path is None``): dangling iff no live
      location in ``collision_index`` shares ``(bare_name, body_hash)`` --
      checked against the SAME live :func:`classify_collisions` index the
      production gate builds once per run, never a standalone re-derivation.
    * **module_path-tier** entry: dangling iff the module at ``module_path``
      no longer declares ``bare_name`` in a LIVE ``__all__`` (``decls``).
      ``body_hash`` is irrelevant here -- the tier is already
      location-bearing (relocation tolerance was already forfeited for this
      entry when it escalated), so a body edit alone does not orphan it.

    Body-sensitivity ONE-signal reconciliation (T016 -- FR-008/FR-009): a
    body edit to a still-dead symbol changes its content-tier key. Taken
    alone, that satisfies "zero live locations" above (the OLD key no longer
    matches) AND the symbol's NEW key -- being un-allowlisted and still
    caller-less -- is independently caught by :func:`_compute_offenders` as
    a fresh offender in the SAME gate run. Reporting both would be an
    ambiguous offender+prune double-flag for one root cause, so: a
    content-tier entry is suppressed from ``dangling`` whenever ``offenders``
    (the SAME run's production offender list, passed in -- never
    re-derived) already names its ``bare_name`` anywhere. The
    offender-refresh signal wins and is the ONLY signal; the operator's fix
    (refresh the allowlist entry to the symbol's new body_hash) is identical
    either way.
    """
    offender_bare_names = {qualified.rpartition("::")[2] for qualified in offenders}
    dangling: list[str] = []
    for entry in sorted(allowlist, key=lambda k: (k.bare_name, k.module_path or "", k.body_hash)):
        if entry.is_content_tier:
            locations = collision_index.get(entry.bare_name, [])
            if any(loc.body_hash == entry.body_hash for loc in locations):
                continue  # still resolves live -- not dangling
            if entry.bare_name in offender_bare_names:
                continue  # offender-refresh already signals this root cause -- no double-flag
            dangling.append(f"{entry.bare_name} (content-tier body_hash={entry.body_hash[:12]})")
        else:
            module_path = entry.module_path
            assert module_path is not None  # not content-tier -- SymbolKey guarantees this
            live_names = decls.get(module_path, frozenset())
            if entry.bare_name in live_names:
                continue  # the module still declares this bare_name -- not dangling
            dangling.append(f"{entry.bare_name} (module_path-tier module_path={module_path})")
    return dangling


def test_no_public_symbol_in_all_is_unimported() -> None:
    """Every name in every ``__all__`` must have at least one caller in src/.

    Failure means a public symbol is declared (``__all__``) but no
    other ``src/`` file imports it. That's the WP08 cycle-1
    "library written but never wired" failure mode at symbol level.
    """
    decls, path_to_dotted, path_to_tree, corpus = _walk_modules()
    per_symbol, star_targets = _imports_by_target(path_to_dotted, path_to_tree)
    submodule_index = _submodule_index(per_symbol)
    collision_index = classify_collisions(corpus)

    offenders = _compute_offenders(decls, per_symbol, star_targets, _SYMBOL_ALLOWLIST, corpus, collision_index)

    # Ratchet direction 1 (pre-existing): the symbol gained a caller --
    # remove it from the allowlist (good news).
    stale = _compute_stale(decls, star_targets, corpus, collision_index, _SYMBOL_ALLOWLIST, per_symbol, submodule_index)

    # Ratchet direction 3 (relocation-hardened-dead-code-scanners-01KX958P
    # WP03/T015/FR-008): the allow-list entry's key no longer resolves to
    # ANY live `__all__` location -- relocation (or deletion) silently
    # orphaned it. Reconciled with body-sensitivity (T016) so a dead-symbol
    # body edit surfaces as exactly ONE signal via `offenders` above, never
    # an ambiguous offender+prune double-flag -- see `_compute_dangling`.
    dangling = _compute_dangling(_SYMBOL_ALLOWLIST, decls, collision_index, offenders)

    messages: list[str] = []
    if offenders:
        bullets = "\n  - ".join(sorted(offenders))
        messages.append(
            "Symbol-level dead-code gate FAILED. The following public "
            "symbols are declared in __all__ but no other src/ file "
            "imports them:\n  - " + bullets + "\n\nFix options (in order of preference):\n"
            "  1) Wire the symbol from a runtime caller.\n"
            "  2) Remove the symbol from __all__ (it stays in the "
            "module as an unexported internal).\n"
            "  3) Delete the symbol entirely if it is truly dead.\n"
            "  4) Add a `SymbolKey(...)` entry (resolve it via "
            "`resolve_symbol_key`/`key_tier` in `_symbol_key.py`) to the "
            "appropriate category frozenset in `_SYMBOL_ALLOWLIST`, "
            "commented with the qualified `module::Name`, plus a rationale "
            "and a follow-up tracker ticket (FR-303).\n"
        )
    if stale:
        bullets = "\n  - ".join(sorted(stale))
        messages.append(
            "Stale `_SYMBOL_ALLOWLIST` entries detected. The following symbols now have at least one caller and must be removed from the allowlist:\n  - " + bullets
        )
    if dangling:
        bullets = "\n  - ".join(sorted(dangling))
        messages.append(
            "Dangling `_SYMBOL_ALLOWLIST` entries detected (FR-008 -- third "
            "ratchet direction). The following allow-listed keys no longer "
            "resolve to ANY live `__all__` declaration -- relocation (or "
            "deletion, or a body edit) silently orphaned them:\n  - " + bullets + "\n\n"
            "If a symbol above also appears in the offenders list, this is "
            "the SAME root cause (refresh the entry's SymbolKey to match the "
            "symbol's current body_hash/location) -- do not add a second "
            "entry. If it does not, the entry is a genuine prune candidate: "
            "delete it from `_SYMBOL_ALLOWLIST`."
        )
    assert not messages, "\n\n".join(messages)


# ---------------------------------------------------------------------------
# T001 regression — _extract_all_literal parser bug fix
# ---------------------------------------------------------------------------


def test_extract_all_literal_skips_non_all_annassign() -> None:
    """A non-``__all__`` AnnAssign before ``__all__`` must not blind the parser.

    Regression for the T001 bug: a top-level ``MESSAGES: dict[...] = {...}``
    (ast.AnnAssign whose target is NOT ``__all__``) was falling through to
    ``if value is None: return frozenset()``, silently zeroing the module's
    ``__all__``.  After the fix, such nodes are skipped with ``continue``.
    """
    src = 'MESSAGES: dict[str, str] = {"x": "y"}\n__all__ = ["Foo", "Bar"]'
    tree = ast.parse(src)
    result = _extract_all_literal(tree)
    assert result == frozenset({"Foo", "Bar"}), f"Expected frozenset({{Foo, Bar}}), got {result!r}"


def test_extract_all_literal_typed_all_annassign() -> None:
    """A typed ``__all__: list[str] = [...]`` AnnAssign is parsed correctly."""
    src = '__all__: list[str] = ["Alpha", "Beta"]'
    tree = ast.parse(src)
    result = _extract_all_literal(tree)
    assert result == frozenset({"Alpha", "Beta"})


def test_extract_all_literal_bare_annassign_returns_frozenset_empty() -> None:
    """``__all__: list[str]`` with no value is treated as dynamic (frozenset())."""
    src = "__all__: list[str]"
    tree = ast.parse(src)
    result = _extract_all_literal(tree)
    assert result == frozenset()


# ---------------------------------------------------------------------------
# T004 no-false-negative guard — detectors must bind to RESOLVED module only
# ---------------------------------------------------------------------------


def test_no_false_negative_module_attr_detector() -> None:
    """Detector (a) must rescue the resolved module's symbol, not a coincidental one.

    This is the binding invariant from the WP01 spec: ``alias.Foo`` where
    ``alias`` resolves to ``other_pkg`` rescues **only** ``other_pkg::Foo``,
    NOT any different module that happens to declare a symbol named ``Foo``.
    """
    src = "import other_pkg as alias\nalias.Foo"
    tree = ast.parse(src)
    alias_map, _ = _build_alias_map_and_consts(tree, "")
    ps: dict[str, set[str]] = {}
    _record_module_attr_edges(tree, alias_map, ps, frozenset({"other_pkg"}))
    sub_idx = _submodule_index(ps)

    # The resolved module IS rescued.
    assert _symbol_has_caller("Foo", "other_pkg", ps, sub_idx), "other_pkg::Foo must be rescued by alias.Foo access"
    # A different module with the same symbol name is NOT rescued.
    assert not _symbol_has_caller("Foo", "declaring_module", ps, sub_idx), "declaring_module::Foo must NOT be rescued by alias.Foo where alias→other_pkg"


def test_no_false_negative_getattr_detector() -> None:
    """Detector (d) must rescue the resolved module's symbol only."""
    src = "import target_mod\ngetattr(target_mod, 'Bar')"
    tree = ast.parse(src)
    alias_map, _ = _build_alias_map_and_consts(tree, "")
    ps: dict[str, set[str]] = {}
    _record_getattr_str_edges(tree, alias_map, ps, frozenset({"target_mod"}))
    sub_idx = _submodule_index(ps)

    assert _symbol_has_caller("Bar", "target_mod", ps, sub_idx), "target_mod::Bar must be rescued by getattr(target_mod, 'Bar')"
    assert not _symbol_has_caller("Bar", "unrelated_mod", ps, sub_idx), "unrelated_mod::Bar must NOT be rescued"


def test_no_false_negative_facade_detector() -> None:
    """Detector (b) must rescue only the submodule the facade re-exports from."""
    src = (
        '_PREFIX = ".sub"\n'
        "_LAZY = {\n"
        '    "Cls": (_PREFIX, "Cls"),\n'
        '    "fn": (".other", "fn"),\n'
        "}\n"
        "def __getattr__(name):\n"
        "    mod_path, attr = _LAZY[name]\n"
        "    return attr\n"
    )
    tree = ast.parse(src)
    _, str_consts = _build_alias_map_and_consts(tree, "mypkg")
    ps: dict[str, set[str]] = {}
    _record_facade_edges(tree, "mypkg", str_consts, ps, frozenset({"mypkg.sub", "mypkg.other"}))
    sub_idx = _submodule_index(ps)

    # Cls is exported from mypkg.sub
    assert _symbol_has_caller("Cls", "mypkg.sub", ps, sub_idx), "mypkg.sub::Cls must be rescued by the facade"
    # fn is exported from mypkg.other
    assert _symbol_has_caller("fn", "mypkg.other", ps, sub_idx)
    # Neither rescues an unrelated module
    assert not _symbol_has_caller("Cls", "mypkg.unrelated", ps, sub_idx), "mypkg.unrelated::Cls must NOT be rescued"


def test_no_false_negative_aliased_symbol_import_does_not_reblind() -> None:
    """T004 regression: ``from M import Cls as C; C.NAME`` must NOT rescue ``M::NAME``.

    This is the re-blinding vector the ``known_modules`` guard closes. ``C``
    binds to the synthetic path ``M.SomeClass`` (a symbol, not a module);
    a class-attribute access ``C.NAME`` must not be mistaken for a
    module-attribute access on ``M``. ``M`` is a real module, but
    ``M.SomeClass`` is not — so no edge may be recorded, and a genuinely-dead
    ``M::NAME`` stays flagged.
    """
    src = "from M import SomeClass as C\nC.NAME"
    tree = ast.parse(src)
    alias_map, _ = _build_alias_map_and_consts(tree, "")
    # ``M`` is a real module; ``M.SomeClass`` (the alias target) is NOT.
    known_modules = frozenset({"M"})
    ps: dict[str, set[str]] = {}
    _record_module_attr_edges(tree, alias_map, ps, known_modules)
    sub_idx = _submodule_index(ps)

    assert not _symbol_has_caller("NAME", "M", ps, sub_idx), (
        "M::NAME must NOT be rescued by the class-attribute access C.NAME "
        "(C = SomeClass imported from M); recording that edge would re-blind "
        "the gate via _submodule_index rule 3."
    )
    # Sanity: without the guard the collision DOES rescue — proves the guard
    # is the load-bearing difference, not a vacuous assertion.
    ps_unguarded: dict[str, set[str]] = {}
    _record_module_attr_edges(tree, alias_map, ps_unguarded, frozenset({"M", "M.SomeClass"}))
    assert _symbol_has_caller("NAME", "M", ps_unguarded, _submodule_index(ps_unguarded)), (
        "control: with M.SomeClass treated as a module, the collision rescues M::NAME"
    )


def test_no_false_negative_call_accessor_detector_direct_chain() -> None:
    """Detector (e) -- dynamic-access→live, direct call-chain shape (IC-01/#2559).

    ``factory().attr`` -- a zero-arg module-scope function whose body
    resolves ``target_mod`` via ``importlib.import_module(...)``, called and
    immediately attribute-accessed with no intermediate local -- rescues
    ``target_mod::Live`` exactly as a plain ``alias.Live`` import-bound
    access would. Resolved generally (no name special-case for
    ``runtime_bridge`` anywhere in the resolver).
    """
    src = (
        "import importlib\n"
        "def _factory():\n"
        "    return importlib.import_module('target_mod')\n"
        "_factory().Live\n"
    )
    tree = ast.parse(src)
    alias_map, str_consts = _build_alias_map_and_consts(tree, "")
    known_modules = frozenset({"target_mod"})
    factories = find_module_factory_functions(
        tree, alias_map, str_consts, "", known_modules, _resolve_relative_module
    )
    ps: dict[str, set[str]] = {}
    record_call_chain_attr_edges(tree, factories, ps)
    sub_idx = _submodule_index(ps)

    assert _symbol_has_caller("Live", "target_mod", ps, sub_idx), (
        "target_mod::Live must be rescued by _factory().Live where _factory() "
        "dynamically resolves target_mod via importlib.import_module"
    )
    assert not _symbol_has_caller("Live", "unrelated_mod", ps, sub_idx), (
        "unrelated_mod::Live must NOT be rescued -- the resolver must not "
        "widen liveness to any attribute access (contract anti-goal)"
    )


def test_no_false_negative_call_accessor_detector_bound_local() -> None:
    """Detector (e) -- dynamic-access→live, the bound-local two-step shape
    actually used by the known ``_runtime_bridge_module()`` call sites in
    ``next_cmd.py`` (``bridge = _runtime_bridge_module(); bridge.attr``).
    """
    src = (
        "import importlib\n"
        "def _factory():\n"
        "    return importlib.import_module('target_mod')\n"
        "bridge = _factory()\n"
        "bridge.Live\n"
    )
    tree = ast.parse(src)
    alias_map, str_consts = _build_alias_map_and_consts(tree, "")
    known_modules = frozenset({"target_mod"})
    factories = find_module_factory_functions(
        tree, alias_map, str_consts, "", known_modules, _resolve_relative_module
    )
    merged_alias_map = {**alias_map, **bind_call_accessor_aliases(tree, factories)}
    ps: dict[str, set[str]] = {}
    _record_module_attr_edges(tree, merged_alias_map, ps, known_modules)
    sub_idx = _submodule_index(ps)

    assert _symbol_has_caller("Live", "target_mod", ps, sub_idx), (
        "target_mod::Live must be rescued by bridge.Live where bridge = "
        "_factory() and _factory() dynamically resolves target_mod via "
        "importlib.import_module"
    )
    assert not _symbol_has_caller("Live", "unrelated_mod", ps, sub_idx)


def test_no_false_negative_call_accessor_detector_unreferenced_stays_dead() -> None:
    """Negative direction (contract dead-code-dynamic-access.md): a symbol with
    no static import AND no first-party dynamic access must still be
    classified dead -- the new detector rescues only the SPECIFIC attribute
    actually accessed through the recognised factory, not every symbol that
    happens to live in the factory's resolved module.
    """
    src = (
        "import importlib\n"
        "def _factory():\n"
        "    return importlib.import_module('target_mod')\n"
        "bridge = _factory()\n"
        "bridge.Live\n"  # only ``Live`` is actually accessed
    )
    tree = ast.parse(src)
    alias_map, str_consts = _build_alias_map_and_consts(tree, "")
    known_modules = frozenset({"target_mod"})
    factories = find_module_factory_functions(
        tree, alias_map, str_consts, "", known_modules, _resolve_relative_module
    )
    merged_alias_map = {**alias_map, **bind_call_accessor_aliases(tree, factories)}
    ps: dict[str, set[str]] = {}
    _record_module_attr_edges(tree, merged_alias_map, ps, known_modules)
    record_call_chain_attr_edges(tree, factories, ps)
    sub_idx = _submodule_index(ps)

    assert _symbol_has_caller("Live", "target_mod", ps, sub_idx)
    assert not _symbol_has_caller("NeverAccessed", "target_mod", ps, sub_idx), (
        "target_mod::NeverAccessed must stay dead -- the gate must not go "
        "blind and rescue every symbol reachable from a recognised factory's "
        "module, only the ones actually attribute-accessed"
    )


def test_wp01_runtime_bridge_facade_symbols_recognised_live_without_allowlist() -> None:
    """IC-01/WP05 DoD (FR-001/FR-002): the 4 known ``runtime.next.runtime_bridge``
    façade symbols are recognised-live via their dynamic
    ``_runtime_bridge_module()`` accessor call sites in ``next_cmd.py`` --
    with NO permanent allowlist entry
    (``_CATEGORY_C_RUNTIME_BRIDGE_DEGOD_COMPAT_SURFACE`` no longer carries
    these 4 rows as of WP05). This test proves the gate's caller-detection
    sees them via the now-wired :func:`_imports_by_target` -- driven
    through the REAL live ``src/`` corpus, not a fixture.
    """
    decls, path_to_dotted, path_to_tree, _corpus = _walk_modules()
    per_symbol, _star_targets = _imports_by_target(path_to_dotted, path_to_tree)
    submodule_index = _submodule_index(per_symbol)

    mod_dotted = "runtime.next.runtime_bridge"
    for name in (
        "get_or_start_run",
        "query_current_state",
        "answer_decision_via_runtime",
        "QueryModeValidationError",
    ):
        assert name in decls.get(mod_dotted, frozenset()), (
            f"{mod_dotted}::{name} must still be declared in __all__ -- this "
            "test targets the real live corpus, not a stale fixture"
        )
        assert _symbol_has_caller(name, mod_dotted, per_symbol, submodule_index), (
            f"{mod_dotted}::{name} must be recognised-live via the "
            "_runtime_bridge_module() dynamic accessor WITHOUT its allowlist "
            "row (IC-01 / FR-001 / FR-002)"
        )


def test_gate_still_flags_a_truly_dead_symbol() -> None:
    """End-to-end teeth (NFR-001 / DoD a): the hardened gate is not a silent no-op.

    Four additive caller-detectors can only ADD rescues, so a self-test must
    prove the aggregate path still FLAGS a symbol that nothing imports — and
    still PASSES one that has a real caller. Driven through the same
    ``_compute_offenders`` path the production gate uses.

    relocation-hardened-dead-code-scanners-01KX958P WP02: the allowlist
    control case now drives a REAL ``resolve_symbol_key``/``key_tier``
    resolution (not a fabricated string) since allowlist membership is
    SymbolKey-based (T009/T012), per C-007 (no standalone-key self-validation).
    """
    decls = {"synthetic.deadmod": frozenset({"NeverImported"})}
    empty_corpus: dict[str, CorpusModule] = {}
    empty_index: dict[str, list[Location]] = {}

    # No caller of any kind → still flagged. The corpus need not resolve a
    # key here: an absent/un-keyable symbol fails closed and falls through
    # to the caller check, which also fails.
    flagged = _compute_offenders(decls, {}, set(), frozenset(), empty_corpus, empty_index)
    assert flagged == ["synthetic.deadmod::NeverImported"], f"gate must flag a symbol with zero callers; got {flagged!r}"

    # A real direct importer → not flagged (control).
    with_caller = {"synthetic.deadmod": {"NeverImported"}}
    assert _compute_offenders(decls, with_caller, set(), frozenset(), empty_corpus, empty_index) == [], "a symbol with a real caller must NOT be flagged"

    # Allowlisted → not flagged (control for the exception path), driven
    # through the REAL resolver: build a one-module synthetic corpus, resolve
    # its SymbolKey, then allowlist that resolved key.
    source = "NeverImported = object()\n"
    tree = ast.parse(source)
    module = CorpusModule(tree=tree, source=source, containing_pkg="synthetic")
    corpus = {"synthetic.deadmod": module}
    collision_index = classify_collisions(corpus)
    key = resolve_symbol_key("NeverImported", "synthetic.deadmod", module, corpus=corpus)
    final_key = key_tier(key, "synthetic.deadmod", collision_index)
    assert final_key is not None
    allow = frozenset({final_key})
    assert _compute_offenders(decls, {}, set(), allow, corpus, collision_index) == []


# ---------------------------------------------------------------------------
# T013 — symbol-granular auto-exempt categories + disjointness meta-test
# ---------------------------------------------------------------------------


def test_auto_exempt_disjoint_from_hand_allowlist() -> None:
    """T013 disjointness meta-test: auto_exempt ∩ hand_allowlist = ∅.

    An entry must not be BOTH auto-derived (registered migration class /
    Typer sub-app definition / re-export shim) AND hand-curated in
    ``_SYMBOL_ALLOWLIST`` -- that would be redundant bookkeeping and risks
    the two silently falling out of sync. Walks the LIVE ``src/`` corpus
    (not a fixture) so this is a real, current-state proof.
    """
    decls, path_to_dotted, path_to_tree, corpus = _walk_modules()
    per_symbol, star_targets = _imports_by_target(path_to_dotted, path_to_tree)
    submodule_index = _submodule_index(per_symbol)
    collision_index = classify_collisions(corpus)

    overlaps: list[str] = []
    for mod_dotted, names in decls.items():
        if mod_dotted in star_targets:
            continue
        module = corpus.get(mod_dotted)
        for name in names:
            final_key = _resolve_final_key(name, mod_dotted, module, corpus, collision_index)
            if not _is_auto_exempt(mod_dotted, name, module, final_key, per_symbol, submodule_index):
                continue
            if final_key is not None and final_key in _SYMBOL_ALLOWLIST:
                overlaps.append(f"{mod_dotted}::{name}")
    assert not overlaps, f"auto-exempt/hand-allowlist overlap violates T013 disjointness (auto_exempt ∩ hand_allowlist must be ∅): {sorted(overlaps)}"


# ---------------------------------------------------------------------------
# T014 — bite battery (a,c,e,f,h,i,k), through the production path (C-007)
# ---------------------------------------------------------------------------


def test_bite_c_same_name_fan_out_dead_sibling_still_caught() -> None:
    """DoD (c) -- a same-name fan-out dead sibling is still caught (T004).

    Two modules independently declare a bare_name ``Shared`` with DIFFERENT
    bodies (a genuine fan-out, not a byte-identical collision). One has a
    real caller; the sibling does not and must stay caught, distinguished by
    its own qualified name.
    """
    mod_a_src = "Shared = 1\n"
    mod_b_src = "Shared = 2\n"
    corpus = {
        "synthetic.mod_a": CorpusModule(ast.parse(mod_a_src), mod_a_src, "synthetic"),
        "synthetic.mod_b": CorpusModule(ast.parse(mod_b_src), mod_b_src, "synthetic"),
    }
    collision_index = classify_collisions(corpus)
    decls = {
        "synthetic.mod_a": frozenset({"Shared"}),
        "synthetic.mod_b": frozenset({"Shared"}),
    }
    per_symbol = {"synthetic.mod_a": {"Shared"}}  # mod_a::Shared has a real caller
    offenders = _compute_offenders(decls, per_symbol, set(), frozenset(), corpus, collision_index)
    assert offenders == ["synthetic.mod_b::Shared"], "the dead fan-out sibling must be caught, the live one must not"


def test_bite_e_dead_migration_helper_still_caught() -> None:
    """DoD (e) -- a dead helper in a migration file is still caught despite FR-010.

    T013's ``_is_registered_migration_class`` auto-exempts ONLY the
    ``@MigrationRegistry.register``-decorated class, never anything else in
    the same ``m_*.py`` file.
    """
    source = (
        "class MigrationRegistry:\n"
        "    @classmethod\n"
        "    def register(cls, k):\n"
        "        return k\n"
        "\n"
        "\n"
        "@MigrationRegistry.register\n"
        "class SyntheticMigration:\n"
        "    pass\n"
        "\n"
        "\n"
        "DEAD_HELPER = 1\n"
    )
    tree = ast.parse(source)
    mod_dotted = "specify_cli.upgrade.migrations.m_9_9_9_synthetic"
    corpus = {mod_dotted: CorpusModule(tree, source, "specify_cli.upgrade.migrations")}
    collision_index = classify_collisions(corpus)
    decls = {mod_dotted: frozenset({"SyntheticMigration", "DEAD_HELPER"})}
    offenders = _compute_offenders(decls, {}, set(), frozenset(), corpus, collision_index)
    assert offenders == [f"{mod_dotted}::DEAD_HELPER"], (
        "the registered migration class must be auto-exempt but the dead helper constant beside it must still be caught"
    )


def test_bite_f_undecidable_key_fails_closed() -> None:
    """DoD (f) -- an undecidable-key symbol (None-key) is fail-closed.

    ``Ghost`` is declared in ``__all__`` but has no ClassDef/FunctionDef/
    Assign/AnnAssign/ImportFrom/facade shape at all -- the resolver must
    return ``None``, and the gate must still flag it (never silently exempt
    an un-keyable symbol).
    """
    source = "__all__ = ['Ghost']\n"
    tree = ast.parse(source)
    module = CorpusModule(tree=tree, source=source, containing_pkg="synthetic")
    corpus = {"synthetic.ghostmod": module}
    collision_index = classify_collisions(corpus)
    decls = {"synthetic.ghostmod": frozenset({"Ghost"})}

    assert resolve_symbol_key("Ghost", "synthetic.ghostmod", module, corpus=corpus) is None, "sanity: this shape must be genuinely undecidable"
    offenders = _compute_offenders(decls, {}, set(), frozenset(), corpus, collision_index)
    assert offenders == ["synthetic.ghostmod::Ghost"], "an un-keyable symbol must fail closed (flagged), never silently exempted"


def test_bite_i_live_collision_escalation_regression_guard() -> None:
    """DoD (i) -- Live-collision escalation (Defect-1 regression guard).

    Simulates a NEW byte-identical same-name pair (the future
    ``GateDecision``-collapse vector): two independent modules each declare
    a class ``GateDecision`` with the IDENTICAL body. One is sanctioned
    (allow-listed via its LIVE tier-assigned key); the other is a rogue,
    unsanctioned sibling with no real caller.

    If the content/forfeit split were frozen at authoring time (the bug this
    mission fixes), the rogue sibling would share the sanctioned entry's
    content-tier key and be silently exempted too. The LIVE classifier must
    instead escalate BOTH occurrences to the module_path tier, so only the
    module_path-qualified sanctioned key is a member of the allowlist and
    the rogue sibling is still caught -- proving the split is
    runtime-recomputed, not frozen.
    """
    body = "class GateDecision:\n    pass\n"
    sanctioned_src = body + "\n\n__all__ = ['GateDecision']\n"
    rogue_src = body + "\n\n__all__ = ['GateDecision']\n"
    corpus = {
        "synthetic.sanctioned": CorpusModule(ast.parse(sanctioned_src), sanctioned_src, "synthetic"),
        "synthetic.rogue": CorpusModule(ast.parse(rogue_src), rogue_src, "synthetic"),
    }
    collision_index = classify_collisions(corpus)
    # Sanity: the live classifier actually sees the collision.
    assert len(collision_index.get("GateDecision", [])) == 2

    sanctioned_content_key = resolve_symbol_key("GateDecision", "synthetic.sanctioned", corpus["synthetic.sanctioned"], corpus=corpus)
    sanctioned_final = key_tier(sanctioned_content_key, "synthetic.sanctioned", collision_index)
    assert sanctioned_final is not None
    assert sanctioned_final.module_path == "synthetic.sanctioned", (
        "a live collision bare_name must escalate to the module_path tier, not stay a bare content-tier key"
    )
    allow = frozenset({sanctioned_final})

    decls = {
        "synthetic.sanctioned": frozenset({"GateDecision"}),
        "synthetic.rogue": frozenset({"GateDecision"}),
    }
    offenders = _compute_offenders(decls, {}, set(), allow, corpus, collision_index)
    assert offenders == ["synthetic.rogue::GateDecision"], (
        "the unsanctioned rogue sibling must still be caught -- live escalation, not a frozen content-tier split, is what prevents T004 re-blinding"
    )


def test_bite_k_full_keyability_hand_and_auto_exempt() -> None:
    """DoD (k) -- 0 un-keyable entries.

    Every hand-allowlisted ``SymbolKey`` is well-formed, and every symbol
    the T013 structural auto-exempt mechanism claims to cover resolves to a
    real ``SymbolKey`` against the live corpus (never a claimed-but-unproven
    exemption).
    """
    for key in _SYMBOL_ALLOWLIST:
        assert key.bare_name and key.body_hash, f"malformed hand-allowlist key: {key!r}"

    decls, path_to_dotted, path_to_tree, corpus = _walk_modules()
    per_symbol, star_targets = _imports_by_target(path_to_dotted, path_to_tree)
    submodule_index = _submodule_index(per_symbol)
    collision_index = classify_collisions(corpus)

    unkeyable_auto_exempt: list[str] = []
    for mod_dotted, names in decls.items():
        if mod_dotted in star_targets:
            continue
        module = corpus.get(mod_dotted)
        for name in names:
            final_key = _resolve_final_key(name, mod_dotted, module, corpus, collision_index)
            if not _is_auto_exempt(mod_dotted, name, module, final_key, per_symbol, submodule_index):
                continue
            if module is None or resolve_symbol_key(name, mod_dotted, module, corpus=corpus) is None:
                unkeyable_auto_exempt.append(f"{mod_dotted}::{name}")
    assert not unkeyable_auto_exempt, f"auto-exempt mechanism claims coverage for an un-keyable symbol (fail-closed violation): {unkeyable_auto_exempt}"


# ---------------------------------------------------------------------------
# T015/T016 (relocation-hardened-dead-code-scanners-01KX958P WP03) -- third
# dangling-entry ratchet, tier-specific + body-sensitivity one-signal
# reconciliation -- see `_compute_dangling` above.
# T017/T018 -- bite battery (b,d,g) + the gate-side DoD (j) 0-false-red
# proof, all through the production `_compute_offenders`/`_compute_stale`/
# `_compute_dangling` path (C-007), never a standalone re-derivation.
# ---------------------------------------------------------------------------


def test_bite_b_relocated_but_wired_symbol_stays_green() -> None:
    """DoD (b) -- a relocated-but-WIRED content-tier symbol stays green.

    ``Helper`` used to live (and be allow-listed as dead) at some prior
    location; the SAME body now lives at ``synthetic.new_home`` and has
    gained a real caller. Because the content-tier key is location-free
    ``(bare_name, body_hash)``, relocation does not disturb it: the symbol
    is (1) NOT an offender (it has a real caller) -- true regardless of
    relocation, (2) correctly flagged STALE by the pre-existing ratchet
    direction (the exception no longer applies, prune it), and (3)
    crucially NOT flagged DANGLING by the NEW T015 detector -- the key
    still resolves to exactly one live location, just at the new module
    path. Carve-out (spec.md DoD b, documented): this "stays green" proof
    covers the simple/content-tier subset only; unconditional relocation
    tolerance for the re-export/module_path-tier subset is explicitly out
    of scope (it would re-blind T004 -- spec.md Out of Scope).
    """
    source = "def Helper():\n    return 1\n\n\n__all__ = ['Helper']\n"
    tree = ast.parse(source)
    module = CorpusModule(tree=tree, source=source, containing_pkg="synthetic")
    corpus = {"synthetic.new_home": module}
    collision_index = classify_collisions(corpus)
    key = resolve_symbol_key("Helper", "synthetic.new_home", module, corpus=corpus)
    final_key = key_tier(key, "synthetic.new_home", collision_index)
    assert final_key is not None
    assert final_key.is_content_tier, "sanity: a non-colliding bare_name must stay content-tier"
    allow = frozenset({final_key})

    decls = {"synthetic.new_home": frozenset({"Helper"})}
    per_symbol = {"synthetic.new_home": {"Helper"}}  # relocated AND wired

    offenders = _compute_offenders(decls, per_symbol, set(), allow, corpus, collision_index)
    assert offenders == [], "a wired symbol must never be flagged, relocated or not"

    submodule_index = _submodule_index(per_symbol)
    stale = _compute_stale(decls, set(), corpus, collision_index, allow, per_symbol, submodule_index)
    assert stale == ["synthetic.new_home::Helper"], "the allow-list entry should be flagged for pruning now that the symbol is wired"

    dangling = _compute_dangling(allow, decls, collision_index, offenders)
    assert dangling == [], "relocation-tolerant content-tier key must still resolve live at the new location -- must NOT also read as dangling"


def test_bite_d_wired_allowlisted_symbol_reds_stale_ratchet() -> None:
    """DoD (d) -- a wired allow-listed symbol reds the stale ratchet
    (body-independent): staleness fires off "key still resolves live AND
    now has a caller" regardless of whether the entry is content-tier or an
    escalated module_path-tier entry (whose identity is location-bearing,
    not body-bearing). Drives BOTH tiers through the SAME `_compute_stale`
    production path.
    """
    # -- content tier --
    source = "Const = 1\n"
    tree = ast.parse(source)
    module = CorpusModule(tree=tree, source=source, containing_pkg="synthetic")
    corpus_content = {"synthetic.wiredmod": module}
    idx_content = classify_collisions(corpus_content)
    key = resolve_symbol_key("Const", "synthetic.wiredmod", module, corpus=corpus_content)
    final_content = key_tier(key, "synthetic.wiredmod", idx_content)
    assert final_content is not None
    assert final_content.is_content_tier
    decls_content = {"synthetic.wiredmod": frozenset({"Const"})}
    per_symbol_content = {"synthetic.wiredmod": {"Const"}}
    submod_content = _submodule_index(per_symbol_content)
    stale_content = _compute_stale(
        decls_content,
        set(),
        corpus_content,
        idx_content,
        frozenset({final_content}),
        per_symbol_content,
        submod_content,
    )
    assert stale_content == ["synthetic.wiredmod::Const"]

    # -- module_path (escalated live-collision) tier --
    body = "class Dup:\n    pass\n"
    src_a = body + "\n\n__all__ = ['Dup']\n"
    src_b = body + "\n\n__all__ = ['Dup']\n"
    corpus_mp = {
        "synthetic.dup_a": CorpusModule(ast.parse(src_a), src_a, "synthetic"),
        "synthetic.dup_b": CorpusModule(ast.parse(src_b), src_b, "synthetic"),
    }
    idx_mp = classify_collisions(corpus_mp)
    key_a = resolve_symbol_key("Dup", "synthetic.dup_a", corpus_mp["synthetic.dup_a"], corpus=corpus_mp)
    final_a = key_tier(key_a, "synthetic.dup_a", idx_mp)
    assert final_a is not None
    assert not final_a.is_content_tier, "sanity: a live byte-identical collision must escalate"
    decls_mp = {
        "synthetic.dup_a": frozenset({"Dup"}),
        "synthetic.dup_b": frozenset({"Dup"}),
    }
    per_symbol_mp = {"synthetic.dup_a": {"Dup"}}  # only dup_a gained a caller
    submod_mp = _submodule_index(per_symbol_mp)
    stale_mp = _compute_stale(decls_mp, set(), corpus_mp, idx_mp, frozenset({final_a}), per_symbol_mp, submod_mp)
    assert stale_mp == ["synthetic.dup_a::Dup"], "stale must fire for a module_path-tier entry too -- body-independent"


def test_bite_g_dangling_entry_reds_both_tiers_and_body_edit_is_one_signal() -> None:
    """DoD (g) -- a dangling entry reds the new third ratchet direction, BOTH
    tiers, AND a dead-symbol body edit yields EXACTLY ONE signal (T016).
    """
    # -- content-tier orphan: (bare_name, body_hash) matches NOTHING live --
    orphan_key = SymbolKey("GhostHelper", "0" * 64)
    dangling_content = _compute_dangling(frozenset({orphan_key}), {}, {}, offenders=[])
    assert dangling_content == ["GhostHelper (content-tier body_hash=000000000000)"]

    # -- module_path-tier orphan: the module no longer declares bare_name --
    mp_key = SymbolKey("Dup", "abc123", module_path="synthetic.dup_a")
    decls_no_dup = {"synthetic.dup_a": frozenset({"SomethingElse"})}
    dangling_mp = _compute_dangling(frozenset({mp_key}), decls_no_dup, {}, offenders=[])
    assert dangling_mp == ["Dup (module_path-tier module_path=synthetic.dup_a)"]

    # -- body-edit -> exactly ONE signal (offender-refresh), never offender+prune --
    old_source = "Baz = 1\n"
    old_module = CorpusModule(ast.parse(old_source), old_source, "synthetic")
    old_corpus = {"synthetic.bazmod": old_module}
    old_key = resolve_symbol_key("Baz", "synthetic.bazmod", old_module, corpus=old_corpus)
    old_final = key_tier(old_key, "synthetic.bazmod", classify_collisions(old_corpus))
    assert old_final is not None
    allow = frozenset({old_final})

    new_source = "Baz = 2\n"  # body EDITED -- still dead (no caller)
    new_module = CorpusModule(ast.parse(new_source), new_source, "synthetic")
    new_corpus = {"synthetic.bazmod": new_module}
    new_index = classify_collisions(new_corpus)
    decls = {"synthetic.bazmod": frozenset({"Baz"})}

    offenders = _compute_offenders(decls, {}, set(), allow, new_corpus, new_index)
    assert offenders == ["synthetic.bazmod::Baz"], "the body-edited symbol must surface as a fresh offender (offender-refresh)"

    dangling_after_edit = _compute_dangling(allow, decls, new_index, offenders)
    assert dangling_after_edit == [], "the SAME root cause must not ALSO trip the dangling/prune ratchet -- exactly one signal, not offender+prune"


def test_bite_j_gate_annassign_whitespace_zero_false_red() -> None:
    """DoD (j) gate-side -- an AnnAssign target survives annotation-whitespace
    reformatting AND relocation with ZERO false-red through the production
    ``_compute_offenders`` path (C-007). The unit-level probe
    (``tests/unit/test_symbol_key.py::test_dod_j_ann_assign_annotation_whitespace_invariance``)
    proves ONLY that ``body_hash`` itself is invariant; a unit-only (j)
    would be the self-validation loophole C-007 forbids -- this proves the
    GATE does not false-red on the same scenario.
    """
    original_src = "TTL_SECONDS:int=3600\n"
    original_module = CorpusModule(ast.parse(original_src), original_src, "synthetic")
    original_corpus = {"synthetic.old_home": original_module}
    original_index = classify_collisions(original_corpus)
    original_key = resolve_symbol_key("TTL_SECONDS", "synthetic.old_home", original_module, corpus=original_corpus)
    final_key = key_tier(original_key, "synthetic.old_home", original_index)
    assert final_key is not None
    allow = frozenset({final_key})

    # Relocated AND annotation-whitespace-reformatted -- still dead (no caller).
    reformatted_src = "TTL_SECONDS : int = 3600\n"
    reformatted_module = CorpusModule(ast.parse(reformatted_src), reformatted_src, "synthetic")
    reformatted_corpus = {"synthetic.new_home": reformatted_module}
    reformatted_index = classify_collisions(reformatted_corpus)
    decls = {"synthetic.new_home": frozenset({"TTL_SECONDS"})}

    offenders = _compute_offenders(decls, {}, set(), allow, reformatted_corpus, reformatted_index)
    assert offenders == [], "annotation-whitespace reformatting + relocation must be ZERO false-red at the gate level"


def test_bite_j_gate_single_alias_relocation_zero_false_red() -> None:
    """DoD (j) gate-side -- a single-alias ``ImportFrom`` entry survives a
    sibling-alias edit AND relocation with ZERO false-red through the
    production ``_compute_offenders`` path (C-007). Mirrors the unit-level
    ``test_dod_j_single_alias_distinct_from_edited_sibling`` probe, but
    proves the GATE itself does not false-red -- a whole-statement hash
    would sibling-contaminate ``B`` when ``Alpha``/``Gamma`` are edited.
    """
    original_src = "from foo.bar import Alpha, Beta as B, Gamma\n"
    original_module = CorpusModule(ast.parse(original_src), original_src, "synthetic")
    original_corpus = {"synthetic.old_home": original_module}
    original_index = classify_collisions(original_corpus)
    original_key = resolve_symbol_key("B", "synthetic.old_home", original_module, corpus=original_corpus)
    final_key = key_tier(original_key, "synthetic.old_home", original_index)
    assert final_key is not None
    allow = frozenset({final_key})

    # Relocated AND both sibling aliases renamed -- B itself untouched, still dead.
    mutated_src = "from foo.bar import AlphaRenamedCompletely, Beta as B, GammaRenamedToo\n"
    mutated_module = CorpusModule(ast.parse(mutated_src), mutated_src, "synthetic")
    mutated_corpus = {"synthetic.new_home": mutated_module}
    mutated_index = classify_collisions(mutated_corpus)
    decls = {"synthetic.new_home": frozenset({"B"})}

    offenders = _compute_offenders(decls, {}, set(), allow, mutated_corpus, mutated_index)
    assert offenders == [], "single-alias relocation + sibling-edit must be ZERO false-red at the gate level -- B must not be caught"
