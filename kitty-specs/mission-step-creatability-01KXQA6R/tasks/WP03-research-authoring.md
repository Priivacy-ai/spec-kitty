---
work_package_id: WP03
title: Research content authoring (Concern B)
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-007
- NFR-004
tracker_refs: []
planning_base_branch: feat/mission-step-creatability
merge_target_branch: feat/mission-step-creatability
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-creatability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-creatability unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/mission-steps/research/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/missions/mission-steps/research/**
- src/doctrine/missions/research/templates/**
role: implementer
tags: []
shell_pid: "2544610"
shell_pid_created_at: "1784288715.79"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer) before anything else.

## Objective
Make the `research` mission type creatable by authoring genuine content for its **5 sequence steps on their own step names** + the runtime template refs. Depends on WP01.

## Context & FROZEN
- Steps (own names — NOT a software-dev shape): `scoping → methodology → gathering → synthesis → output`. (`research/mission-runtime.yaml` also lists `accept`, but there is no `mission-steps/research/accept/` dir — not part of the 5.)
- **Q1 CONTRACT (C-010)**: author a step with `template.artifact_key: "spec"` (creation) + one with `"plan"` (`/plan`-setup). Generic keys; per-type `template_file` (C-003).
- **NFR-004**: genuine research-domain content; non-empty; no `TODO`/`PLACEHOLDER`/`FIXME`.
- Do NOT edit `test_prompt_emptiness.py` (WP05 owns it, C-011).

## Subtasks
### T014 — Template refs
- Add `template:` blocks: `artifact_key: spec`/`template_file: research-spec-template.md` on the scoping-equivalent step; `artifact_key: plan`/`template_file: research-plan-template.md` on the methodology-equivalent step. Filenames are research-vocabulary and per-type-unique.

### T015 — Author scoping/methodology prompts
- `mission-steps/research/{scoping,methodology}/prompt.md`, promoting from each step's `guidelines.md` into the executable prompt shape. Research-domain framing (dialectic-research, forensic-repository-audit, citation-discipline tactics per the governance profile).

### T016 — Author gathering/synthesis/output prompts
- `{gathering,synthesis,output}/prompt.md` (promote from guidelines.md).

### T017 — Template files → research vocabulary
- `missions/research/templates/` currently ships software-dev-shaped `spec-template.md`/`plan-template.md`/`tasks-template.md`. Rename/replace to research vocabulary; create the `template_file`s referenced in T014 so they resolve.

### T018 — Verify creatable (red-first)
- Red-first through the creation entry point: `mission create --mission-type research` fails → author → passes. No dummy markers.

## Branch Strategy
Base `feat/mission-step-creatability`; worktree per `lanes.json`. `spec-kitty agent action implement WP03 --agent <tool>:<model>:python-pedro:implementer` (after WP01 approved).

## Definition of Done
Two distinct deliverables — do NOT conflate (creatability is independent of prompt substance):
- **(a) Creatable (machine-falsifiable)**: `spec`+`plan` refs with research-unique `template_file`s that resolve; `mission create --mission-type research` succeeds. Proves ONLY refs resolve.
- **(b) Prompts substantive (reviewer-gated)**: all 5 `prompt.md` files are genuine research-domain exemplars (not filler), non-empty, marker-free. Green-creatable does NOT prove (b).
- ruff/mypy/lint gates pass; no `test_prompt_emptiness.py` edits.

## ⚠️ Known transient red (do NOT block on it)
Authoring these prompts turns two **non-xfail** assertions in the WP05-owned `tests/doctrine/missions/test_prompt_emptiness.py` **hard-RED for `research`**: `test_seeded_prompt_is_zero_bytes` and `test_every_sequence_step_prompt_is_currently_blank`. This is **expected** — that file is owned solely by **WP05** (C-011), which reconciles the census after all three authoring WPs land. This WP is **forbidden** from touching it. **Green-gate is scoped to creatability (a) + lint — the reviewer must NOT block on the seeded-emptiness suite.**

## Risks & Reviewer Guidance
- Reviewer: own-step-names; `artifact_key` exactly `"spec"`/`"plan"`; research-unique `template_file`s (no software-dev vocabulary); substantive content per DoD (b) — read the prompts. Honor the Known-transient-red note.

## Activity Log

- 2026-07-17T11:16:55Z – claude:sonnet:python-pedro:implementer – shell_pid=2451485 – Assigned agent via action command
- 2026-07-17T11:42:28Z – claude:sonnet:python-pedro:implementer – shell_pid=2451485 – Research mission-type made creatable: template refs on scoping(spec)/methodology(plan) -> research-spec/plan-template.md (git-mv, resolve at package tier); all 5 prompt.md authored from guidelines.md with genuine research-domain content (dialectic-research/forensic-repository-audit/citation-discipline), marker-free, $ARGUMENTS+headings. Creatability proven red-first via resolve_configured_template + mission create --mission-type research. Re-pinned 4 sibling stale null-pins (test_mission_type_repository, test_resolved_mission_type_context, test_runtime_seam, test_mission_type_resolution_integration). FROZEN test_prompt_emptiness.py untouched (6 research reds expected, WP05/C-011). ruff+DRG-fresh+mypy(mine) clean.
- 2026-07-17T11:45:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=2544610 – Started review via action command
- 2026-07-17T11:50:40Z – user – shell_pid=2544610 – Review passed: research is creatable (project_template_set -> {spec: research-spec-template.md, plan: research-plan-template.md}; both files exist; integration test resolves both at PACKAGE_DEFAULT tier). Q1/C-003 exact: scoping.template.artifact_key='spec', methodology='plan', per-type-unique research-vocabulary template_file names. All 5 prompts (scoping/methodology/gathering/synthesis/output) are genuine research-domain exemplars on their own step names -- dialectic-research, forensic-repository-audit, citation-discipline;  + headings + gate-aware substance; marker-free; not software-dev-shaped. 4 sibling null-test re-pins correct: null parametrizations narrowed to still-unauthored documentation/plan, positive research pins mirror the software-dev pattern, integration pin exercises the real resolver. 92 re-pinned tests pass, ruff clean. Only expected transient reds are the 5 WP05-owned test_prompt_emptiness.py seeded-blank census failures (frozen file untouched, C-011).
