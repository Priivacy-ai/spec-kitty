# Contract — Project-Tier Profile Emitter & Totality-Gate Reconciliation (M6)

## C-1. Project-tier profile walk emitter (WP02)

**Home**: reusable walk under `src/doctrine/drg/` (KD-1); composed by `charter.synthesizer.project_drg`.

**Signature (indicative — finalised in tasks)**:
```
emit_project_profile_nodes(
    project_root: Path,
    built_in_drg: DRGGraph,
    *,
    existing_urns: frozenset[str],
) -> list[DRGNode]
```

**Behaviour**:
- Enumerate authored project-tier profiles under `<project_root>/.kittify/doctrine/agent_profiles/` (recursive `*.agent.yaml`, id-key `profile-id`) — reuse `AgentProfileRepository` project reader where its public surface allows; else mirror `extractor._discover_built_in_nodes_in_dir`.
- For each: build `DRGNode(urn=f"agent_profile:{profile_id}", kind=NodeKind.AGENT_PROFILE, label=<name|None>, provenance="project")`.
- **Additive-only (INV-1)**: a URN already present in `built_in_drg` → `ProjectDRGValidationError` (no shadow).
- **Dedupe (INV-2)**: a URN already in `existing_urns` or seen twice in this walk → emitted once / rejected per existing overlay-duplicate discipline.
- **Fail-loud (INV-6 / NFR-002)**: a profile file that fails to parse/validate raises an error naming the file — no silent skip.
- **Asset boundary (INV-4)**: walks agent_profiles only; never emits `asset:*`.

**Integration**: merge the returned nodes into the overlay `DRGGraph` at the `_validation_callback` seam (`orchestrator.py:283-297`, `_synthesis.py:245-252`) **before** `persist`, so they flow through `persist → _promote_graph_overlay` into `.kittify/doctrine/graph.yaml`.

## C-2. Kind-admission map (WP01)

**Before**:
```python
_KIND_TO_NODE_KIND: dict[str, NodeKind] = {
    "directive": NodeKind.DIRECTIVE,
    "tactic": NodeKind.TACTIC,
    "styleguide": NodeKind.STYLEGUIDE,
}
```
**After**:
```python
_KIND_TO_NODE_KIND: dict[ArtifactKind, NodeKind] = {
    ArtifactKind.DIRECTIVE: NodeKind.DIRECTIVE,
    ArtifactKind.TACTIC: NodeKind.TACTIC,
    ArtifactKind.STYLEGUIDE: NodeKind.STYLEGUIDE,
    ArtifactKind.AGENT_PROFILE: NodeKind.AGENT_PROFILE,
}

def _node_kind_for(kind: str) -> NodeKind | None:
    try:
        artifact_kind = ArtifactKind(kind)
    except ValueError:
        return None
    return _KIND_TO_NODE_KIND.get(artifact_kind)
```
- Keys are the **emittable project-tier kind allowlist**; absence is contractual, not an oversight.
- `_node_kind_for` stays `.get`-read (required by the `_EXEMPT_GET_PARTIALS` contract).

## C-3. Totality-gate reconciliation (WP01, atomic with C-2)

In `tests/doctrine/drg/test_kind_mapping_totality.py`:
1. **Add** `"charter.synthesizer.project_drg::_KIND_TO_NODE_KIND"` to `_EXEMPT_GET_PARTIALS` with a rationale comment: *the map is the emittable-project-tier-kind allowlist; the sole read site `_node_kind_for` reads via `.get` and treats a miss as "kind not emitted at project tier" — a deliberate partial (agent_profile emission is M6/#3038).* 
2. **Remove** `_STRING_KEYED_COVERAGE_WITNESS` and `test_string_keyed_kind_map_coverage_sees_previously_hidden_maps` (the map left the string-keyed scan; the witness would false-fail).
3. Leave the other string-keyed authority guards and the enum-keyed guard intact.

**Post-condition**: the full `test_kind_mapping_totality.py` suite is green; the map is gate-visible (a future `ArtifactKind` added without a decision fails the enum-keyed guard unless exempted).

## C-4. Non-goals (bounded diff)

- No cascade relation-set change (M5). No org read-path bridge change (M2). No asset node emission (#3037). No project-tier `procedure` emission.
- Any golden-fixture delta is `agent_profile`-emission-attributable and explained in review.
