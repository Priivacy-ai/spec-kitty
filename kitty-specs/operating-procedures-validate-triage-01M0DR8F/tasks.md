# Tasks: Operating-Procedures Validate, Triage, Data-Drive

**Mission**: operating-procedures-validate-triage-01M0DR8F
**Branch**: `feat/operating-procedures-validate-triage`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

One work package, single lane. The work is coupled through shared artifacts (all built-in
`*.agent.yaml` profiles + the regenerated `*.graph.yaml`) and strictly ordered
(validate → triage → data-drive), so it is not cleanly splittable without a forbidden
`owned_files` overlap. The hard order is enforced inside the WP by ordered commits with a
red-first test at each sub-phase.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Pure validator `resolve_operating_procedures` + `UnresolvedOpProc` value object | WP01 | |
| T002 | Empty-set architectural gate test (RED @ 44) + non-vacuity self-mutation check | WP01 | |
| T003 | Triage: delete the 36 fictional operating-procedures entries | WP01 | |
| T004 | Triage: migrate 5 wrong-kind tactics → `tactic-references`; delete 3 redundant → gate GREEN | WP01 | |
| T005 | Wire the unresolved diagnostic into `doctor doctrine` (+ test) | WP01 | |
| T006 | Extractor: emit guarded `agent_profile→procedure` edges from op-proc + fail-closed raise + C901 helper (red-first extractor test) | WP01 | |
| T007 | Retire the 2 op-proc-sourced hand-pins; add the RECONCILE third trigger edge | WP01 | |
| T008 | Regenerate graph; update `test_extractor_projection.py` pins + `regenerate-graph --check` golden; full validation sweep | WP01 | |

## Work Package WP01 — Operating-Procedures Validate → Triage → Data-Drive

**Goal**: Every built-in `operating-procedures` entry resolves to a real procedure node (loud on
failure); the 44 dead entries are triaged to ∅; `agent_profile→procedure` edges are data-driven
and guarded, with the 2 op-proc hand-pins retired; the RECONCILE third trigger edge is wired.

**Priority**: P1 (the whole mission). **Prompt**: [tasks/WP01-operating-procedures-validate-triage-data-drive.md](./tasks/WP01-operating-procedures-validate-triage-data-drive.md)

**Independent test**: `tests/architectural/test_operating_procedures_resolve.py` (empty-set gate,
RED@44 pre-triage / GREEN@0 post) + `test_extractor.py` emission/guard + `regenerate-graph --check`
green with `agent_profile→procedure` = 8 and RECONCILE inbound = 3.

**Included subtasks**: T001, T002, T003, T004, T005, T006, T007, T008

**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010

**Dependencies**: none.

**Implementation sketch (load-bearing order)**:
1. T001+T002 — validator + gate (RED @ 44).
2. T003+T004 — triage all 44 → gate GREEN (0).
3. T005 — doctor diagnostic.
4. T006 — extractor emission (guarded) + fail-closed raise (red-first extractor test → green).
5. T007 — retire 2 op-proc pins; add RECONCILE edge.
6. T008 — regenerate graph, reconcile pinned counts + golden, full validation.

**Risks**:
- Data-driving before triage mints dangling edges → `assert_valid` failure. Mitigated by strict
  subtask order (T003/T004 before T006).
- `extract_artifact_edges` is at the C901 ceiling — extract a helper, do not raise complexity (NFR-004).
- `test_extractor_projection.py` and the regen golden pin exact counts; update to the new correct
  values (+10 edges) with research.md's delta table as rationale (not greenwashing).

**Estimated prompt size**: ~520 lines (8 subtasks).

## MVP

WP01 is the mission. There is no partial MVP — the hard order requires validate+triage before the
data-drive is safe.

## Next

`/spec-kitty.analyze` (required gate) → `spec-kitty next` implement/review loop.
