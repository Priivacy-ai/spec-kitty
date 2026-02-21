---
work_package_id: WP05
title: Snapshot Computation & Parity Hash
lane: "for_review"
dependencies:
- WP01
- WP03
base_branch: 042-local-mission-dossier-authority-parity-export-WP05-merge-base
base_commit: 7b9158fad4f122121329f384f8e51bad82f70814
created_at: '2026-02-21T15:56:20.857584+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
feature_slug: 042-local-mission-dossier-authority-parity-export
shell_pid: "93614"
agent: "coordinator"
---

# WP05: Snapshot Computation & Parity Hash

**Objective**: Compute deterministic snapshots from MissionDossier state and compute reproducible parity hashes. Snapshots are point-in-time projections of dossier completeness and artifact inventory; parity hashes enable drift detection and SaaS validation.

**Priority**: P1 (Core for determinism requirement)

**Scope**:
- Deterministic snapshot computation (artifact aggregation, counting)
- Parity hash algorithm (sorted artifact hashes, combined hash)
- Snapshot persistence (JSON storage)
- Snapshot reproducibility testing
- Snapshot equality comparison

**Test Criteria**:
- Snapshot computes without errors for 30+ artifacts
- Parity hash deterministic (same content → same hash, multiple runs)
- Snapshot reproducible on different machines/timezones
- Completeness status correctly reflects required artifacts

---

## Context

WP01-WP04 build up to WP05: indexing produces MissionDossier; WP05 projects that dossier into a deterministic snapshot. The snapshot is the canonical record of dossier state at a point in time—it includes artifact counts, completeness status, and parity hash. The parity hash is computed from sorted artifact content hashes, ensuring order-independence and reproducibility across machines.

**Key Requirements**:
- **FR-005**: System MUST compute deterministic parity_hash_sha256 from all indexed artifacts' hashes
- **FR-010**: Dossier projection MUST be deterministic
- **SC-002**: Repeated scans of unchanged content produce identical snapshots
- **SC-006**: Parity hash reproducible across machines/timezones

---

## Detailed Guidance

### T023: Deterministic Snapshot Computation

**What**: Create algorithm to compute snapshot from MissionDossier.

**How**:
1. Create store.py in `src/specify_cli/dossier/store.py`
2. Define compute_snapshot() function:
   ```python
   def compute_snapshot(dossier: MissionDossier) -> MissionDossierSnapshot:
       """Deterministically compute snapshot from dossier.

       Algorithm:
       1. Sort artifacts by artifact_key (deterministic ordering)
       2. Count artifacts by status (required/optional, present/missing)
       3. Compute completeness status (all required present? → complete)
       4. Compute parity hash (see T024)
       5. Return snapshot object
       """
       # 1. Sort artifacts
       sorted_artifacts = sorted(dossier.artifacts, key=lambda a: a.artifact_key)

       # 2. Count artifacts
       required_artifacts = [a for a in sorted_artifacts if a.required_status == 'required']
       optional_artifacts = [a for a in sorted_artifacts if a.required_status == 'optional']
       required_present = sum(1 for a in required_artifacts if a.is_present)
       required_missing = len(required_artifacts) - required_present
       optional_present = sum(1 for a in optional_artifacts if a.is_present)

       # 3. Completeness status
       if not dossier.manifest:
           completeness_status = 'unknown'
       else:
           completeness_status = 'complete' if required_missing == 0 else 'incomplete'

       # 4. Parity hash (handled in T024)
       parity_hash = compute_parity_hash_from_dossier(dossier)

       # 5. Create snapshot
       return MissionDossierSnapshot(
           feature_slug=dossier.feature_slug,
           snapshot_id=str(uuid.uuid4()),
           total_artifacts=len(sorted_artifacts),
           required_artifacts=len(required_artifacts),
           required_present=required_present,
           required_missing=required_missing,
           optional_artifacts=len(optional_artifacts),
           optional_present=optional_present,
           completeness_status=completeness_status,
           parity_hash_sha256=parity_hash,
           parity_hash_components=get_parity_hash_components(dossier),
           artifact_summaries=[
               {
                   'artifact_key': a.artifact_key,
                   'artifact_class': a.artifact_class,
                   'wp_id': a.wp_id,
                   'step_id': a.step_id,
                   'is_present': a.is_present,
                   'error_reason': a.error_reason,
               }
               for a in sorted_artifacts
           ],
           computed_at=datetime.utcnow(),
       )
   ```
3. Ensure all counting logic deterministic (no randomness, no timestamps in computation)
4. Completeness status must match dossier.completeness_status

**Test Requirements**:
- Snapshot computes without errors
- Artifact counts accurate
- Completeness status correct
- Artifact summaries complete (all fields present)

---

### T024: Parity Hash Algorithm

