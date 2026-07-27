# Golden-count inventory (WP11, #2076/FR-014)

Generated 2026-07-13T15:31:39+00:00 by `python -m tests.architectural.test_golden_count_ban --emit-inventory`. Classification heuristic: see `tests/architectural/test_golden_count_ban.py` module docstring.

- Total `len(<collection>) == <int>` sites scanned: **2034**
- `keep` (cardinality is the contract): **1030**
- `convert` (set/frozenset-equality is the real contract), non-escaped: **1004**
- escaped via `# golden-count: cardinality-is-contract`: **0**

## Partition 1 -- batch-owned (WP12/WP13/WP14 burn these down)

### WP12 (160 convert sites across 4 directories)

#### `tests/charter` (61)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/charter/synthesizer/test_evidence.py` | 221 | `test_all_dataclasses_are_hashable` | `len(d) == 4` |
| `tests/charter/synthesizer/test_evidence.py` | 225 | `test_all_dataclasses_are_hashable` | `len(s) == 4` |
| `tests/charter/synthesizer/test_interview_mapping.py` | 418 | `TestResolveFullSnapshot.test_return_type_is_list_of_tuples` | `len(item) == 2` |
| `tests/charter/synthesizer/test_manifest.py` | 173 | `test_manifest_round_trip` | `len(loaded.manifest_hash) == 64` |
| `tests/charter/synthesizer/test_manifest.py` | 174 | `test_manifest_round_trip` | `len(loaded.artifacts) == 1` |
| `tests/charter/synthesizer/test_manifest.py` | 510 | `test_manifest_artifact_ordering` | `len(loaded.artifacts) == 3` |
| `tests/charter/synthesizer/test_project_drg.py` | 81 | `TestEmitProjectLayer.test_single_directive_target_produces_one_node` | `len(graph.nodes) == 1` |
| `tests/charter/synthesizer/test_project_drg.py` | 94 | `TestEmitProjectLayer.test_tactic_target_produces_tactic_node` | `len(graph.nodes) == 1` |
| `tests/charter/synthesizer/test_project_drg.py` | 153 | `TestEmitProjectLayer.test_multiple_targets_produce_multiple_nodes` | `len(graph.nodes) == 2` |
| `tests/charter/synthesizer/test_project_drg.py` | 174 | `TestEdgeDerivedFromSourceUrns.test_directive_source_urn_produces_requires_edge` | `len(graph.edges) == 1` |
| `tests/charter/synthesizer/test_project_drg.py` | 192 | `TestEdgeDerivedFromSourceUrns.test_tactic_source_urn_produces_applies_edge` | `len(graph.edges) == 1` |
| `tests/charter/synthesizer/test_project_drg.py` | 209 | `TestEdgeDerivedFromSourceUrns.test_multiple_source_urns_produce_multiple_edges` | `len(graph.edges) == 2` |
| `tests/charter/synthesizer/test_project_drg.py` | 300 | `TestAdditiveOnlyEnforcement.test_disjoint_urns_succeed` | `len(graph.nodes) == 1` |
| `tests/charter/synthesizer/test_project_drg.py` | 329 | `TestPersistRoundTrip.test_persisted_graph_roundtrips_via_load_graph` | `len(loaded.nodes) == 1` |
| `tests/charter/synthesizer/test_staging_atomicity.py` | 249 | `test_promote_success_writes_files_and_manifest` | `len(loaded.artifacts) == 1` |
| `tests/charter/test_activation_filtered_drg.py` | 314 | `test_org_pack_loader_resolves_legacy_mission_step_contracts_alias` | `len(fragment.nodes) == 1` |
| `tests/charter/test_activations.py` | 216 | `test_allowed_actions_is_the_canonical_10_token_set` | `len(ALLOWED_ACTIONS) == 10` |
| `tests/charter/test_bundle_manifest_model.py` | 28 | `test_canonical_manifest_has_exactly_three_derived_files` | `len(CANONICAL_MANIFEST.derived_files) == 3` |
| `tests/charter/test_bundle_validate_cli.py` | 106 | `_add_synthesis_manifest` | `len(parts) == 2` |
| `tests/charter/test_cascade.py` | 273 | `test_deactivation_removes_exclusive_skips_shared_diamond` | `len(plan.skipped_shared) == 1` |
| `tests/charter/test_charter_ownership_invariant.py` | 109 | `test_charter_ownership_invariant` | `len(found) == 1` |
| `tests/charter/test_charter_scope.py` | 169 | `test_charter_scope_config_accepts_valid_payload` | `len(model.charter_scopes) == 2` |
| `tests/charter/test_compiler.py` | 460 | `test_charter_interview_from_dict_parses_local_supporting_files` | `len(interview.local_supporting_files) == 1` |
| `tests/charter/test_compiler.py` | 552 | `test_validate_accepts_valid_explicit_path` | `len(valid) == 1` |
| `tests/charter/test_compiler.py` | 559 | `test_validate_normalizes_unknown_action_to_none` | `len(valid) == 1` |
| `tests/charter/test_compiler.py` | 580 | `test_validate_mixed_valid_and_invalid` | `len(valid) == 1` |
| `tests/charter/test_compiler.py` | 597 | `test_compile_with_local_support_file_creates_local_reference` | `len(local_refs) == 1` |
| `tests/charter/test_compiler.py` | 622 | `test_compile_local_support_reference_is_additive_not_replacement` | `len(local_refs) == 1` |
| `tests/charter/test_compiler.py` | 569 | `test_validate_accepts_known_actions` | `len(valid) == 1` |
| `tests/charter/test_config_stem_parity.py` | 121 | `test_config_declares_exactly_the_expected_directive_count` | `len(activated_directive_stems) == 25` |
| `tests/charter/test_context_catalog_miss.py` | 282 | `TestEmitCatalogMissWarning.test_logger_extra_carries_structured_fields` | `len(relevant) == 1` |
| `tests/charter/test_context_catalog_miss.py` | 333 | `TestRendererIntegration.test_typo_case_renders_suggestion_and_warns` | `len(miss) == 1` |
| `tests/charter/test_context_catalog_miss.py` | 362 | `TestRendererIntegration.test_missing_artifact_case_renders_dual_hint_and_warns` | `len(miss) == 1` |
| `tests/charter/test_context_catalog_miss.py` | 389 | `TestRendererIntegration.test_schema_failure_case_surfaces_validate_hint` | `len(miss) == 1` |
| `tests/charter/test_context_catalog_miss.py` | 444 | `TestProfileRendererIntegration.test_profile_cited_directive_miss_warns_with_profile_context` | `len(miss) == 1` |
| `tests/charter/test_context_catalog_miss.py` | 520 | `TestScopeFilteredRendererIntegration.test_scope_filtered_styleguide_renders_scope_filtered_cause` | `len(miss) == 1` |
| `tests/charter/test_context_token_budget.py` | 127 | `TestOverBudgetSubstitution.test_severely_over_budget_substitutes_all_bodies` | `len(notes) == 3` |
| `tests/charter/test_context_token_budget.py` | 195 | `TestWarningLine.test_warning_line_counts_against_budget_after_substitution` | `len(notes) == 2` |
| `tests/charter/test_context_token_budget.py` | 283 | `TestFetchStanzaContract.test_fetch_stanza_helper_matches_contract` | `len(lines) == 2` |
| `tests/charter/test_extractor_activations.py` | 221 | `test_activations_round_trips_through_governance_config_model_validate` | `len(reloaded.activations) == 1` |
| `tests/charter/test_governance_references.py` | 24 | `test_collect_governance_references_reports_missing_doc` | `len(statuses) == 1` |
| `tests/charter/test_governance_references.py` | 37 | `test_collect_governance_references_rejects_escape` | `len(statuses) == 1` |
| `tests/charter/test_governance_references.py` | 57 | `test_collect_governance_references_rejects_absolute_path` | `len(statuses) == 1` |
| `tests/charter/test_governance_references.py` | 70 | `test_collect_governance_references_reports_directory` | `len(statuses) == 1` |
| `tests/charter/test_governance_references.py` | 91 | `test_collect_governance_references_rejects_symlink_escape` | `len(statuses) == 1` |
| `tests/charter/test_integration.py` | 72 | `TestEndToEndWorkflow.test_write_sync_load_directives` | `len(config.directives) == 2` |
| `tests/charter/test_integration.py` | 234 | `TestLoaderFunctions.test_load_directives_config_missing_yaml_auto_syncs_when_charter_present` | `len(config.directives) == 2` |
| `tests/charter/test_integration.py` | 446 | `TestPerformance.test_load_directives_config_performance` | `len(config.directives) == 2` |
| `tests/charter/test_org_drg_edge_source_urn_preserved.py` | 72 | `TestShippedEdgeSourceUrnPreservedAfterMerge.test_shipped_edge_source_urn_preserved_after_merge` | `len(merged.edges) == 1` |
| `tests/charter/test_org_drg_edge_source_urn_preserved.py` | 135 | `TestOrgBridgeEdgeSourceUrnPreserved.test_org_bridge_edge_source_urn_is_a_urn` | `len(org_edges) == 1` |
| `tests/charter/test_org_drg_loader.py` | 311 | `TestLoadOrgDrg.test_relative_path_resolved_against_repo_root` | `len(fragments) == 1` |
| `tests/charter/test_org_drg_loader.py` | 532 | `TestMergeThreeLayers.test_org_edge_tagged_with_pack_name` | `len(org_edges) == 1` |
| `tests/charter/test_org_drg_loader.py` | 566 | `TestMergeThreeLayers.test_org_to_shipped_edge_targets_synthesized_urn` | `len(cross_edges) == 1` |
| `tests/charter/test_pack_context.py` | 191 | `test_activated_kinds_defaults_to_all_builtin_when_key_absent` | `len(ctx.activated_kinds) == 10` |
| `tests/charter/test_pack_context.py` | 238 | `test_org_pack_names_and_roots_populated` | `len(ctx.pack_roots) == 2` |
| `tests/charter/test_pack_manager.py` | 61 | `TestYamlKeyMap.test_has_exactly_nine_entries` | `len(YAML_KEY_MAP) == 9` |
| `tests/charter/test_parser.py` | 262 | `TestCharterParser.test_section_integration_with_table` | `len(section.structured_data['tables']) == 1` |
| `tests/charter/test_phase3_integration.py` | 95 | `test_phase3_evidence_bundle_structure` | `len(bundle.url_list) == 2` |
| `tests/charter/test_phase3_integration.py` | 100 | `test_phase3_evidence_bundle_structure` | `len(bundle.corpus_snapshot.entries) == 1` |
| `tests/charter/test_project_layer_override_emits_warning.py` | 92 | `TestProjectNodeOverridesShippedAndEmitsWarning.test_project_node_overrides_shipped_node` | `len(matching) == 1` |
| `tests/charter/test_project_layer_override_emits_warning.py` | 142 | `TestProjectNodeOverridesOrgAndEmitsWarning.test_project_node_overrides_org_node` | `len(matching) == 1` |

