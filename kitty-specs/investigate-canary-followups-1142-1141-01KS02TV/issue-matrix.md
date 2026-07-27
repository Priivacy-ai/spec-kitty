# Issue Matrix — investigate-canary-followups-1142-1141-01KS02TV

Tracks each GitHub issue this mission addresses, the verdict, and the
follow-up handle (per Gate 4 / FR-037 of the mission-review skill).

| issue | repo | title | verdict | evidence_ref |
|---|---|---|---|---|
| [#1142](https://github.com/Priivacy-ai/spec-kitty/issues/1142) | `Priivacy-ai/spec-kitty` | Canary scenarios 1+2 hit TeamSpace FORBIDDEN_KEY block even though WP01 fix verifies clean in direct repro | **deferred-with-followup** | Hypothesis 2 confirmed (WP01 predicate too narrow — see `research/h2-emitter-walk-1142.md`). Recommendation A — open a follow-up 1-WP mission to broaden `is_mission_lifecycle_row` to accept `{Project, Mission, WorkPackage, MissionDossier}` aggregate types. Comment: https://github.com/Priivacy-ai/spec-kitty/issues/1142#issuecomment-4488095110. Outcome: `research/outcome-1142.md`. Follow-up issue handle: this mission's PR description #1160 commits the operator to filing the follow-up mission upon merge. |
| [#1141](https://github.com/Priivacy-ai/spec-kitty/issues/1141) | `Priivacy-ai/spec-kitty` | Scenario 4 of identity-boundary canary tests lifecycle rollback semantics not covered by mission spec | **deferred-with-followup** | H4/H3/H2 ruled out (or partially); H1 (silent fan-out failure) LIKELY but not fully bisected — see `research/h1-evidence-1141.md`. Recommendation A — open a follow-up 1-WP mission to add a logging breadcrumb at `fire_saas_fanout` entry, a unit test for backward `in_review → planned` queue emission, and bisect from a trusted-runner workstation. Comment: https://github.com/Priivacy-ai/spec-kitty/issues/1141#issuecomment-4488224564. Outcome: `research/outcome-1141.md`. Follow-up issue handle: this mission's PR description #1160 commits the operator to filing the follow-up mission upon merge. |

## Notes on verdict semantics

Both rows carry the `deferred-with-followup` verdict because this mission's
spec (`spec.md` constraint **C-003**) explicitly forbids in-mission code
fixes. The investigation deliverables (`research/outcome-{1142,1141}.md`,
posted comments, `mission-exception.md` `## Follow-up` updates) satisfy the
operator commitments that the parent mission deferred at Gate 3.

The follow-up handle for each row is the commitment, in PR #1160's
description, that the operator will file each follow-up mission upon merge.
That commitment will materialize as a separate `kitty-specs/...-01KS...` slug
in the spec-kitty repo. Until those slugs exist, the issue handle is the
commitment text in PR #1160.

## Cross-reference

- Parent mission exception (Gate 3 origin for the canary failures):
  [`kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md`](../unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md).
- Acceptance matrix (per-FR/NFR verdicts):
  [`acceptance-matrix.json`](./acceptance-matrix.json) — all 14 criteria PASS with FR-003 marked n/a.
