# Mission Tracer — Design Decisions

**Mission**: next-committed-state-authority-01M1CA8W · Issues #2947 + #3780

Append-only record of load-bearing decisions and their rationale.

## D1 — Single state authority for `next` (#2947)

`next` (and `agent tasks status`) must resolve mission/WP state from the **committed status authority** + merge evidence **before** selecting a coordination workspace. A stale/artifact-missing workspace fails closed (structured blocked/error), never a fabricated "unstarted" run. Rationale: today's selection is existence-gated and freshness-blind, so a leftover coordination checkout silently overrides the committed truth.

## D2 — Provenance-gated advancement (#3780)

A canceled work package advances the loop past review/implement **only** with operator provenance, mirroring `is_acceptable_ending(has_provenance=True)`. A synthetic cancellation stays blocking (fail-closed). Route through the single shipped authority (`is_acceptable_ending` / `has_operator_provenance`) — do not add a second lane-only definition.

## D3 — Preserve the fail-loud missing-authority contract

Swapping the lane-only read for a full snapshot must **not** swallow the genuinely-missing-status-log case: the `CanonicalStatusNotFoundError` fail-loud path must survive (scout flagged this as a real trap in a naive `wp_snapshot_state` swap).

## D4 — Merge evidence = committed `mission_number` (post-spec squad resolution)

Terminal detection keys on the committed `mission_number` in `meta.json` (assigned at merge via `assign_next_mission_number` = max+1, `merge/ordering.py:135`; `None` pre-merge) **plus** the reduced committed status all-accepted. NOT transient merge-progress artifacts: `merge-state.json`/`MergeState` is resumable in-progress merge and is *cleared* after merge; `MERGE_HEAD` is an *active* git merge — both absent precisely when a mission is finished. Keying terminality on those would be exactly wrong (code-truth lens finding).

## D5 — Single shared read-path guard (post-spec squad resolution)

FR-002/003/004 converge on one seam: both `next` (via `mission_context_for` → `candidate_feature_dir_for_mission` → `_resolve_mission_read_path`) and `agent tasks status` (via `resolve_handle_to_read_path` → `_resolve_mission_read_path`, `tasks_status_cmd.py:178`) resolve through `_resolve_mission_read_path` (`_read_path_resolver.py:868`). The "prefer committed authority / fail-closed on artifact-missing workspace" behavior lands ONCE at that shared seam; only the terminal-verdict *emission* (`kind: terminal`) is `next`-specific in `query_current_state`. Avoids two divergent stale-detection implementations (the drift class C-006 guards).

## D6 — Single reduction preserves fail-loud (post-spec squad resolution)

`get_wp_lane` (`lane_reader.py:51`) fail-louds via `_require_event_log` → `CanonicalStatusNotFoundError` on an absent log; `wp_snapshot_state` (`reducer.py:532`) returns `None` silently on the same. A naive swap breaks C-003. The only design satisfying both C-003 (fail-loud) and C-004 (no redundant reduction) is a **single** `reduce()` per WP that yields lane AND `reason_source`, fronted by an explicit `has_event_log`/`_require_event_log` gate. This is the load-bearing #3780 implementation constraint — NOT the "swap get_wp_lane→wp_snapshot_state" the issue pointer implies.

## D8 — #2947 pre-check lives in `query_current_state`, NOT the shared resolver (post-plan squad F1, BLOCKER)

The prior draft put the "prefer committed authority" guard at `_resolve_mission_read_path`. Wrong locus: that seam has ~9 non-test callers (implement flow `mission_feature_resolution.py:199`, accept gate `acceptance/__init__.py:888`, orchestrator_api, every runtime read via `mission_context_for`) and a documented pure-path contract (`_read_path_resolver.py:555`). Injecting committed-authority preference there reroutes unrelated reads AND is internally contradictory (a pure resolver cannot detect a stale-but-present coord dir without a freshness signal, which D7 forbids). Resolution: the terminal/committed pre-check goes in `query_current_state` BEFORE `mission_context_for` (`runtime_bridge.py:2310`); the resolver stays pure. FR-003 artifact-missing is served by the resolver's EXISTING `require_exists=True` → `StatusReadPathNotFound` (per-caller flag), not a global change.

## D9 — Terminal check reads the PRIMARY/committed surface (post-plan squad F4, BLOCKER)

