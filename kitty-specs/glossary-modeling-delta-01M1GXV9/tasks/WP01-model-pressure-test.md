---
work_package_id: WP01
title: Three model quality checks
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-003
- C-004
tracker_refs:
- spk-glossary-9v0
planning_base_branch: codex/glossary-modeling-delta
merge_target_branch: codex/glossary-modeling-delta
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: null
history:
- 2026-09-02 created
- 2026-09-02 implemented and verified locally
authoritative_surface: src/charter/offering/skills/
owned_files:
- src/charter/offering/skills/spk-doctrine-glossary/SKILL.md
- src/charter/offering/skills/spec-kitty-glossary-context/SKILL.md
execution_mode: instruction_change
role: implementer
tags:
- glossary
- domain-modeling
---

## Goal

Add exactly three mechanisms to the existing glossary workflow: cross-check the model against code, challenge a term with a concrete edge scenario, and apply a three-condition ADR gate. Do not import the external skill wholesale.

## Validate First

Before editing `SKILL.md`, capture the current workflow's response to three synthetic prompts:

1. A model description contradicts types or tests in a small public fixture.
2. The term `status` has two possible meanings and one edge scenario.
3. Of four decisions, three each fail one ADR condition and one passes all three.

The baseline must show which required mechanism is absent or not guaranteed. A parser or fixture error is not evidence.

## Implementation

1. Add only a route from the public skill to the detailed workflow for model-shaping requests.
2. Add one conditional section to the detailed skill without repeating existing glossary rules.
3. For the code cross-check, require a concrete inspected surface or an honest hypothesis label.
4. For an ambiguous term, require one concrete edge scenario without imposing one on already canonical, uncontested terms.
5. Require all three conditions to pass before recommending an ADR.

## Prohibited Scope Expansion

- A new skill or glossary store.
- `CONTEXT.md` / `CONTEXT-MAP.md`.
- Changes to the runtime glossary, CLI, registry, ADR templates, or installed global projection.
- A general rewrite of the existing glossary workflow.

## Definition of Done

- The three repeated smoke scenarios demonstrate the expected behavior.
- Both modified skills pass `quick_validate.py`.
- `tests/doctrine/test_spk_skill_pack.py` passes.
- The scope scan confirms only the two allowed product files.
- The diff is focused, does not duplicate the existing authority, and contains no external framework boilerplate.

## Local Validation Result

- Failing-first baseline: four expected signals were absent.
- Repeated smoke test: all four expected signals are present.
- `quick_validate.py`: both skill files are valid.
- `tests/doctrine/test_spk_skill_pack.py`: `6 passed`.
- Product scope: only the two files listed in `owned_files` changed.
