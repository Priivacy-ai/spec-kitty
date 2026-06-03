# Session Recap — Runtime & State Overhaul (Architecture Phases 1–2)

**Date:** 2026-06-03 · **Participants:** Stijn Dejongh + Architect Alphonso (Claude)
**Issue:** [Priivacy-ai/spec-kitty#1619](https://github.com/Priivacy-ai/spec-kitty/issues/1619)

This is the **narrative** companion to the numbered grounding docs (`01`–`09`). It exists so a
contributor joining the thread can follow *how* we got here, not just the conclusions. If you only
read two files, read `08` (the checkpoint) and `09` (the model); this recap tells the story between them.

---

## Why we started

Spec Kitty keeps shipping point-fixes for the same kind of failure: agents manually hopping between
the main checkout, the coordination branch, and lane worktrees; dependency checks reading stale
state; `safe_commit` telling people to check out branches that fight the orchestration topology;
prompts that describe a topology the CLI no longer uses. PR #1627 closed four concrete child bugs
(#1615–#1618), but the parent epic #1619 stayed open because the *structural* cause was untouched.
Stijn framed the goal: design a to-be state that makes this whole class of problem stop recurring,
then start shifting the codebase toward it.

We did this in the architect role, treating it as a grounding-then-design exercise: gather evidence
first, commit to a design later, keep the doctrine honest throughout.

## How the investigation unfolded

**1. Capture the tickets (`01`).** We read #1619 and every linked issue (#1615–#1618, the related
#1602 and #1348, and the #1627 fix). The pattern was unmistakable across all of them: *split
authority*. Writes go to the coordination branch; many reads and all the prompts still assume the
main checkout or the target branch. Six tickets, one disease.

**2. Map the current code (`02`).** A read-only survey of how ~40 surfaces derive "where is this
mission's state." The finding that reframed everything: the `status/` domain is *already clean* and
event-sourced — the defect isn't in how state transitions, it's in how each caller independently
decides *where state lives and where commands may run*. That decision — **topology resolution** —
has no owner. Two half-resolvers already exist (`resolve_mission_read_path` for reads,
`BookkeepingTransaction` for writes) and they re-derive the same identity tuple separately, via four
duplicated path-builders.

**3. Read the architecture and the doctrine (`03`, `04`).** The 3.x ADRs already commit to a lot we
must honor: lanes own git, WPs own accounting, ULID identity, atomic WP-start as a *service*,
`approved` ≠ `done`, and — crucially — the **Mission Type / Mission / Mission Run** ontology that
tells us the new object is a *Mission Run* concern. The CAACS audits confirmed this is the repo's
densest, most complex, least-tested cluster (bus factor ≈ 1), and that the team already filed epic
#992 "centralize domain invariants." The DDD doctrine (DIRECTIVE_001/031/032) gave us hard rules:
boundaries by ubiquitous language not runtime stage, no shared mutable state across boundaries,
resolve overloaded vocabulary *before* building.

**4. Synthesize (`05`).** One sentence: *execution context is computed by every caller instead of
owned by one model, so the physical truth is reconstructed — differently — at ~40 sites, and the
gaps are the bug class.* We wrote down ten invariants (I-1…I-10) any design must satisfy, and the
list of things already-good that we must **not** break.

**5. First design pass (`06`).** Proposed a bounded-context decomposition and three design options
(value object / operation service / strangler façade), explicitly leaving the choice open.

## The two pivots that changed the design

**Pivot A — "mirror what already exists" (`07`).** Stijn's instinct was to model the new context the
way the codebase already models doctrine/charter infrastructure. Investigating that, we found the
pattern isn't just present — it's *already partly wired for this purpose*. `DoctrineService` +
`PackContext` + `ProjectContext` are the exact "roots-as-data + frozen snapshot + pure assembler +
higher-layer builder" shape. And `OperationalContext` **already exists** as a class — except it
holds *session* facts (model/profile/role), not filesystem aspects. That naming collision became a
design input, not a footnote. We also assessed the two requested extractions: **MissionStatus** is a
near-free aggregate (event-sourcing already gives us hydration + invariants), and **MissionFlow** is
~80% built as a pure FSM — but is hardcoded and identical across all mission types, so "make it
mission-type-driven" is net-new work that should be its *own* later epic, not smuggled into #1619.

**Pivot B — "context is a composition, not an object" (`09`).** Stijn's hypothesis: the flat
`MissionExecutionContext` field list is really several *domain-owned chunks* — infrastructure,
filesystem, version control, execution preferences, execution state — that should be modeled
individually and **composed** per purpose. This turned out to be the key. Classifying every field on
two axes (domain × scope) and separating primitive from derived information, the flat object
dissolves into six fragments — four of which already exist in some form. The collision from Pivot A
resolves cleanly: the existing `OperationalContext` simply *is* the execution-preferences fragment;
the filesystem concept is a *different* fragment. Composites (`ReadContext`, `WriteContext`,
`PromptContext`, …) are assembled from fragments per operation — which is how the atomicity invariant
(I-4) and prompts-from-context (I-6) become true *by construction* rather than by discipline.

## Where we are now

- **Phase 1 (grounding + reconnaissance): complete** — docs `01`–`08`.
- **Phase 2 (conceptual modeling of Context): in progress** — doc `09` proposes the fragment/composite model and shows it satisfies every doctrine constraint while reusing existing code.
- **Decided (working consensus):** a Mission-Run-scoped context family, assembled by a central
  builder under a new `mission_runtime/` umbrella; extend the existing context family (don't
  replace); split MissionFlow into extraction-now / config-driven-later; build the #1619 e2e
  regression (main+lane CWD parity) first as the migration ratchet.
- **Open (next session):** fragment naming ratification (DIRECTIVE_032), whether Infrastructure and
  the per-invocation flags are their own fragments, composite granularity, whether the
  `worktree==destination_ref` invariant becomes a `CommitTarget` type, and reconciling #1619 with epic #992.

## How to engage

- Comments/pushback most useful on `09` (the model) and the open questions in `09` §8 / `08` D1–D7.
- This is **not an ADR yet** — no code has changed. ADRs follow once we pick the design shape and
  ratify the vocabulary. Nothing here is binding; it's the reasoning trail toward a decision.
