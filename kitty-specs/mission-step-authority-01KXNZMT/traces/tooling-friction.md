# Tooling / Gate Friction — Step authority (S-B)

Tracer (seeded at planning; append when friction is hit). Feeds #2017 + the retro.

## Anticipated gate landmines

- **`extra="forbid"` silent strip** — new `MissionStep` fields not added to `_STEP_YAML_TO_MODEL`
  (`mission_step_repository.py:120`) are dropped silently; a parity test can pass while the field vanishes. Add a
  field-round-trip test.
- **DRG freshness (byte-identity)** — the projection must sort deterministically (`sequence_index`) or
  `regenerate-graph --check` goes stale. Re-run after any extractor/projection change.
- **Hot-path I/O** — deriving `action_sequence` on `MissionType` via the step repo can inject filesystem I/O onto
  runtime hot paths; must be cached (NFR-007).
- **Terminology guard + arch suite are CI-heavy** — run `tests/architectural/` before pushing.
- **Lane bare-python imports primary src** — in a lane/clone always `uv run pytest`, never bare `python`.

<!-- Append actual friction (command + fix) during implement. -->

## Implement-review friction (2026-07-16)

- **Pre-existing mypy red on main (NOT S-B):** `src/runtime/next/_internal_runtime/schema.py:29` — `Class cannot subclass "StructuredError" (has type "Any")`. Confirmed pre-existing on the S-A base (errors standalone). WP07's aggregate `mypy --strict` gate will surface it — do NOT attribute to S-B; it is a pre-existing-main issue. If the aggregate gate must be clean, scope mypy to the S-B diff or note this as a known pre-existing red for the PR.
- **Dispatched implementers stalled twice (WP02, WP06)** by backgrounding their gate suite instead of running it foreground; orchestrator completed the handoffs. See memory feedback_dispatched_impl_foreground_tests.
