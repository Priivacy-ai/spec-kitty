# Data Model — Doctrine-activation freshness integrity

This mission is behavior-preserving except an intentional freshness-visibility change; it
introduces no new persisted entities. The "model" below is the set of existing artifacts and
signals the seam relates, plus the one new invariant.

## Entities / artifacts

### Activation ledger — `.kittify/config.yaml`
- **Fields**: `activated_<kind>` lists (directives, tactics, mission-types, …).
- **Writers**: `commit_plan` (`activation_engine.py:392`, pure charter — the operator
  activate/deactivate + `promote_activations` chokepoint) **and** `merge_defaults`
  (`pack_manager.py:747`, default-provisioning bypass, ADR-slated for `init`).
- **Role in seam**: the mutation source the derived freshness signal is currently blind to.

### Bundle-content signal — `compute_bundle_content_hash` (`bundle.py:133`)
- **Input set** (unchanged by this mission — Q1 fail-closed): `governance.yaml`,
  `directives.yaml`, `references.yaml`, `metadata.yaml` (`BUNDLE_CONTENT_HASH_FILES:47-52`),
  under `.kittify/charter/`.
- **Recipe** (PRESERVE — #2732): per-file BOM-strip/CRLF normalization; `None` when any input
  file is absent (`:170-171`).
- **Stamp**: `synthesis-manifest.yaml::bundle_content_hash` (`write_pipeline.py:685`,
  `resynthesize_pipeline.py:205`).
- **Read**: `_compute_synthesized_drg` (`computer.py:349`) recomputes (`:426`) and compares
  (`:428`); `None`/mismatch → `stale`.
- **Note**: `CANONICAL_MANIFEST.derived_files` (`bundle.py:110-119`) lists 3 (references
  excluded) vs the 4-file hash — a pre-existing internal disagreement; **left as-is** under
  the fail-closed fork (do not blind-match).

### Consistency parity — `run_consistency_check` (`consistency_check.py:645`)
- **Checks**: `_check_reference_id_parity` (`:455`, config↔references) +
  `_check_graph_kind_parity` (`:562`, config↔graph). Reads `config.yaml` directly
  (`_load_raw_activation_lists:197`) → **writer-agnostic**.
- **Callers today**: only `charter/pack.py:30` (the `charter consistency-check` CLI).
- **Change**: additionally consulted by the freshness read-path (IC-03).

### Prerequisite owed-set — `_attempt_auto_refresh` (`runner.py:327`)
- **Members**: `charter_source`, `synced_bundle`, `synthesized_drg`.
- **Change**: computed/reported in one pass (IC-04) instead of raise-on-first.

### Shipped DRG — `src/doctrine/*.graph.yaml`
- **Baseline** (`test_extractor_projection.py:52-54`): 289 nodes / 765 edges / 11 orphans.
- **Change**: regenerated + charter citation compiled + baseline re-frozen (IC-01); delta N
  computed from a fresh `generate_graph`.

## Invariants

- **INV-1 (new)**: For any project state, if `config.yaml` `activated_*` disagrees with the
  compiled `references.yaml` / `graph.yaml` kinds, the freshness signal reports **stale**
  (fail-closed). *Independent of which writer produced the config state* (writer-agnostic).
- **INV-2 (preserve, #2732)**: The bundle-content hash of an **unchanged** bundle is
  byte-identical across runs and unaffected by this mission.
- **INV-3 (preserve)**: A never-synthesized (fresh-seed) project short-circuits to fresh via
  the early-exit; the parity read must not force it stale.
- **INV-4 (hot-path)**: Default `charter activate`/`deactivate` performs no synthesis/regen
  (zero subprocess); eager refresh only via `--resynthesize`.
- **INV-5 (layer, C-001)**: `commit_plan` and the charter layer do not import `specify_cli`;
  the reconcile read and any eager orchestration live in `specify_cli`.

## State transition (the seam)

```
[bundle+DRG fresh]
      │  charter activate <kind> <id>   (config.yaml mutated; no synthesis)
      ▼
[config ↔ derived MISMATCH]  ──parity read (IC-03)──►  freshness = STALE   (was: silently fresh)
      │
      ├─ operator runs reconcile (charter generate/synthesize)  ──►  [fresh]
      └─ charter activate … --resynthesize (IC-05)  ──►  [fresh] immediately
```
