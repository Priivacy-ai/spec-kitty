---
title: Creed and FoundationalValues — hardened design
description: "Hardened design after a four-lens squad: the structure is sound and needs no new kind, relation, or node; the numeric layer must be gated behind a one-day experiment because the sign channel is measurably noisy and creed-weighted ranking collapses toward magnitude."
doc_status: draft
updated: '2026-07-26'
related:
- docs/plans/doctrine/creed-and-values-design-as-proposed.md
- docs/plans/doctrine/manifesto-tier-verdict-and-handover.md
- docs/plans/doctrine/index.md
---
# Creed and FoundationalValues — hardened design

**Date:** 2026-07-26 · **Status:** hardened design, **no decision taken**
**Input:** [`creed-and-values-design-as-proposed.md`](creed-and-values-design-as-proposed.md)
**Method:** four profile-loaded lenses, read-only — architect (seams/types),
doctrine-curator (integrity/exemptions/accreditation), reviewer (adversarial),
implementer (feasibility/prototype).

---

## Headline

**The structure is sound. The arithmetic is not yet earned.**

The design needs **no new `ArtifactKind`, no new `NodeKind`, and no new `Relation`** — so it
touches none of this repo's fail-closed enum drift-guards and none of the three silent
kind-drop sites. That is the single most important structural finding, and it is what
separates this design from its rejected predecessor.

Against that, two measurements move the centre of gravity:

- **There is one live cost axis, not seven.** Negative-cell census over the 36 authored
  vectors: `minimal` 19, `maintainable` 3, `agile` 2, `reachable` 2, `extensible` 1,
  `environmental` **0**, `solvable` **0**. Total 27 of 252 cells (10.7%), and `minimal`
  alone carries **19 of 27 (70%)**.
- **Creed-weighted ranking collapses toward magnitude ranking.** Measured (34 authored
  vectors, Dirichlet creeds, Spearman vs the *unweighted row mean*, top-5 overlap vs the
  flat-creed top-5):

  | Creed concentration | Spearman r | Same top-5 |
  |---|---|---|
  | near-flat (α=50) | **0.980** | **97%** |
  | mild tilt (α=20) | 0.958 | 90% |
  | moderate (α=8) | 0.913 | 81% |
  | opinionated (α=3) | 0.825 | 67% |
  | uniform (α=1) | 0.671 | 48% |

  The flat-creed top-5 is exactly the five largest row-sums. `external-memory` (largest
  sum, +3.50) appears in the top-5 for **53% of all creeds**.

**Recommendation: ship the prose layer; gate the numeric layer behind a one-day experiment
(§7) whose failure condition is pre-registered.** Everything else in this document is the
shape to build if that gate passes.

---

## 1. Corrections to the input design's own evidence

Found by independent re-measurement. Two of these are corrections to §5 of the input doc.

1. **Co-location is a convention, not an invariant.** The input doc claims every number is
   paired 1:1 with a rationale. Falsified: `the_point_of_dissent.md` carries 7 deltas and
   **zero** `rationale` keys; `quad_A_test_structure.md` the same; `TEMPLATE_PRACTICE.md`
   has 7 empty-string rationales. ≥3 of 38 violate it. So a mandatory `rationale` is a
   **new** constraint the calibration corpus fails — it needs the same advisory-vs-hard
   decision the negative rule needs.
2. **The 39% figure is contaminated.** Two of the 14 all-non-negative vectors are not
   authored artefacts: `TEMPLATE_PRACTICE` (the authoring template) and
   `quad_A_test_structure` (an unfilled stub) — both all-zero. Honest figure: **12 of 34
   (35%)**. Both stubs also sit inside the n=36 PCA and the per-axis means.
3. **§5.3 survives the correction.** PCA re-run at n=34 with stubs excluded: cumulative
   0.339 / 0.561 / 0.712 / **0.816** / 0.900 — still **5 components for 80%**, per-axis
   signs unchanged. The dimensionality claim is solid and independently replicated. Republish
   §5.2–§5.6 at n=34 anyway; it costs the argument nothing and removes an easy shot.
