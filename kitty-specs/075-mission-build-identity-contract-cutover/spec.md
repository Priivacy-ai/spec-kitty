# Mission & Build Identity Contract Cutover

**Mission**: 075-mission-build-identity-contract-cutover
**Mission Type**: software-dev
**Status**: Draft
**Created**: 2026-04-07
**Revised**: 2026-04-08 (post-review)

## Overview

Spec Kitty tracks development work through "missions." A prior cutover landed on `main` and cleaned the primary surfaces: event types are now `MissionCreated` / `MissionClosed`, event envelopes carry `schema_version="3.0.0"` and `build_id`, the orchestrator API uses mission-era command names, body sync sends `mission_slug` / `mission_type`, and a shared contract gate (`contract_gate.py`) enforces the upstream contract on all outbound calls.

What the prior cutover did not finish:

1. **Inbound read-path fallbacks** — five non-migration runtime files still accept `feature_slug` as a fallback when reading status events and work-package metadata. These are live bridges that should only exist in migration code.
2. **Per-worktree build identity** — `build_id` is stored in `.kittify/config.yaml`, which is committed to git and therefore shared across all worktrees of the same repository. Two worktrees currently emit the same `build_id`, making them indistinguishable to downstream consumers.
3. **Tracker bind** — the tracker bind payload does not yet include `build_id`.

This mission finishes the cutover by closing these three gaps and ensuring no regression on already-clean surfaces.

## Problem Statement

Five runtime files outside the migration path still treat `feature_slug` as a valid inbound field name, acting as compatibility bridges on live read paths. This means downstream code that writes old event shapes can still round-trip through the system without error. The cutover is not complete until these fallbacks are removed and the runtime fails closed on legacy input shapes.

Separately, `build_id` is shared across all git worktrees because it is stored in a committed configuration file. Downstream consumers (SaaS event replay, observability tooling) cannot distinguish which worktree emitted an event, defeating the purpose of the build identity model.

## What Was Already Done (Must Not Regress)

The following surfaces were cleaned by the prior cutover and must remain clean:

| Surface | State |
|---------|-------|
| Event types: `MissionCreated` / `MissionClosed` | Done — `FeatureCreated` / `FeatureCompleted` do not exist |
| Event envelopes: `schema_version="3.0.0"` + `build_id` field | Done |
| Orchestrator API: `accept-mission`, `merge-mission`; `accept-feature`, `merge-feature` forbidden | Done |
| Body sync namespace: `mission_slug` / `mission_type` required; `feature_slug` / `mission_key` forbidden | Done |
| Shared contract gate (`contract_gate.py`) loads `upstream_contract.json` | Done |
| Modules `feature_creation`, `feature_metadata`, `agent/feature`: removed from runtime | Done — not present on `main` |

## Goals

1. Remove all `feature_slug` read fallbacks from non-migration runtime paths.
2. Make `build.id` per-worktree: distinct across worktrees, stable within a single worktree across invocations.
3. Include `build_id` in the tracker bind payload.
4. No regression on any already-clean surface listed above.

## Out of Scope

- Changes to workflow steps: how missions are planned, tasked, or reviewed is unchanged.
- Changes to the doctrine/charter system.
- Dashboard or UI changes not required by this cutover.
- Deprecation warnings or backward-compatible aliases on live API outputs.
- Cleaning `feature_slug` from migration-path code (`upgrade/feature_meta.py`, `migration/rebuild_state.py`) — those are the correct location for legacy field reads.

## Key Entities

| Entity | Description |
|--------|-------------|
| **Mission** | A scoped unit of development work. Identified by `mission_slug`. |
| **Mission Number** | The sequential ordinal of a mission (e.g., `075`). |
| **Mission Type** | The workflow template kind (e.g., `software-dev`, `research`). |
| **Project** | A team-scoped repository identity. Persists `project.uuid`, `project.slug`, `repo_slug`. Stored in committed config. |
| **Build** | One concrete checkout or worktree. Carries a stable `build.id` unique per checkout. Stored in a non-committed, per-worktree location. |
| **Node** | The causal emitter identity for Lamport clock ordering. Carries `node.id`. |
| **Event Envelope** | The wrapper around every emitted event. Includes `schema_version` and `build_id`. |
| **Contract Gate** | Shared primitive (`contract_gate.py`) that validates all outbound remote-facing calls against `upstream_contract.json` before any side effect occurs. |
| **Upstream Contract** | The vendored `upstream_contract.json` file, derived from the pinned spec-kitty-events 3.0.0 commit and distributed with the package. |

