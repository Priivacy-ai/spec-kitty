---
work_package_id: "WP06"
subtasks:
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
title: "Merge Command Updates"
phase: "Phase 1 - Core Implementation"
lane: "done"
dependencies: []
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-07T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Merge Command Updates

**Implementation command:**
```bash
spec-kitty implement WP06
```

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if needed.]*

---

## Objectives & Success Criteria

**Primary Goal**: Update `spec-kitty merge` command to handle workspace-per-WP structure by detecting multiple WP worktrees, validating all are ready for merge, and merging all WP branches to main.

**Success Criteria**:
- ✅ Merge command detects workspace-per-WP structure (multiple .worktrees/###-feature-WP##/ directories)
- ✅ Validates all WP branches exist and are ready to merge
- ✅ Merges all WP branches to main (one merge per WP)
- ✅ Cleanup removes all WP worktrees if --remove-worktree flag set
- ✅ Cleanup deletes all WP branches if --delete-branch flag set
- ✅ Help text updated to document workspace-per-WP behavior
- ✅ Integration test validates merge with workspace-per-WP

---

## Context & Constraints

**Why this update**: Current merge command assumes single feature worktree (`.worktrees/###-feature/`). With workspace-per-WP, there are multiple worktrees (`.worktrees/###-feature-WP01/`, `.worktrees/###-feature-WP02/`, etc.) that must all be merged.

**Reference Documents**:
- [plan.md](../plan.md) - Section 1.2: Modified Commands (merge)
- [spec.md](../spec.md) - FR-019 through FR-021 (merge workflow), User Story 3 acceptance scenario 4
- [data-model.md](../data-model.md) - Worktree lifecycle, merge workflow

**Current Merge Behavior** (0.10.x):
```
spec-kitty merge 008-unified-cli
→ Detects current branch: 008-unified-cli
→ Switches to main, pulls
→ Merges 008-unified-cli branch to main
→ Removes .worktrees/008-unified-cli/ (single worktree)
→ Deletes 008-unified-cli branch
```

**Target Behavior** (0.11.0):
```
spec-kitty merge 010-workspace-per-wp
→ Detects workspace-per-WP structure: .worktrees/010-workspace-per-wp-WP*/
→ Scans for WP branches: 010-workspace-per-wp-WP01, WP02, WP03
→ Switches to main, pulls
→ Merges WP01 branch to main
→ Merges WP02 branch to main
→ Merges WP03 branch to main
→ Removes all WP worktrees: .worktrees/010-workspace-per-wp-WP01/, WP02/, WP03/
→ Deletes all WP branches: 010-workspace-per-wp-WP01, WP02, WP03
```

**Note**: This version merges all WPs together (not incremental WP-by-WP merging). Incremental merging deferred to future version per spec out-of-scope.

---

## Subtasks & Detailed Guidance

### Subtask T041 – Detect workspace-per-WP structure

**Purpose**: Detect whether feature uses legacy (single worktree) or workspace-per-WP (multiple worktrees) structure.

**Steps**:
1. In `src/specify_cli/cli/commands/merge.py`, add detection function:
   ```python
   def detect_worktree_structure(repo_root: Path, feature_slug: str) -> str:
       """Detect if feature uses legacy or workspace-per-WP model.

       Returns: "legacy", "workspace-per-wp", or "none"
       """
       worktrees_dir = repo_root / ".worktrees"
       if not worktrees_dir.exists():
           return "none"

       # Look for legacy pattern: .worktrees/###-feature/
       legacy_pattern = worktrees_dir / feature_slug
       if legacy_pattern.exists() and legacy_pattern.is_dir():
           return "legacy"

       # Look for workspace-per-WP pattern: .worktrees/###-feature-WP##/
       wp_pattern = list(worktrees_dir.glob(f"{feature_slug}-WP*"))
       if wp_pattern:
           return "workspace-per-wp"

       return "none"
   ```

2. Call early in merge() function:
   ```python
   structure = detect_worktree_structure(repo_root, feature_slug)

   if structure == "legacy":
       # Use old merge logic (existing code)
       merge_legacy(...)
   elif structure == "workspace-per-wp":
       # Use new merge logic (implement in T042-T046)
       merge_workspace_per_wp(...)
   else:
       console.print("[yellow]Warning:[/yellow] No worktrees found for {feature_slug}")
       console.print("Feature may already be merged or not yet implemented")
   ```

**Files**: `src/specify_cli/cli/commands/merge.py`

**Parallel?**: No (foundation for T042-T046)

---

### Subtask T042 – Scan for all WP worktrees

**Purpose**: Find all WP worktrees for the feature to be merged.

**Steps**:
1. Scan `.worktrees/` for pattern `{feature_slug}-WP*/`:
   ```python
   def find_wp_worktrees(repo_root: Path, feature_slug: str) -> list[Path]:
       """Find all WP worktrees for a feature."""
       worktrees_dir = repo_root / ".worktrees"
       pattern = f"{feature_slug}-WP*"

       wp_worktrees = sorted(worktrees_dir.glob(pattern))
       return wp_worktrees
   ```

2. Extract WP IDs from worktree names:
   ```python
   def extract_wp_id(worktree_path: Path) -> str:
       """Extract WP ID from worktree directory name.

       Example: .worktrees/010-feature-WP01/ → WP01
       """
       name = worktree_path.name
       match = re.search(r'-(WP\d{2})$', name)
       if match:
           return match.group(1)
       return None
   ```

3. Build list of (worktree_path, wp_id, branch_name) tuples:
   ```python
   wp_workspaces = []
   for wt_path in find_wp_worktrees(repo_root, feature_slug):
       wp_id = extract_wp_id(wt_path)
       branch_name = wt_path.name  # Directory name = branch name
       wp_workspaces.append((wt_path, wp_id, branch_name))
   ```

**Files**: `src/specify_cli/cli/commands/merge.py`

**Parallel?**: No (scans filesystem sequentially)

**Output**: List of WP workspaces to merge, sorted alphabetically by WP ID (WP01, WP02, WP03...)

---

### Subtask T043 – Validate all WP branches ready for merge

**Purpose**: Pre-flight check before merging - ensure all WP branches exist in git and worktrees are clean.

**Steps**:
1. For each WP workspace found in T042, validate:
   ```python
   def validate_wp_ready_for_merge(worktree_path: Path, branch_name: str) -> tuple[bool, str]:
       """Validate WP workspace is ready to merge."""
       # Check 1: Branch exists in git
       result = subprocess.run(
           ["git", "rev-parse", "--verify", branch_name],
           capture_output=True,
           check=False
       )
       if result.returncode != 0:
           return False, f"Branch {branch_name} does not exist"

       # Check 2: No uncommitted changes in worktree
       result = subprocess.run(
           ["git", "status", "--porcelain"],
           cwd=worktree_path,
           capture_output=True,
           text=True
       )
       if result.stdout.strip():
           return False, f"Worktree {worktree_path.name} has uncommitted changes"

       return True, ""
   ```

2. Collect validation errors and display:
   ```python
   errors = []
   for wt_path, wp_id, branch in wp_workspaces:
       is_valid, error_msg = validate_wp_ready_for_merge(wt_path, branch)
       if not is_valid:
           errors.append(f"  - {wp_id}: {error_msg}")

   if errors:
       console.print("[red]Cannot merge:[/red] WP workspaces not ready")
       for err in errors:
           console.print(err)
       raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/merge.py`

**Parallel?**: No (validation runs sequentially)

**Error Example**:
```
Cannot merge: WP workspaces not ready
  - WP01: Worktree 010-workspace-per-wp-WP01 has uncommitted changes
  - WP03: Branch 010-workspace-per-wp-WP03 does not exist
```

---

### Subtask T044 – Merge all WP branches to main

**Purpose**: Iterate through WP branches and merge each to main in sequence.

**Steps**:
1. Switch to main branch (from main repo, not worktree):
   ```python
   os.chdir(repo_root)
   subprocess.run(["git", "checkout", "main"], check=True)
   subprocess.run(["git", "pull", "--ff-only"], check=True)
   ```

2. For each WP branch, merge to main:
   ```python
   for wt_path, wp_id, branch_name in wp_workspaces:
       console.print(f"[cyan]Merging {wp_id} ({branch_name})...[/cyan]")

       # Merge with strategy (--no-ff, --squash, or default)
       if strategy == "squash":
           subprocess.run(["git", "merge", "--squash", branch_name], check=True)
           subprocess.run(["git", "commit", "-m", f"Merge {wp_id} from {feature_slug}"], check=True)
       else:  # merge (default)
           subprocess.run([
               "git", "merge", "--no-ff", branch_name,
               "-m", f"Merge {wp_id} from {feature_slug}"
           ], check=True)

       console.print(f"[green]✓[/green] {wp_id} merged")
   ```

3. Handle merge conflicts:
   ```python
   except subprocess.CalledProcessError as e:
       console.print(f"[red]Merge failed for {wp_id}[/red]")
       console.print("Resolve conflicts manually, then run merge again")
       raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/merge.py`

**Merge Order**: Alphabetical by WP ID (WP01, WP02, WP03...). This ensures dependencies are typically merged in correct order (WP02 depends on WP01, so WP01 merges first).

**Parallel?**: No (merges must be sequential)

---

### Subtask T045 – Add cleanup logic for WP worktrees

**Purpose**: Remove all WP worktrees after successful merge (if --remove-worktree flag set).

**Steps**:
1. After all WP branches merged successfully (T044)
2. If `remove_worktree` flag is True:
   ```python
   if remove_worktree:
       for wt_path, wp_id, branch_name in wp_workspaces:
           try:
               subprocess.run([
                   "git", "worktree", "remove", str(wt_path), "--force"
               ], check=True, capture_output=True)
               console.print(f"[green]✓[/green] Removed worktree: {wp_id}")
           except subprocess.CalledProcessError as e:
               console.print(f"[yellow]Warning:[/yellow] Could not remove worktree {wt_path.name}")
               console.print(f"Remove manually: git worktree remove {wt_path}")
   ```

**Files**: `src/specify_cli/cli/commands/merge.py`

**Parallel?**: No (cleanup runs after merge)

**Error Handling**: If worktree removal fails, log warning but don't fail entire merge. Provide manual cleanup command.

---

### Subtask T046 – Delete all WP branches after merge

**Purpose**: Delete all WP branches after successful merge (if --delete-branch flag set).

**Steps**:
1. After worktrees removed (T045)
2. If `delete_branch` flag is True:
   ```python
   if delete_branch:
       for wt_path, wp_id, branch_name in wp_workspaces:
           try:
               subprocess.run(["git", "branch", "-d", branch_name], check=True, capture_output=True)
               console.print(f"[green]✓[/green] Deleted branch: {branch_name}")
           except subprocess.CalledProcessError:
               # Try force delete
               try:
                   subprocess.run(["git", "branch", "-D", branch_name], check=True, capture_output=True)
                   console.print(f"[green]✓[/green] Force deleted branch: {branch_name}")
               except subprocess.CalledProcessError as e:
                   console.print(f"[yellow]Warning:[/yellow] Could not delete branch {branch_name}")
                   console.print(f"Delete manually: git branch -D {branch_name}")
   ```

**Files**: `src/specify_cli/cli/commands/merge.py`

**Parallel?**: No (runs after worktree cleanup)

**Notes**: Try `-d` first (safe delete, only if fully merged), fallback to `-D` (force delete) if needed.

---

### Subtask T047 – Update help text

**Purpose**: Document workspace-per-WP merge behavior in command help text.

**Steps**:
1. Update merge command docstring:
   ```python
   def merge(
       strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
       delete_branch: bool = typer.Option(True, "--delete-branch/--keep-branch", help="Delete feature branches after merge"),
       remove_worktree: bool = typer.Option(True, "--remove-worktree/--keep-worktree", help="Remove feature worktrees after merge"),
       push: bool = typer.Option(False, "--push", help="Push to origin after merge"),
       target_branch: str = typer.Option("main", "--target", help="Target branch to merge into"),
       dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
   ) -> None:
       """Merge a completed feature into the target branch.

       For workspace-per-WP features (0.11.0+), merges all WP branches
       (010-feature-WP01, 010-feature-WP02, etc.) to main in sequence.

       For legacy features (0.10.x), merges single feature branch.
       """
   ```

2. Add notes section to command output explaining behavior

**Files**: `src/specify_cli/cli/commands/merge.py`

**Parallel?**: Part of overall T041-T046 refactoring

---

### Subtask T048 – Write integration test for workspace-per-WP merge

**Purpose**: Validate merge command works correctly with workspace-per-WP structure.

**Steps**:
1. Create test scenario in `tests/specify_cli/test_integration/test_merge_workspace_per_wp.py`
2. Test flow:
   ```python
   def test_merge_workspace_per_wp(tmp_path):
       """Test merging feature with multiple WP worktrees."""
       # Setup: Create test repo with main branch
       repo = init_test_repo(tmp_path)

       # Create feature in main (planning artifacts)
       create_feature_in_main(repo, "010-test-feature")

       # Create 3 WP workspaces
       create_wp_workspace(repo, "010-test-feature", "WP01", base=None)
       create_wp_workspace(repo, "010-test-feature", "WP02", base="WP01")
       create_wp_workspace(repo, "010-test-feature", "WP03", base=None)

       # Make commits in each workspace
       commit_to_wp(repo, "010-test-feature-WP01", "WP01 changes")
       commit_to_wp(repo, "010-test-feature-WP02", "WP02 changes")
       commit_to_wp(repo, "010-test-feature-WP03", "WP03 changes")

       # Run merge command
       result = run_merge_command(repo, "010-test-feature")

       # Verify all WP branches merged
       git_log = subprocess.run(["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True)
       assert "Merge WP01" in git_log.stdout
       assert "Merge WP02" in git_log.stdout
       assert "Merge WP03" in git_log.stdout

       # Verify worktrees removed
       assert not (repo / ".worktrees" / "010-test-feature-WP01").exists()
       assert not (repo / ".worktrees" / "010-test-feature-WP02").exists()
       assert not (repo / ".worktrees" / "010-test-feature-WP03").exists()

       # Verify branches deleted
       branches = subprocess.run(["git", "branch"], cwd=repo, capture_output=True, text=True)
       assert "010-test-feature-WP01" not in branches.stdout
   ```

**Files**: `tests/specify_cli/test_integration/test_merge_workspace_per_wp.py`

**Parallel?**: Can be written in parallel with implementation

**Test Cases**:
- Happy path: 3 WP workspaces, all merge successfully
- Error case: WP has uncommitted changes (merge blocked)
- Error case: WP branch doesn't exist (merge blocked)
- Cleanup test: Verify worktrees removed and branches deleted
- Legacy compatibility: Verify legacy merge still works

---

## Implementation Flow

**Overall merge workflow:**
```python
def merge(strategy: str, delete_branch: bool, remove_worktree: bool, ...):
    """Merge feature to main."""
    # 1. Detect feature context (T041)
    feature_slug = detect_feature_from_current_context()
    structure = detect_worktree_structure(repo_root, feature_slug)

    if structure == "workspace-per-wp":
        # 2. Find WP worktrees (T042)
        wp_workspaces = find_wp_worktrees(repo_root, feature_slug)

        # 3. Validate all ready (T043)
        validate_all_wp_ready(wp_workspaces)

        # 4. Switch to main, pull
        os.chdir(repo_root)
        subprocess.run(["git", "checkout", "main"], check=True)
        subprocess.run(["git", "pull", "--ff-only"], check=True)

        # 5. Merge each WP branch (T044)
        for wt_path, wp_id, branch in wp_workspaces:
            merge_wp_branch(branch, strategy)

        # 6. Push if requested
        if push:
            subprocess.run(["git", "push", "origin", "main"], check=True)

        # 7. Cleanup worktrees (T045)
        if remove_worktree:
            remove_wp_worktrees(wp_workspaces)

        # 8. Delete branches (T046)
        if delete_branch:
            delete_wp_branches(wp_workspaces)

    elif structure == "legacy":
        # Use existing legacy merge logic (unchanged)
        merge_legacy(...)
```

---

## Test Strategy

**Integration Test**: Full merge workflow with workspace-per-WP

**Test File**: `tests/specify_cli/test_integration/test_merge_workspace_per_wp.py`

**Execution**:
```bash
pytest tests/specify_cli/test_integration/test_merge_workspace_per_wp.py -v
```

**Coverage**:
- Workspace-per-WP merge (happy path)
- Error handling (uncommitted changes, missing branches)
- Cleanup (worktree removal, branch deletion)
- Legacy merge still works (backward compatibility)

---

## Risks & Mitigations

**Risk 1: Merge conflict in one WP blocks entire merge**
- Impact: WP01 merges successfully, WP02 has conflict, WP03 not merged
- Mitigation: Validate all WPs before starting any merges (pre-flight check), stop if any validation fails

**Risk 2: Partial cleanup if removal fails**
- Impact: Some worktrees removed, others remain
- Mitigation: Continue cleanup even if one fails, log all failures at end

**Risk 3: Wrong merge order causes dependency issues**
- Impact: WP02 (depends on WP01) merges before WP01
- Mitigation: Alphabetical sort ensures WP01 < WP02 in merge order, document dependency ordering in help

**Risk 4: Breaking legacy merge**
- Impact: Features 001-008 can't merge after this change
- Mitigation: Detect structure type, use legacy code path for legacy worktrees

---

## Definition of Done Checklist

- [ ] Workspace-per-WP detection implemented (T041)
- [ ] WP worktree scanning implemented (T042)
- [ ] Validation of WP readiness implemented (T043)
- [ ] WP branch merging implemented (T044)
- [ ] Worktree cleanup implemented (T045)
- [ ] Branch deletion implemented (T046)
- [ ] Help text updated (T047)
- [ ] Integration test written and passing (T048)
- [ ] Manual test: Merge feature with 3 WP workspaces, verify all merged
- [ ] Legacy test: Verify old worktrees still merge correctly

---

## Review Guidance

**Reviewers should verify**:
1. **No regression**: Legacy merge still works for features 001-008
2. **All WPs merged**: Verify all WP branches integrated to main (check git log)
3. **Clean cleanup**: No orphaned worktrees or branches after merge
4. **Error messages**: Clear guidance if merge fails (conflicts, uncommitted changes)
5. **Alphabetical merge order**: WP01 merges before WP02 (dependency-safe)

**Key Acceptance Checkpoints**:
- Run merge on workspace-per-WP feature → all WPs merged, worktrees removed
- Run merge on legacy feature → works as before (no regression)
- Trigger error (uncommitted changes) → clear error message, merge blocked

---

## Activity Log

- 2026-01-07T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

Move this WP between lanes using:
```bash
spec-kitty agent tasks move-task WP06 --to <lane>
```

Or edit the `lane:` field in frontmatter directly.
- 2026-01-08T09:25:44Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-08T09:32:19Z – unknown – lane=for_review – Implementation complete and tested. All subtasks completed:
- T041: Detect workspace-per-WP structure ✓
- T042-T046: Implement workspace-per-WP merge logic (scan, validate, merge, cleanup worktrees, delete branches) ✓
- T047: Update help text ✓
- T048: Write integration tests (15 tests, all passing) ✓

Key features:
- Detects workspace-per-WP vs legacy structure automatically
- Validates all WP branches before merging (uncommitted changes, branch existence)
- Merges all WP branches in alphabetical order (WP01, WP02, WP03...)
- Supports merge and squash strategies (rebase not supported for multi-WP)
- Cleanup removes all WP worktrees and deletes all WP branches
- Clear error messages and progress tracking
- Backward compatible with legacy single-worktree features

Tests: All 15 integration tests pass, no regressions in existing tests.
- 2026-01-08T09:40:55Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T09:50:04Z – unknown – lane=for_review – Fixed all review feedback: (1) Workspace-per-WP detection now works from within worktrees via new get_main_repo_root() function, (2) Mixed structure detection now prioritizes workspace-per-WP over legacy, (3) Added true integration tests that exercise merge_workspace_per_wp() and validate all critical behavior. All 20 tests passing, no regressions.
- 2026-01-08T09:51:29Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T09:58:22Z – unknown – lane=done – Review passed - all requirements met, comprehensive tests, no issues found
