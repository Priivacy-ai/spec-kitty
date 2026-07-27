---
work_package_id: WP05
title: 'Guards: emptiness retirement + cross-type uniqueness (Concern B)'
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-008
- NFR-004
- NFR-006
tracker_refs: []
planning_base_branch: feat/mission-step-creatability
merge_target_branch: feat/mission-step-creatability
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-creatability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-creatability unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/doctrine/missions/
create_intent:
- tests/doctrine/missions/test_template_file_uniqueness.py
execution_mode: code_change
owned_files:
- tests/doctrine/missions/test_prompt_emptiness.py
- tests/doctrine/missions/test_template_file_uniqueness.py
role: implementer
tags: []
shell_pid: "2682653"
shell_pid_created_at: "1784292009.94"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer) before anything else.

## Objective
Own the coupled edit to the emptiness guard (C-011 — a single owner prevents the three content WPs merge-conflicting on the golden count), retire the seeded-blank scaffold once all 16 prompts are filled, and add the cross-type `template_file` uniqueness guard (NFR-006). Depends on WP02/03/04 (their authored prompts are the inputs).

## Context & FROZEN
- `tests/doctrine/missions/test_prompt_emptiness.py` is owned **only** by this WP (C-011).
- The 16 seeded-blank prompts are documentation (7) + research (5) + plan (4); `retrospect` steps are excluded (`in_action_sequence: false`).
- `test_seeded_prompt_is_zero_bytes` goes hard-RED on the first authored byte — so the census MUST move in lockstep with the content WPs.

## Subtasks
### T024 — Shrink the census
- As WP02/03/04 land their prompts, in `test_prompt_emptiness.py`: remove each filled `(type, step)` from `_SEEDED_BLANK_STEPS` (`:54`), drop its `xfail` marker, decrement the golden `16` (`:176`, `# golden-count: cardinality-is-contract`), and update `_SEQUENCE_STEPS_BY_TYPE` (`:161`) as needed.

### T025 — Retire the scaffold → positive assertion (with a structural floor)
- Once all 16 are filled (`_SEEDED_BLANK_STEPS` empty, golden `0`), **retire** the seeded-blank scaffold (the `xfail`/`zero-bytes`/`_currently_blank` parametrized tests become vacuous — remove them). Replace with a **positive** assertion over every sequence-step `prompt.md` across the four types, raising the machine floor beyond mere non-emptiness (partial defence against filler-stub prompts): each prompt is (i) non-empty, (ii) free of `TODO`/`PLACEHOLDER`/`FIXME`, **(iii) contains `$ARGUMENTS`, (iv) contains at least one `## ` heading, (v) exceeds a minimum length** (e.g. ≥ N chars — pick a floor that a real prompt clears but a one-liner fails).
- **NFR-004 substance-gate hook — explicit location**: since this WP owns only test files, add the reviewer-checklist substance requirement as a module-level docstring/comment block at the top of the positive-assertion test in `test_prompt_emptiness.py`, stating that the machine floor is necessary-not-sufficient and genuine per-type substance is verified in WP02/03/04 review (NFR-004). (The structural floor above is the machine half; this comment is the human half.)

### T026 — Cross-type uniqueness guard
- Add `tests/doctrine/missions/test_template_file_uniqueness.py`: assert **no two mission types project the same `template_file`** (NFR-006) — iterate the four types' `project_template_set`, collect `template_file`s, assert all distinct. This prevents plan/software-dev name-collision contamination.

## Branch Strategy
Base `feat/mission-step-creatability`; worktree per `lanes.json`. `spec-kitty agent action implement WP05 --agent <tool>:<model>:python-pedro:implementer` (after WP02/03/04 approved).

## Definition of Done
- `_SEEDED_BLANK_STEPS` empty, golden count retired-or-0; positive non-empty assertion green; uniqueness guard green; ruff/mypy clean; `tests/doctrine/` green.

## Risks & Reviewer Guidance
- Reviewer: confirm no content-WP touched this test file (ownership); the positive assertion actually covers all four types' sequence steps; the uniqueness guard reads the *projected* `template_file`s (post-cutover), not a removed field.

## Activity Log

- 2026-07-17T11:57:14Z – claude:sonnet:python-pedro:implementer – shell_pid=2601037 – Assigned agent via action command
- 2026-07-17T12:39:58Z – claude:sonnet:python-pedro:implementer – shell_pid=2601037 – Emptiness scaffold retired → positive prompt floor (non-empty + $ARGUMENTS + heading + min-len); cross-type template_file uniqueness guard; reconciled documentation+plan null-tests across 4 shared files (rationale-backed leeway; research done by WP03) — all now GREEN (116 passed, no transients remain). ruff clean, DRG fresh. Orchestrator finished handoff (implementer stalled on backgrounded arch gate, which passed).
- 2026-07-17T12:40:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=2682653 – Started review via action command
