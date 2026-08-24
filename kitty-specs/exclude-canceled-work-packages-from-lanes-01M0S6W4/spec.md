# Mission Specification: Exclude Canceled Work Packages from Lanes

**Mission Branch**: `fix/exclude-canceled-work-packages-from-lanes`  
**Created**: 2026-08-24  
**Status**: Ready for Implementation

**Audience**: Agentic framework core team  
**Source**: [GitHub issue #3432](https://github.com/Priivacy-ai/spec-kitty/issues/3432)  
**Input**: Canceled work packages cannot currently satisfy ownership validation or execution-lane computation, forcing operators to delete workflow-managed files. Address this before #3281 while preserving a clear scope boundary between the two lane-allocation issues.

## Intent and Scope

When an operator cancels a work package because its scope has been absorbed or abandoned, the work package must remain in the mission's auditable history but stop participating in ownership validation and execution-lane computation. An active work package must never silently bypass a dependency through cancellation: if it still depends on a canceled work package, finalization must fail and identify the dependency declaration to repair.

This mission covers cancellation-aware finalization only. It does not change the meaning of `done`, cancellation transitions, planning-history reconciliation, allocation retry recovery, or dependency-lane propagation.

## User Scenarios & Testing

### User Story 1 - Retire Canceled Work Cleanly (Priority: P1)

As a mission operator, I want a canceled work package excluded from ownership checks and execution-lane computation so that I can retire abandoned scope without deleting its prompt or fabricating ownership.

**Why this priority**: This is the release-blocking path in #3432. The supported cancellation transition currently leaves finalization with no valid route forward.

**Independent Test**: Cancel a work package that has no ownership manifest, leave its prompt and task entry intact, then finalize the mission. Finalization succeeds and computes execution lanes only for non-canceled work packages.

**Acceptance Scenarios**:

1. **Given** a mission contains an active work package and a canceled work package with no ownership declaration, **when** the operator finalizes tasks, **then** ownership validation ignores the canceled work package and finalization succeeds for the active work.
2. **Given** a canceled work package still declares files that overlap an active work package, **when** the operator finalizes tasks, **then** the canceled declaration creates neither an ownership conflict nor an execution-lane collapse.
3. **Given** a previously finalized mission is re-finalized after one work package is canceled, **when** execution lanes are recomputed, **then** that work package is absent from every execution lane and surviving lanes derive only from non-canceled work.
4. **Given** every work package is canceled, **when** the operator finalizes tasks, **then** finalization succeeds with no executable work rather than demanding fabricated ownership.

### User Story 2 - Reject Stale Active Dependencies (Priority: P1)

As a mission operator, I want finalization to reject active work that depends on canceled work so that cancellation cannot silently satisfy or bypass a required predecessor.

**Why this priority**: Excluding canceled nodes without checking incoming dependencies would make an invalid directed acyclic graph appear executable.

**Independent Test**: Leave an active work package dependent on a canceled work package and finalize. Finalization fails before publishing a new execution-lane allocation and names both work packages plus the recovery.

**Acceptance Scenarios**:

1. **Given** active `WP04` depends on canceled `WP03`, **when** the operator finalizes tasks, **then** finalization fails explicitly, identifies `WP04` and `WP03`, and directs the operator to remove or repoint the stale dependency.
2. **Given** a canceled work package depends on another canceled work package and no active work depends on either, **when** finalization runs, **then** both are excluded without a stale-active-dependency error.
3. **Given** multiple active work packages reference canceled predecessors, **when** finalization runs, **then** the result reports every stale direct dependency found rather than stopping after an arbitrary first pair.

### User Story 3 - Preserve Existing Lane Semantics (Priority: P2)

As a mission operator, I want missions without canceled work packages to retain their current execution-lane allocation so that the fix does not disturb valid ownership, collapse, or dependency behavior.

**Why this priority**: #3431 already repaired post-collapse cycle detection, while #3281 owns later allocation recovery. This mission must compose with both without redefining them.

**Independent Test**: Finalize equivalent mission definitions with no canceled work before and after the change and compare execution-lane membership, dependency edges, validation results, and cycle findings.

**Acceptance Scenarios**:

1. **Given** a mission has no canceled work packages, **when** it is finalized, **then** its execution-lane membership, ownership findings, dependency edges, and cycle findings remain unchanged.
2. **Given** a work package is `done` rather than `canceled`, **when** finalization runs, **then** this mission does not newly exclude it under the cancellation rule.
3. **Given** canonical lifecycle state cannot be read or validated, **when** finalization runs, **then** it fails through existing status-integrity behavior rather than guessing that a work package is canceled.

### Edge Cases

- A canceled work package has an empty ownership list, planning-artifact mode, or no ownership fields.
- A canceled work package's former ownership overlaps one or many active work packages.
- A canceled work package is the only member of a previously computed execution lane.
- All work packages are canceled, leaving zero executable lanes.
- A surviving dependency points directly or transitively through canceled work.
- A governed force transition reopens a canceled work package before finalization; its current canonical state governs and it participates normally.
- Derived status disagrees with the append-only event history; canonical event-derived state wins or existing integrity checks fail closed.
- Repeated finalization sees the same canonical states but a prior execution-lane manifest; current state determines the new allocation.

## Domain Language

- **Work package**: A bounded, reviewable unit of mission work. Use “work package,” not “task,” for the domain object.
- **Lifecycle lane**: A work package's canonical status, such as `planned`, `approved`, or `canceled`.
- **Execution lane**: A computed grouping used to allocate compatible work packages. Avoid bare “lane” when the lifecycle or execution sense is ambiguous.
- **Canceled work package**: A work package whose current canonical lifecycle lane is `canceled`; it is permanently abandoned unless reopened through the governed transition path.
- **Stale active dependency**: A dependency declared by a non-canceled work package that points to a canceled work package.
- **Execution-lane computation**: Deterministic derivation of execution-lane membership and dependencies from eligible work packages, distinct from later workspace allocation.

## Requirements

### Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Resolve cancellation authoritatively | Finalization must determine cancellation from canonical lifecycle state rather than mutable prompt metadata or file presence. | High | Accepted |
| FR-002 | Exclude canceled ownership | Ownership-manifest presence, validity, overlap, path matching, authoritative-surface, and audit-coverage checks must exclude canceled work packages. | High | Accepted |
| FR-003 | Exclude canceled execution | Execution-lane computation must exclude canceled work packages from membership, write scope, inferred surfaces, dependency grouping, collapse reporting, and parallelization reporting. | High | Accepted |
| FR-004 | Reject stale active dependencies | Before publishing an execution-lane allocation, finalization must fail if any non-canceled work package depends on a canceled work package. | High | Accepted |
| FR-005 | Explain dependency recovery | Each stale-active-dependency diagnostic must identify the dependent work package, canceled dependency, and instruction to remove or repoint the dependency. | High | Accepted |
| FR-006 | Report all stale pairs | A finalization attempt must report every direct stale active dependency it detects so the graph can be repaired in one pass. | Medium | Accepted |
| FR-007 | Preserve canceled history | Finalization must not require deletion of a canceled work package prompt, task-outline entry, or lifecycle history. | High | Accepted |
| FR-008 | Support zero executable work | A mission in which every work package is canceled must finalize to a valid no-executable-work result. | Medium | Accepted |
| FR-009 | Honor reopened state | A formerly canceled work package validly reopened before finalization must participate according to its current canonical state. | Medium | Accepted |
| FR-010 | Preserve unaffected behavior | Missions without canceled work must retain existing ownership, grouping, dependency, collapse-cycle, and reporting behavior. | High | Accepted |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Deterministic results | For identical mission definitions and canonical lifecycle states, 100% of repeated finalization runs must produce the same execution-lane membership, dependency edges, and stale-dependency findings. | Reliability | High | Accepted |
| NFR-002 | Complete diagnostics | In acceptance coverage, 100% of stale active dependency findings must name both work-package IDs and include a corrective action. | Operability | High | Accepted |
| NFR-003 | Typical-scale performance | On the repository's reference performance runner (Blacksmith 4-vCPU Ubuntu 24.04, CPython 3.11), the p95 of 10 measured finalizations of the canonical 100-work-package fixture, after two discarded warm-up rounds, must be at most two seconds. | Performance | Medium | Accepted |
| NFR-004 | Fail-closed status handling | In 100% of unreadable or corrupt status-authority cases, finalization must refuse to infer cancellation from secondary data. | Integrity | High | Accepted |
| NFR-005 | Regression containment | Existing execution-lane, ownership, and post-collapse-cycle acceptance coverage for missions without canceled work must retain its prior outcome. | Compatibility | High | Accepted |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical status authority | Append-only mission event history remains the sole authority for mutable work-package lifecycle state; derived views and frontmatter cannot become competing authorities. | Architecture | High | Accepted |
| C-002 | Cancellation-only scope | Automatic exclusion applies only to current `canceled` state; this mission must not generalize exclusion to `done` or every terminal state. | Scope | High | Accepted |
| C-003 | Audit preservation | Canceled work-package definitions and lifecycle evidence must be preserved; manual deletion is not an acceptable retirement mechanism. | Governance | High | Accepted |
| C-004 | Existing DAG protection | Post-collapse execution-lane acyclicity delivered for #3431 remains authoritative over the surviving graph. | Dependency | High | Accepted |
| C-005 | Separate allocator recovery | Planning-history reconciliation, incomplete-allocation recovery, workspace reuse, and approved dependency-tip propagation remain within #3281. | Scope | High | Accepted |
| C-006 | Cross-platform behavior | Functional behavior and diagnostic payloads must remain consistent on Linux, macOS, and Windows 10 or later, with at least one cancellation-policy test collected by the repository's `windows_ci` job. | Platform | Medium | Accepted |

### Key Entities

- **Work Package Definition**: Static intent, dependencies, and ownership retained even when the work package is canceled.
- **Lifecycle State**: Current event-derived status deciding whether a work package is eligible for execution-lane computation.
- **Dependency Edge**: A directed prerequisite; an edge from active work to canceled work is stale and invalid.
- **Execution-Lane Manifest**: Persisted allocation containing only eligible work packages and their execution-lane dependencies.
- **Ownership Declaration**: Files or surfaces eligible work may change; canceled declarations remain historical data but do not constrain active allocation.

## Dependencies and Assumptions

- #3431 is merged; its post-collapse execution-lane cycle detection is the baseline.
- #3281 remains downstream and separately owns planning-history reconciliation, allocation retry, and dependency propagation.
- #3127 remains the broader Wave 0 root identified by the execution DAG, but is assigned outside this mission.
- Operators emit the governed transition to `canceled` before re-running finalization.
- An active dependency on canceled work requires human correction; cancellation neither propagates nor satisfies dependencies.
- If all work is canceled, “no executable work” is a valid result while lifecycle history remains intact.

## Out of Scope

- Changing transitions into or out of `canceled`.
- Automatically canceling dependents or rewriting dependency declarations.
- Treating `canceled` as dependency satisfaction.
- Excluding `done` under this rule.
- Deleting or archiving work-package prompts, task-outline sections, or events.
- Repairing planning-commit conflicts, incomplete workspace allocation, or dependency-lane ancestry from #3281.
- Revisiting execution-lane cycle semantics delivered for #3431.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Operators can cancel a work package and finalize without deleting or fabricating any workflow-managed file in 100% of acceptance scenarios.
- **SC-002**: Canceled work packages appear in zero execution lanes and contribute zero ownership conflicts or collapse events.
- **SC-003**: Every active-to-canceled dependency is rejected before allocation is published, with both work-package IDs and a recovery action.
- **SC-004**: Missions without canceled work retain identical execution-lane membership, dependency edges, ownership findings, and cycle findings across the regression corpus.
- **SC-005**: On the reference performance runner, the canonical 100-work-package fixture has p95 finalization time at or below two seconds across 10 measured rounds after two warm-ups.
- **SC-006**: A mission with only canceled work reaches a valid no-executable-work result while retaining all definitions and lifecycle history.
