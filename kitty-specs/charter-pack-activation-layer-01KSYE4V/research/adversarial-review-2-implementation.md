# Adversarial Review Round 2: Implementation
**Reviewer**: Pedro (Senior Python Implementer)
**Date**: 2026-05-31
**Focus**: Implementation feasibility, test strategy, concrete code traps

---

## BLOCKING

### B1. FR-039 will break an existing test that is a documented invariant

`spec/data-model.md` says FR-039 requires removing the `and raw` guard from the `from_config()` reader so that `activated_directives: []` is treated as an explicit empty frozenset rather than a fallback to all built-ins.

The existing `_read_activated_kinds` at `pack_context.py:197` reads:
```python
if isinstance(raw, list) and raw:
    return frozenset(str(k) for k in raw)
return _BUILTIN_ARTIFACT_KINDS
```

And there is an existing passing test at `tests/charter/test_pack_context.py:284`:
```python
def test_empty_activated_kinds_uses_builtin_fallback(tmp_path: Path) -> None:
    """An empty activated_kinds list falls back to all built-in kinds."""
    ...
    activated_kinds: []
    ...
    assert ctx.activated_kinds == _BUILTIN_ARTIFACT_KINDS
```

FR-039 says to remove the `and raw` guard from "all per-kind readers." There are two possible interpretations:
- (a) Remove it only from the NEW per-kind readers (`_read_activated_directives`, etc.) — not from the existing `_read_activated_kinds`. This is the only interpretation that does not break the existing test.
- (b) Remove it from `_read_activated_kinds` too, changing existing behavior of `activated_kinds: []`.

The spec text says "The existing `and raw` guard in `_read_activated_kinds` (which collapses `[]` to all built-ins) must be removed from all per-kind readers." This reads as interpretation (b) — remove it from `_read_activated_kinds` too. But the existing test directly asserts the opposite behavior. An implementer following the spec literally will break `test_empty_activated_kinds_uses_builtin_fallback`, and an implementer preserving the existing test will leave the `and raw` guard in `_read_activated_kinds`, giving conflicting three-state semantics between `activated_kinds` (two states: absent or non-empty) and new per-kind fields (three states: absent, empty, non-empty).

This ambiguity must be resolved before implementation. The spec must say explicitly: does `activated_kinds: []` become an explicit empty restriction (breaking the existing test and requiring a coordinated delete of that test), or is `activated_kinds` grandfathered under the old two-state semantics while only new per-kind fields use the three-state model?

---

### B2. `DRGNode` has no artifact ID field — `_node_is_activated` extension for per-artifact-ID filtering requires URN parsing to extract the artifact ID

FR-038 requires extending `_node_is_activated` to check per-kind frozensets. At `drg.py:639`:
```python
def _node_is_activated(node: DRGNode, pack_context: PackContext) -> bool:
    singular, _ = _split_urn(node.urn)
    ...
```

`DRGNode` (at `doctrine/drg/models.py:73`) has `urn: str`, `kind: NodeKind`, `label: str | None`. There is no `artifact_id` field. To get the artifact ID for a per-kind frozenset check, the implementer must extract it from the URN via `urn.split(":", 1)[1]` (or reuse `_split_urn`). This is safe for standard URNs but the comment block at `drg.py:602` says `_split_urn` returns `(urn, "")` for malformed URNs — an empty identifier string on a malformed node would fail a frozenset membership check silently (not in frozenset). 

The spec does not state what happens when the extracted artifact ID is empty or malformed. The existing `_node_is_activated` handles this implicitly (malformed URN → singular is the full URN → not in `_SINGULAR_TO_PLURAL` → `True` / default-allow). But adding per-kind frozenset checks after URN parsing means a malformed-URN node that currently passes through would now potentially be excluded if `pack_context.activated_directives` is non-None and the empty ID is not in the frozenset.

The implementer needs explicit guidance: when the extracted artifact ID is empty (malformed URN), should per-kind frozenset checks be bypassed (default-allow, matching existing behavior) or applied (potentially restricting malformed nodes)?

---

### B3. `_node_is_activated` per-kind frozenset check applies to Pattern A kinds only — paradigm and procedure nodes ARE in the DRG contrary to what research.md states

