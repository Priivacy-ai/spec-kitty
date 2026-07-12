"""Shard registry — ``arch`` group row (data-model E1) + shared lookup (FR-002).

Originated as the single-source arch-adversarial pole shard-assignment table
(mission ``ci-health-charter-path-and-arch-shard-01KWRTB2`` WP02, #2397), now
generalized into an **N-group registry** (mission
``ci-test-topology-performance-01KXBJRT`` WP01, FR-002/C-003/D-044): ``arch``
and ``next`` (registered by the sibling ``tests/_next_shard_map.py``) are two
rows of *one* mechanism — :data:`SHARD_GROUPS` — not a cloned second table,
hook, or completeness guard.

The ``arch-adversarial`` CI job runs the 4 pole roots — ``tests/adversarial``,
``tests/architectural``, ``tests/architecture``, ``tests/lint`` — as a single
matrix leg. This module owns that group's row: 3 balanced, disjoint shards,
keyed by whole test-file (for ``tests/architectural/*.py``) or whole directory
(for the other three pole roots, folded in as functional units per the
operator's "whole test files kept intact, not split" steer, Decision Moment
``DM-01KWRWB0PPF5TQPNYF5D07XY3W``).

The concrete assignment below is copied **verbatim** from
``kitty-specs/ci-health-charter-path-and-arch-shard-01KWRTB2/data-model.md``
(a 216 / 215 / 215 greedy bin-packing result balanced by a ``def test_`` count
proxy — see ``research.md`` R2 for the honesty caveat that this is a structural
projection, not a live-duration measurement) and reshaped into the
:class:`ShardGroup` row **byte-for-byte** — no relpath moves shard as part of
this generalization. Rebalance by editing this table directly if a future CI
run shows material drift.

``tests/conftest.py``'s ``pytest_collection_modifyitems`` hook applies the
matching ``<marker_prefix>_<N>`` marker to every collected test whose file
falls under one of a registered group's roots, driven by iterating
:data:`SHARD_GROUPS`, looked up via :func:`shard_for`. Nothing outside a
group's roots is touched: :func:`shard_for` returns ``None`` for any path not
covered by the requested group, which is what keeps the hook scoped (enforced
by ``tests/architectural/test_arch_shard_marker_completeness.py`` /
``test_next_shard_marker_completeness.py``, GC-1).

This module is pure data + one lookup function — no pytest import, no side
effects — so it stays trivially unit-testable and reviewable as "just a
table."
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Whole-directory pole roots folded in as single functional units (never
# split across shards).
_ARCH_SHARD_1_DIRS: tuple[str, ...] = ("tests/adversarial",)
_ARCH_SHARD_2_DIRS: tuple[str, ...] = ("tests/lint",)
_ARCH_SHARD_3_DIRS: tuple[str, ...] = ("tests/architecture",)

# Individual `tests/architectural/*.py` file assignments — copied verbatim from
# data-model.md's committed 216 / 215 / 215 split.
_ARCH_SHARD_1_FILES: tuple[str, ...] = (
    # Added post-data-model.md (new file at implementation time, mission
    # ci-test-topology-performance-01KXBJRT WP01, FR-002 — the ``next`` group's
    # completeness guard, sibling to test_arch_shard_marker_completeness.py).
    # shard_1 was the lightest by file count (33 vs 34/34) when this file
    # landed, so it lands here.
    "tests/architectural/test_next_shard_marker_completeness.py",
    # Added post-data-model.md (new file, mission
    # ci-test-topology-performance-01KXBJRT WP04, #2590 — the GC-5
    # marker-baseline guard). WP04 landed this file without registering it in
    # this shard map, leaving it selected by zero arch_shard_N marker (GC-1
    # violation); WP06 (T014/T020, sole owner of ci-quality.yml and the
    # cross-lane roster pass) closes the gap as a follow-on data edit. All
    # three shards were tied at 34 files each when this fix landed; shard_1
    # was picked first (alphabetically paired with test_workflow_dist_lint.py
    # in shard_2 below) to keep the pick auditable.
    "tests/architectural/test_marker_baseline.py",
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
    "tests/architectural/test_session_reaper.py",
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
    # Added post-data-model.md (new file, mission
    # ci-test-topology-performance-01KXBJRT WP04, #2590 — the GC-4
    # workflow-dist lint guard). Same landing gap as
    # test_marker_baseline.py above (WP04 forgot to register it in this shard
    # map); WP06 closes it as a follow-on data edit. Paired into shard_2
    # (sibling of shard_1's pick above) while shards were still tied at 34
    # files each.
    "tests/architectural/test_workflow_dist_lint.py",
    # Added post-data-model.md (new file at implementation time — data-model.md
    # §"Any tests/architectural/*.py file not listed above ... is an
    # assignment gap the completeness guard must catch"). shard_2 was the
    # lightest by file count (29 vs 30/30) at the time this WP was
    # implemented, so it lands here.
    "tests/architectural/test_arch_shard_marker_completeness.py",
    # Added post-data-model.md (new file, mission
    # coord-authority-trio-degod-01KX7094 WP05 -- the trio seam-only +
    # cores-no-I/O gates, FR-004/FR-007). shard_2 was the lightest by file
    # count (32 vs 33/34) when this file landed, so it lands here.
    "tests/architectural/test_trio_seam_only.py",
    "tests/architectural/test_artifact_selection_completeness.py",
    "tests/architectural/test_charter_runtime_canonical_paths.py",
    "tests/architectural/test_commit_target_kind_guard.py",
    "tests/architectural/test_coord_read_residuals_closeout.py",
    "tests/architectural/test_coverage_consumer_needs.py",
    "tests/architectural/test_execution_context_parity.py",
    "tests/architectural/test_gate_coverage.py",
    # Added post-data-model.md (new file, mission mission-resolver-port-01KX1C05
    # WP07 #2447 doctrine-phantom guard). shard_2 was tied lightest by file
    # count (31 vs 33/31) when this file landed, so it lands here.
    "tests/architectural/test_git_matrix_paths_resolve.py",
    # Added post-data-model.md (new file from mission
    # read-surface-ssot-closeout-01KWZV91, the inline meta-read gate). shard_2
    # was the lightest by both file count (30 vs 33/31) and test-fn count
    # (223 vs 287/232) when this file landed, so it lands here.
    "tests/architectural/test_inline_meta_read_gate.py",
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
    # Added post-data-model.md (new file at implementation time, mission
    # content-address-ratchet-allowlists-01KX8M4D WP05, #2469/#2495 IC-METAGUARD
    # standing positional-anchor ban). shard_2 was the lightest by file count
    # (32 vs 33/34) when this file landed, so it lands here.
    "tests/architectural/test_ratchet_positional_anchor_ban.py",
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
    # Added post-data-model.md (new file — mission
    # contract-ownership-boundary-01KWYRE5 WP03, #2441). Kept in shard_3
    # alongside its WP02 driver sibling (test_retired_contracts_absent.py) so
    # the content-anchoring parity family runs on one leg; the pick is
    # auditable and the completeness guard verifies the partition stays total.
    "tests/architectural/test_contract_registry_parity.py",
    "tests/architectural/test_docs_scoped_arch_coverage.py",
    "tests/architectural/test_dossier_sync_boundary.py",
    "tests/architectural/test_events_tracker_public_imports.py",
    "tests/architectural/test_gate_coverage_parse_model.py",
    "tests/architectural/test_gate_read_literal_ban.py",
    "tests/architectural/test_guard_capability_call_sites.py",
    "tests/architectural/test_layer_rules.py",
    # Added post-data-model.md (new file at implementation time, mission
    # mission-resolver-port-01KX1C05 WP04, #2173 FR-007). shard_3 was the
    # lightest by def-test_ count (232 vs 287/251) when this file landed.
    "tests/architectural/test_mission_resolver_walker_gate.py",
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
    # Added post-data-model.md (new file — mission
    # contract-ownership-boundary-01KWYRE5 WP02, #2441). shard_3 and shard_2
    # were tied at 30 files each when this landed; shard_3 was picked to keep
    # the driver near its content-anchoring siblings and the pick auditable.
    "tests/architectural/test_retired_contracts_absent.py",
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
_ARCH_FILE_ASSIGNMENT: dict[str, int] = {
    **dict.fromkeys(_ARCH_SHARD_1_FILES, 1),
    **dict.fromkeys(_ARCH_SHARD_2_FILES, 2),
    **dict.fromkeys(_ARCH_SHARD_3_FILES, 3),
}

# ``dirpath -> shard`` for whole-directory (adversarial / architecture / lint)
# units.
_ARCH_DIR_ASSIGNMENT: dict[str, int] = {
    **dict.fromkeys(_ARCH_SHARD_1_DIRS, 1),
    **dict.fromkeys(_ARCH_SHARD_2_DIRS, 2),
    **dict.fromkeys(_ARCH_SHARD_3_DIRS, 3),
}

# The 4 pole roots the ``arch`` group (and the collection hook, for this
# group) is scoped to. Anything outside these roots must never receive an
# ``arch_shard_N`` marker.
_ARCH_POLE_ROOTS: tuple[str, ...] = (
    "tests/adversarial",
    "tests/architectural",
    "tests/architecture",
    "tests/lint",
)


@dataclass(frozen=True)
class ShardGroup:
    """One row of the shard registry (data-model E1).

    ``dir_assignment`` / ``file_assignment`` are kept as two internal maps
    (rather than one merged dict) purely for :func:`shard_for`'s lookup
    efficiency — a handful of whole-directory prefixes checked first, then an
    ``O(1)`` exact-file lookup — mirroring the pre-generalization resolution
    order exactly (byte-stable for ``arch``). :attr:`assignment` is the
    public, merged ``relpath/dirpath -> shard_idx`` view the data model
    describes.
    """

    group: str
    roots: tuple[str, ...]
    shard_count: int
    marker_prefix: str
    dir_assignment: dict[str, int] = field(default_factory=dict)
    file_assignment: dict[str, int] = field(default_factory=dict)

    @property
    def assignment(self) -> dict[str, int]:
        """Merged ``relpath/dirpath -> shard_idx`` map (data-model E1 field)."""
        return {**self.dir_assignment, **self.file_assignment}


# The single-source registry: ``group name -> ShardGroup``. This module owns
# only the ``arch`` row; ``tests/_next_shard_map.py`` registers the sibling
# ``next`` row into this SAME dict at import time (D-044/C-003 — one
# registry, not a cloned second one). ``tests/conftest.py`` imports
# ``_next_shard_map`` (for its registration side effect) alongside this
# module, then iterates :data:`SHARD_GROUPS`, never hardcoding a group name.
SHARD_GROUPS: dict[str, ShardGroup] = {
    "arch": ShardGroup(
        group="arch",
        roots=_ARCH_POLE_ROOTS,
        shard_count=3,
        marker_prefix="arch_shard",
        dir_assignment=_ARCH_DIR_ASSIGNMENT,
        file_assignment=_ARCH_FILE_ASSIGNMENT,
    ),
}


def shard_for(group: str, relpath: str) -> int | None:
    """Return the ``<marker_prefix>_N`` shard number for *relpath* in *group*.

    ``None`` when *group* is not registered, or *relpath* falls outside that
    group's assignment. *relpath* is a repo-root-relative path using ``/``
    separators (as produced by pytest's own nodeid/relpath reporting).
    Resolution order (per group, identical to the pre-generalization
    ``arch``-only behavior):

    1. Whole-directory roots — any path under one of the group's directory
       units resolves to that directory's single shard.
    2. Exact file match in the group's file assignment.
    3. ``None`` for anything outside the group's roots (including non-test
       infra modules such as ``__init__.py`` / ``conftest.py`` / helper
       modules, and any path not covered by the group's assignment at all).
    """
    spec = SHARD_GROUPS.get(group)
    if spec is None:
        return None
    normalized = relpath.replace("\\", "/")
    for dirpath, shard in spec.dir_assignment.items():
        if normalized == dirpath or normalized.startswith(f"{dirpath}/"):
            return shard
    return spec.file_assignment.get(normalized)
