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

> **Tier: AUTHORITY.** This is the only document in `docs/plans/doctrine/` that may be cited as
> "the design". Everything else in the manifesto/creed corpus is **RECORD** (what was decided
> and why) or **EVIDENCE** (raw squad reports). Where an older document disagrees with this one,
> this one wins — see §10 for the contradiction register.

**Date:** 2026-07-26 · **Status:** canonical design, **no build decision taken**
**Aggregates:** the operator's design, two adversarial squad rounds, one hardening squad, one
design squad, a 36-vector corpus measurement, and a connascence-matrix measurement.

---

## 1. Problem statement

> **We are lacking a systems thinking model.**

Doctrine resolves to an unordered bag of co-valid rules. When two conflict, the arbiter is
whatever prior the consuming model brings — and for current-generation LLMs that prior favours
delivering output now. The system delegates its value arbitration **by omission**.

## 2. The operative frame — governs everything below

> Quantitative measures are unreliable, indeed. But a **limited-horizon heuristic** is a
> pragmatic approach that is "close enough" for practical purposes. Our goal is not to recreate
> absolute truth or reach a mathematical representation of an unrepresentable fact. It is to
> **formally encode our graph in a way that is "good enough for government work" and improves
> the LLM's / agent's reasoning about the operator's intent and preferences.**

Three consequences, all binding:

1. **Per-cell defensibility is not the bar.** A heuristic that informs a reader does not need
   every number to be individually right.
2. **It must never auto-decide.** It makes the trade explicit and the deviation visible, and
   demands a rationale. Numbers are conversation prompts, not verdicts.
3. **Graceful degradation is acceptable.** Weaker inference models get weaker benefit;
   worst-case "better than not doing it" is a valid reason to build.

## 3. Generic over N — the design is not AMMERSE

**AMMERSE is the default basis, not the model.** A consumer may replace it with any value system
of **N ≥ 3** values plus their correlations. Every structure below is parameterised on N; nothing
hardcodes seven.

This is not a courtesy — it is load-bearing, because §5 shows the mathematics is sound for *any*
such basis, and §6.1 shows the extensibility rides machinery this repo already has.

| Element | Generic form | AMMERSE default |
|---|---|---|
| Value set | N values, each `{id, name, description}` | 7: Agile, Minimal, Maintainable, Environmental, Reachable, Solvable, Extensible |
| Connascence matrix | N×N, zero diagonal, coefficients ∈ [−1, 1] | the published first-order matrix |
| Normalisation divisor | **N − 1** (the count of *other* values) | 6 — **verified: 6 = 7 − 1** |
| Creed | N weights + N rationales | — |
| Artefact impact | up to N `{name, delta, rationale}` entries | — |

**Axis identity is by `id`, never by position.** Any consumer-supplied basis of a different N
must work without touching a positional index anywhere.

## 4. The three planes — and the one legal composition

Every earlier round conflated quantities living on different planes. The measurements settle
their shapes, and this separation is the model's spine.

| Plane | Relates | Shape | Right name | Composes by |
|---|---|---|---|---|
| **P1 — value ↔ value** | two values | **symmetric** | *correlation-like* | the matrix; N(N−1)/2 unique unordered pairs |
| **P2 — node → node** | two doctrine artefacts | **directed** | **gain / elasticity** | authored per edge; signed |
| **P3 — artefact → value** | an artefact and a value | directed, an *intervention effect* | **delta** — change from *not adopting* | summable across the active set |

Three rules follow, and they are the whole arithmetic:

1. **`delta` (P3) is the only persistable term.** It is `base`.
2. **The matrix (P1) supplies ripple.** Computed, never stored as authored.
3. **`impacts` (P2) is authored, never derived from P3.** Deriving a P2 edge from two P3 vectors
   is the mechanism that failed measurement (§9.1) and it is forbidden.

> **`delta` is the semantically right word** and it is why the arithmetic works: a delta is
> relative to a baseline (not adopting), so deltas compose. A **weight** does not — two profiles
> each weighting a value at 0.8 does not give 1.6. That is why the creed and profiles carry
> `value_bias` and artefacts carry `value_impact`, as **distinct types** (§6.3).

## 5. The mathematics — sound for any basis, unconditionally

Composition, generic:

```
overall(v) = base(v) + 0.5 × ( Σ_{w ≠ v} M[v][w] · base(w) ) / (N − 1)
```

**Measured on the AMMERSE basis:** dominant |eigenvalue| **λ = 2.3350**, so per-step gain
**λ/(N−1) = 0.3892 < 1**. The Neumann series converges and the two-term truncation carries a
residual governed by `(λ/(N−1))³ ≈ 0.059` — **about 6%.** "Good enough for government work" is
quantitatively defensible here, not merely asserted.

