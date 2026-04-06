# Complete Mission Identity Cutover

**Feature**: 064-complete-mission-identity-cutover
**Mission**: software-dev
**Created**: 2026-04-06
**Status**: Draft

## Problem Statement

The spec-kitty codebase is in a partially completed mission/build identity cutover state. Some canonical changes have already landed on `main` (MissionCreated/MissionClosed event emission, build_id on ProjectIdentity, mission_slug in namespace/body sync paths). However, the cutover is inconsistent: active runtime modules are still feature-named, live machine-facing outputs still inject `feature_slug` aliases, the orchestrator API exposes feature-era command names and error codes, tracker bind omits `build_id`, and the body sync queue schema still carries `feature_slug`/`mission_key` fields on live remote-facing paths.

A previous attempt at this cutover failed because it treated the problem as a surface rename rather than an end-to-end contract alignment. The lessons from that failure are explicit constraints on this specification.

The authoritative upstream contract is defined by:
- **spec-kitty-events** `origin/main @ 5b8e6dc` -- canonical event model and mission catalog conformance
- **spec-kitty-saas** `origin/main @ 3a0e4af` -- ingress contract that validates incoming event envelopes

spec-kitty must conform to these external contracts. This feature completes that conformance.

## Background and Context

### Current State (verified on `main` @ `bcd93826`)

This is a partial cutover already in progress. Some subsystems are fully canonical, others are partially converted (canonical usage exists alongside legacy fields), and others remain purely feature-era. The work is to complete and clean up what is already underway, not to implement the entire cutover from scratch.

**Fully canonical:**
- `spec-kitty agent mission create` exists as the canonical create command
- Sync events emit `MissionCreated` / `MissionClosed`
- `ProjectIdentity` carries `build_id` and writes canonical `project`/`build`/`node` config sections

**Partially converted (canonical usage present, legacy fields remain):**
- Namespace and body transport modules reference `mission_slug`/`mission_type` in some code paths, but `NamespaceRef` and `BodyUploadTask` dataclass fields still use `feature_slug` and `mission_key`
- Body transport sends `mission_slug` as a compatibility alias for `mission_key` alongside `feature_slug` on the live wire
- Tracker bind sends `project.uuid`, `project.slug`, `node_id`, `repo_slug` but does not yet include `build_id`
- `StatusEvent.from_dict()` reads `mission_slug` OR `feature_slug` (dual-read pattern)

**Still fully feature-era (must be changed):**
- Active runtime modules named `feature_creation.py`, `feature_metadata.py`, `agent/feature.py`
- `identity_aliases.py` injects `feature_slug` into 8 live runtime paths (status views, materialize, orchestrator API, next/decision, progress)
- Orchestrator API exposes 3 feature-era command names (`feature-state`, `accept-feature`, `merge-feature`) and 2 feature-era error codes (`FEATURE_NOT_FOUND`, `FEATURE_NOT_READY`)
- All 8 orchestrator API commands emit `feature_slug` in response payloads via `with_tracked_mission_slug_aliases()`
- Newly scaffolded `meta.json` files use legacy field names (`feature_slug`, `feature_number`, `mission`)
- No central compatibility gate exists for remote-facing paths

### Canonical Contract (from upstream)

| Concept | Canonical Term | Forbidden on Live Surfaces |
|---------|---------------|---------------------------|
| Mission instance identifier | `mission_slug` | `feature_slug` |
| Mission sequence number | `mission_number` | `feature_number` (in payloads) |
| Mission workflow/template kind | `mission_type` | `feature_type` |
| Mission catalog events | `MissionCreated`, `MissionClosed` | `FeatureCreated`, `FeatureCompleted` |
| Checkout/worktree identity | `build_id` (on envelopes) | omission or `node_id`-only |
| Causal emitter identity | `node_id` (Lamport ordering) | -- |
| Repository identity | `project.uuid`, `project.slug`, `repo_slug` | -- |

### Lessons from the Failed First Attempt

These are hard constraints, not guidelines:

