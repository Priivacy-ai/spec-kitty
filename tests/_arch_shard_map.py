"""Single-source arch-adversarial pole shard-assignment table (FR-004, FR-005).

Mission ``ci-health-charter-path-and-arch-shard-01KWRTB2`` WP02 (#2397). The
``arch-adversarial`` CI job today runs the 4 pole roots — ``tests/adversarial``,
``tests/architectural``, ``tests/architecture``, ``tests/lint`` — as a single
14.4-minute matrix leg. This module is the **single committed source of truth**
for splitting that pole into 3 balanced, disjoint shards, keyed by whole
test-file (for ``tests/architectural/*.py``) or whole directory (for the other
three pole roots, folded in as functional units per the operator's
"whole test files kept intact, not split" steer, Decision Moment
``DM-01KWRWB0PPF5TQPNYF5D07XY3W``).

The concrete assignment below is copied **verbatim** from
``kitty-specs/ci-health-charter-path-and-arch-shard-01KWRTB2/data-model.md``
(a 216 / 215 / 215 greedy bin-packing result balanced by a ``def test_`` count
proxy — see ``research.md`` R2 for the honesty caveat that this is a structural
projection, not a live-duration measurement). Do not re-derive a different
split here; rebalance by editing this table directly if a future CI run shows
material drift.

``tests/conftest.py``'s ``pytest_collection_modifyitems`` hook applies the
matching ``arch_shard_<N>`` marker to every collected test whose file falls
under one of the 4 pole roots, looked up via :func:`shard_for`. Nothing outside
those roots is touched: :func:`shard_for` returns ``None`` for any other path,
which is what keeps the hook scoped (enforced by
``tests/architectural/test_arch_shard_marker_completeness.py``, IC-03).

This module is pure data + one lookup function — no pytest import, no side
effects — so it stays trivially unit-testable and reviewable as "just a table."
"""

from __future__ import annotations

# Whole-directory pole roots folded in as single functional units (never
# split across shards).
_ARCH_SHARD_1_DIRS: tuple[str, ...] = ("tests/adversarial",)
_ARCH_SHARD_2_DIRS: tuple[str, ...] = ("tests/lint",)
_ARCH_SHARD_3_DIRS: tuple[str, ...] = ("tests/architecture",)

# Individual `tests/architectural/*.py` file assignments — copied verbatim from
# data-model.md's committed 216 / 215 / 215 split.
_ARCH_SHARD_1_FILES: tuple[str, ...] = (
    # Added post-data-model.md (new file at implementation time, mission
    # cmd-output-file-leak-guard-01KWVZX7 #2169 WP01). All three shards were
    # tied at 30 files each when this guard landed; shard_1 was picked
    # arbitrarily to keep the table's insertion order alphabetical-ish and
    # the pick auditable.
    "tests/architectural/test_arch_unblind_matrix.py",
    "tests/architectural/test_charter_facades_reexport_doctrine.py",
    "tests/architectural/test_charter_references_resolve.py",
    "tests/architectural/test_ci_architectural_gate_coverage.py",
    "tests/architectural/test_ci_topology_worklist.py",
    "tests/architectural/test_compat_shims.py",
    "tests/architectural/test_docs_cli_reference_parity.py",
    "tests/architectural/test_integration_boundary.py",
    "tests/architectural/test_marker_job_completeness.py",
    "tests/architectural/test_marker_registry_single_source.py",
    "tests/architectural/test_no_dead_symbols.py",
    "tests/architectural/test_no_invalid_windows_filenames.py",
    "tests/architectural/test_no_legacy_status_emit_callers.py",
    "tests/architectural/test_no_legacy_terminology.py",
    "tests/architectural/test_no_raw_mission_spec_paths.py",
    "tests/architectural/test_no_tracked_test_feature_missions.py",
    "tests/architectural/test_no_write_side_rederivation.py",
    "tests/architectural/test_quarantine_marker.py",
    "tests/architectural/test_resolution_authority_gates.py",
    "tests/architectural/test_runtime_charter_doctrine_boundary.py",
    "tests/architectural/test_shard_universe_bounded.py",
    "tests/architectural/test_shared_package_boundary.py",
    "tests/architectural/test_single_mission_surface_resolver.py",
    "tests/architectural/test_src_filter_coverage.py",
    "tests/architectural/test_status_module_boundary.py",
    "tests/architectural/test_topology_inference_retired.py",
    "tests/architectural/test_topology_resolution_boundary.py",
    "tests/architectural/test_unit_contract_residual_gate.py",
    "tests/architectural/test_unregistered_shim_scanner.py",
    "tests/architectural/test_uv_lock_pin_drift.py",
    "tests/architectural/test_workflow_coherence.py",
    "tests/architectural/test_wp_owned_files_no_kitty_specs.py",
)

