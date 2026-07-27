# Issue matrix — coord-primary-partition-lock-01KWZ46V

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1878 | Coord/primary write-side strangler (placement-routing slice) | in-mission | Delivered by WP01–WP08 (placement seam + routers); WP09 docs move whole strangler to 3.2.x/G2 — terminal verdict owed before mission `done` |
| #1716 | Make coordination topology coherent from mission create through planning | in-mission | Stale "Locked Architecture Decision" superseded; WP09 updated issue body (verified via gh); coherence code lands across WP01–WP08 — terminal before `done` |
| #2091 | Empty-`mid8` guard at CoordinationWorkspace composition seam (FR-007) | in-mission | Guard implemented under WP06 (`coordination/workspace.py`); terminal verdict owed before `done` |
| #2250 | never-created vs DELETED/UNMATERIALIZED coordination-surface states (FR-008) | in-mission | Regression-lock under WP06; terminal verdict owed before `done` |
| #2160 | Sibling cluster on the shared placement seam (authoritative here) | in-mission | Addressed via the shared placement seam (WP01) + routers; terminal verdict owed before `done` |
| #1619 | Runtime/state decomposition (parent epic) | deferred-with-followup | Umbrella epic; this mission is one child slice under #1619 and does not close it — continues beyond this mission |
| #2106 | Planning-stays-on-primary partition (shipped PR, ratified here) | verified-already-fixed | Already merged; spec §L41 + #1716 body cite it as the ratifying prior work this mission ratifies (C-004) |
| #2113 | Planning-stays-on-primary partition (shipped PR, ratified here) | verified-already-fixed | Already merged; spec §L41 + #1716 body cite it as the ratifying prior work this mission ratifies (C-004) |
| #2429 | Extends `resolve_planning_read_dir` (external session PR) | deferred-with-followup | External PR; soft pre-req gating FR-009 timing only (C-007 "verify, do not hold"). Follow-up: #2429 tracked outside this mission |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