**And it generalises unconditionally.** For any matrix with zero diagonal and coefficients in
[−1, 1], Gershgorin gives `|λ| ≤ max row abs-sum ≤ N − 1`, therefore:

> **gain = λ/(N−1) ≤ 1 for every admissible consumer basis, with equality only in the degenerate
> case where all values agree perfectly.**

So soundness does **not** require computing a spectral radius per value set. It follows from two
schema-enforceable constraints:

- **coefficients ∈ [−1, 1]** — schema range check
- **zero diagonal** — validator

Verified across N = 3, 5, 7, 12, 20 at the worst case (all off-diagonal +1): gain = 1.000 exactly
at the bound, never above.

**The spectral radius is therefore a diagnostic, not a gate.** Compute it and **warn as gain → 1**,
because that means the basis is degenerate — the values are not independent concerns, they are
restatements of one concern. That is a genuinely useful check on a consumer-authored basis, and it
is cheap.

**Second-order is not adopted.** The published article claims second-order values come from
"multiplying the first-order impact matrix with itself." **Tested and false** — `M×M` mismatches
49/49 cells; six hypotheses all rejected (best fit `1.75×M` still wrong in 32/49); the published
normalisation is not `raw/max|raw|` either. The second-order matrix is therefore **independently
authored judgement**, not a computed ripple, so it would need its own provenance and cannot inherit
the first-order matrix's. **Use first-order only** — which the in-repo tactic already calls "the
standard path", now for a measured reason rather than a preference.

## 6. The design

### 6.1 `FoundationalValues` — a repository-backed artefact, not an enum

Every enum in this codebase is a closed `StrEnum` with drift-guard tests, so a consumer-replaceable
set cannot be one. But the extensibility wanted **already exists**: the built-in → org → project
three-tier repository layering in `src/doctrine/base.py`. And `Role` in
`src/doctrine/agent_profiles/profile.py` is already a proven, lint-clean, Pydantic-wired *half-open
value object* — copy it rather than invent a pattern.

Openness then lives in a **substitutable artefact**, and the validation target is *the active value
set*, not a module literal.

```yaml
# src/doctrine/values/built-in/ammerse.value-set.yaml
value_set_id: ammerse
name: AMMERSE
attribution: >          # REQUIRED, non-empty — see §11
  AMMERSE value system by J.B. Crossland. Used with the author's authorization.
  AMMERSE, AMMERSE Method, AMMERSE Theory and AMMERSE Value System are trademarks
  of J.B. Crossland. Accreditation, not a license of the consultancy framework.
source:
  url: https://patterns.sddevelopment.be/practices/ammerse_impact_analysis/
  accessed_on: "2026-07-26"
values:
  - id: agile
    name: Agile
    kind: lever            # see §6.2
    description: The ability to adapt quickly to changes, incorporate feedback, and
      maintain flexibility in processes and decision-making.
  # ... N − 1 more
connascence:               # N×N, zero diagonal, symmetric, coefficients in [-1,1]
  matrix_id: ammerse-first-order
  matrix_version: "1.0"
  pairs:                   # N(N-1)/2 unique unordered pairs, not N² cells
    - [agile, minimal, -0.5]
    - [agile, maintainable, 0.25]
    # ...
```

⚠️ **Do not expose the value-set repository as a `DoctrineService` property.** An architectural
test introspects every `@property` on `DoctrineService` and demands matching `selected_<kind>` and
`required_<kind>` config fields — a property silently converts a two-file change into a three-way
lockstep across two packages. Use a named accessor: `resolve_active_value_set()`.

### 6.2 Type the axes — levers vs goals

The in-repo causal-map template already types nodes **Practice / Outcome / Risk**. That distinction
resolves a real defect: across 36 authored vectors, `solvable` and `environmental` are **never
negative**. That is not two dead axes — it is the basis **conflating levers with goals**. Goal
variables sit at the end of causal chains, so nothing pushes them down.

Each value therefore carries `kind: lever | goal`. A creed weighting over goals means something
different from a weighting over levers, and a consumer-authored basis should be forced to say which
is which.

### 6.3 Two fields, two types

| | `value_impact` | `value_bias` |
|---|---|---|
| Semantics | Δ from *not adopting* | weight — "how much we care" |
| Arithmetic | **summable** | **not summable** |
| Side of `bias · deltas` | right | left |
| Carried by | directive, tactic, styleguide, procedure | **creed**, agent_profile, paradigm |

