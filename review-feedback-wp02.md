**Issue 1**: Error message reference is still not exact/complete. It must list the exact user-facing strings. Please add the missing lines and fix mismatches, for example:
- `Error: No merge state to resume` (currently missing the `Error:` prefix)
- `Error: Working directory has uncommitted changes.` (missing `Error:` prefix)
- `Merge failed. Resolve conflicts and try again.` (distinct from `Merge failed. You may need to resolve conflicts.`)
- `Merge failed. You may need to resolve conflicts.` (missing exact text)
- `Error: Already on <branch> branch.` (table hardcodes `main`)
Include other exact red/error strings from `src/specify_cli/cli/commands/merge.py` and `src/specify_cli/merge/preflight.py` that are not in the table.

**Issue 2**: “Missing Worktree” remediation text is inconsistent. The error text says to run `spec-kitty agent workflow implement WP##`, but the guide then adds extra `spec-kitty implement` commands. Please align the fix steps to the actual instruction and avoid redundant/conflicting commands.
