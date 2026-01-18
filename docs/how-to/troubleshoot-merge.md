# How to Troubleshoot Merge Issues

Use this guide to recover from interrupted merges, resolve conflicts, and fix pre-flight failures.

## Quick Reference

```
Merge failed?
├── Pre-flight failed → See "Pre-flight Failures" below
├── Conflicts during merge → See "Resolve Merge Conflicts" below
├── Interrupted (terminal closed) → spec-kitty merge --resume
└── Want to start over → spec-kitty merge --abort
```

## Resume an Interrupted Merge

If your merge was interrupted (terminal closed, system crash, etc.), resume from where it stopped:

```bash
spec-kitty merge --resume
```

Example output:

```
Resuming merge of 017-my-feature
  Progress: 2/5 WPs
  Remaining: WP03, WP04, WP05

Merging WP03 (017-my-feature-WP03)...
✓ WP03 merged
```

### Understanding Merge State

Merge progress is saved in `.kittify/merge-state.json`:

```json
{
  "feature_slug": "017-my-feature",
  "target_branch": "main",
  "wp_order": ["WP01", "WP02", "WP03", "WP04", "WP05"],
  "completed_wps": ["WP01", "WP02"],
  "current_wp": "WP03",
  "has_pending_conflicts": false,
  "strategy": "merge",
  "started_at": "2026-01-18T10:00:00+00:00",
  "updated_at": "2026-01-18T10:15:00+00:00"
}
```

| Field | Description |
|-------|-------------|
| `feature_slug` | The feature being merged |
| `target_branch` | Branch being merged into |
| `wp_order` | Ordered list of WPs to merge |
| `completed_wps` | WPs that have been successfully merged |
| `current_wp` | WP being merged when interrupted (if any) |
| `has_pending_conflicts` | True if git merge conflicts exist |
| `strategy` | Merge strategy (merge, squash, rebase) |
| `started_at` | When merge began |
| `updated_at` | Last state update |

### When to Use --resume

Use `--resume` when:
- Terminal closed during merge
- System crashed mid-merge
- You manually fixed conflicts and want to continue

Do **not** use `--resume` if you want to:
- Change merge strategy
- Merge a different feature
- Start fresh after major changes

## Abort and Start Fresh

Clear merge state and abort any in-progress git merge:

```bash
spec-kitty merge --abort
```

Example output:

```
✓ Merge state cleared for 017-my-feature
  Progress was: 2/5 WPs complete
✓ Git merge aborted
```

After aborting, you can start a new merge:

```bash
spec-kitty merge --feature 017-my-feature
```

### What --abort Clears

1. **Merge state file** (`.kittify/merge-state.json`) - Removed
2. **Git merge state** - If git is mid-merge, runs `git merge --abort`

What it does **not** do:
- Does not delete worktrees (they remain as-is)
- Does not delete branches (completed WPs stay merged)
- Does not revert already-merged commits

### When to Use --abort

Use `--abort` when:
- You want to change merge strategy
- Something went fundamentally wrong
- You need to make changes before re-merging

## Resolve Merge Conflicts

### Status File Conflicts (Automatic)

Conflicts in WP prompt files (`kitty-specs/*/tasks/*.md`) are automatically resolved:

- **Lane field**: Takes the more advanced status (done > for_review > doing > planned)
- **Checkboxes**: Takes checked [x] over unchecked [ ]
- **History array**: Merges both sides chronologically, removes duplicates

You don't need to do anything for these files - they're auto-resolved and staged.

### When Auto-Resolution Fails

If auto-resolution fails (unusual file structure, corrupted content):

1. Open the conflicted file
2. Find conflict markers:
   ```
   <<<<<<< HEAD
   lane: "done"
   =======
   lane: "for_review"
   >>>>>>> 017-feature-WP03
   ```
3. Choose the appropriate value (usually "done" for lane)
4. Remove conflict markers
5. Save and stage:
   ```bash
   git add kitty-specs/017-feature/tasks/WP03-guide.md
   ```
6. Resume merge:
   ```bash
   spec-kitty merge --resume
   ```

### Code Conflicts (Manual)

For conflicts in source code files:

1. Check which files have conflicts:
   ```bash
   git status
   ```
   Look for "both modified" files.

2. Open each conflicted file and resolve:
   ```
   <<<<<<< HEAD
   def existing_function():
       return "old behavior"
   =======
   def existing_function():
       return "new behavior"
   >>>>>>> 017-feature-WP02
   ```

3. Edit to combine both changes appropriately:
   ```python
   def existing_function():
       return "combined behavior"
   ```

4. Stage resolved files:
   ```bash
   git add src/path/to/file.py
   ```

5. Resume merge:
   ```bash
   spec-kitty merge --resume
   ```

### Conflict Resolution Tips

- **Read both sides**: Understand what each WP was trying to do
- **Check imports**: Import conflicts often need combining, not choosing
- **Test after resolve**: Run tests before resuming to catch integration issues
- **When in doubt, abort**: `spec-kitty merge --abort` and merge manually

