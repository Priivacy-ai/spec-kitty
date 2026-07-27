# Mission Specification: DRG Relation — `impacts` Vocabulary

**Created**: 2026-07-26
**Status**: ⏸ **NOT YET SPECCED — deliberately.** Scope sketch only.
**Programme**: Mission **B1** of five — see the programme record [`doctrine-canonical-structure-remediation-01KYEYSD`](../doctrine-canonical-structure-remediation-01KYEYSD/spec.md).
**Order**: Second. Blocked by **A** (`doctrine-silence-guards-01KYFV7Q`). Blocks **B2**.

## Why this is a sketch and not a specification

**Operator guidance, 2026-07-26:** do not over-specify or plan any mission after phase A. The
missions run **one at a time**, and each is specced and planned only after the previous phase is
finalized.

The reason is that phase A changes the ground this mission stands on. A closes four silent-kind-drop
sites, adds `extra="forbid"` to the DRG models, replaces the field-by-field writers' failure mode,
and fixes the org→DRG bridge. What B1 costs, and which of its risks are still real, is a different
question after that lands than before it.

Writing a full requirement set now would pin assumptions that A is about to invalidate — the same
failure the programme exists to close, in the programme's own planning.

**Nothing is lost by waiting.** The measured findings, the concern map, the traps and the ordering
rationale all live in the programme record's [`spec.md`](../doctrine-canonical-structure-remediation-01KYEYSD/spec.md)
and [`plan.md`](../doctrine-canonical-structure-remediation-01KYEYSD/plan.md). Spec this mission from
those, refreshed against the post-A tree.

## Scope sketch

Deliver [ADR 2026-07-26-3](../../docs/adr/3.x/2026-07-26-3-impacts-edge-subsumes-in-tension-with.md)
(ADR-D1 through ADR-D11): replace the boolean `in_tension_with` with a directed, signed
`Relation.IMPACTS`, where `impacts < 0` **is** the tension claim on strict sign, and `impacts` is
authored-only and never derived.

- `Relation.IMPACTS` + the signed `impacts` annotation on `DRGEdge`.
- `is_symmetric: bool = False` on `DRGEdge` — shorthand for the un-written inverse, expanded **by the generator**, never in traversal.
- Retire `in_tension_with`; re-point `reconciles_tension` at negative-`impacts` pairs.
- Migrate the 2 authored tension edges (`directive.graph.yaml:90-93`, `:103-106`), preserving each `reason` verbatim.
- Update `RELATION_DESCRIPTIONS` and verbatim doc parity in the same commit.

**Measured surface** (re-derive before speccing): 21 files reference `in_tension_with` (9 `src/`,
12 `tests/`); **50 files touch the `Relation` vocabulary**; 2 authored tension edges; 0 `refines`
edges. Estimated 3–5 agent-days, ~45–60 files.

## Carried constraints — do not lose these when speccing

- **Blocked by A (C-010).** `extractor.py:133-145` (`_KIND_MAP`) and `:1210-1229` (writers) would silently delete `impacts` and `is_symmetric` at extraction and regeneration, so they would ship inert behind green tests.
- **The bridge fix must have landed** (A) or the new relation inherits a silent-drop path — ADR 2026-07-26-3, Negative consequences.
- **C-009**: model + writer + generator expansion + round-trip test + coverage gate in **one commit** per field.
- **Cache counts move, authored counts do not.** `is_symmetric` expansion takes the two claims from 2 authored to 4 cached — a ledger entry on the **cache side only**.
- **Strict sign has an operational cost**: every negative edge, however small, becomes a formal tension claim requiring reconciliation. Accepted, not overlooked.
- **The positive half has no current author** — expressiveness bought ahead of demand, and exactly what A's zero-producer lint will flag if the coverage gate is nominal rather than real.
- **Two ADRs share the `2026-07-21-1` prefix.** The superseded one is `in-tension-with-drg-edge`; the `glossary-first-order-doctrine-artefact` ADR must not be touched.
- **B1 before B2**, or the two shipped tension claims get migrated twice.
