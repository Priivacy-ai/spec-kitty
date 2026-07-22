# Tracer — Tooling Friction

Seeded at planning; appended when friction is hit; assessed at close. Feeds the guard/gate friction trace
(#2017) and the next mission.

## Known friction to watch (from memory + kickoff)

- **CI-only gates.** The dead-symbol gate (`test_no_dead_symbols.py`) and terminology guard
  (`test_no_legacy_terminology.py`) are NOT caught by a local `pytest tests/charter` — they only fail at the
  arch_shard_1 CI pole. Must reproduce locally before push (quickstart SC-006).
- **Bare `python`/`pytest` in a lane imports the PRIMARY `src`.** Always `uv run` inside lanes/clones.
- **Coord-topology commit friction.** This mission is coord-bound; the status daemon can auto-commit staged
  files with the previous mission's message — commit promptly and reword any stray `chore(<other>):`.
- **DRG freshness** is byte-for-byte; if mission-type discovery or the graph changes, regenerate + verify.

## Friction encountered (append during implementation)

- _(none yet)_

## Assessment (at close)

- **Highest-leverage friction: per-lane review is blind to cross-lane symbol/seam changes.** Two of the
  costliest issues (the CANONICAL cross-lane import; the doctor-test patch-target invalidated by WP06's
  seam change) were individually-green-per-lane and only caught by the terminal WP's aggregate pole and the
  pre-merge review. Takeaway: for a mission where one WP retires/moves a symbol another WP references, the
  aggregate/pre-merge gate is not optional — it's the only place these surface.
- **Gate-scope gaps recurred:** `ruff` scoped to source-only missed test-file lints (WP01); the
  arch-pole-only aggregate check missed non-arch red tests (doctor, import-io) — the pre-merge *reviewer*
  caught them, not automation. A full targeted-suite run on the aggregate (not just the arch pole) should be
  standard before hand-off.
- **A design carve-out (C-012) interacted with pre-existing architecture (eager `charter/__init__`) in a
  way the plan didn't foresee** — the "zero import-time I/O" NFR was only achievable to a ≤1-cached bound
  given the eager import chain + the dead-symbol gate's static-definition requirement. Recorded so it isn't
  re-litigated.
- coord-topology + `move-task` mechanics (matrix on the coord branch, sync-minimal flag, clean-tree
  preflight) added real overhead per transition — the running #2017 guard-friction trace should capture it.
