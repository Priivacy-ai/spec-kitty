# Tracer — Approach

Mission `doctrine-template-asset-kinds-01KX2YQ7` · #2495 (P0) + #2469. Seeded at planning.

## Intended WP shape (pre-plan sketch — /plan and /tasks own the final slicing)

- **WP-A — TEMPLATE first-class (#2495).** Add `templates` to `_ORG_DRG_KIND_ALIASES` + `merge._PLURAL_TO_SINGULAR`;
  keep it OUT of AUGMENTATION_ELIGIBLE_KINDS/_AUGMENTATION_GLOBS (C-001); validator accepts template URNs as edge
  endpoints. Test: an org-pack fixture declares a template node + edge; graph query returns it (S1 / NFR-004 half).
- **WP-B — ASSET kind core (#2469).** Add `ArtifactKind.ASSET` + `NodeKind.ASSET`; loose contract (id + mime + path,
  no schema); validator schema-skip branch + id-uniqueness/mime fail-loud (FR-006/008, C-003). New `src/doctrine/assets/`.
- **WP-C — ASSET pack wiring + dirs (#2469).** `assets/built-in/` + `assets/<pack>/` convention; extractor `_KIND_MAP`
  + `scan_dirs`; `_ORG_DRG_KIND_ALIASES` + `_PLURAL_TO_SINGULAR` for `assets`; not augmentation-eligible.
- **WP-D — Exhaustiveness sweep + new-member guard (both).** Cover every switch/iteration/mapping site (FR-010, C-005):
  drg/query.py, executor._ARTIFACT_TO_NODE_KIND, doctrine._SUFFIX_TO_KIND, template_catalog. Add a test that iterates
  ArtifactKind/NodeKind and asserts each has loader/validator/mapping handling (guards future omissions).
- **WP-E — E2E fixture + no-regression (NFR-001/004).** The Regnology-shaped fixture (template node + edge + asset)
  loads/graphs/validates; full doctrine/DRG/pack-validator suites green.

Dependency hint: WP-A and WP-B/C are parallel (template-node vs asset-kind); WP-D depends on both (needs both members);
WP-E last (integration). Final lanes at finalize.

## Adopt-don't-duplicate
- Reuse the existing DRG node/edge model + URN validation; only EXTEND the kind universe + validator dispatch.
- The 9 existing kinds are the template for the loader/validator wiring — mirror their registration, minus the schema for ASSET.

## Verification
- Full doctrine + drg + pack_validator test suites green (NFR-001).
- Doctrine changes → run the terminology guard + docs-freshness before push (CI-only shards).
- Forward-compat check (NFR-003): the assets/<pack>/ convention must not hardcode the single built-in tree.

## Refinements during implement
_(append here)_
