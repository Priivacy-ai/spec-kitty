# Contract: `spec-kitty do` Output (open-Op dispatch)

## Behavior

`spec-kitty do "<request>" [--profile <id>] [--json]`:
1. Routes request → profile/action (unchanged; routing failure → no Op, exit 1 with recovery text).
2. Loads governance context, writes **started event only**. No completed event is written by `do` under any outcome.
3. Propagates the started event to SaaS via the shared propagator (async, best-effort, sync-gated) — parity with `ask`/`advise`.
4. Prints capsule + close contract; exits 0.

## Rich output (additions/changes)

- Governance capsule unchanged (profile, action, confidence, invocation id, glossary warnings, governance context).
- ADDED (mission dispatch-dry-run-route-only-01M1HKV2, PR-BOUNDARY-002): when the router considered other candidates, an `Alternatives considered (N):` block lists each losing `RouterDecision` candidate (profile, action, confidence) -- the same `alternatives` list already carried in this command's `--json` envelope (see the JSON section below), now also rendered on the rich-console path. Previously only `--dry-run`'s rich renderer printed this block; this closes that unforced console/JSON asymmetry.
- REMOVED: `Op record written — commit it: git add kitty-ops/<id>.jsonl`
- ADDED: close contract block:
  ```
  This Op is OPEN. After completing the work, close it with the real outcome:
    spec-kitty profile-invocation complete --invocation-id <id> --outcome <done|failed|abandoned> [--evidence <file>] [--artifact <path>] [--commit <sha>]
  Unclosed Ops are reported by `spec-kitty doctor ops` and swept to 'abandoned' when stale.
  ```

## JSON output (additions)

Existing payload fields preserved, plus:

```json
{
  "invocation_id": "01KT…",
  "status": "open",
  "close_contract": {
    "command": "spec-kitty profile-invocation complete --invocation-id 01KT… --outcome <done|failed|abandoned>",
    "outcomes": ["done", "failed", "abandoned"],
    "evidence_flag": "--evidence",
    "artifact_flag": "--artifact",
    "commit_flag": "--commit"
  }
}
```

`evidence_flag` is omitted when the Op's `mode_of_work` is `advisory` or `query`, because `profile-invocation complete` refuses `--evidence` for those modes (InvalidModeForEvidenceError, FR-009).

**Planned field (mission `dispatch-dry-run-route-only-01M1HKV2` WP2, not yet present as of WP1):** the payload above will gain an `alternatives` field — the router's already-computed losing candidates for the winning call, always a list, never `null`. WP1 (this doc update) introduces `alternatives` only on the `--dry-run` payloads below; WP2 threads the same field onto this real-dispatch `"status": "open"` payload with its actual per-call values.

## `--dry-run` output (mission `dispatch-dry-run-route-only-01M1HKV2`)

`spec-kitty dispatch "<request>" [--profile <id>] --dry-run [--json]`:

1. Routes request → profile/action exactly as real dispatch does (same `ActionRouter`, same explicit-`--profile` bypass, same empty-charter fallback).
2. Assembles governance context and runs the glossary chokepoint scan — both already read-only, unchanged from the real path.
3. Writes **nothing**: no `kitty-ops/<id>.jsonl`, no `kitty-ops/ops-index.jsonl` line, no `.kittify/events/glossary/*.jsonl` file, no SaaS propagator submit. No Op is opened, so there is no close contract to advertise.

### Success shape

Reuses the real-dispatch payload's field set minus `invocation_id` and `close_contract`, plus a terminal `"status": "dry_run"`:

```json
{
  "status": "dry_run",
  "profile_id": "implementer-fixture",
  "profile_friendly_name": "Implementer (fixture)",
  "action": "implement",
  "governance_context_text": "...",
  "governance_context_hash": "b6b54201f23d00f5",
  "governance_context_available": true,
  "router_confidence": "canonical_verb",
  "glossary_observations": { "matched_urns": [], "high_severity": [], "all_conflicts": [], "tokens_checked": 3, "duration_ms": 0.4, "error_msg": null },
  "recommendation": null,
  "empty_charter_fallback": false,
  "alternatives": []
}
```

### `ROUTER_AMBIGUOUS` shape (FR-009)

A request that would raise `ROUTER_AMBIGUOUS` under real dispatch (exit 1) instead exits **0** under `--dry-run`, with no winner — the deliberate UI-probing affordance the flag exists for. This is NOT an `InvocationPayload` (no profile was resolved, so no governance context, no recommendation, no glossary scan tied to a winner exists to report):

```json
{
  "status": "dry_run",
  "profile_id": null,
  "action": null,
  "router_confidence": "ambiguous",
  "alternatives": [
    {"profile_id": "implementer-a", "action": "implement", "confidence": "canonical_verb", "match_reason": "token 'implement' matched implementer canonical verb"},
    {"profile_id": "implementer-b", "action": "implement", "confidence": "canonical_verb", "match_reason": "token 'implement' matched implementer canonical verb"}
  ]
}
```

`ROUTER_NO_MATCH` and an unknown `--profile` (`PROFILE_NOT_FOUND`) still exit 1 with the same structured error JSON as real dispatch — there is no partial routing signal worth reporting in either case.

## Close surface (informative summary)

> Normative source for record lifecycle and git behavior: `op-record-events.md`. This section is an informative summary for CLI consumers; on any divergence, `op-record-events.md` wins.

`spec-kitty profile-invocation complete --invocation-id <id> --outcome <o> [--evidence …] [--artifact …]* [--commit <sha>]`
- Writes `OpCompletedEvent` with `closed_by="agent"`.
- Idempotent: second close → `AlreadyClosedError`, exit 1, structured error JSON in `--json` mode.
- Auto-commits the Op record at close.