**What**: Implement order-independent parity hash computation.

**How**:
1. Create compute_parity_hash_from_dossier() function:
   ```python
   def compute_parity_hash_from_dossier(dossier: MissionDossier) -> str:
       """Compute SHA256 parity hash from artifact content hashes.

       Algorithm (order-independent):
       1. Extract content_hash_sha256 from all artifacts (skip missing/unreadable)
       2. Sort hashes lexicographically
       3. Concatenate sorted hashes
       4. Compute SHA256 of concatenation
       5. Return hex string
       """
       # 1. Extract hashes from present artifacts only
       present_hashes = [
           a.content_hash_sha256
           for a in dossier.artifacts
           if a.is_present and a.content_hash_sha256
       ]

       # 2. Sort lexicographically
       sorted_hashes = sorted(present_hashes)

       # 3. Concatenate
       combined = "".join(sorted_hashes)

       # 4. Hash
       parity_hash = hashlib.sha256(combined.encode()).hexdigest()

       return parity_hash

   def get_parity_hash_components(dossier: MissionDossier) -> List[str]:
       """Return sorted list of artifact hashes (for audit)."""
       present_hashes = [
           a.content_hash_sha256
           for a in dossier.artifacts
           if a.is_present and a.content_hash_sha256
       ]
       return sorted(present_hashes)
   ```
2. Missing/unreadable artifacts excluded (hash only present artifacts)
3. Duplicate artifact hashes included (intentional, not deduplicated)
4. Order-independence validated by tests

**Order-Independence Proof**:
- Sorting before concatenation ensures artifact scan order irrelevant
- Same content, any scan order → same sorted hashes → same parity hash
- SC-006 validates this across machines/timezones

