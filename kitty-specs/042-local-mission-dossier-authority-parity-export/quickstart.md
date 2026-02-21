# Phase 1 Quickstart: Using Mission Dossier

**Date**: 2026-02-21 | **Feature**: 042-local-mission-dossier-authority-parity-export

## For Curators: Inspect Artifact Completeness

### Scenario 1: Open Dashboard & View Dossier

```bash
# Terminal 1: Start dashboard server
spec-kitty dashboard --open

# Browser: http://localhost:8000
# → Click "Dossier" tab
# → See overview panel with:
#   - Feature: 042-local-mission-dossier
#   - Status: Complete ✅
#   - Artifacts: 15 total, 10 required (all present)
#   - Parity Hash: abc456def789...
```

### Scenario 2: Filter Artifacts by Type

```
Dashboard → Dossier → Filter
  [Class] = "output"
  → Shows: plan.md, tasks.md, tasks/WP01.md, tasks/WP02.md, ...

Dashboard → Dossier → Filter
  [Class] = "evidence"
  → Shows: research.md, data-model.md, (contracts/* if present)
```

### Scenario 3: View Artifact Detail

```
Dashboard → Dossier → Click "spec.md"
  → Artifact Panel opens:
    - Path: spec.md
    - Class: input
    - Hash: a1b2c3d4e5f6...
    - Size: 8.5 KB
    - Content:
      ```
      # Feature Specification: Local Mission Dossier Authority...
      [full text, syntax-highlighted markdown]
      ```
```

### Scenario 4: Detect Missing Required Artifact

```bash
# Feature missing plan.md (manually deleted for testing)
spec-kitty dashboard

# Dashboard shows:
#   Status: Incomplete ⚠️
#   Missing: 1 required artifact
#   - plan.md (output, BLOCKING)
#
# → Look at Events section:
#   - MissionDossierArtifactMissing event emitted
#   - reason_code: "not_found"
#   - blocking: true
```

---

## For Developers: API Integration

### Programmatic Artifact Indexing

```python
from specify_cli.dossier import (
    MissionDossier,
    Indexer,
    ManifestRegistry,
)
from pathlib import Path

# 1. Load manifest
manifest = ManifestRegistry.load_manifest("software-dev")

# 2. Index artifacts
feature_dir = Path("/path/to/feature/042-local-mission-dossier")
dossier = Indexer.index_feature(
    feature_dir=feature_dir,
    mission_type="software-dev",
    mission_slug="software-dev",
    feature_slug="042-local-mission-dossier",
)

# 3. Check completeness
print(f"Completeness: {dossier.completeness_status}")
print(f"Missing: {len(dossier.get_missing_required_artifacts())}")

# 4. Iterate artifacts
for artifact in dossier.artifacts:
    print(f"- {artifact.artifact_key}: {artifact.relative_path}")
```

### Emit Dossier Events

```python
from specify_cli.dossier import (
    emit_indexed_event,
    emit_missing_event,
    emit_snapshot_computed_event,
)

# Emit indexed event
await emit_indexed_event(
    feature_slug="042-local-mission-dossier",
    artifact_key="input.spec.main",
    artifact_class="input",
    content_hash_sha256="a1b2c3d4...",
    size_bytes=8500,
    relative_path="spec.md",
)

# Emit missing event (if required artifact not found)
await emit_missing_event(
    feature_slug="042-local-mission-dossier",
    artifact_key="output.plan.main",
    reason_code="not_found",
    blocking=True,
)

# Emit snapshot computed event (after all artifacts indexed)
snapshot = compute_snapshot(dossier)
await emit_snapshot_computed_event(snapshot)
```

### Query API Endpoints

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

# 1. Get dossier overview
resp = client.get("/api/dossier/overview?feature=042-local-mission-dossier")
overview = resp.json()
# {
#   "feature_slug": "042-local-mission-dossier",
#   "completeness_status": "complete",
#   "parity_hash_sha256": "abc456def789...",
#   "artifact_counts": {...}
# }

# 2. List artifacts with filtering
resp = client.get(
    "/api/dossier/artifacts",
    params={
        "feature": "042-local-mission-dossier",
        "class": "output",
        "step_id": "planning",
    }
)
artifacts = resp.json()
# [
#   {"artifact_key": "output.plan.main", "relative_path": "plan.md", ...},
#   {"artifact_key": "output.tasks.main", "relative_path": "tasks.md", ...},
#   ...
# ]

