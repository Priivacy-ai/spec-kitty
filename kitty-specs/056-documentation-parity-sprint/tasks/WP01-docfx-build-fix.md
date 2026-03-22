---
work_package_id: WP01
title: DocFX Build Fix and Navigation
lane: "doing"
dependencies: []
requirement_refs: [FR-001, FR-010, FR-012, FR-013, FR-014]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
base_branch: fix/skill-audit-and-expansion
base_commit: dd425f9c4c453cdb215c8ecedd4798a38ecd7eca
created_at: '2026-03-22T14:50:35.943533+00:00'
subtasks: [T001, T002, T003, T004, T005]
agent: "codex"
shell_pid: "20880"
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 1
---

# WP01: DocFX Build Fix and Navigation

## Objective

Make all existing Divio docs (tutorials, how-to, reference, explanation) visible
on docs.spec-kitty.ai by updating the DocFX build configuration and site
navigation. Currently only `1x/` and `2x/` are built — 56 docs are invisible.

## Context

- DocFX config: `docs/docfx.json`
- Top-level nav: `docs/toc.yml`
- Homepage: `docs/index.md`
- Missing file: `docs/how-to/use-operation-history.md` (referenced in `docs/how-to/toc.yml`)

## Implementation

### T001: Update docs/docfx.json

Add the 4 Divio directories to the `content.files` array:

```json
"files": [
  "index.md",
  "toc.yml",
  "1x/**/*.md",
  "1x/toc.yml",
  "2x/**/*.md",
  "2x/toc.yml",
  "tutorials/**/*.md",
  "tutorials/toc.yml",
  "how-to/**/*.md",
  "how-to/toc.yml",
  "reference/**/*.md",
  "reference/toc.yml",
  "explanation/**/*.md",
  "explanation/toc.yml"
]
```

Verify the glob patterns match DocFX conventions. Check existing patterns for
guidance on syntax.

### T002: Update docs/toc.yml

Add navigation entries for all 4 Divio categories. Current file only has
entries for 1.x and 2.x tracks. Add:

```yaml
- name: Tutorials
  href: tutorials/toc.yml
- name: How-To Guides
  href: how-to/toc.yml
- name: Reference
  href: reference/toc.yml
- name: Explanation
  href: explanation/toc.yml
```

### T003: Update docs/index.md

Update the homepage to link to all categories. Currently it's a version track
selector (1.x vs 2.x). Add a section that presents the 4 Divio categories
with brief descriptions:

- **Tutorials**: Learn spec-kitty step by step
- **How-To Guides**: Solve specific problems
- **Reference**: CLI commands, configuration, APIs
- **Explanation**: Understand concepts and architecture

### T004: Create docs/how-to/use-operation-history.md

This file is referenced in `docs/how-to/toc.yml` but does not exist. Create
it documenting the `spec-kitty ops` command for operation history and undo
functionality. Check `spec-kitty ops --help` for the actual command interface.

### T005: Verify toc.yml cross-references

Check each subdirectory's `toc.yml` to ensure all referenced files exist:
- `docs/tutorials/toc.yml`
- `docs/how-to/toc.yml`
- `docs/reference/toc.yml`
- `docs/explanation/toc.yml`

Fix any broken references.

## Definition of Done

- [ ] DocFX build config includes all 4 Divio categories
- [ ] Top-level navigation links to all categories
- [ ] Homepage links to all categories
- [ ] Missing `use-operation-history.md` file created
- [ ] No broken file references in any toc.yml
- [ ] `docfx build docs/docfx.json` succeeds (if docfx is available locally)

## Risks

- DocFX glob syntax may differ from what's expected — verify against DocFX docs
- Existing toc.yml files may have other broken references beyond the known one

## Implementation Command

```bash
spec-kitty implement WP01
```

## Activity Log

- 2026-03-22T14:50:36Z – coordinator – shell_pid=19406 – lane=doing – Assigned agent via workflow command
- 2026-03-22T14:54:27Z – coordinator – shell_pid=19406 – lane=for_review – DocFX build config updated with all 4 Divio categories, top-level navigation and homepage rewritten, missing use-operation-history.md created, all toc.yml references verified
- 2026-03-22T14:54:54Z – codex – shell_pid=20880 – lane=doing – Started review via workflow command
