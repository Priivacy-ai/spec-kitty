# Issue matrix — mission-type-drg-edges-01KXKY2N

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2677 | Wire mission_type DRG nodes: root elements → steps (action edges) | fixed | **Phase 1** (spec.md: FR-001..006, SC-001..004; plan IC-1/IC-2). `mission_type→action` `requires` edges from `action_sequence`; 18→10 orphans against the monolith, ceiling unchanged. Ships first, clears the red gate. |
| #2680 | Shard the generated DRG graph into per-kind `*.graph.yaml` fragments | fixed | **Phase 2** (spec.md: FR-007..S10, SC-S1..S3, C-S1..S5; plan IC-3). Behavior-preserving migration of the edge-complete graph — ~22-site reader migration via a canonical seam, atomic monolith retire, partition-totality + equality + silent-degrade proofs. Resequenced AFTER the edges (post-plan squad; DD-0). Must reach a terminal verdict before mission `done`. |
| #2652 | EPIC: specify_cli/missions retirement / mission-type unification | deferred-with-followup | Parent epic (spec.md). This mission is the S0 edge-completion + sharding-enabler slice; #2657/#2659/#2658/#2660/#2661 remain open under the epic. Follow-up: #2652. |
| #2651 | mission_type/action as first-class DRG nodes (nodes-only) | verified-already-fixed | Merged; this mission wires the edges those nodes deferred (`models.py:46`). Not reopened. |
| #883 | MissionType doctrine authority | verified-already-fixed | Design-authority reference only (`883-mission-type-authority-brief.md`, ADR `2026-07-15-1`). Merged via PR #2654; this mission grounds its `requires` edge semantics in the brief (C-006). Not a fix-target of this mission. |
| #1923 | DRG residual orphan curation (14 valid orphans) | deferred-with-followup | Shares `drg-orphan-residual.md` + the `DOCUMENTED_ORPHAN_RESIDUAL=14` constant. This mission wires its 8 orphans (residual→10); #1923 curates the other 10. Coordinate on the shared doc only (C-003). Follow-up: #1923. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
