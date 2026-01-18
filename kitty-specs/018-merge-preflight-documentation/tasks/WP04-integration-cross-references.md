---
work_package_id: "WP04"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
title: "Integration & Cross-References"
phase: "Phase 3 - Polish"
lane: "doing"
dependencies: ["WP01", "WP02", "WP03"]
assignee: ""
agent: "claude"
shell_pid: "88047"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-18T13:21:55Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Integration & Cross-References

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-18

**Issue 1**: Required guide `docs/how-to/merge-feature.md` is missing. Create the file and complete all sections per WP01 subtasks (flags, pre-flight validation, dry-run example, merge strategies, cleanup options) and ensure style matches `docs/how-to/accept-and-merge.md`.


## ⚠️ Dependency Rebase Guidance

**This WP depends on**: WP01, WP02, WP03

Ensure all dependencies are complete before starting. If WP01-WP03 change after you start:
```bash
# Check for updates to dependent WPs
git log --oneline main..HEAD
```

---

## Objectives & Success Criteria

Integrate new documentation into the site structure and add cross-references between docs.

**Success Criteria:**
- New pages appear in docs navigation (toc.yml)
- All internal links work correctly
- Existing docs link to new merge guides where appropriate
- All command examples are copy-pasteable and functional
- Style is consistent across all documentation

## Context & Constraints

**Files to Modify:**
- `docs/toc.yml` - Add new pages to navigation
- `docs/how-to/merge-feature.md` - Add cross-references (from WP01)
- `docs/how-to/troubleshoot-merge.md` - Add cross-references (from WP02)
- `docs/how-to/accept-and-merge.md` - Update to link to new guides

**Style Reference:** Existing cross-reference patterns in docs/how-to/

## Subtasks & Detailed Guidance

### Subtask T025 – Update toc.yml
- **Purpose**: Add new pages to site navigation
- **Steps**:
  1. Read `docs/toc.yml` to understand structure
  2. Find "how-to" section
  3. Add entries for new pages:
     ```yaml
     - name: How to Merge a Feature
       href: how-to/merge-feature.md
     - name: How to Troubleshoot Merge Issues
       href: how-to/troubleshoot-merge.md
     ```
  4. Place entries logically (near accept-and-merge.md)
- **Files**: `docs/toc.yml`
- **Parallel?**: Yes

### Subtask T026 – Add cross-references to merge-feature.md
- **Purpose**: Connect merge guide to related docs
- **Steps**:
  1. Add "Troubleshooting" section with link to troubleshoot-merge.md
  2. Add standard footer sections:
     - **Command Reference**: Link to CLI reference
     - **See Also**: Link to accept-and-merge.md, workspace-per-wp.md
     - **Background**: Link to explanation docs
     - **Getting Started**: Link to tutorials
- **Files**: `docs/how-to/merge-feature.md`
- **Parallel?**: Yes

### Subtask T027 – Add cross-references to troubleshoot-merge.md
- **Purpose**: Connect troubleshooting guide to related docs
- **Steps**:
  1. Add standard footer sections:
     - **Command Reference**: Link to CLI reference
     - **See Also**: Link to merge-feature.md, accept-and-merge.md
     - **Background**: Link to workspace-per-wp explanation
     - **Getting Started**: Link to tutorials
  2. Link back to merge-feature.md from appropriate sections
- **Files**: `docs/how-to/troubleshoot-merge.md`
- **Parallel?**: Yes

### Subtask T028 – Update accept-and-merge.md links
- **Purpose**: Connect existing doc to new guides
- **Steps**:
  1. Read `docs/how-to/accept-and-merge.md`
  2. In "Merge to Main" section, add reference to merge-feature.md for detailed merge options
  3. In "Troubleshooting" section, add reference to troubleshoot-merge.md
  4. Update "See Also" section to include new guides
- **Files**: `docs/how-to/accept-and-merge.md`
- **Parallel?**: Yes

### Subtask T029 – Verify command examples
- **Purpose**: Ensure all examples work
- **Steps**:
  1. Extract all code blocks from merge-feature.md and troubleshoot-merge.md
  2. For each command example:
     - Run in terminal
     - Verify output matches documentation
     - Fix any discrepancies
  3. Focus on:
     - `spec-kitty merge` variants
     - `spec-kitty merge --dry-run`
     - `spec-kitty merge --resume`
     - `spec-kitty merge --abort`
- **Files**: All new documentation files
- **Parallel?**: No (needs WP01, WP02 content complete)

### Subtask T030 – Final style consistency check
- **Purpose**: Ensure uniform documentation style
- **Steps**:
  1. Compare each new doc section against accept-and-merge.md
  2. Check:
     - Heading levels (## for main sections, ### for subsections)
     - Code block formatting (bash for terminal, text for agent commands)
     - List formatting (bullet vs numbered)
     - Section order (Prerequisites, main content, Troubleshooting, Command Reference, See Also, Background, Getting Started)
  3. Fix any inconsistencies
- **Files**: All new documentation files
- **Parallel?**: No (needs all content complete)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Broken links | Use relative paths, test with local docfx build |
| toc.yml syntax error | Validate YAML before committing |
| Command examples outdated | Test each command in terminal |

## Definition of Done Checklist

- [ ] All subtasks completed
- [ ] `docs/toc.yml` updated with new pages
- [ ] merge-feature.md has cross-references
- [ ] troubleshoot-merge.md has cross-references
- [ ] accept-and-merge.md links to new guides
- [ ] All command examples tested and working
- [ ] Style consistent across all docs
- [ ] All internal links resolve correctly

## Review Guidance

1. Click every link in new docs to verify they work
2. Check toc.yml renders correctly (new pages appear in nav)
3. Test 3+ command examples from docs
4. Compare section structure against accept-and-merge.md

## Activity Log

- 2026-01-18T13:21:55Z – system – lane=planned – Prompt created.
- 2026-01-18T13:35:30Z – codex – shell_pid=73212 – lane=doing – Started review via workflow command
- 2026-01-18T13:36:09Z – codex – shell_pid=73212 – lane=planned – Moved to planned
- 2026-01-18T13:49:02Z – claude – shell_pid=88047 – lane=doing – Started implementation via workflow command
