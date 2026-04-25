# CLI Contracts — `spec-kitty agent decision ...`

All commands:
- accept `--mission <handle>` (mission_id, mid8, or mission_slug; uses existing context resolver).
- accept `--actor <id>` (defaults to git-configured user email or `cli`).
- accept `--dry-run` (validate + report would-have-been output, no side effects). Default false except where noted.
- return JSON to stdout. Exit 0 on success, non-zero on structured error. Errors are JSON with `error`, `code`, optional `details`.

## `spec-kitty agent decision open`

**Purpose:** Open a Decision Moment at ask time.

**Required args:** `--flow {charter|specify|plan}`, `--input-key <str>`, `--question <str>`, exactly one of `--step-id <str>` OR `--slot-key <str>`.

**Optional:** `--options '["a","b",...]'` (JSON array), `--actor <id>`, `--dry-run`.

**Behavior:**
1. Resolve mission via context resolver.
2. Build logical key. Look up in index. If matching non-terminal entry exists, return its `decision_id` with `idempotent=true`; do NOT emit event.
3. If matching terminal entry exists, return error `DECISION_ALREADY_CLOSED`.
4. Else: mint ULID, append index entry (status=open), create `DM-<id>.md`, emit `DecisionPointOpened` event.

**Success output:**
```json
{
  "decision_id": "01J2A...",
  "idempotent": false,
  "mission_id": "01KPWT8P...",
  "artifact_path": "kitty-specs/<mission>/decisions/DM-01J2A....md",
  "event_lamport": 42
}
```

**Error (already_closed):**
```json
{"error": "Decision already closed", "code": "DECISION_ALREADY_CLOSED",
 "details": {"decision_id": "01J2A...", "status": "resolved"}}
```

## `spec-kitty agent decision resolve <decision_id>`

**Required:** `--final-answer <str>` (non-empty).
**Optional:** `--other-answer` (flag), `--rationale <str>`, `--resolved-by <id>`, `--actor <id>`, `--dry-run`.

**Behavior:** Idempotent on exact payload match. Emits `DecisionPointResolved(terminal_outcome=resolved)`. Updates index + artifact. Charter path additionally writes to `answers.yaml` via existing charter persistence helper.

**Success output:**
```json
{
  "decision_id": "01J2A...",
  "status": "resolved",
  "terminal_outcome": "resolved",
  "idempotent": false,
  "event_lamport": 57
}
```

## `spec-kitty agent decision defer <decision_id>`

**Required:** `--rationale <str>` (non-empty).
**Optional:** `--resolved-by <id>`, `--actor <id>`, `--dry-run`.

**Behavior:** Emits `DecisionPointResolved(terminal_outcome=deferred)`. No `DecisionInputAnswered`. No answers.yaml write.

## `spec-kitty agent decision cancel <decision_id>`

**Required:** `--rationale <str>` (non-empty).
**Optional:** `--resolved-by <id>`, `--actor <id>`, `--dry-run`.

**Behavior:** Emits `DecisionPointResolved(terminal_outcome=canceled)`. No `DecisionInputAnswered`. No answers.yaml write.

## `spec-kitty agent decision verify`

**Required:** `--mission <handle>`.

**Optional:** `--format {json|text}` (default `json`), `--fail-on-stale` (default `true`).

**Behavior:** Load index, scan `spec.md` and `plan.md` for inline markers, cross-reference. Return structured findings.

**Success (clean):**
```json
{"status": "clean", "deferred_count": 3, "marker_count": 3, "findings": []}
```

**Finding types:**
- `DEFERRED_WITHOUT_MARKER` — deferred decision has no matching inline marker.
- `MARKER_WITHOUT_DECISION` — inline marker references an unknown decision_id.
- `STALE_MARKER` — marker references a decision that's no longer deferred.

Exit code: 0 on clean, non-zero if `findings != []`.

## Terminal command error codes

- `DECISION_NOT_FOUND` — decision_id unknown in this mission's index.
- `DECISION_TERMINAL_CONFLICT` — already terminal with different payload (e.g., resolve after defer, or resolve with a different final_answer).
- `DECISION_ALREADY_CLOSED` — (used on `open` idempotency miss, not on terminal commands retried identically).