## Functional Requirements

Requirements that are already implemented are marked **Already Implemented** to prevent regression; they are acceptance criteria, not new work. Requirements marked **Proposed** are the remaining implementation work.

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The system exposes exactly one canonical command surface for creating a mission (`spec-kitty agent mission create`). | Already Implemented |
| FR-002 | Any invocation of a removed legacy mission-creation surface returns an error directing the user to the canonical command, with no partial side effects (no event emitted, no state written). | Already Implemented |
| FR-003 | The system emits `MissionCreated` and `MissionClosed` event types on all live paths. `FeatureCreated` and `FeatureCompleted` are absent from the codebase and never emitted. | Already Implemented |
| FR-004 | Every emitted event envelope includes `schema_version` and `build_id`. | Already Implemented |
| FR-005 | All emitted event payloads use `mission_slug`, `mission_number`, and `mission_type`. `aggregate_type=Feature` does not appear in any emitted payload. | Already Implemented |
| FR-006 | No live outbound JSON/API payload includes a `feature_slug` field. The contract gate enforces this on all outbound calls. | Already Implemented |
| FR-007 | Project identity (`project.uuid`, `project.slug`, `node.id`, `repo_slug`) is persisted in the committed project configuration. `build.id` is persisted separately in a non-committed, per-worktree location. See **Design Note: build.id Storage** below. | Proposed |
| FR-008 | Each distinct checkout or worktree is assigned a different `build.id`. The same checkout retains the same `build.id` on every subsequent invocation. | Proposed |
| FR-009 | The tracker bind payload includes `build_id`. | Proposed |
| FR-010 | The orchestrator API exposes command names, error codes, and response fields using mission-era terminology. `accept-feature`, `merge-feature`, `FEATURE_NOT_FOUND`, `FEATURE_NOT_READY`, and `feature_slug` response fields are absent. | Already Implemented |
| FR-011 | The dossier and body sync pipeline sends `mission_slug` and `mission_type` as namespace identifiers. `mission_key` and `feature_slug` are absent from all outbound sync payloads. | Already Implemented |
| FR-012 | A dedicated migration path upgrades legacy local project state (e.g., `project.node_id`, feature-era `meta.json` shapes) to the canonical format, committing the result. Migration code is the only permitted location for reading legacy field names from stored state. | Already Implemented (migration exists; verify completeness) |
| FR-013 | The following non-migration runtime files are cleaned of `feature_slug` read fallbacks: `core/identity_aliases.py`, `core/worktree.py`, `status/models.py`, `status/validate.py`, `status/wp_metadata.py`. After removal, these paths fail closed when they encounter a legacy-shaped input — they do not silently fall back. | Proposed |
| FR-014 | The shared contract gate (`contract_gate.py`) validates every outbound remote-facing call against the upstream contract before any side effect (event emission, state write, sync request) occurs. | Already Implemented |
| FR-015 | The gate policy is driven by `upstream_contract.json`, which is vendored in the package from the pinned spec-kitty-events 3.0.0 commit (`5b8e6dc`). The file is loaded via the package resource system (not from a user-editable path) and includes an embedded `schema_version` or provenance field that matches the pinned commit. No separate locally-maintained copy that contradicts the vendored file is permitted. | Proposed (provenance field not yet present) |
| FR-016 | On the first invocation after upgrade, if `build_id` is found in `.kittify/config.yaml`, the system copies it to the chosen per-worktree storage location, removes it from `config.yaml`, and writes the updated config. Subsequent invocations read `build.id` exclusively from the per-worktree location. This migration is idempotent: running it on a config that has no `build_id` field is a no-op. | Proposed |

