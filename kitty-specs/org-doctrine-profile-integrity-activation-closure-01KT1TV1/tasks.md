# Tasks: Org Doctrine Profile Integrity Activation Closure

**Branch**: `mission/org-doctrine-profile-integrity-activation-closure` (planning/base = merge target)
**Mission**: `org-doctrine-profile-integrity-activation-closure-01KT1TV1`
**change_mode**: `bulk_edit` — see [occurrence_map.yaml](occurrence_map.yaml) (governs WP06/WP07)

18 work packages, 80 subtasks, sequenced by dependency across 5 waves. Tests are included (charter C-011 ATDD-First is binding).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | `ArtifactKind.from_operator_token` (hyphen→canonical) + mission-type sentinel | WP01 | |
| T002 | Artifact ID resolver (config-stem ↔ DRG URN via `id:`) in `charter/kind_vocabulary.py` | WP01 | |
| T003 | Unit tests: token normalization, unknown-token error, ID round-trip | WP01 | |
| T004 | Document canonical charter kind universe (ArtifactKind + mission-type) | WP01 | |
| T005 | Add `Relation.SPECIALIZES_FROM` | WP02 | |
| T006 | Add `DRGGraph.edges_to` reverse adjacency | WP02 | [P] |
| T007 | No-leak regression test (`DELEGATES_TO` filter excludes lineage) | WP02 | |
| T008 | Unit tests: edges_to + enum | WP02 | |
| T009 | Create `doctrine/drg/merge.py` — relocated `merge_three_layers` (data-in) | WP03 | |
| T010 | Reduce `charter/drg.py` to caller + activation filtering; fix org-fragment silent-drop | WP03 | |
| T011 | Behavior-preservation + layer-rule tests | WP03 | |
| T012 | Normalize org-vs-project fragment relation handling parity | WP03 | |
| T013 | Single-source augmentation kind set (loader + validator) | WP04 | |
| T014 | Emit augmentation + `specializes_from` edges from fragments (not fields) | WP04 | |
| T015 | Extend augmentation eligibility to directive/toolguide/step-contract/mission-type | WP04 | |
| T016 | Validator intent-aware parity for new kinds | WP04 | |
| T017 | Mission-type augmentation resolution + contract-test sweep (FR-032) | WP04 | |
| T018 | Topology field-merge semantics (step-contract/mission-type) | WP04 | |
| T019 | `SkippedProfile` record (`agent_profiles/diagnostics.py`) | WP05 | |
| T020 | Route all drop sites through `_record_skip`; `skipped_profiles()` accessor (sorted) | WP05 | |
| T021 | Collapse 3 layer loops into one shared per-layer loader; sort scans | WP05 | |
| T022 | Preserve diagnostics on `DoctrineService` | WP05 | |
| T023 | Migrate lineage resolver to DRG `SPECIALIZES_FROM` traversal | WP05 | |
| T024 | Tests: determinism, valid-only list_all, lineage via DRG, zero built-in diagnostics | WP05 | |
| T025 | Remove `enhances`/`overrides` from Tactic/Styleguide/Paradigm/Procedure models | WP06 | |
| T026 | Remove `enhances`/`overrides`/`specializes_from` from agent-profile schema + profile.py | WP06 | |
| T027 | `extra=forbid` rejects keys with actionable error | WP06 | |
| T028 | Tests: field-rejection negative tests per kind | WP06 | |
| T029 | Migrate built-in relationships from fields to `graph.yaml` fragment edges | WP07 | |
| T030 | Add profile-to-profile `specializes_from` + augment-all-kinds fixtures | WP07 | |
| T031 | Zero-loss migration test (count/identity diff pre/post) | WP07 | |
| T032 | DRG docs: lineage vs delegation/enhancement/override/replacement (FR-004) | WP07 | [P] |
| T033 | Update `occurrence_map.yaml` serialized_keys/tests_fixtures as executed | WP07 | |
| T034 | `DoctrineHealthReport` + `PackHealth` model | WP08 | |
| T035 | Refactor `doctrine_check` to build report once; render human from report | WP08 | |
| T036 | Render JSON from report; FR-010 `healthy = valid==discovered` | WP08 | |
| T037 | Split long methods (`doctrine_check`, `_build_selection_block`) | WP08 | |
| T038 | Tests: degraded pack human+JSON, ≤2s budget | WP08 | |
| T039 | Derive `YAML_KEY_MAP`/`_KIND_TO_DOCTRINE_DIR` from canonical resolver | WP09 | |
| T040 | Extend `list_available` to org/project layers (roots as data, C-008) + id-aware | WP09 | |
| T041 | Decouple layer from kind dir; reuse `ArtifactKind.glob_pattern` | WP09 | |
| T042 | Delegate `activate`/`deactivate` bodies to `activation_engine` (thin) | WP09 | |
| T043 | Tests: list_available across layers, kind-table parity | WP09 | |
| T044 | `activation_engine.py`: `ActivationPlan` + `plan_activation` (validate before mutate) | WP10 | |
| T045 | `commit_plan` single write; defaults materialized in plan, not on failure | WP10 | |
| T046 | Unknown-ID actionable error + recovery; FR-021 backward compat | WP10 | |
| T047 | Tests: non-mutation byte-compare on failure, unknown-id exit code | WP10 | |
| T048 | `cascade.py`: `CascadeScope` value object (`all` vs kind set) | WP11 | |
| T049 | Cascade activation via `walk_edges`/`resolve_transitive_refs` by scope | WP11 | |
| T050 | No-cascade skipped-reference warning (FR-013) | WP11 | |
| T051 | Shared-reference deactivation via `edges_to` reverse reachability (C-005) | WP11 | |
| T052 | Tests: scoped activation, `all` shorthand, exclusive vs shared skip | WP11 | |
| T053 | Thread `--cascade` scope (stop bool collapse) in activate/deactivate | WP12 | |
| T054 | Catch `CharterPackConfigError` fail-closed in activation entry (FR-035) | WP12 | |
| T055 | Generalize `kind=="mission-type"` block behind engine/plan | WP12 | |
| T056 | Normalize sub-app exports (one registration pattern); remove dead export (FR-020) | WP12 | |
| T057 | Fix FR-008 comment misattribution in `_app.py` | WP12 | |
| T058 | Tests: cascade scope CLI, fail-closed message, registration | WP12 | |
| T059 | `build_operational_context` pure explicit-param assembler | WP13 | |
| T060 | `require_active_profile`/`require_active_role` raise `ContextPreconditionError` | WP13 | |
| T061 | Tests: guards raise with realistic context; all-None stub gone | WP13 | |
| T062 | Wire OC at `implement.py` claim | WP14 | |
| T063 | Wire OC at `agent/workflow.py` claim | WP14 | |
| T064 | Wire OC at `runtime_bridge.decide_next` (extracted helper, no C901 growth) | WP14 | |
| T065 | Tests: populated context per site; NFR-004 no worktree/status on fail | WP14 | |
| T066 | Remove 7 stale `_SYMBOL_ALLOWLIST` entries (FR-036) | WP15 | |
| T067 | Remove OperationalContext allowlist entries (FR-019) post-wiring | WP15 | |
| T068 | Delete orphaned empty category; allowlist-with-tracker for 2 git/lanes offenders | WP15 | |
| T069 | Tests: dead-symbol gate passes for in-scope symbols | WP15 | |
| T070 | Add `--all` flag (implies `--show-available`) | WP16 | |
| T071 | Annotate artifacts by source layer; include `template` kind | WP16 | |
| T072 | Tests: `list --all` shows built-in/org/project + template | WP16 | |
| T073 | Route `--include` through `from_operator_token`; agent-profile hyphen works | WP17 | |
| T074 | Collapse renderer table onto canonical kinds; advertise agent-profile in help | WP17 | |
| T075 | Wire `template:<id>` resolution in `--include` | WP17 | |
| T076 | Tests: agent-profile include human+JSON, template include, hyphen kinds | WP17 | |
| T077 | Template discovery surface (enumerate tiers/missions, annotate tier) | WP18 | |
| T078 | Mint DRG template nodes with mission-qualified IDs (`template:<mission>/<name>`) | WP18 | |
| T079 | Resolution by template ID (resolver integration) | WP18 | |
| T080 | Tests: discovery, cross-mission disambiguation, DRG-addressable | WP18 | |

