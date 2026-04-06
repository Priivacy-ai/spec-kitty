# Research: Complete Mission Identity Cutover

**Feature**: 064-complete-mission-identity-cutover
**Date**: 2026-04-06

## Decision 1: Orchestrator API Migration Posture

**Decision**: Hard atomic cutover (Option A). All feature-era command names, error codes, and payload fields are removed simultaneously with no fallback, alias, redirect, or deprecation period.

**Rationale**: Consistent with C-007 (no fallback mechanisms). `spec-kitty-orchestrator` is the only known external consumer and can be updated in lockstep.

**Alternatives considered**:
- Versioned endpoint with loud failure on old names: Rejected because it adds complexity and a deprecation period the project doesn't need. With only one known consumer, lockstep is simpler.
- Silent alias forwarding: Rejected per C-007 and the failed first attempt's lesson #2 ("compatibility aliases are dangerous").

**Release coordination**: Priivacy-ai/spec-kitty-orchestrator#6 filed. Production rollout blocked until consumer is updated.

## Decision 2: Module Rename Strategy

**Decision**: Atomic rename via `git mv` with immediate import updates across the entire codebase. No re-export shims from old module paths.

**Rationale**: C-007 (no fallback) and C-006 (shims must be upgrade-only) make re-export wrappers unacceptable on live paths. The blast radius is manageable:
- `feature_creation.py`: 2 production imports, 3 test files
- `feature_metadata.py`: 10 production imports, 3 test files
- `agent/feature.py`: 1 production import (tasks.py), 35+ test imports

