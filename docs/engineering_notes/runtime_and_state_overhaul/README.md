# Runtime & State Overhaul — Engineering Notes

**Status:** Grounding phase (design not yet decided)
**Owner:** Architecture (Architect Alphonso persona) + Stijn Dejongh
**Anchor issue:** [Priivacy-ai/spec-kitty#1619](https://github.com/Priivacy-ai/spec-kitty/issues/1619) — *Epic: Unify mission execution context across coord/main/lane topology*
**Started:** 2026-06-03

---

## Why this directory exists

Spec Kitty keeps shipping point-fixes for the same structural failure class: command surfaces
independently re-derive *where* mission state lives, *which* branch is authoritative, and *what*
the agent should be told — so reads, writes, and prompts disagree. PR #1627 closed four concrete
child bugs (#1615–#1618) but the **parent epic #1619 stays open for the structural fix**: one
canonical execution-context authority resolved once and threaded through every surface.

These notes are the **grounding layer** for co-authoring that to-be design. They capture the
problem, the current code, the architectural intent, and the governing doctrine *before* we commit
to a design, so the design conversation is anchored in evidence rather than memory.

> **This is not a decision record yet.** No design option is selected here. The final document
> (`06`) proposes candidate domains/splits and frames the open design questions we will resolve
> together. ADRs follow once we choose.

## Reading order

| # | Document | Purpose |
|---|----------|---------|
| 00 | [README.md](./README.md) | This index |
| 01 | [01-ticket-capture.md](./01-ticket-capture.md) | Failure modes, evidence, and suggested implementations from #1619 + children (#1615–#1618) + related (#1602, #1348) + the #1627 fix |
| 02 | [02-current-state-map.md](./02-current-state-map.md) | How the codebase derives "mission execution context" today, per surface, with the post-#1627 residue |
| 03 | [03-architecture-context.md](./03-architecture-context.md) | 3.x architectural intent (ADRs), the 2026-05-25 deep-dive review, and the CAACS audits |
| 04 | [04-doctrine-constraints.md](./04-doctrine-constraints.md) | The binding DDD doctrine (DIRECTIVE_001/031/032, paradigms, tactics) that constrains any domain split |
| 05 | [05-architectural-synthesis.md](./05-architectural-synthesis.md) | Aggregated architectural reading: root cause, forces, invariants the design must satisfy |
| 06 | [06-proposed-domains-and-splits.md](./06-proposed-domains-and-splits.md) | Proposed bounded contexts / domain split + the open design questions for our session |
| 07 | [07-existing-pattern-and-domain-extraction.md](./07-existing-pattern-and-domain-extraction.md) | The existing doctrine/charter infra-context pattern to mirror; the `OperationalContext` naming collision; MissionStatus aggregate + MissionFlow FSM extraction assessments (refines `06` §2/§6) |
| 08 | [08-architecture-phase-1-summary.md](./08-architecture-phase-1-summary.md) | **Phase 1 checkpoint** — standalone summary of problem, findings, invariants, decided vs open |
| 09 | [09-context-decomposition-model.md](./09-context-decomposition-model.md) | **Phase 2** — the conceptual model: Context as composition of domain-owned fragments (infra/filesystem/VC/preferences/state) → fit-for-purpose composites |
| 10 | [10-context-needs-capture.md](./10-context-needs-capture.md) | **Phase 2 requirements** — what each actor (code/user/agent) must know at each lifecycle step, across the six dimensions. Lens 1 = intuition; lens 2/3 corroboration in `11` |
| 11 | [11-dialectic-and-revised-claims.md](./11-dialectic-and-revised-claims.md) | **Dialectic** — corroborate-vs-refute pass on our claims. Key correction: harden the existing `ActionContext` (ADR 2026-03-09-1), don't greenfield; policy frozen-at-plan; behaviour single-owner; phase derived-not-added |
| 12 | [12-actor-mental-model.md](./12-actor-mental-model.md) | **Abstraction level up** — the actor mental model: human / LLM / external system × {sense of self, purpose, environment} mapped to AgentProfile, Constitution/Charter, MissionRun, Context |
| — | [SESSION-RECAP.md](./SESSION-RECAP.md) | Narrative of how this thinking unfolded — for contributors joining the thread |

## Source provenance

- Ticket bodies and comments fetched from `Priivacy-ai/spec-kitty` issues #1619, #1615, #1616, #1617, #1618, #1602, #1348, and PR #1627 on 2026-06-03.
- Code citations against working tree at the rc35 development checkout (commit context: `main` @ `48a687db3`).
- Architecture digest from `architecture/3.x/adr/*` + `docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md` + `architecture/audits/2026-05-*caacs*`.
- Doctrine digest from `src/doctrine/{directives,paradigms,tactics,styleguides}/built-in/*`.

All `path:line` citations are point-in-time; verify before acting on any single line.
