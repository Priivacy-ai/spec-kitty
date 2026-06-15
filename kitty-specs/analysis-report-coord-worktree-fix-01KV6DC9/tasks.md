# Tasks: Analysis Report Coord-Worktree Fix & Recovery UX

**Mission**: `analysis-report-coord-worktree-fix-01KV6DC9`  
**Branch**: `fix/analysis-report-coord-worktree-fix`  
**Merge target**: `fix/analysis-report-coord-worktree-fix`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Override write destination in `record_analysis()` with main-checkout path | WP01 | No |
| T002 | Unit test: `write_analysis_report` called with main-checkout path (not coord path) | WP01 | [P] |
| T003 | Integration test: `record-analysis` succeeds when coord worktree lacks `spec.md` | WP01 | [P] |
| T004 | Regression test: `record-analysis` works without coord worktree | WP01 | [P] |
| T005 | Add `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` constant to `analysis_report.py` | WP02 | No |
| T006 | Add carrier-detection branch in `check_analysis_report_current()` | WP02 | No |
| T007 | Unit test: carrier-format file returns `carrier_format_not_wrapped` reason | WP02 | [P] |
| T008 | Regression test: outer-wrapper format still returns `ok=True` | WP02 | [P] |
| T009 | Regression test: arbitrary frontmatter returns `invalid_analysis_report_artifact_type` | WP02 | [P] |
| T010 | Import `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` in `workflow.py` | WP03 | No |
| T011 | Add `carrier_format_not_wrapped` branch emitting exact recovery command | WP03 | No |
| T012 | Update `missing_analysis_report` branch to emit two-step recovery sequence | WP03 | No |
| T013 | Verify stale-inputs branch output is unchanged | WP03 | [P] |
| T014 | Unit test: carrier-format branch emits `Recovery:` line with mission slug and file path | WP03 | [P] |
| T015 | Unit test: missing branch emits `Run step 1:` and `Run step 2:` lines | WP03 | [P] |
| T016 | Append caution block to step 7 of `analyze/prompt.md` skill source | WP04 | No |
| T017 | Verify the rendered source edit (block placement, blockquote, carrier reason ref) | WP04 | [P] |
| T018 | Confirm no agent-directory copies were hand-edited (canonical-source rule) | WP04 | [P] |
| T019 | Run architectural and template-cleanliness tests to verify no regressions | WP04 | [P] |

---

## Work Package 1 — Write-Path Anchor in `record_analysis()`

**Goal**: Fix `record_analysis()` to write `analysis-report.md` to the main-checkout
mission directory, not the coord-worktree path returned by the read-path resolver.  
**Priority**: P1 — root defect; all other WPs are meaningless if this isn't fixed.  
**Independent test**: `record-analysis --mission <slug>` succeeds when a coord worktree is active and `spec.md` exists in the main checkout.  
**Estimated prompt size**: ~260 lines

### Subtasks

- [ ] T001 Override write destination in `record_analysis()` with main-checkout path (WP01)
- [ ] T002 Unit test: `write_analysis_report` called with main-checkout path (not coord path) (WP01)
- [ ] T003 Integration test: `record-analysis` succeeds when coord worktree lacks `spec.md` (WP01)
- [ ] T004 Regression test: `record-analysis` works without coord worktree (WP01)

### Implementation Notes

After `_find_feature_directory()` returns `feature_dir` (which may be the coord path),
compute `write_feature_dir = primary_feature_dir_for_mission(repo_root, feature_dir.name)`
— the **topology-blind** primitive (NOT `candidate_feature_dir_for_mission`, which is
topology-aware and would return the coord worktree). Pass `write_feature_dir` to
`write_analysis_report()`. The original `feature_dir` is still used for `placement_ref`
and `_enforce_analysis_report_write_preflight()`.

### Dependencies

None — independent of all other WPs.

### Prompt

[tasks/WP01-write-path-anchor.md](tasks/WP01-write-path-anchor.md)

---

## Work Package 2 — Named Reason Code for Carrier-Format Files

**Goal**: Add `ANALYSIS_REPORT_REASON_CARRIER_FORMAT = "carrier_format_not_wrapped"` constant
and carrier-detection branch in `check_analysis_report_current()` so the implement gate can
distinguish carrier-format files from generic artifact-type mismatches.  
**Priority**: P1 — required by WP03.  
**Independent test**: `check_analysis_report_current()` returns `reason="carrier_format_not_wrapped"` when the file has `schema: analysis-findings/v1` frontmatter.  
**Estimated prompt size**: ~320 lines

