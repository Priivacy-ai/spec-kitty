---
title: FoundationalValues and Creed — canonical design
description: "The single authority for the FoundationalValues/creed design: a value system generic over N values with AMMERSE as the default basis, per-artefact impact deltas, a signed impacts edge that subsumes in_tension_with, and the measured grounding behind all of it."
doc_status: draft
updated: '2026-07-26'
related:
- docs/plans/doctrine/manifesto-program-delivery-sequence.md
- docs/plans/doctrine/creed-and-values-design-as-proposed.md
- docs/plans/doctrine/squad-reports/index.md
- docs/plans/doctrine/index.md
---
# FoundationalValues and Creed — canonical design

> **Tier: AUTHORITY.** The only document in `docs/plans/doctrine/` citable as "the design".
> Everything else in this corpus is **RECORD** (what was decided and why) or **EVIDENCE** (raw
> squad reports and measurements). Where an older document disagrees, this one wins — §11.

**Date:** 2026-07-26 · **Status:** design proposal. **No build decision has been taken.**

> ### ⚠️ Read this before anything else
>
> - **Nothing was executed.** Every claim about code behaviour in this document is a **static
>   read** of source and test bodies. No test was run. Claims of the form "X silently drops Y"
>   are predictions by construction, not observed failures.
> - **The measurements *are* real and reproducible.** Every number in §6 comes from
>   `_reproduce_matrix_findings.py` (stdlib only, run it) and every corpus number from
>   `_ammerse-corpus-36-practices.json`, both committed beside this file.
> - **One decision gates the whole programme: D-2 — which DRG relation carries `impacts` once
>   `in_tension_with` retires.** It swings the migration between ~5–10 files and ~45–60. The
>   *design* is stable under either answer; only the *programme shape* moves. It must be settled
>   inside the superseding ADR, not discovered during implementation.

## 0. What is being asked of a reviewer

Three questions, in order of what they unblock:

1. **Is the shape right?** Three planes (§5), `impacts` subsuming `in_tension_with` (§7.5), the
   creed on the charter rather than in the doctrine library (§7.7). A "no" here stops everything.
2. **Answer D-2** (§13) — or confirm it is the ADR author's call.
3. **Authorise the prose-only band?** §8 is a self-contained subset that survived every
   adversarial lens, gates on nothing, and is the honest do-less alternative to the numeric layer.

**What it costs, so the ask is priced.** Full detail in the sequence document; headline:

| Band | Effort | Notes |
|---|---|---|
| Prose-only (§8) | ~9–12 files, <0.7 kLOC, **4–7 days** | Gates on nothing. Ships alone |
| Through the gates | ~55–100 files, 2.4–4.6 kLOC, **11–18 days** | |
| Numeric layer | ~120–180 files, 6–11 kLOC, **25–45 days** + authoring | **1,820 authored cells** against a **34-vector** calibration set |

**~85% of the programme's cost sits behind two gates** (D-2 and the `#2538` experiment).

**How we would know it failed.** Two falsification instruments exist and neither has been run: a
**perturbation-stability probe** (jitter the creed weights by the wobble a real interview produces;
if the ranking is unstable the mechanism is dead — ~20 lines, an afternoon) and **`#2538` arm B**
(does an agent given the creed *surface* a trade-off rather than resolve it silently). Prior art
predicts arm B reads null, which is precisely why it should run before the expensive band.

---

## 1. Problem statement

> **We are lacking a systems thinking model.**

Doctrine resolves to an unordered bag of co-valid rules. When two conflict, the arbiter is whatever
prior the consuming model brings — and for current-generation LLMs that prior favours delivering
output now. The system delegates its value arbitration **by omission**.

## 2. The operative frame — governs everything below

> Quantitative measures are unreliable, indeed. But a **limited-horizon heuristic** is a pragmatic
> approach that is "close enough" for practical purposes. Our goal is not to recreate absolute
> truth or reach a mathematical representation of an unrepresentable fact. It is to **formally
> encode our graph in a way that is "good enough for government work" and improves the LLM's /
> agent's reasoning about the operator's intent and preferences.**

Three binding consequences:

1. **Per-cell defensibility is not the bar.** A heuristic that informs a reader does not need every
   number to be individually right.
2. **It must never auto-decide.** It makes the trade explicit and the deviation visible, and demands
   a rationale. Numbers are conversation prompts, not verdicts.
