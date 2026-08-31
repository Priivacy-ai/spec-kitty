# Implementation Plan: Charter Phase 7 Schema Versioning and Provenance Hardening

**Mission**: charter-p7-schema-versioning-provenance-01KQEG13  
**Mission ID**: 01KQEG13YGZN77AMY6Q8DVNKQX  
**Branch**: `main` → merge to `main`  
**Date**: 2026-04-30  
**Spec**: [spec.md](spec.md)  
**Parent issues**: #469, #513, #512, #515, #694 (regression only)

---

## Summary

Charter synthesis bundles currently carry optional provenance fields and have no runtime compatibility gating. This mission adds: (1) `src/doctrine/versioning.py` with a bundle-version compatibility registry and a v1→v2 migration, (2) `ProvenanceEntry` and `SynthesisManifest` Pydantic models hardened to `schema_version: "2"` with new mandatory fields, and (3) upgrade pipeline integration so `spec-kitty upgrade` applies the migration and charter subcommands block on incompatible bundles. Tests cover old-bundle migration, incompatible-bundle blocking, provenance validation, and `charter status --provenance` regression.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pydantic (models), ruamel.yaml (YAML IO), typer/rich (CLI), mypy --strict  
**Storage**: Filesystem only — `.kittify/charter/` YAML bundle, `.kittify/metadata.yaml`  
**Testing**: pytest, ≥ 90% line coverage on new modules, integration tests for CLI commands  
**Target Platform**: All (Linux/macOS/Windows)  
**Performance Goals**: Provenance validation of 50-artifact bundle in < 2 s, no network I/O  
**Constraints**: No changes to external packages (charter site-packages, spec-kitty-events, spec-kitty-runtime, spec-kitty-tracker). All existing public CLI contracts must be preserved.  
**Scale/Scope**: ~6 modified files + 3 new files + fixture updates across `src/charter/`, `src/doctrine/`, `src/specify_cli/`

---

## Charter Check

Project charter requirements verified:
- ✅ typer for CLI — all CLI changes use typer
- ✅ rich for console output — error messages use `console.print()` with rich markup
- ✅ ruamel.yaml for YAML parsing — all YAML reads/writes use ruamel.yaml (existing pattern)
- ✅ pytest with ≥ 90% coverage — 3 new test modules, all targeting ≥ 90% coverage
- ✅ mypy --strict — all new/modified modules must pass mypy --strict
- ✅ Integration tests for CLI commands — WP03 includes integration tests for `charter status` reader block

No charter violations.

---

## Branch Contract

- **Current branch at plan start**: `main`
- **Planning/base branch**: `main`
- **Final merge target for completed changes**: `main`
- `branch_matches_target`: true

---

## Project Structure

### Planning artifacts (this mission)

```
kitty-specs/charter-p7-schema-versioning-provenance-01KQEG13/
├── spec.md                          # Requirements
├── plan.md                          # This file
├── research.md                      # Codebase research and decisions
├── data-model.md                    # Entity model (ProvenanceEntry v2, etc.)
├── quickstart.md                    # Implementation guide for agents
├── contracts/
│   ├── provenance-entry-v2.schema.yaml
│   ├── synthesis-manifest-v2.schema.yaml
│   └── bundle-compatibility-api.schema.yaml
└── tasks.md                         # Created by /spec-kitty.tasks (not yet)
```

### Source code layout

