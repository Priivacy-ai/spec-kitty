# Research: Charter Phase 7 Schema Versioning and Provenance Hardening

**Mission**: charter-p7-schema-versioning-provenance-01KQEG13  
**Date**: 2026-04-30

---

## Codebase Inventory

### Package layout (from pyproject.toml `[tool.hatch.build.targets.wheel]`)
- `src/charter` — charter library (extractor, synthesizer, bundle manifest, schemas)
- `src/doctrine` — doctrine layer (artifact models, DRG, missions, agent profiles)
- `src/specify_cli` — CLI harness (typer commands, upgrade runner, migration system)
- `src/kernel` — kernel utilities

All four are shipped in the same `spec-kitty-cli` wheel. `src/doctrine/` already exists; `src/doctrine/versioning.py` is a new file, not a new package.

### `src/charter/schemas.py` — `ExtractionMetadata`
The `ExtractionMetadata` Pydantic model represents `.kittify/charter/metadata.yaml` content. It currently has:
- `schema_version: str = "1.0.0"` — YAML document format version (semver string, extraction-format concern)
- `extracted_at`, `charter_hash`, `source_path`, `extraction_mode`, `sections_parsed`

**Decision**: Add `bundle_schema_version: int | None = None` as a new optional integer field. The existing `schema_version` semver string is retained (it tracks the extraction YAML format). The new integer tracks overall bundle compatibility for the upgrade pipeline.

### `src/charter/synthesizer/synthesize_pipeline.py` — `ProvenanceEntry`
Current Phase 3 baseline (v1):
- `schema_version: Literal["1"] = "1"` — per-sidecar format version
- `artifact_urn`, `artifact_kind`, `artifact_slug` — identity
- `artifact_content_hash: str` — BLAKE3/SHA-256 hash, mandatory, already correct
- `inputs_hash: str` — hash of the normalized SynthesisRequest
- `adapter_id`, `adapter_version` — synthesis adapter identity
- `source_section: str | None`, `source_urns: list[str]` — source pointers
- `generated_at: str` — when adapter generated the content
- `adapter_notes: str | None = None`
- `evidence_bundle_hash: str | None = None` — optional (not all synthesis has evidence bundles)
- `corpus_snapshot_id: str | None = None` — optional snapshot ID

Fields promoted/added in Phase 7 (v2):
- `schema_version` bumped to `Literal["2"] = "2"`
- `synthesizer_version: str` — mandatory, from `specify_cli.__version__`
- `corpus_snapshot_id: str` — promoted to mandatory (use `"(none)"` sentinel when no snapshot)
- `source_input_ids: list[str]` — mandatory, the ordered input IDs. For the initial implementation these mirror `source_urns` (same list). Can be specialized later without a schema_version bump.
- `produced_at: str` — mandatory ISO 8601 UTC, written at sidecar-write time (in `provenance.dump_yaml`)
- `synthesis_run_id: str` — mandatory, the `StagingDir.run_id` ULID

`evidence_bundle_hash` stays `str | None = None` — not all synthesis pipelines have evidence bundles; requiring it for all would break synthesis use-cases that don't use the evidence layer.

**Note on `artifact_hash`**: The spec requires an "artifact hash". The existing `artifact_content_hash` field already carries the canonical hash of the artifact file bytes (as `canonical_yaml(body)`). The new `produced_at` timestamp is when the sidecar file is written, not when the artifact content was hashed. No separate `artifact_hash` field is added; `artifact_content_hash` satisfies FR-005(e).

**Note on `bundle_hash`**: The spec requires "bundle/manifest hash where applicable". This is satisfied by `synthesis_run_id` (links the sidecar to the manifest unambiguously) combined with `manifest_hash` on `SynthesisManifest`. A direct circular hash on the sidecar would require a two-pass write that would break NFR-006 byte-stability.

### `src/charter/synthesizer/manifest.py` — `SynthesisManifest`
Current v1:
- `schema_version: Literal["1"] = "1"`
- `mission_id: str | None`, `created_at: str`, `run_id: str`
- `adapter_id: str`, `adapter_version: str`
- `artifacts: list[ManifestArtifactEntry]`

Phase 7 (v2) additions:
- `schema_version: Literal["2"] = "2"`
- `synthesizer_version: str` — mandatory, from `specify_cli.__version__`
- `manifest_hash: str` — mandatory, SHA-256 of `canonical_yaml(manifest_without_manifest_hash_field)`

### `src/charter/synthesizer/write_pipeline.py` — `promote()`
The write pipeline assembles provenance entries in memory and then calls `dump_provenance`. The `run_id` is available from `staging_dir.run_id`. The `synthesizer_version` is available from `specify_cli.__version__`. The `produced_at` is stamped at write time in `provenance.dump_yaml`. The `manifest_hash` is computed after the manifest dict is assembled but before the YAML bytes are written.