### Subtasks

- [ ] T005 Add `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` constant to `analysis_report.py` (WP02)
- [ ] T006 Add carrier-detection branch in `check_analysis_report_current()` (WP02)
- [ ] T007 Unit test: carrier-format file returns `carrier_format_not_wrapped` reason (WP02)
- [ ] T008 Regression test: outer-wrapper format still returns `ok=True` (WP02)
- [ ] T009 Regression test: arbitrary frontmatter returns `invalid_analysis_report_artifact_type` (WP02)

### Implementation Notes

In `check_analysis_report_current()`, after successful frontmatter parse and before the
`artifact_type` check: `if frontmatter.get("schema") == FINDINGS_SCHEMA_V1: return AnalysisFreshness(ok=False, stale=True, missing=False, reason=ANALYSIS_REPORT_REASON_CARRIER_FORMAT, mismatches={})`.

### Dependencies

None — independent of WP01.

### Prompt

[tasks/WP02-carrier-reason-code.md](tasks/WP02-carrier-reason-code.md)

---

## Work Package 3 — Recovery-Message Branching

**Goal**: Update `_require_current_analysis_report()` to branch on reason codes and emit
exact, copy-pasteable recovery commands per the error-recovery contract.  
**Priority**: P1 — closes the UX gap for already-affected missions.  
**Independent test**: Running `spec-kitty agent action implement` with a carrier-format
`analysis-report.md` emits a `Recovery:` line with the exact `record-analysis` command
including the file path.  
**Estimated prompt size**: ~380 lines

### Subtasks

- [ ] T010 Import `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` in `workflow.py` (WP03)
- [ ] T011 Add `carrier_format_not_wrapped` branch emitting exact recovery command (WP03)
- [ ] T012 Update `missing_analysis_report` branch to emit two-step recovery sequence (WP03)
- [ ] T013 Verify stale-inputs branch output is unchanged (WP03)
- [ ] T014 Unit test: carrier-format branch emits `Recovery:` line with mission slug and file path (WP03)
- [ ] T015 Unit test: missing branch emits `Run step 1:` and `Run step 2:` lines (WP03)

### Implementation Notes

The `mission_slug` (third parameter) and `analysis_freshness.path` are both available at the
call site and can be interpolated directly into the recovery command string. See
`contracts/error-recovery-contract.md` for the exact output format required.

### Dependencies

WP02 (needs `ANALYSIS_REPORT_REASON_CARRIER_FORMAT` constant).

### Prompt

[tasks/WP03-recovery-messages.md](tasks/WP03-recovery-messages.md)

---

## Work Package 4 — `spec-kitty.analyze` Skill Source Template Update

**Goal**: Document in the `analyze/prompt.md` skill source that writing `analysis-report.md`
directly bypasses format wrapping and will be rejected at the implement gate — preventing
future occurrences of the manual-write workaround.  
**Priority**: P2 — documentation guard against recurrence.  
**Independent test**: The caution block appears in the source template and references `carrier_format_not_wrapped`; terminology + cleanliness tests pass.  
**Estimated prompt size**: ~200 lines

### Subtasks

- [ ] T016 Append caution block to step 7 of `analyze/prompt.md` skill source (WP04)
- [ ] T017 Verify the rendered source edit (block placement, blockquote, carrier reason ref) (WP04)
- [ ] T018 Confirm no agent-directory copies were hand-edited (canonical-source rule) (WP04)
- [ ] T019 Run architectural and template-cleanliness tests to verify no regressions (WP04)

### Implementation Notes

Edit `src/doctrine/missions/mission-steps/software-dev/analyze/prompt.md` step 7 only —
this is the canonical source. Do NOT edit generated agent-directory copies and do NOT run
`spec-kitty upgrade` in this source repo: agent copies are generated downstream in consumer
projects, and this repo does not carry per-agent analyze copies. The only file this WP
changes is the source template.

### Dependencies

None — independent of all code WPs.

### Prompt

[tasks/WP04-skill-template-update.md](tasks/WP04-skill-template-update.md)