---

## Wave 0 — Foundation

### WP01 — Canonical kind & ID vocabulary resolver
- **Goal**: One canonical mapping from operator tokens to kinds and from config IDs to DRG URNs (R-009/FR-027), so downstream WPs stop re-declaring the kind set.
- **Priority**: P0 (unblocks WP09/WP16/WP17). **Independent test**: `from_operator_token("agent-profile") == AGENT_PROFILE`; ID round-trip.
- **Subtasks**: - [ ] T001 (WP01) · - [ ] T002 (WP01) · - [ ] T003 (WP01) · - [ ] T004 (WP01)
- **Dependencies**: none. **Prompt**: [tasks/WP01-kind-id-vocabulary.md](tasks/WP01-kind-id-vocabulary.md) (~220 lines)

### WP02 — DRG relation vocabulary + reverse index
- **Goal**: Add `SPECIALIZES_FROM` (distinct from `DELEGATES_TO`) and `DRGGraph.edges_to` (FR-001/002).
- **Priority**: P0. **Independent test**: no-leak guard; edges_to reverse adjacency.
- **Subtasks**: - [x] T005 (WP02) · - [x] T006 (WP02) · - [x] T007 (WP02) · - [x] T008 (WP02)
- **Dependencies**: none. **Prompt**: [tasks/WP02-drg-relation-reverse-index.md](tasks/WP02-drg-relation-reverse-index.md) (~210 lines)

