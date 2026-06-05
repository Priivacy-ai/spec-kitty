# Task Plan: Op Record Git Durability

**Mission**: op-records-git-durability-01KTB49K  
**Branch**: `main` → `main`  
**Date**: 2026-06-05  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Overview

Move Op record storage from `.kittify/events/profile-invocations/` (gitignored) to `kitty-ops/` (git-tracked). Wire auto-commit after `complete_invocation()`. Add `mission_id`/`wp_id` fields to `InvocationRecord`. Create `doctor ops` orphan listing. This is Step 1 of 3 from issue #1688.

**2 work packages. No WP is parallelizable with any other (WP02 depends on WP01).**

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Change `EVENTS_DIR` to `"kitty-ops"` in `invocation/writer.py` | WP01 | — |
| T002 | Change `INDEX_PATH` and fix `_append_to_index` path in `writer.py` | WP01 | [P] with T003–T005 |
| T003 | Change `LIFECYCLE_LOG_RELATIVE_PATH` in `invocation/lifecycle.py` | WP01 | [P] with T002,T004,T005 |
| T004 | Change `PROPAGATION_ERRORS_PATH` in `invocation/propagator.py` | WP01 | [P] with T002,T003,T005 |
| T005 | Add `mission_id`/`wp_id` fields to `InvocationRecord`; update `MVTP.tier_1.storage_path` | WP01 | [P] with T002–T004 |
| T006 | Add `test_writer.py` tests: EVENTS_DIR=kitty-ops, index at kitty-ops/ops-index.jsonl | WP01 | — |
| T007 | Add `test_record.py` tests: new fields, exclude_none serialisation | WP01 | — |
| T008 | Wire git auto-commit in `complete_invocation()` in `executor.py` | WP02 | — |
| T009 | Implement `list_orphan_ops()` in new `src/specify_cli/doctor/ops.py` | WP02 | [P] with T010 |
| T010 | Wire `spec-kitty doctor ops` CLI subcommand in `doctor.py` | WP02 | [P] with T009 |
| T011 | Add `test_executor.py` commit tests: T-003 (commit after complete), T-004 (restore after clean), T-005 (orphan guard) | WP02 | — |
| T012 | Add `test_executor.py` do-regression test (T-006) and mission_id/wp_id wiring test (T-007) | WP02 | [P] with T011 |
| T013 | Create `test_doctor_ops.py`: orphan detection + CLI integration tests | WP02 | — |
| T014 | Add CHANGELOG entry for `.kittify/events/` abandonment (C-002) | WP02 | [P] with T013 |

---

## Work Packages

### WP01: Storage Path Constants and Model Fields

**Priority**: P0 (foundation for all other work)  
**Estimated prompt size**: ~350 lines  
**Prompt**: [tasks/WP01-storage-path-constants.md](tasks/WP01-storage-path-constants.md)

**Goal**: Change 5 constants across 4 existing files to redirect storage from `.kittify/events/` to `kitty-ops/`. Add 2 optional fields to `InvocationRecord`. Write tests that prove the paths resolve correctly and the model serialises correctly.

**Included subtasks:**

- [x] T001 Change `EVENTS_DIR` to `"kitty-ops"` in `invocation/writer.py` (WP01)
- [x] T002 Change `INDEX_PATH` and fix `_append_to_index` path in `writer.py` (WP01)
- [x] T003 Change `LIFECYCLE_LOG_RELATIVE_PATH` in `invocation/lifecycle.py` (WP01)
- [x] T004 Change `PROPAGATION_ERRORS_PATH` in `invocation/propagator.py` (WP01)
- [x] T005 Add `mission_id`/`wp_id` fields to `InvocationRecord`; update MVTP constant (WP01)
- [x] T006 Add `test_writer.py` path tests (WP01)
- [x] T007 Add `test_record.py` field tests (WP01)

**Implementation sketch**:
1. Edit `writer.py`: change 2 constants, fix `_append_to_index` (3 line edits)
2. Edit `lifecycle.py`: change 1 constant (1 line edit)
3. Edit `propagator.py`: change 1 constant (1 line edit)
4. Edit `record.py`: add 2 model fields, update MVTP `storage_path` string
5. Add tests to `test_writer.py` (new test class or functions)
6. Add tests to `test_record.py` (new test functions)

**Parallel opportunities**: T002–T005 edit different files and can be done in any order.

**Dependencies**: None

**Risks**:
- `_append_to_index` path is NOT driven by the `INDEX_PATH` constant (it computes independently) — must fix both the constant AND the inline computation
- `InvocationRecord` is `frozen=True` — new fields must have defaults (`= None`) or existing tests break

---

### WP02: Auto-Commit, Doctor Ops, and Tests

**Priority**: P0  
**Estimated prompt size**: ~420 lines  
**Prompt**: [tasks/WP02-auto-commit-and-doctor-ops.md](tasks/WP02-auto-commit-and-doctor-ops.md)

**Goal**: Wire git auto-commit in `complete_invocation()` after the `completed` event is written. Create a new `doctor/ops.py` module that lists orphan Ops. Wire `spec-kitty doctor ops` subcommand. Write tests covering all 5 spec test cases.

**Included subtasks:**

- [x] T008 Wire git auto-commit in `complete_invocation()` in `executor.py` (WP02)
- [x] T009 Implement `list_orphan_ops()` in new `src/specify_cli/doctor/ops.py` (WP02)
- [x] T010 Wire `spec-kitty doctor ops` CLI subcommand in `doctor.py` (WP02)
- [x] T011 Add executor commit tests: T-003, T-004 (restore after clean), T-005 (orphan guard) (WP02)
- [x] T012 Add do-regression test (T-006) and mission_id/wp_id wiring test (T-007) (WP02)
- [x] T013 Create `test_doctor_ops.py` orphan detection + CLI integration tests (WP02)
- [x] T014 Add CHANGELOG entry for `.kittify/events/` abandonment (WP02)

**Implementation sketch**:
1. Edit `executor.py`: add auto-commit after `write_completed()` in `complete_invocation()` — use subprocess git, catch errors, log at WARNING
2. Create `src/specify_cli/doctor/ops.py`: `list_orphan_ops()` scans `kitty-ops/*.jsonl` (excluding index/lifecycle/errors), returns files without a `completed` event line
3. Edit `doctor.py`: add `@app.command(name="ops")` function that calls `list_orphan_ops()` and renders results
4. Add tests to `test_executor.py` (using a git-repo fixture)
5. Create `tests/specify_cli/invocation/test_doctor_ops.py`

**Parallel opportunities**: T009 and T010 can be developed simultaneously (different files).

**Dependencies**: WP01 (executor tests need `kitty-ops/` as the write target)

**Risks**:
- Executor tests require a real git repo fixture — use `tmp_path` with `git init` + `git config user.email/name`
- Auto-commit must be best-effort (errors logged, not raised) — test must verify command still returns normally on commit failure
- `doctor.py` is 3000+ lines — use `grep` to find the correct insertion point before editing
