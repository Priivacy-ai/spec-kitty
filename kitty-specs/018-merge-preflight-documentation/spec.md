# Feature Specification: Merge Preflight Documentation

**Feature Branch**: `018-merge-preflight-documentation`
**Created**: 2026-01-18
**Status**: Draft
**Mission**: documentation
**Input**: Full documentation for Feature 017 (Smarter Feature Merge with Preflight) covering all capabilities with troubleshooting emphasis

## Overview

This documentation feature creates comprehensive user and developer documentation for Feature 017's merge enhancements. The documentation follows existing project norms and the Divio 4-type system, with emphasis on practical troubleshooting workflows.

### Documentation Scope

Feature 017 introduced these capabilities requiring documentation:

1. **Resumable Merges**: `--resume` and `--abort` flags for interrupted merge operations
2. **Pre-flight Validation**: Automatic detection of dirty worktrees and missing workspaces before merge
3. **Conflict Forecasting**: Dry-run mode predicts conflicts before actual merge
4. **Status File Auto-Resolution**: Automatic resolution of lane/status file conflicts
5. **Merge State Persistence**: State saved to `.kittify/merge-state.json` for recovery

### Documentation Outputs

| Output | Location | Divio Type |
|--------|----------|------------|
| Merge Command Guide | `docs/merge-guide.md` | How-To |
| Troubleshooting Guide | `docs/merge-troubleshooting.md` | How-To |
| CLAUDE.md Merge Section | `CLAUDE.md` | Reference |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learn Merge Workflow (Priority: P1)

A developer new to spec-kitty needs to understand how to merge completed work packages back to main. They read the merge guide to learn the complete workflow from running the merge command to handling any issues.

**Why this priority**: Without understanding the basic merge workflow, users cannot complete features.

**Independent Test**: Can be tested by having a new user read only the merge guide and successfully merge a simple feature with multiple WPs.

**Acceptance Scenarios**:

1. **Given** a developer has completed a workspace-per-WP feature, **When** they read `docs/merge-guide.md`, **Then** they understand how to run `spec-kitty merge` and what each step does
2. **Given** a developer reads the merge guide, **When** they encounter the `--dry-run` flag section, **Then** they understand how to preview merge operations before executing
3. **Given** the guide explains pre-flight validation, **When** a developer reads it, **Then** they understand what checks run automatically and how to interpret results

---

### User Story 2 - Recover from Interrupted Merge (Priority: P1)

A developer's merge was interrupted (network failure, terminal closed, conflict mid-merge). They need to understand how to resume or abort the merge and get back to a clean state.

**Why this priority**: Interrupted merges are common and users must know recovery options to avoid repository corruption.

**Independent Test**: Can be tested by simulating an interrupted merge and following only the troubleshooting guide to recover.

**Acceptance Scenarios**:

1. **Given** a merge was interrupted after WP01 but before WP03, **When** the user reads the troubleshooting guide, **Then** they understand how to use `--resume` to continue from WP02
2. **Given** a merge has unresolved conflicts, **When** the user reads the troubleshooting guide, **Then** they understand how to resolve conflicts and run `--resume`
3. **Given** a user wants to abandon an interrupted merge, **When** they read the troubleshooting guide, **Then** they understand how to use `--abort` to clear state and start fresh

---

### User Story 3 - Resolve Merge Conflicts (Priority: P2)

A developer encounters merge conflicts during the merge process. They need guidance on identifying conflict types, resolving them manually, and completing the merge.

**Why this priority**: Conflicts are inevitable in multi-developer workflows; clear resolution guidance prevents frustration.

**Independent Test**: Can be tested by creating a known conflict scenario and following the guide to resolution.

**Acceptance Scenarios**:

1. **Given** a merge fails with conflicts, **When** the user reads the troubleshooting guide, **Then** they understand how to identify which files have conflicts
2. **Given** conflicts are in status files (lane markers), **When** the user reads the guide, **Then** they understand these are auto-resolved and what to do if auto-resolution fails
3. **Given** conflicts are in code files, **When** the user reads the guide, **Then** they understand the manual resolution workflow and how to continue

---

### User Story 4 - Understand Pre-flight Failures (Priority: P2)

A developer runs merge but pre-flight validation fails. They need to understand what failed, why, and how to fix it before retrying.

**Why this priority**: Pre-flight is designed to catch issues early; users need to understand and act on these warnings.

**Independent Test**: Can be tested by creating each pre-flight failure condition and verifying the guide explains the fix.

