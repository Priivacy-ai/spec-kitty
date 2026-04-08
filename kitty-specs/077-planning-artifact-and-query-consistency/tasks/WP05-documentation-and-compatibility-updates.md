---
work_package_id: WP05
title: Documentation and Compatibility Updates
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- C-004
- FR-017
- FR-018
- FR-020
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
agent: "opencode:gpt-5.4:python-reviewer:reviewer"
history:
- timestamp: '2026-04-08T15:01:02Z'
  event: created
  actor: opencode
authoritative_surface: docs/
execution_mode: planning_artifact
owned_files:
- docs/index.md
- docs/explanation/runtime-loop.md
- docs/reference/cli-commands.md
- docs/reference/agent-subcommands.md
tags: []
---

# WP05: Documentation and Compatibility Updates

## Objective

Update the active user-facing docs so they teach exactly one public contract for:

- planning-artifact work as repository-root execution outside the execution lane graph
- query mode as `spec-kitty next --mission-run <slug>`
- fresh-run query JSON as `not_started + preview_step`
- the stale JSON transition from flat fields to the canonical nested `stale` object

This WP is intentionally `planning_artifact` so the mission dogfoods its own runtime contract after the earlier code WPs land.

## Success Criterion

After WP01-WP04 land, the active docs under `docs/` consistently:

- show `spec-kitty next --mission-run <slug>` for query mode
- explain that fresh runs return `mission_state = not_started` plus `preview_step`
- explain that callers still passing `--agent` in query mode are using a compatibility form, not the primary contract
- describe planning-artifact work as repository-root execution outside the lane graph

## Context

This WP should start last.

Why:

- it depends on the final code behavior from WP01-WP04
- it is itself a planning-artifact WP, so running it exercises the repo-root planning path introduced by this mission
- docs drift is one of the core user-facing problems this mission is fixing

Use the contract docs in `kitty-specs/077-planning-artifact-and-query-consistency/contracts/` as the source of truth while updating the active docs.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Implementation command: `spec-kitty implement WP05`
- Execution workspace behavior: this WP is `planning_artifact`; after WP01-WP04 land, `/spec-kitty.implement` should resolve it to repository root rather than a lane worktree
- Dependency note: do not start until WP01, WP02, WP03, and WP04 are complete

## Scope

Allowed files are limited to the frontmatter `owned_files` list.

Primary surfaces:

- `docs/index.md`
- `docs/explanation/runtime-loop.md`
- `docs/reference/cli-commands.md`
- `docs/reference/agent-subcommands.md`

Do not edit `README.md` in this WP unless a reviewer explicitly extends scope later.

## Implementation Guidance

### Subtask T024: Update the highest-traffic docs first

**Purpose**: Fix the most visible entry points before deeper reference surfaces.

**Files**:

- `docs/index.md`
- `docs/reference/cli-commands.md`

**Steps**:

1. Replace any query-mode examples that require `--agent` with the canonical `--mission-run` form.
2. Update any explanation that treats `unknown` as the valid fresh-run query state.
3. Add the `not_started + preview_step` language where query-mode JSON is described.
4. Keep advancing-mode examples explicit: `--agent` plus `--result`.

**Validation**:

- [ ] high-traffic docs show the canonical query syntax
- [ ] no fresh-run example teaches `unknown` as valid

### Subtask T025: Update deeper runtime and agent command references

**Purpose**: Make the longer-form docs align with the same public contract.

**Files**:

- `docs/explanation/runtime-loop.md`
- `docs/reference/agent-subcommands.md`

**Steps**:

1. Update the runtime-loop explanation to separate query mode from advancing mode clearly.
2. Update agent command references so workspace resolution is described as execution-mode-aware, not lane-only.
3. Mention repository-root planning work explicitly where status and execution behavior are described.
4. Keep terminology aligned with the mission/spec canon.

**Validation**:

- [ ] runtime-loop docs distinguish query vs advance cleanly
- [ ] agent subcommand docs no longer imply all WPs require lane membership

### Subtask T026: Add explicit compatibility notes

**Purpose**: Machine consumers need to understand which shapes are canonical and which remain transitional.

**Files**:

- `docs/reference/cli-commands.md`
- `docs/reference/agent-subcommands.md`

**Steps**:

1. Add a note that fresh-run query JSON now uses `mission_state = not_started` plus `preview_step`.
2. Add a note that `unknown` is no longer the canonical fresh-run state.
3. Add a note that the nested `stale` object is canonical while flat fields remain during the transition window.
4. Keep the language clear about compatibility forms versus primary contract.

**Validation**:

- [ ] compatibility notes cover both query JSON and stale JSON
- [ ] notes are written for operators and automation authors, not just implementers

### Subtask T027: Sweep active docs for contradictory wording

**Purpose**: Remove leftover phrases that would reintroduce split-brain teaching surfaces.

**Files**:

- all four `owned_files`

**Steps**:

1. Search for phrasing that implies every WP must belong to an execution lane.
2. Search for query-mode examples that still require `--agent` as the primary form.
3. Search for wording that treats `unknown` as the fresh-run state.
4. Normalize the wording so the same contract is taught everywhere.

**Validation**:

- [ ] no contradictory lane-membership or query-mode language remains in the owned docs

### Subtask T028: Validate examples against current CLI help and landed behavior

**Purpose**: End with a concrete validation sweep instead of trusting hand-edited prose.

**Files**:

- all four `owned_files`

**Steps**:

1. Check current CLI help for `spec-kitty next` and relevant agent subcommands.
2. Compare examples in docs against the landed behavior from WP01-WP04.
3. Fix any syntax drift before marking the WP done.
4. Capture any residual mismatch as an explicit reviewer note instead of silently leaving it in docs.

**Validation**:

- [ ] doc examples match the actual CLI and runtime contract
- [ ] no stale example survives because it was copied forward blindly

## Definition of Done

- The four active docs in scope all teach the same workspace and query contract
- Query mode is documented as `spec-kitty next --mission-run <slug>`
- Fresh-run query JSON is documented as `not_started + preview_step`
- The stale nested-object transition is documented explicitly
- This planning-artifact WP can itself be implemented through the repository-root planning path after WP01-WP04 land

## Risks and Guardrails

- Do not start this WP early; it depends on the code behavior being real, not hypothetical.
- Keep the docs scoped to the four owned files. This is a text-only WP.
- Avoid editing examples by memory; validate against current CLI help and landed behavior.

## Reviewer Guidance

Verify the following during review:

1. All active docs in scope teach the same query-mode syntax.
2. Fresh-run query documentation uses `not_started + preview_step`, not `unknown`.
3. Planning-artifact execution is described as repository-root work outside the lane graph.
4. Compatibility notes clearly distinguish canonical nested stale JSON from deprecated flat fields.

## Activity Log

- 2026-04-08T18:54:01Z – opencode:gpt-5.4:python-implementer:implementer – Moved to in_progress
- 2026-04-08T18:59:28Z – opencode:gpt-5.4:python-implementer:implementer – Ready for review
- 2026-04-08T19:13:55Z – opencode:gpt-5.4:python-reviewer:reviewer – Arbiter decision: scoped docs are internally consistent; remaining mismatches are against the stale global install rather than unresolved branch content
