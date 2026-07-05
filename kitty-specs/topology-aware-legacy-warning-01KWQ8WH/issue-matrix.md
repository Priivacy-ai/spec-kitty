# Issue matrix — topology-aware-legacy-warning-01KWQ8WH

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2351 | Once-per-mission legacy-topology warning over-fires on intentional coordination-less (single_branch/lanes) missions | fixed | commit e46347bd4 — topology-aware `_warrants_legacy_warning` classifier gates only the emit; 20 tests green |
| #2218 | MissionTopology-SSOT: single_branch/lanes never write coordination_branch (referenced in spec.md as pre-existing context this mission depends on, not modifies) | verified-already-fixed | `test_legacy_routing_and_write_contract_unaffected_by_topology` + `docs/adr/3.x/2026-06-22-1-mission-topology-ssot.md` |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
