# Quickstart — TEMPLATE + ASSET doctrine kinds

The value in one pack layout: ship a template as a graph node, and a binary asset addressable in the DRG.

## An org pack after this mission

```
my-org-pack/
├── styleguides/my-org/house-style.styleguide.yaml   # existing kind
├── templates/my-org/meeting-minutes.template.yaml   # NEW: a node-declarable template
│     # declares a DRG node template:my-org/meeting-minutes; a styleguide can `requires` it
└── assets/my-org/
      ├── logo.png                                    # the blob (no schema)
      └── logo.asset.yaml                             # the sidecar manifest
```

`assets/my-org/logo.asset.yaml`:
```yaml
id: logo            # -> bare URN  asset:logo   (no <pack>/ qualifier — D-05 revised)
mime: image/png     # type/subtype, matches logo.png
path: logo.png      # relative, under assets/my-org/
```

## What the loader/validator does

```python
# addressable in the DRG (bare <kind>:<id>, like all 11 kinds):
graph.node("asset:logo")               # NodeKind.ASSET
graph.node("template:meeting-minutes") # NodeKind.TEMPLATE, edge-wireable

# an edge from a styleguide to the template validates (no relation-rule change):
#   styleguide:house-style  --requires-->  template:meeting-minutes
```

## What fails loud (the anti-dumping-ground rules)

```yaml
# duplicate id anywhere in the merged graph (any layer) -> duplicate_asset_id
id: logo   # another pack/layer already shipped asset:logo? hard-fail. (templates: duplicate_template_id)

# path escape -> asset_path_escape
path: ../../../etc/passwd    # rejected (must be relative, under assets/<pack>/)

# bad mime -> asset_mime_invalid
mime: notamimetype           # rejected (needs type/subtype, matching the extension)
```

## What stays excluded (the #2495 split)

```python
# node-declarable YES, but:
"asset"    not in AUGMENTATION_ELIGIBLE_KINDS   # (via _NON_AUGMENTATION_ELIGIBLE_KINDS)
"template" not in AUGMENTATION_ELIGIBLE_KINDS
"asset"    not in CHARTER_KIND_TOKENS           # not charter-activatable; no `activated_assets`
```

## Guard rails you will hit
- Adding a kind-keyed `dict` without an entry for every member → `test_kind_mapping_totality` fails.
- Adding `templates`/`assets` to the loader universe without moving `_ALLOWED_KINDS` → the lockstep drift-guard fails.
- Run the doctrine + charter + `test_pack_validator` suites locally (CI-only shards) before push.
