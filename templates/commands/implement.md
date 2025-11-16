---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---
*Path: [templates/commands/implement.md](templates/commands/implement.md)*


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check (CRITICAL for AI Agents)

**BEFORE PROCEEDING:** Verify you are working from inside the feature worktree.

**Check current working directory and branch:**
```bash
pwd
git branch --show-current
```

**Expected output:**
- `pwd`: `/path/to/project/.worktrees/004-feature-name` (or similar)
- Branch: `004-feature-name` (NOT `main` or `release/x.x.x`)

**If you see `main` or `release/*` branch, OR if pwd shows the main repo:**

⛔ **STOP - You are in the wrong location!**

**DO NOT use `cd` to navigate to the worktree.** File creation tools (Write, Edit) will still use your original working directory.

**Instead:**
1. Tell the user: "This command must be run from inside the worktree at `.worktrees/<feature>/`"
2. Stop execution
3. Wait for the user to restart the session from the correct location

**Path reference rule:** Always use paths relative to the worktree root (e.g., `src/specify_cli/`, `kitty-specs/004-feature/`). When communicating with the user, mention absolute paths for clarity.

This is intentional - worktrees provide isolation for parallel feature development.

---

## ⚠️ CRITICAL: Review Feedback Check

**Before you start implementing**, check for prior review feedback:

1. Open the task prompt file for the work you're about to implement
2. Look for the `review_status` field in the frontmatter:
   - **`review_status: has_feedback`** → The task was reviewed and returned with feedback
   - **`review_status: acknowledged`** → You (or another agent) already saw the feedback and started addressing it
   - **`review_status: ""` (empty)** → No feedback; proceed normally
3. **If feedback exists**:
   - Scroll to the `## Review Feedback` section (located right after the frontmatter)
   - Read the **Key Issues** and **Action Items** carefully
   - Treat all action items as your implementation TODO list
   - Update `review_status: acknowledged` when you begin work
   - As you fix each item, update the Activity Log: `Addressed feedback: [specific fix description]`
4. **If you miss or ignore feedback**, your work will be returned again for the same issues

---

## Outline

1. **Verify worktree context** (already validated in pre-flight):
   - Working directory MUST be inside `PROJECT_ROOT/.worktrees/FEATURE-SLUG`
   - If not, the pre-flight check should have stopped you
   - All file paths are relative to this worktree root

2. Run `{SCRIPT}` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.

2. **Check checklists status** (if FEATURE_DIR/checklists/ exists):
   - Scan all checklist files in the checklists/ directory
   - For each checklist, count:
     * Total items: All lines matching `- [ ]` or `- [X]` or `- [x]`
     * Completed items: Lines matching `- [X]` or `- [x]`
     * Incomplete items: Lines matching `- [ ]`
   - Create a status table:
     ```
     | Checklist | Total | Completed | Incomplete | Status |
     |-----------|-------|-----------|------------|--------|
     | ux.md     | 12    | 12        | 0          | ✓ PASS |
     | test.md   | 8     | 5         | 3          | ✗ FAIL |
     | security.md | 6   | 6         | 0          | ✓ PASS |
     ```
   - Calculate overall status:
     * **PASS**: All checklists have 0 incomplete items
     * **FAIL**: One or more checklists have incomplete items
   
   - **If any checklist is incomplete**:
     * Display the table with incomplete item counts
     * **STOP** and ask: "Some checklists are incomplete. Do you want to proceed with implementation anyway? (yes/no)"
     * Wait for user response before continuing
     * If user says "no" or "wait" or "stop", halt execution
     * If user says "yes" or "proceed" or "continue", proceed to step 3
   
   - **If all checklists are complete**:
     * Display the table showing all checklists passed
     * Automatically proceed to step 3

