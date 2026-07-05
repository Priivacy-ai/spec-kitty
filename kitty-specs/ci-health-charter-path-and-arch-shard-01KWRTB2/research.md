# Phase 0 Research: CI Health: Charter-Path Hotfix + Arch-Adversarial Shard

## R1 — Docs charter-path offender scope (FR-001, FR-002)

- **Decision**: Fix the single surviving offender at `docs/guides/contributing.md:394`
  (`memory files (memory/charter.md)` → reference the canonical
  `.kittify/charter/charter.md`), then run the guard itself to confirm zero
  offenders remain.
- **Rationale**: `test_current_docs_do_not_publish_memory_charter_path`
  (`tests/docs/test_current_charter_paths.py`) scans all four guarded roots
  (`docs/context`, `docs/guides`, `docs/api`, `spec-driven.md`) for both
  `memory/charter.md` and `.kittify/memory/charter.md`. A live grep across all
  four roots today returns exactly one hit. No other guarded file references
  the retired path.
- **Alternatives considered**: None — this is a single-line, mechanically
  verified fix. Widening the guard's scope was considered and rejected: the
  four guarded roots already match the spec's stated exception clause
  ("the same stale path must not survive anywhere else under the guarded
  roots"), and widening beyond that is out of this mission's scope.

## R2 — Arch-adversarial shard count and partition strategy (FR-003, FR-004)

- **Decision**: N=3 shards, partitioned at the **whole-test-file** granularity
  (no single file split across shards), balanced by a test-count proxy
  (216 / 215 / 215), routed via three new pytest markers
  (`arch_shard_1`, `arch_shard_2`, `arch_shard_3`).
- **Rationale**: Confirmed via the operator's Decision Moment
  (`DM-01KWRWB0PPF5TQPNYF5D07XY3W`): "N=3 shards minimum, functional/module-level
  slicing (whole test files kept intact, not split), routed via dedicated
  pytest markers (not raw `--ignore` path lists)". A greedy bin-packing pass
  over the 4 pole directories' test-function counts (94 files in
  `tests/architectural/` individually, plus `tests/adversarial`,
  `tests/architecture`, `tests/lint` folded in as whole units for functional
  cohesion) produced a near-perfectly balanced 216/215/215 split with zero
  file splitting required — see the shard-assignment table in
  `data-model.md`. This test-count proxy is the same kind of honest
  structural projection the mission's own
  `tests/release/ci_topology_timings_postshrink.json` already uses elsewhere
  (labeled explicitly as a projection, not a live-duration measurement,
  because a live post-split CI run cannot exist pre-merge). Real per-test
  durations should be backfilled from the first post-merge CI run and may
  motivate a follow-up rebalance — that rebalance is out of scope here (the
  assignment table is a single editable source, so rebalancing later is
  cheap).
- **Alternatives considered**:
  - **N=2**: fewer matrix legs, but the 14.4-min pole would only roughly
    halve to ~7.2 min per shard even in a perfect split — more margin than
    needed, but a materially coarser split misses the operator's explicit
    "N=3 minimum" steer.
  - **Duration-hash-based dynamic splitting** (e.g., `pytest-split` with a
    committed `.test_durations` cache): more precise long-run balancing, but
    introduces a new dependency and a new artifact-freshness problem (stale
    duration cache silently skews shards); rejected as disproportionate to a
    3-shard, 802-test split, and not what "functional/module-level slicing"
    calls for.
  - **Raw path/`--ignore` lists** (the literal `fast-tests-core-misc`
    pattern): rejected per the operator's explicit steer toward pytest
    tags/labels. It would also be far more verbose here — `fast-tests-core-misc`
    ignores ~20 nested roots across 2 shards; a 3-way, 94-file split by
    `--ignore` would need dozens of entries per shard versus a single marker
    reference.

## R3 — Shard routing mechanism (FR-004)

