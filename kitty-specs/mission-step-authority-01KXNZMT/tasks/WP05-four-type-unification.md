---
work_package_id: WP05
title: Four-type unification + red-flags — mission-steps/ layout for all 4
dependencies:
- WP01
- WP02
requirement_refs:
- FR-005
- FR-013
tracker_refs: []
planning_base_branch: feat/mission-step-authority
merge_target_branch: feat/mission-step-authority
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-authority unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
phase: Phase 3 - Unification
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1254942"
shell_pid_created_at: "1784232022.75"
history:
- at: '2026-07-16T17:35:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/mission-steps/documentation/
create_intent:
- tests/doctrine/missions/test_referential_integrity.py
- tests/doctrine/missions/test_prompt_emptiness.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/mission-steps/documentation/**
- src/doctrine/missions/mission-steps/research/**
- src/doctrine/missions/mission-steps/plan/**
- tests/doctrine/missions/test_referential_integrity.py
- tests/doctrine/missions/test_prompt_emptiness.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Four-type unification + red-flags

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for `python-pedro` (`implementer`, `claude`).

---

## Objective

Give documentation / research / plan the **same `mission-steps/<type>/<step>/` step-authority layout** software-dev
has, so all four types share one structure. Author `step.yaml` per sequence step; **seed a blank `prompt.md`** for
every prompt-less step and red-test the emptiness (no content invented — S-C fills them). Depends on WP01 (fields)
+ WP02 (projection).

## Context (grounded — read carefully)
- software-dev **duplicates**: it has BOTH `actions/<step>/{guidelines.md, index.yaml}` (the DRG **node** source)
  AND `mission-steps/software-dev/<step>/{step.yaml, prompt.md, guidelines.md}` (the step authority). Match that.
- **DO NOT touch `missions/<type>/actions/*/index.yaml`** — it is the action-**node** source (`extractor.py:674`).
  Leaving it untouched keeps node count at 280 (NFR-002 0-delta). True de-dup of the actions/↔mission-steps/
  guidelines duplication is a **follow-up**, not S-B (sw-dev has the same duplication today).
- Content census (verified): documentation (7 sequence steps) + research (5) have `actions/<step>/guidelines.md`
  but **NO prompt.md**; `plan` (4) has neither (only empty `index.yaml`). `prompt_template` stays **required**
  (WP01) — so seed blank prompt files.
- Sequences: documentation `[discover, audit, design, generate, validate, publish, accept]`; research
  `[scoping, methodology, gathering, synthesis, output]`; plan `[specify, research, plan, review]`.
  `retrospect` (documentation, research) is NOT in sequence → `in_action_sequence: false`.

## Subtasks

### T014 — documentation → mission-steps/ [P]
For each of documentation's 7 sequence steps, create `mission-steps/documentation/<step>/step.yaml` (id,
display_name, step_type, `prompt_template: prompt.md`, `sequence_index`, `in_action_sequence: true`); copy the
existing `actions/<step>/guidelines.md` → `mission-steps/documentation/<step>/guidelines.md` (match sw-dev's
duplicated layout); also author `retrospect` step.yaml with `in_action_sequence: false`.

### T015 — research → mission-steps/ [P]
Same for research's 5 sequence steps + `retrospect` (in_action_sequence:false). Copy existing guidelines.

### T016 — plan step.yaml + seed the 16 blank prompts
- Author `mission-steps/plan/<step>/step.yaml` for plan's 4 sequence steps (no guidelines to copy — plan has none).
- **Seed a blank/empty `prompt.md`** in every one of the **16** prompt-less step dirs (documentation 7 + research 5 + plan 4) so the required `prompt_template` resolves to a real (empty) file. A blank placeholder is not invented content (C-004).

### T017 — Emptiness red test + referential-integrity + dispatch-invariance
- `tests/doctrine/missions/test_prompt_emptiness.py`: assert **no step prompt is empty/dummy** → this is **RED** for the 16 seeded blanks (accepted; S-C fills to green). Name each red step so the gap is legible.
- `tests/doctrine/missions/test_referential_integrity.py` (NFR-001b): each type's projected `action_sequence` round-trips to the current authored value; every referenced artifact that exists resolves; copied guidelines are byte-identical to the source.
- Dispatch-invariance (NFR-006): assert `spec-kitty next` produces identical dispatch decisions before/after adding step.yaml to the 3 types (the composed-action path stays inert while `agent_profile` is null).

## Branch Strategy
Base/merge: `feat/mission-step-authority`. Implement: `spec-kitty agent action implement WP05 --agent <name>`.

## Definition of Done
- [ ] All 4 types have `mission-steps/<type>/<step>/step.yaml` for their sequence steps (+ retrospect flagged false).
- [ ] 16 blank `prompt.md` seeded; **prompt-emptiness test RED** for exactly those 16 (named), green elsewhere.
- [ ] `actions/*/index.yaml` untouched → node count 280 (0-delta); `regenerate-graph --check` fresh.
- [ ] Referential-integrity (3 types) + dispatch-invariance (NFR-006) green.
- [ ] `ruff`/`mypy` clean where applicable.

## Risks / Reviewer guidance
- If `actions/*/index.yaml` is moved/deleted, action nodes vanish → DRG delta. Reviewer confirms it is untouched.
- Do NOT invent prompt content — a blank file + red test is the correct disposition (DD-06).
- Keep this WP ≤ its subtasks; if the move balloons, split plan-only out (its shape — author + all-red — differs).

## Requirements: FR-005, FR-013

## Activity Log

- 2026-07-16T19:44:19Z – claude:sonnet:python-pedro:implementer – shell_pid=1195962 – Assigned agent via action command
- 2026-07-16T19:59:51Z – claude:sonnet:python-pedro:implementer – shell_pid=1195962 – 4-type mission-steps/ layout + 16 blank prompts + emptiness-gap (16 named, xfail) + referential-integrity + dispatch-invariance; actions/index.yaml untouched → DRG 280/757/10 fresh
- 2026-07-16T20:00:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=1254942 – Started review via action command
- 2026-07-16T20:05:35Z – user – shell_pid=1254942 – Review passed (reviewer-renata). CRITICAL INVARIANT: no actions/*/index.yaml or any index.yaml touched (git diff --name-only clean) → DRG regenerate-graph --check FRESH, load_built_in_graph() = 280 nodes / 757 edges / 10 orphans (0-delta NFR-002). step.yaml order matches authored mission_types/*.yaml action_sequence exactly: documentation discover..accept (0-6)+retrospect(false), research scoping..output (0-4)+retrospect(false), plan specify..review (0-3). All 18 prompt.md are 0 bytes. NFR-001b referential-integrity + guidelines byte-identity (filecmp shallow=False) + dispatch-invariance (resolve_mission_type_context unchanged, all agent_profile null) exercise real production paths (not synthetic). 16-step emptiness gap VISIBLE-not-blocking: 16 named xfail(strict=False), anti-vacuity guard proves files genuinely zero-bytes, exhaustiveness guard reads FS directly (exactly 16, retrospect correctly excluded). Gates: pytest tests/doctrine/ = 2680 passed / 16 xfailed / 0 real fail; ruff + mypy --strict clean on both new test files. Scope clean: only mission-steps/{documentation,research,plan}/** + 2 test files (no sw-dev dir, no actions/ change).