3. **Graceful degradation is acceptable.** Weaker inference models get weaker benefit; worst-case
   "better than not doing it" is a valid reason to build.

## 3. Provenance

The design builds on prior art by **Stijn Dejongh** (the Pragmatic Penguin Patterns library, the
three-tier sense-making meta model) and **J.B. Crossland** (the AMMERSE value system and its impact
matrices). AMMERSE is used with the author's authorization: **accreditation is required, not a
license of the consultancy framework.** AMMERSE, AMMERSE Method, AMMERSE Theory and AMMERSE Value
System are trademarks of J.B. Crossland. §12 states where accreditation must appear.

## 4. Generic over N — the design is not AMMERSE

**AMMERSE is the default basis, not the model.** A consumer may substitute any value system of
**N ≥ 3** values plus their correlations. Every structure is parameterised on N.

| Element | Generic form | AMMERSE default |
|---|---|---|
| Value set | N values, each `{id, name, kind, description}` | 7: Agile, Minimal, Maintainable, Environmental, Reachable, Solvable, Extensible |
| Connascence matrix | N×N, zero diagonal, coefficients ∈ [−1, 1] | the published first-order matrix |
| Normalisation divisor | **N − 1** | published as **6**; see the caveat below |
| Creed | N weights + N rationales | — |
| Artefact impact | up to N `{name, delta, rationale}` entries | — |

**Axis identity is by `id`, never by position.**

> ⚠️ **The `N − 1` reading is an interpretation, not an upstream statement.** The article publishes
> a divisor of **6** and sums over the six *other* values. Reading that 6 as `N − 1` is what makes
> §6's generic bound transfer. If an upstream divisor were arbitrary rather than "count of other
> values", the bound would not generalise. This is load-bearing and it is an inference.

## 5. The three planes — and the one legal composition

| Plane | Relates | Shape | Right name | Composes by |
|---|---|---|---|---|
| **P1 — value ↔ value** | two values | **symmetric** | *correlation-like* | the matrix; N(N−1)/2 unordered pairs |
| **P2 — node → node** | two doctrine artefacts | **directed** | **gain / elasticity** | authored per edge; signed |
| **P3 — artefact → value** | an artefact and a value | directed *intervention effect* | **delta** — change from *not adopting* | summable across the active set |

1. **`delta` (P3) is the only persistable term.** It is `base`.
2. **The matrix (P1) supplies ripple.** Computed, never stored as authored.
3. **`impacts` (P2) is authored, never derived from P3.** Derivation failed measurement (§10.1) and
   is forbidden.

> **`delta` is the semantically right word**, and it is why the arithmetic works: a delta is
> relative to a baseline, so deltas compose. A **weight** does not — two profiles each weighting a
> value at 0.8 does not give 1.6. Hence `value_bias` (creed, profiles) vs `value_impact`
> (artefacts), as **distinct types** (§7.3).

## 6. The mathematics

**Adopted composition — two terms, damped:**

```
overall(v) = (1 − r) × [ base(v) + 0.5 × ( Σ_{w ≠ v} M[v][w] · base(w) ) / (N − 1) ]
```

All figures reproducible via `_reproduce_matrix_findings.py`, reading
`_ammerse-connascence-first-order.json`, both committed beside this document.

### 6.1 Per-step gain and the adopted truncation's residual

On the AMMERSE basis: **λ = 2.3350**, so per-step gain **λ/(N−1) = 0.3892**. With the ½ dampening
the decay ratio is **r = 0.5 × λ/(N−1) = 0.1946**, and the residual of the **adopted two-term
damped** truncation is

> **r²/(1 − r) = 4.70%**

For the avoidance of the error an earlier draft made, the four candidates are:

| Truncation | Residual |
|---|---|
| undamped, two terms | 24.79% |
| undamped, three terms | 9.65% |
| **damped, two terms — adopted** | **4.70%** |
| damped, three terms | 0.91% |

`r` is an **asymptotic bound**, not the observed per-tier ratio: on a real artefact the observed
decay is roughly half of `r`, because a real base vector is not aligned with the dominant
eigenvector.

### 6.2 The generic bound — bounded always, sound for any non-degenerate basis

For any matrix with zero diagonal and coefficients in [−1, 1], Gershgorin gives
`|λ| ≤ max row abs-sum ≤ N − 1`, therefore:

