# Contract: `CharterBundleManifest` v2 (`src/charter/bundle.py`)

## Changes
- `SCHEMA_VERSION`: `"1.0.0"` → `"2.0.0"` (single bump; C-004).
- `BUNDLE_CONTENT_HASH_FILES`: `("governance.yaml","directives.yaml","references.yaml","metadata.yaml")` → `("charter.yaml",)`.
- `CANONICAL_MANIFEST.tracked_files`: `[charter.md]` → `[charter.md, charter.yaml]`.
- `content_hash_files` (**NEW field**, sourced from `BUNDLE_CONTENT_HASH_FILES`): `[charter.yaml]` — a field **distinct** from `derived_files`.
- `derived_files` / `derivation_sources`: `[]` / `{}` — nothing generated-and-gitignored remains in the charter bundle. **`charter.yaml` is NOT placed in `derived_files`.**
- `gitignore_required_entries`: the four bundle files removed.

## Guarantees
- **M1**: the content-hash input set is `content_hash_files == {charter.yaml}`, held in a field **distinct** from `derived_files` (they were always distinct — that distinction is literally the historic 4-vs-3 mismatch). `derived_files == {}`.
- **M2**: `CharterBundleManifest._validate`'s `tracked ∩ derived = ∅` invariant is **preserved untouched** — `charter.yaml` appears only in `tracked_files`, never in `derived_files`. (Do NOT relax the disjointness rule; keeping "authored ≠ generated" meaningful is the point.)
- **M3**: `compute_bundle_content_hash` hashes exactly the `content_hash_files` (`charter.yaml`) via the unchanged per-file recipe (BOM-strip/CRLF); write-side stampers (`write_pipeline.py:685`, `resynthesize_pipeline.py:205`) and the freshness reader (`computer.py`) route the same single recipe — minimal call-site edits (NFR-001).
- **M4**: the shared `charter.yaml` filename constant is the single source consumed by all charter modules + the migration.
- **M5**: all writes to `charter.yaml` go through the single shared `load→mutate-owned-section→round-trip-save` helper (INV-9), preserving non-owned sections byte-for-byte.

## Anti-requirements
- Do NOT introduce a parallel/hand-rolled manifest model.
- Do NOT carry `references.yaml`/`governance.yaml`/`directives.yaml`/`metadata.yaml` in any v2 file list except the migration's *input* enumeration.
