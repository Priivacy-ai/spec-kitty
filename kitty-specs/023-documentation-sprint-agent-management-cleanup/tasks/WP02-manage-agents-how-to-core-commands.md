---
work_package_id: "WP02"
subtasks:
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Manage Agents How-To Guide - Core Commands"
phase: "Phase 1 - Core Documentation"
lane: "planned"
assignee: ""
agent: "codex"
shell_pid: "24794"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-23T10:23:45Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Manage Agents How-To Guide - Core Commands

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-26

**Issue 1 (requirements - length)**: File exceeds the 600-line limit (631 lines per `wc -l`). The WP requires “keep under 600 lines (target ~500)”. Please trim content (e.g., tighten examples, remove redundancy, or move secondary material to WP03).

**Issue 2 (broken link)**: Overview links to Getting Started at `../getting-started.md` (line 9), which doesn’t exist. Use `../tutorials/getting-started.md` or another valid target.

**Issue 3 (invalid upgrade link)**: The “Upgrading to 0.12.0” links use `upgrade-to-0-11-0.md#upgrading-to-0120` (lines ~75 and ~626), but that anchor doesn’t exist in `docs/how-to/upgrade-to-0-11-0.md`. Point to an existing section or update the upgrade guide link.

**Issue 4 (incorrect behavior)**: “Corrupt or Missing config.yaml” says commands treat all 12 agents as configured (legacy fallback) (line ~550). Actual behavior is empty `agents.available` when config is missing/invalid (see `load_agent_config`), and `spec-kitty agent config list` reports “No agents configured.” Please correct the description.

**Issue 5 (placeholder URL)**: “spec-kitty GitHub Issues” link uses `https://github.com/yourusername/spec-kitty/issues` (line ~602). Replace with the real repo URL (e.g., `https://github.com/Priivacy-ai/spec-kitty/issues`, consistent with other docs).


## ⚠️ Dependency Rebase Guidance

**This WP depends on WP01** (check frontmatter `dependencies:` field).

Before starting, ensure WP01 is complete and review research findings. This WP requires:
- Command signatures from WP01 research
- Config schema from WP01 research
- Error handling details from WP01 research

**Check if WP01 is complete**:
```bash
spec-kitty agent tasks status --feature 023-documentation-sprint-agent-management-cleanup
```

Look for WP01 in "done" lane. If not complete, wait for WP01 or coordinate with that agent.

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

**Goal**: Create comprehensive how-to guide `docs/how-to/manage-agents.md` documenting all 5 agent config commands with task-oriented, actionable guidance.

**Success Criteria**:
- [ ] File created at `docs/how-to/manage-agents.md` (approximately 500 lines)
- [ ] Overview section establishes prerequisites and context
- [ ] "Agent Configuration Model" section explains config-driven approach (config.yaml as single source)
- [ ] All 5 subcommands documented: `list`, `add`, `remove`, `status`, `sync`
- [ ] Each command section includes: purpose, command syntax, concrete examples, error handling behavior
- [ ] Examples demonstrate common use cases (adding after init, removing unused agents, checking status)
- [ ] Documentation follows spec-kitty how-to style (task-oriented, imperative tone, practical focus)
- [ ] User can follow guide to manage agents without reading source code

**Independent Test**: New user can follow guide to add/remove agents, verify with status command, and understand config-driven model.

## Context & Constraints

**Purpose**: This is the primary how-to guide for agent management post-initialization. It addresses User Story 1 (FR-001, FR-002, FR-003).

**Reference Documents**:
- WP01 research findings (command signatures, config schema, agent mappings)
- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/spec.md` (requirements FR-001 through FR-003)
- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/plan.md` (validation strategy)
- `architecture/adrs/2026-01-23-6-config-driven-agent-management.md` (architectural context for config-driven model)

**Source Files for Validation** (read-only, for cross-reference if needed):
- `src/specify_cli/cli/commands/agent/config.py` (command implementations)
- `src/specify_cli/orchestrator/agent_config.py` (AgentConfig dataclass)