> **gain ≤ 1 for every admissible consumer basis.**

The bound is **non-strict**, and the Neumann series converges only for gain **< 1**. So:

- **bounded** for any admissible basis;
- **sound for any non-degenerate basis** (gain < 1).

**Equality (gain = 1) characterises perfect *polarisation*, not perfect agreement.** Verified at
N = 3, 5, 7, 12: all off-diagonal `+1` gives gain 1.0000, and so does all off-diagonal **−1**
(perfect mutual disagreement), as does any two-camp sign-flip pattern. In every such case the basis
has collapsed to a single concern, possibly sign-flipped.

*(If P1 were constrained to be a genuine correlation matrix — positive semi-definite after adding
the identity — all-agree would become the unique equality case. The design does not currently impose
that, and it is a candidate third constraint.)*

**Consequence for the validator:** enforce coefficients ∈ [−1, 1] and a zero diagonal by schema;
then **error at gain ≥ 1 − ε** and **warn as gain → 1**. The spectral radius is load-bearing at
exactly the boundary case, so it is a check, not decoration. Empirically it is not a tight
constraint — the AMMERSE basis sits at 0.389, well inside.

### 6.3 Sensitivity to the one asymmetric cell

The published matrix is symmetric in **48 of 49** cells; the exception is
`maintainable → extensible = +0.75` against `extensible → maintainable = −0.75` — a probable
upstream sign error (§10.4). λ was computed on the **unrepaired** matrix, and the repair choice
moves the result:

| Reading | gain | residual |
|---|---|---|
| as published (asymmetric) | 0.3892 | 4.70% |
| symmetrised to +0.75 | 0.3766 | 4.37% |
| symmetrised to −0.75 | 0.4337 | **6.00%** |
| cell zeroed (abstain) | 0.3995 | 4.99% |

The spread is 4.37%–6.00%. Nothing about the design's soundness turns on it, but the headline number
does, so **the cell must be adjudicated before the matrix ships** (D-6).

### 6.4 Do not renormalise per tier — that is what causes absolutism

Renormalising after each matrix application **is power iteration**: `M^k v / ‖M^k v‖` converges to
the dominant eigenvector regardless of `v`, so every artefact converges to the same attractor and
its own identity is destroyed. Demonstrated with three deliberately dissimilar artefacts — all
migrate to the same pattern by tier 5. Values piling onto ±1 and 0 is the signature, and the
published *normalised* second-order matrix contains cells at exactly ±1.

**The dampening already solves this; the renormalisation was silently undoing it.** Stopping at
first-order costs 4.70%; a third tier would cost 0.91%. So truncation depth is a free choice, not a
defensive one.

**Scale once at the end, never per tier.** `(1 − r) = 0.8054` bounds the output into [−1, 1] and,
because every artefact is multiplied by the *same* constant, preserves all relative ordering
exactly. *(That constant is derived from the infinite damped series, `S = 1/(1−r)`; the tight
constant for a two-term truncation is `1/(1+r) = 0.8371`. Either bounds the output; `(1−r)` is
simply the more conservative.)*

### 6.5 Second-order is not adopted

The article states second-order values come from "multiplying the first-order impact matrix with
itself." **Tested and false:** every one of the **42 off-diagonal** cells mismatches `M×M` (the 7
diagonal cells are trivially different, since the published second-order diagonal is zeroed). Six
hypotheses were tested and rejected, best fit `1.75 × M` still wrong in 32 of 49; the published
normalisation is also not `raw / max|raw|`.

So the second-order matrix is **independently authored judgement, not a computed ripple** — it needs
its own provenance and cannot inherit the first-order matrix's. **Use first-order only**, which the
in-repo tactic already calls "the standard path". It is also already max-normalised, so consuming it
would import the absolutism step of §6.4.

## 7. The design

### 7.1 `FoundationalValues` — a repository-backed artefact, not an enum

The closed-`StrEnum`-plus-drift-guard pattern is the norm in this codebase, so a
consumer-replaceable set cannot be one. The extensibility wanted **already exists**: the built-in →
org → project three-tier repository layering in `src/doctrine/base.py`. And `Role` in
`src/doctrine/agent_profiles/profile.py` is already a proven, Pydantic-wired *half-open value
object* — copy it rather than invent a pattern. Openness then lives in a **substitutable artefact**,
and the validation target is *the active value set*, not a module literal.

