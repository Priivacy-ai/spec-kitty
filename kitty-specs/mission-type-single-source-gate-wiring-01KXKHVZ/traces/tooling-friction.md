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

- _(to be filled at mission close)_