#### `tests/doctrine` (73)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/doctrine/directives/test_models.py` | 53 | `TestDirective.test_enriched_construction` | `len(directive.procedures) == 2` |
| `tests/doctrine/directives/test_models.py` | 54 | `TestDirective.test_enriched_construction` | `len(directive.references) == 1` |
| `tests/doctrine/directives/test_models.py` | 57 | `TestDirective.test_enriched_construction` | `len(directive.integrity_rules) == 1` |
| `tests/doctrine/directives/test_models.py` | 58 | `TestDirective.test_enriched_construction` | `len(directive.validation_criteria) == 1` |
| `tests/doctrine/directives/test_models.py` | 59 | `TestDirective.test_enriched_construction` | `len(directive.explicit_allowances) == 1` |
| `tests/doctrine/directives/test_repository.py` | 18 | `TestDirectiveRepository.test_list_all_from_shipped` | `len(directives) == 1` |
| `tests/doctrine/directives/test_repository.py` | 50 | `TestDirectiveRepository.test_load_from_custom_shipped_dir` | `len(directives) == 1` |
| `tests/doctrine/drg/migration/test_extractor.py` | 188 | `TestExtractArtifactEdges.test_directive_opposed_by_produces_replaces` | `len(d024_replaces) == 1` |
| `tests/doctrine/drg/migration/test_extractor.py` | 368 | `TestExtractActionEdges.test_empty_lists_produce_no_edges` | `len(specify_edges) == 3` |
| `tests/doctrine/drg/migration/test_extractor.py` | 407 | `TestExtractActionEdges.test_tasks_action_has_seven_refs` | `len(tasks_edges) == 7` |
| `tests/doctrine/drg/migration/test_path_ref_resolver.py` | 172 | `test_path_kind_patterns_count` | `len(_PATH_KIND_PATTERNS) == 7` |
| `tests/doctrine/drg/test_kind_mapping_totality.py` | 110 | `_dict_target_and_value` | `len(stmt.targets) == 1` |
| `tests/doctrine/drg/test_loader_multifile.py` | 120 | `test_directory_multiple_fragments` | `len(graph.edges) == 1` |
| `tests/doctrine/drg/test_org_pack_auto_emit.py` | 162 | `test_auto_emit_deduplicates_hand_authored_edge` | `len(matching) == 1` |
| `tests/doctrine/mission_step_contracts/test_repository.py` | 17 | `TestMissionStepContractRepository.test_list_all_from_shipped` | `len(contracts) == 1` |
| `tests/doctrine/paradigms/test_repository.py` | 18 | `TestParadigmRepository.test_list_all_from_shipped` | `len(paradigms) == 1` |
| `tests/doctrine/paradigms/test_repository.py` | 34 | `TestParadigmRepository.test_load_from_custom_shipped_dir` | `len(paradigms) == 1` |
| `tests/doctrine/procedures/test_models.py` | 36 | `TestProcedureModel.test_enriched_procedure` | `len(p.references) == 2` |
| `tests/doctrine/procedures/test_repository.py` | 25 | `TestProcedureRepository.test_list_all_from_shipped` | `len(procedures) == 1` |
| `tests/doctrine/styleguides/test_models.py` | 49 | `TestStyleguide.test_minimal_construction` | `len(sg.principles) == 1` |
| `tests/doctrine/styleguides/test_models.py` | 57 | `TestStyleguide.test_enriched_construction` | `len(sg.principles) == 2` |
| `tests/doctrine/styleguides/test_models.py` | 58 | `TestStyleguide.test_enriched_construction` | `len(sg.anti_patterns) == 1` |
| `tests/doctrine/styleguides/test_models.py` | 61 | `TestStyleguide.test_enriched_construction` | `len(sg.references) == 1` |
| `tests/doctrine/styleguides/test_repository.py` | 19 | `TestStyleguideRepository.test_list_all_from_shipped` | `len(styleguides) == 1` |
| `tests/doctrine/styleguides/test_repository.py` | 64 | `TestStyleguideRepository.test_load_from_custom_shipped_dir` | `len(styleguides) == 1` |
| `tests/doctrine/tactics/test_models.py` | 87 | `TestTactic.test_enriched_construction` | `len(tactic.references) == 1` |
| `tests/doctrine/tactics/test_repository.py` | 18 | `TestTacticRepository.test_list_all_from_shipped` | `len(tactics) == 1` |
| `tests/doctrine/tactics/test_repository.py` | 36 | `TestTacticRepository.test_load_from_custom_shipped_dir` | `len(tactics) == 1` |
| `tests/doctrine/test_activation_parity_guard.py` | 325 | `test_org_overlay_activated_artefact_resolves_for_parity` | `len(ctx.pack_context.pack_roots) == 2` |
| `tests/doctrine/test_base_org_layer.py` | 420 | `TestDoctrineLayerCollisionWarning.test_org_shadows_builtin_emits_warning` | `len(collision_msgs) == 1` |
| `tests/doctrine/test_drg_merge.py` | 205 | `TestSpecializesFromAndUnknownRelation.test_org_specializes_from_edge_appears_in_merged_graph` | `len(lineage_edges) == 1` |
| `tests/doctrine/test_drg_merge.py` | 246 | `TestSpecializesFromAndUnknownRelation.test_org_refines_relation_is_preserved` | `len(merged.edges) == 1` |
| `tests/doctrine/test_drg_merge.py` | 263 | `TestSpecializesFromAndUnknownRelation.test_org_extends_relation_maps_to_lineage_not_applies` | `len(merged.edges) == 1` |
| `tests/doctrine/test_drg_merge.py` | 284 | `TestSpecializesFromAndUnknownRelation.test_bridge_preserves_every_canonical_relation_verbatim` | `len(merged.edges) == 1` |
| `tests/doctrine/test_drg_merge.py` | 515 | `TestInvariantsPreserved.test_same_kind_org_override_records_org_override_conflict` | `len(conflicts) == 1` |
| `tests/doctrine/test_drg_relations.py` | 82 | `test_edges_to_returns_incoming_edges` | `len(incoming) == 1` |
| `tests/doctrine/test_drg_relations.py` | 117 | `test_edges_to_relation_filter` | `len(graph.edges_to('agent_profile:parent')) == 2` |
| `tests/doctrine/test_generic_agent_profile.py` | 35 | `test_generic_agent_references_directive_028` | `len(directive_codes) == 1` |
| `tests/doctrine/test_org_pack_subdir.py` | 310 | `TestResolveOrgRoots.test_no_subdir_pack_returns_resolved_local_path` | `len(roots) == 1` |
| `tests/doctrine/test_org_pack_subdir.py` | 321 | `TestResolveOrgRoots.test_subdir_pack_returns_joined_effective_root` | `len(roots) == 1` |
| `tests/doctrine/test_org_pack_subdir.py` | 345 | `TestResolveOrgRoots.test_multiple_packs_mixed_subdir` | `len(roots) == 2` |
| `tests/doctrine/test_org_pack_subdir.py` | 368 | `TestRoundTrip.test_subdir_preserved_in_round_trip` | `len(loaded.packs) == 1` |
| `tests/doctrine/test_org_pack_subdir.py` | 405 | `TestRoundTrip.test_legacy_single_pack_shape_carries_subdir` | `len(loaded.packs) == 1` |
| `tests/doctrine/test_org_pack_subdir.py` | 579 | `TestEnvVarExpansion.test_round_trip_preserves_env_var_template` | `len(loaded.packs) == 1` |
| `tests/doctrine/test_profile_diagnostics.py` | 90 | `TestSkippedDiagnostics.test_invalid_profile_recorded_with_all_fields` | `len(skipped) == 1` |
| `tests/doctrine/test_profile_diagnostics.py` | 109 | `TestSkippedDiagnostics.test_missing_profile_id_recorded` | `len(skipped) == 1` |
| `tests/doctrine/test_profile_diagnostics.py` | 129 | `TestSkippedDiagnostics.test_list_all_is_valid_only` | `len(repo.skipped_profiles()) == 1` |
| `tests/doctrine/test_profile_inheritance.py` | 311 | `test_list_fields_merged_by_union` | `len(directive_codes) == 3` |
| `tests/doctrine/test_profile_inheritance.py` | 318 | `test_list_fields_merged_by_union` | `len(cap_names) == 3` |
| `tests/doctrine/test_profile_model.py` | 116 | `TestAgentProfileOne.test_full_profile_creation` | `len(profile.capabilities) == 5` |
| `tests/doctrine/test_profile_model.py` | 118 | `TestAgentProfileOne.test_full_profile_creation` | `len(profile.collaboration.handoff_to) == 2` |
| `tests/doctrine/test_profile_model.py` | 119 | `TestAgentProfileOne.test_full_profile_creation` | `len(profile.mode_defaults) == 1` |
| `tests/doctrine/test_profile_model.py` | 121 | `TestAgentProfileOne.test_full_profile_creation` | `len(profile.specialization_context.languages) == 2` |
| `tests/doctrine/test_profile_model.py` | 151 | `TestAgentProfileMany.test_multiple_profiles_different_roles` | `len(profiles) == 8` |
| `tests/doctrine/test_profile_model.py` | 429 | `TestTaskContext.test_task_context_full` | `len(ctx.file_paths) == 1` |
| `tests/doctrine/test_profile_repository.py` | 231 | `TestAgentProfileRepositoryOne.test_load_single_shipped_profile` | `len(profiles) == 3` |
| `tests/doctrine/test_profile_repository.py` | 255 | `TestAgentProfileRepositoryMany.test_load_multiple_shipped_profiles` | `len(profiles) == 3` |
| `tests/doctrine/test_profile_repository.py` | 268 | `TestAgentProfileRepositoryMany.test_load_shipped_and_project_profiles` | `len(profiles) == 4` |
| `tests/doctrine/test_profile_repository.py` | 467 | `TestAgentProfileRepositoryExceptions.test_invalid_yaml_skipped_with_warning` | `len(repo.list_all()) == 3` |
| `tests/doctrine/test_profile_repository.py` | 538 | `TestAgentProfileRepositorySimple.test_find_by_role_enum` | `len(implementers) == 2` |
| `tests/doctrine/test_profile_repository.py` | 546 | `TestAgentProfileRepositorySimple.test_find_by_role_string` | `len(implementers) == 2` |
| `tests/doctrine/test_profile_repository.py` | 563 | `TestAgentProfileRepositoryHierarchy.test_get_children` | `len(children) == 1` |
| `tests/doctrine/test_profile_repository.py` | 842 | `TestAgentProfileRepositoryLoader.test_skip_recorded_once_per_invalid_shipped_file` | `len(builtin_skips) == 1` |
| `tests/doctrine/test_role_value_object.py` | 123 | `TestAgentProfileModel.test_scalar_role_coerces_to_list_with_warning` | `len(w) == 1` |
| `tests/doctrine/test_service.py` | 76 | `test_service_loads_all_repositories_from_built_in_defaults` | `len(service.directives.list_all()) == 1` |
| `tests/doctrine/test_spdd_reasons_artifacts.py` | 96 | `test_directive_038_lenient_adherence_with_four_allowances` | `len(allowances) == 4` |
| `tests/doctrine/test_template_discovery.py` | 94 | `test_discovery_disambiguates_same_name_across_missions` | `len(spec_refs) == 2` |
| `tests/doctrine/test_template_discovery.py` | 98 | `test_discovery_disambiguates_same_name_across_missions` | `len({r.template_id for r in spec_refs}) == 2` |
| `tests/doctrine/test_template_discovery.py` | 114 | `test_discovery_dedupes_multi_tier_to_highest_precedence` | `len(spec_sw) == 1` |
| `tests/doctrine/test_template_discovery.py` | 165 | `test_cross_mission_nodes_are_distinct` | `len(urns) == 2` |
| `tests/doctrine/toolguides/test_models.py` | 21 | `TestToolguide.test_enriched_construction` | `len(toolguide.commands) == 2` |
| `tests/doctrine/toolguides/test_repository.py` | 18 | `TestToolguideRepository.test_list_all_from_shipped` | `len(toolguides) == 1` |
| `tests/doctrine/toolguides/test_repository.py` | 34 | `TestToolguideRepository.test_load_from_custom_shipped_dir` | `len(toolguides) == 1` |

