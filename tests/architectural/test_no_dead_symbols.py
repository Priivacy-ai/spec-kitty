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
        "charter._catalog_miss::CatalogMissDiagnosis",
        "charter._catalog_miss::CharterCatalogMissError",
        "charter._catalog_miss::CharterCatalogMissWarning",
        "charter.activations::ALLOWED_MISSION_TYPES",
        "charter.activations::REGISTERED_TRIGGERS",
        "charter.compact::CompactView",
        "charter.compact::extract_section_anchors",
        "charter.synthesizer.provenance::ProvenanceEntry",
        "charter.synthesizer.write_pipeline::StagedArtifact",
        "charter.synthesizer.write_pipeline::promote",
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
        "specify_cli.acceptance::ArtifactEncodingError",
        "specify_cli.acceptance::WorkPackageState",
        "specify_cli.acceptance::detect_mission_slug",
        "specify_cli.acceptance::normalize_feature_encoding",
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
        "specify_cli.cli.commands._branch_strategy_gate::ALREADY_CONFIRMED",
        "specify_cli.cli.commands._branch_strategy_gate::GateDecision",
        "specify_cli.cli.commands._branch_strategy_gate::GateOutcome",
        "specify_cli.cli.commands.agent.config::app",
        "specify_cli.cli.commands.agent::app",
        "specify_cli.cli.commands.auth::app",
        "specify_cli.cli.commands.context::app",
        "specify_cli.cli.commands.doctrine::app",
        "specify_cli.cli.commands.implement::_ensure_vcs_in_meta",
        "specify_cli.cli.commands.implement::detect_feature_context",
        "specify_cli.cli.commands.implement::find_wp_file",
        "specify_cli.cli.commands.mission::app",
        "specify_cli.cli.commands.review::TestExtraMissing",
        "specify_cli.cli.commands.review::assert_pytest_available",
        "specify_cli.cli.commands.review::review_mission",
        "specify_cli.cli.commands.sync::app",
        "specify_cli.cli.commands.verify::verify_setup",
        # _render_nag_if_needed and _should_suppress_nag removed from
        # allowlist: both now have live callers in the CLI startup readiness
        # coordinator path (Priivacy-ai/spec-kitty#1093).
        "specify_cli.compat._adapters.detector::VersionDetector",
        "specify_cli.compat._adapters.gate::_EXEMPT_COMMANDS",
        "specify_cli.compat._adapters.gate::check_schema_version",
        "specify_cli.compat._adapters.version_checker::MismatchType",
        "specify_cli.compat._adapters.version_checker::compare_versions",
        "specify_cli.compat._adapters.version_checker::format_version_error",
        "specify_cli.compat._adapters.version_checker::get_cli_version",
        "specify_cli.compat._adapters.version_checker::get_project_version",
        "specify_cli.compat._adapters.version_checker::should_check_version",
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
        "specify_cli.core.identity_aliases::with_tracked_mission_slug_aliases",
        "specify_cli.core.paths::StatusReadUnsupported",
        "specify_cli.core.paths::assert_worktree_supported",
        "specify_cli.core.paths::check_broken_symlink",
        "specify_cli.core.paths::resolve_with_context",
        "specify_cli.core.upgrade_probe::DEFAULT_TIMEOUT_S",
        "specify_cli.core.upgrade_probe::PYPI_JSON_URL",
        "specify_cli.core.utils::ensure_within_directory",
        "specify_cli.core.worktree_topology::FeatureTopology",
        "specify_cli.core.worktree_topology::WPTopologyEntry",
        "specify_cli.core.worktree_topology::render_topology_text",
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
        "specify_cli.decisions.emit::emit_decision_opened",
        "specify_cli.decisions.emit::emit_decision_resolved",
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
        "specify_cli.frontmatter::validate_frontmatter",
        "specify_cli.git.sparse_checkout::_reset_session_warning_state",
        "specify_cli.git.sparse_checkout::scan_path",
        "specify_cli.git.sparse_checkout_remediation::STEP_REFRESH_WORKING_TREE",
        "specify_cli.git.sparse_checkout_remediation::STEP_REMOVE_PATTERN_FILE",
        "specify_cli.git.sparse_checkout_remediation::STEP_SPARSE_DISABLE",
        "specify_cli.git.sparse_checkout_remediation::STEP_UNSET_CONFIG",
        "specify_cli.git.sparse_checkout_remediation::STEP_USER_DECLINED",
        "specify_cli.git.sparse_checkout_remediation::STEP_VERIFY_CLEAN",
        "specify_cli.git.sparse_checkout_remediation::SparseCheckoutRemediationReport",
        "specify_cli.git.sparse_checkout_remediation::SparseCheckoutRemediationResult",
        "specify_cli.glossary.semantic_events::SemanticConflictRecord",
        "specify_cli.intake.brief_writer::CrossFilesystemWriteError",
        "specify_cli.intake.brief_writer::atomic_write_bytes",
        "specify_cli.intake.brief_writer::atomic_write_text",
        "specify_cli.invocation.projection_policy::POLICY_TABLE",
        "specify_cli.invocation.projection_policy::ProjectionRule",
        "specify_cli.lanes.auto_rebase::AutoRebaseReport",
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
        "specify_cli.merge.state::get_state_path",
        "specify_cli.migration::normalize_mission_lifecycle_repo",
        "specify_cli.mission_brief::IntakeFileMissingError",
        "specify_cli.mission_brief::IntakeFileUnreadableError",
        "specify_cli.mission_brief::clear_mission_brief",
        "specify_cli.mission_v1.runner::MachineError",
        "specify_cli.mission_v1::MissionProtocol",
        "specify_cli.mission_v1::load_mission",
        "specify_cli.mission_v1::load_mission_by_name",
        "specify_cli.missions._legacy_aliases::LEGACY_FEATURE_HELP",
        "specify_cli.missions._legacy_aliases::hidden_feature_option",
        "specify_cli.missions::PrimitiveExecutionContext",
        "specify_cli.missions::execute_with_glossary",
        "specify_cli.next._internal_runtime.emitter::RuntimeEventEmitter",
        "specify_cli.next._internal_runtime.events::DecisionInputAnsweredPayload",
        "specify_cli.next._internal_runtime.events::DecisionInputRequestedPayload",
        "specify_cli.next._internal_runtime.events::JsonlEventLog",
        "specify_cli.next._internal_runtime.events::MissionRunCompletedPayload",
        "specify_cli.next._internal_runtime.events::MissionRunStartedPayload",
        "specify_cli.next._internal_runtime.events::NextStepAutoCompletedPayload",
        "specify_cli.next._internal_runtime.events::NextStepIssuedPayload",
        "specify_cli.next._internal_runtime.events::SignificanceEvaluatedPayload",
        "specify_cli.next._internal_runtime.events::TimeoutExpiredPayload",
        "specify_cli.next.discovery::ClaimablePreview",
        "specify_cli.ownership.inference::SRC_FALLBACK_GLOB",
        "specify_cli.ownership.inference::SRC_FALLBACK_WARNING",
        "specify_cli.ownership.validation::validate_authoritative_surface",
        "specify_cli.ownership.validation::validate_execution_mode_consistency",
        "specify_cli.ownership.validation::validate_no_overlap",
        "specify_cli.plan_validation::detect_unfilled_plan",
        "specify_cli.runtime.home::_is_windows",
        "specify_cli.runtime.resolver::ResolutionResult",
        "specify_cli.runtime.resolver::ResolutionTier",
        "specify_cli.runtime::AssetDisposition",
        "specify_cli.runtime::MigrationReport",
        "specify_cli.runtime::OriginEntry",
        "specify_cli.runtime::ResolutionResult",
        "specify_cli.runtime::ResolutionTier",
        "specify_cli.runtime::classify_asset",
        "specify_cli.scripts.tasks.acceptance_support::AcceptanceError",
        "specify_cli.scripts.tasks.acceptance_support::AcceptanceMode",
        "specify_cli.scripts.tasks.acceptance_support::AcceptanceResult",
        "specify_cli.scripts.tasks.acceptance_support::AcceptanceSummary",
        "specify_cli.scripts.tasks.acceptance_support::ArtifactEncodingError",
        "specify_cli.scripts.tasks.acceptance_support::WorkPackageState",
        "specify_cli.scripts.tasks.acceptance_support::acceptance_lane_derivations",
        "specify_cli.scripts.tasks.acceptance_support::choose_mode",
        "specify_cli.scripts.tasks.acceptance_support::collect_feature_summary",
        "specify_cli.scripts.tasks.acceptance_support::detect_mission_slug",
        "specify_cli.scripts.tasks.acceptance_support::normalize_feature_encoding",
        "specify_cli.scripts.tasks.acceptance_support::resolve_acceptance_actor",
        "specify_cli.scripts.tasks.acceptance_support::perform_acceptance",
        "specify_cli.shims::SkillRegistry",
        "specify_cli.shims::generate_shims",
        "specify_cli.skills.manifest_store::SCHEMA_VERSION",
        "specify_cli.skills.manifest_store::fingerprint",
        "specify_cli.skills.manifest_store::fingerprint_file",
        "specify_cli.skills.manifest_store::load",
        "specify_cli.skills.manifest_store::save",
        "specify_cli.status.lifecycle_events::LIFECYCLE_EVENT_TYPES",
        "specify_cli.status.lifecycle_events::MISSION_CREATED",
        "specify_cli.status.lifecycle_events::MISSION_EVENTS_FILENAME",
        "specify_cli.status.lifecycle_events::PROJECT_EVENTS_FILENAME",
        "specify_cli.status.lifecycle_events::PROJECT_INITIALIZED",
        "specify_cli.status.lifecycle_events::WP_CREATED",
        "specify_cli.status.lifecycle_events::append_lifecycle_event",
        "specify_cli.status.lifecycle_events::has_lifecycle_event",
        "specify_cli.status.lifecycle_events::mission_event_log_path",
        "specify_cli.status.lifecycle_events::project_event_log_path",
        "specify_cli.status.lifecycle_events::read_lifecycle_events",
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
        "specify_cli.sync.replay::ProjectMismatch",
        "specify_cli.sync.replay::ReplayConflictRecord",
        "specify_cli.sync.replay::ReplayDecision",
        "specify_cli.sync.replay::ReplayResult",
        "specify_cli.sync.replay::ReplayTarget",
        "specify_cli.sync.replay::TenantMismatch",
        "specify_cli.sync.replay::classify_event",
        "specify_cli.sync.replay::replay_events",
        "specify_cli.sync.tracker_client_glue::RetryHistoryEntry",
        "specify_cli.sync.tracker_client_glue::TrackerSyncFailed",
        "specify_cli.sync.tracker_client_glue::TrackerSyncPolicy",
        "specify_cli.sync.tracker_client_glue::run_bidirectional_sync_with_retry",
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
        "specify_cli.upgrade.migrations.m_3_2_3_unified_bundle::MIGRATION_ID",
        "specify_cli.upgrade.migrations.m_3_2_3_unified_bundle::TARGET_VERSION",
        "specify_cli.upgrade.migrations.m_3_2_3_unified_bundle::UnifiedBundleMigration",
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
        "specify_cli.workspace.assert_initialized::SPEC_KITTY_REPO_NOT_INITIALIZED",
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
        "charter.invocation_context::OperationalContext",
        "charter.invocation_context::build_operational_context",
        "charter.invocation_context::OperationalContext.require_active_profile",
        "charter.invocation_context::OperationalContext.require_active_role",
        "charter.invocation_context::ContextPreconditionError",
        # consumed by charter pack consistency-check CLI command (WP06,
        # charter-pack-activation-layer lane-f); wiring deferred
        "charter.consistency_check::ConsistencyReport",
        "charter.consistency_check::run_consistency_check",
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
# These two package-level exports intentionally support legacy
# package-level mock patch targets in tests and downstream
# consumers while submodules resolve the values dynamically from the package.
_CATEGORY_C_CHARTER_SPLIT_LEGACY_PATCH_SURFACE: frozenset[str] = frozenset(
    {
        "specify_cli.cli.commands.charter::_dm_service",
        "specify_cli.cli.commands.charter::find_repo_root",
    }
)

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
        # STATUS_READ_PATH_NOT_FOUND_CODE / StatusReadPathNotFound are
        # the public error contract of the read-path resolver used by
        # WP08's CLI status mediation. Today the CLI uses the resolver
        # function directly; the structured error code is exercised by
        # tests/integration/test_cli_status_mediation.py.
        "specify_cli.missions._read_path_resolver::STATUS_READ_PATH_NOT_FOUND_CODE",
        "specify_cli.missions._read_path_resolver::StatusReadPathNotFound",
        # resolve_planning_branch_from_meta is the pure-helper variant
        # used by tests/specify_cli/cli/commands/agent/test_mission_finalize_tasks.py;
        # production callers route through the IO-shaped wrapper that
        # itself calls the pure helper internally.
        "specify_cli.missions._resolve_planning_branch::resolve_planning_branch_from_meta",
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
    }
)


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
        # doctrine.missions.mission_step_repository: MissionStepRepository and StepKey
        # ship ahead of the charter.resolve_action_sequence caller (WP08)
        "doctrine.missions.mission_step_repository::MissionStepRepository",
        "doctrine.missions.mission_step_repository::StepKey",
        # specify_cli.charter_activate: activation helper functions consumed by
        # CLI activate command (WP06 wiring deferred to activation CLI WP)
        "specify_cli.charter_activate::AffectedMission",
        "specify_cli.charter_activate::StepRemovalWarning",
        "specify_cli.charter_activate::emit_step_removal_warnings",
        "specify_cli.charter_activate::find_removed_steps",
        "specify_cli.charter_activate::scan_inflight_missions",
        # specify_cli.cli.commands.charter.activate: activate_cmd is the CLI
        # entry point registered via the charter command group (WP06 wiring deferred)
        "specify_cli.cli.commands.charter.activate::activate_cmd",
        # specify_cli.doctrine.org_charter: cycle/extension error types consumed
        # by CLI validation (WP06 wiring deferred)
        "specify_cli.doctrine.org_charter::OrgCharterCycleError",
        "specify_cli.doctrine.org_charter::OrgCharterExtensionError",
    }
)


