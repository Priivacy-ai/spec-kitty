---
work_package_id: WP09
title: move-task Delegation
lane: "for_review"
dependencies:
- WP07
base_branch: 2.x
base_commit: 726239759dba411a3720af8f19e18b8dc222655e
created_at: '2026-02-08T15:02:40.958109+00:00'
subtasks:
- T043
- T044
- T045
- T046
- T047
phase: Phase 1 - Canonical Log
assignee: ''
agent: ''
shell_pid: "59111"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 -- move-task Delegation

## Review Feedback Status

> **IMPORTANT**: Before starting implementation, check the `review_status` field in this file's frontmatter.
> - If `review_status` is empty or `""`, proceed with implementation as described below.
> - If `review_status` is `"has_feedback"`, read the **Review Feedback** section below FIRST and address all feedback items before continuing.
> - If `review_status` is `"approved"`, this WP has been accepted -- no further implementation needed.

## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Refactor the existing `move_task()` function in `cli/commands/agent/tasks.py` to delegate its state mutation to the canonical `emit_status_transition()` pipeline while retaining ALL existing pre-validation logic unchanged.

**This is the highest-risk WP in the feature** because it modifies the most frequently used command in the entire system. Every AI agent calls `move_task` multiple times per work session.

**Success Criteria**:
1. `spec-kitty agent tasks move-task WP01 --to doing` works IDENTICALLY to pre-refactor behavior from the user's perspective.
2. After move-task, BOTH `status.events.jsonl` AND WP frontmatter are updated (dual-write via the emit pipeline).
3. All existing pre-validation checks (_check_unchecked_subtasks, _check_ready_for_review, _check_dependent_warnings) are preserved EXACTLY.
4. The `--no-commit` flag is still respected.
5. All existing tests in `tests/specify_cli/test_cli/test_agent_feature.py` and `tests/specify_cli/cli/commands/test_event_emission.py` continue to pass.
6. New integration tests verify the delegation produces canonical events.

## Context & Constraints

**Architecture References**:
- `plan.md` AD-8 defines the delegation pattern: move_task retains validation, delegates mutation.
- `research.md` R-3 documents the current move_task() flow (lines 592-898 in tasks.py).
- `plan.md` AD-6 shows the full fan-out pipeline that emit_status_transition triggers.

**Current move_task() Flow** (from research.md R-3):
1. `ensure_lane(to)` -- validates target lane
2. Feature detection and branch checkout
3. Locate WP file
4. Validation: agent ownership, review feedback, unchecked subtasks, uncommitted changes
5. `set_scalar(frontmatter, "lane", target)` -- update frontmatter
6. Update assignee, agent, shell_pid, review_status, reviewed_by
7. Append activity log history entry
8. Write file to disk
9. Auto-commit (if enabled)
10. `emit_wp_status_changed()` -- SaaS telemetry

**New Flow** (after this WP):
1. `resolve_lane_alias(to)` -- NEW: resolve "doing" to "in_progress" (from WP05)
2. Feature detection and branch checkout -- UNCHANGED
3. Locate WP file -- UNCHANGED
4. Validation (steps 4 above) -- UNCHANGED
5. `emit_status_transition()` -- NEW: replaces steps 5-7 of old flow. This appends event, materializes snapshot, updates frontmatter views, and emits SaaS.
6. Git add/commit (includes status.events.jsonl + status.json + WP file) -- MODIFIED: more files to stage
7. SaaS emit removed from move_task -- MOVED: now inside emit_status_transition (T033)

**Dependency Artifacts Available**:
- WP07 provides `emit_status_transition()` from `status/emit.py`.
- WP05 provides expanded lanes in `tasks_support.py` with alias resolution.

**Constraints**:
- This is a REFACTOR, not a rewrite. Change the minimum amount of code needed.
- All existing test suites must continue to pass. Run the full test suite before considering this done.
- The `--no-commit` flag must still work. When set, skip the git commit step but still run the emit pipeline.
- Additional metadata (assignee, agent, shell_pid, review_status, reviewed_by) must still be updated in frontmatter.

**Implementation Command**: `spec-kitty implement WP09 --base WP07` (merge WP05 branch manually)

## Subtasks & Detailed Guidance

### T043: Refactor move_task() Delegation

