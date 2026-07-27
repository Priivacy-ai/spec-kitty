# Issue matrix — drg-relation-parity-activation-gate-01KY48PD

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2843 | DRG completeness (#2833 residue): relation-description parity + activation-gate consolidation | in-mission | This mission's target (re-scoped to items 2+3). WP01–WP03 deliver FR-001–004/NFR-001–002 (activation-gate live-bug fix + workaround consolidation); WP04–WP05 deliver FR-005–008/NFR-003 (relation-description parity). Terminal `fixed` at mission `done`. |
| #2847 | Anti-pattern corpus promotion (item 1) | deferred-with-followup | Operator-split out of #2843 into its own mission (research.md "Operator decision — SPLIT": ~22× the size, needs a human curation pass, zero build-dependency). Explicitly out of scope here (C-005). Follow-up: #2847. |
| #2466 | Doctrine extensibility & pack ecosystem (parent epic) | deferred-with-followup | Umbrella epic; this mission is one child and does not close it. Remains open for its other children. Follow-up: #2466. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