`research.md §2` classifies `paradigm` and `procedure` as Pattern B (flat catalog, bypass DRG). But `doctrine/drg/models.py:35-38` has `NodeKind.PARADIGM` and `NodeKind.PROCEDURE`. `doctrine/drg/query.py:231,234` confirms `resolve_context()` populates `paradigms` and `procedures` buckets from DRG traversal. `doctrine/drg/org_pack_loader.py:70-71` loads paradigm and procedure nodes from YAML files.

Paradigm and procedure nodes do appear in the DRG. They would be subject to `_node_is_activated` through `_SINGULAR_TO_PLURAL` (at `drg.py:588-591`: `"paradigm": "paradigms"`, `"procedure": "procedures"`). However, `_classify_artifact_urns` in `context.py:318-332` only processes `DIRECTIVE`, `TACTIC`, `STYLEGUIDE`, and `TOOLGUIDE` nodes — it ignores paradigm and procedure URNs from the DRG even when present.

The research.md classification "Pattern B — flat catalog (paradigm, procedure) — bypass the DRG entirely" is therefore half-wrong: they exist in the DRG but are not extracted by the charter context builder's DRG classification path. The wiring for per-kind filtering of paradigms and procedures needs to target both:
1. The flat catalog path (DoctrineService `.paradigms` / `.procedures` properties) — research's Pattern B.
2. Any DRG traversal path that returns paradigm/procedure URNs to callers other than `_classify_artifact_urns`.

FR-038 says extend `_node_is_activated` for paradigm/procedure but the filter only has effect if those nodes reach `filter_graph_by_activation`. Since `_load_action_doctrine_bundle` discards them, an implementer who only wires `filter_graph_by_activation` into `_load_action_doctrine_bundle` will have technically wired the filter but paradigm/procedure activation will still not be enforced for the charter context command. The working implementation requires a separate fix in the flat catalog path regardless of whether `_node_is_activated` is extended.

---

### B4. `mission_step_contract` mapping mismatch: `_SINGULAR_TO_PLURAL` maps to `"mission_steps"` but `PackContext._BUILTIN_ARTIFACT_KINDS` has `"mission_step_contracts"`

At `drg.py:592`:
```python
_SINGULAR_TO_PLURAL: dict[str, str] = {
    ...
    "mission_step_contract": "mission_steps",
}
```

At `pack_context.py:58`:
```python
_BUILTIN_ARTIFACT_KINDS: frozenset[str] = frozenset(
    {
        ...
        "mission_step_contracts",
    }
)
```

`"mission_steps"` != `"mission_step_contracts"`. When `_node_is_activated` is called with a `mission_step_contract` node that is ownerless (no owner recovered from URN, so it falls through to the kind filter at line 660), `plural = _SINGULAR_TO_PLURAL.get("mission_step_contract")` returns `"mission_steps"`. Then `"mission_steps" in pack_context.activated_kinds` checks against a set that contains `"mission_step_contracts"` — the check always returns `False`, meaning ownerless mission-step-contract nodes are always excluded regardless of the `activated_kinds` setting.

This is an existing bug that the spec does not acknowledge. FR-038 requires adding per-kind frozenset checks for `activated_mission_step_contracts` — but the `PackContext` field and YAML key are both spelled `activated_mission_step_contracts` (plural with 's') while `_SINGULAR_TO_PLURAL["mission_step_contract"]` = `"mission_steps"` (no final 's'). The mapping that would dispatch from the node's kind to the new `PackContext.activated_mission_step_contracts` field is broken before the implementer even starts. This must be resolved before attempting FR-038 for this kind.

---

### B5. The upgrade migration's `detect()` condition is too narrow — partial upgrades are invisible

`research.md §5` specifies: `detect(): project has .kittify/ AND no activated_directives in config.yaml`.

This single-key check means:
- If a user manually added `activated_directives` to config.yaml before running upgrade (e.g., copied from documentation), the migration detects the key and skips. All other per-kind keys (`activated_tactics`, `activated_styleguides`, etc.) will remain absent. The project is in a partial state: `activated_directives` is an explicit frozenset, all others are `None` (fallback to all built-ins). The migration never fires again because `detect()` returns False.
- If the migration ran on one machine and the user cloned to another machine, the per-kind keys are present — migration skips. This is correct, but there is no validation that ALL per-kind keys are populated.

The deeper problem: there is no "check that all 9 per-kind keys are present" step. The migration is all-or-nothing on a single-key signal. A project that went through a partial state (any one per-kind key present) is silently treated as fully migrated, and all other kinds stay in `None` (backwards-compat fallback) indefinitely without any warning.

