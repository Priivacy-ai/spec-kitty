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

``_SYMBOL_ALLOWLIST`` carries documented exceptions as qualified
``module::Name`` strings. As of WP02 GREEN the ratchet starts empty:
the WP migrates every charter / kernel module to declare ``__all__``
AND wires (or prunes) every otherwise-orphan symbol. Future entries
MUST cite a rationale and a follow-up tracker ticket per FR-303.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from specify_cli.ast_analysis.imports import (
    extract_static_all as _extract_all_literal,
    module_of_import_from as _resolve_import_from,
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
# carried over from earlier missions. WP02 did not delete these in the
# interest of preserving their intended public-API contracts; a future
# mission MUST either wire each from a runtime caller, remove it from
# ``__all__``, or delete the symbol entirely. Target = 0 by Slice G.
_CATEGORY_A_SLICE_F_DEFERRED: frozenset[str] = frozenset(
    {
        "charter._catalog_miss::CatalogMissCause",
        "charter._catalog_miss::CharterCatalogMissError",
        "charter._catalog_miss::CharterCatalogMissWarning",
        "charter.activations::ALLOWED_MISSION_TYPES",
        "charter.activations::REGISTERED_TRIGGERS",
        "charter.compact::CompactView",
        "charter.compact::extract_section_anchors",
        "charter.synthesizer.provenance::ProvenanceEntry",
        "charter.synthesizer.write_pipeline::StagedArtifact",
        # promote: rescued by detector (a) — add_typer/app.command patterns
        # now capture module-attr accesses (WP01 harden-dead-symbol-gate).
        "kernel._safe_re::is_re2_active",
    }
)

# ---------- B. Grandfathered legacy (out of WP02 scope) ----------
# Pre-existing public symbols across ``src/doctrine/`` + ``src/specify_cli/``
# whose ``__all__`` membership predates the WP02 symbol-level gate. WP02
# is scoped to ``src/charter/`` + ``src/kernel/`` per C-007 / FR-121, so
# these entries are inherited as-is into the ratchet baseline. The
# expectation is that a follow-up mission (post-WP12) will sweep this
# category by widening the C-007 ``__all__`` convention to the remaining
# subpackages, at which point each entry must be wired / pruned / deleted
# under the same discipline applied by WP02 to charter+kernel.
#
# Per the Slice F ratchet policy (C-004), this category MAY only shrink:
# growth requires an entry in ``_baselines.yaml`` plus a
# ``# justification:`` comment and a follow-up tracker ticket per FR-303.
_CATEGORY_B_GRANDFATHERED_LEGACY: frozenset[str] = frozenset(
    {
        "doctrine.directives::ArtifactKind",
        "doctrine.missions::MissionRepository",
        # doctrine.missions.models symbols are used internally by
        # MissionTypeRepository but not imported directly by specify_cli
        # callers; grandfathered into the baseline until a follow-up
        # sweep wires or removes them (FR-303).
        "doctrine.missions.models::IDENTIFIER_PATTERN",
        "doctrine.missions.models::Mission",
        "doctrine.missions.models::MissionOrchestration",
        "doctrine.missions.models::MissionStateObject",
        "doctrine.missions.models::MissionTransition",
        "doctrine.procedures::ArtifactKind",
        "doctrine.shared::ConflictType",
        "doctrine.shared::ExtractedTerm",
        "doctrine.shared::GlossaryScope",
        "doctrine.shared::ScopeRef",
        "doctrine.shared::SemanticConflict",
        "doctrine.shared::SenseRef",
        "doctrine.shared::Severity",
        "doctrine.shared::Strictness",
        "doctrine.shared::TermSurface",
        "doctrine.tactics::ArtifactKind",
        "specify_cli.acceptance::AcceptanceMode",
        "specify_cli.acceptance::WorkPackageState",
        "specify_cli.acceptance::detect_mission_slug",
        "specify_cli.auth.refresh_transaction::RefreshResult",
        "specify_cli.cli.commands._auth_doctor::DaemonSummary",
        "specify_cli.cli.commands._auth_doctor::DoctorReport",
        "specify_cli.cli.commands._auth_doctor::Finding",
        "specify_cli.cli.commands._auth_doctor::LockSummary",
        "specify_cli.cli.commands._auth_doctor::ServerSessionStatus",
        "specify_cli.cli.commands._auth_doctor::SessionSummary",
        "specify_cli.cli.commands._auth_doctor::assemble_report",
        "specify_cli.cli.commands._auth_doctor::compute_exit_code",
        "specify_cli.cli.commands._auth_doctor::render_report",
        "specify_cli.cli.commands._auth_doctor::render_report_json",
        "specify_cli.cli.commands._branch_strategy_gate::GateDecision",
        "specify_cli.cli.commands._branch_strategy_gate::GateOutcome",
        # agent.config::app, agent::app, auth::app, context::app,
        # doctrine::app, mission::app, review::review_mission, sync::app,
        # verify::verify_setup: rescued by detector (a) — add_typer(mod.app)
        # and app.command()(mod.fn) accesses are now walked as module-attr
        # accesses (WP01 harden-dead-symbol-gate-01KW0RJR).
        "specify_cli.cli.commands.charter.activate::charter_activate_app",
        "specify_cli.cli.commands.charter.deactivate::charter_deactivate_app",
        "specify_cli.cli.commands.implement::_ensure_vcs_in_meta",
        "specify_cli.cli.commands.implement::detect_feature_context",
        "specify_cli.cli.commands.implement::find_wp_file",
        "specify_cli.cli.commands.review::TestExtraMissing",
        "specify_cli.cli.commands.review::assert_pytest_available",
        # _render_nag_if_needed and _should_suppress_nag removed from
        # allowlist: both now have live callers in the CLI startup readiness
        # coordinator path (Priivacy-ai/spec-kitty#1093).
        # compat._adapters.{detector,gate,version_checker}::* removed: dead pure-shim
        # files deleted (salvaged from closed #2159/#2049).
        "specify_cli.core.context_validation::CurrentContext",
        "specify_cli.core.context_validation::ExecutionContext",
        "specify_cli.core.context_validation::detect_execution_context",
        "specify_cli.core.context_validation::get_context_env_vars",
        "specify_cli.core.context_validation::get_current_context",
        "specify_cli.core.context_validation::require_either",
        "specify_cli.core.context_validation::require_worktree",
        "specify_cli.core.context_validation::set_context_env_vars",
        "specify_cli.core.file_lock::STALE_AFTER_S_DEFAULT",
        "specify_cli.core.git_ops::BranchResolution",
        "specify_cli.core.git_ops::has_tracking_branch",
        "specify_cli.core.git_preflight::GitPreflightIssue",
        "specify_cli.core.git_preflight::GitPreflightResult",
        "specify_cli.core.paths::StatusReadUnsupported",
        "specify_cli.core.paths::assert_worktree_supported",
        "specify_cli.core.paths::check_broken_symlink",
        "specify_cli.core.paths::resolve_with_context",
        "specify_cli.core.upgrade_probe::DEFAULT_TIMEOUT_S",
        "specify_cli.core.upgrade_probe::PYPI_JSON_URL",
        "specify_cli.core.worktree_topology::FeatureTopology",
        "specify_cli.core.worktree_topology::WPTopologyEntry",
        "specify_cli.core.worktree_topology::render_topology_text",
        # Pre-existing main drift surfaced when #612 triggers core-misc.
        # Follow-up: FR-303 should wire or de-export these public names.
        # WP04 (org-doctrine-profile-integrity-closeout): removed
        # ``charter.pack_context::CharterPackConfigError`` — WP12 wired a
        # live src/ caller, so the gate now reports it as a stale entry.
        "specify_cli.dashboard.api_types::ArtifactDirectoryFile",
        "specify_cli.dashboard.api_types::ArtifactInfo",
        "specify_cli.dashboard.api_types::CurrentFeatureDetected",
        "specify_cli.dashboard.api_types::CurrentFeatureNotDetected",
        "specify_cli.dashboard.api_types::DashboardHealthInfo",
        "specify_cli.dashboard.api_types::DiagnosticsErrorResponse",
        "specify_cli.dashboard.api_types::DiagnosticsFeatureStatus",
        "specify_cli.dashboard.api_types::DiagnosticsResponse",
        "specify_cli.dashboard.api_types::ErrorResponse",
        "specify_cli.dashboard.api_types::FeaturesListErrorResponse",
        "specify_cli.dashboard.api_types::FileIntegrity",
        "specify_cli.dashboard.api_types::KanbanStats",
        "specify_cli.dashboard.api_types::MissionRecord",
        "specify_cli.dashboard.api_types::ResearchArtifact",
        "specify_cli.dashboard.api_types::SyncInfo",
        "specify_cli.dashboard.api_types::SyncTriggerSuccess",
        "specify_cli.dashboard.api_types::WorkflowStatus",
        "specify_cli.dashboard.api_types::WorktreeInfo",
        "specify_cli.dashboard.lifecycle::_write_dashboard_file",
        "specify_cli.dashboard.templates::get_dashboard_html",
        # emit_decision_opened, emit_decision_resolved: rescued by detector (a)
        # — decisions module accessed via module-attr pattern (WP01).
        "specify_cli.doctrine.org_charter::GovernancePolicy",
        "specify_cli.doctrine.org_charter::REQUIRED_KIND_FIELDS",
        "specify_cli.doctrine.org_charter::apply_org_charter_pre_fill",
        "specify_cli.doctrine.pack_assembler::AssemblyResult",
        "specify_cli.doctrine.pack_assembler::ConflictItem",
        # ValidationIssue + ValidationResult removed from allowlist (WP08):
        # doctrine org validate now imports them directly → no longer dead.
        "specify_cli.dossier.api::ArtifactDetailResponse",
        "specify_cli.dossier.api::ArtifactListItem",
        "specify_cli.dossier.api::ArtifactListResponse",
        "specify_cli.dossier.api::DossierHandlerAdapter",
        "specify_cli.dossier.api::DossierOverviewResponse",
        "specify_cli.dossier.api::SnapshotExportResponse",
        "specify_cli.frontmatter::add_history_entry",
        "specify_cli.frontmatter::get_field",
        # unshim-wave2-01KWMCAX (#2326) WP07: the singular update_field triad
        # (module wrapper, __all__ entry, orphaned instance method) is DELETED —
        # verified caller-less first (its twin update_fields stays live via
        # implement.py / lanes.implement_support). Row drained here; category_b
        # re-derived to the honest live count (NFR-004).
        "specify_cli.frontmatter::validate_frontmatter",
        "specify_cli.git.sparse_checkout::_reset_session_warning_state",
        "specify_cli.git.sparse_checkout::SparseCheckoutKind",
        "specify_cli.git.sparse_checkout::scan_path",
        "specify_cli.git.sparse_checkout_remediation::STEP_REFRESH_WORKING_TREE",
        "specify_cli.git.sparse_checkout_remediation::STEP_REMOVE_PATTERN_FILE",
        "specify_cli.git.sparse_checkout_remediation::STEP_SPARSE_DISABLE",
        "specify_cli.git.sparse_checkout_remediation::STEP_UNSET_CONFIG",
        "specify_cli.git.sparse_checkout_remediation::STEP_USER_DECLINED",
        "specify_cli.git.sparse_checkout_remediation::STEP_VERIFY_CLEAN",
        "specify_cli.git.sparse_checkout_remediation::SparseCheckoutRemediationReport",
        "glossary.semantic_events::SemanticConflictRecord",
        "specify_cli.intake.brief_writer::CrossFilesystemWriteError",
        "specify_cli.intake.brief_writer::atomic_write_bytes",
        "specify_cli.intake.brief_writer::atomic_write_text",
        "specify_cli.invocation.projection_policy::POLICY_TABLE",
        "specify_cli.invocation.projection_policy::ProjectionRule",
        "specify_cli.lanes.lifecycle_sync::LANE_AUTO_REBASE_FAILED",
        "specify_cli.merge.conflict_classifier::ClassifierRule",
        "specify_cli.merge.conflict_classifier::RULES",
        "specify_cli.merge.conflict_classifier::Resolution",
        "specify_cli.merge.conflict_classifier::r_default_manual",
        "specify_cli.merge.conflict_classifier::r_init_imports_union",
        "specify_cli.merge.conflict_classifier::r_pyproject_deps_union",
        "specify_cli.merge.conflict_classifier::r_urls_list_union",
        "specify_cli.merge.conflict_classifier::r_uvlock_regenerate",
        "specify_cli.merge.ordering::display_merge_order",
        "specify_cli.merge.state::MergeAmbiguousStateError",
        "specify_cli.merge.state::detect_git_merge_state",
        "specify_cli.migration::normalize_mission_lifecycle_repo",
        "specify_cli.mission_brief::IntakeFileMissingError",
        "specify_cli.mission_brief::IntakeFileUnreadableError",
        "specify_cli.mission_brief::clear_mission_brief",
        "specify_cli.mission_v1.runner::MachineError",
        "specify_cli.mission_v1::MissionProtocol",
        "specify_cli.mission_v1::load_mission",
        "specify_cli.mission_v1::load_mission_by_name",
        "specify_cli.missions::PrimitiveExecutionContext",
        "specify_cli.missions::execute_with_glossary",
        "runtime.next._internal_runtime.emitter::RuntimeEventEmitter",
        "runtime.next._internal_runtime.events::JsonlEventLog",
        "runtime.next.discovery::ClaimablePreview",
        "specify_cli.ownership.inference::SRC_FALLBACK_GLOB",
        "specify_cli.ownership.inference::SRC_FALLBACK_WARNING",
        "specify_cli.ownership.validation::validate_authoritative_surface",
        "specify_cli.ownership.validation::validate_execution_mode_consistency",
        "specify_cli.ownership.validation::validate_no_overlap",
        "specify_cli.plan_validation::detect_unfilled_plan",
        "specify_cli.status.uninitialized_hint::find_wp_dependency_cycles",
        "specify_cli.runtime.home::_is_windows",
        "specify_cli.runtime.resolver::ResolutionResult",
        "specify_cli.runtime.resolver::ResolutionTier",
        "specify_cli.runtime::AssetDisposition",
        "specify_cli.runtime::MigrationReport",
        "specify_cli.runtime::OriginEntry",
        "specify_cli.runtime::ResolutionResult",
        "specify_cli.runtime::ResolutionTier",
        "specify_cli.runtime::classify_asset",
        "specify_cli.shims::SkillRegistry",
        "specify_cli.shims::generate_shims",
        "specify_cli.skills.manifest_store::SCHEMA_VERSION",
        "specify_cli.skills.manifest_store::load",
        "specify_cli.skills.manifest_store::save",
        "specify_cli.status.lifecycle_events::MISSION_CREATED",
        "specify_cli.status.lifecycle_events::MISSION_EVENTS_FILENAME",
        "specify_cli.status.lifecycle_events::PROJECT_EVENTS_FILENAME",
        "specify_cli.status.lifecycle_events::PROJECT_INITIALIZED",
        "specify_cli.status.lifecycle_events::WP_CREATED",
        "specify_cli.status.lifecycle_events::append_lifecycle_event",
        "specify_cli.status.lifecycle_events::has_lifecycle_event",
        # WP04 (org-doctrine-profile-integrity-closeout): removed
        # ``mission_event_log_path`` and ``read_lifecycle_events`` — both are
        # now wired from live src/ callers, so the gate reports them stale.
        "specify_cli.status.lifecycle_events::project_event_log_path",
        "specify_cli.sync.diagnostics::SyncDiagnostic",
        "specify_cli.sync.diagnostics::reset_emitted_codes",
        "specify_cli.sync.orphan_sweep::SweepReport",
        "specify_cli.sync.project_identity::atomic_write_config",
        "specify_cli.sync.project_identity::derive_project_slug",
        "specify_cli.sync.project_identity::generate_build_id",
        "specify_cli.sync.project_identity::generate_node_id",
        "specify_cli.sync.project_identity::generate_project_uuid",
        "specify_cli.sync.project_identity::is_writable",
        "specify_cli.sync.project_identity::load_identity",
        # unshim-wave1-01KWKVHB (#2292) WP03: the sync.replay (8) and
        # sync.tracker_client_glue (4) symbol rows were removed here in the
        # same tip as the module deletions (T008) — the modules no longer
        # exist, so these allowlist entries would be silent danglers.
        "specify_cli.task_metadata_validation::TaskMetadataError",
        "specify_cli.task_metadata_validation::detect_lane_mismatch",
        "specify_cli.task_metadata_validation::validate_task_metadata",
        "specify_cli.template.asset_generator::_convert_markdown_syntax_to_format",
        "specify_cli.text_sanitization::PROBLEMATIC_CHARS",
        "specify_cli.text_sanitization::sanitize_markdown_text",
        "specify_cli.tracker.origin::MissionFromTicketResult",
        "specify_cli.tracker.origin::OriginCandidate",
        "specify_cli.tracker.origin::SearchOriginResult",
        "specify_cli.tracker.origin::search_origin_candidates",
        "specify_cli.tracker.origin::start_mission_from_ticket",
        "specify_cli.upgrade.migrations.m_3_2_0rc35_unified_bundle::MIGRATION_ID",
        "specify_cli.upgrade.migrations.m_3_2_0rc35_unified_bundle::TARGET_VERSION",
        "specify_cli.upgrade.migrations.m_3_2_0rc35_unified_bundle::UnifiedBundleMigration",
        # 3.2.0rc39 orientation-block refresh migration: auto-discovered; no
        # static importer. Class is exercised via the MigrationRegistry.
        "specify_cli.upgrade.migrations.m_3_2_0rc39_refresh_orientation_block::RefreshOrientationBlockMigration",
        "specify_cli.upgrade.migrations::MigrationDiscoveryError",
        "specify_cli.validators.csv_schema::CSVSchemaValidation",
        "specify_cli.validators.paths::PathValidationResult",
        "specify_cli.validators.paths::suggest_directory_creation",
        "specify_cli.validators.research::APA_PATTERN",
        "specify_cli.validators.research::BIBTEX_PATTERN",
        "specify_cli.validators.research::CitationFormat",
        "specify_cli.validators.research::CitationIssue",
        "specify_cli.validators.research::CitationValidationResult",
        "specify_cli.validators.research::ResearchValidationError",
        "specify_cli.validators.research::SIMPLE_PATTERN",
        "specify_cli.validators.research::VALID_CONFIDENCE_LEVELS",
        "specify_cli.validators.research::VALID_RELEVANCE_LEVELS",
        "specify_cli.validators.research::VALID_SOURCE_STATUS",
        "specify_cli.validators.research::VALID_SOURCE_TYPES",
        "specify_cli.validators.research::detect_citation_format",
        "specify_cli.validators.research::is_apa_format",
        "specify_cli.validators.research::is_bibtex_format",
        "specify_cli.validators.research::is_simple_format",
        "specify_cli.validators.research::validate_citations",
        "specify_cli.validators.research::validate_source_register",
        "specify_cli.widen.interview_helpers::render_widen_hint_if_present",
    }
)

# ---------- C. WP-in-flight Slice F charter symbols ----------
# WP11 wiring trigger reached (post-merge remediation cycle 1, 2026-05-19):
# prompt_builder.py now imports build_with_scope from charter.scope_router,
# which transitively pulls CharterScope, CharterScopeConfig,
# CharterScopeConflict, CharterScopeNotFound into the live src/ import
# graph. All four symbols have live callers; the allowlist is empty.
# See HIGH-1 in the mission-review-report.md for the full rationale.
# specced, wiring deferred to follow-on mission (charter-pack-activation-layer WP03)
_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE: frozenset[str] = frozenset(
    {
        # WP04 (org-doctrine-profile-integrity-closeout): removed
        # ``charter.invocation_context::OperationalContext`` and
        # ``build_operational_context`` — WP14 wired live src/ callers, so
        # the gate now reports both as stale allowlist entries. The
        # method-level and ContextPreconditionError entries below remain
        # (not flagged: no live module-level ``__all__`` caller yet).
        "charter.invocation_context::OperationalContext.require_active_profile",
        "charter.invocation_context::OperationalContext.require_active_role",
        # ProjectContext: live callers landed in charter-pack-activation-layer-01KSYE4V
        # ContextPreconditionError: raised internally; no direct import in other src/ modules yet
        "charter.invocation_context::ContextPreconditionError",
        # run_consistency_check: live callers landed in charter/pack.py (WP06)
        # ConsistencyReport: no src/ caller yet — remains allowlisted
        "charter.consistency_check::ConsistencyReport",
    }
)

# ---------- C. WP-in-flight Slice F workflow registry symbols ----------
# WP11 removal trigger reached: get_workflow, UnknownWorkflowError,
# list_available_workflows are now imported by planner.py (which is in
# src/), and ActionStep is used as a type annotation in the same module.
# All four symbols have live src/ callers; the allowlist entry is removed.
_CATEGORY_C_WP_IN_FLIGHT_WORKFLOW_REGISTRY: frozenset[str] = frozenset()

# ---------- C. Charter command split legacy patch surface ----------
# WP06 split ``cli.commands.charter`` from a monolithic module into a package.
# WP01 (harden-dead-symbol-gate-01KW0RJR): both entries are now rescued by
# detector (a) — charter submodules import the package as
# ``import specify_cli.cli.commands.charter as _charter_pkg`` and access
# ``_charter_pkg.find_repo_root()`` / ``_charter_pkg._dm_service`` via
# module-attribute accesses that the new gate walks.  Emptied so the stale-
# allowlist check does not fail.
_CATEGORY_C_CHARTER_SPLIT_LEGACY_PATCH_SURFACE: frozenset[str] = frozenset()

# ---------- C. Mission #1348 coordination-branch atomic event log ----------
# Mission `mission-coordination-branch-atomic-event-log-01KSPTVW`
# (Priivacy-ai/spec-kitty#1348) introduced five public helper symbols
# whose only callers today live in the test suite. Each symbol is part
# of the new public surface for missions / coordination-branch
# topology and is already exercised by integration + unit tests; the
# in-process production callers will land as follow-up wiring during
# the migration tracked under Priivacy-ai/spec-kitty#1355 / #1356.
_CATEGORY_C_WP_IN_FLIGHT_COORDINATION_BRANCH: frozenset[str] = frozenset(
    {
        # CoordinationBranchResult / coordination_branch_name are the
        # public surface for the WP03 mission-create coord-branch
        # helper. Production callers in mission_creation use these
        # symbols' private siblings; the public surface is for future
        # rewiring and test fixtures.
        "specify_cli.missions._create::CoordinationBranchResult",
        "specify_cli.missions._create::coordination_branch_name",
        # resolve_planning_branch_from_meta is the pure-helper variant
        # used by tests/specify_cli/cli/commands/agent/test_mission_finalize_tasks.py;
        # production callers route through the IO-shaped wrapper that
        # itself calls the pure helper internally.
        "specify_cli.missions._resolve_planning_branch::resolve_planning_branch_from_meta",
    }
)


# ---------- C. WP-in-flight topology authority seam (mission 01KTYGTE) ----------
# Mission ``name-vs-authority-remediation-01KTYGTE`` WP03 adds the topology
# authority seam in ``coordination.surface_resolver``. The two structured types
# below are genuinely public API but are reached transitively rather than by
# name:
#   * ``ResolvedStatusSurface`` is the return type of the already-wired
#     ``resolve_status_surface_with_anchor`` (callers consume the value, not the
#     name); it predates this WP and was opted into the gate by adding ``__all__``
#     per C-007.
#   * ``CoordinationBranchDeleted`` was previously allowlisted as a transitive-via-
#     superclass consumer (the ``except StatusReadPathNotFound`` handlers catch it).
#     Mission 01KVN754 WP05 (coord-deleted convergence / #1848 / FR-005) now imports
#     it BY NAME into both ``status.aggregate._resolve_read_dir`` (a more-specific
#     ``except CoordinationBranchDeleted: raise`` AHEAD of the superclass re-wrap, so
#     the data-loss verdict is propagated, not masked) and
#     ``missions._read_path_resolver`` (the read-path DELETED hard-fail). Those
#     by-name importers make it a LIVE cross-module symbol, so its allowlist entry is
#     removed (a removal-probe now PASSES the gate because the real callers exist).
#   * ``CoordinationWorktreeEmpty`` was DELETED by mission 01KVN754 WP04 (coord-empty
#     Option B / #1716 / FR-003): coord-empty no longer raises — the surface falls
#     back to primary + emits a loud warning — so the carve-out is gone and its
#     allowlist entry was removed.
# Follow-up tracker: none — ``ResolvedStatusSurface`` is the lone remaining
# transitive-consumption entry (callers consume the return value, not the name).
_CATEGORY_C_WP_IN_FLIGHT_TOPOLOGY_AUTHORITY: frozenset[str] = frozenset(
    {
        "specify_cli.coordination.surface_resolver::ResolvedStatusSurface",
    }
)


# ---------- C. WP-in-flight unified MissionStep model (mission 01KSWJVX) ----------
# Mission ``charter-doctrine-mission-type-configuration-01KSWJVX`` WP01
# unified the previously-fragmented ``MissionStep`` classes into
# ``doctrine.missions.models.MissionStep`` and relocated the legacy
# step-contract types to ``doctrine.missions.step_contracts``. The
# public surface below ships ahead of the production callers that will
# land in later WPs of the same mission (WP03 ``MissionTypeRepository``,
# WP04 ``MissionStepRepository``, WP05 ``charter.resolve_action_sequence``).
# Until those WPs land, the symbols are exposed in ``__all__`` so the
# unified API is discoverable but carry only test callers. Follow-up
# tracker: mission-internal WP03/WP04/WP05.
_CATEGORY_C_WP_IN_FLIGHT_UNIFIED_MISSION_STEP: frozenset[str] = frozenset(
    {
        "doctrine.missions.models::IDENTIFIER_PATTERN",
        "doctrine.missions.models::Mission",
        "doctrine.missions.models::MissionOrchestration",
        "doctrine.missions.models::MissionStateObject",
        "doctrine.missions.models::MissionTransition",
        "doctrine.missions.step_contracts::DelegatesTo",
        # MissionStepRepository: live caller landed in charter.mission_steps (WP09)
        "doctrine.missions.mission_step_repository::StepKey",
    }
)


# ---------- C. WP-in-flight charter-pack activation layer (01KSYE4V) ----------
# ---------- C. WP-in-flight charter pack activation layer (mission 01KSYE4V) ----------
# Mission ``charter-pack-activation-layer-01KSYE4V`` WP05/WP06 introduce
# new public symbols across charter, doctrine, and specify_cli whose only
# callers today are in the test suite or in later WPs still being developed
# in parallel lanes. Production callers (CLI commands, activation pipeline)
# will wire these in follow-on WPs within the same mission.
# Follow-up tracker: mission-internal WP06/WP08 (CLI wiring).
_CATEGORY_C_WP_IN_FLIGHT_CHARTER_ACTIVATION: frozenset[str] = frozenset(
    {
        # charter.drg: PackContext is the DRG traversal context for pack-scoped
        # activation; consumed by charter activation pipeline (WP06 wiring deferred)
        "charter.drg::PackContext",
        # charter.pack_manager: activation/merge result types consumed by CLI
        # activation command (WP06 wiring deferred)
        "charter.pack_manager::ActivationResult",
        "charter.pack_manager::MergeResult",
        # doctrine.missions.mission_step_repository: MissionStepRepository live caller landed
        # in charter.mission_steps (WP09); StepKey still has test-only callers
        "doctrine.missions.mission_step_repository::StepKey",
        # specify_cli.charter_activate: AffectedMission and StepRemovalWarning are
        # return/field types used indirectly; emit_step_removal_warnings,
        # find_removed_steps, scan_inflight_missions wired from activate.py
        # in charter-pack-activation-layer-01KSYE4V post-merge remediation.
        "specify_cli.charter_activate::AffectedMission",
        "specify_cli.charter_activate::StepRemovalWarning",
        # specify_cli.doctrine.org_charter: cycle/extension error types consumed
        # by CLI validation (WP06 wiring deferred)
        "specify_cli.doctrine.org_charter::OrgCharterCycleError",
        "specify_cli.doctrine.org_charter::OrgCharterExtensionError",
    }
)


# ---------- C. org-doctrine close-out (mission-authored public surface) ----------
# Mission ``org-doctrine-profile-integrity-activation-closure-01KT1TV1`` and
# its close-out (``org-doctrine-profile-integrity-closeout-01KT3G68``)
# introduced public charter/doctrine API symbols whose production callers
# either ship in later WPs of the same mission family or are intentionally
# part of a discoverable public surface that is only test-exercised today.
# The parent's WP15 allowlist covering these symbols was dropped during the
# ``specify_cli.next`` -> ``runtime.next`` upstream rebase (it conflicted with
# the namespace migration); WP04 re-derives it against the live import graph
# in the current ``runtime.*`` namespace. WP03's ``charter.template_catalog``
# facade did NOT pull the ``doctrine.template_catalog`` accessor functions into
# the import graph, so all four remain genuinely unimported and are
# re-allowlisted here. ``charter.kind_vocabulary::CHARTER_KIND_TOKENS`` is NOT
# listed: it already has a live caller and is not flagged.
# Follow-up: these are mission-authored symbols awaiting live callers; they
# are re-derived each cycle, not a standing tracker (the mission owns them).
_CATEGORY_C_ORG_DOCTRINE_CLOSEOUT: frozenset[str] = frozenset(
    {
        "charter.activation_engine::ActivationPlan",
        "charter.cascade::DeactivationPlan",
        "charter.cascade::REFERENCE_RELATIONS",
        "charter.cascade::ReferencedArtifact",
        "charter.cascade::SharedSkip",
        "charter.drg::UnknownRelationError",
        "charter.kind_vocabulary::MISSION_TYPE_TOKEN",
        "doctrine.drg.org_pack_loader::AUGMENTATION_RELATIONS",
        "doctrine.drg.org_pack_loader::TOPOLOGY_KINDS",
        "doctrine.drg.org_pack_loader::merge_topology_artifact",
        "doctrine.template_catalog::template_id_for",
        "doctrine.template_catalog::template_node",
        "doctrine.template_catalog::template_nodes",
        "doctrine.template_catalog::template_urn",
        "specify_cli.cli.commands._doctrine_health::PackHealth",
    }
)


# ---------- C. Upstream session-presence public surface (pre-existing on main) ----------
# Three public symbols in ``specify_cli.session_presence`` modules that were
# added to ``upstream/main`` (#1756) ahead of callers that will land in a
# follow-on mission.  They surfaced in this gate run only because the
# mission's ``src/specify_cli/status/`` changes triggered the ``core_misc``
# path filter (the filter was not triggered on the upstream commits themselves).
# These are NOT this mission's code.  Allowlisted-with-tracker so the gate is
# GREEN.  Follow-up: wire or prune when the session-presence callers land.
_CATEGORY_C_UPSTREAM_SESSION_PRESENCE: frozenset[str] = frozenset(
    {
        # CACHE_PATH / TTL_SECONDS are module-level constants used internally
        # by UpgradeChecker but have no import-site callers in src/ yet.
        "specify_cli.session_presence.upgrade_check::CACHE_PATH",
        "specify_cli.session_presence.upgrade_check::TTL_SECONDS",
    }
)


_CATEGORY_C_QUALITY_DEBT_1928: frozenset[str] = frozenset(
    {
        # PathValidationError is the public exception type raised by
        # validate_mission_paths(..., strict=True). It is exercised by
        # tests/agent/test_validators_unit.py (which imports it as a public
        # symbol) and is part of the validator's documented public surface,
        # but the sole runtime caller (acceptance/__init__.py) invokes the
        # validator non-strict, so no src/ module imports the exception yet.
        # Kept in __all__ as a deliberate public API. Tracked under the
        # quality-debt epic #1928 (FR-303).
        "specify_cli.validators.paths::PathValidationError",
    }
)


_CATEGORY_C_BRANCH_NAMING_FAILOVER_SEAM: frozenset[str] = frozenset(
    {
        # Both symbols are LIVE — the gate only counts cross-file src/ `__all__`
        # importers, so a test-only hook and an intra-module env read are invisible
        # to it (NOT dead). Manufacturing a fake src/ importer is the exact
        # anti-pattern this gate warns against, so they are allow-listed instead.
        #
        # reset_legacy_failover_warning: a pytest one-shot reset hook for the
        # legacy-failover deprecation notice. Exercised by
        # tests/lanes/test_branch_naming_seam.py and
        # tests/merge/test_mid8_embedded_preflight.py. Part of the seam's public
        # test surface; no src/ caller by design (resetting one-shot state is a
        # test concern).
        "specify_cli.lanes.branch_naming::reset_legacy_failover_warning",
        # LEGACY_FAILOVER_SUPPRESS_ENV: the env-var name read INSIDE
        # branch_naming._emit_legacy_failover_warning (runtime-exercised via
        # _check_mission_branch -> resolve_branch_name). It is consumed in the
        # same module that declares it, so no cross-file src/ import exists; it is
        # exported so operators/tests can reference the canonical env name.
        "specify_cli.lanes.branch_naming::LEGACY_FAILOVER_SUPPRESS_ENV",
    }
)


# ---------- C. Test-facing agent.tasks re-export compatibility ----------
_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT: frozenset[str] = frozenset(
    {
        # Mission decompose-agent-tasks-god-module-01KVWVAR (#2058) split the
        # ``agent/tasks.py`` god-module into ``tasks_outline``,
        # ``tasks_materialization``, ``tasks_finalize_validation``, and
        # ``tasks_dependency_graph`` seams. These six names are RE-EXPORTED from
        # ``agent.tasks.__all__`` (``from ...tasks_* import <name>`` + ``__all__``)
        # purely to keep the existing test-facing import/patch surface stable:
        # the suite imports them via ``from ...agent.tasks import <name>`` and
        # patches them at ``...agent.tasks.<name>`` (see tests/agent/*,
        # tests/contract/*). The dead-symbol gate counts only cross-file *src/*
        # ``__all__`` importers, so a test-only re-export surface is invisible to
        # it (NOT dead). Manufacturing a fake src/ importer is the anti-pattern
        # this gate warns against, so they are allow-listed instead. ``app`` is
        # the seam's Typer sub-app, registered (not src-imported), mirroring the
        # already-grandfathered ``specify_cli.cli.commands.agent::app`` entry.
        # Burns down if/when the re-export is collapsed into the seam modules.
        # WP09 (tasks-py-degod-wave2-01KWH9EQ) burn-down:
        # ``_behind_commits_touch_only_planning_artifacts`` and
        # ``_check_dependent_warnings`` left this set — the wave-2 relocations
        # gave both live src/ callers via the ``_tasks.<attr>`` seam bridge
        # (tasks_shared.py / tasks_move_task.py), so the gate now sees them.
        "specify_cli.cli.commands.agent.tasks::_lane_targets_for_emit",
        "specify_cli.cli.commands.agent.tasks::_wp_lane_from_status_events",
        # agent.tasks::app: rescued by detector (a) (WP01 harden-dead-symbol-gate).
        "specify_cli.cli.commands.agent.tasks::compute_incomplete_dependents",
    }
)


# ---------- C. Merge god-module decomposition shim re-exports (mission #2057) -
# The ``cli/commands/merge.py`` god-module (3383 LOC, maxCC ~102) was
# decomposed into cohesive seams under ``specify_cli/merge/`` (issue #2057,
# behavior-preserving refactor). FR-006 mandates that the thin command shim
# re-export every relocated symbol so the ~41 importing test files and external
# back-compat consumers keep working with ZERO import edits and a byte-stable
# ``__all__``. Each symbol below is LIVE runtime code defined in (and used by)
# a ``merge/*`` seam; the shim re-export simply has no *src/* caller importing
# it *via the shim* (the seams import siblings directly, one-way — C-006/INV-2;
# tests import the relocated names from the shim, which this gate does not
# count). On origin/main this gate passed because each symbol's canonical home
# was already a seam with a cross-file src importer; the decomposition widened
# the shim's re-export surface from 24 to ~57 names, so the proof-of-life that
# previously covered them no longer reaches the new re-exports. Burn-down
# (FR-303): when the importing test files are repointed to the seam homes, the
# shim re-exports (and these entries) can be deleted.
_CATEGORY_C_MERGE_DECOMP_SHIM_REEXPORT_2057: frozenset[str] = frozenset(
    {
        f"specify_cli.cli.commands.merge::{name}"
        for name in (
            "_assert_baseline_merge_commit_on_target",
            "_assert_bookkeeping_snapshot_path_is_trusted",
            "_assert_merged_wps_done_on_target",
            "_assert_merged_wps_reached_done",
            "_assert_status_path_within_target_surface",
            "_assert_status_surface_path_is_trusted",
            "_bake_mission_number_into_mission_branch",
            "BaselineMergeCommitError",
            "_branch_trees_equal",
            "_capture_bookkeeping_snapshots",
            "_check_mission_branch",
            "_classify_porcelain_lines",
            "_clear_merge_state_for_mission",
            "_collect_hollow_review_warnings",
            "_effective_push_requested",
            "_emit_merge_diff_summary",
            "_emit_remediation_hint",
            "_enforce_canonical_status_history",
            "_enforce_planning_artifact_target_branch",
            "_enforce_review_artifact_consistency",
            "_enforce_target_branch_sync_preflight",
            "_has_branch_ref",
            "_has_transition_to",
            "HollowReviewWarnings",
            "_is_git_repo",
            "_is_linear_history_rejection",
            "_lane_already_integrated",
            "LINEAR_HISTORY_REJECTION_TOKENS",
            "_load_merge_state_for_mission",
            "_load_or_create_merge_state",
            "MissionBranchBlocker",
            "_paths_have_status_changes",
            "_project_status_bookkeeping_to_target",
            "_raw_porcelain_status",
            "_read_committed_meta_json",
            "_reconcile_completed_wps_for_resume",
            "_record_baseline_merge_commit",
            "_recorded_baseline_from_working_meta",
            "_refresh_primary_checkout_after_merge",
            "_resolve_merge_actor",
            "_restore_final_bookkeeping_snapshots",
            # _run_lane_based_merge: rescued by detector (a) (WP01).
            "_run_lane_based_merge_locked",
            "_STATUS_EVENTS_FILENAME",
            "_STATUS_FILENAME",
            "_target_bookkeeping_status_paths",
            "TARGET_BRANCH_NOT_SYNCHRONIZED",
            "_target_branch_still_at_baseline",
            "TARGET_BRANCH_SYNC_INVARIANT",
            "_target_branch_sync_payload",
            "target_branch_sync_remediation",
            "_validate_mission_slug_path_segment",
            "_warn_or_confirm_hollow_reviews",
        )
    }
    | {
        # Seam-INTERNAL helpers / the phase-state dataclass that mission #2057
        # exports from each new seam's own ``__all__`` as the FR-004 focused-test
        # contract (the per-seam test files import these names directly to drive
        # >=90% coverage of the moved code). Each is LIVE runtime code with
        # multiple intra-module references; they lost their cross-file *src/*
        # caller when the decomposition moved the consuming call out of
        # ``cli/commands/merge.py`` into a sibling seam (so the gate's
        # cross-file-src-importer proof-of-life no longer reaches them). They are
        # not dead — only seam-private + test-exercised. Burn-down (FR-303): drop
        # them from the seam ``__all__`` (leaving them as unexported internals)
        # once the focused tests reference them without the public-contract
        # expectation, or wire a runtime cross-seam caller.
        "specify_cli.merge.bookkeeping_projection::_assert_status_surface_file_path_is_trusted",
        "specify_cli.merge.bookkeeping_projection::_read_optional_bytes",
        "specify_cli.merge.bookkeeping_projection::_restore_optional_bytes",
        "specify_cli.merge.executor::_MergeRunState",
        "specify_cli.merge.ordering::_already_baked",
        "specify_cli.merge.ordering::_compute_next_mission_number_or_none",
        "specify_cli.merge.ordering::_is_assigned_mission_number",
        "specify_cli.merge.ordering::_mark_mission_number_baked",
        "specify_cli.merge.ordering::_write_mission_number_to_branch",
        "specify_cli.merge.push_preflight::check_push_safety",
        "specify_cli.merge.resolve::_extract_mission_slug",
        "specify_cli.merge.resolve::_iter_merge_states_for_slug",
        "specify_cli.merge.resolve::_merge_state_key_candidates",
    }
)


# ---------- B. T001-unblinded symbols (WP01 harden-dead-symbol-gate) ----------
# The T001 bug in ``_extract_all_literal`` caused any module with a top-level
# ``ast.AnnAssign`` (like ``MESSAGES: dict[...] = {...}``) BEFORE ``__all__``
# to be silently zeroed, hiding those modules from the gate entirely.  WP01
# fixes the parser; these symbols surfaced as offenders for the first time.
# They are grandfathered at the same "investigate + wire/prune/delete" policy
# as ``_CATEGORY_B_GRANDFATHERED_LEGACY``.  Burns down when each symbol is
# wired from a runtime caller, removed from ``__all__``, or deleted (FR-303).
_CATEGORY_B_T001_UNBLINDED: frozenset[str] = frozenset(
    {
        # auth.transport: public client classes and factory functions that
        # external consumers (plugins, org-packs, SaaS integration — #2158
        # SaaS-migration wave FR-006) use directly; no internal src/
        # from-import callers because the SaaS migration is deferred.
        "specify_cli.auth.transport::AuthenticatedClient",
        "specify_cli.auth.transport::AsyncAuthenticatedClient",
        "specify_cli.auth.transport::AuthRefreshFailed",
        "specify_cli.auth.transport::get_client",
        "specify_cli.auth.transport::get_async_client",
        "specify_cli.auth.transport::reset_clients",
    }
)


# ---------- C. Common Docs directive-id SSOT (scripts/-consumed) ----------
# ``COMMON_DOCS_DIRECTIVE_ID`` is the single source of truth for the Common
# Docs directive id (C-003 binding-must-resolve). Its only callers are the
# anti-sprawl structure ratchet (``scripts/docs/anti_sprawl_ratchet.py``) and
# that ratchet's self-test — both wired from scripts/ + tests/, not from any
# src/ module — so the qualified-import scanner sees no src/ caller. The module
# is correspondingly allowlisted in ``test_no_dead_modules._CATEGORY_2``.
# Manufacturing a fake src/ caller is the anti-pattern this gate warns against;
# allowlisted instead. (The dead-symbols gate is a separate file from the
# dead-modules gate, so the module allowlist does not suppress this check.)
_CATEGORY_C_COMMON_DOCS_RATCHET_CONSTANT: frozenset[str] = frozenset(
    {
        "doctrine.directives.common_docs::COMMON_DOCS_DIRECTIVE_ID",
    }
)


# ---------- C. event-sync retention/delivery mission public surface ----------
# Mission ``event-sync-retention-delivery-01KVYWRG`` (#2124) shipped two new
# domains (``specify_cli.delivery.*`` + ``specify_cli.event_journal.*``) plus a
# ``sync.migrate_journal`` migration. Their ACTIVE runtime callers are the CLI
# event-sync surface (``cli/commands/sync.py`` imports EventSyncConfig, Mode,
# DefaultReceiverFactory, dispatch, build_status_report, gc_payloads,
# archive_payloads, SqliteDeliveryLedger, SqliteDeliveryTargetRegistry,
# EventJournal/resolve_journal_path) and the capture path (``sync/emitter.py`` +
# ``sync/migrate_journal.py``). The names below are the remaining mission public
# surface: the locked per-WP test-contract (constants/dataclasses/protocols/
# helpers exercised directly by tests under tests/delivery + tests/event_journal)
# plus the C-008 OPT_OUT discard-safety machinery (FamilyClassification,
# DiscardDecision[Kind], DiscardAuditRecord, AuditSink, JsonlAuditSink,
# discard_decision). The discard machinery is implemented and unit-tested but its
# LIVE runtime enforcement on the capture path is DEFERRED to the legacy-queue
# retirement follow-up (mission-review-report DRIFT-1 / RISK-1): until the legacy
# destructive ``queue.py`` drain is retired there is no single live capture-time
# discard site to guard, and no production family-classification source exists
# yet (the only honest classification is fail-closed UNKNOWN). Wiring it into the
# per-event emit hot path now would be net-new design, not remediation. Tracked
# as a deferred follow-up in
# ``kitty-specs/event-sync-retention-delivery-01KVYWRG/issue-matrix.md``.
# Burn-down (FR-303): the follow-up that retires the legacy drain wires the
# discard guard + migration CLI + status/gc evaluators, shrinking this set.
_CATEGORY_C_EVENT_SYNC_RETENTION_DELIVERY: frozenset[str] = frozenset(
    {
        # delivery.config — policy axes + C-008 discard-safety machinery
        "specify_cli.delivery.config::AuditSink",
        "specify_cli.delivery.config::Delivery",
        "specify_cli.delivery.config::DiscardAuditRecord",
        "specify_cli.delivery.config::DiscardDecision",
        "specify_cli.delivery.config::DiscardDecisionKind",
        "specify_cli.delivery.config::FamilyClassification",
        "specify_cli.delivery.config::JsonlAuditSink",
        "specify_cli.delivery.config::MissingExternalEndpointError",
        "specify_cli.delivery.config::PolicyResolutionError",
        "specify_cli.delivery.config::ReceiverFactory",
        "specify_cli.delivery.config::ResolvedPolicy",
        "specify_cli.delivery.config::ResolvedTarget",
        "specify_cli.delivery.config::Retention",
        "specify_cli.delivery.config::UnknownModeError",
        "specify_cli.delivery.config::discard_decision",
        # delivery.ledger — per-target ledger contract surface
        "specify_cli.delivery.ledger::LEDGER_INDEX_NAME",
        "specify_cli.delivery.ledger::LedgerRow",
        "specify_cli.delivery.ledger::TERMINAL_STATUSES",
        "specify_cli.delivery.ledger::init_ledger",
        # delivery.receivers — DeliveryReceiver contract + gate vocabulary
        "specify_cli.delivery.receivers::BATCH_ENDPOINT_PATH",
        "specify_cli.delivery.receivers::BATCH_TIMEOUT_SECONDS",
        "specify_cli.delivery.receivers::GateDecision",
        "specify_cli.delivery.receivers::GateKind",
        "specify_cli.delivery.receivers::HttpResponse",
        "specify_cli.delivery.receivers::ReceiverGate",
        "specify_cli.delivery.receivers::STUB_ENDPOINT_URL",
        "specify_cli.delivery.receivers::StubReceiver",
        "specify_cli.delivery.receivers::map_batch_response",
        # delivery.status_report — additive status JSON section keys + helpers
        "specify_cli.delivery.status_report::ADDITIVE_SECTION_KEYS",
        "specify_cli.delivery.status_report::BODY_UPLOAD_COMPAT_KEY",
        "specify_cli.delivery.status_report::DELIVERY_LEDGER_KEY",
        "specify_cli.delivery.status_report::DELIVERY_TARGETS_KEY",
        "specify_cli.delivery.status_report::EVENT_JOURNAL_KEY",
        "specify_cli.delivery.status_report::GC_LARGE_JOURNAL_THRESHOLD_BYTES",
        "specify_cli.delivery.status_report::MIGRATION_CONFLICTS_KEY",
        "specify_cli.delivery.status_report::TARGET_AUTHORITY_KEY",
        "specify_cli.delivery.status_report::TERMINAL_FAILURES_KEY",
        "specify_cli.delivery.status_report::evaluate_gc_suggestion",
        # event_journal.coalesce — WP08 coalescing contract surface
        "specify_cli.event_journal.coalesce::CoalescingStrategy",
        "specify_cli.event_journal.coalesce::DeliveredAnywhereQuery",
        "specify_cli.event_journal.coalesce::SUPERSEDED_TABLE",
        "specify_cli.event_journal.coalesce::SupersedeMarker",
        "specify_cli.event_journal.coalesce::install",
        "specify_cli.event_journal.coalesce::read_supersede_markers",
        # event_journal.journal / models — append-only journal contract surface
        "specify_cli.event_journal.journal::JOURNAL_SUBDIR",
        "specify_cli.event_journal.models::ORDERED_COLUMNS",
        # sync.migrate_journal — WP10 migration entry points + audit surface.
        # ``AUDIT_DB_NAME``, ``MigrationResult`` and ``migrate_queues_to_journal``
        # gained live callers in WP12 (``spec-kitty sync migrate`` + the status
        # migration-audit read path in ``cli/commands/sync.py``); they are no
        # longer dead and were removed from this ratchet.
        "specify_cli.sync.migrate_journal::KNOWN_PREFIX",
        "specify_cli.sync.migrate_journal::LEGACY_DIGEST",
        "specify_cli.sync.migrate_journal::MIGRATION_NOTE",
        "specify_cli.sync.migrate_journal::MigrationConflict",
        "specify_cli.sync.migrate_journal::SourceDb",
        "specify_cli.sync.migrate_journal::SourceOutcome",
        "specify_cli.sync.migrate_journal::UNKNOWN_PREFIX",
        "specify_cli.sync.migrate_journal::discover_source_dbs",
        "specify_cli.sync.migrate_journal::migration_target_token",
    }
)


# sync-daemon-orphan-cleanup-01KWC2A3 (#2261): the ``ResetResult`` per-entry
# dataclasses are the public structured-reporting surface for
# ``auth doctor --reset`` (FR-005). They are constructed/asserted directly by the
# auth-doctor + orphan-sweep test suites (``tests/auth/test_auth_doctor_*`` and
# ``tests/sync/test_orphan_sweep_classification.py``) but, like their sibling
# ``SweepReport`` already on this allowlist, have no in-``src/`` importer because
# production code consumes them only through the ``ResetResult`` container.
_CATEGORY_C_SYNC_RESET_RESULT_ENTRIES: frozenset[str] = frozenset(
    {
        "specify_cli.sync.orphan_sweep::FailedEntry",
        "specify_cli.sync.orphan_sweep::SkippedEntry",
        "specify_cli.sync.orphan_sweep::SweptEntry",
    }
)


# Aggregate. The gate consults this; the per-category frozensets are
# the surface introspected by the ratchet-baseline meta-test
# (``tests/architectural/test_ratchet_baselines.py``).
_SYMBOL_ALLOWLIST: frozenset[str] = (
    _CATEGORY_A_SLICE_F_DEFERRED
    | _CATEGORY_B_GRANDFATHERED_LEGACY
    | _CATEGORY_B_T001_UNBLINDED
    | _CATEGORY_C_COMMON_DOCS_RATCHET_CONSTANT
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
]:
    """Walk src/, return (decls, path_to_dotted, path_to_tree).

    * ``decls`` maps module dotted name to the static ``__all__`` set.
    * ``path_to_dotted`` maps each ``*.py`` path to its dotted name.
    * ``path_to_tree`` caches parsed ASTs so the import walk does not
      re-read every file.
    """
    decls: dict[str, frozenset[str]] = {}
    path_to_dotted: dict[Path, str] = {}
    path_to_tree: dict[Path, ast.Module] = {}
    for path in _iter_src_python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - defensive
            continue
        dotted = _module_dotted(path)
        path_to_dotted[path] = dotted
        path_to_tree[path] = tree
        names = _extract_all_literal(tree)
        if names is not None:
            decls[dotted] = names
    return decls, path_to_dotted, path_to_tree


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
    return per_symbol, star_targets


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
      in ``charter.__all__`` and imported via ``charter.generator``
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
    return any(
        name in per_symbol.get(sub, set())
        for sub in submodule_prefixes.get(mod_dotted, ())
    )


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


def _compute_offenders(
    decls: dict[str, frozenset[str]],
    per_symbol: dict[str, set[str]],
    star_targets: set[str],
    allowlist: frozenset[str],
) -> list[str]:
    """Return sorted ``module::Name`` offenders for the symbol-level gate.

    Extracted so the end-to-end "teeth" self-test
    (``test_gate_still_flags_a_truly_dead_symbol``) drives a constructed
    dead-symbol fixture through the *exact* aggregate path the real gate
    uses — proving the four additive caller-detectors did not turn the gate
    into a silent no-op (NFR-001 / gate-can't-self-validate).
    """
    submodule_index = _submodule_index(per_symbol)
    offenders: list[str] = []
    for mod_dotted, names in sorted(decls.items()):
        if mod_dotted in star_targets:
            # Star-imported elsewhere; ``__all__`` is consumed wholesale.
            continue
        for name in sorted(names):
            qualified = f"{mod_dotted}::{name}"
            if qualified in allowlist:
                continue
            if _symbol_has_caller(name, mod_dotted, per_symbol, submodule_index):
                continue
            offenders.append(qualified)
    return offenders


def test_no_public_symbol_in_all_is_unimported() -> None:
    """Every name in every ``__all__`` must have at least one caller in src/.

    Failure means a public symbol is declared (``__all__``) but no
    other ``src/`` file imports it. That's the WP08 cycle-1
    "library written but never wired" failure mode at symbol level.
    """
    decls, path_to_dotted, path_to_tree = _walk_modules()
    per_symbol, star_targets = _imports_by_target(path_to_dotted, path_to_tree)
    submodule_index = _submodule_index(per_symbol)

    offenders = _compute_offenders(decls, per_symbol, star_targets, _SYMBOL_ALLOWLIST)

    # Detect stale allowlist entries (good news: the symbol gained a
    # caller; remove from allowlist).
    stale: list[str] = []
    for entry in _SYMBOL_ALLOWLIST:
        if "::" not in entry:
            continue
        mod_dotted, name = entry.split("::", 1)
        if _symbol_has_caller(name, mod_dotted, per_symbol, submodule_index):
            stale.append(entry)

    messages: list[str] = []
    if offenders:
        bullets = "\n  - ".join(sorted(offenders))
        messages.append(
            "Symbol-level dead-code gate FAILED. The following public "
            "symbols are declared in __all__ but no other src/ file "
            "imports them:\n  - "
            + bullets
            + "\n\nFix options (in order of preference):\n"
            "  1) Wire the symbol from a runtime caller.\n"
            "  2) Remove the symbol from __all__ (it stays in the "
            "module as an unexported internal).\n"
            "  3) Delete the symbol entirely if it is truly dead.\n"
            "  4) Add the qualified `module::Name` to "
            "`_SYMBOL_ALLOWLIST` in this file with a rationale and a "
            "follow-up tracker ticket (FR-303).\n"
        )
    if stale:
        bullets = "\n  - ".join(sorted(stale))
        messages.append(
            "Stale `_SYMBOL_ALLOWLIST` entries detected. The following "
            "symbols now have at least one caller and must be removed "
            "from the allowlist:\n  - " + bullets
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
    assert result == frozenset({"Foo", "Bar"}), (
        f"Expected frozenset({{Foo, Bar}}), got {result!r}"
    )


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
    assert _symbol_has_caller("Foo", "other_pkg", ps, sub_idx), (
        "other_pkg::Foo must be rescued by alias.Foo access"
    )
    # A different module with the same symbol name is NOT rescued.
    assert not _symbol_has_caller("Foo", "declaring_module", ps, sub_idx), (
        "declaring_module::Foo must NOT be rescued by alias.Foo where alias→other_pkg"
    )


def test_no_false_negative_getattr_detector() -> None:
    """Detector (d) must rescue the resolved module's symbol only."""
    src = "import target_mod\ngetattr(target_mod, 'Bar')"
    tree = ast.parse(src)
    alias_map, _ = _build_alias_map_and_consts(tree, "")
    ps: dict[str, set[str]] = {}
    _record_getattr_str_edges(tree, alias_map, ps, frozenset({"target_mod"}))
    sub_idx = _submodule_index(ps)

    assert _symbol_has_caller("Bar", "target_mod", ps, sub_idx), (
        "target_mod::Bar must be rescued by getattr(target_mod, 'Bar')"
    )
    assert not _symbol_has_caller("Bar", "unrelated_mod", ps, sub_idx), (
        "unrelated_mod::Bar must NOT be rescued"
    )


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
    _record_facade_edges(
        tree, "mypkg", str_consts, ps, frozenset({"mypkg.sub", "mypkg.other"})
    )
    sub_idx = _submodule_index(ps)

    # Cls is exported from mypkg.sub
    assert _symbol_has_caller("Cls", "mypkg.sub", ps, sub_idx), (
        "mypkg.sub::Cls must be rescued by the facade"
    )
    # fn is exported from mypkg.other
    assert _symbol_has_caller("fn", "mypkg.other", ps, sub_idx)
    # Neither rescues an unrelated module
    assert not _symbol_has_caller("Cls", "mypkg.unrelated", ps, sub_idx), (
        "mypkg.unrelated::Cls must NOT be rescued"
    )


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
    _record_module_attr_edges(
        tree, alias_map, ps_unguarded, frozenset({"M", "M.SomeClass"})
    )
    assert _symbol_has_caller(
        "NAME", "M", ps_unguarded, _submodule_index(ps_unguarded)
    ), "control: with M.SomeClass treated as a module, the collision rescues M::NAME"


def test_gate_still_flags_a_truly_dead_symbol() -> None:
    """End-to-end teeth (NFR-001): the hardened gate is not a silent no-op.

    Four additive caller-detectors can only ADD rescues, so a self-test must
    prove the aggregate path still FLAGS a symbol that nothing imports — and
    still PASSES one that has a real caller. Driven through the same
    ``_compute_offenders`` path the production gate uses.
    """
    decls = {"synthetic.deadmod": frozenset({"NeverImported"})}

    # No caller of any kind → still flagged.
    flagged = _compute_offenders(decls, {}, set(), frozenset())
    assert flagged == ["synthetic.deadmod::NeverImported"], (
        f"gate must flag a symbol with zero callers; got {flagged!r}"
    )

    # A real direct importer → not flagged (control).
    with_caller = {"synthetic.deadmod": {"NeverImported"}}
    assert _compute_offenders(decls, with_caller, set(), frozenset()) == [], (
        "a symbol with a real caller must NOT be flagged"
    )

    # Allowlisted → not flagged (control for the exception path).
    allow = frozenset({"synthetic.deadmod::NeverImported"})
    assert _compute_offenders(decls, {}, set(), allow) == []
