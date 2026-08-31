# Data Model: Charter Phase 7 Schema Versioning and Provenance Hardening

**Mission**: charter-p7-schema-versioning-provenance-01KQEG13  
**Date**: 2026-04-30

---

## 1. Bundle Schema Version (bundle_schema_version)

**What it is**: An integer stored in `.kittify/charter/metadata.yaml` that declares the overall compatibility version of the charter synthesis bundle. It is distinct from the existing `schema_version: "1.0.0"` semver string in that same file (the semver tracks the extraction YAML format; the integer tracks the synthesis bundle compatibility).

**Lifecycle**:
- `None` / absent → treated as version 1 (pre-Phase 7 bundles that exist today)
- `1` → Phase 3 baseline (v1 sidecars: `corpus_snapshot_id` optional, no `synthesizer_version`)
- `2` → Phase 7 hardened (v2 sidecars: all mandatory fields present)

**Storage location**: `.kittify/charter/metadata.yaml` key `bundle_schema_version` (new integer field alongside existing `schema_version: "1.0.0"` string).

**Model change** (`src/charter/schemas.py`, `ExtractionMetadata`):
```python
class ExtractionMetadata(BaseModel):
    schema_version: str = "1.0.0"        # unchanged
    extracted_at: str = ""               # unchanged
    charter_hash: str = ""               # unchanged
    source_path: str = ".kittify/charter/charter.md"  # unchanged
    extraction_mode: str = "deterministic"  # unchanged
    sections_parsed: SectionsParsed = ...  # unchanged
    bundle_schema_version: int | None = None  # NEW — None means "pre-Phase 7 = v1"
```

---

## 2. ProvenanceEntry v2

**Module**: `src/charter/synthesizer/synthesize_pipeline.py`  
**Storage**: `.kittify/charter/provenance/<kind>-<slug>.yaml`  
**Change**: `schema_version` bumps from `Literal["1"]` to `Literal["2"]`. Six new/promoted fields.

### Full v2 field set

| Field | Type | Required | Change from v1 | Notes |
|-------|------|----------|----------------|-------|
| `schema_version` | `Literal["2"]` | yes | bumped from `"1"` | Pydantic validator ensures only "2" accepted in v2 model |
| `artifact_urn` | `str` | yes | unchanged | |
| `artifact_kind` | `Literal["directive","tactic","styleguide"]` | yes | unchanged | |
| `artifact_slug` | `str` | yes | unchanged | |
| `artifact_content_hash` | `str` | yes | unchanged | blake3-256/SHA-256 of `canonical_yaml(body)` bytes |
| `inputs_hash` | `str` | yes | unchanged | hash of normalized `SynthesisRequest` |
| `adapter_id` | `str` | yes | unchanged | |
| `adapter_version` | `str` | yes | unchanged | |
| `synthesizer_version` | `str` | **yes** | **NEW** | `specify_cli.__version__` at synthesis time |
| `source_section` | `str \| None` | conditional | unchanged | at least one of `source_section` / `source_urns` required (existing validator) |
| `source_urns` | `list[str]` | conditional | unchanged | |
| `source_input_ids` | `list[str]` | **yes** | **NEW** | initially mirrors `source_urns`; same list for Phase 7 |
| `generated_at` | `str` | yes | unchanged | ISO 8601 UTC from `AdapterOutput.generated_at` |
| `produced_at` | `str` | **yes** | **NEW** | ISO 8601 UTC stamped in `provenance.dump_yaml` at write time |
| `corpus_snapshot_id` | `str` | **yes** | **promoted** from `str \| None = None` | `"(none)"` when no snapshot available |
| `synthesis_run_id` | `str` | **yes** | **NEW** | `StagingDir.run_id` ULID, links sidecar to manifest |
| `evidence_bundle_hash` | `str \| None` | no | unchanged (stays Optional) | SHA-256 of serialized EvidenceBundle; `None` when no evidence |
| `adapter_notes` | `str \| None` | no | unchanged | |

### Migration sentinel values (v1 → v2 migration)

When upgrading a v1 sidecar that lacks the new fields, the migration fills them with unambiguous sentinel strings rather than fabricating data:

| Field | Sentinel value | Meaning |
|-------|----------------|---------|
| `synthesizer_version` | `"(pre-phase7-migration)"` | Version unknown; artifact was synthesized before Phase 7 |
| `source_input_ids` | (copy of existing `source_urns`) | Best approximation |
| `produced_at` | (file modification time of the sidecar, or `"(pre-phase7-migration)"` if unavailable) | Best approximation |
| `corpus_snapshot_id` | existing value or `"(none)"` if was `None` | |
| `synthesis_run_id` | `"(pre-phase7-migration)"` | Run ID unknown; manifest may not exist |

Validation during bundle validate: sentinel-valued fields produce a **warning** (not an error) when bundle validate is run in default mode. Running with `--strict` causes sentinels to produce errors. This allows migrated bundles to pass CI without re-synthesizing, while new synthesis is always fully provenance-complete.

---

## 3. SynthesisManifest v2

**Module**: `src/charter/synthesizer/manifest.py`  
**Storage**: `.kittify/charter/synthesis-manifest.yaml`  
**Change**: `schema_version` bumps from `Literal["1"]` to `Literal["2"]`. Two new fields.

### Full v2 field set