## Pre-flight Validation Failures

Pre-flight runs before any merge operations. All issues are shown upfront.

### Uncommitted Changes

```
Pre-flight failed. Fix these issues before merging:
  1. Uncommitted changes in 017-feature-WP02
```

**Fix**: Commit or stash changes in that worktree:

```bash
cd .worktrees/017-feature-WP02
git add -A
git commit -m "Complete WP02 implementation"
```

Or stash if you're not ready to commit:

```bash
cd .worktrees/017-feature-WP02
git stash
```

### Missing Worktree

```
Pre-flight failed. Fix these issues before merging:

  1. Missing worktree for WP03. Expected at 017-feature-WP03. Run: spec-kitty agent workflow implement WP03
```

**Fix**: Create the missing worktree using the agent workflow command:

```bash
spec-kitty agent workflow implement WP03
```

### Target Branch Behind Origin

```
Pre-flight failed. Fix these issues before merging:
  1. main is 3 commit(s) behind origin. Run: git checkout main && git pull
```

**Fix**: Update your local main branch:

```bash
git checkout main
git pull
```

Then retry the merge from your WP worktree.

### Branch Does Not Exist

```
Pre-flight failed. Fix these issues before merging:
  1. Branch 017-feature-WP02 does not exist
```

**Fix**: This usually means the worktree was manually deleted without the branch. Recreate:

```bash
spec-kitty implement WP02
```

---

## Error Message Reference

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `Error: Already on <branch> branch.` | Running merge from target branch without --feature | Use `spec-kitty merge --feature <slug>` |
| `Error: No WP worktrees found for feature '<slug>'.` | Feature has no worktrees or wrong slug | Check slug, run `spec-kitty agent workflow implement WP01` |
| `Cannot merge: WP workspaces not ready` | One or more WP worktrees are not merge-ready | Fix the listed WP errors, then retry merge |
| `Worktree <name> has uncommitted changes` | Specific worktree has unstaged/uncommitted work | `cd .worktrees/<name>` then commit or stash |
| `Uncommitted changes in <worktree-name>` | Worktree has uncommitted changes (pre-flight) | Commit or stash changes in that worktree |
| `Error: Working directory has uncommitted changes.` | Legacy merge run from a dirty worktree | Commit or stash changes, then retry merge |
| `Target repository at <path> has uncommitted changes.` | Main repo has uncommitted work | Commit or stash in main repo |
| `Missing worktree for WP##. Expected at <path>. Run: spec-kitty agent workflow implement WP##` | Expected worktree doesn't exist | Run `spec-kitty agent workflow implement WP##` |
| `Branch <branch> does not exist` | Git branch was deleted manually | Recreate worktree with `spec-kitty implement WP##` |
| `<branch> is N commit(s) behind origin. Run: git checkout <branch> && git pull` | Target branch diverged from origin | Run the suggested git checkout and pull commands |
| `Warning: Could not fast-forward <branch>.` | Fast-forward failed, conflicts likely | Resolve conflicts manually |
| `Merge failed. Resolve conflicts and try again.` | Git merge conflict occurred (workspace-per-WP) | Resolve conflicts, then `spec-kitty merge --resume` |
| `Merge failed. You may need to resolve conflicts.` | Git merge conflict occurred (legacy merge) | Resolve conflicts, then re-run merge |
| `Error: No merge state to resume` | No `.kittify/merge-state.json` exists | Run `spec-kitty merge --feature <slug>` to start a new merge |
| `⚠ Invalid merge state file cleared` | State file was corrupted | Start fresh with `spec-kitty merge` |
| `⚠ Git merge in progress - resolve conflicts first` | Unresolved conflict from previous attempt | Resolve conflicts, then `spec-kitty merge --resume` |
| `No merge state to abort` | No active merge to abort | Nothing to do, merge was already complete or never started |
| `Note: Rebase strategy not supported for workspace-per-WP.` | Used --strategy rebase with workspace-per-WP | Use `merge` or `squash` strategy instead |
| `Pre-flight failed. Fix these issues before merging:` | One or more pre-flight checks failed | See numbered list below message, fix each issue |
| `Warning: No WP worktrees found for feature <slug>` | Feature may be merged or not implemented | Check feature slug, ensure worktrees exist |

---

## Command Reference

- [Merge Feature Guide](merge-feature.md) - Complete merge workflow
- [CLI Commands](../reference/cli-commands.md) - Full CLI reference

## See Also

- [Merge a Feature](merge-feature.md) - Standard merge workflow
- [Accept and Merge](accept-and-merge.md) - Pre-merge validation
- [Handle Dependencies](handle-dependencies.md) - WP dependency management

## Background

- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - How worktrees and merging work
- [Git Worktrees](../explanation/git-worktrees.md) - Git worktree fundamentals

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
