# Implementation Plan: Next Resolves State From Committed Authority

**Branch**: `fix/next-committed-state-authority` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/next-committed-state-authority-01M1CA8W/spec.md` · Issues #2947 (P1), #3780 (P2) · Milestone 3.2.6

## Summary

Route the `spec-kitty next` control loop (and the `agent tasks status` board) through the **committed status authority** and the **operator-provenance authority**, instead of a stale coordination worktree checkout or a lane-only predicate.

Two independent defects, one theme:
- **#2947** — `next` selects a coordination workspace *before* consulting committed state; the selection is existence-gated and freshness-blind, so a leftover coordination checkout at an old commit makes a merged mission look unstarted (`kind:step` / discovery / research), and `agent tasks status` rolls it up all-`planned`.
- **#3780** — the step-advancement predicate `_wp_blocks_step("review", …)` is lane-only, so an operator-canceled WP (an honest ending post-#3774) stalls the loop; provenance is not available at the call site.

The fix **consumes** the already-shipped `is_acceptable_ending` / `has_operator_provenance` authority (#3774) and the committed `mission_number` merge signal; it does **not** touch that authority, the lane state machine, the transition matrix, or the shared read-path resolver's pure-path contract.

> **Design provenance**: this plan incorporates the post-plan adversarial squad (architect lens). Its two BLOCKERs relocated the #2947 pre-check out of the shared path resolver into `query_current_state` (F1), pinned the committed *surface* the terminal check reads (F4), and factored the acceptable-ending fold into one shared helper (F6). See tracer-design-decisions D8–D12.

## Technical Context

**Language/Version**: Python 3.11+
**Primary surfaces**:
- `src/runtime/next/runtime_bridge.py` — `_should_advance_wp_step` (:692), `_wp_blocks_step` (:727), `query_current_state` (:2289), `mission_context_for` call site (:2310), `_finalized_task_board_override_step` (:652, invoked :2391)
- **NEW** `src/runtime/next/committed_authority.py` — the shared committed-authority + acceptable-ending fold module (see IC-01/IC-02)
- `src/specify_cli/missions/_read_path_resolver.py` — `read_primary_meta` (:820), `primary_feature_dir_for_mission`, `_resolve_mission_read_path` (:868, **kept pure — not modified for behavior**), existing `require_exists=True` → `StatusReadPathNotFound` (:566)
- `src/specify_cli/cli/commands/agent/tasks_status_cmd.py` — `_st_resolve_dirs` (:152, resolve :178, legacy fallback :179–188), `_st_runtime_row`→`reconstruct_wp_view` (:219)
- `src/specify_cli/status/reducer.py` — `wp_snapshot_state` (:532); `status/lane_reader.py` — `get_wp_lane`/`_require_event_log` (:51/:43)
- `src/specify_cli/status_lanes.py` — `is_acceptable_ending` (:42), `has_operator_provenance` (:70) — **consumed, not modified**
**Testing**: pytest. `tests/specify_cli/next/test_runtime_bridge.py` (#3780 direct-unit); new `tests/runtime/next/test_merged_mission_terminal.py` (#2947 via `query_current_state`); board regression in `tests/specify_cli/cli/commands/agent/` (tasks status); guard-preserving `tests/runtime/test_bridge_parity.py` (+ `_bridge_oracle.py`), `test_bridge_decide_next.py`, `test_bridge_composition.py`, `tests/next/test_query_mode_unit.py`, `tests/contract/test_next_no_implicit_success.py`.
**Constraints**: no new data model; consume existing status reduction (`reason_source`) + `meta.json.mission_number`. No wall-clock latency regression on `next`; **single status reduction per WP** (C-004).
**Scale/Scope**: two localized behavioral fixes over a small shared authority module; ~4–5 source files, disjoint ownership.

## Charter / Constitution Check

*GATE: must hold through implementation.*

- **ATDD / red-first (C-011, DIRECTIVE_034, ADR 2026-07-17-1)** — each WP lands its issue-pinned `@pytest.mark.regression` repro as the FIRST lane commit, RED on `planning_base_branch`, GREEN on final. #3780 additionally needs a **live** `next`-run proof (C-007).
- **Single canonical authority (DIRECTIVE_044, FR-007/FR-008)** — one acceptable-ending fold (IC-01) consumed by both the predicate and the terminal verdict; one committed-authority reader (IC-02). No second predicate, no second stale-detection path.
- **Do-not-touch surfaces (C-001/C-002)** — `is_acceptable_ending` authority and the lane state machine are pure dependencies. `_resolve_mission_read_path` keeps its documented pure-path contract (F1) — no behavior injected there.
- **Fail-loud preservation (C-003)** — both the per-WP fold (IC-01) and the primary-surface committed read (IC-02) preserve today's fail-loud on a genuinely-absent status log; a naive `get_wp_lane`→`wp_snapshot_state` swap silently breaks it.
- **Locality of change (DIRECTIVE_024)** — the #2947 pre-check lives in `query_current_state`, not the shared resolver; the 9 other resolver callers are untouched (F1).
- **Terminology canon (C-006)** — distinguish *committed status authority* from *materialized-but-stale coordination worktree checkout*; name the *read-path-resolution* seam. No `feature*` domain leakage in new prose.

No Constitution violations require Complexity Tracking.

## Design — Implementation Concerns (IC)

### IC-01 · Shared acceptable-ending fold (the one authority atom) — `committed_authority.py`

A single pure helper both fixes consume, so there is exactly one definition (FR-007, DIRECTIVE_044):
- `wp_ending(feature_dir, wp_id)` → derives lane **and** `reason_source` from a **single** status reduction (C-004), fronted by an explicit `has_event_log`/`_require_event_log` gate so a genuinely-absent log still raises `CanonicalStatusNotFoundError` (C-003). Returns lane + `is_acceptable_ending(lane, has_provenance=has_operator_provenance(snapshot))`.
- Discriminator: `has_operator_provenance` reads `reason_source == "operator"`; synthetic (`"synthetic"`, empty, `"Force move to "`/`"move-task: "` templates) → not acceptable (fail-closed, NFR-002).

### IC-02 · Committed terminal/conflict verdict from the PRIMARY surface — `committed_authority.py`

`mission_terminal_verdict(repo_root, mission_slug)` → `{terminal | blocked_conflict | none}`, read **only** from the committed/primary surface (F4), never the coord checkout:
- `mission_number` via `read_primary_meta` (`_read_path_resolver.py:820`); committed status from `primary_feature_dir_for_mission`.
- `mission_number` assigned **and** every WP acceptable-ending (IC-01 fold) → `terminal`.
- `mission_number` assigned **but** not all-accepted → `blocked_conflict` (FR-009).
- `mission_number` absent → `none` (proceed on the unmerged path).
- Committed status log genuinely absent → `none` (fall through to today's behavior; do NOT read absence as conflict — C-003, F6).
- Merge signal is the committed `mission_number` ONLY — never transient merge-state/`MERGE_HEAD` (C-005).

### IC-03 · `next` loop routing through IC-01/IC-02 — `runtime_bridge.py`

- **#2947 terminal pre-check** in `query_current_state`, placed **before `mission_context_for` (:2310)** so it never sees the stale surface and `_finalized_task_board_override_step` (:652/:2391) never runs on a merged mission (F4):
  - `terminal` → emit the existing terminal result shape (`kind: terminal`, `mission_state="done"`; cf. :2153/:2268), no runtime run created.
  - `blocked_conflict` → emit `kind: blocked` with a pinned conflict reason (reuse an existing `DecisionKind.blocked` reason schema; F6 — pin at implement).
  - `none` → today's flow unchanged. **Invariant (F5): the pre-check fires only when `mission_number` is present AND committed status resolves**; otherwise zero behavior change — protects the many in-flight query fixtures.
  - FR-003 artifact-missing on the unmerged actionable path is served by the resolver's existing `require_exists=True` → `StatusReadPathNotFound` (F1) — wire/verify, do not add global behavior.
- **#3780 predicate** — `_should_advance_wp_step`/`_wp_blocks_step` consume IC-01’s fold. Extend `_wp_blocks_step(step_id, state, has_provenance=False)` (default keeps its single caller + test monkeypatches stable); route `review` through `is_acceptable_ending`. **Do NOT** change `_should_advance_wp_step`'s public 2-arg signature (callers :785/:1574, `runtime_bridge_composition.py:500`).

### IC-04 · `agent tasks status` board reads committed lanes — `tasks_status_cmd.py`

The board's lane rollup must read committed authority, not the coord `feature_dir` (F2). `_st_resolve_dirs` reads `tasks/` from PRIMARY (:193) but WP lanes flow from the coord-aware `feature_dir` (:178) consumed by `_st_runtime_row`→`reconstruct_wp_view` (:219); a legacy fallback (:179–188) is a second stale route. Point the lane/status read at committed authority and close the legacy fallback; carry a board-level regression (SC-002) — do **not** rely on any "fixed by construction" claim.

### No new data model / contracts

Consumes existing `StatusEvent` reduction (`reason_source`) and `meta.json.mission_number`. No schema/envelope/contract change. (The #3780 secondary `upstream_contract.json` observation is out of scope — C-008.)

## Parallel Work Analysis

### Dependency Graph

```
WP01 (foundation: committed-authority module IC-01/IC-02 + board IC-04)
        │
        ▼
