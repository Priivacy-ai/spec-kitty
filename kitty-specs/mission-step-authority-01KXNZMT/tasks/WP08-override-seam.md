---
work_package_id: WP08
title: Override seam + live consumer — recommended_model_tier as an offer
dependencies:
- WP01
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: feat/mission-step-authority
merge_target_branch: feat/mission-step-authority
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-authority unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
phase: Phase 2 - Offer seam
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1108285"
shell_pid_created_at: "1784229426.63"
history:
- at: '2026-07-16T17:35:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/step_offer_seam.py
create_intent:
- src/doctrine/missions/step_offer_seam.py
- tests/doctrine/model_task_routing/test_override_precedence.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/step_offer_seam.py
- src/doctrine/model_task_routing/evaluator.py
- tests/doctrine/model_task_routing/test_override_precedence.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – Override seam + live consumer

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for `python-pedro` (`implementer`, `claude`).

---

## Objective

Make `recommended_model_tier` a real, falsifiable **advisory offer**: read it through one named seam with a
defined precedence (charter/runtime override **>** step offer), and ship at least **one live consumer** so the
override precedence can be tested (NFR-003). Depends on WP01 (the field). Parallel with the WP02→WP07 spine.

## Design boundary (D4 / C-002)
Doctrine only **offers**; routing authority stays with charter/runtime. The step is the single source of the
model-tier **offer**, NOT the routing **decision**. `recommended_role` is the existing `agent_profile` (no new
field). The full ≥4-site role/model consolidation (FR-009) is **deferred** — out of scope here.

## Subtasks

### T024 — Named offer seam [P]
Create `src/doctrine/missions/step_offer_seam.py`: a small, pure function that, given a step's
`recommended_model_tier` (the offer) and an optional charter/runtime override, returns the effective value with
**override-wins** precedence and surfaces the offer as advisory-only. Define the precedence explicitly and
document that doctrine never overrides a routing decision.

### T025 — Wire the live consumer + precedence test [P]
Wire the seam into `src/doctrine/model_task_routing/evaluator.py:229` (`evaluate`) as the live consumer of
`recommended_model_tier` — so the offer actually influences a model-tier decision unless overridden.
`tests/doctrine/model_task_routing/test_override_precedence.py` (NFR-003): with an override present, the override
value wins in 100% of cases and the step offer is advisory-only; with no override, the offer is used.

## Branch Strategy
Base/merge: `feat/mission-step-authority`. Implement: `spec-kitty agent action implement WP08 --agent <name>`.

## Definition of Done
- [ ] `step_offer_seam.py` reads the offer with a defined override-wins precedence.
- [ ] `evaluator.py` consumes `recommended_model_tier` (a real, live surface — not dead schema).
- [ ] Override-precedence test proves override > offer (NFR-003); no routing-authority leak (C-002).
- [ ] `ruff`/`mypy --strict` clean; complexity ≤15; `regenerate-graph --check` fresh.

## Risks / Reviewer guidance
- An offer with no consumer is unfalsifiable — reviewer confirms the evaluator actually reads it.
- Do NOT let the doctrine offer override a charter/runtime routing decision (C-002).
- Do NOT consolidate the other role/model sites here (FR-009 deferred).

## Requirements: FR-008

## Activity Log

- 2026-07-16T19:08:12Z – claude:sonnet:python-pedro:implementer – shell_pid=1079105 – Assigned agent via action command
- 2026-07-16T19:16:31Z – claude:sonnet:python-pedro:implementer – shell_pid=1079105 – Offer seam (override>offer) + live evaluator consumer; existing evaluator behavior unchanged when offer absent; tests/ruff/mypy green
- 2026-07-16T19:17:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=1108285 – Started review via action command
- 2026-07-16T19:19:58Z – user – shell_pid=1108285 – Review passed: override-wins is UNCONDITIONAL — seam returns override whenever it is not None regardless of the step offer (verified via parametrized ('premium'->'low') disagreement case: effective==override). Change is strictly ADDITIVE: two keyword-only args + new model_tier field all default None; _resolve_model_tier returns None when both absent so catalog/profile candidate scoring, override_mode, objective are byte-for-byte unchanged (test_offer_seam_does_not_change_catalog_or_profile_candidates + legacy==explicit_none). Live consumer confirmed: executor.py:82 -> evaluate -> _resolve_model_tier -> resolve_model_tier_offer, seam not dead. C-002 no routing-authority leak; no recommended_role invented; no FR-009 consolidation. Scope clean (only 4 owned files in WP08 commit). Gates: 16 pytest pass, ruff clean, mypy --strict clean, DRG fresh, no feature terminology.
