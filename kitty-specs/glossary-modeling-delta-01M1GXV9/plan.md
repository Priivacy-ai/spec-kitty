# Implementation Plan: Strengthen Glossary Skills with Model Validation

**Branch**: `codex/glossary-modeling-delta` | **Date**: 2026-09-02 | **Specification**: `spec.md`

## Summary

Add three focused mechanisms to the existing glossary workflow: cross-check material model claims against available code, challenge ambiguous terms with a concrete edge scenario, and apply a three-condition gate before recommending an ADR. Do not import the external `domain-modeling` skill, its file structure, or its general workflow.

## Technical Context

**Format**: Markdown instructions for Codex skills
**Primary dependencies**: existing `spk-doctrine-glossary` and `spec-kitty-glossary-context`
**Storage**: N/A
**Validation**: skill validator, doctrine skill-pack tests, and three synthetic behavioral smoke scenarios
**Target platform**: Codex skills on supported platforms
**Change type**: focused update to existing instruction artifacts
**Size constraint**: at most two product `SKILL.md` files, with no new runtime code or new skill

## Charter Check

- One canonical source: changes are limited to `src/charter/offering/skills/`; installed global projections are not edited.
- Terminology integrity: the new checks extend the existing concepts, aliases, conflicts, and semantic-drift workflow.
- ATDD: capture three observable smoke scenarios before changing the instructions; each must pass afterward.
- Narrow scope: runtime glossary, registry, CLI, templates, and ADR documents remain unchanged.
- PR-only delivery: the implementation remains on the task branch; the maintainer/operator performs the merge.

No charter violations require an exception.

## Technical Solution

### 1. Public Routing

Add a short route to `src/charter/offering/skills/spk-doctrine-glossary/SKILL.md`: when a request shapes a domain model rather than merely curating terminology, the detailed workflow must apply the model pressure-test. The public skill does not duplicate the detailed instructions.

### 2. Detailed Model Pressure-Test

Add a compact conditional section to `src/charter/offering/skills/spec-kitty-glossary-context/SKILL.md` for model-shaping work and contested terms:

1. Check material claims against available types, APIs, and tests; when evidence is unavailable, label the claim as a hypothesis.
2. Challenge an ambiguous term with one concrete edge scenario and refine its definition, boundary, or relationship when they disagree.
3. Recommend an ADR only when the decision is hard to reverse, surprising without context, and involves a real trade-off.

### 3. Result Validation

- Run the three synthetic scenarios before implementation and record the observable baseline.
- Repeat the same scenarios after implementation.
- Run both skill validators and the targeted doctrine skill-pack test.
- Scan the diff to confirm it adds no `CONTEXT.md`, `CONTEXT-MAP.md`, new skill, runtime code, or ADR template.

## Change Structure

```text
src/charter/offering/skills/
|-- spk-doctrine-glossary/SKILL.md
`-- spec-kitty-glossary-context/SKILL.md

tests/doctrine/
`-- test_spk_skill_pack.py        # Existing regression test; no required edit
```

**Structure decision**: one work package owns both instruction files because the public route and detailed workflow form one contract and must change atomically.

## Implementation Map

### IC-01 - Domain-Model Quality Checks

- **Purpose**: add the three agreed mechanisms without creating a parallel workflow.
- **Requirements**: FR-001-FR-006, NFR-001-NFR-003, C-001-C-004.
- **Surfaces**: two canonical `SKILL.md` files and existing validation commands.
- **Dependencies**: none.
- **Risks**: an overly broad trigger, duplication of the glossary workflow, and excessive ADR creation.
- **Mitigations**: conditional trigger, one detailed authority, all-three ADR gate, and no new file structure.

## Codemap

`docs/codemap/codemap.lock` is absent. A codemap update is unnecessary because module boundaries, dependencies, routes, storage, and data flow do not change; the product diff contains only instruction artifacts.

## Delivery Gates

1. Reconfirm the baseline before product edits.
2. Capture failing-first/snapshot evidence for the three synthetic scenarios.
3. Implement only in the task-owned worktree.
4. Run validators, targeted tests, and the scope scan.
5. Review and open the PR; installation/projection and merge remain out of scope.
