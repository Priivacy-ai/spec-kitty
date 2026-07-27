# Implementation Plan: Local Mission Dossier Authority & Parity Export

**Feature Branch**: `042-local-mission-dossier-authority-parity-export`
**Date**: 2026-02-21 | **Spec**: `/kitty-specs/042-local-mission-dossier-authority-parity-export/spec.md`

## Summary

Implement a mission artifact dossier system that indexes all spec-kitty feature artifacts, computes deterministic content hashes and parity signatures, and emits canonical dossier events to sync infrastructure. Local runtime performs parity-drift detection offline; SaaS backend receives events for dashboard rendering and parity validation. Phase 1 (this feature) delivers:

- **Core Indexing**: ArtifactRef model, deterministic SHA256 hashing, MissionDossier data model
- **Expected Artifacts**: Registry of required/optional artifacts per mission type (software-dev, research, documentation)
- **Dossier Events**: 4 canonical event types (Indexed, Missing, Computed, ParityDrift) integrated with sync infrastructure
- **Dashboard API**: Endpoints for overview, list, filter, detail, export
- **Local UI**: Dashboard dossier panel with filtering and artifact detail views
- **Parity Detection**: Local drift detection comparing current snapshot vs cached baseline

Deterministic design ensures identical artifact content always produces identical parity hash, enabling reliable SaaS parity validation.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase requirement)
**Primary Dependencies**:
  - `hashlib` (SHA256, stdlib) – deterministic content hashing
  - `pydantic` (data validation, existing spec-kitty dependency) – type-safe models
  - `rich` (console output, existing) – console UI
  - `ruamel.yaml` (YAML parsing for mission manifests) – manifest loading + mission.yaml reading
  - `spec_kitty_events` (sync infrastructure, existing) – event emission + OfflineQueue
  - `http.server.HTTPServer` (stdlib, existing dashboard server) – HTTP request dispatch
  - `src/specify_cli/dashboard/handlers/` (existing handler pattern) – dossier API handlers
  - `src/specify_cli/sync/project_identity.py` (existing) – baseline key identity/scoping
  - Static JavaScript (existing) – dashboard UI updates (fetch + DOM manipulation, no Vue/SPA framework)

**Storage**: Filesystem only (YAML configs, JSON event logs, markdown artifacts)
**Testing**: `pytest` + `pytest-asyncio` (for async API tests)
**Target Platform**: Linux/macOS/Windows (CLI + local HTTP server)
**Project Type**: Single Python package (spec-kitty CLI) + dashboard Vue plugin
**Performance Goals**:
  - Artifact indexing: <1s for 30 artifacts
  - API responses: <500ms for full catalog (SC-001)
  - Parity hash computation: deterministic, reproducible (SC-006, SC-007)

**Constraints**:
  - No external service calls during local indexing (offline-capable)
  - Deterministic hashing (identical content → identical hash across machines/timezones)
  - UTF-8 robustness (consistent handling of encoding edge cases)
  - No silent failures (all anomalies explicit in events)

**Scale/Scope**:
  - Support >1000 artifacts per feature (SC-005)
  - 3 mission types with manifests in v1 (software-dev, research, documentation)
  - 6 artifact classes (input, workflow, output, evidence, policy, runtime) – deterministic, no fallback
  - 4 dossier event types (Indexed, Missing, Computed, ParityDrift) – anomaly events conditional

## Decision Analysis: Architectural Hardening

This section documents the key design decisions for O42 with explicit trade-offs and chosen paths.

### Decision 1: Dashboard Stack Path

**Context**: Current dashboard uses `http.server.HTTPServer` + handler routing + static JS. Question: Should O42 migrate to FastAPI/Vue?

**Options**:

**Option A: Migrate to FastAPI + Vue (In This Feature)**
- Pros: Modern stack, cleaner REST patterns, component reuse
- Cons: Scope explosion, breaks O42 single-feature boundary, risk of regression
- Risk: Estimated 15-20 WP-days additional work, migration testing burden
- Mitigation: Defer to post-O42 feature (e.g., "044-dashboard-modernization")

