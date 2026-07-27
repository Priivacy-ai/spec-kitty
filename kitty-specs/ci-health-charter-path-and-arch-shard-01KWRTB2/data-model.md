# Phase 1 Data Model: CI Health: Charter-Path Hotfix + Arch-Adversarial Shard

This mission has no application data model. The one structural entity worth
documenting formally is the **arch-pole shard-assignment table** — the single
source of truth `tests/_arch_shard_map.py` introduces (R3 in `research.md`).

## Entity: shard assignment table

| Field | Type | Description |
|-------|------|--------------|
| `unit` | `str` | A test-file relpath (e.g. `tests/architectural/test_layer_rules.py`) or a whole-directory unit (`tests/adversarial`, `tests/architecture`, `tests/lint`), kept whole — never split across shards. |
| `shard` | `int` (1, 2, or 3) | The `arch_shard_N` marker applied to every test collected from that unit. |

**Invariants** (enforced by the new `test_arch_shard_marker_completeness.py`
guard, IC-03):

1. **Total partition** — every test collected under the 4 pole roots
   (`tests/adversarial`, `tests/architectural`, `tests/architecture`,
   `tests/lint`) carries **exactly one** `arch_shard_N` marker. No test is
   unmarked; no test carries more than one.
2. **Union = full pre-split universe** — `arch_shard_1 ∪ arch_shard_2 ∪
   arch_shard_3` (by node ID) equals the full set of tests the single
   pre-split `-m 'not windows_ci and (git_repo or integration or
   architectural)'` selection collected across the 4 roots (FR-005).
