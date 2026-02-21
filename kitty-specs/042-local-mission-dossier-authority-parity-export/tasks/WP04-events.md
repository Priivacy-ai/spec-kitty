---
work_package_id: WP04
title: Dossier Event Types & Emission
lane: planned
dependencies: []
subtasks:
- T018
- T019
- T020
- T021
- T022
feature_slug: 042-local-mission-dossier-authority-parity-export
---

# WP04: Dossier Event Types & Emission

**Objective**: Define 4 canonical dossier event schemas and integrate emission with sync infrastructure (spec_kitty_events, OfflineQueue). Events are the bridge between local dossier system and SaaS backend, enabling parity validation and audit trails.

**Priority**: P1 (Required for SaaS integration)

**Scope**:
- Define 4 dossier event types (schemas, payloads)
- Add JSON Schema definitions to spec-kitty-events contracts
- Implement event emitters (async, OfflineQueue integration)
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

Feature 042 is designed to emit events that SaaS backend consumes for parity validation and dashboard display. Events are immutable, timestamped, and self-contained; they form the canonical record of dossier state. The sync infrastructure (spec_kitty_events, OfflineQueue) handles delivery.

**Key Requirements**:
- **FR-006**: System MUST support 4 canonical dossier event types
- **FR-011**: System MUST integrate with existing sync infrastructure
- **SC-003**: Dossier events are consumable by offline queue

**Sync Context**:
- spec_kitty_events: Central event schema registry
- OfflineQueue: Async, retry-safe event queueing
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

class MissionDossierArtifactIndexedEvent(BaseModel):
    """Event envelope."""
    event_type: str = "mission_dossier_artifact_indexed"
    payload: MissionDossierArtifactIndexedPayload
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: Optional[str] = None
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

class MissionDossierArtifactMissingEvent(BaseModel):
    """Anomaly event: required artifact missing."""
    event_type: str = "mission_dossier_artifact_missing"
    payload: MissionDossierArtifactMissingPayload
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: Optional[str] = None
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

class MissionDossierSnapshotComputedEvent(BaseModel):
    """Event: snapshot computed after indexing."""
    event_type: str = "mission_dossier_snapshot_computed"
    payload: MissionDossierSnapshotComputedPayload
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: Optional[str] = None
```

**Event 4: MissionDossierParityDriftDetected**
```python
class MissionDossierParityDriftDetectedPayload(BaseModel):
    """Emitted when local snapshot differs from baseline."""
    feature_slug: str
    local_parity_hash: str
    baseline_parity_hash: str
    missing_in_local: List[str] = []  # artifact_keys
    missing_in_baseline: List[str] = []  # artifact_keys
    severity: str  # "info" | "warning" | "error"

class MissionDossierParityDriftDetectedEvent(BaseModel):
    """Anomaly event: parity hash differs from baseline."""
    event_type: str = "mission_dossier_parity_drift_detected"
    payload: MissionDossierParityDriftDetectedPayload
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: Optional[str] = None
```

3. Add validation rules to each payload model
4. Document event semantics (when emitted, purpose, audience)

**Test Requirements**:
- Each event model validates with correct data
- Event model rejects invalid data (missing required fields)
- event_id auto-generated (UUID)
- timestamp auto-populated (UTC)

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

**What**: Implement async event emission integrated with OfflineQueue.

**How**:
1. Create emitter functions in events.py:
   ```python
   async def emit_artifact_indexed(
       feature_slug: str,
       artifact: ArtifactRef,
       actor: Optional[str] = None,
   ) -> MissionDossierArtifactIndexedEvent:
       """Emit MissionDossierArtifactIndexed event."""
       event = MissionDossierArtifactIndexedEvent(
           payload=MissionDossierArtifactIndexedPayload(
               feature_slug=feature_slug,
               artifact_key=artifact.artifact_key,
               artifact_class=artifact.artifact_class,
               relative_path=artifact.relative_path,
               content_hash_sha256=artifact.content_hash_sha256,
               size_bytes=artifact.size_bytes,
               wp_id=artifact.wp_id,
               step_id=artifact.step_id,
               required_status=artifact.required_status,
           ),
           actor=actor,
       )
       await OfflineQueue.emit(event)
       return event

   async def emit_artifact_missing(
       feature_slug: str,
       artifact_key: str,
       artifact_class: str,
       expected_path_pattern: str,
       reason_code: str,
       reason_detail: Optional[str] = None,
       blocking: bool = True,
       actor: Optional[str] = None,
   ) -> MissionDossierArtifactMissingEvent:
       """Emit MissionDossierArtifactMissing event (only if required)."""
       if not blocking:
           return None  # Don't emit for optional artifacts
       event = MissionDossierArtifactMissingEvent(
           payload=MissionDossierArtifactMissingPayload(...),
           actor=actor,
       )
       await OfflineQueue.emit(event)
       return event

   async def emit_snapshot_computed(
       feature_slug: str,
       snapshot: MissionDossierSnapshot,
       actor: Optional[str] = None,
   ) -> MissionDossierSnapshotComputedEvent:
       """Emit MissionDossierSnapshotComputed event (always)."""
       event = MissionDossierSnapshotComputedEvent(
           payload=MissionDossierSnapshotComputedPayload(...),
           actor=actor,
       )
       await OfflineQueue.emit(event)
       return event

   async def emit_parity_drift_detected(
       feature_slug: str,
       local_parity_hash: str,
       baseline_parity_hash: str,
       missing_in_local: List[str] = None,
       missing_in_baseline: List[str] = None,
       severity: str = "warning",
       actor: Optional[str] = None,
   ) -> MissionDossierParityDriftDetectedEvent:
       """Emit MissionDossierParityDriftDetected event (only if drift)."""
       event = MissionDossierParityDriftDetectedEvent(
           payload=MissionDossierParityDriftDetectedPayload(...),
           actor=actor,
       )
       await OfflineQueue.emit(event)
       return event
   ```
2. Integrate with OfflineQueue (import from sync infrastructure)
3. Handle async/await correctly
4. Return event for testing/verification

**Test Requirements**:
- Emitting artifact_indexed enqueues event
- Emitting artifact_missing enqueues only if blocking=True
- Emitting snapshot_computed always enqueues
- Emitting parity_drift enqueues only if drift
- Events accessible via OfflineQueue (for mock webhook testing)

---

### T021: Payload Validation

**What**: Ensure payloads are valid before emission.

**How**:
1. Leverage pydantic validation (automatic with BaseModel)
2. Add custom validation methods:
   ```python
   class MissionDossierArtifactIndexedPayload(BaseModel):
       ...

       @validator('content_hash_sha256')
       def validate_hash(cls, v):
           if not re.match(r'^[a-f0-9]{64}$', v):
               raise ValueError(f'Invalid SHA256 hash: {v}')
           return v

       @validator('artifact_class')
       def validate_class(cls, v):
           valid_classes = {'input', 'workflow', 'output', 'evidence', 'policy', 'runtime'}
           if v not in valid_classes:
               raise ValueError(f'Invalid artifact_class: {v}')
           return v

       @validator('required_status')
       def validate_status(cls, v):
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