**Option B: Keep HTTPServer + Handlers, Add Adapter Layer for Future Migration**
- Pros: Minimal scope (O42 stays focused), clear migration path, backward-compatible
- Cons: Some handler code may need refactoring, not "modern" by today's standards
- Risk: Adapter layer may not fully decouple in practice; requires discipline
- Mitigation: Define adapter interface now (in WP06), test with mock FastAPI implementation in unit tests

**Option C: Keep HTTPServer + Handlers, No Adapter (Status Quo)**
- Pros: Simplest, zero refactoring, O42 is purely additive
- Cons: Migration burden pushed entirely to future team; accumulated technical debt
- Risk: Future migration becomes larger, more complex
- Mitigation: Document migration roadmap explicitly (see "Deferred Decisions")

**→ CHOSEN: Option B (Keep Current, Define Adapter Path)**
- Rationale: Balance scope containment with forward-looking design. O42 adds dossier handlers following current patterns; adapter interface in WP06 makes future migration mechanical, not architectural.
- Implementation: Add dossier handlers to `src/specify_cli/dashboard/handlers/api.py`, follow router dispatch pattern, define handler interface spec in contracts/.

---

### Decision 2: Parity Baseline Identity & Scoping

**Context**: Baseline is point-in-time hash snapshot for drift detection. Question: What is the minimal key to prevent false positives across features/branches/machines/manifest versions?

**Options**:

**Option A: Global Single File (`.kittify/dossier-baseline.json`)**
- Pros: Simplest to implement, single source of truth
- Cons: **False positives**: feature A scan overwrites feature B baseline; branch switches collide; manifest version conflicts cause incorrect "drift"
- Risk: Curator sees spurious ParityDriftDetected after switching branches (confusing)
- Mitigation: None without adding scoping