An implementer needs to decide whether `detect()` should check all 9 per-kind keys are absent (fire if ANY is missing) or only check `activated_directives`. Neither approach is specified for the partial-upgrade case.

---

### B6. `ProjectContext.from_repo()` error propagation is unspecified — `PackContext.from_config()` silently swallows config.yaml absence

`pack_context.py:166-187` (`_load_config`): if `.kittify/config.yaml` is absent, returns `{}` (empty dict), which triggers the backward-compat fallback — all built-in kinds active, all four mission types active. No error is raised.

`data-model.md` specifies `ProjectContext.from_repo(cls, repo_root: Path) -> "ProjectContext"` with pack_context populated from `PackContext.from_config(repo_root)`. When config.yaml is absent:
- `from_config()` returns a default-filled `PackContext` (no error).
- `from_repo()` successfully constructs a `ProjectContext` where `pack_context` has all defaults.
- Guards `require_pack_context()` would succeed — no error raised — even on a project without any kittify config.

Then `CharterPackManager.activate()` is called from a CLI command with this `ProjectContext`. `ctx.require_pack_context()` passes. The manager writes a new `activated_directives` key to config.yaml. But if `.kittify/` itself does not exist, the write will fail with a FileNotFoundError at the ruamel.yaml dump step, not at the `require_pack_context()` guard. The guard fires on field presence, not on filesystem validity — the `PackContext` field is always populated (even with fallback defaults).

This means `require_pack_context()` provides no protection against "not a kittify project" scenarios. An implementer who relies on the guard to catch "not a kittify project" will be surprised when the guard passes and the write fails later. The correct guard is "does `.kittify/config.yaml` exist" — but that logic lives inside `_load_config`, which has already run by the time the guard is consulted. Specify what the guard is supposed to catch and what it explicitly does not catch.

---

### B7. CascadeScope naming in data-model is inconsistent with FR-007 and the CLI contract — only 3 of 8 non-mission-type kinds have named cascade values

`data-model.md` CascadeScope table names: `profiles`, `directives`, `tactics` (plus `all`, `none`). `plan.md` Literal: `"none" | "all" | "profiles" | "directives" | "tactics"`.

`charter-activate-cli.md` says `--cascade: all, profiles, directives, tactics, or comma-separated subset`. `charter-deactivate-cli.md` says the same.

The activation kinds include `styleguide`, `toolguide`, `paradigm`, `procedure`, `agent_profile` (as distinct from `profile`), `mission-step-contract`. An implementer building the `--cascade` flag parser from the data model's CascadeScope table will build a parser that accepts only `profiles, directives, tactics, all, none`. A user running `charter activate directive python-style-guide --cascade styleguides` would get a validation error even though FR-007 explicitly says `--cascade all|<kind>[,<kind>...]` with comma-separated kinds.

The two surfaces are incompatible: FR-007 says accept any kind name as a cascade target; the CascadeScope table only enumerates 3 named values. An implementer writing strict Literal typing against the table will make the command reject valid cascade targets that the spec explicitly promises.

---

## SIGNIFICANT

### S1. `charter context` requires `--action` flag — success criteria 11 and 12 are untestable as written

Success criteria 11 and 12 say "running `charter context` produces exactly that subset" and "running `charter context` produces zero directives." The actual command signature at `src/specify_cli/cli/commands/charter/context.py:21` is:

```python
def context(
    action: str = typer.Option(..., "--action", help="..."),
    ...
```

The `...` default means `--action` is required. `spec-kitty charter context` without `--action` exits with a usage error. The success criteria do not specify which action to use for the verification test. For an integration test, the implementer must choose an action (e.g., `--action implement`) — but the number of directives returned depends on the DRG edges from that action node, not just the activation state. A test could pass criterion 11 ("only that subset appears") even if the filter is not working, if the chosen action has no DRG edges to any directive other than the one activated.

The correct test shape for criterion 11 is: activate exactly one directive ID; call `charter context --action <action> --json`; check that `all_directives` (not `directives`) contains exactly that one ID and no others. The `all_directives` field in the JSON payload shows all project-scoped directives, not just action-scoped ones. But the test criteria reference "charter context" without specifying `--json` or which field to check.

An implementer writing this acceptance test will make arbitrary choices that may not actually verify the end-to-end filter.

---

### S2. `OperationalContext` is specced but `build_operational_context(...)` has no specified source for its fields

