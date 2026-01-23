---
work_package_id: "WP05"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "CLI Reference - Agent Config Commands"
phase: "Phase 2 - Reference Documentation"
lane: "done"
assignee: ""
agent: "Claude"
shell_pid: "38505"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-23T10:23:45Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – CLI Reference - Agent Config Commands

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## ⚠️ Dependency Rebase Guidance

**This WP depends on WP01** (check frontmatter `dependencies:` field).

Before starting, ensure WP01 is complete and review research findings. This WP requires:
- Command signatures from WP01 research (T001)
- Exact syntax, flags, defaults, error messages

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

**Goal**: Document `spec-kitty agent config` command group with all 5 subcommands in CLI reference format.

**Success Criteria**:
- [ ] `docs/reference/cli-commands.md` updated with new `spec-kitty agent config` section
- [ ] Main command section includes overview and subcommand list
- [ ] All 5 subcommands documented: `list`, `add`, `remove`, `status`, `sync`
- [ ] Each subcommand includes: synopsis, description, arguments, options, output, examples
- [ ] Follows existing CLI reference style and format
- [ ] Exact syntax matches WP01 research findings
- [ ] Cross-references manage-agents.md for task-oriented guidance
- [ ] Approximately 450 lines total

**Independent Test**: Developer can consult CLI reference to find complete command syntax, flags, defaults, and examples.

## Context & Constraints

**Purpose**: Provide reference documentation for developers and scripters who need precise command syntax. This addresses User Story 3 (FR-006, FR-007).