**Option B: Feature-Scoped Only (`.kittify/dossiers/{feature_slug}/parity-baseline.json`)**
- Pros: Handles multi-feature workflows, feauture isolation
- Cons: Doesn't handle branch switches, manifest version changes, different machines/users in same project
- Risk: User switches from main→2.x, same feature has different manifest version, baseline mismatch looks like drift
- Mitigation: Document branch isolation (baseline doesn't cross branches); manifest versioning strategy TBD

**Option C: Fully Namespaced Key (Robust Identity Set)**
- Pros: Handles multi-feature, multi-branch, multi-user, multi-manifest-version scenarios
- Cons: More complex to compute and persist, larger storage footprint
- Risk: Namespace collision discovery is deferred; complexity may hide bugs
- Mitigation: Use reversible serialization (JSON), validate uniqueness constraints in tests

**→ CHOSEN: Option C (Fully Namespaced)**
- Rationale: Local-first workflows (multi-feature, multi-branch, multi-user) are already happening; don't defer baseline stability to post-O42. Namespacing is mechanical, complexity is manageable.
- Implementation:
  ```
  Baseline Key = {
    project_identity.project_uuid,
    project_identity.node_id,
    feature_slug,
    target_branch,
    mission_key,
    manifest_version
  }
  Storage: .kittify/dossiers/{feature_slug}/parity-baseline.json
  File contains: {baseline_key_hash, parity_hash_sha256, captured_at, captured_by}
  ```
- Validation: Baseline acceptance only if key matches current project/branch/mission/manifest (else treat as "no baseline", emit info-level drift event)

---

### Decision 3: Manifest Design (Step-Aware vs Phase-Locked)

**Context**: Dossier needs to know which artifacts are required at any given point in workflow. Question: Should manifest use hardcoded phases (spec_complete, planning_complete, tasks_complete) or mission-step-aware?

**Options**:

**Option A: Hardcoded Phases in Manifest**
- Pros: Simple schema (plan for 3 workflow stages), familiar to software-dev mindset
- Cons: **Locks in linearity**, breaks for research (scoping→methodology→gathering→synthesis→output) and documentation missions; phase names don't align with mission states
- Risk: Non-software-dev missions can't express completeness properly (example: research needs findings.md at "synthesis" state, not "planning_complete")
- Mitigation: Add mission-specific overrides (ugly, defeats purpose)

**Option B: Mission-Step-Aware (Read from Mission YAML State Machine)**
- Pros: Flexible, honors mission definition, supports any workflow shape
- Cons: Coupling to mission.yaml state definitions; manifest schema is more complex
- Risk: Manifest schema depends on mission.yaml structure; breaking changes to states affect dossier
- Mitigation: Version manifest independently; states are stable (rare changes); dossier validates state existence

**Option C: Minimal Schema (No Phase/Step Lock)**
- Pros: Completely decoupled from workflow, artifacts just have required/optional
- Cons: Can't check completeness for workflow stage (only all-or-nothing)
- Risk: Curator can't verify "have I done enough for planning phase?" without manual inspection
- Mitigation: Dossier only tracks presence/absence; completeness gates are workflow's responsibility

**→ CHOSEN: Option B (Mission-Step-Aware)**
- Rationale: Dossier is audit tool for workflow; it needs to speak the mission's language (states). Phase lock-in is anti-pattern; step-awareness is flexible and fits the software-dev, research, documentation, and future missions.
- Implementation:
  ```yaml
  # Expected artifact manifest (per mission type)
  schema_version: "1.0"
  mission_type: "software-dev"  # or "research", "documentation"
  manifest_version: "1"

  required_always:  # Independent of any state
    - artifact_key: "..."
      artifact_class: "..."
      path_pattern: "..."

  required_by_step:  # Step names from mission.yaml states
    specify:
      - artifact_key: "input.spec.main"
        artifact_class: "input"
        path_pattern: "spec.md"
    plan:
      - artifact_key: "output.plan.main"
        artifact_class: "output"
        path_pattern: "plan.md"
    # More steps as mission defines...

  optional_always:  # Always checked, never blocking
    - artifact_key: "..."
      artifact_class: "..."
      path_pattern: "..."
  ```
- Validation: Dossier reads mission YAML to get current state; fetches manifest for that mission type; checks only required_always + required_by_step[current_state] + optional_always (if present).
- Deferred: Manifest versioning strategy and backward compatibility (see "Deferred Decisions").

---

### Summary: Design Decisions

| Decision | Chosen Path | Key Trade-off | Implementation Load |
|----------|-------------|----------------|---------------------|
| **Stack** | Keep HTTPServer, define adapter interface for future migration | Scope containment vs modern stack | WP06: handler interface spec |
| **Baseline** | Feature-namespaced + project identity + branch + mission + manifest version | Robustness vs storage/complexity | WP08: baseline key computation |
| **Manifest** | Mission-step-aware, read from mission.yaml states | Flexibility vs coupling to mission definition | WP02: manifest loader + state validation |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Filesystem-Only Storage**: No new database tables required. Dossier state persists as JSONL event log and JSON snapshots in feature directory.

✅ **No Breaking Changes to Existing Models**: Feature introduces new dossier-specific entities (ArtifactRef, MissionDossier, etc.), does not modify existing mission/feature models.

✅ **Sync Infrastructure Integration**: Uses existing spec_kitty_events contracts and OfflineQueue. Adds 4 new event types (Dossier*) to schema, backward-compatible.

✅ **Dashboard Server Already Exists**: FastAPI server and Vue frontend for dashboard already deployed. Dossier panel is a new Vue component, reuses existing API middleware.

✅ **Async OK for API Endpoints**: Feature uses FastAPI's async/await for dashboard endpoints. Existing dashboard already uses async patterns, consistent with codebase.

✅ **Third-Party Dependencies**: All required dependencies already vendored (pydantic, ruamel.yaml, fastapi, rich). No new external packages required.

✅ **Mission Agnostic Foundation**: Dossier system is mission-agnostic; manifests are extensible per mission type. V1 ships strict manifests only for 3 missions, others degrade gracefully.

**Gates Passed**: All constitutional gates green. Proceeding to Phase 1 design.

## Project Structure

### Documentation (this feature)

```
kitty-specs/042-local-mission-dossier-authority-parity-export/
├── spec.md              # Feature specification (source of truth)
├── plan.md              # This file (technical design)
├── research.md          # Phase 0 research (TBD by /spec-kitty.plan)
├── data-model.md        # Phase 1 data model (TBD by /spec-kitty.plan)
├── quickstart.md        # Phase 1 quickstart (TBD by /spec-kitty.plan)
├── contracts/           # Phase 1 JSON Schema contracts (TBD by /spec-kitty.plan)
└── tasks.md             # Phase 2 work packages (generated by /spec-kitty.tasks)
```

### Source Code Structure

```
src/specify_cli/
├── dossier/                          # NEW: Dossier subsystem
│   ├── __init__.py
│   ├── models.py                     # ArtifactRef, MissionDossier, MissionDossierSnapshot
│   ├── manifest.py                   # ExpectedArtifactManifest, registry per mission type
│   ├── indexer.py                    # Artifact indexing, hashing, missing detection
│   ├── hasher.py                     # Deterministic SHA256 hashing, parity computation
│   ├── events.py                     # Dossier event emission (4 types)
│   ├── store.py                      # Snapshot persistence (JSON JSONL)
│   ├── drift_detector.py             # Local parity-drift detection
│   └── test_fixtures.py              # Shared test helpers
│
├── dashboard/
│   ├── handlers/
│   │   ├── api.py                    # MODIFY: Add DossierHandler mixin with methods:
│   │   │   ├── handle_dossier_overview()  # GET /api/dossier/overview
│   │   │   ├── handle_dossier_artifacts()  # GET /api/dossier/artifacts
│   │   │   ├── handle_dossier_artifact_detail()  # GET /api/dossier/artifacts/{key}
│   │   │   └── handle_dossier_snapshot_export()  # GET /api/dossier/snapshots/export
│   │   │
│   │   └── router.py                 # MODIFY: Add routes in do_GET():
│   │       - if path.startswith('/api/dossier/'): self.handle_dossier(path)
│   │
│   ├── static/
│   │   └── js/
│   │       ├── dashboard.js          # MODIFY: Add fetch wrappers for dossier endpoints
│   │       └── dossier-panel.js      # NEW: Dossier UI component (vanilla JS, no Vue)
│   │
│   ├── templates/
│   │   └── dashboard.html            # MODIFY: Add dossier panel tab/section
│   │
│   └── scanner.py                    # MODIFY: Call dossier.indexer.index_feature() on scan
│
├── missions/
│   ├── software-dev/
│   │   └── expected-artifacts.yaml   # NEW: Manifest for software-dev mission artifacts
│   ├── research/
│   │   └── expected-artifacts.yaml   # NEW: Manifest for research mission artifacts
│   └── documentation/
│       └── expected-artifacts.yaml   # NEW: Manifest for documentation mission artifacts
│
└── sync/
    └── events.py                     # MODIFY: Register 4 new dossier event types

tests/
├── specify_cli/dossier/              # NEW: Dossier test suite
│   ├── test_models.py
│   ├── test_manifest.py
│   ├── test_indexer.py
│   ├── test_hasher.py
│   ├── test_events.py
│   ├── test_drift_detector.py
│   └── integration/
│       ├── test_determinism.py       # Hash reproducibility
│       ├── test_missing_detection.py # All 4 event types
│       └── test_encoding.py          # UTF-8 edge cases
│
└── integration/
    ├── test_dashboard_dossier.py     # Dashboard API integration
    └── test_sync_dossier.py          # Sync pipeline integration
```

**Structure Decision**: Single Python package (spec-kitty) + optional frontend Vue components. Dossier subsystem is self-contained in `src/specify_cli/dossier/`, integrates with dashboard API and sync infrastructure via extension points (not modification of core).

## Phase Breakdown & Work Packages

### Phase 1: Core Projection & Events (WP01-WP05)

| WP | Title | Deliverables | Dependencies |
|----|-------|--------------|--------------|
| **WP01** | ArtifactRef Model & Deterministic Hashing | `models.py` + hasher.py with SHA256 logic | None |
| **WP02** | Expected Artifact Manifests | 3 YAML manifests (software-dev, research, documentation) in `missions/*/` | None |
| **WP03** | Indexing & Missing Detection | `indexer.py` + manifest-based validation | WP01, WP02 |
| **WP04** | Dossier Event Types & Emit Integration | `events.py` + 4 event schemas in contracts/ | WP01, WP03 |
| **WP05** | Deterministic Snapshot & Parity Hash | Snapshot computation, store.py, reproduce on identical content | WP01, WP04 |

### Phase 2: API & Dashboard (WP06-WP08)

| WP | Title | Deliverables | Dependencies |
|----|-------|--------------|--------------|
| **WP06** | Dashboard API Endpoints | 4 FastAPI routes (overview, list, detail, export) | WP01-WP05 |
| **WP07** | Dashboard UI Integration | DossierPanel.vue + ArtifactDetail.vue + filtering | WP06 |
| **WP08** | Local Parity-Drift Detector | `drift_detector.py`, local baseline cache, event emission | WP05, WP06 |

### Phase 3: Testing & Hardening (WP09-WP10)

| WP | Title | Deliverables | Dependencies |
|----|-------|--------------|--------------|
| **WP09** | Determinism Test Suite | Hash reproducibility, ordering stability, encoding tests | All Phase 1 |
| **WP10** | Integration & Edge Cases | Dashboard API tests, sync pipeline integration, large artifacts, encoding errors | All Phase 2 + WP09 |

## Key Technical Decisions

### 1. **Deterministic Hashing**
- Use SHA256 (hashlib, stdlib)
- Hash artifact bytes directly (not relative path or metadata)
- Order-independent parity: sort hashes before combining, compute combined hash
- Encoding: Read as binary, fail explicitly if invalid UTF-8 (no silent fallback)

### 2. **Manifest System**
- YAML per mission type: `src/specify_cli/missions/{mission}/expected-artifacts.yaml`
- Schema:
  ```yaml
  required_by_step:
    planning: [spec, plan, tasks, tasks/*.md]
    implementation: [...]
  optional_always: [research, gap-analysis]
  ```
- Extensible: Other missions degrade gracefully (no manifest = no missing detection, only indexing)

### 3. **Artifact Classification**
- 7 classes: input, workflow, output, evidence, policy, runtime, + extensible
- Derived from filename patterns or explicit frontmatter (if added to mission templates)
- Used for filtering in dashboard

### 4. **Event Emission (Conditional & Deterministic)**
- Integrated with spec_kitty_events contracts
- **Always Emitted**: MissionDossierArtifactIndexed (one per artifact), MissionDossierSnapshotComputed (after scan completes)
- **Conditionally Emitted**: MissionDossierArtifactMissing (only if required artifacts missing), MissionDossierParityDriftDetected (only if local hash differs from baseline)
- Routed via OfflineQueue (async, retry-safe)
- Each event immutable, timestamped, includes envelope metadata

### 5. **Local Parity Detection (Robust Namespacing)**
- Baseline: locally cached point-in-time parity hash with identity tuple (stored in `.kittify/dossiers/{feature_slug}/parity-baseline.json`)
- **Baseline Key**: Hash of identity tuple = `{project_uuid, node_id, feature_slug, target_branch, mission_key, manifest_version}`
  - Prevents false positives: branch switch, manifest version change, multi-user/multi-machine scenarios, manifest updates
  - Uses local ProjectIdentity (from sync infrastructure) as authority
- **Acceptance Logic**: Accept baseline only if key matches current project/branch/mission/manifest; else treat as "no baseline"
- **Drift Detection**: Compare current snapshot hash vs cached baseline (if accepted); emit ParityDriftDetected only if hash differs and baseline accepted
- Works offline: no SaaS call required
- **Deferred**: Cross-org/global baseline reconciliation (see "Deferred Decisions")

### 6. **Dashboard API Design**
- Stateless endpoints, no session required
- Filtering by class, wp_id, step_id with stable ordering
- Detail endpoint returns full text (with truncation notice for >5MB)
- Export endpoint returns snapshot JSON (importable by SaaS)

### 7. **Mission-Step-Aware Completeness & Manifest Scoping**
- **No Hardcoded Phases**: Manifest uses mission-defined step names (from mission.yaml state machine), not generic phases
  - software-dev: discover → specify → plan → implement → review → done
  - research: scoping → methodology → gathering → synthesis → output → done
  - documentation: (mission-specific states)
- **Manifest Schema**: Per mission type, define:
  - `required_always`: Artifacts needed regardless of workflow step
  - `required_by_step`: Dict mapping step_id → list of required artifacts (e.g., step "specify" → ["spec.md"])
  - `optional_always`: Artifacts checked if present, never block completeness
- **Completeness Check**: Given current mission state, check `required_always` + `required_by_step[current_state]`
- **Deferred**: Manifest versioning strategy (see "Deferred Decisions")

### 8. **Error Handling**
- No silent failures: all anomalies explicit in events and API
- Unreadable artifacts: emit MissionDossierArtifactMissing with reason_code="unreadable"
- UTF-8 errors: record hash error, include in anomaly event, continue scan
- Missing required artifacts for current phase: blocking anomaly (completeness_status="incomplete")
- Missing optional artifacts: non-blocking, recorded, not counted as missing

## Deferred Decisions (Post-O42)

Explicitly deferred to preserve O42 scope and maintain KISS principle:

### 1. Dashboard Stack Migration
- **Decision**: HTTPServer + handler pattern stays. Future migration path documented in WP06 adapter interface.
- **Defer Reason**: Scope containment; migration is orthogonal to dossier functionality
- **Future Feature**: "044-dashboard-modernization" (FastAPI + Vue SPA, global event store, WebSocket subscriptions)
- **Impact on O42**: None; O42 handlers follow current pattern, adapter interface allows mechanical migration without breaking dossier logic

### 2. Manifest Versioning & Backward Compatibility
- **Decision**: V1 ships single manifest_version per mission type. No version negotiation or evolution strategy.
- **Defer Reason**: Single mission type per project (typical use case); complex versioning requires ADR, not O42 scope
- **Future Feature**: "045-manifest-versioning" (explicit version negotiation, migration strategies, deprecation paths)
- **Impact on O42**: Manifest key includes manifest_version; future feature adds version resolution logic

### 3. Cross-Org & Global Canonical Feature Naming
- **Decision**: O42 uses local project_uuid + feature_slug. No global uniqueness strategy or federation protocol.
- **Defer Reason**: SaaS integration (auth, org boundaries, cross-repo features) is out of scope; local workflows are v1 requirement
- **Future Feature**: "046-saas-project-federation" (org identifiers, canonical feature naming, cross-project references)
- **Impact on O42**: Project identity is local-first (from sync/project_identity.py). Global uniqueness is SaaS's responsibility.

### 4. SaaS Parity Reconciliation & Event Replay
- **Decision**: O42 emits events to offline queue. SaaS receives and validates in separate feature.
- **Defer Reason**: Parity reconciliation (detecting SaaS misalignment, replay workflows) is SaaS concern, not local sync
- **Future Feature**: "047-saas-parity-reconciliation" (SaaS parity validation, event replay, conflict resolution)
- **Impact on O42**: Events are append-only, immutable. SaaS feature will add reconciliation logic.

### 5. Artifact Content Caching & Full-Text Search
- **Decision**: O42 indexes artifacts but does not cache content (read-on-demand) or enable search.
- **Defer Reason**: Caching adds complexity; search requires indexing overhead; filtering by class/step is sufficient for v1
- **Future Feature**: "048-artifact-search" (full-text search, content caching, analytics)
- **Impact on O42**: API detail endpoints read artifact content on-demand; no caching layer in O42

### 6. Manifest Evolution & Custom Missions
- **Decision**: V1 ships strict manifests for 3 missions (software-dev, research, documentation). Other missions degrade gracefully (no completeness check).
- **Defer Reason**: Manifest schema is frozen in O42; custom/extension missions require template system evolution
- **Future Feature**: "049-custom-mission-manifests" (mission plugins, manifest schema extensibility, dynamic artifact definitions)
- **Impact on O42**: Manifest loader skips unknown missions; no blocking behavior

---

## Out-of-Scope (Non-Goals)

1. Building SaaS dashboard UI in this feature (local dashboard UI is in scope)
2. Implementing event replay/theater workflows (emit-only this phase)
3. Replacing git/filesystem as source of truth for artifacts
4. Full-text search indexing (basic filtering only)
5. Real-time artifact sync (batch scan-based)
6. Artifact versioning or delta tracking (snapshot-based, not incremental)
7. Dashboard framework migration (future feature, separate from dossier logic)
8. Cross-org project federation or global canonical naming (future SaaS feature)