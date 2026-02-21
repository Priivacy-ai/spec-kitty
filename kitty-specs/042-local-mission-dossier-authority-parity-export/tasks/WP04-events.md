---
work_package_id: WP04
title: Dossier Event Types & Emission
lane: planned
dependencies:
- WP03
subtasks:
- T018
- T019
- T020
- T021
- T022
feature_slug: 042-local-mission-dossier-authority-parity-export
---

# WP04: Dossier Event Types & Emission

**Objective**: Define 4 canonical dossier event payloads and integrate emission with existing sync infrastructure (`specify_cli.sync.events` / `EventEmitter`). Events are the bridge between local dossier system and SaaS backend, enabling parity validation and audit trails.

**Priority**: P1 (Required for SaaS integration)

**Scope**:
- Define 4 dossier event types (schemas, payloads)
- Add JSON Schema definitions to spec-kitty-events contracts
- Implement event emitters using the existing sync emitter API (not direct queue writes)
- Pydantic payload validation
- Event routing and envelope metadata

**Event Types**:
1. MissionDossierArtifactIndexed (emitted per artifact)
2. MissionDossierArtifactMissing (emitted if required missing)
3. MissionDossierSnapshotComputed (emitted after scan)
4. MissionDossierParityDriftDetected (emitted if drift detected)

**Test Criteria**:
- All 4 event types emit with valid schemas
- Conditional events (missing, drift) emit only when conditions met
- Events enqueue to offline queue (no SaaS call)
- Payload validation works (reject invalid data)

---

## Context

Feature 042 is designed to emit events that SaaS backend consumes for parity validation and dashboard display. Events are immutable, timestamped, and self-contained; they form the canonical record of dossier state. The sync infrastructure (`EventEmitter` + queue routing) handles delivery.

**Key Requirements**:
- **FR-006**: System MUST support 4 canonical dossier event types
- **FR-011**: System MUST integrate with existing sync infrastructure
- **SC-003**: Dossier events are consumable by offline queue

**Sync Context**:
- spec_kitty_events: Central event schema registry
- EventEmitter: builds canonical envelopes and routes to queue/websocket
- OfflineQueue: persistence backend used by EventEmitter (not called directly by dossier code)
- Webhook routing: Events posted to SaaS endpoint (or mock in tests)

---

## Detailed Guidance

### T018: Define 4 Dossier Event Schemas

**What**: Define pydantic models for event payloads.

**How**:
1. Create events.py in `src/specify_cli/dossier/events.py`
2. Define 4 event payload models (from data-model.md):

**Event 1: MissionDossierArtifactIndexed**
```python
class MissionDossierArtifactIndexedPayload(BaseModel):
    """Emitted when artifact successfully indexed."""
    feature_slug: str
    artifact_key: str
    artifact_class: str
    relative_path: str
    content_hash_sha256: str
    size_bytes: int
    wp_id: Optional[str] = None
    step_id: Optional[str] = None
    required_status: str  # "required" | "optional"

# Note: Do not define a custom envelope model here.
# Envelope construction/validation is owned by specify_cli.sync.emitter.
```

**Event 2: MissionDossierArtifactMissing**
```python
class MissionDossierArtifactMissingPayload(BaseModel):
    """Emitted when required artifact missing or unreadable."""
    feature_slug: str
    artifact_key: str
    artifact_class: str
    expected_path_pattern: str
    reason_code: str  # "not_found" | "unreadable" | "invalid_format" | "deleted_after_scan"
    reason_detail: Optional[str] = None
    blocking: bool  # True if blocks completeness

# Note: Do not define a custom envelope model here.
```

**Event 3: MissionDossierSnapshotComputed**
```python
class ArtifactCountsPayload(BaseModel):
    total: int
    required: int
    required_present: int
    required_missing: int
    optional: int
    optional_present: int

class MissionDossierSnapshotComputedPayload(BaseModel):
    """Emitted after snapshot computed."""
    feature_slug: str
    parity_hash_sha256: str
    artifact_counts: ArtifactCountsPayload
    completeness_status: str  # "complete" | "incomplete" | "unknown"
    snapshot_id: str

# Note: Do not define a custom envelope model here.
```

**Event 4: MissionDossierParityDriftDetected**
```python
class MissionDossierParityDriftDetectedPayload(BaseModel):
    """Emitted when local snapshot differs from baseline."""
    feature_slug: str
    local_parity_hash: str
    baseline_parity_hash: str
    missing_in_local: List[str] = Field(default_factory=list)  # artifact_keys
    missing_in_baseline: List[str] = Field(default_factory=list)  # artifact_keys
    severity: str  # "info" | "warning" | "error"
# Note: Do not define a custom envelope model here.
```