**What**: Integrate events with spec_kitty_events offline queue and webhook routing.

**How**:
1. Ensure OfflineQueue integration:
   ```python
   from specify_cli.sync.events import OfflineQueue

   # In emitter functions:
   await OfflineQueue.emit(event)
   ```
2. Verify webhook routing configuration:
   - Events routed to SaaS webhook endpoint (or mock in tests)
   - Envelope metadata included (event_id, timestamp, actor)
   - Retry logic handled by OfflineQueue
3. Add error handling:
   ```python
   try:
       await OfflineQueue.emit(event)
   except Exception as e:
       logger.error(f"Failed to emit event: {e}")
       # Event is still stored locally (offline-capable)
   ```
4. Document webhook contract (payload format, retry semantics)

**Test Requirements**:
- Events enqueue to OfflineQueue
- Mock webhook receives events
- Envelope metadata included
- Offline mode works (no exception if SaaS unreachable)

---

## Definition of Done

- [ ] 4 event type models created (pydantic BaseModel)
- [ ] 4 JSON Schema files added to spec-kitty-events contracts
- [ ] 4 emitter functions implemented (async, OfflineQueue)
- [ ] Payload validation working (reject invalid data)
- [ ] Event routing integrated with sync infrastructure
- [ ] Conditional events emit only when conditions met (missing, drift)
- [ ] All events include envelope metadata (event_id, timestamp, actor)
- [ ] All 4 event types tested with valid/invalid payloads
- [ ] Mock webhook integration test passing
- [ ] FR-006, FR-011 requirements satisfied

---

## Risks & Mitigations

**Risk 1**: Event emission failure breaks dossier scan
- **Mitigation**: Wrap emission in try-catch, log errors, continue scan

**Risk 2**: Invalid payload emitted (corrupts SaaS)
- **Mitigation**: Pydantic validation (fail fast, reject before emit)

**Risk 3**: OfflineQueue integration breaks existing sync
- **Mitigation**: Extend existing infrastructure, don't modify core

**Risk 4**: Event schema version conflicts post-042
- **Mitigation**: Schema versioning deferred post-042 (current: v1 only)

---

## Reviewer Guidance

When reviewing WP04:
1. Verify 4 event types defined (pydantic models)
2. Check JSON schemas match pydantic models exactly
3. Confirm emitters async and use OfflineQueue
4. Validate payload validation working (reject invalid)
5. Check conditional events emit only when needed (missing only if required, drift only if diff)
6. Verify envelope metadata included (event_id, timestamp, actor)
7. Test mock webhook receives all 4 event types
8. Confirm offline mode works (no SaaS call during local scan)
9. Validate SC-003 requirement satisfied

---

## Implementation Notes

- **Storage**: events.py (models, emitters)
- **Dependencies**: pydantic, spec_kitty_events.OfflineQueue (existing)
- **Estimated Lines**: ~350 (events.py + JSON schemas + tests)
- **Integration Point**: WP05 (snapshot) and WP08 (drift detection) will emit events
- **Deferred**: Event replay/theater workflows (post-042)
