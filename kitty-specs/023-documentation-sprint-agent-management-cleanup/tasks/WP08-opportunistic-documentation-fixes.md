---
work_package_id: WP08
title: Opportunistic Documentation Fixes
lane: "done"
dependencies:
- WP01
subtasks:
- T034
- T035
- T036
phase: Phase 3 - Cleanup
assignee: ''
agent: "Claude"
shell_pid: "51920"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-01-23T10:23:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Opportunistic Documentation Fixes

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

**This WP has no dependencies** (check frontmatter `dependencies: []` field).

This is an independent cleanup work package that can start immediately. Loosely depends on WP01 for config schema reference, but can proceed without it.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

**Goal**: Fix obvious documentation-code mismatches discovered during validation (outdated command syntax, broken links, config examples).

**Success Criteria**:

- [ ] Documented commands match `--help` output (FR-013 requirement)
- [ ] Config examples match AgentConfig schema (FR-014 requirement)
- [ ] All internal documentation links resolve (FR-015 requirement)
- [ ] Obvious mismatches fixed (scope: only "easy wins", no comprehensive audit)
- [ ] Approximately 200 lines of changes

**Independent Test**: Documented commands match `--help` output, config examples match AgentConfig schema, and all internal links resolve.

## Context & Constraints

**Purpose**: Fix obvious documentation issues discovered during feature implementation. This addresses User Story 5 (FR-013 through FR-015) and improves overall documentation quality.

**Reference Documents**:

