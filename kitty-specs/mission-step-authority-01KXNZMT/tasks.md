# Tasks: Step authority — step.yaml as single source (S-B)

**Mission**: `mission-step-authority-01KXNZMT` | **Branch**: `feat/mission-step-authority` (stacked on the S-A commit)
**Plan**: [plan.md](./plan.md) (see "Post-Plan Squad Refinements (BINDING for /tasks)") | **Spec**: [spec.md](./spec.md)

Topology: **FLAT** (still writes `lanes.json` + DFS cycle check). Execution lanes base on the S-A-bearing HEAD
(`feat/mission-step-authority`), NOT origin/main. No PR — WP07's local aggregate-gate-green is the merge signal.

**Baseline (proof anchor):** DRG `280 nodes / 757 edges / 10 orphans`, fresh (#2712-bearing base).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add MissionStep fields (sequence_index, in_action_sequence, recommended_model_tier, template ref) — prompt_template stays required | WP01 | |
| T002 | Register new fields in `_STEP_YAML_TO_MODEL` (extra="forbid" trap) | WP01 | |
| T003 | MissionType action_sequence/template_set absence-tolerant + relocate `_validate_action_sequence` to the projection | WP01 | |
| T004 | Field-round-trip test (new fields survive load; validator on projection) | WP01 | |
| T005 | Create `step_projection.py`: `project_action_sequence` (in_action_sequence:true, sorted by sequence_index) | WP02 | |
| T006 | `project_template_set` keyed on artifact_key (drops template-less steps) | WP02 | |
| T007 | Cached accessor: `MissionTypeRepository._load` injection + memoized `default()` (@functools.cache) | WP02 | |
| T008 | Re-assert non-empty+unique invariant on the projection; module-level projection tests | WP02 | |
| T009 | Author sequence_index + in_action_sequence on software-dev's 12 step.yaml | WP03 | |
| T010 | Author template ref on specify/plan steps (artifact_key → existing files); round-trip test | WP03 | |
| T011 | Re-point `extract_mission_type_edges` to the projection (builtin-only, filtered, no dir listing) | WP04 | |
| T012 | Assert in_action_sequence:false mints no edge; DRG 0-delta + freshness | WP04 | |
| T013 | Re-point raw-YAML test helpers (test_mission_type_nodes.py:98, test_extractor.py:700) | WP04 | |
| T014 | Move documentation per-step content → mission-steps/documentation/<step>/ + author step.yaml (7) | WP05 | [P] |
| T015 | Move research per-step content → mission-steps/research/<step>/ + author step.yaml (5) | WP05 | [P] |
| T016 | Author plan step.yaml (4, no content); seed blank prompt.md for all 16 prompt-less steps | WP05 | |
| T017 | Red test on prompt emptiness/dummy-content; referential-integrity (3 types) + dispatch-invariance | WP05 | |
| T018 | Switch `_resolve_action_slot` (694/697) + `_resolve_template_set_slot` (750) to the cached seam | WP06 | |
| T019 | Switch decision.py:606 + runtime_bridge_composition.py:186/321 | WP06 | |
| T020 | extends-fallback check across 4 types; seam-equivalence tests | WP06 | |
| T021 | Add sw-dev parity scaffold, prove green while YAML authored | WP07 | |
| T022 | Remove action_sequence/template_set from mission_types/*.yaml (4 files) + reconcile | WP07 | |
| T023 | Delete parity scaffold; run full aggregate gate locally | WP07 | |
| T024 | Create `step_offer_seam.py` (named seam, precedence override > offer) | WP08 | [P] |
| T025 | Wire `model_task_routing/evaluator.py:229` as live recommended_model_tier consumer + override-precedence test | WP08 | [P] |

## Work Packages

### WP01 — Schema foundation
**Goal**: Extend the `MissionStep` schema (the authority) + make `MissionType` projection-ready, in one owner of `models.py`. **Prompt**: [tasks/WP01-schema-foundation.md](./tasks/WP01-schema-foundation.md)
Dependencies: none
- [x] T001 Add MissionStep fields; prompt_template stays required (WP01)
- [x] T002 Register new fields in `_STEP_YAML_TO_MODEL` (WP01)
- [x] T003 MissionType absence-tolerant + validator → projection (WP01)
- [x] T004 Field-round-trip test (WP01)

### WP02 — Projection seam + caching
**Goal**: One canonical doctrine-layer projection module + cached accessor. **Prompt**: [tasks/WP02-projection-seam.md](./tasks/WP02-projection-seam.md)
Dependencies: WP01
- [x] T005 `project_action_sequence` (WP02)
- [x] T006 `project_template_set` keyed on artifact_key (WP02)
- [x] T007 Cached accessor: repo injection + memoized `default()` (WP02)
- [x] T008 Projection invariant + module tests (WP02)

### WP03 — Software-dev step data
**Goal**: Author order/membership + template refs onto sw-dev's 12 step.yaml; parity round-trip. **Prompt**: [tasks/WP03-softwaredev-step-data.md](./tasks/WP03-softwaredev-step-data.md)
Dependencies: WP01, WP02
- [x] T009 sequence_index + in_action_sequence on 12 step.yaml (WP03)
- [x] T010 template ref on specify/plan + round-trip test (WP03)

### WP04 — Extractor re-point
**Goal**: Extractor emits edges from the projection; DRG 0-delta. **Prompt**: [tasks/WP04-extractor-repoint.md](./tasks/WP04-extractor-repoint.md)
Dependencies: WP02, WP03
- [x] T011 Re-point extractor to projection (builtin-only, filtered) (WP04)
- [x] T012 in_action_sequence:false → no edge; DRG 0-delta + freshness (WP04)
- [x] T013 Re-point raw-YAML test helpers (WP04)

### WP05 — Four-type unification + red-flags
**Goal**: Unify all 4 types onto mission-steps/ layout; seed blanks + emptiness red tests. **Prompt**: [tasks/WP05-four-type-unification.md](./tasks/WP05-four-type-unification.md)
Dependencies: WP01, WP02
- [x] T014 Move documentation content + author step.yaml (WP05)
- [x] T015 Move research content + author step.yaml (WP05)
- [x] T016 Author plan step.yaml + seed 16 blank prompt.md (WP05)
- [x] T017 Emptiness red test + referential-integrity + dispatch-invariance (WP05)

### WP06 — Consumer switch
**Goal**: Switch every real authority read to the cached seam. **Prompt**: [tasks/WP06-consumer-switch.md](./tasks/WP06-consumer-switch.md)
Dependencies: WP02, WP03, WP05
- [x] T018 Switch `_resolve_action_slot` + `_resolve_template_set_slot` (WP06)
- [x] T019 Switch decision.py + runtime_bridge_composition.py (WP06)
- [x] T020 extends-fallback check + seam-equivalence tests (WP06)

### WP07 — YAML cutover + scaffold lifecycle
**Goal**: Remove the flat fields; own the parity scaffold add→prove→delete; aggregate gate. **Prompt**: [tasks/WP07-yaml-cutover.md](./tasks/WP07-yaml-cutover.md)
Dependencies: WP04, WP06
- [ ] T021 Add parity scaffold, prove green while YAML authored (WP07)
- [ ] T022 Remove action_sequence/template_set from 4 YAMLs + reconcile (WP07)
- [ ] T023 Delete scaffold; full aggregate gate local (WP07)

### WP08 — Override seam + live consumer
**Goal**: recommended_model_tier read through a named seam with a live consumer. **Prompt**: [tasks/WP08-override-seam.md](./tasks/WP08-override-seam.md)
Dependencies: WP01
- [x] T024 Create `step_offer_seam.py` (WP08)
- [x] T025 Wire evaluator.py consumer + override-precedence test (WP08)

## Dependency graph

```
WP01 ──┬──► WP02 ──┬──► WP03 ──► WP04 ──┐
       │           └──► WP05 ──┐        ├──► WP07
       └──► WP08              └──► WP06 ─┘
```
WP04 ← WP02,WP03 · WP06 ← WP02,WP03,WP05 · WP07 ← WP04,WP06. ~2 lanes (projection→cutover spine + unify/override side).

## Deferred (NOT in any WP — follow-ups under #2721)
FR-009 (≥4-site role/model consolidation) · FR-011 (MISSION_STEP_CONTRACT / D6, needs a net-new Relation).

## MVP
WP01 (schema) is the foundation. The behavior-preserving core is WP01→WP02→WP03→WP04 (sw-dev projection + extractor, DRG 0-delta) before the 4-type unification and cutover.
