---
work_package_id: WP08
title: Integration & Cross-Linking
lane: "done"
dependencies: [WP01, WP02, WP03, WP04, WP05, WP06, WP07]
base_branch: 030-2x-sync-auth-docs-WP07
base_commit: 090c6c0bea1add1ac7d89552609e8f88392f1ba1
created_at: '2026-02-05T15:32:25.339350+00:00'
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
phase: Phase 5 - Integration
assignee: ''
agent: ''
shell_pid: "19813"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-05T15:08:07Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Integration & Cross-Linking

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Update all `toc.yml` files to include new documentation pages.
- Verify all cross-page links resolve correctly.
- Run `docfx build` validation if available.
- **FR-009**: Proper DocFX conventions (toc.yml entries).
- **FR-012**: All new files added to toc.yml on the docs branch.
- **SC-004**: Documentation builds with zero warnings.
- **SC-005**: No placeholder text or TODOs in any doc file.

## Context & Constraints

- **Branch**: `docs/2x-sync-auth` off `2.x`
- **Depends on ALL other WPs**: All documentation pages must be written before integration
- **Existing toc.yml files**: `docs/tutorials/toc.yml`, `docs/how-to/toc.yml`, `docs/reference/toc.yml`
- **New toc.yml**: `docs/explanations/toc.yml` (created in WP03, verified here)
- **Top-level toc.yml**: `docs/toc.yml` should already have Explanations tab
- **Implementation command**: `spec-kitty implement WP08 --base WP07` (or whichever WP merged last)

## Subtasks & Detailed Guidance

### Subtask T040 – Update `docs/tutorials/toc.yml`

- **Purpose**: Add the server connection tutorial to navigation.
- **Steps**:
  1. Read `docs/tutorials/toc.yml`
  2. Add entry for the new tutorial:
     ```yaml
     - name: Connect to a Server
       href: server-connection.md
     ```
  3. Place it after "Your First Feature" (it's the natural next step after local setup)
- **Files**: `docs/tutorials/toc.yml`
- **Notes**: Check existing entries for exact formatting (indentation, field order)

### Subtask T041 – Update `docs/how-to/toc.yml`

- **Purpose**: Add auth, sync, and dashboard how-to pages to navigation.
- **Steps**:
  1. Read `docs/how-to/toc.yml`
  2. Add entries for three new how-to pages:
     ```yaml
     - name: Authenticate
       href: authenticate.md
     - name: Sync to Server
       href: sync-to-server.md
     - name: Use the SaaS Dashboard
       href: use-saas-dashboard.md
     ```
  3. Placement: Group these together, after the existing "Sync Workspaces" entry (they're related topics)
- **Files**: `docs/how-to/toc.yml`
- **Notes**: The existing `sync-workspaces.md` entry must remain unchanged

### Subtask T042 – Verify or create `docs/explanations/toc.yml`

- **Purpose**: Ensure the explanations directory has proper navigation.
- **Steps**:
  1. Check if `docs/explanations/toc.yml` was created by WP03
  2. If it exists, verify it contains:
     ```yaml
     - name: Sync Architecture
       href: sync-architecture.md
     ```
  3. If it doesn't exist, create it with the above content
  4. Verify `docs/toc.yml` (top-level) has an Explanations entry pointing to `explanations/toc.yml`
  5. If the top-level Explanations entry is missing, add:
     ```yaml
     - name: Explanations
       href: explanations/
       homepage: explanations/sync-architecture.md
     ```
- **Files**: `docs/explanations/toc.yml`, potentially `docs/toc.yml`

### Subtask T043 – Verify cross-page See Also links

- **Purpose**: Ensure all links between new pages work correctly.
- **Steps**:
  1. For each new page, check that all "See Also" links point to valid files:
     - `authenticate.md` → cli-commands.md, configuration.md, server-connection.md, sync-architecture.md
     - `sync-to-server.md` → sync-workspaces.md, cli-commands.md, authenticate.md, sync-architecture.md
     - `use-saas-dashboard.md` → authenticate.md, sync-architecture.md, sync-to-server.md
     - `server-connection.md` → use-saas-dashboard.md, sync-architecture.md, sync-to-server.md, authenticate.md, cli-commands.md, configuration.md
     - `sync-architecture.md` → authenticate.md, sync-to-server.md, cli-commands.md, configuration.md
  2. For updated reference pages, check that new See Also entries use correct relative paths
  3. Fix any broken links
- **Files**: All new and updated documentation files
- **Notes**: Relative paths from how-to/ to reference/ should use `../reference/`

### Subtask T044 – Verify internal link anchors

- **Purpose**: Ensure links to specific sections (anchors) resolve correctly.
- **Steps**:
  1. Check that anchor links in See Also sections match actual headings:
     - `cli-commands.md#spec-kitty-auth` → verify this heading exists in cli-commands.md
     - `cli-commands.md#spec-kitty-sync` → verify this heading exists
     - `configuration.md#server-configuration-2x` → verify this heading exists
  2. DocFX generates anchors from heading text: spaces become hyphens, lowercase
  3. Fix any anchor mismatches
- **Files**: All new and updated documentation files

### Subtask T045 – Run docfx build validation

- **Purpose**: Verify the documentation builds without warnings.
- **Steps**:
  1. If DocFX is installed locally:
     ```bash
     cd docs/
     docfx build
     ```
  2. Check output for warnings or errors
  3. Common issues: broken links, missing files referenced in toc.yml, duplicate headings
  4. If DocFX is not installed:
     - Document the build command in the WP activity log
     - Note that build validation is deferred to CI/CD
  5. Check all new files for:
     - No placeholder text (`[REPLACE]`, `TODO`, `FIXME`)
     - No template markers (`{{TIMESTAMP}}`, `WPxx`)
     - Proper heading hierarchy (H1 only once per file)
- **Files**: All documentation files
- **Notes**: DocFX build validation is optional if the tool isn't installed locally

## Risks & Mitigations

- **Risk**: DocFX not installed → Flag as optional, document command for CI
- **Risk**: Top-level toc.yml missing Explanations tab → Check and add if needed

## Review Guidance

- Verify every new page appears in its section's toc.yml
- Test at least 3 cross-page links manually (open file, find referenced anchor)
- Check that the existing `sync-workspaces.md` toc entry is unchanged
- Confirm no placeholder text in any doc file
- Verify heading hierarchy: each file has exactly one H1, followed by H2/H3

## Activity Log

- 2026-02-05T15:08:07Z – system – lane=planned – Prompt created.
