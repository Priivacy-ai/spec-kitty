# Issue Matrix — Step authority (S-B)

Canonical verdicts (issue-matrix allow-list): `fixed` · `verified-already-fixed` ·
`deferred-with-followup` (evidence_ref must carry a `#NNN` follow-up handle) ·
`in-mission` (closed by a later WP in THIS mission; must reach a terminal verdict before the `done` gate).

Rows below mirror every issue referenced in `spec.md`. Only **#2723** is a fix target of
this S-B mission. The epic parent / sub-epic / downstream / deferred sibling slices are carried
for traceability as `deferred-with-followup` with their tracking handle; the already-shipped base
PR is `verified-already-fixed`.

| issue | title | scope | verdict | evidence_ref |
|-------|-------|-------|---------|--------------|
| [#2723](https://github.com/Priivacy-ai/spec-kitty/issues/2723) | S-B step authority: step.yaml authoritative, project action_sequence/template_set | Fix target — this mission IS S-B | `in-mission` | Closed by this mission (final WP / on merge); resolve to `fixed` at the terminal (done) gate. |
| [#2652](https://github.com/Priivacy-ai/spec-kitty/issues/2652) | EPIC root: mission-type step-model unification | Parent epic — stays OPEN | `deferred-with-followup` | S-B is one Prio-0 child (spec.md L6); epic tracks remaining slices. Follow-up: #2721. |
| [#2721](https://github.com/Priivacy-ai/spec-kitty/issues/2721) | Sub-epic: step-model unification | Parent sub-epic — stays OPEN | `deferred-with-followup` | Tracks the S-B/S-C/S-D/S-E slice family; not closed by S-B alone. Follow-up: #2652. |
| [#883](https://github.com/Priivacy-ai/spec-kitty/issues/883) | template_set graph-backing / uncreatable exemplar | Closed by S-C, not S-B | `deferred-with-followup` | S-B provides the `template` reference SLOT only; content + `instantiates` edges land in S-C (spec.md C-004). Follow-up: #2724. |
| [#2724](https://github.com/Priivacy-ai/spec-kitty/issues/2724) | S-C exemplars + graph-back template_set | Downstream slice (blocked_by S-B) | `deferred-with-followup` | S-C authors exemplar CONTENT + `instantiates` edges after S-B lands the slot (spec.md C-004). Follow-up: #2721. |
| [#2725](https://github.com/Priivacy-ai/spec-kitty/issues/2725) | S-D substeps | Deferred sibling slice | `deferred-with-followup` | Out of scope for S-B; explicitly deferred (spec.md C-005). Follow-up: #2721. |
| [#2726](https://github.com/Priivacy-ai/spec-kitty/issues/2726) | S-E guards | Deferred sibling slice | `deferred-with-followup` | Out of scope for S-B; explicitly deferred (spec.md C-005). Follow-up: #2721. |
| [#2712](https://github.com/Priivacy-ai/spec-kitty/pull/2712) | mission_type→action edges + sharding | Shipped base (merged) | `verified-already-fixed` | Already merged; S-B re-sources these DRG edges from the step authority. Baseline 280/757/10. |
| [#2689](https://github.com/Priivacy-ai/spec-kitty/pull/2689) | template_set slot / uncreatable regression | Closed by S-C, not S-B | `deferred-with-followup` | Slot mechanism stays; the uncreatable regression is closed by S-C content work, not S-B (spec.md C-004). Follow-up: #2724. |

## Verdict rules honored

- Only **#2723** is a fix target of S-B (`in-mission` → `fixed` at the done gate).
- Epic **#2652** / sub-epic **#2721** and deferred/downstream slices **#883**, **#2724**,
  **#2725** (S-D), **#2726** (S-E), **#2689** are recorded `deferred-with-followup` with an explicit
  `#NNN` handle — none are closed by this mission, all stay OPEN by design.
- Shipped base PR **#2712** is `verified-already-fixed` (already merged; S-B builds on it).
- No `unknown`/empty verdicts; every row carries a canonical allow-list verdict.