```
src/
├── doctrine/
│   └── versioning.py                # NEW: compatibility registry
├── charter/
│   ├── schemas.py                   # MODIFY: add bundle_schema_version to ExtractionMetadata
│   ├── extractor.py                 # MODIFY: stamp bundle_schema_version on sync
│   └── synthesizer/
│       ├── synthesize_pipeline.py   # MODIFY: ProvenanceEntry v2
│       ├── manifest.py              # MODIFY: SynthesisManifest v2
│       ├── provenance.py            # MODIFY: stamp produced_at at write time
│       ├── write_pipeline.py        # MODIFY: pass new fields to ProvenanceEntry
│       └── resynthesize_pipeline.py # MODIFY: same as write_pipeline.py
└── specify_cli/
    ├── cli/commands/charter.py      # MODIFY: reader block helper
    └── upgrade/migrations/
        └── m_3_2_6_charter_bundle_v2.py  # NEW: BaseMigration subclass

tests/
├── doctrine/
│   └── test_versioning.py           # NEW
├── charter/
│   ├── synthesizer/
│   │   ├── test_provenance.py       # MODIFY
│   │   ├── test_manifest.py         # MODIFY
│   │   ├── test_adapter_contract.py # MODIFY
│   │   ├── test_schema_conformance.py # MODIFY
│   │   └── fixtures/synthesizer/   # MODIFY (YAML sidecar fixtures)
└── specify_cli/
    ├── upgrade/
    │   └── test_charter_bundle_v2_migration.py  # NEW
    └── cli/commands/
        └── test_charter_status_provenance.py    # NEW
```

---

## Key Decision: Bundle Migration Trigger

**DM-01KQEG9HTZ8RSZW4D50CN8V6CJ — Resolved as Option C**

Normal charter commands check `bundle_schema_version` and block if incompatible. `spec-kitty upgrade` is the single migration entry point. No new `charter migrate-bundle` command. Tests cover both the reader block and the upgrade migration path.

Contract:
- `charter status`, `charter bundle validate`, `charter resynthesize` call `_assert_bundle_compatible()` before touching the doctrine bundle
- `charter sync` and fresh `charter synthesize` (building from scratch) do NOT need the reader block
- `spec-kitty upgrade` runs `CharterBundleV2Migration` which calls `doctrine.versioning.run_migration()`

---

## Work Packages

### WP01 — Compatibility registry + bundle schema_version infrastructure

**Lane A** (independent, no WP dependencies)  
**Closes**: FR-001, FR-002, FR-003 (registry), partial FR-004 (stubs)

**Files to create/modify**:

| Action | Path | Description |
|--------|------|-------------|
| CREATE | `src/doctrine/versioning.py` | Compatibility registry, version constants, `check_bundle_compatibility()`, `get_bundle_schema_version()`, migration registration, `migrate_v1_to_v2()` stub |
| MODIFY | `src/charter/schemas.py` | Add `bundle_schema_version: int \| None = None` to `ExtractionMetadata` |
| MODIFY | `src/charter/extractor.py` | Stamp `bundle_schema_version = CURRENT_BUNDLE_SCHEMA_VERSION` when writing `metadata.yaml` |
| CREATE | `tests/doctrine/test_versioning.py` | Unit tests for compatibility registry |

**Acceptance criteria**:
1. `check_bundle_compatibility(None)` → `MISSING_VERSION`, exit_code=1
2. `check_bundle_compatibility(2)` → `COMPATIBLE`, exit_code=0
3. `check_bundle_compatibility(3)` → `INCOMPATIBLE_NEW`, exit_code=1
4. `check_bundle_compatibility(0)` → `INCOMPATIBLE_OLD`, exit_code=1
5. `get_bundle_schema_version(charter_dir)` returns `None` when file absent or field absent
6. `ExtractionMetadata(**without_bundle_schema_version)` parses without error (field optional, None default)
7. `ExtractionMetadata(bundle_schema_version=2)` round-trips through ruamel.yaml
8. `mypy --strict src/doctrine/versioning.py` passes
9. `tests/doctrine/test_versioning.py` achieves ≥ 90% coverage of `versioning.py`

---

### WP02 — ProvenanceEntry v2 + SynthesisManifest v2

**Lane B** (independent, no WP dependencies)  
**Closes**: FR-005, FR-006

**Files to modify**:

| Action | Path | Description |
|--------|------|-------------|
| MODIFY | `src/charter/synthesizer/synthesize_pipeline.py` | Bump `schema_version` Literal to "2"; add `synthesizer_version`, `source_input_ids`, `produced_at`, `synthesis_run_id`; promote `corpus_snapshot_id` to mandatory str |
| MODIFY | `src/charter/synthesizer/manifest.py` | Bump `schema_version` to "2"; add `synthesizer_version`, `manifest_hash` |
| MODIFY | `src/charter/synthesizer/provenance.py` | `dump_yaml()` sets `produced_at` at write time; pass through new fields |
| MODIFY | `src/charter/synthesizer/write_pipeline.py` | Pass `synthesizer_version`, `synthesis_run_id`, `corpus_snapshot_id or "(none)"`, `produced_at`, `source_input_ids`; compute and set `manifest_hash` |
| MODIFY | `src/charter/synthesizer/resynthesize_pipeline.py` | Same provenance field additions as write_pipeline.py |
| MODIFY | `tests/charter/synthesizer/test_provenance.py` | Update assertions for v2 fields |
| MODIFY | `tests/charter/synthesizer/test_manifest.py` | Update assertions for v2 fields |
| MODIFY | `tests/charter/synthesizer/test_adapter_contract.py` | Update fixtures |
| MODIFY | `tests/charter/fixtures/synthesizer/` | Update all YAML sidecar fixtures to include v2 fields |

**Acceptance criteria**:
1. `ProvenanceEntry(schema_version="2", ..., corpus_snapshot_id=None)` raises `ValidationError`
2. `ProvenanceEntry(schema_version="2", ..., synthesizer_version="")` raises `ValidationError` (empty string disallowed — add `Field(min_length=1)` or `@field_validator`)
3. `ProvenanceEntry(schema_version="1", ...)` raises `ValidationError` (Literal["2"] enforces this)
4. Fresh synthesis produces sidecars with all 6 new/promoted fields populated with real values
5. `produced_at` field in sidecar is set by `dump_yaml()` at write time (not by factory default)
6. `manifest_hash` validates: load manifest → strip field → re-hash → matches stored value
7. `test_synthesize_path_parity.py` still passes (NFR-004 byte-stability regression)
8. All existing tests in `tests/charter/synthesizer/` pass with updated fixtures
9. `mypy --strict` passes on all modified files

**Critical note on `produced_at`**: The `ProvenanceEntry` model is frozen (`ConfigDict(frozen=True)`). `produced_at` must be passed by the caller (`write_pipeline.promote()`) at the moment of write, not via a factory default. The caller stamps `datetime.now(UTC).isoformat()` and passes it to the constructor.

**Critical note on `manifest_hash`**: Computed as `sha256(canonical_yaml({all_manifest_fields_except_manifest_hash})).hexdigest()`. Because `SynthesisManifest` is also frozen, use `manifest.model_dump(mode="python")`, pop the `manifest_hash` key, compute the hash, then create the final manifest instance with `manifest_hash` set.

---

### WP03 — Upgrade migration + reader blocks + full test suite

**Depends on**: WP01 merged (for `doctrine.versioning` imports) AND WP02 merged (for v2 model definitions)  
**Closes**: FR-004 (complete migration), FR-007, FR-008, FR-009, FR-010, FR-011

**Files to create/modify**:

| Action | Path | Description |
|--------|------|-------------|
| COMPLETE | `src/doctrine/versioning.py` | Complete `migrate_v1_to_v2()` implementation (WP01 may stub; WP03 completes) |
| CREATE | `src/specify_cli/upgrade/migrations/m_3_2_6_charter_bundle_v2.py` | `CharterBundleV2Migration(BaseMigration)` |
| MODIFY | `src/specify_cli/cli/commands/charter.py` | Add `_assert_bundle_compatible()` helper; call from `status`, `charter_resynthesize`, `bundle validate` path |
| CREATE | `tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py` | Migration integration tests with synthetic v1 bundle fixture |
| CREATE | `tests/specify_cli/cli/commands/test_charter_status_provenance.py` | Regression tests for `charter status --provenance` |
| MODIFY | `tests/charter/synthesizer/test_schema_conformance.py` | Update schema version assertions |

