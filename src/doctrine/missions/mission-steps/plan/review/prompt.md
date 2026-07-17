---
description: Validate the decomposition and decisions before the plan is approved
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<plan>/`). Never refer to a folder by name alone.

**In repos with multiple missions, always pass `--mission <handle>` to every spec-kitty command.** The `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the ULID), or `mission_slug`. The resolver disambiguates by `mission_id` and returns a structured `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity — there is no silent fallback.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## What This Step Is

This is the terminal validation step of the plan mission. You are not
re-doing the decomposition or re-deciding the trade-offs — you are checking
that the specification, research, and plan artifacts are internally
consistent, that every decision is actually traceable, and that the plan is
fit to hand off. This step does not evaluate code or implementation
quality; there is none to evaluate at this altitude.

## What to Do

1. **Trace specification to decomposition.** Confirm every Must/Should goal
   from the specification maps to at least one sub-problem in the plan's
   decomposition. A goal with no corresponding sub-problem is a gap; flag
   it rather than silently accepting the plan.

2. **Trace research to decisions.** For each decision in the plan, confirm
   its Context section is actually grounded in a finding from the research
   step (not asserted from nowhere). A decision resting on an unsourced
   assumption should be flagged back for either sourcing or explicit
   labeling as an assumption.

3. **Validate every decision has real alternatives.** Reject any decision
   entry whose Alternatives list is empty or contains only strawman options
   — a decision without a genuinely considered alternative is not
   traceable per the ADR Drafting Workflow / Traceable Decisions standard
   this mission type applies.

4. **Check MoSCoW and sequencing coherence.** Confirm the Must set alone is
   viable (the plan does not silently depend on a Should or Could to
   function), and that the Eisenhower-prioritised sequence does not put a
   dependent sub-problem ahead of what it depends on.

5. **Re-run the premortem lens as a check, not a fresh brainstorm.** Ask: do
   the recorded risks plausibly cover the failure modes visible from the
   finished plan? If an obvious failure mode is missing (e.g., a
   dependency on a stakeholder who was never actually consulted), add it
   before approval rather than let it surface later as a surprise.

6. **Confirm no code/API content has crept in.** A plan mission's artifacts
   stay at the decomposition-and-decision altitude. If any section reads
   like an implementation plan (data models, API contracts, code
   structure), it does not belong here — recommend spinning it into a
   software-dev mission as part of the handoff instead.

7. **Render a verdict.** State approved, needs-changes (with the specific
   gaps found), or blocked (with what is blocking and who needs to act).

## Deliverable

A validation record covering: specification-to-decomposition traceability,
research-to-decision traceability, decision-alternatives completeness,
MoSCoW/sequencing coherence, premortem adequacy, a code/API-content check,
and the final verdict.

## Success Criteria

- Every goal traces to a sub-problem; every decision traces to research.
- No decision is approved with an empty or strawman alternatives list.
- The verdict is unambiguous and, if not "approved", names concretely what
  must change before it can be.
