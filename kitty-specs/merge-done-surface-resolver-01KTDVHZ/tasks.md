# Tasks: Merge Done-Marking Surface Resolver

**Mission**: merge-done-surface-resolver-01KTDVHZ (01KTDVHZKGCHCW6HQ4V577PNES)
**Branch**: `main` → merges into `main`
**Generated**: 2026-06-06T07:19:42Z

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T005 | Study topology resolution in status_transition.py + transaction.py | WP01 | [P] |
| T006 | Implement `resolve_status_surface` in surface_resolver.py | WP01 | – |
| T007 | Write unit tests for both topologies + missing-meta error | WP01 | – |
| T008 | mypy --strict + ruff + circular-import check | WP01 | – |
| T000 | Write failing ATDD test for coord-branch done assertion — RED commit before any implementation | WP02 | – |
| T001 | Enumerate status write sites in merge.py + called modules | WP02 | [P] |
| T002 | Enumerate status read sites in merge.py + called modules | WP02 | [P] |
| T003 | Assess each site for locate-vs-observe divergence | WP02 | – |
| T004 | Document audit findings as code comment in merge.py | WP02 | – |
| T009 | Read `_mark_wp_merged_done` and trace feature_dir into emit path | WP02 | – |
| T010 | Update `_mark_wp_merged_done` to use `resolve_status_surface` | WP02 | – |
| T011 | Update `_assert_merged_wps_reached_done` to use `resolve_status_surface` | WP02 | – |
| T012 | Apply any additional fixes from audit; document if none | WP02 | – |
| T013 | Run pytest + mypy on changed files; confirm no regressions | WP02 | – |
| T014 | Build `coord_branch_mission_fixture` pytest fixture | WP03 | – |
| T015 | Add planning-only merge test with coord branch (no mocking) | WP03 | – |
| T016 | Add code-change merge test with coord branch (no mocking) | WP03 | – |
| T017 | Add coord-branch test to test_merge_done_recording.py | WP03 | – |
| T018 | Coverage check: 90%+ on surface_resolver.py new paths | WP03 | – |
| T019 | Write CHANGELOG.md entry | WP04 | – |
| T020 | Run full suite gate: pytest + mypy --strict + ruff | WP04 | – |
| T021 | Verify audit comment in merge.py; update spec.md FR statuses | WP04 | – |

---

## Work Package 1: Surface Resolver Implementation

**Priority**: Foundation
**Execution mode**: `code_change`
**Prompt**: [tasks/WP01-surface-resolver.md](tasks/WP01-surface-resolver.md)
**Dependencies**: none
**Estimated prompt size**: ~340 lines

**Goal**: Introduce `src/specify_cli/coordination/surface_resolver.py` with a fully typed, tested `resolve_status_surface(repo_root, mission_slug) -> Path` function.

**Included subtasks:**
- [ ] T005 Study topology resolution in status_transition.py + transaction.py (WP01)
- [ ] T006 Implement `resolve_status_surface` in surface_resolver.py (WP01)
- [ ] T007 Write unit tests for both topologies + missing-meta error (WP01)
- [ ] T008 mypy --strict + ruff + circular-import check (WP01)

**Success criteria**: New module exists, all unit tests pass, mypy clean, no circular imports introduced.

---

## Work Package 2: Merge-Path Audit and Wire Resolver

**Priority**: Core fix
**Execution mode**: `code_change`
**Prompt**: [tasks/WP02-wire-resolver.md](tasks/WP02-wire-resolver.md)
**Dependencies**: WP01
**Estimated prompt size**: ~480 lines

**Goal**: Audit every status write/read site on the merge path for the locate-vs-observe surface divergence class; document findings as a code comment in `merge.py`; then wire `resolve_status_surface` into both done-marking functions.

**Included subtasks:**
- [ ] T000 Write failing ATDD test for coord-branch done assertion — RED commit before any implementation (WP02)
- [ ] T001 Enumerate status write sites in merge.py + called modules (WP02)
- [ ] T002 Enumerate status read sites in merge.py + called modules (WP02)
- [ ] T003 Assess each site for locate-vs-observe divergence (WP02)
- [ ] T004 Document audit findings as code comment in merge.py (WP02)
- [ ] T009 Read `_mark_wp_merged_done` and trace feature_dir into emit path (WP02)
- [ ] T010 Update `_mark_wp_merged_done` to use `resolve_status_surface` (WP02)
- [ ] T011 Update `_assert_merged_wps_reached_done` to use `resolve_status_surface` (WP02)
- [ ] T012 Apply any additional fixes from audit; document if none (WP02)
- [ ] T013 Run pytest + mypy on changed files; confirm no regressions (WP02)

**Success criteria**: Both functions use the resolver; audit comment in `merge.py`; `pytest tests/` passes; `mypy --strict` clean on `merge.py` and `surface_resolver.py`.

**Parallel opportunities**: T001 and T002 can be done in a single parallel read pass before T003.

---

## Work Package 3: Regression Tests

**Priority**: Core parity ratchet
**Execution mode**: `code_change`
**Prompt**: [tasks/WP03-regression-tests.md](tasks/WP03-regression-tests.md)
**Dependencies**: WP02
**Estimated prompt size**: ~420 lines

**Goal**: Add regression tests that exercise both done-marking functions without mocking them, against fixtures that include `coordination_branch`. Cover planning-only and code-change merge paths.

**Included subtasks:**
- [ ] T014 Build `coord_branch_mission_fixture` pytest fixture (WP03)
- [ ] T015 Add planning-only merge test with coord branch (no mocking) (WP03)
- [ ] T016 Add code-change merge test with coord branch (no mocking) (WP03)
- [ ] T017 Add coord-branch test to test_merge_done_recording.py (WP03)
- [ ] T018 Coverage check: 90%+ on surface_resolver.py new paths (WP03)

**Success criteria**: All new tests pass; no mocking of `_mark_wp_merged_done` or `_assert_merged_wps_reached_done`; 90%+ coverage on `surface_resolver.py`.

**Risk**: Fixture complexity — creating a realistic coordination worktree stub may require understanding `CoordinationWorkspace.resolve` conventions; reference `coordination/transaction.py` lines ~598–765.

---

## Work Package 4: CHANGELOG and Final Gate

**Priority**: Closeout
**Execution mode**: `code_change`
**Prompt**: [tasks/WP04-changelog-final-gate.md](tasks/WP04-changelog-final-gate.md)
**Dependencies**: WP03
**Estimated prompt size**: ~200 lines

**Goal**: Write the `CHANGELOG.md` entry, run the full validation suite as a final gate, and confirm all artifacts are in order.

**Included subtasks:**
- [ ] T019 Write CHANGELOG.md entry (WP04)
- [ ] T020 Run full suite gate: pytest + mypy --strict + ruff (WP04)
- [ ] T021 Verify audit comment in merge.py; update spec.md FR statuses (WP04)

**Success criteria**: `CHANGELOG.md` updated; full suite green; spec.md FR statuses updated to `Accepted`.

---

## Dependency Graph

```
WP01 (resolver) ──→ WP02 (audit+wire) ──→ WP03 (tests) ──→ WP04 (final)
```

Sequential pipeline: each WP depends on the previous.
WP01 can start immediately.
