# Feature Specification: Local Mission Dossier Authority & Parity Export

**Feature Branch**: `042-local-mission-dossier-authority-parity-export`
**Created**: 2026-02-21
**Status**: Draft
**Priority**: P1 (Highest)
**Target Branch**: `2.x`
**Mission**: software-dev

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Artifact Curator Inspects Complete Mission (Priority: P1)

A mission curator wants to verify that all required artifacts for a software-dev feature at Phase 2 (Planning Complete) exist in local spec-kitty and have been correctly captured.

**Why this priority**: This is the foundational workflow. Without artifact visibility, nothing else works. Curators/reviewers need to see what exists.

**Independent Test**: A curator can run `/spec-kitty.status` or open the local dashboard, see a dossier panel that shows: (1) which required artifacts are present, (2) content hash for each, (3) any missing required artifacts flagged with reason codes.

**Acceptance Scenarios**:

1. **Given** a feature at Phase 2 (spec, plan, tasks present), **When** curator opens dashboard dossier, **Then** all 3 artifacts are indexed with paths, sizes, content hashes, and state=present
2. **Given** a feature missing `plan.md`, **When** dossier scans, **Then** MissionDossierArtifactMissing event emitted with reason_code="not_found" and blocking=true
3. **Given** an artifact with UTF-8 encoding issues, **When** indexed, **Then** content_hash_sha256 is deterministic across repeated scans
4. **Given** a feature with optional artifact (e.g., `research.md`), **When** missing, **Then** no missing-anomaly event emitted (optional artifacts indexed if present, ignored if absent)

---

### User Story 2 - SaaS Sync Receives Parity Snapshot (Priority: P1)

The local sync pipeline needs to emit canonical dossier events so that a SaaS backend can reconstruct the mission artifact state and verify parity with what stakeholders expect.

**Why this priority**: Parity export is the entire deliverable. Without canonical events, SaaS has no way to consume and display mission artifacts.

**Independent Test**: After a local scan/index operation, exactly 4 types of dossier events have been emitted to the sync pipeline (or queued offline): MissionDossierArtifactIndexed, MissionDossierSnapshotComputed, optional MissionDossierArtifactMissing, optional MissionDossierParityDriftDetected. SaaS can parse these events deterministically.

**Acceptance Scenarios**:

1. **Given** a mission with 10 indexed artifacts, **When** dossier is computed, **Then** MissionDossierSnapshotComputed event emitted with completeness_status, parity_hash_sha256, artifact counts
2. **Given** a MissionDossierSnapshotComputed event, **When** SaaS receives it, **Then** it can reconstruct full artifact catalog from prior MissionDossierArtifactIndexed events
3. **Given** 2 local scans with no content changes, **When** both generate snapshots, **Then** parity_hash_sha256 is identical (deterministic)
4. **Given** local snapshot hash differs from SaaS hash, **When** drift detection runs, **Then** MissionDossierParityDriftDetected emitted with severity, missing_in_local, missing_in_saas

---

### User Story 3 - Dashboard Renders Full-Text Artifact Detail (Priority: P2)

Reviewers want to read artifact content in the dashboard without leaving to open files.

**Why this priority**: Reduces friction for review. High-value UX improvement, but artifact indexing is more critical.

**Independent Test**: Dashboard GET `/api/dossier/artifacts/{artifact_key}` returns artifact metadata + full text content (up to size limit), with syntax highlighting hints (markdown, json, yaml).

**Acceptance Scenarios**:

1. **Given** an artifact indexed in dossier, **When** GET `/api/dossier/artifacts/input.spec.main`, **Then** response includes path, class, hash, full text, and media_type hint
2. **Given** an artifact >5MB, **When** requested, **Then** response includes size_bytes and truncation_notice (full content not returned inline)
3. **Given** unreadable artifact (encoding error, deleted), **When** accessed, **Then** HTTP 404 or 410 with missing reason

---

### User Story 4 - Curator Filters Artifacts by Type & Phase (Priority: P2)

Curator wants to query "show me all output artifacts from Phase 2" or "all evidence artifacts" to cross-check completeness.

**Why this priority**: Advanced filtering unlocks audit workflows. Lower priority than core parity export.

**Independent Test**: Dashboard GET `/api/dossier/artifacts?class=output&step_id=planning` returns filtered list with correct counts and ordering.

