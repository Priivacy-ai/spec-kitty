# Acceptance

You are entering the terminal **accept** step. The `publish` step produced
`release.md` and emitted the publication-ready handoff. No agent profile
is bound to this step; acceptance is performed by the operator (or by
automation acting on operator authority).

## Objective

Validate that the documentation mission produced a coherent, defensible
body of work and is ready to be marked complete.

## Acceptance Checklist

Confirm each of the following before marking the mission `done`:

- [ ] `spec.md` names a clear documentation brief, audience, and
  iteration mode.
- [ ] `gap-analysis.md` documents the coverage matrix and prioritized
  gaps for the iteration mode.
- [ ] `plan.md` records Divio assignments, generator choices, and
  navigation hierarchy for every HIGH-priority gap.
- [ ] The documentation tree under `docs/` contains every artifact named
  in `plan.md` at its declared path.
- [ ] `audit-report.md` records a pass verdict for every quality gate, or
  explicit operator-approved deferrals for any failures.
- [ ] `release.md` declares "ready to publish" and names the post-publish
  maintainer.

## Definition of Done

When every checkbox is satisfied, advance the mission to `done`. The
mission state machine treats `accept` as terminal; no further steps will
be dispatched by composition.
