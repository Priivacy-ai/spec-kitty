# Issue matrix — mission-step-creatability-01KXQA6R

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2724 | S-C mission-step-creatability (this mission's tracking issue) | fixed | All 7 WPs approved: Concern A cutover (WP01), 3-type authoring (WP02/03/04), guards+reconciliation (WP05), graph-back (WP06), resolve-by-URN (WP07). The full S-C slice is delivered. |
| #2721 | Step-model sub-epic (Prio-0 slice) | deferred-with-followup | Parent sub-epic; S-C is the Prio-0 slice and is complete, but the epic continues via follow-ups #2751 (action_sequence symmetry), #2725 (S-D), #2726 (S-E). Not closed by this slice. |
| #2652 | Step-model epic (parent) | deferred-with-followup | Parent epic (#2721 is a sub-epic of it); advanced by this mission but not closed — remains open for its other slices. |
| #2689 | Three of four built-in types uncreatable regression | fixed | documentation/research/plan are creatable again (WP02/03/04 authored per-type template refs+content; project_template_set non-null for all 4 types; red-first creation proofs green). SC-001 pass. |
| #883 | mission_type→template edge class / non-software mission-type support | fixed | Non-software mission types are creatable + the mission_type→step→template chain is graph-backed via instantiates edges (WP06, N=8→288/765/10). SC-004 pass. |
| #2712 | Prior step-authority slice (template exemplars) | verified-already-fixed | #2712 (DRG template nodes + mission_type→action edges) was already MERGED; this mission builds on it (WP06 extends the graph, leaving the 16 bare exemplars untouched) — no re-fix needed. |
| #2751 | `action_sequence` symmetry cutover | deferred-with-followup | Follow-up: #2751 (spec.md:118,146,152 — explicitly OUT OF SCOPE per C-007, spawned as a follow-up blocked-by this mission; WP01 leaves the `action_sequence` overlay untouched) |
| #2725 | S-D substeps | deferred-with-followup | Follow-up: #2725 (spec.md:148 — out of this mission's scope, S-D) |
| #2726 | S-E guards | deferred-with-followup | Follow-up: #2726 (spec.md:148 — out of this mission's scope, S-E) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