**Purpose**: Replace the manual frontmatter set_scalar/write/emit sequence with a call to emit_status_transition().

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/tasks.py` and locate the `move_task()` function.
2. Identify the state mutation section (after all validation, where `set_scalar` is called for "lane").
3. Replace the following sequence:
   ```python
   # OLD CODE (approximate):
   set_scalar(frontmatter, "lane", target)
   # ... set_scalar for assignee, agent, etc.
   # ... append_activity_log(...)
   # ... write file to disk
   ```
   With:
   ```python
   # NEW CODE:
   from specify_cli.status.emit import emit_status_transition

   # Determine from_lane from current frontmatter
   current_lane = extract_scalar(frontmatter, "lane")

   # Call the canonical pipeline
   event = emit_status_transition(
       feature_dir=feature_dir,
       feature_slug=feature_slug,
       wp_id=wp_id,
       to_lane=target,  # already alias-resolved
       actor=actor_value,  # from --agent or detected agent
       force=force,
       reason=reason,
       evidence=evidence,
       review_ref=review_ref,
       execution_mode=execution_mode,
       repo_root=repo_root,
   )
   ```
4. AFTER the emit call, update additional metadata fields that are NOT part of the canonical event:
   ```python
   # These are move-task-specific metadata, not canonical status fields.
   # The legacy bridge updates the lane field, but these extras need direct handling.
   if assignee:
       set_scalar(frontmatter, "assignee", assignee)
   if agent_name:
       set_scalar(frontmatter, "agent", agent_name)
   if shell_pid:
       set_scalar(frontmatter, "shell_pid", shell_pid)
   if review_status_value:
       set_scalar(frontmatter, "review_status", review_status_value)
   if reviewed_by:
       set_scalar(frontmatter, "reviewed_by", reviewed_by)

   # Re-write the file with metadata updates
   # (the legacy bridge already wrote the lane, but we need to persist the extras)
   content = build_document(frontmatter, body)
   wp_path.write_text(content)
   ```
5. Remove the direct `emit_wp_status_changed()` call from move_task -- it is now inside the orchestration pipeline (T033 in WP07).

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**:
- Existing test `test_move_task_updates_lane` still passes.
- After move_task, `status.events.jsonl` contains the new event.
- After move_task, `status.json` reflects the updated lane.
- After move_task, frontmatter still has correct assignee, agent, etc.

**Edge Cases**:
- `move_task` is called with `--no-commit`: the emit pipeline still runs (events are appended), but the git commit step is skipped.
- `move_task` is called without `--agent`: the actor should be derived from the current agent identity or default to "unknown".
- The emit pipeline raises `TransitionError`: move_task should catch it and display a user-friendly error (same pattern as current validation errors).

### T044: Retain All Existing Pre-Validation

**Purpose**: Verify that all existing pre-validation functions are preserved and called BEFORE emit_status_transition().

**Steps**:
1. Identify all validation functions currently called in `move_task()`:
   - `_check_unchecked_subtasks(frontmatter, body, target)` -- warns about incomplete subtasks when moving to for_review.
   - `_check_ready_for_review(...)` -- checks research artifacts exist, no uncommitted changes, implementation commits present.
   - `_check_dependent_warnings(...)` -- warns if dependents will need rebasing.
   - Agent ownership validation -- checks if the WP is claimed by a different agent.
   - Review feedback check -- checks if review_status requires reading feedback before moving forward.
2. Verify each of these is called BEFORE the `emit_status_transition()` call.
3. Do NOT move these validations into the status engine. They are move_task-specific business logic, not canonical status concerns.
4. The canonical pipeline has its OWN validation (`validate_transition()` in transitions.py) which checks the state machine. The move_task validations are ADDITIONAL checks on top of that.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**:
- Test: move WP01 to for_review with unchecked subtasks. Verify the subtask warning is still emitted.
- Test: move WP01 to for_review without implementation commits. Verify the readiness check fails.
- Test: move WP01 that is assigned to a different agent. Verify ownership warning.

**Edge Cases**:
- Pre-validation passes but canonical validation fails (e.g., illegal transition). The pre-validation messages have already been shown. The canonical error should add to them, not replace them.
- Pre-validation fails with a typer.Exit(1). The canonical pipeline should NOT be called.

### T045: Map move-task Parameters

**Purpose**: Translate move_task CLI parameters into emit_status_transition arguments and frontmatter metadata.

**Steps**:
1. Create a mapping table:

   | move_task param | Where it goes | Notes |
   |----------------|---------------|-------|
   | `--to` (lane) | `emit_status_transition(to_lane=...)` | After alias resolution |
   | `--assignee` | Frontmatter `assignee` field (post-emit) | Not part of canonical event |
   | `--agent` | `emit_status_transition(actor=...)` AND frontmatter `agent` field | Actor in event = agent identity |
   | `--shell-pid` | Frontmatter `shell_pid` field (post-emit) | Not part of canonical event |
   | `--note` | Frontmatter activity log (post-emit) | Append to history as before |
   | `--no-commit` | Skip git commit step (unchanged) | Does not affect emit pipeline |
   | `--feedback` | Sets `review_status` in frontmatter (post-emit) | Also triggers review_ref in event if going to in_progress |
   | `--reviewed-by` | Frontmatter `reviewed_by` field (post-emit) AND potentially evidence | If moving to done, this could populate evidence.review.reviewer |
   | `--force` | `emit_status_transition(force=...)` | Pass through |

2. Handle the `--feedback` -> `review_ref` mapping:
   - If target lane is `in_progress` and current lane is `for_review`, and `--feedback` or `--reviewed-by` is provided, construct the `review_ref` parameter.
   - `review_ref` could be the note text or the reviewer identity.

3. Handle `--reviewed-by` -> evidence mapping:
   - If target lane is `done` and `--reviewed-by` is provided, construct a minimal evidence dict:
     ```python
     evidence = {
         "review": {
             "reviewer": reviewed_by,
             "verdict": "approved",
             "reference": note or "CLI approval",
         }
     }
     ```

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**:
- Test: move_task with --agent maps to event's actor field.
- Test: move_task to done with --reviewed-by creates evidence in the event.
- Test: move_task from for_review to doing with --feedback maps to review_ref.

**Edge Cases**:
- `--reviewed-by` provided but target is not `done`: still sets frontmatter field, but no evidence generated.
- `--agent` not provided: derive actor from environment or WP's current agent field.

### T046: Backward Compatibility

**Purpose**: Ensure that `--to doing` still works and maps to `in_progress` transparently.

**Steps**:
1. The alias resolution happens in two places:
   - `ensure_lane("doing")` in tasks_support.py (from WP05) should return `"in_progress"`.
   - `resolve_lane_alias("doing")` in status/transitions.py (from WP01) should return `"in_progress"`.
2. Verify that the target lane is resolved BEFORE passing to emit_status_transition().
3. The event will contain `to_lane: "in_progress"` (canonical), never `"doing"`.
4. The frontmatter update (via legacy bridge) will also write `lane: "in_progress"`.
5. However, for Phase 1 backward compatibility, the ACTIVITY LOG history entry should show the resolved canonical lane, not the alias.
6. Verify ALL of these existing CLI invocations work:
   ```bash
   spec-kitty agent tasks move-task WP01 --to doing
   spec-kitty agent tasks move-task WP01 --to in_progress
   spec-kitty agent tasks move-task WP01 --to for_review
   spec-kitty agent tasks move-task WP01 --to planned
   spec-kitty agent tasks move-task WP01 --to claimed    # NEW lane
   spec-kitty agent tasks move-task WP01 --to blocked    # NEW lane
   spec-kitty agent tasks move-task WP01 --to canceled   # NEW lane
   ```

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`, `src/specify_cli/tasks_support.py`