**Reference Documents**:
- WP01 research findings (T001 - command signatures, flags, defaults, error handling)
- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/spec.md` (requirements FR-006, FR-007)
- Existing `docs/reference/cli-commands.md` (for style and format)

**Source Files for Validation** (read-only):
- `src/specify_cli/cli/commands/agent/config.py` (command implementations)

**Writing Style**:
- **Reference format**: Formal, structured, comprehensive
- **Synopsis**: Exact command syntax with placeholders
- **Description**: What the command does (brief, 1-2 sentences)
- **Arguments**: Required positional arguments
- **Options**: Optional flags with defaults
- **Output**: What user sees when command runs
- **Examples**: Concrete usage examples (1-3 per command)
- **Consistent structure**: Match existing cli-commands.md format

**Constraints**:
- Must match existing CLI reference style exactly
- T019 sets up main section, T020-T024 can be parallelized (different subcommands)
- Extract exact syntax from WP01 research (don't invent or summarize)
- Keep under 500 lines total (approximately 75 lines per subcommand)

## Subtasks & Detailed Guidance

### Subtask T019 – Add `spec-kitty agent config` Main Section

**Purpose**: Insert main command section into cli-commands.md with overview and subcommand index.

**Steps**:

1. **Locate insertion point** in `docs/reference/cli-commands.md`:
   - Find section for `spec-kitty agent` commands
   - Insert after existing agent subcommands (or at end of agent section)

2. **Add main command header**:
   ```markdown
   ### spec-kitty agent config

   Manage project AI agent configuration (add, remove, list agents).

   **Usage**:
   ```bash
   spec-kitty agent config [OPTIONS] COMMAND [ARGS]...
   ```

   **Description**: The `config` subcommand provides tools for managing which AI agents are active in your project. Agent configuration is stored in `.kittify/config.yaml` and controls which agent directories are present on the filesystem.
   ```

3. **Add subcommand index**:
   ```markdown
   **Subcommands**:

   | Command | Description |
   |---------|-------------|
   | `list` | View configured agents and available options |
   | `add` | Add one or more agents to your project |
   | `remove` | Remove one or more agents from your project |
   | `status` | Audit agent configuration sync status |
   | `sync` | Synchronize filesystem with config.yaml |
   ```

4. **Add cross-reference to how-to guide**:
   ```markdown
   **See also**: [Managing AI Agents](../how-to/manage-agents.md) for task-oriented guidance on agent management workflows.
   ```

5. **Add note about config-driven model**:
   ```markdown
   > **Note**: Starting in 0.12.0, agent configuration is config-driven. `.kittify/config.yaml` is the single source of truth, and migrations respect your configuration choices. See [Upgrading to 0.12.0](../how-to/upgrade-to-0-11-0.md#upgrading-to-0120) for migration details.
   ```

**Files**: `docs/reference/cli-commands.md`

**Parallel**: No (must complete before T020-T024)

**Notes**:
- Extract exact usage and description from WP01 research T001
- Subcommand table provides quick reference
- Cross-reference establishes link to how-to guide
- Note about config-driven model provides context

**Validation**:
- [ ] Main section inserted at correct location in cli-commands.md
- [ ] Usage syntax matches WP01 research
- [ ] Subcommand table lists all 5 commands
- [ ] Cross-reference to manage-agents.md included
- [ ] Note about 0.12.0 config-driven model included

---

### Subtask T020 – Document `list` Subcommand in CLI Reference

**Purpose**: Add reference documentation for `spec-kitty agent config list` command.

**Steps**:

1. **Add subcommand header** (use existing CLI reference format):
   ```markdown
   #### spec-kitty agent config list

   View configured agents and available options.
   ```

2. **Add synopsis**:
   ```markdown
   **Synopsis**:
   ```bash
   spec-kitty agent config list
   ```
   ```

3. **Add description**:
   ```markdown
   **Description**:

   Lists agents currently configured in your project (from `.kittify/config.yaml`) with status indicators, and shows available agents that can be added.
   ```

4. **Add arguments** (none for list):
   ```markdown
   **Arguments**: None
   ```

5. **Add options** (none for list):
   ```markdown
   **Options**: None
   ```

6. **Add output format** (extract from WP01 research T001):
   ```markdown
   **Output**:

   Two sections:
   - **Configured agents**: Agents in `config.yaml` with status indicators:
     - ✓ (green) - Directory exists
     - ⚠ (yellow) - Configured but directory missing
   - **Available but not configured**: Agents you can add
   ```

7. **Add examples**:
   ```markdown
   **Examples**:

   View configured agents:
   ```bash
   spec-kitty agent config list
   ```

   Example output:
   ```
   Configured agents:
     ✓ opencode (.opencode/command/)
     ✓ claude (.claude/commands/)

   Available but not configured:
     - codex
     - gemini
     - cursor
     ...
   ```
   ```

**Files**: `docs/reference/cli-commands.md`

**Parallel**: Yes (after T019, parallel with T021-T024)

**Notes**:
- Extract exact output format from WP01 research T001 (lines 39-76)
- Follow existing CLI reference structure precisely
- Include realistic example output
- Keep under 75 lines

**Validation**:
- [ ] Subcommand documented with header
- [ ] Synopsis shows exact command
- [ ] Description explains purpose briefly
- [ ] Arguments section (none)
- [ ] Options section (none)
- [ ] Output format explained with status indicators
- [ ] Example with realistic output included

---

### Subtask T021 – Document `add` Subcommand in CLI Reference

**Purpose**: Add reference documentation for `spec-kitty agent config add` command.

**Steps**:

1. **Add subcommand header**:
   ```markdown
   #### spec-kitty agent config add

   Add one or more agents to your project.
   ```

2. **Add synopsis**:
   ```markdown
   **Synopsis**:
   ```bash
   spec-kitty agent config add <agent1> [agent2] [agent3] ...
   ```
   ```

3. **Add description**:
   ```markdown
   **Description**:

   Adds specified agents to your project by creating agent directories, copying slash command templates, and updating `.kittify/config.yaml`.
   ```

4. **Add arguments**:
   ```markdown
   **Arguments**:

   - `<agents>`: Space-separated list of agent keys to add. Valid keys: `claude`, `codex`, `gemini`, `cursor`, `qwen`, `opencode`, `windsurf`, `kilocode`, `roo`, `copilot`, `auggie`, `q`.
   ```

5. **Add options** (none for add):
   ```markdown
   **Options**: None
   ```

6. **Add output format** (extract from WP01 research T001):
   ```markdown
   **Output**:

   - Success: `✓ Added <agent-dir>/<subdir>/` for each agent
   - Already configured: `Already configured: <agent>` (informational, not an error)
   - Error: `Error: Invalid agent keys: <keys>` with list of valid keys
   ```

7. **Add side effects**:
   ```markdown
   **Side Effects**:

   - Creates agent directory (e.g., `.claude/commands/`)
   - Copies slash command templates from mission templates
   - Adds agent key to `.kittify/config.yaml` under `agents.available`
   ```

8. **Add examples**:
   ```markdown
   **Examples**:

   Add a single agent:
   ```bash
   spec-kitty agent config add claude
   ```

   Add multiple agents:
   ```bash
   spec-kitty agent config add codex gemini cursor
   ```

   Example output:
   ```
   ✓ Added .codex/prompts/
   ✓ Added .gemini/commands/
   ✓ Added .cursor/commands/
   Updated .kittify/config.yaml
   ```

   Error handling (invalid key):
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
   ```

**Files**: `docs/reference/cli-commands.md`

**Parallel**: Yes (after T019, parallel with T020, T022-T024)

**Notes**:
- Extract exact behavior from WP01 research T001 (lines 78-157)
- Document error handling explicitly
- Show side effects (what changes on filesystem)
- Include both success and error examples

**Validation**:
- [ ] Synopsis shows command with arguments placeholder
- [ ] Description explains purpose
- [ ] Arguments documented with valid keys list
- [ ] Options section (none)
- [ ] Output format explained (success, already configured, error)
- [ ] Side effects listed (directories, templates, config.yaml)
- [ ] Examples show single agent, multiple agents, and error handling

---

### Subtask T022 – Document `remove` Subcommand in CLI Reference

**Purpose**: Add reference documentation for `spec-kitty agent config remove` command.

**Steps**:

1. **Add subcommand header**:
   ```markdown
   #### spec-kitty agent config remove

   Remove one or more agents from your project.
   ```

2. **Add synopsis**:
   ```markdown
   **Synopsis**:
   ```bash
   spec-kitty agent config remove [OPTIONS] <agent1> [agent2] [agent3] ...
   ```
   ```

3. **Add description**:
   ```markdown
   **Description**:

   Removes specified agents from your project by deleting agent directories and updating `.kittify/config.yaml`.
   ```

4. **Add arguments**:
   ```markdown
   **Arguments**:

   - `<agents>`: Space-separated list of agent keys to remove. Valid keys: same as `add` command.
   ```

5. **Add options** (extract from WP01 research T001):
   ```markdown
   **Options**:

   - `--keep-config`: Keep agent in `config.yaml` but delete directory (default: False)
   ```

6. **Add output format**:
   ```markdown
   **Output**:

   - Success: `✓ Removed <agent-dir>/` for each agent
   - Already removed: `• <agent-dir>/ already removed` (dim, informational)
   - Error: `Error: Invalid agent keys: <keys>` with list of valid keys
   ```

7. **Add side effects**:
   ```markdown
   **Side Effects**:

   - Deletes entire agent directory (e.g., `.gemini/` and all contents)
   - Removes agent key from `.kittify/config.yaml` (unless `--keep-config` used)

   **Warning**: Directory deletion is permanent. Ensure you don't have custom modifications in template files before removing.
   ```

8. **Add examples**:
   ```markdown
   **Examples**:

   Remove a single agent:
   ```bash
   spec-kitty agent config remove gemini
   ```

   Remove multiple agents:
   ```bash
   spec-kitty agent config remove cursor qwen windsurf
   ```

   Example output:
   ```
   ✓ Removed .cursor/
   ✓ Removed .qwen/
   ✓ Removed .windsurf/
   Updated .kittify/config.yaml
   ```

   Keep in config but remove directory:
   ```bash
   spec-kitty agent config remove gemini --keep-config
   ```

   Restore later with:
   ```bash
   spec-kitty agent config sync --create-missing
   ```
   ```

**Files**: `docs/reference/cli-commands.md`

**Parallel**: Yes (after T019, parallel with T020-T021, T023-T024)

**Notes**:
- Extract exact behavior from WP01 research T001 (lines 159-228)
- Emphasize destructive nature (directory deletion)
- Document `--keep-config` flag use case
- Show restoration workflow for `--keep-config` case

**Validation**:
- [ ] Synopsis shows OPTIONS placeholder
- [ ] Description explains purpose
- [ ] Arguments documented
- [ ] Options documented (`--keep-config` with default)
- [ ] Output format explained (success, already removed, error)
- [ ] Side effects listed with warning about permanent deletion
- [ ] Examples show single agent, multiple agents, and `--keep-config` usage

---

### Subtask T023 – Document `status` Subcommand in CLI Reference

**Purpose**: Add reference documentation for `spec-kitty agent config status` command.

**Steps**:

1. **Add subcommand header**:
   ```markdown
   #### spec-kitty agent config status

   Audit agent configuration sync status.
   ```

2. **Add synopsis**:
   ```markdown
   **Synopsis**:
   ```bash
   spec-kitty agent config status
   ```
   ```

3. **Add description**:
   ```markdown
   **Description**:

   Displays a comprehensive table showing all 12 supported agents, whether they're configured, whether directories exist, and sync status.
   ```

4. **Add arguments** (none):
   ```markdown
   **Arguments**: None
   ```

5. **Add options** (none):
   ```markdown
   **Options**: None
   ```

6. **Add output format** (extract from WP01 research T001):
   ```markdown
   **Output**:

   Rich table with columns:
   - **Agent Key** (cyan): Agent identifier
   - **Directory** (dim): Filesystem path
   - **Configured**: ✓ if in `config.yaml`, ✗ otherwise
   - **Exists**: ✓ if directory present, ✗ otherwise
   - **Status**: Colored status indicator

   **Status values**:
   - `[green]OK[/green]`: Configured and directory exists (normal state)
   - `[yellow]Missing[/yellow]`: Configured but directory doesn't exist (needs sync)
   - `[red]Orphaned[/red]`: Directory exists but not configured (should be cleaned up)
   - `[dim]Not used[/dim]`: Neither configured nor present (available to add)

   **Actionable message**: If orphaned directories detected, shows: `"Run 'spec-kitty agent config sync --remove-orphaned' to clean up"`
   ```

7. **Add examples**:
   ```markdown
   **Examples**:

   Audit agent configuration:
   ```bash
   spec-kitty agent config status
   ```

   Example output:
   ```
   Agent Key  Directory                Configured  Exists  Status
   ──────────────────────────────────────────────────────────────────
   claude     .claude/commands/        ✓           ✓       OK
   codex      .codex/prompts/          ✗           ✓       Orphaned
   gemini     .gemini/commands/        ✓           ✗       Missing
   cursor     .cursor/commands/        ✗           ✗       Not used
   qwen       .qwen/commands/          ✓           ✓       OK
   ...

   ⚠ Found 1 orphaned directory
   Run 'spec-kitty agent config sync --remove-orphaned' to clean up
   ```
   ```

**Files**: `docs/reference/cli-commands.md`

**Parallel**: Yes (after T019, parallel with T020-T022, T024)

**Notes**:
- Extract exact table structure from WP01 research T001 (lines 230-295)
- Document all 4 status values with color indicators
- Show actionable message for orphaned directories
- Include realistic table example

**Validation**:
- [ ] Synopsis shows command
- [ ] Description explains purpose
- [ ] Arguments section (none)
- [ ] Options section (none)
- [ ] Output format documented with table structure
- [ ] All 4 status values explained (OK, Missing, Orphaned, Not used)
- [ ] Actionable message for orphaned directories noted
- [ ] Example shows realistic table output

---

### Subtask T024 – Document `sync` Subcommand in CLI Reference

**Purpose**: Add reference documentation for `spec-kitty agent config sync` command.

**Steps**:

1. **Add subcommand header**:
   ```markdown
   #### spec-kitty agent config sync

   Synchronize filesystem with config.yaml.
   ```

2. **Add synopsis**:
   ```markdown
   **Synopsis**:
   ```bash
   spec-kitty agent config sync [OPTIONS]
   ```
   ```

3. **Add description**:
   ```markdown
   **Description**:

   Automatically aligns filesystem with `.kittify/config.yaml` by creating missing directories and/or removing orphaned directories.
   ```

4. **Add arguments** (none):
   ```markdown
   **Arguments**: None
   ```

5. **Add options** (extract from WP01 research T001):
   ```markdown
   **Options**:

   - `--create-missing`: Create directories for configured agents that are missing from filesystem (default: False)
   - `--remove-orphaned` / `--keep-orphaned`: Remove orphaned directories (directories present but not configured). Default: `--remove-orphaned` (True)

   **Default behavior** (no flags): Removes orphaned directories only. Does NOT create missing directories.
   ```

6. **Add output format**:
   ```markdown
   **Output**:

   - Creating: `✓ Created <agent-dir>/<subdir>/`
   - Removing: `✓ Removed orphaned <agent-dir>/`
   - No changes: `No changes needed - filesystem matches config`
   ```

7. **Add side effects**:
   ```markdown
   **Side Effects**:

   - Creates agent directories with slash command templates (if `--create-missing`)
   - Deletes orphaned agent directories (if `--remove-orphaned`, default)
   ```

8. **Add examples**:
   ```markdown
   **Examples**:

   Default sync (remove orphaned only):
   ```bash
   spec-kitty agent config sync
   ```

   Create missing configured agents:
   ```bash
   spec-kitty agent config sync --create-missing
   ```

   Complete sync (both directions):
   ```bash
   spec-kitty agent config sync --create-missing --remove-orphaned
   ```

   Keep orphaned directories:
   ```bash
   spec-kitty agent config sync --keep-orphaned
   ```

   Example output:
   ```
   ✓ Created .claude/commands/
   ✓ Removed orphaned .gemini/
   ```

   No changes needed:
   ```
   No changes needed - filesystem matches config
   ```
   ```

**Files**: `docs/reference/cli-commands.md`

**Parallel**: Yes (after T019, parallel with T020-T023)

**Notes**:
- Extract exact behavior from WP01 research T001 (lines 297-380)
- Clarify default behavior (remove orphaned, NOT create missing)
- Show flag combinations
- Include "no changes needed" scenario

**Validation**:
- [ ] Synopsis shows OPTIONS placeholder
- [ ] Description explains purpose
- [ ] Arguments section (none)
- [ ] Options documented (`--create-missing`, `--remove-orphaned`, `--keep-orphaned`)
- [ ] Default behavior clarified (remove orphaned only)
- [ ] Output format explained (creating, removing, no changes)
- [ ] Side effects listed
- [ ] Examples show default, create-missing, complete sync, keep-orphaned
- [ ] "No changes needed" scenario included

---

## Test Strategy

**Manual Validation**:

1. **Syntax Validation**:
   - Cross-reference all documented commands against WP01 research T001
   - Verify flags and defaults match source code
   - Check that `--help` output matches documented syntax

2. **Format Consistency**:
   - Compare format against existing cli-commands.md entries
   - Ensure all subcommands use same structure (synopsis, description, arguments, options, output, examples)
   - Verify formatting matches (headers, code blocks, tables)

3. **Example Execution**:
   - Run each example command in test project
   - Verify output matches documented examples
   - Check that errors trigger as documented

4. **Cross-Reference Validation**:
   - Verify link to manage-agents.md resolves
   - Ensure subcommand table accurately reflects all 5 commands
   - Confirm note about 0.12.0 config-driven model is accurate

## Risks & Mitigations

**Risk**: Format doesn't match existing CLI reference style
- **Mitigation**: Review existing cli-commands.md before writing; copy structure exactly
- **Detection**: Side-by-side comparison during review

**Risk**: Documented syntax doesn't match actual CLI behavior
- **Mitigation**: Extract exact syntax from WP01 research T001; verify against `--help` output
- **Validation**: Run commands manually to confirm

**Risk**: Examples too abstract or don't demonstrate key features
- **Mitigation**: Use realistic agent selections (claude, codex common); show error handling
- **Validation**: Test each example to ensure it works

**Risk**: Content exceeds 500 lines (too verbose for reference)
- **Mitigation**: Keep examples concise; use tables for structured information
- **Detection**: Check line count after completion

## Review Guidance

**Acceptance Checkpoints**:
- [ ] All six subtasks (T019-T024) completed
- [ ] Main section inserted into cli-commands.md
- [ ] All 5 subcommands documented: list, add, remove, status, sync
- [ ] Each subcommand includes: synopsis, description, arguments, options, output, examples
- [ ] Format matches existing CLI reference style
- [ ] Exact syntax matches WP01 research findings
- [ ] Cross-reference to manage-agents.md included
- [ ] Approximately 450 lines total (75 per subcommand + main section)

**Review Focus**:
- **Accuracy**: Does documented syntax match WP01 research and actual CLI behavior?
- **Completeness**: Are all flags, options, and error conditions documented?
- **Consistency**: Does format match existing cli-commands.md entries?
- **Usability**: Can developer find command syntax quickly?

**Success Indicator**: Developer consulting CLI reference can find complete command syntax, flags, defaults, and examples for all 5 agent config subcommands without needing to run `--help` or read source code.

## Activity Log

**Initial entry**:
- 2026-01-23T10:23:45Z – system – lane=planned – Prompt generated.

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP05 --to <lane> --note "message"` (recommended)

The CLI command updates both frontmatter and activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

---
- 2026-01-23T11:06:32Z – claude – shell_pid=28306 – lane=doing – Started implementation via workflow command
- 2026-01-23T11:08:19Z – claude – shell_pid=28306 – lane=for_review – Ready for review: Added complete CLI reference documentation for spec-kitty agent config command group. Documented all 5 subcommands (list, add, remove, status, sync) with synopsis, description, arguments, options, output format, and examples. Added main section with subcommand index and cross-reference to manage-agents how-to guide. 324 lines added following existing CLI reference format.
- 2026-01-23T11:15:46Z – Claude – shell_pid=38505 – lane=doing – Started review via workflow command
- 2026-01-23T11:15:46Z – Claude – shell_pid=38505 – lane=done – Review passed: Implementation complete

## Implementation Command

**Depends on WP01** - Ensure WP01 is complete before starting.

```bash
spec-kitty implement WP05 --base WP01
```

This WP is independent from WP02-WP04 (can run in parallel). After WP05 completes, WP06 can reference this CLI documentation.
