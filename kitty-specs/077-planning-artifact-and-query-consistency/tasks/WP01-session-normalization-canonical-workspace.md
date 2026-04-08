---
work_package_id: WP01
title: Session Normalization and Canonical Workspace Resolution
dependencies: []
requirement_refs:
- C-001
- C-002
- C-006
- FR-001
- FR-002
- FR-003
- FR-004
- FR-006
- FR-019
- NFR-001
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base derived from finalized lanes, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- timestamp: '2026-04-08T15:01:02Z'
  event: created
  actor: opencode
authoritative_surface: src/specify_cli/workspace_context.py
execution_mode: code_change
owned_files:
- src/specify_cli/workspace_context.py
- src/specify_cli/core/worktree.py
- src/specify_cli/ownership/inference.py
- tests/runtime/test_workspace_context_unit.py
tags: []
---

# WP01: Session Normalization and Canonical Workspace Resolution

## Objective

Create one runtime compatibility seam for missing `execution_mode` and make `src/specify_cli/workspace_context.py` the single authoritative resolver for both lane-backed code-change work and repository-root planning work.

Success means:

- supported historical WPs with missing `execution_mode` are normalized once per mission/session
- `planning_artifact` WPs resolve to repository root without lane membership
- `code_change` WPs keep the existing lane-backed workspace contract
- callers stop re-discovering execution mode or workspace rules independently

## Success Criterion

A mixed mission containing:

- a code-change WP with lane membership
- a planning-artifact WP excluded from `lanes.json`
- a historical WP missing `execution_mode`

resolves deterministically through one API: repeated lookups return the same workspace classification and path, planning-artifact WPs map to repository root, and an unclassifiable legacy WP raises one actionable compatibility error before downstream callers start branching on ad hoc heuristics.

## Context

This is the foundation WP for the entire mission.

Current state:

- `src/specify_cli/core/worktree.py` already has the correct execution-mode-aware planning-artifact route in `create_wp_workspace()`.
- `src/specify_cli/workspace_context.py` still assumes every WP must resolve through workspace context files or `lanes.json`.
- `src/specify_cli/ownership/inference.py` already exposes `infer_execution_mode()`.
- `src/specify_cli/cli/commands/agent/mission.py` already uses `_inmemory_frontmatter` to normalize metadata once in memory.

This WP should not invent new routing heuristics. Reuse the existing ones and centralize them.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Implementation command: `spec-kitty implement WP01`
- Execution worktree allocation: this WP is `code_change`; `/spec-kitty.implement` will allocate or reuse the finalized lane workspace for it from `lanes.json`
- Dependency note: none; this is the resolver foundation that unlocks later WPs

## Scope

You may modify only the files listed in frontmatter under `owned_files`.

Primary surface:

- `src/specify_cli/workspace_context.py`

Supporting surfaces:

- `src/specify_cli/core/worktree.py`
- `src/specify_cli/ownership/inference.py`
- `tests/runtime/test_workspace_context_unit.py`

Do not edit caller modules in this WP. Later WPs will consume the new resolver contract.

## Implementation Guidance

### Subtask T001: Create the mission-scoped normalization seam

**Purpose**: Load WP metadata once per mission/session and cache the normalized result so every caller sees the same execution-mode classification.

**Files**:

- `src/specify_cli/workspace_context.py`

**Steps**:

1. Add a process-local normalization cache keyed by repository root and mission slug.
2. Create an internal helper that reads WP files for a mission and returns normalized metadata entries.
3. Keep the helper read-only. Do not write inferred fields back to disk.
4. Include enough metadata in the normalized entry to support downstream diagnostics, not just the final `WPMetadata` object.

**Validation**:

- [ ] Normalization happens once per mission/session, not once per caller
- [ ] Repeated lookups for the same mission reuse the normalized state
- [ ] The cache can be invalidated by tests or explicit helper calls

### Subtask T002: Infer missing `execution_mode` once and record `mode_source`

**Purpose**: Reuse the existing inference engine for supported historical missions, but make the result explicit and traceable.

**Files**:

- `src/specify_cli/workspace_context.py`
- `src/specify_cli/ownership/inference.py`

