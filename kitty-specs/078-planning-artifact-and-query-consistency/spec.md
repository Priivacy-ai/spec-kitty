# Spec: Planning Artifact and Query Consistency

**Mission:** 078-planning-artifact-and-query-consistency
**Mission type:** software-dev
**Status:** Specified
**Target branch:** main

---

## Overview

Spec Kitty currently applies two conflicting runtime models to valid work packages and mission runs:

- Planning-artifact work packages are intentionally excluded from the execution lane graph, but some downstream workflow and workspace consumers still treat lane membership as mandatory.
- Fresh mission-run query mode can report an "unknown" state even when the mission definition itself is valid and the next step is deterministically knowable.

This mission establishes one explicit contract across planning, runtime, workflow, stale detection, and documentation:

- `execution_mode` is the top-level workspace contract.
- `planning_artifact` work packages remain outside the execution lane graph and resolve to the repository root.
- Query mode is read-only, does not require `--agent`, and reports an explicit not-started state plus a deterministic preview of the first step when nothing has been issued yet.

---

## Problem Statement

Three validated issues expose the same underlying design gap: producer and consumer surfaces do not share a single model for where work runs and how read-only runtime state should be represented.

1. Planning-artifact work packages are surfaced as valid planning outputs but can still be rejected by commands that assume every work package must belong to an execution lane.
2. Workflow and stale-detection commands can fail on planning-artifact work packages even though those work packages are valid by design.
3. Fresh-run `spec-kitty next` query mode collapses "no step issued yet" into a misleading `unknown` state and requires an agent identifier that has no meaning in read-only mode.

Part of the runtime already models repository-root planning work correctly, but that behavior is not yet the single shared authority used by downstream workflow and query consumers. This mission closes that contract gap rather than inventing a second abstraction.

If these contracts remain ambiguous, Spec Kitty continues to teach one model, persist another, and execute a third.

---

## Goals

- Make planning-artifact work packages first-class runtime citizens without inventing synthetic execution lanes for them.
- Establish a single canonical workspace-resolution contract that all consumers share.
- Make fresh-run query mode truthful, deterministic, and useful before any step has been issued.
- Align active documentation and command contracts with the runtime behavior users should rely on.

## Non-Goals

- Redesigning lane computation for `code_change` work packages.
- Changing the lifecycle status-lane model (`planned`, `doing`, `for_review`, `done`).
- Introducing a new `--query` flag or changing the meaning of advancing results.
- Requiring operators to migrate or rewrite historical mission artifacts before they can continue working.

---

## Actors

| Actor | Description |
|-------|-------------|
| Mission operator | A human running Spec Kitty commands to inspect state, implement work packages, and coordinate mission progress. |
| AI agent | An automated coding agent using Spec Kitty as an execution and coordination surface. |
| Runtime | The Spec Kitty command layer that resolves workspaces, reports mission state, and advances mission steps. |
| Documentation reader | A contributor using docs and command help to understand the correct invocation contract. |

---

## User Scenarios & Testing

### Scenario 1 - Task Status Shows Planning-Artifact Work As Valid Repo-Root Work

**Given** a mission whose finalized work packages include both `code_change` and `planning_artifact` items
**When** the operator runs `spec-kitty agent tasks status`
**Then** the output includes the planning-artifact work packages in normal lifecycle status reporting, and makes clear that their execution context is repository-root planning work rather than a missing-lane error.

**Acceptance**: The command exits successfully, includes every planning-artifact work package in human-readable and JSON status output, and does not require execution-lane membership to report them.

### Scenario 2 - Implement Resolves Planning-Artifact Work Without Lane Failure

**Given** a valid planning-artifact work package in `planned` status
**When** the operator runs `spec-kitty agent action implement <wp-id>`
**Then** the command resolves the work package to the repository root, begins the implement workflow, and continues the normal lifecycle transition without any "work package is not in a lane" failure.

**Acceptance**: The implement command starts successfully for a planning-artifact work package, uses the repository root as its workspace, and preserves the same lifecycle progression rules used for other work packages.

### Scenario 2b - Planning-Artifact Review And Completion Use Artifact Acceptance, Not Lane Merge

**Given** a planning-artifact work package that has been implemented in the repository root
**When** it moves through review and completion
**Then** it uses the same lifecycle statuses as any other valid work package, but its completion is defined by accepted repository-root artifacts rather than by merging a lane-backed branch or worktree.

