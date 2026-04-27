# Retrospective Learning Loop

**Spec**: [`kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/spec.md`](../kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/spec.md)
**Plan**: [`kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/plan.md`](../kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/plan.md)

This page is the operator reference for the retrospective learning loop. It
explains what happens at mission terminus, how the governance gate works, how
to read cross-mission patterns, and how to apply staged proposals. Audience:
spec-kitty operators running missions in either human-in-command (HiC) or
autonomous mode.

<!-- TODO: register in docs nav (mkdocs.yml or toc.yml) once nav pattern is
     confirmed; ask reviewer to confirm correct location. -->

---

## Overview

When any mission reaches its last domain step, Spec Kitty captures a structured
retrospective: what helped, what did not help, what governance or context gaps
appeared, and what concrete doctrine, DRG, or glossary changes are proposed.

- In **autonomous mode** (FR-011, FR-012), the retrospective is mandatory — the
  mission cannot be marked `done` without it. A silent skip is impossible by
  construction.
- In **human-in-command mode** (FR-013, FR-014, FR-015), the runtime offers the
  retrospective to the operator, who may either run it or explicitly skip it
  with an audit trail. Silent auto-run is impossible.

Findings are stored in `.kittify/missions/<mission_id>/retrospective.yaml`
(keyed by canonical ULID, never by display number) and as events in
`kitty-specs/<slug>/status.events.jsonl`. Accepted proposals feed a synthesizer
that updates project-local doctrine, DRG edges, and glossary terms with
full provenance back to the originating mission.

---

## Scenario 1 — HiC run that captures findings

A human-in-command operator finishes a `software-dev` mission. The runtime
offers the retrospective at terminus. (FR-013)

```bash
$ spec-kitty next --agent claude --mission 01KQ6YEG
...
Mission reached terminus.
Mode: human_in_command (source: charter:mode-policy:hic-default)

Run retrospective now? [Y/n]: Y
Dispatching profile:retrospective-facilitator action:retrospect ...

Retrospective complete:
  helped:        4
  not_helpful:   2
  gaps:          3
  proposals:     5

Record:  .kittify/missions/01KQ6YEGT4YBZ3GZF7X680KQ3V/retrospective.yaml
Events:  kitty-specs/<slug>/status.events.jsonl  (+8 retrospective events)

Mission marked done.
```

Events emitted in order: `retrospective.requested`, `retrospective.started`,
`retrospective.proposal.generated` (×5), `retrospective.completed` (FR-017).

The operator can now read findings and review staged proposals.

---

## Scenario 2 — HiC run that skips with audit trail

The operator chooses to skip, supplying a reason. (FR-010, FR-015)

```bash
$ spec-kitty next --agent claude --mission 01KQ6YE2
...
Mission reached terminus.
Mode: human_in_command (source: charter:mode-policy:hic-default)

Run retrospective now? [Y/n]: n
Skip reason: low-value docs fix

Retrospective skipped:
  Record:  .kittify/missions/01KQ6YE2.../retrospective.yaml
           (status: skipped, skip_reason: "low-value docs fix")
  Events:  +1 retrospective.skipped event

Mission marked done.
```

The retrospective record carries `status: skipped` and an explicit
`skip_reason`. The skip is visible in cross-mission summaries (FR-026, SC-004).
Both the YAML record and the skipped event are required; neither alone is
sufficient (FR-010).

---

## Scenario 3 — Autonomous run cannot silently skip

In autonomous mode the retrospective runs unconditionally. (FR-011, FR-012)

```bash
$ SPEC_KITTY_MODE=autonomous spec-kitty next --agent claude --mission 01KQ6YE3
...
Mode: autonomous (source: env:SPEC_KITTY_MODE)
Dispatching profile:retrospective-facilitator action:retrospect ...
Retrospective complete.
Mission marked done.
```

If the agent attempts to pass `--skip-retrospective`:

```bash
Error: Charter does not authorize operator-skip in autonomous mode.
       Mode source: env:SPEC_KITTY_MODE
       Charter clause checked: charter:mode-policy:autonomous-no-skip
       Refusing to mark mission done.
       Run the retrospective or change mode policy in the charter.
Exit code: 2
```

If the facilitator dispatch fails, the mission is blocked — it does not silently
transition to `done` with an incomplete retrospective (NFR-002, NFR-008):

```bash
Error: Retrospective facilitator failed.
       Failure code: facilitator_error
       Mission cannot transition to "done" in autonomous mode.
Exit code: 2
```

---

## Scenario 4 — Charter sovereignty wins over operator flag

A project charter declares `autonomous-no-skip`. A CI runner tries to override
with `--mode hic`. Charter wins (FR-016, C-013):

```bash
$ spec-kitty next --agent claude --mission 01KQ6YE4 --mode hic
Error: Charter override pins mode=autonomous for this project.
       --mode hic ignored.
       Mode source: charter_override (charter:mode-policy:batch-runs)
```

Mode-detection precedence: **charter/project override > explicit flag >
environment > parent process** (FR-016).

---

## Scenario 5 — Read cross-mission patterns

```bash
$ spec-kitty retrospect summary
```

Sample output (FR-025, FR-026, NFR-003):

```
Spec Kitty Retrospective Summary
Project: /path/to/project
Generated: 2026-04-27T11:35:00+00:00

Counts
  Total missions:               42
  Completed retrospectives:     27
  Skipped (HiC):                 8
  Failed:                        1
  In flight:                     4
  Legacy (no retrospective):     2

Top "not helpful" targets
  drg:edge:doctrine_directive_017->action_specify    (flagged in 5 missions)
  glossary:term:legacy-frontmatter                    (flagged in 4 missions)

Top missing glossary terms
  lifecycle-terminus-hook                             (3 missions)

Top missing DRG edges
  doctrine_tactic:premortem -> action:plan            (3 missions)

Proposal acceptance
  total: 46  accepted: 19  rejected: 11  applied: 14  pending: 10
```

