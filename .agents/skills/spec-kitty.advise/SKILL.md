---
name: spec-kitty.advise
description: Get governance context for an action and open an invocation record.
---

# spec-kitty.advise

Get governance context for an action and open an invocation record.

This skill documents the `advise`, `ask`, `do`, `profiles list`,
`invocations list`, and `profile-invocation complete` command surfaces.

## Usage

### Discover profiles
```bash
spec-kitty profiles list --json
```

### Get governance context (opens an invocation record)
```bash
spec-kitty advise "implement WP03" --json
spec-kitty ask pedro "review WP05" --json
spec-kitty do "implement the payment module" --json
```

Response fields:

| Field | Type | Description |
|-------|------|-------------|
| `invocation_id` | string (ULID) | Unique ID for this invocation record |
| `profile_id` | string | Resolved profile identifier |
| `action` | string | Normalised action string |
| `governance_context_text` | string | Full governance context assembled from the project DRG |
| `governance_context_hash` | string | SHA-256 hash of `governance_context_text` |
| `governance_context_available` | boolean | `false` when charter has not been synthesised |
| `router_confidence` | string or null | Routing confidence score (auto-routing only) |

### Governance context injection

After calling `advise`, `ask`, or `do`, the response includes a `governance_context_text` field.

**You must inject this text into your working context before executing the task.**

Steps:
1. Read `governance_context_text` from the JSON response.
2. Add the text to the beginning of your task execution context. Treat it as binding governance: follow any directives, constraints, and guidelines it contains when generating code, plans, or analyses.
3. If `governance_context_available` is `false`, note it to the user ("governance context unavailable — run `spec-kitty charter synthesize` to build the DRG") but proceed with the task. The invocation trail is still recorded.
4. Execute the user's request yourself in the host agent. Spec Kitty does not search the repository, edit files, or call another LLM.
5. Write a git-managed trace for user-facing `/spec-kitty` work (see "Git-managed trace" below).
6. After completing the task, close the record (see "Close the record" below).

The `governance_context_hash` field in the response is a checksum of the context used. It is stored in the invocation record for provenance.

### Close the record
```bash
spec-kitty profile-invocation complete \
  --invocation-id <id> \
  --outcome done
```

`--outcome` accepts: `done`, `failed`, `abandoned`.  Only `--invocation-id`
is required.

Use `--artifact <path>` for output artifacts and `--commit <sha>` for the
primary content commit produced by the invocation:

```bash
spec-kitty profile-invocation complete \
  --invocation-id <id> \
  --outcome done \
  --artifact src/auth/middleware.py \
  --commit abc123def456
```

### Git-managed trace

For user-facing `/spec-kitty` requests, also create a tracked trace file:

```text
kitty-specs/_profile-invocations/YYYY-MM-DD/
  YYYY-MM-DDTHHMMSSZ-<slug>-<invocation_id>/
    trace.md
```

The trace file must include the invocation ID, timestamp, request, selected
profile/action, governance context hash, answer or work summary, evidence
consulted, artifact paths, outcome, and content commit SHA when one exists.

Git cycle:
1. Read-only advice/research: answer the user, write `trace.md`, close the
   invocation, then commit the trace file.
2. Code/doc changes: commit the content changes first, close the invocation
   with `--commit <content-sha>` and relevant `--artifact` paths, then write and
   commit `trace.md` referencing the content SHA.
3. Failure after opening: close with `--outcome failed` or `abandoned`, write a
   failure trace when possible, and commit the trace if it is useful for later
   reconstruction.

### Review recent invocations
```bash
# Newest 20 records (default)
spec-kitty invocations list --json

# Filter to one profile
spec-kitty invocations list --profile pedro --json

# Limit result count
spec-kitty invocations list --limit 10 --json
```

`invocations list` response fields per record:

| Field | Type | Description |
|-------|------|-------------|
| `invocation_id` | string | ULID identifier |
| `profile_id` | string | Profile that handled the invocation |
| `action` | string | Requested action |
| `started_at` | ISO-8601 string | When the invocation was opened |
| `status` | `"open"` or `"closed"` | Whether a `completed` event has been appended |
| `completed_at` | ISO-8601 string or null | Set when status is `"closed"` |
| `outcome` | string or null | Outcome recorded at close time |
| `evidence_ref` | string or null | Path to evidence file (Tier 2 promotion) |

## When to use

| Situation | Command |
|-----------|---------|
| Before implementing — profile known | `spec-kitty ask <profile> "implement <mission>"` |
| Before implementing — profile unknown | `spec-kitty do "implement <mission>"` |
| After completing work | `spec-kitty profile-invocation complete --invocation-id <id> --outcome done` |
| Audit what ran recently | `spec-kitty invocations list --json` |
| Filter by profile | `spec-kitty invocations list --profile <id> --json` |

## What gets recorded

Every `advise` / `ask` / `do` call writes one JSONL file to
`.kittify/events/profile-invocations/<invocation_id>.jsonl`.

A successfully closed invocation appends a second line with `event=completed`.

This is the Tier 1 minimal viable trail — always written, never skipped,
even when `governance_context_available` is `false`.

For `/spec-kitty` host-skill usage, the JSONL trail is paired with the tracked
`kitty-specs/_profile-invocations/.../trace.md` file so normal git history can
show the timestamped user request and answer.

## Invariants

- `advise` / `ask` / `do` **never** spawn a separate LLM call.
- `governance_context_text` is assembled from the project DRG; no network
  calls are made if the charter has already been synthesised.
- If `governance_context_available` is `false`, run
  `spec-kitty charter synthesize` to build the DRG before the next invocation.
- File names are `<invocation_id>.jsonl` — no profile prefix.  The
  `invocations list --profile` filter reads `profile_id` from file **content**,
  not the filename.