**Acceptance**: For planning-artifact work packages, `for_review` means the repository-root artifacts are ready for review, and `done` means those artifacts have been accepted as complete. No lane-merge precondition is required.

### Scenario 3 - Workspace Lookup Succeeds And Planning-Artifact Staleness Is Explicitly Exempt

**Given** a planning-artifact work package that is subject to stale detection or any other workspace lookup
**When** the runtime checks that work package's workspace or evaluates staleness
**Then** workspace lookup resolves through the same canonical contract used by implement, returns the repository root, and completes without requiring a synthetic execution lane. Workspace-based stale detection does not treat unrelated repository-root activity as proof that the work package is fresh.

**Acceptance**: Workspace-dependent commands return a valid workspace for both execution modes and never fail solely because a planning-artifact work package is intentionally outside the execution lane graph. For planning-artifact work packages, stale detection reports workspace freshness as not applicable unless a separate work-package-scoped freshness rule is defined.

### Scenario 4 - Fresh Query Mode Reports Not-Started State Honestly

**Given** a valid mission run with no issued step yet
**When** the operator runs `spec-kitty next --mission-run <slug>` with no `--result`
**Then** the command stays read-only and reports that the run is `not_started` while also previewing the first issuable step.

**Acceptance**: For a valid mission definition, human-readable output uses the shape below, and JSON output exposes `mission_state: "not_started"` and `preview_step: "<first-step-id>"` without advancing state. If the mission definition has no issuable first step, query mode fails with an actionable validation error instead of returning `unknown` or an empty success response.

```text
[QUERY - run not started, state not advanced]
  Mission: software-dev @ not_started
  Next step: discovery
  Run ID: <run-id>
```

### Scenario 5 - Query Mode Does Not Require An Agent Identifier

**Given** an operator or automation that wants a read-only answer about a mission run
**When** it calls `spec-kitty next --mission-run <slug>` without `--result`
**Then** the command succeeds without requiring `--agent`.

**Acceptance**: Query mode is documented and supported without `--agent`. If an existing caller still supplies `--agent` in query mode, the command remains read-only and returns the same state answer.

### Scenario 6 - Docs And Help Teach One Canonical Contract

**Given** a contributor reading active Spec Kitty docs or command help
**When** they look up planning-artifact execution behavior or query-mode syntax
**Then** they see one consistent public contract:

- planning-artifact work packages remain outside the execution lane graph and resolve to repository root
- query mode is `spec-kitty next --mission-run <slug>`
- advancing mode is `spec-kitty next --agent <agent> --mission-run <slug> --result <outcome>`

**Acceptance**: Active docs and command reference examples contain no contradictory syntax or behavioral explanation for these flows.

### Scenario 7 - Existing Missions Continue Without Artifact Migration

**Given** an existing mission with planning-artifact work packages or an existing mission run that has not yet issued a step
**When** the operator uses status, implement, stale detection, or query mode after this mission ships
**Then** the commands follow the new public contract without requiring manual edits to mission artifacts or run records.

**Acceptance**: Existing missions remain operable with zero mandatory migration steps.

---

## Functional Requirements

### Workspace Contract

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `execution_mode` is the sole top-level authority for determining where a work package runs. | Proposed |
| FR-002 | Work packages with `execution_mode: planning_artifact` remain outside the execution lane graph by design. Their absence from the lane graph is valid behavior, not an error condition. | Proposed |
| FR-002a | Supported historical missions whose persisted work-package artifacts predate explicit `execution_mode` declaration remain operable without manual artifact edits. Before workspace resolution is applied, the runtime establishes an equivalent execution-mode classification for those missions from their existing mission metadata. | Proposed |
| FR-003 | Work packages with `execution_mode: code_change` continue to resolve through the execution lane graph to their lane-backed workspace. | Proposed |
| FR-004 | Work packages with `execution_mode: planning_artifact` resolve to the repository root workspace. | Proposed |
| FR-005 | Lifecycle status reporting continues to include all valid work packages regardless of execution mode. Execution-lane membership is not a prerequisite for appearing in task status. | Proposed |
| FR-006 | All workspace-dependent command flows share one canonical workspace-resolution contract so operators do not encounter mode-specific contradictions between status, implement, stale detection, or other workspace lookups. | Proposed |

### Workflow And Status Behavior

