# Contract: Charter Freshness Cache (WP-B)

Governs NFR-002 (no stale governance verdict), C-005 (fail-closed, content-keyed).

## Key inputs (all three; a missing one = fail-closed miss)

The freshness verdict depends on THREE off-`BUNDLE_CONTENT_HASH_FILES` inputs that `_compute_synthesized_drg` (`computer.py:648-669`) reads. The key MUST fold in all three:
1. the charter bundle — `compute_bundle_content_hash(repo_root)` (covers `charter.yaml`);
2. the synthesized-DRG **graph** file (`graph.yaml`, via `_doctrine_graph_path`);
3. the **synthesis-manifest** file (`.kittify/charter/synthesis-manifest.yaml`, `MANIFEST_PATH`) — the verdict reads `manifest.built_in_only` (`:655`) and `manifest.bundle_content_hash` (`:761-767`), so a `(charter, graph)`-only key serves a stale verdict when the manifest drifts.

Key = `sha256(bundle_hash + ":" + graph_hash + ":" + manifest_hash)`.

## Behavioral guarantees (each is an in-diff test)

1. **Hit correctness**: given an unchanged charter bundle, graph file, AND manifest file, a second `next` returns a verdict equal to the freshly-computed one, without calling `_safe_load_yaml`/`compute_freshness` (proven by a spy/patch asserting the parse is skipped).
2. **Bundle invalidation**: mutate any file in `BUNDLE_CONTENT_HASH_FILES` (e.g. `charter.yaml`) → the next lookup MISSES → the served verdict reflects the change.
3. **DRG-graph invalidation**: mutate the graph file only (bundle + manifest untouched) → the next lookup MISSES → the served verdict reflects the change.
4. **Manifest invalidation**: mutate `synthesis-manifest.yaml` only (bundle + graph untouched) — e.g. flip `built_in_only` or change `bundle_content_hash` → the next lookup MISSES → the served verdict reflects the change. (The B1 stale-"fresh" guard the post-tasks squad added.)
5. **Fail-closed**: if any of the three hashes cannot be computed (missing/unreadable), the read is treated as a miss and `compute_freshness` runs; no poisoned entry is written.
6. **Content-only key**: touching a file's mtime without changing its content does NOT invalidate (proves the key is content-based, not mtime-based).
7. **Schema-version invalidation**: bumping `schema_version` invalidates all prior entries.

## Non-goals

- Does not change charter-freshness *semantics* — the verdict a cache-miss computes is byte-for-byte the pre-mission verdict.
- Does not cache anything beyond the freshness verdict on the `next` preflight path.