| Field | Type | Required | Change from v1 | Notes |
|-------|------|----------|----------------|-------|
| `schema_version` | `Literal["2"]` | yes | bumped | |
| `mission_id` | `str \| None` | no | unchanged | |
| `created_at` | `str` | yes | unchanged | ISO 8601 UTC |
| `run_id` | `str` | yes | unchanged | ULID |
| `adapter_id` | `str` | yes | unchanged | |
| `adapter_version` | `str` | yes | unchanged | |
| `synthesizer_version` | `str` | **yes** | **NEW** | `specify_cli.__version__` |
| `manifest_hash` | `str` | **yes** | **NEW** | SHA-256 hex of `canonical_yaml(manifest_fields_excluding_manifest_hash)` |
| `artifacts` | `list[ManifestArtifactEntry]` | yes | unchanged | |

### `manifest_hash` computation algorithm

```
manifest_dict = {all manifest fields EXCEPT manifest_hash}
manifest_bytes = canonical_yaml(manifest_dict)
manifest_hash = sha256(manifest_bytes).hexdigest()
```

Validation: load manifest → strip `manifest_hash` → re-serialize → re-hash → compare. Mismatch = corrupt manifest.

---

## 4. BundleCompatibilityResult

**Module**: `src/doctrine/versioning.py` (new file)

```python
@dataclass(frozen=True)
class BundleCompatibilityResult:
    status: BundleCompatibilityStatus
    bundle_version: int | None  # None means field was absent
    supported_min: int
    supported_max: int
    message: str         # human-readable, action-oriented
    exit_code: int       # 0 = compatible, 1 = incompatible/needs migration

    @property
    def is_compatible(self) -> bool: ...
    @property
    def needs_migration(self) -> bool: ...
```

### `BundleCompatibilityStatus` enum

| Value | Meaning | `exit_code` |
|-------|---------|-------------|
| `COMPATIBLE` | Bundle version == current CLI's supported version | 0 |
| `NEEDS_MIGRATION` | Bundle version < current, registered migration exists | 1 (run `spec-kitty upgrade`) |
| `INCOMPATIBLE_OLD` | Bundle version < current, no migration registered | 1 (manual recovery required) |
| `INCOMPATIBLE_NEW` | Bundle version > supported max | 1 (upgrade CLI) |
| `MISSING_VERSION` | `bundle_schema_version` absent from metadata (pre-Phase 7) | 1 — treated as v1 per research decision 4 |

---

## 5. Compatibility Registry (src/doctrine/versioning.py)

```
CURRENT_BUNDLE_SCHEMA_VERSION: int = 2
MIN_READABLE_BUNDLE_SCHEMA: int = 1    # v1 bundles are readable with migration
MAX_READABLE_BUNDLE_SCHEMA: int = 2    # v2 is the current format

REGISTERED_MIGRATIONS: dict[int, Callable[[Path, bool], MigrationResult]] = {
    1: migrate_v1_to_v2,  # the one real migration required by FR-004
}

Public API:
  check_bundle_compatibility(bundle_version: int | None) -> BundleCompatibilityResult
  run_migration(from_version: int, bundle_root: Path, dry_run: bool) -> MigrationResult
  get_bundle_schema_version(charter_dir: Path) -> int | None
```

`migrate_v1_to_v2(bundle_root: Path, dry_run: bool) -> MigrationResult`:
1. Read all sidecar files from `.kittify/charter/provenance/*.yaml`
2. For each sidecar with `schema_version: "1"`, add sentinel values for new mandatory fields
3. Write upgraded sidecar (with `schema_version: "2"`) atomically
4. If synthesis manifest exists, upgrade it to v2 (add `synthesizer_version` and `manifest_hash`)
5. Update `metadata.yaml` `bundle_schema_version` to `2`
6. Return `MigrationResult` with list of changed paths

---

## 6. ExtractionMetadata (updated)

**Module**: `src/charter/schemas.py`

The `ExtractionMetadata` Pydantic model gains one new optional field `bundle_schema_version: int | None = None`. The extractor (`src/charter/extractor.py`) stamps `bundle_schema_version = CURRENT_BUNDLE_SCHEMA_VERSION` (imported from `doctrine.versioning`) when writing `metadata.yaml` during `charter sync`.

---

## State Machine: Bundle Schema Version

```
[absent/None]  →  [v1: bundle_schema_version=1]  →  [v2: bundle_schema_version=2]
     ↑__________migration path (spec-kitty upgrade)_____________↑

Reader behavior:
  v2 (current) → COMPATIBLE → proceed
  v1 or absent → NEEDS_MIGRATION → block + "run spec-kitty upgrade"
  v3+ (future) → INCOMPATIBLE_NEW → block + "upgrade CLI"
  <v1 (impossible in practice) → INCOMPATIBLE_OLD → block + contact support
```

---

## Invariants

1. Every sidecar written by Phase 7+ synthesis has `schema_version: "2"` and all six new/promoted mandatory fields populated with non-empty, non-None values (except `evidence_bundle_hash` which stays Optional).
2. Every v2 manifest carries `manifest_hash` = SHA-256 of its own canonical YAML (excluding the `manifest_hash` key). Any deviation from this is a corrupt manifest.
3. `bundle_schema_version` in `metadata.yaml` is the single source of truth for bundle compatibility gating. No code path infers version from sidecar field absence.
4. Validation fails closed: any code path that encounters a sidecar missing a mandatory v2 field produces an error, never silently treats it as valid.
5. The existing `corpus_snapshot_id: str | None` column in provenance status output remains valid for migrated bundles where the sentinel `"(none)"` was substituted. Readers must treat `"(none)"` as "snapshot not available" not as a snapshot ID.