#### `tests/doctrine_synthesizer` (10)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/doctrine_synthesizer/test_apply.py` | 865 | `TestAddEdgeExisting.test_add_edge_appends_to_existing` | `len(loaded) == 2` |
| `tests/doctrine_synthesizer/test_conflict_failclosed.py` | 199 | `TestDetectConflictsDirect.test_p1_add_vs_remove_same_edge` | `len(groups) == 1` |
| `tests/doctrine_synthesizer/test_conflict_failclosed.py` | 228 | `TestDetectConflictsDirect.test_p2_add_vs_rewire_destination_conflict` | `len(groups) == 1` |
| `tests/doctrine_synthesizer/test_conflict_failclosed.py` | 247 | `TestDetectConflictsDirect.test_p3_remove_vs_rewire_source_conflict` | `len(groups) == 1` |
| `tests/doctrine_synthesizer/test_conflict_failclosed.py` | 265 | `TestDetectConflictsDirect.test_p4_add_gloss_same_key_different_hash` | `len(groups) == 1` |
| `tests/doctrine_synthesizer/test_conflict_failclosed.py` | 292 | `TestDetectConflictsDirect.test_p5_update_gloss_same_key_different_hash` | `len(groups) == 1` |
| `tests/doctrine_synthesizer/test_conflict_failclosed.py` | 310 | `TestDetectConflictsDirect.test_p6a_synthesize_directive_conflict` | `len(groups) == 1` |
| `tests/doctrine_synthesizer/test_conflict_failclosed.py` | 336 | `TestDetectConflictsDirect.test_p6b_synthesize_tactic_conflict` | `len(groups) == 1` |
| `tests/doctrine_synthesizer/test_conflict_failclosed.py` | 346 | `TestDetectConflictsDirect.test_p6c_synthesize_procedure_conflict` | `len(groups) == 1` |
| `tests/doctrine_synthesizer/test_conflict_failclosed.py` | 380 | `TestDetectConflictsDirect.test_multiple_conflicts_in_one_batch` | `len(groups) == 2` |