**Writing Style**:
- **Task-oriented**: Focus on what user wants to accomplish (add agent, remove agent, check status)
- **Imperative tone**: Use commands like "Run `spec-kitty agent config list`" not "You can run..."
- **Concrete examples**: Real commands with realistic agent selections (claude, codex, opencode)
- **Error handling**: Document what happens when things go wrong (invalid keys, missing dirs)
- **No implementation details**: Don't explain internal dataclasses, functions, or code structure

**Constraints**:
- Must be complete in single WP (WP03 adds supplementary content)
- Sequential subtasks (build document section by section)
- Extract exact syntax from WP01 research findings
- Keep under 600 lines (target 500 lines)

## Subtasks & Detailed Guidance

### Subtask T004 – Create manage-agents.md - Overview and Prerequisites

**Purpose**: Establish document structure, introduce agent management concept, and set user expectations.

**Steps**:

1. **Create file** at `docs/how-to/manage-agents.md`

2. **Write title and frontmatter** (if your docs use frontmatter):
   ```markdown
   # Managing AI Agents

   Learn how to add, remove, and manage AI agents in your spec-kitty project after initialization.
   ```

3. **Write Overview section** (5-7 paragraphs):
   - Introduce the concept: Spec-kitty supports 12 AI agents (Claude, Codex, etc.)
   - Explain when this guide applies: After `spec-kitty init`, when you want to change active agents
   - Mention config-driven model briefly: "Agent configuration is managed through `.kittify/config.yaml` and the `spec-kitty agent config` command family."
   - State goal: This guide shows you how to add, remove, list, and sync agents post-initialization
   - Preview the 5 commands briefly: `list`, `add`, `remove`, `status`, `sync`

4. **Write Prerequisites section**:
   ```markdown
   ## Prerequisites

   Before using agent config commands, ensure:

   - You have initialized a spec-kitty project (`spec-kitty init`)
   - You are in the project root directory (where `.kittify/` exists)
   - You have write permissions to the project directory
   ```

5. **Add "Quick Reference" table** (optional but helpful):
   | Command | Purpose |
   |---------|---------|
   | `spec-kitty agent config list` | View configured agents and available options |
   | `spec-kitty agent config add <agents>` | Add agents to your project |
   | `spec-kitty agent config remove <agents>` | Remove agents from your project |
   | `spec-kitty agent config status` | Audit agent configuration sync status |
   | `spec-kitty agent config sync` | Synchronize filesystem with config.yaml |

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: No (must complete before other subtasks)

**Notes**:
- Keep overview focused on user goals (not technical implementation)
- Prerequisites should be minimal (most users will have these)
- Quick reference table helps users navigate long document

**Validation**:
- [ ] File created at correct path
- [ ] Overview explains when/why to use this guide
- [ ] Prerequisites are clear and minimal
- [ ] Quick reference table lists all 5 commands

---

### Subtask T005 – Write "Agent Configuration Model" Section

**Purpose**: Explain the config-driven model where `.kittify/config.yaml` is the single source of truth.

**Steps**:

1. **Add section header**:
   ```markdown
   ## Understanding Agent Configuration
   ```

2. **Explain config-driven model** (3-4 paragraphs):
   - State the principle: "`.kittify/config.yaml` is the single source of truth for agent configuration."
   - Explain what this means: Agent directories on filesystem are derived from this config
   - Contrast with manual approach: "Do not manually edit agent directories or config.yaml - use `spec-kitty agent config` commands instead."
   - Explain benefits: Migrations respect your choices, no unexpected directory recreation

3. **Show config.yaml structure** (extract from WP01 research):
   ```yaml
   agents:
     available:
       - claude
       - codex
       - opencode
   ```

   Add explanation:
   - `available`: List of active agent keys
   - Agent keys correspond to directories (e.g., `claude` → `.claude/commands/`)
   - When you add/remove agents via CLI, this list is automatically updated