`data-model.md` specifies `src/specify_cli/context/factory.py` provides `build_operational_context(...) -> OperationalContext` where `specify_cli` knows how to read `active_model`, `active_profile`, `active_role` from "CLI state." The existing `src/specify_cli/context/` package contains `errors.py`, `middleware.py`, `mission_resolver.py`, `models.py`, `resolver.py`, `store.py` — none of which relate to model/profile/role state.

There is no existing mechanism in the codebase for resolving "current active_model" or "current active_role" from CLI state. These would need to come from environment variables, config.yaml `agents` section, WP frontmatter, or the agent runtime context — none of which are specified. The `OperationalContext` is marked "specced but not wired in this mission, wiring deferred to follow-on," which means `build_operational_context` is being created in this mission without any specification of how it actually reads its fields.

An implementer creating `context/factory.py:build_operational_context(...)` will invent the field population logic from scratch. Whatever they invent will become the de-facto contract for a follow-on mission that tries to actually wire it. The spec should either provide the population logic or omit `build_operational_context` from this mission's scope (leaving only `build_project_context`).

---

### S3. `CharterPackManager.activate()` from `None` state requires enumerating all built-in artifact IDs — the source is underspecified

`data-model.md` says: "If None: initialize to all built-ins, then add." The source is described as `src/charter/packs/default.yaml` (the file being created in this mission). But `default.yaml` does not exist yet — it is a deliverable of this mission, not a pre-existing file. The initialization path in `activate()` reads a file that is simultaneously being authored by the same implementer.

If `default.yaml` is incomplete or contains wrong IDs at the time `activate()` is first tested, the initialization produces the wrong starting set. More importantly: if an implementer tests `activate()` before `default.yaml` is fully populated (e.g., during WP-by-WP implementation), the test will pass with a wrong starting set and the error will only be caught when a later WP populates `default.yaml` correctly.

The implementation order matters: `default.yaml` must be complete before `CharterPackManager.activate()` from-`None` path is tested. This dependency between WPs must be explicit in the task sequencing or the from-`None` path must have a guard that fails fast when `default.yaml` is absent.

---

### S4. `test_no_dead_symbols.py` has two independent failure causes — FR-024 addresses only one

`test_no_dead_symbols.py` at line 118 has `"doctrine.missions.models::MissionStep"` in `_CATEGORY_B_GRANDFATHERED_LEGACY`. The first adversarial review (A5) noted this is stale because `MissionStepRepository` now has live callers via `mission_step_repository.py:37` (`from .models import MissionStep`). However, looking at the actual test implementation at lines 719-751, the test uses `assert not messages` which catches both:
1. Dead symbols (those in `__all__` with no src/ callers) — FR-024 addresses 12 specific symbols.
2. Stale allowlist entries (symbols in the allowlist that now have live callers) — the `MissionStep` allowlist entry check.

FR-024 says "wire or allowlist 12 dead symbols." It does not say "remove stale allowlist entries." If the `MissionStep` allowlist entry is stale (the symbol has callers), the test will report a "stale entry" failure even after all 12 dead symbols are addressed. The plan's structure (plan.md line 93: `test_no_dead_symbols.py — Wire or allowlist 12 dead symbols`) does not mention removing the `MissionStep` stale entry as a required step.

Verify: does `doctrine.missions.models::MissionStep` now have a non-test caller in `src/`? `mission_step_repository.py:37` is in `src/doctrine/` and imports it at module level (`from .models import MissionStep`). The dead-symbols scanner counts module-level imports as callers. If that import counts, `MissionStep` has a live caller and the allowlist entry is stale — the test will fail with a "stale entry" message that the implementer did not anticipate from FR-024's scope.

---

### S5. NFR-001 performance test uses full mocks — FR-026 extension requires real YAML I/O against real doctrine layout with no fixture specification

`tests/specify_cli/next/test_runtime_bridge_dispatch.py:260` (`TestPerformance.test_resolve_action_sequence_within_100ms`):
```python
mock_repo = MagicMock()
mock_repo.get.side_effect = lambda k: sw_dev if k == "software-dev" else None
saved = _inject_mission_type_repository_mock(mock_repo)
```
The test patches `MissionTypeRepository` with a mock that returns immediately. It measures import-cache warmup, not I/O.

FR-026 says: "add a real-filesystem scenario that exercises actual YAML loading and `PackContext` construction against a non-mocked doctrine layout." The plan (plan.md line 104) references `test_runtime_bridge_dispatch.py` as the file to modify.

