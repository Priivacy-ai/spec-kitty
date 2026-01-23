---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
title: "Manage Agents How-To Guide - Supplementary Content"
phase: "Phase 1 - Core Documentation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01", "WP02"]
history:
  - timestamp: "2026-01-23T10:23:45Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Manage Agents How-To Guide - Supplementary Content

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

**This WP depends on WP01 and WP02** (check frontmatter `dependencies:` field).

Before starting, ensure both dependencies are complete:
- WP01 provides agent mappings research (T003)
- WP02 creates the base `manage-agents.md` file

**Check if dependencies are complete**:
```bash
spec-kitty agent tasks status --feature 023-documentation-sprint-agent-management-cleanup
```

Look for WP01 and WP02 in "done" lane. If not complete, wait or coordinate with those agents.

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

**Goal**: Complete `docs/how-to/manage-agents.md` with agent directory mappings table, troubleshooting section, and cross-reference links.

**Success Criteria**:
- [ ] Agent directory mappings table added (12 agents, special cases highlighted)
- [ ] Troubleshooting section covers common issues (orphaned dirs, missing dirs, corrupt config)
- [ ] Cross-reference links added (ADR #6, CLI reference, supported agents)
- [ ] Guide is comprehensive and self-contained (users don't need external resources)
- [ ] Special cases (copilot, auggie, q) clearly identified in mappings table

**Independent Test**: Guide includes all 12 agent mappings with special cases highlighted, troubleshooting covers common issues, and cross-references link to relevant docs.

## Context & Constraints

**Purpose**: Add supplementary content to complete the how-to guide created in WP02. This addresses remaining requirements from FR-003 (config-driven model explanation with agent mappings).

**Reference Documents**:
- WP01 research findings (T003 - agent mappings with special cases)
- WP02 output (`docs/how-to/manage-agents.md` - base document)
- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/spec.md` (requirements)
- `architecture/adrs/2026-01-23-6-config-driven-agent-management.md` (ADR #6)

**Source Files for Validation** (read-only):
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` (AGENT_DIR_TO_KEY mapping)

**Writing Style**:
- Consistent with WP02 style (task-oriented, imperative)
- Reference documentation (mappings table) should be concise
- Troubleshooting should be solution-oriented

**Constraints**:
- Append to existing `manage-agents.md` (don't overwrite WP02 content)
- Keep supplementary content under 200 lines total
- All three subtasks can be completed in parallel (independent sections)

## Subtasks & Detailed Guidance

### Subtask T011 – Create Agent Directory Mappings Table

**Purpose**: Provide reference table showing all 12 agent keys, their directory paths, and special case notes.

**Steps**:

1. **Add section header** to `docs/how-to/manage-agents.md`:
   ```markdown
   ## Agent Directory Mappings

   The following table shows the mapping between agent keys (used in commands) and their filesystem directories:
   ```

2. **Create markdown table** (extract from WP01 research T003):
   ```markdown
   | Agent Key | Directory Path | Notes |
   |-----------|----------------|-------|
   | `claude` | `.claude/commands/` | Standard mapping |
   | `codex` | `.codex/prompts/` | Standard mapping |
   | `gemini` | `.gemini/commands/` | Standard mapping |
   | `cursor` | `.cursor/commands/` | Standard mapping |
   | `qwen` | `.qwen/commands/` | Standard mapping |
   | `opencode` | `.opencode/command/` | Singular "command" subdirectory |
   | `windsurf` | `.windsurf/workflows/` | Workflows instead of commands |
   | `kilocode` | `.kilocode/workflows/` | Workflows instead of commands |
   | `roo` | `.roo/commands/` | Standard mapping |
   | `copilot` | `.github/prompts/` | **Special**: GitHub Copilot uses `.github` directory |
   | `auggie` | `.augment/commands/` | **Special**: Key `auggie` maps to `.augment` directory |
   | `q` | `.amazonq/prompts/` | **Special**: Short key `q` maps to `.amazonq` directory |
   ```

3. **Add explanatory note for special cases**:
   ```markdown
   **Special Cases**:

   - **copilot**: GitHub Copilot uses the standard `.github/prompts/` directory (not `.copilot/`)
   - **auggie**: Config key `auggie` maps to `.augment/commands/` directory (Augment Code agent)
   - **q**: Minimal key `q` maps to `.amazonq/prompts/` directory (Amazon Q agent)

   For all standard agents, the agent key matches the directory name (e.g., `claude` → `.claude/`).
   ```

4. **Add subdirectory variation note**:
   ```markdown
   **Subdirectory Patterns**:

   - Most agents use `commands/` subdirectory (plural)
   - `opencode` uses `command/` (singular)
   - `codex`, `copilot`, `q` use `prompts/` subdirectory
   - `windsurf` and `kilocode` use `workflows/` subdirectory

   These variations are handled automatically by spec-kitty commands - you don't need to memorize them.
   ```

5. **Add usage note**:
   ```markdown
   > **When to reference this table**: Use agent keys (left column) in commands like `spec-kitty agent config add claude codex`. The directory paths (middle column) show where templates are stored, but you shouldn't need to interact with these directories directly.
   ```

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: Yes (independent from T012 and T013)

**Notes**:
- Extract exact mappings from WP01 research T003
- Highlight special cases visually (bold text)
- Explain subdirectory variations for user awareness
- Emphasize that users interact via keys, not directories

**Validation**:
- [ ] Table includes all 12 agents
- [ ] Special cases (copilot, auggie, q) highlighted
- [ ] Subdirectory variations explained
- [ ] Usage note clarifies when to reference table
- [ ] Mappings match AGENT_DIR_TO_KEY from m_0_9_1_complete_lane_migration.py

---

### Subtask T012 – Write Troubleshooting Section

**Purpose**: Document common issues and solutions for agent management.

**Steps**:

1. **Add section header** to `docs/how-to/manage-agents.md`:
   ```markdown
   ## Troubleshooting

   This section covers common issues you may encounter when managing agents.
   ```

2. **Document orphaned directories issue**:
   ```markdown
   ### Orphaned Agent Directories

   **Problem**: You see directories like `.gemini/` on filesystem, but the agent is not configured in `.kittify/config.yaml`.

   **Cause**: Agent was manually deleted from config.yaml, or directory was created manually.

   **Solution**:
   ```bash
   # Option 1: Remove orphaned directory
   spec-kitty agent config sync --remove-orphaned

   # Option 2: Add to configuration to keep it
   spec-kitty agent config add gemini
   ```

   **Detection**: Run `spec-kitty agent config status` - orphaned agents show red "Orphaned" status.
   ```

3. **Document missing directories issue**:
   ```markdown
   ### Missing Configured Agent Directories

   **Problem**: Agent is listed in `.kittify/config.yaml` but directory doesn't exist.

   **Cause**: Directory was manually deleted, or filesystem corruption.

   **Solution**:
   ```bash
   # Option 1: Restore missing directory
   spec-kitty agent config sync --create-missing

   # Option 2: Remove from configuration if you don't use it
   spec-kitty agent config remove gemini
   ```

   **Detection**: Run `spec-kitty agent config status` - missing agents show yellow "Missing" status.
   ```

4. **Document corrupt config.yaml issue**:
   ```markdown
   ### Corrupt or Missing config.yaml

   **Problem**: `.kittify/config.yaml` is missing, unreadable, or has invalid YAML syntax.

   **Symptoms**: Commands fail with YAML parsing errors, or all 12 agents are treated as configured (legacy fallback).

   **Solution**:
   ```bash
   # Check current config structure
   cat .kittify/config.yaml

   # If corrupt or missing, recreate with desired agents
   spec-kitty agent config add claude codex opencode
   # This recreates config.yaml with only specified agents
   ```

   **Prevention**: Don't manually edit `.kittify/config.yaml` - use `spec-kitty agent config` commands instead.
   ```

5. **Document "command not found" issue**:
   ```markdown
   ### "spec-kitty: command not found"

   **Problem**: Terminal doesn't recognize `spec-kitty` command.

   **Cause**: spec-kitty is not installed or not in PATH.

   **Solution**: Ensure spec-kitty is installed via `pip install spec-kitty-cli` and your shell's PATH includes Python package binaries.

   **Not a configuration issue**: This is an installation problem. See [Installation Guide](install-spec-kitty.md).
   ```

6. **Document "Invalid agent keys" error**:
   ```markdown
   ### "Invalid agent keys" Error

   **Problem**: You get an error like "Invalid agent keys: cluade" when running `add` or `remove`.

   **Cause**: Typo in agent key name.

   **Solution**: Check the error message for the list of valid agent keys, and correct your command:
   ```bash
   # Error message shows:
   # Valid agent keys:
   #   claude, codex, gemini, cursor, qwen, opencode,
   #   windsurf, kilocode, roo, copilot, auggie, q

   # Fix typo and retry
   spec-kitty agent config add claude  # Not "cluade"
   ```

   **Reference**: See [Agent Directory Mappings](#agent-directory-mappings) table for complete list.
   ```

7. **Add "Still Stuck?" note**:
   ```markdown
   ### Still Stuck?

   If your issue isn't covered here:

   1. Check [Supported AI Agents](../reference/supported-agents.md) for agent-specific requirements
   2. Review [Configuration Reference](../reference/configuration.md) for config.yaml schema
   3. Consult [CLI Commands Reference](../reference/cli-commands.md#spec-kitty-agent-config) for detailed command syntax
   4. Report bugs at [spec-kitty GitHub Issues](https://github.com/yourusername/spec-kitty/issues)
   ```

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: Yes (independent from T011 and T013)

**Notes**:
- Focus on common issues users actually encounter
- Provide both detection and solution steps
- Link to relevant sections for more context
- Keep solutions concise and actionable

**Validation**:
- [ ] Orphaned directories issue documented
- [ ] Missing directories issue documented
- [ ] Corrupt config.yaml issue documented
- [ ] "command not found" issue documented
- [ ] "Invalid agent keys" error documented
- [ ] "Still Stuck?" section with external links

---

### Subtask T013 – Add Cross-Reference Links

**Purpose**: Link to related documentation for deeper exploration of agent management topics.

**Steps**:

1. **Add "See Also" section** at end of `docs/how-to/manage-agents.md`:
   ```markdown
   ## See Also

   For more information on agent management and related topics:
   ```

2. **Link to CLI commands reference** (FR-009 requirement):
   ```markdown
   ### Command Reference

   - [CLI Commands: spec-kitty agent config](../reference/cli-commands.md#spec-kitty-agent-config) - Detailed command syntax, flags, and options for all agent config subcommands
   ```

3. **Link to supported agents reference**:
   ```markdown
   ### Supported Agents

   - [Supported AI Agents](../reference/supported-agents.md) - Complete list of 12 supported agents with capabilities, installation requirements, and usage notes
   ```

4. **Link to configuration reference**:
   ```markdown
   ### Configuration

   - [Configuration Reference](../reference/configuration.md) - Complete `.kittify/config.yaml` schema including agent selection strategies (preferred vs random)
   ```

5. **Link to ADR #6** (architectural context):
   ```markdown
   ### Architecture

   - [ADR #6: Config-Driven Agent Management](../../architecture/adrs/2026-01-23-6-config-driven-agent-management.md) - Architectural decision record explaining why migrations now respect `config.yaml` and the config-driven model rationale
   ```

6. **Link to migration guide**:
   ```markdown
   ### Migration Guides

   - [Upgrading to 0.12.0](upgrade-to-0-11-0.md#upgrading-to-0120) - Migration guide for 0.11.x users transitioning to config-driven agent management
   ```

7. **Link to init documentation** (for initial agent selection):
   ```markdown
   ### Initial Setup

   - [Installing spec-kitty](install-spec-kitty.md) - Initial agent selection during `spec-kitty init`
   ```

8. **Add navigation note** at top of document (after overview, before first section):
   ```markdown
   ---

   **Quick Navigation**: [Listing Agents](#listing-agents) | [Adding Agents](#adding-agents) | [Removing Agents](#removing-agents) | [Checking Status](#checking-agent-status) | [Synchronizing](#synchronizing-filesystem) | [Troubleshooting](#troubleshooting) | [See Also](#see-also)

   ---
   ```

**Files**: `docs/how-to/manage-agents.md`

**Parallel**: Yes (independent from T011 and T012)

**Notes**:
- Use relative paths for cross-references
- Ensure all linked files exist (check with WP06)
- Add brief description for each link (explain what user will find)
- Include both reference docs and conceptual docs

**Validation**:
- [ ] "See Also" section added at end of document
- [ ] Link to CLI commands reference (cli-commands.md)
- [ ] Link to supported agents reference (supported-agents.md)
- [ ] Link to configuration reference (configuration.md)
- [ ] Link to ADR #6 (architecture/adrs/)
- [ ] Link to migration guide (upgrade-to-0-11-0.md or upgrade-to-0-12-0.md)
- [ ] Link to init documentation (install-spec-kitty.md)
- [ ] Quick navigation added at top of document
- [ ] All relative paths use correct directory structure

---

## Test Strategy

**Manual Validation**:

1. **Mappings Table Validation**:
   - Cross-reference table against WP01 research T003
   - Verify special cases (copilot, auggie, q) are highlighted
   - Confirm all 12 agents included

2. **Troubleshooting Validation**:
   - Simulate each issue in test project
   - Verify documented solutions work
   - Check that error messages match actual CLI output

3. **Cross-Reference Validation**:
   - Click each "See Also" link
   - Verify linked files exist at specified paths
   - Confirm linked sections exist (e.g., `#spec-kitty-agent-config` anchor)

4. **Integration Check**:
   - Read entire `manage-agents.md` from start to finish
   - Ensure supplementary content flows naturally after WP02 core content
   - Verify no duplicate sections or conflicting information

## Risks & Mitigations

**Risk**: Mappings table out of sync with source code
- **Mitigation**: Extract exact mappings from WP01 research T003 (which extracted from m_0_9_1_complete_lane_migration.py)
- **Detection**: Compare table against `AGENT_DIR_TO_KEY` constant

**Risk**: Troubleshooting solutions don't work
- **Mitigation**: Test each solution in a real project before documenting
- **Validation**: Simulate issues (orphaned dirs, missing dirs) and verify solutions

**Risk**: Cross-reference links broken (files don't exist or moved)
- **Mitigation**: Verify link targets exist; WP06 will add cross-references from other files (two-way linking)
- **Detection**: Manual link checking; future tooling could automate

**Risk**: Supplementary content overlaps with WP02 core content
- **Mitigation**: Review WP02 output before starting; ensure T011-T013 add new information only
- **Validation**: Read full document to check for duplication

## Review Guidance

**Acceptance Checkpoints**:
- [ ] Agent directory mappings table added with all 12 agents
- [ ] Special cases (copilot, auggie, q) highlighted in table
- [ ] Subdirectory variations explained
- [ ] Troubleshooting section covers 5+ common issues
- [ ] Each troubleshooting issue includes detection and solution steps
- [ ] "See Also" section with 7+ cross-reference links
- [ ] Quick navigation added for long document
- [ ] All three subtasks (T011-T013) completed
- [ ] Content integrates naturally with WP02 core content
- [ ] No duplicate information from WP02

**Review Focus**:
- **Completeness**: Are all 12 agents in mappings table? Are common issues covered?
- **Accuracy**: Do mappings match WP01 research? Do solutions actually work?
- **Usability**: Can user find information quickly via navigation and cross-references?
- **Integration**: Does supplementary content complement (not duplicate) WP02 core content?

**Success Indicator**: A user encountering an agent management issue can find the answer in troubleshooting section, or follow cross-references to find more details in reference documentation.

## Activity Log

**Initial entry**:
- 2026-01-23T10:23:45Z – system – lane=planned – Prompt generated.

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP03 --to <lane> --note "message"` (recommended)

The CLI command updates both frontmatter and activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

---

## Implementation Command

**Depends on WP01 and WP02** - Ensure both are complete before starting.

```bash
spec-kitty implement WP03 --base WP02
```

After completing this WP, manage-agents.md is complete (WP02 + WP03).