Distinct Pydantic types (`ValueImpact` vs `ValueWeighting`), **not** one model with a `mode`
discriminator, so the type system structurally prevents dotting a profile with a directive. The
**creed's own field is `value_bias`** — the creed is the project's profile. `paradigm` sits on the
bias side too: a worldview *is* a stance, not a Δ-from-baseline.

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
`mode="before"` validator that **rejects non-`str` raw input**, because `Decimal(float)` is lossy
and an unquoted `delta: 0.9` (which ruamel yields as `float`) must be a hard error. This round-trips
the corpus byte-identically, permits exact arithmetic, and needs no comparison epsilon. **Do not
enforce a resolution grid** — the corpus authors `0.125`.

### 6.4 Which kinds carry a value field

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
`template`, `asset`, `anti_pattern` (align with `_NON_AUGMENTATION_ELIGIBLE_KINDS`).

`anti_pattern` is *structurally* incapable: its nodes hold only `urn`/`kind`/`label`/`tags`, so
there is nowhere for the mandatory rationale. A negative-only vector is its natural form — which is
exactly why it must be **derived** as the sign-flip of whatever `rejects` it, never authored.

> ⚠️ **Open (§12, D-1):** two lenses disagreed on `toolguide` and `agent_profile`. Adjudicated
> above on semantics, but it is a judgement, not a measurement. Settle it before any WP touches the
> model/schema files.

### 6.5 `impacts` subsumes `in_tension_with`

**Operator ruling, settled:** `impacts: -1` *is* what "is antagonistic towards" means. A generic
signed-strength edge does not contradict the specific verbiage — `in_tension_with` is the special
case of a negative `impacts`. The earlier "keep them separate" position is **withdrawn**; keeping
both would be maintaining two authorities for one concept, which the charter's canonical-source
principle forbids.

`DRGEdge` already carries optional `when` and `reason`, so the annotation is a sibling of existing
fields. The candidate-pair predicate becomes `relation == impacts and impacts < 0` — **strict sign,
no tunable threshold**, because a threshold would reintroduce exactly the overlap that killed
derivation (genuine tensions scored 4–6, unrelated pairs 2–4, overlapping at 4).

**This introduces no false positives, because every edge is authored.** The 5/5 false-positive
result measured *derivation* from value vectors; authorship is a different mechanism.

`reconciles_tension` **survives** and re-points at negative-`impacts` pairs — the lifecycle half
must not be orphaned.

**This requires a superseding ADR** for `2026-07-21-1`. That is an accepted cost, not an objection.
The ADR must also settle the one question that cannot be discovered during implementation:

> ⚠️ **Open (§12, D-2), and it is the program-shape gate:** *which relation carries `impacts` once
> `in_tension_with` retires?* A new `Relation.IMPACTS` member, or retain the relation name and
> retire only the lifecycle? The answer swings the migration between ~45–60 files and ~5–10.

### 6.6 The composition invariant, enforced structurally

Every doctrine and charter writer in this repo serialises through `model_dump()`. So:

> Make the computed projection a **frozen dataclass with no `model_dump()`**, in a module no writer
> imports, carrying a mandatory `matrix_id` / `matrix_version` stamp.

A projection that cannot produce a `model_dump()` **can never be written back** — by anyone,
including a future agent who never read this document. That closes the worst failure mode (computed
ripple laundered into an authored assessment, then re-composed against itself) by construction
rather than by a discipline reminder.

### 6.7 The creed, and where it lives

The creed is **project-specific data**, so it lives on the **charter**, not in the reusable doctrine
library. It carries `value_set: <id>` — a pointer, not inline axis names — plus N weights each with
a rationale.

Two seams that are not where they look:

- **`CharterYaml` is `frozen=True, extra="forbid"`, but in production it is only ever
  *constructed*** — every production reader goes through raw ruamel, and `model_validate` against
  the on-disk document appears only in tests. A `creed:` block on disk would be **silently
  unvalidated**. Add an explicit per-section `CreedConfig.model_validate(...)` at the sync seam.
- **`load_creed_config` must be three-state** — `absent` / `partial` / `complete` — with `absent`
  surfacing as a **consistency-check finding**, not a `logger.info`. The canonical section-loader
  treats an absent section as "empty config" with an info log, and that is precisely the decay shape
  that kept a register inert for 162 days behind green tests.

## 7. The prose layer — ships first, gates on nothing

Independent of every gate below, and it survived all four adversarial lenses:

1. **A `costs:` sentence** on the `value_impact` kinds — what adopting this makes worse.
2. **An operator-authored charter statement** naming what the project deprioritises. Human-authored,
   not agent-drafted: an agent drafting the operator's values is the self-scoring failure.
