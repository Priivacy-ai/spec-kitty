# ADR-004 — Tier 2 evidence SaaS projection stays local-only in 3.2.x

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Status**: Accepted
**Date**: 2026-04-23
**Relates to**: FR-011, SC-006, C-002, C-005
**Supersedes**: None

## Context

Phase 4 core shipped Tier 2 evidence promotion: `spec-kitty profile-invocation complete --evidence <path>` creates a local artifact under `.kittify/evidence/<invocation_id>/evidence.md` plus a `record.json`. The shipped `docs/trail-model.md` already states:

> Tier 2 evidence artifacts: Local only in 3.2. Not uploaded to SaaS.

Issue #701 asks the closeout to resolve this **decisively** — either confirm the local-only stance with named reasoning and a revisit trigger, or define a bounded SaaS projection profile (size limit, redaction rule, timing) and ship it.

The brief for this closeout mission explicitly rejects broad rewrites and prioritises decisive closeout stewardship. It does not ask for SaaS evidence projection to be designed now.

## Decision

**Tier 2 evidence remains local-only in 3.2.x.** No code change to the Tier 2 path is made by this mission. The status quo is promoted from an implicit note to a named, rationalised decision in `docs/trail-model.md` under a new subsection "Tier 2 SaaS Projection — Deferred".

## Rationale

1. **The shipped contract already reflects this.** Operators observing 3.2.0a5 see local-only evidence today; this decision confirms that observation, removing ambiguity from the doc without changing behaviour.
2. **SaaS projection of evidence bodies would require privacy, redaction, and size-limit design** — surface area explicitly out of scope for this closeout. Doing it half-way would introduce a bounded profile that operators would then need to audit and manage.
3. **Future projection remains possible without contract change.** If Phase 6 or 7 introduces a bounded projection profile, it can read the existing Tier 2 artifact on disk and emit its own envelope. No invocation-record field needs to be reserved now; no SaaS schema needs to be changed now.
4. **Operator expectations are already set.** The 3.2.x release line already behaves this way. Confirming it in doctrine does not surprise anyone.
5. **Local-first invariant reinforced (C-002).** Keeping Tier 2 local-only means evidence reconstruction does not depend on SaaS reachability.

## Alternatives considered

| Option | Outcome | Why rejected |
|--------|---------|--------------|
| **A. Keep local-only in 3.2.x (status quo, decisive)** | **Accepted** | See Rationale. |
| B. Ship bounded SaaS projection with size limit, redaction, and timing | Rejected for this mission | Scope exceeds "decisive closeout stewardship"; would require privacy policy work; no operator has requested it. Candidate for Phase 6+ epic if demand surfaces. |
| C. Leave the question unanswered in shipped docs | Rejected | Exactly the ambiguity #701 asks us to remove (SC-006 requires a single documented answer). |
| D. Always project evidence bodies to SaaS | Rejected | Contradicts the shipped note; would change behaviour for every operator without their consent; privacy and retention implications. |

## Consequences

- `docs/trail-model.md` gains a new subsection "Tier 2 SaaS Projection — Deferred" with:
  - The status statement (local-only in 3.2.x).
  - The reasoning above (distilled to 3–5 sentences).
  - The revisit trigger (below).
- `CHANGELOG.md` unreleased section records the deferral as part of the mission's migration note (FR-013).
- No change to `ProfileInvocationExecutor.complete_invocation`, `promote_to_evidence`, or `_propagate_one` beyond what ADR-001 and ADR-003 already require.
- Operators with SaaS sync enabled see no evidence-body uploads — identical behaviour to today.

## Revisit trigger

Revisit when at least one of the following is true:

- A named future mission / epic accepts "SaaS evidence projection" as its scope (Phase 6+).
- Operators actively request that evidence artifacts be viewable in the SaaS dossier. No such request observed as of 2026-04-23.
- A regulatory or audit requirement mandates centralised evidence retention.

None of these are anticipated during the 3.2.x line.

## References

- `docs/trail-model.md` — existing shipped "Local only in 3.2" note
- `src/specify_cli/invocation/executor.py::complete_invocation` — Tier 2 promotion path (unchanged)
- `src/specify_cli/invocation/record.py::promote_to_evidence` — local promotion helper
- Issue #701 — Minimal Viable Trail
- Spec FR-011, SC-006
