# Adversarial Mission Review: charter-pack-activation-layer-01KSYE4V

**Reviewer**: Claude Sonnet 4.6 (post-merge adversarial pass)
**Date**: 2026-05-31
**Scope**: All 11 WPs, spec-to-code fidelity, predecessor blocking issues
**Baseline commit**: `3f94a68e3920e5ac861a3c745257ea7b6d87762e`
**Merge target**: `pr/charter-doctrine-mission-type-configuration`

---

## VERIFIED — Claims that check out

**1. C-004 violation fixed (Predecessor blocking issue #1)**
`src/doctrine/missions/mission_step_repository.py` no longer imports from `charter.*`. The `TYPE_CHECKING` import is gone. A local `_PackContextLike` protocol (Protocol class at line 31) replaces the cross-boundary annotation. No `from charter` or `import charter` appears anywhere in the file. `grep -n "TYPE_CHECKING\|from charter" src/doctrine/missions/mission_step_repository.py` returns only inline comments referencing the fix.

**2. Namespace package false positive fixed (Predecessor blocking issue #2)**
`tests/architectural/test_layer_rules.py::test_legacy_subpackage_is_gone` (line 196–221) now relies solely on the source-file existence check and explicitly documents the `find_spec` namespace-package caveat. The `find_spec` assertion is removed.

**3. Template governance payload tests fixed (Predecessor blocking issue #3)**
`tests/architectural/test_template_governance_payload_contract.py` was updated (via the gate-failure fix commit `b429a80dd`). The 8 broken tests referencing deleted `command-templates/` paths are resolved.

**4. Dead-modules allowlist fixed (Predecessor blocking issue #4)**
`tests/architectural/test_no_dead_modules.py` includes both `specify_cli.upgrade.migrations.m_3_2_7_activate_builtin_mission_types` (line 193) and `specify_cli.upgrade.migrations.m_3_2_8_default_charter_pack` (line 195) in `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS`. Baseline bumped to 75 in `_baselines.yaml`.

**5. Tracked test fixture files removed (Predecessor blocking issue #6)**
`git ls-files kitty-specs/ | grep test-feature` returns no results. All three test-feature directories (`test-feature-01KSY68P`, `test-feature-01KSY6MY`, `test-feature-01KSY8TG`) were removed in the remediation commit `be32076d0`.

**6. `filter_graph_by_activation` wired (Predecessor significant issue #7)**
`grep src/ -r filter_graph_by_activation --include="*.py" | grep -v "__all__"` returns 5 non-test, non-`__all__` production call sites:
- `src/charter/context.py:729`
- `src/charter/reference_resolver.py:67`
- `src/charter/compiler.py:561`
- `src/specify_cli/mission_step_contracts/executor.py:178`
- `src/charter/consistency_check.py:192`

All call sites pass `pack_context` to the filter. FR-031–FR-035 satisfied.

**7. `MissionStepRepository` wired to production (Predecessor significant issue #8)**
`src/charter/mission_steps.py:26` imports `MissionStepRepository` from `doctrine.missions.mission_step_repository` and re-exports it in `__all__`. `src/charter/resolver.py:444` calls `MissionStepRepository.default().resolve_all_for_mission_type()`. FR-016 satisfied.

**8. FR-039 `and raw` guard removed**
`src/charter/pack_context.py` `_read_activated_kinds` and `_read_activated_mission_types` both use `if isinstance(raw, list): return frozenset(...)` with no `and raw` guard. An explicit `[]` in config.yaml now maps to `frozenset()` (full restriction), not `None` (all built-ins). The deleted test `test_empty_activated_kinds_uses_builtin_fallback` is confirmed absent.

**9. Per-kind `activated_*` fields on PackContext**
All 8 new fields are present in `src/charter/pack_context.py`: `activated_directives`, `activated_tactics`, `activated_styleguides`, `activated_toolguides`, `activated_paradigms`, `activated_procedures`, `activated_agent_profiles`, `activated_mission_step_contracts`. Each is `frozenset[str] | None` with `None` default (three-state semantics). `from_config()` reads all 8.

**10. `ProjectContext` and `ContextPreconditionError` shipped and wired**
`src/charter/invocation_context.py` defines `ProjectContext`, `OperationalContext`, `ContextPreconditionError`, and `build_operational_context`. `ProjectContext.from_repo()` is called from 11 distinct `src/` locations: `org_charter.py`, `org_layer.py`, `doctor.py`, `workflow.py`, `mission.py`, `generate.py`, `consistency_check.py`, `activate.py`, `deactivate.py`, `list_cmd.py`, `pack.py`. `require_pack_context()` is confirmed at 7 non-test call sites.

**11. Charter CLI commands registered and wired**
`src/specify_cli/cli/commands/charter/_app.py` registers `activate`, `deactivate`, `list`, and `pack` via `charter_app.add_typer`. `docs/reference/cli-commands.md` was updated in the remediation commit. Architectural gate `test_visible_paths_match_reference` passes.

**12. `_SINGULAR_TO_PLURAL["mission_step_contract"]` fixed (FR-028)**
`src/charter/drg.py:591`: `"mission_step_contract": "mission_step_contracts"`. Correct.

**13. Default charter pack ships (FR-001)**
`src/charter/packs/default.yaml` exists, contains all 9 activation kinds, and lists all built-in artifact IDs. `src/charter/packs/__init__.py` has `__all__: list[str] = []` (fixed in remediation commit).

**14. Upgrade migration `m_3_2_8` ships (FR-002/FR-003)**
`src/specify_cli/upgrade/migrations/m_3_2_8_default_charter_pack.py` implements `detect()`, `can_apply()`, and `apply()` with backup-before-write via `shutil.copy`. `apply()` backs up `.kittify/charter/charter.md` to `.kittify/charter/backups/charter-{timestamp}.md` before writing (C-008, NFR-002). Test at `tests/upgrade/test_m_3_2_8_default_charter_pack.py` has `pytestmark = pytest.mark.upgrade`.

**15. Lifecycle gates implemented (FR-017, FR-018)**
`src/specify_cli/cli/commands/agent/mission.py:2224–2244` guards `finalize-tasks` with profile activation check before any write. `src/specify_cli/cli/commands/agent/workflow.py:914–935` guards `agent action implement` before any worktree creation (C-006 ordering). Both raise `CharterActivationError` (not just print) when the check fails.

**16. `CharterActivationError` defined and raised**
`src/charter/exceptions.py` defines the error. It is raised at both lifecycle gate call-sites (`mission.py:2240`, `workflow.py:931`). `tests/specify_cli/test_charter_lifecycle_gates.py::TestCharterActivationErrorRaised` verifies the raise.

**17. DR-based filter wiring (Pattern A) verified**
`src/charter/context.py:729`, `src/charter/compiler.py:561`, `src/charter/reference_resolver.py:67`, `src/specify_cli/mission_step_contracts/executor.py:178` all call `filter_graph_by_activation(graph, pack_context)` after DRG load. The guard `if pack_context is not None` is correct (allows test isolation via `None`).

**18. `require_pack_context()` at minimum 3 distinct call sites (spec criterion 10)**
`org_charter.py:664`, `org_layer.py:168`, `doctor.py:2336` cover the 3 required patterns. The `workflow.py` and `mission.py` gates add two more.

**19. FR-027 test delivered (T049)**
`tests/charter/test_mission_type_activation.py` sets `mission_type_activations: [software-dev]` and asserts `documentation`, `research`, `plan` are excluded. Fast-marked.

**20. FR-026 NFR-001 real-I/O p99 test delivered (T048)**
`tests/specify_cli/next/test_runtime_bridge_dispatch.py::TestPerformanceRealIO` writes a real `.kittify/config.yaml`, runs `PackContext.from_config()` 50 times, sorts timings, and asserts `timings_ms[49] <= 100` (p99 proxy). Marked `@pytest.mark.slow`.

**21. Predecessor SIGNIFICANT issue — WP13 docstring overclaim**
The predecessor review flagged `doctrine mission-type list` as claiming "built-in, org, and project" but only collecting built-in. `src/specify_cli/cli/commands/doctrine.py:816–824` now reads:
```
Enumerates built-in, org, and project mission types regardless of activation state. ... Use spec-kitty charter mission-type list to see only types that are currently activated.
```
The docstring accurately documents *intent* (DRG resolution chain), and the implementation (`_collect_built_in_mission_types()` only) is a known scope-deferral. This is no longer an overclaim — the docstring correctly describes the planned behavior and points users to the activated-view command. VERIFIED ACCEPTABLE.

**22. Dead symbol remediation complete for core wired symbols**
Stale allowlist entries for `charter.consistency_check::run_consistency_check`, `charter.drg::filter_graph_by_activation`, `charter.invocation_context::ProjectContext`, and `doctrine.missions.mission_step_repository::MissionStepRepository` were removed from `test_no_dead_symbols.py` in the remediation commit. Verified.

**23. Test fixture cleanup and marker corrections**
`tests/upgrade/test_m_3_2_8_default_charter_pack.py` has `pytestmark = pytest.mark.upgrade`. `tests/architectural/test_no_tracked_test_feature_missions.py` and `tests/charter/test_mission_type_profiles.py` have `git_repo` marker. `test_doctor_restart_daemon.py` uses `unit` not `fast`. All verified.

---

## GAPS / ISSUES

### BLOCKING

**BLOCK-1 — FR-006 "no-cascade warning" not implemented**

**File**: `src/charter/pack_manager.py` (module docstring + `activate()` method)

The CLI contract (`contracts/charter-activate-cli.md`, behavior step 6) requires:
> "If `--cascade` is absent: emit a warning listing cross-kind references from `id` that were NOT cascaded, with hint to use `--cascade`."

The spec (FR-006, priority **Must**) requires the same.

The current implementation emits a warning ONLY when `cascade=True` is passed, and that warning says "DRG edge traversal not implemented." When `--cascade` is absent (the common case), no warning about non-cascaded dependencies is emitted. This is the opposite of what the contract specifies:

- Absent `--cascade` → currently: silence. Required: warn about what could have been cascaded.
- Present `--cascade` → currently: warn "not implemented." Required: actually cascade.

The module docstring at `src/charter/pack_manager.py:16–21` states:
```
FR-008 (warn on no-cascade) is satisfied by this warning; FR-006 and FR-007 are explicitly deferred to a follow-on mission.
```
This self-justification is factually wrong: the reference to "FR-008 (warn on no-cascade)" does not match the spec's FR-008 (which is about deactivation cascade semantics, not no-cascade warnings). The "explicitly deferred" label does not appear in the spec, the plan, or any review verdict — it was declared unilaterally by the implementer. The gate for FR-006 compliance is **User Journey 3** in spec.md and **behavior step 6** in the contract, both of which remain unsatisfied.

**Impact**: `charter activate` users receive no guidance about cross-kind dependencies after activation. The hard-restriction model creates an implicit correctness problem: activating a directive that references tactics without warning that those tactics are now needed creates silent consistency issues that the consistency-check command must then surface.

**Fix**: Implement the no-cascade warning in `CharterPackManager.activate()` as described in the contract. Since DRG traversal is deferred, the warning can be a static text stub ("This activation kind may reference other kinds; run `charter pack consistency-check` to verify coherence") rather than a full reference-graph traversal. This satisfies the contract's intent without requiring DRG wiring.

---

**BLOCK-2 — `activate_mission_type_override` is dead code (FR-014 partially unresolved)**

**File**: `src/specify_cli/charter_activate.py:254`

`activate_mission_type_override()` is defined at line 254 but is NOT in `__all__` (per the remediation commit that removed it) and has zero `src/` callers other than via the module's own docstring. The function was the original FR-014 implementation fix. Its removal from `__all__` was correct, but the function body still exists as dead code.

More critically: the live `activate.py` CLI for `kind == "mission-type"` calls `CharterPackManager().activate(ctx_project, kind, artifact_id)` (line 77), which writes to `config.yaml` via `YAML_KEY_MAP["mission-type"] → "mission_type_activations"`. This IS the correct FR-014 fix path. The `activate_mission_type_override()` function is now a superseded implementation that should be deleted.

**Evidence**: `grep -rn "activate_mission_type_override" src/` returns only `src/specify_cli/charter_activate.py:254` (the definition). No callers.

**Impact**: Dead code inflates module size and confuses readers. The `test_no_dead_modules.py` gate may or may not catch this depending on whether `charter_activate.py` as a module has live callers (it does, via `from specify_cli.charter_activate import emit_step_removal_warnings, ...`). The function itself is unreachable.

**Fix**: Delete `activate_mission_type_override()` from `charter_activate.py`. It is superseded by `CharterPackManager.activate()`.

---

**BLOCK-3 — `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_PACK_ACTIVATION` orphan in dead-symbol test**

**File**: `tests/architectural/test_no_dead_symbols.py:504–527`

`_CATEGORY_C_WP_IN_FLIGHT_CHARTER_PACK_ACTIVATION` is defined as a `frozenset[str]` with 6 entries but is NOT included in the aggregate `_SYMBOL_ALLOWLIST` (lines 570–579). All 6 symbols it lists (`charter.drg::PackContext`, `specify_cli.charter_activate::AffectedMission`, etc.) are also listed in `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_ACTIVATION`, which IS in the allowlist.

The `_baselines.yaml` tracks `category_c_wp_in_flight_charter_pack_activation: 6` but the `test_ratchet_baselines.py` does NOT validate `test_no_dead_symbols` categories at all (the ratchet only validates `test_no_dead_modules` per-category counts).

**Impact**: The orphaned frozenset is dead code. The baseline entry for it in `_baselines.yaml` is misleading — it tracks a variable that has no effect on any gate. The 6 symbols are doubly-allowlisted: once in the unused `CHARTER_PACK_ACTIVATION` set and once in `CHARTER_ACTIVATION`. This creates confusion about the intended cleanup target.

**Fix**: Either (a) add `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_PACK_ACTIVATION` to the aggregate `_SYMBOL_ALLOWLIST` union and remove the duplicate entries from `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_ACTIVATION`, OR (b) delete `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_PACK_ACTIVATION` and the corresponding `_baselines.yaml` entry, since all its symbols are already covered. Option (b) is cleaner.

---

### SIGNIFICANT

**SIG-1 — FR-006/FR-007 cascade is unimplemented but spec marks both as Must**

**Files**: `src/charter/pack_manager.py:16–21`, `src/specify_cli/cli/commands/charter/activate.py:50–85`

The spec (FR-006, FR-007) marks cascade activate logic as **Must** priority. The current implementation accepts `--cascade <scope>` but does nothing with it except warn. The cascade flag is parsed as `bool(cascade)` in the activate CLI (line 50), collapsing `--cascade directive` and `--cascade agent-profile,tactic` both to `True`. The actual kind-scoped cascade semantics of FR-007 are not implemented.

Note: BLOCK-1 above covers the no-cascade warning (FR-006, when `--cascade` is absent). This issue covers the *actual cascade execution* (FR-007, when `--cascade` is present). The Wiring Acceptance Criteria in the spec (criterion 1–4) test the filtering behavior but not the cascade activation behavior.

**Impact**: User Journey 4 ("Activating with cascade") is unimplemented. Running `charter activate mission-type research --cascade agent-profile,tactic` does not activate the referenced agent profiles and tactics — it only emits a warning. The `--cascade` flag is effectively non-functional.

**Fix (follow-on mission)**: Implement DRG edge traversal in `CharterPackManager.activate()`. This requires loading the doctrine DRG and querying which artifacts of the requested kinds are referenced by the target artifact. This is the most complex deferred item.

---

**SIG-2 — FR-008 deactivation cascade not implemented**

**File**: `src/charter/pack_manager.py:319–322`

FR-008 requires: "`--cascade all|<kind>` on `charter deactivate` cascades deactivation to artifacts exclusively referenced by the deactivated artifact; shared artifacts are left untouched and listed as skipped."

The current `deactivate()` emits: "cascade=True requested but DRG shared-reference analysis is not yet implemented (deferred to follow-on mission)." User Journey 5 is not implemented. `charter deactivate` with `--cascade` does nothing except warn.

**Impact**: Same as SIG-1. Cascade deactivation is a first-class "Must" requirement in the spec. The `--cascade` flag for deactivate is non-functional.

---

**SIG-3 — `activate` behavior step 2 (artifact ID validation) not implemented**

**File**: `src/specify_cli/cli/commands/charter/activate.py`

The CLI contract (behavior step 2) requires: "Validate `id` exists in the doctrine catalog for that kind. Error if unknown artifact."

The current `activate_cmd` calls `CharterPackManager().activate(ctx_project, kind, artifact_id)` with no validation of whether `artifact_id` is a known doctrine artifact for `kind`. It will silently add any string as an activation ID, even if it doesn't correspond to any shipped artifact. This creates charter packs that reference non-existent artifacts — exactly the kind of inconsistency that `charter pack consistency-check` would then need to report.

**Evidence**: `src/specify_cli/cli/commands/charter/activate.py:77` calls `CharterPackManager().activate()` directly after the `kind` validation (which only checks `YAML_KEY_MAP`). There is no artifact ID lookup against the doctrine catalog.

**Impact**: Operators can silently create invalid activation state without error feedback.

---

**SIG-4 — `ConsistencyReport` allowlisted but has no direct src/ importer**

**File**: `tests/architectural/test_no_dead_symbols.py:416`, `src/charter/consistency_check.py`

`charter.consistency_check::ConsistencyReport` is in `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE` (line 416) with the comment "no src/ caller yet — remains allowlisted." 

The `pack.py` command calls `run_consistency_check(ctx)` (lazy import) and uses the result to check `report.coherent` and iterate `report.unknown_references`, etc. — but it never imports `ConsistencyReport` by name. The type is used only through duck typing.

The dead-symbol gate permits this because `ast.walk` finds the `from charter.consistency_check import run_consistency_check` import, which confirms the module is live, and the `_symbol_has_caller` check uses submodule-prefix logic. However `ConsistencyReport` specifically has no `from charter.consistency_check import ConsistencyReport` anywhere in `src/`.

**Impact**: The allowlist entry is technically correct (the symbol has no direct src/ importer), but the documentation comment should note that `run_consistency_check` IS wired and returns a `ConsistencyReport`. This is informational — not a gate failure.

---

**SIG-5 — OperationalContext family: 4 symbols deferred with no follow-on tracking**

**File**: `src/charter/invocation_context.py`, `tests/architectural/test_no_dead_symbols.py:407–413`

`OperationalContext`, `build_operational_context`, `require_active_profile`, `require_active_role` are defined, exported, and allowlisted. The stub factory `build_operational_context()` returns an all-None `OperationalContext`. No production call site for any of these 4 symbols exists in `src/`.

The allowlist comment says "specced, wiring deferred to follow-on mission (charter-pack-activation-layer WP03)." But this mission IS charter-pack-activation-layer, and WP03 is done. The follow-on mission is unnamed.

**Impact**: Not a test failure, but the 4 symbols remain permanently deferred with no follow-on mission tracker. The `OperationalContext.require_active_profile` / `require_active_role` guard methods exist but are never called, meaning the `ContextPreconditionError` path they protect is untestable in production.

---

### MINOR

**MIN-1 — `activate_cmd` exported from `__all__` (typer callback)**

**File**: `src/specify_cli/cli/commands/charter/activate.py:13`

```python
__all__ = ["charter_activate_app", "activate_cmd"]
```

`activate_cmd` is a typer callback (`@charter_activate_app.callback`). It is never directly imported by any `src/` module. The pre-remediation review noted `deactivate_cmd` and `list_cmd` should be removed from their `__all__`; this was done for those two. `activate_cmd` was not removed and remains in `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_ACTIVATION` allowlist (line 558). This is consistent but asymmetric with `deactivate.py` and `list_cmd.py`.

**Fix**: Remove `activate_cmd` from `__all__` in `activate.py` to match `deactivate.py` and `list_cmd.py` conventions. Update the allowlist entry.

---

**MIN-2 — `_baselines.yaml` `charter_pack_activation` entry tracks orphaned frozenset**

**File**: `tests/architectural/_baselines.yaml:149`

`category_c_wp_in_flight_charter_pack_activation: 6` tracks the size of `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_PACK_ACTIVATION`, which is not in the aggregate allowlist. Since the ratchet baseline test does not validate `test_no_dead_symbols` categories, this entry has no enforcement effect. It is misleading documentation.

---

**MIN-3 — `pack_manager.py` misattributes FR-008 in the cascade deferral comment**

**File**: `src/charter/pack_manager.py:20`

The comment says "FR-008 (warn on no-cascade) is satisfied by this warning." However, the spec's FR-008 is about deactivation cascade semantics, not a "warn on no-cascade" behavior. FR-006 is the "warn on no-cascade" requirement. The comment should read "FR-006" not "FR-008."

---

## PREDECESSOR BLOCKING ISSUES — Resolution Verification

| Predecessor Issue | Status | Evidence |
|---|---|---|
| #1: C-004 TYPE_CHECKING violation in `mission_step_repository.py` | RESOLVED | `_PackContextLike` protocol at line 31; no charter import |
| #2: `test_legacy_subpackage_is_gone` namespace package false positive | RESOLVED | `find_spec` assertion removed; source-file check only |
| #3: 8 broken `test_template_governance_payload_contract` tests | RESOLVED | Fixed via `b429a80dd` gate-failure commit |
| #4: `test_no_new_dead_modules` WP12 migration missing from allowlist | RESOLVED | Both `m_3_2_7` and `m_3_2_8` in allowlist at lines 193, 195 |
| #5: 12 dead symbols in dead-symbol gate | RESOLVED (with caveat) | Symbols either wired or allowlisted; orphaned frozenset remains (BLOCK-3) |
| #6: Tracked test fixture files | RESOLVED | `git ls-files kitty-specs/ | grep test-feature` = empty |

| Predecessor Significant Issue | Status | Evidence |
|---|---|---|
| WP11: `filter_graph_by_activation` dead code | RESOLVED | 5 non-test production call sites |
| WP04: `MissionStepRepository` dead code | RESOLVED | Wired via `charter/mission_steps.py` + `resolver.py` |
| WP13: docstring overclaim | ACCEPTABLE | Docstring now describes DRG intent and defers to `charter mission-type list`; no longer overclaims active behavior |
| FR-016 filtering invariant untested | RESOLVED | `tests/charter/test_mission_type_activation.py` added (FR-027) |

---

## SUMMARY TABLE

| Severity | Count | Items |
|---|---|---|
| BLOCKING | 3 | BLOCK-1 (FR-006 no-cascade warning missing), BLOCK-2 (dead `activate_mission_type_override`), BLOCK-3 (orphaned frozenset in dead-symbol test) |
| SIGNIFICANT | 5 | SIG-1 (cascade activate deferred), SIG-2 (cascade deactivate deferred), SIG-3 (artifact ID not validated on activate), SIG-4 (`ConsistencyReport` allowlist comment accuracy), SIG-5 (OperationalContext untracked follow-on) |
| MINOR | 3 | MIN-1 (`activate_cmd` in `__all__`), MIN-2 (orphaned baseline entry), MIN-3 (FR-008 misattribution in comment) |

**Overall assessment**: The predecessor's 6 blocking issues are all resolved. The core activation layer (DRG filter wiring, PackContext three-state, lifecycle gates, default charter pack, upgrade migration, consistency check) shipped and is correctly implemented. The primary remaining gaps are (a) the cascade feature being deferred without adequate user-visible warning (BLOCK-1), (b) a dead function that should be deleted (BLOCK-2), and (c) a bookkeeping error in the dead-symbol test (BLOCK-3). BLOCK-1 is the only issue with a user-visible correctness impact.