3. **The sign-vs-rationale-polarity lint** — flag any cell whose rationale names only a cost while
   `delta ≥ 0`. **The only component of this design with a validation set available today.**

**The floor that makes "good enough" actually good enough:**

> **Never render a number without its rationale, and treat the rationale as authoritative where
> they disagree.** The corpus shows the prose is right when the number is wrong.

## 8. The feedback gap — and the one thing that closes it

The neural-network analogy holds for its conclusion ("individual weights need not be right") but is
missing the property that makes it true: NN weights tolerate individual meaninglessness because of a
**loss signal**, **gradient updates rather than authoring**, and **redundancy**. This design has
none — authored once, no loss, one number per axis per artefact.

Without a correction mechanism an authored weight set does not converge; it simply *is*, carrying
its author's bias. **That gap is cheap to close, and closing it is what makes the analogy real:**

> **Override events are the available gradient.** A deviation ledger recording
> *(suggestion, override, reason)* turns a static authored matrix into something correctable.

Recommended as the design's own next iteration, not as a precondition.

## 9. Measured grounding

### 9.1 What failed measurement — do not rebuild these

| Mechanism | Result |
|---|---|
| Deriving a **precedence ordering** from value vectors | **0 reproductions of 6**; four distinct orderings; worse than chance. Failure is *categorical*: the target encodes a pipeline of operator types (generator / transformer / guard), and a scalar weighting has one output type |
| Deriving **tension edges** from sign opposition | **5/5 false positives** on deliberately unrelated pairs; opposition counts overlap genuine cases |
| Second-order matrix as `M×M` | **49/49 mismatch** |

### 9.2 What the corpus shows — 36 authored vectors, and it is a real calibration set

- **Dimensionality: 5 components for 80% of variance** (31.9 / 21.3 / 14.2 / 12.5 / 8.7 / 7.6 /
  3.9), holding at n=34 with stubs excluded. Only two pairwise correlations exceed |0.35|. **The
  seven axes carry genuine independent information.**
- **It is not slogan-shaped.** `avoid_gold_plating` extensible −0.70; `AMMERSE_impact_analysis`
  minimal −0.60 *for its own method*; `be_a_STARR_at_interviews` minimal −0.65. Specific, costly,
  unflattering self-assessments.
- **The sign channel is noisy — the one finding that bites a heuristic.** `manual_of_me` records
  minimal **+0.25** for prose reading *"decidedly not minimal"*, against `AMMERSE_impact_analysis`'s
  **−0.60** for the same claim: 0.85 apart, opposite signs. `fail_fast` records maintainable
  **+0.50** for *"long-term maintenance challenges"*. Eleven of twelve all-non-negative entries name
  explicit costs **in prose** while the number sits at or above zero. **The 35% is a measurement of
  sign-channel noise, not of authorial honesty**, and exactly one entry is a true slogan.
- **Therefore: no `minItems: 1` negative as a schema constraint.** It gates on the least reliable
  field and inverts its own outcome — it would reject eleven careful analyses and **pass** the only
  real offender. Ship it as an advisory lint.

### 9.3 The design's own self-assessment, already authored upstream

