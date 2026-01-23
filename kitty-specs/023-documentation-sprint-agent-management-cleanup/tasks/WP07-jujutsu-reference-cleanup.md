---
work_package_id: "WP07"
subtasks:
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
title: "Jujutsu Reference Cleanup"
phase: "Phase 3 - Cleanup"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "33676"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-23T10:23:45Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Jujutsu Reference Cleanup

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

This is an independent cleanup work package that can start immediately.

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

**Goal**: Remove all jujutsu/jj references from documentation and fix broken links to deleted jj files.

**Success Criteria**:
- [ ] Zero jujutsu/jj references in `docs/` directory (SC-005 requirement)
- [ ] All internal links resolve to existing files (SC-003 requirement)
- [ ] VCS detection documentation reflects git-only behavior
- [ ] No broken links to deleted jj files (auto-rebase-and-conflicts.md, jujutsu-for-multi-agent.md, etc.)
- [ ] `docs/reference/cli-commands.md` init section updated to remove jj priority mentions

**Independent Test**: `grep -r "jujutsu|jj\s" docs/` returns zero matches (SC-005), and all internal links resolve (SC-003).

## Context & Constraints

**Purpose**: Clean up documentation after jujutsu support removal (commit 99b0d84). This addresses FR-010, FR-011, FR-012, and success criteria SC-003, SC-005.

**Reference Documents**:
- `/kitty-specs/023-documentation-sprint-agent-management-cleanup/spec.md` (requirements FR-010 through FR-012)
- Git commit 99b0d84 (jujutsu removal commit)

**Background**:
- Jujutsu (jj) support was removed in commit 99b0d84
- Five jj-specific documentation files were deleted:
  - `docs/explanation/auto-rebase-and-conflicts.md`
  - `docs/explanation/jujutsu-for-multi-agent.md`
  - `docs/how-to/handle-conflicts-jj.md`
  - `docs/how-to/use-operation-history.md`
  - `docs/tutorials/jujutsu-workflow.md`
- Remaining documentation may still reference jj or link to deleted files