#### `tests/glossary` (16)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/glossary/test_drg_builder.py` | 94 | `test_glossary_urn_prefix` | `len(hex_part) == 8` |
| `tests/glossary/test_drg_builder.py` | 277 | `test_build_index_senses_list_populated` | `len(index.surface_to_senses['lane']) == 1` |
| `tests/glossary/test_entity_pages.py` | 164 | `test_generate_all_three_terms` | `len(written) == 3` |
| `tests/glossary/test_entity_pages.py` | 204 | `test_generate_all_idempotent` | `len(md_files) == 3` |
| `tests/glossary/test_entity_pages.py` | 271 | `test_generate_all_500_terms_under_10_seconds` | `len(written) == 500` |
| `tests/glossary/test_entity_pages.py` | 334 | `test_conflict_history_missing_dir_no_raise` | `len(written) == 3` |
| `tests/glossary/test_observation.py` | 91 | `test_high_severity_returns_notice` | `len(notices) == 1` |
| `tests/glossary/test_observation.py` | 106 | `test_critical_severity_returns_notice` | `len(notices) == 1` |
| `tests/glossary/test_observation.py` | 145 | `test_multiple_terms_multiple_notices` | `len(notices) == 2` |
| `tests/glossary/test_observation.py` | 172 | `test_same_term_deduplicated_last_seen_wins` | `len(notices) == 1` |
| `tests/glossary/test_observation.py` | 206 | `test_malformed_json_line_skipped` | `len(notices) == 1` |
| `tests/glossary/test_observation.py` | 226 | `test_invocation_id_filter` | `len(notices_001) == 2` |
| `tests/glossary/test_observation.py` | 230 | `test_invocation_id_filter` | `len(notices_002) == 1` |
| `tests/glossary/test_scope.py` | 167 | `TestLoadSeedFile.test_valid_file_loads_senses` | `len(senses) == 2` |
| `tests/glossary/test_scope.py` | 275 | `TestSaveSeedFile.test_roundtrip` | `len(loaded) == 1` |
| `tests/glossary/test_seed_schema.py` | 203 | `TestGlossarySeedFileValid.test_valid_file_with_terms` | `len(seed.terms) == 2` |

### WP13 (106 convert sites across 9 directories)

#### `tests/upgrade` (31)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/upgrade/migrations/test_m_0_12_1_remove_kitty_specs_from_gitignore.py` | 63 | `TestFindBlockingEntries.test_finds_blocking_entries` | `len(entries) == 1` |
| `tests/upgrade/migrations/test_m_0_12_1_remove_kitty_specs_from_gitignore.py` | 74 | `TestFindBlockingEntries.test_finds_multiple_blocking_entries` | `len(entries) == 2` |
| `tests/upgrade/migrations/test_m_0_12_1_remove_kitty_specs_from_gitignore.py` | 264 | `TestRealWorldScenarios.test_user_reported_scenario` | `len(entries) == 1` |
| `tests/upgrade/migrations/test_m_2_0_6_consistency_sweep.py` | 134 | `test_apply_repairs_feature_state_and_legacy_prompt_refs` | `len(backup_files) == 1` |
| `tests/upgrade/test_m_3_2_0rc35_default_charter_pack.py` | 225 | `test_apply_creates_backup_when_charter_md_exists` | `len(backup_files) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 359 | `TestExecuteMigration.test_mixed_dispositions` | `len(report.removed) == 2` |
| `tests/upgrade/test_migrate_integration.py` | 360 | `TestExecuteMigration.test_mixed_dispositions` | `len(report.moved) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 361 | `TestExecuteMigration.test_mixed_dispositions` | `len(report.kept) == 2` |
| `tests/upgrade/test_migrate_integration.py` | 362 | `TestExecuteMigration.test_mixed_dispositions` | `len(report.unknown) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 382 | `TestExecuteMigration.test_actual_execution_removes_identical` | `len(report.removed) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 409 | `TestExecuteMigration.test_actual_execution_moves_customized_to_overrides` | `len(report.moved) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 489 | `TestMigrateDryRun.test_dry_run_no_filesystem_changes` | `len(report.removed) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 490 | `TestMigrateDryRun.test_dry_run_no_filesystem_changes` | `len(report.moved) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 491 | `TestMigrateDryRun.test_dry_run_no_filesystem_changes` | `len(report.kept) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 532 | `TestMigrateIdempotent.test_migrate_idempotent` | `len(report1.removed) == 2` |
| `tests/upgrade/test_migrate_integration.py` | 533 | `TestMigrateIdempotent.test_migrate_idempotent` | `len(report1.moved) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 604 | `TestCustomizedFilesMovedToOverrides.test_customized_files_moved_to_overrides` | `len(report.moved) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 639 | `TestCustomizedFilesMovedToOverrides.test_multiple_customized_files_preserve_hierarchy` | `len(report.moved) == 3` |
| `tests/upgrade/test_migrate_integration.py` | 678 | `TestCustomizedFilesMovedToOverrides.test_outdated_agents_md_superseded` | `len(report.superseded) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 706 | `TestCustomizedFilesMovedToOverrides.test_mix_of_identical_customized_and_superseded` | `len(report.removed) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 710 | `TestCustomizedFilesMovedToOverrides.test_mix_of_identical_customized_and_superseded` | `len(report.superseded) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 714 | `TestCustomizedFilesMovedToOverrides.test_mix_of_identical_customized_and_superseded` | `len(report.moved) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 719 | `TestCustomizedFilesMovedToOverrides.test_mix_of_identical_customized_and_superseded` | `len(report.kept) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 889 | `TestExecuteMigrationSuperseded.test_superseded_files_removed_not_moved_to_overrides` | `len(report.superseded) == 2` |
| `tests/upgrade/test_migrate_integration.py` | 921 | `TestExecuteMigrationSuperseded.test_genuine_customization_still_moved_to_overrides` | `len(report.moved) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 961 | `TestExecuteMigrationSuperseded.test_version_skew_scenario_end_to_end` | `len(report.superseded) == 2` |
| `tests/upgrade/test_migrate_integration.py` | 999 | `TestExecuteMigrationSuperseded.test_superseded_count_in_report` | `len(report.removed) == 1` |
| `tests/upgrade/test_migrate_integration.py` | 1000 | `TestExecuteMigrationSuperseded.test_superseded_count_in_report` | `len(report.superseded) == 1` |
| `tests/upgrade/test_runner_status_classification.py` | 272 | `test_record_migration_is_idempotent_for_identical_records` | `len([m for m in metadata.applied_migrations if m.id == '9.9.9_not_needed']) == 1` |
| `tests/upgrade/test_runner_status_classification.py` | 310 | `test_repeated_not_needed_upgrade_does_not_grow_applied_migrations` | `len(skipped) == 1` |
| `tests/upgrade/test_runner_status_classification.py` | 346 | `test_worktree_skipped_migration_keeps_last_upgraded_at_stable_on_rerun` | `len(skipped) == 1` |

