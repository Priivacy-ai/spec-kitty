---
work_package_id: "WP06"
subtasks:
  - "T023"
  - "T024"
  - "T025"
title: "Reference - Commands"
phase: "Phase 1 - Content Creation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "58964"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies: ["WP02"]
history:
  - timestamp: "2026-01-16T16:16:58Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Reference - Commands

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create complete reference documentation for all commands
- 100% of CLI commands documented
- 100% of slash commands documented
- **Success**: User can find syntax, flags, and examples for any command

## Context & Constraints

- **Spec**: `kitty-specs/014-comprehensive-end-user-documentation/spec.md`
- **Plan**: `kitty-specs/014-comprehensive-end-user-documentation/plan.md`
- **Divio Type**: Reference = information-oriented, complete

### Reference Principles (from Divio)
- Reference docs are **information-oriented**
- Describe the machinery (not explain concepts)
- Be accurate and complete
- Structure around the code/commands
- Consistency is key

### Commands to Document
- **14 slash commands**: /spec-kitty.specify, .plan, .tasks, .implement, .review, .accept, .merge, .status, .dashboard, .constitution, .clarify, .research, .checklist, .analyze
- **CLI commands**: init, upgrade, implement, accept, merge, dashboard, research, mission, validate-encoding, validate-tasks, verify-setup, list-legacy-features, repair
- **Agent subcommands**: agent feature *, agent tasks *, agent context *, agent workflow *, agent release *

## Subtasks & Detailed Guidance

### Subtask T023 – Create cli-commands.md
- **Purpose**: Complete reference for all spec-kitty CLI commands
- **Steps**:
  1. Run `spec-kitty --help` to get command list
  2. For each command, document:
     - Synopsis
     - Description
     - Arguments
     - Options/Flags
     - Examples
     - See Also
  3. Structure:
     ```markdown
     # CLI Command Reference

     ## spec-kitty init
     **Synopsis**: `spec-kitty init [PROJECT_NAME] [OPTIONS]`

     **Description**: Initialize a new Spec Kitty project.

     **Arguments**:
     - `PROJECT_NAME`: Name for new project directory (optional)

     **Options**:
     | Flag | Description |
     |------|-------------|
     | `--ai` | AI assistant: claude, gemini, copilot, cursor, etc. |
     | `--here` | Initialize in current directory |
     | `--force` | Skip confirmation for non-empty directories |
     | `--no-git` | Skip git initialization |
     | `--mission` | Mission key to seed templates |

     **Examples**:
     ```bash
     spec-kitty init my-project
     spec-kitty init my-project --ai claude
     spec-kitty init --here --ai gemini
     ```

     **See Also**: [Installation](../how-to/install-and-upgrade.md)

     ---

     ## spec-kitty upgrade
     [Continue for all commands...]
     ```
- **Files**: `docs/reference/cli-commands.md`
- **Parallel?**: Yes - can generate from --help
- **Notes**: Use `spec-kitty <cmd> --help` to get accurate info

### Subtask T024 – Create slash-commands.md
- **Purpose**: Complete reference for all /spec-kitty.* slash commands
- **Steps**:
  1. List all slash commands from `.claude/commands/` (or equivalent agent directories)
  2. For each command, document:
     - Command syntax
     - When to use
     - Prerequisites
     - What it does
     - What it creates/modifies
     - Related commands
  3. Structure:
     ```markdown
     # Slash Command Reference

     Slash commands are invoked within your AI coding agent (Claude Code, Cursor, etc.).

     ## /spec-kitty.specify

     **Syntax**: `/spec-kitty.specify [description]`

     **Purpose**: Create a feature specification from a natural language description.

     **Prerequisites**: None (first command in workflow)

     **What it does**:
     1. Starts discovery interview
     2. Blocks with WAITING_FOR_DISCOVERY_INPUT
     3. Creates spec.md in kitty-specs/###-feature/
     4. Commits to main branch

     **What it creates**:
     - `kitty-specs/###-feature/spec.md`
     - `kitty-specs/###-feature/meta.json`

     **Example**:
     ```
     /spec-kitty.specify Build a task management app with drag-and-drop
     ```

     **Related**: [create-specification](../how-to/create-specification.md)

     ---

     ## /spec-kitty.plan
     [Continue for all 14 slash commands...]
     ```
- **Files**: `docs/reference/slash-commands.md`
- **Parallel?**: Yes
- **Notes**: Read actual command files from .claude/commands/ for accuracy

### Subtask T025 – Create agent-subcommands.md
- **Purpose**: Complete reference for spec-kitty agent * subcommands
- **Steps**:
  1. Run `spec-kitty agent --help` and each subcommand's --help
  2. Document all agent command groups:
     - `agent feature`: create-feature, check-prerequisites, setup-plan, accept, merge, finalize-tasks
     - `agent tasks`: move-task, mark-status, list-tasks, add-history, finalize-tasks, validate-workflow, status
     - `agent context`: (subcommands)
     - `agent workflow`: implement, review
     - `agent release`: (subcommands)
  3. Structure:
     ```markdown
     # Agent Subcommand Reference

     The `spec-kitty agent` commands are designed for AI agents to execute programmatically.

     ## agent feature

     ### agent feature create-feature
     **Synopsis**: `spec-kitty agent feature create-feature <SLUG> [OPTIONS]`

     **Description**: Create new feature directory in main repository.

     **Options**:
     | Flag | Description |
     |------|-------------|
     | `--json` | Output JSON for parsing |

     **Example**:
     ```bash
     spec-kitty agent feature create-feature "my-feature" --json
     ```

     ---

     ## agent tasks

     ### agent tasks move-task
     [Continue for all subcommands...]
     ```
- **Files**: `docs/reference/agent-subcommands.md`
- **Parallel?**: Yes
- **Notes**: These are less user-facing but important for understanding

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Commands change | Generate from --help output |
| Missing commands | Verify against codebase CLI definitions |
| Outdated flags | Re-run --help during review |

## Definition of Done Checklist

- [ ] T023: cli-commands.md documents ALL CLI commands
- [ ] T024: slash-commands.md documents all 14 slash commands
- [ ] T025: agent-subcommands.md documents all agent * commands
- [ ] All commands have syntax, description, options, examples
- [ ] Generated from actual --help output for accuracy

## Review Guidance

- Verify command syntax against `spec-kitty <cmd> --help`
- Check all flags are documented
- Ensure examples are working commands

## Activity Log

- 2026-01-16T16:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-16T16:31:20Z – __AGENT__ – shell_pid=28468 – lane=doing – Started implementation via workflow command
- 2026-01-16T16:39:28Z – __AGENT__ – shell_pid=28468 – lane=for_review – Ready for review: added CLI, slash, and agent command reference docs
- 2026-01-16T17:50:21Z – claude – shell_pid=58964 – lane=doing – Started review via workflow command
- 2026-01-16T17:50:30Z – claude – shell_pid=58964 – lane=done – Review passed: All 3 command reference docs created (CLI, slash, agent subcommands)