### Design Note: build.id Storage

`build.id` must be stored in a location that is **not committed to git** and is **not shared across worktrees**. The current location (`.kittify/config.yaml`, which is committed) does not satisfy this.

Acceptable storage locations share one property: each working-tree directory has its own copy, independent of other worktrees.

- **Preferred option**: a gitignored file at `.kittify/build_id.local` within each working-tree directory. Since each git worktree has its own working directory, this file is naturally per-worktree. The project `.gitignore` must exclude this file.
- **Alternative**: a file within the `.git/` directory (e.g., `.git/spec-kitty-build-id`). This is also per-worktree (each worktree has its own `.git` reference), does not require a `.gitignore` entry, and survives the working tree being cleaned. Downside: `.git/` paths are less stable across git versions.

The implementation plan should select one of these options and document the choice. This selection is the primary design decision gating FR-007 and FR-008.

Once the per-worktree storage location is chosen, `project.build_id` is removed from `.kittify/config.yaml`, and the `ProjectIdentity` loader reads `build.id` from the non-committed location, generating and persisting a fresh one if none exists.

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage on all new and modified modules | ≥90% line coverage (project standard) | Proposed |
| NFR-002 | Type safety | All new and modified code passes `mypy --strict` with zero errors | Proposed |
| NFR-003 | Event rejection rate after cutover | Zero events rejected by spec-kitty-saas due to contract mismatch over a 24-hour smoke-test window, measured via SaaS admin rejection log | Proposed |
| NFR-004 | Per-worktree build.id stability | The same worktree produces an identical `build.id` on 100 consecutive invocations with no intermediate state reset | Proposed |
| NFR-005 | Orchestrator API response latency | Median response time shows no regression vs. pre-cutover baseline | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The implementation must conform to spec-kitty-events 3.0.0 as merged at origin/main commit `5b8e6dc`. | Active |
| C-002 | The implementation must conform to spec-kitty-saas as merged at origin/main commit `3a0e4af`. | Active |
| C-003 | No compatibility bridge on any live remote-facing surface. Any shim must be upgrade-only and unreachable from normal runtime or public API flows. `feature_slug` read fallbacks in `core/identity_aliases.py`, `core/worktree.py`, `status/models.py`, `status/validate.py`, and `status/wp_metadata.py` are the remaining bridges and are the primary cleanup target. | Active |
| C-004 | `FeatureCreated` and `FeatureCompleted` event types must not appear on any live emission path. | Active (already satisfied) |
| C-005 | `aggregate_type=Feature` must not appear in any emitted contract. | Active (already satisfied) |
| C-006 | Legacy field names from local state may only be read by explicit upgrade/migration code paths. | Active |
| C-007 | `build.id` must not be stored in a committed file. Storing it in `.kittify/config.yaml` (committed) is prohibited. | Active — currently violated; FR-007/FR-008 fix this |

## User Scenarios & Testing

### Scenario 1 — Legacy input shape rejected on inbound read path

A status event stored in `status.events.jsonl` uses `feature_slug` instead of `mission_slug` (written by a pre-cutover client). When the runtime reads this event, it raises an error or returns a structured failure. It does not silently normalize `feature_slug` to `mission_slug`.

**Acceptance**: Reading a fixture event that contains only `feature_slug` (no `mission_slug`) raises a `KeyError` or domain error from `StatusEvent.from_dict`. No fallback normalization occurs outside the migration path.

### Scenario 2 — Two worktrees emit distinguishable build identities

A developer has two worktrees for the same repository. Any event-emitting command run in worktree A and worktree B produces events with different `build_id` values. Re-running the same command in either worktree produces the same `build_id` as before.

**Acceptance**: `build_id` in events from worktree A ≠ `build_id` in events from worktree B. Running the same command 10 times in worktree A produces the same `build_id` each time. The per-worktree `build_id` file (at the chosen non-committed storage path) persists the value between invocations.

### Scenario 3 — Tracker bind includes build_id

A developer runs any command that triggers a tracker bind. The bind payload sent to the remote tracker includes `build_id`.