4. **"Two axes carry no cost information" understates it.** Five of seven axes have ≤3
   negative cells. Restate as **one cost axis and six benefit axes**.
5. **Parts 2 and the connascence matrix have zero grounding in §5.** Every measurement in §5
   is about the artefact→value delta field. Nothing in the 36-vector corpus calibrates an
   edge strength or an inter-value coefficient — and 774 DRG edges is **23× the entire
   calibration set**. Split the document so §5's credibility does not travel across the
   section boundary.
6. **"The interview is the producer" answers ~0.5% of the register.** The creed is 7 weights
   + 7 rationales = 14 cells. The design also adds 260 behavioural artefacts × 7 × (delta +
   rationale) = **1,820 cells**, plus **774** edge values, plus a 7×7 matrix ≈ **2,650
   cells** total.
7. **The design retires nothing.** `in_tension_with` is still 2 edges and is the subject of
   an Accepted ADR this design does not propose superseding. Net: **+5 registers, −0.**

---

## 2. The 39% question — settled, and the answer is a third option

The input doc says this cannot be resolved from the data. It can. Twelve of the fourteen
files were read in full.

**Eleven of twelve name an explicit cost in prose while the number sits at or above zero:**

| Practice | Axis | delta | Rationale (verbatim excerpt) |
|---|---|---|---|
| `manual_of_me` | minimal | **+0.25** | "introduces documentation and cognitive overhead… it is **decidedly not minimal**" |
| `fail_fast` | maintainable | **+0.50** | "overhead of maintaining complex validation rules… **potential long-term maintenance challenges**" |
| `wipe_the_board` | maintainable | **0** | "the daily upkeep burden **limits long-term sustainability**" |
| `external-memory` | minimal | **+0.75** | "there is a **risk of over-complicating** the external memory system" |
| `LARS` | minimal | **0** | "**may introduce complexity** in managing emotional aspects" |
| `define_test_boundaries` | minimal | **+0.20** | "moderated slightly by the **complexity introduced**" |

