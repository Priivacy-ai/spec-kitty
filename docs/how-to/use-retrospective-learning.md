---
title: How to Use the Retrospective Learning Loop
description: Run retrospect summary, preview and apply synthesis proposals, resolve conflicts, and handle facilitator failures.
---

# How to Use the Retrospective Learning Loop

This guide covers the operator workflow for the retrospective learning loop: viewing summaries,
previewing proposals, applying synthesis, resolving conflicts, and understanding the HiC vs
autonomous gate behavior.

For an explanation of why retrospectives exist and the gate model, see
[Understanding the Retrospective Learning Loop](../explanation/retrospective-learning-loop.md).

---

## 1. View the retrospective summary

Get a cross-mission overview of retrospective activity:

```bash
uv run spec-kitty retrospect summary
```

The summary reads `.kittify/missions/*/retrospective.yaml` and
`kitty-specs/*/status.events.jsonl`. It produces a cross-mission view showing:

- Total missions, completed retrospectives, skipped (HiC), failed, in-flight, and legacy counts
- Top "not helpful" targets (DRG edges or artifacts flagged repeatedly)
- Top missing glossary terms
- Top missing DRG edges
- Proposal acceptance statistics (total, accepted, rejected, applied, pending)

> **Note**: This command requires at least one completed mission with a retrospective record. On
> a brand-new project with no completed missions, it will report zero missions — this is expected.

For machine-readable output:

```bash
uv run spec-kitty retrospect summary --json

# Restrict to missions started on or after a date
uv run spec-kitty retrospect summary --since 2026-01-01

# Adjust top-N ranking limit (default 20)
uv run spec-kitty retrospect summary --limit 10
```

---

## 2. Preview synthesis proposals (dry-run)

`agent retrospect synthesize` defaults to dry-run mode. It shows what proposals would be applied
without making any changes:

```bash
uv run spec-kitty agent retrospect synthesize --mission my-feature-slug
```

Sample dry-run output:

```
Mode: dry-run (default)

Planned applications: 3
  ✔ P1  add_glossary_term     "lifecycle-terminus-hook"
  ✔ P2  flag_not_helpful      drg:edge:doctrine_directive_017->action_specify
  ✔ P3  add_edge              drg:edge:doctrine_tactic:premortem->action:plan

Apply: not run (use --apply to mutate)
```

**Proposal kinds** include:
- `add_glossary_term` / `update_glossary_term` — add or update a glossary term in the doctrine
- `flag_not_helpful` — mark a DRG artifact as not helpful; auto-included in the apply batch
- `add_edge` / `synthesize_*` — DRG graph changes; require `--apply`

No proposal writes during dry-run. `flag_not_helpful` is automatically included when you run
with `--apply`, even if you did not name its proposal ID explicitly. All mutations still require
explicit `--apply`.

You can restrict the batch to specific proposals:

```bash
uv run spec-kitty agent retrospect synthesize --mission my-feature-slug --proposal-id P1 --proposal-id P3
```

---

## 3. Apply synthesis

When the dry-run looks correct, apply with `--apply`:

```bash
uv run spec-kitty agent retrospect synthesize --mission my-feature-slug --apply
```

Applied proposals mutate project state: glossary terms are written under `.kittify/glossary/`,
DRG edges are updated under `.kittify/drg/`, synthesized doctrine artifacts are written under
`.kittify/doctrine/`, and `flag_not_helpful` records are written under `.kittify/doctrine/.flags/`.
Provenance is recorded for every change, linking the application back to its originating
retrospective and mission.

Write the JSON envelope to a file in addition to console output:

```bash
uv run spec-kitty agent retrospect synthesize --mission my-feature-slug --apply \
  --json-out synthesis-result.json
```

---

## 4. Resolve conflicts

If the synthesizer detects conflicting proposals (two proposals that contradict each other, e.g.,
one adds a term and another modifies its definition differently), it fails closed and applies
nothing from the conflicting set.

The dry-run output will show which proposals conflict:

