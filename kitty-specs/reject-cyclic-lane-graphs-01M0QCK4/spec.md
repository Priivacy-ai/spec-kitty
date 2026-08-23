# Mission Specification: Reject Cyclic Lane Graphs

**Mission Branch**: `fix/reject-cyclic-lane-graphs`  
**Created**: 2026-08-23  
**Status**: Ready for Planning  
**Input**: [GitHub issue #3431](https://github.com/Priivacy-ai/spec-kitty/issues/3431)

## Intent Summary

Spec Kitty maintainers and operators need
`spec-kitty agent mission finalize-tasks` to reject an
unexecutable execution-lane dependency graph when ownership-overlap collapse
turns an otherwise acyclic work-package graph into a cycle. The command must
fail before creating or replacing `lanes.json`, preserve any valid existing
`lanes.json`, identify the cycle, and never report success for the invalid
result. This persistence guarantee is intentionally limited to the lane
manifest; rollback of non-lane state written earlier in finalization is outside
this Mission.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy task finalization (Priority: P1)

As a Spec Kitty operator, I want task finalization to reject a cyclic execution
plan so that a reported success always represents work that can actually be
allocated and executed.

**Why this priority**: A false success creates a deadlocked mission and allows
an invalid planning artifact to become authoritative.

**Independent Test**: Run `spec-kitty agent mission finalize-tasks` for a
Mission whose work-package dependencies are acyclic before ownership-overlap
collapse but whose resulting execution lanes depend on each other. The command
fails, identifies the cycle, and does not persist the cyclic result.

**Acceptance Scenarios**:

1. **Given** an acyclic work-package dependency graph whose ownership-overlap collapse produces two mutually dependent execution lanes, **When** the operator runs `spec-kitty agent mission finalize-tasks`, **Then** finalization exits nonzero and does not create `lanes.json`.
2. **Given** the same cyclic result and an existing valid `lanes.json`, **When** the operator reruns `spec-kitty agent mission finalize-tasks`, **Then** finalization exits nonzero and preserves the existing file byte-for-byte.
3. **Given** the same cyclic result, **When** the operator runs `spec-kitty agent mission finalize-tasks --validate-only`, **Then** validation exits nonzero, reports the same cycle contract, and performs no mutation.
4. **Given** ownership-overlap collapse that produces an acyclic execution-lane graph, **When** the operator runs either mutating or `--validate-only` mission finalization, **Then** the command succeeds with its existing observable behavior.

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

1. **Given** a cyclic execution-lane graph, **When** mutating or validation-only finalization fails, **Then** the diagnostic identifies at least one complete closed cycle and the work-package membership of each named execution lane.
2. **Given** `--json` is requested, **When** finalization rejects the graph, **Then** it exits nonzero and returns `error_code: "LANE_DEPENDENCY_CYCLE"`, a human-readable `error`, a closed `cycle_path` array whose first lane is repeated at the end, and a `cycle_lanes` array containing each lane's `lane_id` and sorted `wp_ids`.
3. **Given** equivalent graph inputs with different insertion orders, process hash seeds, or multiple available cycles, **When** the cycle is reported, **Then** the structured cycle details are identical.

### Edge Cases

- A cycle may contain more than two execution lanes; detection must not be limited to mutual pairs.
- Multiple cycles may exist; reporting one complete deterministic cycle is sufficient to make the refusal actionable.
- Planning-artifact execution lanes participate in the same validation when they carry dependencies.
- A failure must preserve the prior artifact even when the newly computed graph differs in every execution lane.
- The absence of a prior `lanes.json` must remain absence; a rejected diagnostic graph is not persisted as an artifact.
- Cycle selection examines lane IDs and each lane's dependency IDs in lexical order, reports the first directed cycle encountered, and rotates that cycle to begin at its smallest lane ID while preserving direction; `cycle_lanes` follows first appearance in the closed `cycle_path` and excludes the repeated closing lane.

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
| FR-006 | Support structured callers | As an automation author, I want structured output to use the specified `LANE_DEPENDENCY_CYCLE` envelope and a nonzero exit. | High | Open |
| FR-007 | Preserve valid finalization | As an operator, I want acyclic execution-lane graphs to finalize and persist with their existing observable behavior. | High | Open |
| FR-008 | Validate without mutation | As an operator, I want `--validate-only` to reject the same cyclic final graph with the same diagnostic contract and no mutation. | High | Open |
| FR-009 | Canonical deterministic cycle | As an automation author, I want equivalent inputs to select and normalize the same diagnostic cycle across runs and environments. | Medium | Open |
| FR-010 | Terminate safely | As an operator, I want cyclic input to produce the governed failure without recursion failure, traceback, or indefinite execution. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Artifact integrity | In 100% of rejected cyclic finalizations, a pre-existing `lanes.json` remains byte-identical and an absent file remains absent. | Reliability | High | Open |
| NFR-002 | Deterministic diagnosis | Across permuted equivalent input order and at least three process hash seeds, 100% of runs return byte-equivalent structured cycle details. | Reliability | High | Open |
| NFR-003 | Mission-scale responsiveness | For a fixed fixture of 100 execution lanes and 500 dependency edges, the p95 of 20 cycle-validation runs after 5 warm-up runs is at most 100 milliseconds on the CI runner. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Post-collapse authority | Validation applies to the final execution-lane graph after all grouping and ownership-overlap collapse, not only to the authored work-package graph. | Product boundary | High | Open |
| C-002 | No diagnostic artifact | A cyclic graph may be returned in failure diagnostics but must not be persisted as `lanes.json`. | Data integrity | High | Open |
| C-003 | Single acceptance authority | The post-collapse graph has one canonical accepted-or-rejected outcome shared by mutating and validation-only modes; no caller may independently reinterpret a rejected cyclic graph as acceptable. | Product boundary | High | Open |
| C-004 | Focused scope | This Mission does not redesign ownership-overlap collapse or automatically rewrite dependencies to break a cycle. | Scope | Medium | Open |
| C-005 | Persistence boundary | The no-write guarantee covers creation or replacement of `lanes.json`; rollback or reordering of earlier non-lane finalization mutations is outside scope. | Scope | High | Open |
| C-006 | Command boundary | The governed surfaces are mutating and `--validate-only` modes of `spec-kitty agent mission finalize-tasks`; the separate legacy `spec-kitty agent tasks finalize-tasks` surface does not compute execution lanes and is outside scope. | Compatibility | High | Open |

### Key Entities

- **Work package**: Carries authored dependencies and ownership that contribute to execution grouping.
- **Execution lane**: Contains one or more work packages and depends on zero or more other execution lanes.
- **Cycle diagnostic**: The rejected result's stable classification, ordered closed dependency path, and work-package membership needed for operator remediation.
- **Lane manifest**: The accepted persisted execution plan; only an acyclic final graph may become this authoritative artifact.

## Assumptions

- The authored work-package dependency graph continues to use its existing validation; this Mission closes the distinct cycle introduced during execution-lane collapse.
- Reporting one complete deterministic cycle is sufficient even if additional cycles exist.
- Operators remediate the source dependencies or ownership declarations and rerun finalization; automatic graph repair is out of scope.
- Non-lane state that canonical mission finalization records before lane computation remains governed by its existing behavior and is not rolled back by this Mission.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fixture matrix covering a two-lane cycle, a cycle of three or more lanes, multiple available cycles, planning-lane participation, absent `lanes.json`, an existing valid `lanes.json`, mutating mode, and `--validate-only` returns failure and persists no cyclic manifest in every applicable cell.
- **SC-002**: In every rejection test with a pre-existing valid `lanes.json`, the file is byte-identical before and after finalization.
- **SC-003**: Every cycle diagnostic names a complete closed path and its execution lanes' work-package membership in both human-readable and the specified structured envelope.
- **SC-004**: All existing acceptance coverage for acyclic execution-lane computation and successful task finalization remains green.
- **SC-005**: Equivalent graphs with permuted input order, multiple available cycles, and at least three process hash seeds produce byte-equivalent structured cycle details in every run.
