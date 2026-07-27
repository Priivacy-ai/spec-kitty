# Contract — `charter status --json` (extended)

**Backed by**: FR-005, FR-009 (`built_in_only` flag), FR-015 (vocabulary)

## Top-level shape (post-mission)

```json
{
  "result": "success",
  "charter_sync": { /* existing */ },
  "synthesis":    { /* existing — see Synthesis section below */ },
  "org_layer":    { /* existing */ },
  "freshness":    { /* NEW — see Freshness section below */ }
}
```

## `freshness` (NEW)

```json
{
  "charter_source": {
    "state": "fresh" | "stale" | "missing" | "invalid",
    "last_change": "2026-05-19T13:00:45.966069+00:00" | null,
    "remediation": "spec-kitty charter sync" | null
  },
  "synced_bundle": {
    "state": "fresh" | "stale" | "missing" | "invalid",
    "last_change": "..." | null,
    "remediation": "spec-kitty charter sync" | null
  },
  "synthesized_drg": {
    "state": "fresh" | "stale" | "missing" | "built_in_only" | "invalid",
    "last_change": "..." | null,
    "remediation": "spec-kitty charter synthesize" | null
  }
}
```

Each sub-object MUST be present (never elided). State `"built_in_only"` on `synthesized_drg` is set when `synthesis-manifest.yaml` declares `built_in_only: true` (FR-009).

## `synthesis` (existing — vocabulary changes only)

Fields `generation_state`, `evidence`, `provenance`, `manifest` keep their existing shape, but any string value of `"shipped"` is replaced with `"built-in"` (FR-015). External consumers who pattern-matched `"shipped"` MUST be migrated; CHANGELOG entry (FR-017) documents this.

## Staleness computation

- `charter_source.state = "stale"` when the file's SHA-256 differs from the hash stored in `.kittify/charter/metadata.yaml`.
- `synced_bundle.state = "stale"` when any bundle file's mtime is older than `charter_source.last_change`.
- `synthesized_drg.state = "stale"` when the synthesis manifest's `bundle_content_hash` does not match a freshly recomputed SHA-256 content-identity hash of the current synced bundle (`governance.yaml`, `directives.yaml`, `references.yaml`, `metadata.yaml` under `.kittify/charter/`, via `charter.bundle.compute_bundle_content_hash`) — a content comparison, not a timestamp comparison. A manifest that predates this field (missing `bundle_content_hash`) is treated as a mismatch: `stale`, self-healing to `fresh` on the next `spec-kitty charter synthesize` or `spec-kitty charter resynthesize` run. This check only runs once `synced_bundle.state == "fresh"`; an upstream-stale bundle still short-circuits `synthesized_drg` to `stale` first (see the bullet above).
- `synthesized_drg.state = "missing"` when `.kittify/doctrine/graph.yaml` does not exist AND `synthesis-manifest.yaml` does not declare `built_in_only: true`.

## Backward compatibility

- Existing keys (`charter_sync`, `synthesis`, `org_layer`) keep their shape.
- New key `freshness` is additive.
- Vocabulary change is breaking and documented in CHANGELOG.

## Failure modes

- `charter status --json` exits non-zero ONLY when the charter file cannot be read at all (existing behaviour). All freshness sub-states map to `result: "success"` with informative sub-states; staleness is not a CLI error.
