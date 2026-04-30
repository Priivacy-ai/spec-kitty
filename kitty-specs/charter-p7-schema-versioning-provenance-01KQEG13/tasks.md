# Tasks: Charter Phase 7 Schema Versioning and Provenance Hardening

**Mission**: charter-p7-schema-versioning-provenance-01KQEG13  
**Mission ID**: 01KQEG13YGZN77AMY6Q8DVNKQX  
**Generated**: 2026-04-30T06:23:33Z  
**Branch**: main → main

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Create `src/doctrine/versioning.py`: constants, enums, dataclasses | WP01 | [P] | [D] |
| T002 | Implement `check_bundle_compatibility()` in versioning.py | WP01 | [D] |
| T003 | Implement `get_bundle_schema_version()` in versioning.py | WP01 | [D] |
| T004 | Stub `migrate_v1_to_v2()` and `run_migration()` in versioning.py | WP01 | [D] |
| T005 | Add `bundle_schema_version: int \| None = None` to ExtractionMetadata | WP01 | [D] |
| T006 | Stamp `bundle_schema_version = CURRENT_BUNDLE_SCHEMA_VERSION` in extractor.py | WP01 | [D] |
| T007 | Write `tests/doctrine/test_versioning.py` (≥90% coverage) | WP01 | [D] |
| T008 | Bump ProvenanceEntry → schema_version Literal["2"]; add 5 new/promoted fields | WP02 | [P] |
| T009 | Bump SynthesisManifest → schema_version Literal["2"]; add synthesizer_version, manifest_hash | WP02 | [P] |
| T010 | Update provenance.py dump_yaml() to stamp produced_at at write time | WP02 | [P] |
| T011 | Update write_pipeline.py promote() to pass all v2 ProvenanceEntry fields; compute manifest_hash | WP02 | [P] |
| T012 | Update resynthesize_pipeline.py with same v2 provenance field additions | WP02 | [P] |
| T013 | Update YAML sidecar fixtures in tests/charter/fixtures/synthesizer/ | WP02 | [P] |
| T014 | Update test_provenance.py, test_manifest.py, test_adapter_contract.py for v2 | WP02 | [P] |
| T015 | Complete migrate_v1_to_v2() in versioning.py (add sentinel values, stamp v2) | WP03 | — |
| T016 | Create CharterBundleV2Migration(BaseMigration) in m_3_2_6_charter_bundle_v2.py | WP03 | — |
| T017 | Add _assert_bundle_compatible() to charter.py; call from status, resynthesize, validate | WP03 | — |
| T018 | Create test_charter_bundle_v2_migration.py (migration integration tests) | WP03 | — |
| T019 | Create test_charter_status_provenance.py (regression tests) | WP03 | — |
| T020 | Update test_schema_conformance.py for v2 schema version assertions | WP03 | — |

---

## Work Packages

### WP01 — Compatibility Registry and Bundle Schema Version Infrastructure

**Lane A** (parallel with WP02)  
**Phase**: Phase 1 — Foundation  
**Priority**: High  
**Dependencies**: None  
**Prompt**: [tasks/WP01-compatibility-registry-and-bundle-schema-version.md](tasks/WP01-compatibility-registry-and-bundle-schema-version.md)

**Goal**: Create `src/doctrine/versioning.py` with a compatibility registry, wire `bundle_schema_version` into `ExtractionMetadata`, and stamp the version on every new bundle.

**Included subtasks**:

- [x] T001 Create `src/doctrine/versioning.py`: constants, enums, dataclasses (WP01)
- [x] T002 Implement `check_bundle_compatibility()` in versioning.py (WP01)
- [x] T003 Implement `get_bundle_schema_version()` in versioning.py (WP01)
- [x] T004 Stub `migrate_v1_to_v2()` and `run_migration()` in versioning.py (WP01)
- [x] T005 Add `bundle_schema_version: int | None = None` to ExtractionMetadata (WP01)
- [x] T006 Stamp `bundle_schema_version = CURRENT_BUNDLE_SCHEMA_VERSION` in extractor.py (WP01)
- [x] T007 Write `tests/doctrine/test_versioning.py` (≥90% coverage) (WP01)

**Success criteria**:
- `check_bundle_compatibility(None)` → `MISSING_VERSION`
- `check_bundle_compatibility(2)` → `COMPATIBLE`
- `check_bundle_compatibility(3)` → `INCOMPATIBLE_NEW`
- `get_bundle_schema_version()` returns `None` when file absent or field missing
- `mypy --strict src/doctrine/versioning.py` passes with 0 errors
- `pytest tests/doctrine/test_versioning.py` achieves ≥90% coverage

---

### WP02 — ProvenanceEntry v2 and SynthesisManifest v2

