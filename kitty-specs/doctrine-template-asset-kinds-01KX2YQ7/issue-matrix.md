# Issue matrix — doctrine-template-asset-kinds-01KX2YQ7

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2495 | Templates as first-class org-pack DRG nodes | fixed | Templates are node-declarable but NOT augmentation/charter-eligible via canonical `_NON_AUGMENTATION_ELIGIBLE_KINDS` (WP01/WP02), compose via `_PLURAL_TO_SINGULAR` (WP03), edges validate + bare `template:<id>` URN uniqueness enforced at `merge_three_layers` (WP03), proven e2e (WP08 `test_template_asset_e2e.py`). All 8 WPs approved by reviewer-renata. |
| #2469 | New loose-contract asset doctrine kind | fixed | `ArtifactKind.ASSET`/`NodeKind.ASSET` + `*.asset.yaml` glob (WP01); sidecar `AssetManifest` + separate `_validate_asset_manifests` pass with path-containment (reused `effective_root`) + mime validation (WP04); extractor/suffix registration (WP05); global URN-uniqueness hard-fail (WP03); transitive-refs `.assets` fix + totality guard (WP07); e2e + 4 fail-loud negatives (WP08). All 8 WPs approved. |
| #2467 | Pack-split keystone (doctrine dir re-layout) | deferred-with-followup | spec.md Out-of-scope + C-004/C-006: taken out-of-order by operator decision; kind contract kept forward-compatible (NFR-003). Follow-up: #2467 remains open in tracker. |
| #2466 | Doctrine/Charter extensibility & pack ecosystem (epic) | deferred-with-followup | Parent epic; this mission delivers two children (#2495/#2469). Other children (#2468/#2470/#2471) OUT per spec.md Out-of-scope. Epic remains open. |
| #2216 | Governance-tiers | deferred-with-followup | Explicitly OUT of scope per spec.md Out-of-scope; no change in this mission. Follow-up: #2216 remains open in tracker. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