4. **Explain agent directories**:
   - Each configured agent has a directory (e.g., `.claude/commands/`)
   - Directory contains slash command templates (e.g., `spec-kitty.specify.md`)
   - Directories are created/removed automatically by CLI commands

5. **Add "Why This Matters" callout**:
   ```markdown
   > **Why This Matters**: In spec-kitty 0.11.x and earlier, users could manually delete agent directories, but migrations would recreate them. Starting in 0.12.0, migrations respect `config.yaml` - if an agent is not listed in `available`, its directory stays deleted. See [Upgrading to 0.12.0](upgrade-to-0-11-0.md#upgrading-to-0120) for details.
   ```

6. **Link to ADR #6** (optional architectural reference):
   ```markdown
   For architectural details, see [ADR #6: Config-Driven Agent Management](../../architecture/adrs/2026-01-23-6-config-driven-agent-management.md).
   ```

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: No (sequential after T004)

**Notes**:
- Focus on user-facing behavior (not internal dataclasses)
- Explain benefits of config-driven approach (migrations respect choices)
- Link to migration guide for 0.11.x users

**Validation**:
- [ ] Config-driven model explained clearly
- [ ] config.yaml structure shown with example
- [ ] Benefits of model stated (migration behavior)
- [ ] Callout references migration guide

---

### Subtask T006 – Document `config list` Command

**Purpose**: Document the `list` subcommand for viewing configured agents and available options.

**Steps**:

1. **Add section header**:
   ```markdown
   ## Listing Agents

   ### View Configured Agents

   To see which agents are currently configured in your project:
   ```

2. **Show command**:
   ```bash
   spec-kitty agent config list
   ```

3. **Explain output** (extract format from WP01 research T001):
   - Two sections: "Configured agents" and "Available but not configured"
   - Configured agents show status indicator:
     - ✓ = Agent directory exists
     - ⚠ = Configured but directory missing (rare)
   - Available section shows agents you can add

4. **Show example output** (create realistic example):
   ```
   Configured agents:
     ✓ opencode (.opencode/command/)
     ✓ claude (.claude/commands/)

   Available but not configured:
     - codex
     - gemini
     - cursor
     - qwen
     - windsurf
     - kilocode
     - roo
     - copilot
     - auggie
     - q
   ```

5. **Explain use case**:
   ```markdown
   Use `list` to:
   - See which agents are active in your project
   - Check if configured agents have directories on filesystem
   - Discover available agents you can add
   ```

6. **Add troubleshooting note**:
   ```markdown
   **Troubleshooting**: If you see ⚠ next to a configured agent, the directory is missing from filesystem. Run `spec-kitty agent config sync --create-missing` to restore it.
   ```

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: No (sequential after T005)

**Notes**:
- Extract exact output format from WP01 research
- Use realistic example (not all 12 agents configured)
- Include use case summary

**Validation**:
- [ ] Command syntax shown
- [ ] Output format explained with status indicators
- [ ] Example output demonstrates typical scenario
- [ ] Use case summary provided
- [ ] Troubleshooting note for missing directories

---

### Subtask T007 – Document `config add` Command

**Purpose**: Document the `add` subcommand for adding agents to existing projects.

**Steps**:

1. **Add section header**:
   ```markdown
   ## Adding Agents

   ### Add One or More Agents

   To add agents to your project after initialization:
   ```

2. **Show command syntax**:
   ```bash
   spec-kitty agent config add <agent1> <agent2> ...
   ```

3. **Provide concrete examples**:
   ```bash
   # Add a single agent
   spec-kitty agent config add claude

   # Add multiple agents at once
   spec-kitty agent config add codex gemini cursor
   ```

4. **Explain what happens** (extract from WP01 research T001):
   - Agent directory is created (e.g., `.claude/commands/`)
   - Slash command templates are copied to directory
   - Agent key is added to `.kittify/config.yaml` under `agents.available`
   - Success message: "✓ Added .claude/commands/"