```
CONFLICT detected between P1 and P4:
  P1: add_glossary_term "lifecycle-terminus-hook" (scope: team_domain)
  P4: add_glossary_term "lifecycle-terminus-hook" (scope: mission_local)
  → Both proposals target the same term surface with different scopes.

Conflict detection is fail-closed: no proposals applied.
```

To resolve:
1. Read the conflict output carefully to understand which proposals conflict.
2. Apply only the non-conflicting proposal IDs with repeated `--proposal-id` flags, or update the
   source retrospective record so only the intended proposal remains accepted.
3. If you resolve the issue manually, edit the durable target surface for the proposal type:
   `.kittify/glossaries/<scope>.yaml` for curated glossary terms, `.kittify/drg/edges.yaml` for
   project DRG edges, or `.kittify/doctrine/` for project-local doctrine artifacts.
4. Re-run `agent retrospect synthesize --mission <slug>` and then apply the surviving batch with
   `--apply`.

---

## 5. Staleness

A retrospective summary becomes stale when many missions have completed but their proposals have
not been reviewed. The summary itself does not become invalid, but unreviewed proposals accumulate.

Detect staleness:
```bash
uv run spec-kitty retrospect summary --json | head -50
```

Look at the `proposal_acceptance.pending` count. If pending proposals are high, work through them
mission by mission:

```bash
# For each completed mission slug, preview proposals:
uv run spec-kitty agent retrospect synthesize --mission <slug>
# Then apply if they look good:
uv run spec-kitty agent retrospect synthesize --mission <slug> --apply
```

---

## 6. Facilitator failures

When the retrospective facilitator itself fails (for example, the retrospective record cannot be
loaded or the synthesis process errors), the failure is visible in the summary:

```bash
uv run spec-kitty retrospect summary
```

The output shows failed retrospective counts separately from skipped ones. For a specific mission,
dry-run synthesis reports the failure reason:

```bash
uv run spec-kitty agent retrospect synthesize --mission my-feature-slug
```

Common facilitator failure causes:
- Malformed `retrospective.yaml` — check the YAML syntax in
  `.kittify/missions/<mission_id>/retrospective.yaml`
- Missing status events — check `kitty-specs/<slug>/status.events.jsonl` for retrospective events
- Stale evidence — proposals reference event IDs that no longer resolve

See [Troubleshooting Charter Failures](../how-to/troubleshoot-charter.md) for fix steps.

---

## 7. HiC vs Autonomous behavior

The retrospective gate operates differently depending on the mission's governance mode:

**Autonomous mode**: The retrospective is mandatory. It runs unconditionally at mission terminus.
A silent skip is impossible by construction. If the facilitator dispatch fails, the mission is
blocked — it does not silently transition to `done`. Exit code 2 is returned.

**Human-in-Command (HiC) mode**: The runtime offers the retrospective to the operator at terminus.
The operator may either run it or explicitly skip it. Skipping requires an explicit action with a
reason. An audit record is always created for the skip. Silent auto-run is impossible in HiC mode.

The mode is determined by the charter's mode policy, with this precedence:
charter/project override > explicit flag > environment variable > parent process.

---

## 8. Skip semantics (HiC mode)

In HiC mode, when `spec-kitty next` presents the retrospective, you can skip it by responding
`n` and providing a reason at the prompt. The skip is recorded as:

- `status: skipped` in `.kittify/missions/<mission_id>/retrospective.yaml`
- A `retrospective.skipped` event in `kitty-specs/<slug>/status.events.jsonl`
- Both the YAML record and the event are required

Skipped retrospectives appear in `retrospect summary` counts under "Skipped (HiC)".

---

## Exit codes for `agent retrospect synthesize`

| Exit code | Meaning |
|---|---|
| 0 | Success — dry-run complete (no mutations) or proposals applied |
| Non-zero | Failure — consult the command output for the structured error |

For the full exit code reference, see
[Retrospective Schema Reference](../reference/retrospective-schema.md).

---

## See Also

- [Understanding the Retrospective Learning Loop](../explanation/retrospective-learning-loop.md)
- [Retrospective Schema Reference](../reference/retrospective-schema.md)
- [How Charter Works](../3x/charter-overview.md)
