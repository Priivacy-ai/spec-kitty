# Issue matrix — spec-kitty-home-isolation-01KW1JXX

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2171 | make `SPEC_KITTY_HOME` isolate runtime state | in-mission | WP01 keystone commit 5e4531afc (get_runtime_root honors SPEC_KITTY_HOME on all platforms); consumer wiring in WP02–WP06 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
