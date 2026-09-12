# Plan: [PLAN TITLE]

**Branch**: `[plan-slug]` | **Date**: [DATE] | **Spec**: `[link to plan-spec-skeleton output]`
**Input**: Plan specification + `research.md` from the `research` step.

**Note**: This document is filled in by the `plan` step. It is the
decomposition-and-decision artifact for a plan mission — there is
deliberately no code, API, or implementation-detail section here; that
belongs to a downstream software-dev mission if and when this plan is
executed.

## Summary

[One paragraph: what is being decided/sequenced, and the recommended
direction, extracted from the spec and research inputs.]

## Problem Decomposition

<!--
  Apply the Problem Decomposition tactic: break the problem into smaller,
  independently tractable sub-problems before committing to a sequence.
  Group related sub-problems into bounded work clusters; note where a
  cluster crosses a bounded-context boundary (different vocabulary,
  different owners) and should stay decoupled rather than merged.
-->

| # | Sub-problem | Cluster / bounded context | Depends on |
|---|-------------|----------------------------|------------|
| SP-1 | [Sub-problem statement] | [Cluster name] | [SP-# or none] |
| SP-2 | [Sub-problem statement] | [Cluster name] | [SP-# or none] |

## Scope — MoSCoW

<!-- Apply the MoSCoW Scoping Lens to bound what this plan commits to. -->

- **Must**: [Without this, the plan fails its purpose]
- **Should**: [Important, painful to omit, but not fatal if deferred]
- **Could**: [Desirable, included only if Must/Should leave room]
- **Won't (this cut)**: [Explicitly deferred — may return in a later cut]

## Sequencing & Prioritisation

<!--
  Apply Eisenhower Prioritisation to order the Must/Should sub-problems:
  rate each by importance and urgency, then sequence accordingly.
-->

| Order | Sub-problem | Importance | Urgency | Rationale |
|-------|-------------|------------|---------|-----------|
| 1 | [SP-#] | [High/Low] | [High/Low] | [Why it goes first] |
| 2 | [SP-#] | [High/Low] | [High/Low] | [Why it goes next] |

## Decisions

<!--
  Apply the ADR Drafting Workflow for every material trade-off surfaced
  during decomposition. One entry per decision; keep the Decision section
  under ~120 words. Record rejected alternatives with a one-sentence
  rejection rationale each — decisions without alternatives are not
  traceable (Traceable Decisions tactic).
-->

### Decision D-1: [Decision title]

- **Context**: [Problem, drivers, constraints forcing this decision now]
- **Decision**: [Chosen option, stated plainly]
- **Rationale**: [Why this option wins]
- **Alternatives considered**:
  - [Alternative A] — rejected because [reason]
  - [Alternative B] — rejected because [reason]
- **Consequences**: [Accepted trade-offs, positive and negative]

## Risks — Premortem

<!--
  Apply Premortem Risk Identification: assume this plan has already failed
  and work backward to the causes. Rate impact/likelihood, then carry the
  top risks forward with mitigations.
-->

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [Failure scenario] | [High/Med/Low] | [High/Med/Low] | [Mitigation or accepted risk] |

## Handoff

<!-- What the `review` step needs to validate, and what happens after
     approval (e.g., spin off a software-dev mission per Must sub-problem). -->

- [Downstream action 1]
- [Downstream action 2]

## Open Questions Carried Forward

- [ ] [Anything still unresolved after decomposition and decision-making]