1. **Removing one command is not enough.** All live/public machine-facing outputs must be audited, not just the obvious create path.
2. **Compatibility aliases are dangerous.** Runtime helpers that inject `feature_slug` into live JSON/API responses must not exist on active paths.
3. **Public machine interfaces matter as much as the CLI.** The orchestrator API, tracker bind, body sync, and status JSON are all contract surfaces.
4. **Module renaming is part of the cutover.** Active runtime modules centered on feature naming must be renamed, not just their internal field names.
5. **Build identity must be end-to-end.** `build_id` must flow through config, tracker bind, event envelopes, and every path that serializes, validates, queues, replays, reduces, or rehydrates sync events.
6. **Dossier/body sync is part of the cutover.** NamespaceRef, body queue, body transport, and dossier pipeline must use canonical terms on live paths.
7. **Upstream contract pinning matters.** The local contract must match what SaaS actually validates, not a hand-maintained local approximation.

## Actors

| Actor | Description |
|-------|-------------|
| AI Agent Operator | An AI agent using spec-kitty CLI commands and orchestrator API to drive mission workflows |
| External SaaS | The spec-kitty-saas service that receives and validates event envelopes, tracker binds, and body sync payloads |
| Migration User | A project operator upgrading from a pre-cutover or partially-cutover local state |
| CI/Automation | Automated systems that consume orchestrator API machine-facing JSON outputs |

## User Scenarios and Testing

### Scenario 1: Agent Creates and Drives a Mission

An AI agent operator creates a new mission using `spec-kitty agent mission create`, implements work packages, transitions status, and syncs events to SaaS. At every step, the emitted JSON payloads, event envelopes, tracker bind calls, and body sync uploads use canonical mission-era terms exclusively. No `feature_slug` alias appears in any machine-facing output.

### Scenario 2: Orchestrator API Consumer Reads State

A CI system calls the orchestrator API to query mission state, start implementation, transition work packages, and accept/merge a mission. All command names, response payloads, and error codes use mission-era naming. Feature-era command names and error codes are not recognized.

### Scenario 3: Legacy Project Upgrade

A project that was initialized before the cutover runs `spec-kitty upgrade`. The upgrade process reads legacy `feature_slug` / `feature_number` local state from `meta.json` and `.kittify/config.yaml`, rewrites it to canonical terms, and bootstraps any missing identity fields (e.g., `build_id`). After upgrade, all runtime paths use canonical terms.

### Scenario 4: Build Identity Across Worktrees

An operator has the same repository checked out in two worktrees. Each worktree has a distinct `build_id` persisted in its local `.kittify/config.yaml`. Events emitted from each worktree carry the correct `build_id` on envelopes. When events from both worktrees arrive at SaaS, they are distinguishable by `build_id`.

### Scenario 5: Body Sync Upload

When spec-kitty uploads artifact bodies to SaaS, the upload payload uses `mission_slug` and `mission_type` as namespace identifiers. The body queue schema stores these canonical fields. No `feature_slug` or `mission_key` field appears in the queue or transport payload on live paths.

### Scenario 6: New Mission Metadata Uses Canonical Fields

An AI agent creates a new mission via `spec-kitty agent mission create`. The scaffolded `meta.json` uses `mission_slug`, `mission_number`, and `mission_type` as field names. No `feature_slug`, `feature_number`, or `mission` field appears in the newly written file. Downstream commands that read metadata consume the canonical field names without fallback.

### Scenario 7: Pending Body Uploads Survive Queue Migration

A project has pending body upload tasks queued in the SQLite queue with the old schema (`feature_slug`, `mission_key` columns). The operator runs `spec-kitty upgrade`. The migration rewrites the queue schema to canonical terms (`mission_slug`, `mission_type`) and preserves all pending tasks with their namespace fields translated. After migration, the upload worker processes the pending tasks successfully using canonical fields.

### Scenario 8: Compatibility Gate Rejects Legacy Payloads

