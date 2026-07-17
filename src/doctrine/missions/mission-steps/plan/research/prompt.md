---
description: Gather the decision inputs the plan step needs to decompose and decide
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<plan>/`). Never refer to a folder by name alone.

**In repos with multiple missions, always pass `--mission <handle>` to every spec-kitty command.** The `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the ULID), or `mission_slug`. The resolver disambiguates by `mission_id` and returns a structured `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity — there is no silent fallback.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## What This Step Is

This step gathers the **decision inputs** the `plan` step needs to
decompose the problem and commit to trade-offs with confidence. It answers
the open questions the `specify` step raised. It is evidence-gathering for
a decision, not technical feasibility research for a build — do not drift
into library choices, framework comparisons, or API design; that belongs to
a downstream software-dev mission.

## What to Do

1. **Work the open-questions list from the specification.** For each open
   question left by `specify`, identify what evidence would resolve it —
   prior decisions, precedent elsewhere in the organization, stakeholder
   input, data, or documented constraints — and go get it.

2. **Apply the Deepening Opportunity Assessment lens where structure is in
   question.** When the problem looks like a shallow cluster that could be
   consolidated, name the real friction (not abstract cleanliness): where
   does understanding or changing one concept currently require bouncing
   between many small pieces or coordinating edits across owners? Use the
   deletion test — if removing a piece makes the friction disappear, it was
   a pass-through; if the same coordination cost reappears elsewhere, the
   cluster is earning its keep and should stay separate, or be deepened
   rather than split further.

3. **Apply Bounded Context Identification where vocabulary diverges.**
   Listen for the same term meaning different things to different
   stakeholders (polysemy) or different terms describing the same thing
   (synonymy) — both are boundary signals. Record where a single
   consistent model applies and where it does not; this shapes how the
   `plan` step clusters sub-problems.

4. **Collect precedent.** Note prior decisions (ADRs, past plans, standing
   policy) that constrain or inform this one. Flag any conflict between
   this plan's likely direction and an established decision — surface it
   now rather than letting the `plan` step discover it mid-decomposition.

5. **Log evidence with sources.** Every claim that will inform a `plan`-step
   decision needs a traceable source: a document, a person consulted, a
   data point, a prior ADR. Unsourced assumptions must be labeled as
   assumptions, not facts.

## Deliverable

A research document that: resolves (or explicitly fails to resolve, with
reasons) every open question from the specification; records vocabulary
and boundary findings from the Bounded Context lens; records structural
friction findings from the Deepening Opportunity Assessment lens; and lists
precedent and evidence sources for each finding.

## Success Criteria

- Every open question from `specify` has a resolution or an explicit
  "still open" with a reason.
- Findings are traceable to a source, not asserted from memory.
- No technical build-feasibility content has crept in — this remains
  decision-input research, not implementation research.
