# Issue matrix — read-surface-ssot-closeout-01KWZV91

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1716 | Coordination topology coherence from create through planning (epic) | fixed | Epic closed (SC-004); open children enumerated = exactly {#2088, #2100} (GitHub subIssues: 22 total, 20 closed, 2 open), both terminal |
| #1878 | Write-side placement strangler (parent epic) | deferred-with-followup | Parent epic; this read-side mission advances it, does not close it |
| #2088 | Ownership-overlap validator dependency/lane-blind | verified-already-fixed | 69dd1fa46 (ancestor of base) + regression lock `test_1716_closeout_regression.py` (WP17) |
| #2100 | Inline meta.json reads not routed to load_meta | fixed | Thread B: WP05/06/07 collision B-edits + WP12/13/14/15 routing + non-vacuous ratchet WP16 |
| #2453 | resolve_feature_dir_for_mission kind-blind read sweep | fixed | Thread A: WP04–09 routing + coord_authority drain WP11 (floor 4, FR-003-corrected) |
| #2404 | accept reads acceptance-matrix.json from stale -coord | fixed | Thread C: seam WP01 + accept routing WP02 + coord-topology characterization WP03 (SC-003) |
| #2160 | implement/review-loop coord authority (parent epic) | deferred-with-followup | Parent epic; this mission is under it, does not close it |
| #1619 | Runtime/state overhaul (root epic) | deferred-with-followup | Root epic; this mission is under it, does not close it |
| #2462 | Coord/primary placement-partition lock (write-side) | verified-already-fixed | Merged to upstream/main 38257f737 (2026-07-08); consumed as the seam base |
| #2091 | Empty-mid8 malformed coordination branch | verified-already-fixed | Closed by #2462 (empty-mid8 composition guard) |

**Follow-ups filed by this mission:** #2477/#2478/#2479 (`m_0_13_*` migration meta-read deferrals), #2480 (charter-layer meta reads — layer rule blocks routing), #2482 (stray-primary-matrix residue-GC gap, orthogonal to #2404), #2485 (dashboard Tasks/Implement perf). **Pre-existing follow-up noted:** `feature_write_dir` uses the forbidden `feature*` term — rename ticket.

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