5. **Show example output**:
   ```
   ✓ Added .claude/commands/
   ✓ Added .codex/prompts/
   Updated .kittify/config.yaml
   ```

6. **Document error handling** (extract from WP01 research T001):
   ```markdown
   ### Error Handling

   **Invalid agent key**: If you provide an invalid agent key, you'll see an error with the list of valid agents:

   ```bash
   spec-kitty agent config add cluade
   ```

   Output:
   ```
   Error: Invalid agent keys: cluade

   Valid agent keys:
     claude, codex, gemini, cursor, qwen, opencode,
     windsurf, kilocode, roo, copilot, auggie, q
   ```

   **Already configured**: If an agent is already configured, it's skipped with a message:
   ```
   Already configured: claude
   ```
   ```

7. **Add use case examples**:
   ```markdown
   ### Common Scenarios

   **Starting with one agent, adding more later**:
   ```bash
   # Initialized with opencode only
   spec-kitty agent config add claude codex
   # Now you have 3 agents for multi-agent workflows
   ```

   **Enabling cross-review**:
   ```bash
   # Add a reviewer agent different from your implementer
   spec-kitty agent config add codex
   # Configure in .kittify/config.yaml:
   # agents:
   #   selection:
   #     preferred_implementer: claude
   #     preferred_reviewer: codex
   ```
   ```

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: No (sequential after T006)

**Notes**:
- Extract exact error messages from WP01 research
- Show realistic examples (not contrived)
- Explain what files/directories are modified
- Include common use cases

**Validation**:
- [ ] Command syntax documented
- [ ] Examples show single and multiple agents
- [ ] Side effects explained (directories, config.yaml)
- [ ] Error handling documented (invalid keys, already configured)
- [ ] Common scenarios provided

---

### Subtask T008 – Document `config remove` Command

**Purpose**: Document the `remove` subcommand for removing agents from projects.

**Steps**:

1. **Add section header**:
   ```markdown
   ## Removing Agents

   ### Remove One or More Agents

   To remove agents you no longer use:
   ```

2. **Show command syntax**:
   ```bash
   spec-kitty agent config remove <agent1> <agent2> ...
   ```

3. **Provide concrete examples**:
   ```bash
   # Remove a single agent
   spec-kitty agent config remove gemini

   # Remove multiple agents at once
   spec-kitty agent config remove cursor qwen windsurf
   ```

4. **Explain what happens** (extract from WP01 research T001):
   - Agent directory is deleted (e.g., `.gemini/` and all contents)
   - Agent key is removed from `.kittify/config.yaml`
   - Success message: "✓ Removed .gemini/"

5. **Show example output**:
   ```
   ✓ Removed .gemini/
   ✓ Removed .cursor/
   Updated .kittify/config.yaml
   ```

6. **Document `--keep-config` flag** (extract from WP01 research T001):
   ```markdown
   ### Keep in Configuration but Remove Directory

   To remove an agent's directory but keep it in `config.yaml` (for temporary cleanup):

   ```bash
   spec-kitty agent config remove gemini --keep-config
   ```

   **What this does**:
   - Deletes `.gemini/` directory
   - Leaves `gemini` in `config.yaml` under `available`
   - Useful for temporary cleanup without losing configuration

   **Restore later**: Run `spec-kitty agent config sync --create-missing` to restore the directory.
   ```

7. **Document error handling**:
   ```markdown
   ### Error Handling

   **Invalid agent key**: Same error as `add` command - shows list of valid agents.

   **Already removed**: If agent is already removed, you'll see:
   ```
   • .gemini/ already removed
   ```

   This is informational, not an error - command continues processing other agents.
   ```

8. **Add warning callout**:
   ```markdown
   > **Warning**: Removing an agent deletes its entire directory and all slash command templates. This is safe if you're not using the agent, but ensure you don't have custom modifications in those template files before removing.
   ```

