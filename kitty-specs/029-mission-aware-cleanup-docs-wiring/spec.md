# Feature Specification: Mission-Aware Cleanup & Docs Wiring
<!-- Replace [FEATURE NAME] with the confirmed friendly title generated during /spec-kitty.specify. -->

**Feature Branch**: `029-mission-aware-cleanup-docs-wiring`  
**Created**: 2026-02-04  
**Status**: Draft  
**Input**: User description: "to address all of the points youve identified. But I dont want to make symlinks, I want to update the tests and remove the cruft."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Legacy Script Duplication (Priority: P1)

As a maintainer, I want only one authoritative set of script entrypoints so that tests and shipped templates stay consistent and do not drift over time.

**Why this priority**: Duplicate entrypoints are already diverging; removing them reduces risk and maintenance burden immediately.

**Independent Test**: Running the existing automated test suite exercises only the packaged script entrypoints and still passes.

**Acceptance Scenarios**:

1. **Given** the repository contains legacy root-level script copies, **When** the cleanup is applied, **Then** only the packaged script entrypoints remain in use by tests and tooling.
2. **Given** a developer runs the test suite, **When** it references script entrypoints, **Then** it uses the single source of truth without requiring symlinks.

---

### User Story 2 - Consistent Task/Acceptance Behavior (Priority: P1)

As a maintainer, I want task and acceptance helpers to use a single, non-deprecated implementation so that behavior stays consistent across CLI paths and worktrees.

**Why this priority**: Divergent helpers create worktree bugs and block removal of deprecated modules.

**Independent Test**: Task/acceptance commands behave identically in a normal repo and in a worktree checkout.

**Acceptance Scenarios**:

1. **Given** a user runs task or acceptance commands inside a worktree, **When** repo root detection occurs, **Then** the main repository root is used consistently.
2. **Given** acceptance logic executes in the primary CLI, **When** it needs shared helpers, **Then** it does not depend on deprecated modules.

---

### User Story 3 - Documentation Mission Tooling Executes in Existing Flows (Priority: P2)

As a documentation-mission user, I want gap analysis and documentation state to run automatically within existing commands so I can get mission outputs without new public commands.

**Why this priority**: Documentation mission features are partially implemented and need to become functional without expanding the CLI surface area.

**Independent Test**: Running existing planning or validation flows for a documentation mission produces a gap analysis artifact and updates documentation state.

**Acceptance Scenarios**:

1. **Given** a documentation mission feature, **When** planning or research is run, **Then** a gap analysis report is generated and stored for the feature.
2. **Given** a documentation mission feature, **When** validation or acceptance runs, **Then** it checks for a recent gap analysis and documentation state metadata.

---

### Edge Cases

- What happens when a non-documentation mission runs planning or validation? (No documentation tooling should run.)
- How does the system handle a documentation mission when required generator tools are not installed? (Must fail gracefully with clear guidance.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST remove duplicated script entrypoints and ensure tests use the single packaged source of truth.
- **FR-002**: The system MUST NOT introduce symlinks as a solution for script consolidation.
- **FR-003**: Task and acceptance helpers MUST be consolidated into a shared, non-deprecated implementation used by all entrypoints.
- **FR-004**: Worktree-aware repository root detection MUST be consistently applied across task and acceptance flows.
- **FR-005**: Documentation mission state MUST be initialized during specification for documentation mission features.
- **FR-006**: Documentation mission gap analysis MUST execute during planning and research flows when applicable.
- **FR-007**: Documentation mission validation/acceptance MUST verify presence and recency of gap analysis artifacts and state metadata.
- **FR-008**: Base planning templates MUST be aligned with mission templates to avoid drift in feature detection guidance.

### Key Entities *(include if feature involves data)*

- **Script Source of Truth**: The authoritative script entrypoints used by tests and packaged templates.
- **Documentation State**: Mission-specific metadata stored with the feature to track iteration mode, selections, and audit timing.
- **Gap Analysis Report**: The generated audit of existing documentation coverage and missing areas.
- **Mission Type**: The mission classification that gates which workflows and checks are applied.

### Assumptions

- The cleanup targets `main` for a 0.13.29 release and will be cherry-picked into `2.x` after release readiness.
- No new public CLI commands will be added in this release; mission-specific behavior will be wired into existing commands only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The full automated test suite passes without relying on duplicated root-level script copies.
- **SC-002**: Task and acceptance commands produce the same outcomes when run from a main repo or a worktree checkout.
- **SC-003**: Documentation mission planning or research produces a gap analysis report for 100% of documentation mission features that request it.
- **SC-004**: Documentation mission acceptance/validation fails if required documentation state or gap analysis artifacts are missing.
