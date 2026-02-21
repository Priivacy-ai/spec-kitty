---
feature_slug: 042-local-mission-dossier-authority-parity-export
feature_title: Local Mission Dossier Authority & Parity Export
total_work_packages: 10
total_subtasks: 58
lane: planned
---

# Work Packages: Local Mission Dossier Authority & Parity Export

## Summary

Feature 042 implements a mission artifact dossier system that indexes all spec-kitty feature artifacts, computes deterministic content hashes and parity signatures, and emits canonical dossier events to sync infrastructure. The system enables local parity-drift detection (offline) while exporting events for SaaS backend integration.

**Phases**:
- **Phase 1 (WP01-WP05)**: Core models, manifests, indexing, events, snapshots
- **Phase 2 (WP06-WP08)**: Dashboard API, UI integration, parity detection
- **Phase 3 (WP09-WP10)**: Testing, edge cases, integration

**Total Effort**: ~58 subtasks across 10 work packages | **Delivery Mode**: API + local dashboard UI parity slice

---

## Phase 1: Core Projection & Events (WP01-WP05)

### WP01: ArtifactRef Model & Deterministic Hashing

**Goal**: Define immutable artifact reference model and deterministic SHA256 hashing utilities

**Priority**: P1 (Foundation for all downstream WPs)

**Status**: planned

**Subtasks**: T001-T005 (5 subtasks)
- [x] T001: Create ArtifactRef pydantic model (identity, location, content hash, provenance, state fields)
- [x] T002: Implement SHA256 deterministic hashing utility (file → hash)
- [x] T003: Build Hasher class with order-independent parity (sorted hashes, combined hash)
- [x] T004: UTF-8 validation & error handling (explicit failure, no silent corruption)
- [x] T005: Unit tests for hashing determinism (same file → same hash, reproducibility)

**Implementation Notes**:
- ArtifactRef: ~25 fields covering identity, location, metadata, provenance, state (see data-model.md for full spec)
- Hasher: Standalone utility class, no dependencies beyond hashlib (stdlib)
- Order-independence: Sort artifact hashes lexicographically before concatenation
- UTF-8: Read file as bytes, hash bytes directly; if invalid UTF-8 detected, emit error_reason and continue

**Test Criteria**:
- ArtifactRef validates all required fields, rejects malformed artifact_key
- Same file hashed 10x produces identical SHA256
- Different files produce different hashes
- Parity hash unchanged by artifact order

**Dependencies**: None

**Estimated Scope**: ~300 lines (models.py + hasher.py + tests)

---

### WP02: Expected Artifact Manifests

**Goal**: Define manifest schema and load v1 manifests for software-dev, research, documentation missions

**Priority**: P1 (Foundation for completeness checking)

**Status**: planned

**Subtasks**: T006-T011 (6 subtasks)
- [x] T006: Design manifest schema (required_always, required_by_step, optional_always)
- [x] T007: Implement ManifestRegistry loader (reads mission.yaml states, loads YAML manifests)
- [x] T008: Create software-dev expected-artifacts.yaml (step-aware, using existing mission artifacts)
- [x] T009: Create research expected-artifacts.yaml (step-aware)
- [x] T010: Create documentation expected-artifacts.yaml (step-aware)
- [x] T011: Manifest validation (verify steps exist in mission.yaml, path patterns valid)

**Implementation Notes**:
- Manifest schema: YAML per mission, with schema_version, mission_type, manifest_version fields
- Step-aware: `required_by_step` keys are state IDs from mission.yaml (e.g., "planning", "implementation")
- V1 scope: Only software-dev, research, documentation; other missions degrade gracefully (index only, no completeness check)
- ManifestRegistry: Singleton loader, cache manifests in memory
- Path patterns: Support wildcards (e.g., "tasks/*.md")

**Test Criteria**:
- Manifest loads from YAML without errors
- Registry correctly maps step names to artifact lists
- Unknown missions handled gracefully (return None, no exception)

**Dependencies**: WP01 (ArtifactRef model context)

**Estimated Scope**: ~400 lines (manifest.py + 3 YAML files + tests)

---

### WP03: Indexing & Missing Detection

**Goal**: Implement artifact scanner that indexes feature directory, classifies artifacts, detects missing required artifacts

