---
work_package_id: "WP06"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "Cross-Reference Updates"
phase: "Phase 2 - Reference Documentation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02", "WP05"]
history:
  - timestamp: "2026-01-23T10:23:45Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Cross-Reference Updates

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

**This WP depends on WP02 and WP05** (check frontmatter `dependencies:` field).

Before starting, ensure both dependencies are complete:
- WP02 creates `docs/how-to/manage-agents.md` (link target)
- WP05 creates CLI reference section for `spec-kitty agent config` (link target)

**Check if dependencies are complete**:
```bash
spec-kitty agent tasks status --feature 023-documentation-sprint-agent-management-cleanup
```

Look for WP02 and WP05 in "done" lane. If not complete, wait or coordinate with those agents.

If this WP has dependent WPs (other WPs depend on this one): None - WP06 is a leaf node.

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

**Goal**: Add cross-references to agent config documentation from related pages (agent-subcommands, configuration, install guide, supported-agents) to improve discoverability.

**Success Criteria**:
- [ ] `docs/reference/agent-subcommands.md` updated with `config` entry in command index
- [ ] `docs/reference/configuration.md` updated with config-driven model section
- [ ] `docs/how-to/install-spec-kitty.md` updated with cross-reference to manage-agents
- [ ] `docs/reference/supported-agents.md` updated with cross-reference to manage-agents
- [ ] All cross-references use correct relative paths
- [ ] Links tested to ensure they resolve
- [ ] Agent config commands discoverable from at least 3 related pages (SC-006 requirement)

**Independent Test**: Agent config commands are discoverable via CLI help and referenced from at least 3 related documentation pages (SC-006).

## Context & Constraints

**Purpose**: Improve documentation discoverability by adding cross-references from related pages. This addresses FR-008 and FR-009 requirements and ensures SC-006 (3+ cross-references).

