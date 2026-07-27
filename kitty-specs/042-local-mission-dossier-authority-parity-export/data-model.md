# Phase 1 Data Model: Mission Dossier Entities

**Date**: 2026-02-21 | **Feature**: 042-local-mission-dossier-authority-parity-export

## Dossier Entities & Relationships

### ArtifactRef (WP01)

**Purpose**: Immutable reference to a single indexed artifact

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ArtifactRef(BaseModel):
    """Single artifact indexed in a dossier."""

    # Identity
    artifact_key: str = Field(
        ...,
        description="Stable, unique key for this artifact (e.g., 'input.spec.main', 'output.tasks.per_wp')"
    )
    artifact_class: str = Field(
        ...,
        description="Classification: input | workflow | output | evidence | policy | runtime | other"
    )

    # Location & Content
    relative_path: str = Field(
        ...,
        description="Relative path from feature directory (e.g., 'spec.md', 'tasks/WP01.md')"
    )
    content_hash_sha256: str = Field(
        ...,
        description="SHA256 hash of artifact bytes (deterministic)"
    )
    size_bytes: int = Field(
        ...,
        description="File size in bytes"
    )

    # Metadata
    wp_id: Optional[str] = Field(
        None,
        description="Work package ID if linked (e.g., 'WP01', None if not WP-specific)"
    )
    step_id: Optional[str] = Field(
        None,
        description="Mission step (e.g., 'planning', 'implementation', None if not step-specific)"
    )
    required_status: str = Field(
        default="optional",
        description="'required' | 'optional' (from manifest)"
    )

    # Provenance
    provenance: Optional[dict] = Field(
        default=None,
        description="Source info: {source_kind: 'git'|'runtime'|'generated'|'manual', actor_id, captured_at}"
    )

    # State
    is_present: bool = Field(
        default=True,
        description="True if file currently exists and readable"
    )
    error_reason: Optional[str] = Field(
        None,
        description="If not present: 'not_found' | 'unreadable' | 'invalid_format' | 'deleted_after_scan'"
    )

    # Timestamps
    indexed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this artifact was indexed"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

**Uniqueness Constraint**: `(feature_slug, artifact_key)` is unique per dossier.

---

### ExpectedArtifactManifest (WP02)

**Purpose**: Registry of required/optional artifacts per mission type and step

```python
from typing import List, Dict
from enum import Enum

class ArtifactClassEnum(str, Enum):
    """6 artifact classes (deterministic, no fallback)."""
    INPUT = "input"
    WORKFLOW = "workflow"
    OUTPUT = "output"
    EVIDENCE = "evidence"
    POLICY = "policy"
    RUNTIME = "runtime"

class ExpectedArtifactSpec(BaseModel):
    """Single expected artifact definition."""
    artifact_key: str = Field(..., description="e.g., 'input.spec.main'")
    artifact_class: ArtifactClassEnum
    path_pattern: str = Field(..., description="e.g., 'spec.md' or 'tasks/*.md'")
    blocking: bool = Field(default=False, description="True if missing blocks completeness")

class ExpectedArtifactManifest(BaseModel):
    """Registry for a mission type, step-aware."""
    schema_version: str = "1.0"
    mission_type: str = Field(..., description="e.g., 'software-dev', 'research', 'documentation'")
    manifest_version: str = Field(default="1", description="Manifest version for compatibility/evolution")

    required_always: List[ExpectedArtifactSpec] = Field(
        default_factory=list,
        description="Artifacts required regardless of workflow step"
    )
    required_by_step: Dict[str, List[ExpectedArtifactSpec]] = Field(
        default_factory=dict,
        description="Step ID (from mission.yaml states) → list of required specs for that step"
    )
    optional_always: List[ExpectedArtifactSpec] = Field(
        default_factory=list,
        description="Optional artifacts checked if present, but missing is non-blocking"
    )

    @classmethod
    def from_yaml_file(cls, path: Path) -> "ExpectedArtifactManifest":
        """Load manifest from YAML."""
        import ruamel.yaml
        yaml = ruamel.yaml.YAML()
        with open(path) as f:
            data = yaml.load(f)
        return cls(**data)
```

