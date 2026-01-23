---
work_package_id: WP04
title: Migration Guide for 0.12.0
lane: "doing"
dependencies:
- WP01
- WP02
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Core Documentation
assignee: ''
agent: "Claude"
shell_pid: "42078"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-23T10:23:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Migration Guide for 0.12.0

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
- Config schema from WP01 research (T002)
- Understanding of config-driven model

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

**Goal**: Provide 0.11.x → 0.12.0 upgrade guidance explaining config-driven agent management for existing users.

**Success Criteria**:
- [ ] Migration content created (section or separate file, based on content length)
- [ ] "What Changed" section explains migration behavior change (recreating deleted dirs → respecting config)
- [ ] "Why This Change" section explains benefits (user control, predictable behavior)
- [ ] Step-by-step migration workflow (5 steps with commands)
- [ ] Migration troubleshooting subsection covers common issues
- [ ] Content is under 500 words (SC-002 requirement)
- [ ] Links to ADR #6 for architectural details
- [ ] Cross-references manage-agents.md for command details

**Independent Test**: Existing 0.11.x users can follow migration steps to remove unwanted agents and verify they stay deleted after upgrade.

## Context & Constraints

**Purpose**: Address User Story 2 - existing users upgrading to 0.12.0 need to understand new config-driven agent management. This satisfies FR-004 and FR-005.