**Lane B** (parallel with WP01)  
**Phase**: Phase 1 — Foundation  
**Priority**: High  
**Dependencies**: None  
**Prompt**: [tasks/WP02-provenance-entry-v2-and-synthesis-manifest-v2.md](tasks/WP02-provenance-entry-v2-and-synthesis-manifest-v2.md)

**Goal**: Harden the Pydantic models and synthesis pipeline so every fresh synthesis writes v2 sidecars with all mandatory fields populated. Update all fixtures and tests.

**Included subtasks**:

- [ ] T008 Bump ProvenanceEntry → schema_version Literal["2"]; add 5 new/promoted fields (WP02)
- [ ] T009 Bump SynthesisManifest → schema_version Literal["2"]; add synthesizer_version, manifest_hash (WP02)
- [ ] T010 Update provenance.py dump_yaml() to stamp produced_at at write time (WP02)
- [ ] T011 Update write_pipeline.py promote() to pass all v2 ProvenanceEntry fields; compute manifest_hash (WP02)
- [ ] T012 Update resynthesize_pipeline.py with same v2 provenance field additions (WP02)
- [ ] T013 Update YAML sidecar fixtures in tests/charter/fixtures/synthesizer/ (WP02)
- [ ] T014 Update test_provenance.py, test_manifest.py, test_adapter_contract.py for v2 (WP02)

**Success criteria**:
- `ProvenanceEntry(corpus_snapshot_id=None, ...)` raises `ValidationError`
- `ProvenanceEntry(synthesizer_version="", ...)` raises `ValidationError`
- `ProvenanceEntry(schema_version="1", ...)` raises `ValidationError`
- Fresh synthesis produces sidecars with all 6 new/promoted fields populated
- `manifest_hash` validates: strip field → re-hash → matches stored value
- `test_synthesize_path_parity.py` still passes (byte-stability regression)
- `mypy --strict` passes on all modified files

---

### WP03 — Upgrade Migration, Reader Blocks, and Full Test Suite

**Phase**: Phase 2 — Integration  
**Priority**: High  
**Dependencies**: WP01, WP02  
**Prompt**: [tasks/WP03-upgrade-migration-reader-blocks-and-tests.md](tasks/WP03-upgrade-migration-reader-blocks-and-tests.md)

**Goal**: Complete the v1→v2 migration implementation, add reader blocks to charter subcommands, wire the migration into `spec-kitty upgrade`, and verify with integration tests.

**Included subtasks**:

- [ ] T015 Complete migrate_v1_to_v2() in versioning.py (add sentinel values, stamp v2) (WP03)
- [ ] T016 Create CharterBundleV2Migration(BaseMigration) in m_3_2_6_charter_bundle_v2.py (WP03)
- [ ] T017 Add _assert_bundle_compatible() to charter.py; call from status, resynthesize, validate (WP03)
- [ ] T018 Create test_charter_bundle_v2_migration.py (migration integration tests) (WP03)
- [ ] T019 Create test_charter_status_provenance.py (regression tests) (WP03)
- [ ] T020 Update test_schema_conformance.py for v2 schema version assertions (WP03)

**Success criteria**:
- `CharterBundleV2Migration.detect(v1_project)` returns `True`; `detect(v2_project)` returns `False`
- Migration applies sentinel values to all v1 sidecar fields; result parses as `ProvenanceEntry` with `schema_version: "2"`
- Running migration twice: second run reports `changes_made=[]` (idempotent)
- `charter status` with v1 bundle: exits 1, error contains "spec-kitty upgrade"
- `charter status` with bundle_schema_version=99: exits 1
- `charter status --provenance` on v2 bundle: exits 0, includes `synthesizer_version` and `produced_at`
- All pre-existing `charter bundle validate` tests pass on v2 bundles

---

## Definition of Done

- [ ] `mypy --strict` passes across all new and modified modules (zero new type errors)
- [ ] `pytest tests/doctrine/test_versioning.py` passes, ≥90% coverage on `src/doctrine/versioning.py`
- [ ] `pytest tests/charter/synthesizer/` passes without regressions (including `test_synthesize_path_parity.py`)
- [ ] `pytest tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py` passes
- [ ] `pytest tests/specify_cli/cli/commands/test_charter_status_provenance.py` passes
- [ ] `spec-kitty charter status` on v1 bundle exits 1 with "spec-kitty upgrade" in message
- [ ] `spec-kitty charter status` on v2 bundle exits 0
- [ ] `spec-kitty charter bundle validate` fails on incomplete provenance sidecar
- [ ] `spec-kitty charter bundle validate` passes on complete v2 bundle
- [ ] `spec-kitty charter status --provenance` output unchanged from WP7.4 (regression)
- [ ] `spec-kitty upgrade` applies v1→v2 migration on synthetic v1 bundle
