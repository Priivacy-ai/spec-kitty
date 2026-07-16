---
title: 'Mission-type step-model unification — retire "template" as a discriminator'
description: 'Operator proposal to reserve "template" for doctrine example-artefacts and make recursive steps the mission-type building block; assessment + grounding questions.'
doc_status: active
updated: '2026-07-16'
related:
- docs/architecture/mission-type-resolution.md
- docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md
---

# Mission-type step-model unification

> Status: **investigation / proposal** (not yet a spec or ADR). Captured on the `feat/templates-as-config`
> (#2658) branch to inform where the `template_set` seam should evolve.

## 1. The problem — "template" is an overloaded discriminator

Across the recently-merged doctrine work the word **template** names three disjoint things, and it is being
used as a *structural discriminator* for mission types where it should not be:

1. **`template_set`** (PR #2689 / #2658) — a flat per-mission-type map of semantic keys → *content-scaffold
   filenames* (`spec: spec-template.md`, `plan: plan-template.md`), resolved through the 5-tier filesystem.
2. **`template:` DRG nodes** (PR #2712 / #2680) — 16 graph-modelled *doctrine example artefacts*
   (`template:c4-context-mermaid-template`, `template:glossary-template`, …) referenced by governance; today
   edge-less.
3. **Per-step prompt/WP templates** — `task-prompt-template.md`, per-action prompts under
   `missions/<type>/templates/` — the instructions that drive an agent *through* a step.

These are different populations with different consumers. Using "template" (and `template_set`) as the thing a
mission type is *made of* conflates a content scaffold with the mission-type structure and collides nominally
with the doctrine `template:` artefact kind. (See `docs/investigation`-adjacent analysis and the
mission-type-resolution ADR §"bundle shaped to grow".)

## 2. Operator decision — the canonical vocabulary

**Reserve "template" for doctrine example-artefacts, and make *steps* the building block of mission types.**

### 2a. `template` (narrowed, canonical)
A **template** is a *doctrine artefact that is an example* — referenced *by* tactics, directives, procedures,
etc. (e.g. a C4 context diagram skeleton, a glossary example, an analysis-canvas exemplar). This is exactly the
existing `template:` DRG artefact kind (`NodeKind.TEMPLATE`). "Template" stops being a mission-type structural
term; it is one doctrine artefact kind among directive/tactic/procedure/paradigm/styleguide/toolguide/asset.

### 2b. `step` — the mission-type building block (the unification)
A **mission type is an ordered tree of steps.** Each **step** carries:

| Field | Optional? | Meaning |
|-------|-----------|---------|
| `description` | required | What the step accomplishes. |
| `recommended_role` | optional | The agent profile suited to it (e.g. `python-pedro`, `reviewer-renata`). Advisory. |
| `recommended_model_tier` | optional | The model class suited to it (e.g. `sonnet`, `opus`). Advisory. |
| `prompt` | required | A **parameterizable** prompt — the instruction that drives an agent through the step, with substitution parameters. |
| `template` | optional | A reference to a doctrine **`template:` artefact** (2a) — the example/skeleton the step's output should resemble or fill in. |
| `substeps` | optional | An ordered list of child **steps** (recursion) — a step decomposes into finer steps. |

This one structure subsumes today's scattered concepts:

- **`template_set` (flat filename map)** → becomes the `template` field of the relevant steps (the `specify`
  step's `template` = the spec skeleton; the `plan` step's `template` = the plan skeleton). No separate
  type-level template map.
- **per-step prompt/WP templates** → become each step's `prompt` (parameterizable).
- **WP-frontmatter `agent_profile` / `model`** → become `recommended_role` / `recommended_model_tier` at the
  step grain, authored in doctrine rather than emitted per-mission.
- **`action_sequence` action nodes** → *are* the top-level steps; `substeps` adds the recursion actions lack today.
- **guards** → gate steps (a future concern; no `GUARD` kind exists yet).

## 3. Why this is coherent

- **One discriminator, one vocabulary.** Mission types are made of **steps**; doctrine has example
  **templates**. The nominal collision disappears — "template" always means the artefact kind.
- **Richer + recursive.** Steps gain description/role/model-tier/prompt and, crucially, **substeps** — the
  recursion that lets a coarse step (e.g. `implement`) decompose into finer authored steps, which the current
  flat `action_sequence` cannot express.
- **Config-carried, activation-gated.** A step's `template` reference and `prompt` are doctrine the mission
  type *carries* and the charter *activates* — the same "doctrine offers / charter activates / runtime
  consumes" spine the governing ADR establishes.
- **`template_set` becomes a clean transitional subset.** #2689's flat 2-key map is exactly the `template`
  field of the `specify`/`plan` steps, expressed before the step model existed. It grows *into* this model
  additively (per the ADR's "bundle shaped to grow"), not a throwaway.

## 4. Assessment (orchestrator) — promising, with three things to resolve

**Verdict: architecturally sound and the right direction — it resolves the naming collision at the root and
gives the "steps + guards, each step a template" model a concrete shape. Three items need grounding before it
becomes a spec:**

1. **`template` (step field) vs `template:` (doctrine artefact) must be the SAME population.** The step's
   `template` should be a *reference to a `template:` DRG node*, not another loose filename — otherwise we
   re-introduce a fourth "template." That means the current `spec-template.md`/`plan-template.md` content
   scaffolds must become `template:` doctrine artefacts (minting a `template:spec-skeleton` / `template:plan-skeleton`
   node population and a `step → template` DRG edge), unifying the graph-backed and filesystem notions. This is
   the `mission_type → template` edge class #2712 explicitly *deferred* (#883) — this proposal is its
   motivation and design.
2. **Steps as a first-class recursive DRG population.** Today steps are `action:*` nodes (flat, one grain).
   `substeps` needs either a recursive `action:*/…` URN scheme or a new step model with parent/child edges, plus
   a `step → template` and (future) `step → guard` edge class. How this relates to the existing
   `MISSION_STEP_CONTRACT` NodeKind must be settled (is a step contract the typed I/O of a step in this model?).
3. **Migration + backward-compat surface.** `action_sequence`, `template_set`, action `index.yaml` files, WP
   prompt templates, and WP-frontmatter role/model are all live inputs. The proposal reframes all of them.
   Scope, sequencing, and the fail-closed/legacy paths (#2660) need a real migration plan — this is a
   multi-slice epic (#2652) effort, not a single PR.

## 5. Open questions for the design-and-code grounding squad

- **Design coherence:** does the step tree (description/role/tier/prompt/template/substeps) cleanly subsume
  `template_set` + action nodes + WP-frontmatter role/model + per-step prompts, with no orphan concept? Where
  does `MISSION_STEP_CONTRACT` fit (step I/O)? Where do guards attach (step-level, and via what kind)?
- **Code grounding:** what surfaces does this touch — `mission_types/*.yaml` schema, `action/*/index.yaml`,
  `MissionTypeRepository`, `mission_type_profiles.resolve_mission_type_context`, the DRG generator
  (`extractor.py` node/edge emission), the resolver (`resolve_configured_template`), WP generation
  (`/tasks`), and the runtime loop? Is the model expressible in the current DRG (`NodeKind`/`Relation`) or does
  it need new kinds (`STEP`? `GUARD`?) and edge classes (`step→template`, `step→substep`, `step→guard`)?
- **Conflict / continuity:** does this contradict the just-merged #2712 (mission_type→action edges) and #2689
  (`template_set`), or subsume them as first drafts? Is `action` == top-level `step` (rename), or a distinct
  kind? Confirm the recursion doesn't break the DRG acyclicity/validation invariants.
- **Realism:** is the optional role/model-tier authored-in-doctrine the right place (vs emitted per-mission at
  `/tasks`)? Does a parameterizable `prompt` at the step grain replace the WP prompt template cleanly?
- **Sizing:** is this one ADR + a multi-WP mission under #2652, or does it need to be sliced (steps-as-nodes →
  step-templates-as-edges → substeps → guards)? What is the smallest coherent first slice?

---

*Captured by the orchestrator for the operator's step-model unification proposal. Next: a design-and-code
grounding squad grounds §5 against the ADR and the live code before this becomes a spec.*
