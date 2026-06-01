# Adversarial Review: Architecture & Wiring Claims
# Charter Pack Activation Layer

**Reviewer**: Adversarial Architecture Reviewer (Claude Sonnet 4.6)
**Date**: 2026-05-31
**Focus**: Wiring correctness, layer rule compliance, dead-code risk, migration safety

---

## BLOCKING (must address before tasks)

**1. Per-artifact-ID filtering is specified in the data model but has no implementation path.**

`data-model.md` introduces 8 new `PackContext` fields (`activated_directives`, `activated_tactics`, etc.) and states the invariant: "A non-empty frozenset means 'only these IDs are available.'" `CharterPackManager.activate/deactivate` stores these values in config.yaml. But `filter_graph_by_activation` in `src/charter/drg.py:639-663` only reads `activated_kinds` (kind-level) and `activated_mission_types`. It does **not** read per-artifact-ID fields. The `_node_is_activated` function has no code path that checks whether a specific directive ID (e.g., `python-style-guide`) is in `activated_directives`.

Result: `charter activate directive python-style-guide` writes to config.yaml, `PackContext` gains the field, but the charter context builder and DRG resolver **never consult it**. None of FR-031 through FR-037 require per-artifact-ID filtering — they only require kind-level filtering (`activated_kinds`). The FRs can be satisfied without ever implementing the per-ID path, leaving 8 of the 9 new `PackContext` fields as stored-but-ignored state.

**Resolution required**: Either (a) explicitly descope per-artifact-ID filtering from this mission and document it as a future phase, removing the per-kind fields from `PackContext` and `CharterPack` until the filter layer is extended, or (b) add an FR that extends `_node_is_activated` to check per-artifact-ID fields when non-None and include that in the plan.

---

**2. C-004 fix (`TYPE_CHECKING` removal) will break mypy strict without a Protocol.**

`src/doctrine/missions/mission_step_repository.py` has `from __future__ import annotations` and uses a `TYPE_CHECKING` guard to import `PackContext` from charter. The pytestarch test currently fails because pytestarch follows `TYPE_CHECKING` imports in AST analysis.

The research.md fix ("replace with string literal annotation `'PackContext'` and remove the TYPE_CHECKING import") addresses pytestarch. But with `from __future__ import annotations`, ALL annotations are already lazy strings at runtime — the TYPE_CHECKING guard is needed **for mypy**. Removing it without replacement causes:

```
error: Name "PackContext" is not defined  [name-defined]
```

This was confirmed empirically. Correct fix options:
- (a) Define a local structural `Protocol` in `doctrine.*` that matches `PackContext`'s interface and annotate with it
- (b) Use `Any` for the annotation with a comment
- (c) Add a mypy override for the specific file

The plan's stated fix is incomplete. Without a Protocol or override, the mypy gate in CI will fail after the architectural test passes.

---

**3. `_load_action_doctrine_bundle` and `build_charter_context` have no `pack_context` parameter — threading it requires API changes to multiple callers.**

`src/charter/context.py:488-545`: `_load_action_doctrine_bundle` takes `(repo_root, action, effective_depth, org_root)` — no `pack_context`. Called from lines 234 and 2452.

`build_charter_context` at line 114 has signature `(repo_root, *, profile, action, mark_loaded, depth, org_root, scope)` — also no `pack_context`. This function is imported and called from at least `invocation/executor.py` and `cli/commands/agent/workflow.py`.

The research table labels the line 523 fix as "Pass `pack_context`; call `filter_graph_by_activation`" — a one-line description. But the parameter does not exist on these functions. Adding it requires:
1. `build_charter_context` → add `pack_context: PackContext | None = None`
2. `_load_action_doctrine_bundle` → add `pack_context: PackContext | None = None`
3. All callers of `build_charter_context` in `specify_cli.*` → update to pass `PackContext.from_config(repo_root)`