Compare against controls, where the same author *does* net correctly:
`AMMERSE_impact_analysis` minimal **−0.60** ("introduces significant complexity and effort,
conflicting with minimalism"), `avoid_gold_plating` extensible **−0.70**,
`be_a_STARR_at_interviews` minimal **−0.65**.

> `manual_of_me` scores minimal **+0.25** for "decidedly not minimal".
> `AMMERSE_impact_analysis` scores minimal **−0.60** for the same claim.
> **0.85 apart, opposite signs, near-identical prose.**

**Verdict:** the 35% is not a measurement of authorial honesty — it is a measurement of
**noise in the sign channel**, the one field a mandatory-negative rule reads. Eleven of
twelve authors did the honest analysis; the number failed to record it. Exactly **one**
entry is a true slogan (`the_point_of_dissent`: bare numbers, no rationales) — and a
sign-reading rule would **pass** it while rejecting the eleven careful ones.

This also replicates the earlier squad's *other* measurement, which §5.3 did not test: sign
instability under equivalent input. It held for an LLM across two passes; it holds for a
human across a corpus.

**Consequences, and they are the design's most important:**

1. **`minItems: 1` negative must not ship as a schema constraint.** Not because the corpus
   is slogan-shaped (3%), but because it gates on the least reliable field and inverts the
   outcome it wants.
2. **The constraint belongs on the prose:** every rationale must name what adopting this
   makes worse. Eleven of twelve already comply.
3. **The highest-value new component is a sign-vs-rationale-polarity lint** — flag any cell
   whose rationale names only a cost while `delta ≥ 0`. It is mechanically checkable by an
   LLM on prose the design already mandates, and it is **the only component of this design
   with a validation set available today** (the twelve rows above). Make it Part 0.
4. **The rationale is the surviving channel.** In `fail_fast` and `wipe_the_board` the prose
   is right and the number is wrong. This is strong evidence *for* the design's own
   counterpoint that the rationale fields are pivotal — and against the numeric layer.

---

## 3. Hardened structure — decisions

### 3.1 `FoundationalValues` — not an enum

The "half-open enum" dissolves. `Role` in `src/doctrine/agent_profiles/profile.py` is already
a **proven, lint-clean, Pydantic-wired half-open value object** in this codebase — copy it
rather than invent a pattern. Openness then lives in a **substitutable artefact** resolved
through the existing built-in → org → project layering (`src/doctrine/base.py`), and the
validation target becomes *the active value set* rather than a module literal.

⚠️ **BLOCKER — do not expose the value-set repository as a `DoctrineService` property.**
`tests/architectural/test_artifact_selection_completeness.py:55-62` introspects **every**
`@property` on `DoctrineService` and demands a matching `selected_<kind>` on
`DoctrineSelectionConfig` *and* `required_<kind>` on `OrgCharterPolicy`. A property silently
converts a 2-file change into a three-way lockstep across two packages. Use a named accessor:
`resolve_active_value_set()`.

### 3.2 Two fields, two types — `value_impact` vs `value_bias`

The input design uses one concept for two semantics, distinguished only by which artefact
carries it. Split it:

| | `value_impact` | `value_bias` |
|---|---|---|
| Semantics | Δ from *not adopting* | weight — "how much I care" |
| Arithmetic | **summable / composable** | **not summable** (renormalise or average) |
| Position in `creed · deltas` | right-hand side | left-hand side |
| Carried by | directive, tactic, styleguide, procedure | agent_profile, paradigm, **and the creed** |

Make them **distinct Pydantic model types**, not one model with a `mode` discriminator, so the
type system structurally prevents dotting a profile with a directive (DIRECTIVE_043).

**The creed's field is `value_bias` too** — the creed *is* the project's profile. And
`paradigm` belongs on the bias side: a worldview *is* a stance, not a Δ-from-baseline.

### 3.3 The value-bearing kind set — positive, declared once, in code

```
_VALUE_IMPACT_KINDS = {directive, tactic, styleguide, procedure}
_VALUE_BIAS_KINDS   = {agent_profile, paradigm}   # + the charter creed
```

**OUT, with reasons:** `toolguide` (consulted, not adopted — no Δ-from-not-adopting; zero of
36 corpus entries is tool documentation); `mission_step_contract` (structural wiring; a vector
double-counts the directives its action resolves); `glossary_pack` (terminology has no
adoption delta; also has **no JSON schema file at all**); `template`, `asset`, `anti_pattern`
(align with `_NON_AUGMENTATION_ELIGIBLE_KINDS`).

Two points that matter more than the membership:

- **Declare it as a named frozenset in `artifact_kinds.py`, not as a prose sentence.** That
  file's own docstring forbids a second kind enumeration, and there are already ten divergent
  kind lists in this codebase. A prose sentence becomes the eleventh.
- **Positive, not negative.** `_NON_AUGMENTATION_ELIGIBLE_KINDS` is an exclusion set, so a new
  kind is silently *included* by default. For value-bearing that default is wrong — a new kind
  would silently acquire a scoring obligation nobody authored.

**`anti_pattern` is structurally incapable** of carrying this, three ways: its nodes hold only
`urn`/`kind`/`label`/`tags` so there is nowhere for the mandatory rationale; `DRGNode` has no
`model_config`; and `extractor._KIND_MAP` lacks it entirely. Negative-only *is* its natural
form — which is exactly why it must be **derived** as the sign-flip of whatever `rejects` it,
never authored.

### 3.4 `impacts` — a field on edges, and `in_tension_with` survives

**Adopt: an optional numeric annotation on `DRGEdge`, sibling to the existing `when` and
`reason`.** Reject a new `Relation.IMPACTS` member — it is semantically wrong (an `impacts`
edge with no relation type says two nodes interact without saying how) and it fires the
`RELATION_DESCRIPTIONS` totality gate plus verbatim doc parity.

**The load-bearing sub-decision:** `impacts` does **not** make `in_tension_with` one band of a
continuum, and must not be allowed to. `in_tension_with` is a *typed existence claim with a
lifecycle* — symmetric, canonically stored, consumed as set membership by
`_tension_candidate_pairs` and both-sides bridging by `_tension_reconciled_urns`. A band makes
pair membership a function of a tunable threshold, and the earlier verdict measured that **no
threshold separates genuine tensions (4–6) from unrelated pairs (2–4)** — they overlap at 4.

> `{relation: in_tension_with, impacts: "-0.7"}` reads *"this authored tension is severe."*
> `impacts` is a strength annotation **on** an authored, typed edge — never a membership
> criterion.

`scan_unreconciled_tensions` is untouched. **ADR `2026-07-21-1` is untouched — no superseding
ADR needed.** Allow `impacts` on any relation; document it as meaningful on
`in_tension_with` / `rejects` / `refines` and ignored elsewhere. No per-relation table, because
there is no totality guard for a `Relation`-keyed table and a table with no guard rots.

If the intent really is to *retire* `in_tension_with`, that is a different, larger change and
it does need a superseding ADR. **Say which reading is meant.**

### 3.5 `delta` — string on the wire, `Decimal` in memory

Neither plain string nor float. `condecimal(ge=-1, le=1)` plus a `mode="before"` validator that
**rejects a non-`str` raw input** — because `Decimal(float)` is lossy, so an unquoted
`delta: 0.9` (which ruamel yields as `float`) must be a hard error, not a silent conversion.
This round-trips the corpus byte-identically, permits exact arithmetic for the composition
formula, and needs no comparison epsilon.

**Do not enforce a 0.05 resolution** — `wipe_the_board` authors `0.125`, so that rule also
rejects the calibration set.

### 3.6 The connascence matrix — parked, and the composition invariant is a *type*

**Do not ship the matrix in the first commit.** The first-order matrix is not in this
repository; both existing copies defer to an external URL, and the coefficients are the
trademarked party's uncalibrated judgement. That makes it precisely *a schema slot with no
available producer* — a fourth instance of the pattern this design was written to avoid.
Define the schema and park it.

When it lands: it lives **inside the value-set artefact**, not on the charter — a matrix and a
value list that can drift apart is the Environmental-definition drift repeated at N² scale.
Nested mapping with an `after` validator asserting squareness, key-set equality with `values`,
and zero diagonal.

**The composition invariant, enforced structurally.** Authored doctrine already defines
`base + 0.5×first_order/6` and `overall = base + 0.5×fo + 0.25×so`. So the authored `delta`
**is** `base`, and it is the only persistable term. Guarantee that with a type, not a rule:

> Make the computed projection a **frozen dataclass with no `model_dump()`**, living in a
> module no writer imports, carrying a mandatory `matrix_id` / `matrix_version` stamp.

Every doctrine and charter writer in this repo serialises through `model_dump()`. A projection
that cannot produce one **can never be written back** — by anybody, including a future agent
who has not read this document. That closes the design's worst failure mode (a computed ripple
laundered into an authored assessment, then re-composed against itself) by construction.

