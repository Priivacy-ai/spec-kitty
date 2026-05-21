# Case Study: CLI ↔ SaaS Schema-Drift Chain (epic #1198)

The motivating incident for this skill.

## Background

Over 24 hours, `spec-kitty-cli` rc12 → rc18 unmasked a chain of
CLI ↔ SaaS schema drifts that all shared the same shape: an
`emit_*` function in the CLI constructed a payload via a
hand-rolled `dict` literal that diverged from the canonical
`spec_kitty_events.*Payload` pydantic model, and the SaaS rejected
the batch with HTTP 400.

This was the fifth recorded instance of the same drift class
(prior occurrences: #401, #1047, #1188, #1190). Four reactive
point-fixes had shipped. The chain continued. The next mask was
expected.

## The Dispatch

Five sub-agents were dispatched in parallel. Each was constrained
to one paradigm. None could communicate with the others until
synthesis.

## The Convergence

All five paradigms converged on the same structural fix: replace
hand-rolled dict literals in every `emit_*` function with
canonical pydantic-model construction, widen the strict-validate
matcher, and add a producer-conformance CI gate.

## The Unique Findings

- The Falsifier produced a catalog of falsified hypotheses (SaaS
  skipping strict for `MissionCreated`; events package and CLI on
  different versions) so they cannot be re-litigated.
- The Five-Whys Cartographer named the terminal root cause: two
  parallel emit pipelines for the same conceptual event, only one
  of which constructs payloads via the canonical pydantic model.
  Built the Pareto table proving 3 of 6 historical incidents
  trace to this single structural fork.
- The Bisector built the timeline: introducing commit `533e47d2`
  (2026-04-14) for envelope duplication; `498cf69a` (2026-05-16)
  for the lifecycle emitter born broken; SaaS-gate cutover
  `0fe3da67` (2026-05-05); decoupling moment 2026-05-16 11:19:08.
  Crucially: the events package never drifted upstream — schemas
  have been stable since 2026-04-05. Only the CLI was wrong.
- The Matrix-Maker built the full violation matrix including four
  dormant masks not yet surfaced by canary
  (`emit_wp_created` four-way drift, `emit_artifact_phase`
  Started-variant key leakage, `mission_slug`/`mission_id`
  injection in 10+ tolerant types, seven schemaless event types).
  Also proved Matrix-2 identity: events package and SaaS encode
  the same contract.
- The Stenographer discovered drift #7, a completely separate bug
  no other paradigm could have found: the CLI's `batch.py` error
  renderer reads `details[*].error` / `.reason` from SaaS failure
  responses, but the SaaS ships `details[*].detail`. The CLI
  silently threw away the entire per-event violation diversity
  for the full 24-hour investigation. Filed as #1202.

## Outcome

One structural intervention (#1200) replaces five would-be
reactive PRs. Half of historical incidents in this class trace to
the same structural fork; the structural fix closes them all.
Dormant masks are pre-emptively addressed.

## What This Skill Inherits From the Incident

- The five paradigm names (each one named for a property the
  others cannot match).
- The discipline of dispatching all five in parallel rather than
  picking one.
- The deliverable shape: structural fix plus catalog of falsified
  hypotheses plus divergence matrix plus orthogonal-bug list.
- The trigger criteria: recurrence count, reactive-PR count,
  contested ownership.
