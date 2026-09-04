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

## Close assessment (2026-08-31)

- **Both issues fixed, one cohesive mission.** #2947 (state authority) + #3780 (provenance-gated advancement) share the committed-authority module (`committed_authority.py`); the decompose-by-layer split (authority+board → loop) kept owned_files disjoint and made the single-authority principle literal.
- **Disambiguate-before-routing paid off.** Four adversarial point-cuts (post-spec ×2, post-plan, post-tasks) caught **five** BLOCKERs before a line of impl was written: the shared-seam mis-placement (F1), the terminal-surface ambiguity (F4), the deleted `primary_feature_dir_for_mission` primitive (BLOCKER-1), and the two-entry-point / query-mode-`kind` reconciliation (BLOCKER-2). Every one would have produced a wrong or non-compiling implementation.
- **Live evidence held the line on #3780.** The stall was proven gone by driving the real `decide_next_via_runtime` after advancing the runtime engine to the review step (operator-cancel → advances review→accept; synthetic → stalls) — not static reading. A pre-merge review-squad fold then corrected the query-mode `blocked_conflict` `kind` to preserve the `is_query` invariant.
- **Delivered as draft PR #3825 (Priivacy-ai), operator merges.** 7 clean linear commits off upstream/main; full-sweep verify green (arch gates, guard suites, 809-test affected smoke, docs-freshness, ruff/mypy).
- **Deferred (tracked in PR):** two #3780 secondary observations (done_bookkeeping redundant read; upstream_contract reason_source denylist) and two perf items (board O(N) reductions; redundant primary-meta read — coordinate with `next-latency-durable-fix`).
