# Issue matrix — doctrine-catfooding-2196-01KWE16N

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2196 | Doctrine Catfooding epic (functional parent) | in-mission | WP01 73905750c re-parented (scope-tracker framing removed); epic closes on mission land |
| #2095 | §3 Mission tracer-files experiment | in-mission | Folded into FR-007 (§3 tracer conversion WP); closes on mission land |
| #2282 | Canonical docs freshener (`inventory_lockfile.py`) | verified-already-fixed | WP01 registered the source doc via the freshener; `check_docs_freshness.py --ci` exit=0 |
| #2277 | Page-inventory tail-append coordination | in-mission | Inventory regenerated via canonical freshener in WP01 (no hand-merge); terminal on mission land |
| #2159 | Shrink-only architectural-gate ratchet | in-mission | Cited as exemplar for FR-009 (§5a arch-gate WP); terminal on mission land |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
