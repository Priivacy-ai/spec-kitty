# Acceptance

You are entering the terminal **accept** step. The `output` step produced
`report.md` and emitted the `publication_approved` gate event. No
agent-profile is bound to this step; acceptance is performed by the
operator (or by automation acting on operator authority).

## Objective

Validate that the research mission produced a coherent, defensible body of
work and is ready to be marked complete.

## Acceptance Checklist

Confirm each of the following before marking the mission `done`:

- [ ] `spec.md` names a clear research question and scope.
- [ ] `plan.md` documents methodology, source strategy, and reproducibility
  plan.
- [ ] `source-register.csv` carries at least three high-quality, properly
  cited sources.
- [ ] `findings.md` traces every conclusion to one or more source rows.
- [ ] `report.md` is publication-ready and the publication-approval gate
  has been emitted.
- [ ] No outstanding `Open Questions` remain in `spec.md` without a resolved
  owner or explicit deferral note.

## Definition of Done

When every checkbox is satisfied, advance the mission to `done`. The mission
state machine treats `accept` as terminal; no further steps will be
dispatched by composition.
