# Issue matrix — coord-shadows-followups-01KXBCZ1

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

`in-mission` = being fixed by a WP in this mission (non-terminal; must reach a terminal verdict — `fixed` — before mission `done`). `deferred-with-followup` = parent/adjacent/out-of-scope issue this mission does not close. `verified-already-fixed` = the referenced work already shipped; this mission relates to or hardens it.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2574 | Consolidate triplicated subtask-gate-dir resolver → resolve_subtasks_gate_dir() | in-mission | WP01 (FR-001/002/003) — canonical seam in missions/_read_path_resolver.py; weak status_transition site gains git-ancestry fallback; duplicate deleted |
| #2575 | is_process_alive does not guard against PID reuse | in-mission | WP02 (FR-004/005/006) — persisted create_time baseline at all 3 claim sites; companion is_claiming_process_alive; additive degradation |
| #2576 | Harden _mt_uncheck_rollback_subtasks read/write path (follow-up to #2513) | in-mission | WP03 (FR-007) — house-guard write + surfaced-not-swallowed failure mode; out-of-lock design preserved |
| #2567 | acceptance gate _find_unchecked_tasks is a fifth divergent checkbox parser | in-mission | WP04 (FR-008/009) — canonical iter_unchecked_subtask_rows; stray regex removed; tightening ratified |
| #2568 | review lock LockInfo.is_stale uses independent os.kill liveness probe | in-mission | WP05 (FR-010) — folds onto canonical core/process_liveness.is_process_alive |
| #2513 | uncheck tasks.md subtask rows on WP rollback to planned (F3 origin) | verified-already-fixed | Shipped in coord-shadows-arm-closeout; #2576/WP03 hardens robustness (relate-only) |
| #2572 | coord-shadows-arm-closeout PR (predecessor, merged) | verified-already-fixed | Merged; this mission closes its post-merge residuals |
| #2160 | Coord topology: unify artifact authority (parent epic, P0) | deferred-with-followup | This mission is one functional child slice; epic stays open. #2574/#2575/#2576 are native sub-issues |
| #2071 | Test-suite friction epic (parent of #2567/#2568) | deferred-with-followup | Epic stays open; #2567/#2568 are children closed here |
| #2017 | Guards that block legitimate actions / self-write-then-guard (parent of #2566) | deferred-with-followup | Not this mission's epic; #2566 belongs to a separate #2017 slice |
| #2566 | setup-plan / specify scaffold→block friction | deferred-with-followup | OUT of scope (unanimous squad verdict) — different defect class, parent epic #2017; a separate slice owns it |
| #2573 | move-task for_review runs a synchronous multi-minute pre-review gate (reads as hang) | deferred-with-followup | Follow-up: #2573 — out of scope here (C-004 fences WP03 away from _mt_run_pre_review_gate); targeted by the fast-follow loop-friction mission |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
