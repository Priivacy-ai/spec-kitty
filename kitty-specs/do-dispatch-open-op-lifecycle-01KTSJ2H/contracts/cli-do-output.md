# Contract: `spec-kitty do` Output (open-Op dispatch)

## Behavior

`spec-kitty do "<request>" [--profile <id>] [--json]`:
1. Routes request → profile/action (unchanged; routing failure → no Op, exit 1 with recovery text).
2. Loads governance context, writes **started event only**. No completed event is written by `do` under any outcome.
3. Propagates the started event to SaaS via the shared propagator (async, best-effort, sync-gated) — parity with `ask`/`advise`.
4. Prints capsule + close contract; exits 0.

## Rich output (additions/changes)

- Governance capsule unchanged (profile, action, confidence, invocation id, glossary warnings, governance context).
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

## Close surface (informative summary)

> Normative source for record lifecycle and git behavior: `op-record-events.md`. This section is an informative summary for CLI consumers; on any divergence, `op-record-events.md` wins.

`spec-kitty profile-invocation complete --invocation-id <id> --outcome <o> [--evidence …] [--artifact …]* [--commit <sha>]`
- Writes `OpCompletedEvent` with `closed_by="agent"`.
- Idempotent: second close → `AlreadyClosedError`, exit 1, structured error JSON in `--json` mode.
- Auto-commits the Op record at close.