```yaml
# src/doctrine/values/built-in/ammerse.value-set.yaml
value_set_id: ammerse
name: AMMERSE
attribution: >          # REQUIRED, non-empty
  AMMERSE value system by J.B. Crossland, used with the author's authorization.
  AMMERSE and related marks are trademarks of J.B. Crossland. Accreditation,
  not a license of the consultancy framework.
source:
  url: https://patterns.sddevelopment.be/practices/ammerse_impact_analysis/
  accessed_on: "2026-07-26"
values:
  - id: minimal
    name: Minimal
    kind: lever          # lever | goal — see §7.2
    description: The focus on simplicity and avoiding unnecessary complexity.
  # ... N − 1 more
connascence:             # N(N−1)/2 unordered pairs; symmetric by construction
  matrix_id: ammerse-first-order
  matrix_version: "1.0"
  pairs:
    - [minimal, maintainable, 0.75]
    # ...
```

⚠️ **Do not expose the value-set repository as a `DoctrineService` property.** An architectural test
introspects every `@property` on `DoctrineService` and demands matching `selected_<kind>` and
`required_<kind>` config fields, so a property silently turns a two-file change into a three-way
lockstep across two packages. Use a named accessor: `resolve_active_value_set()`.

### 7.2 Type the axes — levers vs goals

Across the 36 authored vectors, `solvable` and `environmental` are **never negative**, and five of
seven axes carry ≤3 negative cells — effectively **one cost axis and six benefit axes**.

The **adjudication** (an interpretation, not a measurement) is that the basis **conflates levers with
goals**: goal variables sit at the end of causal chains, so nothing pushes them down. The in-repo
causal-map template already types nodes Practice / Outcome / Risk. Competing explanations — one
author's optimism, or those axes genuinely rarely costing anything — are not excluded.

Each value therefore carries `kind: lever | goal`, and a consumer-authored basis is forced to say
which is which.

### 7.3 Two fields, two types

| | `value_impact` | `value_bias` |
|---|---|---|
| Semantics | Δ from *not adopting* | weight — "how much we care" |
| Arithmetic | **summable** | **not summable** |
| Side of `bias · deltas` | right | left |
| Carried by | directive, tactic, styleguide, procedure | **creed**, agent_profile, paradigm |

Distinct Pydantic types (`ValueImpact` vs `ValueWeighting`), **not** one model with a `mode`
discriminator, so the type system structurally prevents dotting a profile with a directive. The
creed's own field is `value_bias` — the creed *is* the project's profile. `paradigm` sits on the bias
side too: a worldview is a stance, not a Δ-from-baseline.

**Authored entry shape — verbatim from the calibration corpus, so imports need zero translation:**

```yaml
value_impact:
  - name: minimal
    delta: "-0.25"        # STRING on the wire; Decimal in memory
    rationale: >
      Introduces additional complexity through documentation and tracking,
      but the overall negative impact remains low.
```

**`delta` is a string on the wire and `Decimal` in memory** — `condecimal(ge=-1, le=1)` plus a
`mode="before"` validator that **rejects non-`str` raw input**, because `Decimal(float)` is lossy and
an unquoted `delta: 0.9` (which ruamel yields as `float`) must be a hard error. This round-trips the
corpus byte-identically, permits exact arithmetic, and needs no comparison epsilon. **Do not enforce
a resolution grid** — the corpus authors `0.125`.

### 7.4 Which kinds carry a value field

Declared as **positive** frozensets in `src/doctrine/artifact_kinds.py`, never as prose:

```python
_VALUE_IMPACT_KINDS = {DIRECTIVE, TACTIC, STYLEGUIDE, PROCEDURE}
_VALUE_BIAS_KINDS   = {AGENT_PROFILE, PARADIGM}          # + the charter creed
```

Positive, not negative, because an exclusion set silently *includes* a future kind — which would
acquire a scoring obligation nobody authored.

**Out, with reasons:** `toolguide` (consulted, not adopted — no Δ-from-not-adopting);
`mission_step_contract` (structural wiring; a vector double-counts the directives its action
resolves); `glossary_pack` (terminology has no adoption delta; also has no JSON schema at all);
`template`, `asset`, `anti_pattern` (align with the existing non-augmentable exclusion set).