**Manifests Shipped in V1**:
- `src/specify_cli/missions/software-dev/expected-artifacts.yaml`
- `src/specify_cli/missions/research/expected-artifacts.yaml`
- `src/specify_cli/missions/documentation/expected-artifacts.yaml`

**Registry Access**:
```python
# src/specify_cli/dossier/manifest.py
class ManifestRegistry:
    """Load and query expected artifact manifests."""

    @staticmethod
    def load_manifest(mission_type: str) -> Optional[ExpectedArtifactManifest]:
        """Load manifest for mission, return None if not found."""
        # Check missions/*/expected-artifacts.yaml

    @staticmethod
    def get_required_artifacts(manifest: ExpectedArtifactManifest, step_id: str) -> List[ExpectedArtifactSpec]:
        """Get required specs for mission step (from mission.yaml state machine).

        Returns: required_always + required_by_step[step_id]
        """
        base = manifest.required_always
        step_specific = manifest.required_by_step.get(step_id, [])
        return base + step_specific
```

---

### MissionDossier (WP01)

**Purpose**: Collection of indexed artifacts for a single feature

```python
class MissionDossier(BaseModel):
    """Complete artifact inventory for a mission/feature."""

    # Identity
    mission_slug: str = Field(..., description="e.g., 'software-dev'")
    mission_run_id: str = Field(..., description="UUID or feature run identifier")
    feature_slug: str = Field(..., description="e.g., '042-local-mission-dossier'")
    feature_dir: str = Field(..., description="Absolute path to feature directory")

    # Artifacts
    artifacts: List[ArtifactRef] = Field(default_factory=list, description="All indexed artifacts")

    # Completeness
    manifest: Optional[ExpectedArtifactManifest] = Field(
        None,
        description="Loaded manifest for this mission type (None if not found)"
    )

    # Snapshot
    latest_snapshot: Optional["MissionDossierSnapshot"] = Field(
        None,
        description="Most recent snapshot (after all artifacts indexed)"
    )

    # Timestamps
    dossier_created_at: datetime = Field(default_factory=datetime.utcnow)
    dossier_updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_required_artifacts(self, step_id: Optional[str] = None) -> List[ArtifactRef]:
        """Return required artifacts for step (or all required if step_id=None)."""
        if not self.manifest:
            return []
        # Match artifacts against manifest requirements

    def get_missing_required_artifacts(self, step_id: Optional[str] = None) -> List[ArtifactRef]:
        """Return required artifacts that are not present."""
        required = self.get_required_artifacts(step_id)
        return [a for a in required if not a.is_present]

    @property
    def completeness_status(self) -> str:
        """'complete' iff all required artifacts present, else 'incomplete'."""
        if not self.manifest:
            return "unknown"  # No manifest, can't judge completeness
        missing = self.get_missing_required_artifacts()
        return "complete" if not missing else "incomplete"
```

---

### MissionDossierSnapshot (WP05)

**Purpose**: Point-in-time projection of dossier state + parity hash

