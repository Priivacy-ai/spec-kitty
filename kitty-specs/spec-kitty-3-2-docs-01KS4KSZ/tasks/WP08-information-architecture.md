---
work_package_id: WP08
title: Divio information architecture & gap list
dependencies:
- WP02
- WP05
requirement_refs:
- FR-011
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
agent: claude
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: curator-carla
authoritative_surface: docs/development/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- docs/development/3-2-information-architecture.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

## Objective

Author the 3.2 documentation information architecture: every planned 3.2 docs page (tutorials, how-to, reference, explanation) with Divio type, audience, nav placement, and disposition (reuse / rewrite / new) against the current `docs/` tree.

## Context

- FR-011 / FR-012.
- Source pages: WP02 inventory (`docs/development/3-2-page-inventory.yaml`).
- Source CLI reference list: WP07 rebuilt reference + agent-subcommands.
- Divio four-type guidance is the IA spine: tutorial = learn, how-to = task, reference = lookup, explanation = understand.

## Subtasks

### T025 — Author the IA doc

Create `docs/development/3-2-information-architecture.md` with these sections:

1. **Tutorials** — list each planned tutorial with: title, target audience, prerequisites, success criterion, nav placement.
2. **How-to guides** — same shape; include install/upgrade/uninstall family, run-a-mission-in-host family, diagnose family, recover family.
3. **Reference** — same shape; include CLI commands, slash commands, generated project file structure, configuration, env vars, supported harnesses, init/upgrade lifecycle, glossary.
4. **Explanation** — same shape; include what-spec-kitty-is, mission model, charter and doctrine, runtime loop and next, harness integration, version compatibility, pip-vs-pipx-vs-uv, workspace-git-and-branches.
5. **Cross-references** — for each page, list the inventory row it corresponds to (or "NEW" if it's a new page).

### T026 — Gap list (reuse / rewrite / new)

For each of the four Divio directories (`docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/`):

| Existing page | Inventory tag | Disposition | Target IA slot |
|---------------|---------------|-------------|----------------|

Disposition values:

- `reuse` — page is current and stays as-is (modulo `version_tag` frontmatter add in a later mission).
- `rewrite` — page exists but its content needs a 3.2-aligned rewrite.
- `archive` — page is 1.x/2.x and moves out of current nav per WP09.
- `migrate-note` — page is 3.1 and becomes a migration note per plan default.
- `new` — page does not exist; create during this mission's implement phase.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `C`. First WP in lane C; allocates `.worktrees/spec-kitty-3-2-docs-<mid8>-lane-c/`.

## Test Strategy

Reviewer gate only.

## Definition of Done

- [ ] IA doc covers all four Divio directories.
- [ ] Every page in the WP07 reference is referenced in the IA.
- [ ] Gap list dispositions are explicit for every existing page.
- [ ] No files outside `owned_files` modified.

## Risks

- **IA drift from inventory** — Mitigation: cite inventory row IDs (path-based) for every page; reviewer cross-checks counts.

## Reviewer Guidance

- Confirm one section per Divio type with every planned page.
- Confirm the gap list dispositions cover every existing page (no untouched rows).
- Confirm "new" pages match the file surfaces in `plan.md` §"Project Structure".

## Implement command

```bash
spec-kitty agent action implement WP08 --agent claude
```
