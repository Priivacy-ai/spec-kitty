# Issue matrix — event-sync-retention-delivery-01KVYWRG

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2130 | Event sync retention/delivery design synthesis (PR) — folded into spec | in-mission | spec.md L6 (design folded in); implemented across mission WPs |
| #2146 | Target authority prerequisite — single resolved sync target | in-mission | WP01 lane-a `src/specify_cli/sync/target_authority.py` (resolver foundation; full wiring WP02+) |
| #2144 | Capture-before-drain invariant — no event loss on drain | in-mission | spec.md L8 (C-?); delivered by WP03 capture-first durability |
| #2165 | Docs reorganization context — acknowledged, out of mission scope | deferred-with-followup | spec.md L8 (acknowledged docs-reorg context, does not move this mission's artifacts). Follow-up: #2165 stays open for a separate docs-reorg effort |
| #2131 | Multi-target fan-out — declined for MVP (single active target) | deferred-with-followup | spec.md L128 C-003 (fan-out declined; ledger schema kept extensible). Follow-up: #2131 deferred post-MVP — re-open for many-targets ledger extension |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