The same data in machine-readable form:

```bash
$ spec-kitty retrospect summary --json --limit 10 > summary.json
$ jq '.result.proposal_acceptance' summary.json
```

The summary tolerates rich, brief, skipped, missing, and malformed records
without aborting (FR-027, NFR-004). Malformed records are excluded with a
structured reason and surfaced for repair.

---

## Scenario 6 — Apply staged proposals (default dry-run)

```bash
$ spec-kitty agent retrospect synthesize --mission 01KQ6YEG
Mode: dry-run (default)

Planned applications: 3
  ✔ P1  add_glossary_term     "lifecycle-terminus-hook"
  ✔ P2  flag_not_helpful      drg:edge:doctrine_directive_017->action_specify
  ✔ P3  add_edge              drg:edge:doctrine_tactic:premortem->action:plan

Apply: not run (use --apply to mutate)
```

```bash
$ spec-kitty agent retrospect synthesize --mission 01KQ6YEG --apply
Applied: 3
  ✔ P1  add_glossary_term  -> .kittify/glossary/lifecycle-terminus-hook.yaml
  ✔ P2  flag_not_helpful   -> .kittify/doctrine/.provenance/<...>.yaml
  ✔ P3  add_edge           -> src/doctrine/graph.yaml (overlay)

Provenance written for all 3 applications.
Events emitted: 3 × retrospective.proposal.applied
```

Only `flag_not_helpful` auto-applies. All other proposal kinds (`synthesize_*`,
`*_edge`, `add_glossary_term`, `update_glossary_term`) are staged for human
approval before they touch project-local governance state (FR-020, FR-021). The
synthesizer fails closed on conflicting proposals and applies nothing from the
conflicting set (FR-023).

---

## Scenario 7 — Next mission sees the change

After the operator applied the `add_glossary_term` proposal above, the follow-up
mission's bootstrap surfaces the new term:

```bash
$ spec-kitty next --agent claude --mission 01KQ6YE5
...
  - Glossary terms loaded: 117  (+1 since last mission: "lifecycle-terminus-hook")
    source: retrospective:01KQ6YEGT4YBZ3GZF7X680KQ3V (proposal P1)
```

Every synthesized change carries provenance: source mission id, proposal id, and
evidence event ids (FR-022, NFR-006). A reviewer can trace any change back to its
originating retrospective in one step (SC-005). (FR-024, SC-007.)

---

## What you cannot do (and why)

| Attempt | Result | Spec reference |
|---|---|---|
| Bypass autonomous gate without charter authorization | `Exit 2` | FR-012, C-013 |
| Auto-run retrospective in HiC without operator action | `Exit 2`, `silent_auto_run_attempted` | FR-014 |
| Apply doctrine/DRG/glossary changes without `--apply` | dry-run only | FR-020, FR-021 |
| Apply a proposal whose evidence event ids no longer resolve | `Exit 5`, `stale_evidence` | FR-023 |
| Apply a batch with conflicting proposals | `Exit 4`, fail-closed | FR-023 |
| Hand-edit the retrospective YAML to fake `status: completed` | gate refuses on schema or evidence-reachability | NFR-002 |

---

## Where to look when something goes wrong

| Question | Where to look |
|---|---|
| What does the retrospective record look like? | `.kittify/missions/<mission_id>/retrospective.yaml` |
| What lifecycle events did the runtime emit? | `kitty-specs/<slug>/status.events.jsonl` (filter by `event_name` prefix `retrospective.`) |
| What did the gate decide? | Structured error message from the blocked transition, or latest `retrospective.*` events |
| Is a proposal stale? | `spec-kitty agent retrospect synthesize --mission <handle>` (dry-run) |
| Are calibration recommendations available? | `architecture/calibration/<mission>.md` (one per mission) |
| Where does provenance live? | Sidecar files under `.kittify/<surface>/.provenance/` |
| Which directives were flagged not-helpful repeatedly? | `spec-kitty retrospect summary` (see "Top not helpful targets") |

---

## What this surface does not add

- A web UI for the summary — the CLI report and JSON artifact are the surface
  for this tranche.
- Auto-application of doctrine/DRG/glossary changes — only `flag_not_helpful`
  auto-applies; all other proposal kinds require human approval.
- A separate retrospective event log — retrospective events live alongside other
  lifecycle events in `status.events.jsonl`.
- Backfill of historical missions — legacy missions without a retrospective
  appear as `legacy` in the summary, not as failed runs.
- Prompt-builder filtering — calibration changes are DRG edge changes only
  (C-011).

---

## See also

- ADR for the gate shared-module decision:
  [`architecture/2.x/adr/2026-04-27-1-retrospective-gate-shared-module.md`](../architecture/2.x/adr/2026-04-27-1-retrospective-gate-shared-module.md)
- Upstream events cutover runbook:
  [`docs/migration/retrospective-events-upstream.md`](migration/retrospective-events-upstream.md)
- Mission spec (full FR/NFR list):
  [`kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/spec.md`](../kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/spec.md)
- Gate API contract:
  [`kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/gate_api.md`](../kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/gate_api.md)
- Events contract:
  [`kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/retrospective_events_v1.md`](../kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/retrospective_events_v1.md)
