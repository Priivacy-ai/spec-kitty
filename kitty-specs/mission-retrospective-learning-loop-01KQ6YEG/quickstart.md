# Quickstart: Mission Retrospective Learning Loop

**Mission**: `01KQ6YEGT4YBZ3GZF7X680KQ3V` (mid8: `01KQ6YEG`)
**Plan**: [./plan.md](./plan.md) · **Spec**: [./spec.md](./spec.md)

This quickstart shows what an operator and an autonomous agent see when this tranche is shipped. It is also the script the integration tests follow.

---

## Prerequisites

- `spec-kitty` CLI at the version that ships this tranche.
- A project that has at least one charter and at least one mission that has reached its last domain step.

---

## Scenario 1 — Human-in-command run that captures findings

A HiC operator finishes a `software-dev` mission. The runtime offers the retrospective.

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

The runtime emitted these events in order:

```
retrospective.requested
retrospective.started
retrospective.proposal.generated  (×5)
retrospective.completed
```

The operator can now read findings and review proposals.

---

## Scenario 2 — Human-in-command run that skips with audit trail

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

The retrospective record carries `status: skipped` and an explicit `skip_reason`. The skip is visible in cross-mission summaries.

---

## Scenario 3 — Autonomous run cannot silently skip

```bash
$ SPEC_KITTY_MODE=autonomous spec-kitty next --agent claude --mission 01KQ6YE3
...
Mission reached terminus.
Mode: autonomous (source: env:SPEC_KITTY_MODE)

Dispatching profile:retrospective-facilitator action:retrospect ...
Retrospective complete:
  helped:        2
  not_helpful:   0
  gaps:          1
  proposals:     1

Mission marked done.
```

If the agent attempts to skip:

```bash
$ SPEC_KITTY_MODE=autonomous spec-kitty next --agent claude --mission 01KQ6YE3 --skip-retrospective
Error: Charter does not authorize operator-skip in autonomous mode.
       Mode source: env:SPEC_KITTY_MODE
       Charter clause checked: charter:mode-policy:autonomous-no-skip
       Refusing to mark mission done.
       Run the retrospective or change mode policy in the charter.
Exit code: 2
```

If the autonomous agent's facilitator dispatch fails:

```bash
Error: Retrospective facilitator failed.
       Failure code: facilitator_error
       Message:      <redacted error chain>
       Mission cannot transition to "done" in autonomous mode.
       Re-run the retrospective once the underlying error is resolved.
Exit code: 2
```

---

## Scenario 4 — Charter sovereignty wins over operator flag

A project charter declares autonomous mode for batch runs, with `autonomous-no-skip`. The operator passes `--mode hic` from a CI runner trying to bypass the gate:

```bash
$ spec-kitty next --agent claude --mission 01KQ6YE4 --mode hic
Error: Charter override pins mode=autonomous for this project.
       --mode hic ignored.
       Falling through to autonomous gate.
       Mode source: charter_override (charter:mode-policy:batch-runs)
```

(FR-016, C-013, R-001.)

---

## Scenario 5 — Read cross-mission patterns

```bash
$ spec-kitty retrospect summary
Spec Kitty Retrospective Summary
Project: /Users/rob/projects/spec-kitty
Generated: 2026-04-27T11:35:00+00:00

Counts
  Total missions:               42
  Completed retrospectives:     27
  Skipped (HiC):                 8
  Failed:                        1
  In flight:                     4
  Legacy (no retrospective):     2
  Terminus, no retrospective:    0
  Malformed records:             0

Top "not helpful" targets
  drg:edge:doctrine_directive_017->action_specify    (flagged in 5 missions)
  glossary:term:legacy-frontmatter                    (flagged in 4 missions)
  ...

Top missing glossary terms
  lifecycle-terminus-hook                             (3 missions)
  charter-override-clause                             (2 missions)
  ...

Top missing DRG edges
  doctrine_tactic:premortem -> action:plan            (3 missions)
  ...

Proposal acceptance
  total:        46
  accepted:     19
  rejected:     11
  applied:      14    (auto-applied: 6, operator-applied: 8)
  pending:      10
  superseded:    2

Top skip reasons
  "low-value docs fix"                                (3)
  "investigation only"                                (2)
  ...
```

The same data is available as JSON:

```bash
$ spec-kitty retrospect summary --json --limit 10 > summary.json
$ jq '.result.proposal_acceptance' summary.json
{
  "total": 46,
  "accepted": 19,
  ...
}
```