### `src/specify_cli/__init__.py` — version export
`specify_cli.__version__` is available (read from `importlib.metadata` when installed, falls back to env var `SPEC_KITTY_CLI_VERSION` or `"0.5.0-dev"` in development). This is the value to use as `synthesizer_version`.

### Upgrade runner pattern (`src/specify_cli/upgrade/migrations/base.py`)
`BaseMigration` provides:
- `migration_id: str` — identifier, format `"{version}_{short_description}"`
- `description: str`
- `detect(project_path: Path) -> bool` — returns True if migration is needed
- `apply(project_path: Path, dry_run: bool) -> MigrationResult`

The charter bundle migration will follow this pattern, checking for `bundle_schema_version` absent or < 2 in `.kittify/charter/metadata.yaml`.

### Charter command version-check pattern
`src/specify_cli/cli/commands/charter.py` already uses `_resolve_charter_path()` which raises with a message including "or 'spec-kitty upgrade' if migrating from an older version." The new version-check adds to this pattern: after loading the bundle's `metadata.yaml`, call `check_bundle_compatibility(metadata.bundle_schema_version)` and raise a `TaskCliError` with actionable text if incompatible.

---

## Key Decisions

| # | Decision | Rationale | Alternatives considered |
|---|----------|-----------|------------------------|
| 1 | New `bundle_schema_version: int` field in `ExtractionMetadata` (not replacing `schema_version: str`) | Additive change; existing `schema_version: "1.0.0"` serves a different purpose (extraction format). Breaking the semver field would require a migration just to rename a field. | Replace semver with integer: risks breaking any reader that imports `ExtractionMetadata.schema_version` as a string |
| 2 | `synthesis_run_id: str` on ProvenanceEntry instead of `bundle_hash` as a direct file hash | No circular write dependency; `run_id` + `manifest_hash` on the manifest satisfies the audit requirement. Direct hash would require two-pass write, breaking NFR-006. | Two-pass write with manifest hash back-fill: breaks byte-stability contract |
| 3 | `evidence_bundle_hash` stays Optional | Not all synthesis uses evidence bundles. Requiring it universally would block non-evidence synthesis pipelines. | Make mandatory with `"(none)"` sentinel: harder to distinguish "no evidence" from "unknown" |
| 4 | Pre-Phase 7 bundles treated as v1 (not v0 absent) | The existing charter bundle has `schema_version: "1"` on sidecars, so it is logically version 1 even if `bundle_schema_version` field is absent from metadata.yaml. The compatibility registry can treat `bundle_schema_version = None` as equivalent to v1. | Treat as v0 requiring two sequential migrations: unnecessary complexity, no benefit |
| 5 | Migration trigger: reader blocks + `spec-kitty upgrade` applies | Consistent with project schema_version UX. No new CLI command surface. | `spec-kitty charter migrate-bundle`: extra surface, same migration code |
| 6 | `src/doctrine/versioning.py` as a free-standing module in the `doctrine` package | `src/doctrine/` already exists and is in the same wheel. Keeps versioning concern close to doctrine artifact layer (the consumer side). | `src/charter/versioning.py`: mixes charter library concern with version gating; `src/specify_cli/charter/versioning.py`: duplicates path |
| 7 | `corpus_snapshot_id` promoted to `str`, sentinel `"(none)"` for no-snapshot runs | Fails closed on absent field (Pydantic validation catches missing str). Distinguishes "no snapshot this run" from "field not present" without making the migration impossible. | Keep Optional: silently allows missing values, undermines fail-closed goal |

---

## Pre-existing Tests to Preserve

- `tests/charter/synthesizer/test_provenance.py` — must update for v2 fields
- `tests/charter/synthesizer/test_manifest.py` — must update for v2 fields
- `tests/charter/synthesizer/test_adapter_contract.py` — may need v2 fixture updates
- `tests/charter/synthesizer/test_write_pipeline.py` — must pass with v2 sidecars
- `tests/charter/synthesizer/test_synthesize_path_parity.py` — byte-stability regression
- All existing `charter bundle validate` tests — must still pass on v2 bundles

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Existing fixture snapshots break when ProvenanceEntry bumps schema_version to "2" | Update all synthetic fixtures in `tests/charter/fixtures/synthesizer/` as part of WP02 |
| `evidence_bundle_hash: str | None` stays optional but `corpus_snapshot_id: str` becomes mandatory — synthesis runs that never had a corpus snapshot will fail unless the synthesizer pipeline passes `"(none)"` explicitly | Audit every `ProvenanceEntry(...)` construction call in `write_pipeline.py` and `resynthesize_pipeline.py` to confirm `corpus_snapshot_id` is always set |
| `manifest_hash` self-hash computation: any change to the manifest YAML structure after `manifest_hash` is computed will produce a hash mismatch at validation | Compute `manifest_hash` as the very last operation before serializing the manifest dict; freeze the dict with a deepcopy |
| `synthesis_run_id` not available at sidecar-assembly time in `resynthesize_pipeline.py` | Verify that `resynthesize_pipeline.py` also has access to `run_id` (it uses StagingDir similarly) |