#### `tests/dossier` (46)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/dossier/test_determinism.py` | 126 | `TestHashReproducibility.test_hash_file_reproducibility_10_runs` | `len(set(hashes)) == 1` |
| `tests/dossier/test_determinism.py` | 127 | `TestHashReproducibility.test_hash_file_reproducibility_10_runs` | `len(hashes[0]) == 64` |
| `tests/dossier/test_determinism.py` | 176 | `TestHashReproducibility.test_snapshot_reproducibility_multiple_runs` | `len(unique_hashes) == 1` |
| `tests/dossier/test_determinism.py` | 382 | `TestUTF8Handling.test_utf8_emoji` | `len(hash_val) == 64` |
| `tests/dossier/test_determinism.py` | 393 | `TestUTF8Handling.test_utf8_mixed_scripts` | `len(hash_val) == 64` |
| `tests/dossier/test_determinism.py` | 404 | `TestUTF8Handling.test_utf8_special_characters` | `len(hash_val) == 64` |
| `tests/dossier/test_determinism.py` | 466 | `TestLineEndingHandling.test_lf_only_reproducibility` | `len(set(hashes)) == 1` |
| `tests/dossier/test_determinism.py` | 475 | `TestLineEndingHandling.test_crlf_only_reproducibility` | `len(set(hashes)) == 1` |
| `tests/dossier/test_determinism.py` | 608 | `TestParityHashStability.test_parity_hash_algorithm_deterministic` | `len(set(parity_hashes)) == 1` |
| `tests/dossier/test_determinism.py` | 624 | `TestParityHashStability.test_parity_hash_stable_with_large_dossier` | `len(set(hashes)) == 1` |
| `tests/dossier/test_determinism.py` | 754 | `TestDeterminismIntegration.test_determinism_at_scale` | `len(unique) == 1` |
| `tests/dossier/test_determinism.py` | 141 | `TestHashReproducibility.test_hash_file_reproducibility_various_sizes` | `len(set(hashes)) == 1` |
| `tests/dossier/test_drift_detector.py` | 87 | `TestBaselineKey.test_baseline_key_compute_hash` | `len(hash_val) == 64` |
| `tests/dossier/test_emitter_adapter.py` | 71 | `TestFireDossierEventDirect.test_registered_emitter_receives_kwargs_and_routes_return` | `len(captured) == 1` |
| `tests/dossier/test_emitter_adapter.py` | 159 | `TestEmitArtifactIndexedThroughAdapter.test_registered_emitter_receives_correctly_shaped_event` | `len(captured) == 1` |
| `tests/dossier/test_events.py` | 156 | `TestEmitArtifactIndexed.test_emits_namespaced_envelope` | `len(captured_emissions) == 1` |
| `tests/dossier/test_hasher.py` | 31 | `TestHashFile.test_hash_file_determinism` | `len(set(hashes)) == 1` |
| `tests/dossier/test_hasher.py` | 33 | `TestHashFile.test_hash_file_determinism` | `len(hashes[0]) == 64` |
| `tests/dossier/test_hasher.py` | 314 | `TestHasher.test_hasher_single_hash` | `len(parity) == 64` |
| `tests/dossier/test_hasher.py` | 380 | `TestHasher.test_hasher_parity_result_is_valid_hex` | `len(parity) == 64` |
| `tests/dossier/test_hasher.py` | 403 | `TestHasher.test_hasher_can_add_non_sha256_hashes` | `len(parity) == 64` |
| `tests/dossier/test_indexer.py` | 48 | `TestIndexerScanning.test_scan_directory_yields_files` | `len(files) == 4` |
| `tests/dossier/test_indexer.py` | 66 | `TestIndexerScanning.test_scan_directory_skips_hidden_files` | `len(files) == 1` |
| `tests/dossier/test_indexer.py` | 78 | `TestIndexerScanning.test_scan_directory_skips_kittify_directory` | `len(files) == 1` |
| `tests/dossier/test_indexer.py` | 92 | `TestIndexerScanning.test_scan_directory_recursive` | `len(files) == 3` |
| `tests/dossier/test_indexer.py` | 248 | `TestMissingArtifactDetection.test_detect_missing_required_artifact` | `len(missing) == 1` |
| `tests/dossier/test_indexer.py` | 288 | `TestMissingArtifactDetection.test_detect_multiple_missing_artifacts` | `len(missing) == 2` |
| `tests/dossier/test_indexer.py` | 390 | `TestMissingArtifactDetection.test_step_aware_missing_detection` | `len(missing) == 1` |
| `tests/dossier/test_indexer.py` | 658 | `TestLargeScaleIndexing.test_scan_30_plus_artifacts_without_errors` | `len(dossier.artifacts) == 35` |
| `tests/dossier/test_indexer.py` | 661 | `TestLargeScaleIndexing.test_scan_30_plus_artifacts_without_errors` | `len(present) == 35` |
| `tests/dossier/test_indexer.py` | 449 | `TestUnreadableArtifactHandling.test_scan_continues_after_unreadable_artifact` | `len(indexed_artifacts) == 2` |
| `tests/dossier/test_indexer.py` | 453 | `TestUnreadableArtifactHandling.test_scan_continues_after_unreadable_artifact` | `len(present) == 1` |
| `tests/dossier/test_indexer.py` | 454 | `TestUnreadableArtifactHandling.test_scan_continues_after_unreadable_artifact` | `len(unreadable) == 1` |
| `tests/dossier/test_manifest.py` | 41 | `TestArtifactClassEnum.test_enum_has_six_values` | `len(list(ArtifactClassEnum)) == 6` |
| `tests/dossier/test_manifest.py` | 157 | `TestExpectedArtifactManifest.test_create_manifest_with_specs` | `len(manifest.required_always) == 1` |
| `tests/dossier/test_manifest.py` | 158 | `TestExpectedArtifactManifest.test_create_manifest_with_specs` | `len(manifest.optional_always) == 1` |
| `tests/dossier/test_manifest.py` | 281 | `TestManifestRegistry.test_get_blocking_artifacts` | `len(blocking) == 1` |
| `tests/dossier/test_models.py` | 475 | `TestMissionDossier.test_dossier_with_artifacts` | `len(dossier.artifacts) == 2` |
| `tests/dossier/test_models.py` | 515 | `TestMissionDossier.test_get_required_artifacts` | `len(required) == 2` |
| `tests/dossier/test_models.py` | 549 | `TestMissionDossier.test_get_missing_required_artifacts` | `len(missing) == 1` |
| `tests/dossier/test_snapshot.py` | 263 | `TestComputeSnapshotDeterministic.test_artifact_summaries_complete` | `len(snapshot.artifact_summaries) == 1` |
| `tests/dossier/test_snapshot.py` | 363 | `TestParityHashAlgorithm.test_parity_hash_deterministic_single_artifact` | `len(hash1) == 64` |
| `tests/dossier/test_snapshot.py` | 566 | `TestParityHashAlgorithm.test_duplicate_hashes_included` | `len(components) == 2` |
| `tests/dossier/test_snapshot.py` | 895 | `TestSnapshotEquality.test_snapshot_hash_for_set_usage` | `len(snapshot_set) == 2` |
| `tests/dossier/test_snapshot.py` | 939 | `TestLargeSnapshot.test_snapshot_computes_for_30_plus_artifacts` | `len(snapshot.parity_hash_sha256) == 64` |
| `tests/dossier/test_snapshot.py` | 940 | `TestLargeSnapshot.test_snapshot_computes_for_30_plus_artifacts` | `len(snapshot.artifact_summaries) == 35` |

#### `tests/lanes` (12)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/lanes/test_acceptance_matrix.py` | 131 | `TestPersistence.test_round_trip` | `len(restored.criteria) == 1` |
| `tests/lanes/test_acceptance_matrix.py` | 132 | `TestPersistence.test_round_trip` | `len(restored.negative_invariants) == 1` |
| `tests/lanes/test_acceptance_matrix.py` | 535 | `TestScaffoldAcceptanceMatrix.test_scaffold_empty_but_valid_when_no_requirements` | `len(matrix.criteria) == 1` |
| `tests/lanes/test_branch_naming_seam.py` | 385 | `test_resolve_branch_legacy_emits_one_shot_warning` | `len(dep) == 1` |
| `tests/lanes/test_compute_planning_artifact.py` | 107 | `TestCodeWPsStillGetNormalLanes.test_code_wps_with_planning_wps_get_normal_lane_ids` | `len(code_lanes) == 2` |
| `tests/lanes/test_compute_planning_artifact_deps.py` | 104 | `test_planning_wp_depends_on_code_wp_creates_lane_edge` | `len(code_lane_ids) == 1` |
| `tests/lanes/test_implementation_recovery.py` | 247 | `TestScanRecoveryState.test_scan_detects_orphaned_branch` | `len(lane_a_states) == 2` |
| `tests/lanes/test_implementation_recovery.py` | 280 | `TestScanRecoveryState.test_scan_detects_branch_with_no_context` | `len(lane_a_states) == 2` |
| `tests/lanes/test_models.py` | 67 | `test_lanes_manifest_round_trip` | `len(restored.lanes) == 2` |
| `tests/lanes/test_models.py` | 154 | `test_parallel_groups` | `len(groups[0]) == 2` |
| `tests/lanes/test_models.py` | 155 | `test_parallel_groups` | `len(groups[1]) == 1` |
| `tests/lanes/test_persistence.py` | 54 | `test_write_and_read` | `len(restored.lanes) == 1` |

#### `tests/migrate` (5)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/migrate/test_charter_encoding_migration.py` | 185 | `test_yes_flag_normalizes_without_prompt` | `len(payload['normalized']) == 1` |
| `tests/migrate/test_charter_encoding_migration.py` | 223 | `test_yes_exits_nonzero_on_ambiguous_file` | `len(payload['ambiguous']) == 1` |
| `tests/migrate/test_charter_encoding_migration.py` | 252 | `test_idempotency_second_run_is_noop` | `len(payload1['normalized']) == 1` |
| `tests/migrate/test_charter_encoding_migration.py` | 268 | `test_idempotency_second_run_is_noop` | `len(payload2['already_utf8']) == 1` |
| `tests/migrate/test_charter_encoding_migration.py` | 299 | `test_idempotency_precheck_skips_utf8_files_without_chokepoint` | `len(payload['already_utf8']) == 1` |

#### `tests/merge` (7)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/merge/test_merge_compat_surface.py` | 242 | `test_consolidated_map_is_superset_of_retired_batteries` | `len(_RETIRED_BATTERY_UNION) == 54` |
| `tests/merge/test_merge_post_merge_invariant.py` | 41 | `test_classify_tracked_modification_is_offending` | `len(offending) == 1` |
| `tests/merge/test_merge_post_merge_invariant.py` | 50 | `test_classify_mixed_untracked_and_tracked` | `len(offending) == 1` |
| `tests/merge/test_merge_post_merge_invariant.py` | 59 | `test_classify_deletion_is_offending` | `len(offending) == 1` |
| `tests/merge/test_merge_post_merge_invariant.py` | 77 | `test_classify_empty_lines_ignored` | `len(offending) == 1` |
| `tests/merge/test_merge_state_unit.py` | 364 | `TestStatePersistence.test_per_mission_scoping` | `len(loaded_b.wp_order) == 2` |
| `tests/merge/test_mid8_embedded_preflight.py` | 244 | `TestCheckMissionBranchResolverWarning.test_legacy_slug_resolves_with_one_shot_warning` | `len(dep) == 1` |

