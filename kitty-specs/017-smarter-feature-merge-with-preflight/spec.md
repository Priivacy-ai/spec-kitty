# Feature Specification: Smarter Feature Merge with Pre-flight and Auto-cleanup

**Feature Branch**: `017-smarter-feature-merge-with-preflight`
**Created**: 2025-01-18
**Status**: Draft
**Input**: Post-mortem feedback from features 016 (6 WPs, 15 conflict markers, 12 manual cleanup commands) and 002 (10 WPs, 40+ conflicts in status files alone)

## Problem Statement

The current `spec-kitty merge` command is a thin wrapper around sequential `git merge` calls. When merging features with multiple work packages developed in parallel, users experience:

1. **Blocked starts** - Uncommitted changes in any worktree halt the entire merge with no pre-flight visibility
2. **Cascading conflicts** - Sequential merges (WP01→WP02→...) cause later WPs to conflict with newly-merged content, creating O(n) conflicts for n WPs
3. **Status file noise** - 100% of conflicts in some merges were in status tracking files (YAML frontmatter), not actual code
4. **Manual cleanup** - Worktrees and branches must be deleted manually after merge (12+ commands for a 6-WP feature)
5. **No recovery** - Interrupted merges lose context; users must manually reconstruct state
6. **Blind merging** - No way to preview conflicts before committing to the merge

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pre-flight Validation (Priority: P1)

As a developer finishing a multi-WP feature, I want to see all blockers before the merge starts so I can fix them in one pass rather than discovering them one-by-one.

**Why this priority**: This is the highest-impact improvement. The post-mortems show that discovering blockers mid-merge wastes significant time and creates confusion. Showing everything upfront transforms a frustrating iterative process into a single fix-then-merge workflow.

**Independent Test**: Can be fully tested by running `spec-kitty merge` on a feature with uncommitted changes in multiple worktrees. The command should report all issues without attempting any merge operations.

**Acceptance Scenarios**:

1. **Given** a feature with 4 WP worktrees where 2 have uncommitted changes, **When** user runs `spec-kitty merge`, **Then** the command lists all 4 WPs with their status (clean/uncommitted) and exits with actionable remediation steps before any merge is attempted
2. **Given** a feature where the target branch has diverged from origin, **When** user runs `spec-kitty merge`, **Then** the command reports the divergence and suggests `git pull` before any merge is attempted
3. **Given** a feature with all worktrees clean, **When** user runs `spec-kitty merge`, **Then** pre-flight passes and merge proceeds

---

### User Story 2 - Conflict Forecast (Priority: P2)

As a developer, I want to see which files will conflict before merging so I can prepare for resolution or adjust my merge strategy.

**Why this priority**: Knowing conflicts ahead of time allows developers to plan their approach. The post-mortems show that discovering conflicts mid-merge (especially in later WPs) creates exponentially more work.

**Independent Test**: Can be tested by running `spec-kitty merge --dry-run` on a feature where WPs modify overlapping files. The output should predict which files will conflict without performing any merge.

**Acceptance Scenarios**:

1. **Given** WP01 and WP03 both modify `tests/conftest.py`, **When** user runs `spec-kitty merge --dry-run`, **Then** output shows "conftest.py: will conflict between WP01 and WP03"
2. **Given** WPs that modify completely separate files, **When** user runs `spec-kitty merge --dry-run`, **Then** output shows "No conflicts predicted"
3. **Given** a dry-run with predicted conflicts, **When** user reviews the output, **Then** they see the merge order and which WP introduces each conflict

---

### User Story 3 - Smart Merge Order (Priority: P2)

As a developer, I want WPs merged in dependency order rather than numerical order so that dependent WPs have the latest code from their dependencies.

**Why this priority**: Merging in dependency order reduces conflicts because dependent WPs branch from (or rebase onto) their dependencies. Numerical order ignores the dependency graph and causes avoidable conflicts.

**Independent Test**: Can be tested by creating a feature where WP03 depends on WP01 (declared in frontmatter). Merge should process WP01 first regardless of which WP the user is in.

**Acceptance Scenarios**:

1. **Given** WP02 depends on WP01 (per frontmatter `dependencies: ["WP01"]`), **When** user runs `spec-kitty merge`, **Then** WP01 is merged before WP02
2. **Given** WP03 and WP04 are independent (no dependencies on each other), **When** user runs `spec-kitty merge`, **Then** both may be merged in any order (or potentially together via octopus merge)
3. **Given** a circular dependency in frontmatter, **When** user runs `spec-kitty merge`, **Then** pre-flight fails with a clear error explaining the cycle