`anti_pattern` is *structurally* incapable: its nodes hold only `urn`/`kind`/`label`/`tags`, so there
is nowhere for the mandatory rationale. A negative-only vector is its natural form — which is exactly
why it must be **derived** as the sign-flip of whatever `rejects` it, never authored.

### 7.5 `impacts` subsumes `in_tension_with`

**Operator ruling, settled:** `impacts: -1` *is* what "is antagonistic towards" means, so
`in_tension_with` is the special case of a negative `impacts`. Keeping both would maintain two
authorities for one concept. `DRGEdge` already carries optional `when` and `reason`, so the
annotation is a sibling of existing fields.

The candidate-pair predicate becomes `relation == impacts and impacts < 0` — **strict sign**.

> **What this does and does not remove.** It removes the *derivation-induced* false positives that
> measurement found (§10.1). **Authoring error remains**, and under strict sign **every negative
> edge, however small, is a formal tension claim** that the consistency check will surface as
> unreconciled. An author writing `impacts: -0.05` for a mild trade-off creates a reconciliation
> obligation. That is a real operational consequence of the strict-sign choice.

`reconciles_tension` **survives**, re-pointed at negative-`impacts` pairs — the lifecycle half must
not be orphaned.

This requires a **superseding ADR** for `docs/adr/3.x/2026-07-21-1-in-tension-with-drg-edge.md`
(cite the full filename — a second ADR shares the `2026-07-21-1` prefix). Note for the ADR author:
a hardening lens previously **rejected** `Relation.IMPACTS` and concluded no superseding ADR was
needed; the operator ruling overrides that, and D-2 reopens the relation question as a genuine
choice (§11).

### 7.6 The composition invariant, enforced structurally

> Make the computed projection a **frozen dataclass with no `model_dump()`**, in a module no writer
> imports, carrying a mandatory `matrix_id` / `matrix_version` stamp.

Doctrine and charter writers serialise through `model_dump()`, so a projection that cannot produce
one can never be written back — by anyone, including a future agent who never read this document.
That closes the worst failure mode (computed ripple laundered into an authored assessment, then
re-composed against itself) by construction. **One known exception to extend the guard to:** the DRG
extractor writes graph YAML with a deliberate field-by-field builder, bypassing `model_dump()`.

### 7.7 The creed lives on the charter

The creed is **project-specific data**, so it belongs on the charter, not in the reusable doctrine
library. It carries `value_set: <id>` — a pointer, not inline axis names — plus N weights each with a
rationale.

⚠️ **The charter's on-disk sections are not model-validated in production** (every production reader
goes through raw ruamel; `model_validate` appears only in tests), so a `creed:` block would land
**silently unvalidated**. It needs an explicit per-section validate at the sync seam, and a
**three-state** loader (`absent` / `partial` / `complete`) whose `absent` state surfaces as a
consistency-check finding rather than an info log.

## 8. The prose layer — the do-less option, ships first, gates on nothing

Independent of every gate, and it survived all four hardening lenses:

1. **A `costs:` sentence** on the `value_impact` kinds — what adopting this makes worse.
2. **An operator-authored charter statement** naming what the project deprioritises. Human-authored:
   an agent drafting the operator's values is the self-scoring failure.
3. **The sign-vs-rationale-polarity lint** — flag any cell whose rationale names only a cost while
   `delta ≥ 0`. **The only component with a validation set available today.**

> **The floor that makes "good enough" actually good enough: never render a number without its
> rationale, and treat the rationale as authoritative where they disagree.** The corpus shows the
> prose is right when the number is wrong (§10.2).

**This is the honest alternative to the numeric layer**, not merely its first slice.

## 9. The feedback gap

The neural-network analogy holds for its conclusion ("individual weights need not be right") but is
missing what makes that true: NN weights tolerate individual meaninglessness because of a **loss
signal**, **gradient updates rather than authoring**, and **redundancy**. This design has none.

Without a correction mechanism an authored weight set does not converge; it simply *is*, carrying its
author's bias. **Override events are the available gradient** — a deviation ledger recording
*(suggestion, override, reason)* makes the analogy real.

> A reviewer may reasonably argue this should be a **precondition** rather than a next iteration,
> since the document's own analysis makes the missing gradient the load-bearing risk. That is a fair
> challenge and it is not settled.

