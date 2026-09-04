---
description: "Work package for strengthening glossary skills with model validation"
---

# Work Packages: Strengthen Glossary Skills with Model Validation

**Inputs**: `spec.md`, `plan.md`
**Organization**: one atomic package; the public route and detailed workflow are not split between implementers.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Capture the baseline for three synthetic smoke scenarios before changing the skills | WP01 | No |
| T002 | Add a short route to `spk-doctrine-glossary/SKILL.md` | WP01 | No |
| T003 | Add the model pressure-test to `spec-kitty-glossary-context/SKILL.md` | WP01 | No |
| T004 | Repeat the three smoke scenarios and compare them with the baseline | WP01 | No |
| T005 | Run validators, targeted tests, and the scope scan | WP01 | No |

---

## WP01 - Three Model Quality Checks (P1, MVP)

**Goal**: atomically add a code cross-check, concrete edge scenario, and all-three ADR gate to the existing glossary workflow.

**Independent validation**: three synthetic prompts demonstrate the required behavior; validators and targeted tests pass; the diff remains within the allowed scope.

**Prompt**: `tasks/WP01-model-pressure-test.md`
**Requirements**: FR-001-FR-006, NFR-001-NFR-003, C-001-C-004
**Dependencies**: none.

### Included Subtasks

T001 Capture the failing-first/snapshot baseline for three synthetic smoke scenarios before changing the skills

T002 Add a short route to `src/charter/offering/skills/spk-doctrine-glossary/SKILL.md`

T003 Add a conditional model pressure-test to `src/charter/offering/skills/spec-kitty-glossary-context/SKILL.md`

T004 Repeat the same smoke scenarios and confirm the code cross-check, edge scenario, and ADR gate

T005 Run both skill validators, `tests/doctrine/test_spk_skill_pack.py`, and the scope scan

### Actual Status

- T001-T004 completed: the failing-first baseline did not find the required mechanisms; the repeated smoke test confirmed all three.
- T005 completed: both validators passed, targeted tests reported `6 passed`, and the scope scan found only the two allowed product files.

### Risks and Mitigations

- Broad trigger: apply the pressure-test only to modeling work or contested terms.
- Duplication: detailed rules live only in the legacy detailed skill; the public skill only routes to it.
- Documentation noise: recommend an ADR only when all three gates pass.
- Unverified claim: require a hypothesis label when code evidence is unavailable.

## Coverage Summary

| Requirements | Package |
|--------------|---------|
| FR-001-FR-006 | WP01 |
| NFR-001-NFR-003 | WP01 |
| C-001-C-004 | WP01 |