There is no specification of:
- What fixture layout to create (how many directives, tactics, etc.)?
- Whether to use the real `src/doctrine/` directory or a tmp_path copy?
- What timing methodology to use (monotonic time, `timeit`, pytest-benchmark)?
- What the warm vs cold distinction means in this context?
- How to ensure the test is not flaky on CI (slow machines, tmpfs vs real disk)?

An implementer writing this test will invent all fixture and timing details. The spec says "≤ 100ms p99" but the test uses `elapsed_ms < 100` (single run, no percentile). FR-026 adds a real-I/O test but specifies only the outcome threshold, not the methodology. A single-run `< 100ms` test on a real filesystem can fail intermittently on CI machines without being a real performance regression.

---

### S6. FR-037 scope is incomplete — `doctor.py:2332` is a known production caller of `load_org_charter_policies(repo_root)` without `pack_context`, confirmed in the prior review (A4), and remains unaddressed in FR-037's scope

From the prior review (A4), `src/specify_cli/cli/commands/doctor.py:2332` calls:
```python
policy = load_org_charter_policies(repo_root)
```
without `pack_context`. This is a production caller that would run `spec-kitty doctor` without activation filtering.

FR-037 says "all call sites that currently pass `pack_context=None` are updated." The research wiring table lists only lines 660 and 710 inside `org_charter.py` itself and line 161 in `org_layer.py`. `doctor.py:2332` is not in the wiring table and is not referenced in FR-037's scope or plan.md's file list.

The prior review flagged this as BLOCKING (A4). The updated spec added FR-038/FR-039/FR-040 in response but did not add `doctor.py:2332` to FR-037's scope or to any plan change entry. An implementer reading only this version of the spec will miss this call site.

---

### S7. Wiring acceptance criterion 2 is untestable as specified — "trigger a review dispatch" is not a unit-testable action

Wiring acceptance criterion 2: "Deactivate a specific tactic in the charter. Trigger a review dispatch. Assert that tactic is absent from the resolved prompt context."

"Trigger a review dispatch" requires:
1. A WP in `for_review` state in a real feature directory
2. A running `spec-kitty next` process that selects a review dispatch
3. The runtime bridge reading charter context

This is a full integration test requiring a git repo, a feature with status events, a reviewable WP, and the full next command pipeline. It cannot be written as a unit test or even a standard integration test without a complete scaffolded project. The acceptance criterion gives no indication of what scaffolding is needed or what command to run.

Contrast with criterion 1 (deactivate kind, run `charter context --action implement --json`, assert zero directives) which is clearly implementable as a CLI integration test with a tmp_path project fixture.

---

## MINOR

### M1. `test_org_charter_pack_context.py:65` stale kind string

`tests/specify_cli/doctrine/test_org_charter_pack_context.py:65`:
```python
"mission_step_contracts",
```
This is in `PackContext(activated_kinds=frozenset({..., "mission_step_contracts", ...}))`. The canonical plural kind in `_BUILTIN_ARTIFACT_KINDS` at `pack_context.py:58` is also `"mission_step_contracts"` — so this is NOT stale today. FR-028 says "correct this to the current canonical kind identifier," but the current canonical kind in `_BUILTIN_ARTIFACT_KINDS` IS `"mission_step_contracts"`. What FR-028 intends is unclear — either the FR is wrong about the stale string, or `_BUILTIN_ARTIFACT_KINDS` is the stale thing (should be `"mission_steps"` per `drg.py:592`). Confirm which is the canonical string before making this change, otherwise the "fix" may introduce a different inconsistency.

---

### M2. `test_legacy_subpackage_is_gone` already uses source-file checks, not `find_spec` alone

FR-021 says "replace the `find_spec` assertion with a source-file-only check." Reading `test_layer_rules.py:196-223`, the test already does a source-file check first (lines 209-215: checks `__init__.py`, `models.py`, `repository.py`) and THEN calls `find_spec` (line 219) as an additional assertion. The test is already a hybrid. FR-021 says to remove `find_spec` — but this is safe only if the source-file check is sufficient. If a `.pyc` file causes the package to remain importable despite source removal, the `find_spec` check catches it. Confirm whether namespace package semantics (the stated cause in the spec) specifically affects `find_spec` but not the source-file check, and whether the source check alone is sufficient to guarantee the package is unimportable.

---

