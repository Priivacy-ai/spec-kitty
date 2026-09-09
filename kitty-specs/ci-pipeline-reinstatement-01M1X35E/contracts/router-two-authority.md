# Contract — Router two-authority model (E5)

The path→job routing has exactly **two hand-authored sources**; everything else is derived + asserted.

## The two authorities
1. **dorny filter block** (`changes` job): `group → globs[]` (path→group).
2. **job `if:` gates**: `if: needs.changes.outputs.<group>` (group→job).

## Derived (asserted against the two, never hand-maintained)
- The catch-all unmatched OR-list; the aggregator `needs:` set; the completeness oracle.

## Invariants
1. A `src/**` change matched by **no** group forces `run-all` (loud unmatched alarm), never a silent skip.
2. `docs`/`corpus` are non-src → excluded from the unmatched loop (data, not code).
3. **Gate-selection authority (FR-016/#2476):** ONE importable function **parses these two authorities**
   (does not re-encode them) and answers "which shards/gates does this diff select" — reused by **CI
   routing** and **local pre-PR parity** (no second parser). Built with **T1 (router)**; consumed by L3.
4. **Non-vacuous completeness oracle:** reads the **real on-disk** workflow YAML; fails if any test is
   zero-gated or an enumerated must-run gate is unwired; carries a planted-orphan negative test (#2967).
5. Reintroducing filters updates `test_ci_quality_path_filters.py` **in lockstep** (it currently asserts the
   husk has *no* filter).
6. `on.paths` (Gate-0) and dorny `filters:` (Gate-1) stay in lockstep OR the workflow runs on every PR with
   Gate-0 dropped (#3008 hazard); corpus keeps its exit-5 floor.

## Module shard registry (E7, matrix realization)
- Per-module shards are a **matrix over a committed module registry** inside a **bounded** set of reusable
  workflows (≤ GitHub's 20-unique-reusable-workflows-per-caller limit), **not** ~40 separate `module-*.yml`.
  The registry (module → roots, `--cov` target, tier, shard_count) is the single data source; adding a
  module is a registry row, not a new workflow file.
