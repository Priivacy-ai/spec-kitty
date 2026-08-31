# Mission Tracer — Approach

**Mission**: next-committed-state-authority-01M1CA8W · Issues #2947 + #3780 · Milestone 3.2.6

Append-only log of the approach taken. Seeded at planning; appended during implementation; assessed at close.

## Planning (2026-08-31)

- Folded two issues into one mission: shared defect class — the `next` loop resolves state from the wrong authority (stale coordination checkout / lane-only predicate) instead of the committed status + operator provenance.
- Two profile-loaded scouts mapped the surface with file:line precision before any spec text (disambiguate-before-routing).
  - #3780 is well-localized: `_should_advance_wp_step` / `_wp_blocks_step` in `runtime_bridge.py:692-738`; route review/implement through `is_acceptable_ending` / `has_operator_provenance` (`status_lanes.py:42,70`); snapshot source `wp_snapshot_state` (`reducer.py:532`) gives `reason_source` at zero extra I/O.
  - #2947 is more architectural: status surface selected topology-first, existence-gated, freshness-blind in `query_current_state` (`runtime_bridge.py:2289`) → `mission_context_for` (`resolution.py:1043`) → `_read_path_resolver`. No merged/terminal authority consulted before workspace selection. `agent tasks status` shares the root cause via `resolve_handle_to_read_path`.
- Base: clean `main` == `upstream/main` (eff6353260); mission on PR-bound `fix/next-committed-state-authority`.

## Implementation

- **WP01 (foundation) landed + approved.** `committed_authority.py` (`wp_ending` single-reduction+fail-loud fold; `mission_terminal_verdict` PRIMARY-surface, mission_number-keyed) + `agent tasks status` board reads committed lanes. Sonnet implementer → opus independent review APPROVE (61 targeted+arch-gates & 2048 broad green, ruff+mypy --strict clean, zero diff to status_lanes/lane machine, 4 deviations sound). RED-first regressions genuine (two-surface stale-coord fixture).
- **Lane-hygiene friction** (recorded in tracer-tooling-friction + memory): mark-status in the lane polluted the lane with kitty-specs → blocked for_review; dependent-lane (WP02) allocation auto-merge conflicted on those kitty-specs → resolved with `git merge -X ours lane-a` (took WP01 code, kept lane-b kitty-specs).
- **WP02 (next loop) dispatched** (sonnet) once WP01 code was in lane-b HEAD.
- (append as WPs land)

## Close assessment

- (append at mission close)