_ARCH_SHARD_2_FILES: tuple[str, ...] = (
    # Added post-data-model.md (new file at implementation time — data-model.md
    # §"Any tests/architectural/*.py file not listed above ... is an
    # assignment gap the completeness guard must catch"). shard_2 was the
    # lightest by file count (29 vs 30/30) at the time this WP was
    # implemented, so it lands here.
    "tests/architectural/test_arch_shard_marker_completeness.py",
    "tests/architectural/test_artifact_selection_completeness.py",
    "tests/architectural/test_charter_runtime_canonical_paths.py",
    "tests/architectural/test_commit_target_kind_guard.py",
    "tests/architectural/test_coord_read_residuals_closeout.py",
    "tests/architectural/test_coverage_consumer_needs.py",
    "tests/architectural/test_execution_context_parity.py",
    "tests/architectural/test_gate_coverage.py",
    "tests/architectural/test_job_count_ceiling.py",
    "tests/architectural/test_merge_pipeline_ratchets.py",
    "tests/architectural/test_migration_chain_integrity.py",
    "tests/architectural/test_mission_runtime_surface.py",
    "tests/architectural/test_no_op_stable_writes.py",
    "tests/architectural/test_no_phantom_worktree_repair.py",
    "tests/architectural/test_no_runtime_pypi_dep.py",
    "tests/architectural/test_org_activation_seam.py",
    "tests/architectural/test_plugin_validate_workflow.py",
    "tests/architectural/test_pyproject_shape.py",
    "tests/architectural/test_pytest_marker_convention.py",
    "tests/architectural/test_ratchet_baselines.py",
    "tests/architectural/test_status_sync_boundary.py",
    "tests/architectural/test_surface_resolution_audit.py",
    "tests/architectural/test_tasks_command_surface.py",
    "tests/architectural/test_tid251_enforcement.py",
    "tests/architectural/test_trigger_registry_coverage.py",
    "tests/architectural/test_typer_compat_ci.py",
    "tests/architectural/test_untrusted_path_containment.py",
    "tests/architectural/test_wp05_write_target_drain.py",
    "tests/architectural/test_wp_prompt_build_latency.py",
    "tests/architectural/test_write_surface_placement_guard.py",
)