#### `tests/review` (5)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/review/test_artifacts.py` | 65 | `test_review_cycle_artifact_to_dict_round_trip` | `len(restored.affected_files) == 1` |
| `tests/review/test_artifacts.py` | 90 | `test_write_and_from_file_round_trip` | `len(restored.affected_files) == 1` |
| `tests/review/test_baseline.py` | 491 | `TestDiffBaseline.test_diff_baseline_sentinel` | `len(new) == 2` |
| `tests/review/test_dirty_classifier.py` | 61 | `test_other_wp_task_files_are_benign` | `len(benign) == 3` |
| `tests/review/test_dirty_classifier.py` | 115 | `test_kittify_paths_are_benign` | `len(benign) == 3` |

### WP14 (146 convert sites across 29 directories)

#### `tests/audit` (9)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/audit/test_audit_classifiers.py` | 362 | `test_status_events_collects_all_corrupt_lines` | `len(corrupt) == 2` |
| `tests/audit/test_audit_classifiers.py` | 469 | `test_status_json_reducer_oserror_detail_is_deterministic` | `len(drift) == 1` |
| `tests/audit/test_audit_classifiers.py` | 496 | `test_status_json_reducer_oserror_strerror_path_is_redacted` | `len(drift) == 1` |
| `tests/audit/test_audit_engine.py` | 147 | `test_mission_filter_scoping` | `len(report.missions) == 1` |
| `tests/audit/test_audit_engine.py` | 214 | `test_corrupt_jsonl_does_not_crash_engine` | `len(report.missions) == 1` |
| `tests/audit/test_audit_engine.py` | 232 | `test_non_object_meta_and_status_json_do_not_crash_engine` | `len(report.missions) == 1` |
| `tests/audit/test_audit_engine.py` | 325 | `test_performance_204_missions` | `len(report.missions) == 204` |
| `tests/audit/test_audit_models.py` | 30 | `TestSeverity.test_has_exactly_three_members` | `len(members) == 3` |
| `tests/audit/test_audit_models.py` | 364 | `TestRepoAuditReport.test_missions_serialized` | `len(d['missions']) == 2` |

#### `tests/auth` (22)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/auth/concurrency/test_machine_refresh_lock.py` | 272 | `test_concurrent_refresh_serializes_through_machine_lock` | `len(outcomes) == 2` |
| `tests/auth/concurrency/test_single_flight_refresh.py` | 315 | `test_factory_returns_same_instance_across_concurrent_callers` | `len(tm_ids) == 1` |
| `tests/auth/concurrency/test_stale_grant_preservation.py` | 344 | `test_current_rejection_clears_with_message` | `len(outcomes) == 1` |
| `tests/auth/integration/test_browser_login_e2e.py` | 215 | `TestBrowserLoginE2E.test_full_browser_login_happy_path` | `len(fake_storage.writes) == 1` |
| `tests/auth/integration/test_browser_login_e2e.py` | 221 | `TestBrowserLoginE2E.test_full_browser_login_happy_path` | `len(stored.teams) == 2` |
| `tests/auth/integration/test_browser_login_e2e.py` | 353 | `TestBrowserLoginE2E.test_login_force_resets_session` | `len(fake_storage.writes) == 1` |
| `tests/auth/integration/test_headless_login_e2e.py` | 167 | `TestHeadlessLoginE2E.test_full_device_flow_happy_path` | `len(fake_storage.writes) == 1` |
| `tests/auth/integration/test_headless_login_e2e.py` | 234 | `TestHeadlessLoginE2E.test_device_flow_respects_pending_poll` | `len(fake_storage.writes) == 1` |
| `tests/auth/integration/test_logout_e2e.py` | 100 | `TestLogoutE2E.test_logout_server_success` | `len(captured_posts) == 1` |
| `tests/auth/integration/test_refresh_through_transport.py` | 380 | `TestRefreshThroughTransport.test_expired_token_refreshes_before_health_probe` | `len(seeded_tm.writes) == 1` |
| `tests/auth/test_auth_doctor_classification.py` | 198 | `test_json_orphan_record_has_cleanup_class` | `len(orphans) == 2` |
| `tests/auth/test_auth_doctor_classification.py` | 297 | `test_reset_json_has_reset_result` | `len(rr['swept']) == 1` |
| `tests/auth/test_auth_doctor_classification.py` | 334 | `test_reset_json_skipped_has_cleanup_class` | `len(skipped) == 1` |
| `tests/auth/test_auth_doctor_classification.py` | 479 | `test_no_reset_performs_no_sweep` | `len(payload['orphans']) == 1` |
| `tests/auth/test_authorization_code_flow.py` | 257 | `TestBuildSession.test_happy_path_uses_absolute_expires_at` | `len(session.teams) == 1` |
| `tests/auth/test_device_code_flow.py` | 400 | `TestBuildSession.test_happy_path_uses_absolute_expires_at` | `len(session.teams) == 1` |
| `tests/auth/test_pkce.py` | 34 | `test_verifier_is_43_characters` | `len(verifier) == 43` |
| `tests/auth/test_pkce.py` | 46 | `test_verifier_is_random_between_calls` | `len(verifiers) == 32` |
| `tests/auth/test_pkce.py` | 77 | `test_generate_pkce_pair_returns_matching_verifier_and_challenge` | `len(verifier) == 43` |
| `tests/auth/test_secure_storage_file.py` | 102 | `test_write_creates_salt_file_with_0600` | `len(salt_file.read_bytes()) == 16` |
| `tests/auth/test_state_manager.py` | 63 | `test_state_manager_generate_returns_fresh_state` | `len(state.code_verifier) == 43` |
| `tests/auth/test_token_manager.py` | 786 | `test_refresh_logs_outcome_at_info` | `len(matching) == 1` |

#### `tests/tasks` (10)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/tasks/test_finalize_tasks_lanes_disjoint_fan_in.py` | 38 | `test_disjoint_upstreams_remain_parallel_until_fan_in` | `len(upstream_lane_ids) == 6` |
| `tests/tasks/test_tasks_support.py` | 156 | `TestActivityEntries.test_parse_simple_agent_name` | `len(entries) == 1` |
| `tests/tasks/test_tasks_support.py` | 177 | `TestActivityEntries.test_parse_hyphenated_agent_name` | `len(entries) == 2` |
| `tests/tasks/test_tasks_support.py` | 196 | `TestActivityEntries.test_parse_multiple_hyphens_in_agent_name` | `len(entries) == 1` |
| `tests/tasks/test_tasks_support.py` | 206 | `TestActivityEntries.test_parse_without_shell_pid` | `len(entries) == 1` |
| `tests/tasks/test_tasks_support.py` | 223 | `TestActivityEntries.test_parse_mixed_agent_names` | `len(entries) == 4` |
| `tests/tasks/test_tasks_support.py` | 236 | `TestActivityEntries.test_parse_with_hyphen_separator` | `len(entries) == 1` |
| `tests/tasks/test_tasks_support.py` | 247 | `TestActivityEntries.test_parse_with_en_dash_separator` | `len(entries) == 1` |
| `tests/tasks/test_tasks_support.py` | 258 | `TestActivityEntries.test_parse_multiline_note` | `len(entries) == 1` |
| `tests/tasks/test_tasks_support.py` | 286 | `TestActivityEntries.test_parse_all_lanes` | `len(entries) == 4` |

#### `tests/missions` (17)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/missions/test_doc_state.py` | 62 | `test_initialize_documentation_state` | `len(state['generators_configured']) == 1` |
| `tests/missions/test_doc_state.py` | 186 | `test_set_generators_configured` | `len(meta['documentation_state']['generators_configured']) == 1` |
| `tests/missions/test_doc_state_formatting.py` | 129 | `TestSetGeneratorsFormat.test_sorted_keys_and_trailing_newline` | `len(parsed['documentation_state']['generators_configured']) == 1` |
| `tests/missions/test_documentation_mission.py` | 55 | `test_documentation_mission_workflow_phases` | `len(phases) == 6` |
| `tests/missions/test_mission_loading_integration.py` | 406 | `TestBackwardCompatibility.test_mission_get_workflow_phases` | `len(phases) == 2` |
| `tests/missions/test_mission_software_dev_integration.py` | 77 | `TestStateMachineStructure.test_six_states_defined` | `len(states) == 6` |
| `tests/missions/test_mission_software_dev_integration.py` | 95 | `TestStateMachineStructure.test_six_transitions_defined` | `len(transitions) == 6` |
| `tests/missions/test_mission_software_dev_integration.py` | 99 | `TestStateMachineStructure.test_advance_transitions_count` | `len(advance_transitions) == 5` |
| `tests/missions/test_mission_software_dev_integration.py` | 103 | `TestStateMachineStructure.test_rework_transition_exists` | `len(rework_transitions) == 1` |
| `tests/missions/test_mission_software_dev_integration.py` | 201 | `TestGuardsSection.test_five_guards_defined` | `len(guards) == 5` |
| `tests/missions/test_mission_software_dev_integration.py` | 272 | `TestV0BackwardCompatibility.test_v0_workflow_preserved` | `len(phases) == 5` |
| `tests/missions/test_mission_v1_compat_unit.py` | 224 | `TestAPICompatibility.test_get_states` | `len(states) == 3` |
| `tests/missions/test_mission_v1_compat_unit.py` | 244 | `TestLegacyDelegation.test_get_workflow_phases` | `len(phases) == 5` |
| `tests/missions/test_mission_v1_compat_unit.py` | 344 | `TestEdgeCases.test_many_phases` | `len(pm.get_states()) == 21` |
| `tests/missions/test_mission_v1_events_unit.py` | 51 | `TestEmitEvent.test_writes_jsonl_line` | `len(lines) == 1` |
| `tests/missions/test_resolution_convergence.py` | 495 | `test_form_to_dir_all_unique` | `len(FORM_TO_DIR) == 5` |
| `tests/missions/test_resolution_convergence.py` | 500 | `test_form_to_dir_all_unique` | `len(unique_paths) == 5` |

