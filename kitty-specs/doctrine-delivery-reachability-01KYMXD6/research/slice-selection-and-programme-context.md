---
title: "Why this mission exists — programme adequacy and slice selection"
description: "Routing analysis showing none of PR #3007's seventeen follow-up issues had an owning requirement, and the reasoning that selected this mission's scope over the alternatives."
doc_status: active
updated: '2026-07-28'
related:
- kitty-specs/doctrine-canonical-structure-remediation-01KYEYSD/spec.md
- kitty-specs/doctrine-delivery-reachability-01KYMXD6/spec.md
---
# Programme Adequacy and Slice Selection

**Origin.** Pre-spec discovery for this mission, 2026-07-28. The operator's framing:
*"the projected / planned 5 missions will be woefully inadequate to remediate these."*
This document records the test of that claim and the reasoning that produced this mission's scope.

---

## 1. The programme as planned

`doctrine-canonical-structure-remediation-01KYEYSD` was specced, then split into five child
missions: **A** `doctrine-silence-guards-01KYFV7Q` (landed as PR #3007, merged `ed470756e`,
2026-07-28), **B1** `drg-relation-impacts-vocabulary-01KYFV87`, **B2**
`drg-edge-migration-extractor-retirement-01KYFV8C`, **C** `test-quality-doctrine-series-01KYFV8H`,
**D** `foundational-values-creed-band-01KYFV8N`. Mandatory order A -> B1 -> B2 -> C; D gates on A.

State at discovery time: **only A is specced.** B1/B2/C/D are 3.9-15 KB sketch stubs carrying a
`NOT YET SPECCED - deliberately` banner, no `plan.md`, zero WPs. That is per operator guidance
("do not over-specify or plan any mission after phase A") and is not itself a defect — but it means
nothing after A had been requirement-tested against the tree.

## 2. The routing result

Every issue number PR #3007 filed was grepped across all five mission directories and the
programme spec. **All returned `NONE`.**

