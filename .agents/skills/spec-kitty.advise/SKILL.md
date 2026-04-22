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
4. After completing the task, close the record (see "Close the record" below).

The `governance_context_hash` field in the response is a checksum of the context used. It is stored in the invocation record for provenance.

### Close the record
```bash
spec-kitty profile-invocation complete \
  --invocation-id <id> \
  --outcome done
```

`--outcome` accepts: `done`, `failed`, `abandoned`.  Only `--invocation-id`
is required.

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
| Before implementing — profile known | `spec-kitty ask <profile> "implement <feature>"` |
| Before implementing — profile unknown | `spec-kitty do "implement <feature>"` |
| After completing work | `spec-kitty profile-invocation complete --invocation-id <id> --outcome done` |
| Audit what ran recently | `spec-kitty invocations list --json` |
| Filter by profile | `spec-kitty invocations list --profile <id> --json` |

## What gets recorded

Every `advise` / `ask` / `do` call writes one JSONL file to
`.kittify/events/profile-invocations/<invocation_id>.jsonl`.

A successfully closed invocation appends a second line with `event=completed`.

This is the Tier 1 minimal viable trail — always written, never skipped,
even when `governance_context_available` is `false`.

## Invariants

- `advise` / `ask` / `do` **never** spawn a separate LLM call.
- `governance_context_text` is assembled from the project DRG; no network
  calls are made if the charter has already been synthesised.
- If `governance_context_available` is `false`, run
  `spec-kitty charter synthesize` to build the DRG before the next invocation.
- File names are `<invocation_id>.jsonl` — no profile prefix.  The
  `invocations list --profile` filter reads `profile_id` from file **content**,
  not the filename.
