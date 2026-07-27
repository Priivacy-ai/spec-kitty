# Work Packages: Bulk Edit Occurrence Classification Guardrail

**Mission**: bulk-edit-occurrence-classification-guardrail-01KP423X
**Date**: 2026-04-13
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Add `change_mode` to `MissionMetaOptional` TypedDict + validation | WP01 | [P] | [D] |
| T002 | Unit tests for `change_mode` metadata field | WP01 | [D] |
| T003 | Create `src/specify_cli/bulk_edit/` package with `__init__.py` | WP02 | [D] |
| T004 | Create `occurrence_map.py` — YAML loading, structural validation, admissibility | WP02 | [D] |
| T005 | Unit tests for occurrence map validation | WP02 | [D] |
| T006 | Create `inference.py` — weighted keyword scanning + threshold | WP03 | [D] |
| T007 | Unit tests for inference keyword scanning | WP03 | [D] |
| T008 | Create `gate.py` — `ensure_occurrence_classification_ready()` guard function | WP04 | | [D] |
| T009 | Wire gate into `implement.py` between planning validation and workspace allocation | WP04 | | [D] |
| T010 | Wire gate into `workflow.py` review function | WP04 | | [D] |
| T011 | Wire inference warning into implement path for non-bulk-edit missions | WP04 | | [D] |
| T012 | Integration tests for implement and review gate CLI behavior | WP04 | | [D] |
| T013 | Register `occurrence_map_complete` guard primitive in `guards.py` | WP05 | [D] |
| T014 | Update `expected-artifacts.yaml` with conditional `occurrence_map.yaml` | WP05 | [D] |
| T015 | Create doctrine directive 035 YAML | WP05 | [D] |
| T016 | Create `occurrence-classification-workflow` tactic YAML | WP05 | [D] |
| T017 | Update implement command template to reference occurrence map | WP06 | | [D] |
| T018 | Update review command template to reference occurrence map | WP06 | | [D] |

## Dependency Graph

```
WP01 (metadata) ──┐
WP02 (schema)  ───┼── WP04 (gates + CLI wiring) ──┐
WP03 (inference) ─┘                                ├── WP06 (templates)
WP02 (schema)  ───── WP05 (guards + doctrine) ────┘
```

**Parallelization**: WP01, WP02, WP03 are fully parallel (no shared dependencies). WP04 fans in from all three. WP05 depends only on WP02. WP06 depends on WP04 and WP05.

---

## Phase 1: Foundation (parallel)

### WP01 — Mission Metadata: change_mode Field

**Priority**: P0 (foundation)
**Dependencies**: none
**Prompt**: [tasks/WP01-mission-metadata-change-mode.md](tasks/WP01-mission-metadata-change-mode.md)
**Estimated size**: ~250 lines

- [x] T001 Add `change_mode` to `MissionMetaOptional` TypedDict + validation (WP01)
- [x] T002 Unit tests for `change_mode` metadata field (WP01)

### WP02 — Occurrence Map Schema & Validation

**Priority**: P0 (foundation)
**Dependencies**: none
**Prompt**: [tasks/WP02-occurrence-map-schema.md](tasks/WP02-occurrence-map-schema.md)
**Estimated size**: ~350 lines

- [x] T003 Create `src/specify_cli/bulk_edit/` package with `__init__.py` (WP02)
- [x] T004 Create `occurrence_map.py` — YAML loading, structural validation, admissibility (WP02)
- [x] T005 Unit tests for occurrence map validation (WP02)

### WP03 — Inference Warning System

**Priority**: P0 (foundation)
**Dependencies**: none
**Prompt**: [tasks/WP03-inference-warning.md](tasks/WP03-inference-warning.md)
**Estimated size**: ~250 lines

- [x] T006 Create `inference.py` — weighted keyword scanning + threshold (WP03)
- [x] T007 Unit tests for inference keyword scanning (WP03)

---

## Phase 2: Core Integration

### WP04 — Gate Function & CLI Wiring

**Priority**: P0 (core)
**Dependencies**: WP01, WP02, WP03
**Prompt**: [tasks/WP04-gate-function-cli-wiring.md](tasks/WP04-gate-function-cli-wiring.md)
**Estimated size**: ~450 lines

- [x] T008 Create `gate.py` — `ensure_occurrence_classification_ready()` guard function (WP04)
- [x] T009 Wire gate into `implement.py` between planning validation and workspace allocation (WP04)
- [x] T010 Wire gate into `workflow.py` review function (WP04)
- [x] T011 Wire inference warning into implement path for non-bulk-edit missions (WP04)
- [x] T012 Integration tests for implement and review gate CLI behavior (WP04)

---

## Phase 3: Supporting Infrastructure (parallel)

### WP05 — Guard Registration, Expected Artifacts & Doctrine

**Priority**: P1 (supporting)
**Dependencies**: WP02
**Prompt**: [tasks/WP05-guards-artifacts-doctrine.md](tasks/WP05-guards-artifacts-doctrine.md)
**Estimated size**: ~350 lines

- [x] T013 Register `occurrence_map_complete` guard primitive in `guards.py` (WP05)
- [x] T014 Update `expected-artifacts.yaml` with conditional `occurrence_map.yaml` (WP05)
- [x] T015 Create doctrine directive 035 YAML (WP05)
- [x] T016 Create `occurrence-classification-workflow` tactic YAML (WP05)

---

## Phase 4: Template Updates

### WP06 — Command Template Updates

**Priority**: P1 (documentation)
**Dependencies**: WP04, WP05
**Prompt**: [tasks/WP06-command-template-updates.md](tasks/WP06-command-template-updates.md)
**Estimated size**: ~250 lines

- [x] T017 Update implement command template to reference occurrence map (WP06)
- [x] T018 Update review command template to reference occurrence map (WP06)