## 10. Measured grounding

**Corpus ladder, stated once:** 38 practice files → 37 with an `ammerse` block → **36 with a
complete 7-axis vector** → **34 excluding two all-zero stubs** (`TEMPLATE_PRACTICE`,
`quad_A_test_structure`). Every figure below names its basis.

### 10.1 What failed measurement — do not rebuild these

| Mechanism | Result |
|---|---|
| Deriving a **precedence ordering** from value vectors | **0 reproductions of 6**; four distinct orderings; worse than chance. Categorical: the target encodes a pipeline of operator types (generator / transformer / guard), and a scalar weighting has one output type |
| Deriving **tension edges** from sign opposition | **5 of 5 false positives** on deliberately unrelated pairs, with opposition counts overlapping genuine cases. ⚠️ Wide interval — 5 pairs out of ~47,900, chosen as expected-to-be-unrelated rather than adversarially hard |
| Second-order matrix as `M×M` | **42 of 42 off-diagonal cells mismatch** |

### 10.2 What the corpus shows

- **Effective dimensionality: ~4–5 of 7.** Per-component variance at n=36:
  31.9 / 21.3 / 14.2 / 12.5 / 8.7 / 7.6 / 3.9 — so **4 components reach 79.8%** and 5 reach 88.6%.
  At n=34 the series is 33.9 / 56.1 / 71.2 / 81.6 / 90.0 cumulative, again ~80% at four. Pairwise
  correlations exceeding |0.35|: **two at n=36**, **three at n=34** (the third marginal at −0.37).
  ⚠️ This measures how *this* author used the axes across 34–36 vectors. It does not prove a property
  of the basis, and a different author on a different corpus could collapse them — which matters
  because §4 makes the design generic over consumer bases.
- **It is not slogan-shaped.** `avoid_gold_plating` extensible −0.70; `AMMERSE_impact_analysis`
  minimal −0.60 *for its own method*; `be_a_STARR_at_interviews` minimal −0.65. Specific, costly,
  unflattering self-assessments.
- **The sign channel is noisy — the finding that bites a heuristic.** `manual_of_me` records minimal
  **+0.25** for prose reading *"decidedly not minimal"*, against `AMMERSE_impact_analysis`'s
  **−0.60** for the same claim: 0.85 apart, opposite signs. `fail_fast` records maintainable
  **+0.50** for *"long-term maintenance challenges"*. Eleven of twelve all-non-negative entries name
  explicit costs **in prose** while the number sits at or above zero. **The 12-of-34 (35%) figure
  measures sign-channel noise, not authorial honesty**, and exactly one entry is a true slogan.
- **Therefore: no `minItems: 1` negative as a schema constraint.** It gates on the least reliable
  field and inverts its own outcome — it would reject eleven careful analyses and **pass** the only
  real offender. Ship it as an advisory lint.

### 10.3 Upstream discrepancies to report

1. **Probable sign error** — the sole asymmetry in 49 cells (§6.3), while the published second-order
   matrix is fully symmetric.
2. **The derivation claim is false** (§6.5).

**The operator reports these, not an agent** — an external communication about a trademarked work,
inside the accreditation relationship. Record them in-repo with a `source_digest` so a later re-port
detects an upstream fix, **before the matrix ships** (D-6).

## 11. Contradiction register — this document's values win

