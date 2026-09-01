# Data Model

The only new persisted entity is the charter-freshness cache sidecar (WP-B). WP-A (imports), WP-C (benchmark), WP-D (gate removal) introduce no persisted data.

## FreshnessCacheKey (computed, not stored standalone)

A single content hash composed of:

| Component | Source | Why |
|-----------|--------|-----|
| bundle content hash | `compute_bundle_content_hash(repo_root)` (`src/charter/bundle.py`) — per-file, mtime-agnostic, BOM/CRLF-normalized sha256 over `BUNDLE_CONTENT_HASH_FILES` (`charter.yaml`) | Captures the charter bundle |
| synthesized-DRG graph hash | sha256 of the graph file (`graph.yaml`, via `_doctrine_graph_path`) read by `_compute_synthesized_drg` (`computer.py:648-669`) | **NOT** in `BUNDLE_CONTENT_HASH_FILES`; without it the cache serves a stale `synthesized_drg` sub-state |
| synthesis-manifest hash | sha256 of `.kittify/charter/synthesis-manifest.yaml` (`MANIFEST_PATH`) | The verdict reads `manifest.built_in_only` (`:655`) and `manifest.bundle_content_hash` (`:761-767`); a `(charter, graph)`-only key serves a stale verdict when the manifest drifts (post-tasks squad B1) |

- **Composition**: `sha256(bundle_hash + ":" + graph_hash + ":" + manifest_hash)` (order-fixed, delimiter-separated). Deterministic; content-only; **never mtime**.
- **Fail-closed**: if ANY of the three components cannot be computed (missing file, read error), the key is treated as a miss → recompute `compute_freshness` and do not write a poisoned entry.

## FreshnessCacheEntry (persisted sidecar)

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | int | Bump to invalidate all entries on format change |
| `key` | str (hex sha256) | The composite `FreshnessCacheKey` |
| `verdict` | serialized `CharterFreshness` | The exact object `compute_freshness` returns; deserialized identically (no semantic recompute) |
| `written_at` | ISO-8601 str | Diagnostic only; NEVER part of the key or the invalidation decision |

- **Location**: a per-repo runtime cache directory (gitignored; e.g. under the repo's existing runtime/cache area — final path chosen in WP-B to match repo conventions, not a new top-level dir). Repo-global (freshness is keyed on `repo_root`), single entry-set; no per-mission fan-out.
- **Read path**: compute key → look up entry → on `key` match, deserialize and return the verdict, skipping `_safe_load_yaml`/`compute_freshness`. On any mismatch/miss/error → recompute, then write the fresh entry under the new key.
- **Invariant (NFR-002)**: for any change to a keyed input, the next lookup misses and recomputes. Proven by test: mutate a bundle file → recompute; mutate the DRG graph file → recompute; unchanged → hit.
- **Invariant (NFR-004)**: the deserialized-from-cache verdict must drive byte-identical `next` output vs the freshly-computed verdict (excluding the intrinsic per-call `timestamp`).

## Relationships

`next_cmd._run_charter_preflight_for_next` → (compute key) → FreshnessCacheEntry lookup → hit: return verdict / miss: `compute_freshness` then persist. No other consumer reads the sidecar; the in-process `@functools.cache` layers remain unchanged and orthogonal (they die at process exit; the sidecar survives across processes).