3. **MANDATORY: Initialize Task Workflow** ⚠️ BLOCKING STEP

   **For EACH task you will implement**:

   a. **Move task prompt to doing lane**:
      ```bash
      # Capture your shell PID
      SHELL_PID=$(echo $$)

      # Move prompt (example for T001)
      .kittify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG TXXX doing \
        --shell-pid "$SHELL_PID" \
        --agent "claude" \
        --note "Started implementation"
      ```
      > Windows users: run `.kittify/scripts/powershell/tasks-move-to-lane.ps1` with the same arguments.

   b. **Verify frontmatter metadata** in the moved file:
      ```yaml
      lane: "doing"
      assignee: "Your Name or Agent ID"
      agent: "claude"  # or codex, gemini, etc.
      shell_pid: "12345"  # from echo $$
      ```

   c. **Confirm the Activity Log** shows a new entry that records the transition to `doing` (the helper script adds it automatically—adjust the note if needed).

   d. **Commit the move**:
      ```bash
      git status --short
      git commit -m "Start TXXX: Move to doing lane"
      ```

   **VALIDATION**: Before proceeding to implementation, verify:
   - [ ] Prompt file exists in `tasks/doing/phase-X-name/`
   - [ ] Frontmatter has `lane: "doing"`
   - [ ] Frontmatter has your `shell_pid`
   - [ ] Activity log has "Started implementation" entry
   - [ ] Changes are committed to git

   **If validation fails**: STOP and fix the workflow before implementing.
   (Optional) Run `scripts/bash/validate-task-workflow.sh TXXX FEATURE_DIR` for automated checks.

