# Tasks: DRG Read-Path Bridge

**Mission**: drg-read-path-bridge-01M0CHVZ
**Branch**: `mission/drg-read-path-bridge-01M0CHVZ` (planning/base = merge target; single_branch)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

## Overview

Bridge org `drg/fragment.yaml` `requires`/`suggests` edges into the graph charter
cascade walks, re-scope the graphless warning, and reconcile the validator — the
validator finding and runtime bridge flipping **atomically** (C-001 / NFR-003).
Because atomicity forbids a partial merge, the SC-critical change is a single
coherent work package (WP01); WP02 extends the same bridge to additive graph
consumers and can be deferred without affecting SC-001..SC-004.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | RED-first: flip the pinning test to assert the fragment edge cascades | WP01 | |
| T002 | `load_org_drg(strict=…)` resilient per-pack fragment load | WP01 | |
| T003 | Bridge `load_validated_graph(org_fragments=…)` via `merge_three_layers` | WP01 | |
| T004 | Re-scope the D-005 graphless warning | WP01 | |
| T005 | Thread `activate.py` / `deactivate.py` cascade call sites | WP01 | |
| T006 | Reconcile validator `_check_drg_root_graph_missing` (atomic) | WP01 | |
| T007 | Regression sweep + single golden re-ledger; diagnostic invariance | WP01 | |
| T008 | Thread `review/gate_bindings.py` additive consumer | WP02 | |
| T009 | Thread `mission_step_contracts/executor.py` (defer if non-trivial) | WP02 | |
| T010 | Focused regression for the additive consumers | WP02 | |

## Work Packages

### WP01 — Bridge + atomic validator flip (SC deliverable)

**Goal**: Make org `drg/fragment.yaml` `requires`/`suggests` edges cascade at
`charter activate/deactivate`, warn only for genuinely-graphless packs, and flip
the validator finding in the SAME change — satisfying SC-001..SC-004.
**Priority**: P1 (the mission's core defect #3572 + folded #3573).
**Independent test**: an org pack declaring `A requires B` **only** in
`drg/fragment.yaml` cascade-activates B with `--cascade all`; a fragment-only pack
emits no graphless warning; `pack validate` emits no "will not be read" finding;
root-graph cascade tests stay green.
**Prompt**: [tasks/WP01-bridge-and-validator-flip.md](./tasks/WP01-bridge-and-validator-flip.md) (~420 lines)

Included subtasks: T001, T002, T003, T004, T005, T006, T007

**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, NFR-001,
NFR-002, NFR-003, C-001, C-002, C-003, C-005

**Sequence** (ATDD): T001 (red) → T002+T003+T004 (bridge green) → T005 (threading,
integration test green) → T006 (validator, atomic) → T007 (sweep + re-ledger).

**Risks**: (R1) routing the cascade path through a strict `load_org_drg` regresses
the green root-graph tests — mitigated by `strict=False` (T002). (R2) diagnostic
path drift — mitigated by not touching diagnostic callers and asserting invariance
(T007). (R3) validator/runtime disagreement at some intermediate commit —
mitigated by landing T006 with T003 (atomic).

### WP02 — Additive graph-consumer threading (coherence extension)

**Goal**: Extend the same fragment bridge to the review-gate and mission-step
graph consumers so org fragment edges are visible there too. Not on the SC path —
deferrable.
**Priority**: P2.
**Dependencies**: WP01.
**Independent test**: `gate_bindings` graph load (and, if threaded, the executor
graph load) contains an org fragment edge when a fragment-bearing pack is
configured; no diagnostic-path change.
**Prompt**: [tasks/WP02-additive-consumer-threading.md](./tasks/WP02-additive-consumer-threading.md) (~180 lines)

Included subtasks: T008, T009, T010

**Requirement refs**: FR-001

**Note**: Per research.md D4, if the executor's `healthy_roots`/pre-probe degrade
logic makes T009 non-trivial, drop T009 with a one-line tracked rationale in the
WP history; T008 + T010 still deliver the extension.