`_finalized_task_board_override_step` (`runtime_bridge.py:652`, invoked :2391) already does all-done detection but reads `status_state.read_dir` — the SELECTED, possibly-stale surface — which is the bug engine. The new terminal check MUST read `mission_number` (`read_primary_meta`, `_read_path_resolver.py:820`) + committed status from the primary feature dir, and short-circuit BEFORE `_finalized_task_board_override_step` runs. The existing :683-689 `done`/`accept` branches stay for the unmerged (`mission_number`-absent) path.

## D10 — The board is NOT fixed "by construction" (post-plan squad F2)

`agent tasks status` reads `tasks/` from PRIMARY but WP lanes from the coord `feature_dir` (`tasks_status_cmd.py:178,193`), plus a legacy fallback (:179-188) that re-derives a stale path. FR-004 needs its own committed-lane read fix + board regression in WP02; it does not fall out of the #2947 loop fix.

## D11 — One shared acceptable-ending fold, reused by predicate + terminal (post-plan squad F6)

Both the #3780 predicate (per-WP) and the #2947 terminal check (all-WP fold) need the single-reduction→lane+`reason_source`→`is_acceptable_ending` machinery. Factor it once in a new `src/runtime/next/committed_authority.py` (IC-01), consumed by both. Avoids WP02 re-deriving a second reduction/fold (C-004, DIRECTIVE_044).

## D12 — Decompose by LAYER, not by issue (ownership resolution)

Both #3780 (`_should_advance_wp_step`) and #2947 (`query_current_state`) live in `runtime_bridge.py`; owned_files cannot overlap. Resolution: WP02 (foundation) owns the new `committed_authority.py` module (IC-01/IC-02) + the board (IC-04) — no `runtime_bridge.py` edit; WP01 (depends WP02) owns all `runtime_bridge.py` loop edits (IC-03), consuming WP02's module. Acyclic, non-overlapping, and it embodies the single-authority principle (WP02 builds the authority, WP01 consumes it). F5 invariant: the #2947 pre-check fires ONLY when `mission_number` present AND committed status resolves — zero behavior change otherwise (protects in-flight query fixtures).

## D13 — #2947 fixes BOTH `next` entry points (post-tasks squad BLOCKER-2)

The issue's actual repro used `spec-kitty next --result success` = ADVANCING mode → `decide_next` → `runtime_bridge.decide_next_via_runtime` (`runtime_bridge.py:2090`), which CAN emit `kind: terminal`. QUERY mode (`query_current_state:2289`) is structurally `kind: query` only (every builder hardcodes it; `tests/contract/test_next_no_implicit_success.py:127` asserts it). Resolution: the `mission_terminal_verdict` pre-check is consumed by BOTH — advancing returns `kind: terminal` (matches the issue), query returns `kind: query`/`mission_state="done"` (finalized-override precedent `:2153`). Both live in `runtime_bridge.py` (WP02-owned; `decide_next` in decision.py is a thin delegator) — no owned_files change. This makes FR-008 (one authority, both surfaces) literal.

## D14 — Sanctioned PRIMARY-surface primitives (post-tasks squad BLOCKER-1)

`primary_feature_dir_for_mission` was DELETED; manual primary-path composition trips `tests/architectural/test_no_read_side_bypass.py` (which does NOT sanction `src/runtime/next/`). `committed_authority.py` uses the sanctioned primitives: `read_primary_meta(repo_root, slug)` (`_read_path_resolver.py:819`, returns `(meta, declares_coordination)`) for `mission_number`, and `runtime_bridge_identity._primary_runtime_feature_dir(repo_root, slug)` (identity seam — does NOT import runtime_bridge, so no cycle) for the primary status dir.

## D15 — New module needs an in-WP01 consumer (post-tasks squad NICE-8)

`committed_authority.py` is consumed by WP02 (which lands AFTER WP01), so in isolation it risks the `test_no_dead_modules`/`test_no_dead_symbols` gates. Resolution: WP01's board fix (IC-04, `tasks_status_cmd.py`) consumes `committed_authority` for the committed lane — giving the module an in-WP01 importer. WP01 T006 runs the arch-gate suite explicitly.

## D7 — "Stale" dissolves into "prefer committed authority" (post-spec squad resolution)

No new git-commit-freshness detector is needed. The #2947 fix is to consult the committed status authority (not the coord checkout's reduced state) first; a stale checkout simply loses to committed authority. The only fail-closed workspace check is *artifact-missing* (which maps to the existing `require_exists`/`CoordinationBranchDeleted` seam), keeping FR-003 within the existing surface rather than growing a freshness seam.