A remote-facing path (sync, tracker, body upload) attempts to send a payload. The central compatibility gate validates that the payload conforms to the upstream 3.0.0 contract shape before allowing the side effect. If a legacy-shaped payload is constructed (e.g., by stale code), the gate rejects it with a clear error rather than sending a non-conformant request.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `spec-kitty agent mission create` must be the only canonical mission creation command surface. No `create-feature` command may exist on any active CLI path. | Draft |
| FR-002 | All live event emission must use `MissionCreated` and `MissionClosed` event types. No `FeatureCreated` or `FeatureCompleted` emitter or event rule may exist on active paths. | Draft |
| FR-003 | No live public JSON or API output may include a `feature_slug` alias field. The `identity_aliases` runtime injection must be removed from all active paths. | Draft |
| FR-004 | Orchestrator API: all feature-era command names are removed atomically. All feature-era error codes are removed atomically. No fallback, alias, redirect, or "deprecated but still works" behavior is allowed. Calls using old command names must fail as unknown/unsupported commands, not execute. See command and error code mapping tables below. | Draft |
| FR-005 | `ProjectIdentity` must carry `project.uuid`, `project.slug`, `build.id`, `node.id`, and `repo_slug`. `.kittify/config.yaml` must persist canonical `project`, `build`, and `node` sections. | Draft |
| FR-006 | Each distinct checkout or worktree must have a unique `build_id`. The same checkout must retain its `build_id` across sessions. `build_id` must be generated on first use and persisted to config. | Draft |
| FR-007 | Event envelopes must include `schema_version` and `build_id`. Payloads must use `mission_slug`, `mission_number`, and `mission_type`. | Draft |
| FR-008 | `build_id` must be preserved through every path that serializes, validates, queues, replays, reduces, or rehydrates sync events. It must not be silently dropped during storage or reconstruction. | Draft |
| FR-009 | Tracker bind must send `build_id` along with `project.uuid`, `project.slug`, and `node_id`. | Draft |
| FR-010 | Body sync queue schema must use `mission_slug` and `mission_type` as namespace fields. No `feature_slug` or `mission_key` field may appear in the queue schema or transport payload on live paths. | Draft |
| FR-011 | `NamespaceRef`, body transport payloads, and dossier pipeline logging must use `mission_slug` and `mission_type` end-to-end. | Draft |
| FR-012 | A single shared compatibility gate primitive must exist. All remote-facing paths (sync, tracker, dossier, merge, status, heartbeat) must invoke this gate before performing side effects. | Draft |
| FR-013 | The compatibility gate policy must derive from the shape of the upstream spec-kitty-events 3.0.0 cutover artifact, not from hand-maintained local constants. | Draft |
| FR-014 | Dedicated upgrade/migration code may read legacy local state (`feature_slug`, `feature_number`, `node_id` in legacy positions) and rewrite it to canonical terms. | Draft |
| FR-015 | Normal runtime and public paths must fail closed when encountering legacy mission-domain contract surfaces. They must not silently accept or translate legacy-shaped data. | Draft |
| FR-016 | No active runtime module, command surface, machine-facing payload, or error code may remain feature-era after the cutover. Specifically: `feature_creation.py`, `feature_metadata.py`, and `agent/feature.py` must be renamed to mission-era equivalents, and all internal imports must be updated. If anything feature-shaped survives, it must be migration-only and provably unreachable from normal runtime paths. | Draft |
| FR-017 | Any compatibility shim that remains in the codebase must be provably reachable only from explicit upgrade/migration code paths, not from normal runtime or public flows. | Draft |
| FR-018 | The vendored/local event model must match the 3.0.0 contract shape enforced by SaaS (envelope fields, payload field names, aggregate type). `aggregate_type=Feature` must not appear anywhere in emitted events. | Draft |
| FR-019 | Newly scaffolded mission metadata (`kitty-specs/*/meta.json`) must use canonical field names: `mission_slug`, `mission_number`, and `mission_type`. The legacy field names `feature_slug`, `feature_number`, and `mission` must not appear in newly written metadata. This applies to the `create-feature` / `agent mission create` scaffolding path and any other code that writes `meta.json`. Existing legacy metadata is handled by migration (FR-014); new writes have no exemption. | Draft |
| FR-020 | Pending body upload tasks already queued in the body upload queue must survive schema migration without data loss. Migration must either drain and replay pending uploads before schema changes, or perform an in-place schema migration that preserves all queued tasks and rewrites their namespace fields to canonical terms. Acceptance criterion: a test with a populated queue containing legacy-schema rows must demonstrate zero task loss after migration, with all namespace fields rewritten to canonical terms. | Draft |
| FR-021 | `spec-kitty-orchestrator` (`Priivacy-ai/spec-kitty-orchestrator`) is a known external consumer and must be updated as a release dependency. Production rollout of the orchestrator API rename is blocked until consumer updates are ready and validated against the renamed contract. | Draft |

### FR-004 Detail: Orchestrator API Command Name Mapping

