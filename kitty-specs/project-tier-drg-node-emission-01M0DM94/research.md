# Research — Project-Tier DRG Node Emission (M6)

**Method**: read-only trace against current `main` (post-M1 / PR #3588). All references are `file:line`.

## R-1. Canonical node-kind authority (derive-don't-restate source)

- `NodeKind` is a declared **superset** of `ArtifactKind` by string value — `src/doctrine/drg/models.py:43-55` (`NodeKind.AGENT_PROFILE = "agent_profile"`), `src/doctrine/artifact_kinds.py:137` (`ArtifactKind.AGENT_PROFILE = "agent_profile"`). Invariant guarded by `tests/doctrine/drg/test_nodekind_artifactkind.py::test_node_kind_remains_superset_of_artifact_kind`.
- Canonical **total** authority: `src/doctrine/drg/migration/extractor.py:240` `_KIND_MAP = {kind.value: kind for kind in NodeKind}` (total by construction). `NodeKind("agent_profile")` also resolves directly.
- **Conclusion**: node-kind for any admitted kind derives from the superset; no new `NodeKind.from_artifact_kind` helper needed. The project `_KIND_TO_NODE_KIND` map's real job is the **emittable-kind allowlist**, not the conversion.

## R-2. Built-in agent_profile → node emission (pattern to mirror)

- `src/doctrine/drg/migration/extractor.py:1041` `_discover_built_in_nodes_in_dir`: glob `*.agent.yaml` (`:1052`), id-key `profile-id` (`:1053`), `rglob` recursive (`:1054`), `urn = artifact_to_urn(kind, artifact_id)` (`:1062`), `_ensure_node(..., NodeKind.AGENT_PROFILE, ...)` (`:1063`). Dispatcher table at `:1027-1033` lists `("agent_profiles", "agent_profile", NodeKind.AGENT_PROFILE)`.

## R-3. Project profile reader (single-authority reuse candidate)

- `src/doctrine/agent_profiles/repository.py:37` `_AGENT_PROFILE_GLOB = "*.agent.yaml"`; project layer scan at `:404` `directory.rglob(...)` with `recursive = overlay_scan_is_recursive(ArtifactKind.AGENT_PROFILE)` (`:355`), id-key `profile-id` (`:458`).
- `DoctrineService._project_dir` (`src/doctrine/service.py:36-45`) resolves `.kittify/doctrine/agent_profiles` via `PROJECT_KIND_DIRS`.

## R-4. Emit → persist → promote → cascade-read chain

- Emit/persist: `src/charter/synthesizer/project_drg.py:116` `emit_project_layer`; `:375` `persist` (writes `staging_dir/doctrine/graph.yaml`).
- Hook seam (emit+persist+validate co-occur): `src/charter/synthesizer/orchestrator.py:283-297` `_validation_callback`; `src/specify_cli/cli/commands/charter/_synthesis.py:245-252`.
- Promote: `src/charter/synthesizer/write_pipeline.py:585` `_promote_graph_overlay` → live `.kittify/doctrine/graph.yaml`.
- Cascade read: `src/charter/_drg_helpers.py:163-170` `load_validated_graph` reads project `.kittify/doctrine/graph.yaml` (or `*.graph.yaml`) via `src/doctrine/drg/loader.py:33` `has_graph_files` / `:81` `load_graph_or_dir`. Cascade traversal: `src/charter/cascade.py:306` `cascade_activation_targets`.

## R-5. Totality gate (M1 interaction)

- `tests/doctrine/drg/test_kind_mapping_totality.py`: enum-keyed guard `test_kind_keyed_dicts_are_total_or_exempt` (total-or-`_EXEMPT_GET_PARTIALS`); string-keyed authority guard; and `_STRING_KEYED_COVERAGE_WITNESS = "charter.synthesizer.project_drg::_KIND_TO_NODE_KIND"` asserted **discovered + partial** by `test_string_keyed_kind_map_coverage_sees_previously_hidden_maps`.
- Re-keying to `ArtifactKind` moves the map out of the string scan (witness test breaks → remove it) and into the enum scan (partial → must join `_EXEMPT_GET_PARTIALS`, read site already `.get`-based at `project_drg.py:_node_kind_for`).
- The M1 witness comment explicitly anticipates M6: *"converting it to enum-keyed is M6 (#3038), out of scope for M1."*

## R-6. Open risk (probe first in WP02)

Does an **edgeless** `agent_profile` project node pass `assert_valid` (`_drg_helpers.py:171`) and the orphan/exhaustiveness lints (`tests/doctrine/drg/test_kind_cascade_exhaustive.py`, `test_tiered_standards_non_orphan.py`)? Edge authoring is M5 (out of scope). The WP02 red-first step probes this before committing to node-only emission.
