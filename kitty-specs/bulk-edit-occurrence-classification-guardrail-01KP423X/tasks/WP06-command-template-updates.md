---
work_package_id: WP06
title: Command Template Updates
dependencies:
- WP04
- WP05
requirement_refs:
- FR-002
- FR-006
- FR-007
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
agent: "claude:opus:implementer:implementer"
shell_pid: "85590"
history:
- date: '2026-04-13'
  author: claude
  action: created
authoritative_surface: src/specify_cli/missions/software-dev/command-templates/
execution_mode: code_change
owned_files:
- src/specify_cli/missions/software-dev/command-templates/implement.md
- src/specify_cli/missions/software-dev/command-templates/review.md
tags: []
---

# WP06 — Command Template Updates

## Objective

Update the implement and review command templates for the software-dev mission to reference the occurrence map artifact. These templates are the agent-facing instructions that guide AI agents through the implement and review actions.

## Context

- **Spec**: FR-002 (required classification step), FR-006 (blocked implementation), FR-007/FR-008 (review validation)
- **Plan**: Integration Point 8 — Command Template Updates
- **CLAUDE.md warning**: Command templates live in `src/specify_cli/missions/*/command-templates/` — these are the SOURCE files. Do NOT edit agent copies in `.claude/`, `.amazonq/`, etc.
- Templates propagate to all 12 agents via migration during `spec-kitty upgrade`
- The templates are Markdown files with instructions for agents — they don't import code
- WP04 added the actual gate logic; these templates explain the gate to agents

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

---

### Subtask T017: Update Implement Command Template

**Purpose**: Add occurrence map awareness to the implement template so agents understand the gate and how to handle it.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/command-templates/implement.md`

2. Add a new section near the pre-implementation checks (before the main implementation loop). Insert after any existing pre-flight checks:

   ```markdown
   ## Bulk Edit Occurrence Classification

   If this mission has `change_mode: bulk_edit` in its `meta.json`, an occurrence
   classification artifact is required before implementation can begin.

   **What to check**:
   1. Read `meta.json` in the feature directory — look for `"change_mode": "bulk_edit"`
   2. If present, verify `occurrence_map.yaml` exists in the same directory
   3. The occurrence map classifies the target term by semantic category with
      per-category actions: `rename`, `manual_review`, `do_not_change`, `rename_if_user_visible`

   **During implementation**:
   - Consult the occurrence map before modifying any file
   - Respect category actions: do NOT modify occurrences in categories marked `do_not_change`
   - For `manual_review` categories, document your decision in the WP review notes
   - For `rename_if_user_visible`, only change user-facing text (docs, UI, error messages)
   - Check the `exceptions` section for files/patterns with overriding rules

   **If the gate blocks you**:
   The system will refuse to start implementation if the occurrence map is missing or
   incomplete. If you see this error:
   - Create `occurrence_map.yaml` following the schema in `data-model.md`
   - Ensure it has `target`, `categories` (3+ with actions), and optionally `exceptions`
   - Re-run the implement command

   **If an inference warning fires**:
   The system may warn that spec content looks like a bulk edit even without `change_mode` set.
   Either set `change_mode: "bulk_edit"` in meta.json, or re-run with `--acknowledge-not-bulk-edit`.
   ```

3. Keep the addition concise — agents need actionable guidance, not policy essays.

**Files**: `src/specify_cli/missions/software-dev/command-templates/implement.md`

**Validation**:
- [ ] Template still valid Markdown
- [ ] New section doesn't break existing template structure
- [ ] Instructions are actionable for agents

---

### Subtask T018: Update Review Command Template

**Purpose**: Add occurrence map reference to the review template so reviewing agents know to check classification compliance.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/command-templates/review.md`

2. Add a section to the review checklist or review criteria area:

   ```markdown
   ## Bulk Edit Compliance (if applicable)

   If this mission has `change_mode: bulk_edit` in `meta.json`:

   1. **Verify occurrence map exists**: `occurrence_map.yaml` must be present in the feature directory
   2. **Reference during review**: The occurrence map is the governing artifact for this bulk edit
   3. **Check category compliance**:
      - Verify changes respect `do_not_change` categories — reject if these were modified
      - Verify `manual_review` categories have documented justification
      - Flag any changed files that fall outside classified categories
   4. **Check exceptions**: Verify exception files/patterns were not modified
   5. **If occurrence map is missing**: Reject the review — bulk edit missions require classification

   The system enforces map existence automatically, but as a reviewer you should verify
   that the *substance* of the changes aligns with the classification, not just that the
   file exists.
   ```

3. Place this section where it will be seen during the review workflow (near other quality checks).

**Files**: `src/specify_cli/missions/software-dev/command-templates/review.md`

**Validation**:
- [ ] Template still valid Markdown
- [ ] Review instructions reference occurrence map as governing artifact
- [ ] Instructions distinguish automated checks (map existence) from human judgment (substance review)

## Definition of Done

- [ ] Implement template updated with bulk edit awareness section
- [ ] Review template updated with compliance check section
- [ ] Both templates are valid Markdown
- [ ] Instructions are actionable and concise
- [ ] No existing template content broken

## Risks

- **Low**: Templates are frequently updated. Changes are additive sections, minimizing merge conflict risk.
- **Low**: Template changes propagate to all 12 agents on next `spec-kitty upgrade`. No migration needed for the template content itself.

## Reviewer Guidance

- Verify the added sections are concise and actionable (agents don't need policy justification)
- Check that the implement template explains how to handle both the gate and the inference warning
- Check that the review template distinguishes system-enforced checks from reviewer judgment
- Confirm templates are valid Markdown and integrate naturally with existing content

## Activity Log

- 2026-04-13T19:25:42Z – claude:opus:implementer:implementer – shell_pid=85590 – Started implementation via action command
- 2026-04-13T19:31:12Z – claude:opus:implementer:implementer – shell_pid=85590 – Ready for review
- 2026-04-13T19:31:42Z – claude:opus:implementer:implementer – shell_pid=85590 – Review passed: implement template updated with bulk edit section, review template created with compliance section.
- 2026-04-13T19:32:12Z – claude:opus:implementer:implementer – shell_pid=85590 – Done override: Feature merged to main
