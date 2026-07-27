---
work_package_id: WP06
title: 'Class-closing guard (#2711): resume non-reemission invariant'
dependencies:
- WP04
requirement_refs:
- FR-008
tracker_refs:
- '2711'
planning_base_branch: fix/red-handling-policy-and-drg-regression-marks
merge_target_branch: fix/red-handling-policy-and-drg-regression-marks
branch_strategy: Planning artifacts for this mission were generated on fix/red-handling-policy-and-drg-regression-marks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/red-handling-policy-and-drg-regression-marks unless the human explicitly redirects the landing branch.
subtasks:
- T014
phase: Phase 3 - Class guard (#2711 chain)
assignee: ''
agent: ''
history:
- timestamp: '2026-07-17T20:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_resume_non_reemission_guard.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_resume_non_reemission_guard.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Class-closing guard (#2711)

## Objective
Close the "rollback leaves committed/working incoherent; resume duplicates transitions"
class by construction — not a re-run of WP02 (FR-008, SC-005).

## Fix (T014)
A non-vacuous invariant asserting resume derives progress from durable events and never
re-emits an already-recorded transition. **The BINDING guard MUST be the property test**
(it covers the observable outcome, incl. a duplicate-emit via any path):
- **Property test (binding):** for an arbitrary committed coord log + a rolled-back
  `MergeState`, resume is **identity-idempotent** — the committed `done` `event_id` per WP
  is unchanged after resume (`resume` re-emits nothing already recorded). **WP02 empirical
  note:** frame this as `event_id` byte-stability / no-churn, NOT as a tip `count == 1`
  (safe-commit replaces the tip, so a count assertion is vacuous/green-on-base).
- **AST/contract lint (optional adjunct, NOT a substitute):** resume progress reads
  `EventLogReadContract.coordination_branch_ref` not `MergeState.completed_wps`. This pins a
  mechanism and cannot catch a duplicate-emit through another path, so it may accompany but
  never replace the property test.

## Acceptance criteria
- The **property test** FAILS on a synthetic duplicate-emit path (regardless of mechanism) and
  on "resume trusts `completed_wps`" (SC-005), and PASSES on the fixed tree.
- Complements (does not duplicate) WP02's outcome test.

## Validation
- `PWHEADLESS=1 uv run pytest tests/architectural/ -q` and the #2711 regression stays green.
- Self-mutation proof: reintroduce the `completed_wps`-trusting derivation → guard goes RED → revert.

## Ownership
Owns: new invariant under `tests/architectural/` (or `tests/merge/` if a property test fits better there).

## Notes
Rebase-first (C-003). Co-delivered with the #2711 fix.
