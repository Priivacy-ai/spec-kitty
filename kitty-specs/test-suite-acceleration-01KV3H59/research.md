# Phase 0 Research — Test Suite Acceleration

All unknowns were resolved by the 43-agent verified audit
(`architecture/test-suite-acceleration-plan.md`); this document consolidates the
load-bearing decisions with rationale and rejected alternatives. There are **no
open `[NEEDS CLARIFICATION]` items**.

## D1 — Parallelization mechanism (CI fast-shards + local)

- **Decision**: Use `pytest-xdist` with `-n auto --dist loadfile`. Roll out
  shard-by-shard in CI (charter first), gated by a stability ratchet.
- **Rationale**: The exact flag combination is already in production in this
  same repo on `integration-tests-core-misc` (ci-quality.yml lines ~1181/1295/1307),
  so topology and per-worker coverage-XML merge are proven safe. `loadfile` pins
  whole files to a worker, which preserves file-local autouse registry/cache
  resets.
- **Alternatives rejected**: bare `--dist load` (work-stealing) — breaks
  file-local autouse resets that assume same-file co-location; `pytest-parallel`
  / `pytest-run-parallel` — not already vetted here, would add a new dependency.

## D2 — Per-worker home/state isolation (the master enabler)

- **Decision**: Add a **worker-id-keyed autouse fixture** in `tests/conftest.py`
  that redirects `Path.home()` and `HOME`/`USERPROFILE`/`LOCALAPPDATA`/`XDG_*`
  to a per-worker temp dir. Keep the existing intra-worker queue-wipe fixtures.
- **Rationale**: The real hazard is verified: `tests/agent/conftest.py:15-41`
  autouse-truncates `Path.home()/".spec-kitty"` (`tests/conftest.py:119`) with no
  HOME isolation. `--dist loadfile` pins files, not a shared real HOME, so
  concurrent workers would clobber the same SQLite DB. A worker-scoped home makes
  both local and CI parallelism safe. Pattern to copy:
  `tests/sync/test_sync_boundary_preflight.py:66-79`.
- **Alternatives rejected**: **session-scoped** home (all workers re-collide on
  one tmp home — reintroduces the exact hazard); deleting the queue-wipe fixtures
  (loses intra-worker isolation); relying on `loadfile` alone (does not serialize
  cross-file access to a shared real DB).

## D3 — Coverage-neutrality safeguards

- **Decision**: Every reduction/flip ships with (a) per-shard collection-node
  equivalence (serial vs xdist must collect identical nodeids), (b) a
  run-twice/run-thrice stability ratchet, (c) an architectural guard that fails
  if any test mutates the real `Path.home()/.spec-kitty` under xdist, and (d) a
  mutation/equivalence proof for any test whose structure is rewritten.
- **Rationale**: Satisfies C-001/NFR-004/NFR-007 by construction; mirrors the
  existing no-op-stability ratchet already in the repo.
- **Alternatives rejected**: trusting green-on-one-run (misses flakes);
  coverage-percentage-only checks (would not catch a silently dropped nodeid).

## D4 — Volume reduction with preserved power

- **Decision**: Reduce default iteration counts (ULID volume 100→25; sync
  concurrency 50→20 / 20→10) and FSM parity matrix collapse, but retain the
  full-volume variant behind an env-gate (`SPEC_KITTY_ULID_VOLUME_FULL`) /
  `@slow` nightly path.
- **Rationale**: Corruption/uniqueness-detection power scales with volume
  (C-004); the default run only needs a representative scale to prove the
  contract. ULID alone is ~36s/push + ~36s local.
- **Alternatives rejected**: silently lowering volume (weakens a real stress
  guard); deleting the high-volume test (loses the guard entirely).

## D5 — Read-only fixture sharing & caching (with carve-outs)

- **Decision**: Share one migrated-project fixture for the **3 identical
  read-only** migration asserts only; cache whole-tree AST (architectural) and
  DRG graph (doctrine) behind module/session fixtures. **Exclude** integrity,
  idempotency, file-existence, and freshness tests; **exclude** the migration
  counter and rollback/dry-run tests.
- **Rationale**: Read-only sharing is coverage-neutral; the excluded tests
  mutate state or assert freshness and would bleed state if shared (C-007).
- **Alternatives rejected**: module-scoping the destructive `run_migration`
  setup (state bleed destroys failure-path coverage — explicitly rejected by the
  verifier).

## D6 — Templated git-repo fixture

- **Decision**: Build one bare-repo template and clone per test for the common
  "needs a baseline repo" case; gate adoption by an **execution-allowlist** (run
  with the autouse `git init` removed and allowlist every
  `NotInsideRepositoryError`), not by grep-for-symbol.
- **Rationale**: 233 files do real `git init`; grep-by-symbol misses 18
  transitive callers and would silently break them. Bespoke unborn/detached/
  bare/worktree setups keep their own init.
- **Alternatives rejected**: grep-by-symbol gating (misses transitive callers);
  templating worktree/unborn repos (semantics differ).

## D7 — Timing-floor assertions

- **Decision**: Convert wall-clock `elapsed < 0.1` floors (e.g.
  `tests/charter/test_integration.py:427,450`, ~16 across `tests/charter`) to
  `@pytest.mark.timeout(N)` with a generous ceiling; keep the accompanying
  functional asserts (`isinstance`, `len == 2`, spy-call-count) verbatim.
- **Rationale**: The floors flake under CPU contention (blocking parallelism); a
  timeout still trips a pathological O(n) regression. This is the precondition
  that unblocks the charter shard flip.
- **Alternatives rejected**: deleting the timing asserts (loses the perf guard);
  raising the floor (still contention-sensitive).

## D8 — Rollout sequencing

- **Decision**: Wave 1 safe-now quick wins → Wave 2 HOME isolation (isolation
  only, no flips) → Wave 3 de-dup/caching → Wave 4 shard-by-shard flips (charter
  first, run each 2–3× green) → Wave 5 structural fixtures → Wave 6 document the
  local default.
- **Rationale**: Quick coverage-neutral wins first; the single enabling fixture
  next; de-risk collection/topology before flips; publish the local recipe only
  once its preconditions are proven green.
- **Alternatives rejected**: flipping all shards at once (un-ratcheted, high
  flake risk); documenting the local command before isolation lands (would
  corrupt developers' real `~/.spec-kitty`).