**Acceptance Scenarios**:

1. **Given** pre-flight fails with "uncommitted changes in WP02", **When** the user reads the guide, **Then** they understand they need to commit or stash changes in that worktree
2. **Given** pre-flight fails with "missing worktree for WP03", **When** the user reads the guide, **Then** they understand the workspace was never created and how to create it
3. **Given** pre-flight shows multiple issues, **When** the user reads the guide, **Then** they understand all issues are shown upfront and can be fixed in any order

---

### User Story 5 - Developer Reference in CLAUDE.md (Priority: P3)

A developer or AI agent contributing to spec-kitty needs quick reference for merge patterns, state file locations, and integration with the workspace-per-WP model.

**Why this priority**: Developer reference enables consistent contributions and AI agent effectiveness.

**Independent Test**: Can be tested by having a contributor use only CLAUDE.md to understand merge state management.

**Acceptance Scenarios**:

1. **Given** a developer reads the CLAUDE.md merge section, **When** they need to understand state persistence, **Then** they find the `.kittify/merge-state.json` structure documented
2. **Given** an AI agent reads CLAUDE.md, **When** implementing merge-related features, **Then** they find patterns for pre-flight validation and conflict handling

---

### Edge Cases

- What happens when merge state file is corrupted or invalid JSON?
- How does merge behave when run from main branch vs. from a worktree?
- What if a user manually deletes a worktree mid-merge?
- How to handle merge when some WP branches were force-pushed?

## Requirements *(mandatory)*

### Functional Requirements

**Merge Guide (`docs/merge-guide.md`)**

- **FR-001**: Guide MUST explain the `spec-kitty merge` command syntax and all flags (`--strategy`, `--dry-run`, `--push`, `--resume`, `--abort`, `--keep-branch`, `--keep-worktree`)
- **FR-002**: Guide MUST include a visual workflow diagram showing the merge process for workspace-per-WP features
- **FR-003**: Guide MUST explain pre-flight validation checks and their purpose
- **FR-004**: Guide MUST document the dry-run conflict forecasting feature with example output
- **FR-005**: Guide MUST explain automatic status file conflict resolution behavior

**Troubleshooting Guide (`docs/merge-troubleshooting.md`)**

- **FR-006**: Guide MUST document all error messages users may encounter during merge
- **FR-007**: Guide MUST provide step-by-step recovery procedures for interrupted merges
- **FR-008**: Guide MUST explain how to use `--resume` with examples of partial merge states
- **FR-009**: Guide MUST explain how to use `--abort` and when it's appropriate
- **FR-010**: Guide MUST document manual conflict resolution workflow
- **FR-011**: Guide MUST include a decision tree for common merge failures

**CLAUDE.md Updates**

- **FR-012**: CLAUDE.md MUST include a "Merge & Preflight Patterns" subsection under workspace-per-WP documentation
- **FR-013**: Section MUST document merge state file structure and location
- **FR-014**: Section MUST document pre-flight validation integration points
- **FR-015**: Section MUST include code examples for programmatic merge state access

**Cross-cutting Requirements**

- **FR-016**: All documentation MUST follow existing tone and formatting conventions in `docs/`
- **FR-017**: All command examples MUST be copy-pasteable and tested
- **FR-018**: Documentation MUST cross-reference related guides (workspace-per-wp.md, upgrading guides)

### Key Entities

- **Merge State**: Persisted state in `.kittify/merge-state.json` tracking feature_slug, completed_wps, remaining_wps, current_wp, strategy
- **Pre-flight Result**: Validation outcome containing passed/failed status, list of WP statuses, errors, and warnings
- **Conflict Prediction**: Forecast of potential conflicts including file paths and conflict type (status file vs. code)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can recover from an interrupted merge using only the documentation within 5 minutes
- **SC-002**: New users can complete their first workspace-per-WP merge using only the merge guide
- **SC-003**: All documented command examples execute successfully when copy-pasted
- **SC-004**: Troubleshooting guide covers 100% of error messages produced by the merge command
- **SC-005**: AI agents using CLAUDE.md can correctly implement merge-related features without additional context

## Assumptions

1. Feature 017 has been fully merged and is available in the codebase
2. Existing documentation style in `docs/` serves as the formatting template
3. Users have basic familiarity with git concepts (branches, merges, conflicts)
4. The workspace-per-WP model documentation (`docs/workspace-per-wp.md`) already exists and can be cross-referenced
