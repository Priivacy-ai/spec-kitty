# Data Model: Event Architecture — Git Semantic Truth + WebSocket Awareness (CLI)

**Mission:** event-architecture-cli-git-truth-01KT119Y
**Date:** 2026-06-01

---

## New Files & Schemas

### `kitty-specs/<mission_slug>/decisions.events.jsonl`

Append-only JSONL file, one record per line, keys sorted. Created on first decision event for the mission. Co-located with `status.events.jsonl`.

**Record shape (both event types):**

```json
{
  "at": "<ISO8601-UTC>",
  "build_id": "<ULID>",
  "event_id": "<ULID>",
  "event_type": "DecisionInputRequested | DecisionInputAnswered",
  "mission_id": "<ULID>",
  "payload": { "<event-type-specific fields>" }
}
```

**Invariants:**
- No PII fields at any level (envelope or payload).
- `event_id` is a unique ULID per record.
- `at` is UTC ISO8601; no local timezone offset.
- File is never rewritten or compacted; only appended.
- `DecisionInputRequested` and `DecisionInputAnswered` records appear in chronological order; each `Answered` record follows its `Requested` record.
- Orphaned `Requested` records (no matching `Answered`) are valid; they indicate a session that ended before the decision was resolved.

**Lifecycle:**
- Created lazily on first `DecisionInputRequested` for the mission.
- Committed to git on each `DecisionInputAnswered` (capturing the request+answer pair).
- Never deleted or truncated by the CLI.

---

### `.kittify/sync-state.json`

Project-scoped file tracking WebSocket sync state. Written atomically.

```json
{
  "last_saas_confirmed_hash": "<full git SHA | null>",
  "pending_local_commits": [
    {
      "type": "LocalCommit",
      "git_hash": "<full SHA>",
      "mission_id": "<ULID>",
      "build_id": "<ULID>",
      "changed_files": ["kitty-specs/<mission>/decisions.events.jsonl"],
      "committed_at": "<ISO8601-UTC>"
    }
  ]
}
```

**Invariants:**
- `last_saas_confirmed_hash` is `null` until the SaaS sends the first `LocalCommitAck`.
- `pending_local_commits` is ordered chronologically (oldest first).
- Each entry in `pending_local_commits` is a complete `LocalCommit` frame — the same dict sent over WebSocket.
- When a `LocalCommitAck` is received for hash H: remove all entries from `pending_local_commits` with `git_hash == H` and update `last_saas_confirmed_hash = H`.
- When a commit is amended: the new `LocalCommit` frame (new hash) replaces the prior pending frame for the same build_id.
- No PII fields.

**Lifecycle:**
- Created on first `LocalCommit` emit if not present.
- Updated atomically on every emit and every `LocalCommitAck`.
- Never deleted; grows bounded (entries are removed as the SaaS acknowledges them).

---

## Modified Files

### `kitty-specs/<mission_slug>/status.events.jsonl`

**Change:** PII sanitization applied before every append (both new and existing write paths via `status/store.py::append_event`). Field list stripped: `machine_name`, `hostname`, `workspace_path`, `developer_name`, `developer_email`. Absolute session timestamps replaced by `session_duration_s: int`.

No structural change to the existing format.

---

### `.kittify/glossaries/<scope>.yaml`

**Change:** Updated immediately (synchronously) after each `GlossaryClarificationResolved` event. No structural change to the YAML format.

**Glossary state equality definition (for FR-022):**

Two glossary states are considered equal when, for every scope, the set of term keys is identical and each term's `resolution_text` value is identical. Timestamps and internal metadata fields are excluded from equality comparison. Reconstruction from `seed file + GlossaryClarificationResolved events` is valid if the following holds: iterating all `GlossaryClarificationResolved` events in chronological order and applying each as an upsert to the seed state produces an identical `{scope → {term_key → resolution_text}}` map as the direct seed file read.

Example equivalent states:
```yaml
# scope: core
terms:
  mission:
    resolution_text: "A time-boxed unit of specification and implementation work."
  work_package:
    resolution_text: "A scoped, independently implementable coding task within a mission."
```

`GlossarySenseUpdated` events carry intermediate extraction hypotheses that are superseded by the final `GlossaryClarificationResolved` outcome. Omitting them from reconstruction does not change the final resolved state.

---

## New Modules

### `specify_cli/events/sanitizer.py`

