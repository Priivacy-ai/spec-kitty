# Tracer — Tooling Friction

Seeded at planning; append when hit; assess at close.

## Known friction to watch

- **Byte-identity freshness gate**: `graph.yaml` MUST be regenerated (`spec-kitty doctrine regenerate-graph`)
  and committed in the same WP, or the freshness twins red. Calibration may widen the diff beyond 21 lines
  (DD-5) — expected.
- **Shared residual doc (#1923)**: `drg-orphan-residual.md` is co-owned; touch only the mission-type/plan-action
  rows to avoid a merge collision (C-003).
- **`_KIND_MAP` silent-drop**: endpoints missing from `_KIND_MAP` are silently dropped by the backfill loop —
  add the `mission_type` entry (DD-3) so this can't bite a future partial-node state.
- **Bare `python`/`pytest`** import the wrong src outside `uv run` — always `uv run` in a lane.

## Friction encountered (append during implementation)

- _(none yet)_

## Assessment (at close)

- _(to be filled)_