9. **Add use case examples**:
   ```markdown
   ### Common Scenarios

   **Simplifying multi-agent setup**:
   ```bash
   # Started with many agents, narrowing to preferred ones
   spec-kitty agent config remove windsurf kilocode roo
   # Keep only the agents you actively use
   ```

   **Preparing for upgrade** (0.11.x → 0.12.0):
   ```bash
   # Before upgrading, remove unwanted agents properly
   spec-kitty agent config remove gemini cursor qwen
   # Migrations will now respect your choices
   ```
   ```

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: No (sequential after T007)

**Notes**:
- Extract exact behavior from WP01 research
- Emphasize directory deletion (destructive operation)
- Document `--keep-config` flag clearly
- Include migration use case (relevant for 0.11.x users)

**Validation**:
- [ ] Command syntax documented
- [ ] Examples show single and multiple agents
- [ ] Side effects explained (directory deletion, config.yaml update)
- [ ] `--keep-config` flag documented with use case
- [ ] Error handling documented
- [ ] Warning about directory deletion included
- [ ] Common scenarios provided

---

### Subtask T009 – Document `config status` Command

**Purpose**: Document the `status` subcommand for auditing agent configuration sync status.

**Steps**:

1. **Add section header**:
   ```markdown
   ## Checking Agent Status

   ### Audit Configuration Sync

   To see a comprehensive view of all agents and their sync status:
   ```

2. **Show command**:
   ```bash
   spec-kitty agent config status
   ```

3. **Explain output format** (extract from WP01 research T001):
   - Rich table with 5 columns:
     - Agent Key (cyan)
     - Directory (dim)
     - Configured (✓/✗)
     - Exists (✓/✗)
     - Status (colored)

4. **Document status values** (extract from WP01 research T001):
   ```markdown
   **Status values**:
   - **OK** (green): Agent is configured and directory exists - normal state
   - **Missing** (yellow): Agent is configured but directory doesn't exist - needs sync
   - **Orphaned** (red): Agent directory exists but not configured - should be cleaned up
   - **Not used** (dim): Agent is neither configured nor present - available to add
   ```

5. **Show example output** (create realistic table):
   ```
   Agent Key  Directory                Configured  Exists  Status
   ──────────────────────────────────────────────────────────────────
   claude     .claude/commands/        ✓           ✓       OK
   codex      .codex/prompts/          ✗           ✓       Orphaned
   gemini     .gemini/commands/        ✓           ✗       Missing
   cursor     .cursor/commands/        ✗           ✗       Not used
   ...

   ⚠ Found 1 orphaned directory
   Run 'spec-kitty agent config sync --remove-orphaned' to clean up
   ```

6. **Explain use cases**:
   ```markdown
   Use `status` to:
   - Audit your agent configuration for inconsistencies
   - Detect orphaned directories (present but not configured)
   - Identify missing directories (configured but not present)
   - See all 12 agents at a glance
   ```

7. **Add actionable guidance**:
   ```markdown
   ### Taking Action Based on Status

   **Orphaned directories** (red "Orphaned" status):
   ```bash
   # Remove orphaned directories automatically
   spec-kitty agent config sync --remove-orphaned
   ```

   **Missing directories** (yellow "Missing" status):
   ```bash
   # Restore missing configured agents
   spec-kitty agent config sync --create-missing
   ```

   **Not used** (dim "Not used" status):
   ```bash
   # Add to your project if you want to use them
   spec-kitty agent config add <agent>
   ```
   ```

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: No (sequential after T008)

**Notes**:
- Extract exact table format and status values from WP01 research
- Show realistic example with mixed statuses
- Provide actionable guidance for each status
- Link to `sync` command for remediation

**Validation**:
- [ ] Command syntax documented
- [ ] Output format explained with table structure
- [ ] All 4 status values documented (OK, Missing, Orphaned, Not used)
- [ ] Example output shows realistic scenario
- [ ] Use cases listed
- [ ] Actionable guidance for each status type

---

### Subtask T010 – Document `config sync` Command

**Purpose**: Document the `sync` subcommand for synchronizing filesystem with config.yaml.

**Steps**:

1. **Add section header**:
   ```markdown
   ## Synchronizing Filesystem

   ### Auto-Sync Agents with Configuration

   The `sync` command automatically aligns your filesystem with `.kittify/config.yaml`:
   ```

2. **Show command**:
   ```bash
   spec-kitty agent config sync
   ```

3. **Explain default behavior** (extract from WP01 research T001):
   ```markdown
   **Default behavior** (no flags):
   - Removes orphaned directories (present but not configured)
   - Does NOT create missing directories
   - Reports actions taken or "No changes needed"
   ```

4. **Document `--create-missing` flag**:
   ```markdown
   ### Create Missing Configured Agents

   To restore directories for configured agents that are missing from filesystem:

   ```bash
   spec-kitty agent config sync --create-missing
   ```

   **What this does**:
   - Creates directories for agents in `config.yaml` but missing from filesystem
   - Copies slash command templates to each created directory
   - Also removes orphaned directories (default behavior)

   **Example output**:
   ```
   ✓ Created .claude/commands/
   ✓ Removed orphaned .gemini/
   ```
   ```

5. **Document `--keep-orphaned` flag**:
   ```markdown
   ### Keep Orphaned Directories

   To prevent deletion of orphaned directories:

   ```bash
   spec-kitty agent config sync --keep-orphaned
   ```

   **What this does**:
   - Does NOT remove orphaned directories
   - Still creates missing directories if `--create-missing` is used

   **Use case**: You have agent directories not in config.yaml but want to keep them (rare).
   ```

6. **Document `--remove-orphaned` flag** (explicit version of default):
   ```markdown
   ### Explicitly Remove Orphaned Directories

   The default behavior removes orphaned directories, but you can be explicit:

   ```bash
   spec-kitty agent config sync --remove-orphaned
   ```

   This is equivalent to running `sync` with no flags.
   ```

7. **Show combined flag usage**:
   ```markdown
   ### Complete Sync (Both Directions)

   To fully sync filesystem with config (create missing AND remove orphaned):

   ```bash
   spec-kitty agent config sync --create-missing --remove-orphaned
   ```

   This ensures filesystem exactly matches `config.yaml`.
   ```

8. **Add "No Changes Needed" scenario**:
   ```markdown
   ### When Filesystem Matches Config

   If your filesystem already matches `config.yaml`:

   ```
   No changes needed - filesystem matches config
   ```
   ```

9. **Add use case examples**:
   ```markdown
   ### Common Scenarios

   **After manual directory deletion** (not recommended, but happens):
   ```bash
   # You manually deleted .gemini/ but forgot to update config.yaml
   spec-kitty agent config status
   # Shows "Missing" status for gemini

   # Option 1: Restore directory
   spec-kitty agent config sync --create-missing

   # Option 2: Remove from config properly
   spec-kitty agent config remove gemini
   ```

   **After git checkout** (switched branches with different agent configs):
   ```bash
   # Branch A has claude, Branch B has codex
   git checkout branch-b

   # Sync filesystem to match branch-b's config
   spec-kitty agent config sync --create-missing --remove-orphaned
   ```

   **Cleanup after testing** (removed agents manually):
   ```bash
   # Default sync removes orphaned directories
   spec-kitty agent config sync
   ```
   ```

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: No (sequential after T009)

**Notes**:
- Extract exact flag behavior from WP01 research
- Clarify default behavior (removes orphaned, does NOT create missing)
- Show flag combinations
- Provide realistic use cases

**Validation**:
- [ ] Command syntax documented
- [ ] Default behavior explained (remove orphaned only)
- [ ] `--create-missing` flag documented
- [ ] `--keep-orphaned` flag documented
- [ ] `--remove-orphaned` flag documented (explicit default)
- [ ] Combined flag usage shown
- [ ] "No changes needed" scenario included
- [ ] Common scenarios provided

---

## Test Strategy

**Manual Validation** (not automated tests):

1. **Command Syntax Check**:
   - Cross-reference all documented commands against `spec-kitty agent config --help` output
   - Verify flags match WP01 research findings