### WP03 — Relocate three-layer merge into doctrine
- **Goal**: Move `merge_three_layers` into `doctrine/drg/merge.py` (doctrine owns merge; charter aggregates), fix org-fragment silent-drop (C-009/OQ-2-ii, FR-003).
- **Priority**: P0. **Independent test**: layer-rule passes; merged graph identical to pre-relocation.
- **Subtasks**: - [ ] T009 (WP03) · - [ ] T010 (WP03) · - [ ] T011 (WP03) · - [ ] T012 (WP03)
- **Dependencies**: WP02. **Prompt**: [tasks/WP03-relocate-drg-merge.md](tasks/WP03-relocate-drg-merge.md) (~250 lines)

---

## Wave 1 — Diagnostics Integrity

### WP04 — Augmentation auto-emit single-source + parity
- **Goal**: Emit augmentation + lineage edges from fragments; single-source kind set; extend to 4 kinds; mission-type resolution; topology semantics (FR-028/029/030/031/032).
- **Priority**: P1. **Independent test**: fragment augmentation validates for all kinds; validator parity.
- **Subtasks**: - [ ] T013 · - [ ] T014 · - [ ] T015 · - [ ] T016 · - [ ] T017 · - [ ] T018 (WP04)
- **Dependencies**: WP01, WP02. **Prompt**: [tasks/WP04-augmentation-autoemit-parity.md](tasks/WP04-augmentation-autoemit-parity.md) (~340 lines)

### WP05 — Agent-profile load diagnostics + lineage via DRG
- **Goal**: `SkippedProfile` diagnostics, loader dedup, determinism, and migrate lineage resolution onto DRG traversal (FR-005/006/007/002, NFR-002/005).
- **Priority**: P1. **Independent test**: invalid profile retained in diagnostics; lineage resolves via DRG.
- **Subtasks**: - [ ] T019 · - [ ] T020 · - [ ] T021 · - [ ] T022 · - [ ] T023 · - [ ] T024 (WP05)
- **Dependencies**: WP03, WP06. **Prompt**: [tasks/WP05-profile-diagnostics-lineage.md](tasks/WP05-profile-diagnostics-lineage.md) (~330 lines)

### WP06 — Retire relationship fields (hard cutover)
- **Goal**: Remove `enhances`/`overrides`/`specializes_from` fields from all artifact models; keys become validation errors (FR-028, OQ-2-i). **Bulk-edit governed.**
- **Priority**: P1. **Independent test**: each kind rejects the field with an actionable error.
- **Subtasks**: - [ ] T025 (WP06) · - [ ] T026 (WP06) · - [ ] T027 (WP06) · - [ ] T028 (WP06)
- **Dependencies**: WP07. **Prompt**: [tasks/WP06-retire-relationship-fields.md](tasks/WP06-retire-relationship-fields.md) (~230 lines)

### WP07 — Migrate built-in relationships to fragments (zero-loss)
- **Goal**: Move built-in/shipped field-authored relationships to `graph.yaml` fragment edges; fixtures; zero-loss proof; DRG docs (FR-001/003/004/029, NFR-007). **Bulk-edit governed.**
- **Priority**: P1. **Independent test**: count/identity diff shows zero relationship loss.
- **Subtasks**: - [ ] T029 · - [ ] T030 · - [ ] T031 · - [ ] T032 · - [ ] T033 (WP07)
- **Dependencies**: WP02, WP03, WP04. **Prompt**: [tasks/WP07-migrate-relationships-to-fragments.md](tasks/WP07-migrate-relationships-to-fragments.md) (~300 lines)

### WP08 — `doctor doctrine` health report
- **Goal**: Shared `DoctrineHealthReport` for human+JSON; fix false-healthy (FR-008/009/010, NFR-001).
- **Priority**: P1. **Independent test**: degraded pack surfaced in both outputs; ≤2s.
- **Subtasks**: - [ ] T034 · - [ ] T035 · - [ ] T036 · - [ ] T037 · - [ ] T038 (WP08)
- **Dependencies**: WP05. **Prompt**: [tasks/WP08-doctor-health-report.md](tasks/WP08-doctor-health-report.md) (~300 lines)