_ARCH_SHARD_3_FILES: tuple[str, ...] = (
    "tests/architectural/test_activation_registry_schema.py",
    "tests/architectural/test_all_declarations_required.py",
    "tests/architectural/test_arch_pole_deserialized.py",
    "tests/architectural/test_auth_transport_singleton.py",
    "tests/architectural/test_builtin_override_policy.py",
    "tests/architectural/test_ci_quality_path_filters.py",
    "tests/architectural/test_docs_scoped_arch_coverage.py",
    "tests/architectural/test_dossier_sync_boundary.py",
    "tests/architectural/test_events_tracker_public_imports.py",
    "tests/architectural/test_gate_coverage_parse_model.py",
    "tests/architectural/test_gate_read_literal_ban.py",
    "tests/architectural/test_guard_capability_call_sites.py",
    "tests/architectural/test_layer_rules.py",
    "tests/architectural/test_no_dead_modules.py",
    "tests/architectural/test_no_primary_anchored_gates.py",
    "tests/architectural/test_no_prompt_filtering_added.py",
    "tests/architectural/test_no_shipped_layer_label.py",
    "tests/architectural/test_no_tmp_paths_in_tests.py",
    "tests/architectural/test_no_worktree_name_guess.py",
    # Added post-data-model.md (new file at implementation time, mission
    # review-regression-gate-01KWX6DF WP01, #572/#1979/#2283). shard_3 was the
    # lightest by file count (30 vs 31/31) when this file landed.
    "tests/architectural/test_pre_review_scope_singlesource.py",
    "tests/architectural/test_protection_resolver_call_sites.py",
    "tests/architectural/test_pytest_marker_correctness.py",
    "tests/architectural/test_real_home_isolation_guard.py",
    "tests/architectural/test_safe_commit_import_boundary.py",
    "tests/architectural/test_safety_registry_completeness.py",
    "tests/architectural/test_same_tier_uniqueness.py",
    "tests/architectural/test_serial_port_preservation.py",
    "tests/architectural/test_shim_registry_schema.py",
    "tests/architectural/test_tasks_domain_gate_visibility.py",
    "tests/architectural/test_template_governance_payload_contract.py",
    "tests/architectural/test_worktrees_index_clean.py",
)

# ``relpath -> shard`` for exact-file (architectural) units.
ARCH_SHARD_FILE_MAP: dict[str, int] = {
    **dict.fromkeys(_ARCH_SHARD_1_FILES, 1),
    **dict.fromkeys(_ARCH_SHARD_2_FILES, 2),
    **dict.fromkeys(_ARCH_SHARD_3_FILES, 3),
}

# ``dirpath -> shard`` for whole-directory (adversarial / architecture / lint)
# units.
ARCH_SHARD_DIR_MAP: dict[str, int] = {
    **dict.fromkeys(_ARCH_SHARD_1_DIRS, 1),
    **dict.fromkeys(_ARCH_SHARD_2_DIRS, 2),
    **dict.fromkeys(_ARCH_SHARD_3_DIRS, 3),
}

# The 4 pole roots this table (and the collection hook) is scoped to. Anything
# outside these roots must never receive an ``arch_shard_N`` marker.
POLE_ROOTS: tuple[str, ...] = (
    "tests/adversarial",
    "tests/architectural",
    "tests/architecture",
    "tests/lint",
)


def shard_for(relpath: str) -> int | None:
    """Return the ``arch_shard_N`` number (1/2/3) for *relpath*, or ``None``.

    *relpath* is a repo-root-relative path using ``/`` separators (as produced
    by pytest's own nodeid/relpath reporting). Resolution order:

    1. Whole-directory pole roots (``tests/adversarial``, ``tests/architecture``,
       ``tests/lint``) — any path under one of these directories resolves to
       that directory's single shard.
    2. Exact file match in :data:`ARCH_SHARD_FILE_MAP` (the
       ``tests/architectural/*.py`` per-file assignment).
    3. ``None`` for anything outside the 4 pole roots (including
       non-test infra modules inside ``tests/architectural/`` such as
       ``__init__.py`` / ``conftest.py`` / ``_gate_coverage.py`` /
       ``_gate_collect_plugin.py`` / ``_ratchet_keys.py``, and any path that
       isn't under one of :data:`POLE_ROOTS` at all).
    """
    normalized = relpath.replace("\\", "/")
    for dirpath, shard in ARCH_SHARD_DIR_MAP.items():
        if normalized == dirpath or normalized.startswith(f"{dirpath}/"):
            return shard
    return ARCH_SHARD_FILE_MAP.get(normalized)
