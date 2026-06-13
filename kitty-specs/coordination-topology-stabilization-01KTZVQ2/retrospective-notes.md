
## Op Record Write Blocked on Protected Main (Retrospective Finding)

**Observed**: When closing a `spec-kitty do` / `profile-invocation complete` invocation from the primary checkout (which is on protected `main`), the auto-commit of the Op record (`kitty-ops/<id>.jsonl`) fails with `ProtectedBranchRefused`. The call returns `result: success` (the in-memory update succeeds) but the Op record is not persisted to git from the primary checkout path.

**User verdict**: This is a bug. Op record writes should not be silently dropped — they should be auto-routed to the coordination branch (same as other planning artifacts), or at minimum the warning should escalate to an actionable error with a recovery command.

**Workaround used**: Manually copied the Op JSONL to the coord worktree and committed via `safe-commit` from there.

**Suggested fix**: The `profile-invocation complete` auto-commit path should detect the active coordination branch for the current project and commit to it via `safe-commit --to-branch <coord_branch>` rather than attempting a direct primary-checkout commit.