---

### User Story 4 - Status File Auto-Resolution (Priority: P3)

As a developer, I want conflicts in status tracking files (task frontmatter, tasks.md checkboxes) resolved automatically so I only manually resolve actual code conflicts.

**Why this priority**: The 002 post-mortem shows 40+ conflicts where 100% were in status files, not code. Auto-resolving these would have eliminated all manual work in that merge.

**Independent Test**: Can be tested by creating conflicting status in two WPs (e.g., one marks a task "done", another marks it "for_review"). Merge should auto-resolve to "done" without user intervention.

**Acceptance Scenarios**:

1. **Given** WP01 has `lane: done` and WP02 has `lane: for_review` for the same task, **When** merge encounters this conflict, **Then** auto-resolve to `lane: done` (more-done wins)
2. **Given** WP01 has `- [x] Task A` and WP02 has `- [ ] Task A` in tasks.md, **When** merge encounters this conflict, **Then** auto-resolve to `- [x] Task A` (checked wins)
3. **Given** conflicting `history:` arrays in frontmatter, **When** merge encounters this conflict, **Then** auto-resolve by concatenating entries chronologically
4. **Given** a conflict in actual code (not status files), **When** merge encounters this conflict, **Then** pause for manual resolution as normal

---

### User Story 5 - Automatic Cleanup (Priority: P3)

As a developer, I want worktrees and branches automatically deleted after a successful merge so I don't have cruft left behind.

**Why this priority**: The current command already has `--delete-branch` and `--remove-worktree` flags, but the post-mortems show cleanup wasn't happening reliably. This story ensures cleanup is the default and works correctly.

**Independent Test**: Can be tested by running `spec-kitty merge` on a 3-WP feature and verifying that afterward, no worktrees exist in `.worktrees/` for that feature and no branches exist matching the feature pattern.

**Acceptance Scenarios**:

1. **Given** a successful merge of 3 WPs, **When** merge completes, **Then** all 3 worktree directories are removed from `.worktrees/`
2. **Given** a successful merge of 3 WPs, **When** merge completes, **Then** all 3 WP branches are deleted from git
3. **Given** `--keep-worktree` flag is provided, **When** merge completes successfully, **Then** worktrees are preserved
4. **Given** worktree removal fails for one WP, **When** merge continues, **Then** the failure is reported but other cleanup continues

---

### User Story 6 - Merge Resume (Priority: P4)

As a developer whose merge was interrupted (context compaction, network failure, etc.), I want to resume from where I left off rather than starting over.

**Why this priority**: While less common than other issues, interrupted merges cause significant confusion. The 016 post-mortem specifically mentions context compaction interrupting the merge.

**Independent Test**: Can be tested by starting a merge, simulating an interruption after 2 of 4 WPs, then running `spec-kitty merge --resume` and verifying it continues from WP03.

**Acceptance Scenarios**:

1. **Given** a merge in progress (2 of 4 WPs complete), **When** user runs `spec-kitty merge --resume`, **Then** merge continues from WP03
2. **Given** no merge in progress, **When** user runs `spec-kitty merge --resume`, **Then** command reports "No merge in progress" and exits
3. **Given** a merge with conflicts pending in WP02, **When** user runs `spec-kitty merge --resume` after resolving, **Then** merge continues with WP02 committed and proceeds to WP03

---

### Edge Cases

