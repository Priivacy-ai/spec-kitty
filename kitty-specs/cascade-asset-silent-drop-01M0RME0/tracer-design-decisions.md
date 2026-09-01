# Tracer — Design Decisions

**Clarifications section placement and content.** The mission brief mandated persisting the
operator's verbatim decision on diagnostic verbosity (Option A: always render one line per
dropped kind-filtered node, both render paths). Placed it as its own `## Clarifications`
section immediately after the title/status/Summary block and before User Scenarios, so a
reviewer hits the binding decision before reading requirements that depend on it, and so the
rejected Options B/C are visible and citable without re-deriving them from the readiness
probe. Quoted the operator's answer close to verbatim rather than paraphrasing, per the
mission brief's "substantially this" instruction — paraphrasing a binding decision risks
losing the exact rationale a later reviewer needs to avoid re-litigating it.

**Splitting FR-001 (collection) from FR-002/FR-005/FR-007 (per-consumer threading).** The
issue's suggested shape treats "collect the dropped nodes" and "render them in N places" as
one step. Split them in the spec because the collection happens once at the shared
`_referenced_artifacts` seam (C-002's symmetry requirement depends on this: if collection
were duplicated per-caller instead of centralized, the three consumers could drift), while
rendering happens three times (activation report, no-cascade warning, deactivation report)
with three different wording constraints (FR-005 specifically forbids reusing the
"re-run with --cascade" hint for a kind that `--cascade` can never activate). Keeping these
as separate, independently-falsifiable FRs makes the symmetry requirement checkable per-FR
rather than buried in one large requirement.

**Kind-filtered vs. scope-skipped must stay visually distinct (FR-008, Edge Case 3).** Added
this as its own requirement rather than folding it into FR-003, because the two failure modes
have different recovery stories — "out of scope" is recoverable by widening `--cascade`;
"kind not charter-activatable" is never recoverable by any `--cascade` value. Conflating the
wording would produce a new, more subtle silent-failure-adjacent defect (an operator
retrying with a wider scope for something that can never activate), which the charter's D-005
throughline treats as exactly the class of problem this mission exists to close, not
reintroduce elsewhere.

**Deactivation folded in as P2, not P1 or excluded.** ADR 2026-08-20-1's "Symmetry" section
is explicit and binding (C-002), so deactivation could not be treated as out of scope. But its
blast radius and trigger condition (`--cascade` must be explicitly supplied; no no-cascade
warning path exists on the deactivate side) are narrower than the activation-side fix, so it
is P2 rather than P1 — sequenced after the primary fix but still mandatory for the mission to
be considered complete, per C-002/NFR-003.
