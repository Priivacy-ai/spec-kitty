# Issue matrix — spec-kitty-home-isolation-01KW1JXX

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2171 | make `SPEC_KITTY_HOME` isolate runtime state | fixed | All global state routed through `get_runtime_root().base` (env-aware): keystone WP01 (5e4531afc), sync config/queue/daemon/clock WP02 (429b17ae7, fec2bf14e), auth store/lock + Windows normalization WP03 (054ab0e77), tracker creds/DB WP04 (e0577bfff), state doctor/contract WP05 (3ef4ce1a5), architectural guard + CLI isolation test + SKILL.md/CHANGELOG WP06 (d01751a20). All 6 WPs approved; guard prevents re-scatter. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
