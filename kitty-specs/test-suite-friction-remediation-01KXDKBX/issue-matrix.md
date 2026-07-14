# Issue matrix — test-suite-friction-remediation-01KXDKBX

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2071 | Epic: Tests as scaffold, not friction | deferred-with-followup | Umbrella epic — stays open; mission #2620 is a native sub-issue closing several children in-mission |
| #1931 | EPIC: Test quality & suite hygiene | deferred-with-followup | Umbrella epic — stays open; parent of #2071 |
| #2609 | CI test-topology performance (sibling PR) | verified-already-fixed | Merged into upstream/main; this mission is its declared follow-up tail |
| #2073 | CT2: de-theater security path-validation tests | verified-already-fixed | Closed 2026-07-12 (commit d883b26c0); test_path_validation.py has zero xfail |
| #2077 | CT7: positional-anchor recurrence guard | verified-already-fixed | Closed 2026-07-12 (0705404e6); test_ratchet_positional_anchor_ban.py landed |
| #2564 | test-gate hole: seed-tuple laundering evades #2077 ban | in-mission | WP06 (Lane A) — FR-005 |
| #2559 | dead-code gate blind to first-party module.attr access | in-mission | WP01 (Lane 0) — FR-001/002 |
| #2075 | CT4: re-point mock-wiring 'assert HOW not WHAT' tests | in-mission | WP08 (Lane A) — FR-007 |
| #2561 | runtime_bridge compat-delegate surface (retire) | in-mission | WP02/WP03/WP04 (Lane 0) — FR-003 |
| #2293 | unshim: burn down category_b_grandfathered_legacy | in-mission | WP05 (Lane 0) — FR-004 |
| #2076 | CT5: stale golden-count assertions + tail | in-mission | WP07 flagship + WP11-14 sweep (Lane A/C) — FR-006/014 |
| #2074 | CT3: meta/mission test factory delegating to production | in-mission | WP09 (Lane A) — FR-008 |
| #2553 | test_example_round_trip legacy-contract backfill | verified-already-fixed | WP10 confirmed real record_property fix (14 nudges surface, 0 warnings) — closeable |
| #2309 | daemon-reaper kill-gate contract (product bug) | deferred-with-followup | Follow-up: #2309 stays open as its own red-first bugfix mission (product bug, not test-hygiene) |
| #2295 | triage the 17 CI-quarantined tests | verified-already-fixed | WP10 recount = 1 marker (17 already resolved; #2309 is skip-not-quarantine) |
| #2621 | shard registry import-side-effect → explicit register() seam | in-mission | WP16 (Lane B) — FR-011 |
| #2622 | quality-gate.needs ⊇ pytest-jobs guard | in-mission | WP17 (Lane B) — FR-012 |
| #2623 | Sonar UI-e2e coverage denominator | in-mission | WP17 (Lane B) — FR-013 |
| #2616 | gc2b exact-selection ratchet over-fires | in-mission | WP15 (Lane B) — FR-015 |
| #2463 | drop pre-3.2.x legacy mission support (empty-mid8) | deferred-with-followup | Routed out — unsafe to delete now (3-meaning sentinel live); own #1797 sentinel-disambiguation slice |
| #2603 | de-god next_step (CC36) | deferred-with-followup | Routed out → #1797 (no Thread-A test overlap) |
| #2604 | reduce _mt_commit_wp_file complexity | deferred-with-followup | Routed out → #1797 |
| #2465 | workflow.py resolver consolidation | deferred-with-followup | Routed out → #1797 / surface-resolver cluster #1716 |
| #1797 | Epic: dead-code & LOC reduction | deferred-with-followup | Follow-up: #1797 (this epic is the tracking root for the routed-out god-decomps) |
| #2173 | Epic: infra-to-logic separation | deferred-with-followup | Follow-up: #2173 (this epic is the tracking root for the routed-out port extractions) |
| #2342 | retrospective 200-mission summary perf | deferred-with-followup | Follow-up: #2342 stays open (perf/reliability slice, not test-hygiene) |
| #2323 | test_example_round_trip allowlist backfill | deferred-with-followup | Follow-up: #2323 stays open (count-keyed baseline churn, not fixable friction) |
| #2308 | Wave-2 tasks.py degod | verified-already-fixed | Merged (proof-of-mechanism, 4569→1206 LOC) |
| #2059 | decompose cli/commands/doctor.py | deferred-with-followup | Routed out → #1797 |
| #2057 | decompose cli/commands/merge.py | deferred-with-followup | Routed out → #1797 |
| #2026 | Epic: merge.py god-module decomposition | deferred-with-followup | Routed out → #1797 |
| #2056 | decompose agent/mission.py | deferred-with-followup | Routed out → #1797 |
| #2532 | decompose charter/context.py | deferred-with-followup | Routed out → #1797 |
| #2560 | runtime_bridge degod strangler slice | deferred-with-followup | Routed out → #1797 (distinct from WP02's delegate retire) |
| #2595 | extract ScopeSource port | deferred-with-followup | Routed out → #2173 |
| #2600 | extract mission_number bake cluster | deferred-with-followup | Routed out → #2173 |
| #2499 | consolidate compat/registry.py shim registry | deferred-with-followup | Follow-up: #1797 (optional-deferred; live, parity-tested — not a delete) |
| #2625 | golden-count remediation: excluded co-owned-dir sites | deferred-with-followup | Follow-up: #2625 tracks the ~1,200 excluded-dir convert-sites (specify_cli chief) grandfathered into WP11's baseline |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

Note: `in-mission` rows flip to `fixed` as their WPs are approved/merged; all must be terminal before mission `done`. Deferred golden-count remainder tracked as follow-up #2625.