**17 of 17 issues have no owning requirement.** Counting three as *routable-with-a-spec-amendment*
(#2977 -> B1, #2994 -> B2, #3009-R5 -> pre-B2) still leaves **14 genuinely unhoused**, of which
**8 are P1**.

The reason is structural rather than negligent: there was no requirement set for new findings to
fall into, because four of five missions had none yet.

### The part that is not merely additive

Two unhoused items sit **inside** the mandated chain:

- **#3036 and #3037 block mission C's own requirements.** C authors 4 assets (FR-009) and SC-004
  demands every resolved-only node carry an inbound edge — while #3037 says the `asset` kind has no
  consumer resolution path at all. C would ship the programme's own defect class.
- **#2977 blocks B1.** B1's entire deliverable is two new `DRGEdge` fields, and two write paths
  still drop unknown fields (see [drg-writer-and-reachability-inventory.md](./drg-writer-and-reachability-inventory.md)).

So the five-mission plan would not merely have run short at the end — it would have driven B2 and
C into walls that were not on the map when it was drawn.

### Wider sweep

112 open issues carry the `doctrine` label; the programme houses 6. Narrowed to the fair
comparison — P0/P1, milestone `3.2.x`, non-epic — it is **6 of 26**.

A coherent cluster emerged that no mission had named: #2467 (KEYSTONE), #2763, #3022, #3023,
#3024, #3037, #3038, #2862, #3036 — **9 issues, 4 of them P1, all answering one question: where
can doctrine live and how does a consumer get it.**

## 3. Why this scope, over the alternatives

Three candidate slices were scoped in parallel. All three were independently landable; the
selection was made on thesis coherence plus ordering pressure.

| candidate | files | ordering pressure | blocked by |
|---|---|---|---|
| Kind-vocabulary consolidation + derived serializer | ~21 | **must precede B1** | nothing |
| Asset resolution + install path | ~13-18 | none, but unblocks C | nothing |
| Activation reachability (R1) | ~5 files, 150-250 lines | precedes B2 | nothing (R2 deferred) |

**The selected mission takes the delivery-layer core of all three** because they share a single
thesis rather than merely a domain:

> Mission A closed *declared-but-inert* at the **validation** layer — declarations that loaded and
> validated while doing nothing. These are the same defect at the **delivery** layer: a declaration
> that passes every check and still reaches nobody.
>
> - **Assets** ship in the wheel, validate, and cannot be addressed by any consumer.
> - **Activation** compiles into `charter.yaml` and reaches agents only on a once-per-project
>   render that `spec-kitty next` burns with an empty payload.
> - **Edge fields** are declared on the model and silently dropped by the writers that serialize
>   them.

Deliberately **excluded**: the full 8-site kind-vocabulary consolidation (#2981 proper), the
ratchet widening (#2986), the `operating-procedures` triage (#2994), the destination-tier
adjudication (#3023) and pack extraction (#3022), the gate contradiction (#3036), and R2's
vocabulary collapse. Each has a tracked home and none is a prerequisite of this mission.

### The sequencing risk, and how it is handled

#2977 is the only piece with a hard deadline — B1 cannot start clean without it. The activation
work is the opposite: it carries the largest blast radius in the set, because it changes what every
agent receives at every action boundary in every consumer project.

**Mitigation, agreed at discovery:** the writer fix is WP01 with no dependencies, so it can land
and unblock B1 even if the activation work takes review rounds. Same mission, decoupled lane.

## 4. Operator rulings taken during discovery (2026-07-28)

1. **The 91 action-unreachable activated artefacts** — add the `procedure_ids` field and author
   edges for the **obvious** artefacts. The non-obvious remainder goes to an **after-mission
   operator interview** rather than being guessed at in-mission.
2. **The activation store** — `charter.yaml` / `charter.yml` is the authority; `.kittify/config`
   holds Spec Kitty's own repository config and metadata and **points at the charter file via a
   `charter_file:` field**. This reverses the prior R2 recommendation, which named the dead store.
3. **Change mode** — ordinary schema change with a consumer migration, **not** a bulk edit.
4. **Landing** — this branch is the reconciliation target; lane work consolidates into it, then a
   PR is raised to `upstream/main`.

## 5. Recommended re-cut of the programme

Recorded as input for whoever specs the remainder; **not** a deliverable of this mission.

The five keep their shape — none should be merged into another — but three are missing:

| | Mission | Delivers |
|---|---|---|
| **A** | `doctrine-silence-guards` *(landed)* | validation-layer silence guards |
| **A2** | silence-guard residuals + gate hygiene | #2981, #2986, #3026, #3039, #2979 |
| **E** | **this mission** — delivery reachability | #3037, #2977, #3038 (partial), #3009 residual, activation |
| **B1** | `drg-relation-impacts-vocabulary` | `Relation.IMPACTS`, `is_symmetric` — **gated on this mission's WP01** |
| **F** | doctrine tiering + distribution | #3023, #3022, #3024, #2763, #2862, #3036; advances #2467 |
| **B2** | `drg-edge-migration-extractor-retirement` | 774 -> authored edges; **gated on the reachability metric** |
| **C** | `test-quality-doctrine-series` | **gated on F for #3037/#3036** |
| **D** | `foundational-values-creed-band` | gates on A only; fully independent |

Even at eight, this covers roughly 15 of the 26 P0/P1/3.2.x doctrine issues. A separate
charter-lifecycle cluster (#3045, #2831, #2940, #2521/#2522/#2520, #2399, #2304) remains unaddressed
— **#3045 in particular is this programme's own thesis one layer up: charter sync always reports
success, `--force` is a no-op, and a test pins the wrong behaviour.**

## 6. Provenance note

PR #3007's body carries a *"Landing-order constraint — this PR gates on #3003"* section that was
already false when the PR merged (#3003 merged 15:22Z; the PR tip post-dated it; `cutover-guard`
was SUCCESS; rollup 48 SUCCESS / 31 SKIPPED / 0 FAILURE). Recorded here because a reader following
that section into this mission's premises would inherit a stale blocker.