**Writing Style**:
- Surgical removals (don't rewrite large sections)
- Update VCS references to git-only
- Remove or replace broken links to deleted jj files
- Don't introduce new git-specific content unless necessary for clarity

**Constraints**:
- T029 sequential (audit first)
- T030 sequential after T029 (CLI commands update)
- T031-T033 can be parallelized (different doc sections)
- Keep changes minimal (only remove jj references, don't refactor)

## Subtasks & Detailed Guidance

### Subtask T029 – Run Grep Audit for Jujutsu/jj References

**Purpose**: Identify all remaining jujutsu/jj references in documentation.

**Steps**:

1. **Run comprehensive grep command**:
   ```bash
   cd /Users/robert/Code/spec-kitty
   grep -r "jujutsu\|jj\s\|\.jj" docs/ | grep -v ".jj/" | grep -v "jjust"
   ```

   **Pattern explanation**:
   - `jujutsu`: Full product name
   - `jj\s`: Command name followed by space (avoids false positives like "jjust")
   - `\.jj`: File extensions or directory references (e.g., `.jj/`)
   - Exclude `.jj/` directory references (not relevant)
   - Exclude "jjust" (false positive)

2. **Document findings**:
   - List all files with matches
   - Note line numbers and context
   - Categorize by fix type:
     - **Remove reference**: Delete sentence/paragraph mentioning jj
     - **Update reference**: Change "jj/git" to "git"
     - **Fix link**: Remove or replace link to deleted jj file

3. **Expected result**: Zero matches (cleanup in commit 99b0d84 should have removed all)

4. **If matches found**:
   - List files for T030-T033
   - Prioritize by doc type:
     - **Priority 1**: Reference docs (cli-commands.md) - users consult frequently
     - **Priority 2**: How-to guides - task-oriented, users follow step-by-step
     - **Priority 3**: Tutorials and explanations - learning-oriented, less critical

5. **Document in working notes** for use in T030-T033

**Files**: None (audit only)

**Parallel**: No (must complete first to inform T030-T033)

**Notes**:
- If zero matches found, T030-T033 are no-ops (verify and document)
- If matches found, provide specific file/line/context for each fix
- Use grep exit code to determine if any matches exist

**Validation**:
- [ ] Grep command run with correct pattern
- [ ] All matches documented (file, line, context)
- [ ] Matches categorized by fix type
- [ ] Zero matches expected (based on commit 99b0d84)

---

### Subtask T030 – Update CLI Commands Init Section - Remove jj VCS Detection

**Purpose**: Remove jujutsu priority mentions from VCS detection documentation.

**Steps**:

1. **Open file**: `docs/reference/cli-commands.md`

2. **Locate `spec-kitty init` section**:
   - Find description of `--ai` option and VCS detection

3. **Identify jj references**:
   - Look for text like "jj preferred if available"
   - Look for VCS detection order mentioning jj
   - Look for examples showing jj initialization

4. **Update VCS detection explanation**:

   **Before** (example):
   ```markdown
   VCS detection order: jj (preferred), git (fallback)
   ```

   **After**:
   ```markdown
   VCS: Initializes git repository if not already present
   ```

5. **Remove jj-specific examples**:

   **Before** (example):
   ```bash
   # Initialize with jj VCS
   spec-kitty init --ai claude
   ```

   **After**:
   ```bash
   # Initialize with git VCS
   spec-kitty init --ai claude
   ```

6. **Update VCS option documentation** (if present):

   **Before** (example):
   ```markdown
   --vcs [git|jj]: Specify version control system (default: jj if available, otherwise git)
   ```

   **After**:
   ```markdown
   --vcs git: Specify version control system (default: git)
   ```

7. **Verify no other jj mentions** in init documentation:
   - Check for references to "jujutsu workflow"
   - Check for links to deleted jj tutorial files

**Files**: `docs/reference/cli-commands.md`

**Parallel**: No (sequential after T029)

**Notes**:
- Update to reflect git-only behavior
- Remove any jj priority or preference language
- Keep changes minimal (surgical removals)
- If no jj references found in T029, this is a verification-only task

**Validation**:
- [ ] VCS detection order updated to git-only
- [ ] jj examples removed or updated to git
- [ ] VCS option documentation updated (if present)
- [ ] No remaining jj mentions in init section
- [ ] Changes reflect actual implementation (git-only)

---

### Subtask T031 – Fix Broken jj Links in How-To Guides

**Purpose**: Remove or replace links to deleted jj how-to files.

**Steps**:

1. **Identify files to check**:
   - `docs/how-to/*.md` (all how-to guides)
   - Common candidates:
     - `docs/how-to/handle-conflicts.md` (might link to handle-conflicts-jj.md)
     - `docs/how-to/getting-started.md` (might reference jj workflow)

2. **Search for links to deleted jj files**:
   ```bash
   cd docs/how-to
   grep -r "handle-conflicts-jj\|use-operation-history\|jujutsu-workflow" .
   ```

3. **For each broken link found**:

   **Option 1: Remove link and reference** (if jj-specific content):
   ```markdown
   Before: See [Handling Conflicts in Jujutsu](handle-conflicts-jj.md) for jj-specific workflow.
   After: (entire sentence removed)
   ```

   **Option 2: Replace with git equivalent** (if parallel git content exists):
   ```markdown
   Before: See [Handling Conflicts](handle-conflicts-jj.md) for conflict resolution.
   After: See [Handling Conflicts](handle-conflicts.md) for conflict resolution.
   ```

   **Option 3: Generalize reference** (if concept applies to git):
   ```markdown
   Before: Use jj's operation history to undo changes. See [Operation History](use-operation-history.md).
   After: Use git reflog to undo changes.
   ```

4. **Check for orphaned jj workflows**:
   - Remove any "Jujutsu Workflow" sections
   - Remove callouts like "🔧 Jujutsu users: see..."
   - Remove comparisons like "jj vs git for multi-agent workflows"

5. **Document all changes** for review:
   - List each file modified
   - Note what was removed/replaced
   - Verify remaining content still makes sense

**Files**: Various `docs/how-to/*.md` files

**Parallel**: Yes (after T030, parallel with T032-T033)

**Notes**:
- Prioritize removal over replacement (jj is gone, don't force git substitutes)
- If parallel git content doesn't exist, remove reference entirely
- Ensure remaining paragraphs flow naturally after deletions

**Validation**:
- [ ] All how-to guides checked for jj links
- [ ] Broken links to deleted jj files removed or replaced
- [ ] No orphaned jj workflow sections remain
- [ ] Remaining content flows naturally after edits
- [ ] grep confirms zero matches for deleted file names

---

### Subtask T032 – Fix Broken jj Links in Tutorials

**Purpose**: Remove or replace links to deleted jj tutorial files.

**Steps**:

1. **Identify files to check**:
   - `docs/tutorials/*.md` (all tutorials)
   - Common candidates:
     - `docs/tutorials/getting-started.md` (might reference jujutsu-workflow.md)
     - `docs/tutorials/first-feature.md` (might link to jj conflict handling)

2. **Search for links to deleted jj files**:
   ```bash
   cd docs/tutorials
   grep -r "jujutsu-workflow\|jujutsu-for-multi-agent\|auto-rebase-and-conflicts" .
   ```

3. **For each broken link found**:

   **Remove tutorial references to jj**:
   ```markdown
   Before: For advanced workflows, see the [Jujutsu Workflow Tutorial](jujutsu-workflow.md).
   After: (sentence removed, or replaced with git-specific tutorial if available)
   ```

4. **Remove jj-specific tutorial steps**:
   - If tutorial has "Option 1: Git" and "Option 2: Jujutsu" sections, remove Option 2
   - If tutorial is entirely jj-focused, consider removing entire tutorial (check with spec FR-011)

5. **Update tutorial navigation**:
   - Remove links to jujutsu-workflow.md from tutorial index pages
   - Update "Next Steps" sections that reference jj tutorials

**Files**: Various `docs/tutorials/*.md` files

**Parallel**: Yes (after T030, parallel with T031, T033)

**Notes**:
- Tutorials are learning-oriented, so removal is usually better than awkward substitution
- If tutorial assumes jj features (auto-rebase), entire section may need removal
- Check for tutorial index pages that list jj tutorials

**Validation**:
- [ ] All tutorials checked for jj links
- [ ] Broken links to deleted jj files removed
- [ ] jj-specific tutorial steps removed
- [ ] Tutorial navigation updated (no dead links in indexes)
- [ ] Remaining tutorials don't assume jj features

---

### Subtask T033 – Fix Broken jj Links in Explanation Articles

**Purpose**: Remove or replace links to deleted jj explanation files.

**Steps**:

1. **Identify files to check**:
   - `docs/explanation/*.md` (all explanation articles)
   - Common candidates:
     - `docs/explanation/multi-agent-workflows.md` (might reference jujutsu-for-multi-agent.md)
     - `docs/explanation/conflict-resolution.md` (might link to auto-rebase-and-conflicts.md)

2. **Search for links to deleted jj files**:
   ```bash
   cd docs/explanation
   grep -r "jujutsu-for-multi-agent\|auto-rebase-and-conflicts" .
   ```

3. **For each broken link found**:

   **Remove jj-specific explanations**:
   ```markdown
   Before: Jujutsu's automatic rebasing simplifies multi-agent workflows. See [Jujutsu for Multi-Agent](jujutsu-for-multi-agent.md) for details.
   After: (sentence removed, or replaced with git-based explanation if relevant)
   ```

4. **Update architectural explanations**:
   - Remove comparisons like "Why jj is better for multi-agent"
   - Remove jj-specific architecture diagrams or callouts
   - Update to git-only context

5. **Check for cross-references from other explanation articles**:
   - Ensure no circular references to deleted jj explanations
   - Update "See Also" sections that list jj articles

**Files**: Various `docs/explanation/*.md` files

**Parallel**: Yes (after T030, parallel with T031-T032)

**Notes**:
- Explanation articles are understanding-oriented, focus on concepts
- If jj concept doesn't translate to git, remove rather than force analogy
- Check for diagrams or visuals referencing jj

**Validation**:
- [ ] All explanation articles checked for jj links
- [ ] Broken links to deleted jj files removed
- [ ] jj-specific explanations removed or updated to git
- [ ] No cross-references to deleted jj explanation articles
- [ ] Remaining explanations are git-focused or VCS-agnostic

---

## Test Strategy

**Manual Validation**:

1. **Grep Validation** (SC-005):
   ```bash
   cd /Users/robert/Code/spec-kitty
   grep -r "jujutsu\|jj\s\|\.jj" docs/ | grep -v ".jj/" | grep -v "jjust"
   ```
   Expected: Zero matches

2. **Link Resolution** (SC-003):
   - Use link checker tool or manual inspection
   - Verify no broken links to:
     - `auto-rebase-and-conflicts.md`
     - `jujutsu-for-multi-agent.md`
     - `handle-conflicts-jj.md`
     - `use-operation-history.md`
     - `jujutsu-workflow.md`
   - Expected: All links resolve to existing files

3. **Content Flow**:
   - Read modified files in full
   - Ensure paragraphs flow naturally after deletions
   - Check that removed references don't leave orphaned content

4. **VCS Documentation Accuracy**:
   - Verify init documentation reflects git-only behavior
   - Check that no jj priority or preference language remains

## Risks & Mitigations

**Risk**: Grep audit finds zero matches (cleanup already complete)
- **Mitigation**: Verify and document as no-op; T030-T033 become verification-only
- **Action**: Confirm commit 99b0d84 removed all jj references; update WP status

**Risk**: Removing jj references leaves awkward or incomplete content
- **Mitigation**: Read surrounding paragraphs; ensure natural flow after edits
- **Validation**: Manual review of modified files

**Risk**: Missing broken links (grep doesn't catch all link formats)
- **Mitigation**: Manual inspection of common link locations (See Also, Next Steps sections)
- **Detection**: Use link checker tool if available

**Risk**: Removing jj explanations makes multi-agent workflow docs less clear
- **Mitigation**: Only remove jj-specific content; preserve VCS-agnostic concepts
- **Validation**: Ensure remaining explanations are understandable

## Review Guidance

**Acceptance Checkpoints**:
- [ ] All five subtasks (T029-T033) completed
- [ ] Grep audit run and findings documented
- [ ] CLI commands init section updated (VCS detection git-only)
- [ ] All how-to guides checked and fixed (T031)
- [ ] All tutorials checked and fixed (T032)
- [ ] All explanation articles checked and fixed (T033)
- [ ] Zero jujutsu/jj references in docs/ directory (SC-005)
- [ ] All internal links resolve (SC-003)
- [ ] Modified files read for natural content flow

**Review Focus**:
- **Completeness**: Are all jj references removed?
- **Accuracy**: Does VCS documentation reflect git-only behavior?
- **Link Resolution**: Do all internal links work?
- **Content Quality**: Do modified files still read naturally?

**Success Indicator**: `grep -r "jujutsu|jj\s" docs/` returns zero matches (SC-005), all internal links resolve (SC-003), and documentation accurately reflects git-only implementation.

## Activity Log

**Initial entry**:
- 2026-01-23T10:23:45Z – system – lane=planned – Prompt generated.

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP07 --to <lane> --note "message"` (recommended)

The CLI command updates both frontmatter and activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

---
- 2026-01-23T11:10:55Z – claude – shell_pid=33676 – lane=doing – Started implementation via workflow command

## Implementation Command

**No dependencies** - This is an independent work package.

```bash
spec-kitty implement WP07
```

Can run in parallel with WP02, WP04, WP05, WP08 (all independent after WP01 completes).