- WP01 research findings (for config schema reference, if available)
- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/spec.md` (requirements FR-013 through FR-015)

**Source Files for Validation** (read-only):

- `src/specify_cli/orchestrator/agent_config.py` (AgentConfig dataclass for config examples)
- `src/specify_cli/cli/commands/*.py` (command implementations for syntax validation)

**Scope Definition**:

- **"Obvious"**: Issues found through casual inspection, not deep audit
- **"Easy wins"**: Fixes that take < 5 minutes per issue
- **Out of scope**: Comprehensive documentation audit, major rewrites, new content
- **Examples of in-scope fixes**:
  - Command syntax typo (e.g., `spec-kitty agents list` → `spec-kitty agent config list`)
  - Config example with wrong field name (e.g., `agents.list` → `agents.available`)
  - Broken link to moved file (e.g., `../old-path.md` → `../new-path.md`)
- **Examples of out-of-scope fixes**:
  - Rewriting entire how-to guide for clarity
  - Adding missing documentation sections
  - Comprehensive link checker across all docs

**Writing Style**:

- Surgical fixes (change minimal text)
- Match existing doc style
- Don't introduce new content unless fixing omission

**Constraints**:

- All three subtasks can be parallelized (independent)
- Limit to 10-15 fixes total (scope control)
- Document all changes for review
- Keep under 200 lines total changes

## Subtasks & Detailed Guidance

### Subtask T034 – Validate Command Syntax in Tutorials Against Source Code

**Purpose**: Find and fix command syntax mismatches in tutorials (most user-facing).

**Steps**:

1. **Identify tutorials to check**:

   ```bash
   ls docs/tutorials/*.md
   ```

   Prioritize: `getting-started.md`, `first-feature.md`, `multi-agent-workflow.md` (if exists)

2. **Extract commands from each tutorial**:
   - Look for code blocks with bash/shell commands
   - List all `spec-kitty` commands found

3. **Validate against `--help` output**:

   ```bash
   # For each command found, check help
   spec-kitty <command> --help
   ```

   **Common mismatches**:
   - Renamed commands (e.g., old: `spec-kitty init --agents`, new: `spec-kitty init --ai`)
   - Renamed flags (e.g., old: `--agent-list`, new: `--ai`)
   - Deprecated commands (e.g., `spec-kitty agent add` → `spec-kitty agent config add`)
   - Wrong syntax (e.g., `spec-kitty specify` → `spec-kitty specify <feature>`)

4. **Fix command syntax**:

   **Example fix**:

   ```markdown
   Before:
   ```bash
   spec-kitty init --agents claude codex
   ```

   After:

   ```bash
   spec-kitty init --ai claude
   ```

5. **Validate flags and arguments**:
   - Check that documented flags exist
   - Verify argument order matches implementation
   - Confirm default values are correct

6. **Limit scope**:
   - Fix only tutorials (not all docs)
   - Fix only obvious mismatches (not edge cases)
   - Maximum 5-7 command fixes

7. **Document changes**:
   - List each file modified
   - Note old command → new command
   - Verify with `--help` output

**Files**: `docs/tutorials/*.md`

**Parallel**: Yes (independent from T035 and T036)

**Notes**:

- Focus on high-traffic tutorials (getting-started, first-feature)
- If unsure, run command to see actual behavior
- Don't fix commands that work but are "old style" (e.g., older flag names that still work)

**Validation**:

- [ ] Tutorials checked for command syntax
- [ ] Common mismatches identified (renamed commands, flags)
- [ ] Command syntax fixed to match `--help` output
- [ ] Changes limited to 5-7 obvious issues
- [ ] All fixed commands validated by running with `--help`

---

### Subtask T035 – Validate Config Examples Against AgentConfig Dataclass

**Purpose**: Find and fix config.yaml examples that don't match AgentConfig schema.

**Steps**:

1. **Extract AgentConfig schema** (from WP01 research T002, or directly from source):
   - File: `src/specify_cli/orchestrator/agent_config.py`
   - Dataclasses: `AgentConfig`, `AgentSelectionConfig`
   - Expected fields:

     ```python
     class AgentConfig:
         available: list[str]
         selection: AgentSelectionConfig

     class AgentSelectionConfig:
         strategy: SelectionStrategy  # PREFERRED or RANDOM
         preferred_implementer: str | None
         preferred_reviewer: str | None
     ```

2. **Find config examples in docs**:

   ```bash
   cd docs
   grep -r "agents:" . --include="*.md" -A 5
   ```

   This finds YAML blocks with `agents:` key

3. **Check each example against schema**:

   **Common mismatches**:
   - Wrong field names (e.g., `agents.list` instead of `agents.available`)
   - Wrong types (e.g., `strategy: "preferred"` instead of `strategy: preferred` - no quotes needed)
   - Missing required fields (e.g., `agents:` without `available`)
   - Invalid enum values (e.g., `strategy: auto` instead of `preferred` or `random`)

4. **Fix config examples**:

   **Example fix 1: Wrong field name**:

   ```yaml
   Before:
   agents:
     list:
       - claude

   After:
   agents:
     available:
       - claude
   ```

   **Example fix 2: Wrong enum value**:

   ```yaml
   Before:
   agents:
     selection:
       strategy: automatic

   After:
   agents:
     selection:
       strategy: preferred
   ```

   **Example fix 3: Missing structure**:

   ```yaml
   Before:
   agents:
     - claude
     - codex

   After:
   agents:
     available:
       - claude
       - codex
   ```

5. **Validate selection strategy values**:
   - Only two valid values: `preferred`, `random`
   - Case-sensitive (lowercase)
   - No quotes needed in YAML

6. **Limit scope**:
   - Fix only config.yaml examples (not all YAML in docs)
   - Fix only field name/type mismatches (not missing documentation)
   - Maximum 3-5 config example fixes

7. **Document changes**:
   - List each file modified
   - Note incorrect field → correct field
   - Verify against AgentConfig dataclass

**Files**: Various docs with config.yaml examples

**Parallel**: Yes (independent from T034 and T036)

**Notes**:

- Focus on high-visibility docs (configuration.md, getting-started.md)
- If unsure, check AgentConfig dataclass definition
- Don't add new config examples, only fix existing ones

**Validation**:

- [ ] Config examples found via grep
- [ ] Each example checked against AgentConfig schema
- [ ] Field names corrected (`available`, not `list`)
- [ ] Enum values corrected (`preferred`/`random` only)
- [ ] Structure corrected (nested `selection` object)
- [ ] Changes limited to 3-5 obvious issues

---

### Subtask T036 – Check and Fix Broken Internal Documentation Links

**Purpose**: Find and fix broken links within documentation.

**Steps**:

1. **Identify link-heavy documentation**:
   - Reference docs (high cross-reference density)
   - Index pages
   - "See Also" sections

2. **Manual link checking** (if no automated tool available):

   ```bash
   cd docs
   # Extract markdown links
   grep -r "\[.*\](.*.md)" . --include="*.md"
   ```

   This finds `[text](path.md)` style links

3. **Check common broken link patterns**:

   **Pattern 1: File moved**:

   ```markdown
   Before: [Config Guide](config.md)
   After: [Config Guide](../reference/configuration.md)
   ```

   **Pattern 2: File renamed**:

   ```markdown
   Before: [Agent Commands](agent-cmds.md)
   After: [Agent Commands](agent-subcommands.md)
   ```

   **Pattern 3: Incorrect relative path**:

   ```markdown
   Before: [Install](install-spec-kitty.md)  # from reference/ directory
   After: [Install](../how-to/install-spec-kitty.md)  # correct relative path
   ```

4. **Verify link targets exist**:

   ```bash
   # For each link found, check target file exists
   ls docs/path/to/target.md
   ```

5. **Fix broken links**:

   **Example fix 1: Update relative path**:

   ```markdown
   Before (from docs/reference/cli-commands.md):
   See [Managing Agents](manage-agents.md)

   After:
   See [Managing Agents](../how-to/manage-agents.md)
   ```

   **Example fix 2: Remove dead link**:

   ```markdown
   Before:
   For details, see [Advanced Topics](advanced.md).

   After:
   For details on advanced topics, consult the CLI reference.
   (link removed if target doesn't exist and no replacement available)
   ```

6. **Check anchor links** (if time permits):

   ```markdown
   [Command Syntax](cli-commands.md#spec-kitty-agent-config)
   ```

   Verify section `#spec-kitty-agent-config` exists in target file

7. **Limit scope**:
   - Check only high-traffic pages (reference docs, getting-started)
   - Fix only obviously broken links (target doesn't exist)
   - Don't do comprehensive link audit (out of scope)
   - Maximum 5-7 link fixes

8. **Document changes**:
   - List each file modified
   - Note broken link → fixed link
   - Verify target file exists

**Files**: Various docs with internal links

**Parallel**: Yes (independent from T034 and T035)

**Notes**:

- Focus on reference docs and index pages (highest link density)
- If link target doesn't exist and no replacement, remove link or generalize text
- Use relative paths (not absolute)
- Test fixed links by clicking in documentation browser

**Validation**:

- [ ] High-traffic docs checked for links
- [ ] Broken links identified (target file doesn't exist)
- [ ] Relative paths corrected
- [ ] Dead links removed or generalized
- [ ] Anchor links validated (section exists)
- [ ] Changes limited to 5-7 obvious issues

---

## Test Strategy

**Manual Validation**:

1. **Command Syntax Validation** (FR-013):
   - Run each fixed command with `--help`
   - Verify syntax matches documented examples
   - Check that flags and arguments work as documented

2. **Config Example Validation** (FR-014):
   - Compare each fixed config example against AgentConfig dataclass
   - Verify field names, types, enum values correct
   - Check structure (nested objects) matches schema

3. **Link Resolution** (FR-015):
   - Click each fixed link in documentation browser
   - Verify link resolves to correct file and section
   - Check that relative paths work from source file location

4. **Scope Control**:
   - Count total fixes across all three subtasks
   - Ensure total changes under 200 lines
   - Verify only "obvious" issues fixed (no deep audit work)

## Risks & Mitigations

**Risk**: Scope creep (finding too many issues, spending too much time)

- **Mitigation**: Strict limit of 10-15 fixes total; time-box to 1-2 hours
- **Action**: If more issues found, document for future work package

**Risk**: Fixing commands that are "old style" but still work

- **Mitigation**: Only fix commands that fail or produce errors; leave deprecated-but-working syntax
- **Validation**: Run command to verify it actually fails before fixing

**Risk**: Config examples have subtly wrong structure (hard to detect)

- **Mitigation**: Focus on obvious field name mismatches; defer complex schema issues
- **Validation**: Cross-reference WP01 research T002 or AgentConfig dataclass directly

**Risk**: Breaking working links with incorrect relative path fixes

- **Mitigation**: Verify target file exists before fixing; test link in browser
- **Validation**: Click link after fix to ensure it resolves

## Review Guidance

**Acceptance Checkpoints**:

- [ ] All three subtasks (T034-T036) completed
- [ ] Command syntax validated in tutorials (T034)
- [ ] Config examples validated against schema (T035)
- [ ] Internal links checked and fixed (T036)
- [ ] Total fixes: 10-15 issues (scope control)
- [ ] Changes under 200 lines
- [ ] Documented commands match `--help` output (FR-013)
- [ ] Config examples match AgentConfig schema (FR-014)
- [ ] Internal links resolve (FR-015)

**Review Focus**:

- **Accuracy**: Do fixed commands actually work?
- **Scope Control**: Were only "obvious" issues fixed?
- **Impact**: Are fixed issues user-facing (high priority)?
- **Regression**: Did fixes break anything else?

**Success Indicator**: User browsing documentation encounters accurate command syntax, valid config examples, and working internal links for the fixed issues. All fixes are verifiable via `--help` output, AgentConfig dataclass, and link resolution.

## Activity Log

**Initial entry**:

- 2026-01-23T10:23:45Z – system – lane=planned – Prompt generated.

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP08 --to <lane> --note "message"` (recommended)

The CLI command updates both frontmatter and activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

---

- 2026-01-23T11:27:22Z – claude – shell_pid=50727 – lane=doing – Started implementation via workflow command
- 2026-01-23T11:29:42Z – claude – shell_pid=50727 – lane=for_review – Completed opportunistic documentation fixes: (T034) Validated tutorial command syntax - all current; (T035) Fixed config.yaml example in configuration.md - removed unnecessary quotes from strategy/agent names; (T036) Fixed 2 broken links to deleted jj docs in cli-commands.md and configuration.md. Total: 3 fixes, <50 lines changed, well under scope limits.
- 2026-01-23T11:30:00Z – Claude – shell_pid=51920 – lane=doing – Started review via workflow command
- 2026-01-23T11:30:00Z – Claude – shell_pid=51920 – lane=done – Review passed: Implementation complete

## Implementation Command

**No dependencies** - This is an independent work package (loosely depends on WP01 for config schema, but can proceed without it).

```bash
spec-kitty implement WP08
```

Can run in parallel with WP02, WP04, WP05, WP07 (all independent after WP01 completes).

**Note**: Lowest priority (P3), so consider deferring if other WPs have higher urgency.