**Validation**:
- Test: `--to doing` produces event with `to_lane: "in_progress"`.
- Test: `--to in_progress` produces same behavior as `--to doing`.
- Test: `--to claimed` is accepted (new canonical lane from WP05).
- Test: `--to invalid_lane` is rejected with a clear error.

**Edge Cases**:
- Agents may have `--to doing` hardcoded in slash command templates. The alias MUST continue to work indefinitely.
- The `ensure_lane()` function may need to be updated in WP05 to return the canonical name. Verify it does.

### T047: Integration Tests

**Purpose**: Verify that move_task delegation produces canonical events while maintaining identical external behavior.

**Steps**:
1. Create or extend tests in `tests/specify_cli/test_cli/test_agent_feature.py` or a new file `tests/integration/test_move_task_delegation.py`.
2. Test cases:

   **test_move_task_produces_jsonl_event**:
   - Set up feature with WP file.
   - Call `move_task()` programmatically (or via CliRunner).
   - Verify `status.events.jsonl` exists and contains one event.
   - Verify event fields match the move_task parameters.

   **test_move_task_produces_status_json**:
   - Call move_task.
   - Verify `status.json` exists and reflects the new lane.

   **test_move_task_frontmatter_still_updated**:
   - Call move_task.
   - Read WP file and verify frontmatter `lane` field matches target.
   - Verify `assignee`, `agent`, `shell_pid` fields are set correctly.

   **test_move_task_doing_alias_maps_to_in_progress**:
   - Call move_task with `--to doing`.
   - Verify event has `to_lane: "in_progress"`.
   - Verify frontmatter has `lane: "in_progress"`.

   **test_move_task_pre_validation_still_works**:
   - Set up WP with unchecked subtasks.
   - Call move_task with `--to for_review`.
   - Verify subtask warning is emitted.

   **test_move_task_no_commit_still_emits_event**:
   - Call move_task with `--no-commit`.
   - Verify event is in JSONL.
   - Verify no git commit was made.

   **test_move_task_saas_not_called_directly**:
   - Mock `sync.events.emit_wp_status_changed`.
   - Call move_task.
   - Verify the mock was called (via the emit pipeline) but NOT called directly from move_task.

   **test_move_task_behavior_matches_pre_refactor**:
   - Create a baseline test that captures the exact output and file state from the pre-refactor move_task.
   - Compare with post-refactor output and state.
   - This is the MOST IMPORTANT test -- it proves backward compatibility.