# 3. Get artifact detail with full text
resp = client.get(
    "/api/dossier/artifacts/input.spec.main",
    params={"feature": "042-local-mission-dossier"}
)
detail = resp.json()
# {
#   "artifact_key": "input.spec.main",
#   "content": "# Feature Specification: ...",
#   "media_type_hint": "markdown",
#   ...
# }

# 4. Export snapshot for SaaS import
resp = client.get(
    "/api/dossier/snapshots/export",
    params={"feature": "042-local-mission-dossier"}
)
snapshot_json = resp.json()
# Full MissionDossierSnapshot, ready for SaaS backend
```

---

## For SaaS: Consuming Dossier Events

### Event Stream Example

```json
[
  {
    "event_type": "mission_dossier_artifact_indexed",
    "feature_slug": "042-local-mission-dossier",
    "payload": {
      "artifact_key": "input.spec.main",
      "artifact_class": "input",
      "relative_path": "spec.md",
      "content_hash_sha256": "a1b2c3d4e5f6...",
      "size_bytes": 8500,
      "required_status": "required"
    },
    "timestamp": "2026-02-21T10:00:00Z"
  },
  {
    "event_type": "mission_dossier_artifact_indexed",
    "feature_slug": "042-local-mission-dossier",
    "payload": {
      "artifact_key": "output.plan.main",
      "artifact_class": "output",
      "relative_path": "plan.md",
      "content_hash_sha256": "b2c3d4e5f6g7...",
      "size_bytes": 6200,
      "required_status": "required"
    },
    "timestamp": "2026-02-21T10:00:01Z"
  },
  {
    "event_type": "mission_dossier_snapshot_computed",
    "feature_slug": "042-local-mission-dossier",
    "payload": {
      "parity_hash_sha256": "xyz789...",
      "artifact_counts": {
        "total": 15,
        "required": 10,
        "required_present": 10,
        "required_missing": 0,
        "optional": 5,
        "optional_present": 3
      },
      "completeness_status": "complete"
    },
    "timestamp": "2026-02-21T10:00:05Z"
  }
]
```

### SaaS Parity Check

```python
# SaaS receives events
artifacts_from_events = {}
for event in event_stream:
    if event["event_type"] == "mission_dossier_artifact_indexed":
        payload = event["payload"]
        artifacts_from_events[payload["artifact_key"]] = payload

# Receive snapshot
snapshot_event = [e for e in event_stream if e["event_type"] == "mission_dossier_snapshot_computed"][0]
local_parity_hash = snapshot_event["payload"]["parity_hash_sha256"]

# Verify parity locally (recompute hash from indexed events)
hashes = sorted([a["content_hash_sha256"] for a in artifacts_from_events.values()])
computed_parity = hashlib.sha256("".join(hashes).encode()).hexdigest()

assert computed_parity == local_parity_hash, "Parity mismatch!"
# ✅ Parity verified
```

---

## Expected Artifact Manifests (Reference)

### Software-Dev Mission

**File**: `src/specify_cli/missions/software-dev/expected-artifacts.yaml`

```yaml
schema_version: "1.0"
mission_type: "software-dev"

required_by_phase:
  spec_complete:
    - artifact_key: "input.spec.main"
      artifact_class: "input"
      path_pattern: "spec.md"

  planning_complete:
    - artifact_key: "input.spec.main"
      artifact_class: "input"
      path_pattern: "spec.md"
    - artifact_key: "output.plan.main"
      artifact_class: "output"
      path_pattern: "plan.md"

  tasks_complete:
    - artifact_key: "input.spec.main"
      artifact_class: "input"
      path_pattern: "spec.md"
    - artifact_key: "output.plan.main"
      artifact_class: "output"
      path_pattern: "plan.md"
    - artifact_key: "output.tasks.main"
      artifact_class: "output"
      path_pattern: "tasks.md"
    - artifact_key: "output.tasks.per_wp"
      artifact_class: "output"
      path_pattern: "tasks/*.md"

optional_always:
  - artifact_key: "evidence.research"
    artifact_class: "evidence"
    path_pattern: "research.md"
  - artifact_key: "evidence.data_model"
    artifact_class: "evidence"
    path_pattern: "data-model.md"
  - artifact_key: "evidence.contracts"
    artifact_class: "evidence"
    path_pattern: "contracts/*"
