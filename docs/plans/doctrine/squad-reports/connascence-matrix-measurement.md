---
title: Connascence-matrix measurement
description: "Measured analysis of the AMMERSE first- and second-order impact matrices: spectral radius, truncation soundness, the false derivation claim, and the one asymmetric cell."
doc_status: draft
updated: '2026-07-26'
related:
- docs/plans/doctrine/foundational-values-and-creed.md
---
# Connascence-matrix analysis — measured 2026-07-26

Source: `https://patterns.sddevelopment.be/practices/ammerse_impact_analysis/`.
Coefficients now available (previously not in-repo). All results computed, not asserted.

## 1. The truncation is SOUND — the design's central maths question is answered favourably

First-order matrix `M` (7×7, rows = impacting value, cols = impacted).

- **Dominant |eigenvalue| λ = 2.3350** (power iteration, 3000 iters)
- Max abs row sum (upper bound) = 4.0000
- AMMERSE applies **divisor 6** in the formula
- **Effective per-step gain λ/6 = 0.3892 < 1** ⇒ the Neumann series converges
- **Truncation error after two terms is governed by (λ/6)³ ≈ 0.0589 (~6%)**

> `base + 0.5×first_order + 0.25×second_order` is a legitimate limited-horizon truncation with
> ~6% residual. "Good enough for government work" is **quantitatively defensible here.** This
> retires the convergence objection.

## 2. The second-order matrix is NOT derivable from the first-order one

The article states second-order values are obtained *"by multiplying the first-order impact
matrix with itself."* **Tested and false.** Hypotheses tried, mismatches out of 49 cells:

| Hypothesis | Mismatches |
|---|---|
| `M×M` (as published claim) | **49/49** |
| `M×M` with diagonal zeroed | 42/49 |
| indirect paths only, `Σ_{k≠i,j} M[i][k]·M[k][j]` | 42/49 |
| `M + 0.5·(M×M)`, diagonal zeroed | 40/49 |
| `1.75 × M` | 32/49 (best fit, still wrong) |
| first-order with diagonal zeroed | 42/49 |

The published normalisation is also not `raw / max|raw|`: for the Agile row that gives
`[0, −0.58, 0.29, 0.12, −0.88, 0.58, 0.50]` against the published
`[0, −0.69, 0.25, 0.05, −1.00, 0.82, 0.56]`.

**Consequence:** the second-order matrix is **independently authored judgement**, not a computed
ripple. Two design implications:

1. The `0.25 × second_order` term is a **second independent input**, so it needs its own
   provenance record — it cannot inherit the first-order matrix's.
2. The composition invariant ("authored `delta` is the only persistable term; the matrix supplies
   derived ripple") holds for first-order and **does not hold** for second-order.

**Recommendation: use first-order only.** The existing in-repo tactic already calls first-order
"the standard path" and second-order "high-stakes only". That guidance is now backed by a
measurement rather than a preference — and first-order alone carries the sound λ/6 = 0.389 gain.

## 3. One probable typo in the published first-order matrix

The first-order matrix is symmetric in **48 of 49** cells. The single exception:

- `Maintainable → Extensible = +0.75`
- `Extensible → Maintainable = −0.75`

The published *second-order* matrix is **fully symmetric (0 asymmetric pairs)**. Given the
surrounding symmetry, this is very likely a sign error worth reporting upstream. It matters
because it is the one cell that would make the matrix directional, and any consumer must decide
which sign to trust.

## 4. The matrix is symmetric — which vindicates the "correlation" framing *for the matrix*

An earlier review argued the authored number is a **gain**, not a correlation, because
correlation is symmetric while causal links are directed. Measured: the connascence matrix **is
symmetric** (48/49, see §3), i.e. correlation-shaped, not gain-shaped.

So both framings are right, in different places:

| Artefact | Shape | Right name |
|---|---|---|
| **Value↔value connascence matrix** | symmetric | **correlation-like** — the operator's framing is correct here |
| **Node→node `impacts` edge** | directed | **gain / elasticity** — directed, so not a correlation |
| **Artefact→value `delta`** | directed, intervention effect | **effect of adopting**, neither of the above |

The earlier "it's a gain not a correlation" correction applies to the **edges**, not to the
matrix. Withdraw it for the matrix.
