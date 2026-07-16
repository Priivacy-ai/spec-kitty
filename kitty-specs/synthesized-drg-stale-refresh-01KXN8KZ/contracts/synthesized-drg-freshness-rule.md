# Contract: Corrected `synthesized_drg` Freshness Rule

**Mission:** `synthesized-drg-stale-refresh-01KXN8KZ` · Fixes [#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681) · Implements FR-007

## Canonical location

The `charter status --json` payload contract lives at:

```
kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/charter-status-json.md
```

This file's "Staleness computation" section is the published, canonical
description of the freshness rules. `computer.py`'s module docstring
restates the same rules for readers of the source. **Both** must carry the
corrected text below; the tasks phase must update both files (see
`data-model.md` → "Contract-doc updates required").

## Corrected rule text

Replace the current (defective) bullet:

> `synthesized_drg.state = "stale"` when `synthesis-manifest.yaml.run_id`
> references inputs whose mtime is older than `synced_bundle.last_change`.

with:

> `synthesized_drg.state = "stale"` when the synthesis manifest's
> `bundle_content_hash` does not match a freshly recomputed SHA-256 hash of
> the current synced-bundle content (`governance.yaml`, `directives.yaml`,
> `references.yaml`, `metadata.yaml` under `.kittify/charter/`) — a
> content-identity comparison, not a timestamp comparison. A manifest that
> predates this signal (missing `bundle_content_hash`) is treated the same
> as a mismatch: `stale`, self-healing to `fresh` on the next `spec-kitty
> charter synthesize` or `spec-kitty charter resynthesize` run. This
> comparison only runs once `synced_bundle.state == "fresh"` — an upstream-
> stale bundle still short-circuits to `stale` before this check (unchanged
> precedence, see the bullet above it).

The `missing` and `built_in_only` bullets are unchanged by this mission
(FR-004/FR-006, C-002).

## Relationship to `manifest.verify()` / per-artifact `content_hash`

Stated explicitly per C-005 so the two do not read as competing authorities:

- **`manifest.verify()` / `ManifestArtifactEntry.content_hash`** — OUTPUT
  integrity. "Do the doctrine files actually on disk under
  `.kittify/doctrine/` still match what the manifest says it committed?"
  Answers a tampering/corruption question about the artifacts synthesis
  *produced*.
- **`synthesis-manifest.yaml`'s `bundle_content_hash`** (this mission) —
  INPUT currency. "Was the manifest (and the tree it committed) built from
  the doctrine/bundle content that is current right now?" Answers a
  freshness question about the artifacts synthesis *consumed*.

Both signals live on the same manifest. Neither subsumes the other:
`verify()` can pass while `bundle_content_hash` is stale (the #2681
scenario, corrected by this mission), and `bundle_content_hash` can be fresh
while `verify()` fails (an out-of-band edit to a doctrine artifact, a
separate, pre-existing failure mode this mission does not touch).

`_compute_synthesized_drg` remains the single canonical **read** authority
for "is the synthesized DRG current" (C-005); the new
`charter.bundle.compute_bundle_content_hash()` helper, called from both
`write_pipeline.promote` and `resynthesize_pipeline._rewrite_manifest`, is
the single canonical **write** authority for the signal it reads (C-006).

Write-side unification is enforced structurally, not by parallel tests: a
single `manifest.finalize_manifest()` finalizer recomputes `manifest_hash`
from the full `SynthesisManifest` instance at **every** manifest-persist site
(the three `SynthesisManifest(` constructors — `promote`,
`_rewrite_manifest`, `project_drg.apply_post_condition` — plus the fresh-seed
persist in `_fresh_doctrine`), so no field (including `bundle_content_hash`)
can be silently omitted from the hashed payload or the persisted instance.
`apply_post_condition` preserves the existing `bundle_content_hash` unchanged
when it flips `built_in_only` (it does not recompute the bundle hash). See
`data-model.md` for the finalizer contract and the mandatory
`verify_manifest_hash` backward-compat shim that accompanies the field.
