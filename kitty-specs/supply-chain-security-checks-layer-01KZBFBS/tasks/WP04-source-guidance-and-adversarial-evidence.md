---
work_package_id: WP04
title: Update SOURCE mission-step guidance and adversarial evidence coverage
dependencies:
  - WP01
  - WP02
requirement_refs:
  - FR-007
  - FR-010
  - NFR-005
planning_base_branch: feat/supply-chain-security-checks-layer
merge_target_branch: feat/supply-chain-security-checks-layer
branch_strategy: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
subtasks:
  - T013
  - T014
  - T015
phase: Phase 4 - SOURCE prompt and evidence guidance
history:
  - at: '2026-08-06T14:18:00Z'
    actor: system
    action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: packs/built-in/missions/mission-steps/software-dev/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
  - packs/built-in/missions/mission-steps/software-dev/plan/prompt.md
  - packs/built-in/missions/mission-steps/software-dev/plan/guidelines.md
  - packs/built-in/missions/mission-steps/software-dev/implement/prompt.md
  - packs/built-in/missions/mission-steps/software-dev/implement/guidelines.md
  - packs/built-in/missions/mission-steps/software-dev/review/prompt.md
  - packs/built-in/missions/mission-steps/software-dev/review/guidelines.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 - Update SOURCE mission-step guidance and adversarial evidence coverage

## ⚡ Do This First: Load Agent Profile

- **Profile**: `doctrine-daphne`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Update software-dev SOURCE mission-step guidance so generated agent surfaces inherit the new security checks and adversarial evidence expectations.

Success means:

- `plan`, `implement`, `review` SOURCE prompts/guidelines explicitly reference the new security behavior.
- Adversarial cadence and disposition expectations are explicit for plan/research and review-facing artifacts.
- No generated agent-copy directories are edited.

## Context & Constraints

- Read:
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/spec.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/plan.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/research.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/contracts/adversarial-evidence-contract.md`
- Edit SOURCE files only in `src/doctrine/missions/mission-steps/software-dev/`.
- Keep guidance advisory-compatible in v1.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
- **Planning base branch**: feat/supply-chain-security-checks-layer
- **Merge target branch**: feat/supply-chain-security-checks-layer

## Subtasks & Detailed Guidance

### T013 – Update `plan` mission-step SOURCE guidance

- **Purpose**: Ensure design-time security and adversarial cadence expectations are explicit.
- **Steps**: Add concise guidance for security checks and adversarial disposition evidence in planning outputs.
- **Files**: `packs/built-in/missions/mission-steps/software-dev/plan/prompt.md`, `packs/built-in/missions/mission-steps/software-dev/plan/guidelines.md`
- **Parallel?**: No.

### T014 – Update `implement` mission-step SOURCE guidance

- **Purpose**: Ensure implementation-stage script discipline and Node LTS posture checks are explicit.
- **Steps**: Add guidance on deny-by-default script approvals, registry/freshness checks, and risk disclosure.
- **Files**: `packs/built-in/missions/mission-steps/software-dev/implement/prompt.md`, `packs/built-in/missions/mission-steps/software-dev/implement/guidelines.md`
- **Parallel?**: Yes.

### T015 – Update `review` mission-step SOURCE guidance

- **Purpose**: Ensure review requires explicit adversarial finding dispositions and security evidence.
- **Steps**: Add reviewer-facing checkpoints tying decisions to evidence and disposition states.
- **Files**: `packs/built-in/missions/mission-steps/software-dev/review/prompt.md`, `packs/built-in/missions/mission-steps/software-dev/review/guidelines.md`
- **Parallel?**: Yes.

## Test Strategy

- Targeted tests validating mission-step contract/guidance linkage where applicable.
- Spot-check generated command surfaces after upgrade path in later integration WP if needed.

## Risks & Mitigations

- **Risk**: accidental edits to generated copies.
  - **Mitigation**: restrict owned files to SOURCE path only.
- **Risk**: guidance drift from contracts.
  - **Mitigation**: align wording with adversarial evidence contract and review during WP05.

## Review Guidance

- Confirm only SOURCE files changed.
- Confirm adversarial evidence scope matches resolved decision.
- Confirm wording is actionable, not abstract.

## Activity Log

- 2026-08-06T14:18:00Z – system – Prompt created.
