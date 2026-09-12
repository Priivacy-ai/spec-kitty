---
work_package_id: WP03
title: Bind targeted agent profiles and graph edges
dependencies:
  - WP01
requirement_refs:
  - FR-006
  - FR-009
planning_base_branch: feat/supply-chain-security-checks-layer
merge_target_branch: feat/supply-chain-security-checks-layer
branch_strategy: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
subtasks:
  - T009
  - T010
  - T011
  - T012
phase: Phase 3 - Profile governance alignment
history:
  - at: '2026-08-06T14:17:00Z'
    actor: system
    action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: packs/built-in/agent_profiles/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
  - packs/built-in/agent_profiles/reviewer-renata.agent.yaml
  - packs/built-in/agent_profiles/implementer-ivan.agent.yaml
  - packs/built-in/agent_profiles/node-norris.agent.yaml
  - packs/built-in/agent_profiles/frontend-freddy.agent.yaml
  - packs/built-in/agent_profiles/python-pedro.agent.yaml
  - packs/built-in/agent_profiles/java-jenny.agent.yaml
  - packs/built-in/agent_profiles/architect-alphonso.agent.yaml
  - packs/built-in/agent_profile.graph.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 - Bind targeted agent profiles and graph edges

## ⚡ Do This First: Load Agent Profile

- **Profile**: `curator-carla`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Align profile-level behavior with the new security doctrine layer.

Success means:

- Review and implementation profiles expose consistent supply-chain checks.
- Node-script and Active-LTS awareness rules appear where expected.
- Profile graph edges connect profiles to the new directive/tactic layer.

## Context & Constraints

- Read:
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/spec.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/plan.md`
  - `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/contracts/security-checks-layer-contract.md`
- This WP must enhance existing profiles; do not create a new built-in AppSec profile in v1.
- Keep each profile’s primary role intact.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on feat/supply-chain-security-checks-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/supply-chain-security-checks-layer unless the human explicitly redirects the landing branch.
- **Planning base branch**: feat/supply-chain-security-checks-layer
- **Merge target branch**: feat/supply-chain-security-checks-layer

## Subtasks & Detailed Guidance

### T009 – Update `reviewer-renata`

- **Purpose**: Make review security posture explicit and evidence-driven.
- **Steps**: Add directive/tactic references and explicit adversarial evidence disposition expectation in security-audit context.
- **Files**: `packs/built-in/agent_profiles/reviewer-renata.agent.yaml`
- **Parallel?**: No.

### T010 – Update implementation-first profiles

- **Purpose**: Apply script and LTS posture to core implementer surfaces.
- **Steps**: Update `implementer-ivan`, `node-norris`, and `frontend-freddy`.
- **Files**: corresponding profile YAML files.
- **Parallel?**: Yes.

### T011 – Update supporting profiles

- **Purpose**: Ensure profile coverage consistency beyond primary implementers.
- **Steps**: Update `python-pedro`, `java-jenny`, `architect-alphonso` with relevant cross-surface checks.
- **Files**: corresponding profile YAML files.
- **Parallel?**: Yes.

### T012 – Update profile graph edges

- **Purpose**: Ensure reachability/delivery through profile graph relationships.
- **Steps**: Add or update `requires`/`suggests` edges in `agent_profile.graph.yaml` for the new directive/tactic path.
- **Files**: `packs/built-in/agent_profile.graph.yaml`
- **Parallel?**: No.

## Test Strategy

- Profile-resolution and doctrine-reachability tests covering updated profiles and graph edges.

## Risks & Mitigations

- **Risk**: inconsistent expectations across profiles.
  - **Mitigation**: validate each targeted profile against the same checklist dimensions.
- **Risk**: graph edges present but not delivered in context.
  - **Mitigation**: include context-resolution verification in tests.

## Review Guidance

- Verify no new persona is introduced.
- Verify targeted profiles all include expected security references.
- Verify `agent_profile.graph.yaml` edges are coherent and scoped.

## Activity Log

- 2026-08-06T14:17:00Z – system – Prompt created.
