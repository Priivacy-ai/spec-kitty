---
work_package_id: WP02
title: Routing evaluator (objective scorer)
dependencies:
- WP01
- WP04
requirement_refs:
- FR-003
- NFR-004
- C-004
tracker_refs:
- '2364'
planning_base_branch: design/model-discipline-dispatch-2364
merge_target_branch: design/model-discipline-dispatch-2364
branch_strategy: Planning artifacts for this mission were generated on design/model-discipline-dispatch-2364. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/model-discipline-dispatch-2364 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
phase: Phase 1 - Implementation
assignee: ''
agent: "claude"
shell_pid: '619732'
history:
- at: '2026-07-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/model_task_routing/
create_intent:
- src/doctrine/model_task_routing/evaluator.py
- tests/doctrine/test_model_task_routing_evaluator.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/model_task_routing/evaluator.py
- tests/doctrine/test_model_task_routing_evaluator.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Routing evaluator (objective scorer)

## Load Agent Profile (python-pedro)

Use the `/ad-hoc-profile-load` skill to load the `python-pedro` agent profile (role: `implementer`) before doing any work, and behave according to its guidance while executing this prompt.

## Objectives & Success Criteria

- Deliver a deterministic evaluator that computes a recommendation from `task_fit` × `weights` under `objective`, applying `tier_constraints` and resolving `override_policy` precedence.
- **Capability lever**: `objective: quality_first` is how capability is expressed (there is no separate capability tier in the schema) — the evaluator must actually rank the strongest-fit model for high-judgment task types under `quality_first`.
- Under `override_policy: advisory`, emit both the catalog pick and the profile's declared `model` (from WP04) as provenance-tagged candidates — enforce neither.
- Pure/stub-testable: no I/O in `evaluator.py`; it consumes WP01's loaded catalog + task_type and the WP04 profile field as plain inputs.
- Deterministic: same inputs always produce the same output (NFR-004).

## Context & Constraints

- Source of truth: `kitty-specs/model-discipline-dispatch-binding-01KWPW36/spec.md` FR-003, NFR-004, C-004; `plan.md` IC-02; `tasks.md` WP02 section; `adversarial-review.md` Round 2 fold #5 (US2 precedence resolution).
- Depends on **WP01** (catalog loader + task_type vocabulary) and **WP04** (the profile `model`/`effort` field) — both must be available to consume; do not stub around them.
- Precedence semantics under `advisory` were pinned by the post-spec squad: emit catalog + profile as provenance-tagged candidates, enforce neither. Do not silently prefer one over the other.
- `override_policy` modes `gated`/`required` are out of scope (C-004) — the evaluator may read the mode field but only `advisory` is exercised/tested.
- Cover edge cases: no match in `task_fit`, empty `task_fit`, `tier_constraints` capping the winner.
- Note: `evaluator.py` is an ORPHAN until WP03 wires it into `invoke()` — expected; dead-modules validated at the WP03 tip. Per-WP reviewers: do NOT reject WP02 on the expected evaluator orphan.
- Consumed profile contract (from WP04): read `profile.preferred_model` and `profile.effort` (aliases `model`/`effort` in YAML).
- Keep `ruff`/`mypy` clean; complexity ≤ 15.

## Subtasks

- [ ] T007 [red-first] `tests/doctrine/test_model_task_routing_evaluator.py`: quality_first ranks strongest-fit for a high-judgment task_type; `tier_constraints` cap respected; deterministic (same inputs → same output). RECORD RED.
- [ ] T008 [red-first] override precedence under `advisory`: catalog pick + profile declaration both surfaced with provenance, neither enforced. RECORD RED.
- [ ] T009 [FR-003] `src/doctrine/model_task_routing/evaluator.py`: pure scorer (no I/O) consuming WP01's loaded catalog + task_type + the WP04 profile field.
- [ ] T010 [NFR-004] determinism + edge cases (no match, empty task_fit) covered.
- [ ] T011 `ruff`/`mypy` clean; complexity ≤ 15.

## Branch Strategy

- **Strategy**: Planning artifacts are generated on design/model-discipline-dispatch-2364; completed changes merge back there.
- **Planning base branch**: `design/model-discipline-dispatch-2364`
- **Merge target branch**: `design/model-discipline-dispatch-2364`

## Definition of Done

- [ ] T007/T008 recorded RED pre-fix, then GREEN post-implementation.
- [ ] `evaluator.py` is pure (no I/O), consumes the WP01 catalog/task_type and WP04 profile field, and ranks strongest-fit under `quality_first`.
- [ ] `tier_constraints` capping and `override_policy: advisory` precedence (both candidates, provenance-tagged, neither enforced) are covered by tests.
- [ ] Determinism proven: same catalog + task_type + profile → same recommendation across repeated calls.
- [ ] Edge cases (no match, empty `task_fit`) handled without raising.
- [ ] `ruff check` and `mypy` clean on owned files; complexity ≤ 15.
- [ ] No changes outside `owned_files`.

## Activity Log

- 2026-07-04T18:12:53Z – claude – shell_pid=619732 – Moved to for_review
- 2026-07-04T18:13:05Z – user – shell_pid=619732 – APPROVE (opus, uv-run): red-first genuine; see adversarial-review.
