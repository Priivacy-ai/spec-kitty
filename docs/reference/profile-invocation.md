---
title: Profile Invocation Reference
description: Reference for ask/advise/do modes, profile-invocation complete, invocation trail fields, and lifecycle states.
---

# Profile Invocation Reference

Profile invocation is the local audit-trail mechanism used by the ad-hoc `ask`, `advise`, and
`do` commands. Each invocation receives Charter context and writes an append-only JSONL record.
For an explanation of the model, see
[Understanding Governed Profile Invocation](../explanation/governed-profile-invocation.md).

`spec-kitty next` is the canonical mission loop. In the current 3.2.x CLI it issues governed
prompt files and separate mission-step lifecycle records; it does not open these
`profile-invocation` JSONL files directly.

---

## Invocation modes

Three CLI commands open a governed invocation record:

| Mode | Command | Description |
|---|---|---|
| Ask | `spec-kitty ask <profile> <request>` | Invoke a named profile directly for a query or advisory flow. The caller specifies the profile. |
| Advise | `spec-kitty advise [--profile <profile>] <request>` | Get governance context for a request; opens an invocation record. Runtime may auto-route. |
| Do | `spec-kitty do <request>` | Route a request to the best-matching profile for action (anonymous dispatch). |

---

## spec-kitty ask

**Synopsis**: `spec-kitty ask [OPTIONS] PROFILE REQUEST`

**Description**: Invoke a named profile directly.

| Argument/Flag | Description |
|---|---|
| `PROFILE` | Profile ID or name [required] |
| `REQUEST` | Natural language request [required] |
| `--json` | Output JSON payload |

**Example**:
```bash
uv run spec-kitty ask implementer-ivan "Review this implementation approach"
uv run spec-kitty ask reviewer-renata "Check this PR description" --json
```

---

## spec-kitty advise

**Synopsis**: `spec-kitty advise [OPTIONS] REQUEST`

**Description**: Get governance context for a request (opens an invocation record).

| Argument/Flag | Description |
|---|---|
| `REQUEST` | Natural language request to route [required] |
| `--profile`, `-p TEXT` | Explicit profile ID or name (optional — auto-routed if omitted) |
| `--json` | Output JSON payload |

**Example**:
```bash
uv run spec-kitty advise "What testing approach should I use for this module?"
uv run spec-kitty advise "How should I structure this API?" --profile architect-alphonso --json
```

---

## spec-kitty do

**Synopsis**: `spec-kitty do [OPTIONS] REQUEST`

**Description**: Route a request to the best-matching profile (anonymous dispatch). The router
picks the profile based on the request content and current mission context.

| Argument/Flag | Description |
|---|---|
| `REQUEST` | Natural language request [required] |
| `--json` | Output JSON payload |

**Example**:
```bash
uv run spec-kitty do "Implement the user authentication module"
uv run spec-kitty do "Write a spec for the payments feature" --json
```

---

## spec-kitty profile-invocation complete

**Synopsis**: `spec-kitty profile-invocation complete [OPTIONS]`

**Description**: Close an open invocation record. This is the signal that closes the invocation
trail. Call it when execution finishes to append a `completed` event to the trail file.

| Flag | Description |
|---|---|
| `--invocation-id`, `-i TEXT` | Invocation ULID to close [required] |
| `--outcome TEXT` | `done`, `failed`, or `abandoned` |
| `--evidence TEXT` | Path to evidence file (Tier 2 promotion). Not allowed for `advisory` or `query` invocations. |
| `--artifact TEXT` | Path to an artifact produced by this invocation (repeatable) |
| `--commit TEXT` | Git commit SHA most directly produced by this invocation (singular) |
| `--json` | Output JSON payload |

**Example**:
```bash
# Close with success outcome and link artifact
uv run spec-kitty profile-invocation complete \
  --invocation-id 01KQABCDEF1234567890 \
  --outcome done \
  --artifact docs/how-to/my-guide.md \
  --commit abc123def456

# Close a failed invocation
uv run spec-kitty profile-invocation complete \
  --invocation-id 01KQABCDEF1234567890 \
  --outcome failed
```

---

## Invocation trail fields

