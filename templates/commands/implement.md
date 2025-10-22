---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Verify worktree context**:
   - The feature worktree lives at `PROJECT_ROOT/.worktrees/FEATURE-SLUG`.
   - Determine the expected path from the JSON returned by `create-new-feature` (or compose it using the slug).
   - If your current working directory is not inside that worktree, `cd` into it before proceeding.
   - If the worktree directory is missing, run `git worktree add PROJECT_ROOT/.worktrees/FEATURE-SLUG FEATURE-SLUG` to recreate it, then `cd` into it.

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
      .specify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG TXXX doing \
        --shell-pid "$SHELL_PID" \
        --agent "claude" \
        --note "Started implementation"
      ```
      > Windows users: run `.specify/scripts/powershell/tasks-move-to-lane.ps1` with the same arguments.

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
   - Before you pull a new work package from `tasks/planned/`, list `tasks/for_review/phase-*` to see if anything is waiting on feedback. Handle at least one ready-for-review bundle (move it to doing, run the review flow, and hand it back to `tasks/done/`) before starting fresh work so the kanban never stalls.
   - **Phase-by-phase execution**: Complete each phase before moving to the next
   - **Respect dependencies**: Run sequential tasks in order, parallel tasks [P] can run together  
   - **Follow TDD approach**: Execute test tasks before their corresponding implementation tasks
   - **File-based coordination**: Tasks affecting the same files must run sequentially
   - **Validation checkpoints**: Verify each phase completion before proceeding
   - **Kanban discipline**: Use the lane helper scripts to keep the prompt in `tasks/doing/`, update the Activity Log, and capture your shell PID (`echo $$`). These should already be complete from step 3—verify before coding.

7. Implementation execution rules:
   - **Setup first**: Initialize project structure, dependencies, configuration
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
     .specify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG TXXX for_review \
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
   - `.specify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG WPID doing --note "Started implementation"`
   - Verify frontmatter: `lane: "doing"`, confirm `shell_pid`, `agent`
   - Confirm activity log entry
   - Commit

2. **WORK**: Implement the task
   - Follow prompt guidance
   - Create/modify files as specified
   - Test your changes

3. **COMPLETE**: `doing/` → `for_review/`
   - Add completion entry to activity log
   - `.specify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG WPID for_review --note "Ready for review"`
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

[^claude_subagents]: Anthropic, “Subagents,” showing how to create and invoke Claude Code subagents and explicitly request them for parallel work.
[^codex_cloud]: OpenAI Developers, “Codex Concepts,” describing how cloud tasks let Codex work on multiple jobs in parallel.
[^cursor_parallel]: Cursor, “Cursor Agent CLI,” announcing you can “have multiple agents run in parallel in the terminal or remotely.”
[^copilot_agent]: GitHub, “Kick off and track Copilot coding agent sessions from the GitHub CLI,” documenting the `gh agent-task` commands.
[^gemini_parallel]: Dagger, “Make Gemini CLI work in parallel and isolated dev environments,” demonstrating two Gemini CLI agents operating simultaneously via Container Use.
[^qwen_task]: Moncef Abboud, “How Coding Agents Actually Work: Inside OpenCode,” detailing the task tool instructions (“launch multiple agents concurrently whenever possible”) that Qwen Code inherits.
[^opencode_parallel]: Moncef Abboud, “How Coding Agents Actually Work: Inside OpenCode,” same section describing the concurrent subagent guidance.
[^amazonq_parallel]: Dagger, “Parallel AI Experiments Using Dagger + Amazon Q Developer CLI,” showing multiple Amazon Q CLI sessions running in parallel.
