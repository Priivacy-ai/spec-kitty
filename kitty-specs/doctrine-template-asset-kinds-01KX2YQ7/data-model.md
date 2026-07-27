# Phase 1 — Data Model

Mission `doctrine-template-asset-kinds-01KX2YQ7` · #2495 + #2469. Two new kind members + one manifest schema +
one canonical exclusion set; no change to the DRG node/edge model beyond these.

## New enum members

### `ArtifactKind.ASSET` (`src/doctrine/artifact_kinds.py`)
- Value `"asset"`; `glob_pattern = "*.asset.yaml"` (the sidecar manifest; NOT empty-glob).
- Member of `_NON_AUGMENTATION_ELIGIBLE_KINDS` (below).

### `NodeKind.ASSET` (`src/doctrine/drg/models.py`)
- Value `"asset"`; URN prefix `asset:` (models.py enforces prefix==kind). **Bare** URN `asset:<id>` — no
  `<pack>/` qualifier (D-05 revised; the shared URN bridge mints bare `<kind>:<id>` for all 11 kinds). Cross-pack
  / cross-layer collisions are caught by the global-uniqueness scan (D-04 revised), not by URN qualification.

### `TEMPLATE` (existing, now org-pack node-declarable)
- No enum change; becomes usable as an org-pack node kind via the loader universe (below).

## Canonical exclusion set (new)

```python
# artifact_kinds.py (or a shared home imported by the loader)
_NON_AUGMENTATION_ELIGIBLE_KINDS: frozenset[ArtifactKind] = frozenset(
    {ArtifactKind.TEMPLATE, ArtifactKind.ASSET}
)
```
Drives **both**:
- `AUGMENTATION_ELIGIBLE_KINDS` / `_AUGMENTATION_GLOBS` (`org_pack_loader.py`) — `kind not in _NON_AUGMENTATION_ELIGIBLE_KINDS`.
- `CHARTER_KIND_TOKENS` (`artifact_kinds.py`) — same predicate (was `is not TEMPLATE`).

**Three orthogonal properties, now cleanly separated:** node-declarable (in `_ORG_DRG_CANONICAL_KINDS`),
augmentation-eligible (not in `_NON_AUGMENTATION_ELIGIBLE_KINDS`), charter-activatable (in `CHARTER_KIND_TOKENS`).
TEMPLATE + ASSET: node-declarable = yes; the other two = no.

## The sidecar asset manifest (`*.asset.yaml`)

| Field | Type | Rule |
|-------|------|------|
| `id` | str | required; unique **globally** across the merged graph (D-04 revised); forms **bare** URN `asset:<id>` |
| `mime` | str | required; `type/subtype` shape AND consistent with `path`'s extension (`mimetypes.guess_type`) |
| `path` | str | required; **relative**, normalises strictly under the owning `assets/<pack>/` root (D-06, via the reused `effective_root` containment — D-12) |
| `title` | str | optional (display) |

The manifest is the validated surface, via a new `AssetManifest` Pydantic model in `pack_validator.py`; the
referenced blob is never schema-validated (and is never scanned — the glob is `*.asset.yaml`, so there is no
"skip the blob" branch to write). `_OrgDRGNode` (`org_pack_loader.py`, `extra="forbid"`) is **unchanged** —
identity-only for all 11 kinds; asset metadata (mime/path) lives **only** in the sidecar (D-08 revised).

## Node-declarable universe (extended)

- `_ORG_DRG_KIND_ALIASES` / `_ORG_DRG_CANONICAL_KINDS` (`org_pack_loader.py`) += `templates`, `assets`.
- **Locked mirrors (must move in lockstep — drift-guard test):** `charter/activations.py::_ALLOWED_KINDS`,
  `charter/pack_context.py::_BUILTIN_ARTIFACT_KINDS`.
- `merge.py::_PLURAL_TO_SINGULAR` += `templates`, `assets`.

## Merge behavior (new — global URN-uniqueness scan, ASSET + TEMPLATE)

`merge.py::merge_three_layers` (:471) gains a **single post-merge uniqueness scan** over the fully-merged node
set: any duplicate `asset:` URN → hard-fail `duplicate_asset_id`; any duplicate `template:` URN → hard-fail
`duplicate_template_id` (D-04 revised). This replaces the original org-vs-org-only tweak and covers all three
collision surfaces (built-in-vs-org, org-vs-org, project-vs-any) in one order-independent check. Extract a small
`_check_node_urn_unique(prefix, nodes)` helper (keeps `merge.py` complexity ≤15; `_merge_org_fragment` is
already at the ceiling). The other 9 kinds' layered override tolerance is untouched **by construction** —
`models.py` enforces URN-prefix == kind, so an `asset:`/`template:` URN can only collide with its own kind.

## Query result (fixed)

`drg/query.py::ResolveTransitiveRefsResult` gains `assets: list[str]` + a wired return line, so asset nodes
reached transitively are not silently dropped.

## Structured errors (fail-loud, NFR-005)

- `duplicate_asset_id` — global `asset:` URN collision (any layer).
- `duplicate_template_id` — global `template:` URN collision (any layer; covers the two template producers).
- `asset_path_escape` — path is absolute or escapes the pack root.
- `asset_mime_invalid` — malformed mime or path-extension mismatch.

## Exhaustiveness surfaces added post-plan squad (IC-02 / IC-05)

- **IC-02** absorbs a 4th TEMPLATE-exclusion site: `charter/context.py:500` (`_render_generic_artifact_include`
  candidate-kind probe — a comprehension, invisible to the totality guard; D-11).
- **IC-05** additionally names four `.get`-defaulted `dict[ArtifactKind]` partials the totality guard must
  **exempt** (not false-fail on): `charter/kind_vocabulary.py:75/79`, `charter/pack_manager.py:132/225` (D-13).

## Out-of-model (not touched)
The 9 existing kinds' schemas + behavior; the DRG relation rules (edges to template/asset are free); the
`template_catalog` built-in producer's `template:<mission>/<name>` id scheme (kept as-is — its slash-bearing
ids coexist with bare org-pack `template:<id>` under one uniqueness scan, so a clash is **enforced**, not
presumed disjoint — D-05 revised).