**Reference Documents**:
- `architecture/adrs/2026-01-23-6-config-driven-agent-management.md` (ADR #6 - source of migration rationale)
- WP01 research findings (config schema, agent mappings)
- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/spec.md` (requirements FR-004, FR-005)

**Writing Style**:
- Upgrade-focused (speak to 0.11.x users)
- Explain "before vs after" behavior clearly
- Provide actionable steps (not just concepts)
- Keep concise (under 500 words total per SC-002)

**Decision Point (T015)**: If migration content exceeds 500 words, create separate file `upgrade-to-0-12-0.md`. Otherwise, add section to existing `upgrade-to-0-11-0.md`.

**Constraints**:
- T014 can start immediately (read ADR #6)
- T015-T018 sequential after T014 completes
- Keep total content under 500 words (concise upgrade guidance)
- Link to ADR #6 for architectural deep-dive

## Subtasks & Detailed Guidance

### Subtask T014 – Read ADR #6 for Migration Content Extraction

**Purpose**: Extract key points from ADR #6 to inform migration guide content.

**Steps**:

1. **Open ADR #6**:
   - File: `architecture/adrs/2026-01-23-6-config-driven-agent-management.md`
   - Read in full, focusing on:
     - **Problem statement**: Why did migrations recreate deleted directories?
     - **Decision**: config.yaml as single source of truth
     - **Consequences**: User workflow changes, migration behavior changes

2. **Extract key migration points**:
   - **Before 0.12.0**: Migrations processed all 12 agents regardless of user intent
   - **After 0.12.0**: Migrations respect `config.yaml` - only process configured agents
   - **User impact**: Manually deleted agent directories no longer recreated on upgrade
   - **New workflow**: Use `spec-kitty agent config remove` instead of manual deletion

3. **Identify migration steps** from ADR:
   - Step 1: Check current agent configuration
   - Step 2: Remove unwanted agents via CLI (not manual deletion)
   - Step 3: Verify filesystem matches config
   - Step 4: Upgrade to 0.12.0
   - Step 5: Confirm migrations respected config

4. **Note troubleshooting scenarios** mentioned in ADR:
   - Orphaned directories (present but not configured)
   - Missing directories (configured but not present)
   - Corrupt config.yaml (falls back to all 12 agents)

5. **Document findings** in working notes for use in T015-T018

**Files**: None (read-only research)

**Parallel**: Yes (can start immediately, independent)

**Notes**:
- ADR #6 is authoritative source for migration rationale
- Focus on user-facing behavior changes (not internal implementation)
- Extract concrete examples if ADR provides them

**Validation**:
- [ ] ADR #6 read in full
- [ ] Problem statement extracted (why change was needed)
- [ ] Decision extracted (config.yaml as single source)
- [ ] User workflow changes identified
- [ ] Migration steps outlined
- [ ] Troubleshooting scenarios noted

---

### Subtask T015 – Create 0.12.0 Migration Section

**Purpose**: Decide on file location and create migration content structure.

**Steps**:

1. **Check existing upgrade guide**:
   ```bash
   wc -w docs/how-to/upgrade-to-0-11-0.md
   ```
   Check file length and structure

2. **Make decision**:
   - **If upgrade-to-0-11-0.md has multiple version sections**: Add new section "## Upgrading to 0.12.0" in that file
   - **If upgrade-to-0-11-0.md is specific to 0.11.0 only**: Create new file `docs/how-to/upgrade-to-0-12-0.md`
   - **Decision criteria**: If migration content will exceed 500 words, create separate file for clarity

3. **Create structure** (assuming separate file for this example):

   **File**: `docs/how-to/upgrade-to-0-12-0.md`

   ```markdown
   # Upgrading to 0.12.0

   This guide covers breaking changes and migration steps for spec-kitty 0.11.x users upgrading to 0.12.0.

   ## Overview

   Version 0.12.0 introduces config-driven agent management, changing how migrations handle agent directories. This upgrade guide explains what changed, why, and how to prepare for a smooth upgrade.

   **Key change**: Migrations now respect `.kittify/config.yaml` when processing agent directories. Agents not listed in `config.yaml` are no longer recreated during upgrades.

   ## What You Need to Do

   If you previously manually deleted agent directories, you MUST use `spec-kitty agent config remove` before upgrading. Otherwise, deleted directories will persist as "orphaned" (present but not configured).

   See sections below for details.
   ```

   **OR** (if adding to existing file):

   **File**: `docs/how-to/upgrade-to-0-11-0.md`

   Add at end of file:
   ```markdown
   ---

   ## Upgrading to 0.12.0

   [Same content as above]
   ```

4. **Add table of contents** (if separate file):
   ```markdown
   ## Contents

   - [What Changed](#what-changed)
   - [Why This Change](#why-this-change)
   - [Migration Steps](#migration-steps)
   - [Troubleshooting](#troubleshooting)
   - [See Also](#see-also)
   ```

**Files**: Either `docs/how-to/upgrade-to-0-12-0.md` (new) or `docs/how-to/upgrade-to-0-11-0.md` (append section)

**Parallel**: No (sequential after T014)

**Notes**:
- Check existing file structure before deciding
- Separate file is cleaner if content is substantial
- Ensure consistent formatting with existing upgrade guides

**Validation**:
- [ ] File location decided (new file or section in existing)
- [ ] Structure created with overview and table of contents
- [ ] Key change highlighted upfront
- [ ] User action required stated clearly

---

### Subtask T016 – Write "What Changed" and "Why This Change" Explanations

**Purpose**: Explain behavior change and rationale in user-friendly terms.

**Steps**:

1. **Write "What Changed" section**:
   ```markdown
   ## What Changed

   ### Before 0.12.0: Migrations Recreated Deleted Directories

   In spec-kitty 0.11.x and earlier, running `spec-kitty upgrade` processed all 12 agent directories regardless of whether you used them. If you manually deleted `.gemini/` or `.cursor/`, migrations would recreate these directories on the next upgrade.

   **Problem**: Users lost control over agent configuration. Manually deleting unwanted agents was a temporary fix that didn't persist across upgrades.

   ### After 0.12.0: Migrations Respect config.yaml

   Starting in 0.12.0, `.kittify/config.yaml` is the single source of truth for agent configuration. The `agents.available` field lists active agents:

   ```yaml
   agents:
     available:
       - claude
       - codex
       - opencode
   ```

   Migrations now:
   - **Only process agents listed in `config.yaml`**
   - **Ignore agents not in the list** (no directory recreation)
   - **Respect user configuration choices**

   **Benefit**: Agents you remove stay removed across upgrades. Configuration is predictable and user-controlled.
   ```

2. **Write "Why This Change" section**:
   ```markdown
   ## Why This Change

   ### User Pain Point

   Multiple users reported frustration with migrations recreating unwanted agent directories. The old behavior assumed all users wanted all 12 agents, which was rarely true.

   ### Solution: Config-Driven Model

   The config-driven model gives users explicit control:
   - **Declare your agents**: List only the agents you use in `config.yaml`
   - **Persist your choices**: Migrations honor your configuration
   - **Avoid surprises**: No unexpected directory recreation

   ### Architectural Decision

   This change is documented in [ADR #6: Config-Driven Agent Management](../../architecture/adrs/2026-01-23-6-config-driven-agent-management.md). Key points:

   - **Single source of truth**: `config.yaml` replaces implicit "all agents" assumption
   - **Migration safety**: Migrations use `get_agent_dirs_for_project()` helper (config-aware)
   - **Backward compatibility**: Projects without `config.yaml` fall back to all 12 agents (legacy behavior)

   For technical details, see the ADR.
   ```

**Files**: Migration guide file (from T015)

**Parallel**: No (sequential after T015)

**Notes**:
- Use "before vs after" framing for clarity
- Explain user benefit (control, predictability)
- Link to ADR #6 for architectural deep-dive
- Keep language accessible (not overly technical)

**Validation**:
- [ ] "What Changed" section explains before/after behavior
- [ ] Problem statement included (recreating deleted dirs)
- [ ] Solution explained (config.yaml as single source)
- [ ] "Why This Change" section explains rationale
- [ ] User pain point acknowledged
- [ ] Benefits stated clearly
- [ ] ADR #6 linked for technical details

---

### Subtask T017 – Write Step-by-Step Migration Workflow

**Purpose**: Provide concrete migration steps with commands for 0.11.x users.

**Steps**:

1. **Write "Migration Steps" section header**:
   ```markdown
   ## Migration Steps

   Follow these steps to migrate from 0.11.x to 0.12.0 cleanly:
   ```

2. **Step 1: Check Current Configuration**:
   ```markdown
   ### Step 1: Check Current Agent Configuration

   Before upgrading, see which agents you actually use:

   ```bash
   # List configured agents (if already on 0.12.0-dev)
   spec-kitty agent config list

   # Or check filesystem manually
   ls -d .*/  # Lists all agent directories
   ```

   Identify agents you don't use. Common candidates for removal: `gemini`, `cursor`, `qwen`, `windsurf`.
   ```

3. **Step 2: Remove Unwanted Agents Properly**:
   ```markdown
   ### Step 2: Remove Unwanted Agents (0.11.x Users)

   **IMPORTANT**: Do NOT manually delete directories. Use the proper command:

   ```bash
   # Remove agents you don't use
   spec-kitty agent config remove gemini cursor qwen
   ```

   **What this does**:
   - Deletes agent directories
   - Updates `.kittify/config.yaml` to exclude removed agents
   - Ensures migrations respect your choices

   **If you already manually deleted directories**: They may be recreated on upgrade. After upgrading to 0.12.0, run `spec-kitty agent config sync --remove-orphaned` to clean up.
   ```

4. **Step 3: Verify Filesystem Matches Config**:
   ```markdown
   ### Step 3: Verify Configuration Sync

   Check that your filesystem matches your intended configuration:

   ```bash
   spec-kitty agent config status
   ```

   **Expected output**:
   - Configured agents show green "OK" status
   - Unwanted agents show dim "Not used" status (not "Orphaned")

   **If you see "Orphaned"**: Run `spec-kitty agent config sync --remove-orphaned` to clean up.
   ```

5. **Step 4: Upgrade to 0.12.0**:
   ```markdown
   ### Step 4: Upgrade spec-kitty

   Now upgrade to 0.12.0:

   ```bash
   pip install --upgrade spec-kitty-cli
   spec-kitty --version  # Verify 0.12.0 or later
   ```

   Run migrations (automatically triggered on first command, or manually):

   ```bash
   spec-kitty upgrade
   ```

   Migrations will respect your `config.yaml` and skip agents you removed.
   ```

6. **Step 5: Confirm Migration Success**:
   ```markdown
   ### Step 5: Confirm Migrations Respected Configuration

   After upgrade, verify agents you removed stayed deleted:

   ```bash
   spec-kitty agent config status
   ```

   **Expected behavior**:
   - Removed agents show "Not used" status (no directories)
   - Configured agents show "OK" status (directories present)

   **If unwanted directories reappeared**: You may have skipped Step 2. Remove them now:

   ```bash
   spec-kitty agent config remove <unwanted-agents>
   ```
   ```

**Files**: Migration guide file (from T015)

**Parallel**: No (sequential after T016)

**Notes**:
- Emphasize proper removal workflow (not manual deletion)
- Provide fallback for users who already manually deleted
- Include verification steps after each action
- Use realistic agent examples (gemini, cursor common candidates)

**Validation**:
- [ ] Five migration steps documented
- [ ] Step 1: Check current configuration
- [ ] Step 2: Remove unwanted agents via CLI (not manual deletion)
- [ ] Step 3: Verify filesystem sync
- [ ] Step 4: Upgrade to 0.12.0
- [ ] Step 5: Confirm success
- [ ] Each step includes commands and expected output
- [ ] Fallback guidance for manual deletions provided

---

### Subtask T018 – Add Migration Troubleshooting Subsection

**Purpose**: Cover common migration issues and solutions.

**Steps**:

1. **Add "Troubleshooting" section header**:
   ```markdown
   ## Troubleshooting

   Common issues during 0.11.x → 0.12.0 migration:
   ```

2. **Issue 1: Orphaned Directories After Upgrade**:
   ```markdown
   ### Orphaned Directories After Upgrade

   **Problem**: After upgrading to 0.12.0, you see directories for agents you manually deleted in 0.11.x.

   **Cause**: You manually deleted directories without using `spec-kitty agent config remove` before upgrading. Migrations recreated them because they were still in legacy configuration.

   **Solution**:
   ```bash
   # Check status
   spec-kitty agent config status

   # Remove orphaned directories
   spec-kitty agent config sync --remove-orphaned
   ```

   **Prevention**: Always use `spec-kitty agent config remove` instead of manual deletion.
   ```

3. **Issue 2: Missing Configured Agents**:
   ```markdown
   ### Missing Configured Agents After Upgrade

   **Problem**: Agents you use are missing after upgrade.

   **Cause**: Agents were accidentally removed from `config.yaml` or directories were deleted.

   **Solution**:
   ```bash
   # Restore missing agents
   spec-kitty agent config sync --create-missing
   ```

   **If specific agents missing**: Add them explicitly:
   ```bash
   spec-kitty agent config add claude codex
   ```
   ```

4. **Issue 3: All 12 Agents Still Active**:
   ```markdown
   ### All 12 Agents Still Active After Upgrade

   **Problem**: After upgrading to 0.12.0, all 12 agents are still configured.

   **Cause**: You didn't remove unwanted agents before upgrading. Legacy projects default to all 12 agents for backward compatibility.

   **Solution**: Remove unwanted agents now:
   ```bash
   spec-kitty agent config remove gemini cursor qwen windsurf kilocode roo
   # Keep only agents you use
   ```
   ```

5. **Issue 4: Corrupt config.yaml**:
   ```markdown
   ### Corrupt config.yaml After Upgrade

   **Problem**: `spec-kitty` commands fail with YAML parsing errors.

   **Cause**: Upgrade or manual edit corrupted `.kittify/config.yaml`.

   **Solution**: Recreate config with desired agents:
   ```bash
   # Back up corrupt file
   cp .kittify/config.yaml .kittify/config.yaml.backup

   # Recreate by adding agents
   spec-kitty agent config add claude codex opencode
   # This recreates config.yaml with only specified agents
   ```
   ```

6. **Add "Still Having Issues?" note**:
   ```markdown
   ### Still Having Issues?

   - Review [Managing AI Agents](manage-agents.md) for detailed agent config commands
   - Consult [ADR #6](../../architecture/adrs/2026-01-23-6-config-driven-agent-management.md) for architectural context
   - Report upgrade bugs at [spec-kitty GitHub Issues](https://github.com/yourusername/spec-kitty/issues)
   ```

**Files**: Migration guide file (from T015)

**Parallel**: No (sequential after T017)

**Notes**:
- Focus on issues specific to migration (not general agent management)
- Provide quick solutions (not lengthy explanations)
- Link to manage-agents.md for detailed command guidance
- Keep concise (troubleshooting adds to 500-word limit)

**Validation**:
- [ ] Troubleshooting section added
- [ ] Issue 1: Orphaned directories after upgrade
- [ ] Issue 2: Missing configured agents
- [ ] Issue 3: All 12 agents still active
- [ ] Issue 4: Corrupt config.yaml
- [ ] Each issue includes cause and solution
- [ ] "Still Having Issues?" note with external links
- [ ] Total migration guide content under 500 words (check word count)

---

## Test Strategy

**Manual Validation**:

1. **Migration Workflow Testing**:
   - Simulate 0.11.x environment (manually delete agent directories)
   - Follow migration steps (T017) exactly as written
   - Verify deleted agents stay deleted after upgrade
   - Check that configured agents are preserved

2. **Troubleshooting Validation**:
   - Simulate each troubleshooting scenario
   - Verify documented solutions resolve issues
   - Confirm commands and expected outputs match reality

3. **Content Review**:
   - Verify content under 500 words (SC-002 requirement)
   - Ensure ADR #6 is linked correctly
   - Check cross-references to manage-agents.md resolve
   - Confirm tone is appropriate for existing users (not newcomers)

4. **Accuracy Check**:
   - Cross-reference ADR #6 for migration rationale
   - Verify behavior changes match actual 0.12.0 implementation
   - Confirm fallback behavior (legacy projects → all 12 agents)

## Risks & Mitigations

**Risk**: Migration steps don't match actual upgrade behavior
- **Mitigation**: Extract migration logic from ADR #6 (authoritative source)
- **Validation**: Test migration workflow in 0.11.x → 0.12.0 upgrade scenario

**Risk**: Content exceeds 500 words (SC-002 violation)
- **Mitigation**: Write concisely; link to ADR #6 and manage-agents.md for details
- **Detection**: Run `wc -w` on final file

**Risk**: Users skip Step 2 (removing agents properly)
- **Mitigation**: Emphasize "IMPORTANT" callouts and provide fallback guidance
- **Validation**: Include troubleshooting for orphaned directories (Issue 1)

**Risk**: Migration guide contradicts manage-agents.md
- **Mitigation**: Reference manage-agents.md for command details (don't duplicate)
- **Cross-check**: Ensure command syntax matches between guides

## Review Guidance

**Acceptance Checkpoints**:
- [ ] Migration content created (separate file or section in existing file)
- [ ] All five subtasks (T014-T018) completed
- [ ] "What Changed" section explains before/after behavior
- [ ] "Why This Change" section explains rationale
- [ ] Five-step migration workflow documented
- [ ] Troubleshooting section covers 4+ common issues
- [ ] Content is under 500 words (SC-002)
- [ ] ADR #6 linked for architectural details
- [ ] manage-agents.md cross-referenced for command details
- [ ] Tone appropriate for existing 0.11.x users

**Review Focus**:
- **Clarity**: Can 0.11.x user understand what changed and why?
- **Actionability**: Can user follow migration steps without confusion?
- **Completeness**: Are common migration issues covered?
- **Conciseness**: Is content under 500 words while remaining useful?

**Success Indicator**: Existing 0.11.x user can follow migration steps to remove unwanted agents and verify they stay deleted after upgrading to 0.12.0, without encountering unexpected directory recreation.

## Activity Log

**Initial entry**:
- 2026-01-23T10:23:45Z – system – lane=planned – Prompt generated.

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP04 --to <lane> --note "message"` (recommended)

The CLI command updates both frontmatter and activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

---
- 2026-01-23T11:01:43Z – claude – shell_pid=20855 – lane=doing – Started implementation via workflow command
- 2026-01-23T11:18:18Z – claude – shell_pid=20855 – lane=for_review – Ready for review: Migration guide for 0.12.0 config-driven agent management. Step-by-step upgrade workflow covering removal of unwanted agents before upgrade, verification, optional sync, and adding new agents. Includes troubleshooting section for common scenarios.
- 2026-01-23T11:19:52Z – Claude – shell_pid=42078 – lane=doing – Started review via workflow command

## Implementation Command

**Depends on WP01** - Ensure WP01 is complete before starting.

```bash
spec-kitty implement WP04 --base WP01
```

This WP is independent from WP02/WP03 (can run in parallel).