**Priority**: P1 (Core dossier functionality)

**Status**: planned

**Subtasks**: T012-T017 (6 subtasks)
- [x] T012: Implement Indexer.index_feature() scanning logic (walk feature directory)
- [x] T013: Artifact classification (derive from filename patterns, manifest definitions)
- [x] T014: Missing artifact detection (required vs optional, per manifest)
- [x] T015: Unreadable artifact handling (permission denied, encoding errors, deleted mid-scan)
- [x] T016: MissionDossier builder from indexed artifacts (create complete inventory)
- [x] T017: Step-aware completeness checking (given mission step, which artifacts required?)

**Implementation Notes**:
- Indexer: Recursive directory scan, yield artifacts as discovered
- Classification: 6 deterministic classes (input, workflow, output, evidence, policy, runtime)
- Missing detection: Compare filesystem scan against manifest requirements; record reason_code (not_found, unreadable, invalid_format)
- Error handling: Catch permission errors, UTF-8 decode failures; emit error_reason, continue scan (no silent failures)
- MissionDossier: Aggregates artifacts, links to manifest, computes completeness_status

**Test Criteria**:
- Scans 30+ artifacts without errors
- Correctly identifies required vs optional
- Missing required artifacts flagged with reason codes
- Optional artifacts ignored if absent (no missing events)

**Dependencies**: WP01 (ArtifactRef), WP02 (manifest)

**Estimated Scope**: ~400 lines (indexer.py + tests)

---

### WP04: Dossier Event Types & Emission

**Goal**: Define 4 canonical dossier event schemas and integrate emission with sync infrastructure

**Priority**: P1 (Required for SaaS integration)

**Status**: planned

**Subtasks**: T018-T022 (5 subtasks)
- [ ] T018: Define 4 dossier event schemas (ArtifactIndexed, ArtifactMissing, SnapshotComputed, ParityDriftDetected)
- [ ] T019: Add schemas to spec-kitty-events contracts (JSON Schema)
- [ ] T020: Event emitters (async, integrate with OfflineQueue)
- [ ] T021: Payload validation (Pydantic models, fail on invalid data)
- [ ] T022: Event routing to sync infrastructure (enqueue, webhook dispatch)

**Implementation Notes**:
- Event types: See data-model.md for complete payload schemas
  - MissionDossierArtifactIndexed: Emitted once per artifact indexed
  - MissionDossierArtifactMissing: Emitted only if required artifact missing
  - MissionDossierSnapshotComputed: Emitted after all artifacts indexed
  - MissionDossierParityDriftDetected: Emitted only if parity hash differs from baseline
- Emission: Via spec_kitty_events.OfflineQueue.emit(), respects offline mode
- Validation: Pydantic BaseModel for each payload; raise on schema violation

**Test Criteria**:
- All 4 event types emit with valid schemas
- Events enqueue to offline queue (no SaaS call during local scan)
- Conditional events (missing, drift) emit only when conditions met
- Envelope metadata (event_id, timestamp, actor) auto-populated

**Dependencies**: WP03 (indexing produces artifacts), spec_kitty_events (existing)

**Estimated Scope**: ~350 lines (events.py + JSON schemas + tests)

---

### WP05: Snapshot Computation & Parity Hash

**Goal**: Compute deterministic snapshots from dossier state and compute reproducible parity hashes

**Priority**: P1 (Core for determinism requirement)

**Status**: planned

**Subtasks**: T023-T027 (5 subtasks)
- [ ] T023: Deterministic snapshot computation (sort artifacts, count by status)
- [ ] T024: Parity hash algorithm (sorted artifact hashes, combined hash)
- [ ] T025: Snapshot persistence (JSON storage to `.kittify/dossiers/{feature_slug}/snapshot-latest.json`)
- [ ] T026: Snapshot validation (reproducibility: same content → same hash)
- [ ] T027: Snapshot equality comparison (parity_hash_sha256 as source of truth)

**Implementation Notes**:
- Snapshot: Point-in-time projection with artifact counts, completeness status, parity hash
- Parity hash: SHA256 of concatenated sorted artifact hashes (order-independent)
- Persistence: Store as JSON, include timestamp and artifact summaries for audit
- Reproducibility: Identical artifact content (on any machine, any timezone) produces identical parity hash
- SC-002 validation: Run twice on unchanged content, verify parity_hash_sha256 identical

