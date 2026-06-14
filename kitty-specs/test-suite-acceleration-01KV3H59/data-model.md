# Phase 1 Data Model — Test Suite Acceleration

This mission has no product data model. The "entities" are test-infrastructure
constructs; this document fixes their shapes, fields, and invariants so the
work packages share one contract.

## E1 — Worker Home Isolation (autouse fixture)

- **Fields / inputs**: xdist `worker_id` (e.g. `gw0`, or `master` when serial),
  a `tmp_path_factory`-derived per-worker base dir.
- **Redirects**: `Path.home()` (monkeypatched), env `HOME`, `USERPROFILE`,
  `LOCALAPPDATA`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`.
- **Invariants**:
  - I1: Two distinct `worker_id`s resolve to two distinct home directories.
  - I2: No test reads/writes/truncates the real `~/.spec-kitty` under xdist.
  - I3: Serial mode (`master`) still gets an isolated home (never the real one).
  - I4: Existing intra-worker queue-wipe fixtures still run (composition, not
    replacement).
- **Scope**: function or worker — must NOT be session-only (re-collision).

## E2 — Volume Gate

- **Fields**: env var name (e.g. `SPEC_KITTY_ULID_VOLUME_FULL`), default scale
  (reduced), full scale (original), marker (`@slow` / nightly).
- **Invariants**:
  - I1: Unset env → reduced scale; truthy env → full scale.
  - I2: The assertion code is identical across scales (only the count changes).
  - I3: The full scale runs in at least one CI path (nightly or env-gated).

## E3 — Collection-Equivalence Check

- **Fields**: shard selector (paths + `-m` expr), serial nodeid set, parallel
  nodeid set.
- **Invariants**:
  - I1: `serial_nodeids == parallel_nodeids` for the shard (set equality).
  - I2: Any intended count change is asserted explicitly with a reviewed delta
    (NFR-007), never silent.

## E4 — Stability Ratchet

- **Fields**: shard selector, run count N (2 or 3), per-run outcome.
- **Invariants**:
  - I1: A flip is accepted only if all N consecutive parallel runs are green.
  - I2: Zero new flaky tests introduced relative to the serial baseline.

## E5 — Templated Git Repo Fixture

- **Fields**: cached bare-repo template path (built once), per-test working
  clone path, allowlist of call sites cleared to adopt it.
- **Invariants**:
  - I1: The template is a plain bare repo — no worktrees, no detached/unborn
    special state.
  - I2: Bespoke setups (unborn/detached/bare/worktree) keep their own init.
  - I3: `cache_clear()` semantics for repo-root resolution are preserved.
  - I4: Adoption is gated by execution-allowlist, covering transitive callers.

## E6 — Read-Only Shared/Cached Fixture

- **Fields**: cached artifact (migrated project / AST tree / DRG graph), scope
  (module or session), exclusion list.
- **Invariants**:
  - I1: Consumers are read-only; no consumer mutates the cached artifact.
  - I2: Integrity, idempotency, file-existence, and freshness tests are excluded.
  - I3: The migration counter and rollback/dry-run tests are excluded (mutating /
    distinct inputs).

## State transitions — per-shard parallelization flip

```
serial (baseline)
  → preconditions met? (IC-01 timing fix for charter; IC-02 HOME isolation for cli/sync/agent/status)
      → collection-equivalence PASS
          → ratchet (N green runs) PASS
              → flipped (parallel, accepted)
          → ratchet FAIL → revert to serial, root-cause
      → equivalence FAIL → revert, fix selector
  → preconditions unmet → stays serial
```
