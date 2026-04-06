---
work_package_id: WP02
title: Implementation Crash Recovery
dependencies: [WP01]
requirement_refs:
- C-002
- FR-004
- FR-005
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T007, T008, T009, T010, T011]
agent: "claude:opus:implementer:implementer"
shell_pid: "31463"
history:
- timestamp: '2026-04-06T18:43:32+00:00'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/lanes/
execution_mode: code_change
owned_files:
- src/specify_cli/workspace_context.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/lanes/implement_support.py
- src/specify_cli/lanes/worktree_allocator.py
- tests/specify_cli/lanes/test_implement*
- tests/runtime/test_workspace_context*
---

# WP02: Implementation Crash Recovery

## Objective

Add a supported recovery path for the implementation phase when the agent process crashes. When branches and worktrees survive but Spec Kitty's internal state is inconsistent, the operator must be able to reconcile and resume without manual Git commands.

**Issue**: [#415](https://github.com/Priivacy-ai/spec-kitty/issues/415)

## Context

Implementation state is spread across 4 surfaces:
1. **Workspace context**: `.kittify/workspaces/{mission_slug}-{lane_id}.json` (WorkspaceContext dataclass at `workspace_context.py:36-87`)
2. **Runtime run index**: `.kittify/runtime/feature-runs.json` (`next/runtime_bridge.py:57-77`)
3. **WP frontmatter**: `kitty-specs/{mission}/tasks/WP##.md` (has `base_branch`, `base_commit`, `shell_pid`)
4. **Status event log**: `kitty-specs/{mission}/status.events.jsonl`

The **circular dependency** that blocks recovery: `implement` → needs worktree → `git worktree add -b` at `worktree_allocator.py:143` → needs branch to NOT exist → branch exists from pre-crash run. The specific line is:
```python
["git", "worktree", "add", "-b", branch, str(worktree_path), base_branch]
```
Recovery must use `git worktree add <path> <existing-branch>` (without `-b`) when the branch already exists.

Existing building blocks:
- `find_orphaned_contexts()` at `workspace_context.py:345-362` — detects contexts where worktree path doesn't exist
- Reuse detection at `implement_support.py:76-81` — checks `.git` marker + `_has_commits_beyond_base()`
- `cleanup_orphaned_contexts()` at `workspace_context.py:365-379` — removes stale context files

### Key files

| File | Line(s) | What |
|------|---------|------|
| `src/specify_cli/workspace_context.py` | 36-87 | WorkspaceContext dataclass |
| `src/specify_cli/workspace_context.py` | 125-136 | `get_context_path()` — context file path formula |
| `src/specify_cli/workspace_context.py` | 345-362 | `find_orphaned_contexts()` — detects stale contexts |
| `src/specify_cli/lanes/worktree_allocator.py` | 105-134 | `_ensure_mission_branch()` — branch creation |
| `src/specify_cli/lanes/worktree_allocator.py` | 137-153 | `_create_lane_worktree()` — the failing `git worktree add -b` |
| `src/specify_cli/lanes/implement_support.py` | 76-81 | Reuse detection via `.git` marker |
| `src/specify_cli/lanes/implement_support.py` | 87-95 | Context refresh on reuse |
| `src/specify_cli/cli/commands/implement.py` | ~357 | shell_pid update in frontmatter |

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

## Subtasks

### T007: Build Recovery Scan

**Purpose**: Detect the post-crash state by scanning for orphaned branches, workspace contexts, and status events that are out of sync.

**Steps**:

1. Create a `scan_recovery_state()` function (in `workspace_context.py` or a new `recovery.py` module):
   - List all local branches matching `kitty/mission-{slug}*` pattern via `git branch --list`
   - List all workspace context files from `.kittify/workspaces/`
   - Read status event log from `kitty-specs/{mission}/status.events.jsonl`
   - Materialize current snapshot to get per-WP lane state

2. For each branch found:
   - Check if a matching workspace context exists
   - Check if a matching worktree path exists on disk
   - Check the WP's current lane from the status event log

3. Build a recovery report:
   ```
   RecoveryState:
     branch_exists: bool
     worktree_exists: bool
     context_exists: bool
     status_lane: str  # current lane from event log
     has_commits: bool  # commits beyond base
     recovery_action: str  # "recreate_worktree" | "recreate_context" | "emit_transitions" | "no_action"
   ```

4. Return list of `(wp_id, lane_id, RecoveryState)` tuples

**Validation**:
- [ ] Detects branch with no worktree
- [ ] Detects branch with no context
- [ ] Detects context with no worktree
- [ ] Correctly identifies recovery action for each case

### T008: Implement Worktree Reconciliation

**Purpose**: When a branch exists from a pre-crash implementation but the worktree was lost, recreate the worktree from the existing branch.

**Steps**:

1. In `worktree_allocator.py`, add a `_recover_lane_worktree()` function:
   ```python
   def _recover_lane_worktree(
       repo_root: Path, worktree_path: Path, existing_branch: str
   ) -> None:
       """Recreate worktree from existing branch (recovery mode)."""
       worktree_path.parent.mkdir(parents=True, exist_ok=True)
       result = subprocess.run(
           ["git", "worktree", "add", str(worktree_path), existing_branch],
           cwd=str(repo_root), capture_output=True, text=True,
       )
       if result.returncode != 0:
           raise RuntimeError(f"Failed to recover worktree: {result.stderr.strip()}")
   ```
   Note: This uses `git worktree add <path> <branch>` WITHOUT `-b` — attaches to existing branch.

2. When a workspace context exists but the worktree path is gone:
   - Call `_recover_lane_worktree()` with the branch from the context
   - Refresh the context's `worktree_path` if needed

3. When a workspace context is missing but branch exists:
   - Recreate the worktree as above
   - Create a new WorkspaceContext from the branch metadata
   - Save the context via `save_context()`

**Validation**:
- [ ] `git worktree add <path> <branch>` (without -b) succeeds when branch exists
- [ ] WorkspaceContext is created/updated after worktree recovery
- [ ] Recovered worktree has correct branch checked out

### T009: Implement Status Reconciliation

**Purpose**: After crash, the status event log may be behind reality. If a branch exists with commits but status is `planned`, emit the missing transitions.

**Steps**:

1. Create a `reconcile_status()` function:
   - For each WP in the recovery scan results:
   - Determine expected lane based on evidence:
     - Branch exists with commits beyond base → at least `in_progress`
     - Workspace context has `created_by: "implement-command"` → at least `claimed`
   - Read current lane from event log snapshot
   - If current lane is behind expected: emit transitions to catch up

2. Emit transitions conservatively:
   - If current is `planned` and expected is `in_progress`: emit `planned→claimed`, then `claimed→in_progress`
   - Use `emit_status_transition()` from `status/emit.py`
   - Set `actor` to `"recovery"` to distinguish from normal flow
   - Set `reason` to `"Recovered after crash — branch exists with commits"`

3. Do NOT advance past `in_progress` during recovery — let the normal workflow handle review/approval.

**Validation**:
- [ ] Missing `planned→claimed→in_progress` transitions are emitted
- [ ] Recovery actor is `"recovery"` in emitted events
- [ ] Status is not advanced beyond `in_progress` during recovery

### T010: Add `--recover` Flag to Implement CLI

**Purpose**: Provide a CLI entry point that orchestrates the recovery scan, worktree reconciliation, and status reconciliation.

**Steps**:

1. In `src/specify_cli/cli/commands/implement.py`, add `--recover` flag to the implement command:
   ```python
   recover: bool = typer.Option(False, "--recover", help="Recover from crashed implementation session")
   ```

2. When `--recover` is set:
   a. Run `scan_recovery_state()` (T007)
   b. Display recovery report with rich table showing each WP's state
   c. For each WP needing recovery:
      - Run worktree reconciliation (T008) if worktree is missing
      - Run status reconciliation (T009) if status is behind
   d. Report what was recovered

3. JSON output mode (`--json`):
   ```json
   {
     "recovered_wps": ["WP01", "WP03"],
     "worktrees_recreated": 2,
     "transitions_emitted": 4,
     "errors": []
   }
   ```

4. Error handling:
   - If no recovery needed: "No crashed implementation sessions found."
   - If recovery partially fails: report what succeeded and what failed, continue with remaining WPs

**Validation**:
- [ ] `spec-kitty implement --recover` detects and recovers crashed sessions
- [ ] JSON output includes recovery details
- [ ] Partial failure doesn't abort entire recovery

### T011: Write Tests for Crash Recovery

**Test scenarios**:

1. **test_scan_detects_orphaned_branch**: Create a branch without worktree, verify scan finds it
2. **test_recover_worktree_from_existing_branch**: Delete worktree, keep branch, run recovery, verify worktree recreated
3. **test_recover_context_from_branch**: Delete context, keep branch+worktree, verify context recreated
4. **test_status_reconciliation_emits_transitions**: Set status to `planned` for a WP with commits, run reconciliation, verify `planned→claimed→in_progress` emitted
5. **test_recovery_does_not_advance_past_in_progress**: Verify recovery never emits for_review/approved/done transitions
6. **test_recover_flag_integration**: Test `implement --recover` end-to-end with simulated crash state
7. **test_no_recovery_needed**: Verify clean state produces "no recovery needed" message

**Files**: `tests/specify_cli/lanes/test_implementation_recovery.py` (new file)

## Definition of Done

- `spec-kitty implement --recover` detects orphaned branches/worktrees and reconciles them
- Worktrees are recreated from surviving branches without `-b` flag
- Status event log is caught up to match filesystem reality
- No manual `git worktree` commands required
- 90%+ test coverage on new code

## Risks

- Recovery might incorrectly infer lane state from branch contents (mitigate: conservative — only advance to `in_progress`, never further)
- Multiple branches from different crash sessions could confuse the scan (mitigate: scope scan to specific mission pattern)

## Reviewer Guidance

- Verify `git worktree add` (without `-b`) is used for recovery, not `git worktree add -b`
- Check that status reconciliation uses `actor: "recovery"` for auditability
- Confirm recovery doesn't advance past `in_progress`
- Test with real git operations, not mocked subprocess calls

## Activity Log

- 2026-04-06T19:07:43Z – claude:opus:implementer:implementer – shell_pid=31463 – Started implementation via action command
- 2026-04-06T19:18:14Z – claude:opus:implementer:implementer – shell_pid=31463 – Crash recovery with --recover flag, worktree+status reconciliation, 16 tests all passing
