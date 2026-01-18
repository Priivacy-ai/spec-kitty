---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
title: "Setup & TOC Update"
phase: "Phase 0 - Setup"
lane: "done"
assignee: ""
agent: "codex"
shell_pid: "35960"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies: []
history:
  - timestamp: "2026-01-17T18:14:07Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Setup & TOC Update

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Update `docs/toc.yml` to include navigation entries for all 6 new documentation pages
- Maintain valid YAML syntax
- Preserve existing structure and ordering conventions
- Success: toc.yml parses without errors and includes all new entries

## Context & Constraints

- **Spec**: `kitty-specs/016-jujutsu-vcs-documentation/spec.md`
- **Plan**: `kitty-specs/016-jujutsu-vcs-documentation/plan.md` - see "Target Documentation Changes" section
- **Research**: `kitty-specs/016-jujutsu-vcs-documentation/research.md`
- **Existing toc.yml**: `docs/toc.yml` - review current structure before editing

### New Pages to Add

**Tutorials section**:
- `tutorials/jujutsu-workflow.md` - "Jujutsu (jj) Workflow"

**How-To Guides section**:
- `how-to/sync-workspaces.md` - "Sync Workspaces"
- `how-to/handle-conflicts-jj.md` - "Handle Conflicts (jj)"
- `how-to/use-operation-history.md` - "Use Operation History"

**Explanations section**:
- `explanation/jujutsu-for-multi-agent.md` - "Jujutsu for Multi-Agent Development"
- `explanation/auto-rebase-and-conflicts.md` - "Auto-Rebase and Non-Blocking Conflicts"

## Subtasks & Detailed Guidance

### Subtask T001 – Add tutorial entry to toc.yml

- **Purpose**: Make the new jj workflow tutorial discoverable in navigation
- **Steps**:
  1. Read current `docs/toc.yml` to understand structure
  2. Locate the Tutorials section
  3. Add entry: `- name: Jujutsu (jj) Workflow` with `href: tutorials/jujutsu-workflow.md`
  4. Position after existing tutorials (or alphabetically)
- **Files**: `docs/toc.yml`
- **Notes**: Use both "Jujutsu" and "jj" in title for searchability

### Subtask T002 – Add how-to entries to toc.yml

- **Purpose**: Make the three new how-to guides discoverable
- **Steps**:
  1. Locate the How-To Guides section in toc.yml
  2. Add three entries:
     - `- name: Sync Workspaces` → `how-to/sync-workspaces.md`
     - `- name: Handle Conflicts (jj)` → `how-to/handle-conflicts-jj.md`
     - `- name: Use Operation History` → `how-to/use-operation-history.md`
  3. Position logically (after related guides or alphabetically)
- **Files**: `docs/toc.yml`
- **Notes**: "(jj)" suffix distinguishes from general conflict handling

### Subtask T003 – Add explanation entries to toc.yml

- **Purpose**: Make the two new explanation articles discoverable
- **Steps**:
  1. Locate the Explanations section in toc.yml
  2. Add two entries:
     - `- name: Jujutsu for Multi-Agent Development` → `explanation/jujutsu-for-multi-agent.md`
     - `- name: Auto-Rebase and Non-Blocking Conflicts` → `explanation/auto-rebase-and-conflicts.md`
  3. Position logically among existing explanations
- **Files**: `docs/toc.yml`
- **Notes**: These provide the "why" behind jj integration

## Risks & Mitigations

- **Invalid YAML syntax**: Validate with `python -c "import yaml; yaml.safe_load(open('docs/toc.yml'))"` before committing
- **Broken references**: Files don't exist yet - that's expected. Subsequent WPs will create them.

## Definition of Done Checklist

- [ ] T001: Tutorial entry added to toc.yml
- [ ] T002: Three how-to entries added to toc.yml
- [ ] T003: Two explanation entries added to toc.yml
- [ ] YAML syntax validated (no parse errors)
- [ ] Existing entries unchanged (no accidental deletions)

## Review Guidance

- Verify all 6 new entries are present
- Check YAML indentation consistency
- Confirm entry names include searchable terms ("jj", "jujutsu")
- Verify href paths match planned file locations from plan.md

## Activity Log

- 2026-01-17T18:14:07Z – system – lane=planned – Prompt created.
- 2026-01-17T18:34:06Z – claude – shell_pid=29955 – lane=doing – Started implementation via workflow command
- 2026-01-17T18:35:21Z – claude – shell_pid=29955 – lane=for_review – All 6 toc.yml entries added and validated - 1 tutorial, 3 how-tos, 2 explanations
- 2026-01-17T18:42:42Z – codex – shell_pid=35960 – lane=doing – Started review via workflow command
- 2026-01-17T18:42:57Z – codex – shell_pid=35960 – lane=done – Review passed: toc.yml entries added, YAML parses
