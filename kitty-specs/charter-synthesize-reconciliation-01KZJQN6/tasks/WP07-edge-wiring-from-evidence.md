---
work_package_id: WP07
title: Edge wiring from evidence (#3052)
dependencies:
- WP01
requirement_refs:
- FR-012
planning_base_branch: fix/charter-synthesize-reconciliation
merge_target_branch: fix/charter-synthesize-reconciliation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-synthesize-reconciliation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-synthesize-reconciliation unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
phase: Phase 3 - Folds
history:
- timestamp: '2026-08-09T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/synthesizer/
create_intent:
- tests/charter/synthesizer/test_edge_wiring.py
execution_mode: code_change
mission_id: 01KZJQN68SWZ7T1YKGDB4Q4EVH
owned_files:
- src/charter/activation/synthesizer/interview_mapping.py
- src/charter/activation/synthesizer/targets.py
- src/charter/activation/synthesizer/project_drg.py
- tests/charter/synthesizer/test_edge_wiring.py
tags: []
tracker_refs: []
agent_profile: python-pedro
role: implementer
agent: claude
wp_code: WP07
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role:
implementer) before anything else. Then read `plan.md`, `research.md` (#3052 fold), and the
issue context for #3052.

# Work Package Prompt: WP07 – Edge wiring from evidence (#3052)

## Objectives & Success Criteria

- Where an interview section declares an upstream doctrine relationship, `charter synthesize`
  emits the corresponding edge (instead of `edges: []`), so the DRG lint no longer flags the
  just-generated directives.
- **No edge is fabricated** where no `source_urns` evidence exists (NFR-007).

## Context & Constraints

- **Why** (research.md, #3052): `emit_project_layer` derives edges solely from
  `target.source_urns` (`project_drg.py:215-241`); `source_urns` is populated only for the
  `how-we-apply-DIRECTIVE_xxx` tactic pattern (`interview_mapping.py:334`). Consumer-pack sections
  that declare an upstream relationship but do not populate `source_urns` therefore emit no edge.
- **Framing/rationale**: synthesis should wire the charter-relevant edges the doctrine DRG /
  interview mapping already declares — conservatively. Do **not** infer relationships from the
  built-in DRG snapshot; only emit an edge where a section provides an explicit upstream URN.
- **Scope**: you own `interview_mapping.py`, `targets.py`, `project_drg.py`. Do not touch the
  reconcile seam (WP01) or `validation_gate.py` (WP02).

## Subtasks & Detailed Guidance

### Subtask T027 – Populate `source_urns` from evidence
- In `interview_mapping.py` / `targets.py`, extend `source_urns` population to the consumer-pack
  interview sections that declare an upstream doctrine URN (mirroring the existing
  `how-we-apply-DIRECTIVE_xxx` pattern). Only populate where the section provides the URN — never
  synthesize a URN that was not declared.

### Subtask T028 – Confirm edge emission + lint
- Verify `emit_project_layer`'s existing `source_urns`→edge derivation now emits the declared
  edges for those sections (no changes to the derivation rule beyond what evidence provides). Run
  `charter lint` on a synthesized consumer pack and confirm the generated directives are no longer
  flagged as orphaned.

### Subtask T029 – Tests
- **Record the fixture first.** The `FixtureAdapter` is **inputs-hash-keyed** (via
  `compute_inputs_hash`) and **RAISES on a miss** — a new `source_urns`-bearing target changes the
  inputs hash, so a matching fixture must exist under
  `tests/charter/fixtures/synthesizer/{directive,tactic,styleguide}/` or the test errors on a
  fixture miss rather than exercising edge emission. Record/add the fixture for the
  `source_urns`-bearing target before asserting.
- New `tests/charter/synthesizer/test_edge_wiring.py`:
  - **Positive**: a section declaring an upstream URN → the overlay contains the corresponding
    edge (not `edges: []`); DRG lint passes.
  - **Negative (no fabrication)**: a section with no declared upstream URN → **no** edge is emitted
    for that node.

## Branch Strategy

- Planning-base / merge-target: `fix/charter-synthesize-reconciliation` (PRs into `main`).
- Depends on WP01; run `spec-kitty agent action implement WP07 --agent <name>` after WP01 is
  approved/done. Execution worktree per computed lane from `lanes.json`.

## Definition of Done

- [ ] Declared upstream relationships emit edges; DRG lint no longer flags generated directives.
- [ ] No fabricated edges where evidence is absent (positive + negative tests green).
- [ ] `ruff` + `mypy` clean; complexity ≤ 15.
- [ ] Run `tests/architectural/test_no_legacy_terminology.py` on the touched `src/` surfaces (C-005; Mission not feature).

## Risks & Reviewer Guidance

- **Risk**: fabricating wrong relationships (worse than an orphan). Reviewer: confirm the negative
  no-fabrication test and that population is evidence-gated.

## 🔴 Post-tasks squad amendments (MUST READ before implementing)

1. **[MINOR] Avoid the FR-020 built-in-collision hard-fail in the positive test.**
   `emit_project_layer` raises `ProjectDRGValidationError` when a newly declared triple already
   exists in the built-in DRG (`project_drg.py:222-233`). Choose positive-test evidence whose
   upstream URN does **not** duplicate an existing built-in edge, so emission emits (not raises).
2. **[MINOR] Dependency note.** WP07's edge-wiring is independent of the reconcile seam; the
   `dependencies: [WP01]` is conservative (avoids a merge race on `graph.yaml` shape). It may be run
   in parallel off the branch base if the lane scheduler allows.