### 3.7 `creed` on the charter — and the validation seam is not where you think

⚠️ **`CharterYaml` is `frozen=True, extra="forbid"`, but in production it is only ever
*constructed*.** Every production reader goes through raw ruamel; `model_validate` against the
on-disk document appears **only in tests**. So a `creed:` block on disk would be **silently
unvalidated** — the mirror image of the three silent-drop sites. Add an explicit per-section
`CreedConfig.model_validate(...)` at the sync seam.

⚠️ **`load_creed_config` must be three-state** — `absent` / `partial` / `complete` — and the
`absent` state must surface as a **consistency-check finding**, not a `logger.info`. The
canonical section-loader treats an absent section as "empty config" with an info log, and that
*is* the decay shape that kept `Directive.severity` inert for 162 days behind green tests.

### 3.8 Accreditation

- **Required field on the loadable value-set artefact.** Copy `GlossaryPack.provenance`
  (required, not optional) and `SourceEntry`. Fields: `attribution` (required, non-empty),
  `trademark_notice`, `source{url, accessed_on}`, `authorization_basis`. Everything else
  points here — do not replicate the notice per artefact.
- **`NOTICE` at repo root.** `LICENSE` is MIT and says *"Copyright GitHub, Inc."*; appending a
  trademark line there would misstate who attributes what. **Verify `NOTICE` ships in the
  sdist/wheel** or the accreditation never reaches consumers.