---

## Wave 3 — Charter Activation

### WP09 — Pack-manager catalog core (kind tables + list_available)
- **Goal**: Derive kind tables from the resolver; extend `list_available` to org/project; thin activate/deactivate delegation (FR-026, C-008).
- **Priority**: P2. **Independent test**: `list_available` returns org/project IDs with layer.
- **Subtasks**: - [ ] T039 · - [ ] T040 · - [ ] T041 · - [ ] T042 · - [ ] T043 (WP09)
- **Dependencies**: WP01, WP10. **Prompt**: [tasks/WP09-packmgr-catalog-core.md](tasks/WP09-packmgr-catalog-core.md) (~290 lines)

### WP10 — Activation engine (plan/commit seam)
- **Goal**: `plan_activation`/`commit_plan` so validation provably precedes the single write; unknown-ID fail-closed (FR-011/012/021, NFR-003).
- **Priority**: P2. **Independent test**: config bytes unchanged after a failing plan.
- **Subtasks**: - [ ] T044 (WP10) · - [ ] T045 (WP10) · - [ ] T046 (WP10) · - [ ] T047 (WP10)
- **Dependencies**: WP01, WP09. **Prompt**: [tasks/WP10-activation-engine.md](tasks/WP10-activation-engine.md) (~250 lines)

### WP11 — Cascade engine (scope + shared-reference safety)
- **Goal**: `CascadeScope`, scoped cascade activation, no-cascade warning, shared-reference-safe deactivation via `edges_to` (FR-013/014/015/016, C-005).
- **Priority**: P2. **Independent test**: shared artifact skipped with referencing artifact named.
- **Subtasks**: - [ ] T048 · - [ ] T049 · - [ ] T050 · - [ ] T051 · - [ ] T052 (WP11)
- **Dependencies**: WP02, WP03, WP10. **Prompt**: [tasks/WP11-cascade-engine.md](tasks/WP11-cascade-engine.md) (~300 lines)

### WP12 — Charter activation CLI (wiring + cleanup)
- **Goal**: Thread cascade scope, fail-closed `CharterPackConfigError`, generalize mission-type block, normalize sub-app exports, fix FR-008 comment (FR-035/020, FR-013/014 CLI).
- **Priority**: P2. **Independent test**: `--cascade agent-profile,tactic` honored; malformed config fails closed.
- **Subtasks**: - [ ] T053 · - [ ] T054 · - [ ] T055 · - [ ] T056 · - [ ] T057 · - [ ] T058 (WP12)
- **Dependencies**: WP10, WP11. **Prompt**: [tasks/WP12-charter-activation-cli.md](tasks/WP12-charter-activation-cli.md) (~320 lines)

---

## Wave 4 — Runtime & Catalog UX

### WP13 — OperationalContext assembler + guards
- **Goal**: Pure explicit-parameter `build_operational_context`; guards raise `ContextPreconditionError` (FR-017 builder/FR-018, C-006).
- **Priority**: P3. **Independent test**: guards raise with actionable messages.
- **Subtasks**: - [ ] T059 (WP13) · - [ ] T060 (WP13) · - [ ] T061 (WP13)
- **Dependencies**: none. **Prompt**: [tasks/WP13-operational-context-builder.md](tasks/WP13-operational-context-builder.md) (~180 lines)

### WP14 — Wire OperationalContext at runtime entry points
- **Goal**: Populate OC at WP claim (`implement.py`, `workflow.py`) and `next` decision (`runtime_bridge.py`) (FR-017, NFR-004).
- **Priority**: P3. **Independent test**: populated context per site; no worktree/status on precondition fail.
- **Subtasks**: - [ ] T062 · - [ ] T063 · - [ ] T064 · - [ ] T065 (WP14)
- **Dependencies**: WP13. **Prompt**: [tasks/WP14-wire-operational-context.md](tasks/WP14-wire-operational-context.md) (~240 lines)

### WP15 — Dead-symbol gate hygiene
- **Goal**: Remove 7 stale allowlist entries, prune OC entries post-wiring, delete orphan category; green for in-scope symbols (FR-019/036/020, NFR-006).
- **Priority**: P3. **Independent test**: `test_no_dead_symbols.py` passes for in-scope symbols.
- **Subtasks**: - [ ] T066 (WP15) · - [ ] T067 (WP15) · - [ ] T068 (WP15) · - [ ] T069 (WP15)
- **Dependencies**: WP12, WP14. **Prompt**: [tasks/WP15-dead-symbol-hygiene.md](tasks/WP15-dead-symbol-hygiene.md) (~200 lines)