#### `tests/cross_cutting` (3)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/cross_cutting/encoding/test_contextive_traceability.py` | 91 | `test_parse_terms_count` | `len(ctx.terms) == 2` |
| `tests/cross_cutting/encoding/test_contextive_traceability.py` | 202 | `test_load_map` | `len(tmap.scopes) == 1` |
| `tests/cross_cutting/misc/test_plan_validation.py` | 226 | `test_validate_plan_with_partial_markers` | `len(markers) == 2` |

#### `tests/docs` (14)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/docs/test_anti_sprawl_ratchet.py` | 162 | `test_floor_is_the_enumerated_thirteen_sections` | `len(floor['sections']) == 13` |
| `tests/docs/test_build_cli_reference.py` | 335 | `TestPartition.test_partition_includes_hidden_when_requested` | `len(hidden) == 1` |
| `tests/docs/test_check_cli_reference_freshness.py` | 179 | `TestRules.test_missing_reference_emits_ref_missing` | `len(missing) == 1` |
| `tests/docs/test_check_cli_reference_freshness.py` | 190 | `TestRules.test_extra_reference_emits_ref_extra` | `len(extra) == 1` |
| `tests/docs/test_check_cli_reference_freshness.py` | 307 | `TestRules.test_help_drift_warning_by_default` | `len(drift) == 1` |
| `tests/docs/test_check_docs_freshness.py` | 548 | `test_select_link_check_paths_samples_when_oversize` | `len(selected) == 21` |
| `tests/docs/test_check_docs_freshness.py` | 637 | `test_findings_from_payload_skips_non_dict_entries` | `len(out) == 1` |
| `tests/docs/test_frontmatter_backfill.py` | 271 | `test_plan_backfill_walks_the_inventory` | `len(load_inventory(inventory)) == 2` |
| `tests/docs/test_relative_link_fixer.py` | 328 | `TestRewriteBodyHelper.test_rewrite_body_skips_frontmatter_region` | `len(rewrites) == 1` |
| `tests/docs/test_relative_link_fixer.py` | 446 | `TestNoExcludeFlag.test_no_exclude_flag_plumbs_through_main` | `len(captured) == 1` |
| `tests/docs/test_relative_link_fixer.py` | 582 | `TestDeliberateBreakage.test_all_dead_links_reported_with_line_numbers` | `len(dead) == 2` |
| `tests/docs/test_relative_link_fixer.py` | 609 | `TestDeliberateBreakage.test_dead_link_line_reported_correctly_with_frontmatter` | `len(dead) == 1` |
| `tests/docs/test_runtime_read_resolution.py` | 141 | `TestShimRegistryReadersResolveNewHome.test_load_registry_resolves_docs_migrations` | `len(entries) == 1` |
| `tests/docs/test_version_leakage_check.py` | 64 | `test_load_inventory_clean` | `len(entries) == 3` |

#### `tests/cli` (4)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/cli/commands/test_doctor_topology.py` | 73 | `test_mission_scoping` | `len(missions) == 1` |
| `tests/cli/commands/test_implement_base_flag.py` | 163 | `TestValidateBaseRef.test_valid_ref_returns_sha` | `len(sha) == 40` |
| `tests/cli/commands/test_retrospect.py` | 312 | `TestCreateCommand.test_create_mission_not_completed_json` | `len(data['open_wps']) == 1` |
| `tests/cli/commands/test_sync_commands.py` | 861 | `test_sync_now_posts_exactly_once_and_drains_body` | `len(posts) == 1` |

#### `tests/doctor` (11)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/doctor/test_identity_audit.py` | 260 | `test_find_duplicate_prefixes_three_080` | `len(dupes['080']) == 3` |
| `tests/doctor/test_identity_audit.py` | 296 | `test_find_duplicate_prefixes_skips_non_directory_entries` | `len(dupes['080']) == 2` |
| `tests/doctor/test_identity_audit.py` | 319 | `test_find_duplicate_prefixes_distinct_07x` | `len(dupes['070']) == 2` |
| `tests/doctor/test_identity_audit.py` | 320 | `test_find_duplicate_prefixes_distinct_07x` | `len(dupes['071']) == 2` |
| `tests/doctor/test_identity_audit.py` | 337 | `test_find_ambiguous_selectors_three_080` | `len(ambiguous['080']) == 3` |
| `tests/doctor/test_identity_audit.py` | 348 | `test_find_ambiguous_selectors_shared_human_slug` | `len(ambiguous['foo-bar']) == 2` |
| `tests/doctor/test_identity_audit.py` | 381 | `test_find_ambiguous_selectors_distinct_081_and_081_bar` | `len(ambiguous['081']) == 2` |
| `tests/doctor/test_identity_audit.py` | 432 | `test_identity_json_schema` | `len(missions) == 6` |
| `tests/doctor/test_identity_audit.py` | 447 | `test_identity_json_schema` | `len(doc['duplicate_prefixes']['080']) == 2` |
| `tests/doctor/test_identity_audit.py` | 511 | `test_identity_mission_scope` | `len(doc['missions']) == 1` |
| `tests/doctor/test_identity_audit.py` | 563 | `test_nfr_002_timing_200_missions` | `len(states) == 200` |

#### `tests/core` (7)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/core/test_loopback_http.py` | 88 | `test_serve_loopback_server_binds_loopback_and_serves_forever` | `len(_RecordingServer.instances) == 1` |
| `tests/core/test_loopback_http.py` | 128 | `test_serve_loopback_server_does_not_bind_non_loopback_host` | `len(_RecordingServer.instances) == 1` |
| `tests/core/test_mission_creation_identity.py` | 86 | `test_mission_id_minted_at_creation` | `len(meta['mission_id']) == 26` |
| `tests/core/test_mission_number_null_schema.py` | 267 | `test_new_mission_feature_dir_uses_human_slug_mid8` | `len(parts) == 2` |
| `tests/core/test_mission_number_null_schema.py` | 269 | `test_new_mission_feature_dir_uses_human_slug_mid8` | `len(mid8_part) == 8` |
| `tests/core/test_wps_manifest.py` | 31 | `TestLoadWpsManifest.test_load_valid_manifest` | `len(manifest.work_packages) == 1` |
| `tests/core/test_wps_manifest.py` | 72 | `TestLoadWpsManifest.test_load_multiple_work_packages` | `len(manifest.work_packages) == 2` |

#### `tests/characterization` (7)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/characterization/test_trio_pure_cores.py` | 310 | `TestCheckLaneGates.test_target_branch_mismatch_between_meta_and_lanes_blocks` | `len(skipped) == 4` |
| `tests/characterization/test_trio_pure_cores.py` | 360 | `TestCheckLaneGates.test_planning_artifact_only_mission_skips_matrix_entirely` | `len(skipped) == 4` |
| `tests/characterization/test_trio_pure_cores.py` | 377 | `TestCheckLaneGates.test_missing_acceptance_matrix_blocks` | `len(skipped) == 3` |
| `tests/characterization/test_trio_pure_cores.py` | 276 | `TestCheckLaneGates.test_corrupt_lanes_json_blocks_and_skips_all_checks` | `len(blocked) == 1` |
| `tests/characterization/test_trio_pure_cores.py` | 308 | `TestCheckLaneGates.test_target_branch_mismatch_between_meta_and_lanes_blocks` | `len(blocked) == 1` |
| `tests/characterization/test_trio_pure_cores.py` | 325 | `TestCheckLaneGates.test_branch_outside_allowed_set_blocks` | `len(blocked) == 1` |
| `tests/characterization/test_trio_pure_cores.py` | 376 | `TestCheckLaneGates.test_missing_acceptance_matrix_blocks` | `len(blocked) == 1` |