- **Not the schema `$comment`.** Schemas are **generated** from the Pydantic models; a
  hand-added comment is erased on the next regeneration. Use
  `Field(json_schema_extra=...)`.
- **Unify the two drifted definition copies FIRST.** The template copy has lost *"impact on
  nature"* from Environmental. **Accrediting a misquoted definition is worse than not
  accrediting.** Sequence: unify → reference by id → accredit once.
- **Close the AMMERSE tactic's provenance gap in the same change** — it currently carries no
  attribution at all and cites "the AMMERSE practice article" with no URL. It is where
  accreditation is actually *read*.
- **Provenance uses existing machinery.** `import_candidates` already has
  `external_references[].attribution_reason` — literally the field for this obligation — and
  **zero authored instances**, so the 36-vector import is its first real producer. The design
  should claim this. Add `source_ref` + `source_digest` on each imported vector so a hand-edit
  of an imported delta fails loudly. *That is the check that would have caught the "impact on
  nature" loss.*

---

## 4. The interview loop — the sharpest live objection

Part 3 hands question design to the model, and the chain closes on itself:

1. **The seven axes are all virtues.** No operator says solvability is unimportant. With no
   constant-sum budget and no forced choice, independent scoring over seven virtues is a
   textbook acquiescence instrument, and its predictable output is a **near-flat creed**.
2. **Near-flat is exactly the regime where the creed is inert** — r = 0.980, 97% top-5
   identity with ignoring the creed entirely. *The elicitation instrument most likely to be
   produced is the one that makes its own output irrelevant.*
3. **The laundering step is provenance, not generation.** The model picks the questions, the
   answers land in `creed.yaml`, and the same model class then reads it as the operator's
   authority. Nothing records **who supplied each weight**. Downstream, "the operator ranked
   maintainability 0.8" and "the model proposed 0.8 and the operator did not object" are
   byte-identical.
4. **Prior art says format decides the answer** — declared value orderings moved revealed
   priorities by 0.145 with rankings *inverting between elicitation formats*. The one variable
   identified as outcome-determining is the one the design leaves free.

The design's counterpoints do not reach this: the rationale-fields argument defends the
*consumption* side (and is accepted), but this is a *production*-side failure — and it gets
**stronger** with a better model, because a more fluent interview produces a creed the
operator is more likely to endorse and less likely to have originated.

**Fixes, all cheap:** an **authored, versioned question bank** (the model administers, does not
design); **forced-choice or constant-sum** (21 pairwise comparisons, or a 100-point budget
across 7 — both make the flat creed unreachable); **per-weight provenance**
(`source: operator | model-proposed-accepted | default`, and refuse to render the creed as
operator authority when the `operator` count is zero); and **apply the mandatory-negative rule
to the creed itself** — require the operator to name what they are **deprioritising**, with a
rationale. That is the one place the rule has unambiguous teeth.

---

## 5. Prerequisites that must land first

These are not part of the design; the design **breaks silently** without them.

