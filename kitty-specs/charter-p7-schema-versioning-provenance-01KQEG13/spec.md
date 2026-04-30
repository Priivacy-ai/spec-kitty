# Charter Phase 7: Schema Versioning and Provenance Hardening

**Mission ID**: 01KQEG13YGZN77AMY6Q8DVNKQX  
**Mission slug**: charter-p7-schema-versioning-provenance-01KQEG13  
**Mission type**: software-dev  
**Target branch**: main  
**Parent issue**: #469 (Phase 7 of the Charter EPIC #461)  
**Implements issues**: #513 (WP7.1), #512 (WP7.2), #515 (WP7.3)  
**Regression-guard only**: #694 (WP7.4, already landed)

---

## Purpose

Charter synthesis bundles currently carry optional provenance fields and have no runtime mechanism to detect or migrate schema-incompatible bundles. Operators and CI systems cannot trust that a provenance record is complete, and there is no path for upgrading a bundle produced by an older version of the tool to meet the requirements of a newer one.

This mission hardens that surface by making provenance mandatory across all synthesized artifacts, adding a bundle-level integer schema version consumed by the upgrade pipeline, and creating a compatibility registry that maps old bundle versions to migration functions. The result is that CI and operators can trust provenance chains completely and that stale or incompatible bundles are detected and either migrated automatically or rejected with clear, actionable errors.

---

## Scope

**In scope** (spec-kitty product repository only):
- Bundle-level integer schema_version metadata added to charter `metadata.yaml` and consumed by the upgrade pipeline
- Compatibility registry (`src/doctrine/versioning.py`) with a supported-version range and at least one real migration function
- Provenance sidecar hardening: additional mandatory fields (`synthesizer_version`, `produced_at`, `bundle_hash`) and promotion of previously-optional fields to mandatory
- Fail-closed provenance validation: missing or malformed mandatory provenance fields must fail validation
- Tests: old-bundle migration, incompatible bundle blocking, provenance validation, and `charter status --provenance` regression coverage

