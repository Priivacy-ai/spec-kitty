---
work_package_id: WP02
title: Wire software-dev workflow surfaces
dependencies:
  - WP01
requirement_refs:
  - FR-004
  - FR-005
  - FR-009
planning_base_branch: feat/supply-chain-security-checks-layer
merge_target_branch: feat/supply-chain-security-checks-layer
branch_strategy: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
subtasks:
  - T004
  - T005
  - T006
  - T007
  - T008
phase: Phase 2 - Action and step-contract wiring
history:
  - at: '2026-08-06T14:16:00Z'
    actor: system
    action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: packs/built-in/missions/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
  - packs/built-in/missions/software-dev/actions/plan/index.yaml
  - packs/built-in/missions/software-dev/actions/implement/index.yaml
  - packs/built-in/missions/software-dev/actions/review/index.yaml
  - packs/built-in/missions/built_in_step_contracts/plan.step-contract.yaml
  - packs/built-in/missions/built_in_step_contracts/implement.step-contract.yaml
  - packs/built-in/missions/built_in_step_contracts/review.step-contract.yaml
  - packs/built-in/action.graph.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 - Wire software-dev workflow surfaces

## ⚡ Do This First: Load Agent Profile

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Bind the security layer into software-dev action and step-contract surfaces.

Success means:

- `plan`, `implement`, `review` action indexes include the new security artifacts.
- Step contracts include security stages for all three actions.
- Existing v1 advisory compatibility remains intact (no new fail-closed transition gate introduced).

## Context & Constraints

- Read:
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/spec.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/plan.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/contracts/security-checks-layer-contract.md`
- WP01 must land first (directive/tactic IDs become authoritative inputs here).
- Do not alter unrelated mission types.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
- **Planning base branch**: feat/supply-chain-security-checks-layer
- **Merge target branch**: feat/supply-chain-security-checks-layer

## Subtasks & Detailed Guidance

### T004 – Wire action indexes

- **Purpose**: Include security layer artifacts in software-dev action context.
- **Steps**: Update `plan/index.yaml`, `implement/index.yaml`, `review/index.yaml` to include directive/tactics per plan.
- **Files**: action index files under `packs/built-in/missions/software-dev/actions/`.
- **Parallel?**: No.

### T005 – Update action graph scope edges

- **Purpose**: Ensure graph-level scope resolution includes new security bindings.
- **Steps**: Add/update `scope` edges in `packs/built-in/action.graph.yaml` for targeted actions.
- **Files**: `packs/built-in/action.graph.yaml`
- **Parallel?**: Yes (after T004 artifact list is known).

### T006 – Add plan security step

- **Purpose**: Make design-time security checks explicit before implementation.
- **Steps**: Introduce a plan security stage with delegates to the appropriate tactic/directive.
- **Files**: `packs/built-in/missions/built_in_step_contracts/plan.step-contract.yaml`
- **Parallel?**: No.

### T007 – Add implement security step

- **Purpose**: Run supply-chain checks before standard quality gate in implement flow.
- **Steps**: Add a security stage preceding quality gate semantics.
- **Files**: `packs/built-in/missions/built_in_step_contracts/implement.step-contract.yaml`
- **Parallel?**: No.

### T008 – Add review security step with advisory compatibility

- **Purpose**: Ensure review includes explicit security stage while preserving existing gate behavior.
- **Steps**: Add review security stage and confirm no new fail-closed transition gate handler is introduced.
- **Files**: `packs/built-in/missions/built_in_step_contracts/review.step-contract.yaml`
- **Parallel?**: No.

## Test Strategy

- Targeted doctrine/contract tests validating action and step-contract resolution.
- Focused assertions that transition gate semantics remain advisory-compatible.

## Risks & Mitigations

- **Risk**: accidental hard-gate behavior.
  - **Mitigation**: explicitly preserve existing gate handler setup and add tests asserting no new fail-closed handler path.
- **Risk**: inconsistent action coverage.
  - **Mitigation**: verify all three actions include security layer references.

## Review Guidance

- Confirm all three action indexes are updated.
- Confirm each of plan/implement/review step-contracts includes security stage.
- Confirm no fail-closed transition handler was introduced.

## Activity Log

- 2026-08-06T14:16:00Z – system – Prompt created.