```python
class MissionDossierSnapshot(BaseModel):
    """Deterministic snapshot of dossier state."""

    # Identity
    feature_slug: str
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Artifact Counts
    total_artifacts: int = Field(..., description="Total indexed artifacts")
    required_artifacts: int = Field(..., description="Count of required artifacts")
    required_present: int = Field(..., description="Count of required artifacts present")
    required_missing: int = Field(..., description="Count of required artifacts missing (blocking)")
    optional_artifacts: int = Field(..., description="Count of optional artifacts")
    optional_present: int = Field(..., description="Count of optional present")

    # Completeness
    completeness_status: str = Field(
        ...,
        description="'complete' | 'incomplete' | 'unknown' (no manifest)"
    )

    # Parity Hash (Core Determinism)
    parity_hash_sha256: str = Field(
        ...,
        description="SHA256 of sorted artifact content hashes. Deterministic, reproducible."
    )
    parity_hash_components: List[str] = Field(
        ...,
        description="Sorted list of individual artifact hashes (for audit)"
    )

    # Artifacts Summary
    artifact_summaries: List[dict] = Field(
        default_factory=list,
        description="[{artifact_key, class, wp_id, step_id, is_present, error_reason}]"
    )

    # Timestamps
    computed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

**Computation Algorithm**:
```python
def compute_snapshot(dossier: MissionDossier) -> MissionDossierSnapshot:
    """Deterministically compute snapshot from dossier."""

    # 1. Sort artifacts by artifact_key
    sorted_artifacts = sorted(dossier.artifacts, key=lambda a: a.artifact_key)

    # 2. Extract hashes (present artifacts only)
    present_hashes = [a.content_hash_sha256 for a in sorted_artifacts if a.is_present]

    # 3. Sort hashes lexicographically (for order-independence)
    sorted_hashes = sorted(present_hashes)

    # 4. Concatenate and hash
    combined = "".join(sorted_hashes)
    parity_hash = hashlib.sha256(combined.encode()).hexdigest()

    # 5. Count artifacts by status
    required = [a for a in sorted_artifacts if a.required_status == "required"]
    optional = [a for a in sorted_artifacts if a.required_status == "optional"]

    completeness_status = (
        "complete" if all(a.is_present for a in required)
        else "incomplete" if any(r for r in required if not r.is_present)
        else "unknown"
    )

    return MissionDossierSnapshot(
        feature_slug=dossier.feature_slug,
        total_artifacts=len(sorted_artifacts),
        required_artifacts=len(required),
        required_present=sum(1 for a in required if a.is_present),
        required_missing=sum(1 for a in required if not a.is_present),
        optional_artifacts=len(optional),
        optional_present=sum(1 for a in optional if a.is_present),
        completeness_status=completeness_status,
        parity_hash_sha256=parity_hash,
        parity_hash_components=sorted_hashes,
        artifact_summaries=[...],  # Summarize each artifact
    )
```

---

## Dossier Event Schemas (WP04)

### MissionDossierArtifactIndexed

**Purpose**: Emitted when artifact successfully indexed

```python
class MissionDossierArtifactIndexedPayload(BaseModel):
    feature_slug: str
    artifact_key: str
    artifact_class: str
    relative_path: str
    content_hash_sha256: str
    size_bytes: int
    wp_id: Optional[str]
    step_id: Optional[str]
    required_status: str  # "required" | "optional"

class MissionDossierArtifactIndexed(BaseModel):
    """Event emitted for each successfully indexed artifact."""
    event_type: str = "mission_dossier_artifact_indexed"
    payload: MissionDossierArtifactIndexedPayload
```

---

### MissionDossierArtifactMissing

**Purpose**: Emitted when required artifact missing or unreadable

```python
class MissionDossierArtifactMissingPayload(BaseModel):
    feature_slug: str
    artifact_key: str
    artifact_class: str
    expected_path_pattern: str
    reason_code: str  # "not_found" | "unreadable" | "invalid_format" | "deleted_after_scan"
    reason_detail: Optional[str]
    blocking: bool  # True if this blocks completeness

class MissionDossierArtifactMissing(BaseModel):
    """Anomaly event: required artifact missing."""
    event_type: str = "mission_dossier_artifact_missing"
    payload: MissionDossierArtifactMissingPayload
```

---

### MissionDossierSnapshotComputed

**Purpose**: Emitted when snapshot computed (after all artifacts indexed)

```python
class MissionDossierSnapshotComputedPayload(BaseModel):
    feature_slug: str
    parity_hash_sha256: str
    artifact_counts: dict  # {total, required, required_present, required_missing, optional, optional_present}
    completeness_status: str  # "complete" | "incomplete" | "unknown"
    snapshot_id: str

class MissionDossierSnapshotComputed(BaseModel):
    """Event: snapshot computed after dossier finalized."""
    event_type: str = "mission_dossier_snapshot_computed"
    payload: MissionDossierSnapshotComputedPayload
```

---

### MissionDossierParityDriftDetected

**Purpose**: Emitted when local snapshot differs from cached baseline

```python
class MissionDossierParityDriftDetectedPayload(BaseModel):
    feature_slug: str
    local_parity_hash: str
    baseline_parity_hash: str
    missing_in_local: List[str]  # artifact_keys
    missing_in_baseline: List[str]  # artifact_keys (new artifacts)
    severity: str  # "info" | "warning" | "error"

