# Mission Specification: Reject Cyclic Lane Graphs

**Mission Branch**: `fix/reject-cyclic-lane-graphs`  
**Created**: 2026-08-23  
**Status**: Ready for Planning  
**Input**: [GitHub issue #3431](https://github.com/Priivacy-ai/spec-kitty/issues/3431)

## Intent Summary

Spec Kitty maintainers and operators need `finalize-tasks` to reject an
unexecutable execution-lane dependency graph when ownership-overlap collapse
turns an otherwise acyclic work-package graph into a cycle. The command must
fail before persistence, preserve any valid existing `lanes.json`, identify the
cycle, and never report success for the invalid result. The defensive
lower-level depth calculation may remain non-crashing, but it must not make a
cyclic final manifest acceptable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy task finalization (Priority: P1)

As a Spec Kitty operator, I want task finalization to reject a cyclic execution
plan so that a reported success always represents work that can actually be
allocated and executed.

**Why this priority**: A false success creates a deadlocked mission and allows
an invalid planning artifact to become authoritative.

**Independent Test**: Finalize a mission whose work-package dependencies are
acyclic before ownership-overlap collapse but whose resulting execution lanes
depend on each other. The command fails, identifies the cycle, and does not
persist the cyclic result.

**Acceptance Scenarios**:

1. **Given** an acyclic work-package dependency graph whose ownership-overlap collapse produces two mutually dependent execution lanes, **When** the operator runs `finalize-tasks`, **Then** finalization fails and does not create `lanes.json`.
2. **Given** the same cyclic result and an existing valid `lanes.json`, **When** the operator reruns `finalize-tasks`, **Then** finalization fails and preserves the existing file unchanged.
3. **Given** ownership-overlap collapse that produces an acyclic execution-lane graph, **When** the operator runs `finalize-tasks`, **Then** finalization succeeds and persists the result as before.

---

### User Story 2 - Actionable cycle diagnosis (Priority: P2)

As a Spec Kitty operator, I want the failure to identify the circular
dependency so that I can correct work-package dependencies or ownership without
reverse-engineering `lanes.json`.

**Why this priority**: Rejecting the graph prevents corruption; naming the cycle
makes the refusal recoverable.

**Independent Test**: Trigger a cycle involving three execution lanes and
verify that both human-readable and structured output identify a complete
closed dependency path and the work packages assigned to its lanes.

**Acceptance Scenarios**:

1. **Given** a cyclic execution-lane graph, **When** finalization fails, **Then** the diagnostic identifies at least one complete closed cycle and the work-package membership of each named execution lane.
2. **Given** structured output is requested, **When** finalization rejects the graph, **Then** the response carries a stable machine-readable cycle classification and cycle details rather than a success result.
3. **Given** the same inputs are finalized repeatedly, **When** the cycle is reported, **Then** the cycle path is ordered consistently across runs.

### Edge Cases

- A cycle may contain more than two execution lanes; detection must not be limited to mutual pairs.
- Multiple cycles may exist; reporting one complete deterministic cycle is sufficient to make the refusal actionable.
- Planning-artifact execution lanes participate in the same validation when they carry dependencies.
- A failure must preserve the prior artifact even when the newly computed graph differs in every execution lane.
- The absence of a prior `lanes.json` must remain absence; a rejected diagnostic graph is not persisted as an artifact.

## Domain Language

- **Work package**: The canonical executable slice of work inside a Mission, typically identified as `WPxx`.
- **Execution lane**: A group of work packages allocated together because of shared ownership or planning semantics. This term is distinct from a work package's lifecycle **Lane** (`planned`, `in_progress`, `done`, and related states).
- **Execution-lane dependency graph**: The directed dependency relationships between execution lanes after grouping and ownership-overlap collapse.
- **Cyclic execution plan**: An execution-lane dependency graph containing a closed dependency path, making at least part of the plan impossible to allocate in dependency order.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Validate the final graph | As an operator, I want the post-collapse execution-lane dependency graph checked for cycles before it is accepted. | High | Open |
| FR-002 | Fail on every cycle | As an operator, I want any detected execution-lane cycle to make `finalize-tasks` fail rather than report success. | High | Open |
| FR-003 | Prevent invalid persistence | As an operator, I want a rejected cyclic graph never to create or replace `lanes.json`. | High | Open |
| FR-004 | Preserve prior valid state | As an operator, I want any existing valid `lanes.json` preserved unchanged when a newly computed graph is rejected. | High | Open |
| FR-005 | Identify a complete cycle | As an operator, I want the failure to name at least one complete closed dependency path and the work packages assigned to its execution lanes. | High | Open |
| FR-006 | Support structured callers | As an automation author, I want structured output to carry a stable cycle classification and cycle details with a failure result. | Medium | Open |
| FR-007 | Preserve valid finalization | As an operator, I want acyclic execution-lane graphs to finalize and persist with their existing observable behavior. | High | Open |
| FR-008 | Keep defensive depth handling | As a maintainer, I want direct depth calculation over malformed cyclic input to remain non-crashing while final manifest acceptance independently rejects cycles. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Artifact integrity | In 100% of rejected cyclic finalizations, a pre-existing `lanes.json` remains byte-identical and an absent file remains absent. | Reliability | High | Open |
| NFR-002 | Deterministic diagnosis | For identical inputs, 100% of repeated runs return the same cycle classification and ordered cycle path. | Reliability | High | Open |
| NFR-003 | Mission-scale responsiveness | For missions containing up to 100 work packages, cycle validation adds no more than 100 milliseconds to task finalization under normal local operating conditions. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Post-collapse authority | Validation applies to the final execution-lane graph after all grouping and ownership-overlap collapse, not only to the authored work-package graph. | Product boundary | High | Open |
| C-002 | No diagnostic artifact | A cyclic graph may be returned in failure diagnostics but must not be persisted as `lanes.json`. | Data integrity | High | Open |
| C-003 | Compatibility boundary | Valid acyclic missions, the persisted manifest contract, and direct defensive depth calculation remain compatible with current behavior. | Compatibility | High | Open |
| C-004 | Focused scope | This Mission does not redesign ownership-overlap collapse or automatically rewrite dependencies to break a cycle. | Scope | Medium | Open |

### Key Entities

- **Work package**: Carries authored dependencies and ownership that contribute to execution grouping.
- **Execution lane**: Contains one or more work packages and depends on zero or more other execution lanes.
- **Cycle diagnostic**: The rejected result's stable classification, ordered closed dependency path, and work-package membership needed for operator remediation.
- **Lane manifest**: The accepted persisted execution plan; only an acyclic final graph may become this authoritative artifact.

## Assumptions

- The authored work-package dependency graph continues to use its existing validation; this Mission closes the distinct cycle introduced during execution-lane collapse.
- Reporting one complete deterministic cycle is sufficient even if additional cycles exist.
- Operators remediate the source dependencies or ownership declarations and rerun finalization; automatic graph repair is out of scope.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every rejecting fixture in which collapse creates a two-lane or longer cycle returns failure and persists no cyclic manifest.
- **SC-002**: In every rejection test with a pre-existing valid `lanes.json`, the file is byte-identical before and after finalization.
- **SC-003**: Every cycle diagnostic names a complete closed path and its execution lanes' work-package membership in both human-readable and structured modes.
- **SC-004**: All existing acceptance coverage for acyclic execution-lane computation and successful task finalization remains green.
- **SC-005**: Repeated finalization of the same cyclic input produces identical structured cycle details in every run.
