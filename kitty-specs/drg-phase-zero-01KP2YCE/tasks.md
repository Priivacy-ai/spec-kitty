# Tasks: DRG Phase Zero

**Mission ID**: `01KP2YCESBSG61KQH5PQZ9662H`
**Mission slug**: `drg-phase-zero-01KP2YCE`
**Date**: 2026-04-13
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Document behavioral delta between canonical and legacy `build_charter_context()` | WP00 | | [D] |
| T002 | Verify canonical path resolves correct artifacts for all (action, depth) | WP00 | | [D] |
| T003 | Document Phase 1 reroute scope and expected behavior changes | WP00 | | [D] |
| T005 | Define `NodeKind` and `Relation` enums | WP01 | [D] |
| T006 | Implement `DRGNode`, `DRGEdge`, `DRGGraph` Pydantic models | WP01 | | [D] |
| T007 | Implement `load_graph()` and `merge_layers()` | WP01 | | [D] |
| T008 | Implement validator: dangling refs, cycles, malformed URNs, duplicate edges | WP01 | | [D] |
| T009 | Create fixture graphs (valid, dangling, cyclic, malformed) | WP01 | [D] |
| T010 | Unit tests for models, loader, validator | WP01 | | [D] |
| T011 | Implement `id_normalizer.py` (DIRECTIVE_NNN <-> NNN-slug) | WP02 | [D] |
| T012 | Implement artifact walker: directives, tactics, paradigms | WP02 | | [D] |
| T013 | Implement action index walker | WP02 | | [D] |
| T014 | Create `tasks` action index for software-dev mission | WP02 | | [D] |
| T015 | Implement surface calibrator (adjust review and tasks scope edges) | WP02 | | [D] |
| T016 | Generate `graph.yaml` from shipped artifacts | WP02 | | [D] |
| T017 | Validate edge count >= inline field count | WP02 | | [D] |
| T018 | Unit tests for extractor, calibrator, normalizer | WP02 | | [D] |
| T019 | Implement DRG query primitives (`walk_edges`, `resolve_context`) | WP03 | | [D] |
| T020 | Implement `build_context_v2()` in `src/charter/context.py` | WP03 | | [D] |
| T021 | Unit tests for query primitives against fixture graphs | WP03 | | [D] |
| T022 | Verify no per-action filtering logic in `build_context_v2` | WP03 | | [D] |
| T023 | Create test matrix generator (profile x action x depth) | WP04 | | [D] |
| T024 | Implement artifact-reachability comparison logic (URN set equality) | WP04 | | [D] |
| T025 | Create `accepted_differences.yaml` schema and loader | WP04 | | [D] |
| T026 | Implement invariant test with accepted-differences integration | WP04 | | [D] |
| T027 | Configure CI triggers for doctrine/charter/graph.yaml changes | WP04 | [D] |
| T028 | Implement surface size measurement function | WP05 | | [D] |
| T029 | Assert calibration inequalities for all shipped actions | WP05 | | [D] |
| T030 | Verify DRG-only-knob rule: no filtering logic anywhere | WP05 | | [D] |
| T031 | Configure CI triggers (shared with WP04 config) | WP05 | [D] |

## Dependency Graph

```
WP00 (call-site audit) ────────────────────────┐
                                                │
WP01 (DRG schema + model) ─┐                   │
                            ├── WP02 (migration │+ calibration)
                            │       │           │
                            └───────┴── WP03 (build_context_v2)
                                        │       │
                                        ├───────┤
                                        │       │
                                        ├── WP04 (invariant test)
                                        │
                                        └── WP05 (calibration test)
```

- WP00 has no dependencies (produces documentation, not code; runs in parallel with WP01-WP03)
- WP01 has no dependencies
- WP02 depends on WP01
- WP03 depends on WP01 and WP02
- WP04 depends on WP00 (oracle confirmed) and WP03 (build_context_v2 exists)
- WP05 depends on WP03

---

## WP00: Call-Site Audit and Oracle Confirmation

**Priority**: High (prerequisite for invariant test oracle selection)
**Dependencies**: None
**Prompt**: [tasks/WP00-call-site-reroute.md](tasks/WP00-call-site-reroute.md)
**Estimated size**: ~250 lines

**Goal**: Document the behavioral delta between the two `build_charter_context()` implementations and confirm the canonical path is the correct parity oracle. No production code is changed.

**Included subtasks**:
- [x] T001 Document behavioral delta between canonical and legacy `build_charter_context()` (WP00)
- [x] T002 Verify canonical path resolves correct artifacts for all (action, depth) (WP00)
- [x] T003 Document Phase 1 reroute scope and expected behavior changes (WP00)

**Success criteria**: Delta document exists; canonical path confirmed as correct oracle; Phase 1 reroute scope documented.

---

## WP01: DRG Schema and Pydantic Model