**Acceptance criteria**:
1. `CharterBundleV2Migration.detect(v1_project)` returns `True`
2. `CharterBundleV2Migration.detect(v2_project)` returns `False`
3. `CharterBundleV2Migration.apply(v1_project)` produces: all sidecars parse as `ProvenanceEntry` with `schema_version: "2"`, manifest parses as `SynthesisManifest` with `schema_version: "2"`, `metadata.yaml` has `bundle_schema_version: 2`
4. Running migration twice returns `changes_made=[]` on second run (idempotent)
5. `spec-kitty charter status` with v1 bundle: exits 1, error message contains "spec-kitty upgrade"
6. `spec-kitty charter status` with future version bundle (e.g., `bundle_schema_version: 99`): exits 1, error message contains "upgrade"
7. `spec-kitty charter bundle validate` on a sidecar missing `synthesizer_version`: exits 1, reports missing field and artifact path
8. `spec-kitty charter bundle validate` on a sidecar where a manifest-listed artifact has no sidecar file: exits 1
9. `spec-kitty charter status --provenance` on a valid v2 bundle: exits 0, JSON output includes `synthesizer_version` and `produced_at` per entry (regression guard for WP7.4)
10. All pre-existing `charter bundle validate` tests continue to pass

**`_assert_bundle_compatible` placement**:
- ✅ `status()` — when charter is `available` (has metadata.yaml) 
- ✅ `charter_resynthesize()` — reads existing bundle 
- ✅ `charter_bundle.py` `validate()` — validates the doctrine bundle
- ❌ `charter sync` — operates on charter.md, not the doctrine bundle
- ❌ Fresh `charter synthesize` (first run) — creates a new v2 bundle; not blocked

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Fixture YAML snapshots break when schema_version bumps to "2" | High | Medium | WP02 agent audits and updates all fixture files in `tests/charter/fixtures/synthesizer/` |
| `corpus_snapshot_id` promotion to mandatory str breaks synthesis runs with no snapshot | Medium | High | Audit all `ProvenanceEntry(...)` construction calls; add `or "(none)"` at each site |
| `manifest_hash` circular frozen-model issue | Low | Medium | Build via `model_dump`, pop key, hash, then reconstruct with `manifest_hash` set |
| `synthesis_run_id` not threaded through `resynthesize_pipeline.py` | Low | Medium | WP02 agent checks `resynthesize_pipeline.py` explicitly for StagingDir.run_id access |
| Circular import: `charter.py` → `doctrine.versioning` → unknown | Low | Medium | `doctrine` has no dependency on `charter`; import direction is charter→doctrine, safe |
| Reader block fires on fresh `charter synthesize` (no prior bundle) | Low | Medium | Only call `_assert_bundle_compatible` if `metadata.yaml` exists and has `bundle_schema_version` |

---

## Definition of Done

- [ ] `mypy --strict` passes across all new and modified modules (zero new type errors)
- [ ] `pytest tests/doctrine/test_versioning.py` passes, ≥ 90% coverage on `src/doctrine/versioning.py`
- [ ] `pytest tests/charter/synthesizer/` passes without regressions (including `test_synthesize_path_parity.py`)
- [ ] `pytest tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py` passes
- [ ] `pytest tests/specify_cli/cli/commands/test_charter_status_provenance.py` passes
- [ ] `spec-kitty charter status` on v1 bundle exits 1 with "spec-kitty upgrade" in message
- [ ] `spec-kitty charter status` on v2 bundle exits 0
- [ ] `spec-kitty charter bundle validate` fails on incomplete provenance sidecar
- [ ] `spec-kitty charter bundle validate` passes on complete v2 bundle
- [ ] `spec-kitty charter status --provenance` output unchanged from WP7.4 (regression)
- [ ] `spec-kitty upgrade` applies v1→v2 migration on synthetic v1 bundle

---

## Final Branch Contract

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- All work packages implement on `main` via the standard Spec Kitty lane workflow
