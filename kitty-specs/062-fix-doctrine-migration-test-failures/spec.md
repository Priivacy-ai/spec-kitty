# Mission Specification: Fix Doctrine Migration Test Failures

**Mission Branch**: `feature/agent-profile-implementation-rebased`
**Created**: 2026-04-02
**Status**: Draft
**Input**: User description: "Fix CI test failures caused by doctrine migration: update stale path references, assertion mismatches, and mock targets across 10 test files"

## Context

Commit `bd7a288c` migrated mission YAML and templates from `src/specify_cli/missions/` to `src/doctrine/missions/`. The migration updated production code to use `MissionTemplateRepository` but left stale references in 10 test files, causing 120 test failures and 43 errors in CI. A secondary diff-coverage gate (76% < 80% threshold) also fails on the CI Quality workflow.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CI Green on Release Readiness (Priority: P1)

A contributor pushes to the `feature/agent-profile-implementation-rebased` branch and the Release Readiness Check workflow passes with zero test failures related to stale doctrine paths.

**Why this priority**: The branch cannot be merged while CI is red. This blocks all further development on the feature branch.

**Independent Test**: Run the full test suite; all 10 previously-failing test files pass.

**Acceptance Scenarios**:

1. **Given** the branch has the path fixes applied, **When** CI runs the Release Readiness Check, **Then** the 120 failures and 43 errors from doctrine-path tests are eliminated.
2. **Given** a test references mission YAML, **When** it resolves the path, **Then** it uses `src/doctrine/missions/` (not `src/specify_cli/missions/`).

---

### User Story 2 - CI Green on Diff-Coverage Gate (Priority: P2)

A contributor pushes to the branch and the CI Quality workflow passes with diff-coverage at or above 80%.

**Why this priority**: The coverage gate is a secondary blocker. Fixing the broken tests (P1) will recover coverage from the ~163 tests that were failing. If still below 80%, targeted tests fill the gap.

**Independent Test**: Run `diff-cover` against the branch diff; coverage is >= 80%.

**Acceptance Scenarios**:

1. **Given** all path/assertion fixes are applied and broken tests pass again, **When** diff-coverage is measured, **Then** coverage is at or above 80%.
2. **Given** coverage is still below 80% after P1 fixes, **When** targeted tests are added for uncovered lines, **Then** coverage rises above 80%.

---

### User Story 3 - Architectural Fitness Review (Priority: P3)

An architect reviews the branch direction and validates that the doctrine migration, path conventions, and test patterns align with the project's architectural vision.

**Why this priority**: Ensures the fixes are not just mechanically correct but architecturally sound. Catches systemic issues (e.g., tests that should use `MissionTemplateRepository` instead of hardcoded paths).

**Independent Test**: Architect produces a review verdict (approve/request-changes) with rationale.

**Acceptance Scenarios**:

1. **Given** the P1 and P2 fixes are complete, **When** the architect reviews the branch, **Then** they confirm the path conventions are consistent with the doctrine package design.
2. **Given** the architect identifies systemic issues, **When** they flag them, **Then** the issues are documented for follow-up (not necessarily fixed in this mission).

---

### Edge Cases

