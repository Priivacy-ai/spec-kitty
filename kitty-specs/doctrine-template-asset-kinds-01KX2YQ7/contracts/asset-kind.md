# Contract — ASSET kind + TEMPLATE node

Internal doctrine/DRG contract (no HTTP surface). Binds the behavior of the two kinds.

## Sidecar manifest (`assets/<pack>/<name>.asset.yaml`)

```yaml
# round-trip: skip: illustrative sidecar-manifest shape sketch — the executable AssetManifest schema + round-trip coverage live in tests/specify_cli/doctrine/test_pack_validator.py (this block documents the on-disk convention, not a registered Pydantic contract)
id: company-logo            # required; bare URN -> asset:company-logo (no <pack>/ qualifier — D-05 revised)
mime: image/png             # required; type/subtype + must match path extension
path: logo.png              # required; relative, under assets/<pack>/, no ../ or absolute
title: Company logo         # optional
```

## Behavioral contract

| # | Guarantee | Verified by |
|---|-----------|-------------|
| AT-1 | An `assets/<pack>/*.asset.yaml` is registered as a `NodeKind.ASSET` node addressable as bare `asset:<id>`. | loader/extractor test |
| AT-2 | The blob's content is NOT schema-validated; only the manifest (id/mime/path, via `AssetManifest`) is. The blob is never scanned (glob = `*.asset.yaml`). | `pack_validator` ASSET test |
| AT-3 | A duplicate `asset:` URN anywhere in the merged graph (built-in ∪ every pack ∪ project — **all three layers**) → hard-fail `duplicate_asset_id`, via the single post-merge uniqueness scan at `merge_three_layers` (not silent first-wins, not layered override). | merge dup-id test (NFR-005) |
| AT-4 | A `path` that is absolute or escapes `assets/<pack>/` (`../`) → hard-fail `asset_path_escape`, via the reused `effective_root`/`OrgPackSubdirEscapeError` containment (D-12), in a separate `_validate_asset_manifests` pass. | containment test (NFR-005) |
| AT-5 | A `mime` not matching `type/subtype`, or inconsistent with the path extension → hard-fail `asset_mime_invalid`. | mime test (NFR-005) |
| AT-6 | `ASSET` and `TEMPLATE` are node-declarable but NOT augmentation-eligible and NOT charter-activatable — via `_NON_AUGMENTATION_ELIGIBLE_KINDS`; `charter list` / `YAML_KEY_MAP` / augmentation globs / the `context.py:500` bare-probe filter all exclude them. | augmentation + charter-token + context-probe tests (S6) |
| AT-7 | An asset node reached via `resolve_transitive_refs` appears in the result (`assets` field), not dropped. | query test (D-09) |
| AT-8 | `_OrgDRGNode` carries no asset-specific field (no `mime`/`path`); it stays identity-only for all 11 kinds. Asset mime/path are declared solely in the sidecar. | model-shape test (D-08 revised) |
| TT-1 | An org pack declares a bare `template:<id>` node + an edge (e.g. styleguide `requires` it); the merged DRG contains node + edge; a query returns it. | e2e fixture (S1) |
| TT-2 | An edge to a non-existent template URN → the generic dangling-ref check flags it (free). | validator test (#2495 AC) |
| TT-3 | A duplicate `template:` URN across the merged graph (org-vs-org, or org-vs-built-in `template_catalog`) → hard-fail `duplicate_template_id`, via the same post-merge scan. | merge dup-id test (D-04 revised) |

## Structural contract (totality guard — C-005)

`tests/doctrine/test_kind_mapping_totality.py` (new): for every module-level `dict` keyed by `ArtifactKind`
or `NodeKind` (discovered by reflection/AST), assert it contains an entry (or a documented `.get`-default) for
**every** member — so a future kind cannot silently miss a mapping site. Upgrades the existing subset guard
(`test_nodekind_artifactkind.py`).

## Lockstep contract (#2495)

`_ORG_DRG_CANONICAL_KINDS == (charter.activations._ALLOWED_KINDS normalised) ∪ {mission_types}` — the
drift-guard test stays green because `_ALLOWED_KINDS` + `_BUILTIN_ARTIFACT_KINDS` move in lockstep with the
loader universe.