3. Use `tmp_path` and monkeypatch extensively. Mock git operations where needed.

**Files**: `tests/integration/test_move_task_delegation.py`

**Validation**: All tests pass. All existing tests in the test suite still pass.

**Edge Cases**:
- Tests that mock `emit_wp_status_changed` at the tasks.py import location: these import paths change because the call now comes from `status/emit.py`. Update mock targets.
- Tests that assert on exact git commit messages: verify the commit message format is unchanged.

## Test Strategy

**Existing Test Preservation**:
The following test files MUST continue to pass without modification (or with minimal mock target changes):
- `tests/specify_cli/test_cli/test_agent_feature.py`
- `tests/specify_cli/cli/commands/test_event_emission.py`

If any existing test needs modification, document the change and the reason.

**New Tests**:
- `tests/integration/test_move_task_delegation.py` (T047)

**Regression Testing**:
```bash
# Run the full test suite before and after the refactor
python -m pytest tests/ -x -q
```

**Manual Smoke Test**:
```bash
# In a test project with a feature and WP:
spec-kitty agent tasks move-task WP01 --to doing --agent test
# Verify: status.events.jsonl created, status.json created, frontmatter updated
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing agent workflows | ALL agents stop working | Extensive backward compatibility testing (T047). Run full test suite. |
| Mock target changes break existing tests | CI failures | Grep for `emit_wp_status_changed` mock patches; update targets to new import path |
| Git commit includes unexpected new files | Commit noise | Explicitly git add only: WP file, status.events.jsonl, status.json |
| Metadata (assignee, agent) not persisted after emit | Frontmatter missing metadata | Write metadata AFTER emit; re-read and re-write the file |
| emit_status_transition and move_task both write WP file | Double write, file corruption | Coordinate: emit writes lane via legacy_bridge, move_task writes metadata on top. Or: pass metadata to emit. |
| Performance regression from reading entire JSONL | Slower move_task for large features | Acceptable for MVP. Optimize with status.json read in Phase 2. |

**Critical Risk: Double Write Coordination**

The emit pipeline (via legacy_bridge) writes the WP frontmatter lane field. Then move_task needs to write additional metadata (assignee, agent, shell_pid, etc.) to the same file. Two approaches:

**Option A** (Preferred): After `emit_status_transition()` returns, re-read the WP file (which now has the updated lane from legacy_bridge), apply the metadata fields, and write again.

**Option B**: Pass additional metadata to `emit_status_transition()` as kwargs, and have the legacy_bridge write them alongside the lane. This is cleaner but couples move_task metadata into the status engine.

Recommend Option A for this WP to keep the status engine clean. Consider Option B as a future optimization.

## Review Guidance

When reviewing this WP, verify:
1. **Pre-validation ordering**: ALL existing validation checks run BEFORE emit_status_transition().
2. **No removed validation**: Compare the validation section with the pre-refactor code. Nothing should be missing.
3. **Alias resolution**: `--to doing` maps to `in_progress` in the canonical event.
4. **Double write safety**: The WP file is not corrupted by the emit + metadata write sequence.
5. **Git staging**: The commit includes `status.events.jsonl`, `status.json`, AND the WP file.
6. **SaaS deduplication**: The direct `emit_wp_status_changed()` call is REMOVED from move_task (it now lives in the emit pipeline).
7. **Existing test compatibility**: ALL existing tests pass. Document any mock target changes.
8. **No fallback mechanisms**: If the emit pipeline fails, move_task fails. No silent degradation to the old path.

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T15:24:52Z – unknown – shell_pid=59111 – lane=for_review – move-task delegation to emit pipeline with 273 tests
