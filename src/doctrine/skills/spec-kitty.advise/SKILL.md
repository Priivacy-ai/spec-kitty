---
name: spec-kitty.advise
description: >-
  Standalone profile-governed invocations: get governance context for an
  action, open an Op, do the work under that context, and close the Op with
  the real outcome. Documents the advise, ask, do, profiles list,
  invocations list, and profile-invocation complete command surfaces.
  Triggers: "use spec kitty to", "hey spec kitty", "spec kitty, fix/do/ask/advise",
  ad-hoc requests that are not part of a running mission workflow.
---

# spec-kitty.advise

Get governance context for an action and open an Op (invocation record).

This skill documents the `advise`, `ask`, `do`, `profiles list`,
`invocations list`, and `profile-invocation complete` command surfaces.

## The open→work→close contract

Every standalone invocation follows the same three-step lifecycle:

1. **Open** — `spec-kitty do` (or `ask` / `advise`) opens the Op and loads
   governance context. It does NOT do the work and it does NOT close the Op.
2. **Work** — the agent does the work under that governance context.
3. **Close** — the agent MUST close the Op with the real outcome:

   ```bash
   spec-kitty profile-invocation complete \
     --invocation-id <id> \
     --outcome <done|failed|abandoned> [--evidence <path>]
   ```

   Failed work closes as `failed` — an Op is never left open deliberately.
   `spec-kitty doctor ops` reports orphaned (open) Ops, and
   `spec-kitty doctor ops --close-stale` sweeps stale ones closed as
   `abandoned` with `closed_by: doctor_sweep`.

## Usage

### Discover profiles
```bash
spec-kitty profiles list --json
```

### Get governance context (opens an Op)
```bash
spec-kitty advise "implement WP03" --json
spec-kitty ask pedro "review WP05" --json
spec-kitty do "implement the payment module" --json
```

Response fields:

| Field | Type | Description |
|-------|------|-------------|
| `invocation_id` | string (ULID) | Unique ID for this Op |
| `profile_id` | string | Resolved profile identifier |
| `action` | string | Normalised action string |
| `governance_context_text` | string | Full governance context assembled from the project DRG |
| `governance_context_hash` | string | SHA-256 hash of `governance_context_text` |
| `governance_context_available` | boolean | `false` when charter has not been synthesised |
| `router_confidence` | string or null | Routing confidence score (auto-routing only) |
| `status` | `"open"` | The Op is open until you close it |
| `close_contract` | object | Exact close command, accepted outcomes, and flags |

### Governance context injection

After calling `advise`, `ask`, or `do`, the response includes a
`governance_context_text` field.

**You must inject this text into your working context before executing the task.**

Steps:
1. Read `governance_context_text` from the JSON response.
2. Add the text to the beginning of your task execution context. Treat it as
   binding governance: follow any directives, constraints, and guidelines it
   contains when generating code, plans, or analyses.
3. If `governance_context_available` is `false`, note it to the user
   ("governance context unavailable — run `spec-kitty charter synthesize` to
   build the DRG") but proceed with the task. The Op trail is still recorded.
4. After completing the work, close the Op (see "Close the Op" below).

The `governance_context_hash` field in the response is a checksum of the
context used. It is stored in the Op record for provenance.

### Close the Op
```bash
spec-kitty profile-invocation complete \
  --invocation-id <id> \
  --outcome <done|failed|abandoned>
```

`--outcome` is required and must reflect what actually happened: `done` for
completed work, `failed` for work that did not succeed, `abandoned` for work
that was dropped. Optional flags: `--evidence <path>`, `--artifact <ref>`,
`--commit <sha>`.

### Review recent invocations
```bash
# Newest 20 records (default)
spec-kitty invocations list --json

# Filter to one profile
spec-kitty invocations list --profile pedro --json

# Limit result count
spec-kitty invocations list --limit 10 --json
```

## When to use

| Situation | Command |
|-----------|---------|
| Before implementing — profile known | `spec-kitty ask <profile> "implement <mission>"` |
| Before implementing — profile unknown | `spec-kitty do "implement <mission>"` |
| After completing work | `spec-kitty profile-invocation complete --invocation-id <id> --outcome <done\|failed\|abandoned>` |
| Audit what ran recently | `spec-kitty invocations list --json` |
| Find orphaned (open) Ops | `spec-kitty doctor ops` |
| Sweep stale open Ops | `spec-kitty doctor ops --close-stale` |

## What gets recorded

Every `advise` / `ask` / `do` call writes one JSONL file to
`kitty-ops/<invocation_id>.jsonl` with a `started` event. Closing the Op
appends a `completed` event carrying the real `outcome` and `closed_by`.

An Op without a `completed` event is an **orphan** — visible in
`spec-kitty invocations list` as `open`, reported by `spec-kitty doctor ops`,
and surfaced at Claude Code session start/stop.

## Invariants

- `advise` / `ask` / `do` **never** spawn a separate LLM call.
- `do` opens the Op and returns — it never closes the Op itself. The working
  agent closes it with the real outcome.
- `governance_context_text` is assembled from the project DRG; no network
  calls are made if the charter has already been synthesised.
- If `governance_context_available` is `false`, run
  `spec-kitty charter synthesize` to build the DRG before the next invocation.
