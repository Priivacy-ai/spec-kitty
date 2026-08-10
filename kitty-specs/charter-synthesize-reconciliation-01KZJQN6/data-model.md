# Phase 1 Data Model — Charter Synthesize Reconciliation

No persistent schema changes. This mission introduces/relocates a few in-memory value objects
and preserves existing on-disk artifact shapes. Entities below are the design vocabulary the
tasks build against.

## On-disk artifacts (shape unchanged; reconciliation preserves them)

### Project DRG overlay — `.kittify/doctrine/graph.yaml`
- `schema_version`, `generated_at`, `generated_by` (volatile fields excluded from no-op comparison).
- `nodes[]`: `{ urn, kind, label }` — `kind ∈ {directive, tactic, styleguide}`.
- `edges[]`: `{ source, target, relation, reason }` — `relation ∈ {requires, applies, …}`.
- **Invariant (NFR-001)**: a node/edge present on disk and backed by a doctrine artifact is never removed by a plain run.
- **Invariant (FR-002)**: an edge is retained/removed atomically with its `source` node.

### Synthesis manifest — `.kittify/charter/synthesis-manifest.yaml`
- `artifacts[]`: `{ kind, slug, path, provenance_path, content_hash }`, plus `bundle_content_hash`, `run_id`, `synthesizer_version`.
- **Invariant (FR-004)**: reconciled with the overlay under the same contract; on a no-op re-synthesis it is byte-identical (NFR-002).

### Backing doctrine artifact — `.kittify/doctrine/**/*.yaml`
- Existence defines **backed** vs **orphaned** for a graph node (via the manifest `path`).

## In-memory value objects

### ReconciliationDelta (new — FR-009)
Returned by the library seam; consumed by the CLI and boundary reconciler.
- `retained: list[NodeOrEdgeRef]` — on-disk content preserved (not in the current target set).
- `added: list[NodeOrEdgeRef]` — content the current run emits.
- `removable: list[NodeOrEdgeRef]` — content a `--prune` run would delete (each with backed/orphaned flag).
- `manifest_delta: {retained, added, removable}` — same, for manifest entries.
- `conflicts: list[ReconciliationConflict]` — preserved-content conflicts to report (see below).
- **Used by**: `--dry-run` (report `removable` + `conflicts`, write nothing), `--prune` (effect `removable`, list them), preserve default (report `retained`), refusal (unpreservable subset).

### ReconciliationConflict (NEW object in `reconcile.py`, modeled after — not reusing — the DRG shape — FR-006/FR-014)
- Fields: `kind`, `target_id` (the URN/triple), `backing_artifact` (path or `null` for orphaned), `remediation`, `provenance ∈ {preserved, new_emit}`.
- **Remediation vocabulary lives in `reconcile.py`** (NOT `src/doctrine/drg/merge.py._CONFLICT_REMEDIATIONS`, whose `kind` is a closed `Literal` with no `duplicate_triple` and which belongs to the org-pack fragment-merge subsystem).
- **Distinct `kind` names** (avoid colliding with `merge.py`'s closed Literal strings):
  - `duplicate_triple` — a preserved edge duplicates a `(source, target, relation)` triple.
  - `preserved_dangling_endpoint` — a preserved edge whose endpoint the current run legitimately removed/renamed. Deliberately distinct from `merge.py`'s `unresolved_edge_endpoint` label so the two subsystems never name-collide on a forked string.
- **Completeness gate**: `reconcile.py`'s remediation set gets its own completeness test mirroring `merge.py`'s `test_every_conflict_class_carries_a_remediation_line` (every `kind` carries a non-empty remediation).
- **Rule**: `provenance == preserved` → report channel (non-fatal, surfaced); `provenance == new_emit` → hard error (unchanged behavior).

### WP01→WP02 conflict flow (in-memory interface of record — no sidecar)
- Conflicts travel through the in-memory `ReconciliationDelta.conflicts` list within one
  in-process `synthesize()` call — there is **no** `.reconcile-conflicts.json` staging file.
- **WP01** populates `delta.conflicts` (detect + classify `provenance`) before returning the delta.
- **WP02** receives the classified conflicts via a **widened `validate()` signature** and performs
  only the suppress (`preserved`) vs raise (`new_emit`) decision.
- Structured detection (duplicate triple / dangling endpoint) is sourced from shared helpers in
  `src/doctrine/drg/validator.py` consumed by both `validate_graph` and `reconcile.py`.

### SynthesizeMode (new selector — FR-009)
- `preserve` (default; drops nothing, exit 0) · `prune` (effect removals) · `dry_run` (compute delta, no write).
- Library default = `preserve`; CLI maps flags → mode; `auto_refresh`/`activate` use `preserve`.

## Freshness (behavioral, FR-008)
- `synthesized_drg` substate resolves to `fresh` after a successful non-destructive heal; the
  re-stamp is decoupled from any destructive rebuild.

## State transitions (synthesize over a divergent on-disk overlay)

```
on-disk overlay (superset) + current target set (subset)
        │
        ▼   library seam: merge (preserve backed) → ReconciliationDelta
   ┌────────────┬───────────────┬────────────────────────────┐
   │ preserve   │ dry_run       │ prune                        │
   ▼            ▼               ▼                              │
 write merged  no write,      write merged minus removable,   │
 (retained),   report delta   list deletions                  │
 exit 0                                                        │
        │                                                      │
        └── unpreservable (orphan w/o prune | unparseable) ────┘
                     ▼ (manual CLI only)
              refuse, exit 1, list conflicts+remediation
```