2. **Example Execution**:
   - Run each example command in a test project
   - Verify output matches documented examples
   - Check that errors trigger as documented

3. **Flow Validation**:
   - Follow guide as a new user (simulate first-time experience)
   - Ensure each command section provides enough context to succeed
   - Verify examples are realistic and actionable

4. **Cross-Reference Validation**:
   - Ensure all references to WP01 research are accurate
   - Verify config.yaml structure matches AgentConfig dataclass (from WP01 research)
   - Confirm agent key list matches AGENT_DIR_TO_KEY (from WP01 research)

## Risks & Mitigations

**Risk**: Commands documented don't match actual CLI behavior
- **Mitigation**: Extract exact syntax from WP01 research; cross-reference against `spec-kitty agent config --help` output
- **Detection**: Manual command execution during validation

**Risk**: Examples too abstract or contrived
- **Mitigation**: Use realistic scenarios (claude, codex, opencode are common agents)
- **Validation**: Test examples in a real project

**Risk**: Missing edge cases or error conditions
- **Mitigation**: Review WP01 research T001 thoroughly for error handling details
- **Cross-check**: Run commands with invalid inputs to confirm error messages

**Risk**: Guide too technical (implementation-focused)
- **Mitigation**: Stay at user/task level; avoid mentioning dataclasses, functions, internal logic
- **Validation**: Read guide as a non-developer user persona

## Review Guidance

**Acceptance Checkpoints**:
- [ ] File created at `docs/how-to/manage-agents.md`
- [ ] Document is approximately 500 lines (target size)
- [ ] All 7 subtasks (T004-T010) completed
- [ ] Overview and prerequisites establish context
- [ ] "Agent Configuration Model" section explains config-driven approach
- [ ] All 5 commands documented: list, add, remove, status, sync
- [ ] Each command section includes: syntax, examples, side effects, error handling
- [ ] Examples are concrete and realistic (not abstract placeholders)
- [ ] Error handling matches WP01 research findings
- [ ] Writing style is task-oriented and imperative
- [ ] No implementation details (dataclasses, functions) included
- [ ] Cross-references to migration guide included where relevant

**Review Focus**:
- **Completeness**: Are all 5 commands fully documented?
- **Accuracy**: Do documented commands match WP01 research findings?
- **Usability**: Can a user follow guide without additional resources?
- **Style**: Does it follow spec-kitty how-to conventions?

**Success Indicator**: A new user can successfully add, remove, list, and sync agents by following this guide alone, without reading source code or asking for help.

## Activity Log

**Initial entry**:
- 2026-01-23T10:23:45Z – system – lane=planned – Prompt generated.

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP02 --to <lane> --note "message"` (recommended)

The CLI command updates both frontmatter and activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

---
- 2026-01-23T10:56:39Z – claude – shell_pid=15781 – lane=doing – Started implementation via workflow command
- 2026-01-23T10:58:56Z – claude – shell_pid=15781 – lane=for_review – Ready for review: Comprehensive 461-line how-to guide covering all 5 agent config commands (list, add, remove, status, sync) with concrete examples, error handling, and common scenarios. Includes config-driven model explanation and cross-references to migration guide and ADR #6.
- 2026-01-23T10:59:40Z – Claude – shell_pid=19176 – lane=doing – Started review via workflow command
- 2026-01-23T10:59:54Z – Claude – shell_pid=19176 – lane=done – Review passed: Comprehensive how-to guide for managing agents covering all 5 core commands with examples, error handling, and common scenarios.
- 2026-01-26T08:56:02Z – codex – shell_pid=24794 – lane=doing – Started review via workflow command
- 2026-01-26T09:00:19Z – codex – shell_pid=24794 – lane=planned – Moved to planned

## Implementation Command

**Depends on WP01** - Ensure WP01 is complete before starting.

```bash
spec-kitty implement WP02 --base WP01
```

After completing this WP, WP03 can start (adds supplementary content to manage-agents.md).