This is a non-trivial API change. The plan must explicitly call this out, document the backward-compat strategy (`None` = no filtering, backward compatible), and identify which callers need updating.

---

**4. `doctor.py:2332` caller of `load_org_charter_policies` is missing from the wiring table.**

`src/specify_cli/cli/commands/doctor.py:2332` calls `load_org_charter_policies(repo_root)` without `pack_context`. Research.md lists only lines 660 and 710 (inside `org_charter.py` itself) and line 161 in `org_layer.py` — that is 3 callers. `doctor.py:2332` is a 4th production caller not in the table.

FR-037 says "all call sites that currently pass `pack_context=None` are updated." If `doctor.py:2332` is missed during implementation, `spec-kitty doctor` runs will resolve policies without activation filtering, giving the wrong picture silently.

---

**5. Stale `doctrine.missions.models::MissionStep` allowlist entry in `test_no_dead_symbols.py` is not addressed.**

`test_no_dead_symbols.py` currently fails for two separate reasons:
1. 12 dead symbols (covered by FR-024)
2. Stale allowlist entry: `doctrine.missions.models::MissionStep` in `_CATEGORY_C_WP_IN_FLIGHT_UNIFIED_MISSION_STEP` — WP01 gave `MissionStep` callers, so this allowlist entry must be removed

The plan addresses the 12 new symbols but does not mention removing the stale `MissionStep` entry. The test will remain failing after all 12 new symbols are addressed because `assert not messages` catches both failures in a single assertion. Implementers will be confused.

---

## SIGNIFICANT (should address before implementation)

**6. `CharterPackManager.activate()` initialization from `None` state requires DoctrineService catalog enumeration — unspecified.**

"If None: initialize to all built-ins, then add." Implementing this requires `CharterPackManager.activate()` to enumerate all built-in artifact IDs for the kind. `pack_manager.py` CAN import `doctrine.service.DoctrineService` (layer is allowed), but this is not mentioned anywhere in plan or research. The `list_available(repo_root, kind)` method signature in the data model implies this capability, but: which `DoctrineService` repo method is called, what root path is used, whether org-layer artifacts are included in the initialization set — all unspecified.

---

**7. `_read_activated_kinds` empty-list edge case contradicts the data model invariant.**

`src/charter/pack_context.py:196-199`:
```python
raw = data.get("activated_kinds")
if isinstance(raw, list) and raw:  # "and raw" silently treats [] as absent
    return frozenset(str(k) for k in raw)
return _BUILTIN_ARTIFACT_KINDS
```

`data-model.md` defines three states including "empty frozenset = explicit restriction to nothing." But the reader collapses `[]` into all-built-ins. If new per-kind readers use the same `and raw` guard, then `activated_directives: []` in config.yaml would be treated as `None` (all built-ins) rather than an explicit restriction. The "empty frozenset" semantic cannot be represented with the existing reader pattern. Either the invariant must be weakened (no empty-restriction state), or the reader logic must change.

---

**8. `reference_resolver.py:40` and its caller `resolver.py:263` have no `PackContext` — multi-level propagation required.**

`resolve_references_transitively(directive_ids, doctrine_service, *, graph=None, repo_root=None)` — no `pack_context` parameter. Its caller `resolver.py:263` `resolve_governance_for_profile` also has no `pack_context`. All callers of `resolver.py` in `charter.*` and `specify_cli.*` would need updating. Research labels this as a "1-line fix at line 40" but it requires multi-level signature propagation similar to finding #3.

---

**9. `StepContractExecutor` at `executor.py:142` has no `pack_context`; its production caller `runtime_bridge.py:1325` is not in the plan.**

`runtime_bridge.py:1325`: `result = StepContractExecutor(repo_root=repo_root).execute(...)`. Adding pack_context filtering at `executor.py:170` requires adding `pack_context` to `StepContractExecutor.__init__` and updating `runtime_bridge.py:1325` to pass `PackContext.from_config(repo_root)`. The `runtime_bridge.py` is in `specify_cli` and CAN import `charter.pack_context` (layer safe). But `runtime_bridge.py` is not identified in the plan as a file requiring changes.

