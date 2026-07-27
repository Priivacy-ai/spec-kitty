---
work_package_id: WP05
title: 'LocalCommit Core: SyncState and Frame Logic'
dependencies: []
requirement_refs:
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-event-architecture-cli-git-truth-01KT119Y
base_commit: faaf611259fa3591387b77a6662d1612f5e6b6db
created_at: '2026-06-01T08:19:38.832985+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
agent: "claude:claude-sonnet-4-6:orchestrator:orchestrator"
shell_pid: "68886"
history:
- date: '2026-06-01'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/local_commit.py
- tests/specify_cli/sync/test_local_commit.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Create `src/specify_cli/sync/local_commit.py` — the complete data layer and business logic for the `LocalCommit` feature. This WP builds the core machinery: `SyncState` dataclass, atomic `sync-state.json` persistence, `emit_local_commit()`, `flush_pending_local_commits()`, `record_local_commit_ack()`, and amended-commit handling. No integration with `commit_helpers.py` or the WebSocket client yet — that is WP06.

**Implement command**: `spec-kitty agent action implement WP05 --agent claude`

**Dependencies**: None — independent, can run in parallel with all of Lane A and WP04.

---

## Context

**The `LocalCommit` frame** (from `contracts/websocket-frames.md`):
```json
{
  "type": "LocalCommit",
  "git_hash": "<full 40-char SHA>",
  "mission_id": "<ULID>",
  "build_id": "<ULID>",
  "changed_files": ["kitty-specs/<mission>/decisions.events.jsonl"],
  "committed_at": "2026-06-01T07:30:00Z"
}
```

**`sync-state.json`** lives at `.kittify/sync-state.json` and holds:
```json
{
  "last_saas_confirmed_hash": "<SHA | null>",
  "pending_local_commits": [ { ...LocalCommit frame... }, ... ]
}
```

**Key behaviors**:
- `emit_local_commit()`: if connected → send immediately; if not → store as pending in `sync-state.json`.
- `flush_pending_local_commits()`: called on WebSocket connect; sends all pending frames with `git_hash` ≠ `last_saas_confirmed_hash` in `committed_at` order.
- `record_local_commit_ack(hash)`: removes entry for `hash` from pending; updates `last_saas_confirmed_hash`.
- Amended commit: if a new `LocalCommit` has the same `build_id` as a pending entry, replace the old entry.

**Atomic writes**: Use `specify_cli.core.atomic.atomic_write` for all `sync-state.json` writes.

**No PII**: The frame itself has no PII fields by construction (no machine name, no path, no developer identity). No sanitizer call needed here.

**Existing utilities to read**:
- `src/specify_cli/core/atomic.py` — `atomic_write` function
- `src/specify_cli/invocation/propagator.py` — `_get_saas_client()` pattern for checking WebSocket availability + `_send_event()`

**Spec references**: FR-010–FR-017