| Old Command (Feature-Era) | New Command (Mission-Era) | Notes |
|---------------------------|--------------------------|-------|
| `feature-state` | `mission-state` | Query mission status and WP lanes |
| `accept-feature` | `accept-mission` | Mark all WPs done, accept mission |
| `merge-feature` | `merge-mission` | Execute merge of mission worktrees to target branch |

Commands already using neutral names (no rename needed): `contract-version`, `list-ready`, `start-implementation`, `start-review`, `transition`, `append-history`.

### FR-004 Detail: Orchestrator API Error Code Mapping

| Old Error Code (Feature-Era) | New Error Code (Mission-Era) | Notes |
|------------------------------|------------------------------|-------|
| `FEATURE_NOT_FOUND` | `MISSION_NOT_FOUND` | Mission slug does not resolve to a kitty-specs directory |
| `FEATURE_NOT_READY` | `MISSION_NOT_READY` | Not all WPs done (for accept-mission) |

Error codes already using neutral names (no rename needed): `USAGE_ERROR`, `POLICY_METADATA_REQUIRED`, `POLICY_VALIDATION_FAILED`, `WP_NOT_FOUND`, `TRANSITION_REJECTED`, `WP_ALREADY_CLAIMED`, `PREFLIGHT_FAILED`, `CONTRACT_VERSION_MISMATCH`, `UNSUPPORTED_STRATEGY`.

### FR-004 Detail: Payload Field Mapping

All orchestrator API response payloads currently include `feature_slug` via `with_tracked_mission_slug_aliases()`. After cutover, all response payloads must use `mission_slug` exclusively. No `feature_slug` field may appear in any response envelope.

### FR-021 Detail: Release Gate

The cutover is not shippable until:
1. `spec-kitty-orchestrator` has been updated to use the new command names and error codes.
2. The updated `spec-kitty-orchestrator` has been validated against the renamed contract.
3. Both repos are released in lockstep or `spec-kitty-orchestrator` is released first.

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All new and modified code must have automated test coverage. | 90% line coverage for changed modules | Draft |
| NFR-002 | Shape-based conformance tests must validate envelope and payload structures against the upstream contracts defined by spec-kitty-events @ 5b8e6dc and spec-kitty-saas @ 3a0e4af. | 100% of envelope/payload fields validated | Draft |
| NFR-003 | The compatibility gate must add negligible overhead to remote-facing operations. | Less than 5ms per invocation | Draft |
| NFR-004 | Migration from legacy local state to canonical terms must complete without data loss. | 100% of identity fields preserved through migration | Draft |
| NFR-005 | `build_id` generation must produce universally unique identifiers that do not collide across independent checkouts. | Collision probability below 1 in 10^18 | Draft |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The upstream contracts in spec-kitty-events @ 5b8e6dc and spec-kitty-saas @ 3a0e4af are immutable. spec-kitty must conform to them; changes to upstream are out of scope. | Active |
| C-002 | The installed `spec-kitty-events` package in the dev environment is currently 2.9.0. Upgrading it to 3.0.0 is a separate task not in this feature's scope. Conformance tests must use shape assertions, not direct package imports of 3.0.0 models. | Active |
| C-003 | spec-kitty-saas is a Django application, not an importable Python package. Contract validation must use shape/assertion tests against its source contract, not imports. | Active |
| C-004 | The codebase is partially cutover. The starting point is `main` @ `bcd93826`, not a clean pre-cutover baseline. Changes must be incremental on top of existing state. | Active |
| C-005 | Legacy local state in existing user projects must remain readable by migration code. Deleting or corrupting legacy state files is not acceptable. | Active |
| C-006 | Compatibility shims, if any remain, must be provably unreachable from live runtime and public API paths. The burden of proof is on the implementation. | Active |
| C-007 | No fallback mechanisms. Code must fail explicitly when encountering non-conformant state on live paths. | Active |

## Key Entities

