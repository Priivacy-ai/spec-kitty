# Mission & Build Identity Contract Cutover

**Mission**: 075-mission-build-identity-contract-cutover
**Mission Type**: software-dev
**Status**: Draft
**Created**: 2026-04-07

## Overview

Spec Kitty tracks development work through "missions." Internally, earlier versions used the word "feature" for this concept — in commands, events, API responses, and configuration. That legacy naming has been replaced in the canonical event and data contracts (spec-kitty-events 3.0.0 and spec-kitty-saas), but the spec-kitty runtime still emits and accepts feature-era names on its live surfaces. This mission cuts over the runtime to match those canonical contracts.

Additionally, build identity — the ability to distinguish one checkout or worktree from another — is currently incomplete. This mission makes build identity a first-class persisted concept: each concrete checkout carries a stable identifier that travels with every emitted event.

A prior cutover attempt was partial: it changed some surfaces while leaving others, creating broken integrations. This spec describes a clean reimplementation.

## Problem Statement

Teams and integrations that consume spec-kitty's machine-facing outputs (event envelopes, orchestrator API, status JSON, body sync, tracker bind) receive a mix of legacy "feature" naming and new "mission" naming. External systems built against spec-kitty-events 3.0.0 reject events that carry the old contract shape. Build identity is absent from event envelopes, making it impossible for downstream consumers to distinguish events from parallel worktrees.

## Goals

1. Every live machine-facing output from spec-kitty uses mission-era terminology exclusively.
2. Event envelopes are accepted by spec-kitty-saas without modification.
3. Each worktree or clone has a stable, distinct build identity that appears on all emitted events.
4. Legacy local project state can be upgraded to the new shape without data loss.
5. No compatibility bridge exists on any live remote-facing surface.

## Out of Scope

- Changes to workflow steps: how missions are planned, tasked, or reviewed is unchanged.
- Changes to the doctrine/charter system.
- Any dashboard or UI changes not required by the contract cutover.
- Deprecation warnings or backward-compatible aliases on live API outputs.

## Key Entities

