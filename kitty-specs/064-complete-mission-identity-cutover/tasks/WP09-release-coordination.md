---
work_package_id: WP09
title: Release Coordination
dependencies: [WP08]
requirement_refs:
- FR-021
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
phase: Phase E - Release
assignee: ''
agent: "claude:sonnet-4.6:python-implementer:implementer"
shell_pid: "53197"
history:
- timestamp: '2026-04-06T05:39:39Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: kitty-specs/064-complete-mission-identity-cutover/
execution_mode: code_change
owned_files:
- kitty-specs/064-complete-mission-identity-cutover/release-readiness.md
---

# Work Package Prompt: WP09 – Release Coordination

## Objective

Verify that the external consumer (`spec-kitty-orchestrator`) is ready for the hard cutover. Document release readiness. This WP gates the production rollout per FR-021.

## Context

Priivacy-ai/spec-kitty-orchestrator#6 was filed with the complete command/error/parameter mapping tables. The cutover is not shippable until:
1. `spec-kitty-orchestrator` has been updated to use new command names, error codes, and `--mission` flag
2. The updated orchestrator has been validated against the renamed contract
3. Both repos release in lockstep (or orchestrator ships first)

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`

## Implementation

### T051: Verify Orchestrator Consumer Readiness

**Purpose**: Confirm the external consumer is updated.

**Steps**:
1. Check Priivacy-ai/spec-kitty-orchestrator#6 status: `gh issue view 6 --repo Priivacy-ai/spec-kitty-orchestrator`
2. If resolved: verify the PR/commit that resolved it updated all command names, error codes, and `--mission` flag
3. If not resolved: document what's blocking and flag as a release gate
4. Check for any other consumers: search for references to `feature-state`, `accept-feature`, `merge-feature` in other Priivacy-ai repos

### T052: Document Release Readiness

**Purpose**: Clear go/no-go signal for production rollout.

**Steps**:
1. Create `kitty-specs/064-complete-mission-identity-cutover/release-readiness.md`
2. Document:
   - Orchestrator consumer status (updated/pending)
   - Audit results (from WP08)
   - Conformance test results (from WP07)
   - All success criteria status (8 criteria from spec)
   - Go/no-go recommendation
3. If go: recommend release sequence (orchestrator first, then spec-kitty, or lockstep)
4. If no-go: document blockers

## Definition of Done

- [ ] Priivacy-ai/spec-kitty-orchestrator#6 status verified
- [ ] Release readiness document created
- [ ] All 8 success criteria assessed
- [ ] Clear go/no-go recommendation

## Risks

- External consumer may not be ready — this WP cannot force the timeline, only document the gate

## Activity Log

- 2026-04-06T09:10:42Z – claude:sonnet-4.6:python-implementer:implementer – shell_pid=53197 – Started implementation via action command
- 2026-04-06T09:11:47Z – claude:sonnet-4.6:python-implementer:implementer – shell_pid=53197 – Release readiness documented. Verdict: NO-GO pending orchestrator update.
