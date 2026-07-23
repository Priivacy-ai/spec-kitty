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

## Input basis (FR-002)

The `content_hash` for a work-package artifact is computed over the **normalized
WP static projection**, not the raw file bytes. Runtime-mutable frontmatter
(lane, agent, `shell_pid`, activity history) is excluded, so status churn does
**not** change the snapshot hash. Only authored content changes do.

## Golden vector

Input: `[("spec.md", "sha256:aaa"), ("plan.md", "sha256:bbb")]`
Joined (after sort by path): `plan.md\tsha256:bbb\nspec.md\tsha256:aaa`
Result: `sha256:` + `sha256("plan.md\tsha256:bbb\nspec.md\tsha256:aaa")`.

## Implementations (kept in lock-step)

| Side | Location | Golden test |
|------|----------|-------------|
| CLI  | `src/specify_cli/dossier/hasher.py` → `compute_dossier_snapshot_hash` | `tests/dossier/test_hasher.py` (empty-string digest, determinism, order-independence) |
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
