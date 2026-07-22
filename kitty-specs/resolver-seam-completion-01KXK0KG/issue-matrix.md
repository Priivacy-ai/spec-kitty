# Issue matrix — resolver-seam-completion-01KXK0KG

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2651 | Resolver-seam completion (action-grain union) | fixed | Delivered by all 5 approved WPs: mission_type DRG node (8b038d01d), action_grain union module (13929e231), lazy resolver seam retiring _EMPTY_GRAIN (ba593907), doctrine-integrity gate + non-vacuity twin (f9f412b84), second-source reconciliation + NFR-001 spy (666118774). Re-scoped to S0 DRG-node + integrity gate per ADR #2655. |
| #883 | Mission-type doctrine authority | verified-already-fixed | Merged upstream/main via PR #2654; ADR #2655. This mission builds on the #883 seam. |
| #2659 | Activation-driven enumeration (#2652-E) | deferred-with-followup | Out of scope (spec §Out of Scope — S3/consume-path); this mission is a precursor that de-risks it. Tracked under epic #2652. |
| #2658 | Templates-as-config (#2652-T) | deferred-with-followup | Out of scope (spec §Coverage/Out of Scope). This mission's DRG node + lazy seam unblock it; tracked under #2652. |
| #2656 | Mission-instance governance addendum | deferred-with-followup | Out of scope (spec §Out of Scope). Builds on this mission's reworked `ResolvedGovernance.from_grains`; `blocked_by` #2651. |
| #2657 | Provisioned default charter | deferred-with-followup | Out of scope (spec §Out of Scope). Independent sibling under #461; touches the same `existing_mission_types` fallback IC-10 trims (distinct concern). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
