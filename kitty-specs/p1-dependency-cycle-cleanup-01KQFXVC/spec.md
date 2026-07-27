# P1 Dependency Cycle Cleanup

## Purpose

**TLDR:** Remove two circular import cycles between the dossier/sync and status/sync packages to restore clean architectural boundaries.

**Context:** The spec-kitty codebase has two priority-1 circular import paths identified in GitHub issue #862. The dossier package and sync package import each other bidirectionally, and status/emit imports directly from the sync package, creating a transitive cycle. These cycles prevent clean package separation, complicate unit testing, and risk transitive dependency leaks. This mission removes both cycles through targeted structural refactoring with no behavioral changes to existing sync, dossier, status events, SaaS fan-out, body upload, or status persistence.

## Background

Two specific circular dependencies exist in the current codebase:

**P1.2 — Dossier ↔ Sync cycle:** `dossier/drift_detector.py` imports `ProjectIdentity` from `sync/project_identity.py`, while `sync/dossier_pipeline.py` imports multiple dossier modules (`drift_detector`, `events`, `indexer`, `manifest`, `snapshot`) to run the dossier sync pipeline. This creates a mutual dependency: dossier depends on sync for the identity type, and sync depends on dossier for its pipeline.

**P1.3 — Status → Sync dependency:** `status/emit.py` imports `trigger_feature_dossier_sync_if_enabled` from `sync/dossier_pipeline` and `emit_wp_status_changed` from `sync/events`, embedding the SaaS fan-out and dossier-sync calls inline inside canonical status persistence. This creates a `status → sync → core → status` transitive cycle.

## User Scenarios & Testing

**Scenario 1 — Developer triggers dossier drift detection:** A developer invokes a CLI command that runs drift detection on a mission. All detection results and reported drifts are identical to pre-change behavior. The dossier call stack contains no imports from `specify_cli.sync`.

**Scenario 2 — Developer emits a status event:** A developer (or an agent via CLI) transitions a work package to a new lane. The canonical status event is persisted to the event log immediately and unconditionally. SaaS fan-out and dossier-sync callbacks execute afterward as best-effort side effects; they cannot block or roll back the canonical persistence, even if the remote endpoint is unreachable.

**Scenario 3 — CI runs the architectural import boundary check:** The CI pipeline executes the static import boundary test. It reports zero `dossier → sync` edges and zero `status → sync` edges. The same test run on the pre-fix codebase would fail.

**Scenario 4 — Existing caller uses the legacy `ProjectIdentity` import path:** A caller that previously imported `ProjectIdentity` from the sync-owned module path either continues to work via a backward-compatible shim or has been explicitly updated to the canonical new path with no change in runtime behavior.

**Edge case — SaaS fan-out endpoint is unreachable:** The SaaS service is down. Status persistence completes and the event is durably written. The fan-out failure is logged but does not raise an exception or affect the caller's observable state.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | The `ProjectIdentity` type must be relocated from its current sync-package module to a dossier-owned or shared neutral module that has no import dependency on `specify_cli.sync` | Proposed |
| FR-002 | Dossier package modules must contain zero runtime or static imports from `specify_cli.sync` after this change | Proposed |
| FR-003 | A backward-compatible import shim must be provided at the original `ProjectIdentity` import path unless all known callers have been confirmed migrated and the architectural guard confirms no remaining usages | Proposed |
| FR-004 | All existing callers of `ProjectIdentity` in the sync, tracker, and dossier modules must be updated to import from the canonical new location | Proposed |
| FR-005 | `status/emit.py` must stop importing from `specify_cli.sync`; dossier-sync triggers and SaaS fan-out calls must be invoked through a decoupled event-adapter or callback-registration boundary | Proposed |
| FR-006 | SaaS fan-out and dossier-sync side effects triggered by status events must remain best-effort and must never block or roll back canonical status persistence | Proposed |
| FR-007 | An architectural guard test must be added or extended to statically assert that no `specify_cli.dossier` module imports `specify_cli.sync` and that no `specify_cli.status` module imports `specify_cli.sync` | Proposed |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Static import scan across all Python source files reports zero `specify_cli.dossier → specify_cli.sync` import edges | 0 violations | Proposed |
| NFR-002 | Static import scan across all Python source files reports zero `specify_cli.status → specify_cli.sync` import edges | 0 violations | Proposed |
| NFR-003 | All existing dossier, sync, status, and contract test suites pass without modification to test assertions | 100% pass rate | Proposed |
| NFR-004 | Strict type checking produces zero new errors introduced by this change | 0 new type errors | Proposed |

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | No behavioral changes to sync operations, dossier drift detection, tracker binding, SaaS fan-out, body/dossier contracts, or status persistence beyond what is strictly required to break the import cycles | Accepted |
| C-002 | Compatibility shims at existing public import paths must not be removed until tests and architectural rules confirm all supported callers have migrated | Accepted |
| C-003 | No rollout gating, feature flags, or changes to the `spec-kitty-tracker` package are in scope | Accepted |
| C-004 | Each cycle fix must be delivered as small, independently reviewable patches rather than a single large change | Accepted |

## Success Criteria

- A static import scan run against the full source tree after the change reports zero `dossier → sync` import edges
- A static import scan run against the full source tree after the change reports zero `status → sync` import edges
- All existing test suites for dossier, sync, status, and contract packages pass at 100% with no assertion changes
- The architectural guard test is present in the test suite and would fail if either forbidden import edge were reintroduced
- A caller importing `ProjectIdentity` from either the old path (via shim) or the new canonical path receives the correct type with no runtime error

## Key Entities

| Entity | Description |
|--------|-------------|
| `ProjectIdentity` | The identity type currently owned by the sync package; to be relocated to a dossier-owned or neutral module |
| Dossier Pipeline | The sync-package orchestrator that drives dossier sync operations; must continue functioning correctly after `ProjectIdentity` is relocated |
| Status Event | The immutable record emitted by `status/emit.py`; canonical persistence must be unaffected by the fan-out decoupling |
| Fan-out Adapter | The new decoupled boundary (callback registration or event adapter) through which status events trigger optional SaaS and dossier-sync side effects |

## Assumptions

- The fan-out decoupling boundary for P1.3 can be implemented using existing language and framework primitives with no new external package dependencies
- Both P1.2 and P1.3 share no root module and can be developed in parallel without conflicting changes
- Compatibility shims at legacy import paths will be retained through at least the next minor release cycle

## Dependencies

- GitHub issue #862 documents the full dependency-cycle audit that identified these P1 items and serves as the authoritative record of the current cycles
- The existing architectural test infrastructure provides the testing surface for new import boundary guards
- The dossier, sync, status, and contract test suites must be green on the base branch before implementation begins