**Steps**:

1. Reuse `infer_execution_mode()` instead of creating a second inference implementation.
2. When a WP already has `execution_mode`, mark the source as `frontmatter`.
3. When a supported historical WP is missing `execution_mode`, infer it from existing WP content and mark the source as `inferred_legacy`.
4. Capture a human-readable diagnostic string or equivalent field so later callers can explain what happened when debugging.

**Validation**:

- [ ] Existing `execution_mode` values remain untouched
- [ ] Missing `execution_mode` values are inferred exactly once per mission/session
- [ ] The normalization result preserves whether the value came from disk or inference

### Subtask T003: Expand `ResolvedWorkspace` and route planning-artifact WPs to repo root

**Purpose**: Make the resolver capable of representing both lane workspaces and repository-root planning work without fake lane data.

**Files**:

- `src/specify_cli/workspace_context.py`
- `src/specify_cli/core/worktree.py`

**Steps**:

1. Extend `ResolvedWorkspace` with execution-mode-aware fields such as `execution_mode`, `mode_source`, and `resolution_kind`.
2. Make `branch_name` and `lane_id` nullable in the returned contract for repo-root planning work.
3. Preserve current lane-backed behavior for `code_change` WPs.
4. For `planning_artifact` WPs, return repository root directly and avoid any dependency on lane membership.
5. Keep the existing `create_wp_workspace()` contract in mind so runtime read and write paths stay aligned.

**Validation**:

- [ ] `code_change` WPs still resolve through `lanes.json` and workspace contexts
- [ ] `planning_artifact` WPs resolve to repository root without lane membership
- [ ] Returned metadata is rich enough for later caller type narrowing

### Subtask T004: Emit one actionable compatibility error when classification is impossible

**Purpose**: If a supported historical WP still cannot be classified, fail clearly once instead of letting multiple callers fail differently.

**Files**:

- `src/specify_cli/workspace_context.py`

**Steps**:

1. Centralize the compatibility failure in the normalization/resolver path.
2. Include the mission slug, WP id, and a clear repair suggestion in the error message.
3. Make the failure happen before later callers attempt lane lookups or branch assumptions.
4. Keep the error stable enough for tests to assert on it.

**Validation**:

- [ ] Unclassifiable legacy WPs fail once with a useful message
- [ ] Later callers do not emit different follow-on errors for the same root cause

### Subtask T005: Add focused resolver tests

**Purpose**: Lock in the new normalization and workspace contract before downstream callers start depending on it.

**Files**:

- `tests/runtime/test_workspace_context_unit.py`

**Steps**:

1. Add a test for repeated deterministic lookup across different working directories within the same repository.
2. Add a test for a historical WP missing `execution_mode` that normalizes to `planning_artifact` and resolves to repository root.
3. Add a test for a `code_change` WP that still resolves through the lane-backed path.
4. Add a test for the single compatibility error when classification is impossible.

**Validation**:

- [ ] Tests cover frontmatter-sourced and inferred legacy execution modes
- [ ] Tests assert on `resolution_kind`, path, and error shape
- [ ] Tests remain local and deterministic

## Definition of Done

- One mission-scoped normalization seam exists in `src/specify_cli/workspace_context.py`
- `ResolvedWorkspace` can represent both lane-backed and repo-root planning work
- Missing `execution_mode` for supported historical WPs is handled once in memory
- Impossible legacy classification fails once with actionable guidance
- `tests/runtime/test_workspace_context_unit.py` covers the new resolver contract

## Risks and Guardrails

- Avoid caller-specific branches in this WP; the whole point is to centralize the decision.
- Keep all inference read-only. Runtime compatibility must not rewrite WP files on disk.
- Be careful with type changes: nullable branch/lane fields should be explicit and deliberate.

## Reviewer Guidance

Verify the following during review:

1. `src/specify_cli/workspace_context.py` is now the single place that decides how a WP resolves.
2. The planning-artifact path does not consult `lane_for_wp()`.
3. The compatibility error is emitted at the normalization seam, not leaked from later caller code.
4. Tests prove deterministic repeated resolution and the repo-root planning path.
