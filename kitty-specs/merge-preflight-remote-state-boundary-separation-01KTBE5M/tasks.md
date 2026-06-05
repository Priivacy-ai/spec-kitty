# Tasks: Merge Preflight Remote-State Boundary Separation

**Mission**: merge-preflight-remote-state-boundary-separation-01KTBE5M
**Mission ID**: 01KTBE5MPD24VTVFHXKCF8MGHN
**Target branch**: `main`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Subtask Index

| ID   | Description                                                             | WP   | Parallel |
|------|-------------------------------------------------------------------------|------|----------|
| T001 | Author ADR for merge-publish layer boundary                             | WP01 |          |
| T002 | Create `push_preflight.py` skeleton with types and `TargetBranchPushSafetyResult` | WP01 |          |
| T003 | Move fetch/inspect functions from `preflight.py` to `push_preflight.py` | WP01 |          |
| T004 | Implement `check_push_safety()` in `push_preflight.py`                  | WP01 |          |
| T005 | Deprecate `is_safe`; add `is_safe_to_push` to `TargetBranchSyncStatus` | WP01 |          |
| T006 | Strip domain-incompatible code from `preflight.py`                      | WP02 |          |
| T007 | Gate `_enforce_target_branch_sync_preflight` with `if push:` in `merge.py` | WP02 |          |
| T008 | Add `push_requested` field to `MergeState` with resume wiring           | WP02 |          |
| T009 | Invert existing blocked-ahead test assertions                           | WP03 | [P]      |
| T010 | Add push-path safety tests (push=True/False × state matrix)             | WP03 | [P]      |
| T011 | Add #1706 regression test (local ahead+behind, no-push, merge completes)| WP03 |          |
| T012 | Remove focused-PR-path workaround from `AGENTS.md`                      | WP04 | [P]      |
| T013 | Add `CHANGELOG.md` entry for behaviour change                           | WP04 | [P]      |

---

## Work Package 1 — Publish-Layer Module and Boundary Types

**Goal**: Create `push_preflight.py` with all remote-state infrastructure, author the ADR, and deprecate the inverted `is_safe` predicate.

**Priority**: P0 — foundational; WP02 and WP03 depend on it

**Dependencies**: none

**Estimated prompt size**: ~380 lines

**Subtasks**:
- [x] T001 Author ADR for merge-publish layer boundary (WP01)
- [x] T002 Create `push_preflight.py` skeleton with types and `TargetBranchPushSafetyResult` (WP01)
- [x] T003 Move fetch/inspect functions from `preflight.py` to `push_preflight.py` (WP01)
- [x] T004 Implement `check_push_safety()` in `push_preflight.py` (WP01)
- [x] T005 Deprecate `is_safe`; add `is_safe_to_push` to `TargetBranchSyncStatus` (WP01)

**Success criteria**:
- `push_preflight.py` exports `check_push_safety`, `TargetBranchPushSafetyResult`, `TargetBranchSyncStatus`, `TargetBranchRefreshStatus`
- `preflight.py` no longer imports or defines any network-I/O functions
- ADR committed to `architecture/3.x/adr/2026-06-05-1-merge-publish-layer-boundary.md`
- `mypy --strict` passes on `push_preflight.py`

**Prompt**: [tasks/WP01-publish-layer-module.md](tasks/WP01-publish-layer-module.md)

---

## Work Package 2 — Domain Cleanup, Call-Site Gate, and MergeState Field

**Goal**: Remove remote-state code from `preflight.py`, gate the preflight call on push intent in `merge.py`, add `push_requested` to `MergeState`.

**Priority**: P0

**Dependencies**: WP01

**Estimated prompt size**: ~320 lines

**Subtasks**:
- [ ] T006 Strip domain-incompatible code from `preflight.py` (WP02)
- [ ] T007 Gate `_enforce_target_branch_sync_preflight` with `if push:` in `merge.py` (WP02)
- [ ] T008 Add `push_requested` field to `MergeState` with resume wiring (WP02)

**Success criteria**:
- `spec-kitty merge` without `--push` completes without network I/O in a git fixture where local is ahead of origin
- `spec-kitty merge --push` still triggers origin sync check before push step
- Resumed merge with `push_requested=True` in state performs the push check
- `mypy --strict` passes on all three modified files

**Prompt**: [tasks/WP02-domain-cleanup-and-call-site.md](tasks/WP02-domain-cleanup-and-call-site.md)

---

## Work Package 3 — Test Coverage

**Goal**: Invert blocked-ahead assertions, add push-path matrix tests, add #1706 regression test.

**Priority**: P1

**Dependencies**: WP02

**Estimated prompt size**: ~340 lines

**Subtasks**:
- [ ] T009 Invert existing blocked-ahead test assertions (WP03)
- [ ] T010 Add push-path safety tests (push=True/False × state matrix) (WP03)
- [ ] T011 Add #1706 regression test (local ahead+behind, no-push, merge completes) (WP03)

**Success criteria**:
- All existing merge preflight tests pass with updated assertions
- New parametrized tests cover all six origin states × push/no-push combinations
- `pytest tests/merge/test_target_branch_preflight.py -v` exits 0
- Coverage for `push_preflight.py` ≥90%

**Prompt**: [tasks/WP03-test-coverage.md](tasks/WP03-test-coverage.md)

---

## Work Package 4 — Documentation

**Goal**: Remove the outdated focused-PR-path workaround from `AGENTS.md`; document the behaviour change in `CHANGELOG.md`.

**Priority**: P1

**Dependencies**: WP02 (confirms behaviour is changed)

**Estimated prompt size**: ~130 lines

**Subtasks**:
- [ ] T012 Remove focused-PR-path workaround from `AGENTS.md` (WP04)
- [ ] T013 Add `CHANGELOG.md` entry for behaviour change (WP04)

**Success criteria**:
- `AGENTS.md` no longer advises users to use the PR path when local main is ahead
- `CHANGELOG.md` entry accurately describes: local merge no longer blocked by origin sync state; push-safety check now fires only when `--push` is requested

**Prompt**: [tasks/WP04-documentation.md](tasks/WP04-documentation.md)

---

## Dependency Graph

```
WP01 (publish-layer module)
  └── WP02 (domain cleanup + call site)
        ├── WP03 (tests)
        └── WP04 (docs)    ← WP03 and WP04 can run in parallel after WP02
```

## Parallelization

- WP01 → WP02 (sequential, WP02 builds on WP01's module)
- WP03 ∥ WP04 (both depend on WP02, no file overlap, can run concurrently)
- Within WP03: T009 and T010 are `[P]` (different test cases, same file — coordinate via branches)
- Within WP04: T012 and T013 are `[P]` (different files)