WP02 (runtime_bridge.py loop routing IC-03 — #3780 predicate + #2947 pre-check)
```

Decomposed **by layer, not by issue**, so owned_files never overlap: only WP02 edits `runtime_bridge.py`; WP01 owns the new authority module + the board. This dissolves the earlier shared-file tension (the disjoint-region merge worry in the prior draft was factually overstated — regions are ~40 lines / a full function apart and would not conflict; the real reason to order the WPs is that WP02 *consumes* WP01's module).

### Work Distribution

- **WP01 — Committed-authority module + status board** (foundation; model: sonnet). Owns `src/runtime/next/committed_authority.py` (IC-01 fold + IC-02 verdict), `src/specify_cli/cli/commands/agent/tasks_status_cmd.py` (IC-04), and their tests. Carries the #2947 **board** regression (`agent tasks status` reports committed lanes) + fold/verdict unit tests. No `runtime_bridge.py` edit. `dependencies: []`.
- **WP02 — `next` loop routing** (model: sonnet). Owns `src/runtime/next/runtime_bridge.py` (IC-03), `tests/specify_cli/next/test_runtime_bridge.py`, `tests/runtime/next/test_merged_mission_terminal.py`. Carries the #3780 regression (predicate + **live** `next` run) and the #2947 **next-restart** regression (via `query_current_state`). `dependencies: [WP01]`.

### Coordination Points

- **Ownership guard**: `runtime_bridge.py` is owned solely by WP02; the committed-authority module + board solely by WP01. No glob overlap (the real no-overlap guard, charter Standing Order #8).
- **Shared authority**: both consume `status_lanes.is_acceptable_ending`/`has_operator_provenance` unchanged; a diff to either is a review-blocking scope breach (C-001).
- **Guard-preserving exit criteria (WP02, the runtime_bridge loop change)**: keep green the parity/oracle suites (`tests/runtime/test_bridge_parity.py:817`, `_bridge_oracle.py`), `test_bridge_decide_next.py`, `test_bridge_composition.py`, `tests/next/test_query_mode_unit.py`, `tests/contract/test_next_no_implicit_success.py` (F5), and the existing `tests/specify_cli/next/test_runtime_bridge.py:229` (implement-canceled).
- **Integration**: after both lanes, full-sweep verify (arch shards, docs-freshness, terminology baselines) + a live `next` run for the #3780 stall proof (C-007).
