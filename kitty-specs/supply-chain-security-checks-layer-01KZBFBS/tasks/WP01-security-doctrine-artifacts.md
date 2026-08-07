---
work_package_id: WP01
title: Author the security doctrine artifacts
dependencies: []
requirement_refs:
  - FR-001
  - FR-002
  - FR-003
  - FR-009
planning_base_branch: feat/supply-chain-security-checks-layer
merge_target_branch: feat/supply-chain-security-checks-layer
branch_strategy: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
subtasks:
  - T001
  - T002
  - T003
phase: Phase 1 - Doctrine layer authoring
agent: "cursor:composer:python-pedro:implementer"
shell_pid: "47161"
history:
  - at: '2026-08-06T14:15:00Z'
    actor: system
    action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: packs/built-in/
create_intent:
  - packs/built-in/directives/051-supply-chain-install-safety.directive.yaml
  - packs/built-in/tactics/security/supply-chain-install-safety.tactic.yaml
execution_mode: code_change
model: ''
owned_files:
  - packs/built-in/directives/051-supply-chain-install-safety.directive.yaml
  - packs/built-in/tactics/architecture/dependency-hygiene.tactic.yaml
  - packs/built-in/tactics/security/supply-chain-install-safety.tactic.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 - Author the security doctrine artifacts

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile below before implementing.

- **Profile**: `doctrine-daphne`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Author the core doctrine artifacts for the supply-chain security layer so downstream workflow/profile wiring has a stable policy base.

Success means:

- `051-supply-chain-install-safety` exists with the agreed policy pillars:
  - official registry authenticity checks
  - package freshness/last-update visibility
  - deny-by-default lifecycle script approvals
  - Node Active LTS awareness and skew disclosure
  - incident-list and IoC posture
- `dependency-hygiene` is extended for JS/TS without regressing existing Java/Python guidance.
- `supply-chain-install-safety` tactic exists and is actionable/reviewable.

## Context & Constraints

- Read:
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/spec.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/plan.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/research.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/contracts/security-checks-layer-contract.md`
- Keep v1 advisory posture: no hard fail-closed transition semantics are introduced in this WP.
- Threat model is class-based, not static package-denylist based.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
- **Planning base branch**: feat/supply-chain-security-checks-layer
- **Merge target branch**: feat/supply-chain-security-checks-layer

## Subtasks & Detailed Guidance

### T001 – Author directive `051-supply-chain-install-safety`

- **Purpose**: Establish policy-level governance for install-time and dependency supply-chain risk handling.
- **Steps**:
  1. Create the new directive file under `packs/built-in/directives/`.
  2. Encode all required policy areas from spec FR-001 and updated user asks.
  3. Add clear references to related tactics/directives.
- **Files**: `packs/built-in/directives/051-supply-chain-install-safety.directive.yaml`
- **Parallel?**: No (foundation for T002/T003).

### T002 – Extend `dependency-hygiene` for JS/TS

- **Purpose**: Align existing hygiene guidance with JS/TS supply-chain realities.
- **Steps**:
  1. Add JS/TS applicability.
  2. Add registry/freshness/script/LTS expectations.
  3. Preserve existing non-JS guidance and intent.
- **Files**: `packs/built-in/tactics/architecture/dependency-hygiene.tactic.yaml`
- **Parallel?**: Yes (after T001 draft stabilizes).

### T003 – Add `supply-chain-install-safety` tactic

- **Purpose**: Provide operational checklist semantics for implement/review execution.
- **Steps**:
  1. Create tactic file under `packs/built-in/tactics/security/`.
  2. Include actionable checks and evidence expectations.
  3. Include adversarial evidence/disposition touchpoint language consistent with research decision.
- **Files**: `packs/built-in/tactics/security/supply-chain-install-safety.tactic.yaml`
- **Parallel?**: Yes (after T001 draft stabilizes).

## Test Strategy

- `pytest tests/doctrine/ -q` (targeted doctrine artifact validation surface)
- Any mission-local schema checks that validate directive/tactic structure

## Risks & Mitigations

- **Risk**: Hardcoding incident-specific package versions in core doctrine.
  - **Mitigation**: keep directive class-based; cite CAS/vendor incident lists as external authority.
- **Risk**: Inconsistent script policy language between directive and tactic.
  - **Mitigation**: keep wording aligned and cross-referenced.

## Review Guidance

- Confirm the new directive is present and complete.
- Confirm `dependency-hygiene` retains prior language while adding JS/TS controls.
- Confirm tactic instructions are operational (not aspirational prose only).

## Activity Log

- 2026-08-06T14:15:00Z – system – Prompt created.
- 2026-08-06T14:44:43Z – cursor:composer:python-pedro:implementer – shell_pid=47161 – Assigned agent via action command