- What happens when a WP worktree was deleted but its branch still exists? Pre-flight should detect and report this inconsistency.
- What happens when running merge from main branch instead of a worktree? Command should work (detect feature from current directory or prompt for feature slug).
- What happens when one WP has unpushed commits to its remote tracking branch? Pre-flight should warn but not block (local merge doesn't require push).
- What happens when `.gitattributes` merge drivers are not configured? Status file auto-resolution should work without requiring users to configure git.
- What happens when the dependency graph cannot be determined (missing frontmatter)? Fall back to numerical order with a warning.

## Requirements *(mandatory)*

### Functional Requirements

**Pre-flight Validation**
- **FR-001**: System MUST check all WP worktrees for uncommitted changes before starting any merge operation
- **FR-002**: System MUST verify target branch can fast-forward to origin before starting merge
- **FR-003**: System MUST display all pre-flight issues together with remediation steps, not one at a time
- **FR-004**: System MUST exit with non-zero status if pre-flight fails, without modifying any branches

**Conflict Forecast**
- **FR-005**: System MUST predict file conflicts by comparing each WP's changes against the target branch and other WPs
- **FR-006**: System MUST display predicted conflicts during `--dry-run` grouped by file and showing which WPs touch each file
- **FR-007**: System MUST show merge order in dry-run output

**Smart Merge Order**
- **FR-008**: System MUST parse `dependencies: []` from WP frontmatter to build a dependency graph
- **FR-009**: System MUST merge WPs in topological order (dependencies before dependents)
- **FR-010**: System MUST detect circular dependencies and fail pre-flight with a clear error
- **FR-011**: System MUST fall back to numerical order if no dependency information is available

**Status File Auto-Resolution**
- **FR-012**: System MUST auto-resolve conflicts in files matching `kitty-specs/**/tasks/*.md` and `kitty-specs/**/tasks.md`
- **FR-013**: System MUST resolve `lane:` conflicts by preferring the "more done" value (done > for_review > doing > planned)
- **FR-014**: System MUST resolve checkbox conflicts by preferring checked `[x]` over unchecked `[ ]`
- **FR-015**: System MUST resolve `history:` array conflicts by concatenating entries sorted by timestamp
- **FR-016**: System MUST NOT auto-resolve conflicts in files outside the status file patterns

**Automatic Cleanup**
- **FR-017**: System MUST remove all WP worktrees after successful merge (default behavior)
- **FR-018**: System MUST delete all WP branches after successful merge (default behavior)
- **FR-019**: System MUST support `--keep-worktree` and `--keep-branch` flags to preserve resources
- **FR-020**: System MUST continue cleanup of remaining resources if one cleanup operation fails

**Merge Resume**
- **FR-021**: System MUST persist merge state to `.kittify/merge-state.json` during multi-WP merge
- **FR-022**: System MUST support `--resume` flag to continue an interrupted merge
- **FR-023**: System MUST clear merge state file after successful completion or explicit abort
- **FR-024**: System MUST detect active git merge state and integrate with resume logic

**Feature-Wide Default**
- **FR-025**: System MUST merge ALL "done" WPs for the feature by default (not just current WP)
- **FR-026**: System MUST support `--single` flag to merge only the current WP (legacy behavior)
- **FR-027**: System MUST work when invoked from main branch (detect feature from context or require explicit slug)

### Key Entities

- **Merge State**: Persisted state tracking which WPs have been merged, which are pending, and any conflicts requiring resolution. Stored in `.kittify/merge-state.json`.
- **Conflict Forecast**: Predicted conflicts before merge starts, showing file paths and which WPs will conflict.
- **Dependency Graph**: Directed acyclic graph of WP dependencies parsed from frontmatter, used to determine merge order.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify all merge blockers (uncommitted changes, diverged branches) in a single command invocation, reducing pre-merge preparation from multiple iterations to one
- **SC-002**: Users can preview all predicted conflicts before committing to a merge, eliminating mid-merge surprise conflicts
- **SC-003**: Status file conflicts (lane, checkboxes, history) are resolved automatically, reducing manual conflict resolution by the proportion of status-only conflicts (100% in the 002 post-mortem case)
- **SC-004**: Worktrees and branches are cleaned up automatically after merge, eliminating the 12+ manual cleanup commands reported in post-mortems
- **SC-005**: Interrupted merges can be resumed without losing progress, reducing recovery time from "reconstruct everything" to "run --resume"
- **SC-006**: Features with 6+ WPs merge with fewer total conflicts than current sequential approach due to dependency-ordered merging

## Assumptions

- Git is the VCS in use (jj-specific optimizations are out of scope for this feature)
- The existing `spec-kitty merge` command structure and CLI framework (typer) will be preserved
- WP frontmatter format remains stable and parseable for dependency extraction
- Users are willing to adopt `--single` flag if they need the old single-WP behavior

## Out of Scope

- JJ-specific merge strategies (non-blocking conflicts, auto-rebase) - separate feature
- Moving status tracking to SQLite or external storage - requires migration
- Auto-rebase of remaining worktrees when one WP merges - complex coordination
- Octopus merge for independent WPs - git-specific optimization, can be added later
- Integration with external merge tools (vimdiff, meld) - user can configure git for this
