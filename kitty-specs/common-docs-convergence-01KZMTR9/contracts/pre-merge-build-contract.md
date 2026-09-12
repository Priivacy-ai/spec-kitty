# Contract — Pre-Merge DocFX Build Gate (FR-017, NFR-001)

Today the DocFX build, `seo_verify`, and redirect-coverage gates run only on push to `main`/`2.x`.
This mission adds a `pull_request` job so structural doc moves are verified before merge.

- **Trigger**: `pull_request` touching `docs/**`, `scripts/docs/**`, or the nav manifests.
- **Steps**:
  1. `docfx docs/docfx.json` — build MUST be zero-error and zero-warning (no glob rot, e.g. the dead
     `apidoc/**` glob must be resolved).
  2. `redirect_stub_generator.py coverage` — every baseline URL + every occurrence-map move covered.
  3. `seo_verify.py --strict` against the built `_site` (description band, etc.).
- **Relation to #3265**: folds the pre-merge slice of the deferred SEO gate; the remainder stays
  tracked under #3265. Advisory beyond build correctness (does not add a new blocking Commit-Boundary gate).
- **Cross-check**: a cheap source-level assertion that `occurrence_map.yaml moves:` ⊆
  `redirect_map.yaml` entries runs on PR even when the full build is skipped.