**Test Criteria**:
- Snapshot computes without errors for 30+ artifacts
- Parity hash deterministic (same content → same hash, multiple runs)
- Snapshot reproducible on different machines/timezones (if artifact content identical)
- Completeness status correctly reflects required artifacts present/missing

**Dependencies**: WP01 (ArtifactRef, hasher), WP03 (MissionDossier)

**Estimated Scope**: ~350 lines (store.py + snapshot logic + tests)

---

## Phase 2: API & Dashboard Integration (WP06-WP08)

### WP06: Dashboard API Endpoints

**Goal**: Expose 4 REST endpoints for dossier access, implement adapter pattern for future FastAPI migration

**Priority**: P1 (Enables dashboard UI)

**Status**: planned

**Subtasks**: T028-T033 (6 subtasks)
- [ ] T028: Implement GET /api/dossier/overview endpoint (returns DossierOverviewResponse)
- [ ] T029: Implement GET /api/dossier/artifacts endpoint (list, filtering by class/wp_id/step_id)
- [ ] T030: Implement GET /api/dossier/artifacts/{artifact_key} endpoint (detail, full text)
- [ ] T031: Implement GET /api/dossier/snapshots/export endpoint (returns snapshot JSON for SaaS import)
- [ ] T032: Router dispatch rules (add dossier routes to dashboard handler)
- [ ] T033: Define adapter interface for future FastAPI migration (handler protocol spec)

**Implementation Notes**:
- Overview: Returns completeness_status, parity_hash, artifact counts, last_scanned_at
- Artifacts list: Supports filtering by class, wp_id, step_id; stable ordering (by artifact_key)
- Detail: Returns full text content (if <5MB), media_type_hint (markdown, json, yaml), truncation notice if >5MB
- Export: Returns snapshot JSON (importable by SaaS backend)
- Handlers: Integrate with existing dashboard handler pattern (HTTPServer + dispatch)
- Adapter interface: Define protocol/interface for handler methods (enables future FastAPI port)

**Test Criteria**:
- All endpoints return valid JSON with correct schema
- Filtering works (class=output returns only output artifacts)
- Detail endpoint truncates large files (>5MB) gracefully
- Export returns snapshot JSON compatible with SaaS import

**Dependencies**: WP05 (snapshot), WP04 (event models)

**Estimated Scope**: ~400 lines (api.py handlers + adapter interface + tests)

---

### WP07: Dashboard UI Integration

**Goal**: Render dossier overview, artifact list, filtering, and detail views in local dashboard

**Priority**: P1 (User-facing feature)

**Status**: planned

**Subtasks**: T034-T039 (6 subtasks)
- [ ] T034: Create dossier-panel.js (vanilla JS, fetch wrappers, no Vue framework)
- [ ] T035: Add dossier tab to dashboard HTML (tabs: overview, artifacts, detail)
- [ ] T036: Render artifact list with filtering UI (checkboxes for class, wp_id, step_id)
- [ ] T037: Implement artifact detail view (full-text display, syntax highlighting hints)
- [ ] T038: Add truncation notice for large artifacts (>5MB, with download link if needed)
- [ ] T039: Media type hints (markdown badge, json icon, yaml label)

**Implementation Notes**:
- Vanilla JS: No Vue/SPA framework; fetch API + DOM manipulation
- Panel: Integrated as new tab in existing dashboard
- Filtering: Client-side filtering (load full list, filter locally) or server-side (add query params to /api/dossier/artifacts)
- Detail view: Modal or side panel showing full artifact content
- Truncation: If size_bytes > 5242880 (5MB), show notice + link to raw file
- Syntax hints: Add CSS classes (markdown-content, json-content) for browser-native highlighting

**Test Criteria**:
- Dashboard renders dossier panel without errors
- Artifact list loads and displays 30+ artifacts
- Filtering works (click class=output, list updates)
- Detail view displays full text for small artifacts, truncation notice for large

**Dependencies**: WP06 (API endpoints)