---

**10. config.yaml will have three naming patterns for activation state — an outlier that should be documented.**

- `activated_kinds` (kind-level gate, 8-element set of plural kind names)
- `mission_type_activations` (legacy mission-type key from Phase 1)
- `activated_directives` / `activated_tactics` / etc. (new per-kind keys)

`mission_type_activations` is a naming outlier (not `activated_mission_types`). The plan does not address whether this key will be normalized or permanently remain a legacy name. Future readers of config.yaml will find three different naming conventions for the same conceptual domain. Should be documented or normalized.

---

## MINOR

**11. Research.md under-counts `load_org_charter_policies` callers**: lists 3 but finds only 2 in the explicit table. `doctor.py:2332` is not in the table (see blocking #4 for the runtime risk).

**12. `charter.drg::PackContext` is a dead re-export in `__all__` that the plan does not address.** `src/charter/drg.py:81`: `"PackContext"` is in `__all__`. No `src/` file imports `PackContext` from `charter.drg`. FR-024 says "wire or allowlist 12 dead symbols" but this specific re-export's disposition (remove from `__all__` vs allowlist) is not decided. Removing is the clean answer.

**13. Migration `target_version = "3.2.8"` fires only on stable release, not during rc-series testing.** `Version("3.2.8") > Version("3.2.0rc30")` — migration fires when the stable 3.2.8 ships. Testing during the rc phase must explicitly call `detect()`/`apply()` directly or stub `target_version`. Should be noted in WP test strategy.

---

## VERIFIED (claims that check out)

- `context.py:523` calls `load_validated_graph(repo_root, org_root=org_root)` — correct line, correct function name
- `reference_resolver.py:40` calls `load_validated_graph(repo_root)` — correct
- `compiler.py:499` calls `load_validated_graph(repo_root)` — correct
- `mission_step_repository.py:43` contains `from charter.pack_context import PackContext` inside `TYPE_CHECKING` — confirmed; `test_doctrine_does_not_import_charter` currently fails because of it
- `load_org_charter_policies` at `org_charter.py:462` has `pack_context: PackContext | None = None` — confirmed optional
- `MissionStepRepository` has zero production callers in `src/` — confirmed by grep and dead-symbols test
- `filter_graph_by_activation` has zero production callers — confirmed by grep and dead-symbols test
- `src/charter/packs/` directory does NOT exist yet — confirmed
- `PackContext.from_config()` does NOT import from `specify_cli.*` — confirmed; uses only ruamel.yaml and `doctrine.drg.org_pack_config`
- `charter.pack_manager.py` CAN write to config.yaml without importing `specify_cli.*` — layer safe confirmed
- m_3_2_7 migration pattern (ruamel.yaml round-trip, `preserve_quotes=True`, `detect()` requiring config.yaml) — correctly described in research.md
- `activated_kinds` read by `_read_activated_kinds` in `pack_context.py:190-199` — confirmed; new per-kind keys absent from `from_config()` and `PackContext` dataclass
- `mission_steps.py` re-export: `MissionStepRepository` NOT exported — confirmed
- Migration versioning: `Version("3.2.8") > Version("3.2.0rc30")` math is correct

---

## SUMMARY TABLE

| Severity | Count | Top item |
|----------|-------|----------|
| BLOCKING | 5 | Per-artifact-ID filtering specified in data model but has no implementation path |
| SIGNIFICANT | 5 | C-004 fix incomplete — removing `TYPE_CHECKING` import breaks mypy strict (confirmed empirically) |
| MINOR | 3 | Stale dead re-export `charter.drg::PackContext` in `__all__` unaddressed |
| VERIFIED | 14 | Line numbers correct; dead-code state confirmed; layer safety of pack_manager.py confirmed; migration versioning valid |
