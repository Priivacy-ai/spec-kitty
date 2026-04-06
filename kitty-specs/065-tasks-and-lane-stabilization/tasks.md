# Tasks: 065 Tasks And Lane Stabilization

**Mission**: 065-tasks-and-lane-stabilization
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Target Branch**: main
**Date**: 2026-04-06

## Subtask Index

| ID | Summary | WP | Parallel |
|----|---------|-----|----------|
| T001 | Extract shared dependency parser into reusable module | WP01 | No |
| T002 | Add bullet-list dependency format recognition | WP01 | No |
| T003 | Wire both finalize-tasks entry points to shared parser | WP01 | No |
| T004 | Implement disagree-loud on non-empty dependency conflict | WP01 | No |
| T005 | Fix set_scalar type mismatch — use FrontmatterManager for list fields | WP01 | No |
| T006 | Gate all mutations on validate_only flag | WP01 | No |
| T007 | Implement validate-only mutation report | WP01 | No |
| T008 | Implement accurate per-WP mutation reporting | WP01 | No |
| T009 | Write regression tests for WP01 | WP01 | No |
| T010 | Assert all executable WPs appear in lane assignment | WP02 | No |
| T011 | Fail diagnostically on executable WPs missing ownership manifests | WP02 | No |
| T012 | Add planning-artifact exclusion diagnostic to output | WP02 | No |
| T013 | Add glob-match validation warning for zero-match owned_files | WP02 | No |
| T014 | Add warning for src/** fallback in ownership inference | WP02 | No |
| T015 | Write regression tests for WP02 | WP02 | No |
| T016 | Add CollapseReport data model to lanes/models.py | WP03 | No |
| T017 | Record collapse events during union-find rules | WP03 | No |
| T018 | Refine Rule 3 — gate surface heuristic on non-disjoint ownership | WP03 | No |
| T019 | Count independent-WP collapses in report | WP03 | No |
| T020 | Wire collapse report into finalize-tasks and compute_lanes output | WP03 | No |
| T021 | Write regression tests for WP03 | WP03 | No |
| T022 | Add pipe-table row detection to mark-status | WP04 | [P] |
| T023 | Implement pipe-table status update logic | WP04 | [P] |
| T024 | Standardize tasks template to checkbox format | WP04 | [P] |
| T025 | Write regression tests for WP04 | WP04 | [P] |
| T026 | Fix --feature to --mission in middleware.py error message | WP05 | [P] |
| T027 | Fix --feature to --mission in store.py error message | WP05 | [P] |
| T028 | Add --mission hint to shim template | WP05 | [P] |
| T029 | Fix tasks.md template context resolve example | WP05 | [P] |
| T030 | Audit all template command examples for missing --mission | WP05 | [P] |
| T031 | Improve require_explicit_feature error message | WP05 | [P] |
| T032 | Write regression tests for WP05 | WP05 | [P] |
| T033 | Fix --feature command_hint in 5 require_explicit_feature callers | WP05 | [P] |

## Work Package Execution Order

**Phase 1 (parallel)**: WP01, WP02, WP05 — no inter-dependencies, disjoint file ownership
**Phase 2 (parallel)**: WP03, WP04 — WP03 depends on WP02 (lane computation); WP04 depends on WP01 + WP05 (shared tasks.py and tasks template ownership)

---

## WP01 — Dependency and Frontmatter Truth

**Priority**: P0
**Issues**: #406, #417
**Prompt**: [tasks/WP01-dependency-frontmatter-truth.md](tasks/WP01-dependency-frontmatter-truth.md)
**Estimated size**: ~550 lines

### Summary

Fix the `finalize-tasks` pipeline so it (a) parses both inline and bullet-list dependency formats, (b) fails loudly on non-empty disagreement between tasks.md and frontmatter, (c) preserves existing deps when parser finds nothing, (d) uses the correct FrontmatterManager API for list-typed fields, (e) gates all file mutations behind the `--validate-only` flag, and (f) reports mutations accurately.

### Included Subtasks

- [x] T001 Extract shared dependency parser into reusable module
- [x] T002 Add bullet-list dependency format recognition
- [x] T003 Wire both finalize-tasks entry points to shared parser
- [x] T004 Implement disagree-loud on non-empty dependency conflict
- [x] T005 Fix set_scalar type mismatch — use FrontmatterManager for list fields
- [x] T006 Gate all mutations on validate_only flag
- [x] T007 Implement validate-only mutation report
- [x] T008 Implement accurate per-WP mutation reporting
- [x] T009 Write regression tests for WP01

### Dependencies

None — can start immediately.

### Risks

- Changing the dependency parser could break existing features that use inline format. Mitigate with regression tests against both formats.
- The two entry points (mission.py and tasks.py) must remain synchronized per C-004.

---

## WP02 — Lane Materialization Correctness

**Priority**: P0
**Issues**: #422 (completeness half)
**Prompt**: [tasks/WP02-lane-materialization-correctness.md](tasks/WP02-lane-materialization-correctness.md)
**Estimated size**: ~400 lines

### Summary

Ensure lane computation produces a lane assignment for every executable WP, fails diagnostically when assignment is impossible, and warns on ownership problems (zero-match globs, broad fallbacks).

### Included Subtasks

- [x] T010 Assert all executable WPs appear in lane assignment
- [x] T011 Fail diagnostically on executable WPs missing ownership manifests
- [x] T012 Add planning-artifact exclusion diagnostic to output
- [x] T013 Add glob-match validation warning for zero-match owned_files
- [x] T014 Add warning for src/** fallback in ownership inference
- [x] T015 Write regression tests for WP02

### Dependencies

None — can start immediately.

### Risks

- Failing on missing manifests could break features where ownership inference previously filled gaps silently. Mitigate by ensuring the inference path still works — only fail when inference cannot produce a manifest at all.

---

## WP03 — Realistic Parallelism Preservation

**Priority**: P1
**Issues**: #423
**Prompt**: [tasks/WP03-realistic-parallelism-preservation.md](tasks/WP03-realistic-parallelism-preservation.md)
**Estimated size**: ~450 lines

### Summary

Refine the lane computation algorithm so that surface-heuristic merging (Rule 3) does not collapse WPs with provably disjoint ownership. Add a CollapseReport data model that records every union event with rule and evidence. Wire the report into finalize-tasks output.

### Included Subtasks

- [ ] T016 Add CollapseReport data model to lanes/models.py
- [ ] T017 Record collapse events during union-find rules
- [ ] T018 Refine Rule 3 — gate surface heuristic on non-disjoint ownership
- [ ] T019 Count independent-WP collapses in report
- [ ] T020 Wire collapse report into finalize-tasks and compute_lanes output
- [ ] T021 Write regression tests for WP03

### Dependencies

Depends on WP02 — WP02 adds assertions and diagnostics to compute_lanes; WP03 builds on those changes to refine rules and add collapse reporting.

### Risks

- Changing Rule 3 could alter lane assignments for existing mid-implementation features. Mitigate by running compute_lanes against all kitty-specs/ features and comparing output before/after (C-005).

---

## WP04 — Mutable Task-State Compatibility

**Priority**: P0
**Issues**: #438
**Prompt**: [tasks/WP04-mutable-task-state-compatibility.md](tasks/WP04-mutable-task-state-compatibility.md)
**Estimated size**: ~300 lines

### Summary

Add pipe-table row parsing and mutation to `mark-status` so it can update task state in both checkbox and pipe-table formatted `tasks.md` files. Standardize future generation to checkbox format only.

### Included Subtasks

- [ ] T022 Add pipe-table row detection to mark-status
- [ ] T023 Implement pipe-table status update logic
- [ ] T024 Standardize tasks template to checkbox format
- [ ] T025 Write regression tests for WP04

### Dependencies

Depends on WP01, WP05. WP01 owns `tasks.py` (shared file); WP05 owns the tasks template (shared file). WP04 modifies `mark_status` in `tasks.py` and task-format instructions in the template; WP01 and WP05 must complete their changes to these files first.

### Risks

- Pipe-table status marker regex must not corrupt the Parallel column (`[P]`) — it must target a dedicated status column or use column-position-aware matching. Mitigate by testing against the real 063 tasks.md artifact.
- The existing pipe-table format has no dedicated status column. The `[P]` in column 4 is the Parallel marker, not a status marker. The implementation must either add a status column convention or use a different status representation that doesn't collide with `[P]`.

---

## WP05 — Command Ergonomics for External Agents

**Priority**: P1
**Issues**: #434
**Prompt**: [tasks/WP05-command-ergonomics-agents.md](tasks/WP05-command-ergonomics-agents.md)
**Estimated size**: ~350 lines

### Summary

Fix all generated command guidance so that `--mission <slug>` is present wherever required. Fix inconsistent flag naming (`--feature` vs `--mission`) in error messages. Improve error message quality with complete copy-pasteable examples.

### Included Subtasks

- [ ] T026 Fix --feature to --mission in middleware.py error message
- [ ] T027 Fix --feature to --mission in store.py error message
- [ ] T028 Add --mission hint to shim template
- [ ] T029 Fix tasks.md template context resolve example
- [ ] T030 Audit all template command examples for missing --mission
- [ ] T031 Improve require_explicit_feature error message
- [ ] T032 Write regression tests for WP05
- [ ] T033 Fix --feature command_hint in 5 require_explicit_feature callers

### Dependencies

None — can start immediately.

### Risks

- Shim template changes require a migration to propagate to existing projects. This is handled by the standard `spec-kitty upgrade` path — no additional risk.
