---
title: Profile Invocation Reference
description: Reference for ask/advise/do modes, profile-invocation complete, invocation trail fields, and lifecycle states.
---

# Profile Invocation Reference

Profile invocation is the mechanism by which a governed agent persona is called with Charter
context. For an explanation of the model, see
[Understanding Governed Profile Invocation](../explanation/governed-profile-invocation.md).

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
Each file contains two events: `started` and `completed`.

### started event fields

| Field | Type | Description |
|---|---|---|
| `invocation_id` | ULID string | Unique identifier for this invocation |
| `profile` | string | Agent profile identifier (e.g., `implementer-ivan`) |
| `action` | string | Mission action being performed (e.g., `implement`) |
| `governance_context` | object | Charter context snapshot at invocation time (DRG-derived) |
| `started_at` | ISO 8601 timestamp | When the invocation was opened |
| `mode_of_work` | string | `advisory`, `task_execution`, `mission_step`, or `query` |
| `mission_id` | ULID string | Associated mission identifier (if applicable) |

### completed event fields

| Field | Type | Description |
|---|---|---|
| `invocation_id` | ULID string | Matches the `started` event |
| `outcome` | string | `done`, `failed`, or `abandoned` |
| `completed_at` | ISO 8601 timestamp | When `profile-invocation complete` was called |
| `artifacts` | string[] | Repo-relative paths to produced artifacts |
| `commit` | string | Git SHA of the primary produced commit |

---

## Lifecycle states

An invocation passes through three states:

1. **opened**: A `started` event has been written. The invocation ID is available. Execution has
   not yet completed.
2. **in_progress**: The executor is running. Intermediate events may be written.
3. **complete** (or **failed** / **abandoned**): `profile-invocation complete` has been called.
   A `completed` event with the final outcome is appended to the trail file.

An invocation that was opened but never completed (no `completed` event) is considered stale.
This can happen if the agent process was interrupted. Stale invocations are visible in the
retrospective facilitator's diagnostic output.

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
{"event":"started","invocation_id":"01KQA1B2C3D4E5F6G7H8J9K0","profile":"implementer-ivan","action":"implement","mode_of_work":"mission_step","started_at":"2026-04-29T10:00:00Z","mission_id":"01KQA0X0Y0Z0A0B0C0D0E0F0"}
{"event":"completed","invocation_id":"01KQA1B2C3D4E5F6G7H8J9K0","outcome":"done","completed_at":"2026-04-29T10:45:00Z","artifacts":["src/auth/token.py","tests/test_token.py"],"commit":"abc123def456789"}
```

This is an illustrative example. Actual field names and ordering may vary; rely on the field
descriptions above rather than this example for parsing.

---

## See Also

- [Understanding Governed Profile Invocation](../explanation/governed-profile-invocation.md)
- [How to Run a Governed Mission](../how-to/run-governed-mission.md)
- [How Charter Works](../3x/charter-overview.md)
