---
work_package_id: WP05
title: Architecture docs + seam checklist
dependencies:
- WP04
requirement_refs:
- FR-003
- C-003
- NFR-001
- NFR-005
planning_base_branch: kitty/mission-workflow-self-doc
merge_target_branch: kitty/mission-workflow-self-doc
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-workflow-self-doc. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-workflow-self-doc unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
history: []
authoritative_surface: docs/architecture/
create_intent: []
execution_mode: code_change
owned_files:
- docs/architecture/execution-lanes.md
- docs/architecture/git-worktrees.md
- docs/architecture/artifact-placement-seam.md
tags: []
tracker_refs: []
---

## Objective
Correct/enrich the architecture docs: the real workspace-resolution contract, cross-mission concurrency, and the partition-move audit checklist.

## Subtasks
- **T010** `execution-lanes.md`: the real contract — `resolve_workspace_for_wp` requires `lanes.json` for flat/`SINGLE_BRANCH`/`LANES`, raising `MissingLanesError`; NO `-WP##` fallback. Add the `bulk_edit` disjoint-ownership-avoids-cyclic-lanes nuance. `git-worktrees.md`: two missions in one checkout race the shared git HEAD/index (concurrency-safety note).
- **T011** `artifact-placement-seam.md`: a partition-move AUDIT CHECKLIST (when a partition classification moves: grep EVERY reader; classify; watch out-of-loop coord-resolving callers; e2e-not-unit catches the straggler — PR #3437) + the two-axis resolver-site classification (raise-or-degrade AND anchor-root). CITE the read/write-symmetry principle by its ADR (`2026-06-24-1`) / wording — NOT a phantom "INV-5" (that string is absent from the file).

## Rules
Verify the resolver contract against `src/specify_cli/workspace/context.py` + `lanes/persistence.py` (C-005). Do NOT regenerate rollups (WP06). Terminology green. `.venv/bin/python`, never bare `uv run`.

## Done
`MissingLanesError` contract correct; checklist actionable; INV-5 phantom avoided; terminology green.