**Acceptance Scenarios**:

1. **Given** a dossier with mixed artifact classes, **When** filtering by class=evidence, **Then** only artifact_class="evidence" returned, in stable order
2. **Given** a feature spanning multiple mission steps, **When** filtering by step_id, **Then** only artifacts for that step included
3. **Given** a feature with multiple WPs, **When** filtering by wp_id=WP02, **Then** only artifacts linked to WP02 returned

---

### Edge Cases

- What happens when spec.md is unreadable (encoding, permission)?
  - Recorded as missing/unreadable, not silent failure. MissionDossierArtifactMissing emitted with reason_code="unreadable".

- How are git history artifacts (e.g., commit messages, commit SHAs) indexed?
  - Revision fields capture git SHA when available. Provenance tracks source_kind="git".

- What if artifact manifest is not yet defined for a new mission type?
  - Graceful degradation: index artifacts found, emit warnings, but do not block sync. Missing-artifact detection skipped until manifest defined.

- What if content changes during scan (file being written)?
  - Content hash captures the state at scan time. If file changes immediately after, next scan produces different hash (expected).

- How do optional vs required artifacts impact "completeness" score?
  - completeness_status = "complete" iff all required artifacts present. Optional artifacts do not affect score.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST index all artifact files in a feature directory and compute deterministic content_hash_sha256 for each
- **FR-002**: System MUST support 6 artifact classes (input, workflow, output, evidence, policy, runtime) with stable, extensible encoding
- **FR-003**: System MUST define expected-artifact manifests per mission type and mission step (Phase 0, 1, 2 for software-dev; extensible for other missions)
- **FR-004**: System MUST detect missing required artifacts and emit MissionDossierArtifactMissing events with reason codes (not_found, unreadable, invalid_format, not_produced_yet)
- **FR-005**: System MUST compute deterministic parity_hash_sha256 from all indexed artifacts' content hashes, such that identical artifact content always produces identical parity hash
- **FR-006**: System MUST emit 4 canonical dossier events to the sync pipeline: MissionDossierArtifactIndexed, MissionDossierArtifactMissing, MissionDossierSnapshotComputed, MissionDossierParityDriftDetected
- **FR-007**: System MUST expose dashboard API endpoints: `/api/dossier/overview`, `/api/dossier/artifacts`, `/api/dossier/artifacts/{artifact_key}`, `/api/dossier/snapshots/export`
- **FR-008**: System MUST support artifact filtering by class, wp_id, step_id with stable, repeatable ordering
- **FR-009**: System MUST never silently omit artifacts; all anomalies (missing, unreadable, invalid format) MUST be explicit in dossier events and API responses
- **FR-010**: Dossier projection MUST be deterministic—repeated scans of unchanged content produce identical snapshots and parity hashes
- **FR-011**: System MUST integrate with existing sync/events infrastructure (spec_kitty_events contracts, offline queue, WebSocket routing)

### Key Entities *(if data involved)*

- **Artifact**: Indexed unit with artifact_key, artifact_class, path, wp_id, step_id, content_hash_sha256, size_bytes, required_status, provenance references
- **ArtifactRef**: Stable, content-hashed reference to a single artifact
- **ProvenanceRef**: Tracks source (event_log, git, runtime, generated, manual) with actor_id, actor_type, captured_at
- **MissionDossier**: Collection of indexed artifacts + snapshot for a single mission run, with mission_slug, mission_run_id, feature_slug
- **MissionDossierSnapshot**: Point-in-time projection with parity_hash, artifact counts (required/optional × present/missing), completeness_status, timestamp
- **ExpectedArtifactManifest**: Registry of required/optional artifacts per mission type and step (e.g., "software-dev Phase 1 requires spec.md, plan.md, tasks.md, tasks/*.md")

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Local dashboard can retrieve and render complete artifact catalog (>30 artifacts tested) with full-text detail in under 500ms
- **SC-002**: Dossier projection is deterministic—running scan twice on unchanged content produces byte-for-byte identical parity_hash_sha256 and event payloads
- **SC-003**: All 4 canonical dossier event types (Indexed, Missing, Computed, ParityDrift) are emitted and consumable by offline queue (testable via mock SaaS webhook endpoint)
- **SC-004**: Missing required artifacts are always surfaced—zero silent omissions in 100 test missions across 5 mission types
- **SC-005**: API response times for artifact filtering queries (e.g., "all output artifacts") scale linearly with artifact count, supporting up to 1000 artifacts per feature
- **SC-006**: Parity hash computation is reproducible—identical artifact content on different machines/timezones produces identical hash
- **SC-007**: Artifact content hashing is robust—UTF-8 encoding issues detected and handled consistently, not causing hash mismatches