class MissionDossierParityDriftDetected(BaseModel):
    """Anomaly event: parity hash differs from baseline."""
    event_type: str = "mission_dossier_parity_drift_detected"
    payload: MissionDossierParityDriftDetectedPayload
```

---

## Dashboard API Response Models

### DossierOverviewResponse

```python
class DossierOverviewResponse(BaseModel):
    feature_slug: str
    completeness_status: str
    parity_hash_sha256: str
    artifact_counts: dict
    missing_required_count: int
    last_scanned_at: Optional[datetime]
```

### ArtifactListResponse

```python
class ArtifactListItem(BaseModel):
    artifact_key: str
    artifact_class: str
    relative_path: str
    size_bytes: int
    wp_id: Optional[str]
    step_id: Optional[str]
    is_present: bool
    error_reason: Optional[str]

class ArtifactListResponse(BaseModel):
    total_count: int
    filtered_count: int
    artifacts: List[ArtifactItem]  # Filtered & sorted
    filters_applied: dict  # {class, wp_id, step_id, required_only}
```

### ArtifactDetailResponse

```python
class ArtifactDetailResponse(BaseModel):
    artifact_key: str
    artifact_class: str
    relative_path: str
    content_hash_sha256: str
    size_bytes: int
    wp_id: Optional[str]
    step_id: Optional[str]
    required_status: str
    is_present: bool
    error_reason: Optional[str]

    # Full content (or truncation notice)
    content: Optional[str]  # Full text if <5MB, else None
    content_truncated: bool
    truncation_notice: Optional[str]  # "File >5MB, content not included"
    media_type_hint: str  # "markdown" | "json" | "yaml" | "text"

    indexed_at: datetime
```

---

## Storage Format

### Dossier Snapshot Persistence

**File**: `.kittify/dossiers/{feature_slug}/snapshot-latest.json`

Contains serialized MissionDossierSnapshot (immutable point-in-time projection).

```json
{
  "feature_slug": "042-local-mission-dossier",
  "snapshot_id": "abc123...",
  "total_artifacts": 15,
  "required_artifacts": 10,
  "required_present": 10,
  "required_missing": 0,
  "completeness_status": "complete",
  "parity_hash_sha256": "abc456def789...",
  "computed_at": "2026-02-21T10:00:00Z"
}
```

### Parity Baseline Cache (Robustly Namespaced)

**File**: `.kittify/dossiers/{feature_slug}/parity-baseline.json`

Stores point-in-time parity hash with identity tuple for robust drift detection (prevents false positives):

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
  "captured_by": "node_id_at_capture"
}
```

**Baseline Key Components** (prevent false positives):
- `project_uuid`: Local project identity (from sync/project_identity.py)
- `node_id`: Stable machine identifier (from sync/project_identity.py)
- `feature_slug`: Feature identifier
- `target_branch`: Git branch where feature is based (main, 2.x, etc.)
- `mission_key`: Mission type (software-dev, research, documentation)
- `manifest_version`: Manifest schema version

**Acceptance Logic**:
- On parity detection, compute current key
- Compare current key vs baseline key (via hash)
- Accept baseline only if keys match; else treat as "no baseline" (informational drift event)
- This prevents false positives from branch switches, manifest updates, multi-user/multi-machine scenarios

---

## Integration Points

### With Sync Infrastructure

- Dossier events register in `src/specify_cli/sync/events.py`
- Emitted via `OfflineQueue.emit()` (async-safe)
- Routed to webhook (mock SaaS in tests)

### With Dashboard API

- Endpoints in `src/specify_cli/dashboard/api.py`
- Import `MissionDossier`, `DossierSnapshot`, filter/query logic
- Vue components fetch via `/api/dossier/*`

### With Mission System

- Load `ExpectedArtifactManifest` for feature's mission type
- Registry extensible for new missions (graceful degradation if no manifest)

---

## References

- **Pydantic Documentation**: https://docs.pydantic.dev/
- **datetime Handling**: Use `datetime.utcnow()` (UTC-aware, no timezone ambiguity)
- **SHA256 Hashing**: Use `hashlib.sha256()` from stdlib
- **YAML Parsing**: Use `ruamel.yaml` (existing spec-kitty dependency)
