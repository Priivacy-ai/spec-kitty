# Mission Specification: Finalize owned-checkout mission resolver

**Mission Branch**: `owned-checkout-finalize-resolver-01M0094H`
**Created**: 2026-08-14
**Status**: Approved for implementation
**Input**: Resolve the linked-worktree split-brain in `agent mission finalize-tasks` with one shared mission operation context.

## User Scenarios & Testing

### User Story 1 - Finalize a mission from its owned checkout (Priority: P1)

As an agent running in a caller-owned linked worktree, I want `finalize-tasks` to read and write the mission that exists in that checkout so planning is not silently taken from the primary checkout.

**Why this priority**: A wrong mission surface can finalize or mutate a different mission while reporting success; this is a correctness and data-integrity defect.

**Independent Test**: Create a mission only in a real linked worktree, run `finalize-tasks --validate-only --mission <slug>`, and verify it resolves that mission without reading the primary checkout.

**Acceptance Scenarios**:

1. **Given** a mission exists only in an explicit caller-owned linked worktree, **when** `finalize-tasks --validate-only --mission <slug>` runs, **then** validation reads that worktree's spec/tasks and reports their real validation result.
2. **Given** the primary checkout contains no copy of the mission, **when** the command runs from either relevant CWD with the owned root selected, **then** the primary checkout remains byte-identical.

### User Story 2 - Preserve safe lifecycle routing (Priority: P2)

As a maintainer, I want mission resolution, placement, and target-branch reads to consume the same immutable operation context so sibling lifecycle commands cannot reintroduce an ambient-root fallback.

**Why this priority**: A one-command fix would leave the same boundary leak in related lifecycle paths.

**Independent Test**: Exercise the shared resolver and an architectural census guard that rejects new direct primary-root reconstruction in covered lifecycle consumers.

**Acceptance Scenarios**:

1. **Given** an owned mission and a managed coordination/lane worktree, **when** lifecycle consumers resolve the mission, **then** they agree on repository root, mission anchor, and identity without crossing surfaces.

### User Story 3 - Fail closed on ambiguity (Priority: P3)

As an operator, I want missing, ambiguous, or conflicting mission selectors to produce structured diagnostics rather than silently selecting a plausible directory.

**Why this priority**: Refusing an unsafe operation is preferable to mutating the wrong checkout.

**Independent Test**: Present missing and conflicting mission surfaces and assert stable error codes and safe candidate projections.

**Acceptance Scenarios**:

1. **Given** two same-selector mission copies with different immutable identities, **when** resolution runs, **then** it returns `MISSION_SURFACE_CONFLICT` and does not write either surface.

### Edge Cases

- A mission exists only in a caller-owned worktree and the command is launched from the primary checkout.
- A managed coordination/lane worktree is current; its non-authoritative copy must not hide the primary mission.
- The selector is missing, ambiguous, unsafe, or resolves to different mission IDs across allowed surfaces.
- The owned checkout pointer is nested, foreign, or broken; resolution must refuse with the existing ownership error family.
- `--validate-only` must remain zero-mutation, including event/state files.

## Requirements

### Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Resolve one operation context | Every covered lifecycle command receives one read-only context containing repository root, mission anchor root, canonical mission identity, and checkout provenance. | High | Approved |
| FR-002 | Route finalize reads/writes | `finalize-tasks` resolves mission artifacts, target branch metadata, placement, and workspace reads through that context; it must not reconstruct a primary path from ambient CWD. | High | Approved |
| FR-003 | Preserve legacy topology | Primary-checkout and managed coordination/lane behavior remains unchanged, including existing primary anchoring and fail-closed coordination errors. | High | Approved |
| FR-004 | Conflict diagnostics | Missing, ambiguous, unsafe, foreign, nested, broken, or conflicting selectors return stable structured errors and perform no writes. | High | Approved |
| FR-005 | Validate-only invariant | `--validate-only` performs zero filesystem mutations on both primary and owned surfaces. | High | Approved |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Single authority | Covered lifecycle consumers use the operation-context seam; an architectural census test fails when a sibling path reintroduces direct ambient-root reconstruction. | Reliability | High | Approved |
| NFR-002 | Deterministic resolution | A selector is indexed once per candidate surface per invocation; repeated resolution returns the same identity and anchor. | Reliability | High | Approved |
| NFR-003 | Test quality | New production behavior has red-first regression coverage and targeted tests pass with no newly introduced failures. | Quality | High | Approved |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Git isolation | Changes are made only in the task-owned worktree/branch and delivered through a PR; primary `main` is not edited directly. | Technical | High | Approved |
| C-002 | Compatibility | Existing CLI patch seams and primary/managed topology behavior remain compatible unless the new explicit resolver contract requires a structured refusal. | Technical | High | Approved |
| C-003 | No implicit widening | No installed-wrapper switch or acceptance of unrelated PRs occurs until targeted tests, canary smoke, and review gates pass. | Delivery | High | Approved |

### Key Entities

- **MissionOperationContext**: immutable per-invocation binding of repository root, mission anchor root, canonical mission identity, and checkout provenance.
- **MissionSurfaceConflict**: safe diagnostic projection of same-selector candidates that disagree on immutable mission identity.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A mission present only in an owned linked worktree is resolved by `finalize-tasks --validate-only` from both relevant CWDs without a primary-copy read.
- **SC-002**: Primary checkout byte snapshot is identical before and after owned-checkout validate-only and missing/conflict refusal cases.
- **SC-003**: Targeted resolver/finalize/architecture tests pass; real canary invocation no longer reports `FEATURE_CONTEXT_UNRESOLVED` for a valid owned mission.
- **SC-004**: Existing primary and managed-worktree lifecycle tests remain green, with any pre-existing unrelated failures recorded separately rather than hidden.