**Priority**: High (foundation for all subsequent WPs)
**Dependencies**: None
**Prompt**: [tasks/WP01-drg-schema-model.md](tasks/WP01-drg-schema-model.md)
**Estimated size**: ~450 lines
**Issue**: #470

**Goal**: Define the DRG schema as Pydantic models with graph validation.

**Included subtasks**:
- [x] T005 Define `NodeKind` and `Relation` enums (WP01)
- [x] T006 Implement `DRGNode`, `DRGEdge`, `DRGGraph` Pydantic models (WP01)
- [x] T007 Implement `load_graph()` and `merge_layers()` (WP01)
- [x] T008 Implement validator: dangling refs, cycles, malformed URNs, duplicate edges (WP01)
- [x] T009 Create fixture graphs (valid, dangling, cyclic, malformed) (WP01)
- [x] T010 Unit tests for models, loader, validator (WP01)

**Success criteria**: Pydantic model loads fixture graph; validator rejects all malformed variants; mypy --strict clean; 90%+ coverage.

---

## WP02: Migration Extractor and Surface Calibration

**Priority**: High (populates graph.yaml)
**Dependencies**: WP01
**Prompt**: [tasks/WP02-migration-extractor.md](tasks/WP02-migration-extractor.md)
**Estimated size**: ~500 lines
**Issue**: #473

**Goal**: Extract all inline references from shipped doctrine artifacts and action indices into `graph.yaml`, applying per-action surface calibration.

**Included subtasks**:
- [x] T011 Implement `id_normalizer.py` (DIRECTIVE_NNN <-> NNN-slug) (WP02)
- [x] T012 Implement artifact walker: directives, tactics, paradigms (WP02)
- [x] T013 Implement action index walker (WP02)
- [x] T014 Create `tasks` action index for software-dev mission (WP02)
- [x] T015 Implement surface calibrator (adjust review and tasks scope edges) (WP02)
- [x] T016 Generate `graph.yaml` from shipped artifacts (WP02)
- [x] T017 Validate edge count >= inline field count (WP02)
- [x] T018 Unit tests for extractor, calibrator, normalizer (WP02)

**Success criteria**: `graph.yaml` validates with zero errors; edge count >= inline field count; calibration inequalities satisfied; migration is idempotent.

---

## WP03: build_context_v2

**Priority**: High (enables test harnesses)
**Dependencies**: WP01, WP02
**Prompt**: [tasks/WP03-build-context-v2.md](tasks/WP03-build-context-v2.md)
**Estimated size**: ~400 lines
**Issue**: #471

**Goal**: Implement `build_context_v2(profile, action, depth)` by composing DRG query primitives.

**Included subtasks**:
- [x] T019 Implement DRG query primitives (`walk_edges`, `resolve_context`) (WP03)
- [x] T020 Implement `build_context_v2()` in `src/charter/context.py` (WP03)
- [x] T021 Unit tests for query primitives against fixture graphs (WP03)
- [x] T022 Verify no per-action filtering logic in `build_context_v2` (WP03)

**Success criteria**: Function returns deterministic results for fixture graphs; no filtering logic in function body; composes DRG primitives only.

---

## WP04: Invariant Regression Test

**Priority**: Critical (gates Phase 1)
**Dependencies**: WP00, WP03
**Prompt**: [tasks/WP04-invariant-test.md](tasks/WP04-invariant-test.md)
**Estimated size**: ~400 lines
**Issue**: #472

**Goal**: Prove `build_context_v2` resolves the same governance artifacts (by URN) as the canonical `build_charter_context()` for all shipped (profile, action, depth) combinations.

**Included subtasks**:
- [x] T023 Create test matrix generator (profile x action x depth) (WP04)
- [x] T024 Implement artifact-reachability comparison logic (URN set equality) (WP04)
- [x] T025 Create `accepted_differences.yaml` schema and loader (WP04)
- [x] T026 Implement invariant test with accepted-differences integration (WP04)
- [x] T027 Configure CI triggers for doctrine/charter/graph.yaml changes (WP04)

**Success criteria**: Artifact-reachability parity for 100% of matrix; accepted-differences < 10% threshold; runs in < 60s; CI triggers on relevant file changes.

---

## WP05: Surface Calibration Test

**Priority**: Critical (gates Phase 1)
**Dependencies**: WP03
**Prompt**: [tasks/WP05-calibration-test.md](tasks/WP05-calibration-test.md)
**Estimated size**: ~300 lines
**Issue**: #474

**Goal**: Assert minimum-effective-dose surface inequalities for every shipped action.

**Included subtasks**:
- [x] T028 Implement surface size measurement function (WP05)
- [x] T029 Assert calibration inequalities for all shipped actions (WP05)
- [x] T030 Verify DRG-only-knob rule: no filtering logic anywhere (WP05)
- [x] T031 Configure CI triggers (shared with WP04 config) (WP05)

**Success criteria**: All inequalities hold; review ≈ implement (within 80% threshold); violations produce clear error messages naming the violating action.
