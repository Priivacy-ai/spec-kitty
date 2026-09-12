# Contract: Canonical Dossier Snapshot Hash (CLI ↔ Server)

**Mission:** dossier-parity-reconciler-01KXYXVP · **Tracker:** Priivacy-ai/spec-kitty#2180
**Constraint:** C-001 (single canonical authority), C-003 (cross-repo split)

This is the binding cross-repo contract the CLI (`spec-kitty`) and the SaaS
server (`spec-kitty-saas`) must both honor. If either side changes the
ordering, separator, algorithm, prefix, or input basis without the other, the
`DossierReconciler` will report divergence for identical content. Do not change
one side without the other, in lock-step.

## Definition

The dossier snapshot hash is computed over a set of `(artifact_path, content_hash)`
entries:

1. Take the entries as `(path: str, content_hash: str | None)` pairs.
2. Sort by `path` (byte-stable, ascending).
3. Join into lines: for each entry, `f"{path}\t{content_hash or ''}"` (tab
   separator; a `None`/absent content hash serializes as the empty string).
4. Join the lines with `"\n"` (newline).
5. `sha256` over the UTF-8 encoding of the joined string.
6. Prefix the lowercase hex digest with `sha256:`.

Empty input hashes the empty string:
`sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

### Per-artifact `content_hash` form (bare hex, no prefix)

Each entry's `content_hash` is a **bare, lowercase 64-character hex SHA-256
digest — with NO `sha256:` prefix** (it is an `ArtifactRef.content_hash_sha256`,
not a snapshot hash). Only the *outer* snapshot digest carries the `sha256:`
prefix. Both sides join the `content_hash` verbatim, so a per-artifact hash that
carried a prefix on one side would diverge on every entry.

`artifact_path` values must not contain a literal tab (`\t`) or newline (`\n`) —
those are the field/record separators; a path containing one could forge or
merge an entry line. Mission artifact paths are relative POSIX paths and never
do, but both sides rely on this and must not add path escaping unilaterally.

## Input basis (FR-002)

The `content_hash` for a work-package (`WP##`) artifact is computed over the
**normalized WP static projection**, not the raw file bytes. Runtime-mutable
frontmatter (`lane`, `agent`, `shell_pid`, `assignee`, `review_*`, activity
`history`, …) is excluded, so status churn does **not** change the snapshot
hash. Only authored content changes do.

The projection is serialized deterministically before hashing — both sides MUST
use this exact form:

```
sha256( json.dumps(projection, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False, default=str).encode("utf-8") )
```

i.e. keys sorted; compact separators (`,`/`:`, **no spaces**); non-ASCII kept
verbatim; absent scalars serialize as `null`, empty lists as `[]`. The projected
field set is `WP_STATIC_PROJECTION_FIELDS`. A server serializing with default
separators (`", "`/`": "`) or tuple-order keys yields a different per-artifact
hash — and therefore a different snapshot hash — for identical content.

## Golden vectors

**Outer snapshot hash** — input `[("plan.md", "hash_plan"), ("spec.md",
"hash_spec"), ("tasks/WP01.md", "hash_wp01")]` (short readable stand-ins for the
bare-hex content hashes; note the absence of any `sha256:` prefix on the
per-artifact values) joins, after sort by path, to
`plan.md\thash_plan\nspec.md\thash_spec\ntasks/WP01.md\thash_wp01`;
the CLI pins the resulting digest and the empty-input sentinel in
`tests/dossier/test_canonical_hash.py` (`GOLDEN_HASH`, `EMPTY_HASH`).

**Per-WP projection hash** — the CLI pins a fully-specified WP projection input,
its exact serialized bytes, and the resulting bare-hex digest in the same file
(`GOLDEN_WP_DATA`, `GOLDEN_WP_PROJECTION_SERIALIZED`, `GOLDEN_WP_PROJECTION_HASH`).
The server MUST reproduce the same projection digest from `GOLDEN_WP_DATA` for
the cross-repo contract to hold.

## Implementations (kept in lock-step)

| Side | Location | Golden test |
|------|----------|-------------|
| CLI  | `src/specify_cli/dossier/hasher.py` → `compute_dossier_snapshot_hash` / `hash_wp_static_projection` | `tests/dossier/test_canonical_hash.py` (snapshot + projection golden vectors, empty-string sentinel, determinism, order-independence, churn-immunity) |
| Server | `spec-kitty-saas` `apps/dossier/materialize.py` → `_compute_snapshot_hash` | `apps/dossier/tests/test_snapshot_hash.py::test_matches_documented_definition` (multi-entry byte layout) |

The server implementation shipped in saas#352 and already matches this
definition (its docstring cites #2180). **IC-05 requires no companion code
change** — verified byte-identical during this mission; the server test pins the
multi-entry layout and the CLI test pins the empty-string digest, so a formula
drift on either side breaks at least one golden.

## Consumers

- **Emit (FR-008):** the CLI emits this value under the unchanged `snapshot_hash`
  event field (`sha256:`-prefixed).
- **Reconcile (FR-004/005):** `DossierReconciler` rebuilds a projection from
  source, recomputes this hash, and compares against the recorded/emitted value.
- **Re-baseline (FR-009):** `spec-kitty migrate rebaseline-dossier-hashes`
  recomputes recorded hashes from source under this definition.
- **import-history (#2262):** gates materialization via
  `reconcile_mission_dossier(...)`.