**Estimated Scope**: ~300 lines (dossier-panel.js + HTML/CSS + tests)

---

### WP08: Local Parity-Drift Detector

**Goal**: Implement local baseline management and parity drift detection, emit drift events

**Priority**: P1 (Core parity feature, offline-capable)

**Status**: planned

**Subtasks**: T040-T045 (6 subtasks)
- [ ] T040: Baseline key computation (identity tuple: project_uuid, node_id, feature_slug, target_branch, mission_key, manifest_version)
- [ ] T041: Baseline persistence (JSON file: `.kittify/dossiers/{feature_slug}/parity-baseline.json`)
- [ ] T042: Baseline acceptance logic (key match validation, prevent false positives)
- [ ] T043: Drift detection (compare current parity_hash_sha256 vs cached baseline)
- [ ] T044: ParityDriftDetected event emission (severity, missing_in_local, missing_in_saas)
- [ ] T045: Baseline update logic (capture new baseline when accepted)

**Implementation Notes**:
- Baseline key: Fully namespaced to prevent false positives (branch switches, manifest updates, multi-user/machine)
- Key components: project_uuid, node_id (from sync/project_identity.py), feature_slug, target_branch, mission_key, manifest_version
- Acceptance: Compare current key hash vs baseline key hash; accept only if match (else treat as "no baseline")
- Drift detection: Works offline, compares hashes only (no SaaS call)
- Event: Emitted only if baseline accepted AND hash differs; includes severity (info/warning/error)

**Test Criteria**:
- Baseline computes and persists without errors
- Acceptance correctly validates key match
- Drift detection identifies hash changes
- False positives prevented (branch switch triggers "no baseline", not drift event)
- Event emitted only on true drift (hash change with matching baseline)

**Dependencies**: WP05 (snapshot/parity hash), WP04 (event emission), sync/project_identity (existing)

**Estimated Scope**: ~350 lines (drift_detector.py + tests)

---

## Phase 3: Testing & Hardening (WP09-WP10)

### WP09: Determinism Test Suite

**Goal**: Comprehensive tests for hash reproducibility, ordering stability, encoding robustness

**Priority**: P1 (Critical for SC-002, SC-006, SC-007 success criteria)

**Status**: planned

**Subtasks**: T046-T050 (5 subtasks)
- [ ] T046: Hash reproducibility (same file → same hash, tested 10 runs)
- [ ] T047: Order independence (artifact order irrelevant to parity hash)
- [ ] T048: UTF-8 handling (special chars, BOM, CJK, surrogates)
- [ ] T049: CRLF vs LF consistency (Windows/Unix line endings)
- [ ] T050: Parity hash stability (machines, timezones, different Python versions)

**Implementation Notes**:
- Reproducibility: Hash same file multiple times, verify identical SHA256
- Order independence: Create dossier with artifacts in random order, verify parity hash unchanged
- UTF-8: Test BOM-prefixed files, CJK characters (Chinese/Japanese), UTF-8 surrogates, invalid sequences (should fail explicitly)
- CRLF: Test files with Windows (CRLF) and Unix (LF) line endings; hash should be order-independent
- Cross-machine: If possible, run same test on different machines (Linux/macOS/Windows), verify hash identical

**Test Criteria**:
- All SC-002, SC-006, SC-007 success criteria passed
- Zero hash mismatches across 10+ runs, multiple machines
- UTF-8 edge cases handled explicitly (error_reason, no corruption)
- Line-ending differences don't cause hash mismatches

**Dependencies**: WP01 (hasher), WP05 (snapshot)

**Estimated Scope**: ~300 lines (test_determinism.py)

---

### WP10: Integration & Edge Cases

**Goal**: Integration tests covering full scan workflow, encoding errors, large artifacts, edge cases

**Priority**: P1 (Hardening, final validation)

**Status**: planned

**Subtasks**: T051-T058 (8 subtasks)
- [ ] T051: Missing required artifact detection (edge case: multiple missing, blocking)
- [ ] T052: Optional artifact handling (edge case: optional missing, non-blocking)
- [ ] T053: Unreadable artifact handling (permission denied, disk I/O errors)
- [ ] T054: Large artifact handling (>5MB, dashboard truncation, no memory issues)
- [ ] T055: Full scan workflow integration test (specify → plan → tasks → index → snapshot → events)
- [ ] T056: SaaS webhook simulator (mock endpoint receives all 4 event types)
- [ ] T057: Concurrent file modification edge case (file changed during scan)
- [ ] T058: Manifest version mismatch edge case (manifest updated, baseline key mismatch)

