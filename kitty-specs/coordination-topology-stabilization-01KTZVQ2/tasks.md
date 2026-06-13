# Tasks: Coordination Topology Stabilization

**Mission**: coordination-topology-stabilization-01KTZVQ2
**Branch**: main → main
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Add placement-aware is_committed() overload in _substantive.py | WP01 | N |
| T002 | Migrate setup-plan entry gate caller to use coord-aware is_committed() | WP01 | N |
| T003 | Convert _planning_commit_worktree silent fallbacks to structured errors | WP01 | N |
| T004 | Regression test: setup-plan passes with spec on coord branch only | WP01 | N |
| T005 | Architectural lint: no new callers of the old 2-arg is_committed form | WP01 | N |
| T006 | Fix _feature_dir_file_paths root anchor in implement.py | WP02 | N |
| T007 | Add path_is_under_worktrees() rejection gate in safe_commit | WP02 | P |
| T008 | Add path_is_under_worktrees() guard in BookkeepingTransaction.write_artifact | WP02 | P |
| T009 | Architectural ratchet test: git ls-files .worktrees/ must return empty | WP02 | N |
| T010 | Regression test for writer fix (coord-worktree paths not staged) | WP02 | N |
| T011 | Replace "unknown" branches in query_current_state with MISSION_NOT_FOUND | WP03 | N |
| T012 | Fix StatusReadPathNotFound swallow in _resolve_mission_slug | WP03 | N |
| T013 | Fix advancing-mode --result not-found path | WP03 | N |
| T014 | CLI tests: non-zero exit + named error in both human and JSON modes | WP03 | N |
| T015 | Classify literal vs glob entries in validate_glob_matches | WP04 | N |
| T016 | Promote literal-path zero-match to hard error with nearest-match suggestion | WP04 | N |
| T017 | Add create_intent: true annotation support for planned-new-file | WP04 | N |
| T018 | Route ownership_warnings to stderr (JSON mode) and human-readable output | WP04 | N |
| T019 | Re-validate ownership at lane-compute time to block phantoms in lanes.json | WP04 | N |
| T020 | Update tasks-finalize source prompt to require acting on warnings | WP04 | N |
| T021 | Add message-capture expression classifier in _literal_findings_for_assertion | WP05 | N |
| T022 | Fix changed_literals last-wins dict (report all removal sites, not just last) | WP05 | N |
| T023 | Add confidence threshold/grouping in merge summary for stale-assertion output | WP05 | N |
| T024 | Regression tests for message-content FP suppression | WP05 | N |
| T025 | Fix mutate_matrix in --no-commit mode (accept.py:284) | WP06 | N |
| T026 | Implement write-aware dirty baseline: snapshot before writes + exclude accept-owned paths | WP06 | N |
| T027 | Call _commit_residual_acceptance_artifacts on ALL writing exit paths (not just success) | WP06 | N |
| T028 | Fix write-target split in _check_lane_gates (use coord-resolved feature_dir) | WP06 | N |
| T029 | Convergence regression test: run accept twice same state → same pass/fail | WP06 | N |
| T030 | --no-commit read-only regression test: git status identical before/after | WP06 | N |
| T031 | Add merge-completion postcondition check for retrospective.yaml | WP07 | N |
| T032 | Consolidate run_terminus dead code with _run_retrospective_learning_capture | WP07 | N |
| T033 | Emit RetrospectiveSkipped/CaptureFailed event on failure/skip | WP07 | N |
| T034 | Fix _record_path_str to use correct canon path (FR-006/#1771 canon) | WP07 | N |
| T035 | Regression test: merge path → retrospective.yaml or skip event present | WP07 | N |
| T036 | Add workflow-failures-log.md ingestor to retrospective generator | WP08 | N |
| T037 | Add analysis-report.md and mission-review-report.md ingestors | WP08 | P |
| T038 | Revisit "helped only by contrast" rule to allow findings on clean missions | WP08 | N |
| T039 | Fix stale docstring in generator.py:844-846 | WP08 | P |
| T040 | Golden test: mission-131 fixture → non-empty findings (not ran_no_findings) | WP08 | N |
| T041 | Add coord-owned-residue exclusion to advance_branch_ref (shared with #1814) | WP09 | N |
| T042 | Roll out advance_branch_ref as standard post-write primary-ref sync | WP09 | N |
| T043 | Retire _ensure_branch_checked_out shim | WP09 | N |
| T044 | End-to-end test: zero manual ff-merges through full coordination lifecycle | WP09 | N |
| T045 | Remove 26 tracked .worktrees/ paths via git rm -r --cached | WP10 | N |
| T046 | Verify spec-kitty doctor passes after cleanup | WP10 | N |
| T047 | Verify is_committed interaction defect: test both pre- and post-cleanup states | WP10 | N |
| T048 | Pre-flight: verify PR #1895 scope before starting WP01/WP03 implementation | WP01 | N |
| T049 | Remove xfail marker from test_worktrees_index_clean.py once WP02 ratchet lands | WP10 | N |

---

## Work Packages

### Phase 1 — Foundation (dispatch first; all parallelizable among themselves)

---

## WP01 — Coordination-Aware Read Primitive

**File**: [tasks/WP01-coord-aware-read-primitive.md](tasks/WP01-coord-aware-read-primitive.md)
**Priority**: P1-Critical | **Closes**: FR-003 | **Issues**: #1884
**Effort**: Medium (~5 subtasks, ~350 lines)

**Goal**: Add a placement-aware `is_committed()` that consults the coordination branch before primary HEAD, so all gate checks see coord-branch commits as valid. This is the foundational fix that WP06 and WP09 depend on.

**Subtasks**:
- [x] T001 Add placement-aware is_committed() overload in _substantive.py (WP01)
- [x] T002 Migrate setup-plan entry gate caller to use coord-aware is_committed() (WP01)
- [x] T003 Convert _planning_commit_worktree silent fallbacks to structured errors (WP01)
- [x] T004 Regression test: setup-plan passes with spec on coord branch only (WP01)
- [x] T005 Architectural lint: no new callers of the old 2-arg is_committed form (WP01)
- [x] T048 Pre-flight: verify PR #1895 scope before starting implementation (WP01)

**Dependencies**: none
**Unblocks**: WP06, WP09 (partially WP07)

---

## WP02 — .worktrees/ Writer Fix + Ratchet

**File**: [tasks/WP02-worktrees-writer-fix.md](tasks/WP02-worktrees-writer-fix.md)
**Priority**: P1-Critical | **Closes**: FR-005 (writer half) | **Issues**: #1887
**Effort**: Medium (~5 subtasks, ~320 lines)

**Goal**: Stop `.worktrees/<coord>/` paths entering the git index at the writer level. Add fail-closed guards at `_feature_dir_file_paths`, `safe_commit`, and `BookkeepingTransaction.write_artifact`. Add architectural ratchet test. (Cleanup PR is WP10 after ratchet lands.)

**Subtasks**:
- [x] T006 Fix _feature_dir_file_paths root anchor in implement.py (WP02)
- [x] T007 Add path_is_under_worktrees() rejection gate in safe_commit (WP02)
- [x] T008 Add path_is_under_worktrees() guard in BookkeepingTransaction.write_artifact (WP02)
- [x] T009 Architectural ratchet test: git ls-files .worktrees/ must return empty (WP02)
- [x] T010 Regression test for writer fix (WP02)

**Dependencies**: none
**Unblocks**: WP10

---

## WP03 — next Fail-Closed Query Mode

**File**: [tasks/WP03-next-fail-closed.md](tasks/WP03-next-fail-closed.md)
**Priority**: P2-High | **Closes**: FR-004 | **Issues**: #1885
**Effort**: Small (~4 subtasks, ~250 lines)

**Goal**: Replace the silent exit-0 "unknown" stub in `query_current_state` with a structured `MISSION_NOT_FOUND` error that exits non-zero in both human and JSON modes.

**Subtasks**:
- [x] T011 Replace "unknown" branches in query_current_state with MISSION_NOT_FOUND (WP03)
- [x] T012 Fix StatusReadPathNotFound swallow in _resolve_mission_slug (WP03)
- [x] T013 Fix advancing-mode --result not-found path (WP03)
- [x] T014 CLI tests: non-zero exit + named error in both modes (WP03)

**Dependencies**: none (coordinate with PR #1895 before starting)

---

## WP04 — Ownership Warning Routing

**File**: [tasks/WP04-ownership-warning-routing.md](tasks/WP04-ownership-warning-routing.md)
**Priority**: P2-High | **Closes**: FR-006 | **Issues**: #1888
**Effort**: Medium (~6 subtasks, ~380 lines)

**Goal**: Promote literal-path zero-match from warning to hard error; route all ownership warnings to stderr; add planned-new-file escape hatch; re-validate at lane-compute time; update source prompt.

**Subtasks**:
- [x] T015 Classify literal vs glob entries in validate_glob_matches (WP04)
- [x] T016 Promote literal-path zero-match to hard error with nearest-match suggestion (WP04)
- [x] T017 Add create_intent: true annotation support for planned-new-file (WP04)
- [x] T018 Route ownership_warnings to stderr in JSON mode and human-readable output (WP04)
- [x] T019 Re-validate ownership at lane-compute time (WP04)
- [x] T020 Update tasks-finalize source prompt to require acting on warnings (WP04)

**Dependencies**: none

---

## WP05 — Stale-Assertion Message-Content Classifier

**File**: [tasks/WP05-stale-assertion-classifier.md](tasks/WP05-stale-assertion-classifier.md)
**Priority**: P2-High | **Closes**: FR-009 | **Issues**: #1886
**Effort**: Small (~4 subtasks, ~280 lines)

**Goal**: Classify message-capture expressions in `_literal_findings_for_assertion`; suppress or demote findings where the literal is inside `str(exc)`, `.message`, `.stderr`, etc. Fix the `changed_literals` last-wins dict and add confidence grouping.

**Subtasks**:
- [x] T021 Add message-capture expression classifier in _literal_findings_for_assertion (WP05)
- [x] T022 Fix changed_literals last-wins dict (WP05)
- [x] T023 Add confidence threshold/grouping in merge summary (WP05)
- [x] T024 Regression tests for message-content FP suppression (WP05)

**Dependencies**: none

---

### Phase 2 — Gate Fixes (dispatch after WP01 for WP06; WP07/WP08 can parallel)

---

## WP06 — Accept Gate Transactional Ownership

**File**: [tasks/WP06-accept-gate-transactional.md](tasks/WP06-accept-gate-transactional.md)
**Priority**: P1-Critical | **Closes**: FR-001, FR-002 | **Issues**: #1883
**Effort**: Medium-large (~6 subtasks, ~440 lines)

**Goal**: Make `--no-commit` truly read-only; implement write-aware dirty baseline; commit residue on all writing exit paths; fix write-target split.

**Subtasks**:
- [x] T025 Fix mutate_matrix in --no-commit mode (WP06)
- [x] T026 Implement write-aware dirty baseline with accept-owned exclusions (WP06)
- [x] T027 Call _commit_residual_acceptance_artifacts on ALL writing exit paths (WP06)
- [x] T028 Fix write-target split in _check_lane_gates (WP06)
- [x] T029 Convergence regression test (WP06)
- [x] T030 --no-commit read-only regression test (WP06)

**Dependencies**: WP01

---

## WP07 — Terminus Retrospective Triggering

**File**: [tasks/WP07-retrospective-triggering.md](tasks/WP07-retrospective-triggering.md)
**Priority**: P1-Critical | **Closes**: FR-007 | **Issues**: #1164
**Effort**: Medium (~5 subtasks, ~360 lines)

**Goal**: Add merge-completion postcondition; consolidate dead `run_terminus` with live capture path; emit `RetrospectiveSkipped` event on failure; fix `_record_path_str` stale path.

**Subtasks**:
- [x] T031 Add merge-completion postcondition check for retrospective.yaml (WP07)
- [x] T032 Consolidate run_terminus dead code with _run_retrospective_learning_capture (WP07)
- [x] T033 Emit RetrospectiveSkipped/CaptureFailed event on failure/skip (WP07)
- [x] T034 Fix _record_path_str to use correct canon path (WP07)
- [x] T035 Regression test: merge path → retrospective.yaml or skip event (WP07)

**Dependencies**: none (triggering half; content in WP08 is independent)

---

## WP08 — Retrospective Generator Ingestors

**File**: [tasks/WP08-retrospective-ingestors.md](tasks/WP08-retrospective-ingestors.md)
**Priority**: P1-Critical | **Closes**: FR-008 | **Issues**: #1164
**Effort**: Medium (~5 subtasks, ~320 lines)

**Goal**: Add mission-local artifact ingestors (workflow-failures-log.md, analysis-report.md, mission-review-report.md) to the retrospective generator; revisit "helped only by contrast" rule; fix stale docstring.

**Subtasks**:
- [x] T036 Add workflow-failures-log.md ingestor (WP08)
- [x] T037 Add analysis-report.md and mission-review-report.md ingestors (WP08)
- [x] T038 Revisit "helped only by contrast" rule in generator.py (WP08)
- [x] T039 Fix stale docstring in generator.py:844-846 (WP08)
- [x] T040 Golden test: mission-131 fixture → non-empty findings (WP08)

**Dependencies**: none (content half; independent of WP07)

---

### Phase 3 — Automation and Cleanup (dispatch last)

---

## WP09 — ff-merge Treadmill Elimination

**File**: [tasks/WP09-ffmerge-treadmill.md](tasks/WP09-ffmerge-treadmill.md)
**Priority**: P3-Medium | **Closes**: FR-010 | **Issues**: #1878
**Effort**: Medium (~4 subtasks, ~300 lines)

**Goal**: Add coord-owned-residue exclusion to `advance_branch_ref`; roll it out as standard post-write primary-ref sync; retire `_ensure_branch_checked_out` shim.

**Subtasks**:
- [x] T041 Add coord-owned-residue exclusion to advance_branch_ref (WP09)
- [x] T042 Roll out advance_branch_ref as standard post-write sync (WP09)
- [x] T043 Retire _ensure_branch_checked_out shim (WP09)
- [x] T044 End-to-end test: zero manual ff-merges through full lifecycle (WP09)

**Dependencies**: WP01, WP06

---

## WP10 — .worktrees/ Index Cleanup

**File**: [tasks/WP10-worktrees-index-cleanup.md](tasks/WP10-worktrees-index-cleanup.md)
**Priority**: P3-Medium | **Closes**: FR-005 (cleanup half) | **Issues**: #1887
**Effort**: Small (~3 subtasks, ~200 lines)

**Goal**: Remove the 26 currently tracked `.worktrees/` paths from `origin/main`. Verify doctor passes. Test the IC-01/IC-02 interaction defect in both pre- and post-cleanup states.

**Subtasks**:
- [x] T045 Remove 26 tracked .worktrees/ paths via git rm -r --cached (WP10)
- [x] T046 Verify spec-kitty doctor passes after cleanup (WP10)
- [x] T047 Verify is_committed interaction defect tested in both states (WP10)
- [x] T049 Remove xfail from test_worktrees_index_clean.py after WP02 ratchet lands (WP10)

**Dependencies**: WP01, WP02

---

## Parallelization Map

```
Phase 1 (all parallel): WP01, WP02, WP03, WP04, WP05
Phase 2 (WP01 done):    WP06, WP07, WP08 (all parallel)
Phase 3 (WP01+WP06):    WP09
Phase 3 (WP01+WP02):    WP10
```
