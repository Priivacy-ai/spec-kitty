# Phase 1 Data Model: Untrusted-Path Containment Hardening

This mission hardens behaviour rather than introducing new persisted entities.
The "model" is the validation seam and the trust classification of inputs.

## Value concepts

### Untrusted path segment
- **Definition**: a single path label (`mission_slug`, `feature_slug`, `wp_id`) sourced from on-disk content (`status.events.jsonl`, `meta.json`, frontmatter), config, or CLI args.
- **Invariant**: never used to build a filesystem path until it has passed the canonical seam.

### Trusted root set
- **Definition**: the allowlist of repo-derived directories a sink may touch.
- **Members**: `.kittify/derived/`, `kitty-specs/`, `.worktrees/`, merge-state surface (`.kittify/runtime/merge`, `.kittify/merge-state.json`).
- **Note**: `feature_dir.name` is itself a trusted segment (derived from the directory the operator is acting on) and is the write-surface fallback.

### Canonical seam (the validators)
| Function | Module | Role | Failure mode |
|----------|--------|------|--------------|
| `assert_safe_path_segment(value)` | `core/paths.py` | segment grammar — reject empty, non-ASCII, separators, `.`/`..`, absolute | raises `ValueError` |
| `safe_mission_slug(slug, fallback)` | `core/paths.py` | fail-closed wrapper — return slug if safe, else warn + return trusted fallback | never raises |
| `ensure_within_any(path, roots)` | `core/utils.py` | `resolve()`-containment — resolve symlinks, assert within a trusted root | raises `ValueError` |

## State transitions (per consumed segment)

```
segment (untrusted)
   │  assert_safe_path_segment  ── fail ─▶ READ sink: return None (skip)   [C-004]
   │                                       WRITE sink: fall back to feature_dir.name
   ▼ pass
built path
   │  ensure_within_any(path, trusted_roots)  ── fail ─▶ reject (same fail-closed branch)
   ▼ pass
filesystem read / write / mkdir  (in-bounds, safe)
```

> **Guard applies per sink type**: `ensure_within_any` (`resolve()`-containment)
> applies to **read** resolvers (store.py). **Write** sinks (progress/lifecycle/
> views) are protected by `safe_mission_slug` at their slug *sources* — the
> reducer seam for the event slug AND `mission_metadata.resolve_mission_identity`
> for the `meta.json` slug (IC-05) — after which an unsafe slug becomes the
> trusted `feature_dir.name`. The fail branch above therefore has two shapes:
> read → `None`; write → trusted-fallback.

### Untrusted slug sources (both must be sanitized)
- Event-log slug (`status.events.jsonl`) → reducer seam (`safe_mission_slug`), landed in #2036.
- `meta.json mission_slug` via `resolve_mission_identity` → IC-05 (still open after #2036).

## Validation rules

- VR-1 (FR-001): no FS sink consumes an untrusted segment that skipped the seam.
- VR-2 (FR-002): the store.py read resolver applies BOTH grammar and `resolve()`-containment. (aggregate.py grammar-guard already raises; its composed-path containment is an IC-02 audit disposition — FR-003.)
- VR-6 (FR-009): the `meta.json` slug source is sanitized via `safe_mission_slug`, fail-closed to `feature_dir.name`.
- VR-3 (C-004): read sinks → `None`; write sinks → trusted fallback; exactly one WARNING each; no raise on hot path.
- VR-4 (FR-008): each guard has a mutation-killing negative test, incl. symlink-escape.
- VR-5 (FR-005): the architectural guard rejects new unvalidated joins on audited surfaces.

## Audit record (produced by IC-02)

A table — one row per untrusted→FS sink found in `src/specify_cli`:

| Sink (file:line) | Untrusted source | Sink op | Reachable? | Disposition |
|------------------|------------------|---------|-----------|-------------|

Every sink MUST have a disposition (fixed / not-reachable-documented); none left blank (SC-003).