### M3. Migration `detect()` guard reads config.yaml twice — and ignores `can_apply()` edge case when config.yaml exists but contains non-dict YAML

In `m_3_2_7` pattern: `detect()` loads with `YAML(typ="safe")` and returns `False` on exception. `apply()` loads again with round-trip YAML. If config.yaml is modified between `detect()` and `apply()` (e.g., another process writes it), `apply()` may encounter a different state. This is acceptable and documented as a known limitation in the migration framework. But the new `m_3_2_8` migration reads `default.yaml` from `src/charter/packs/default.yaml` at runtime during `apply()`. If the package is installed editable and `default.yaml` is missing (e.g., a broken install where only the `.py` files were deployed), `apply()` will raise `FileNotFoundError` inside an `apply()` call, producing an unformatted exception rather than a `MigrationResult(success=False, errors=[...])`. The migration should explicitly guard for `default.yaml` absence.

---

### M4. `activated_kinds` and new per-kind keys create three naming conventions — `mission-type` dispatch is still the odd one out

The dispatch logic in `CharterPackManager` must write to `mission_type_activations` for `kind="mission-type"` but to `activated_<kind>` for all others. This is specified in `data-model.md` ActivationKind table. However the `activate()` method signature `activate(repo_root, kind, artifact_id, cascade) -> ActivationResult` takes `kind` as a string. The dispatch:
```python
if kind == "mission-type":
    key = "mission_type_activations"
else:
    key = f"activated_{kind.replace('-', '_')}s"
```
is not in the spec; an implementer will invent it. The pluralization rule (append `s`) breaks for `"agent-profile"` → `"activated_agent_profiles"` (note: `"agent-profiles"` with an `s` appended is `"activated_agent-profiles"` — needs underscore substitution AND pluralization). The data-model table maps this correctly but does not document the pluralization algorithm. An implementer who writes a general-purpose mapper instead of using the explicit table will get it wrong for hyphenated kinds.

---

### M5. Prior review items A12 and A13 remain open

**A12 (`charter.drg::PackContext` dead re-export)**: `PackContext` is in `charter.drg.__all__` at line 81. FR-024 says "wire or allowlist 12 dead symbols" but does not specifically address removing `PackContext` from `__all__` in `charter.drg`. If `PackContext` is imported only from `charter.pack_context` in production and never from `charter.drg`, this is a stale re-export. The plan does not confirm whether it will be removed or added to the allowlist.

**A13 (migration rc testing)**: The migration's `target_version = "3.2.8"` will not fire during rc testing (`Version("3.2.8") > Version("3.2.0rc30")`). This is now noted in the data-model but is not reflected in the task strategy. Tests for `m_3_2_8` must call `detect()` and `apply()` directly. If any test author writes a standard migration integration test that goes through the upgrade pipeline with the current rc version, the migration will not fire and the test will give a false green.

---

## VERIFIED

| Claim | Status |
|-------|--------|
| `filter_graph_by_activation` at `drg.py:666` has zero non-test, non-`__all__` callers in `src/` | Confirmed |
| `PackContext` is a stdlib `@dataclass(frozen=True)`, not Pydantic | Confirmed |
| `_node_is_activated` checks `activated_kinds` only (kind-level), no per-artifact-ID check | Confirmed |
| `src/charter/packs/` directory does not exist yet | Confirmed |
| `src/charter/invocation_context.py` does not exist yet | Confirmed |
| `charter list`, `charter deactivate`, `charter pack` commands do not exist yet | Confirmed |
| `spec-kitty charter context` exists and requires `--action` flag (not optional) | Confirmed at `context.py:21` |
| `doctor.py:2332` calls `load_org_charter_policies(repo_root)` without `pack_context` — 4th production caller not in FR-037 wiring table | Confirmed |
| `PackContext` from-config does NOT raise when config.yaml is absent — returns default-filled instance | Confirmed at `pack_context.py:174-175` |
| `_SINGULAR_TO_PLURAL["mission_step_contract"]` = `"mission_steps"` (without trailing 's'), while `_BUILTIN_ARTIFACT_KINDS` has `"mission_step_contracts"` — mismatch exists today | Confirmed |
| Existing test `test_empty_activated_kinds_uses_builtin_fallback` asserts `activated_kinds: []` → all built-ins | Confirmed at `test_pack_context.py:284` |
| NFR-001 performance test uses full MagicMock — no real filesystem I/O | Confirmed at `test_runtime_bridge_dispatch.py:263` |
| `NodeKind` enum has `PARADIGM` and `PROCEDURE` — these kinds appear in DRG; `_classify_artifact_urns` in `context.py` discards them | Confirmed |
| `specify_cli.*` CAN import `charter.*` (layer direction is allowed) | Confirmed from existing imports |
| `m_3_2_7` migration pattern (ruamel.yaml round-trip, `preserve_quotes=True`, `detect()` checking key absence) — valid template for `m_3_2_8` | Confirmed |

