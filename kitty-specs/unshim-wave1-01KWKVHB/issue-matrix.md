# Issue Matrix — unshim-wave1-01KWKVHB

<!-- Schema: issue | title (optional) | verdict | evidence ref (mandatory) -->
<!-- Valid verdicts: fixed | verified-already-fixed | deferred-with-followup | in-mission -->

| Issue | Title | Verdict | Evidence ref |
|---|---|---|---|
| #2289 | closes: delete 8 category_4 shims + re-anchors | in-mission | WP01 (lane-a): 7 shims deleted + 9 import sites re-anchored to spec rev-2 census paths; tasks_support handled in WP02 (lane-b). IC-01 criteria met; gate/config drain atomic. Issue body 4 wrong canonical-home cells + "~15 imports" estimate corrected by squad census (spec table is authoritative). |
| #2292 | closes: 6 category_7 orphan adjudication | in-mission | WP01/WP03: 4 executed deletes (FR-004/FR-005 lane-a); policy.audit follow-up (FR-006); auth.transport documented-deferred per ADR 2026-05-18-2/Robert (FR-007). Meets ≥4 resolved AC. Blocker misattribution (#2292 body → ADR/Robert) corrected via comment. |
| #1797 | parent epic: unshim + category debt progress | in-mission | Progress comment at merge: category_4 drained 8→1 (WP01) →0 (WP02); category_7 6→2 (WP01); category_b 237→224 (WP03). |
| #2258 | closes: pre-mission dead-code cleanup | fixed | Executed as governed pre-mission op (invocation 01KWKWQC58KWSN3VDCZ3VZB2GR, commit c194f8d on this branch, −248 LOC): deadness verified incl. merge_history reader-chain check; both functions + 4 test classes deleted; gates green. Rides this mission's PR (`Closes #2258`). Evidence comment posted on the issue. |
| #2124 | reference: event-sync rework (supersedes orphans) | verified-already-fixed | Closed. Event-sync mission rebuilt the delivery/replay domain and still left sync.replay + tracker_client_glue orphaned → both WP01 deletions safe on that basis. |
| #2131 | reference: event-sync PR landed | verified-already-fixed | PR #2131 merged. Supersedes sync.replay and left tracker_client_glue orphaned; WP01 deletes both on that basis. |
| #2280 | reference: uncommitted-retrospective-files bug | verified-already-fixed | CLOSED. #2292 misreads as a wire signal for retrospective.lifecycle — it is the uncommitted-retrospective-files bug; unrelated. Delete verdict stands on zero-importers grounds. |
| #2290 | boundary: charter_lint/freshness deprecation | deferred-with-followup | Wave 2 follow-up: #2290. Post-spec squad NO-FOLD verdict (paula): has live legacy-name callers needing re-point + additive `__deprecated__` markers, violating C-002 deletion-only identity. Wave 2 slice. |
| #2291 | boundary: specify_cli.next / glossary removals | deferred-with-followup | Wave 2 follow-up: #2291. Post-spec squad NO-FOLD verdict (paula): live-caller re-point migration, categorically different risk class; folding would ~double the mission. |
| #2293 | boundary: Wave 2 unshim item | deferred-with-followup | Wave 2 follow-up: #2293. Out of scope per C-003; this wave establishes accurate baselines for Wave 2 planning. |
