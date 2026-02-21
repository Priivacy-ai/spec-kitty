---
work_package_id: WP08
title: Local Parity-Drift Detector
lane: "done"
dependencies:
- WP04
- WP05
base_branch: 042-local-mission-dossier-authority-parity-export-WP08-merge-base
base_commit: 1bf5196379830703d153f67da65abff9469ed59d
created_at: '2026-02-21T15:59:47.689895+00:00'
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
feature_slug: 042-local-mission-dossier-authority-parity-export
shell_pid: "99003"
agent: "coordinator"
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# WP08: Local Parity-Drift Detector

**Objective**: Implement local baseline management and parity drift detection. The system compares current snapshot parity hash against locally cached baseline to detect unintended content changes. Operates offline (no SaaS call). Baseline namespacing prevents false positives from branch switches, manifest updates, multi-user/machine scenarios.

**Priority**: P1 (Core parity feature, offline-capable)

**Scope**:
- Baseline key computation (project, node, feature, branch, mission, manifest)
- Baseline persistence (JSON file)
- Baseline acceptance logic (key match validation)
- Drift detection (hash comparison)
- ParityDriftDetected event emission
- Baseline update logic

**Test Criteria**:
- Baseline computes and persists without errors
- Acceptance validates key match
- Drift detection identifies hash changes
- False positives prevented (branch switch doesn't trigger drift)
- Event emitted only on true drift

---

## Context

After WP05 computes snapshots and WP06 exposes them via API, WP08 closes the parity loop: it maintains locally cached baselines and compares current snapshots against them to detect drift. The design is robust (fully namespaced baseline key) to prevent false positives in multi-feature, multi-branch, multi-user scenarios.

**Key Requirements**:
- **FR-012**: Local runtime MUST own parity-drift detection and operate offline
- **Decision 2** (plan.md): Fully namespaced baseline (project, node, feature, branch, mission, manifest version)

**Baseline Purpose**:
- Detect unintended content changes (drift)
- Work offline (no SaaS call)
- Prevent false positives (branch switches, manifest updates)
- Support multi-feature workflows

---

## Detailed Guidance

### T040: Baseline Key Computation

**What**: Create identity tuple (baseline key) that uniquely identifies baseline scope.

**How**:
1. Create drift_detector.py in `src/specify_cli/dossier/drift_detector.py`
2. Define BaselineKey dataclass:
   ```python
   from dataclasses import dataclass
   from typing import Optional
   import hashlib
   import json

   @dataclass
   class BaselineKey:
       """Unique identifier for baseline scope (prevent false positives)."""
       project_uuid: str  # From sync/project_identity.py
       node_id: str  # From sync/project_identity.py (machine ID)
       feature_slug: str  # e.g., "042-local-mission-dossier"
       target_branch: str  # e.g., "main", "2.x"
       mission_key: str  # e.g., "software-dev"
       manifest_version: str  # e.g., "1"

       def to_dict(self) -> dict:
           return {
               'project_uuid': self.project_uuid,
               'node_id': self.node_id,
               'feature_slug': self.feature_slug,
               'target_branch': self.target_branch,
               'mission_key': self.mission_key,
               'manifest_version': self.manifest_version,
           }

       def compute_hash(self) -> str:
           """Compute SHA256 hash of baseline key (for file-safe comparison)."""
           data = json.dumps(self.to_dict(), sort_keys=True)
           return hashlib.sha256(data.encode()).hexdigest()
   ```
3. Create compute_baseline_key() function:
   ```python
   def compute_baseline_key(
       feature_slug: str,
       target_branch: str,
       mission_key: str,
       manifest_version: str,
       project_identity: ProjectIdentity,  # From sync/project_identity.py
   ) -> BaselineKey:
       """Compute baseline key from current context."""
       return BaselineKey(
           project_uuid=project_identity.project_uuid,
           node_id=project_identity.node_id,
           feature_slug=feature_slug,
           target_branch=target_branch,
           mission_key=mission_key,
           manifest_version=manifest_version,
       )
   ```
4. Key components (rationale):
   - **project_uuid**: Different projects → different baseline (no collision)
   - **node_id**: Different machines/users in same project → different baseline (multi-user safe)
   - **feature_slug**: Different features → different baseline (multi-feature safe)
   - **target_branch**: Different branches → different baseline (branch switches safe)
   - **mission_key**: Different mission types → different baseline
   - **manifest_version**: Manifest updates → different baseline (prevents false drift)

**Test Requirements**:
- compute_baseline_key() produces valid BaselineKey
- to_dict() includes all 6 components
- compute_hash() produces 64-char SHA256 hash
- Same inputs → same hash (deterministic)
- Different inputs → different hash

---

### T041: Baseline Persistence

**What**: Store and load baseline key + parity hash to/from JSON file.

**How**:
1. Define BaselineSnapshot dataclass:
   ```python
   @dataclass
   class BaselineSnapshot:
       """Cached baseline with metadata."""
       baseline_key: BaselineKey
       baseline_key_hash: str  # SHA256 of baseline_key
       parity_hash_sha256: str  # Snapshot parity hash at baseline capture
       captured_at: datetime
       captured_by: str  # node_id that captured this baseline

       def to_dict(self) -> dict:
           return {
               'baseline_key': self.baseline_key.to_dict(),
               'baseline_key_hash': self.baseline_key_hash,
               'parity_hash_sha256': self.parity_hash_sha256,
               'captured_at': self.captured_at.isoformat(),
               'captured_by': self.captured_by,
           }

       @staticmethod
       def from_dict(data: dict) -> "BaselineSnapshot":
           return BaselineSnapshot(
               baseline_key=BaselineKey(**data['baseline_key']),
               baseline_key_hash=data['baseline_key_hash'],
               parity_hash_sha256=data['parity_hash_sha256'],
               captured_at=datetime.fromisoformat(data['captured_at']),
               captured_by=data['captured_by'],
           )
   ```
2. Create save_baseline() function:
   ```python
   def save_baseline(feature_slug: str, baseline: BaselineSnapshot, repo_root: Path) -> None:
       """Persist baseline to JSON.

       File: {repo_root}/.kittify/dossiers/{feature_slug}/parity-baseline.json
       """
       baseline_dir = repo_root / '.kittify' / 'dossiers' / feature_slug
       baseline_dir.mkdir(parents=True, exist_ok=True)

       baseline_file = baseline_dir / 'parity-baseline.json'
       with open(baseline_file, 'w') as f:
           json.dump(baseline.to_dict(), f, indent=2)
   ```
3. Create load_baseline() function:
   ```python
   def load_baseline(feature_slug: str, repo_root: Path) -> Optional[BaselineSnapshot]:
       """Load baseline from JSON.

       Returns: BaselineSnapshot or None if not found
       """
       baseline_file = repo_root / '.kittify' / 'dossiers' / feature_slug / 'parity-baseline.json'
       if not baseline_file.exists():
           return None

       with open(baseline_file) as f:
           data = json.load(f)
       return BaselineSnapshot.from_dict(data)
   ```
4. File location: `.kittify/dossiers/{feature_slug}/parity-baseline.json`
5. Store full baseline object (key + hash + metadata)

**File Format Example**:
```json
{
  "baseline_key": {
    "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "node_id": "abcdef123456",
    "feature_slug": "042-local-mission-dossier",
    "target_branch": "2.x",
    "mission_key": "software-dev",
    "manifest_version": "1"
  },
  "baseline_key_hash": "baseline_key_sha256_hash",
  "parity_hash_sha256": "abc456def789...",
  "captured_at": "2026-02-21T09:00:00Z",
  "captured_by": "abcdef123456"
}
```

**Test Requirements**:
- save_baseline() creates file in correct location
- load_baseline() reads file without errors
- Round-trip (save, load) preserves all fields
- Missing file returns None (no exception)

---

### T042: Baseline Acceptance Logic

**What**: Validate baseline key matches current context (prevent false positives).

**How**:
1. Create accept_baseline() function:
   ```python
   def accept_baseline(
       loaded_baseline: BaselineSnapshot,
       current_key: BaselineKey,
       strict: bool = True,
   ) -> Tuple[bool, Optional[str]]:
       """Check if loaded baseline matches current context.

       Args:
           loaded_baseline: Baseline loaded from file
           current_key: Computed baseline key for current context
           strict: If True, exact match required; if False, partial match allowed

       Returns:
           (is_accepted, reason)
           - (True, None): Baseline accepted, safe to compare hashes
           - (False, reason): Baseline rejected, treat as "no baseline"
       """
       if strict:
           # Exact match: all components must match
           if loaded_baseline.baseline_key != current_key:
               # Detailed comparison to find which component differs
               diffs = []
               if loaded_baseline.baseline_key.project_uuid != current_key.project_uuid:
                   diffs.append("project_uuid")
               if loaded_baseline.baseline_key.node_id != current_key.node_id:
                   diffs.append("node_id")
               if loaded_baseline.baseline_key.feature_slug != current_key.feature_slug:
                   diffs.append("feature_slug")
               if loaded_baseline.baseline_key.target_branch != current_key.target_branch:
                   diffs.append("target_branch")
               if loaded_baseline.baseline_key.mission_key != current_key.mission_key:
                   diffs.append("mission_key")
               if loaded_baseline.baseline_key.manifest_version != current_key.manifest_version:
                   diffs.append("manifest_version")

               reason = f"Baseline key mismatch: {', '.join(diffs)}"
               return False, reason

       # Accepted
       return True, None
   ```
2. Usage in drift detection:
   ```python
   loaded_baseline = load_baseline(feature_slug, repo_root)
   if not loaded_baseline:
       # No baseline to compare against
       return None, "No baseline available"

   accepted, reason = accept_baseline(loaded_baseline, current_key)
   if not accepted:
       # Baseline rejected (e.g., branch switched)
       logger.info(f"Baseline rejected: {reason}")
       return None, f"Baseline rejected: {reason}"

   # Baseline accepted, proceed to drift check
   ```
3. Acceptance logic:
   - If loaded baseline key != current key → reject ("no baseline")
   - If keys match → accept, safe to compare hashes

**False Positive Prevention**:
- Branch switch (target_branch differs) → baseline rejected (no drift event)
- Manifest update (manifest_version differs) → baseline rejected
- Multi-user (node_id differs) → baseline rejected
- Multi-project → baseline rejected

**Test Requirements**:
- Exact match → accepted
- project_uuid differs → rejected
- target_branch differs → rejected
- manifest_version differs → rejected
- Reason message includes which components differ

---

### T043: Drift Detection

**What**: Compare current snapshot parity hash vs cached baseline.

**How**:
1. Create detect_drift() function:
   ```python
   def detect_drift(
       feature_slug: str,
       current_snapshot: MissionDossierSnapshot,
       repo_root: Path,
       project_identity: ProjectIdentity,
       target_branch: str,
       mission_key: str,
       manifest_version: str,
   ) -> Tuple[bool, Optional[dict]]:
       """Detect parity drift.

       Returns:
           (has_drift, drift_info)
           - (False, None): No drift (or no baseline to compare)
           - (True, {parity_hashes, missing_in_local, missing_in_baseline, severity}): Drift detected
       """
       # Compute current baseline key
       current_key = compute_baseline_key(
           feature_slug=feature_slug,
           target_branch=target_branch,
           mission_key=mission_key,
           manifest_version=manifest_version,
           project_identity=project_identity,
       )

       # Load stored baseline
       stored_baseline = load_baseline(feature_slug, repo_root)
       if not stored_baseline:
           return False, None  # No baseline, nothing to compare

       # Accept baseline (validate key match)
       accepted, reason = accept_baseline(stored_baseline, current_key)
       if not accepted:
           return False, None  # Baseline rejected (treat as "no baseline")

       # Compare parity hashes
       current_hash = current_snapshot.parity_hash_sha256
       baseline_hash = stored_baseline.parity_hash_sha256

       if current_hash == baseline_hash:
           return False, None  # No drift

       # Drift detected
       # Compute severity (optional: based on missing artifact counts, manifest status, etc.)
       severity = "warning"  # Can be "info", "warning", "error"

       drift_info = {
           'local_parity_hash': current_hash,
           'baseline_parity_hash': baseline_hash,
           'missing_in_local': [],  # TODO: compute from artifact summaries
           'missing_in_baseline': [],  # TODO: compute from artifact summaries
           'severity': severity,
       }

       return True, drift_info
   ```
2. Severity levels:
   - "info": Minor drift (e.g., optional artifact changed)
   - "warning": Significant drift (e.g., multiple required artifacts changed)
   - "error": Critical drift (e.g., completeness status changed from complete to incomplete)
3. Missing artifacts: Compute by comparing artifact keys in snapshot vs baseline

**Test Requirements**:
- Same hash → no drift
- Different hash → drift detected
- No baseline → no drift (return False)
- Baseline key mismatch → no drift (baseline rejected)

---

### T044: ParityDriftDetected Event Emission

**What**: Emit event when drift detected (only if conditions met).

**How**:
1. Integrate drift detection with event emission:
   ```python
   async def emit_drift_if_detected(
       feature_slug: str,
       current_snapshot: MissionDossierSnapshot,
       repo_root: Path,
       project_identity: ProjectIdentity,
       target_branch: str,
       mission_key: str,
       manifest_version: str,
       actor: Optional[str] = None,
   ) -> Optional[MissionDossierParityDriftDetectedEvent]:
       """Detect drift and emit event if found."""
       has_drift, drift_info = detect_drift(
           feature_slug=feature_slug,
           current_snapshot=current_snapshot,
           repo_root=repo_root,
           project_identity=project_identity,
           target_branch=target_branch,
           mission_key=mission_key,
           manifest_version=manifest_version,
       )

       if not has_drift:
           return None  # No drift, no event

       # Emit ParityDriftDetected event (from WP04)
       event = await emit_parity_drift_detected(
           feature_slug=feature_slug,
           local_parity_hash=drift_info['local_parity_hash'],
           baseline_parity_hash=drift_info['baseline_parity_hash'],
           missing_in_local=drift_info['missing_in_local'],
           missing_in_baseline=drift_info['missing_in_baseline'],
           severity=drift_info['severity'],
           actor=actor,
       )

       return event
   ```
2. Conditional emission: Event emitted only if has_drift=True
3. Integrate into indexing workflow (call after snapshot computed)

**Test Requirements**:
- Event emitted if drift detected
- Event not emitted if no drift
- Event not emitted if no baseline
- Event not emitted if baseline rejected
- Event includes severity and artifact lists

---

### T045: Baseline Update Logic

**What**: Implement logic to capture new baseline when accepted by user.

**How**:
1. Create capture_baseline() function:
   ```python
   def capture_baseline(
       feature_slug: str,
       current_snapshot: MissionDossierSnapshot,
       repo_root: Path,
       project_identity: ProjectIdentity,
       target_branch: str,
       mission_key: str,
       manifest_version: str,
   ) -> BaselineSnapshot:
       """Capture current snapshot as new baseline.

       Call this after curator reviews drift and accepts new content as correct.
       """
       current_key = compute_baseline_key(
           feature_slug=feature_slug,
           target_branch=target_branch,
           mission_key=mission_key,
           manifest_version=manifest_version,
           project_identity=project_identity,
       )

       baseline = BaselineSnapshot(
           baseline_key=current_key,
           baseline_key_hash=current_key.compute_hash(),
           parity_hash_sha256=current_snapshot.parity_hash_sha256,
           captured_at=datetime.utcnow(),
           captured_by=project_identity.node_id,
       )

       save_baseline(feature_slug, baseline, repo_root)
       return baseline
   ```
2. Usage:
   - Curator reviews drift event
   - If change is intentional, curator runs `spec-kitty accept-baseline {feature}`
   - CLI calls capture_baseline() and saves to file
3. Baseline should only be captured by curator (manual acceptance, not automatic)

**Baseline Update Triggers**:
- Manual: `spec-kitty accept-baseline {feature}` command
- Deferred: Automatic capture on snapshot after CI/CD validation (post-042)

**Test Requirements**:
- capture_baseline() creates BaselineSnapshot
- Baseline saved to correct file
- Baseline_key_hash computed correctly
- captured_by includes node_id
- captured_at is current timestamp

---

## Definition of Done

- [ ] BaselineKey dataclass created (6-component identity)
- [ ] BaselineSnapshot dataclass created (key + hash + metadata)
- [ ] Baseline key computation working (deterministic hash)
- [ ] Baseline persistence (save/load JSON)
- [ ] Baseline acceptance logic (key match validation)
- [ ] Drift detection working (hash comparison)
- [ ] ParityDriftDetected event emission (conditional)
- [ ] Baseline capture logic (manual update)
- [ ] False positives prevented (branch switch, manifest update)
- [ ] All drift detection tests passing
- [ ] FR-012 requirement satisfied

---

## Risks & Mitigations

**Risk 1**: Baseline key namespace incomplete (collision possible)
- **Mitigation**: Include all context (project, node, feature, branch, mission, manifest); test multi-user scenarios

**Risk 2**: Baseline files accumulate (storage bloat)
- **Mitigation**: Keep one baseline per feature (overwrite on capture); cleanup in future (deferred)

**Risk 3**: Drift detection too noisy (false positive events)
- **Mitigation**: Robust key matching (exact component comparison) + clear logging

**Risk 4**: Baseline update race condition (concurrent captures)
- **Mitigation**: File locking (optional, deferred post-042)

---

## Reviewer Guidance

When reviewing WP08:
1. Verify BaselineKey includes all 6 components (project, node, feature, branch, mission, manifest)
2. Check baseline persistence (save/load JSON correctly)
3. Confirm acceptance logic validates all key components
4. Verify drift detection compares hashes correctly
5. Check ParityDriftDetected event emitted only on true drift
6. Validate false positives prevented (branch switch → no event)
7. Check baseline capture logic implemented (manual acceptance)
8. Test with multi-feature, multi-branch, multi-user scenarios
9. Validate FR-012 requirement (offline-capable, local detection)

---

## Implementation Notes

- **Storage**: drift_detector.py (detector functions, baselines)
- **Dependencies**: WP05 (snapshot), WP04 (events), sync/project_identity
- **Estimated Lines**: ~350 (drift_detector.py + tests)
- **Integration Point**: Called after snapshot computed (in indexing workflow)
- **Deferred**: Automatic baseline capture post-CI, cross-org reconciliation (post-042)

## Activity Log

- 2026-02-21T15:59:47Z – coordinator – shell_pid=99003 – lane=doing – Assigned agent via workflow command
- 2026-02-21T16:02:16Z – coordinator – shell_pid=99003 – lane=for_review – Ready for review: Implemented complete parity-drift detector with 30 comprehensive tests, all passing
- 2026-02-21T16:03:23Z – coordinator – shell_pid=99003 – lane=done – Code review passed: 30 tests, baseline namespacing verified, offline drift detection validated
