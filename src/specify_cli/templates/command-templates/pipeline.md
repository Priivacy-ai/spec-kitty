---
description: Implement, review, and complete all planned WPs for a feature in a single session.
---

# /spec-kitty.pipeline - Full Feature Pipeline

**Purpose**: Loop through all planned WPs in dependency order: implement -> commit -> review -> next WP. Runs everything within a single conversation so you have full visibility and control.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). The user may specify a feature slug, a starting WP, or constraints like "only WP03-WP05".

## Phase 1: Discovery

### 1.1 Detect Active Feature

Run:
```bash
spec-kitty agent tasks status
```

If no feature is found automatically and the user didn't specify one, scan `kitty-specs/` directories and pick the one with WPs in `planned` lane. If multiple features qualify, ask the user which one.

### 1.2 Build WP Execution Order

Read each WP file's YAML frontmatter in the feature's `tasks/` directory. Extract:
- `work_package_id` (e.g., WP01)
- `lane` (planned, doing, for_review, done)
- `dependencies` (list of WP IDs this WP depends on)

**Classify WPs into groups:**
- **Skip**: WPs already in `done` lane
- **Resume**: WPs in `doing` or `for_review` lane (handle these first)
- **Queue**: WPs in `planned` lane

**Determine execution order** by topological sort on dependencies:
- A WP can only start when all its dependencies are in `done` lane
- WPs with no dependencies (or all dependencies done) are ready first
- Among ready WPs, process in WP number order (WP01 before WP02)

### 1.3 Present the Plan

Show the user a summary before starting:

```
## Pipeline Plan

Feature: <feature-slug>
Already done: WP01, WP03
To resume: WP02 (for_review)
To implement: WP04, WP05, WP06

Execution order: WP02 (resume review) -> WP04 -> WP05 -> WP06
```

Wait for user confirmation before proceeding. If they say to skip certain WPs or change order, adjust accordingly.

## Phase 2: Execute WP Loop

For each WP in execution order, follow the appropriate path:

### Path A: WP in `for_review` Lane (Resume Review)

1. Run:
   ```bash
   spec-kitty agent workflow review <WP_ID> --agent claude
   ```
2. Follow the review prompt instructions completely
3. **If approved**: move to `done` with:
   ```bash
   spec-kitty agent tasks move-task <WP_ID> --to done --note "Review passed: <summary>"
   ```
4. **If issues found**: fix them in the worktree, re-commit, then re-review (max 2 retries). If still failing after retries, stop the pipeline and report to the user.

### Path B: WP in `doing` Lane (Resume Implementation)

1. The worktree already exists. `cd` into it:
   ```bash
   cd .worktrees/<feature-slug>-<WP_ID>/
   ```
2. Check what's been done, complete any remaining subtasks
3. Commit:
   ```bash
   git add -A && git commit -m "feat(<WP_ID>): <describe implementation>"
   ```
4. Move to `for_review`:
   ```bash
   spec-kitty agent tasks move-task <WP_ID> --to for_review --note "Ready for review: <summary>"
   ```
5. **Immediately review** (follow Path A above)

### Path C: WP in `planned` Lane (Fresh Implementation)

1. **Return to main repo first**:
   ```bash
   cd <main-repo-path>
   ```
2. Run:
   ```bash
   spec-kitty agent workflow implement <WP_ID> --agent claude
   ```
3. Follow the implement prompt instructions completely:
   - `cd` into the worktree directory shown in the output
   - Implement all subtasks listed in the prompt
   - Run any specified tests/validations
4. Commit in the worktree:
   ```bash
   git add -A && git commit -m "feat(<WP_ID>): <describe implementation>"
   ```
5. Move to `for_review`:
   ```bash
   spec-kitty agent tasks move-task <WP_ID> --to for_review --note "Ready for review: <summary>"
   ```
6. **Immediately self-review**: Run:
   ```bash
   spec-kitty agent workflow review <WP_ID> --agent claude
   ```
7. Follow the review prompt. Focus the self-review on:
   - Correctness: does the code work as specified?
   - Completeness: are all subtasks addressed?
   - Dependencies: does it integrate properly with completed WPs?
   - Tests: do they pass?
   - Do NOT nitpick style - you wrote it, you'd just be arguing with yourself
8. **If approved**: move to `done`:
   ```bash
   spec-kitty agent tasks move-task <WP_ID> --to done --note "Review passed: <summary>"
   ```
9. **If issues found**: fix in worktree, re-commit, re-review (max 2 retries)

### Between WPs

After completing each WP:

1. **Always `cd` back to the main repo root**:
   ```bash
   cd <main-repo-path>
   ```
2. **Check dependency readiness** for the next WP - all its dependencies must now be in `done`
3. **Report progress**: show a brief status update before starting the next WP

## Phase 3: Completion

After all WPs are done:

1. Return to main repo:
   ```bash
   cd <main-repo-path>
   ```
2. Run a final status check:
   ```bash
   spec-kitty agent tasks status
   ```
3. Present a summary:
   ```
   ## Pipeline Complete

   Feature: <feature-slug>
   WPs completed this session: WP02, WP04, WP05, WP06
   Total: 6/6 WPs done

   Next step: Run `/spec-kitty.accept` to validate and accept the feature.
   ```

## Rules

- **Always `cd` back to the main repo between WPs.** Worktree paths are only valid for their specific WP.
- **Respect dependency order.** Never start a WP before its dependencies are in `done`.
- **Skip WPs already in `done`.** Don't re-implement or re-review completed work.
- **Self-review is pragmatic.** Focus on correctness and completeness, not style preferences.
- **Max 2 retries per WP.** If a WP fails review twice after fixes, stop and ask the user.
- **Report progress after each WP.** The user should always know where you are in the pipeline.
- **Never force through failures.** If a command fails or tests don't pass, stop and report rather than skipping.
- **Commit before moving to `for_review`.** The `move-task` command validates that commits exist.