**Implementation Notes**:
- Missing detection: Create feature with spec.md missing, plan.md present; verify MissionDossierArtifactMissing event
- Optional handling: Create feature with research.md (optional) missing; verify no missing event
- Unreadable: Create artifact with no read permissions; verify unreadable error_reason, continue scan
- Large artifacts: Create 10MB artifact; verify API truncates, shows notice, no memory explosion
- Full workflow: Create feature with all artifacts, run scan, verify all events emitted in order
- Webhook simulator: Mock HTTP endpoint that accepts POST /webhook/dossier, logs all 4 event types
- Concurrent modification: Modify file mid-scan (if possible); verify hash captures pre-modification state
- Manifest mismatch: Change manifest_version, re-scan; verify baseline rejected (no drift event, informational instead)

**Test Criteria**:
- All edge cases handled gracefully (no silent failures, no crashes)
- SaaS webhook simulator receives all expected events
- Large artifacts processed without memory issues
- Concurrent modification handled (scan completes, hash captures point-in-time state)
- Manifest version changes prevent false positive drift events

**Dependencies**: All WP01-WP09

**Estimated Scope**: ~450 lines (test_integration.py, test_encoding.py, fixtures)

---

## Dependency Graph

```
WP01 (ArtifactRef, Hasher)
  ├─→ WP02 (Manifests)
  ├─→ WP03 (Indexing)
  ├─→ WP05 (Snapshot, Parity)
  └─→ WP09 (Determinism Tests)

WP02 (Manifests)
  └─→ WP03 (Indexing)

WP03 (Indexing)
  ├─→ WP04 (Events)
  └─→ WP05 (Snapshot)

WP04 (Events)
  ├─→ WP06 (API Endpoints)
  └─→ WP08 (Drift Detection)

WP05 (Snapshot, Parity)
  ├─→ WP06 (API Endpoints)
  ├─→ WP08 (Drift Detection)
  └─→ WP09 (Determinism Tests)

WP06 (API Endpoints)
  ├─→ WP07 (Dashboard UI)
  └─→ WP10 (Integration Tests)

WP07 (Dashboard UI)
  └─→ WP10 (Integration Tests)

WP08 (Drift Detection)
  └─→ WP10 (Integration Tests)

WP09 (Determinism Tests)
  └─→ WP10 (Integration Tests)
```

**Critical Path**: WP01 → WP02 → WP03 → (WP04 + WP05) → WP06 → WP07 → WP10

**Parallelizable Groups**:
- Phase 1: WP01, then WP02, then WP03, then WP04 + WP05 in parallel
- Phase 2: WP06 (after WP04 + WP05), then WP07 (after WP06), and WP08 in parallel (after WP04 + WP05)
- Phase 3: WP09 (after WP01 + WP05), WP10 (after WP06 + WP07 + WP08 + WP09)

---

## Success Criteria Summary

| Success Criteria | Coverage |
|------------------|----------|
| SC-001 (API <500ms) | WP06, WP10 testing |
| SC-002 (Deterministic snapshots) | WP05, WP09 |
| SC-003 (Event emission) | WP04, WP10 |
| SC-004 (Missing detection) | WP03, WP10 |
| SC-005 (Scale to 1000 artifacts) | WP10 |
| SC-006 (Parity reproducible) | WP05, WP09 |
| SC-007 (UTF-8 robustness) | WP09, WP10 |

All work packages collectively deliver complete feature 042 specification.

---

## Notes

- **Dependencies finalized**: WP frontmatter dependency lists are now aligned with this graph for deterministic `implement` validation.
- **Test-driven**: Each WP includes unit tests + integration tests (WP10 comprehensive)
- **Scope containment**: No FastAPI migration, no manifest versioning, no cross-org federation (deferred to post-042)
- **Quality bar**: Zero silent failures, explicit error handling, deterministic hashing, full spec compliance
