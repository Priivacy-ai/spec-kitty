# Research: Event Architecture — Git Semantic Truth + WebSocket Awareness (CLI)

**Mission:** event-architecture-cli-git-truth-01KT119Y
**Date:** 2026-06-01

---

## Decision 1: Decision event commit strategy

**Decision:** Eager per-answer commit — file appends are immediate for both event types; git commit is triggered by the answer event only.

**Rationale:** An unanswered request in git is not meaningful as a decision record. The atomic unit is the request+answer pair. Appending to disk immediately gives OS-level crash durability for both events; triggering the commit on answer gives a clean one-commit-per-decision history. Orphaned request lines (session crash between request and answer) are left in place — the SaaS reader is expected to handle a request line with no subsequent matching answer line gracefully.

**Alternatives considered:**
- *Commit on request + commit on answer* — generates two commits per decision, one of which records an incomplete decision. Rejected because it produces noise in git history.
- *Lazy session-end commit* — batches all decision events into one commit at session close. Rejected because a session crash loses all decisions from that session, violating the durability goal.

---

## Finding 2: Existing write paths for decision events

**Current state:** `DecisionInputRequested` and `DecisionInputAnswered` are emitted via `RuntimeEventEmitter` in `engine.py` (lines ~447, ~697–701). The concrete emitter is `JsonlEventLog`, which writes to a local debug log (`.kittify/events/...`). There is **no** write to `kitty-specs/<mission>/decisions.events.jsonl` and no git commit.

**Impact on design:** A new `DecisionGitLog` emitter class is needed. It wraps `JsonlEventLog` for the existing local debug log, adds an append to `decisions.events.jsonl` (after PII sanitization), and triggers `safe_commit()` on answer. The engine's emitter wiring in `next/runtime_bridge.py` or wherever the concrete emitter is constructed needs updating.

**Alternatives considered:**
- Modifying `JsonlEventLog` in-place — rejected because `JsonlEventLog` has no awareness of missions, repo roots, or git. Adding those dependencies violates separation of concerns.
- A post-emit hook at the propagator layer — rejected because the propagator is WebSocket/SaaS-focused; adding git commits there mixes two orthogonal concerns.

---

## Finding 3: safe_commit API contract

**Current state:** `safe_commit()` in `git/commit_helpers.py:742` is keyword-only, takes `repo_root`, `worktree_root`, `destination_ref`, `message`, and `paths`. It asserts HEAD matches `destination_ref` before staging, validates the worktree, and returns a `CommitResult` carrying the new SHA.

**Protected branch guard:** `safe_commit` refuses commits to branches listed in `PROTECTED_BRANCHES` (includes `main`). Decision event commits must land on the **coordination branch** (`kitty/mission-<slug>-<mid8>`), not on `main`. The engine's emitter must receive the coordination branch as `destination_ref`.

**Impact on design:** The `DecisionGitLog` emitter must be initialized with `repo_root`, `worktree_root`, `destination_ref` (coordination branch), and `mission_slug`. All of these are available at engine startup.

---

## Finding 4: PII fields in current event envelopes

**Fields confirmed present in event envelopes** (from `propagator.py`, `engine.py`, `glossary/events.py`):
- `machine_name` / `hostname` — emitted in session-start envelope
- `workspace_path` — absolute path, present in some payload shapes
- `developer_name`, `developer_email` — present in session-level fields
- Absolute session start/end timestamps — present in `MissionRunStartedPayload`, `MissionRunCompletedPayload`

**Sanitizer design:** A pure function `sanitize_event_for_log(envelope: dict[str, Any]) -> dict[str, Any]` that removes the named fields and replaces absolute timestamps with a relative `session_duration_s: int` field. Applied at two boundaries: `DecisionGitLog` (before writing to `decisions.events.jsonl`) and the existing `status.events.jsonl` write path (in `status/store.py::append_event`).