**Alternatives considered**:
- Create new modules + deprecation re-exports from old paths: Rejected per C-006/C-007. Would leave feature-era module names importable from runtime paths.
- Gradual rename over multiple PRs: Rejected because partial renames create confusing mixed state (the exact problem we're cleaning up).

**Module name mapping**:
| Old Module | New Module |
|------------|------------|
| `specify_cli/core/feature_creation.py` | `specify_cli/core/mission_creation.py` |
| `specify_cli/feature_metadata.py` | `specify_cli/mission_metadata.py` |
| `specify_cli/cli/commands/agent/feature.py` | `specify_cli/cli/commands/agent/mission.py` |
| `specify_cli/core/identity_aliases.py` | Removed entirely (not renamed) |

## Decision 3: Compatibility Gate Architecture

**Decision**: A single validation function invoked at chokepoint locations rather than a decorator or middleware pattern.

**Rationale**: The codebase has 6 natural chokepoints that funnel all remote-facing traffic:
1. `EventEmitter._emit()` (line 579) — upstream of all event routing (WebSocket + offline queue)
2. `batch_sync()` (line 363) — before HTTP POST to events/batch
3. `OfflineBodyUploadQueue.enqueue()` (line 125) — before SQLite INSERT
4. `push_content()` (line 42) — before HTTP POST to push-content
5. `SaaSTrackerClient._request()` (line 159) — before all tracker HTTP calls
6. `WebSocketClient.send_event()` (line 229) — before WebSocket transmission

A function call at each chokepoint is simpler and more auditable than decorators (which hide control flow) or middleware (which doesn't exist in this codebase's architecture).

**Gate behavior**: Validate that the payload/envelope conforms to the 3.0.0 contract shape. On non-conformance, raise a clear error and block the side effect. No silent correction.

**Policy derivation**: The gate must load its validation rules from a vendored machine-readable contract artifact (`contracts/upstream-3.0.0-shape.json`), which is derived from the upstream spec-kitty-events 3.0.0 and spec-kitty-saas contracts. The gate must NOT use hand-maintained field lists or local constants. At runtime, the gate loads this JSON artifact and enforces its `required_fields`, `forbidden_fields`, `allowed`/`forbidden` enumerations. If the artifact drifts from upstream, the fix is to update the artifact from the authoritative source, not to patch the gate code.

**Alternatives considered**:
- Decorator on each remote-facing function: Rejected because it hides control flow and is harder to audit. Some chokepoints (like `_emit()`) are methods, not standalone functions.
- Middleware/interceptor pattern: Rejected because the codebase doesn't have a middleware layer for sync/tracker operations.

## Decision 4: Body Queue Schema Migration

**Decision**: In-place SQLite ALTER TABLE migration that preserves pending uploads, with column rename and data rewrite.

**Rationale**: SQLite 3.25.0+ (2018) supports `ALTER TABLE RENAME COLUMN`, which is available on all supported platforms (Python 3.11+ bundles SQLite 3.39+). This is safer than drain-and-recreate because:
- No window of data loss during drain
- Atomic operation within a transaction
- Pending uploads survive without replay

**Migration steps**:
1. BEGIN TRANSACTION
2. ALTER TABLE body_upload_queue RENAME COLUMN feature_slug TO mission_slug
3. ALTER TABLE body_upload_queue RENAME COLUMN mission_key TO mission_type
4. COMMIT

**Acceptance criterion**: Test with populated queue containing legacy-schema rows demonstrates zero task loss after migration, with all namespace fields rewritten.

**Alternatives considered**:
- Drain queue before migration: Rejected because it requires network connectivity and introduces a failure window.
- Drop and recreate table: Rejected because it loses pending uploads (violates FR-020).
- New table + copy: Unnecessary complexity when ALTER TABLE RENAME COLUMN works.

## Decision 5: identity_aliases Removal Strategy

**Decision**: Remove `identity_aliases.py` entirely and update all 7 call sites to emit `mission_slug` directly instead of injecting `feature_slug` aliases.

**Rationale**: The module exists solely to inject `feature_slug` alongside `mission_slug` in live outputs. After cutover, this injection is the exact behavior we must eliminate. There is no legitimate post-cutover use case for this module.

**Call sites to update** (27 calls across 7 files):
- `orchestrator_api/commands.py` — 8 calls (response envelope wrapping)
- `cli/commands/agent/status.py` — 4 calls
- `status/views.py` — 1 call
- `status/models.py` — 1 call (StatusSnapshot.to_dict)
- `status/progress.py` — 1 call
- `next/decision.py` — 1 call
- `cli/commands/materialize.py` — 1 call

At each site, replace `with_tracked_mission_slug_aliases(data)` with the data dict directly (it already contains `mission_slug`).

## Decision 6: meta.json Canonical Fields

**Decision**: New `meta.json` writes must use `mission_slug`, `mission_number`, and `mission_type`. No exemption for spec scaffolding.

**Rationale**: FR-019 requires this explicitly. The current scaffolding code writes `feature_slug`, `feature_number`, and `mission` — all legacy field names. If scaffolding is exempted, every newly created mission starts with legacy metadata, perpetuating the partial cutover state.

**Field mapping**:
| Legacy Field | Canonical Field |
|-------------|----------------|
| `feature_slug` | `mission_slug` |
| `feature_number` | `mission_number` |
| `mission` | `mission_type` |
| `feature_slug` (composite) | `mission_slug` (composite, same value pattern: `###-slug`) |
| `slug` | `slug` (unchanged, short form) |
| `friendly_name` | `friendly_name` (unchanged) |

**Migration for existing meta.json**: Upgrade code reads legacy fields and rewrites to canonical. Both old and new field names are accepted during migration; only canonical names are written.

## Decision 7: Conformance Test Strategy

**Decision**: Shape-based assertion tests that validate envelope and payload structures against hardcoded expected shapes derived from the upstream contracts.

**Rationale**: C-002 (spec-kitty-events 2.9.0 installed, not 3.0.0) and C-003 (spec-kitty-saas not importable) prevent direct package import testing. Shape assertions are the most reliable approach given these constraints.

**Test structure**:
- One test module per contract surface: event envelope, tracker bind, body upload, orchestrator API response
- Each test constructs a payload using the live code path, then asserts the output shape matches the expected 3.0.0 contract
- Expected shapes derived once from upstream sources (spec-kitty-events @ 5b8e6dc, spec-kitty-saas @ 3a0e4af) and stored as test fixtures
- Tests fail if unexpected fields (e.g., `feature_slug`) appear or required fields (e.g., `build_id`) are missing

## Decision 8: Sequencing

**Decision**: Five-phase implementation sequence with clear dependency ordering.

**Phase A (Foundation)**: Compatibility gate + meta.json canonical writes (independent, can parallelize)
**Phase B (Core Renames)**: Module renames + import updates (sequential, high blast radius)
**Phase C (Contract Cleanup)**: identity_aliases removal, orchestrator API rename, body sync migration, tracker bind (partially parallelizable after Phase B)
**Phase D (Validation)**: Conformance tests + end-to-end audit
**Phase E (Release)**: spec-kitty-orchestrator coordination + release gate

Rationale: Gate must exist before contract cleanup (Phase C needs it). Module renames must precede contract cleanup (otherwise import paths are confusing during cleanup). Validation must follow all changes. Release is gated on external consumer readiness.
