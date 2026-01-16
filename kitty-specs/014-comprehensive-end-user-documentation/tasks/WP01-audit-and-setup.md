---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Audit & Directory Setup"
phase: "Phase 0 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "19353"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-16T16:16:58Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Audit & Directory Setup

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Audit all existing documentation in `docs/` directory
- Create Divio 4-type directory structure
- Remove outdated and out-of-scope documentation
- Migrate salvageable content to appropriate locations
- **Success**: Directory structure exists, outdated docs removed, audit documented

## Context & Constraints

- **Spec**: `kitty-specs/014-comprehensive-end-user-documentation/spec.md`
- **Plan**: `kitty-specs/014-comprehensive-end-user-documentation/plan.md`
- **Research/Audit**: `kitty-specs/014-comprehensive-end-user-documentation/research.md`
- **Target Audience**: End users only (not contributors)

### Key Decisions from Research
- **Preserve**: installation.md, workspace-per-wp.md, upgrading-to-0-11-0.md, documentation-mission.md
- **Remove**: testing-guidelines.md, local-development.md, releases/readiness-checklist.md (contributor docs)
- **Rewrite**: index.md, quickstart.md (outdated)

## Subtasks & Detailed Guidance

### Subtask T001 – Audit Existing Documentation
- **Purpose**: Document current state of all docs for migration decisions
- **Steps**:
  1. List all files in `docs/` directory
  2. For each file, assess:
     - Accuracy: ✅ Accurate, ⚠️ Outdated, ❌ Wrong
     - Divio Type: Tutorial, How-To, Reference, or Explanation
     - Salvageable content: What paragraphs/sections are worth keeping?
  3. Document findings (can update research.md or create audit-results.md)
- **Files**: `docs/**/*.md`
- **Parallel?**: No - must complete before other subtasks
- **Notes**: Use research.md findings as starting point

### Subtask T002 – Create Divio Directory Structure
- **Purpose**: Establish the 4-type documentation organization
- **Steps**:
  1. Create `docs/tutorials/` directory
  2. Create `docs/how-to/` directory
  3. Create `docs/reference/` directory
  4. Create `docs/explanation/` directory
  5. Add `.gitkeep` or placeholder README in each
- **Files**:
  - `docs/tutorials/`
  - `docs/how-to/`
  - `docs/reference/`
  - `docs/explanation/`
- **Parallel?**: Yes - can run alongside T003, T004
- **Notes**: Simple directory creation

### Subtask T003 – Remove Outdated/Out-of-Scope Docs
- **Purpose**: Clean up docs that don't belong in end-user documentation
- **Steps**:
  1. Remove contributor documentation:
     - `docs/testing-guidelines.md`
     - `docs/local-development.md`
     - `docs/releases/readiness-checklist.md`
  2. Remove outdated model docs (if not being migrated):
     - `docs/WORKTREE_MODEL.md` (replaced by workspace-per-wp.md)
  3. Do NOT remove yet:
     - `docs/index.md` (will be rewritten in WP02)
     - `docs/quickstart.md` (content may be salvaged)
- **Files**: See list above
- **Parallel?**: Yes - can run alongside T002, T004
- **Notes**: Git commit removals with clear message

### Subtask T004 – Migrate Salvageable Content
- **Purpose**: Move good content to appropriate Divio locations
- **Steps**:
  1. Move `docs/workspace-per-wp.md` → `docs/explanation/workspace-per-wp.md`
  2. Move `docs/upgrading-to-0-11-0.md` → `docs/how-to/upgrade-to-0-11-0.md`
  3. Move `docs/documentation-mission.md` → `docs/explanation/documentation-mission.md`
  4. Review `docs/installation.md` - keep in place or move to `docs/how-to/`
  5. Extract any good content from `docs/quickstart.md` for tutorials
- **Files**: See migration list above
- **Parallel?**: Yes - can run alongside T002, T003
- **Notes**: Update any internal links in migrated files

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Accidentally delete valuable content | Verify against research.md before deletion |
| Break existing links | Track all moves for link updates in WP09 |
| Miss files in audit | Use `find docs -name "*.md"` to ensure complete |

## Definition of Done Checklist

- [ ] T001: All docs audited with accuracy rating and Divio classification
- [ ] T002: Four Divio directories created (`tutorials/`, `how-to/`, `reference/`, `explanation/`)
- [ ] T003: Outdated/contributor docs removed
- [ ] T004: Salvageable content migrated to Divio locations
- [ ] All changes committed with clear messages
- [ ] No broken internal links introduced (verified)

## Review Guidance

- Verify directory structure matches plan.md specification
- Confirm no valuable content was deleted
- Check that migrated files have updated internal links
- Ensure audit findings are documented

## Activity Log

- 2026-01-16T16:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-16T16:24:16Z – claude – shell_pid=19353 – lane=doing – Started implementation via workflow command
- 2026-01-16T16:26:26Z – claude – shell_pid=19353 – lane=for_review – All subtasks complete: Divio structure created, outdated docs removed, salvageable content migrated. Ready for review.