**Exports:** `sanitize_event_for_log(envelope: dict[str, Any]) -> dict[str, Any]`

Pure function. Input is an arbitrary event envelope dict. Output is a new dict with PII fields removed and absolute session timestamps replaced by `session_duration_s`.

**PII fields stripped (at all nesting levels):** `machine_name`, `hostname`, `workspace_path`, `developer_name`, `developer_email`.

**Timestamp replacement:** If both `session_started_at` and `session_ended_at` are present, compute `session_duration_s = int((ended - started).total_seconds())` and remove both source fields. If only `session_started_at` is present (session still running), remove it without replacement.

**Invariant:** Function is pure — does not mutate the input dict. Returns a deep copy.

---

### `specify_cli/events/decision_log.py`

**Exports:** `DecisionGitLog` (implements `RuntimeEventEmitter` protocol)

**Constructor:** `DecisionGitLog(repo_root, worktree_root, destination_ref, mission_slug, *, inner: RuntimeEventEmitter)`

- `inner` is the existing emitter (e.g. `JsonlEventLog`) that continues to write to the local debug log.

**Behavior:**
- `emit_decision_input_requested(payload)` — sanitize payload, append to `decisions.events.jsonl`, delegate to `inner`.
- `emit_decision_input_answered(payload)` — sanitize payload, append to `decisions.events.jsonl`, call `safe_commit(repo_root, worktree_root, destination_ref, message, paths=(decisions_file,))`, delegate to `inner`.
- All other `emit_*` methods — delegate to `inner` only (no git write).

**Commit message:** `"chore(decisions): record decision for <mission_slug> [skip ci]"`

---

### `specify_cli/sync/local_commit.py`

**Exports:**
- `emit_local_commit(repo_root, git_hash, mission_id, build_id, changed_files, committed_at)` — build and send the `LocalCommit` frame, or store in `sync-state.json` if not connected.
- `flush_pending_local_commits(repo_root, client)` — send all pending `LocalCommit` frames newer than `last_saas_confirmed_hash`.
- `record_local_commit_ack(repo_root, git_hash)` — update `sync-state.json` on `LocalCommitAck`.
- `load_sync_state(repo_root) -> SyncState` / `save_sync_state(repo_root, state)`.

**`SyncState` dataclass:**
```python
@dataclass
class SyncState:
    last_saas_confirmed_hash: str | None
    pending_local_commits: list[dict[str, Any]]
```

**Invariant:** All writes to `sync-state.json` use `atomic_write` from `specify_cli.core.atomic`.

---

## State Transitions

### Decision event lifecycle

```
[engine requests decision]
    → DecisionInputRequested appended to decisions.events.jsonl (sanitized)
    → delegated to inner emitter (local debug log)
    
[user/agent answers]
    → DecisionInputAnswered appended to decisions.events.jsonl (sanitized)
    → safe_commit() → CommitResult.sha
    → LocalCommit frame emitted (triggers local_commit.emit_local_commit)
    → delegated to inner emitter
    
[session crash after request, before answer]
    → decisions.events.jsonl has orphaned Requested line
    → no git commit (acceptable; SaaS handles gracefully)
```

### LocalCommit lifecycle

```
[safe_commit succeeds on kitty-specs/ path]
    → build LocalCommit frame
    → if WebSocket connected: send immediately via send_event()
    → if not connected: append to sync-state.json pending_local_commits
    
[WebSocket reconnects]
    → flush_pending_local_commits() sends all pending frames in order
    
[SaaS sends LocalCommitAck(hash=H)]
    → record_local_commit_ack() removes H from pending, updates last_saas_confirmed_hash
    
[commit amended]
    → new LocalCommit frame (new hash, same build_id)
    → replace prior pending frame for this build_id in sync-state.json
```

### Glossary queue lifecycle (after change)

```
GlossarySenseUpdated:
    → local JSONL append (.kittify/events/glossary/) ← UNCHANGED
    → canonical adapter (_pkg_append_event) ← REMOVED

GlossaryClarificationResolved:
    → local JSONL append ← UNCHANGED
    → canonical adapter → queue ← UNCHANGED
    → seed file (.kittify/glossaries/<scope>.yaml) updated immediately ← UNCHANGED (confirmed synchronous)

GlossaryClarificationRequested:
    → local JSONL append ← UNCHANGED
    → canonical adapter → queue ← UNCHANGED
```