**Reference Documents**:
- WP02 output (`docs/how-to/manage-agents.md` - link target)
- WP05 output (`docs/reference/cli-commands.md#spec-kitty-agent-config` - link target)
- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/spec.md` (requirements FR-008, FR-009, SC-006)

**Writing Style**:
- Minimal additions (don't rewrite existing content)
- Add cross-reference notes/links in logical locations
- Use relative paths for links
- Ensure link text is descriptive

**Constraints**:
- T025 sequential (updates command index)
- T026-T028 can be parallelized (independent files)
- Each update should be 1-3 sentences plus link
- Verify all link paths resolve before committing

## Subtasks & Detailed Guidance

### Subtask T025 – Update agent-subcommands.md Command Index

**Purpose**: Add `config` subcommand to the agent subcommands index table.

**Steps**:

1. **Open file**: `docs/reference/agent-subcommands.md`

2. **Locate command index table**:
   - Find table listing agent subcommands (likely near top of file)
   - Table format: `| Command | Description |`

3. **Add row for `config` subcommand**:
   ```markdown
   | `config` | Manage project AI agent configuration (add, remove, list, sync agents) |
   ```

   Insert alphabetically if table is sorted, or at logical location.

4. **Add section for `config` details** (if file has detailed sections for each subcommand):
   ```markdown
   ### spec-kitty agent config

   Manage project AI agent configuration. This command family provides tools for adding, removing, listing, and syncing agents post-initialization.

   **Subcommands**: `list`, `add`, `remove`, `status`, `sync`

   **See**:
   - [CLI Reference: spec-kitty agent config](cli-commands.md#spec-kitty-agent-config) - Complete command syntax and options
   - [Managing AI Agents](../how-to/manage-agents.md) - Task-oriented guide for agent management workflows
   ```

5. **Verify table alignment**:
   - Ensure table formatting is consistent
   - Check that pipe characters align properly

**Files**: `docs/reference/agent-subcommands.md`

**Parallel**: No (single file, sequential)

**Notes**:
- Extract description from WP05 main section
- Add both table entry and detailed section (if file structure supports it)
- Link to both CLI reference (syntax) and how-to guide (workflow)

**Validation**:
- [ ] `config` row added to command index table
- [ ] Description matches WP05 main section
- [ ] Detailed section added (if file has per-command sections)
- [ ] Links to CLI reference and manage-agents.md included
- [ ] Table formatting consistent

---

### Subtask T026 – Update configuration.md with Config-Driven Model Section

**Purpose**: Add section explaining config-driven agent management in configuration reference.

**Steps**:

1. **Open file**: `docs/reference/configuration.md`

2. **Locate appropriate insertion point**:
   - Find section discussing `.kittify/config.yaml` structure
   - Insert after general config explanation, or create new section "Agent Configuration"

3. **Add section header**:
   ```markdown
   ## Agent Configuration

   Agent configuration is stored in `.kittify/config.yaml` under the `agents` key.
   ```

4. **Explain config-driven model**:
   ```markdown
   ### Config-Driven Agent Management

   Starting in spec-kitty 0.12.0, agent configuration follows a config-driven model where `.kittify/config.yaml` is the single source of truth for which agents are active in your project.

   **Key principles**:
   - Agent directories on filesystem (e.g., `.claude/commands/`) are derived from `config.yaml`
   - Migrations respect `config.yaml` - only process configured agents
   - Use `spec-kitty agent config` commands to manage agents (not manual editing)

   **Schema**:
   ```yaml
   agents:
     available:
       - claude
       - codex
       - opencode
     selection:
       strategy: preferred  # or "random"
       preferred_implementer: claude
       preferred_reviewer: codex
   ```

   **Fields**:
   - `available` (list): Agent keys currently active in project
   - `selection.strategy` (string): Agent selection strategy (`preferred` or `random`)
   - `selection.preferred_implementer` (string): Preferred agent for implementation tasks
   - `selection.preferred_reviewer` (string): Preferred agent for review tasks

   **See**:
   - [Managing AI Agents](../how-to/manage-agents.md) - Complete guide to agent management commands
   - [CLI Reference: spec-kitty agent config](cli-commands.md#spec-kitty-agent-config) - Command syntax and options
   - [ADR #6: Config-Driven Agent Management](../../architecture/adrs/2026-01-23-6-config-driven-agent-management.md) - Architectural decision rationale
   ```

5. **Add note about legacy behavior**:
   ```markdown
   > **Legacy behavior**: Projects without `agents.available` field default to all 12 agents for backward compatibility. To adopt config-driven model, use `spec-kitty agent config remove` to remove unwanted agents.
   ```

**Files**: `docs/reference/configuration.md`

**Parallel**: Yes (independent from T027 and T028)

**Notes**:
- Extract config schema from WP01 research T002
- Explain fields and values
- Link to manage-agents.md, CLI reference, and ADR #6
- Note about legacy fallback behavior

**Validation**:
- [ ] Section added to configuration.md
- [ ] Config-driven model explained
- [ ] Schema shown with YAML example
- [ ] All fields documented (`available`, `selection.strategy`, `preferred_*`)
- [ ] Links to manage-agents.md, CLI reference, ADR #6
- [ ] Legacy behavior note included

---

### Subtask T027 – Update install-spec-kitty.md Cross-Reference

**Purpose**: Add cross-reference to manage-agents.md in installation guide.

**Steps**:

1. **Open file**: `docs/how-to/install-spec-kitty.md`

2. **Locate appropriate insertion point**:
   - Find section discussing `spec-kitty init --ai` command
   - Likely near end of init examples or in "Next Steps" section

3. **Add cross-reference note**:
   ```markdown
   ### Managing Agents After Initialization

   After running `spec-kitty init`, you can add or remove agents at any time using the `spec-kitty agent config` command family.

   To manage agents post-init:
   - **Add agents**: `spec-kitty agent config add <agents>`
   - **Remove agents**: `spec-kitty agent config remove <agents>`
   - **Check status**: `spec-kitty agent config status`

   See [Managing AI Agents](manage-agents.md) for complete documentation on agent management workflows.
   ```

4. **Alternative (if simpler note preferred)**:
   ```markdown
   > **Managing agents after init**: To add or remove agents later, see [Managing AI Agents](manage-agents.md).
   ```

**Files**: `docs/how-to/install-spec-kitty.md`

**Parallel**: Yes (independent from T026 and T028)

**Notes**:
- Insert near init examples (logical progression from init to post-init management)
- Can be subsection or simple callout, depending on file structure
- Use relative path (same directory: `manage-agents.md`)

**Validation**:
- [ ] Cross-reference added after init examples
- [ ] Note mentions agent management is possible post-init
- [ ] Link to manage-agents.md included
- [ ] Relative path correct (`manage-agents.md`, not `../how-to/manage-agents.md`)

---

### Subtask T028 – Update supported-agents.md Cross-Reference

**Purpose**: Add cross-reference to manage-agents.md in supported agents reference.

**Steps**:

1. **Open file**: `docs/reference/supported-agents.md`

2. **Locate appropriate insertion point**:
   - Likely at the beginning (intro paragraph) or in a "Managing Agents" section

3. **Add intro paragraph with cross-reference**:
   ```markdown
   ## Managing Active Agents

   Spec-kitty supports 12 AI agents (listed below). You can activate or deactivate agents at any time using the `spec-kitty agent config` command family.

   To manage which agents are active in your project:
   - **View configured agents**: `spec-kitty agent config list`
   - **Add agents**: `spec-kitty agent config add <agents>`
   - **Remove agents**: `spec-kitty agent config remove <agents>`

   See [Managing AI Agents](../how-to/manage-agents.md) for complete documentation on agent management workflows.
   ```

4. **Or add simpler note** (if file already has intro):
   ```markdown
   > **Managing agents**: Use `spec-kitty agent config` commands to manage which agents are active in your project. See [Managing AI Agents](../how-to/manage-agents.md) for details.
   ```

5. **Update existing agent list** (if needed):
   - Ensure all 12 agents are listed
   - Add note about config-driven model: "Active agents are managed via `.kittify/config.yaml`"

**Files**: `docs/reference/supported-agents.md`

**Parallel**: Yes (independent from T026 and T027)

**Notes**:
- Insert at logical location (intro or dedicated section)
- Use relative path (`../how-to/manage-agents.md` from reference/ directory)
- Ensure agent list is complete (12 agents)

**Validation**:
- [ ] Cross-reference added to supported-agents.md
- [ ] Note explains agent management commands
- [ ] Link to manage-agents.md included
- [ ] Relative path correct (`../how-to/manage-agents.md`)
- [ ] Agent list is complete (12 agents) if file includes list

---

## Test Strategy

**Manual Validation**:

1. **Link Resolution**:
   - Click each added link in documentation
   - Verify links resolve to correct files and sections
   - Check relative paths work from each file's location

2. **Cross-Reference Coverage** (SC-006 validation):
   - Count pages referencing agent config documentation
   - Expected: 4 pages (agent-subcommands.md, configuration.md, install-spec-kitty.md, supported-agents.md)
   - Requirement: At least 3 pages (SC-006)

3. **Content Integration**:
   - Ensure added content flows naturally with existing text
   - Check that cross-references don't disrupt reading flow
   - Verify no duplicate information across pages

4. **Relative Path Validation**:
   - Verify paths from each file:
     - From `reference/` to `how-to/`: `../how-to/`
     - Within `how-to/`: no `../` needed
     - To `architecture/adrs/`: `../../architecture/adrs/`

## Risks & Mitigations

**Risk**: Broken links due to incorrect relative paths
- **Mitigation**: Test each link by clicking in documentation browser
- **Detection**: Manual link checking; future tooling could automate

**Risk**: Cross-references disrupt existing content flow
- **Mitigation**: Insert at logical locations (after related content, in "See Also" sections)
- **Validation**: Read surrounding paragraphs to ensure natural flow

**Risk**: Duplicate information across manage-agents.md and cross-reference locations
- **Mitigation**: Keep cross-references brief (1-3 sentences); link to manage-agents.md for details
- **Validation**: Compare cross-reference text against manage-agents.md to avoid duplication

**Risk**: Files don't exist or have moved
- **Mitigation**: Verify file existence before adding links
- **Detection**: Link resolution testing

## Review Guidance

**Acceptance Checkpoints**:
- [ ] All four subtasks (T025-T028) completed
- [ ] agent-subcommands.md updated with `config` entry
- [ ] configuration.md updated with config-driven model section
- [ ] install-spec-kitty.md updated with cross-reference
- [ ] supported-agents.md updated with cross-reference
- [ ] All relative paths correct and tested
- [ ] Agent config commands discoverable from 4 pages (exceeds SC-006 requirement of 3)
- [ ] Cross-references don't duplicate manage-agents.md content

**Review Focus**:
- **Discoverability**: Can user find agent config docs from related pages?
- **Link Accuracy**: Do all links resolve correctly?
- **Content Integration**: Do cross-references flow naturally?
- **Coverage**: Are at least 3 pages (SC-006) referencing agent config docs?

**Success Indicator**: User browsing any of the 4 updated pages (agent-subcommands, configuration, install-spec-kitty, supported-agents) can discover agent config documentation through cross-reference links.

## Activity Log

**Initial entry**:
- 2026-01-23T10:23:45Z – system – lane=planned – Prompt generated.

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP06 --to <lane> --note "message"` (recommended)

The CLI command updates both frontmatter and activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

---

## Implementation Command

**Depends on WP02 and WP05** - Ensure both are complete before starting.

```bash
# Branch from WP05 (assumes WP02 already merged into WP05's branch)
spec-kitty implement WP06 --base WP05

# If WP02 and WP05 are in separate branches, you'll need to merge WP02 first:
# cd .worktrees/023-documentation-sprint-WP06/
# git merge 023-documentation-sprint-WP02
```

After completing this WP, all cross-references are in place and agent config docs are discoverable.
