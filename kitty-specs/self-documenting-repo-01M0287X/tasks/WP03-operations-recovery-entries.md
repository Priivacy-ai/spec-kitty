---
work_package_id: WP03
title: Coord/lane recovery entries in operations (G3)
dependencies: []
requirement_refs:
- FR-003
- FR-004
- C-001
- C-002
- NFR-001
planning_base_branch: kitty/mission-self-doc-gapclose
merge_target_branch: kitty/mission-self-doc-gapclose
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-self-doc-gapclose. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-self-doc-gapclose unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-self-documenting-repo-01M0287X
base_commit: ecc0215b995f3a816b44e68507e350a80a413dbc
created_at: '2026-08-15T08:48:56.473403+00:00'
subtasks:
- T007
- T008
- T009
- T010
phase: Phase 1
history:
- timestamp: '2026-08-15T08:10:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: docs/operations/
execution_mode: code_change
mission_id: 01M0287XCV1R9VDEXHSDB0RTYR
owned_files:
- docs/operations/recovery-index.md
- docs/operations/toc.yml
- docs/development/3-2-page-inventory.yaml
- docs/development/3-2-docs-retrieval-index.yaml
tags: []
tracker_refs: []
wp_code: WP03
---

# Work Package Prompt: WP03 – Coord/lane recovery entries in operations (G3)

## Objective
Publish six coord/lane split-brain recovery entries in the EXISTING `docs/operations/` home (C-001), each leading with a shipped `spec-kitty doctor … --fix` where one exists.

## Subtasks
- **T007 Doctor audit.** Map each of the six classes (coord-off-main add/add; --start-branch coord divergence; stale-lane-seed; missing -coord worktree; cutover-flip-from-worktree; base-strand-after-rebase) to its `doctor` subcommand + `--fix` semantics (present/partial/absent). Verify names (`coordination`, `sparse-checkout --fix`, `workspaces`→`_workspace_husk_doctor.py`, `cutover`).
- **T008 Author six entries** (new `docs/operations/*.md`, `type: none` (or omit `type`, matching existing operations runbooks — the inventory reads the `type` key)): lead with the shipped command; manual steps + operator-grant caveat only where no `--fix`. Cite `docs/plans/engineering-notes/coord-splitbrain-rootcause.md` for the 'why' (don't re-derive).
- **T009 Register + reconcile IA.** Add each to `recovery-index.md` + `toc.yml`; add bidirectional cross-links with the second recovery home `docs/guides/how-to/recovery/` + a one-line rationale (operational-recovery vs agent-facing-crash/merge).
- **T010 Regenerate rollups.** `inventory_lockfile.py --write`; `check_docs_freshness --ci` errors=0 (frontmatter, description 50-180, divio_type, registration).

## Done
Each class reproducible-to-recovery via its entry; docs-freshness errors=0.
