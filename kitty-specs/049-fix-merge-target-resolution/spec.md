# Feature Specification: Fix Merge Target Branch Resolution

**Feature Branch**: `049-fix-merge-target-resolution`
**Created**: 2026-03-10
**Status**: Draft
**Input**: Hotfix for CRITICAL bug where `spec-kitty merge` ignores feature `meta.json` `target_branch` and defaults to repo primary branch, causing merges into the wrong branch for dual-branch features.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Merge Resolves Correct Target Branch (Priority: P1)

A developer working on a feature that targets `2.x` (as declared in `meta.json`) runs `spec-kitty merge --feature 049-fix-merge-target-resolution`. The merge operation reads `target_branch` from the feature's `meta.json` and merges into `2.x`, not `main`.

**Why this priority**: This is the entire reason for the hotfix. Wrong-target merge is destructive and has already caused real failures in production (v2.0.5).

**Independent Test**: Run `spec-kitty merge --dry-run --feature <slug>` for a feature whose `meta.json` declares `target_branch: "2.x"`. The dry-run output must show `target_branch: "2.x"`, not `"main"`.

**Acceptance Scenarios**:

1. **Given** a feature with `meta.json` containing `target_branch: "2.x"`, **When** `spec-kitty merge --feature <slug>` is run without `--target`, **Then** the merge targets `2.x`.
2. **Given** a feature with `meta.json` containing `target_branch: "main"`, **When** `spec-kitty merge --feature <slug>` is run without `--target`, **Then** the merge targets `main`.
3. **Given** a feature with `meta.json` containing `target_branch: "2.x"`, **When** `spec-kitty merge --feature <slug> --target main` is run, **Then** the explicit `--target main` overrides `meta.json` and the merge targets `main`.
4. **Given** a feature with no `meta.json` or a `meta.json` missing `target_branch`, **When** `spec-kitty merge --feature <slug>` is run, **Then** the merge falls back to `resolve_primary_branch()` (existing behavior preserved).

---

### User Story 2 - Merge Template Uses Single Canonical Command (Priority: P1)

An AI agent executing the `/spec-kitty.merge` slash command follows the template instructions and runs `spec-kitty merge --feature <slug>`, which is the single canonical merge API. The template frontmatter and body both reference only this command. No alternative command paths are documented.

**Why this priority**: The template inconsistency amplifies the bug — split guidance between two command paths is exactly how LLMs get nondeterministic tool choice and prompt drift.

**Independent Test**: Read the merge command template and verify that frontmatter and body both reference only `spec-kitty merge --feature <slug>`. No mention of `spec-kitty agent feature merge` anywhere in the template.

**Acceptance Scenarios**:

1. **Given** the merge command template, **When** an agent reads it, **Then** the frontmatter description and body instructions reference only `spec-kitty merge --feature <slug>`.
2. **Given** the merge command template, **When** an agent follows the documented merge command, **Then** the command resolves `target_branch` from feature metadata (not `resolve_primary_branch()`).

---

### User Story 3 - No-Feature Merge Preserves Existing Behavior (Priority: P2)

A developer running `spec-kitty merge` without `--feature` gets the existing fallback behavior (`resolve_primary_branch()`). The hotfix must not break this path.

**Why this priority**: Backward compatibility. Some users may invoke merge without an explicit feature flag.

**Independent Test**: Run `spec-kitty merge --dry-run` without `--feature` and verify it still resolves to the repository's primary branch.

**Acceptance Scenarios**:

1. **Given** no `--feature` flag is provided, **When** `spec-kitty merge` is run, **Then** target branch resolves via `resolve_primary_branch()` (unchanged from current behavior).

---

### Edge Cases

- What happens when `meta.json` exists but `target_branch` field is missing? Falls back to `resolve_primary_branch()`.
- What happens when `meta.json` exists but is malformed JSON? Falls back to `resolve_primary_branch()` with a warning.
- What happens when `--target` is explicitly provided alongside `--feature`? Explicit `--target` wins.
- What happens when the target branch in `meta.json` no longer exists in the repo? Hard error — do not silently fall back to a different branch.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Top-level `spec-kitty merge` MUST resolve `target_branch` from the feature's `meta.json` when `--feature` is provided and `--target` is not | Draft |
| FR-002 | Explicit `--target` flag MUST override `meta.json` `target_branch` in all cases | Draft |
| FR-003 | When `--feature` is provided but `meta.json` is missing or lacks `target_branch`, the system MUST fall back to `resolve_primary_branch()` | Draft |
| FR-004 | When `--feature` is not provided, target resolution MUST remain unchanged (use `resolve_primary_branch()`) | Draft |
| FR-005 | The merge command template MUST route agents to a command path that consults feature metadata for target resolution | Draft |
| FR-006 | When `meta.json` specifies a `target_branch` that does not exist as a local or remote branch, the merge MUST fail with a clear error rather than silently falling back | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Target resolution from `meta.json` MUST add no more than 100ms to merge startup | <100ms | Draft |
| NFR-002 | Regression test suite for target resolution MUST cover at least: `2.x` target, `main` target, missing `meta.json`, explicit `--target` override | 4+ test cases | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Fix MUST land on `2.x` branch first, then be ported to `main` via separate PR | Draft |
| C-002 | Fix MUST NOT change the behavior of `spec-kitty agent feature merge` (already correct) | Draft |
| C-003 | Fix MUST NOT introduce new dependencies | Draft |
| C-004 | The `get_feature_target_branch()` function in `feature_detection.py` MUST be reused (not duplicated) for the top-level merge fix | Draft |

### Key Entities

- **Feature metadata** (`meta.json`): Contains `target_branch` field that declares where a feature's work packages should be merged.
- **Merge target resolution**: The logic that determines which branch receives merged work — currently split between `resolve_primary_branch()` (generic) and `get_feature_target_branch()` (feature-aware).
- **Merge command template** (`merge.md`): The prompt template that tells AI agents which command to run for merge operations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

| ID | Criterion |
|----|-----------|
| SC-001 | `spec-kitty merge --feature <slug> --dry-run` returns the correct `target_branch` from `meta.json` in 100% of test cases |
| SC-002 | No regression: `spec-kitty merge` without `--feature` continues to resolve via `resolve_primary_branch()` |
| SC-003 | Merge template produces consistent agent behavior — frontmatter and body reference the same command path |
| SC-004 | All regression tests pass for: feature targeting `2.x`, feature targeting `main`, missing meta.json, explicit `--target` override, nonexistent target branch error |

## Assumptions

- The existing `get_feature_target_branch()` function in `feature_detection.py` (lines 645-696) is correct and battle-tested via the agent merge path.
- The `resolve_primary_branch()` function in `git_ops.py` (lines 262-319) is correct for the no-feature fallback case.
- The merge template source is at `src/specify_cli/missions/software-dev/command-templates/merge.md` (not the generated agent copies).

## Out of Scope

- Feature auto-detection fallback fix (deferred to stabilization feature)
- Task ID `[T005]` bracket normalization (deferred)
- Dossier snapshot exclusion from research output checks (deferred)
- Constitution bootstrap noise suppression (deferred)
- Version stamping expansion (deferred)
- Any changes to `spec-kitty agent feature merge` (already correct)
