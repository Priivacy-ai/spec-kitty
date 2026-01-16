---
work_package_id: WP09
title: Cross-References & Links
lane: "for_review"
dependencies:
- WP03
subtasks:
- T038
- T039
- T040
- T041
- T042
phase: Phase 2 - Polish
assignee: ''
agent: "__AGENT__"
shell_pid: "25767"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-16T16:16:58Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 – Cross-References & Links

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Add cross-references between all documentation files
- Ensure no broken internal links
- **Success**: Every doc has relevant cross-references, all links work

## Context & Constraints

- **Spec**: `kitty-specs/014-comprehensive-end-user-documentation/spec.md`
- **Plan**: `kitty-specs/014-comprehensive-end-user-documentation/plan.md`
- **Dependencies**: All content WPs must be complete (WP03-WP08)

### Cross-Reference Principles
- Each tutorial should link to related how-tos and reference docs
- Each how-to should link to related reference and explanations
- Each explanation should link back to tutorials and how-tos
- Use relative paths for internal links

## Subtasks & Detailed Guidance

### Subtask T038 – Add Cross-References to Tutorials
- **Purpose**: Connect tutorials to related practical guides
- **Steps**:
  1. For each tutorial in `docs/tutorials/`:
     - Add "Related How-To Guides" section
     - Add "Reference Documentation" section
     - Add "Learn More" section with explanations
  2. Example additions:
     ```markdown
     ## Related How-To Guides
     - [Create a Specification](../how-to/create-specification.md)
     - [Implement a Work Package](../how-to/implement-work-package.md)

     ## Reference
     - [CLI Commands](../reference/cli-commands.md)
     - [Slash Commands](../reference/slash-commands.md)

     ## Learn More
     - [Spec-Driven Development](../explanation/spec-driven-development.md)
     ```
- **Files**: All files in `docs/tutorials/`
- **Parallel?**: Yes

### Subtask T039 – Add Cross-References to How-To Guides
- **Purpose**: Connect how-tos to reference and conceptual content
- **Steps**:
  1. For each how-to in `docs/how-to/`:
     - Add "Command Reference" section linking to relevant commands
     - Add "See Also" section for related how-tos
     - Add "Background" section linking to explanations
  2. Example:
     ```markdown
     ## Command Reference
     - [`spec-kitty implement`](../reference/cli-commands.md#spec-kitty-implement)
     - [`/spec-kitty.implement`](../reference/slash-commands.md#spec-kittyimplement)

     ## See Also
     - [Handle Dependencies](handle-dependencies.md)
     - [Parallel Development](parallel-development.md)

     ## Background
     - [Git Worktrees Explained](../explanation/git-worktrees.md)
     - [Workspace-per-WP Model](../explanation/workspace-per-wp.md)
     ```
- **Files**: All files in `docs/how-to/`
- **Parallel?**: Yes

### Subtask T040 – Add Cross-References to Reference Docs
- **Purpose**: Connect reference docs to practical usage guides
- **Steps**:
  1. For each reference doc in `docs/reference/`:
     - Add "Getting Started" links to tutorials
     - Add "Practical Usage" links to how-tos
  2. Example in cli-commands.md:
     ```markdown
     ## spec-kitty implement
     ...
     **See Also**:
     - Tutorial: [Your First Feature](../tutorials/your-first-feature.md)
     - How-To: [Implement a Work Package](../how-to/implement-work-package.md)
     ```
- **Files**: All files in `docs/reference/`
- **Parallel?**: Yes

### Subtask T041 – Add Cross-References to Explanations
- **Purpose**: Connect conceptual content to practical guides
- **Steps**:
  1. For each explanation in `docs/explanation/`:
     - Add "Try It" section linking to tutorials
     - Add "How-To Guides" for practical application
     - Add "Reference" for detailed command info
  2. Example:
     ```markdown
     ## Try It
     - [Multi-Agent Workflow Tutorial](../tutorials/multi-agent-workflow.md)

     ## How-To Guides
     - [Parallel Development](../how-to/parallel-development.md)
     - [Handle Dependencies](../how-to/handle-dependencies.md)

     ## Reference
     - [File Structure](../reference/file-structure.md)
     ```
- **Files**: All files in `docs/explanation/`
- **Parallel?**: Yes

### Subtask T042 – Verify All Internal Links
- **Purpose**: Ensure no broken links in the documentation
- **Steps**:
  1. Use a link checker tool or manual verification
  2. Check all relative paths are correct
  3. Verify anchor links (e.g., `#spec-kitty-implement`) exist
  4. Fix any broken links found
  5. Options for verification:
     ```bash
     # Option 1: DocFX build (warns about missing files)
     docfx docs/docfx.json

     # Option 2: Grep for markdown links
     grep -r '\[.*\](.*\.md' docs/

     # Option 3: Use a link checker tool
     ```
- **Files**: All files in `docs/`
- **Parallel?**: No - run after T038-T041
- **Notes**: Important for user experience

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Broken links | Use DocFX build warnings |
| Missing cross-refs | Systematic review of each file |
| Circular references | Keep links hierarchical |

## Definition of Done Checklist

- [ ] T038: All tutorials have cross-references
- [ ] T039: All how-tos have cross-references
- [ ] T040: All reference docs have cross-references
- [ ] T041: All explanations have cross-references
- [ ] T042: All internal links verified working
- [ ] No broken links in DocFX build

## Review Guidance

- Check that cross-references are relevant (not just link spam)
- Verify relative paths are correct
- Test links by clicking through documentation

## Activity Log

- 2026-01-16T16:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-16T17:42:56Z – __AGENT__ – shell_pid=25767 – lane=doing – Started implementation via workflow command
- 2026-01-16T17:55:04Z – __AGENT__ – shell_pid=25767 – lane=for_review – Ready for review: added cross-references across tutorials/how-to/reference/explanations, fixed broken links, updated toc/index, verified internal links