4. Load and analyze the implementation context:
   - **REQUIRED**: Read tasks.md for the complete task list and execution plan
   - **REQUIRED**: Read the task prompt file from `tasks/doing/phase-X-name/TXXX-slug.md` (moved in step 3)
   - **MANDATORY** 🚨 **REVIEW FEEDBACK CHECK**: Look at the `review_status` field in the frontmatter:
     - If `review_status: has_feedback` or `review_status: acknowledged`, **STOP** and read the `## Review Feedback` section immediately (it's right after the frontmatter)
     - **Do not proceed** until you have read and understood all feedback items
     - Make each action item a TODO in your implementation plan
     - Update `review_status: acknowledged` to signal you've read and will address it
   - **VERIFY**: Frontmatter shows `lane: "doing"`, `agent`, and `shell_pid`
   - **IF METADATA MISSING**: You skipped step 3. Pause and complete the workflow initialization before continuing.
   - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure
   - **IF EXISTS**: Read data-model.md for entities and relationships
   - **IF EXISTS**: Read contracts/ for API specifications and test requirements
   - **IF EXISTS**: Read research.md for technical decisions and constraints
   - **IF EXISTS**: Read quickstart.md for integration scenarios

5. Parse tasks.md structure and extract:
   - **Task phases**: Setup, Tests, Core, Integration, Polish
   - **Task dependencies**: Sequential vs parallel execution rules
   - **Task details**: ID, description, file paths, parallel markers [P]
   - **Execution flow**: Order and dependency requirements

6. Execute implementation following the task plan:
   - **Pull from planned intentionally**: Select the next task from `tasks/planned/`.
     - **If it recently came back from `for_review/`** (check `reviewed_by` field and `review_status: has_feedback`):
       - Treat the `## Review Feedback` section as your primary TODO list
       - Complete all action items in the "Action Items" checklist
       - Update the Activity Log for each item you fix: `Addressed feedback: [item description]`
       - Do NOT move to `for_review/` again until all feedback items are checked off
   - **Phase-by-phase execution**: Complete each phase before moving to the next
   - **Respect dependencies**: Run sequential tasks in order, parallel tasks [P] can run together
   - **Follow TDD approach**: Execute test tasks before their corresponding implementation tasks
   - **File-based coordination**: Tasks affecting the same files must run sequentially
   - **Validation checkpoints**: Verify each phase completion before proceeding
   - **Kanban discipline**: Use the lane helper scripts to keep the prompt in `tasks/doing/`, update the Activity Log, and capture your shell PID (`echo $$`). These should already be complete from step 3—verify before coding.

7. Implementation execution rules:
   - **Setup first**: Initialize feature scaffolding, dependencies, configuration
   - **Tests before code**: If you need to write tests for contracts, entities, and integration scenarios
   - **Core development**: Implement models, services, CLI commands, endpoints
   - **Integration work**: Database connections, middleware, logging, external services
   - **Polish and validation**: Unit tests, performance optimization, documentation

8. Progress tracking and error handling:
   - Report progress after each completed task
   - Halt execution if any non-parallel task fails
   - For parallel tasks [P], continue with successful tasks, report failed ones
   - Provide clear error messages with context for debugging
   - Suggest next steps if implementation cannot proceed
   - Leave the task checkbox unchecked—reviewers will mark completion when moving the prompt to `tasks/done/`.
   - **After completing each task**:
     - Update the prompt's activity log:
       ```markdown
       - 2025-10-07T17:00:00Z – claude – shell_pid=12345 – lane=doing – Completed implementation
       ```
     - Move prompt to for_review:
     ```bash
     .kittify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG TXXX for_review \
       --shell-pid "$SHELL_PID" \
       --agent "claude" \
       --note "Ready for review"
     ```
     - Commit:
       ```bash
       git status --short
       git commit -m "Complete TXXX: Move to for_review lane"
       ```
   - **VALIDATION BEFORE CONTINUING TO NEXT TASK**:
     - [ ] Prompt is in `tasks/for_review/` lane
     - [ ] Frontmatter shows `lane: "for_review"`
     - [ ] Activity log has completion entry
     - [ ] Git commit exists for the move

9. Completion validation:
   - Verify all required tasks are completed
   - Check that implemented features match the original specification
   - Validate that tests pass and coverage meets requirements
   - Confirm the implementation follows the technical plan
   - Report final status with summary of completed work

## Task Workflow Summary (Quick Reference)

**For every task**:

1. **START**: `planned/` → `doing/`
   - `.kittify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG WPID doing --note "Started implementation"`
   - Verify frontmatter: `lane: "doing"`, confirm `shell_pid`, `agent`
   - Confirm activity log entry
   - Commit

2. **WORK**: Implement the task
   - Follow prompt guidance
   - Create/modify files as specified
   - Test your changes

3. **COMPLETE**: `doing/` → `for_review/`
   - Add completion entry to activity log
   - `.kittify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG WPID for_review --note "Ready for review"`
   - Verify frontmatter: `lane: "for_review"`
   - Confirm review-ready log entry
   - Commit

4. **REVIEW**: Reviewer moves `for_review/` → `done/`
   - Reviewer validates work
   - Reviewer updates tasks.md checkbox (`- [x]`)
   - Reviewer uses the lane helper script to move to `tasks/done/` and commits

**Shell PID**: Capture once per session with `echo $$` and reuse it

**Timestamp format**: ISO 8601 with timezone, e.g. `2025-10-07T16:00:00Z`

**Agent identifiers**: claude, codex, gemini, copilot, cursor, windsurf, etc.

Note: This command assumes a complete task breakdown exists in tasks.md. If tasks are incomplete or missing, suggest running `/tasks` first to regenerate the task list.

## Agent-Specific Parallelization Tips

Leverage your agent’s native orchestration so one work package advances while another gets reviewed:

- **Claude Code** – Use the `/agents` command to spin up specialized subagents and explicitly delegate work (for example, “Use the code-reviewer subagent to audit WP02”) so different assistants run in parallel.[^claude_subagents]
- **OpenAI Codex** – Offload secondary tasks as cloud jobs with commands like `codex exec --cloud "refactor the adapters"`; cloud tasks are designed to run concurrently with your local session.[^codex_cloud]
- **Cursor Agent CLI** – Launch multiple instances (`cursor-agent chat "…"`) in separate terminals or remote shells; the CLI explicitly supports parallel agents.[^cursor_parallel]
- **GitHub Copilot CLI** – Schedule or review background work with `gh agent-task create`, `gh agent-task list`, and `gh agent-task view --log --follow` while you keep implementing locally.[^copilot_agent]
- **Google Gemini CLI** – Pair Gemini with Container Use to open isolated shells (e.g., `cu shell --name=tests -- gemini-cli`) so two Gemini agents can run safely side by side.[^gemini_parallel]
- **Qwen Code** – When you call the `/task` tool, include multiple `task` tool uses in one turn; the bundled guidance explicitly encourages launching several subagents concurrently.[^qwen_task]
- **OpenCode** – The task tool reminds you to “launch multiple agents concurrently whenever possible”; start a review subagent while the build agent continues edits.[^opencode_parallel]
- **Amazon Q Developer CLI** – Use Container Use recipes to create multiple isolated Q sessions so one agent handles reviews while another implements new changes.[^amazonq_parallel]

If an agent lacks built-in subagents, mimic the pattern manually: open a second terminal, move a review prompt to `tasks/doing/`, and run the reviewer commands there while your primary session keeps coding.