`AMMERSE_impact_analysis` scores itself **minimal −0.60** (*"introduces significant complexity and
effort, conflicting with minimalism"*) and **agile −0.35** (*"time-consuming and may hinder
agility… the potential indirect support for better decisions is not enough to offset this"*). It is
the most credible thing available and it was free.

### 9.4 Upstream discrepancies to report

- **Probable sign error:** `Maintainable → Extensible = +0.75` while `Extensible → Maintainable =
  −0.75` — the **sole asymmetry in 49 cells**, while the published second-order matrix is fully
  symmetric.
- **The derivation claim is false** (§5).

**The operator reports these, not an agent** — it is an external communication about a trademarked
work inside the accreditation relationship. Record them in-repo with a `source_digest` so a later
re-port detects an upstream fix, and **before** the matrix ships, because the symmetry validator has
to encode a decision about the asymmetric cell. Safe default: take the symmetric reading, or set the
cell to `0` and record the abstention — abstaining on 1 of 49 costs ~2% and cannot introduce a wrong
steer.

## 10. Contradiction register — this document's values win

| Claim | Superseded value | **Canonical** |
|---|---|---|
| `trade-off` / `long-term` in doctrine YAML | 0 / 0 | **35 / 15** (the original census had a regex bug) |
| All-non-negative corpus vectors | 39% (14/36) | **35% (12/34)** — two of the fourteen are stubs |
| Corpus dimensionality | "collapses to ~one axis" | **rank ≈ 5** of 7 |
| AMMERSE tactic status | "completely inert" | **charter-activated and `requires`-mandated, yet zero scores exist** |
| Paradigm instances | 14 | **13 DRG nodes** (one file sits outside `built-in/`) |
| "All paradigms are methodologies" | asserted | **overstated** — the defect is that the *schema* cannot hold a value |
| Directive ID contract | `^DIRECTIVE_\d{3}$` | **`^[A-Z][A-Z0-9_-]*$`** — the real defect is unreachability |
| `impacts` vs `in_tension_with` | keep separate | **`impacts` subsumes it** (operator ruling) |
| "It's a gain, not a correlation" | applied to everything | **matrix is symmetric ⇒ correlation-like; edges are directed ⇒ gain.** Both true, different planes |
| Convergence of the truncation | unknown, needs per-basis check | **unconditionally sound** for coefficients ∈ [−1,1] with zero diagonal |
| Field-authored-relationship ban | blocks `value_impact` | **does not apply** — the ban covers three lineage fields only |
| "3-for-3 decay is a law" | blocker | **a strong regularity, not a law** — `routing_priority` had producers and consumers from inception |

## 11. Accreditation

- **Required, non-empty `attribution` on the value-set artefact** — the single authority. Copy
  `GlossaryPack.provenance`, which is a *required* field. Everything else points here.
- **`NOTICE` at repo root** (none exists; `LICENSE` is MIT and says "Copyright GitHub, Inc.", so
  appending there would misstate who attributes what). **Verify it ships in the sdist/wheel** or the
  accreditation never reaches consumers.
- **Not a schema `$comment`** — schemas are generated, so a hand-added comment is erased. Use
  `Field(json_schema_extra=...)`.
- **Unify the two drifted definition copies first.** The template copy has lost *"impact on
  nature"*. **Accrediting a misquoted definition is worse than not accrediting.**
- **Close the AMMERSE tactic's provenance gap** — it carries no attribution at all today, and it is
  where accreditation is actually read.
- **Provenance rides existing machinery** — `import_candidates` has
  `external_references[].attribution_reason`, literally the field for this, and **zero authored
  instances**, so the corpus import is its first real producer.

## 12. Open decisions

| # | Decision | Why it matters |
|---|---|---|
| **D-1** | Value-bearing kinds: is `toolguide` in, and is `agent_profile` `value_bias` or out? | Two lenses disagreed. §6.4 adjudicates on semantics; settle before touching model/schema files |
| **D-2** | **Which relation carries `impacts` after `in_tension_with` retires?** | **The program-shape gate.** Swings the migration between ~45–60 files and ~5–10. Must be decided *inside* the ADR |
| **D-3** | Does the creed feed **arithmetic**, or does an agent read `creed.yaml` as prose context? | If prose, the ranking function is unnecessary and the numeric layer shrinks dramatically |
| **D-4** | Interview instrument: authored question bank + forced-choice, or model-chosen questions? | Model-chosen over N virtues with no budget predictably yields a near-flat creed, which is the regime where the creed is inert. And nothing records *who supplied each weight*, so a model's prior can acquire operator provenance |
| **D-5** | Mandatory `rationale`: advisory or hard? | The calibration corpus fails it (≥3 of 38) |
| **D-6** | The asymmetric matrix cell (§9.4) | The symmetry validator cannot be written without it |

## 13. Sequence

See **[`manifesto-program-delivery-sequence.md`](manifesto-program-delivery-sequence.md)** for the
executable plan: critical path with gate positions, 22 increments ranked by evidence-per-cost, the
ADR scope, tracker shape, park register, and effort envelope.

**Ships first (campsite band, gates on nothing):** the zero-producer lint, the polarity lint,
`generate_schemas --check` in CI, and the AMMERSE definition unification.

## 14. Method limits

Nothing was executed — every "breaks silently" claim is a static read of source and test bodies.
Sixteen profile-loaded agents contributed across four squads, all read-only. The corpus sampling for
the sign-channel finding was 14 of 38 files plus 3 controls, so it establishes that inconsistency
exists at ±0.85 for equivalent prose but does **not** characterise its distribution; a coherent
constant shift, under which sign is meaningless but *ordering* survives, was not ruled out. The
ranking measurement assumed a linear dot product because D-3 is unresolved. Artefact counts (260
behavioural artefacts, 774 edges, ~310 DRG nodes) are greps, directionally right and unaudited. The
`#2538` rig's liveness is unverified by anyone, and the experiment gate decays with it.