**Out of scope**:
- Issues #832, #883, #649, #522, #534, #848
- Edit history and unified lifecycle state machine (deferred per #469)
- The external `charter` installed package, `spec-kitty-events`, `spec-kitty-runtime`, `spec-kitty-tracker` (no changes to those packages)
- Re-implementing `charter status --provenance` (WP7.4 is already landed; regression tests only)

---

## Actors

- **CLI operators**: Run `spec-kitty charter` subcommands to synthesize, validate, and inspect doctrine bundles
- **CI systems**: Invoke `spec-kitty charter bundle validate` and `spec-kitty charter status --provenance` to gate merges on provenance completeness
- **Upgrade pipeline**: The `spec-kitty upgrade` runner that reads bundle schema version and applies registered migrations
- **Future CLI releases**: Any CLI build that loads a previously-generated bundle must be able to determine compatibility immediately

---

## User Scenarios & Testing

### Primary scenario — Fresh synthesis produces complete provenance

A CI job runs `spec-kitty charter synthesize`. After synthesis, every artifact in `.kittify/charter/provenance/` carries a complete provenance sidecar including synthesizer version, corpus snapshot ID, produced-at timestamp, artifact content hash, and bundle/manifest hash. A subsequent `spec-kitty charter bundle validate` reports zero missing or malformed provenance entries.

### Scenario — Operator reads status with provenance detail

An operator runs `spec-kitty charter status --provenance`. The command succeeds, shows a table of provenance entries with their adapter, corpus snapshot ID, and evidence hash, and exits with code 0. The output shape matches what was established by WP7.4.

### Scenario — Old bundle is auto-migrated on upgrade

An operator upgrades from an older version of spec-kitty. On the next `spec-kitty upgrade`, the upgrade pipeline reads the bundle's integer schema_version, finds a registered migration function for that version, runs the migration, and writes the upgraded bundle. The operator receives a confirmation message and the bundle now carries the new schema version.

### Scenario — Incompatible bundle is blocked with a clear error

An operator attempts to use a bundle that is either too new for this CLI build or too old with no registered migration path. The CLI emits a clear error message identifying the bundle's schema version, the range this CLI supports, and the remediation action (either upgrade the CLI or run `spec-kitty upgrade`). The command exits with a non-zero code.

### Scenario — Validation rejects incomplete provenance

A test fixture or hand-crafted bundle is submitted to `spec-kitty charter bundle validate`. One artifact's provenance sidecar is missing the `synthesizer_version` field. Validation fails closed: the command reports the specific missing field and the artifact that triggered the failure, and exits with a non-zero code.

### Scenario — Existing CLI contracts are unchanged

An operator on a fully-migrated, Phase 7 bundle runs `spec-kitty charter sync`, `spec-kitty charter bundle validate`, and `spec-kitty charter status`. All commands succeed and produce the same output shape as before this mission was implemented.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | Every charter doctrine bundle carries an integer `schema_version` field in `metadata.yaml`. This integer is the compatibility version read by the upgrade pipeline — distinct from the existing semver string field. | Proposed |
| FR-002 | The upgrade pipeline reads the bundle integer `schema_version` before any other operation. Bundles whose version falls outside the CLI's declared supported range are blocked with a human-readable error and a non-zero exit code. | Proposed |
| FR-003 | A compatibility registry exists at `src/doctrine/versioning.py`. It maps each supported bundle schema version to: (a) the CLI version range that can read it, and (b) one or more migration functions that can upgrade a bundle from that version to the next. | Proposed |
| FR-004 | The compatibility registry contains at least one real, end-to-end tested migration function. The migration transforms a synthetic "old bundle" (version N) into a valid "new bundle" (version N+1). | Proposed |
| FR-005 | Every synthesized artifact provenance sidecar must carry all of the following mandatory fields: (a) `synthesizer_version` — the CLI version string of the spec-kitty build that ran synthesis; (b) `corpus_snapshot_id` — the identity of the source corpus snapshot (previously optional, now mandatory); (c) `source_input_ids` — the ordered list of source input identifiers used by the synthesis adapter; (d) `produced_at` — ISO 8601 UTC timestamp when the provenance record was written to disk; (e) `artifact_hash` — a content hash of the artifact file bytes at write time; (f) `bundle_hash` — a hash of the synthesis manifest at the time the sidecar is written. | Proposed |
| FR-006 | Provenance validation fails closed: any provenance sidecar with one or more missing or malformed mandatory fields causes the bundle validate command to exit with a non-zero code and report the specific field and artifact path. | Proposed |
| FR-007 | Bundles where any artifact listed in the synthesis manifest is missing its provenance sidecar file cause bundle validate to fail. | Proposed |
| FR-008 | A test suite covers the old-bundle migration path: a synthetic fixture representing a pre-Phase 7 bundle (no integer schema_version, optional provenance fields) is processed by the compatibility registry, the registered migration is applied, and the result passes full validation. | Proposed |
| FR-009 | A test suite covers incompatible bundle blocking: at minimum (a) a bundle too new for the current CLI and (b) a bundle too old with no registered migration path each produce the appropriate error and non-zero exit code. | Proposed |
| FR-010 | The existing `charter status --provenance` behavior established by WP7.4 is covered by regression tests that assert the command's output shape, field presence, and exit code under a valid Phase 7 bundle. | Proposed |
| FR-011 | All existing public `spec-kitty charter` subcommand interfaces maintain backward-compatible behavior on fully-migrated, Phase 7 bundles. No existing command changes its output schema or exit-code contract. | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Type safety: mypy --strict passes for all new and modified modules with zero new type errors. | 0 new type errors | Proposed |
| NFR-002 | Test coverage: 90% or greater line coverage for all new modules (compatibility registry, provenance validation, migration functions). | ≥ 90% | Proposed |
| NFR-003 | Performance: provenance validation of a full synthesis bundle of up to 50 artifacts completes in under 2 seconds without network calls. | < 2 s, no network I/O | Proposed |
| NFR-004 | Serialization stability: provenance sidecars hardened in this mission use the same canonical YAML serializer as existing sidecars; the byte-stability contract (NFR-006 of the charter synthesizer design) continues to hold. | No regressions in existing sidecar hash tests | Proposed |
| NFR-005 | Fail-closed security posture: the bundle validation gate rejects unrecognized schema versions deterministically without falling back to a permissive mode. | No permissive fallback for unknown versions | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Scope is the spec-kitty product repository only. No changes to external packages (`charter` installed at site-packages, `spec-kitty-events`, `spec-kitty-runtime`, `spec-kitty-tracker`). | Active |
| C-002 | WP7.4 (`charter status --provenance`) is already implemented and may not be removed or re-implemented; this mission adds regression tests for it only. | Active |
| C-003 | Do not modify, plan work for, or reference the following issues: #832, #883, #649, #522, #534, #848. | Active |
| C-004 | Edit history and unified lifecycle state machine remain out of scope per issue #469 ("they don't gate any FR1/2/3/4 capability"). | Active |
| C-005 | Existing public CLI contract: all `spec-kitty charter` subcommand output schemas and exit-code contracts must remain backward compatible on Phase 7 bundles. | Active |

---

## Success Criteria

1. Every synthesized artifact in all test fixtures carries a complete provenance sidecar with all mandatory Phase 7 fields — zero fixtures pass with incomplete provenance.
2. A synthetic "old bundle" fixture processed by the compatibility registry upgrades successfully to a valid Phase 7 bundle in the migration test suite.
3. Two incompatible-bundle scenarios (bundle too new, bundle too old without migration path) each produce the expected error and non-zero exit code in the test suite.
4. `spec-kitty charter bundle validate` exits with code 0 on a fully-synthesized Phase 7 bundle and code 1 on any bundle with missing or malformed provenance.
5. The `charter status --provenance` regression test suite passes on the same fixtures that pass bundle validate.
6. mypy --strict and pytest (≥ 90% coverage on new modules) both pass in CI with no regressions in existing tests.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| **Bundle integer schema_version** | An integer stored in `metadata.yaml` under the charter directory that declares the overall compatibility version of the synthesis bundle. Distinct from the existing semver string field. |
| **Compatibility registry** | A central mapping of bundle integer schema versions to supported CLI version ranges and migration functions. Lives in `src/doctrine/versioning.py`. |
| **Migration function** | A callable registered in the compatibility registry that accepts a bundle at version N and returns a bundle at version N+1. |
| **ProvenanceEntry** | Per-artifact provenance record stored as a YAML sidecar in `.kittify/charter/provenance/`. Phase 7 adds mandatory fields: `synthesizer_version`, `produced_at`, `bundle_hash`; promotes `corpus_snapshot_id` and related fields from optional to mandatory. |
| **SynthesisManifest** | Top-of-bundle commit marker at `.kittify/charter/synthesis-manifest.yaml`. Phase 7 may add a `synthesizer_version` field. |
| **Bundle validate gate** | The `charter bundle validate` command and the programmatic validation function it calls. Phase 7 must cause this gate to fail closed on incomplete provenance. |

---

## Assumptions

1. The `src/doctrine/versioning.py` path refers to a new module within the spec-kitty product repository (under `src/`), co-located with or adjacent to the existing `src/charter/` package. The exact package structure will be determined during planning.
2. "Bundle integer schema_version" is distinct from the existing `schema_version: 1.0.0` semver string in `metadata.yaml` and the per-artifact `schema_version: "1"` literal field. A new integer key (e.g., `bundle_schema_version`) is the most likely implementation approach.
3. The Phase 3 baseline for provenance (`src/charter/synthesizer/synthesize_pipeline.py` ProvenanceEntry) is the starting point; hardening adds fields and promotes optionals to mandatories.
4. "Fails closed" means: any code path that cannot verify complete provenance returns an error, never silently proceeds as if provenance were valid.
5. Pre-Phase 7 bundles (no integer schema_version, i.e. `bundle_schema_version` absent from `metadata.yaml`) are treated as version 1 (`MISSING_VERSION` → `needs_migration=True`) by the compatibility registry. Treating them as version 0 would require a two-hop migration. Version 0 and negative versions are classified as `INCOMPATIBLE_OLD` (below `MIN_READABLE_BUNDLE_SCHEMA=1`) with no registered migration path — those produce a hard block, not a migration offer.

---

## Open Questions

None. All decisions resolved through issue analysis and codebase research.