### Acceptance Criteria

- ✅ Local dashboard/API code is deployed to spec-kitty 2.x
- ✅ Expected artifact manifests defined for software-dev mission (Phase 0, 1, 2)
- ✅ Dossier events schema added to spec-kitty-events contracts
- ✅ Dashboard integration tests cover all 4 endpoint categories (overview, list, detail, export)
- ✅ Event emission tests verify deterministic ordering and hash reproducibility
- ✅ Missing artifact detection tested across 5+ mission edge cases
- ✅ SaaS webhook simulator (mock) successfully parses all emitted events

## Assumptions

1. **Expected artifact manifests are defined in mission templates**, not hard-coded. This allows future mission types to declare their own requirements without code changes.
2. **Content hashing uses SHA256** (standard, widely available, sufficient for collision resistance in this context).
3. **Parity hash is order-independent**: hash is computed from sorted list of artifact hashes, ensuring determinism regardless of scan iteration order.
4. **Sync/events infrastructure (spec_kitty_events, offline queue) is already stable** and compatible with new event types.
5. **Artifact provenance tracking is optional**: ProvenanceRef[] can be empty; events do not fail if provenance data is unavailable.
6. **SaaS is responsible for storing/displaying snapshots**, not spec-kitty local. Local role is indexing and emitting; SaaS role is archiving and rendering.
7. **Artifact content remains stable once scanned**: we assume files are not being written to during a scan (user responsibility to avoid concurrent edits).

## Out of Scope (Non-Goals)

1. Building SaaS UI or dashboard UI (only API layer)
2. Implementing event replay/theater workflows (emit-only this phase)
3. Replacing git/filesystem as source of truth for artifacts
4. Full-text search indexing (basic filtering only)
5. Real-time artifact sync (batch scan-based)
6. Artifact versioning or delta tracking (snapshot-based, not incremental)

## Implementation Notes

### Phase 1: Core Projection & Events (WP01-WP05)

- **WP01**: ArtifactRef model + deterministic hashing + Dossier data model
- **WP02**: Expected artifact manifest system + software-dev Phase 0/1/2 registries
- **WP03**: Indexing + missing artifact detection
- **WP04**: Dossier event types + emit integration with spec_kitty_events + offline routing
- **WP05**: Deterministic snapshot computation + parity hash algorithm

### Phase 2: API & Dashboard Integration (WP06-WP08)

- **WP06**: Dashboard API endpoints (overview, list, detail, export)
- **WP07**: Dashboard UI integration (dossier panel + filters)
- **WP08**: Event routing to SaaS webhook simulator (test harness)

### Phase 3: Testing & Hardening (WP09-WP10)

- **WP09**: Deterministic test suite (hash reproducibility, ordering, missing detection)
- **WP10**: Integration tests + edge cases (encoding, unreadable, large artifacts)

## Related Artifacts

- **PRD**: /Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty-planning/product-ideas/mission-collaboration-platform-ddd/prd-mission-dossier-dashboard-parity-v1.md
- **Existing Dashboard**: src/specify_cli/dashboard/ (scanner.py, api.py, server.py)
- **Existing Sync**: src/specify_cli/sync/ (events.py, emitter.py, OfflineQueue)
- **Spec-Kitty-Events Contracts**: spec-kitty-events/contracts/events.schema.json (to be extended)

## References & External Context

- Dossier event payloads: 4 new JSON Schema definitions (MissionDossierArtifactIndexed, MissionDossierArtifactMissing, MissionDossierSnapshotComputed, MissionDossierParityDriftDetected) with envelope guidance
- Expected artifact manifest format: YAML per mission (e.g., src/specify_cli/missions/software-dev/expected-artifacts.yaml)
- Dashboard parity export: JSON snapshot exportable for SaaS import (format TBD, likely aligned with MissionDossierSnapshotComputed envelope)
