# Tasks: Mission-Type DRG Node + Cross-Grain Integrity Gate (S0 + seam completion)

**Mission:** resolver-seam-completion-01KXK0KG · **Branch:** feat/2651-resolver-seam-completion
**Plan:** [plan.md](plan.md) (12-IC map) · **Design:** ADR 2026-07-15-1 + 2026-07-14-2

## WP → IC mapping & lanes

The 7-IC-grouping from the post-plan squad is realized as **5 WPs**, refined so `owned_files`
never overlap: IC-07's union logic is extracted into a **new `src/charter/action_grain.py`**
module (WP02), so `mission_type_profiles.py` is owned by **WP03 alone** (IC-06+IC-10+IC-12), and
the gate (WP04) + reconciled tests (WP05) **reuse** that one module — killing the second source.
**IC-03 (mission-type cascade) is deferred** to S0-continuation (cosmetic without edges).

| WP | ICs | Lane | Depends on | Owns (no overlap) |
|----|-----|------|------------|-------------------|
| WP01 | IC-01, IC-02 | DRG | — | `src/doctrine/drg/{models.py, migration/extractor.py}`, `graph.yaml` + DRG tests |
| WP02 | IC-07 (+IC-11 spike) | Resolver-helper | — | **new** `src/charter/action_grain.py` + its test |
| WP03 | IC-06, IC-10, IC-12 | Resolver-core | WP02 | `src/charter/mission_type_profiles.py` + its unit tests |
| WP04 | IC-04, IC-05, IC-11 | Gate | WP02 | **new** `tests/doctrine/drg/test_cross_grain_integrity.py` |
| WP05 | IC-08, IC-09 | Test | WP03 | the 3 existing test-union / NFR files |

**Parallelism:** WP01 ∥ WP02 (disjoint files). Critical path **WP02 → WP03 → WP05**; WP04 is a parallel tail after WP02.
**MVP:** WP01 + WP02 + WP03 (the DRG node + the lazy union land the core); WP04/WP05 harden.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Register `MISSION_TYPE` NodeKind enum member + node-kind test | WP01 | |
| T002 | Extractor `_discover_mission_type_nodes` from `mission_types/*.yaml` + wire into `generate_graph` | WP01 | |
| T003 | Regenerate `graph.yaml`; keep `regenerate-graph --check` + freshness/totality/superset tests green | WP01 | |
| T004 | `action_index_to_mapping` pure adapter (`ActionIndex`→`Mapping[str,list[str]]`) + test | WP02 | [P] |
| T005 | `aggregate_action_grain(built_in_dir, type)` — enumerate `actions/*`, `load_action_index` each, union | WP02 | [P] |
| T006 | IC-11 dup-scan spike: assert zero shipped cross-grain collisions (feeds WP04) | WP02 | [P] |
| T007 | Make `governance` a lazy `compare=False` thunk (mirror `_expected_artifacts_thunk`) | WP03 | |
| T008 | Rework `_resolve_governance_slot`→`(provenance,text,thunk)`; fix `:469` provenance force | WP03 | |
| T009 | Wire `aggregate_action_grain` into the thunk; retire `_EMPTY_GRAIN`; guard fires on `.governance` | WP03 | |
| T010 | Campsite (IC-10): repoint `_load_mission_type_profile` test, drop ImportError fallback, TypedDict typing ×3, docstrings, parity-scaffold guard | WP03 | |
| T011 | IC-12 regression pins: gating byte-identical; thunk severs collision→action_sequence coupling | WP03 | |
| T012 | Doctrine-integrity gate: all `(type,action)` via `action_grain` union, disjoint + non-empty | WP04 | |
| T013 | Non-vacuity twin: temp-tree deliberate-collision fixture through `load_action_index` MUST fail | WP04 | |
| T014 | Reconcile `_resolve_union` + `_resolve_union_from_mission` to read `bundle.governance` only | WP05 | |
| T015 | NFR spy: replace `from_config` p99 gate; spy `load_action_index` NOT called on hot path | WP05 | |

---

## WP01 — mission_type DRG node + generator

**Goal:** make `mission_type` a first-class DRG node (ADR S0). **Independent test:** `graph.yaml` has 4 `mission_type` nodes; `regenerate-graph --check` green.
Prompt: [tasks/WP01-mission-type-drg-node.md](tasks/WP01-mission-type-drg-node.md)

- [x] T001 Register `MISSION_TYPE` NodeKind enum member + node-kind test (WP01)
- [x] T002 Extractor `_discover_mission_type_nodes` + wire into `generate_graph` (WP01)
- [x] T003 Regenerate `graph.yaml`; keep freshness/totality/superset green (WP01)

**Dependencies:** none. **Parallel with:** WP02.

## WP02 — action-grain aggregation module (foundational)

**Goal:** the single canonical type-scoped action-grain union, in a new module. **Independent test:** `aggregate_action_grain` returns the unioned per-kind mapping for each built-in type; adapter round-trips.
Prompt: [tasks/WP02-action-grain-module.md](tasks/WP02-action-grain-module.md)

- [x] T004 `action_index_to_mapping` pure adapter + test (WP02)
- [x] T005 `aggregate_action_grain` builtin-root enumeration + union (WP02)
- [x] T006 IC-11 dup-scan spike: assert zero shipped collisions (WP02)

**Dependencies:** none. **Parallel with:** WP01.

## WP03 — resolver lazy union + campsite + pins

**Goal:** wire the lazy action-grain union into the resolver, retire `_EMPTY_GRAIN`, campsite, keep gating byte-identical. **Independent test:** hot `.action_sequence` triggers no `load_action_index`; `.governance` fast-fails on collision; charter suite green.
Prompt: [tasks/WP03-resolver-lazy-union.md](tasks/WP03-resolver-lazy-union.md)

- [x] T007 Lazy `compare=False` governance thunk (WP03)
- [x] T008 `_resolve_governance_slot`→`(provenance,text,thunk)`; fix `:469` (WP03)
- [x] T009 Wire `aggregate_action_grain` into thunk; retire `_EMPTY_GRAIN` (WP03)
- [x] T010 Campsite: repoint test, drop fallback, TypedDict typing, docstrings, parity guard (WP03)
- [x] T011 IC-12 regression pins (WP03)

**Dependencies:** WP02.

## WP04 — cross-grain integrity gate + non-vacuity twin

**Goal:** the load-bearing FR-013 enforcer as a doctrine-integrity gate reusing WP02's union. **Independent test:** gate passes on shipped tree, fails on the deliberate-collision fixture.
Prompt: [tasks/WP04-integrity-gate.md](tasks/WP04-integrity-gate.md)

- [x] T012 Doctrine-integrity gate over all `(type,action)` (WP04)
- [x] T013 Non-vacuity twin fixture (WP04)

**Dependencies:** WP02.

## WP05 — test-union reconciliation + NFR spy

**Goal:** remove the second-source unions; correct the NFR-001 threshold. **Independent test:** the two former union sites read `bundle.governance`; a spy proves the hot path calls no `load_action_index`.
Prompt: [tasks/WP05-test-reconciliation.md](tasks/WP05-test-reconciliation.md)

- [ ] T014 Reconcile the two `_resolve_union*` sites to `bundle.governance` (WP05)
- [ ] T015 NFR spy on the real hot path; drop `from_config` p99 citation (WP05)

**Dependencies:** WP03.