| Entity | Description | Canonical Fields |
|--------|-------------|-----------------|
| ProjectIdentity | Team-scoped repository identity | `project.uuid`, `project.slug`, `build.id`, `node.id`, `repo_slug` |
| Event Envelope | Wrapper for all sync events sent to SaaS | `schema_version`, `build_id`, `mission_slug`, `mission_number`, `mission_type`, `aggregate_type` (must be `Mission`) |
| NamespaceRef | Namespace identifier for body sync and dossier operations | `mission_slug`, `mission_type` |
| StatusSnapshot | Materialized mission status | `mission_slug` (no `feature_slug` alias) |
| BodyUploadTask | Queued body sync upload | `mission_slug`, `mission_type` (no `feature_slug`, no `mission_key`) |
| TrackerBindPayload | Payload sent during tracker registration | `project_uuid`, `project_slug`, `build_id`, `node_id` |
| CompatibilityGate | Central validation primitive for remote-facing paths | Derives policy from upstream 3.0.0 contract shape |

## Success Criteria

1. An AI agent can create a mission, drive it through its full lifecycle, and sync all events to SaaS without any feature-era field appearing in any emitted payload, API response, or machine-facing output.
2. Two independent worktrees of the same repository emit events with distinct `build_id` values, and SaaS can distinguish them.
3. A project upgraded from legacy local state retains all identity information and functions correctly on all runtime paths afterward.
4. The compatibility gate catches and rejects any non-conformant payload before it reaches an external service, with a clear diagnostic error.
5. No grep for `feature_slug` across live runtime paths (excluding test fixtures and explicit migration/upgrade modules) returns results.
6. Shape conformance tests validate 100% of envelope and payload fields against the upstream contracts, and pass.
7. No live orchestrator API surface accepts feature-era commands or returns feature-era error codes. Calling `feature-state`, `accept-feature`, or `merge-feature` must fail as unknown/unsupported commands.
8. The cutover is not shippable until `spec-kitty-orchestrator` has been updated and validated against the renamed contract.

## Assumptions

- The upstream contracts at the specified commits are stable and will not change during implementation of this feature.
- Existing user projects with legacy local state are a supported migration path and must not break.
- The `body_upload_queue` SQLite table schema can be migrated (the current `feature_slug` column error observed during feature creation is a symptom of the partial cutover).
- `spec-kitty-orchestrator` (`Priivacy-ai/spec-kitty-orchestrator`) is the known external consumer of the orchestrator API and must be updated in lockstep with this cutover. No indefinite backward compatibility period for feature-era command names.
- `build_id` generation using UUIDs is acceptable for the uniqueness requirement.

## Dependencies

- **spec-kitty-events @ 5b8e6dc** (upstream, read-only): Defines the canonical event model and mission catalog conformance rules.
- **spec-kitty-saas @ 3a0e4af** (upstream, read-only): Defines the ingress validation contract that event envelopes and body sync payloads must satisfy.
- **Existing partial cutover on `main`**: This feature builds incrementally on work already landed; it does not revert and redo.
- **spec-kitty-orchestrator** (`Priivacy-ai/spec-kitty-orchestrator`): Known external consumer of orchestrator API. Must be updated and validated against renamed commands/error codes before production rollout. Release gate dependency.

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Module renames break imports across the codebase | Build failure, widespread test breakage | Systematic import update with automated verification; incremental rename with tests at each step |
| Orchestrator API command rename breaks `spec-kitty-orchestrator` | External orchestration stops working | Hard cutover with lockstep release. GitHub issues filed on `Priivacy-ai/spec-kitty-orchestrator` with mapping tables. Production rollout blocked until consumer is updated and validated (FR-021). |
| Body sync queue schema migration corrupts queued uploads | Data loss for pending uploads | Drain or migrate pending queue before schema change; test migration with populated queue |
| Compatibility gate is too strict and rejects valid payloads | Runtime failures on legitimate operations | Derive gate policy from actual upstream contract, not assumptions; comprehensive test coverage |
| Legacy project migration misses edge cases | User projects break after upgrade | Test migration against diverse legacy state shapes; preserve original state for rollback |

## Scope Boundary

**In scope:**
- All 21 functional requirements above (FR-001 through FR-021)
- Shape-based upstream conformance tests
- Migration code for legacy local state
- Central compatibility gate
- Module renames for active runtime surfaces

**Out of scope:**
- Upgrading the installed `spec-kitty-events` package from 2.9.0 to 3.0.0
- Changes to `spec-kitty-events` or `spec-kitty-saas` repositories
- Changes to the human-readable CLI output formatting (only machine-facing contract surfaces)
- Deprecation communication to external orchestrator API consumers (coordination, not implementation)