```

### Research Mission

**File**: `src/specify_cli/missions/research/expected-artifacts.yaml`

```yaml
schema_version: "1.0"
mission_type: "research"

required_by_phase:
  spec_complete:
    - artifact_key: "input.spec.main"
      artifact_class: "input"
      path_pattern: "spec.md"

optional_always:
  - artifact_key: "evidence.research_notes"
    artifact_class: "evidence"
    path_pattern: "research.md"
```

### Documentation Mission

**File**: `src/specify_cli/missions/documentation/expected-artifacts.yaml`

```yaml
schema_version: "1.0"
mission_type: "documentation"

required_by_phase:
  spec_complete:
    - artifact_key: "input.spec.main"
      artifact_class: "input"
      path_pattern: "spec.md"

optional_always:
  - artifact_key: "evidence.generated_api_docs"
    artifact_class: "evidence"
    path_pattern: "api-docs/*"
```

---

## Testing Determinism

### Verify Parity Hash Reproducibility

```python
from specify_cli.dossier import Indexer, compute_snapshot
from pathlib import Path

feature_dir = Path("/path/to/feature/042-local-mission-dossier")

# Scan 1
dossier1 = Indexer.index_feature(feature_dir, "software-dev", "software-dev", "042-local-mission-dossier")
snapshot1 = compute_snapshot(dossier1)
hash1 = snapshot1.parity_hash_sha256

# Scan 2 (no artifact changes)
dossier2 = Indexer.index_feature(feature_dir, "software-dev", "software-dev", "042-local-mission-dossier")
snapshot2 = compute_snapshot(dossier2)
hash2 = snapshot2.parity_hash_sha256

assert hash1 == hash2, f"Hashes differ: {hash1} vs {hash2}"
# ✅ Determinism verified
```

---

## Common Workflows

### Workflow 1: After Planning Complete

```bash
# User creates spec, plan, tasks
cd /path/to/feature/042-local-mission-dossier

# Open dashboard
spec-kitty dashboard

# → Dossier tab shows:
#   - All required artifacts present ✅
#   - Completeness: complete
#   - Parity hash computed and stable
```

### Workflow 2: Detect Artifact Corruption

```bash
# User modifies spec.md (introduces typo)
echo "corrupted" >> spec.md

# Dashboard auto-detects
# → Parity hash changed
# → If baseline cached, MissionDossierParityDriftDetected emitted
# → Review changes in dashboard detail view
```

### Workflow 3: Export for SaaS Import

```bash
curl -s http://localhost:8000/api/dossier/snapshots/export?feature=042-local-mission-dossier \
  | jq . > snapshot.json

# Ship snapshot.json to SaaS backend
curl -X POST https://saas.example.com/api/import-dossier \
  -H "Content-Type: application/json" \
  -d @snapshot.json

# SaaS verifies parity, displays artifact catalog in dashboard
```

---

## Troubleshooting

### "Missing required artifact" event

**Cause**: Feature missing required artifact (e.g., plan.md)

**Fix**:
```bash
# Check what's missing
spec-kitty dashboard → Dossier → Filter [Required Only]

# Regenerate missing artifact
spec-kitty plan  # Recreates plan.md

# Re-scan
# (Dashboard auto-rescans on file change)
```

### "Parity hash mismatch"

**Cause**: Artifact content changed (expected after edits)

**Fix**:
```bash
# Re-capture parity baseline
curl -s http://localhost:8000/api/dossier/snapshots/export?feature=042-local-mission-dossier \
  > /path/to/.kittify/dossiers/042-local-mission-dossier/parity-baseline.json

# Or manually edit the file with new hash from current snapshot
```

### "Encoding error on artifact"

**Cause**: Artifact file not valid UTF-8

**Fix**:
```bash
# Check file encoding
file -i artifact.md
# artifact.md: text/plain; charset=utf-16

# Convert to UTF-8
iconv -f UTF-16 -t UTF-8 artifact.md > artifact-fixed.md
mv artifact-fixed.md artifact.md

# Re-scan
```

---

## Next Steps

- **WP01-WP05**: Implement core indexing, events, snapshot computation
- **WP06-WP08**: Build dashboard API and UI, local drift detection
- **WP09-WP10**: Comprehensive testing, edge case hardening