Trail records are stored in `.kittify/events/profile-invocations/{invocation_id}.jsonl`.
Each file contains a `started` event and, once closed, a `completed` event. It may also contain
additional append-only events such as `glossary_checked`, `artifact_link`, or `commit_link`.

### started event fields

| Field | Type | Description |
|---|---|---|
| `invocation_id` | ULID string | Unique identifier for this invocation |
| `event` | string | `started` |
| `profile_id` | string | Agent profile identifier (e.g., `implementer-ivan`) |
| `action` | string | Mission action being performed (e.g., `implement`) |
| `request_text` | string | Natural-language request supplied to `ask`, `advise`, or `do` |
| `governance_context_hash` | string | First 16 hex characters of the rendered Charter context SHA-256 |
| `governance_context_available` | boolean | Whether Charter context was available when the record was opened |
| `actor` | string | Caller identity such as `operator`, `claude`, or `codex` |
| `router_confidence` | string/null | Router confidence for auto-routed requests |
| `started_at` | ISO 8601 timestamp | When the invocation was opened |
| `mode_of_work` | string | `advisory`, `task_execution`, `mission_step`, or `query` |

### completed event fields

| Field | Type | Description |
|---|---|---|
| `event` | string | `completed` |
| `invocation_id` | ULID string | Matches the `started` event |
| `profile_id` | string | Profile ID copied from the `started` event |
| `outcome` | string | `done`, `failed`, or `abandoned` |
| `completed_at` | ISO 8601 timestamp | When `profile-invocation complete` was called |
| `evidence_ref` | string/null | Evidence path or text supplied with `--evidence` |

### correlation events

When `--artifact` or `--commit` is supplied to `profile-invocation complete`, the CLI appends
separate correlation events after the completed record:

| Event | Key fields | Description |
|---|---|---|
| `artifact_link` | `kind`, `ref`, `at` | Repo-relative or absolute artifact reference |
| `commit_link` | `sha`, `at` | Primary git commit SHA |

---

## Lifecycle states

An invocation passes through two durable states:

1. **open**: A `started` event has been written. The invocation ID is available. Execution has
   not yet completed.
2. **closed**: `profile-invocation complete` has been called.
   A `completed` event with the final outcome is appended to the trail file.

An invocation that was opened but never completed (no `completed` event) is considered stale.
This can happen if the agent process was interrupted. Use `spec-kitty invocations list` to find
open records.

---

## Mode-of-work enforcement

`--evidence` on `profile-invocation complete` is enforced against the invocation's
`mode_of_work`. Attempting to promote evidence on an `advisory` or `query` invocation results
in `InvalidModeForEvidenceError`, and no write occurs. Re-run `complete` without `--evidence` to
close the invocation cleanly.

| mode_of_work | Tier 2 evidence (`--evidence`) eligible |
|---|---|
| `advisory` | No |
| `query` | No |
| `task_execution` | Yes |
| `mission_step` | Yes |

---

## Example trail record (illustrative)

```jsonl
{"event":"started","invocation_id":"01KQA1B2C3D4E5F6G7H8J9K0","profile_id":"implementer-ivan","action":"implement","request_text":"Implement token validation","governance_context_hash":"0123abcd4567ef89","governance_context_available":true,"actor":"operator","started_at":"2026-04-29T10:00:00Z","mode_of_work":"mission_step"}
{"event":"completed","invocation_id":"01KQA1B2C3D4E5F6G7H8J9K0","profile_id":"implementer-ivan","action":"","completed_at":"2026-04-29T10:45:00Z","outcome":"done","evidence_ref":null}
{"event":"artifact_link","invocation_id":"01KQA1B2C3D4E5F6G7H8J9K0","kind":"artifact","ref":"src/auth/token.py","at":"2026-04-29T10:45:02Z"}
{"event":"commit_link","invocation_id":"01KQA1B2C3D4E5F6G7H8J9K0","sha":"abc123def456789","at":"2026-04-29T10:45:03Z"}
```

This is an illustrative example. Actual field names and ordering may vary; rely on the field
descriptions above rather than this example for parsing.

---

## See Also

- [Understanding Governed Profile Invocation](../explanation/governed-profile-invocation.md)
- [How to Run a Governed Mission](../how-to/run-governed-mission.md)
- [How Charter Works](../3x/charter-overview.md)