---

## Scenario 6 — Apply staged proposals (default dry-run)

```bash
$ spec-kitty agent retrospect synthesize --mission 01KQ6YEG
Loading retrospective: .kittify/missions/01KQ6YEGT4YBZ3GZF7X680KQ3V/retrospective.yaml
Mode: dry-run (default)

Planned applications: 3
  ✔ 01KQ6YE...P1  add_glossary_term     "lifecycle-terminus-hook"
  ✔ 01KQ6YE...P2  flag_not_helpful      drg:edge:doctrine_directive_017->action_specify
  ✔ 01KQ6YE...P3  add_edge              drg:edge:doctrine_tactic:premortem->action:plan

Conflicts: none
Stale-evidence rejections: none
Apply: not run (use --apply to mutate)
Exit code: 0
```

```bash
$ spec-kitty agent retrospect synthesize --mission 01KQ6YEG --apply
...
Applied: 3
  ✔ 01KQ6YE...P1  add_glossary_term     -> .kittify/glossary/lifecycle-terminus-hook.yaml
  ✔ 01KQ6YE...P2  flag_not_helpful      -> .kittify/doctrine/.provenance/<...>.yaml
  ✔ 01KQ6YE...P3  add_edge              -> src/doctrine/graph.yaml (overlay)

Provenance written for all 3 applications.
Events emitted: 3 × retrospective.proposal.applied
Exit code: 0
```

If conflicts exist:

```bash
$ spec-kitty agent retrospect synthesize --mission 01KQ6YEG --apply
Conflicts detected; nothing applied.
  Group: 01KQ6YE...P3, 01KQ6YE...P5
  Reason: add_edge and remove_edge target same (from_node, to_node, kind)
Exit code: 4
```

---

## Scenario 7 — Next mission sees the change

After the operator applied the `add_glossary_term` proposal above, a follow-up mission's bootstrap surfaces the new term:

```bash
$ spec-kitty next --agent claude --mission 01KQ6YE5
...
Loading charter context for action: research
  - Glossary terms loaded: 117  (+1 since last mission: "lifecycle-terminus-hook")
    source: retrospective:01KQ6YEGT4YBZ3GZF7X680KQ3V (proposal 01KQ6YE...P1)
```

The change is visible in the next mission's context bootstrap with provenance. (FR-024, SC-007.)

---

## What you cannot do (and why)

| Attempt | Result | Why |
|---|---|---|
| Bypass autonomous gate without charter authorization | `Exit 2` | FR-012, charter sovereignty |
| Auto-run retrospective in HiC mode | `Exit 2`, `silent_auto_run_attempted` | FR-014 |
| Apply doctrine/DRG/glossary changes without `--apply` | dry-run only | FR-020, FR-021 |
| Apply a proposal whose evidence event ids no longer exist | `Exit 5`, `stale_evidence` | R-006 staleness check |
| Apply a batch with conflicting proposals | `Exit 4`, fail-closed | FR-023 |
| Hand-edit `.kittify/missions/<mission_id>/retrospective.yaml` to fake `status: completed` | gate refuses on schema or evidence-reachability | NFR-002, R-003 |

---

## Where to look when something goes wrong

| Question | File or command |
|---|---|
| What does the retrospective record look like? | `.kittify/missions/<mission_id>/retrospective.yaml` |
| What lifecycle events did the runtime emit? | `kitty-specs/<slug>/status.events.jsonl` (filter `event_name` starting with `retrospective.`) |
| What did the gate decide? | Recorded as a structured error message; or read the latest `retrospective.*` events |
| Is a proposal stale? | `spec-kitty agent retrospect synthesize --mission <handle>` (dry-run) |
| Are calibration recommendations available? | `architecture/calibration/<mission>.md` (one per mission) |
| Where does provenance live? | Sidecar files under `.kittify/<surface>/.provenance/` |

---

## What this tranche does **not** add

- A web UI for the summary. The CLI report and JSON artifact are the surface.
- Auto-application of doctrine/DRG/glossary changes. Only `flag_not_helpful` auto-applies.
- A separate retrospective event log. Retrospective events live alongside other lifecycle events.
- Migration of historical missions to backfill retrospectives. They show up as `legacy` in the summary.
- Prompt-builder filtering. Calibration changes are DRG edges only.