- **Decision**: A new module `tests/_arch_shard_map.py` holds the single-source
  `dict[str, int]` mapping (test-file relpath or module stem → shard number,
  1/2/3). A `pytest_collection_modifyitems` hook in `tests/conftest.py`
  applies `pytest.mark.arch_shard_<N>` to every collected item whose file
  falls under one of the 4 pole roots (`tests/adversarial`,
  `tests/architectural`, `tests/architecture`, `tests/lint`), looked up
  against that table. The three new markers are registered in `pytest.ini`
  (the single source of truth per `test_marker_registry_single_source.py`,
  #2034).
- **Rationale**: `tests/architectural/_gate_coverage.py` already models every
  CI selection gate generically as `Gate(paths, ignores, marker_expr)` and
  compiles `marker_expr` through pytest's own `Expression` engine
  (`CompiledGate`) — marker-expression-based shard selection is a first-class,
  already-supported case in this codebase's CI model, not a new concept being
  bolted on. Applying the marker at collection time from one committed table
  (rather than hand-annotating ~94 files with `pytestmark`) keeps the
  assignment auditable and trivially rebalanceable, and guarantees every test
  gets *exactly one* shard marker by construction (enforced by the new
  completeness guard in IC-03) rather than by convention.
- **Reproduction**: `pytest -m 'arch_shard_2 and not windows_ci and (git_repo or integration or architectural)' tests/adversarial tests/architectural tests/architecture tests/lint`
  reproduces shard 2's exact test set locally, byte-for-byte matching CI
  selection (FR-004's determinism requirement).

## R4 — Coverage ownership re-partition (FR-006)

- **Decision**: Keep the existing `coverage-arch-adversarial-${{ matrix.shard }}.xml`
  / `arch-adversarial-${{ matrix.shard }}-reports` naming; only `matrix.shard`
  values change (from the single `architectural` to `arch_shard_1`,
  `arch_shard_2`, `arch_shard_3`).
- **Rationale**: `tests/release/test_coverage_topology_ownership.py`
  already collapses GHA `${{ ... }}` interpolations to a placeholder before
  matching against the `coverage-*.xml` / `*-reports` glob patterns — it is
  shard-label-agnostic by design. Renaming the shard values is expected to
  pass this guard unmodified; Phase 1 confirms this by running it against the
  updated workflow rather than assuming it.

## R5 — Existing shard-universe invariant gap (discovered during planning)

- **Finding**: `tests/architectural/test_shard_universe_bounded.py` (the
  SC-003a "no single shard collects the full catch-all universe" invariant
  from mission `ci-topology-shrink-01KWQAVX`) scopes its catch-all job family
  to jobs whose name contains the substring `"core-misc"`
  (`_CATCH_ALL_SUBSTR = "core-misc"`). `arch-adversarial` does not match that
  substring, so this guard **does not currently gate arch-adversarial at
  all** — sharding it without touching this guard would ship FR-005 (union =
  full universe, no drops, no double-counts) gate-unmasked, per the charter's
  "a gate-unmask cannot self-validate" standing order.
- **Decision**: Generalize the invariant (or add a sibling assertion scoped to
  `arch-adversarial`) so the same union/no-double-count property is asserted
  for the newly-sharded pole. Author it RED-first against today's
  single-shard topology, mirroring `test_arch_pole_deserialized.py`'s own
  documented discipline ("Authored FAILING against today's topology").
- **Alternatives considered**: Leaving the guard unchanged and relying only on
  the new marker-completeness guard (IC-02/IC-03) — rejected because
  marker-completeness proves every test has *a* shard marker, not that the
  matrix's `-m` selection actually realizes a clean partition end-to-end
  (e.g., a stray marker-expression typo in one matrix leg could still
  double-select or silently drop tests without the marker-completeness guard
  catching it).

## Contracts

Not applicable — this mission has no API/service surface. No `contracts/`
artifacts are generated; the "contract" analogue here is the shard-assignment
table itself (documented in `data-model.md`) and the marker-expression
reproduction rule (R3).
