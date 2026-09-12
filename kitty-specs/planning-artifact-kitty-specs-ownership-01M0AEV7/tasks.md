# Tasks: Planning-artifact WPs Own kitty-specs Paths

**Mission**: `planning-artifact-kitty-specs-ownership-01M0AEV7` | **Branch**: `feat/3222-2643-kitty-specs-ownership`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Squad findings**: [squad-findings-post-plan.md](./squad-findings-post-plan.md)

This is a single, cohesive fix — one production predicate change driven ATDD-first by a
comprehensive test set (splitting the code from its red-first tests would break the red→green
loop). One work package.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first positive acceptance test: inference-driven `planning_artifact` + kitty-specs-only finalizes clean, clears downstream gates, lands in the planning lane | WP01 | |
| T002 | Implement the confined exemption in `_invalid_mission_specs_owned_files` | WP01 | |
| T003 | Confinement + fail-closed floor tests (planning+src rejected; code_change+kitty-specs rejected) | WP01 | |
| T004 | Inference tests: unset→inferred-planning ACCEPT; unset→inferred-code REJECT (asserts resolved mode) | WP01 | |
| T005 | Negative-overlap test: two overlapping planning WPs still rejected by `validate_no_overlap` | WP01 | |
| T006 | Update the direct predicate unit tests for `execution_mode`; assert alias/shim identity preserved | WP01 | |
| T007 | Seam-bound regression guards: `authoritative_surface` inference + filename-scoped durability | WP01 | |
| T008 | Quality gate (ruff/mypy/complexity + targeted suites) and file the topology-dedup follow-up | WP01 | |

## Work Packages

### WP01 — Confine and exempt planning_artifact from the finalize kitty-specs ban

- **Goal**: Narrow `finalize-tasks`' `kitty-specs/` owned-files ban so a `planning_artifact` work package whose ownership is confined to planning surfaces may own its `kitty-specs/` deliverables, while `code_change` (and any WP owning code) stays fail-closed.
- **Priority**: P1 (the whole mission).
- **Execution mode**: `code_change`.
- **Dependencies**: none.
- **Independent test**: `spec-kitty agent mission finalize-tasks --validate-only` accepts an inference-driven `planning_artifact` + kitty-specs-only WP and places it in `lane-planning`; a `code_change` + kitty-specs WP and a `planning_artifact` + `src/` WP are both rejected with `INVALID_WP_OWNED_FILES_KITTY_SPECS`.
- **Included subtasks**: T001, T002, T003, T004, T005, T006, T007, T008.
- **Prompt**: [tasks/WP01-confine-planning-artifact-kitty-specs-exemption.md](./tasks/WP01-confine-planning-artifact-kitty-specs-exemption.md)
- **Estimated prompt size**: ~290 lines (within the 200-500 band).
- **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, NFR-001, NFR-002, C-001, C-002, C-003.
- **Risks**: the exemption must key on `ExecutionMode.PLANNING_ARTIFACT.value` (not incidental `StrEnum` equality) AND confine to `_PLANNING_PREFIXES`; the positive acceptance test must clear the two downstream hard-gates (`validate_authoritative_surface`, `validate_glob_matches`) or it is red-both-times; durability is filename-scoped (managed-kind carve-out). Preserve the `_invalid_kitty_specs_owned_files` alias seam. Keep the predicate at complexity ≤ 15.

## MVP

WP01 **is** the MVP — the mission is a single cohesive fix.
