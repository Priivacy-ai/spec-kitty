---
title: Retrospective Schema and Events Reference
description: retrospective.yaml field schema, proposal kinds, retrospective status events, and synthesizer exit codes.
---

# Retrospective Schema and Events Reference

This reference documents the `retrospective.yaml` schema, proposal types, retrospective status
events, and synthesizer exit codes. For how to use the retrospective loop, see
[How to Use the Retrospective Learning Loop](../how-to/use-retrospective-learning.md).

---

## retrospective.yaml schema

Retrospective records are stored at:
```
.kittify/missions/<mission_id>/retrospective.yaml
```

The file is keyed by canonical mission ULID, not display number.

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_id` | ULID string | Yes | Canonical mission identity |
| `mission_slug` | string | Yes | Human-readable mission slug |
| `status` | string | Yes | `pending`, `started`, `completed`, `skipped`, `failed` |
| `skip_reason` | string | No | Populated when `status: skipped`; records the operator-stated reason |
| `helped` | list | No | Artifacts, directives, and tactics that the agent found helpful |
| `not_helpful` | list | No | Artifacts flagged as not helpful during this mission |
| `gaps` | list | No | Governance or context gaps identified during this mission |
| `proposals` | list | No | Structured change proposals (see Proposal kinds below) |
| `evidence_event_ids` | list | Yes | Event IDs that serve as evidence for the retrospective record |
| `facilitator_profile` | string | No | Profile ID of the facilitator that ran the retrospective |
| `started_at` | ISO 8601 timestamp | No | When the retrospective facilitator was dispatched |
| `completed_at` | ISO 8601 timestamp | No | When the retrospective completed |

---

## Proposal kinds

Each proposal in the `proposals` list has a `kind` field that determines what it applies to and
what fields are required.

### add_glossary_term

Add a new term to the project glossary.

| Field | Required | Description |
|---|---|---|
| `kind` | Yes | `add_glossary_term` |
| `surface` | Yes | Lowercase normalized term string (e.g., `lifecycle-terminus`) |
| `scope` | Yes | One of: `mission_local`, `team_domain`, `audience_domain`, `spec_kitty_core` |
| `definition` | Yes | Human-readable definition |
| `confidence` | No | Float 0.0–1.0 (default 1.0) |
| `rationale` | No | Why this term is proposed |

### update_glossary_term

Update an existing glossary term's definition or scope.

| Field | Required | Description |
|---|---|---|
| `kind` | Yes | `update_glossary_term` |
| `surface` | Yes | Existing term surface to update |
| `definition` | No | New definition |
| `scope` | No | New scope |
| `rationale` | No | Why this change is proposed |

### flag_not_helpful

Flag a DRG artifact (directive, tactic, or edge) as not helpful. This is the only proposal kind
that is auto-applied without `--apply`.

| Field | Required | Description |
|---|---|---|
| `kind` | Yes | `flag_not_helpful` |
| `target` | Yes | DRG URN of the artifact (e.g., `drg:edge:doctrine_directive_017->action_specify`) |
| `rationale` | No | Why the artifact was not helpful |

### add_edge

Add a new relationship to the DRG.

| Field | Required | Description |
|---|---|---|
| `kind` | Yes | `add_edge` |
| `from` | Yes | Source node URN |
| `to` | Yes | Target node URN |
| `relationship` | Yes | Edge type (e.g., `implies`, `specializes`, `scopes-to`) |
| `rationale` | No | Why this edge is proposed |

### Synthesizer acceptance criteria

The synthesizer accepts a proposal when:
- All required fields are present and valid
- No conflicting proposal exists in the same batch (same target with different values)
- The referenced artifacts (evidence event IDs) still resolve in the event log

The synthesizer rejects a proposal when:
- Required fields are missing
- The target URN does not exist in the DRG (for `flag_not_helpful`)
- The term surface is malformed (for glossary proposals)
- A conflicting proposal exists (fail-closed: the entire conflicting set is rejected)

---

## Retrospective status events

Retrospective lifecycle events are written to `kitty-specs/<slug>/status.events.jsonl` alongside
other mission lifecycle events. Filter by event name prefix `retrospective.` to isolate them.

| Event name | When emitted | Description |
|---|---|---|
| `retrospective.requested` | At mission terminus | The runtime requested a retrospective |
| `retrospective.started` | Facilitator dispatched | The retrospective facilitator began execution |
| `retrospective.proposal.generated` | Per proposal | One event per generated proposal (×N) |
| `retrospective.completed` | Facilitator finished | The retrospective completed successfully |
| `retrospective.skipped` | Operator skipped | The operator explicitly skipped (HiC mode only) |
| `retrospective.failed` | Facilitator failed | The facilitator encountered an error |
| `retrospective.proposal.applied` | Per applied proposal | One event per applied proposal (×N) |

The `retrospective.skipped` event and the corresponding `status: skipped` in the YAML record are
both required. Neither alone is sufficient to record a valid skip.

---

## Synthesizer exit codes

`spec-kitty agent retrospect synthesize` uses the following exit codes:

| Exit code | Meaning | Action required |
|---|---|---|
| 0 | Success — dry-run complete (no changes) or proposals applied successfully | None |
| Non-zero | Failure — consult the command output for the structured error message | See output for conflict details, schema errors, or missing records |

The `--apply` flag is required for any mutations. Omitting `--apply` always exits 0 on a valid
dry-run regardless of proposal count.

For the current exit code list, run:
```bash
uv run spec-kitty agent retrospect synthesize --help
```

---

## See Also

- [How to Use the Retrospective Learning Loop](../how-to/use-retrospective-learning.md)
- [Understanding the Retrospective Learning Loop](../explanation/retrospective-learning-loop.md)