| Entity | Description |
|--------|-------------|
| **Mission** | A scoped unit of development work. Identified by `mission_slug`. |
| **Mission Number** | The sequential ordinal of a mission (e.g., `075`). |
| **Mission Type** | The workflow template kind (e.g., `software-dev`, `research`). |
| **Project** | A team-scoped repository identity carrying `project.uuid`, `project.slug`, and `repo_slug`. |
| **Build** | One concrete checkout or worktree. Carries a stable `build.id` unique per checkout. |
| **Node** | The causal emitter identity for Lamport clock ordering. Carries `node.id`. |
| **Event Envelope** | The wrapper around every emitted event. Must include `schema_version` and `build_id`. |
| **MissionCreated** | Canonical event emitted when a mission is opened. Replaces `FeatureCreated`. |
| **MissionClosed** | Canonical event emitted when a mission is completed. Replaces `FeatureCompleted`. |
| **Orchestrator API** | The machine-facing command/response interface consumed by external automation and CI/CD. |
| **Dossier / Body Sync** | The pipeline that syncs mission artifact bodies to remote storage. |
| **Compatibility Gate** | A shared primitive that validates all outbound remote-facing calls conform to the 3.0.0 contract before any side effect occurs. |

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The system exposes exactly one canonical command surface for creating a mission. | Proposed |
| FR-002 | Any legacy mission-creation surface that was previously available returns an error directing the user to the canonical command, with no partial side effects. | Proposed |
| FR-003 | The system emits `MissionCreated` and `MissionClosed` event types on all live paths. `FeatureCreated` and `FeatureCompleted` are never emitted on any live or public path. | Proposed |
| FR-004 | Every emitted event envelope includes `schema_version` and `build_id`. | Proposed |
| FR-005 | All emitted event payloads use `mission_slug`, `mission_number`, and `mission_type` as the canonical mission identity fields. `aggregate_type=Feature` does not appear in any emitted payload. | Proposed |
| FR-006 | No live or public JSON/API response includes a `feature_slug` field, whether as a primary field or as an injected alias. | Proposed |
| FR-007 | The project identity model persists `project.uuid`, `project.slug`, `build.id`, `node.id`, and `repo_slug` in the project configuration. | Proposed |
| FR-008 | Each distinct checkout or worktree is assigned a different `build.id`. The same checkout retains the same `build.id` on every subsequent invocation. | Proposed |
| FR-009 | The tracker bind payload includes `build.id`. | Proposed |
| FR-010 | The orchestrator API exposes command names, error codes, and response fields using mission-era terminology exclusively. Legacy command names (`accept-feature`, `merge-feature`), error codes (`FEATURE_NOT_FOUND`, `FEATURE_NOT_READY`), and `feature_slug` response fields are absent. | Proposed |
| FR-011 | The dossier and body sync pipeline sends `mission_slug` and `mission_type` as the canonical namespace identifiers on all remote-facing payloads. `mission_key` and `feature_slug` do not appear in any outbound sync request. | Proposed |
| FR-012 | A dedicated migration path upgrades legacy local project state — including `project.node_id` fields and feature-era `meta.json` shapes — to the canonical format, committing the result. | Proposed |
| FR-013 | The migration path is the only code that reads legacy field names from local state. All normal runtime and public paths fail closed when they encounter legacy contract shapes, without emitting events or writing state. | Proposed |
| FR-014 | A shared compatibility gate validates every outbound remote-facing call against the 3.0.0 contract before any side effect (event emission, state write, sync request) occurs. | Proposed |
| FR-015 | The gate policy derives from the spec-kitty-events 3.0.0 cutover artifact as published upstream, not from locally maintained constant copies. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage on all new and modified modules | ≥90% line coverage (project standard) | Proposed |
| NFR-002 | Type safety | All new and modified code passes `mypy --strict` with zero errors | Proposed |
| NFR-003 | Event rejection rate after cutover | Zero events rejected by spec-kitty-saas due to contract mismatch over a 24-hour smoke-test window | Proposed |
| NFR-004 | Migration reliability | Legacy state migration succeeds for ≥99% of well-formed pre-cutover project fixtures in the test suite | Proposed |
| NFR-005 | Orchestrator API response latency | Median response time shows no regression vs. pre-cutover baseline | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The implementation must conform to spec-kitty-events 3.0.0 as merged at origin/main commit `5b8e6dc`. | Active |
| C-002 | The implementation must conform to spec-kitty-saas as merged at origin/main commit `3a0e4af`. | Active |
| C-003 | No compatibility bridge on any live remote-facing surface. Any shim must be upgrade-only and unreachable from normal runtime or public API flows. | Active |
| C-004 | `FeatureCreated` and `FeatureCompleted` event types must not appear on any live emission path. | Active |
| C-005 | `aggregate_type=Feature` must not appear in any emitted contract. | Active |
| C-006 | Legacy local state may only be ingested by explicit upgrade/migration code paths. Normal runtime paths must not read legacy field names from config or meta files. | Active |
| C-007 | Modules that are mission-domain feature-named (e.g., feature_creation, feature_metadata, agent/feature surfaces) must not remain active in the live runtime or public command surface. | Active |

## User Scenarios & Testing

### Scenario 1 — Creating a mission via the canonical command

A developer runs the canonical mission creation command. The system creates the mission, persists the project and build identity, and emits a `MissionCreated` event that is accepted by spec-kitty-saas without error.

**Acceptance**: `MissionCreated` event received by SaaS with no rejection. Event envelope contains `schema_version` and `build_id`. Command response JSON contains `mission_slug`, `mission_number`, `mission_type`. No `feature_slug` field appears anywhere in the response.

### Scenario 2 — Two worktrees emit distinguishable build identities

A developer working in two worktrees for the same mission runs any event-emitting command in each. Events from worktree A and worktree B carry different `build.id` values. Re-running the same command in either worktree produces the same `build.id` as before.

