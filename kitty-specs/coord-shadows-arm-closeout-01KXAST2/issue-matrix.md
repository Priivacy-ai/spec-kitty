# Issue Matrix: Close #2160 Coord-Shadows Read/Gate Arm (coord-shadows-arm-closeout-01KXAST2)

Canonical schema. Verdicts: `fixed` | `verified-already-fixed` | `deferred-with-followup`
(needs a `#NNN` / `Follow-up:` handle) | `in-mission` (closed by a later WP in this mission; must
resolve to a terminal verdict before merge). Evidence refs are filled with real commit SHAs at
mission close.

| Issue | Verdict | Evidence ref | Scope |
|-------|---------|--------------|-------|
| #2502 | fixed | Aggregate cherry-pick of PR #2503 (`255ecf938`) + WP02 emit-layer hardening | Dashboard artifact viewers read the PRIMARY planning surface, not the coord husk. Landed via the faithful aggregate on this branch; WP02 makes all emit callers primary-correct. |
| #2504 | in-mission | WP01 canonical `_walk_wp_section` (`3f68accfb`) + aggregate PR #2505 | Dashboard WP cards show 2/4 subtask progress. Aggregate shipped the feature; WP01 unifies the row-counting semantic it shares with the guard. Resolves to `fixed` at merge. |
| #2510 | in-mission | WP02 IC-EMIT-CORE (`_infer_subtasks_complete` primary-surface + fail-open close) | Orchestrator-api / native `agent status` for_review gate no longer fails open. Closed by WP02 (+ WP03 retires the redundant #2511 per-door patch). Resolves to `fixed` at merge. |
| #2511 | fixed | PR #2511 incorporated into the aggregate (`da3ed8319`); its per-door patch is retired by WP03 | The orchestrator-api subtask-gate fix. Superseded/incorporated: the shared-layer WP02 fix + WP03 dedup make it correct on every path. |
| #2512 | fixed | Aggregate PR #2514 worktree-recovery (`d9d60fa83`) + WP04 sparse-checkout fix (`4a0c3c7ad`) + WP06 rollback marker-clear seam | Stale-claim lane-allocation failure after OS kill. Recovery landed in the aggregate; WP04 fixes the sparse-checkout regression it introduced; WP06 consolidates the marker-clear. |
| #2513 | in-mission | WP01 canonical uncheck writer (`3f68accfb`) + aggregate PR #2515 | Rollback unchecks tasks.md subtask rows. Aggregate shipped the writer; WP01 corrects its re-appearing-heading re-enter bug. Resolves to `fixed` at merge. |
| #2514 | fixed | PR #2514 incorporated into the aggregate (`d9d60fa83`); its sparse-checkout regression fixed by WP04 | The stale-claim/lane-recovery three-part fix. Incorporated with attribution; the regression it carried is closed by WP04 (FR-006). |
| #1231 | in-mission | WP05 IC-LIVENESS (`core/process_liveness.is_process_alive` + stale-indicator live-claim suppression) | Stale-WP indicator false positives. Closed by WP05 (FR-007). Resolves to `fixed` at merge. |
| #1862 | verified-already-fixed | #1764 `analysis_report._normalize_tasks_md`; pinned by WP06's FR-009 regression guard | Analysis-freshness checkbox-insensitivity already shipped under #1764; this mission adds a regression guard only (no new logic). |
| #1764 | verified-already-fixed | `analysis_report._normalize_tasks_md` (`_CHECKBOX_RE`), pinned by WP06/FR-009 | The mechanism that makes freshness checkbox-insensitive; referenced as the reason #1862 needs no new code. |
| #2160 | deferred-with-followup | Follow-up: #2160 (parent epic remains open) | Parent epic. This mission closes the read/gate arm of the coord-shadows-primary class; the umbrella epic stays open for other children. |
