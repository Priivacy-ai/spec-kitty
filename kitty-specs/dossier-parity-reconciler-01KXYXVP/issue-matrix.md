# Issue matrix — dossier-parity-reconciler-01KXYXVP

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2262 | sync import-history (consumer of this parity foundation) | deferred-with-followup | Consumes the reconciler + canonical hash; separate mission. Follow-up: #2262 |
| #1091 | TeamSpace launch gate epic (parent) | deferred-with-followup | This mission is a launch-gate dependency, not a fix to the epic. Follow-up: #1091 |
| #2684 | Evict WP runtime state into the event log (conforms to this hash input) | deferred-with-followup | Stijn-owned; the WPMetadata static projection here is the input it conforms to. Follow-up: #2684 |
| #2686 | WP static-projection hash input (aligned direction) | deferred-with-followup | Stijn-owned; this mission adopts the normalized-projection input it defines. Follow-up: #2686 |
| #511 | TeamSpace replay/time-travel projection (read side) | deferred-with-followup | Consumes the canonical hash for server-side parity; separate SaaS ticket. Follow-up: #511 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`.

Note: the mission's own tracker is #2180 (build the reconciler + unify the CLI↔server snapshot hash). The server-side alignment (spec-kitty-saas `_compute_snapshot_hash`) lands as a companion PR per constraint C-003.