# Aggregate. The gate consults this; the per-category frozensets are
# the surface introspected by the ratchet-baseline meta-test
# (``tests/architectural/test_ratchet_baselines.py``).
_SYMBOL_ALLOWLIST: frozenset[str] = (
    _CATEGORY_A_SLICE_F_DEFERRED
    | _CATEGORY_B_GRANDFATHERED_LEGACY
    | _CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE
    | _CATEGORY_C_WP_IN_FLIGHT_WORKFLOW_REGISTRY
    | _CATEGORY_C_CHARTER_SPLIT_LEGACY_PATCH_SURFACE
    | _CATEGORY_C_WP_IN_FLIGHT_COORDINATION_BRANCH
    | _CATEGORY_C_WP_IN_FLIGHT_UNIFIED_MISSION_STEP
    | _CATEGORY_C_WP_IN_FLIGHT_CHARTER_ACTIVATION
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


def _resolve_import_from(node: ast.ImportFrom, containing_pkg: str) -> str:
    """Resolve a ``from X import ...`` node to its absolute module name."""
    level = node.level or 0
    mod = node.module or ""
    if level == 0:
        return mod
    pkg_parts = containing_pkg.split(".") if containing_pkg else []
    base_parts = pkg_parts[: len(pkg_parts) - (level - 1)] if level > 1 else pkg_parts[:]
    if mod:
        base_parts = base_parts + mod.split(".")
    return ".".join(base_parts)


def _extract_all_literal(tree: ast.Module) -> frozenset[str] | None:
    """Return the names listed in the module's ``__all__`` if static.

    Returns ``None`` if the module does not declare ``__all__`` OR
    declares it dynamically (e.g. ``__all__ = sorted(...)``). Dynamic
    declarations satisfy ``test_all_declarations_required`` (presence is
    the contract there) but cannot be statically introspected for
    membership and are therefore skipped by this gate.

    Accepts both ``ast.Assign`` and ``ast.AnnAssign`` -- typed
    declarations like ``__all__: list[str] = []`` are equivalent for
    the purposes of this walker.
    """
    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            tgt = node.target
            if isinstance(tgt, ast.Name) and tgt.id == "__all__":
                value = node.value
        else:
            continue
        if value is None:
            # AnnAssign without value (``__all__: list[str]``): treat as
            # dynamic / absent membership.
            return frozenset()
        if not isinstance(value, (ast.List, ast.Tuple)):
            return None
        names: list[str] = []
        for elt in value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                names.append(elt.value)
            else:
                return None
        return frozenset(names)
    return None


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
    for path, tree in path_to_tree.items():
        containing = _package_of(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                target = _resolve_import_from(node, containing)
                for alias in node.names:
                    if alias.name == "*":
                        star_targets.add(target)
                    else:
                        per_symbol.setdefault(target, set()).add(alias.name)
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


def test_no_public_symbol_in_all_is_unimported() -> None:
    """Every name in every ``__all__`` must have at least one caller in src/.

    Failure means a public symbol is declared (``__all__``) but no
    other ``src/`` file imports it. That's the WP08 cycle-1
    "library written but never wired" failure mode at symbol level.
    """
    decls, path_to_dotted, path_to_tree = _walk_modules()
    per_symbol, star_targets = _imports_by_target(path_to_dotted, path_to_tree)
    submodule_index = _submodule_index(per_symbol)

    offenders: list[str] = []
    for mod_dotted, names in sorted(decls.items()):
        if mod_dotted in star_targets:
            # Star-imported elsewhere; ``__all__`` is consumed wholesale.
            continue
        for name in sorted(names):
            qualified = f"{mod_dotted}::{name}"
            if qualified in _SYMBOL_ALLOWLIST:
                continue
            if _symbol_has_caller(name, mod_dotted, per_symbol, submodule_index):
                continue
            offenders.append(qualified)

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