3. **No file split across shards** — every unit in the table is a whole file
   or whole directory; a shard's test set is a disjoint union of whole units,
   never a partial file (operator steer: "functional/module-level slicing...
   whole test files kept intact, not split").

### Concrete assignment (Phase 0 bin-packing result — 216 / 215 / 215)

Balanced by a `def test_` count proxy (see `research.md` R2 for the honesty
caveat: this is a structural projection, not a live-duration measurement).
The table is a single editable source, so a post-merge rebalance from real CI
durations is a cheap follow-up if one shard drifts materially from the
others.

**`arch_shard_1`** (216):
`tests/adversarial`,
`tests/architectural/test_arch_unblind_matrix.py`,
`tests/architectural/test_charter_facades_reexport_doctrine.py`,
`tests/architectural/test_charter_references_resolve.py`,
`tests/architectural/test_ci_architectural_gate_coverage.py`,
`tests/architectural/test_ci_topology_worklist.py`,
`tests/architectural/test_compat_shims.py`,
`tests/architectural/test_docs_cli_reference_parity.py`,
`tests/architectural/test_integration_boundary.py`,
`tests/architectural/test_marker_job_completeness.py`,
`tests/architectural/test_marker_registry_single_source.py`,
`tests/architectural/test_no_dead_symbols.py`,
`tests/architectural/test_no_legacy_status_emit_callers.py`,
`tests/architectural/test_no_legacy_terminology.py`,
`tests/architectural/test_no_raw_mission_spec_paths.py`,
`tests/architectural/test_no_tracked_test_feature_missions.py`,
`tests/architectural/test_no_write_side_rederivation.py`,
`tests/architectural/test_quarantine_marker.py`,
`tests/architectural/test_resolution_authority_gates.py`,
`tests/architectural/test_runtime_charter_doctrine_boundary.py`,
`tests/architectural/test_shard_universe_bounded.py`,
`tests/architectural/test_shared_package_boundary.py`,
`tests/architectural/test_single_mission_surface_resolver.py`,
`tests/architectural/test_src_filter_coverage.py`,
`tests/architectural/test_status_module_boundary.py`,
`tests/architectural/test_topology_inference_retired.py`,
`tests/architectural/test_topology_resolution_boundary.py`,
`tests/architectural/test_unregistered_shim_scanner.py`,
`tests/architectural/test_uv_lock_pin_drift.py`,
`tests/architectural/test_workflow_coherence.py`,
`tests/architectural/test_wp_owned_files_no_kitty_specs.py`.

**`arch_shard_2`** (215):
`tests/architectural/test_artifact_selection_completeness.py`,
`tests/architectural/test_charter_runtime_canonical_paths.py`,
`tests/architectural/test_commit_target_kind_guard.py`,
`tests/architectural/test_coord_read_residuals_closeout.py`,
`tests/architectural/test_coverage_consumer_needs.py`,
`tests/architectural/test_execution_context_parity.py`,
`tests/architectural/test_gate_coverage.py`,
`tests/architectural/test_job_count_ceiling.py`,
`tests/architectural/test_merge_pipeline_ratchets.py`,
`tests/architectural/test_migration_chain_integrity.py`,
`tests/architectural/test_mission_runtime_surface.py`,
`tests/architectural/test_no_op_stable_writes.py`,
`tests/architectural/test_no_phantom_worktree_repair.py`,
`tests/architectural/test_no_runtime_pypi_dep.py`,
`tests/architectural/test_org_activation_seam.py`,
`tests/architectural/test_plugin_validate_workflow.py`,
`tests/architectural/test_pyproject_shape.py`,
`tests/architectural/test_pytest_marker_convention.py`,
`tests/architectural/test_ratchet_baselines.py`,
`tests/architectural/test_status_sync_boundary.py`,
`tests/architectural/test_surface_resolution_audit.py`,
`tests/architectural/test_tasks_command_surface.py`,
`tests/architectural/test_tid251_enforcement.py`,
`tests/architectural/test_trigger_registry_coverage.py`,
`tests/architectural/test_typer_compat_ci.py`,
`tests/architectural/test_untrusted_path_containment.py`,
`tests/architectural/test_wp05_write_target_drain.py`,
`tests/architectural/test_wp_prompt_build_latency.py`,
`tests/architectural/test_write_surface_placement_guard.py`,
`tests/lint`.

**`arch_shard_3`** (215):
`tests/architectural/test_activation_registry_schema.py`,
`tests/architectural/test_all_declarations_required.py`,
`tests/architectural/test_arch_pole_deserialized.py`,
`tests/architectural/test_auth_transport_singleton.py`,
`tests/architectural/test_builtin_override_policy.py`,
`tests/architectural/test_ci_quality_path_filters.py`,
`tests/architectural/test_docs_scoped_arch_coverage.py`,
`tests/architectural/test_dossier_sync_boundary.py`,
`tests/architectural/test_events_tracker_public_imports.py`,
`tests/architectural/test_gate_coverage_parse_model.py`,
`tests/architectural/test_gate_read_literal_ban.py`,
`tests/architectural/test_guard_capability_call_sites.py`,
`tests/architectural/test_layer_rules.py`,
`tests/architectural/test_no_dead_modules.py`,
`tests/architectural/test_no_primary_anchored_gates.py`,
`tests/architectural/test_no_prompt_filtering_added.py`,
`tests/architectural/test_no_shipped_layer_label.py`,
`tests/architectural/test_no_tmp_paths_in_tests.py`,
`tests/architectural/test_no_worktree_name_guess.py`,
`tests/architectural/test_protection_resolver_call_sites.py`,
`tests/architectural/test_pytest_marker_correctness.py`,
`tests/architectural/test_real_home_isolation_guard.py`,
`tests/architectural/test_safe_commit_import_boundary.py`,
`tests/architectural/test_safety_registry_completeness.py`,
`tests/architectural/test_same_tier_uniqueness.py`,
`tests/architectural/test_serial_port_preservation.py`,
`tests/architectural/test_shim_registry_schema.py`,
`tests/architectural/test_tasks_domain_gate_visibility.py`,
`tests/architectural/test_template_governance_payload_contract.py`,
`tests/architectural/test_worktrees_index_clean.py`,
`tests/architecture`.

Any `tests/architectural/*.py` file not listed above and not one of the
non-test infra modules (`__init__.py`, `conftest.py`, `_gate_coverage.py`,
`_gate_collect_plugin.py`, `_ratchet_keys.py`) that exists at implementation
time (new file added between planning and implementation) is an **assignment
gap** the completeness guard (IC-03) must catch — the implementer adds it to
whichever shard is lightest at that time.