- What happens if a test file references both old and new paths (partial migration)?
- How should tests handle the `MissionTemplateRepository` fallback when doctrine package is not installed in editable mode?
- What if fixing a mock target reveals a deeper API change that requires test logic rewrite (not just path swap)?

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Update hardcoded mission paths | As a contributor, I want test files to reference `src/doctrine/missions/` so that tests find mission YAML after the doctrine migration. | High | Open |
| FR-002 | Fix terminology assertions | As a contributor, I want tests to assert `"Mission"` (not `"Feature"`) for `aggregate_type` and use `mission=` (not `feature=`) parameter names so that assertions match the refactored code. | High | Open |
| FR-003 | Repair mock targets | As a contributor, I want test mocks to target the correct import locations for `read_frontmatter` and other moved functions so that mocks intercept the right call sites. | High | Open |
| FR-004 | Fix missing fixtures | As a contributor, I want tests that reference `_proposed/` agent profile directories to use valid paths or create required fixtures so that FileNotFoundErrors are eliminated. | High | Open |
| FR-005 | Fix migration test assertions | As a contributor, I want the documentation mission migration test to assert behavior consistent with the current migration logic. | Medium | Open |
| FR-006 | Targeted coverage for critical paths | As a contributor, I want meaningful tests for critical changed code (status model, mission detection, dashboard API) rather than chasing a flat coverage number, so that test effort is proportional to risk. | Medium | Open |
| FR-007 | Architect review of branch direction | As an architect, I want to review the branch's test patterns and path conventions to confirm alignment with the doctrine package architectural vision. | Low | Open |
| FR-008 | Fix dashboard scanner NameError | As a user, I want the dashboard to scan all missions without crashing on missions that lack an event log, so that the mission selector populates correctly. | High | Open |
| FR-009 | Fix dashboard JS key mismatch | As a user, I want the dashboard frontend to read the correct API response keys (`missions`, `active_mission_id`) so that the feature list renders. | High | Open |
| FR-010 | Dashboard API contract test | As a contributor, I want a pytest that validates the dashboard JS reads the same keys the Python API emits, so that key renames are caught before CI merges. | Medium | Open |
| FR-011 | Dashboard in_review lane rendering | As a user, I want WPs in the `in_review` lane to appear in the dashboard "For Review" column with a visually distinct card style, so that I can see which WPs are actively being reviewed. | Medium | Open |
| FR-012 | WP card agent identity display | As a user, I want the WP detail modal to show the agent tool, profile, role, and model, so that I can see which agent is working on each WP. | Medium | Open |
| FR-013 | Centralize hardcoded doctrine path constants | As a contributor, I want compliance guard tests to import a shared `DOCTRINE_SOURCE_ROOT` constant instead of duplicating the path literal, so that a future path change requires only one update. | Low | Open |
| FR-014 | Dashboard JS terminology clean break | As a contributor, I want the dashboard JS to use only `data.missions` / `data.active_mission_id` and fetch from `/api/missions`, removing dead `feature*` fallbacks, so that the codebase complies with the Terminology Canon. | Medium | Open |
| FR-015 | Feature-to-mission bulk rename | As a contributor, I want ~30 missed `feature*` identifiers across 18 production files renamed to `mission*` equivalents, so that active codepaths comply with the Terminology Canon. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | CI pass rate | All tests in the 10 affected files pass with zero failures and zero errors | Correctness | High | Open |
| NFR-002 | Risk-proportional coverage | Critical paths (status model, mission detection, dashboard API handlers) have >= 90% coverage on changed lines; non-critical paths (migrations, CLI scaffolding) have no minimum | Quality | Medium | Open |
| NFR-003 | No regressions | No previously-passing tests broken by the fixes | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Minimal production code changes | Fixes are primarily test files; production exceptions: two dashboard bugs (already fixed), CI workflow diff-cover config, and migration logic if genuinely wrong | Technical | High | Open |
| C-002 | Use doctrine abstractions | Where possible, tests should use `MissionTemplateRepository` rather than hardcoding new paths, to avoid repeating the same brittleness | Technical | Medium | Open |
| C-003 | Branch scope | All work targets `feature/agent-profile-implementation-rebased`; no changes to `main` or `develop` | Process | High | Open |

### Key Entities

- **Doctrine missions root**: `src/doctrine/missions/` -- the new canonical location for mission YAML and templates
- **MissionTemplateRepository**: The abstraction layer that resolves mission paths at runtime; tests should prefer this over hardcoded paths
- **Agent profiles**: YAML files under `src/doctrine/agent_profiles/` defining agent behavior; `shipped/` exists, `_proposed/` may not

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Release Readiness Check CI workflow passes with 0 failures from the 10 affected test files
- **SC-002**: Critical changed paths (status model, mission detection, dashboard API) have >= 90% diff-coverage; CI Quality workflow coverage gate is satisfied or an explicit waiver is documented
- **SC-003**: No regressions -- total passing test count is equal to or greater than the pre-fix baseline (9144 passed)
- **SC-004**: Architect Alphonso approves branch direction or documents follow-up items

## Work Package Outline

| WP | Title | Agent | Category | Dependencies |
|----|-------|-------|----------|--------------|
| WP01 | Update hardcoded mission paths (Cat A) | python-implementer | FR-001 | -- |
| WP02 | Fix terminology and assertion mismatches (Cat B) | python-implementer | FR-002 | -- |
| WP03 | Repair mock targets and missing fixtures (Cat C) | python-implementer | FR-003, FR-004 | -- |
| WP04 | Fix migration test logic (Cat D) | python-implementer | FR-005 | -- |
| WP05 | Fix dashboard scanner + JS key mismatch (Cat A/B) | python-implementer | FR-008, FR-009 | -- |
| WP06 | Add dashboard API contract test | python-implementer | FR-010 | WP05 |
| WP07 | Targeted coverage + CI gate split (Cat E) | python-implementer | FR-006 | WP01, WP02, WP03, WP04, WP05, WP06 |
| WP08 | Architectural fitness review | architect | FR-007 | WP07 |
| WP09 | Dashboard in-review lane + card identity | python-implementer | FR-011, FR-012 | WP05 |
| WP10 | Centralize doctrine path constants | python-implementer | FR-013 | WP08 |
| WP11 | Dashboard JS terminology clean break (cleanup) | python-implementer | FR-014 | WP09 |
| WP12 | Feature-to-mission bulk rename | python-implementer | FR-015 | WP11 |
