---
title: Understanding the Retrospective Learning Loop
description: Why retrospectives exist, the gate model (autonomous vs HiC), proposal lifecycle, and the synthesizer's role.
---

# Understanding the Retrospective Learning Loop

This document explains why the retrospective learning loop exists and how it works at a conceptual
level. For how to run a retrospective, see
[How to Use the Retrospective Learning Loop](../how-to/use-retrospective-learning.md). For the
schema reference, see [Retrospective Schema Reference](../reference/retrospective-schema.md).

---

## Why retrospectives exist

Governance without feedback is static. If your `charter.md` never changes, your project's policy
doctrine never improves. Directives that are unhelpful stay unhelpful. Glossary terms that are
missing stay missing.

The retrospective learning loop is the mechanism by which completed missions feed back into
governance. When a mission finishes, the runtime captures structured findings: what helped, what
did not help, what governance or context gaps appeared, and what concrete changes are proposed to
the doctrine, DRG edges, or glossary. Over many missions, the retrospective summary reveals
patterns — directives that are consistently flagged as unhelpful, terms that are consistently
missing, DRG edges that would improve context relevance.

Without retrospectives, governance stagnates. With them, governance is a living system that
improves with every completed mission.

---

## The gate model

The retrospective is not optional in the runtime's standard flow. When a mission reaches its last
domain step, the gate activates. Two modes determine what happens:

### Autonomous mode

In autonomous mode, the retrospective is **mandatory**. The mission cannot be marked `done`
without it. A silent skip is impossible by construction — the gate refuses the `done` transition
until the retrospective facilitator completes.

If the facilitator dispatch fails (the component that collects and formats the retrospective
record), the mission is **blocked** — it does not silently transition to `done` with an incomplete
retrospective. Exit code 2 is returned. The operator must diagnose the facilitator failure and
resolve it before the mission can complete.

If the runtime detects an attempt to pass a skip flag in autonomous mode:

```
Error: Charter does not authorize operator-skip in autonomous mode.
       Mode source: env:SPEC_KITTY_MODE
       Charter clause checked: charter:mode-policy:autonomous-no-skip
       Refusing to mark mission done.
Exit code: 2
```

### Human-in-Command (HiC) mode

In HiC mode, the runtime offers the retrospective to the operator at terminus. The operator may
either run it or explicitly skip it with a stated reason. Silent auto-run is also impossible in
HiC mode — the operator must act.

When the operator skips:
- The retrospective record carries `status: skipped` and an explicit `skip_reason`
- A `retrospective.skipped` event is written to `kitty-specs/<slug>/status.events.jsonl`
- Both the YAML record and the event are required; neither alone is sufficient

Skipped retrospectives appear in cross-mission summaries, so the skip pattern is visible across
missions even if individual retrospective details are not present.

### Mode precedence

Mode is determined by the charter's mode policy. The precedence is:
**charter/project override > explicit flag > environment variable > parent process**

A project charter that declares `autonomous-no-skip` wins over any command-line flag or
environment variable. This is **charter sovereignty** — the project's own governance policy
overrides operator attempts to change the mode at runtime.

---

## Proposal lifecycle

A completed retrospective produces **proposals** — concrete, structured suggestions for governance
changes. Proposals come in several kinds:

- `add_glossary_term` / `update_glossary_term` — add or update a term in the project glossary
- `flag_not_helpful` — mark a DRG artifact (directive, tactic, edge) as not helpful
- `add_edge` — add a new relationship to the DRG
- `synthesize_*` — more complex synthesis proposals for doctrine changes

Proposals are stored in `.kittify/missions/<mission_id>/retrospective.yaml` and surfaced by
`retrospect summary`. Their lifecycle:

1. **Generated**: The retrospective facilitator produces proposals and writes them to the YAML.
2. **Staged**: Proposals are visible in dry-run `agent retrospect synthesize` output. No changes
   have been made to governance state yet.
3. **Applied** (or rejected): When the operator runs `agent retrospect synthesize --mission <slug> --apply`,
   the synthesizer validates proposals against current doctrine, detects conflicts, and applies
   accepted proposals. Rejected or conflicting proposals are not applied.
4. **Provenance recorded**: Every applied change carries provenance back to the originating
   mission, proposal ID, and evidence event IDs.

`flag_not_helpful` is auto-included in the effective apply batch, so the operator does not need
to approve it by proposal ID. It still does not mutate governance state during dry-run; all writes
require `agent retrospect synthesize --apply`.

---

## The synthesizer's role

The retrospective synthesizer is the component that bridges proposals and governance. Its role is
not to generate content — it validates, conflicts-check, and applies proposals that already exist
in the retrospective record.

The synthesizer is **fail-closed on conflicts**: if two proposals contradict each other (e.g.,
both add the same glossary term with different definitions), it applies nothing from the
conflicting set. This ensures governance state never receives a partial, inconsistent update.

The synthesizer is the only path from retrospective output to governance change. You cannot
bypass it by editing governance files directly — those files are auto-generated and would be
overwritten on the next `charter synthesize` run. The correct path is always:

1. Review proposals (dry-run)
2. Resolve any conflicts (manually, in `charter.md`)
3. Apply (`agent retrospect synthesize --mission <slug> --apply`)
4. Re-run `charter synthesize` if `charter.md` was edited

---

## Facilitator failures

A **facilitator failure** is different from a synthesizer failure:

- **Facilitator failure**: the component that collects and formats the retrospective record
  failed. The record may be missing, malformed, or incomplete. Symptoms: the retrospective
  summary shows a "failed" count; `agent retrospect synthesize` reports it cannot load the record.

- **Synthesizer failure**: the proposals exist but cannot be applied. Symptoms: non-zero exit
  from `agent retrospect synthesize --apply`; conflict errors or schema validation errors in the
  output.

For facilitator failures, diagnose with:
```bash
uv run spec-kitty retrospect summary
```

Check the `.kittify/missions/<mission_id>/retrospective.yaml` for YAML syntax errors. Check
`kitty-specs/<slug>/status.events.jsonl` for the retrospective event sequence. See
[Troubleshooting Charter Failures](../how-to/troubleshoot-charter.md) for fix steps.

---

## Cross-mission retrospective summary

`uv run spec-kitty retrospect summary` aggregates the retrospective records across all missions
in the project. The aggregate view reveals governance patterns that are not visible from any
single mission — for example, a directive that is flagged as not helpful in 5 of 10 missions is
a strong signal that the directive should be revised or removed.

The summary tolerates a mix of complete, skipped, missing, and malformed records without aborting.
Malformed records are excluded from counts with a structured reason. Use `--include-malformed` to
see the details of malformed records in the output.

---

## See Also

- [How to Use the Retrospective Learning Loop](../how-to/use-retrospective-learning.md)
- [Retrospective Schema Reference](../reference/retrospective-schema.md)
- [How Charter Works](../3x/charter-overview.md)