#### `tests/kernel` (5)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/kernel/test_glossary_types.py` | 73 | `TestSemanticConflictAmbiguousGuard.test_ambiguous_with_candidates_is_valid` | `len(conflict.candidate_senses) == 1` |
| `tests/kernel/test_safe_re.py` | 525 | `TestSplitMutationKills.test_split_with_maxsplit_one_stops_after_first_match` | `len(parts) == 2` |
| `tests/kernel/test_safe_re.py` | 533 | `TestSplitMutationKills.test_split_with_maxsplit_two_stops_after_second_match` | `len(parts) == 3` |
| `tests/kernel/test_safe_re.py` | 553 | `TestSplitMutationKills.test_split_with_ignorecase_flag_forwards_through_dispatcher` | `len(parts) == 3` |
| `tests/kernel/test_safe_re.py` | 658 | `TestSubnMutationKills.test_subn_returns_tuple_not_string` | `len(out) == 2` |

#### `tests/policy` (2)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/policy/test_hook_installer_rendering.py` | 39 | `test_hook_rendering_shape` | `len(exec_lines) == 1` |
| `tests/policy/test_risk_scorer.py` | 50 | `TestSharedParentDirs.test_no_shared_parent` | `len(report.lane_pair_risks) == 1` |

#### `tests/delivery` (14)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/delivery/test_envelope.py` | 111 | `test_journal_stores_full_envelope_so_dispatch_posts_contract_event` | `len(received) == 1` |
| `tests/delivery/test_ledger.py` | 262 | `test_select_undelivered_respects_limit` | `len(selected) == 2` |
| `tests/delivery/test_receivers.py` | 464 | `test_stub_received_events_read_surface` | `len(received) == 1` |
| `tests/delivery/test_targets.py` | 87 | `test_two_urls_same_scope_yield_two_targets` | `len(registry.list_targets()) == 2` |
| `tests/delivery/test_targets.py` | 95 | `test_same_url_same_scope_is_idempotent` | `len(registry.list_targets()) == 1` |
| `tests/delivery/test_targets.py` | 103 | `test_distinct_scope_yields_distinct_target` | `len(registry.list_targets()) == 3` |
| `tests/delivery/test_targets.py` | 111 | `test_anonymous_scope_none_and_empty_collapse` | `len(registry.list_targets()) == 1` |
| `tests/delivery/test_targets.py` | 139 | `test_cosmetic_variants_register_as_one_target` | `len(registry.list_targets()) == 1` |
| `tests/delivery/test_targets.py` | 149 | `test_url_hash_is_one_way_digest` | `len(digest) == 64` |
| `tests/delivery/test_targets.py` | 235 | `test_new_metadata_updates_provenance_without_forking` | `len(registry.list_targets()) == 1` |
| `tests/delivery/test_targets.py` | 262 | `test_reset_flagged_on_stable_field_change` | `len(registry.list_targets()) == 1` |
| `tests/delivery/test_targets.py` | 279 | `test_deployment_id_only_change_is_not_a_reset` | `len(registry.list_targets()) == 1` |
| `tests/delivery/test_targets.py` | 360 | `test_register_from_resolved_anonymous` | `len(registry.list_targets()) == 1` |
| `tests/delivery/test_targets.py` | 397 | `test_registry_is_a_context_manager` | `len(reg.list_targets()) == 1` |

#### `tests/git_ops` (3)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/git_ops/test_git.py` | 346 | `TestCommitOperations.test_get_changes_with_revision_range` | `len(changes) == 2` |
| `tests/git_ops/test_git.py` | 475 | `TestConflictOperations.test_conflict_marker_parsing` | `len(ranges) == 1` |
| `tests/git_ops/test_worktree.py` | 569 | `TestVCSAbstraction.test_create_worktree_falls_back_to_git_with_warning` | `len(w) == 1` |

#### `tests/event_journal` (3)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/event_journal/test_coalesce.py` | 110 | `test_undelivered_events_with_same_key_collapse_to_one_row` | `len(keyed) == 1` |
| `tests/event_journal/test_coalesce.py` | 143 | `test_coalesce_against_delivered_event_leaves_bytes_unchanged` | `len(markers) == 1` |
| `tests/event_journal/test_coalesce.py` | 221 | `test_registration_is_idempotent` | `len(read_supersede_markers(journal)) == 1` |

#### `tests/dashboard` (4)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/dashboard/test_duplicate_prefix_rendering.py` | 125 | `test_registry_has_three_distinct_mission_id_keys` | `len(registry) == 3` |
| `tests/dashboard/test_duplicate_prefix_rendering.py` | 176 | `test_mid8_is_distinct_across_missions` | `len(mid8s) == 3` |
| `tests/dashboard/test_duplicate_prefix_rendering.py` | 233 | `test_dashboard_json_cli_renders_three_distinct_rows` | `len(missions) == 3` |
| `tests/dashboard/test_duplicate_prefix_rendering.py` | 248 | `test_dashboard_json_cli_renders_three_distinct_rows` | `len(payload['display_order']) == 3` |

#### `tests/context` (4)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/context/test_mission_resolver.py` | 150 | `TestResolveBySlug.test_human_slug_ambiguous_when_multiple_match` | `len(err.candidates) == 2` |
| `tests/context/test_mission_resolver.py` | 167 | `TestResolveByNumericPrefix.test_ambiguous_numeric_prefix_raises` | `len(err.candidates) == 2` |
| `tests/context/test_mission_resolver.py` | 275 | `TestAmbiguousHandleErrorJson.test_to_dict_structure` | `len(d['candidates']) == 2` |
| `tests/context/test_mission_resolver.py` | 185 | `TestResolveByNumericPrefix.test_ambiguous_error_candidates_have_mid8` | `len(candidate.mid8) == 8` |

#### `tests/paths` (2)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/paths/test_windows_migrate.py` | 98 | `test_absent_noop` | `len(outcomes) == 4` |
| `tests/paths/test_windows_migrate.py` | 218 | `test_idempotent_second_run` | `len(second) == 4` |

#### `tests/cross_branch` (1)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/cross_branch/test_parity.py` | 118 | `TestReducerParity.test_fixtures_file_integrity` | `len(slugs) == 1` |

#### `tests/release` (1)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/release/test_release_prep.py` | 177 | `test_changelog_includes_accepted_missions` | `len(slugs) == 2` |

#### `tests/readiness` (1)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/readiness/test_upgrade_ux.py` | 529 | `TestRunUpgradeUxFourChoices.test_choice_upgrade_now_safe_installer` | `len(cache_state['writes']) == 1` |

#### `tests/proof` (1)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/proof/test_event_schemas.py` | 126 | `test_build_test_evidence_payload_serializes_required_contract_fields` | `len(payload['idempotency_key']) == 64` |

#### `tests/mission_metadata` (1)

| File | Line | Enclosing qualname | Assertion |
|---|---|---|---|
| `tests/mission_metadata/test_mission_identity.py` | 50 | `test_resolve_mission_identity_includes_mission_id` | `len(identity.mission_id) == 26` |

## Partition 2 -- deferred (owned-file dir), ledgered to follow-up #2625

Convert-sites inside directories wholesale-owned by another WP in this mission (Lane 0/A/B) are **out of scope for this mission's batches** -- deliberately deferred and tracked here, not silently grandfathered into the baseline.

### `tests/specify_cli` (262 convert sites) -- #2625 (largest bucket -- WP04-owned)
### `tests/runtime` (11 convert sites) -- #2625 (WP04-owned)
### `tests/next` (9 convert sites) -- #2625 (WP03-owned)
### `tests/integration` (31 convert sites) -- #2625 (WP04-owned)

## Partition 3 -- no owner in this mission (informational; neither batch-assigned nor part of the #2625 deferral)

Directories with convert-classified sites that no WP in this mission owns wholesale or partially. Not silently grandfathered either -- listed here for visibility; the recurrence guard still bounds them at their current ceiling and any future mission may pick them up.

- `tests/_support` (10 convert sites)
- `tests/agent` (103 convert sites)
- `tests/architectural` (22 convert sites)
- `tests/contract` (7 convert sites)
- `tests/git` (1 convert sites)
- `tests/retrospective` (23 convert sites)
- `tests/status` (33 convert sites)
- `tests/sync` (50 convert sites)
- `tests/test_dashboard` (13 convert sites)
- `tests/unit` (17 convert sites)

## Partially-owned directories (noted, not batch-assigned)

No convert-classified site fell inside a directory this mission's ownership map marks as owned-by-file-only (rather than wholesale) by another WP as of this scan; if a future re-scan finds one, route it to the owning WP rather than a batch.

