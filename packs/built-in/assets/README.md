# Assets

`assets` are Spec Kitty's loose-contract doctrine kind
(`ArtifactKind.ASSET`, singular `asset`, glob `*.asset.yaml`). Unlike the
other nine artifact kinds, the referenced blob itself (an image, font,
template fixture, or other binary/text file) is never parsed or
schema-validated. Instead each blob is described by a small YAML **sidecar
manifest** placed alongside it, and it is the manifest that is the validated
surface.

## Sidecar convention

For a blob at `assets/<pack>/diagrams/logo.png`, the sidecar manifest lives
next to it as `assets/<pack>/diagrams/logo.png.asset.yaml` (or any filename
matching `*.asset.yaml` in the same pack's `assets/` directory tree — the
manifest's own `id` is what identifies it, not the filename).

Manifest shape (`doctrine.assets.models.AssetManifest`):

```yaml
id: acme-logo-png
mime: image/png
path: diagrams/logo.png
title: Acme company logo (PNG)
```

Fields:

| Field   | Required | Description                                                                 |
|---------|----------|-------------------------------------------------------------------------------|
| `id`    | yes      | Stable identifier, unique per pack per kind (cross-pack global uniqueness is enforced separately, by the merge scan). |
| `mime`  | yes      | Declared MIME type, `type/subtype` form, e.g. `image/png`.                    |
| `path`  | yes      | Path to the blob, **relative to the pack's `assets/` directory** — never absolute, never containing a `..` escape. |
| `title` | no       | Optional human-facing display name.                                          |

## Safety contract enforced by the pack validator

`specify_cli.doctrine.pack_validator` validates every `*.asset.yaml`
manifest found under a pack's `assets/` directory in a separate pass
(`_validate_asset_manifests`, run once per pack alongside DRG validation),
in addition to the generic per-kind schema scan. It enforces two safety
rules on top of the `AssetManifest` schema:

* **Path containment** (`asset_path_escape`): `path` must resolve inside the
  owning pack's `assets/` root. An absolute path, a `..`-escape, or a
  symlink that resolves outside the root is rejected. This reuses
  `doctrine.drg.org_pack_config.resolve_relative_path_within_root` — the
  same containment primitive `OrgPackConfig.effective_root` uses for
  `subdir` — rather than a second hand-rolled implementation.
* **MIME consistency** (`asset_mime_invalid`): `mime` must have the
  `type/subtype` shape, and — when Python's `mimetypes.guess_type` can infer
  a type from `path`'s extension — must agree with that guess.

This is a **loose contract**: this validator does *not* enforce global
`id` uniqueness across packs (that is the merge-time scan's responsibility),
and it does not inspect the blob's actual bytes.