---

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`

---

## Subtask Guidance

### T019 — `SyncState` dataclass + `load_sync_state()` / `save_sync_state()`

**Purpose**: Establish the persistent state structure and its serialization/deserialization with atomic writes.

**Steps**:
1. Create `src/specify_cli/sync/local_commit.py`.
2. Define `SyncState`:
   ```python
   from dataclasses import dataclass, field
   from typing import Any

   @dataclass
   class SyncState:
       last_saas_confirmed_hash: str | None = None
       pending_local_commits: list[dict[str, Any]] = field(default_factory=list)
   ```
3. Implement `_sync_state_path(repo_root: Path) -> Path`:
   ```python
   def _sync_state_path(repo_root: Path) -> Path:
       return repo_root / ".kittify" / "sync-state.json"
   ```
4. Implement `load_sync_state(repo_root: Path) -> SyncState`:
   - If file does not exist, return `SyncState()` (default empty state).
   - Read JSON, parse into `SyncState`. Treat missing or malformed file as empty state (log warning, never raise).
5. Implement `save_sync_state(repo_root: Path, state: SyncState) -> None`:
   - Serialize `state` to JSON dict.
   - Use `atomic_write` from `specify_cli.core.atomic` to write `sync-state.json`.
   - Ensure parent directory exists (`repo_root / ".kittify"`).

**Files**: `src/specify_cli/sync/local_commit.py` (~60 lines)

---

### T020 — `emit_local_commit()` — build frame, send or store

**Purpose**: Build the `LocalCommit` frame and either send it immediately (if WebSocket connected) or store it as pending.

**Steps**:
1. Define the function:
   ```python
   def emit_local_commit(
       repo_root: Path,
       git_hash: str,
       mission_id: str,
       build_id: str,
       changed_files: list[str],
       committed_at: str,
   ) -> None:
   ```
2. Build the frame dict:
   ```python
   frame = {
       "type": "LocalCommit",
       "git_hash": git_hash,
       "mission_id": mission_id,
       "build_id": build_id,
       "changed_files": changed_files,
       "committed_at": committed_at,
   }
   ```
3. Try to get the WebSocket client (mirror `_get_saas_client()` pattern from `invocation/propagator.py`). If connected, call `_send_event(client, frame)`.
4. If not connected (client is `None` or not connected), load `sync-state.json`, append the frame to `pending_local_commits`, save.
5. If connected, also save the frame to `pending_local_commits` and let `record_local_commit_ack` remove it when acknowledged — this ensures no frame is lost if the send succeeds but ack is never received.

   Actually — simpler approach: always store in pending, then send if connected. On ack, remove. This avoids a race between send and storage.

**Files**: `src/specify_cli/sync/local_commit.py` (+40 lines)

---

### T021 — `flush_pending_local_commits()` — on-connect replay

**Purpose**: On WebSocket connect, send all pending `LocalCommit` frames that have not yet been acknowledged.

**Steps**:
1. Define:
   ```python
   def flush_pending_local_commits(repo_root: Path, client: Any) -> None:
   ```
2. Load `sync-state.json`.
3. Filter `pending_local_commits` to entries whose `git_hash` ≠ `last_saas_confirmed_hash` (unacknowledged).
4. Sort by `committed_at` ascending (chronological order).
5. For each unacknowledged frame, call `_send_event(client, frame)`.
6. Log the count of flushed frames at DEBUG level.

**Files**: `src/specify_cli/sync/local_commit.py` (+25 lines)

---

### T022 — `record_local_commit_ack()` — remove acked frame

**Purpose**: On `LocalCommitAck`, update `last_saas_confirmed_hash` and remove the corresponding pending entry.

**Steps**:
1. Define:
   ```python
   def record_local_commit_ack(repo_root: Path, git_hash: str) -> None:
   ```
2. Load `sync-state.json`.
3. Set `state.last_saas_confirmed_hash = git_hash`.
4. Remove all entries from `state.pending_local_commits` where `entry["git_hash"] == git_hash`.
5. Save the updated state atomically.

**Files**: `src/specify_cli/sync/local_commit.py` (+20 lines)

---

### T023 — Handle amended commit replacement

**Purpose**: When a commit is amended, the new `LocalCommit` frame (new `git_hash`, same `build_id`) supersedes the prior unacknowledged frame for that build.

**Steps**:
1. In `emit_local_commit()` (T020), before appending the new frame to `pending_local_commits`:
   - Check if any existing pending entry has the same `build_id`.
   - If so, remove it (the amended commit supersedes it).
2. Then append the new frame.
3. This ensures the pending list never has two frames for the same `build_id`.

**Implementation note**: The amended-commit detection is in `emit_local_commit()`, not in a separate function. It's a ~5-line addition to the T020 function body.

**Files**: `src/specify_cli/sync/local_commit.py` (+8 lines within emit_local_commit)

---

### T024 — Unit tests for all `local_commit.py` behaviors

**Purpose**: Comprehensive unit tests covering all six behaviors.

**Steps**:
1. Create `tests/specify_cli/sync/test_local_commit.py`.
2. Use `tmp_path` for `repo_root`. Create `.kittify/` dir as needed.
3. **Test: emit when connected — frame stored and sent**:
   ```python
   def test_emit_when_connected_sends_and_stores(tmp_path):
       mock_client = MagicMock()
       mock_client.connected = True
       with patch("specify_cli.sync.local_commit._get_saas_client", return_value=mock_client):
           emit_local_commit(tmp_path, "abc123" * 5 + "abcd", "mission-id", "build-id", ["kitty-specs/m/f.jsonl"], "2026-06-01T07:00:00Z")
       state = load_sync_state(tmp_path)
       assert len(state.pending_local_commits) == 1  # stored for ack
       mock_client.send_event.assert_called()  # or _send_event called
   ```
4. **Test: emit when disconnected — frame stored only**:
   - `_get_saas_client` returns `None`.
   - Assert pending list has 1 entry; no send called.
5. **Test: flush sends frames in chronological order**:
   - Pre-populate `sync-state.json` with 3 pending frames with different `committed_at`.
   - Call `flush_pending_local_commits()` with a mock client.
   - Assert `send_event` called 3 times in ascending `committed_at` order.
6. **Test: ack removes entry and updates confirmed hash**:
   - Pre-populate with 2 pending frames.
   - Call `record_local_commit_ack(hash_of_first)`.
   - Assert `last_saas_confirmed_hash` updated; first entry removed; second remains.
7. **Test: amended commit replaces prior pending entry**:
   - Emit frame with `build_id="B"`, `git_hash="old"`.
   - Emit frame with `build_id="B"`, `git_hash="new"` (amended).
   - Assert `pending_local_commits` has 1 entry with `git_hash="new"`.
8. **Test: load from non-existent file returns empty state** (no exception).
9. **Test: save/load round-trip** preserves all fields.

**Files**: `tests/specify_cli/sync/test_local_commit.py` (~150 lines)

---

## Definition of Done

- [ ] `SyncState` dataclass defined with `last_saas_confirmed_hash` and `pending_local_commits`
- [ ] `load_sync_state()` returns empty `SyncState` if file missing or malformed
- [ ] `save_sync_state()` uses `atomic_write`
- [ ] `emit_local_commit()` stores frame and sends if connected
- [ ] `flush_pending_local_commits()` sends in chronological order
- [ ] `record_local_commit_ack()` removes entry and updates confirmed hash
- [ ] Amended commit replaces prior pending entry for same `build_id`
- [ ] No PII fields in any frame or in `sync-state.json`
- [ ] `mypy --strict` passes
- [ ] All 9 test scenarios pass; ≥90% coverage on `local_commit.py`

## Risks

- `atomic_write` may require a specific argument order — read its signature in `specify_cli/core/atomic.py` before using.
- `_send_event` is async (`asyncio.create_task`). The call in `emit_local_commit()` must handle the case where no event loop is running. Mirror the existing pattern in `invocation/propagator.py:212`.
- `committed_at` ordering: use `datetime.fromisoformat()` for sorting to avoid string-sort issues with UTC offset variants.

## Reviewer Guidance

1. Confirm `save_sync_state()` uses atomic write (no partial writes on crash)
2. Confirm flush sends in `committed_at` ascending order
3. Confirm amended commit test: two emits with same `build_id` → only one pending entry
4. Confirm no `machine_name`, `hostname`, `workspace_path` in any frame or state file

## Activity Log

- 2026-06-01T08:19:39Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=40590 – Assigned agent via action command
- 2026-06-01T08:26:12Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=40590 – Implementation complete, cycle 1. Tests pass (12/12), lint clean. SyncState + atomic persistence, emit_local_commit, flush_pending_local_commits, record_local_commit_ack, amended-commit replacement. No PII. Wired into sync.__init__ for WP06.
- 2026-06-01T08:29:52Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=68886 – Started review via action command