| Claim | Superseded | **Canonical** |
|---|---|---|
| Residual of the adopted truncation | ~6% | **4.70%** — 6% was the *undamped three-term* figure |
| Generic soundness | "unconditionally sound" | **bounded** always (gain ≤ 1); **sound** for gain < 1 |
| The gain = 1 equality case | "all values agree perfectly" | **perfect polarisation**, incl. all-disagree |
| Effective dimensionality | "5 components for 80%", "rank ≈ 5" | **~4–5 of 7**; 4 reach 79.8% |
| `trade-off` / `long-term` in doctrine YAML | 0 / 0 | **35 / 15** (authored YAML, excluding generated graphs) |
| All-non-negative corpus vectors | 39% (14/36) | **35% (12/34)** — two of the fourteen are stubs |
| Corpus dimensionality | "collapses to ~one axis" | refuted — see above |
| AMMERSE tactic status | "completely inert" | **charter-activated and `requires`-mandated, yet zero scores exist** |
| Paradigm instances | 14 | **13 DRG nodes** |
| Directive ID contract | `^DIRECTIVE_\d{3}$` | **`^[A-Z][A-Z0-9_-]*$`** — the real defect is unreachability |
| `impacts` vs `in_tension_with` | keep separate; no ADR needed | **`impacts` subsumes it**; superseding ADR required (operator ruling) |
| `Relation.IMPACTS` | rejected by a hardening lens | **reopened as D-2** (operator ruling overrides) |
| The connascence matrix | "park it — no available producer" | **unparked**: coefficients are now in-repo and authorized |
| "Two axes carry no cost information" | as stated | **understated** — one cost axis, six benefit axes |
| "Gain, not correlation" | applied to everything | **matrix is symmetric ⇒ correlation-like; edges are directed ⇒ gain** |
| Field-authored-relationship ban | blocks `value_impact` | **does not apply** — covers three lineage fields only. *Adjudicated, not measured* |
| "3-for-3 decay is a law" | blocker | **a strong regularity, not a law** |

## 12. Accreditation

- **Required, non-empty `attribution` on the value-set artefact** — the single authority, copying the
  one existing kind whose provenance field is *required*. Everything else points here; do not
  replicate the notice per artefact.
- **Unify the two drifted definition copies first.** All seven definitions differ between the tactic
  and the template (the template carries compressed glosses while the tactic says "use these
  verbatim"). **Accrediting a misquoted definition is worse than not accrediting.**
- **A root `NOTICE` file**, because the repo's `LICENSE` attributes copyright elsewhere. Mechanics
  (packaging inclusion, `Field(json_schema_extra=...)` rather than a generated schema's `$comment`,
  the existing import-candidate provenance machinery) are in the sequence document.

## 13. Open decisions

| # | Decision | Why it matters |
|---|---|---|
| **D-1** | Value-bearing kinds: is `toolguide` in, and is `agent_profile` `value_bias` or out? | Two lenses disagreed. §7.4 adjudicates on semantics; settle before touching model/schema files |
| **D-2** | **Which relation carries `impacts` after `in_tension_with` retires?** | **The programme-shape gate.** ~45–60 files vs ~5–10. Must be decided inside the ADR |
| **D-3** | Does the creed feed **arithmetic**, or does an agent read `creed.yaml` as prose context? | If prose, the ranking function is unnecessary and the numeric layer shrinks dramatically |
| **D-4** | Interview instrument: authored question bank + forced choice, or model-chosen questions? | Model-chosen over N virtues with no budget predictably yields a near-flat creed, the regime in which the creed is inert — and nothing records *who supplied each weight*, so a model's prior can acquire operator provenance |
| **D-5** | Mandatory `rationale`: advisory or hard? | The calibration corpus fails it (≥3 of 38) |
| **D-6** | The asymmetric matrix cell (§6.3) | The symmetry validator cannot be written without it, and the headline residual moves 4.37%–6.00% |

## 14. Sequence

See `manifesto-program-delivery-sequence.md` for the executable plan: critical path with gate
positions, 22 increments ranked by evidence-per-cost, the ADR scope, tracker shape, park register,
and effort envelope.

**Recommended first band, if built** (gates on nothing): the zero-producer lint, the polarity lint,
wiring the existing `generate_schemas --check` into CI, and the AMMERSE definition unification.

## 15. Method and limits

Twelve profile-loaded agents across three squads (two sequential adversarial rounds, one hardening
round of four lenses), plus a design-aggregation pass, a corpus measurement, a connascence-matrix
measurement, and a publication-readiness review. All read-only.

- **Nothing was executed** — no test was run; every code-behaviour claim is a static read.
- The sign-channel finding sampled 14 of 38 corpus files plus 3 controls: it establishes that
  inconsistency exists at ±0.85 for equivalent prose but does **not** characterise its distribution.
  A coherent constant shift, under which sign is meaningless but *ordering* survives, was not ruled
  out.
- The ranking measurement assumed a linear dot product, because **D-3 is unresolved**.
- Artefact counts (260 behavioural artefacts, 774 edges) are greps — directionally right, unaudited.
- The `#2538` rig's liveness is unverified by anyone; the experiment gate decays with it.
- λ was computed on the **unrepaired** matrix; §6.3 reports the sensitivity.
