---
work_package_id: WP05
title: '#4015 assert_timing_budget helper + delete-triage + coverage-mapping format'
dependencies: []
requirement_refs:
- FR-008
- FR-011
- FR-013
- FR-014
planning_base_branch: issue-4017-ci-suite-stability
merge_target_branch: issue-4017-ci-suite-stability
branch_strategy: Planning artifacts for this mission were generated on issue-4017-ci-suite-stability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-4017-ci-suite-stability unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-suite-stability-test-isolation-01M22MM5
base_commit: 57a561bc03ec7b0c9f9b3ad5d480fa87f8be4be9
created_at: '2026-09-09T14:10:37.390532+00:00'
subtasks: []
phase: Phase 1 - Lane B enabler
history:
- at: '2026-09-09T09:08:01Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- tests/_perf_helpers.py
- tests/_next_shard_map.py
- tests/architectural/test_timing_coverage_invariant.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/_perf_helpers.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer). Read [spec.md](../spec.md) §#4015 + [research.md](../research.md) Decision 3/4. Canonical per-test lists are in commit `1d59ed2ca6`'s body (`git log -1 --format=%B 1d59ed2ca6`) — that is ground truth, do not re-derive a divergent set.

## Objective
Provide the shared timing-budget helper, triage ALL delete candidates into ONE consolidated operator sign-off (HiC), and define the per-split coverage-mapping format the split WPs will each record. (FR-008, FR-011, FR-013)

## Subtasks
### T014b — Sole shard-map owner (planner #3)
WP05 is the SOLE owner of `tests/_next_shard_map.py`. WP01/WP03/WP04 (new tests/runtime/ files) and WP06-09 (relocated @performance files) each RECORD their new/relocated filenames in their Activity Log; the shard-map entries for ALL of them are applied here (or by the orchestrator at integration) — no other lane edits this file (avoids the silent tuple-merge corruption). 

### T014 — assert_timing_budget helper
Create \`tests/_perf_helpers.py\` with \`assert_timing_budget(measured, budget, *, name="elapsed")\` whose CALL-SITE text contains a recognized \`TIMING_ASSERTION_VOCABULARY\` token (e.g. "budget"/"elapsed") so a \`@pytest.mark.performance\` test using it passes the #3665 guard WITHOUT widening the vocabulary. ruff+mypy clean.
### T015 — Triage delete candidates → ONE consolidated operator sign-off (HiC)
From the 9 vocab-blocked + 74 mixed lists, identify EVERY candidate for the DELETE disposition (persistently-flaky low-value PURE-timing, zero functional assertions). For each: record a flake-rate observation + a mechanical AST check proving zero functional assertions. Produce ONE consolidated candidate list and ESCALATE to the operator for a single sign-off (do not delete anything before sign-off; do not scatter this across the split WPs). Record the signed-off dispositions in the Activity Log.
### T016a — Functional-assertion fingerprint baseline + enforcing check (R1 HIGH)
Before the splits, compute a mechanical AST fingerprint of the functional (non-timing) assertions per #4015 source file (assert-node extraction) and commit it as the baseline. Add `tests/architectural/test_timing_coverage_invariant.py` that re-extracts after the sweep and FAILS if any source file's per-PR functional-assertion set (count AND normalized text) drops below baseline — so NFR-003/SC-009 is ENFORCED mechanically, not by eyeball. WP06-09 green cannot hide a dropped/weakened functional assert.

### T016 — Coverage-mapping format
Define the per-split mapping row format (original_test → functional_assertion retained-verbatim-per-PR | timing_assertion relocated-test-id @performance budget-preserved) and document that EACH split WP (WP06-09) records its own rows in its Activity Log (event-sourced; no shared file to avoid cross-WP overlap). The aggregate no-coverage-loss invariant (per-PR functional count/text after ≥ before) is verified at review/accept across all split WPs.

## Validation
\`tests/architectural/test_performance_marker_guard.py\` stays green; a tiny self-test marks a \`@performance\` test using \`assert_timing_budget\` and the guard accepts it. ruff+mypy clean.
## Definition of Done
- Helper created + guard-clean (does NOT widen TIMING_ASSERTION_VOCABULARY).
- **T015 operator sign-off on the consolidated delete list is RECORDED and RESOLVED (blocking — WP06-09 must not apply any delete until this is signed off).**
- `test_timing_coverage_invariant.py` committed with the baseline fingerprint and passing; mapping format documented.
- Sole ownership of tests/_next_shard_map.py established; registration process noted.
## Reviewer guidance
- Confirm the helper does NOT widen TIMING_ASSERTION_VOCABULARY; confirm the delete list carries flake-rate + AST-zero-functional evidence and an operator sign-off before any deletion.
