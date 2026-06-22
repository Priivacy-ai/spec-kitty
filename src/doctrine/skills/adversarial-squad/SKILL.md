---
name: adversarial-squad
description: >-
  Deploy a bounded, profile-loaded adversarial review squad at an SDD point-cut
  (post-spec, post-plan, post-tasks, pre-merge, or an ad-hoc decision) so independent
  doctrine lenses converge on findings one reviewer would miss.
  Triggers: "deploy a squad", "adversarial squad", "post-tasks anti-laziness pass",
  "pre-spec investigation squad", "brownfield check", "second opinion on this design",
  "review squad", "run a multi-lens review".
  Does NOT handle: the implement-review loop (use spec-kitty-implement-review),
  spec/plan/tasks generation, or direct code editing by the orchestrator. It is an
  optional, charter/memory-activated enrichment — it never gates a mission.
---

# Adversarial Squad Deployment (harness)

The operational **HOW**. The doctrinal **WHEN/WHY** is the procedure
`adversarial-squad-deployment` (`src/doctrine/procedures/built-in/adversarial-squad-deployment.procedure.yaml`),
which sits under the `brownfield-onboarding` paradigm. This skill changes **no** mission
type or guard; it is a technique the orchestrator opts into.

## When to use

A squad is worth its tokens at a high-leverage point-cut where one reviewer's blind spot
is expensive:

- **after `/spec-kitty.specify`** → pre-spec investigation (scope, prior art, live repros)
- **after `/spec-kitty.plan`** → post-planning brownfield check (foldable issues, split-brain, deprecations)
- **after `/spec-kitty.tasks`** → post-tasks anti-laziness pass (fakeable DoDs, decomposition realism)
- **before merge** → architectural-gate / cross-base sweep
- **ad-hoc decision** → proponent + adversaries + synthesizer (e.g. delete-vs-migrate)

Do NOT use it as a rubber stamp, and do NOT wire it as a mandatory gate.

## The recipe

1. **Frame one sharp question** and pick the point-cut. A squad answers a question; it is
   not a vibe check.
2. **Select 3–4 distinct profiles by lens** (bounded). Complementary, not redundant:
   - `architect-alphonso` — structure / seams / topology
   - `debugger-debbie` — live-evidence, coverage, "would this catch the regression?"
   - `reviewer-renata` — anti-laziness, contract-vs-implementation, fakeable assertions
   - `randy-reducer` — duplication / dead code (⚠ duct-tape bias — read critically)
   - `paula-patterns` — decomposition, boundaries, second-opinion adjudication
   - `planner-priti` — scope, sequencing, tracker hygiene
   - `python-pedro` — implementer feasibility
   - `doctrine-daphne` — doctrine integrity / DRG wiring
   Scale past 4 only for an explicit "audit / comprehensive" ask.
3. **Dispatch in parallel, profile-LOADED.** Each delegate's prompt MUST begin with:
   *"FIRST read `src/doctrine/agent_profiles/built-in/<id>.agent.yaml` and adopt its
   directives/tactics; state which you applied."* Loading the profile — not naming a
   persona — is the point. Keep delegates read-only unless the task is an isolated
   implementation in its own worktree.
4. **Require structured, non-fakeable output.** Each returns findings as
   `[SEVERITY] file:line — issue — recommendation`, ending in a verdict, grounded in cited
   evidence, with honest concession of where its lens does not apply. A steelman that
   over-claims is weak; an adversary that concedes nothing is noise.
5. **Match model tier to difficulty.** Strong tier for analytical/adversarial lenses;
   lighter tier for mechanical/tracker delegates.
6. **Synthesize; second-opinion on divergence.** Aggregate. Where delegates disagree on a
   consequential point, do NOT average — adjudicate from the source, or dispatch one focused
   second-opinion delegate. Be critical of any delegate with a known bias. If irreconcilable,
   escalate to the human with both positions.
7. **Record the convergent evidence and act.** Capture confirmed findings (artifact,
   findings doc, or memory). The value is convergent evidence that survived independent
   scrutiny — not a single opinion.

## Invocation

Invoke by name (`adversarial-squad`) with the point-cut + question, e.g.
*"adversarial-squad: post-tasks anti-laziness on WP01–WP08."* This skill is the alias
surface; the doctrine procedure is the canonical record of the technique.

## Invariants

Bounded (3–4) · profile-LOADED · structured output · model discipline ·
live-evidence-grounded · second-opinion on divergence · **never a mission gate**.