### WP16 — `charter list --all` catalog completeness
- **Goal**: `--all` flag, layer annotation, include `template` kind (FR-025).
- **Priority**: P3. **Independent test**: `list --all` shows built-in/org/project + template.
- **Subtasks**: - [ ] T070 (WP16) · - [ ] T071 (WP16) · - [ ] T072 (WP16)
- **Dependencies**: WP01, WP09, WP18. **Prompt**: [tasks/WP16-charter-list-all.md](tasks/WP16-charter-list-all.md) (~190 lines)

### WP17 — `charter context --include` selectors (agent-profile + template)
- **Goal**: Route `--include` through canonical kinds; agent-profile hyphen works; template resolution; help advertises kinds (FR-022/023/024/034).
- **Priority**: P3. **Independent test**: `--include agent-profile:<id>` and `template:<id>` resolve.
- **Subtasks**: - [ ] T073 (WP17) · - [ ] T074 (WP17) · - [ ] T075 (WP17) · - [ ] T076 (WP17)
- **Dependencies**: WP01, WP18. **Prompt**: [tasks/WP17-context-include-selectors.md](tasks/WP17-context-include-selectors.md) (~230 lines)

### WP18 — Doctrine template discovery + DRG addressing (#1333)
- **Goal**: Template discovery surface and mission-qualified DRG template nodes; resolution by ID (FR-033/034).
- **Priority**: P3. **Independent test**: discovery enumerates templates; `template:<mission>/<name>` resolves.
- **Subtasks**: - [ ] T077 (WP18) · - [ ] T078 (WP18) · - [ ] T079 (WP18) · - [ ] T080 (WP18)
- **Dependencies**: WP01, WP02, WP03. **Prompt**: [tasks/WP18-template-discovery-drg.md](tasks/WP18-template-discovery-drg.md) (~250 lines)

---

## Dependency graph (summary)

```
WP01 ─┬─▶ WP09 ─▶ WP10 ─▶ WP11 ─▶ WP12 ─▶ WP15
      ├─▶ WP16        ╲________________________▶ WP15
      ├─▶ WP17
      └─▶ WP18 ─▶ WP16, WP17
WP02 ─┬─▶ WP03 ─▶ WP05, WP07, WP18
      ├─▶ WP04 ─▶ WP07
      └─▶ WP11
WP06 ◀── WP07 ;  WP05 ◀── WP06, WP03 ;  WP08 ◀── WP05
WP13 ─▶ WP14 ─▶ WP15
```

**MVP / first lane**: WP01 + WP02 (independent foundations) unblock the widest fan-out. WP13 is independent and can run in parallel early.

**Parallelization**: WP01, WP02, WP13 have no dependencies → 3 parallel starts. Wave 1 (WP04/WP05/WP06/WP07/WP08) forms a partially-ordered chain (WP07→WP06→WP05→WP08; WP04 feeds WP07). Wave 3 activation is a chain (WP09→WP10→WP11→WP12). Catalog UX (WP16/WP17) depends on WP18.

## Notes
- **ATDD test-first (C-011, binding)**: each WP lists its test subtask **last for readability only** — execute it **first**. Commit the failing acceptance test as a separate commit (RED on `planning_base_branch`) BEFORE any implementation commit; reviewer verifies red→green. See contracts CC-3.
- **C-007 `__all__` (binding)**: new `src/charter/` modules (`kind_vocabulary.py` WP01, `activation_engine.py` WP10, `cascade.py` WP11) declare `__all__`; their callers live in later-merging dependent WPs, so the dead-symbol gate is satisfied at mission-merge. Do not add net-new allowlist entries (Burn-down Policy).
- **Bulk edit**: WP06 and WP07 are governed by `occurrence_map.yaml`; the `implement` gate enforces classification before edits.
- **Risk-ordered**: WP07 (migration) + WP03 (merge relocation) are the highest-risk; both carry behavior-preservation/zero-loss tests.
- **WP05 coupling (known)**: WP05 bundles low-risk profile diagnostics with the lineage-via-DRG rewire (both edit `repository.py`), so diagnostics are gated behind WP03+WP06+WP07. Accepted due to file ownership; split only if `repository.py` is decomposed.
- **Pre-existing red gate**: WP15 greens in-scope symbols only (net allowlist **shrinkage**). The 2 git/lanes offenders are out of scope, tracked by [#1588](https://github.com/Priivacy-ai/spec-kitty/issues/1588); any allowlisting requires an explicit `_baselines.yaml` baseline change (Burn-down Policy — no silent growth).