---

## SUMMARY TABLE

| ID | Severity | File/Location | Description |
|----|----------|---------------|-------------|
| B1 | BLOCKING | `pack_context.py:197`, `test_pack_context.py:284` | FR-039 and existing test contradict each other on `activated_kinds: []` semantics |
| B2 | BLOCKING | `drg.py:639` | `DRGNode` has no artifact ID field; per-kind frozenset check requires URN parsing with unspecified malformed-URN behavior |
| B3 | BLOCKING | `context.py:318-332`, `drg/query.py:231,234` | Paradigm/procedure ARE in DRG; research Pattern B classification is wrong; wiring plan covers wrong code path |
| B4 | BLOCKING | `drg.py:592`, `pack_context.py:58` | `_SINGULAR_TO_PLURAL["mission_step_contract"]` = `"mission_steps"` but `activated_kinds` uses `"mission_step_contracts"` — ownerless MSC nodes always excluded today; per-kind check mapping is broken before FR-038 |
| B5 | BLOCKING | `research.md §5` | Migration `detect()` single-key check makes partial upgrades invisible and unrecoverable |
| B6 | BLOCKING | `pack_context.py:166-187`, `data-model.md` | `require_pack_context()` guard always passes (from_config never raises); guard does not protect against "not a kittify project" |
| B7 | BLOCKING | `data-model.md CascadeScope`, `charter-activate-cli.md` | CascadeScope table names only 3 of 8 cascade kinds; `--cascade styleguides` would be rejected by a strict parser built from the table |
| S1 | SIGNIFICANT | `spec.md SC11,SC12`, `context.py:21` | Success criteria 11/12 require `--action` flag but don't specify which action; test can give false green depending on DRG edges |
| S2 | SIGNIFICANT | `data-model.md`, `specify_cli/context/` | `build_operational_context(...)` field population source (model/profile/role) is completely unspecified |
| S3 | SIGNIFICANT | `data-model.md`, `pack_manager.py` | `activate()` from-`None` reads `default.yaml` which is a co-deliverable of this mission — ordering dependency is not explicit |
| S4 | SIGNIFICANT | `test_no_dead_symbols.py:118` | `MissionStep` allowlist entry is likely stale (has caller in `mission_step_repository.py:37`); causes separate test failure not addressed by FR-024 |
| S5 | SIGNIFICANT | `test_runtime_bridge_dispatch.py:260` | FR-026 real-I/O extension has no fixture specification, timing methodology, or flakiness protection |
| S6 | SIGNIFICANT | `doctor.py:2332` | Confirmed 4th `load_org_charter_policies` caller without `pack_context` — missing from FR-037 scope (prior review A4, still open) |
| S7 | SIGNIFICANT | `spec.md Wiring AC 2` | "Trigger a review dispatch" requires full project scaffold + running next command; untestable as a standard acceptance criterion |
| M1 | MINOR | `test_org_charter_pack_context.py:65`, FR-028 | FR-028 calls the string "stale" but it matches current `_BUILTIN_ARTIFACT_KINDS` — either FR-028 or `_BUILTIN_ARTIFACT_KINDS` is wrong |
| M2 | MINOR | `test_layer_rules.py:196-223`, FR-021 | Test already uses source-file check + `find_spec`; removing `find_spec` leaves gap if `.pyc` files persist |
| M3 | MINOR | `m_3_2_8` migration | `default.yaml` absence during `apply()` will raise unformatted `FileNotFoundError` rather than `MigrationResult(success=False)` |
| M4 | MINOR | `data-model.md`, `pack_manager.py` | `kind="agent-profile"` → `activated_agent_profiles` pluralization rule is not documented; general-purpose mapper will get it wrong |
| M5 | MINOR | `drg.py:81`, `test_no_dead_symbols.py` | Prior A12 (stale `PackContext` re-export in `charter.drg.__all__`) and A13 (migration rc test strategy) remain unaddressed in spec or plan |