**Acceptance**: Captured outbound tracker bind payload contains `build_id` field with a non-empty value. The value matches the `build_id` from events emitted in the same invocation.

### Scenario 4 — Contract gate upstream_contract.json provenance

The `upstream_contract.json` file packaged with spec-kitty contains a top-level `schema_version` (or equivalent provenance) field matching the value from the pinned spec-kitty-events commit `5b8e6dc`. Loading the contract via `importlib.resources` produces a dict with this field present.

**Acceptance**: `_load_contract()["schema_version"]` equals the expected value from the pinned commit. The file is not loadable from a user-editable path.

### Scenario 5 — WPMetadata no longer carries feature_slug field

A work-package metadata object is constructed and serialized. The resulting dict does not contain `feature_slug`.

**Acceptance**: `WPMetadata(...).model_dump()` contains no `feature_slug` key.

### Scenario 6 — No regression on already-clean surfaces

An end-to-end smoke test runs `spec-kitty agent mission create`, `spec-kitty agent mission state`, and a body sync push.

**Acceptance**: Zero occurrences of `feature_slug`, `FeatureCreated`, `FeatureCompleted`, or `aggregate_type=Feature` in: (a) any emitted event in `status.events.jsonl`, (b) the tracker bind payload, (c) the body sync outbound payload, (d) the orchestrator API response JSON.

## Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| spec-kitty-events 3.0.0 (origin/main @ `5b8e6dc`) | External — already merged upstream | Defines `upstream_contract.json` content; spec-kitty must conform |
| spec-kitty-saas (origin/main @ `3a0e4af`) | External — already merged upstream | Validates incoming event envelopes; rejection is observable via admin rejection log |

## Assumptions

1. spec-kitty-events 3.0.0 and spec-kitty-saas are immutable external dependencies for this mission. Their contracts will not change during implementation.
2. The prior cutover's changes are substantially on `main`. The primary surfaces (event types, envelopes, orchestrator API, body sync, contract gate) are already clean. The remaining work is the five read-path fallback files and per-worktree build identity.
3. `feature_slug` occurrences in `upgrade/feature_meta.py` and `migration/rebuild_state.py` are in the correct location (migration-only) and are not targets for removal in this mission.
4. No fixture `status.events.jsonl` files with legacy-shaped events currently exist in the test suite. Writing at least one fixture event containing only `feature_slug` (no `mission_slug`) is required work — it is a prerequisite for Scenario 1's acceptance test and must be a dedicated task in the implementation plan.
5. NFR-003 rejection signal is observable via the SaaS admin rejection log — no additional instrumentation is needed to verify this criterion.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Removing `feature_slug` fallbacks breaks existing pre-cutover event log readers | Medium | Medium | Fixture-driven tests; the migration path remains available for explicit upgrade of legacy event files |
| Per-worktree `build.id` storage choice creates cross-platform edge cases (Windows, CI, Docker) | Medium | Medium | Implementation plan must include cross-platform test cases; `.kittify/build_id.local` (gitignored) is simpler than `.git/`-based storage for cross-platform compatibility |
| Changing `build_id` out of `config.yaml` breaks existing projects that have `build_id` there | Low | Low | Migration: on first load after upgrade, if `build_id` found in config.yaml, copy to per-worktree location then remove from config |
| Regression on already-clean surfaces from an incidental change | Low | High | Scenario 6 regression test runs as part of CI on every PR |

## Success Criteria

1. Reading a fixture status event that contains only `feature_slug` raises a domain error — no silent normalization — in all five cleaned runtime files.
2. Two git worktrees of the same repository emit different `build_id` values; each worktree emits the same `build_id` on every invocation.
3. The tracker bind payload captured during an end-to-end test contains `build_id`.
4. `upstream_contract.json` contains a `schema_version` or equivalent provenance field matching the pinned spec-kitty-events 3.0.0 commit.
5. The full test suite passes at ≥90% coverage with zero type errors.
6. An end-to-end smoke test captures zero occurrences of `feature_slug`, `FeatureCreated`, `FeatureCompleted`, or `aggregate_type=Feature` in any live output (event log, tracker bind, body sync, orchestrator API response).
