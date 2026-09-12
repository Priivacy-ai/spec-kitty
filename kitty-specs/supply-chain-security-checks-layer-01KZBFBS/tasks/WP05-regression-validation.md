---
work_package_id: WP05
title: Regression validation and readiness verification
dependencies:
  - WP02
  - WP03
  - WP04
requirement_refs:
  - FR-008
  - NFR-001
  - NFR-002
  - NFR-003
  - NFR-004
planning_base_branch: feat/supply-chain-security-checks-layer
merge_target_branch: feat/supply-chain-security-checks-layer
branch_strategy: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
subtasks:
  - T016
  - T017
  - T018
  - T019
  - T020
phase: Phase 5 - Verification and readiness
history:
  - at: '2026-08-06T14:19:00Z'
    actor: system
    action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer-renata
authoritative_surface: tests/
create_intent:
  - tests/doctrine/test_supply_chain_security_layer.py
  - tests/charter/test_supply_chain_profile_bindings.py
  - tests/architectural/test_supply_chain_step_contract_advisory.py
execution_mode: code_change
model: ''
owned_files:
  - tests/doctrine/test_supply_chain_security_layer.py
  - tests/charter/test_supply_chain_profile_bindings.py
  - tests/architectural/test_supply_chain_step_contract_advisory.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 - Regression validation and readiness verification

## ⚡ Do This First: Load Agent Profile

- **Profile**: `reviewer-renata`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Add and run targeted tests proving the new security layer is wired correctly and remains advisory-compatible in v1.

Success means:

- At least one green test path exists for each binding class:
  - action wiring
  - step-contract wiring
  - profile binding
- No new fail-closed transition gate behavior is introduced.
- Adversarial evidence expectations are represented in verification artifacts.

## Context & Constraints

- Read:
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/spec.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/plan.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/contracts/security-checks-layer-contract.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/contracts/adversarial-evidence-contract.md`
- This WP begins only after WP02, WP03, and WP04 land.
- Keep tests scoped and deterministic; avoid brittle snapshot-only assertions where semantic assertions are available.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
- **Planning base branch**: feat/supply-chain-security-checks-layer
- **Merge target branch**: feat/supply-chain-security-checks-layer

## Subtasks & Detailed Guidance

### T016 – Add action-context wiring tests

- **Purpose**: Prove `plan`/`implement`/`review` context includes security-layer artifacts.
- **Steps**: Add targeted doctrine/context tests with explicit assertions per action.
- **Files**: `tests/doctrine/test_supply_chain_security_layer.py`
- **Parallel?**: No.

### T017 – Add step-contract advisory compatibility tests

- **Purpose**: Prove security stages were added without introducing fail-closed gate behavior.
- **Steps**: Assert presence/order of security stages and advisory-compatible gate semantics.
- **Files**: `tests/architectural/test_supply_chain_step_contract_advisory.py`
- **Parallel?**: No.

### T018 – Add profile-binding tests

- **Purpose**: Prove targeted profiles resolve with expected security checks.
- **Steps**: Assert key profile references/expectations across targeted profile set.
- **Files**: `tests/charter/test_supply_chain_profile_bindings.py`
- **Parallel?**: No.

### T019 – Run targeted suites and remediate regressions

- **Purpose**: Validate mission-local changes end-to-end.
- **Steps**:
  1. Run targeted suites for doctrine/charter/architectural surfaces.
  2. Fix any regressions introduced by this mission.
- **Files**: tests and touched doctrine files as needed.
- **Parallel?**: No.

### T020 – Run terminology guard

- **Purpose**: Ensure canonical mission terminology remains compliant.
- **Steps**: Run `pytest tests/architectural/test_no_legacy_terminology.py`.
- **Files**: none expected (validation step).
- **Parallel?**: Yes (after T016–T018 additions).

## Test Strategy

- `pytest tests/doctrine/ -q`
- `pytest tests/charter/ -q`
- `pytest tests/architectural/ -q`
- `pytest tests/architectural/test_no_legacy_terminology.py -q`

## Risks & Mitigations

- **Risk**: incomplete coverage gives false confidence.
  - **Mitigation**: enforce one explicit test path per binding class.
- **Risk**: advisory compatibility accidentally broken.
  - **Mitigation**: include explicit gate-semantics assertion.

## Review Guidance

- Confirm each requirement class has corresponding tests.
- Confirm test assertions are semantic, not shallow existence checks only.
- Confirm terminology guard remains green.

## Activity Log

- 2026-08-06T14:19:00Z – system – Prompt created.