**Acceptance**: `build.id` values differ between worktrees; the same worktree produces a stable, unchanged `build.id` across multiple invocations.

### Scenario 3 — External CI/CD consuming the orchestrator API

An external CI/CD script calls the orchestrator API to query mission state and drive workflow transitions. All command names, error codes, and response fields use mission-era naming.

**Acceptance**: Automated contract test against the orchestrator API schema returns zero occurrences of `feature_slug`, `FEATURE_NOT_FOUND`, `FEATURE_NOT_READY`, `accept-feature`, `merge-feature`, or any `aggregate_type=Feature` value.

### Scenario 4 — Legacy project state upgrade

A project that was initialized before the cutover runs the dedicated upgrade command. The migration reads legacy `project.node_id` and any feature-era meta fields, rewrites them to the canonical shape, and commits the result. Normal commands work without errors afterward.

**Acceptance**: Migration completes without error. Project configuration contains canonical `project`, `build`, and `node` sections. Subsequent `spec-kitty agent mission create` runs successfully.

### Scenario 5 — Dossier / body sync sends canonical namespace

A developer pushes a mission artifact body to remote storage. The sync pipeline sends `mission_slug` and `mission_type` in the namespace payload.

**Acceptance**: Captured outbound payload contains `mission_slug` and `mission_type`. No `mission_key` or `feature_slug` field is present.

### Scenario 6 — Legacy command surface rejected with no side effects

A developer or script invokes a surface that no longer exists in the live contract. The system returns a clear error naming the canonical replacement. No event is emitted and no state is written.

**Acceptance**: Exit code is non-zero. Error message references the canonical command. No event appears in the event log. No state file is modified.

## Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| spec-kitty-events 3.0.0 (origin/main @ `5b8e6dc`) | External — already merged upstream | Fixed contract baseline; spec-kitty must conform to this shape |
| spec-kitty-saas (origin/main @ `3a0e4af`) | External — already merged upstream | Validates incoming event envelopes; mismatch = rejected events |

## Assumptions

1. spec-kitty-events 3.0.0 and spec-kitty-saas are immutable external dependencies for this mission. Their contracts will not change during implementation.
2. The prior cutover attempt's changes are not on `main`; this spec describes a clean reimplementation from the current `main` state.
3. Projects without any local spec-kitty state (fresh installs) do not require migration. Migration applies only to projects with existing legacy-shaped configuration files.
4. The existing test suite includes fixture projects representative of pre-cutover local state shapes (project.node_id, feature-era meta.json).

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Secondary surfaces missed a second time (orchestrator API, status JSON, body sync replay paths) | Medium | High | Acceptance tests explicitly cover orchestrator API schema; all live machine-facing output paths are enumerated in the implementation plan. |
| Compatibility shim silently re-enters live paths via helper functions | Medium | High | Shared gate primitive is the single entry point; shim code is isolated in the migration module and not importable from runtime paths. |
| Migration corrupts existing project configuration | Low | High | Migration is idempotent and tested against fixture projects; runs on a copy before committing. |
| Upstream contract drifts from pinned commits | Low | Medium | Conformance is pinned to specific commits; version lock enforced in the compatibility gate. |

## Success Criteria

1. Zero spec-kitty-saas event rejections due to contract mismatch over a 24-hour post-cutover smoke-test window.
2. Automated orchestrator API contract tests pass with zero legacy-named fields, error codes, or payload shapes detected.
3. Two independent worktrees of the same mission produce distinct `build.id` values; each worktree produces an identical `build.id` on every invocation.
4. The upgrade migration successfully transforms 100% of well-formed legacy project fixture directories to the canonical shape without data loss.
5. The full test suite passes at ≥90% coverage with zero type errors.
6. An end-to-end smoke test captures zero occurrences of `feature_slug`, `FeatureCreated`, `FeatureCompleted`, or `aggregate_type=Feature` in any live output.