| # | Prerequisite | Why |
|---|---|---|
| 1 | `extra="forbid"` on `DRGNode` and `DRGEdge` | They have **no `model_config`** → Pydantic default `extra="ignore"` → an authored `impacts` is **silently dropped on load**. The `tags` docstring documents this exact hazard verbatim. |
| 2 | `_node_to_dict` / `_edge_to_dict` learn the field | Explicit field-by-field writers — even a correctly modelled `impacts` **vanishes at graph regeneration**. Model + writer + round-trip test in one commit, or do not add the field. |
| 3 | `extra="forbid"` on `AgentProfile` | Has only `populate_by_name=True`. A `value_bias:` key loads and silently vanishes at model level. **The single most likely way this design ships inert.** |
| 4 | Unify the two AMMERSE definition copies | Already drifted once. Do this before authoring a third. |
| 5 | Confirm `generate_schemas --check` is CI-wired | No reference found in `.github/workflows/`. If unwired, model and schema can diverge. |

The dual gate is real: every per-artefact field lands in **both** the Pydantic model
(`extra="forbid"`) and the generated schema (`additionalProperties: false`) — the latter is
enforced only by `test_artifact_compliance`, not at load. ×4 kinds = 8 files minimum.

---

## 6. Sequencing

**Three all-surface sweeps, not two** — the design does not name its own `impacts` edge sweep
as one:

```
#2467 (pack tiers, KEYSTONE)
  → #2591 component-type on all artefacts        ← cheap, reversible, additive marker
    → silent kind-drop closure + prereqs §5
      → THE EXPERIMENT (§7)                       ← DECISION GATE
        → [only if it passes] value_impact / value_bias fields
          → [later, separately] impacts on edges, connascence matrix
```

`#2591` goes first: it is a default-`open` marker with no authoring burden, and the value
field's applicability should be *expressed in terms of* component-type rather than hardcoding
a kind-keyed approximation into schemas. Do **not** batch the two sweeps — one unreviewable
bulk-edit occurrence map, and if the population plan is wrong the correction has to unpick
both.

---

## 7. THE EXPERIMENT — one day, pre-registered, can kill the numeric layer

The proposed prototype (import the corpus, author one creed, implement ranking, eyeball
whether top-N differs) is right in scope and **wrong in its success signal: "the top-N
differ" cannot fail.** Two distinct weight vectors dotted against 36 non-identical vectors
essentially always differ — that is arithmetic, not evidence. It is the same class of error as
the earlier squad's one-axis finding.

The real question is narrower: **does creed-weighted ranking do anything a creed-independent
quality score does not already do, and is it stable under the wobble a real interview
produces?**

**WP-P1 — corpus import + value set + pre-registration** (~3h, no deps)
Snapshot the 36 rows *with rationales* at a pinned commit SHA; author
`ammerse.value-set.yaml` with `attribution` populated; land the **definition-parity test in
the same commit** (expected **red** on first run — the drift is known; do not fix by loosening
the test); commit two hand-authored creeds and the **pre-registered expected top-5 before any
ranking code exists**.

> **Creed B differs from creed A on `minimal` only** — the one axis carrying 70% of all cost
> signal. If flipping the sole informative axis barely moves the ranking, the mechanism is
> dead and you learn it from one fixture.

**WP-P2 — the ranking function** (~4h). Pure, no I/O; owns weight normalisation in one place;
a missing axis is a hard error, never an implicit 0. Hand-roll Kendall τ-b / top-N / Jaccard
(~40 lines; scipy must not become a dependency for a prototype).

**WP-P3 — the experiment** (~3h). Assert the pre-registered thresholds as a real pass/fail.

**Three arms, all required:**

1. **Baseline arm** — rank by unweighted row-mean. If creed-weighted ranking correlates
   r > 0.95 with this, the creed is decoration.
2. **Creed-blind arm** — the `#2538` shape. If the returned set is unchanged, citing
   `creed.yaml` in a trace is decoration too.
3. **Perturbation-stability probe** — jitter each weight by the wobble a real interview
   produces and report rank correlation. This is the arm that can kill the design in an
   afternoon.

**Pre-register the failure condition**, e.g. *top-5 must differ from the flat-creed top-5 by
≥2 items at a moderate creed*. Write it down before running.

---

## 8. What survives every lens — the minimum shippable thing

If the experiment fails, this is what remains, and it is worth shipping on its own:

> A **`costs:` free-text field** on the four `value_impact` kinds — one sentence naming what
> adopting this artefact makes worse — plus an **operator-authored charter statement naming
> what the project deprioritises**, plus the **sign-vs-rationale-polarity lint**.
> No numbers. No 7-vector. No matrix. No edge weights. No ranking function.

Every objection in this document lives in the arithmetic: the sign channel is noisy (§2), one
of seven axes carries cost signal, weighted ranking collapses toward magnitude, and the
register is ~2,650 cells against a 34-vector calibration set. **Nothing here touches the
prose** — and by the corpus's own measurement the prose keeps the only axis that discriminates.

Also surviving intact, and not contested by any lens:

- **The dimensionality claim** (§5.3 of the input, independently replicated at n=34). The
  seven axes carry genuine independent information; the earlier one-dimensionality finding is
  dead.
- **The corpus is not slogan-shaped.** `avoid_gold_plating` extensible −0.70,
  `AMMERSE_impact_analysis` minimal −0.60 *for its own method*,
  `be_a_STARR_at_interviews` minimal −0.65. Specific, costly, unflattering self-assessments —
  a genuine calibration corpus authored by someone doing the work.
- **`minimal` is a real discriminator** — mean +0.024, stdev 0.402, 19 of 34 negative, range
  [−0.65, +0.85]. A single field asking *"what does adopting this cost in simplicity?"*,
  authored with a rationale, is cheap, defensible, and has 34 worked examples.
- **Charter-scoping the creed** is the right home and cleanly retires the
  project-specific-data-in-a-reusable-library objection.
- **The replaceable value set** genuinely defuses basis lock-in.
- **`routing_priority` refutes "3-for-3" as a law** — 18 authored producers and live
  consumers from inception. The discriminating variable is *a consumer in the same seam*,
  which `creed · deltas` can satisfy. 3-for-3 is a strong regularity, not a structural
  impossibility, and should not be carried as a blocker against this design.

---

## 9. Open operator decisions

1. **Mandatory negative: advisory lint, not schema.** Recommended by every lens. Confirm.
2. **Mandatory rationale:** the corpus fails it (§1.1). Advisory or hard?
3. **`impacts`: annotate or replace `in_tension_with`?** Annotate needs no ADR; replace needs a
   superseding one.
4. **Does the ranking use arithmetic at all**, or does an LLM read `creed.yaml` as prose
   context? If the latter, the 1,820 numbers are decorative and the experiment changes shape.
   The input doc does not say, and the two readings have different costs.
5. **Interview instrument:** authored question bank + forced-choice, or keep it model-chosen?
6. **The design's own self-assessment.** The corpus already authored a vector for this very
   practice: `AMMERSE_impact_analysis` scores **minimal −0.60** ("introduces significant
   complexity and effort") and **agile −0.35** ("time-consuming and may hinder agility… the
   potential indirect support for better decisions is not enough to offset this"). It is the
   most credible thing available and it is free. Put it in the design.

---

## 10. Method limits

Four lenses, read-only, no tests executed — every "breaks silently" claim is a static read.
The reviewer sampled 14 of 38 corpus files (the all-non-negative set plus controls), so the
sign-inconsistency finding establishes that inconsistency exists at ±0.85 for equivalent prose
but does **not** characterise its distribution; a coherent constant shift, under which sign is
meaningless but *ordering* survives, was not ruled out and deserves the test. The Dirichlet
sweep is a sensitivity analysis, not a prediction of real operator creeds, and the claim that
LLM interviews yield near-flat creeds is inference from the virtue-framing plus the cited
format-inversion prior art — the weakest joint in the strongest argument, and testable in a day
by the same test-retest recommended in §4. The 260-artefact and 774-edge counts are greps,
directionally right and unaudited. Two lenses diverged on `toolguide` and `agent_profile`
membership; §3.3 adjudicates on semantics (adopted-vs-consulted; stance-vs-delta) and that
adjudication is a judgement, not a measurement.