**Test Requirements**:
- Same artifacts in different order → same parity hash
- Different artifacts → different parity hash
- Missing artifacts excluded (don't contribute to hash)
- Duplicate hashes included in parity (if two artifacts identical content)

---

### T025: Snapshot Persistence

**What**: Store snapshot to JSON file for later retrieval.

**How**:
1. Create persistence functions:
   ```python
   def save_snapshot(snapshot: MissionDossierSnapshot, feature_dir: Path) -> None:
       """Persist snapshot to JSON.

       File: {feature_dir}/.kittify/dossiers/{feature_slug}/snapshot-latest.json
       """
       dossier_dir = feature_dir / '.kittify' / 'dossiers' / snapshot.feature_slug
       dossier_dir.mkdir(parents=True, exist_ok=True)

       snapshot_file = dossier_dir / 'snapshot-latest.json'
       with open(snapshot_file, 'w') as f:
           json.dump(snapshot.dict(), f, indent=2, default=str)

   def load_snapshot(feature_dir: Path, feature_slug: str) -> Optional[MissionDossierSnapshot]:
       """Load snapshot from JSON.

       Returns: MissionDossierSnapshot or None if not found
       """
       snapshot_file = feature_dir / '.kittify' / 'dossiers' / feature_slug / 'snapshot-latest.json'
       if not snapshot_file.exists():
           return None

       with open(snapshot_file) as f:
           data = json.load(f)
       return MissionDossierSnapshot(**data)

   def get_latest_snapshot(feature_dir: Path, feature_slug: str) -> Optional[MissionDossierSnapshot]:
       """Get most recent snapshot (convenience alias)."""
       return load_snapshot(feature_dir, feature_slug)
   ```
2. Snapshot file location: `.kittify/dossiers/{feature_slug}/snapshot-latest.json`
3. Use JSON (not JSONL) for snapshot (single object, not log)
4. Store full snapshot object (all fields)
5. Include computed_at timestamp (immutable)

**File Format Example**:
```json
{
  "feature_slug": "042-local-mission-dossier",
  "snapshot_id": "abc123...",
  "total_artifacts": 15,
  "required_artifacts": 10,
  "required_present": 10,
  "required_missing": 0,
  "optional_artifacts": 5,
  "optional_present": 3,
  "completeness_status": "complete",
  "parity_hash_sha256": "def456ghi789...",
  "parity_hash_components": [...],
  "artifact_summaries": [...],
  "computed_at": "2026-02-21T10:00:00Z"
}
```

**Test Requirements**:
- Snapshot saves to correct file path
- Snapshot loads from JSON without errors
- Round-trip (save, load) preserves all fields
- Missing file returns None (no exception)

---

### T026: Snapshot Validation (Reproducibility)

**What**: Validate that snapshots are reproducible (same content → same hash).

**How**:
1. Create validate_snapshot_reproducibility() test function:
   ```python
   def test_snapshot_reproducibility():
       """Verify same content produces identical snapshot."""
       # Create dossier with fixed artifacts
       feature_dir = create_test_feature_with_artifacts()

       # Scan 1
       dossier1 = indexer.index_feature(feature_dir, mission_type='software-dev')
       snapshot1 = compute_snapshot(dossier1)

       # Scan 2 (same content)
       dossier2 = indexer.index_feature(feature_dir, mission_type='software-dev')
       snapshot2 = compute_snapshot(dossier2)

       # Verify hashes identical
       assert snapshot1.parity_hash_sha256 == snapshot2.parity_hash_sha256
       assert snapshot1.completeness_status == snapshot2.completeness_status
       assert snapshot1.total_artifacts == snapshot2.total_artifacts
   ```
2. Test multiple runs on same content
3. Test on different artifact orderings
4. Validate SC-002 success criterion

**Test Requirements**:
- Same content, 10 scans → same parity hash
- Different orderings → same parity hash
- Completeness status reproducible
- Artifact counts reproducible

---

### T027: Snapshot Equality Comparison

**What**: Implement equality check for parity hashes.

**How**:
1. Add comparison method to MissionDossierSnapshot:
   ```python
   class MissionDossierSnapshot(BaseModel):
       ...

       def has_parity_diff(self, other: "MissionDossierSnapshot") -> bool:
           """Check if parity hashes differ."""
           return self.parity_hash_sha256 != other.parity_hash_sha256

       def __eq__(self, other) -> bool:
           """Equality: parity hash + completeness status."""
           if not isinstance(other, MissionDossierSnapshot):
               return False
           return (
               self.parity_hash_sha256 == other.parity_hash_sha256
               and self.completeness_status == other.completeness_status
           )

       def __hash__(self) -> int:
           """Hash based on parity_hash (for set/dict usage)."""
           return hash(self.parity_hash_sha256)
   ```
2. Parity hash is source of truth (not snapshot_id, computed_at)
3. Equality ignores envelope metadata (event_id, timestamp)
4. Support comparison with other snapshots

**Test Requirements**:
- Same parity hash → equal snapshots
- Different parity hash → unequal
- Snapshot equality ignore timestamp/id differences

---

## Definition of Done

- [ ] compute_snapshot() function implemented (deterministic)
- [ ] Parity hash algorithm implemented (order-independent)
- [ ] snapshot_latest.json persisted to .kittify/dossiers/{feature_slug}/
- [ ] Snapshot loads from JSON without errors
- [ ] Reproducibility validated (same content → same hash)
- [ ] Equality comparison working (parity hash as source of truth)
- [ ] All counting logic deterministic (no randomness, no volatile timestamps)
- [ ] 30+ artifact test suite passing
- [ ] SC-002, SC-006 success criteria validated
- [ ] FR-005, FR-010 requirements satisfied

---

## Risks & Mitigations

**Risk 1**: Artifact ordering affects parity hash
- **Mitigation**: Sort before concatenation (order-independent algorithm)

**Risk 2**: Timestamps make snapshots non-reproducible
- **Mitigation**: Use UTC timezone, don't include timestamps in parity computation

**Risk 3**: Missing/unreadable artifacts counted incorrectly
- **Mitigation**: Test with various missing scenarios (T026)

**Risk 4**: Large dossiers (1000s of artifacts) slow down snapshot
- **Mitigation**: SC-005 validates performance (linear scaling)

---

## Reviewer Guidance

When reviewing WP05:
1. Verify compute_snapshot() sorts artifacts before hashing (order-independence)
2. Check parity hash computed from sorted hashes (not artifact order)
3. Confirm missing/unreadable artifacts excluded from parity (only present)
4. Verify snapshot persisted to `.kittify/dossiers/{feature_slug}/snapshot-latest.json`
5. Validate snapshot reproducibility (same content, multiple runs → same hash)
6. Check completeness status logic (required_missing == 0 → complete)
7. Confirm equality based on parity hash (not snapshot_id, timestamp)
8. Test with 30+ artifacts, verify no performance issues
9. Validate SC-002, SC-006 requirements satisfied

---

## Implementation Notes

- **Storage**: store.py (snapshot persistence, parity hash)
- **Dependencies**: WP01 (hasher), WP03 (MissionDossier/indexing output)
- **Estimated Lines**: ~350 (store.py + tests)
- **Integration Point**: WP06 (API) will return snapshots; WP08 (drift detection) compares hashes
- **Performance**: Snapshot computation <1s for 30 artifacts (SC-001)

## Activity Log

- 2026-02-21T15:56:21Z – coordinator – shell_pid=93614 – lane=doing – Assigned agent via workflow command
- 2026-02-21T15:59:03Z – coordinator – shell_pid=93614 – lane=for_review – Ready for review: Snapshot computation and parity hash implemented with 28 comprehensive tests covering deterministic computation, order-independent parity hash, persistence, reproducibility validation, and equality comparison. All 5 subtasks (T023-T027) completed.