3. Add validation rules to each payload model (payload-only; envelope validation comes from sync emitter)
4. Document event semantics (when emitted, purpose, audience)

**Test Requirements**:
- Each event model validates with correct data
- Event model rejects invalid data (missing required fields)
- payload validators reject invalid values before emission

---

### T019: Add Schemas to spec-kitty-events Contracts

**What**: Register dossier event schemas in spec-kitty-events package.

**How**:
1. Update spec-kitty-events repository (external package, may be in separate repo)
2. Add JSON Schema files for each event type:
   - `src/spec_kitty_events/schemas/mission_dossier_artifact_indexed.schema.json`
   - `src/spec_kitty_events/schemas/mission_dossier_artifact_missing.schema.json`
   - `src/spec_kitty_events/schemas/mission_dossier_snapshot_computed.schema.json`
   - `src/spec_kitty_events/schemas/mission_dossier_parity_drift_detected.schema.json`
3. Each schema should match pydantic model structure
4. Register schemas in event registry (if spec-kitty-events has registry)
5. Document event contract in spec-kitty-events README

**Schema Example** (mission_dossier_artifact_indexed.schema.json):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MissionDossierArtifactIndexed",
  "type": "object",
  "properties": {
    "event_type": {"const": "mission_dossier_artifact_indexed"},
    "payload": {
      "type": "object",
      "properties": {
        "feature_slug": {"type": "string"},
        "artifact_key": {"type": "string"},
        "artifact_class": {"type": "string"},
        "relative_path": {"type": "string"},
        "content_hash_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "size_bytes": {"type": "integer", "minimum": 0},
        "wp_id": {"type": ["string", "null"]},
        "step_id": {"type": ["string", "null"]},
        "required_status": {"enum": ["required", "optional"]}
      },
      "required": ["feature_slug", "artifact_key", "artifact_class", "relative_path", "content_hash_sha256", "size_bytes", "required_status"]
    }
  },
  "required": ["event_type", "payload"]
}
```

**Test Requirements**:
- Schemas validate with valid payloads
- Schemas reject invalid payloads
- All 4 schemas present and discoverable

---

### T020: Event Emitters

**What**: Implement dossier emission helpers that use the existing sync emitter path (canonical envelope + queue/websocket routing).

**How**:
1. In `src/specify_cli/dossier/events.py`, create helper functions that build payload models and forward to public sync emitter helpers.
2. Add public sync helpers in `src/specify_cli/sync/events.py` (for example `emit_mission_dossier_artifact_indexed`, `emit_mission_dossier_artifact_missing`, etc.) so dossier code does not call private emitter methods directly.
   ```python
   from specify_cli.sync.events import emit_mission_dossier_artifact_indexed

   def emit_artifact_indexed(feature_slug: str, artifact: ArtifactRef) -> dict[str, Any] | None:
       payload = MissionDossierArtifactIndexedPayload(
           feature_slug=feature_slug,
           artifact_key=artifact.artifact_key,
           artifact_class=artifact.artifact_class,
           relative_path=artifact.relative_path,
           content_hash_sha256=artifact.content_hash_sha256,
           size_bytes=artifact.size_bytes,
           wp_id=artifact.wp_id,
           step_id=artifact.step_id,
           required_status=artifact.required_status,
       ).model_dump()
       return emit_mission_dossier_artifact_indexed(feature_slug=feature_slug, payload=payload)
   ```
3. Repeat for:
   - `MissionDossierArtifactMissing` (emit only if blocking/required)
   - `MissionDossierSnapshotComputed` (always emit after snapshot build)
   - `MissionDossierParityDriftDetected` (emit only on accepted-baseline drift)
4. Keep emitter helpers synchronous (current sync API is synchronous, non-blocking).
5. Do not call `OfflineQueue` directly from dossier code; route via sync emitter API.

**Test Requirements**:
- Emitting artifact_indexed routes through emitter and returns event dict (or None on validation failure)
- Emitting artifact_missing skips optional/non-blocking artifacts
- Emitting snapshot_computed always emits
- Emitting parity_drift emits only when drift is detected
- Emitted envelope includes canonical metadata (event_id, timestamp, node_id, lamport_clock)

---

### T021: Payload Validation

**What**: Ensure payloads are valid before emission.

**How**:
1. Leverage pydantic validation (automatic with BaseModel)
2. Add custom validation methods:
   ```python
   from pydantic import field_validator

   class MissionDossierArtifactIndexedPayload(BaseModel):
       ...

       @field_validator('content_hash_sha256')
       @classmethod
       def validate_hash(cls, v: str) -> str:
           if not re.match(r'^[a-f0-9]{64}$', v):
               raise ValueError(f'Invalid SHA256 hash: {v}')
           return v

       @field_validator('artifact_class')
       @classmethod
       def validate_class(cls, v: str) -> str:
           valid_classes = {'input', 'workflow', 'output', 'evidence', 'policy', 'runtime'}
           if v not in valid_classes:
               raise ValueError(f'Invalid artifact_class: {v}')
           return v

       @field_validator('required_status')
       @classmethod
       def validate_status(cls, v: str) -> str:
           if v not in {'required', 'optional'}:
               raise ValueError(f'Invalid required_status: {v}')
           return v
   ```
3. Fail fast on validation error (raise, don't emit)
4. Log validation errors

**Test Requirements**:
- Valid payload emits
- Invalid hash rejected
- Invalid artifact_class rejected
- Invalid required_status rejected
- Validation error raised (not silent)

---

### T022: Event Routing to Sync Infrastructure

**What**: Integrate events with `specify_cli.sync.events` so routing follows the existing emitter → queue/websocket pipeline.

**How**:
1. Ensure sync emitter integration:
   ```python
   from specify_cli.sync.events import emit_mission_dossier_artifact_indexed

   # In emitter functions:
   event = emit_mission_dossier_artifact_indexed(feature_slug=feature_slug, payload=payload)
   ```
2. Verify webhook routing configuration:
   - Events routed to SaaS webhook endpoint (or mock in tests)
   - Envelope metadata included (event_id, timestamp, node_id, lamport_clock)
   - Retry logic handled by EventEmitter routing + OfflineQueue backend
3. Add error handling:
   ```python
   try:
       event = emit_mission_dossier_artifact_indexed(...)
   except Exception as e:
       logger.error(f"Failed to emit event: {e}")
       # Scan continues; emitter is non-blocking and queue-backed
   ```
4. Document webhook contract (payload format, retry semantics)

**Test Requirements**:
- Events route through EventEmitter and are persisted to queue when offline
- Mock webhook receives events
- Envelope metadata included
- Offline mode works (no exception if SaaS unreachable)

---

## Definition of Done

- [ ] 4 event type models created (pydantic BaseModel)
- [ ] 4 JSON Schema files added to spec-kitty-events contracts
- [ ] 4 emitter functions implemented (sync, EventEmitter-backed)
- [ ] Payload validation working (reject invalid data)
- [ ] Event routing integrated with sync infrastructure
- [ ] Conditional events emit only when conditions met (missing, drift)
- [ ] All events include canonical envelope metadata (event_id, timestamp, node_id, lamport_clock)
- [ ] All 4 event types tested with valid/invalid payloads
- [ ] Mock webhook integration test passing
- [ ] FR-006, FR-011 requirements satisfied

---

## Risks & Mitigations

**Risk 1**: Event emission failure breaks dossier scan
- **Mitigation**: Wrap emission in try-catch, log errors, continue scan

**Risk 2**: Invalid payload emitted (corrupts SaaS)
- **Mitigation**: Pydantic validation (fail fast, reject before emit)

**Risk 3**: Bypassing EventEmitter causes envelope/schema drift
- **Mitigation**: Reuse existing EventEmitter path; avoid direct queue calls from dossier module

**Risk 4**: Event schema version conflicts post-042
- **Mitigation**: Schema versioning deferred post-042 (current: v1 only)

---

## Reviewer Guidance

When reviewing WP04:
1. Verify 4 event types defined (pydantic models)
2. Check JSON schemas match pydantic models exactly
3. Confirm emitters route via public `specify_cli.sync.events` helpers (no direct queue calls)
4. Validate payload validation working (reject invalid)
5. Check conditional events emit only when needed (missing only if required, drift only if diff)
6. Verify envelope metadata included (event_id, timestamp, node_id, lamport_clock)
7. Test mock webhook receives all 4 event types
8. Confirm offline mode works (no SaaS call during local scan)
9. Validate SC-003 requirement satisfied

---

## Implementation Notes

- **Storage**: events.py (models, emitters)
- **Dependencies**: pydantic, specify_cli.sync.events / EventEmitter (existing)
- **Estimated Lines**: ~350 (events.py + emitter wiring + tests)
- **Integration Point**: WP05 (snapshot) and WP08 (drift detection) will emit events
- **Deferred**: Event replay/theater workflows (post-042)
