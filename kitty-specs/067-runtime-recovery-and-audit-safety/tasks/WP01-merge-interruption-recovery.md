---
work_package_id: WP01
title: Merge Interruption and Recovery
dependencies: []
requirement_refs:
- C-001
- FR-001
- FR-002
- FR-003
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-067-runtime-recovery-and-audit-safety
base_commit: 3d2111f0a8ae6f38cc87624d0da7a2f93d012fad
created_at: '2026-04-06T18:53:10.555091+00:00'
subtasks: [T001, T002, T003, T004, T005, T006]
shell_pid: '88435'
history:
- timestamp: '2026-04-06T18:43:32+00:00'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/merge/
execution_mode: code_change
owned_files:
- src/specify_cli/merge/state.py
- src/specify_cli/merge/workspace.py
- src/specify_cli/cli/commands/merge.py
- tests/specify_cli/merge/**
---

# WP01: Merge Interruption and Recovery

## Objective

Make `spec-kitty merge` recoverable after interruption. When the merge process is killed mid-operation (Ctrl-C, OOM, network drop), the operator must be able to rerun the merge command and have it resume from the last incomplete WP without manual Git cleanup.

**Issue**: [#416](https://github.com/Priivacy-ai/spec-kitty/issues/416)

## Context

The merge subsystem lives in `src/specify_cli/merge/` with CLI entry at `src/specify_cli/cli/commands/merge.py`. The `MergeState` dataclass exists at `merge/state.py:66-121` with `completed_wps`, `current_wp`, and `remaining_wps` (property), but **`_run_lane_based_merge()` currently has ZERO MergeState usage** — it creates no state, saves nothing, loads nothing. The function is a straight-through sequence: merge lanes, merge mission branch, mark done, push, cleanup.

Additionally, `cleanup_merge_workspace()` at `merge/workspace.py:68-96` does `shutil.rmtree()` on the entire runtime directory (`.kittify/runtime/merge/<mission_id>/`), which destroys `state.json` — making recovery impossible even if state had been written.

Resume/abort paths are explicitly disabled at `merge.py:359-361` with an error message: "Resume/abort merge flows were removed with the legacy merge engine."

### Key files

| File | Line(s) | What |
|------|---------|------|
| `src/specify_cli/merge/state.py` | 66-121 | MergeState dataclass with completed_wps, current_wp, remaining_wps |
| `src/specify_cli/merge/state.py` | 123-135 | `get_state_path()` — returns `.kittify/runtime/merge/<mission_id>/state.json` |
| `src/specify_cli/merge/state.py` | 208-234 | `clear_state()` — dead code, defined but never called |
| `src/specify_cli/cli/commands/merge.py` | 237-444 | `_run_lane_based_merge()` — main merge loop, no MergeState usage |
| `src/specify_cli/cli/commands/merge.py` | 28-117 | `_mark_wp_merged_done()` — emits for_review→approved→done transitions |
| `src/specify_cli/cli/commands/merge.py` | 359-361 | Resume/abort disabled with error |
| `src/specify_cli/merge/workspace.py` | 68-96 | `cleanup_merge_workspace()` — shutil.rmtree() on runtime dir |
| `src/specify_cli/lanes/merge.py` | 197-263 | `_merge_branch_into()` — uses git update-ref |

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

## Subtasks

### T001: Wire MergeState Lifecycle into `_run_lane_based_merge()`

**Purpose**: The merge loop must create, update, and consult MergeState at every step so that interrupted merges can resume.

**Steps**:

1. At function entry in `_run_lane_based_merge()` (merge.py:237), add:
   - Call `load_state(repo_root, mission_id)` to check for existing state
   - If state exists and has `completed_wps`: this is a resume. Log "Resuming merge for {mission_slug}, {len(completed_wps)} WPs already completed"
   - If no state: create new `MergeState` with `mission_id`, `mission_slug`, `target_branch`, `wp_order` (from the lane computation)
   - Save the initial state immediately

2. In the lane merge loop (around line 285 where `merge_lane_to_mission()` is called):
   - Before each lane merge: check if all WPs in that lane are in `completed_wps`. If so, skip.
   - After successful lane merge: no state update yet (lane merge is not per-WP)

3. In the mission-to-target merge (around line 293):
   - This is a single operation. If state shows mission-merge completed (need a flag), skip.

4. In the mark-done loop (around line 305 where `_mark_wp_merged_done()` is called for each WP):
   - Before each WP: set `current_wp` and save state
   - After each successful mark-done: add to `completed_wps`, clear `current_wp`, save state

5. After push + cleanup: call `clear_state()` (T002 handles making this work)

**Validation**:
- [ ] MergeState is created at merge start
- [ ] MergeState is loaded on re-entry and completed WPs are skipped
- [ ] State is saved after each WP's done-recording
- [ ] `current_wp` is tracked during merge

### T002: Restructure State File Preservation in Cleanup

**Purpose**: `cleanup_merge_workspace()` currently destroys state.json via `shutil.rmtree()` on the runtime directory. State must survive cleanup so recovery can consult it on re-entry.

**Steps**:

1. In `cleanup_merge_workspace()` at `merge/workspace.py:68-96`:
   - Replace `shutil.rmtree(runtime_dir, ignore_errors=True)` (line 96) with selective deletion
   - Delete worktree files, temp files, and any non-state artifacts in the runtime directory
   - Explicitly skip `state.json` (the `_STATE_FILE` constant)
   - Pattern: iterate directory contents, delete everything except state file

2. Activate `clear_state()`:
   - In `_run_lane_based_merge()`, after cleanup completes successfully AND all WPs are done:
   - Call `clear_state(repo_root, mission_id)` to remove the state file
   - This is the ONLY place `clear_state()` should be called

3. Ensure `clear_state()` is robust:
   - It already handles missing files gracefully (line 218: `state_path.unlink(missing_ok=True)`)
   - Verify it also cleans up the parent runtime directory if empty after state removal

**Validation**:
- [ ] `cleanup_merge_workspace()` removes worktree but preserves state.json
- [ ] `clear_state()` is called only after confirmed full completion
- [ ] State file does not persist after successful merge

### T003: Add Event Dedup Guard in `_mark_wp_merged_done()`

**Purpose**: On retry, `_mark_wp_merged_done()` could attempt to emit transitions for WPs that already reached `done`. While the current lane-state check (early return if `done`) prevents most duplicates, an explicit event_id dedup guard is stronger.

**Steps**:

1. In `_mark_wp_merged_done()` at `merge.py:28-117`:
   - After reading current lane (line 54: `lane = resolve_lane_alias(get_wp_lane(...))`):
   - If lane is already `done`, return early (existing behavior, line 55-56)
   - Before emitting any transition (lines 75-93, 102-113): read the event log for this WP and check if a transition to the target lane already exists
   - If the transition exists, log a message and skip

2. Use `read_events()` from `status/store.py` to check existing events:
   - Filter events by `wp_id` and `to_lane`
   - If a matching event exists, skip emission

**Validation**:
- [ ] Re-running `_mark_wp_merged_done()` for an already-done WP produces no duplicate events
- [ ] Event log has exactly one done transition per WP after retry

### T004: Re-enable Resume/Abort CLI Path

**Purpose**: The resume/abort flags at merge.py:359-361 are explicitly disabled. Replace the error with actual resume logic.

**Steps**:

1. At `merge.py:359-361`, replace:
   ```python
   if resume or abort:
       console.print("[red]Error:[/red] Resume/abort merge flows were removed with the legacy merge engine.")
       raise typer.Exit(1)
   ```
   With:
   - `--resume`: Call `load_state(repo_root, mission_id)`. If state exists, proceed with the normal merge flow (which now consults state per T001). If no state, error "No interrupted merge to resume."
   - `--abort`: Call `clear_state(repo_root, mission_id)` and `cleanup_merge_workspace()`. Report what was cleaned up.

2. Update CLI help text for `--resume` and `--abort` flags.

3. Also handle the auto-resume case: when `merge` is called without `--resume` but state exists, detect this and either auto-resume or prompt the user.

**Validation**:
- [ ] `spec-kitty merge --resume` resumes from last incomplete WP
- [ ] `spec-kitty merge --abort` cleans up state and worktrees
- [ ] Running `merge` with existing state auto-detects and resumes

### T005: Add Retry Tolerance

**Purpose**: On retry after interruption, worktrees and branches may already be removed (partial cleanup). The merge flow must tolerate these missing resources.

**Steps**:

1. **macOS FSEvents delay**: In the worktree removal loop within `cleanup_merge_workspace()` or the CLI cleanup code:
   - Add `time.sleep(delay)` between worktree removals
   - Default: 2.0 seconds on `sys.platform == "darwin"`, 0.0 elsewhere
   - Make configurable via environment variable `SPEC_KITTY_WORKTREE_REMOVAL_DELAY`

2. **Tolerate missing worktrees**: In worktree removal code:
   - Check if worktree path exists before calling `git worktree remove`
   - If path doesn't exist, log and continue (don't fail)

3. **Tolerate missing branches**: In branch deletion code:
   - Check if branch exists before calling `git branch -d`
   - If branch doesn't exist, log and continue

4. **Tolerate already-merged lanes**: In lane merge code:
   - If `merge_lane_to_mission()` fails because the lane is already merged (branch is ancestor of target), treat as success

**Validation**:
- [ ] Retry after partial cleanup succeeds without errors
- [ ] Missing worktrees are logged and skipped
- [ ] Missing branches are logged and skipped
- [ ] macOS delay is applied between worktree removals

### T006: Write Tests for Merge Recovery

**Purpose**: Verify the recovery behavior end-to-end.

**Test scenarios**:

1. **test_merge_creates_state_and_saves_per_wp**: Run merge, verify state.json is created and updated after each WP
2. **test_merge_resume_skips_completed_wps**: Create state with completed_wps=["WP01"], run merge, verify WP01 is skipped
3. **test_merge_resume_after_partial_cleanup**: Simulate interruption after cleanup removes worktree but before state is cleared; verify resume works
4. **test_mark_wp_merged_done_dedup**: Call `_mark_wp_merged_done()` twice for same WP, verify only one set of events
5. **test_merge_abort_cleans_state**: Run merge --abort, verify state file and worktrees are removed
6. **test_cleanup_preserves_state_file**: Run `cleanup_merge_workspace()`, verify state.json still exists
7. **test_clear_state_removes_file**: Call `clear_state()`, verify state.json is gone
8. **test_retry_tolerance_missing_worktree**: Remove worktree manually, run cleanup, verify no error
9. **test_macos_fsevents_delay**: Mock `sys.platform` as darwin, verify sleep is called between removals

**Files**: `tests/specify_cli/merge/test_merge_recovery.py` (new file)

## Definition of Done

- `spec-kitty merge` can be interrupted and resumed without manual Git cleanup
- MergeState is created, saved per-WP, and cleared only after full completion
- No duplicate status events on retry
- Resume/abort CLI paths work
- Missing worktrees/branches are tolerated on retry
- 90%+ test coverage on new code

## Risks

- Race condition if two processes try to merge simultaneously (mitigate with file-lock check at merge entry)
- MergeState schema changes could break in-progress merges from older versions (mitigate with version field and migration)

## Reviewer Guidance

- Verify state.json lifecycle: created at start, updated per-WP, preserved through cleanup, cleared after success
- Check that `shutil.rmtree()` replacement doesn't accidentally leave other temp files
- Confirm event dedup uses event log check, not just lane-state check
- Test the macOS FSEvents delay with `SPEC_KITTY_WORKTREE_REMOVAL_DELAY=0` to disable in CI
