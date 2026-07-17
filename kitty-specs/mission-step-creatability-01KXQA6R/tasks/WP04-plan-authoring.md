---
work_package_id: WP04
title: Plan content authoring (Concern B — heaviest, author-fresh)
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- NFR-004
tracker_refs: []
planning_base_branch: feat/mission-step-creatability
merge_target_branch: feat/mission-step-creatability
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-creatability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-creatability unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/mission-steps/plan/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/missions/mission-steps/plan/**
- src/doctrine/missions/plan/templates/**
role: implementer
tags: []
shell_pid: "2566471"
shell_pid_created_at: "1784288969.97"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer) before anything else.

## Objective
Make the `plan` mission type creatable. This is the **heaviest** authoring WP: `plan` has **no `guidelines.md`** and an **empty `templates/`** (only `.gitkeep`+`README`), so both the 4 step prompts **and** the scaffold template files are **authored fresh**. Depends on WP01.

## Context & FROZEN
- Steps (own names): `specify → research → plan → review`. ⚠️ **Name collision**: `specify`/`plan` collide with software-dev step ids, but `plan` is decomposition/design/decision work (**no code**). Do **NOT** clone the software-dev exemplars (software-dev's `specify/prompt.md` is 36 KB, code-feature-spec-shaped). Author plan-domain content (problem-decomposition, MoSCoW, ADR-drafting, premortem — per `missions/plan/governance-profile.yaml`).
- **Q1 CONTRACT (C-010)**: author a step with `template.artifact_key: "spec"` + one with `"plan"`. Generic keys; per-type `template_file` (C-003 — must NOT reuse software-dev's `spec-template.md`/`plan-template.md` filenames).
- **NFR-004**: genuine plan-domain content; non-empty; no `TODO`/`PLACEHOLDER`/`FIXME`.
- Do NOT edit `test_prompt_emptiness.py` (WP05, C-011).
- If this WP exceeds ~7 subtasks in practice, split scaffolds (T020) from prompts (T021/T022) into a WP04b — flag at implement time.

## Subtasks
### T019 — Template refs
- Add `template:` blocks on plan's `specify` step (`artifact_key: spec`, `template_file: plan-spec-skeleton.md`) and `plan` step (`artifact_key: plan`, `template_file: plan-plan-skeleton.md`). Plan-unique filenames.

### T020 — Author-fresh scaffold template files
- Create `missions/plan/templates/plan-spec-skeleton.md` + `plan-plan-skeleton.md` (plan-domain scaffolds — problem statement, decomposition, options/ADR, risks; NO code/API sections). These are the `template_file`s the refs point at.

### T021 — Author specify/research prompts
- `mission-steps/plan/{specify,research}/prompt.md`, author-fresh in the executable prompt shape (use `mission-steps/software-dev/research/prompt.md` for *shape* only). Plan-domain: `specify` = frame the problem/goals; `research` = gather decision inputs.

### T022 — Author plan/review prompts
- `{plan,review}/prompt.md` author-fresh. `plan` = decompose + sequence + decide (ADR); `review` = validate the decomposition/decision.

### T023 — Verify creatable (red-first)
- Red-first: `mission create --mission-type plan` fails → author → passes; **and** the `/plan`-setup path resolves the `"plan"` key. No dummy markers; no software-dev shape clone.

## Branch Strategy
Base `feat/mission-step-creatability`; worktree per `lanes.json`. `spec-kitty agent action implement WP04 --agent <tool>:<model>:python-pedro:implementer` (after WP01 approved).

## Definition of Done
Two distinct deliverables — do NOT conflate (creatability is independent of prompt/scaffold substance):
- **(a) Creatable (machine-falsifiable)**: `spec`+`plan` refs with plan-unique `template_file`s that resolve; `mission create --mission-type plan` succeeds AND `/plan`-setup resolves the `plan` key. Proves ONLY refs resolve.
- **(b) Content substantive (reviewer-gated)**: 4 `prompt.md` + 2 scaffold templates are genuine plan-domain (decomposition/decision, NO code/API, no software-dev clone), non-empty, marker-free. Green-creatable does NOT prove (b).
- lint/gates pass; no `test_prompt_emptiness.py` edits.

## ⚠️ Known transient red (do NOT block on it)
Authoring these prompts turns two **non-xfail** assertions in the WP05-owned `tests/doctrine/missions/test_prompt_emptiness.py` **hard-RED for `plan`**: `test_seeded_prompt_is_zero_bytes` and `test_every_sequence_step_prompt_is_currently_blank`. This is **expected** — owned solely by **WP05** (C-011), reconciled after all three authoring WPs land. This WP is **forbidden** from touching it. **Green-gate is scoped to creatability (a) + lint — the reviewer must NOT block on the seeded-emptiness suite.**

## Risks & Reviewer Guidance
- **Highest contamination risk** (name collision). Reviewer: confirm plan content is decomposition/decision (no code/API), `template_file`s are plan-unique (not software-dev filenames), `artifact_key` exactly `"spec"`/`"plan"`, content substantive per DoD (b). Honor the Known-transient-red note.

## Activity Log

- 2026-07-17T11:17:04Z – claude:sonnet:python-pedro:implementer – shell_pid=2451485 – Assigned agent via action command
- 2026-07-17T11:48:30Z – claude:sonnet:python-pedro:implementer – shell_pid=2451485 – Plan mission-type now creatable: spec/plan template refs (plan-unique filenames plan-spec-skeleton.md/plan-plan-skeleton.md, C-003) resolve at both mission-create ('spec' key) and /plan-setup ('plan' key); 4 author-fresh plan-domain prompts (decomposition/MoSCoW/ADR/premortem, NO code/API) + 2 scaffold templates, marker-free per NFR-004. Shared null-tests + test_prompt_emptiness.py left as expected WP05-reconciled transient reds (4 shared files reverted per coord to avoid WP03 lane conflict).
- 2026-07-17T11:49:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=2566471 – Started review via action command
- 2026-07-17T11:55:11Z – user – shell_pid=2566471 – Review passed: genuine plan-domain content confirmed (Problem Decomposition/MoSCoW/Eisenhower/ADR/Premortem/Bounded-Context per governance-profile; NO code/API/impl sections; explicit build->software-dev redirects) — NOT a software-dev clone. Creatability proven: project_template_set('plan')={'spec':'plan-spec-skeleton.md','plan':'plan-plan-skeleton.md'}, plan-unique filenames (C-003), exact artifact_keys spec/plan (Q1/C-010). Scope-clean: WP04 commit touches only mission-steps/plan/** + missions/plan/templates/** (8 files, 0 shared test files, test_prompt_emptiness.py untouched). Marker-free (NFR-004); terminology guard green. Reds are ONLY the 6 named WP05-owned transient reconciliations (test_seeded_prompt_is_zero_bytes[plan/*], test_every_sequence_step_prompt_is_currently_blank, test_non_software_builtin_template_set_is_explicitly_null[plan]) — honored per Known-transient-red note.
