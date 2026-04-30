# Quickstart: Charter Phase 7 Implementation

**Mission**: charter-p7-schema-versioning-provenance-01KQEG13

---

## For the implementing agent

### What you are building

Three things that form a complete loop:

1. **A compatibility registry** at `src/doctrine/versioning.py` that says what bundle schema versions this CLI supports and how to migrate old ones.

2. **A hardened provenance model** — `ProvenanceEntry` and `SynthesisManifest` both bump from schema version "1" to "2" and gain mandatory fields that were previously optional or absent.

3. **An upgrade integration** — `spec-kitty upgrade` gains a new migration step that applies the v1→v2 bundle migration; charter subcommands gain a reader check that blocks incompatible bundles with a clear "run `spec-kitty upgrade`" error.

### How to verify locally after each WP

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260430-080211-mjXhys/spec-kitty

# Type-check
cd src && mypy --strict doctrine/versioning.py charter/synthesizer/synthesize_pipeline.py charter/synthesizer/manifest.py charter/schemas.py
cd ..

# Run targeted tests
pytest tests/doctrine/test_versioning.py -v
pytest tests/charter/synthesizer/test_provenance.py tests/charter/synthesizer/test_manifest.py -v
pytest tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py -v

# Full test suite (must not regress)
cd src && pytest ../tests/ -x -q
```

---

## Work Package Summary

### WP01 — Compatibility registry + bundle schema_version infrastructure
**Lane A** (parallel with WP02)

**Deliverables:**
- `src/doctrine/versioning.py` (new file) — compatibility registry, version constants, `check_bundle_compatibility()`, `get_bundle_schema_version()`, migration stubs (actual migration logic can be a stub; WP03 completes it)
- `src/charter/schemas.py` — add `bundle_schema_version: int | None = None` to `ExtractionMetadata`
- `src/charter/extractor.py` — stamp `bundle_schema_version = CURRENT_BUNDLE_SCHEMA_VERSION` when writing `metadata.yaml`
- `tests/doctrine/test_versioning.py` (new file) — unit tests for compatibility registry

**Key correctness invariants:**
- `check_bundle_compatibility(None)` returns `MISSING_VERSION` (not an error type — it's the migration-needed type)
- `check_bundle_compatibility(2)` returns `COMPATIBLE`
- `check_bundle_compatibility(3)` returns `INCOMPATIBLE_NEW`
- `check_bundle_compatibility(0)` returns `INCOMPATIBLE_OLD` (no migration registered for version 0)
- `get_bundle_schema_version()` returns `None` when file absent or field missing (never raises)

### WP02 — ProvenanceEntry v2 + SynthesisManifest v2
**Lane B** (parallel with WP01)

**Files to modify:**
- `src/charter/synthesizer/synthesize_pipeline.py` — `ProvenanceEntry`: add 5 new/promoted fields, bump schema_version to `Literal["2"]`
- `src/charter/synthesizer/manifest.py` — `SynthesisManifest`: add `synthesizer_version`, `manifest_hash`, bump schema_version to `Literal["2"]`
- `src/charter/synthesizer/provenance.py` — `dump_yaml()`: stamp `produced_at = datetime.now(UTC).isoformat()`
- `src/charter/synthesizer/write_pipeline.py` — pass `synthesis_run_id`, `synthesizer_version` into `ProvenanceEntry` construction; compute and set `manifest_hash` on `SynthesisManifest`
- `src/charter/synthesizer/resynthesize_pipeline.py` — same provenance field additions as write_pipeline.py

**Fixture updates (mandatory):**
- `tests/charter/fixtures/synthesizer/` — update all sidecar YAML fixtures to include v2 fields
- `tests/charter/synthesizer/conftest.py` — update any ProvenanceEntry factories
- `tests/charter/synthesizer/test_provenance.py` — update for v2 assertions
- `tests/charter/synthesizer/test_manifest.py` — update for v2 assertions

**Key correctness invariants:**
- `ProvenanceEntry(**v2_fields).schema_version == "2"` (Pydantic Literal enforces this)
- `ProvenanceEntry(corpus_snapshot_id=None)` raises `ValidationError`
- `ProvenanceEntry(synthesizer_version="")` raises `ValidationError` (minLength equivalent — use `@validator` or `Field(min_length=1)`)
- `manifest_hash` computation is stable: given the same manifest fields, two runs produce the same hash
- Existing `test_synthesize_path_parity.py` still passes (NFR-006 byte-stability)

### WP03 — Upgrade migration + reader blocks + full test suite
**Depends on WP01 and WP02**

**Files to create/modify:**
- `src/specify_cli/upgrade/migrations/m_3_2_6_charter_bundle_v2.py` (new) — `CharterBundleV2Migration` implementing `BaseMigration`, calling `doctrine.versioning.run_migration()`
- `src/doctrine/versioning.py` — complete `migrate_v1_to_v2()` implementation (WP01 may stub it; WP03 completes it)
- `src/specify_cli/cli/commands/charter.py` — add `_check_bundle_schema_version(repo_root)` helper and call it from `status`, `charter_synthesize` (for the "re-synthesize existing bundle" path), `charter_resynthesize`, and the `bundle validate` path
- `tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py` (new) — migration tests
- `tests/specify_cli/cli/commands/test_charter_bundle_status_provenance.py` (new or update) — regression tests for `charter status --provenance`
- `tests/charter/synthesizer/test_schema_conformance.py` — update schema conformance tests for v2

**Key correctness invariants (from spec):**
- Reader block: `charter status` with a v1 bundle in `.kittify/charter/metadata.yaml` exits code 1 with "run `spec-kitty upgrade`" in stderr
- Reader block: `charter status` with a v3+ bundle exits code 1 with "upgrade your CLI" message
- Migration: applying `CharterBundleV2Migration` to a synthetic v1 bundle produces a valid v2 bundle (all provenance sidecars parse as `ProvenanceEntry` with `schema_version: "2"`)
- Migration idempotency: running the migration twice on the same bundle produces the same result and reports `changes_made=[]` on second run
- Regression: `charter status --provenance` on a valid v2 bundle exits 0 and includes `schema_version`, `synthesizer_version`, `produced_at` in the per-entry detail
- All pre-existing `charter bundle validate` tests continue to pass on v2 bundles

---

## Critical call paths to update in write_pipeline.py

The `promote()` function builds `ProvenanceEntry` objects for each artifact. After WP02:

```python
# Before: (v1)
entry = ProvenanceEntry(
    schema_version="1",
    ...
    corpus_snapshot_id=corpus_id,      # was Optional
    evidence_bundle_hash=evidence_hash, # was Optional
)

# After: (v2) — new mandatory fields highlighted
entry = ProvenanceEntry(
    schema_version="2",
    ...
    synthesizer_version=specify_cli.__version__,   # NEW
    source_input_ids=list(source.source_urns),     # NEW (mirrors source_urns for Phase 7)
    produced_at="<filled by dump_yaml at write time>",  # NEW — set in provenance.dump_yaml
    corpus_snapshot_id=corpus_id or "(none)",      # PROMOTED (str not Optional)
    synthesis_run_id=staging_dir.run_id,           # NEW
    evidence_bundle_hash=evidence_hash,            # unchanged (stays Optional)
)
```

The `produced_at` field is set by `provenance.dump_yaml()` at the moment of write, not in the `ProvenanceEntry` constructor. This matches the semantic: `generated_at` = when the adapter produced the content; `produced_at` = when the sidecar was written to disk.

Implementation note: either (a) make `produced_at` an optional field in the model with a factory default of `lambda: datetime.now(UTC).isoformat()`, or (b) pass it from `dump_yaml`. Option (b) keeps the model frozen/immutable (ConfigDict frozen=True). The current model IS frozen, so option (b) is required: the caller creates the entry with `produced_at=datetime.now(UTC).isoformat()` at call time.
