---
work_package_id: WP02
title: Documentation content authoring (Concern B)
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-007
- NFR-004
tracker_refs: []
planning_base_branch: feat/mission-step-creatability
merge_target_branch: feat/mission-step-creatability
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-creatability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-creatability unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/mission-steps/documentation/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/missions/mission-steps/documentation/**
- src/doctrine/missions/documentation/templates/**
role: implementer
tags: []
shell_pid: "2514500"
shell_pid_created_at: "1784288061.69"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer) before anything else.

## Objective
Make the `documentation` mission type creatable by authoring genuine content for its **7 sequence steps on their own step names** and adding the template refs the runtime contract requires. Depends on WP01 (clean surface).

## Context & FROZEN
- Steps (own names — do NOT use a software-dev `specify`/`plan` shape): `discover → audit → design → generate → validate → publish → accept`.
- **Q1 CONTRACT (C-010, hard predecessor — satisfied by WP01 landing + this WP)**: the runtime requests the literal `artifact_kind="spec"` at `mission create` and `"plan"` at `/plan`-setup, **generic across all types**. So documentation must author a step with `template.artifact_key: "spec"` and one with `"plan"`. See `contracts/creation-artifact-key.md`.
- **C-003**: `artifact_key` is the shared vocabulary (`"spec"`/`"plan"`); `template_file` is **per-type-unique** (no cross-type filename sharing — WP05 guards this).
- **NFR-004 genuine content**: real per-type exemplar prose. Machine floor: non-empty, **no `TODO`/`PLACEHOLDER`/`FIXME`** literals (the emptiness detector flags those). Substance is a reviewer gate.
- Do NOT edit `tests/doctrine/missions/test_prompt_emptiness.py` — WP05 owns it (C-011).

## Subtasks
### T008 — Template refs
- In the `documentation` step.yaml files, add a `template:` block to the step that produces the initial artifact with `artifact_key: spec`, `template_file: documentation-spec-template.md` (name is per-type; pick a documentation-vocabulary filename), and to a planning-equivalent step with `artifact_key: plan`, `template_file: documentation-plan-template.md`. Choose the hosting steps that best match documentation's flow (e.g. `discover`/`design`).

### T009 — Author discover/audit/design prompts
- Author `mission-steps/documentation/{discover,audit,design}/prompt.md`, **promoting** from each step's existing `guidelines.md` into the executable prompt shape (see `mission-steps/software-dev/research/prompt.md` for the *shape* only: `description:` frontmatter, `--mission <handle>` rules, `## User Input`/`$ARGUMENTS`, location pre-flight, Goal, What-to-do, Success Criteria). Documentation-domain content (Divio types, gap-analysis — see CLAUDE.md "Documentation Mission Patterns").

### T010 — Author generate/validate prompts
- Author `{generate,validate}/prompt.md` (promote from guidelines.md).

### T011 — Author publish/accept prompts
- Author `{publish,accept}/prompt.md` (promote from guidelines.md).

### T012 — Template files → documentation vocabulary
- In `missions/documentation/templates/`, the existing files are software-dev-shaped (`spec-template.md`, etc.). Rename/replace to the documentation vocabulary and create the `template_file`s referenced in T008 so they resolve via the 5-tier chain. Do NOT leave software-dev vocabulary.

### T013 — Verify creatable (red-first)
- Red-first: assert `mission create --mission-type documentation` currently fails, author the refs/content, then it passes (through the pre-existing creation entry point). Confirm no prompt contains dummy markers.

## Branch Strategy
Base `feat/mission-step-creatability`; worktree per `lanes.json`. `spec-kitty agent action implement WP02 --agent <tool>:<model>:python-pedro:implementer` (after WP01 approved).

## Definition of Done
Two distinct deliverables — do NOT conflate them (creatability is independent of prompt substance):
- **(a) Creatable (machine-falsifiable)**: `spec`+`plan` template refs present with documentation-unique `template_file`s that resolve; `mission create --mission-type documentation` succeeds + `/plan`-setup resolves. This proves ONLY the refs resolve — NOT that the prompts are good.
- **(b) Prompts substantive (reviewer-gated)**: all 7 `prompt.md` files are genuine documentation-domain exemplars (not filler), non-empty, marker-free. Green-creatable does NOT prove (b) — the reviewer must read the prompts.
- ruff/mypy/lint gates pass; no `test_prompt_emptiness.py` edits.

## ⚠️ Known transient red (do NOT block on it)
Authoring these prompts turns two **non-xfail** assertions in the WP05-owned `tests/doctrine/missions/test_prompt_emptiness.py` **hard-RED for `documentation`**: `test_seeded_prompt_is_zero_bytes` and `test_every_sequence_step_prompt_is_currently_blank`. This is **expected** — that file is owned solely by **WP05** (C-011), which reconciles the census after all three authoring WPs land. This WP is **forbidden** from touching it. **This WP's green-gate is scoped to its creatability proof (a) + lint — the reviewer must NOT block approval on the seeded-emptiness suite.** (The DRG-freshness gate does NOT trip: no extractor pass reads `step.template` until WP06.)

## Risks & Reviewer Guidance
- Reviewer: confirm own-step-names (not software-dev shape); `artifact_key` is exactly `"spec"`/`"plan"`; `template_file`s are documentation-unique; content is substantive per DoD (b) — read the prompts, don't rely on the emptiness floor. Honor the Known-transient-red note above.

## Activity Log

- 2026-07-17T11:16:26Z – claude:sonnet:python-pedro:implementer – shell_pid=2449409 – Assigned agent via action command
- 2026-07-17T11:32:34Z – claude:sonnet:python-pedro:implementer – shell_pid=2449409 – 7 prompt.md authored (promoted from guidelines.md, genuine documentation-domain content: Divio types, gap-analysis, generator invocation, ADR-shaped design decisions). Template refs: discover carries artifact_key=spec, design carries artifact_key=plan, both documentation-unique template_file (documentation-spec-template.md / documentation-plan-template.md, renamed from software-dev-shaped names). mission create --mission-type documentation verified red-before/green-after via create_mission_core. Ruff clean, DRG regenerate-graph --check FRESH, terminology guard green. Known transient red (out of scope, not touched): test_prompt_emptiness.py (WP05-owned, C-011). Additionally flagging 2 previously-unowned test files that also go red as a necessary side effect and are claimed by no WP's owned_files: tests/integration/test_mission_type_resolution_integration.py and tests/doctrine/missions/test_mission_type_repository.py::test_non_software_builtin_template_set_is_explicitly_null (whose own docstring anticipates this once Concern B lands) -- needs a reconciliation owner (WP05/WP06 or a follow-up), same shape as WP03/WP04 will independently trip for research/plan.
- 2026-07-17T11:34:24Z – claude:opus:reviewer-renata:reviewer – shell_pid=2514500 – Started review via action command
- 2026-07-17T11:41:22Z – user – shell_pid=2514500 – Review PASSED. Content substance (DoD b, the reviewer-only gate): all 7 prompts (discover/audit/design/generate/validate/publish/accept) are genuine documentation-domain exemplars promoted from guidelines.md into executable prompt shape (description frontmatter, --mission rules, $ARGUMENTS, location pre-flight, Goal/What-to-do/Success-Criteria/Handoff). They teach Divio four-type allocation, gap-analysis coverage matrices, generator invocation (Sphinx/JSDoc/rustdoc), ADR-shaped design decisions, iteration modes, accessibility gates, living-documentation cadence, publish/accept handoff -- NOT filler, NOT software-dev-shaped; every handoff references documentation's OWN step names. Creatability (DoD a): real resolver projects template_set={spec: documentation-spec-template.md, plan: documentation-plan-template.md} (non-null, documentation-unique) -- proven by the resolution-integration failure output. Q1/C-010: discover->artifact_key 'spec', design->artifact_key 'plan' (exact); C-003 template_files per-type-unique. Markers: case-sensitive TODO/PLACEHOLDER/FIXME scan clean. Scope: only owned doctrine dirs touched; test_prompt_emptiness.py NOT edited (C-011 honored); template files are git renames. Gates: ruff clean, DRG regenerate-graph --check FRESH. REDS are ONLY the two expected transients: (1) WP05-owned C-011 test_prompt_emptiness.py (7 seeded-blank now-filled + exhaustive-list, 8 fails); (2) the types-null/uncreatable trio test_non_software_builtin_template_set_is_explicitly_null[documentation], test_domain_mission_resolves_zero_software_dev_doctrine[documentation], test_null_template_mapping_fails_closed_with_stable_diagnostics[documentation] -- intentional behavior change from documentation becoming creatable, folded into WP05 reconciliation, NOT a WP02 defect. Non-blocking follow-up for reconciliation owner: the template rename drifts CI selection baseline fast-tests-core-misc-nodeids.txt (guard suites themselves green, 1485 passed); sibling src/specify_cli/missions/documentation/templates/ still carries old names (out of WP02 owned scope; runtime resolves through doctrine copy).
