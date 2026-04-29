---
title: Understanding Governed Profile Invocation
description: How profile invocation works under governance — the (profile, action, governance-context) triple, modes, lifecycle, and the invocation trail.
---

# Understanding Governed Profile Invocation

This document explains governed profile invocation. For how to run a governed mission, see
[How to Run a Governed Mission](../how-to/run-governed-mission.md). For the CLI reference, see
[Profile Invocation Reference](../reference/profile-invocation.md).

---

## The governed invocation primitive

Every mission action in Spec Kitty is a **governed invocation** — a triple of three elements:

1. **Profile**: the agent persona being invoked (e.g., `implementer-ivan`, `reviewer-renata`,
   `researcher-robbie`). A profile encodes domain knowledge, tool preferences, and behavioral
   guidelines appropriate to a specific role.

2. **Action**: the workflow action being performed (e.g., `specify`, `plan`, `implement`,
   `review`). The action determines which DRG subgraph the runtime traverses and which prompt
   template is used.

3. **Governance context**: the Charter bundle context injected at invocation time. This is the
   DRG-derived, action-scoped set of directives, tactics, and glossary terms that the agent
   receives. The governance context is what makes the invocation "governed" — the agent reads
   project policy from this context rather than inventing it.

When `spec-kitty next` prepares a prompt for the current mission step, it resolves the action and
renders governance context into the prompt file returned to the calling agent. The agent does not
construct that context itself; the runtime does.

---

## Three invocation modes

Profile invocation has three CLI-accessible modes. These correspond to the three commands that
open an invocation record:

| Mode | Command | Behavior |
|---|---|---|
| Ask | `spec-kitty ask <profile> <request>` | Invoke a named profile directly for a query or advisory flow. The caller chooses the profile explicitly. |
| Advise | `spec-kitty advise [--profile <profile>] <request>` | Get governance context for a request; opens an invocation record. The runtime routes the request and may auto-select a profile. |
| Do | `spec-kitty do <request>` | Route a request to the best-matching profile for action (anonymous dispatch). The router picks the profile. |

In the current 3.2.x CLI, `spec-kitty next` is separate from these ad-hoc profile-invocation
commands. `next` issues governed prompt files and mission-step lifecycle records; `ask`,
`advise`, and `do` open `.kittify/events/profile-invocations/*.jsonl` records for ad-hoc
governed requests.

---

## Invocation lifecycle

Every invocation opened by `ask`, `advise`, or `do` follows the same append-only lifecycle:

1. **Opened**: A `started` event is written to
   `.kittify/events/profile-invocations/{invocation_id}.jsonl` before the executor returns. This
   write is unconditional — it happens regardless of SaaS connectivity or charter state.

2. **Work happens outside the CLI**: The CLI has returned the prompt/context payload. The caller or
   agent performs the work.

3. **Completed**: When execution finishes, `spec-kitty profile-invocation complete` is called to
   close the trail. This appends a `completed` event to the same JSONL file. `--artifact` and
   `--commit` append separate correlation events after the completed event.

The `profile-invocation complete` command signals that the invocation has ended:

```bash
uv run spec-kitty profile-invocation complete \
  --invocation-id <ULID> \
  --outcome done \
  --artifact path/to/produced/file.md \
  --commit <git-sha>
```

Options for `profile-invocation complete`:
- `--outcome`: `done`, `failed`, or `abandoned`
- `--artifact`: path to an artifact produced by this invocation (repeatable)
- `--commit`: the primary git commit SHA produced by this invocation (singular)
- `--evidence`: promote a file to a Tier 2 evidence artifact (not allowed for `advisory` or
  `query` mode invocations)

---

## The invocation trail

The invocation trail is the local audit record written by every governed invocation. It provides:

1. **Local accountability**: operators can reconstruct what happened on any checkout without SaaS
   connectivity.
2. **SaaS coherence**: the dashboard timeline shows the same history as the local audit log.
3. **Governance provenance**: retrospective and doctrine work can reference specific invocations.

Trail files live at `.kittify/events/profile-invocations/{invocation_id}.jsonl` - one JSONL file
per invocation. Each line is an event (`started`, `completed`, `glossary_checked`,
`artifact_link`, `commit_link`, or future additive events).

Key fields on the `started` event:

| Field | Type | Description |
|---|---|---|
| `profile_id` | string | Agent profile identifier |
| `action` | string | Mission action being performed |
| `request_text` | string | Request supplied to `ask`, `advise`, or `do` |
| `governance_context_hash` | string | Hash of the rendered Charter context |
| `governance_context_available` | boolean | Whether Charter context was available |
| `started_at` | ISO timestamp | When the invocation was opened |
| `mode_of_work` | string | `advisory`, `task_execution`, `mission_step`, or `query` |

Key fields on the `completed` event:

| Field | Type | Description |
|---|---|---|
| `invocation_id` | ULID | Matches the `started` event |
| `outcome` | string | `done`, `failed`, or `abandoned` |
| `completed_at` | ISO timestamp | When `profile-invocation complete` was called |
| `evidence_ref` | string/null | Evidence path or text supplied with `--evidence` |

---

## Evidence and artifact correlation

Artifacts produced during an invocation are linked back to the trail record via separate
`artifact_link` and `commit_link` events appended by the `--artifact` and `--commit` options on
`profile-invocation complete`. This correlation provides:

- A local audit link from an invocation to the artifacts or commit it produced
- Governance provenance context for humans and future automated consumers

Evidence files (promoted via `--evidence`) receive Tier 2 status in the trail, meaning they are
specifically designated as evidence of the invocation's outcome. Note: `--evidence` is not allowed
for `advisory` or `query` mode invocations (enforced before any write).

---

## See Also

- [How Charter Works](../3x/charter-overview.md)
- [How to Run a Governed Mission](../how-to/run-governed-mission.md)
- [Profile Invocation Reference](../reference/profile-invocation.md)