| ID | Requirement | Status |
|----|-------------|--------|
| FR-007 | `spec-kitty agent tasks status` reports planning-artifact work packages as valid repository-root work and does not present them as missing-lane failures. | Proposed |
| FR-008 | `spec-kitty agent action implement <wp-id>` starts successfully for a planning-artifact work package, uses the repository root workspace, and preserves the normal lifecycle transition behavior for that work package. | Proposed |
| FR-008a | Planning-artifact work packages use the same lifecycle statuses as other valid work packages. For those work packages, `for_review` means repository-root artifacts are ready for review, and `done` means those artifacts have been accepted as complete. No lane-merge or worktree-merge precondition exists for completion. | Proposed |
| FR-009 | Stale detection and any other workspace lookup succeed for both execution modes through the same canonical contract and do not require synthetic execution lanes for planning-artifact work packages. For planning-artifact work packages, workspace-based stale detection must report freshness as not applicable unless a separate work-package-scoped rule is defined. Shared repository-root activity is not a valid freshness signal. | Proposed |
| FR-010 | Any lane-oriented diagnostic or planning output distinguishes between lane-backed work packages and intentionally lane-less planning-artifact work packages without inventing placeholder lane membership. | Proposed |

### Query-Mode Contract

| ID | Requirement | Status |
|----|-------------|--------|
| FR-011 | Calling `spec-kitty next` without `--result` enters read-only query mode. Query mode does not advance mission state. | Proposed |
| FR-012 | The public query-mode contract is `spec-kitty next --mission-run <slug>`. `--agent` is not required in query mode. | Proposed |
| FR-013 | If a caller provides `--agent` in query mode for compatibility, the command still behaves as query mode and does not treat the agent identifier as a required lifecycle input. | Proposed |
| FR-014 | For a mission run with no issued step yet, query mode returns `mission_state: "not_started"` and a separate `preview_step` that names the first issuable step. | Proposed |
| FR-014a | If a mission definition has no issuable first step, fresh-run query mode fails with an actionable validation error instead of returning `unknown`, omitting the preview, or fabricating a step. | Proposed |
| FR-015 | Fresh-run human-readable query output explicitly says the run has not started and names the next step. It does not present the run as `unknown`. | Proposed |
| FR-016 | Advancing mode remains the only path that issues or advances mission steps, and it continues to require both `--agent` and `--result`. | Proposed |

### Documentation And Compatibility

| ID | Requirement | Status |
|----|-------------|--------|
| FR-017 | Active documentation and command reference surfaces describe the same canonical distinction between execution-lane membership and execution-mode-aware workspace resolution. | Proposed |
| FR-018 | Active documentation and command reference surfaces describe query mode and advancing mode using one consistent syntax and behavior contract. | Proposed |
| FR-019 | Existing missions and mission runs continue to work under the new contract without mandatory artifact migration or record backfill. | Proposed |
| FR-020 | Active documentation and machine-facing contract references explicitly state that valid fresh-run query responses now use `mission_state: "not_started"` plus `preview_step`. `unknown` is no longer the canonical fresh-run state for a valid mission run. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Workspace resolution is deterministic and independent of ambient caller context for both execution modes. | For an unchanged mission snapshot, 100 out of 100 repeated resolutions of the same work package return the same workspace classification and target path even when invoked from different current working directories within the same repository. | Proposed |
| NFR-002 | Query mode is non-mutating. | For an unchanged mission run, 100 out of 100 repeated query-mode calls leave mission state unchanged. | Proposed |
| NFR-003 | Query and workspace-dependent commands remain responsive. | Status, query mode, implement setup, and stale detection complete in under 1 second for local missions with up to 20 work packages. | Proposed |
| NFR-004 | Existing users are not forced through manual migration. | Existing missions and fresh mission runs require zero mandatory artifact edits before the new contract works. | Proposed |
| NFR-005 | Documentation parity is complete at release time. | Zero contradictory examples remain across active index, runtime-loop, and CLI-reference documentation for these contracts. | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Planning-artifact work packages must not be assigned synthetic execution-lane membership solely to satisfy downstream consumers. | Required |
| C-002 | Workspace resolution must remain execution-mode-aware and must not treat execution-lane membership as the universal source of truth. | Required |
| C-003 | Query mode must remain read-only; only calls with `--result` may advance mission state. | Required |
| C-004 | The public query-mode contract must not require `--agent`. Compatibility support for callers that still pass `--agent` may remain, but that form is not the primary documented interface. | Required |
| C-005 | The lifecycle status-lane model remains unchanged and continues to apply to all valid work packages, including planning-artifact work. | Required |
| C-006 | Existing mission artifacts and mission-run records must remain usable without a mandatory migration step. | Required |
| C-007 | Deterministic mission-step ordering must be preserved. Query preview may reveal the first issuable step but must not issue it. | Required |
| C-008 | Shared repository-root activity must not be used as a freshness proxy for planning-artifact work packages. | Required |

