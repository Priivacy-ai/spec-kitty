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
3. **Given** a non-documentation mission feature, **When** planning, research, validation, or acceptance runs, **Then** documentation tooling is not invoked and no documentation-specific artifacts are created.
4. **Given** a documentation mission feature, **When** generator tools (Sphinx/JSDoc/Rustdoc) are missing, **Then** the system warns with clear guidance and continues without failing the flow.

---

### Edge Cases

- What happens when a non-documentation mission runs planning or validation? (No documentation tooling should run.)
- How does the system handle a documentation mission when required generator tools are not installed? (Must warn with clear guidance and continue, unless the user explicitly requested generator output.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST remove duplicated script entrypoints and ensure tests use the single packaged source of truth.
- **FR-002**: The system MUST NOT introduce symlinks as a solution for script consolidation.
- **FR-003**: Task and acceptance helpers MUST be consolidated into a shared, non-deprecated implementation used by all entrypoints.
- **FR-004**: Worktree-aware repository root detection MUST be consistently applied across task and acceptance flows.
- **FR-005**: Documentation mission state MUST be initialized during specification for documentation mission features.
- **FR-006**: Documentation mission gap analysis MUST execute during planning and research flows when applicable and write to a canonical path: `kitty-specs/<feature>/gap-analysis.md`.
- **FR-007**: Documentation mission validation/acceptance MUST verify presence and recency of gap analysis artifacts and state metadata using the rules in **Documentation State & Recency Rules**.
- **FR-008**: Base planning template `src/specify_cli/templates/command-templates/plan.md` MUST be aligned with the software-dev mission template for feature detection guidance.
- **FR-009**: If documentation generator tools are missing, planning/research MUST warn with clear guidance and continue (no hard-fail).

### Key Entities *(include if feature involves data)*

- **Script Source of Truth**: The authoritative script entrypoints used by tests and packaged templates.
- **Documentation State**: Mission-specific metadata stored with the feature to track iteration mode, selections, and audit timing.
- **Gap Analysis Report**: The generated audit of existing documentation coverage and missing areas.
- **Mission Type**: The mission classification that gates which workflows and checks are applied.

### Documentation State & Recency Rules

**Authoritative schema** (stored in `kitty-specs/<feature>/meta.json` under `documentation_state`):
- `iteration_mode`: `"initial" | "gap_filling" | "feature_specific"` (default: `"initial"`)
- `divio_types_selected`: `string[]` (default: `[]`)
- `generators_configured`: `Array<{ name: "sphinx" | "jsdoc" | "rustdoc", language: string, config_path: string }>` (default: `[]`)
- `target_audience`: `string` (default: `"developers"`)
- `last_audit_date`: ISO 8601 timestamp or `null` (default: `null`)
- `coverage_percentage`: number from `0.0` to `1.0` (default: `0.0`)

**Canonical gap analysis path**: `kitty-specs/<feature>/gap-analysis.md`

**Recency rule**: `last_audit_date` must be **on or after** the feature `created_at` timestamp in `meta.json` and the file at the canonical path must exist. If either check fails, validation/acceptance must report the artifact as missing/stale.

**Mission gating source**: the feature `meta.json` `mission` value is the primary gate; mission config may be used as a secondary confirmation, but tooling must only run when `mission == "documentation"`.

**Terminology**: “Validation” refers to `spec-kitty validate` (including validate-tasks) while “Acceptance” refers to `spec-kitty accept` and `spec-kitty agent feature accept`. Both must enforce documentation mission rules when mission-gated.

### Assumptions

- The cleanup targets `main` for a 0.13.29 release and will be cherry-picked into `2.x` after release readiness.
- No new public CLI commands will be added in this release; mission-specific behavior will be wired into existing commands only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The full automated test suite passes without relying on duplicated root-level script copies.
- **SC-002**: Task and acceptance commands produce the same outcomes when run from a main repo or a worktree checkout.
- **SC-003**: Documentation mission planning or research produces a gap analysis report for 100% of documentation mission features that request it.
- **SC-004**: Documentation mission acceptance/validation fails if required documentation state or gap analysis artifacts are missing.
- **SC-005**: CI passes with `mypy --strict` and new/modified modules meet the 90%+ coverage requirement.