**Fields to preserve:** `node_id`, `build_id`, `mission_id`, `project_uuid`, `git_branch`, `head_commit_sha`, `session_duration_s`, all event-type-specific payload fields.

---

## Finding 5: WebSocket send API

**Current state:** `invocation/propagator.py` exposes `_send_event(client, event_dict)` which calls `await client.send_event(event_dict)` asynchronously via `asyncio.create_task`. The `WebSocketClient` is reachable via `token_manager._ws_client` when connected.

**`_listen()` loop:** The WebSocket client has a `_listen()` coroutine that processes inbound frames. Adding a `LocalCommitAck` handler requires adding a dispatch branch for `event_type == "LocalCommitAck"`.

**On-connect flush:** `WebSocketClient.connect()` currently receives an initial snapshot but sends nothing. Adding flush-on-connect means: after the snapshot is received, read `sync-state.json`, and for each pending `LocalCommit` frame newer than `last_saas_confirmed_hash`, call `send_event()` in order.

**`sync-state.json` location:** `.kittify/sync-state.json` — project-scoped (not user-scoped), consistent with `.kittify/merge-state.json`. Written atomically using `specify_cli.core.atomic.atomic_write`.

---

## Finding 6: Glossary event queue writes

**Current state:** Every glossary event type (including `GlossarySenseUpdated`) goes through `_persist_event()` in `glossary/events.py`. The canonical path (`_pkg_append_event`) routes to the `spec-kitty-events` persistence adapter which ultimately enqueues for SaaS delivery. The local JSONL path writes to `.kittify/events/glossary/<mission_id>.events.jsonl`.

**Required change:** In `emit_glossary_sense_updated()`, skip the canonical adapter (`_pkg_append_event`) entirely. The local JSONL write is unchanged. This is a single-function change with a guard: `if event_type == "GlossarySenseUpdated": skip canonical adapter`.

**Baseline for NFR-004 measurement:** In a typical mission session that runs 10 extraction steps, the current implementation emits approximately 10–30 `GlossarySenseUpdated` events per step (one per term candidate evaluated), for a session total of ~100–300 queue writes from glossary events alone. After this change, only `GlossaryClarificationResolved` and `GlossaryClarificationRequested` events reach the queue — typically 0–5 per session. This represents a ≥97% reduction against the baseline, well above the NFR-004 threshold of ≥90%. A 10-step session with zero clarifications produces exactly 0 glossary queue writes post-change.

**Seed file update:** After `GlossaryClarificationResolved`, the seed file (`.kittify/glossaries/<scope>.yaml`) is updated via `glossary/store.py`. This already happens — the change confirms it happens immediately and synchronously, not deferred.

---

## Finding 7: Invariant — decisions.events.jsonl format

`decisions.events.jsonl` must use the same format as `status.events.jsonl`: one JSON object per line, keys sorted, `separators=(",", ":")`, append-only. This ensures the same tooling (log replay, migration utilities) works without modification.

The standard envelope shape:
```json
{"at":"<ISO8601-UTC>","build_id":"<ULID>","event_id":"<ULID>","event_type":"DecisionInputRequested","mission_id":"<ULID>","payload":{...}}
```

PII fields must not appear in the serialized line.

---

## Finding 8: LocalCommit frame — no existing precedent in CLI

No `LocalCommit` message type exists anywhere in the current CLI codebase. This is fully new. The frame structure defined in issue #1548 is canonical:

```json
{
  "type": "LocalCommit",
  "git_hash": "<full SHA>",
  "mission_id": "<ULID>",
  "build_id": "<ULID>",
  "changed_files": ["kitty-specs/my-mission/decisions.events.jsonl"],
  "committed_at": "<ISO8601-UTC>"
}
```

No PII fields. `build_id` replaces any session-identifying fields. The `type` discriminator follows the existing WebSocket frame convention (other frames use `"type"` not `"event_type"`).