---

## Compatibility And Migration

- No new execution-lane entries are introduced for planning-artifact work packages.
- Existing lane manifests remain valid because planning-artifact work packages continue to be represented as lane exclusions rather than lane members.
- Existing mission runs with no issued step do not need backfilled step identifiers. Query mode derives `not_started` and `preview_step` from existing mission and run state.
- Existing supported missions that do not persist `execution_mode` remain in scope for zero-migration use. The runtime must classify their workspace contract from existing mission metadata before applying the canonical resolver.
- Existing automation that already passes `--agent` in query mode remains compatible, but active docs and examples move to the agent-optional query contract.
- Machine consumers that currently treat `mission_state: "unknown"` as the valid fresh-run query response must update to the new explicit contract. This is an intentional query-output contract change, not a mission-artifact migration requirement.

---

## Success Criteria

1. Operators can list, implement, review, and complete any valid planning-artifact work package without encountering a lane-membership or lane-merge failure.
2. Planning-artifact work packages do not receive misleading stale/fresh classifications from shared repository-root activity; workspace-based staleness is explicitly not applicable unless a work-package-scoped rule exists.
3. A fresh mission run queried with `spec-kitty next --mission-run <slug>` returns a not-started state and names the next step without advancing runtime state.
4. Operators can use query mode without inventing a placeholder agent identifier.
5. Existing missions and mission runs continue working without mandatory artifact edits.
6. Active docs and command reference surfaces present one consistent workspace-resolution and query-mode contract, with zero contradictory examples.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| Execution Mode | The canonical declaration of how a work package runs. In this mission, the relevant modes are `code_change` and `planning_artifact`. |
| Execution Lane Graph | The lane-backed parallel-work topology used for work packages that require lane/worktree resolution. Planning-artifact work packages are intentionally outside this graph. |
| Lifecycle Status Lane | The work-package progress states used by task-status reporting, such as `planned`, `doing`, `for_review`, and `done`. These apply to all valid work packages regardless of execution mode. |
| Workspace Contract | The user-visible rule that determines where a work package runs. This mission makes it execution-mode-aware instead of lane-only. |
| Planning-Artifact Completion Contract | The rule that planning-artifact work reaches `for_review` and `done` through acceptance of repository-root artifacts, not through lane merge semantics. |
| Query Mode | The read-only form of `spec-kitty next` entered when `--result` is omitted. |
| Query Preview | The deterministic preview of the next issuable step returned by query mode when a mission run has not started yet. |
| Mission State | The lifecycle state of a mission run. This mission introduces an explicit `not_started` query result for valid fresh runs with no issued step. |

---

## Dependencies And Assumptions

### Dependencies

- Some current runtime paths already model repository-root planning work correctly, but that behavior is not yet the single authoritative contract across workflow and query consumers.
- Existing planning outputs already distinguish planning-artifact work packages from lane-backed code-change work.
- Active docs and command help remain the authoritative public explanation of CLI behavior.

### Assumptions

- Planning-artifact work packages are a long-term supported part of the mission model rather than a temporary exception.
- Supported historical missions that predate explicit `execution_mode` still retain enough metadata for deterministic compatibility classification without manual artifact edits.
- The first issuable step for a fresh mission run can be determined without mutating runtime state.
- Users benefit from keeping execution-lane topology separate from lifecycle status reporting.
- Compatibility support for query-mode callers that still pass `--agent` is desirable during the transition to the simplified public contract.

---

## Out Of Scope

- Redefining how `code_change` work packages are assigned to execution lanes.
- Changing the names or semantics of lifecycle status lanes.
- Introducing a new public flag for query mode.
- Adding new execution modes beyond the current planning-artifact and code-change distinction.
- Rewriting historical mission documents solely for wording consistency outside the active documentation surfaces affected by this mission.
