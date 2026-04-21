---
work_package_id: WP08
title: Kill charter.resolver survivors (core target ≥ 80 %)
dependencies:
- WP07
requirement_refs:
- FR-009
- FR-013
- FR-014
- FR-015
- NFR-001
- NFR-003
- NFR-004
- NFR-005
- NFR-006
- NFR-007
planning_base_branch: feature/711-mutant-slaying
merge_target_branch: feature/711-mutant-slaying
branch_strategy: Planning artifacts for this feature were generated on feature/711-mutant-slaying. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/711-mutant-slaying unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T039
- T040
phase: Phase 3 - Charter core
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/charter/
execution_mode: code_change
owned_files:
- tests/charter/test_resolver.py
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – Kill charter.resolver survivors (CORE, ≥ 80 %)

## Objectives & Success Criteria

- Drive mutation score on `charter.resolver` to **≥ 80 %** (FR-009, NFR-001). Current baseline: 68 survivors. Fresh re-sample required.
- Starts Phase 3. `charter.resolver` gates charter-based governance decisions.

## Context & Constraints

- **Source under test**: `src/charter/resolver.py` — `resolve_governance`, `resolve_governance_for_profile`, `collect_governance_diagnostics`, `GovernanceResolutionError`.
- **Test file**: `tests/charter/test_resolver.py` (existing; extend. Note: test file opens with `pytestmark = pytest.mark.fast` — keep it).
- **Precondition**: Re-sample `uv run mutmut run "charter.resolver*"` before starting.

## Branch Strategy

- **Strategy**: lane-per-WP (`spec-kitty implement WP08 --base WP07`)
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T036 – Kill `resolve_governance` precedence survivors

- Governance resolution has a precedence chain (charter > fallback > default). Apply **Boundary Pair** to the precedence checks.
- Create fixtures where charter partially overrides: full-override, partial-override, no-override — assert the observed governance matches expected merged state.

### Subtask T037 – Kill fallback-branch survivors

- Fallback paths fire when charter sources are missing/malformed.
- **Bi-Directional Logic**: test all four combinations of (charter-present, fallback-present). Assert the correct branch fires for each.
- **Parallel?**: `[P]` with T038, T039.

### Subtask T038 – Kill `resolve_governance_for_profile` survivors

- Profile-specific resolution layers agent-profile governance over base governance.
- **Non-Identity Inputs**: use distinct profile IDs and governance payloads so mutations that conflate two profiles are caught.
- **Parallel?**: `[P]` with T037, T039.

### Subtask T039 – Kill `collect_governance_diagnostics` survivors

- Diagnostic collection aggregates warnings/errors across resolution tiers.
- Test that diagnostics are accumulated in order (not reversed by a mutant).
- Test that empty-diagnostics case returns an empty collection (not None).
- **Parallel?**: `[P]` with T037, T038.

### Subtask T040 – Rescope mutmut, verify ≥ 80 %, append findings residuals

- `rm mutants/src/charter/resolver.py.meta`
- `uv run mutmut run "charter.resolver*"` → ≥ 80 % (CORE target).
- Append residuals subheading.

## Risks & Mitigations

- **Risk**: Charter fixture construction is non-trivial (see existing `_write_charter_files` helper).
  - **Mitigation**: Reuse the existing helper; extend it with new parameters rather than creating parallel helpers.
- **Risk**: `charter.resolver` has deep import graph; mutation testing may take longer than 15 min.
  - **Mitigation**: If T040 exceeds NFR-004's 15 min budget, scope further by function pattern (`charter.resolver.x_resolve_governance*`).

## Review Guidance

- Scoped mutmut score ≥ 80 % (CORE — strict).
- `_write_charter_files` helper reused (not duplicated).
- No new `non_sandbox` markers.

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.
- 2026-04-20T18:28:52Z – unknown – Descoped: Phase 3 charter.* modules deferred to future mission
